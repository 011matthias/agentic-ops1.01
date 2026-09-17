"""Epoch-keyed approval and the single dispatch claim.

Ported 2026-09-17 from ECC ``skills/operator-approval-loop``
(affaan-m/everything-claude-code) onto the campaign engine. The campaign-level
gates (Approve, Start sending, kill switch, recipient + template pins, deny
floor, suppression list) all stay; this adds the per-message layer they lacked:
what exactly was approved, and proof that exactly that is what leaves.

Vocabulary, ECC -> here:

* obligation  one enrollment-step owed an email; key = ``attempt_key``
              (``cadence:{enrollment_id}:{step_no}``), 1:1 with send_attempts.
* draft       what that step would send right now: subject + body rendered
              from the pinned template and the contact's current fields, plus
              the destination (from / to / cc / bcc). Sidecar row in
              ``obligation_drafts``.
* epoch       per-obligation counter. Re-filing a draft whose text or
              destination changed advances it. A campaign epoch advances when
              the campaign's manifest (its set of drafts) changes; the approval
              panel shows it with the manifest hash prefix, and the approve
              POST must echo both or it is refused as stale.
* decision    one approve or sequence delta by a named operator.
* snapshot    immutable copy of each obligation's draft (text, sha256, epoch,
              recipient, destination), written in the SAME transaction as its
              decision. The claim binds to the latest snapshot.
* claim       the one dispatch permission per obligation:
              claimed -> dispatching -> delivered | unknown;
              claimed -> cancelled (before dispatch only);
              unknown -> delivered | void (``reconcile``, a trusted human step).

What the database enforces (store.py v14): one active-or-delivered claim per
obligation, one dispatch per (obligation, decision), immutable snapshots and
decisions, legal claim transitions only, and no draft or snapshot rewrite while
a claim on that obligation is in flight.

Guarantee: at most one dispatch attempt per approved decision per obligation.
Not exactly-once delivery: a crash inside the send window is ``unknown``, and
``unknown`` never retries on its own.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3

from .store import ContactStore, attempt_key_for

ACTIVE_CLAIM_STATES = ("claimed", "dispatching", "unknown")

# Refusals that mean "someone else has it" or "nothing to do yet", not "the
# approval does not cover this". They skip quietly instead of raising a guard
# alert.
SILENT_REFUSALS = ("lease_unavailable", "claim_in_flight")


class ClaimRefused(RuntimeError):
    """No dispatch permission (or no state transition) was granted."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


# -- drafts -------------------------------------------------------------------

def draft_sha256(subject: str | None, body: str | None) -> str:
    """The draft text hash. Identical to the claim payload's ``body_hash``,
    so the worker's copy-tamper check and the approval binding agree."""
    return hashlib.sha256(
        ((subject or "") + "\n" + (body or "")).encode("utf-8")).hexdigest()


def _addr_list(raw: str | None) -> list[str]:
    return [raw.strip().lower()] if raw and raw.strip() else []


def destination_json(campaign: dict, to_addr: str) -> str:
    return json.dumps({
        "from": (campaign.get("from_address") or "").strip().lower(),
        "to": (to_addr or "").strip().lower(),
        "cc": _addr_list(campaign.get("cc_address")),
        "bcc": _addr_list(campaign.get("bcc_address")),
    }, sort_keys=True)


def render_obligation(store: ContactStore, campaign: dict, enrollment: dict,
                      step: dict, pins: dict[str, int]) -> dict | None:
    """The draft for one enrollment-step under the given template pins, or
    None when the step cannot send email (not email, no address, unpinned)."""
    from .cadence import render

    if step["channel"] != "email":
        return None
    to_addr = (enrollment.get("email") or "").strip()
    version = pins.get(step["template_key"])
    if not to_addr or version is None:
        return None
    tpl = store.get_template(step["template_key"], version)
    if tpl is None:
        return None
    subject = render(tpl["subject"] or "", enrollment)
    body = render(tpl["body"], enrollment)
    return {
        "attempt_key": attempt_key_for(int(enrollment["enrollment_id"]),
                                       int(step["step_no"])),
        "campaign_id": campaign["campaign_id"],
        "enrollment_id": int(enrollment["enrollment_id"]),
        "contact_id": enrollment.get("contact_id"),
        "step_no": int(step["step_no"]),
        "recipient": to_addr.lower(),
        "destination": destination_json(campaign, to_addr),
        "subject": subject,
        "body": body,
        "draft_sha256": draft_sha256(subject, body),
        "template_key": step["template_key"],
        "template_version": int(tpl["version"]),
    }


