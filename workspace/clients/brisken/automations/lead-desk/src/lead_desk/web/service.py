"""Business logic for the Lead Desk: stage/status derivation and the board.

Framework-free on purpose (routes pass plain dicts/values), so it is unit
testable without HTTP, mirroring the expense-recon service layer. The store is
the only I/O dependency.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from .store import STAGES, ContactStore

# A reply we have not answered in this many days is an "aging hot reply".
AGING_DAYS = 3

STAGE_LABELS = {
    "sourced": "Not contacted",
    "sent": "Contacted",
    "replied": "Replied",
    "qualifying": "Qualifying",
    "booked": "Demo booked",
    "held": "Demo held",
    "accepted": "Accepted",
}

SUPPRESS_REASONS = (
    "do_not_contact", "no_consent", "stop", "duplicate", "test",
    "organiser", "own_team", "unreachable", "bounced", "anon",
)

# Controlled vocab for the tier field (free text still accepted via datalist).
TIER_VOCAB = (
    "H5", "T1", "T2", "T3", "GA", "STOP", "ANON",
    "OWN_TEAM", "DUPLICATE", "TEST", "ORGANISER", "UNREACHABLE",
)

# Every field Dirk may edit from the contact page, grouped for the template.
EDITABLE_TEXT = (
    # identity
    "first_name", "last_name", "company", "job_title",
    "email", "alt_email", "phone", "country", "linkedin_url",
    # classification
    "tier", "tier_reason", "lead_type", "persona", "signal",
    "crm_owner", "brisken_customer", "if_we_know_them",
    # provenance (text)
    "attendee_type", "booth_registered_at", "source", "crm_last_activity",
    # qualification / next step
    "demo_date", "dirk_verdict", "demo_owner",
    "next_step", "next_step_due", "notes", "dirk_notes",
)
EDITABLE_FLAGS = (
    "bant_need", "bant_authority", "bant_timeline", "bant_budget",
    "in_our_booth", "scanned_at_booth", "fob_encoded",
    "no_show", "sponsor_opt_in",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _d(value: str | None) -> date | None:
    """Parse the leading YYYY-MM-DD of a timestamp/date string."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _row(r) -> dict:
    return dict(r) if r is not None else {}


def status_label(row: dict) -> str:
    """The human status shown on the board: suppression + wait-state on stage."""
    if row.get("suppressed"):
        reason = row.get("suppress_reason") or "suppressed"
        return f"Suppressed ({reason})"
    stage = row.get("stage", "sourced")
    last_in = _d(row.get("last_in"))
    last_out = _d(row.get("last_out"))
    if stage == "sent":
        if last_in is None or (last_out and last_in < last_out):
            return "Awaiting reply"
        return "Contacted"
    if stage == "replied":
        if last_in and (last_out is None or last_in >= last_out):
            return "Replied, needs reply"
        return "Replied"
    return STAGE_LABELS.get(stage, stage)


def is_awaiting_reply(row: dict) -> bool:
    if row.get("suppressed") or row.get("stage") != "sent":
        return False
    last_in, last_out = _d(row.get("last_in")), _d(row.get("last_out"))
    return last_in is None or (last_out is not None and last_in < last_out)


def is_dangling(row: dict, today: date) -> bool:
    if row.get("suppressed"):
        return False
    if row.get("stage") not in ("sent", "replied", "qualifying"):
        return False
    due = _d(row.get("next_step_due"))
    return due is not None and due < today


def is_aging_hot(row: dict, today: date) -> bool:
    if row.get("suppressed") or row.get("stage") not in ("replied", "qualifying"):
        return False
    last_in, last_out = _d(row.get("last_in")), _d(row.get("last_out"))
    if last_in is None:
        return False
    unanswered = last_out is None or last_in >= last_out
    return unanswered and (today - last_in).days >= AGING_DAYS


