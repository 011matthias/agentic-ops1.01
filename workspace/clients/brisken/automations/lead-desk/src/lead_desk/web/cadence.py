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

from .store import CADENCE_PREFIX, DEGREES, ContactStore, attempt_key_for

LEASE_MINUTES = 30
MAX_SEND_ATTEMPTS = 3

# Recipient domains that must NEVER receive a campaign send, regardless of
# approval (a competitor we hold, and our own internal domain). This is the
# immutable floor; the claim path unions it with any operator-configured extras
# in the 'send_deny_domains' state key, and the worker re-checks the floor
# before the Graph POST. Mirrors the hard @sap.com deny in the ga_send_wave.py
# guard pattern (rule_brisken_graph_send_by_id).
DEFAULT_DENY_DOMAINS = ("sap.com", "brisken.com")

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

def enrollment_state(enrollment: dict, progress: dict, steps: list[dict],
                     contact: dict, campaign: dict) -> dict:
    """Pure derivation of one enrollment's cadence state.

    Returns {state, steps_done, steps_total, next_step, next_due}. States:
    stopped:suppressed / stopped:bounced / stopped:replied / no_sequence /
    done / pending_approval / paused / inactive / active."""
    steps_done = int(progress.get("steps_done") or 0)
    total = len(steps)
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
    if steps_done >= total:
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

    next_step = steps[steps_done]  # 1-based step_no == steps_done + 1
    # Offsets anchor on the PREVIOUS step's actual completion (a delayed send
    # never compresses the follow-up gap); step 1 anchors on approval.
    anchor = (progress.get("last_step_ts")
              or enrollment.get("approved_at")
              or enrollment.get("enrollment_approved_at"))
    anchor_date = date.fromisoformat(str(anchor)[:10]) if anchor else None
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
            {"steps_done": e.get("steps_done"), "last_step_ts": e.get("last_step_ts"),
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
        cap_left = int(campaign["daily_cap"]) - store.cadence_sends_today(
            campaign["campaign_id"], today.isoformat())
        if cap_left <= 0:
            continue
        pins = store.get_pins(campaign["campaign_id"])
        recipient_pins = store.get_recipient_pins(campaign["campaign_id"])
        denied = deny_domains(store)
        blocks: list[dict] = []
        due = due_items(store, campaign["campaign_id"], at)
        for item in due["emails"]:
            if len(claims) >= max_items or cap_left <= 0:
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
            if step["template_key"] not in pins:
                blocks.append({"contact_id": cid, "kind": "unpinned_template",
                               "detail": f"step {step['step_no']} template "
                                         f"{step['template_key']!r} not pinned; re-approve"})
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
    scope_text = (
        f"Approving sends up to {total_emails} emails to {len(active)} contacts "
        f"({degree_summary}), "
        f"from {campaign['from_address']} (CC {campaign['cc_address']}, "
        f"BCC Zoho CRM dropbox), {window['start']}-{window['end']} "
        f"{window['tz']} weekdays, max {campaign['daily_cap']}/day. "
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