def campaign_obligations(store: ContactStore, campaign_id: str,
                         pins: dict[str, int], *, degree: str | None = None,
                         step_nos: set[int] | None = None) -> list[dict]:
    """Every unsent email obligation of the campaign's non-suppressed
    enrollments, rendered under ``pins``. Deliberately independent of the
    enrollment approval stamps, so the manifest the panel shows before
    approval equals the one the approve POST recomputes."""
    from .cadence import parse_sent_steps

    campaign = dict(store.get_campaign(campaign_id))
    sequences = {s["degree"]: s for s in store.sequences_for_campaign(campaign_id)}
    out: list[dict] = []
    for row in store.enrollments_for_campaign(campaign_id):
        e = dict(row)
        if e.get("suppressed"):
            continue
        if degree is not None and e.get("degree") != degree:
            continue
        seq = sequences.get(e.get("degree") or "")
        if seq is None:
            continue
        sent = parse_sent_steps({"sent_steps": e.get("sent_steps"),
                                 "steps_done": e.get("steps_done")})
        for st in seq["steps"]:
            no = int(st["step_no"])
            if no in sent or (step_nos is not None and no not in step_nos):
                continue
            ob = render_obligation(store, campaign, e, st, pins)
            if ob is not None:
                out.append(ob)
    return out


def manifest_sha256(obligations: list[dict]) -> str:
    lines = sorted(f"{o['attempt_key']}|{o['draft_sha256']}|{o['destination']}"
                   for o in obligations)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def approval_manifest(store: ContactStore, campaign_id: str,
                      pins: dict[str, int]) -> dict:
    """What an approval right now would freeze: the obligations, their
    manifest hash, and the campaign epoch that approval would be keyed to (the
    stored epoch, advanced by one if the manifest moved since it was filed).
    Pure read, so rendering the panel never rotates an epoch."""
    obligations = campaign_obligations(store, campaign_id, pins)
    sha = manifest_sha256(obligations)
    campaign = store.get_campaign(campaign_id)
    current = int(campaign["draft_epoch"] or 0)
    epoch = current if sha == campaign["draft_manifest_sha256"] else current + 1
    return {"manifest_sha256": sha, "draft_epoch": epoch,
            "count": len(obligations), "obligations": obligations}


def get_draft(store: ContactStore, attempt_key: str) -> sqlite3.Row | None:
    return store.conn.execute(
        "SELECT * FROM obligation_drafts WHERE attempt_key = ?",
        (attempt_key,)).fetchone()


def _draft_moved(draft: sqlite3.Row | None, ob: dict) -> bool:
    return draft is not None and (draft["draft_sha256"] != ob["draft_sha256"]
                                  or draft["destination"] != ob["destination"])


def active_claim(store: ContactStore, attempt_key: str) -> sqlite3.Row | None:
    return store.conn.execute(
        "SELECT * FROM dispatch_claims WHERE attempt_key = ? AND state IN "
        "('claimed', 'dispatching', 'unknown')", (attempt_key,)).fetchone()


def latest_claim(store: ContactStore, attempt_key: str) -> sqlite3.Row | None:
    return store.conn.execute(
        "SELECT * FROM dispatch_claims WHERE attempt_key = ? "
        "ORDER BY claim_id DESC LIMIT 1", (attempt_key,)).fetchone()