def build_board(store: ContactStore, filters: dict | None = None,
                campaign: str = "rome-2026") -> dict:
    filters = filters or {}
    today = datetime.now(timezone.utc).date()
    rows = [_row(r) for r in store.board_rows(campaign)]
    for r in rows:
        r["status"] = status_label(r)
        r["awaiting"] = is_awaiting_reply(r)
        r["dangling"] = is_dangling(r, today)
        r["aging"] = is_aging_hot(r, today)

    active = [r for r in rows if not r.get("suppressed")]
    stage_counts = {s: 0 for s in STAGES}
    for r in active:
        stage_counts[r.get("stage", "sourced")] = stage_counts.get(r.get("stage", "sourced"), 0) + 1

    buckets = {
        "awaiting_reply": sum(1 for r in active if r["awaiting"]),
        "dangling": sum(1 for r in active if r["dangling"]),
        "aging_hot": sum(1 for r in active if r["aging"]),
    }

    tiers = sorted({r.get("tier") for r in rows if r.get("tier")})
    owners = sorted({r.get("crm_owner") for r in rows if r.get("crm_owner")})

    # Apply filters.
    ftier = (filters.get("tier") or "").strip()
    fstage = (filters.get("stage") or "").strip()
    fowner = (filters.get("owner") or "").strip()
    fbucket = (filters.get("bucket") or "").strip()
    q = (filters.get("q") or "").strip().lower()
    show_suppressed = str(filters.get("show_suppressed") or "").strip() in ("1", "true", "on")

    shown = rows if show_suppressed else active
    if ftier:
        shown = [r for r in shown if r.get("tier") == ftier]
    if fstage:
        shown = [r for r in shown if r.get("stage") == fstage]
    if fowner:
        shown = [r for r in shown if r.get("crm_owner") == fowner]
    if fbucket == "awaiting":
        shown = [r for r in shown if r["awaiting"]]
    elif fbucket == "dangling":
        shown = [r for r in shown if r["dangling"]]
    elif fbucket == "aging":
        shown = [r for r in shown if r["aging"]]
    if q:
        def hit(r):
            hay = " ".join(str(r.get(k) or "") for k in
                           ("first_name", "last_name", "company", "email", "job_title"))
            return q in hay.lower()
        shown = [r for r in shown if hit(r)]

    return {
        "campaign": campaign,
        "stage_counts": stage_counts,
        "stages": list(STAGES),
        "total_active": len(active),
        "total_suppressed": len(rows) - len(active),
        "buckets": buckets,
        "tiers": tiers,
        "owners": owners,
        "rows": shown,
        "filters": {
            "tier": ftier, "stage": fstage, "owner": fowner,
            "bucket": fbucket, "q": filters.get("q") or "",
            "show_suppressed": show_suppressed,
        },
    }


def build_contact_view(store: ContactStore, contact_id: str) -> dict | None:
    row = store.get_contact(contact_id)
    if row is None:
        return None
    contact = _row(row)
    # Attach the derived stage + activity for the header.
    board = {r["contact_id"]: r for r in (dict(x) for x in store.board_rows(contact["campaign"]))}
    enriched = board.get(contact_id, {})
    contact["stage"] = enriched.get("stage", "sourced")
    contact["last_in"] = enriched.get("last_in")
    contact["last_out"] = enriched.get("last_out")
    contact["status"] = status_label({**contact, **enriched})
    events = [_row(e) for e in store.get_events(contact_id)]
    return {
        "contact": contact,
        "events": events,
        "stage_labels": STAGE_LABELS,
        "suppress_reasons": SUPPRESS_REASONS,
        "tier_vocab": list(TIER_VOCAB),
    }


# -- mutations --------------------------------------------------------------

def log_touch(store: ContactStore, contact_id: str, *, channel: str, direction: str,
              type: str, ts: str | None, subject: str | None, detail: str | None,
              user: str | None) -> bool:
    if store.get_contact(contact_id) is None:
        raise ValueError("unknown contact")
    ts = (ts or "").strip() or now_iso()
    return store.add_event(
        contact_id=contact_id, ts=ts, channel=channel, direction=direction,
        type=type, subject=subject, detail=detail, source="manual",
        created_by=user, now=now_iso(),
    )


def toggle_suppress(store: ContactStore, contact_id: str, suppressed: bool,
                    reason: str | None, user: str | None) -> None:
    now = now_iso()
    store.set_suppressed(contact_id, suppressed, reason, user, now)
    # Audit trail: the suppression change is itself an event.
    verb = "suppressed" if suppressed else "un-suppressed"
    store.add_event(
        contact_id=contact_id, ts=now, channel="call", direction="outbound",
        type="note", subject=f"{verb}", detail=f"{verb}" + (f": {reason}" if reason else ""),
        source="manual", created_by=user, now=now,
    )


