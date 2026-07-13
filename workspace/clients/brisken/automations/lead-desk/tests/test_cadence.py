"""Campaign-engine cadence: enrollment_state + due/claim derivation.

Runs against a real ContactStore on tmp_path. claim_sends is ALWAYS called
with an explicit ``at`` so the send-window logic is deterministic:
2026-07-15 09:00 UTC = Wednesday 11:00 Europe/Berlin (inside the default
window), 2026-07-18 = Saturday, 20:00 UTC = 22:00 Berlin (after hours).
"""
from __future__ import annotations

from datetime import datetime, timezone

from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore, attempt_key_for

CAMPAIGN_ID = "camp-1"
IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)     # Wed 11:00 Berlin
SATURDAY = datetime(2026, 7, 18, 9, 0, tzinfo=timezone.utc)
AFTER_HOURS = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)  # Wed 22:00 Berlin

TWO_EMAIL_STEPS = [
    {"step_no": 1, "channel": "email", "template_key": "e1", "day_offset": 0},
    {"step_no": 2, "channel": "email", "template_key": "e2", "day_offset": 3},
]
LI_THEN_EMAIL = [
    {"step_no": 1, "channel": "linkedin", "template_key": "li1", "day_offset": 0},
    {"step_no": 2, "channel": "email", "template_key": "e1", "day_offset": 0},
]


def make_contact(store, cid_suffix, email=None, **fields):
    cid = f"c{cid_suffix}"
    data = {"contact_id": cid, "natural_key": cid, "campaign": "rome-2026",
            "first_name": "A", "last_name": f"B{cid_suffix}", "company": "Co",
            "email": f"{cid}@x.com" if email is None else email}
    data.update(fields)
    store.upsert_contact(data, now_iso())
    return cid


def make_engine_campaign(store, contact_ids, steps=None, approve=True):
    """Campaign + templates + one 'cold' sequence + enrollments (+ approval)."""
    now = now_iso()
    store.create_campaign(CAMPAIGN_ID, "Engine Test", now)
    steps = steps or TWO_EMAIL_STEPS
    for s in steps:
        store.save_template(
            s["template_key"], s["channel"],
            "Hi {{first_name}}" if s["channel"] == "email" else None,
            "Body for {{first_name}} at {{company}}", "tester", now)
    store.upsert_sequence(CAMPAIGN_ID, "cold", "Cold", "auto-matthias", steps)
    for cid in contact_ids:
        store.enroll(cid, CAMPAIGN_ID, "tester", now)
        enr = store.find_enrollment(cid, CAMPAIGN_ID)
        store.set_degree(enr["enrollment_id"], "cold", "manual", "test")
    if approve:
        res = cadence.approve_campaign(store, CAMPAIGN_ID, "tester", CAMPAIGN_ID)
        assert res["ok"], res
    return CAMPAIGN_ID


def state_for(store, contact_id):
    """Assemble enrollment_state inputs from live rows, mirroring the service."""
    enr = store.find_enrollment(contact_id, CAMPAIGN_ID)
    prog = store.conn.execute(
        "SELECT * FROM enrollment_progress WHERE enrollment_id = ?",
        (enr["enrollment_id"],),
    ).fetchone()
    seq = store.get_sequence(CAMPAIGN_ID, enr["degree"] or "")
    steps = seq["steps"] if seq else []
    return cadence.enrollment_state(
        dict(enr), dict(prog), steps,
        dict(store.get_contact(contact_id)), dict(store.get_campaign(CAMPAIGN_ID)))


# -- 1. step pointer counts only the reserved cadence: namespace ---------------