def file_draft(store: ContactStore, ob: dict, now: str) -> dict:
    """File (or re-file) one obligation's draft. A change in text or
    destination advances the epoch. An obligation with a claim in flight is
    never re-filed (``held``): its bytes are frozen until the claim resolves.
    Writes join the caller's transaction."""
    draft = get_draft(store, ob["attempt_key"])
    if draft is None:
        store.conn.execute(
            "INSERT INTO obligation_drafts (attempt_key, campaign_id, enrollment_id, "
            "step_no, draft_epoch, draft_sha256, recipient, destination, subject, "
            "body, template_key, template_version, filed_at) "
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ob["attempt_key"], ob["campaign_id"], ob["enrollment_id"], ob["step_no"],
             ob["draft_sha256"], ob["recipient"], ob["destination"], ob["subject"],
             ob["body"], ob["template_key"], ob["template_version"], now))
        return {"epoch": 1, "changed": True, "held": False}
    if not _draft_moved(draft, ob):
        return {"epoch": int(draft["draft_epoch"]), "changed": False, "held": False}
    if active_claim(store, ob["attempt_key"]) is not None:
        return {"epoch": int(draft["draft_epoch"]), "changed": False, "held": True}
    epoch = int(draft["draft_epoch"]) + 1
    store.conn.execute(
        "UPDATE obligation_drafts SET draft_epoch = ?, draft_sha256 = ?, recipient = ?, "
        "destination = ?, subject = ?, body = ?, template_key = ?, "
        "template_version = ?, filed_at = ? WHERE attempt_key = ?",
        (epoch, ob["draft_sha256"], ob["recipient"], ob["destination"], ob["subject"],
         ob["body"], ob["template_key"], ob["template_version"], now,
         ob["attempt_key"]))
    return {"epoch": epoch, "changed": True, "held": False}


# -- decisions + snapshots ------------------------------------------------------

def record_decision(store: ContactStore, campaign_id: str, kind: str, user: str,
                    now: str, obligations: list[dict], manifest: str,
                    campaign_epoch: int) -> dict:
    """Write one decision and a snapshot per obligation. MUST run inside the
    caller's ``store.transaction()`` together with the approval's other writes
    (status flip, pins), so a decision can never exist without its snapshots
    or the other way round. Obligations with a claim in flight are skipped and
    reported as ``held``."""
    if not store._tx_depth:
        raise RuntimeError("record_decision must run inside store.transaction()")
    held: list[str] = []
    filed: list[tuple[dict, int]] = []
    for ob in obligations:
        if active_claim(store, ob["attempt_key"]) is not None:
            held.append(ob["attempt_key"])
            continue
        filed.append((ob, file_draft(store, ob, now)["epoch"]))
    cur = store.conn.execute(
        "INSERT INTO approval_decisions (campaign_id, kind, decided_by, decided_at, "
        "campaign_draft_epoch, manifest_sha256, snapshot_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (campaign_id, kind, user or "unknown", now, campaign_epoch, manifest,
         len(filed)))
    decision_id = int(cur.lastrowid)
    for ob, epoch in filed:
        store.conn.execute(
            "INSERT INTO approval_snapshots (decision_id, attempt_key, draft_epoch, "
            "draft_sha256, recipient, destination, subject, body, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (decision_id, ob["attempt_key"], epoch, ob["draft_sha256"],
             ob["recipient"], ob["destination"], ob["subject"], ob["body"], now))
    return {"decision_id": decision_id, "snapshots": len(filed), "held": held}


def latest_decision(store: ContactStore, campaign_id: str) -> sqlite3.Row | None:
    return store.conn.execute(
        "SELECT * FROM approval_decisions WHERE campaign_id = ? "
        "ORDER BY decision_id DESC LIMIT 1", (campaign_id,)).fetchone()


def bound_snapshot(store: ContactStore, attempt_key: str) -> sqlite3.Row | None:
    """The snapshot a claim binds to: the obligation's latest decision."""
    return store.conn.execute(
        "SELECT * FROM approval_snapshots WHERE attempt_key = ? "
        "ORDER BY decision_id DESC LIMIT 1", (attempt_key,)).fetchone()


def _binding_refusal(snap: sqlite3.Row | None, draft: sqlite3.Row | None,
                     ob: dict) -> tuple[str, str] | None:
    akey = ob["attempt_key"]
    if snap is None:
        return ("no_approval_snapshot",
                f"{akey}: no approval snapshot covers this message (never "
                "approved, or approved before per-message approval); re-approve")
    if draft_sha256(snap["subject"], snap["body"]) != snap["draft_sha256"]:
        return ("snapshot_corrupt",
                f"{akey}: snapshot text does not match its own hash")
    if draft is None or int(draft["draft_epoch"]) != int(snap["draft_epoch"]):
        current = draft["draft_epoch"] if draft is not None else "none"
        return ("approval_stale",
                f"{akey}: draft re-filed since approval (approved epoch "
                f"{snap['draft_epoch']}, now {current}); re-approve")
    if ob["draft_sha256"] != snap["draft_sha256"]:
        return ("text_mismatch",
                f"{akey}: text hash {ob['draft_sha256'][:8]} is not the approved "
                f"{snap['draft_sha256'][:8]}; re-approve")
    if ob["recipient"] != snap["recipient"]:
        return ("recipient_mismatch",
                f"{akey}: recipient {ob['recipient']!r} is not the approved "
                f"{snap['recipient']!r}; re-approve")
    if ob["destination"] != snap["destination"]:
        return ("destination_mismatch",
                f"{akey}: from/cc/bcc changed since approval; re-approve")
    return None


