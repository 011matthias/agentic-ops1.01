"""The campaign engine: warmness rules, templates, cadence derivation, outbox.

Everything here is a pure function over store reads plus explicit store
writes; no HTTP, no COM. The extended invariant:

    cadence state = f(enrollments, sequence_steps, event log, suppression,
                      campaign status)

``send_attempts`` is a lock table (leases + audit of what was rendered),
never pipeline truth. A send is real only when its ``sent`` event lands,
carrying the reserved ``ext_key = 'cadence:{enrollment_id}:{step_no}'`` -
the event-hash basis (contact, type, ext_key) then admits at most one such
event per step, ever.

Execution model (owner-approved 2026-07-13):
  * fully automatic AFTER a one-time approval that freezes copy (template
    version pins) + the enrolled list (hash) + schedule/caps;
  * cold degrees auto-send from matthias.silva@ (CC Dirk, BCC the Zoho CRM
    dropbox); the warm degree stages ready drafts in Dirk's mailbox
    (send_mode 'draft-dirk') - his click is the gate on his own name;
  * follow-up stops on reply (ts >= enrolled_at), bounce, suppression,
    pause, or a superseded approval - re-checked at claim time;
  * LinkedIn steps never auto-execute: they surface as manual board tasks
    and block later steps until marked done.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..graph_mail import DEFAULT_DENY_DOMAINS
from .store import CADENCE_PREFIX, DEGREES, ContactStore, attempt_key_for

LEASE_MINUTES = 30
MAX_SEND_ATTEMPTS = 3

# Recipient domains that must NEVER receive a campaign send, regardless of
# approval (a competitor we hold, and our own internal domain). This is the
# immutable floor; canonical in graph_mail.DEFAULT_DENY_DOMAINS (re-exported
# above, beside the send primitives that enforce it). The claim path unions it
# with any operator-configured extras in the 'send_deny_domains' state key,
# and the worker re-checks the floor before the Graph POST. Mirrors the hard
# @sap.com deny in the ga_send_wave.py guard pattern
# (rule_brisken_graph_send_by_id).

# Merge variables a template may reference. Deliberately a whitelist over
# contact columns (regex substitution, NOT Jinja - no template injection).
MERGE_FIELDS = (
    "first_name", "last_name", "company", "job_title", "email", "country",
    "persona", "signal", "tier",
)

_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Seed classification rules for a new campaign (editable data, not code).
DEFAULT_RULES = [
    {"priority": 10, "degree": "warm",
     "predicate": json.dumps({"all": [{"fact": "booth_scan"},
                                      {"field": "if_we_know_them", "matches": "dirk|yes|know"}]}),
     "label": "Booth scan + known to Dirk"},
    {"priority": 15, "degree": "warm",
     "predicate": json.dumps({"all": [{"fact": "has_replied"}]}),
     "label": "Has replied before"},
    {"priority": 20, "degree": "cold_touched",
     "predicate": json.dumps({"all": [{"fact": "prior_outbound"}]}),
     "label": "Prior outreach recipient"},
    {"priority": 90, "degree": "cold",
     "predicate": json.dumps({"all": []}),
     "label": "Net new"},
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _recipient_domain(addr: str) -> str:
    return (addr or "").strip().rsplit("@", 1)[-1].lower()


def deny_domains(store: ContactStore) -> set[str]:
    """Hard-denied recipient domains: the built-in floor unioned with any
    operator-configured extras in the 'send_deny_domains' state key (JSON
    array). A malformed state value falls back to the floor alone."""
    try:
        extra = json.loads(store.get_state("send_deny_domains") or "[]")
    except (json.JSONDecodeError, TypeError):
        extra = []
    if not isinstance(extra, list):
        extra = []
    return {d.strip().lower() for d in (*DEFAULT_DENY_DOMAINS, *extra)
            if isinstance(d, str) and d.strip()}


def _record_guard_alert(store: ContactStore, campaign_id: str,
                        blocks: list[dict], now: str) -> None:
    """Surface send-guard blocks (drifted address, denied domain, unpinned
    copy) as a single per-campaign state row, or clear a stale one when the
    pass is clean. Never called on a peek (peek must not mutate state)."""
    key = f"send_guard_alert:{campaign_id}"
    if blocks:
        store.set_state(key, json.dumps(
            {"at": now, "count": len(blocks), "blocked": blocks[:50]}), now)
    elif store.get_state(key) is not None:
        store.delete_state(key)


# -- templates ----------------------------------------------------------------

def render(text: str, contact: dict) -> str:
    def sub(m: re.Match) -> str:
        name = m.group(1)
        if name not in MERGE_FIELDS:
            return m.group(0)
        return str(contact.get(name) or "")
    return _VAR_RE.sub(sub, text or "")


def missing_vars(text: str, contact: dict) -> list[str]:
    """Vars the text references that are unknown or empty for this contact."""
    out = []
    for name in _VAR_RE.findall(text or ""):
        if name not in MERGE_FIELDS or not str(contact.get(name) or "").strip():
            out.append(name)
    return sorted(set(out))


# -- degree rules --------------------------------------------------------------

def contact_facts(store: ContactStore, contact_id: str) -> dict:
    row = store.conn.execute(
        """
        SELECT
          EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = ?
                  AND e.direction = 'outbound' AND e.type IN ('sent', 'invite')) AS prior_outbound,
          EXISTS (SELECT 1 FROM outreach_events e WHERE e.contact_id = ?
                  AND e.direction = 'inbound' AND e.type = 'reply') AS has_replied
        """,
        (contact_id, contact_id),
    ).fetchone()
    return {"prior_outbound": bool(row["prior_outbound"]),
            "has_replied": bool(row["has_replied"])}


def _cond_holds(cond: dict, contact: dict, facts: dict) -> bool:
    if "fact" in cond:
        name = cond["fact"]
        if name == "booth_scan":
            return bool(contact.get("scanned_at_booth"))
        return bool(facts.get(name))
    field = cond.get("field", "")
    val = str(contact.get(field) or "")
    if "eq" in cond:
        return str(cond["eq"]).strip().lower() == val.strip().lower() or (
            cond["eq"] in (0, 1) and bool(cond["eq"]) == bool(contact.get(field)))
    if "ne" in cond:
        return str(cond["ne"]).strip().lower() != val.strip().lower()
    if "matches" in cond:
        try:
            return re.search(cond["matches"], val, re.I) is not None
        except re.error:
            return False
    if "nonempty" in cond:
        return bool(val.strip()) == bool(cond["nonempty"])
    return False


def evaluate_rules(rules: list[dict], contact: dict, facts: dict) -> tuple[str, str] | None:
    """First matching rule (by priority order) wins -> (degree, label)."""
    for rule in rules:
        try:
            pred = json.loads(rule["predicate"]) if isinstance(rule["predicate"], str) else rule["predicate"]
        except (json.JSONDecodeError, TypeError):
            continue
        conds = pred.get("all", [])
        if all(_cond_holds(c, contact, facts) for c in conds):
            return rule["degree"], rule["label"]
    return None


def classify_enrollments(store: ContactStore, campaign_id: str,
                         user: str | None, now: str) -> dict:
    """(Re-)run the campaign's rules over rule-classified, unapproved
    enrollments. Manual overrides and already-approved rows are never touched.
    Every change lands an audit note event."""
    rules = [dict(r) for r in store.get_rules(campaign_id)]
    changed = skipped = 0
    for row in store.enrollments_for_campaign(campaign_id):
        e = dict(row)
        if e.get("degree_source") == "manual" or e.get("enrollment_approved_at"):
            skipped += 1
            continue
        facts = contact_facts(store, e["contact_id"])
        hit = evaluate_rules(rules, e, facts)
        degree, label = hit if hit else (None, None)
        if degree != e.get("degree"):
            store.set_degree(e["enrollment_id"], degree, "rules", label)
            store.add_event(
                contact_id=e["contact_id"], ts=now, channel="email",
                direction="outbound", type="note",
                subject="degree classified",
                detail=f"{campaign_id}: degree={degree} ({label})",
                source="manual", created_by=user, campaign=campaign_id, now=now,
            )
            changed += 1
    return {"changed": changed, "skipped": skipped}


# -- cadence state derivation ---------------------------------------------------

def parse_sent_steps(progress: dict) -> set[int]:
    """The SET of step_nos already sent for one enrollment. Prefers the
    ``sent_steps`` field (comma-joined step_nos from the enrollment_progress
    view); falls back to treating a ``steps_done`` COUNT as the sent prefix
    ``{1..steps_done}`` when only the count is available (which is exactly the
    append-only truth). step_no is the stable send-identity, so this set is what
    keeps the cadence pointer correct across a mid-sequence INSERT/REORDER."""
    raw = progress.get("sent_steps")
    if raw is None:
        n = int(progress.get("steps_done") or 0)
        return set(range(1, n + 1))
    out: set[int] = set()
    for part in str(raw).split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.add(int(part))
    return out


def enrollment_state(enrollment: dict, progress: dict, steps: list[dict],
                     contact: dict, campaign: dict) -> dict:
    """Pure derivation of one enrollment's cadence state.

    Returns {state, steps_done, steps_total, next_step, next_due}. States:
    stopped:suppressed / stopped:bounced / stopped:replied / no_sequence /
    done / pending_approval / paused / inactive / active.

    The step pointer keys on the SET of sent step_nos, not a positional count:
    the next step is the first (in step_no order) whose step_no has NOT been
    sent, and 'done' means every sequence step's step_no is sent. Since a step's
    identity is its step_no (== its send ext_key), inserting or reordering steps
    never re-sends old copy under a shifted index nor skips the new step."""
    sent = parse_sent_steps(progress)
    total = len(steps)
    # Display count: how many of the CURRENT sequence's steps are already sent
    # (== the old positional steps_done for an append-only sequence).
    steps_done = sum(1 for st in steps if int(st["step_no"]) in sent)
    base = {"steps_done": steps_done, "steps_total": total,
            "next_step": None, "next_due": None}
    if contact.get("suppressed"):
        return {**base, "state": "stopped:suppressed"}
    if progress.get("bounced"):
        return {**base, "state": "stopped:bounced"}
    if progress.get("replied"):
        return {**base, "state": "stopped:replied"}
    if not steps:
        return {**base, "state": "no_sequence"}
    # First step whose step_no is unsent; None means every step has been sent.
    next_idx = next((i for i, st in enumerate(steps)
                     if int(st["step_no"]) not in sent), None)
    if next_idx is None:
        return {**base, "state": "done"}
    status = campaign.get("status") or "draft"
    if not enrollment.get("approved_at") and not enrollment.get("enrollment_approved_at"):
        return {**base, "state": "pending_approval"}
    if status == "draft":
        return {**base, "state": "pending_approval"}
    if status == "paused":
        return {**base, "state": "paused"}
    # 'approved' = frozen + reviewed but sending NOT yet confirmed. It is a
    # deliberate holding state: no due sends until a human presses "Start
    # sending" (status -> 'sending'). This is the in-app confirm gate.
    if status == "approved":
        return {**base, "state": "ready"}
    if status != "sending":
        return {**base, "state": "inactive"}

    next_step = steps[next_idx]  # first step whose step_no is not yet sent
    # Offsets anchor on the PREVIOUS step's actual completion (a delayed send
    # never compresses the follow-up gap); step 1 anchors on approval.
    anchor = (progress.get("last_step_ts")
              or enrollment.get("approved_at")
              or enrollment.get("enrollment_approved_at"))
    anchor_date = date.fromisoformat(str(anchor)[:10]) if anchor else None
    # A campaign 'start no earlier than' date holds the FIRST step (which has no
    # prior completion to anchor on) until that date; later steps already anchor
    # on their prior step's real completion, which is >= the start date.
    snb = campaign.get("start_not_before")
    if snb and not progress.get("last_step_ts"):
        snb_date = date.fromisoformat(str(snb)[:10])
        anchor_date = max(anchor_date, snb_date) if anchor_date else snb_date
    next_due = (anchor_date + timedelta(days=int(next_step["day_offset"]))
                if anchor_date else None)
    return {**base, "state": "active", "next_step": dict(next_step),
            "next_due": next_due.isoformat() if next_due else None}


def parse_window(raw: str | None) -> dict:
    try:
        w = json.loads(raw or "{}")
    except json.JSONDecodeError:
        w = {}
    return {"days": w.get("days", [0, 1, 2, 3, 4]),
            "start": w.get("start", "08:30"),
            "end": w.get("end", "17:30"),
            "tz": w.get("tz", "Europe/Berlin")}


def in_window(window: dict, at: datetime) -> bool:
    local = at.astimezone(ZoneInfo(window["tz"]))
    if local.weekday() not in window["days"]:
        return False
    return window["start"] <= local.strftime("%H:%M") <= window["end"]


def _campaign_today(campaign: dict, at: datetime) -> date:
    tz = ZoneInfo(parse_window(campaign.get("send_window"))["tz"])
    return at.astimezone(tz).date()


def due_items(store: ContactStore, campaign_id: str, at: datetime) -> dict:
    """Everything due now for one campaign: auto email sends (the outbox),
    Dirk-draft loads, and manual LinkedIn tasks. Pure derivation."""
    campaign_row = store.get_campaign(campaign_id)
    if campaign_row is None:
        return {"emails": [], "manual": []}
    campaign = dict(campaign_row)
    sequences = {s["degree"]: s for s in store.sequences_for_campaign(campaign_id)}
    today = _campaign_today(campaign, at)
    emails: list[dict] = []
    manual: list[dict] = []

    for row in store.enrollments_for_campaign(campaign_id):
        e = dict(row)
        seq = sequences.get(e.get("degree") or "")
        steps = seq["steps"] if seq else []
        st = enrollment_state(
            {"approved_at": e.get("enrollment_approved_at")},
            {"steps_done": e.get("steps_done"), "sent_steps": e.get("sent_steps"),
             "last_step_ts": e.get("last_step_ts"),
             "replied": e.get("cadence_replied"), "bounced": e.get("cadence_bounced")},
            steps, e, campaign,
        )
        if st["state"] != "active" or not st["next_due"]:
            continue
        if date.fromisoformat(st["next_due"]) > today:
            continue
        step = st["next_step"]
        akey = attempt_key_for(e["enrollment_id"], step["step_no"])
        attempt = store.get_attempt(akey)
        # Only a missing row or a transient 'queued' row is claimable; leased /
        # sent / drafted (waiting on Dirk) / parked / stalled all block here.
        if attempt is not None and attempt["status"] != "queued":
            if step["channel"] == "linkedin" and attempt["status"] not in ("sent",):
                pass  # keep surfacing an unfinished manual task
            else:
                continue
        item = {
            "enrollment": e, "step": step, "sequence": seq,
            "campaign": campaign, "attempt_key": akey,
            "due": st["next_due"], "steps_done": st["steps_done"],
            "steps_total": st["steps_total"],
            # Operator escape hatch (a re-queued 'queued' row): claim drops
            # the step's reply-to-thread flag and sends fresh.
            "force_fresh": bool(attempt["force_fresh"]) if attempt is not None else False,
        }
        if step["channel"] == "email":
            emails.append(item)
        else:
            manual.append(item)
    emails.sort(key=lambda i: (i["due"], i["enrollment"]["enrollment_id"]))
    manual.sort(key=lambda i: (i["due"], i["enrollment"]["enrollment_id"]))
    return {"emails": emails, "manual": manual}


# -- outbox: claim + result -------------------------------------------------------

def claim_sends(store: ContactStore, worker_id: str, max_items: int,
                at: datetime | None = None, peek: bool = False) -> dict:
    """Lease due email sends across approved campaigns, re-checking every stop
    condition at claim time. The attempt_key PRIMARY KEY makes a double-claim
    structurally impossible; rendering uses the PINNED template versions.

    ``peek=True`` computes the same payload WITHOUT taking leases (worker
    --dry-run must not mutate queue state)."""
    at = at or now_utc()
    now = _iso(at)
    if not peek:
        store.expire_leases(now)
    if (store.get_state("kill_switch") or "0") == "1":
        return {"paused": True, "claims": []}

    claims: list[dict] = []
    # Per-mailbox cap across ALL campaigns from one warm mailbox (global state,
    # 0 = off). Seeded per mailbox on first use, then decremented as this pass
    # claims, so two concurrent campaigns from one mailbox share the budget.
    mailbox_cap = int(store.get_state("mailbox_daily_cap") or 0)
    mailbox_used: dict[str, int] = {}
    for campaign_row in store.list_campaigns():
        campaign = dict(campaign_row)
        # The gate: the worker sends ONLY from a campaign a human has
        # explicitly switched to 'sending'. 'approved' (frozen) does not send.
        if campaign["status"] != "sending":
            continue
        window = parse_window(campaign.get("send_window"))
        if not in_window(window, at):
            continue
        today = _campaign_today(campaign, at)
        snb = campaign.get("start_not_before")
        if snb and today.isoformat() < str(snb)[:10]:
            continue  # scheduled to start on a later date (vacation window)
        cap_left = int(campaign["daily_cap"]) - store.cadence_sends_today(
            campaign["campaign_id"], today.isoformat())
        if cap_left <= 0:
            continue
        # Per-day NEW-contact ramp (None = off): how many more step-1 sends may
        # start today. Follow-up steps are not ramp-limited.
        ramp = int(campaign.get("ramp_per_day") or 0)
        ramp_left = (ramp - store.first_step_sends_today(
            campaign["campaign_id"], today.isoformat())) if ramp > 0 else None
        mbx = campaign["from_address"]
        if mailbox_cap > 0:
            if mbx not in mailbox_used:
                mailbox_used[mbx] = store.mailbox_sends_today(mbx, today.isoformat())
            mbx_remaining = mailbox_cap - mailbox_used[mbx]
        else:
            mbx_remaining = None
        pins = store.get_pins(campaign["campaign_id"])
        recipient_pins = store.get_recipient_pins(campaign["campaign_id"])
        denied = deny_domains(store)
        blocks: list[dict] = []
        due = due_items(store, campaign["campaign_id"], at)
        for item in due["emails"]:
            if (len(claims) >= max_items or cap_left <= 0
                    or (mbx_remaining is not None and mbx_remaining <= 0)):
                break
            e, step = item["enrollment"], item["step"]
            to_addr = (e.get("email") or "").strip()
            if not to_addr:
                continue
            # SEND-SAFETY GUARDS (rule_brisken_graph_send_by_id): a send only
            # ever goes to an address a human froze at approval, never to a
            # denied domain, and only under approved (pinned) copy. Any breach
            # blocks the item and surfaces a loud alert; the safe outcome of
            # uncertainty is "send nothing".
            cid = e["contact_id"]
            pinned_to = recipient_pins.get(cid)
            if pinned_to is None:
                blocks.append({"contact_id": cid, "kind": "recipient_not_approved",
                               "detail": f"{to_addr}: no approval-frozen address; re-approve"})
                continue
            if to_addr.lower() != pinned_to:
                blocks.append({"contact_id": cid, "kind": "recipient_drift",
                               "detail": f"approved {pinned_to!r}, now {to_addr.lower()!r}; re-approve"})
                continue
            if _recipient_domain(to_addr) in denied:
                blocks.append({"contact_id": cid, "kind": "domain_denied",
                               "detail": f"{to_addr}: hard-denied recipient domain"})
                continue
            sup = store.suppression_hit(to_addr)
            if sup is not None:
                blocks.append({"contact_id": cid, "kind": "suppression-list",
                               "detail": f"{to_addr}: on the suppression list "
                                         f"({sup['kind']} {sup['entry']})"})
                continue
            if step["template_key"] not in pins:
                blocks.append({"contact_id": cid, "kind": "unpinned_template",
                               "detail": f"step {step['step_no']} template "
                                         f"{step['template_key']!r} not pinned; re-approve"})
                continue
            # Per-day ramp: hold fresh (step-1) contacts once today's ramp is
            # spent. A benign, intentional deferral (no alert); the contact
            # stays step-1 and starts on a later day.
            if ramp_left is not None and step["step_no"] == 1 and ramp_left <= 0:
                continue
            version = pins.get(step["template_key"])
            tpl = store.get_template(step["template_key"], version)
            if tpl is None:
                continue
            subject = render(tpl["subject"] or "", e)
            body = render(tpl["body"], e)
            lease_id = secrets.token_hex(16)
            lease_expires = _iso(at + timedelta(minutes=LEASE_MINUTES))
            if not peek and not store.try_lease(
                attempt_key=item["attempt_key"], enrollment_id=e["enrollment_id"],
                step_no=step["step_no"], send_mode=item["sequence"]["send_mode"],
                lease_id=lease_id, lease_expires=lease_expires, worker_id=worker_id,
                to_addr=to_addr, rendered_subject=subject, rendered_body=body,
                template_key=step["template_key"], template_version=int(tpl["version"]),
                now=now, max_attempts=MAX_SEND_ATTEMPTS,
            ):
                continue
            if peek:
                lease_id = None
                lease_expires = None
            cap_left -= 1
            if ramp_left is not None and step["step_no"] == 1:
                ramp_left -= 1
            if mbx_remaining is not None:
                mbx_remaining -= 1
                mailbox_used[mbx] = mailbox_used.get(mbx, 0) + 1
            prior = attempt_key_for(e["enrollment_id"], step["step_no"] - 1) \
                if step["step_no"] > 1 else None
            claims.append({
                "attempt_key": item["attempt_key"],
                "lease_id": lease_id,
                "lease_expires": lease_expires,
                "enrollment_id": e["enrollment_id"],
                "step_no": step["step_no"],
                "contact_id": e["contact_id"],
                "campaign_id": campaign["campaign_id"],
                "send_mode": item["sequence"]["send_mode"],
                "to": to_addr,
                "cc": [campaign["cc_address"]] if campaign.get("cc_address") else [],
                "bcc": [campaign["bcc_address"]] if campaign.get("bcc_address") else [],
                "from": campaign["from_address"],
                "subject": subject,
                "body": body,
                "body_hash": hashlib.sha256(
                    (subject + "\n" + body).encode("utf-8")).hexdigest(),
                "template_key": step["template_key"],
                "template_version": int(tpl["version"]),
                "thread_ext_key": prior,
                # In-thread reply step: the worker sends this as a Graph reply
                # anchored on the prior step's sent mail. An operator
                # force_fresh (send-fresh escape hatch) overrides it back to a
                # plain fresh send.
                "reply_to_prior": bool(step.get("reply_to_prior"))
                and not item.get("force_fresh"),
                "throttle_seconds": int(campaign["throttle_seconds"]),
                "jitter_seconds": int(campaign["jitter_seconds"]),
            })
        if not peek:
            _record_guard_alert(store, campaign["campaign_id"], blocks, now)
    return {"paused": False, "claims": claims}


def resolve_result(store: ContactStore, payload: dict) -> dict:
    """Worker result for one claim. Idempotent: a repeat 'sent' ack changes
    nothing (the event hash admits one row). Emits the cadence 'sent' event -
    the moment the send becomes pipeline truth."""
    now = _iso(now_utc())
    akey = (payload.get("attempt_key") or "").strip()
    lease_id = (payload.get("lease_id") or "").strip()
    status = (payload.get("status") or "").strip()
    attempt = store.get_attempt(akey)
    if attempt is None:
        return {"ok": False, "error": "unknown attempt_key"}
    if status not in ("sent", "drafted", "failed"):
        return {"ok": False, "error": f"bad status {status!r}"}
    if attempt["lease_id"] != lease_id:
        # A repeat ack after we already recorded this outcome is fine.
        if attempt["status"] == status:
            return {"ok": True, "idempotent": True}
        return {"ok": False, "error": "lease mismatch", "http": 409}

    enrollment = store.get_enrollment(int(attempt["enrollment_id"]))
    if enrollment is None:
        return {"ok": False, "error": "orphan attempt"}

    if status == "sent":
        occurred = (payload.get("occurred_at") or "").strip() or now
        store.update_attempt(akey, {
            "status": "sent", "resolved_at": now,
            "internet_message_id": payload.get("internet_message_id"),
            "entry_id": payload.get("entry_id"),
        })
        inserted = store.add_event(
            contact_id=enrollment["contact_id"], ts=occurred, channel="email",
            direction="outbound", type="sent",
            subject=attempt["rendered_subject"],
            detail=f"cadence step {attempt['step_no']} "
                   f"({attempt['template_key']} v{attempt['template_version']})",
            source="worker-auto", created_by=attempt["worker_id"],
            ext_key=akey, campaign=enrollment["campaign_id"], now=now,
        )
        return {"ok": True, "event_inserted": inserted}

    if status == "drafted":
        # Staged in Dirk's Drafts; the step completes (event lands) only when
        # his actual send is observed - keeps 'a send is real only when the
        # event lands' honest, and no follow-up fires while he sits on it.
        store.update_attempt(akey, {
            "status": "drafted", "resolved_at": now,
            "entry_id": payload.get("entry_id"),
        })
        return {"ok": True, "event_inserted": False}

    # failed
    error_class = (payload.get("error_class") or "permanent").strip()
    reason = (payload.get("failure_reason") or payload.get("detail") or "").strip()
    if error_class == "transient" and int(attempt["attempt_count"]) < MAX_SEND_ATTEMPTS:
        new_status = "queued"
    else:
        new_status = "parked"
    store.update_attempt(akey, {
        "status": new_status, "resolved_at": now,
        "failure_reason": f"{error_class}: {reason}"[:500],
    })
    return {"ok": True, "requeued": new_status == "queued"}


def confirm_draft_sent(store: ContactStore, payload: dict) -> dict:
    """A 'drafted' attempt observed actually sent (capture matched Dirk's Sent
    Items by recipient+subject). Lease already consumed; match on key alone."""
    now = _iso(now_utc())
    akey = (payload.get("attempt_key") or "").strip()
    attempt = store.get_attempt(akey)
    if attempt is None or attempt["status"] not in ("drafted", "sent"):
        return {"ok": False, "error": "not a drafted attempt"}
    enrollment = store.get_enrollment(int(attempt["enrollment_id"]))
    if enrollment is None:
        return {"ok": False, "error": "orphan attempt"}
    occurred = (payload.get("occurred_at") or "").strip() or now
    store.update_attempt(akey, {
        "status": "sent", "resolved_at": now,
        "internet_message_id": payload.get("internet_message_id"),
    })
    inserted = store.add_event(
        contact_id=enrollment["contact_id"], ts=occurred, channel="email",
        direction="outbound", type="sent",
        subject=attempt["rendered_subject"],
        detail=f"cadence step {attempt['step_no']} sent by Dirk "
               f"({attempt['template_key']} v{attempt['template_version']})",
        source="worker-auto", created_by="dirk",
        ext_key=akey, campaign=enrollment["campaign_id"], now=now,
    )
    return {"ok": True, "event_inserted": inserted}


def enumerate_wave(store: ContactStore, campaign_id: str) -> dict:
    """Enumerate one campaign's staged draft-dirk wave from journaled attempts:
    every send_attempt with status 'drafted' AND a correlated Outlook entry_id.
    Read-only visibility - this NEVER sends or releases anything (the gated
    release action is a separate, later decision).

    Each candidate re-runs the claim-time send-safety guards
    (rule_brisken_graph_send_by_id) as PRE-checks, because the world can move
    between staging and Dirk's click: the recipient must still equal its
    approval-frozen ``campaign_recipient_pins`` address, its domain must not be
    denied, and the contact must not be suppressed. Failures land in
    ``blocks`` (with reason), never in ``items``.

    Returns {items, blocks, count, ids_hash, oldest_staged_at,
    oldest_staged_days}; ``ids_hash`` is the sha256 of the newline-joined
    SORTED entry_id list, so two enumerations of the same staged set match
    regardless of row order - the fingerprint a later release step must
    re-derive and compare before acting."""
    today = now_utc().date()
    enrollments = {int(e["enrollment_id"]): dict(e)
                   for e in store.enrollments_for_campaign(campaign_id)}
    recipient_pins = store.get_recipient_pins(campaign_id)
    denied = deny_domains(store)
    items: list[dict] = []
    blocks: list[dict] = []
    for a in store.attempts_for_campaign(campaign_id, statuses=("drafted",)):
        if not a["entry_id"]:
            continue  # staged without a correlated Outlook draft: not part of a wave
        e = enrollments.get(int(a["enrollment_id"]))
        to_addr = (a["to_addr"] or "").strip()
        staged_at = a["resolved_at"] or a["claimed_at"]
        staged_date = date.fromisoformat(str(staged_at)[:10]) if staged_at else None
        item = {
            "attempt_key": a["attempt_key"], "entry_id": a["entry_id"],
            "to": to_addr, "subject": a["rendered_subject"],
            "contact_id": e["contact_id"] if e else None,
            "contact_name": (f"{e.get('first_name') or ''} "
                             f"{e.get('last_name') or ''}").strip() if e else "?",
            "staged_at": staged_at,
            "staged_days": (today - staged_date).days if staged_date else None,
            "step_no": int(a["step_no"]),
        }
        if e is None:
            blocks.append({**item, "kind": "orphan_attempt",
                           "detail": "no enrollment/contact row for this attempt"})
            continue
        pinned_to = recipient_pins.get(e["contact_id"])
        if pinned_to is None:
            blocks.append({**item, "kind": "recipient_not_approved",
                           "detail": f"{to_addr}: no approval-frozen address; re-approve"})
            continue
        if to_addr.lower() != pinned_to:
            blocks.append({**item, "kind": "recipient_drift",
                           "detail": f"approved {pinned_to!r}, now {to_addr.lower()!r}; re-approve"})
            continue
        if _recipient_domain(to_addr) in denied:
            blocks.append({**item, "kind": "domain_denied",
                           "detail": f"{to_addr}: hard-denied recipient domain"})
            continue
        if e.get("suppressed"):
            blocks.append({**item, "kind": "suppressed",
                           "detail": f"{to_addr}: contact suppressed after staging"})
            continue
        items.append(item)
    ids = sorted(i["entry_id"] for i in items)
    staged = [i["staged_at"] for i in items if i["staged_at"]]
    ages = [i["staged_days"] for i in items if i["staged_days"] is not None]
    return {
        "items": items, "blocks": blocks, "count": len(items),
        "ids_hash": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        "oldest_staged_at": min(staged) if staged else None,
        "oldest_staged_days": max(ages) if ages else None,
    }


def mark_manual_done(store: ContactStore, enrollment_id: int, step_no: int,
                     user: str | None) -> dict:
    """A human executed a LinkedIn (manual) step. Same idempotent ext_key
    convention as auto sends, so the pointer advances exactly once."""
    now = _iso(now_utc())
    enrollment = store.get_enrollment(enrollment_id)
    if enrollment is None:
        return {"ok": False, "error": "unknown enrollment"}
    campaign_id = enrollment["campaign_id"]
    seq = None
    for s in store.sequences_for_campaign(campaign_id):
        if s["degree"] == (enrollment["degree"] or ""):
            seq = s
            break
    step = None
    if seq:
        step = next((st for st in seq["steps"] if st["step_no"] == step_no), None)
    if step is None:
        return {"ok": False, "error": "unknown step"}
    akey = attempt_key_for(enrollment_id, step_no)
    inserted = store.add_event(
        contact_id=enrollment["contact_id"], ts=now, channel=step["channel"],
        direction="outbound", type="sent",
        subject=f"manual step {step_no} done",
        detail=f"cadence step {step_no} ({step['template_key']}) marked done",
        source="manual", created_by=user, ext_key=akey,
        campaign=campaign_id, now=now,
    )
    if store.get_attempt(akey) is None:
        store.try_lease(
            attempt_key=akey, enrollment_id=enrollment_id, step_no=step_no,
            send_mode="manual", lease_id="manual", lease_expires=now,
            worker_id=user or "manual", to_addr=None, rendered_subject=None,
            rendered_body="", template_key=step["template_key"],
            template_version=0, now=now,
        )
    store.update_attempt(akey, {"status": "sent", "resolved_at": now})
    return {"ok": True, "event_inserted": inserted}


# -- projected schedule -----------------------------------------------------------

def project_schedule(store: ContactStore, campaign_id: str,
                     at: datetime | None = None, horizon_days: int = 120) -> list[dict]:
    """A day-by-day forward projection of when this campaign's sends land, for
    the confirm-page preview. Simulates the day-level pacing (send window,
    daily_cap, per-day ramp) over the active cohort from each enrollment's
    start. An ESTIMATE: it does not model the cross-campaign mailbox cap,
    reply/bounce drop-off, or intra-day throttle. Returns
    [{"date": "YYYY-MM-DD", "count": N}, ...] for days that carry sends."""
    at = at or now_utc()
    campaign_row = store.get_campaign(campaign_id)
    if campaign_row is None:
        return []
    campaign = dict(campaign_row)
    window = parse_window(campaign.get("send_window"))
    daily_cap = int(campaign["daily_cap"])
    ramp = int(campaign.get("ramp_per_day") or 0)
    sequences = {s["degree"]: s for s in store.sequences_for_campaign(campaign_id)}
    start_floor = _campaign_today(campaign, at)
    snb = campaign.get("start_not_before")
    if snb:
        snb_date = date.fromisoformat(str(snb)[:10])
        start_floor = max(start_floor, snb_date)

    workers: list[dict] = []
    for row in store.enrollments_for_campaign(campaign_id):
        e = dict(row)
        if e.get("suppressed") or e.get("cadence_replied") or e.get("cadence_bounced"):
            continue
        seq = sequences.get(e.get("degree") or "")
        steps = [s for s in (seq["steps"] if seq else []) if s["channel"] == "email"]
        sent = parse_sent_steps(
            {"sent_steps": e.get("sent_steps"), "steps_done": e.get("steps_done")})
        remaining = [s for s in steps if int(s["step_no"]) not in sent]
        if not remaining:
            continue
        fresh = not any(int(s["step_no"]) in sent for s in steps)  # no email step sent yet
        last = e.get("last_step_ts")
        if last:
            anchor = date.fromisoformat(str(last)[:10])
        else:
            appr = e.get("enrollment_approved_at")
            anchor = date.fromisoformat(str(appr)[:10]) if appr else start_floor
            anchor = max(anchor, start_floor)
        workers.append({
            "steps": remaining, "idx": 0,
            "next_due": anchor + timedelta(days=int(remaining[0]["day_offset"])),
            "fresh": fresh,
        })
    if not workers:
        return []

    counts: dict[str, int] = {}
    day = start_floor
    pending = len(workers)
    guard = 0
    while pending > 0 and guard < horizon_days:
        guard += 1
        if day.weekday() in window["days"]:
            cap = daily_cap
            ramp_today = ramp if ramp > 0 else None
            for w in workers:
                if cap <= 0:
                    break
                if w["idx"] >= len(w["steps"]) or w["next_due"] > day:
                    continue
                is_first = w["fresh"] and w["idx"] == 0
                if is_first and ramp_today is not None and ramp_today <= 0:
                    continue
                counts[day.isoformat()] = counts.get(day.isoformat(), 0) + 1
                cap -= 1
                if is_first and ramp_today is not None:
                    ramp_today -= 1
                w["idx"] += 1
                if w["idx"] >= len(w["steps"]):
                    pending -= 1
                else:
                    w["next_due"] = day + timedelta(days=int(w["steps"][w["idx"]]["day_offset"]))
        day = day + timedelta(days=1)
    return [{"date": d, "count": counts[d]} for d in sorted(counts)]


# -- approval ---------------------------------------------------------------------

def approval_report(store: ContactStore, campaign_id: str) -> dict:
    """Everything the approval screen shows + the blocking validation list."""
    campaign_row = store.get_campaign(campaign_id)
    if campaign_row is None:
        return {"ok": False, "errors": ["unknown campaign"]}
    campaign = dict(campaign_row)
    enrollments = [dict(r) for r in store.enrollments_for_campaign(campaign_id)]
    sequences = {s["degree"]: s for s in store.sequences_for_campaign(campaign_id)}
    errors: list[str] = []
    warnings: list[str] = []

    active = [e for e in enrollments if not e.get("suppressed")]
    if not enrollments:
        errors.append("no contacts enrolled")
    unclassified = [e for e in active if not e.get("degree")]
    if unclassified:
        errors.append(f"{len(unclassified)} active enrollment(s) have no degree")

    degrees_in_use = sorted({e["degree"] for e in active if e.get("degree")})
    samples: dict[str, dict] = {}
    for degree in degrees_in_use:
        seq = sequences.get(degree)
        if seq is None or not seq["steps"]:
            errors.append(f"degree '{degree}' has no sequence/steps")
            continue
        cohort = [e for e in active if e.get("degree") == degree]
        rendered_steps = []
        for step in seq["steps"]:
            tpl = store.get_template(step["template_key"])
            if tpl is None:
                errors.append(f"step {step['step_no']} of '{degree}': "
                              f"template '{step['template_key']}' does not exist")
                continue
            if tpl["channel"] != step["channel"]:
                errors.append(f"step {step['step_no']} of '{degree}': template "
                              f"'{step['template_key']}' is {tpl['channel']}, "
                              f"step is {step['channel']}")
            bad: dict[str, list[str]] = {}
            for e in cohort:
                if step["channel"] == "email" and not (e.get("email") or "").strip():
                    bad.setdefault("(no email address)", []).append(
                        f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip())
                    continue
                miss = missing_vars((tpl["subject"] or "") + " " + tpl["body"], e)
                if miss:
                    bad.setdefault(", ".join(miss), []).append(
                        f"{e.get('first_name') or ''} {e.get('last_name') or ''}".strip())
            for what, who in bad.items():
                errors.append(
                    f"'{step['template_key']}' cannot render for {len(who)} "
                    f"contact(s) of '{degree}': missing {what} "
                    f"(e.g. {', '.join(who[:3])})")
            sample = cohort[0] if cohort else None
            rendered_steps.append({
                "step": dict(step), "template_version": tpl["version"],
                "subject": render(tpl["subject"] or "", sample) if sample else tpl["subject"],
                "body": render(tpl["body"], sample) if sample else tpl["body"],
            })
        samples[degree] = {
            "sequence": {k: seq[k] for k in ("name", "send_mode")},
            "cohort_size": len(cohort), "steps": rendered_steps,
        }

    suppressed = [e for e in enrollments if e.get("suppressed")]
    if suppressed:
        warnings.append(f"{len(suppressed)} enrolled contact(s) are suppressed "
                        "and will never receive a send")
    total_emails = sum(
        samples[d]["cohort_size"] * sum(1 for s in sequences[d]["steps"] if s["channel"] == "email")
        for d in degrees_in_use if d in sequences and d in samples
    )
    window = parse_window(campaign.get("send_window"))
    degree_summary = ", ".join(
        f"{samples[d]['cohort_size']} {d}" for d in degrees_in_use if d in samples)
    snb = campaign.get("start_not_before")
    schedule_text = f" Starts no earlier than {str(snb)[:10]}." if snb else ""
    ramp = campaign.get("ramp_per_day")
    if ramp:
        schedule_text += f" Ramp: up to {int(ramp)} new contacts/day."
    scope_text = (
        f"Approving sends up to {total_emails} emails to {len(active)} contacts "
        f"({degree_summary}), "
        f"from {campaign['from_address']} (CC {campaign['cc_address']}, "
        f"BCC Zoho CRM dropbox), {window['start']}-{window['end']} "
        f"{window['tz']} weekdays, max {campaign['daily_cap']}/day.{schedule_text} "
        "Warm-degree steps are staged as drafts in Dirk's mailbox instead of "
        "auto-sending. Follow-ups stop on reply, bounce, or suppression. "
        "NOTE: until inbound capture runs, replies are detected by the local "
        "worker's inbox poll; if the worker is off, log replies by hand or "
        "sends will continue."
    )
    return {
        "ok": not errors, "errors": errors, "warnings": warnings,
        "campaign": campaign, "enrollments": enrollments,
        "degrees": degrees_in_use, "samples": samples,
        "total_emails": total_emails, "active_count": len(active),
        "scope_text": scope_text,
        "projected_schedule": project_schedule(store, campaign_id),
    }


def approve_campaign(store: ContactStore, campaign_id: str, user: str,
                     confirm_slug: str, now: str | None = None) -> dict:
    """THE gate. Validates, freezes template pins + the list hash, stamps the
    campaign approved and every pending enrollment. Nothing sends before this.

    ``now`` (ISO) is injectable so tests can pin approved_at; production leaves
    it None and uses the wall clock."""
    if confirm_slug.strip() != campaign_id:
        return {"ok": False, "errors": ["type the campaign id to confirm"]}
    report = approval_report(store, campaign_id)
    # Lifecycle guard: a 'done' campaign (e.g. the historical Rome roster) must
    # not be re-approvable by data-validation side effects alone; reopening is a
    # deliberate transition. Only draft / paused / (incremental) approved-sending
    # proceed.
    if (report.get("campaign") or {}).get("status") == "done":
        return {"ok": False, "errors": [
            "This campaign is marked done. Reopen it before approving."]}
    if not report["ok"]:
        return report
    now = now or _iso(now_utc())
    # Fresh approval (draft/paused) pins the latest version of every template.
    # An INCREMENTAL approval (campaign already approved; approving late-added
    # enrollments) PRESERVES existing pins - otherwise a template edited since
    # the original approval would silently upgrade the copy for the whole
    # cohort. New copy only applies through pause -> re-approve.
    existing = store.get_pins(campaign_id) \
        if (report["campaign"].get("status") in ("approved", "sending")) else {}
    pins: dict[str, int] = {}
    for degree in report["degrees"]:
        for rs in report["samples"][degree]["steps"]:
            key = rs["step"]["template_key"]
            pins[key] = existing.get(key, int(rs["template_version"]))
    store.pin_templates(campaign_id, pins)
    # Freeze each approved contact's EXACT recipient address. The claim path
    # refuses to send to an address that drifted from this snapshot, closing
    # the hole where a post-approval sheet-sync overwrites an email and the
    # frozen copy would go to an address no human reviewed.
    recipient_pins = {
        e["contact_id"]: (e.get("email") or "").strip().lower()
        for e in report["enrollments"] if (e.get("email") or "").strip()
    }
    store.pin_recipients(campaign_id, recipient_pins)
    ids = sorted(e["contact_id"] for e in report["enrollments"])
    contacts_hash = hashlib.sha1("|".join(ids).encode("utf-8")).hexdigest()
    store.update_campaign(campaign_id, {
        "status": "approved", "approved_at": now, "approved_by": user,
        "approved_contacts_hash": contacts_hash,
    }, now)
    approved_n = store.approve_pending_enrollments(campaign_id, user, now)
    store.set_state(f"approval:{campaign_id}", json.dumps({
        "approved_at": now, "approved_by": user, "pins": pins,
        "contacts_hash": contacts_hash, "enrolled": len(ids),
    }), now)
    return {"ok": True, "approved_enrollments": approved_n, "pins": pins}


def start_sending(store: ContactStore, campaign_id: str, user: str,
                  confirm_slug: str, now: str | None = None) -> dict:
    """THE SECOND GATE. Approval froze the copy + list; this is the explicit
    in-app confirm that actually turns sending ON (status approved -> sending).
    The worker only ever claims from a 'sending' campaign, so nothing leaves
    until a human presses this and re-types the campaign id.

    ``now`` (ISO) is injectable for tests; production leaves it None."""
    if confirm_slug.strip() != campaign_id:
        return {"ok": False, "errors": ["type the campaign id to confirm"]}
    campaign = store.get_campaign(campaign_id)
    if campaign is None:
        return {"ok": False, "errors": ["unknown campaign"]}
    if campaign["status"] != "approved":
        return {"ok": False, "errors": [
            f"campaign is '{campaign['status']}'; it must be 'approved' "
            "(copy + list frozen) before sending can start"]}
    now = now or _iso(now_utc())
    store.update_campaign(campaign_id, {"status": "sending"}, now)
    store.set_state(f"sending-started:{campaign_id}",
                    json.dumps({"at": now, "by": user}), now)
    return {"ok": True}


def supersede_approval(store: ContactStore, campaign_id: str, reason: str) -> None:
    """Copy or sequence changed after approval: the frozen scope no longer
    matches reality, so the campaign drops back to draft until re-approved
    (and re-confirmed for sending). Catches both the 'approved' holding state
    and a live 'sending' campaign."""
    campaign = store.get_campaign(campaign_id)
    if campaign is None or campaign["status"] not in ("approved", "sending"):
        return
    now = _iso(now_utc())
    store.update_campaign(campaign_id, {"status": "draft"}, now)
    store.set_state(f"approval-superseded:{campaign_id}",
                    json.dumps({"at": now, "reason": reason}), now)


# -- live sequence editing (delta approval) ----------------------------------------

def _steps_equal(a: dict, b: dict) -> bool:
    return (a["channel"] == b["channel"]
            and a["template_key"] == b["template_key"]
            and int(a["day_offset"]) == int(b["day_offset"]))


def sequence_delta_report(store: ContactStore, campaign_id: str, degree: str,
                          submitted_steps: list[dict]) -> dict:
    """Plan a live sequence edit that keeps the campaign 'sending' (no demote to
    draft, no full re-approval).

    ``submitted_steps`` is the desired ordered sequence
    ([{channel, template_key, day_offset}], no step_no - assigned here). The
    edit is admissible ONLY in the FUTURE (unsent) region: every step already
    sent to any enrollment (a frozen step_no, see ``store.frozen_step_nos``)
    must stay byte-identical and in place, as the leading prefix. Future steps
    are (re)assigned fresh step_nos ABOVE every attempted step_no, so a new or
    moved step never collides with a spoken-for send ext_key (which is what
    part-1's step_no-keyed pointer then reads correctly).

    Returns {ok, frozen_count, new_steps, added, pins, added_pins, name,
    send_mode, degree, campaign} on success, or {ok: False, errors} when the
    edit would touch sent history (route the operator to pause -> edit ->
    re-approve instead)."""
    campaign = store.get_campaign(campaign_id)
    if campaign is None:
        return {"ok": False, "errors": ["unknown campaign"]}
    if campaign["status"] not in ("approved", "sending", "paused"):
        return {"ok": False, "errors": [
            f"campaign is '{campaign['status']}'; a live sequence delta needs an "
            "approved / sending / paused campaign (edit a draft sequence directly)"]}
    seq = store.get_sequence(campaign_id, degree)
    current = seq["steps"] if seq else []  # ORDER BY step_no
    frozen_set = store.frozen_step_nos(campaign_id, degree)
    # Frozen steps must be a contiguous LEADING run of the current sequence
    # (sends advance in step_no order). A gap - e.g. a still-pending LinkedIn
    # step wedged before a later sent one - is outside the delta's safe
    # envelope, so refuse and route to the heavier pause -> re-approve path.
    frozen_prefix: list[dict] = []
    for s in current:
        if int(s["step_no"]) in frozen_set:
            frozen_prefix.append(s)
        else:
            break
    if {int(s["step_no"]) for s in frozen_prefix} != frozen_set:
        return {"ok": False, "errors": [
            "already-sent steps are not a contiguous prefix (a mid-sequence step "
            "is still pending); pause the campaign to edit this sequence"]}
    k = len(frozen_prefix)
    if len(submitted_steps) < k:
        return {"ok": False, "errors": [
            f"the first {k} step(s) have already been sent and cannot be removed; "
            "keep them and add or change only later steps (or pause to re-approve)"]}
    for i in range(k):
        if not _steps_equal(submitted_steps[i], frozen_prefix[i]):
            return {"ok": False, "errors": [
                f"step {i + 1} has already been sent and cannot be changed; keep "
                "it as-is and edit only later steps (or pause to re-approve)"]}

    frozen_max = max(frozen_set) if frozen_set else 0
    new_steps: list[dict] = [dict(s) for s in frozen_prefix]
    for i, s in enumerate(submitted_steps[k:]):
        new_steps.append({"step_no": frozen_max + 1 + i, "channel": s["channel"],
                          "template_key": s["template_key"],
                          "day_offset": int(s["day_offset"]),
                          "reply_to_prior": int(s.get("reply_to_prior") or 0)})
    future = new_steps[k:]

    # Validate every future template exists and channel matches (mirror approval).
    errors: list[str] = []
    for st in future:
        tpl = store.get_template(st["template_key"])
        if tpl is None:
            errors.append(f"template '{st['template_key']}' does not exist")
        elif tpl["channel"] != st["channel"]:
            errors.append(f"template '{st['template_key']}' is {tpl['channel']}, "
                          f"step is {st['channel']}")
        if int(st["step_no"]) == 1 and st.get("reply_to_prior"):
            errors.append("step 1 cannot be a reply: no prior step to reply to")
    if errors:
        return {"ok": False, "errors": errors}

    # Re-pin: KEEP every existing campaign pin (other degrees + frozen steps);
    # pin the latest version for each template_key a FUTURE step uses, so a saved
    # new version applies to unsent steps and no future step is left unpinned
    # (the increment-1 unpinned-template guard). A key shared with a frozen step
    # keeps its frozen pinned version (that copy already went out).
    existing = store.get_pins(campaign_id)
    frozen_keys = {s["template_key"] for s in frozen_prefix}
    pins = dict(existing)
    added_pins: dict[str, int] = {}
    for st in future:
        key = st["template_key"]
        latest = int(store.get_template(key)["version"])
        if key in frozen_keys:
            pins.setdefault(key, latest)
        else:
            if pins.get(key) != latest:
                added_pins[key] = latest
            pins[key] = latest
    return {"ok": True, "frozen_count": k, "new_steps": new_steps, "added": future,
            "pins": pins, "added_pins": added_pins,
            "name": (seq["name"] if seq else degree),
            "send_mode": (seq["send_mode"] if seq else "auto-matthias"),
            "degree": degree, "campaign": dict(campaign)}


def apply_sequence_delta(store: ContactStore, campaign_id: str, degree: str,
                         submitted_steps: list[dict], user: str | None,
                         now: str | None = None) -> dict:
    """Apply a validated sequence delta WITHOUT demoting the campaign to draft.
    Sent steps are preserved (same step_no); future steps are (re)written with
    fresh step_nos; only changed/new template keys are re-pinned. The campaign
    KEEPS its status, so a 'sending' wave never stops. Send-safety is intact:
    recipient pins + contacts hash are untouched, and every step stays pinned."""
    report = sequence_delta_report(store, campaign_id, degree, submitted_steps)
    if not report["ok"]:
        return report
    now = now or _iso(now_utc())
    store.upsert_sequence(campaign_id, degree, report["name"],
                          report["send_mode"], report["new_steps"])
    store.pin_templates(campaign_id, report["pins"])
    # Keep the recorded approval pins in sync so the audit record matches what
    # will render; do NOT touch campaign status (no supersede).
    marker = store.get_state(f"approval:{campaign_id}")
    if marker:
        try:
            data = json.loads(marker)
            data["pins"] = report["pins"]
            store.set_state(f"approval:{campaign_id}", json.dumps(data), now)
        except (json.JSONDecodeError, TypeError):
            pass
    store.set_state(f"sequence-delta:{campaign_id}:{degree}", json.dumps({
        "at": now, "by": user, "frozen_count": report["frozen_count"],
        "added": [s["template_key"] for s in report["added"]],
        "pins_changed": report["added_pins"],
    }), now)
    return {"ok": True, "frozen_count": report["frozen_count"],
            "added": report["added"], "pins": report["pins"],
            "added_pins": report["added_pins"]}


# -- reconcile -----------------------------------------------------------------------

def reconcile(store: ContactStore) -> dict:
    """Repair drift between the lock table and the event log; expire leases.
    Keeps the step pointer re-derivable from events alone."""
    now = _iso(now_utc())
    stalled = store.expire_leases(now)
    repaired_events = repaired_attempts = 0
    # 1. Attempts recorded 'sent' whose event never landed (lost result write).
    rows = store.conn.execute(
        "SELECT sa.*, en.contact_id AS e_contact, en.campaign_id AS e_campaign "
        "FROM send_attempts sa JOIN enrollments en ON en.enrollment_id = sa.enrollment_id "
        "WHERE sa.status = 'sent'"
    ).fetchall()
    for sa in rows:
        exists = store.conn.execute(
            "SELECT 1 FROM outreach_events WHERE ext_key = ? AND type = 'sent' LIMIT 1",
            (sa["attempt_key"],),
        ).fetchone()
        if not exists:
            if store.add_event(
                contact_id=sa["e_contact"], ts=sa["resolved_at"] or now,
                channel="email", direction="outbound", type="sent",
                subject=sa["rendered_subject"],
                detail=f"cadence step {sa['step_no']} (reconciled)",
                source="worker-auto", created_by=sa["worker_id"],
                ext_key=sa["attempt_key"], campaign=sa["e_campaign"], now=now,
            ):
                repaired_events += 1
    # 2. Cadence events whose attempt row is missing or not marked sent.
    evs = store.conn.execute(
        "SELECT ext_key, ts FROM outreach_events "
        "WHERE type = 'sent' AND ext_key LIKE ?",
        (CADENCE_PREFIX + "%",),
    ).fetchall()
    for ev in evs:
        akey = ev["ext_key"]
        attempt = store.get_attempt(akey)
        if attempt is None:
            try:
                _, eid, step_no = akey.split(":")
                store.try_lease(
                    attempt_key=akey, enrollment_id=int(eid), step_no=int(step_no),
                    send_mode="unknown", lease_id="reconcile", lease_expires=now,
                    worker_id="reconcile", to_addr=None, rendered_subject=None,
                    rendered_body="", template_key="unknown", template_version=0,
                    now=now,
                )
                store.update_attempt(akey, {"status": "sent", "resolved_at": ev["ts"]})
                repaired_attempts += 1
            except (ValueError, TypeError):
                continue
        elif attempt["status"] not in ("sent",):
            store.update_attempt(akey, {"status": "sent", "resolved_at": ev["ts"]})
            repaired_attempts += 1
    return {"stalled": stalled, "repaired_events": repaired_events,
            "repaired_attempts": repaired_attempts}