def apply_fields(store: ContactStore, contact_id: str, fields: dict,
                 user: str | None) -> None:
    """Update any editable contact field (identity, classification, provenance,
    qualification). A change writes a `note` audit event, keeping the log the
    record of every mutation. Setting demo_date / accepted verdict also emits a
    milestone event so the derived stage and the field cannot disagree."""
    current = store.get_contact(contact_id)
    if current is None:
        raise ValueError("unknown contact")
    now = now_iso()
    allowed = set(EDITABLE_TEXT) | set(EDITABLE_FLAGS)
    clean = {k: v for k, v in fields.items() if k in allowed}

    # Audit: record which fields actually change (append-only, never a silent edit).
    changed = []
    for k, v in clean.items():
        old_s = "" if current[k] is None else str(current[k])
        new_s = "" if v is None else str(v)
        if old_s != new_s:
            changed.append(k)

    store.update_fields(contact_id, clean, now)

    if changed:
        store.add_event(
            contact_id=contact_id, ts=now, channel="call", direction="outbound",
            type="note", subject="Fields updated",
            detail="edited: " + ", ".join(sorted(changed)),
            source="manual", created_by=user, now=now,
        )

    new_demo = (clean.get("demo_date") or "").strip()
    if new_demo and not (current["demo_date"] or "").strip():
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="outbound",
            type="booked", subject="Demo booked", detail=f"demo_date={new_demo}",
            source="manual", created_by=user, now=now,
        )
    if clean.get("dirk_verdict") == "accepted" and current["dirk_verdict"] != "accepted":
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="inbound",
            type="accepted", subject="Accepted", detail="Dirk verdict: accepted",
            source="manual", created_by=user, now=now,
        )


def create_contact(store: ContactStore, data: dict, user: str | None) -> tuple[str, bool]:
    """Create a new lead. Dedupes by email: if the address is already on file,
    returns the existing contact_id and (id, False); otherwise inserts and
    returns (new_id, True), logging a `contact created` audit event."""
    from uuid import uuid4

    from ..migrate import natural_key

    now = now_iso()
    email = (data.get("email") or "").strip()
    if email:
        existing = store.find_by_email(email)
        if existing is not None:
            return existing["contact_id"], False

    nk = natural_key(email or None, data.get("first_name"),
                     data.get("last_name"), data.get("company"))
    if store.get_contact_by_key(nk) is not None:
        nk = f"{nk}:{uuid4().hex[:8]}"          # avoid anon-key collision
    contact_id = uuid4().hex

    payload = {"contact_id": contact_id, "natural_key": nk,
               "campaign": "rome-2026", "source": "manual"}
    for k in EDITABLE_TEXT:
        v = (data.get(k) or "").strip()
        if v:
            payload[k] = v
    store.upsert_contact(payload, now)
    store.add_event(
        contact_id=contact_id, ts=now, channel="call", direction="outbound",
        type="note", subject="Contact created", detail="added via Lead Desk",
        source="manual", created_by=user, now=now,
    )
    return contact_id, True


def ingest_event(store: ContactStore, payload: dict) -> dict:
    """Sink for POST /events (the cloud capture worker). Resolves the contact by
    id or email, appends the event idempotently. Returns a small result dict."""
    now = now_iso()
    contact_id = (payload.get("contact_id") or "").strip()
    if not contact_id:
        addr = (payload.get("email") or "").strip()
        row = store.find_by_email(addr) if addr else None
        if row is None:
            return {"ok": False, "reason": "no matching contact",
                    "email": payload.get("email")}
        contact_id = row["contact_id"]
    elif store.get_contact(contact_id) is None:
        return {"ok": False, "reason": "unknown contact_id", "contact_id": contact_id}

    ts = (payload.get("occurred_at") or payload.get("ts") or "").strip() or now
    inserted = store.add_event(
        contact_id=contact_id,
        ts=ts,
        channel=payload.get("channel") or "email",
        direction=payload.get("direction") or "outbound",
        type=payload.get("type") or "sent",
        subject=payload.get("subject"),
        detail=payload.get("detail"),
        source=payload.get("source") or "graph-auto",
        ext_key=payload.get("ext_key") or payload.get("internet_message_id"),
        now=now,
    )
    return {"ok": True, "contact_id": contact_id, "inserted": inserted}