def _spent(store: ContactStore, attempt_key: str, decision_id: int) -> bool:
    return store.conn.execute(
        "SELECT 1 FROM dispatch_claims WHERE attempt_key = ? AND decision_id = ? "
        "AND dispatched_at IS NOT NULL", (attempt_key, decision_id)).fetchone() is not None


def preview_refusal(store: ContactStore, ob: dict) -> tuple[str, str] | None:
    """Read-only answer to "would claim() refuse this?", for a peek."""
    akey = ob["attempt_key"]
    active = store.conn.execute(
        "SELECT state FROM dispatch_claims WHERE attempt_key = ? AND state IN "
        "('claimed', 'dispatching', 'unknown', 'delivered')", (akey,)).fetchone()
    if active is not None:
        return ("claim_in_flight", f"{akey}: claim already {active['state']}")
    draft = get_draft(store, akey)
    if _draft_moved(draft, ob):
        return ("approval_stale", f"{akey}: draft changed since it was filed; re-approve")
    snap = bound_snapshot(store, akey)
    refusal = _binding_refusal(snap, draft, ob)
    if refusal is None and _spent(store, akey, int(snap["decision_id"])):
        return ("decision_spent", f"{akey}: already dispatched under decision "
                                  f"#{snap['decision_id']}; re-approve to send again")
    return refusal


# -- the claim ------------------------------------------------------------------

def claim(store: ContactStore, ob: dict, *, lease: dict, worker_id: str,
          now: str) -> dict:
    """Reserve one approved obligation for dispatch. Returns the claim token.

    Step 1 re-files the draft in its OWN committed transaction, so an epoch
    advance sticks even though the claim below is then refused: a contact
    field that changes and changes back still leaves the old decision dead.
    Step 2 is one ``BEGIN IMMEDIATE`` unit that validates the binding, takes
    the lease and inserts the claim; any refusal rolls all of it back."""
    akey = ob["attempt_key"]
    with store.transaction():
        file_draft(store, ob, now)
    token = secrets.token_hex(32)
    with store.transaction():
        active = store.conn.execute(
            "SELECT state FROM dispatch_claims WHERE attempt_key = ? AND state IN "
            "('claimed', 'dispatching', 'unknown', 'delivered')", (akey,)).fetchone()
        if active is not None:
            raise ClaimRefused("claim_in_flight", f"{akey}: claim already {active['state']}")
        snap = bound_snapshot(store, akey)
        refusal = _binding_refusal(snap, get_draft(store, akey), ob)
        if refusal is not None:
            raise ClaimRefused(*refusal)
        decision_id = int(snap["decision_id"])
        if _spent(store, akey, decision_id):
            raise ClaimRefused(
                "decision_spent",
                f"{akey}: already dispatched once under decision #{decision_id}; "
                "re-approve to send again")
        if not store.take_lease(**lease):
            raise ClaimRefused("lease_unavailable", f"{akey}: lease not available")
        try:
            store.conn.execute(
                "INSERT INTO dispatch_claims (attempt_key, decision_id, token, state, "
                "worker_id, created_at, updated_at) VALUES (?, ?, ?, 'claimed', ?, ?, ?)",
                (akey, decision_id, token, worker_id, now, now))
        except sqlite3.IntegrityError as exc:
            raise ClaimRefused("claim_in_flight", f"{akey}: {exc}") from exc
    return {"token": token, "decision_id": decision_id,
            "draft_epoch": int(snap["draft_epoch"])}


def _claim_by_token(store: ContactStore, token: str | None) -> sqlite3.Row:
    if not token:
        raise ClaimRefused("no_claim", "a dispatch claim token is required")
    row = store.conn.execute(
        "SELECT * FROM dispatch_claims WHERE token = ?", (token,)).fetchone()
    if row is None:
        raise ClaimRefused("unknown_token", "unknown claim token")
    return row