def test_step_pointer_ignores_non_cadence_events(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        s.add_event(contact_id=cid, ts="2026-07-10T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", source="graph-auto",
                    ext_key="msgid-123", now=now_iso())
        row = {r["contact_id"]: dict(r)
               for r in s.enrollments_for_campaign(CAMPAIGN_ID)}[cid]
        assert row["steps_done"] == 0
        assert row["last_step_ts"] is None
        assert state_for(s, cid)["steps_done"] == 0


# -- 2. reply-stop is scoped to replies at/after enrollment --------------------

def test_reply_after_enrollment_stops(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        # enrolled_at was stamped with real now; this ts is safely after it.
        s.add_event(contact_id=cid, ts="2027-01-01T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        assert state_for(s, cid)["state"] == "stopped:replied"


def test_reply_before_enrollment_does_not_stop(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        # enrolled_at is real now (>= 2026-07-13); this reply predates it.
        s.add_event(contact_id=cid, ts="2026-07-01T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=now_iso())
        cadence.start_sending(s, CAMPAIGN_ID, "tester", CAMPAIGN_ID)
        assert state_for(s, cid)["state"] == "active"


# -- 3. the other stop / wait states -------------------------------------------

def test_bounce_stops(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        s.add_event(contact_id=cid, ts="2026-07-10T10:00:00+00:00", channel="email",
                    direction="inbound", type="bounce", now=now_iso())
        assert state_for(s, cid)["state"] == "stopped:bounced"


def test_suppressed_stops(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        s.set_suppressed(cid, True, "stop", "tester", now_iso())
        assert state_for(s, cid)["state"] == "stopped:suppressed"


def test_paused_campaign(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])
        s.update_campaign(CAMPAIGN_ID, {"status": "paused"}, now_iso())
        assert state_for(s, cid)["state"] == "paused"
        assert cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"] == []


def test_unapproved_enrollment_is_pending(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid], approve=False)
        assert state_for(s, cid)["state"] == "pending_approval"
        assert cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"] == []


def test_all_steps_done_is_done(tmp_path):
    one_step = [{"step_no": 1, "channel": "email", "template_key": "e1",
                 "day_offset": 0}]
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid], steps=one_step)
        eid = s.find_enrollment(cid, CAMPAIGN_ID)["enrollment_id"]
        s.add_event(contact_id=cid, ts="2026-07-10T09:00:00+00:00", channel="email",
                    direction="outbound", type="sent", source="worker-auto",
                    ext_key=attempt_key_for(eid, 1), now=now_iso())
        st = state_for(s, cid)
        assert st["state"] == "done"
        assert st["steps_done"] == 1


# -- 4. next_due anchors: approval for step 1, last cadence ts afterwards ------

def test_next_due_anchors_on_approval_then_last_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid])  # day offsets 0 / 3
        cadence.start_sending(s, CAMPAIGN_ID, "tester", CAMPAIGN_ID)
        enr = s.find_enrollment(cid, CAMPAIGN_ID)
        st = state_for(s, cid)
        assert st["state"] == "active"
        assert st["next_step"]["step_no"] == 1
        assert st["next_due"] == str(enr["approved_at"])[:10]

        # Window gate on the claim path (weekend / after hours yield nothing).
        assert cadence.claim_sends(s, "w1", 10, at=SATURDAY)["claims"] == []
        assert cadence.claim_sends(s, "w1", 10, at=AFTER_HOURS)["claims"] == []

        claimed = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert claimed["paused"] is False
        assert [c["step_no"] for c in claimed["claims"]] == [1]
        claim = claimed["claims"][0]
        assert claim["to"] == "c1@x.com"
        assert claim["template_key"] == "e1"

        res = cadence.resolve_result(s, {
            "attempt_key": claim["attempt_key"], "lease_id": claim["lease_id"],
            "status": "sent", "occurred_at": "2026-07-10T09:00:00+00:00",
            "internet_message_id": "imid-1"})
        assert res["ok"] and res["event_inserted"]

        st2 = state_for(s, cid)
        assert st2["steps_done"] == 1
        assert st2["next_step"]["step_no"] == 2
        assert st2["next_due"] == "2026-07-13"  # date(occurred_at) + offset 3


# -- 5. a linkedin step blocks the following email step ------------------------

def test_linkedin_step_blocks_email_until_marked_done(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid = make_contact(s, 1)
        make_engine_campaign(s, [cid], steps=LI_THEN_EMAIL)
        cadence.start_sending(s, CAMPAIGN_ID, "tester", CAMPAIGN_ID)

        due = cadence.due_items(s, CAMPAIGN_ID, IN_WINDOW)
        assert due["emails"] == []
        assert [i["step"]["step_no"] for i in due["manual"]] == [1]
        assert cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)["claims"] == []

        eid = s.find_enrollment(cid, CAMPAIGN_ID)["enrollment_id"]
        res = cadence.mark_manual_done(s, eid, 1, "tester")
        assert res["ok"] and res["event_inserted"]

        claimed = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert [c["step_no"] for c in claimed["claims"]] == [2]
        assert claimed["claims"][0]["template_key"] == "e1"


# -- 6. send window -------------------------------------------------------------

def test_parse_window_defaults_and_in_window():
    w = cadence.parse_window(None)
    assert (w["days"], w["start"], w["end"], w["tz"]) == (
        [0, 1, 2, 3, 4], "08:30", "17:30", "Europe/Berlin")
    assert cadence.in_window(w, IN_WINDOW)          # Wed 11:00 Berlin
    assert not cadence.in_window(w, SATURDAY)       # weekday 5 not in days
    assert not cadence.in_window(w, AFTER_HOURS)    # 22:00 Berlin > 17:30
