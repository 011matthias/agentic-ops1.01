"""Business logic for the Lead Desk: stage/status derivation and the board.

Framework-free on purpose (routes pass plain dicts/values), so it is unit
testable without HTTP, mirroring the expense-recon service layer. The store is
the only I/O dependency.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from .store import CADENCE_PREFIX, STAGES, ContactStore

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
    "held", "do_not_contact", "no_consent", "stop", "duplicate", "test",
    "organiser", "own_team", "unreachable", "bounced", "anon",
)

# Off-board reasons split three ways so the board can show WHY, not just that a
# contact is off it: a deliberate (revisitable) hold, a consent block, or an
# exclusion tier.
CONSENT_REASONS = ("do_not_contact", "no_consent", "stop")
HELD_REASONS = ("held",)

# Every contact field the cockpit editor can write, grouped by input kind.
# apply_fields() allows exactly this union; the contact template renders TEXT as
# inputs/selects and FLAGS as checkboxes. Identity/classification/provenance stay
# sheet-authoritative on a re-sync (migrate.APP_OWNED_ON_RESYNC), but the operator
# can always override any field here from the cockpit.
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

# Tier autocomplete vocabulary for the classification editor (datalist).
TIER_VOCAB = (
    "H5", "T1", "T2", "T3", "GA", "STOP", "ANON",
    "OWN_TEAM", "DUPLICATE", "TEST", "ORGANISER", "UNREACHABLE",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _d(value: str | None) -> date | None:
    """Parse the leading YYYY-MM-DD of a timestamp/date string (age arithmetic)."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _dt(value: str | None) -> datetime | None:
    """Parse a full ISO timestamp (the answered/unanswered decision needs
    sub-day precision, unlike _d which truncates to the date). A naive value is
    normalised to UTC so a naive-vs-aware compare can never raise mid-board."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _unanswered(row: dict) -> bool:
    """True when their latest inbound is strictly newer than our latest outbound,
    at FULL timestamp precision. A reply we answered the SAME day (our ts later)
    is answered - the old date-truncated `>=` mis-flagged it as still owing a
    reply and told the operator to reply again."""
    li, lo = _dt(row.get("last_in")), _dt(row.get("last_out"))
    if li is None:
        return False
    return lo is None or li > lo


def _row(r) -> dict:
    return dict(r) if r is not None else {}


def is_reached_dirk(row: dict) -> bool:
    """A relationship touch from Dirk carried the contact to 'sent' with no
    campaign send behind it: show it as a personal reach, not a campaign send."""
    return (not row.get("suppressed") and row.get("stage") == "sent"
            and bool(row.get("has_touch")) and not row.get("has_campaign_send"))


def status_label(row: dict) -> str:
    """The human status shown on the board: suppression + wait-state on stage.
    Off-board contacts read WHY (held / do-not-contact / excluded), not a flat
    'Suppressed'."""
    if row.get("suppressed"):
        reason = row.get("suppress_reason") or "suppressed"
        if reason in HELD_REASONS:
            # "On hold" (not "Held"): disambiguate the off-board suppression
            # from the 'held' pipeline STAGE, whose label is "Demo held".
            return "On hold"
        if reason in CONSENT_REASONS:
            return f"Do not contact ({reason})"
        return f"Excluded ({reason})"
    stage = row.get("stage", "sourced")
    if stage == "sent":
        if is_reached_dirk(row):
            return "Reached (Dirk)"
        return "Contacted" if _unanswered(row) else "Awaiting their reply"
    if stage == "replied":
        return "Replied, needs reply" if _unanswered(row) else "Replied"
    return STAGE_LABELS.get(stage, stage)


def is_awaiting_reply(row: dict) -> bool:
    if row.get("suppressed") or row.get("stage") != "sent":
        return False
    return not _unanswered(row)


def is_dangling(row: dict, today: date) -> bool:
    """A follow-up the operator scheduled is now past due AND we have not sent
    anything since. Stage-agnostic: a booked/held/accepted contact with a
    past-due next step owes an action too. Clears once we send after the due
    date (last_out >= due)."""
    if row.get("suppressed"):
        return False
    due = _d(row.get("next_step_due"))
    if due is None or due >= today:
        return False
    lo = _d(row.get("last_out"))
    return lo is None or lo < due


def is_aging_hot(row: dict, today: date) -> bool:
    if row.get("suppressed") or row.get("stage") not in ("replied", "qualifying"):
        return False
    if not _unanswered(row):
        return False
    last_in = _d(row.get("last_in"))
    return last_in is not None and (today - last_in).days >= AGING_DAYS


def recommended_action(row: dict, today: date) -> dict:
    """The concrete next action for a contact the board flags as needing one.

    Powers the board's clickable 'Action needed' detail and the contact-page
    callout. Suppressed (off-board) rows never need action. Uses the operator's
    ``next_step`` verbatim when set, otherwise derives a sensible default from
    the wait-state. Returns ``{"needed": False}`` when nothing is owed on our
    side (e.g. we are simply awaiting their reply)."""
    if row.get("suppressed"):
        return {"needed": False}
    due = _d(row.get("next_step_due"))
    today_date = today
    # A next step scheduled for a FUTURE date is an explicit deferral (classic
    # OOO "nudge after they return") - do not nag for a reply meanwhile.
    deferred = due is not None and due > today_date
    # An unanswered inbound at 'replied' OR 'qualifying' owes a reply NOW (not
    # only after AGING_DAYS): a more-qualified lead should not wait longer than
    # a just-replied one.
    replied = (not deferred) and row.get("stage") in ("replied", "qualifying") \
        and _unanswered(row)
    dangling = is_dangling(row, today)
    if not (replied or dangling):
        return {"needed": False}
    last_in = (row.get("last_in") or "")[:10]
    next_step = (row.get("next_step") or "").strip()
    if replied:
        reason = (f"They replied on {last_in} and we have not responded yet."
                  if last_in else "They replied and we have not responded yet.")
        default = "Reply to their latest message."
    else:
        due = (row.get("next_step_due") or "")[:10]
        reason = (f"The planned follow-up was due on {due}." if due
                  else "A planned follow-up is past due.")
        default = "Send the planned follow-up."
    return {
        "needed": True,
        "kind": "reply" if replied else "followup",
        "status": status_label(row),
        "action": next_step or default,
        "from_next_step": bool(next_step),
        "reason": reason,
        "last_in": last_in,
        "last_out": (row.get("last_out") or "")[:10],
    }


def _attach_cadence(store: ContactStore, rows: list[dict], campaign_row) -> None:
    """Per-row cadence state (degree, step x/y, next touch) for enrolled rows."""
    from . import cadence  # local import: cadence imports store, not service

    cdict = dict(campaign_row)
    sequences = {s["degree"]: s for s in store.sequences_for_campaign(cdict["campaign_id"])}
    today = cadence._campaign_today(cdict, cadence.now_utc()).isoformat()
    for r in rows:
        seq = sequences.get(r.get("degree") or "")
        steps = seq["steps"] if seq else []
        st = cadence.enrollment_state(
            {"approved_at": r.get("enrollment_approved_at")},
            {"steps_done": r.get("steps_done"), "last_step_ts": r.get("last_step_ts"),
             "replied": r.get("cadence_replied"), "bounced": r.get("cadence_bounced")},
            steps, r, cdict,
        )
        r["cadence"] = st
        due = bool(st["next_due"]) and st["next_due"] <= today and st["state"] == "active"
        ch = (st["next_step"] or {}).get("channel")
        r["due_today"] = due and ch == "email"
        r["manual_due"] = due and ch == "linkedin"


def outreach_phases(events: list[dict]) -> dict:
    """Split outreach into its two distinct phases so during-event (E1/E2/E3,
    mailbox-grounded) and post-event (sheet booth follow-up) never conflate.
    Reads the phase-labelled event subjects written by ground.py / migrate.py."""
    waves: dict[str, str] = {}
    replied: str | None = None
    post_sent: str | None = None
    post_detail: str | None = None
    for e in events:
        subj = (e.get("subject") or "").strip()
        d = (e.get("ts") or "")[:10]
        if subj == "During-event reply":
            if replied is None or d < replied:
                replied = d
        elif subj.startswith("During-event "):
            wave = subj[len("During-event "):].strip()
            waves.setdefault(wave, d)
        elif subj == "Post-event follow-up":
            if post_sent is None or (d and d > post_sent):
                post_sent = d
                post_detail = e.get("detail")
    return {
        "during_event": {
            "waves": sorted(waves),
            "last": max(waves.values()) if waves else None,
            "replied": replied,
            "any": bool(waves),
        },
        "post_event": {"sent": post_sent, "detail": post_detail, "any": bool(post_sent)},
    }


def build_board(store: ContactStore, filters: dict | None = None,
                campaign: str = "rome-2026") -> dict:
    filters = filters or {}
    today = datetime.now(timezone.utc).date()

    campaigns = [dict(c) for c in store.list_campaigns()]
    campaign_row = store.get_campaign(campaign)
    enrolled = store.enrollments_for_campaign(campaign) if campaign_row else []

    # The board must show EVERY campaign contact, not only the enrolled subset:
    # a synced lead that was never enrolled (a hot T1 replier included) must
    # never vanish, and stage/bucket/total counts must be over the full roster.
    # board_rows() is that full set; enrolled rows carry the cadence overlay.
    board = [dict(x) for x in store.board_rows(campaign)]

    rows: list[dict] = []
    enrolled_ids: set[str] = set()
    if enrolled:
        rows = [_row(r) for r in enrolled]
        board_by_id = {r["contact_id"]: r for r in board}
        for r in rows:
            enrolled_ids.add(r["contact_id"])
            # Enrolled rows come without the touch-derivation flags; backfill them.
            f = board_by_id.get(r["contact_id"], {})
            r["has_touch"] = f.get("has_touch", 0)
            r["has_campaign_send"] = f.get("has_campaign_send", 0)
            r["event_count"] = f.get("event_count", 0)
        _attach_cadence(store, rows, campaign_row)
    # UNION the un-enrolled campaign contacts (defense-in-depth if enroll-on-sync
    # missed one, and the pre-adopt legacy state). No cadence overlay for these;
    # the templates already render a null cadence (the old legacy branch proved it).
    for r in board:
        if r["contact_id"] in enrolled_ids:
            continue
        r["cadence"] = None
        r["due_today"] = r["manual_due"] = False
        rows.append(r)
    rows.sort(key=lambda r: ((r.get("company") or "").lower(),
                             (r.get("last_name") or "").lower()))

    for r in rows:
        r["status"] = status_label(r)
        r["awaiting"] = is_awaiting_reply(r)
        r["dangling"] = is_dangling(r, today)
        r["aging"] = is_aging_hot(r, today)
        r["reached"] = is_reached_dirk(r)
        r["held"] = bool(r.get("suppressed")) and r.get("suppress_reason") in HELD_REASONS
        r["recommended"] = recommended_action(r, today)

    # Outreach-phase summary per contact: during-event (E1/E2/E3) vs post-event,
    # kept distinct. One query over the phase-labelled events, grouped in Python.
    phase_by_contact: dict[str, list[dict]] = {}
    for pr in store.conn.execute(
        "SELECT contact_id, subject, ts, detail FROM outreach_events "
        "WHERE campaign = ? AND (subject LIKE 'During-event%' "
        "OR subject = 'Post-event follow-up')", (campaign,),
    ).fetchall():
        phase_by_contact.setdefault(pr["contact_id"], []).append(dict(pr))
    for r in rows:
        r["phases"] = outreach_phases(phase_by_contact.get(r["contact_id"], []))

    active = [r for r in rows if not r.get("suppressed")]
    stage_counts = {s: 0 for s in STAGES}
    for r in active:
        stage_counts[r.get("stage", "sourced")] = stage_counts.get(r.get("stage", "sourced"), 0) + 1

    stalled_attempts = (
        store.attempts_for_campaign(campaign, ("stalled", "parked"))
        if campaign_row else []
    )
    buckets = {
        # The operator's primary daily question: who owes an action right now.
        # Sum of recommended.needed over the true active roster (P1 corrected it).
        "needs_action": sum(1 for r in active if r["recommended"].get("needed")),
        "awaiting_reply": sum(1 for r in active if r["awaiting"]),
        "dangling": sum(1 for r in active if r["dangling"]),
        "aging_hot": sum(1 for r in active if r["aging"]),
        "reached_dirk": sum(1 for r in active if r["reached"]),
        # Held is an off-board bucket, so it is counted over ALL rows, not active.
        "held": sum(1 for r in rows if r["held"]),
        "due_today": sum(1 for r in active if r["due_today"]),
        "manual_due": sum(1 for r in active if r["manual_due"]),
        "stalled": len(stalled_attempts),
    }

    tiers = sorted({r.get("tier") for r in rows if r.get("tier")})
    owners = sorted({r.get("crm_owner") for r in rows if r.get("crm_owner")})
    degrees = sorted({r.get("degree") for r in rows if r.get("degree")})

    # Apply filters.
    ftier = (filters.get("tier") or "").strip()
    fstage = (filters.get("stage") or "").strip()
    fowner = (filters.get("owner") or "").strip()
    fbucket = (filters.get("bucket") or "").strip()
    fdegree = (filters.get("degree") or "").strip()
    q = (filters.get("q") or "").strip().lower()
    show_suppressed = str(filters.get("show_suppressed") or "").strip() in ("1", "true", "on")

    # The "held" bucket is off-board, so it seeds from all rows; every other
    # view starts from active (or all, when show_suppressed is on).
    if fbucket == "held":
        shown = [r for r in rows if r["held"]]
    else:
        shown = rows if show_suppressed else active
    if ftier:
        shown = [r for r in shown if r.get("tier") == ftier]
    if fstage:
        shown = [r for r in shown if r.get("stage") == fstage]
    if fowner:
        shown = [r for r in shown if r.get("crm_owner") == fowner]
    if fdegree:
        shown = [r for r in shown if r.get("degree") == fdegree]
    if fbucket == "action":
        shown = [r for r in shown if r["recommended"].get("needed")]
    elif fbucket == "awaiting":
        shown = [r for r in shown if r["awaiting"]]
    elif fbucket == "dangling":
        shown = [r for r in shown if r["dangling"]]
    elif fbucket == "aging":
        shown = [r for r in shown if r["aging"]]
    elif fbucket == "reached":
        shown = [r for r in shown if r["reached"]]
    elif fbucket == "due_today":
        shown = [r for r in shown if r["due_today"]]
    elif fbucket == "manual_due":
        shown = [r for r in shown if r["manual_due"]]
    def _hit(r):
        hay = " ".join(str(r.get(k) or "") for k in
                       ("first_name", "last_name", "company", "email", "job_title"))
        return q in hay.lower()
    if q:
        shown = [r for r in shown if _hit(r)]
    # Search fallback: a query that matches only suppressed (hidden) contacts
    # must not dead-end as "No contacts match". Count the suppressed matches so
    # the board can offer to reveal them (links to the same query, show_suppressed=1).
    suppressed_matches = (
        sum(1 for r in rows if r.get("suppressed") and _hit(r))
        if q and not show_suppressed else 0
    )

    # Hide the Degree / Step columns when every visible row is empty (all-NULL
    # degrees, no active cadence): two dead '-' columns just add noise.
    show_degree = any(r.get("degree") for r in shown)
    show_step = any((r.get("cadence") or {}).get("steps_total") for r in shown)

    return {
        "campaign": campaign,
        "campaign_row": dict(campaign_row) if campaign_row else None,
        "campaigns": campaigns,
        "stage_counts": stage_counts,
        "stages": list(STAGES),
        "stage_labels": STAGE_LABELS,
        "show_degree": show_degree,
        "show_step": show_step,
        "total_active": len(active),
        "total_suppressed": len(rows) - len(active),
        "buckets": buckets,
        "tiers": tiers,
        "owners": owners,
        "degrees": degrees,
        "stalled_attempts": [dict(a) for a in stalled_attempts],
        "rows": shown,
        "suppressed_matches": suppressed_matches,
        "filters": {
            "tier": ftier, "stage": fstage, "owner": fowner,
            "bucket": fbucket, "degree": fdegree, "q": filters.get("q") or "",
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
    contact["recommended"] = recommended_action(
        {**contact, **enriched}, datetime.now(timezone.utc).date())
    events = [_row(e) for e in store.get_events(contact_id)]

    # Cadence card: one entry per campaign this contact is enrolled in.
    from . import cadence
    cadences = []
    enr_rows = store.conn.execute(
        "SELECT * FROM enrollments WHERE contact_id = ?", (contact_id,)
    ).fetchall()
    for enr in enr_rows:
        campaign_row = store.get_campaign(enr["campaign_id"])
        if campaign_row is None:
            continue
        seq = store.get_sequence(enr["campaign_id"], enr["degree"] or "")
        steps = seq["steps"] if seq else []
        prog = store.conn.execute(
            "SELECT * FROM enrollment_progress WHERE enrollment_id = ?",
            (enr["enrollment_id"],),
        ).fetchone()
        st = cadence.enrollment_state(
            dict(enr), dict(prog) if prog else {}, steps, contact, dict(campaign_row))
        attempts = store.conn.execute(
            "SELECT * FROM send_attempts WHERE enrollment_id = ? ORDER BY step_no",
            (enr["enrollment_id"],),
        ).fetchall()
        cadences.append({
            "enrollment": dict(enr), "campaign": dict(campaign_row),
            "sequence": seq, "state": st,
            "attempts": [dict(a) for a in attempts],
        })

    return {
        "contact": contact,
        "events": events,
        "cadences": cadences,
        "stage_labels": STAGE_LABELS,
        "suppress_reasons": SUPPRESS_REASONS,
        "tier_vocab": list(TIER_VOCAB),
        "phases": outreach_phases(events),
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
    had_demo = bool((current["demo_date"] or "").strip())
    if new_demo and not had_demo:
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="outbound",
            type="booked", subject="Demo booked", detail=f"demo_date={new_demo}",
            source="manual", created_by=user, now=now,
        )
    # Reversibility: clearing a demo_date un-books the contact. The stage view
    # reads the LATEST booked/unbooked event, so this compensating event wins
    # over the earlier 'booked' - a fat-fingered demo no longer sticks forever.
    elif had_demo and "demo_date" in clean and not new_demo:
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="outbound",
            type="unbooked", subject="Demo un-booked", detail="demo_date cleared",
            source="manual", created_by=user, now=now,
        )
    verdict = clean.get("dirk_verdict")
    if verdict == "accepted" and current["dirk_verdict"] != "accepted":
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="inbound",
            type="accepted", subject="Accepted", detail="Dirk verdict: accepted",
            source="manual", created_by=user, now=now,
        )
    # Reversibility: verdict leaving 'accepted' un-accepts (compensating event).
    elif "dirk_verdict" in clean and verdict != "accepted" and current["dirk_verdict"] == "accepted":
        store.add_event(
            contact_id=contact_id, ts=now, channel="meeting", direction="inbound",
            type="unaccepted", subject="Acceptance revoked",
            detail=f"Dirk verdict changed to {verdict or '(cleared)'}",
            source="manual", created_by=user, now=now,
        )


def create_contact(store: ContactStore, data: dict, user: str | None) -> tuple[str, bool]:
    """Create a new lead. Dedupes by email: if the address is already on file,
    returns the existing contact_id and (id, False); otherwise inserts and
    returns (new_id, True), logging a `contact created` audit event."""
    from uuid import uuid4

    from ..identity import natural_key

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
    """Sink for POST /events (capture workers). Resolves the contact by id or
    email, appends the event idempotently. Returns a small result dict.

    Cadence guards: the ``cadence:`` ext_key namespace is reserved for the
    outbox (the step pointer counts those events - an external writer could
    corrupt it); a captured 'sent' whose internetMessageId matches a worker
    send is dropped (the outbox already logged it - Graph/COM capture seeing
    the same mail must not double-log); a 'bounce' auto-suppresses the contact
    so every campaign halts, not just the one that bounced."""
    now = now_iso()
    ext_key = (payload.get("ext_key") or payload.get("internet_message_id") or "").strip() or None
    if ext_key and ext_key.startswith(CADENCE_PREFIX):
        return {"ok": False, "reason": "reserved ext_key namespace"}

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

    type_ = payload.get("type") or "sent"
    imid = (payload.get("internet_message_id") or "").strip()
    if type_ == "sent" and imid:
        known = store.find_attempt_by_imid(imid)
        if known is not None:
            return {"ok": True, "contact_id": contact_id, "inserted": False,
                    "deduped": "worker send"}

    ts = (payload.get("occurred_at") or payload.get("ts") or "").strip() or now
    inserted = store.add_event(
        contact_id=contact_id,
        ts=ts,
        channel=payload.get("channel") or "email",
        direction=payload.get("direction") or "outbound",
        type=type_,
        subject=payload.get("subject"),
        detail=payload.get("detail"),
        source=payload.get("source") or "graph-auto",
        ext_key=ext_key,
        now=now,
    )
    if type_ == "bounce":
        contact = store.get_contact(contact_id)
        if contact is not None and not contact["suppressed"]:
            store.set_suppressed(contact_id, True, "bounced", "auto", now)
    return {"ok": True, "contact_id": contact_id, "inserted": inserted}