def current_obligation(store: ContactStore, attempt_key: str) -> dict | None:
    """Re-render an obligation from the store as it is NOW (contact fields,
    campaign destination, pinned template), for the dispatch-time check."""
    try:
        _, eid, step_no = attempt_key.split(":")
        enrollment = store.get_enrollment(int(eid))
    except (ValueError, TypeError):
        return None
    if enrollment is None:
        return None
    campaign = store.get_campaign(enrollment["campaign_id"])
    contact = store.get_contact(enrollment["contact_id"])
    seq = store.get_sequence(enrollment["campaign_id"], enrollment["degree"] or "")
    if campaign is None or contact is None or seq is None:
        return None
    step = next((s for s in seq["steps"] if int(s["step_no"]) == int(step_no)), None)
    if step is None:
        return None
    e = {**dict(contact), "enrollment_id": int(eid)}
    return render_obligation(store, dict(campaign), e, step,
                             store.get_pins(enrollment["campaign_id"]))


def _dispatch_checks(store: ContactStore, row: sqlite3.Row, send: dict) -> sqlite3.Row:
    """The revalidation run immediately before transport: the claim's decision
    is still the obligation's latest, the draft was not re-filed, the text the
    store would render NOW hashes to the approved hash with the approved
    recipient and destination, and the payload in the worker's hand is those
    same bytes. Returns the bound snapshot."""
    akey = row["attempt_key"]
    snap = store.conn.execute(
        "SELECT * FROM approval_snapshots WHERE decision_id = ? AND attempt_key = ?",
        (row["decision_id"], akey)).fetchone()
    latest = bound_snapshot(store, akey)
    if snap is None or latest is None or int(latest["decision_id"]) != int(row["decision_id"]):
        raise ClaimRefused("superseded_decision",
                           f"{akey}: a newer decision replaced the one this claim holds")
    ob = current_obligation(store, akey)
    if ob is None:
        raise ClaimRefused("obligation_gone",
                           f"{akey}: the enrollment, step or template no longer renders")
    refusal = _binding_refusal(snap, get_draft(store, akey), ob)
    if refusal is not None:
        raise ClaimRefused(*refusal)
    if draft_sha256(send.get("subject"), send.get("body")) != snap["draft_sha256"]:
        raise ClaimRefused("payload_mismatch",
                           f"{akey}: the payload about to be sent is not the approved text")
    if (send.get("to") or "").strip().lower() != snap["recipient"]:
        raise ClaimRefused("payload_mismatch",
                           f"{akey}: the payload recipient {send.get('to')!r} is not "
                           f"the approved {snap['recipient']!r}")
    return snap


def verify_claim(store: ContactStore, token: str | None, send: dict) -> dict:
    """``begin_dispatch`` without the state change, for draft-to-self: the
    drill rehearses the same binding checks but transports nothing."""
    row = _claim_by_token(store, token)
    if row["state"] != "claimed":
        raise ClaimRefused("claim_not_claimed", f"claim is {row['state']}")
    snap = _dispatch_checks(store, row, send)
    return _bound_payload(snap, row)


def _bound_payload(snap: sqlite3.Row, row: sqlite3.Row) -> dict:
    return {"attempt_key": row["attempt_key"], "decision_id": int(row["decision_id"]),
            "draft_epoch": int(snap["draft_epoch"]), "draft_sha256": snap["draft_sha256"],
            "subject": snap["subject"], "body": snap["body"], "to": snap["recipient"],
            "destination": json.loads(snap["destination"])}


def begin_dispatch(store: ContactStore, token: str | None, send: dict,
                   now: str) -> dict:
    """The last gate before transport. Revalidates the binding and flips the
    claim claimed -> dispatching in one ``BEGIN IMMEDIATE`` unit, then returns
    the approved bytes; the caller transports THOSE, never a re-render. From
    the moment this commits, a crash is an unknown outcome.

    On refusal the claim is cancelled (nothing was transported) and the draft
    is re-filed, so the stale decision cannot release it on a later try."""
    try:
        with store.transaction():
            row = _claim_by_token(store, token)
            if row["state"] != "claimed":
                raise ClaimRefused("claim_not_claimed",
                                   f"claim is {row['state']}; it cannot dispatch again")
            snap = _dispatch_checks(store, row, send)
            changed = store.conn.execute(
                "UPDATE dispatch_claims SET state = 'dispatching', dispatched_at = ?, "
                "updated_at = ? WHERE token = ? AND state = 'claimed'",
                (now, now, token)).rowcount
            if changed != 1:
                raise ClaimRefused("claim_not_claimed", "dispatch transition lost")
    except ClaimRefused as exc:
        if exc.kind not in ("no_claim", "unknown_token", "claim_not_claimed"):
            cancel(store, token, f"refused at dispatch: {exc}", now)
            ob = current_obligation(store, send.get("attempt_key") or "")
            if ob is not None:
                with store.transaction():
                    file_draft(store, ob, now)
        raise
    return _bound_payload(snap, row)


def cancel(store: ContactStore, token: str | None, reason: str, now: str) -> bool:
    """Release a claim that never began dispatch. No-op in any other state."""
    if not token:
        return False
    with store.transaction():
        changed = store.conn.execute(
            "UPDATE dispatch_claims SET state = 'cancelled', updated_at = ?, "
            "outcome_detail = ? WHERE token = ? AND state = 'claimed'",
            (now, reason[:500], token)).rowcount
    return changed == 1


def complete(store: ContactStore, token: str | None, coordinate: str, now: str) -> bool:
    """Record a confirmed dispatch (claim -> delivered). A repeat with the same
    coordinate is a no-op; a contradicting one is refused. Joins the caller's
    transaction, so the worker records the claim and the attempt/event as one
    unit."""
    if not coordinate or not coordinate.strip():
        raise ClaimRefused("no_coordinate", "a confirmed non-empty coordinate is required")
    with store.transaction():
        row = _claim_by_token(store, token)
        if row["state"] == "delivered":
            if row["coordinate"] != coordinate:
                raise ClaimRefused("coordinate_conflict",
                                   "completion contradicts the recorded delivery")
            return False
        if row["state"] != "dispatching":
            raise ClaimRefused("claim_not_dispatching",
                               f"claim is {row['state']}; only a dispatching claim completes")
        store.conn.execute(
            "UPDATE dispatch_claims SET state = 'delivered', coordinate = ?, "
            "updated_at = ? WHERE token = ?", (coordinate, now, token))
    return True


def mark_unknown(store: ContactStore, token: str | None, detail: str, now: str) -> bool:
    """Record an uncertain outcome. The claim goes ``unknown`` and so does the
    attempt row; neither ever re-leases, expires or retries on its own.

    A claim still in 'claimed' is walked through 'dispatching' first. That
    only happens when other evidence (the journal) says transport may have
    begun, and the conservative reading of that is: it may have gone."""
    with store.transaction():
        row = _claim_by_token(store, token)
        if row["state"] == "unknown":
            return False
        if row["state"] == "claimed":
            store.conn.execute(
                "UPDATE dispatch_claims SET state = 'dispatching', dispatched_at = ?, "
                "updated_at = ? WHERE token = ?", (now, now, token))
        elif row["state"] != "dispatching":
            raise ClaimRefused("claim_not_dispatching",
                               f"claim is {row['state']}; it cannot become unknown")
        store.conn.execute(
            "UPDATE dispatch_claims SET state = 'unknown', updated_at = ?, "
            "outcome_detail = ? WHERE token = ?", (now, detail[:500], token))
        store.update_attempt(row["attempt_key"], {
            "status": "unknown", "failure_reason": f"outcome unknown: {detail}"[:500]})
    return True


def note_evidence(store: ContactStore, token: str | None, note: str, now: str) -> None:
    """Attach found evidence to an unknown claim as a SUGGESTION for the human
    reconciling it. Never changes the state."""
    with store.transaction():
        row = _claim_by_token(store, token)
        if row["state"] != "unknown":
            return
        store.conn.execute(
            "UPDATE dispatch_claims SET outcome_detail = ?, updated_at = ? WHERE token = ?",
            (note[:500], now, token))


def reconcile(store: ContactStore, attempt_key: str, outcome: str, *,
              coordinate: str, evidence: str, user: str, now: str) -> dict:
    """The trusted manual step that resolves an unknown outcome. ``delivered``
    needs the coordinate (internetMessageId, or a Sent Items note) and records
    the send; ``not_delivered`` voids the claim, parks the attempt, and leaves
    the decision spent, so sending again needs a fresh approval. This module
    records what the operator asserts; it does not verify the evidence."""
    evidence = (evidence or "").strip()
    coordinate = (coordinate or "").strip()
    if not evidence:
        return {"ok": False, "error": "evidence is required to reconcile"}
    if not user:
        return {"ok": False, "error": "an identified operator is required"}
    if outcome not in ("delivered", "not_delivered"):
        return {"ok": False, "error": f"bad outcome {outcome!r}"}
    if outcome == "delivered" and not coordinate:
        return {"ok": False, "error": "a delivered reconciliation needs the coordinate"}
    with store.transaction():
        row = store.conn.execute(
            "SELECT * FROM dispatch_claims WHERE attempt_key = ? AND state = 'unknown'",
            (attempt_key,)).fetchone()
        if row is None:
            return {"ok": False, "error": "no unknown-outcome claim for this attempt"}
        attempt = store.get_attempt(attempt_key)
        if outcome == "delivered":
            store.conn.execute(
                "UPDATE dispatch_claims SET state = 'delivered', coordinate = ?, "
                "reconciled_by = ?, reconciliation_evidence = ?, updated_at = ? "
                "WHERE claim_id = ?",
                (coordinate, user, evidence[:1000], now, row["claim_id"]))
            fields = {"status": "sent", "resolved_at": now, "failure_reason": None}
            if coordinate.startswith("<"):
                fields["internet_message_id"] = coordinate
            store.update_attempt(attempt_key, fields)
            enrollment = store.get_enrollment(int(attempt["enrollment_id"])) \
                if attempt is not None else None
            if enrollment is not None:
                store.add_event(
                    contact_id=enrollment["contact_id"], ts=now, channel="email",
                    direction="outbound", type="sent",
                    subject=attempt["rendered_subject"],
                    detail=f"cadence step {attempt['step_no']} (reconciled delivered "
                           f"by {user}: {evidence[:200]})",
                    source="manual", created_by=user, ext_key=attempt_key,
                    campaign=enrollment["campaign_id"], now=now)
        else:
            store.conn.execute(
                "UPDATE dispatch_claims SET state = 'void', reconciled_by = ?, "
                "reconciliation_evidence = ?, updated_at = ? WHERE claim_id = ?",
                (user, evidence[:1000], now, row["claim_id"]))
            store.update_attempt(attempt_key, {
                "status": "parked", "resolved_at": now,
                "failure_reason": f"reconciled NOT delivered by {user}: {evidence}; "
                                  "re-approve before sending again"[:500]})
    return {"ok": True, "outcome": outcome}


def retry_block_reason(store: ContactStore, attempt_key: str) -> str | None:
    """Why an operator Retry / Send fresh / Mark sent must not touch this
    attempt, or None. Unknown outcomes are reconciled, never retried; a
    reconciled-not-delivered send needs a fresh decision first."""
    row = latest_claim(store, attempt_key)
    if row is None:
        return None
    if row["state"] in ("dispatching", "unknown"):
        return ("The outcome of this send is unknown. Reconcile it (delivered or "
                "not delivered) instead of retrying.")
    if row["state"] == "delivered":
        return "This send was already delivered."
    if row["state"] == "void":
        snap = bound_snapshot(store, attempt_key)
        if snap is None or int(snap["decision_id"]) == int(row["decision_id"]):
            return ("Reconciled as not delivered under decision "
                    f"#{row['decision_id']}. Re-approve the campaign before sending again.")
    return None


def claims_for_campaign(store: ContactStore, campaign_id: str) -> dict[str, dict]:
    """Latest claim per attempt_key for one campaign, joined to its snapshot
    hash, for the attempts table."""
    rows = store.conn.execute(
        "SELECT dc.*, s.draft_sha256, s.draft_epoch FROM dispatch_claims dc "
        "JOIN approval_decisions d ON d.decision_id = dc.decision_id "
        "LEFT JOIN approval_snapshots s ON s.decision_id = dc.decision_id "
        "AND s.attempt_key = dc.attempt_key "
        "WHERE d.campaign_id = ? ORDER BY dc.claim_id", (campaign_id,)).fetchall()
    return {r["attempt_key"]: dict(r) for r in rows}


def claim_state_counts(store: ContactStore) -> dict[str, int]:
    return {r["state"]: int(r["n"]) for r in store.conn.execute(
        "SELECT state, COUNT(*) AS n FROM dispatch_claims GROUP BY state")}
