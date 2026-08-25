"""Step_no-keyed cadence progress (increment 4, part 1).

enrollment_state picks the next step by the SET of sent step_nos, never a
positional COUNT of events. step_no is the stable send-identity (== the send
ext_key ``cadence:{eid}:{step_no}``), so a mid-sequence INSERT/REORDER can no
longer re-send old copy under a shifted index or skip the new step. Append-only
behaviour is unchanged (the existing suites pin that); these tests pin the
identity-keyed contract that makes the sequence-delta path (part 2) safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import SCHEMA_VERSION, ContactStore, attempt_key_for

IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)   # Wed 11:00 Berlin

CAMP = {"status": "sending", "start_not_before": None}
APPROVED_ENR = {"approved_at": "2026-07-14T09:00:00+00:00"}
CONTACT = {"suppressed": 0}


def _steps(*nos):
    return [{"step_no": n, "channel": "email", "template_key": f"e{n}",
             "day_offset": 0} for n in nos]


# -- 1. pure derivation: first unsent step by identity -------------------------

def test_first_unsent_step_is_next_by_step_no():
    st = cadence.enrollment_state(
        APPROVED_ENR, {"sent_steps": "1"}, _steps(1, 2, 3), CONTACT, CAMP)
    assert st["state"] == "active"
    assert st["next_step"]["step_no"] == 2
    assert st["steps_done"] == 1


def test_gap_in_sent_set_picks_the_missing_step_not_the_count_index():
    # sent {1, 3}, count 2. A positional index steps[2] would pick step_no 3
    # (already sent -> a re-send + the real step_no 2 skipped); identity-keying
    # picks the genuinely unsent step_no 2. THIS is the corruption class fixed.
    st = cadence.enrollment_state(
        APPROVED_ENR, {"sent_steps": "1,3"}, _steps(1, 2, 3), CONTACT, CAMP)
    assert st["next_step"]["step_no"] == 2
    assert st["steps_done"] == 2


def test_all_step_nos_sent_is_done():
    st = cadence.enrollment_state(
        APPROVED_ENR, {"sent_steps": "1,2"}, _steps(1, 2), CONTACT, CAMP)
    assert st["state"] == "done"
    assert st["steps_done"] == 2


def test_sent_step_no_not_in_sequence_is_ignored():
    # A step dropped from the sequence AFTER it was sent must neither mark the
    # enrollment done (a >= total count would) nor inflate steps_done.
    st = cadence.enrollment_state(
        APPROVED_ENR, {"sent_steps": "1,2"}, _steps(2, 3), CONTACT, CAMP)
    assert st["state"] == "active"
    assert st["next_step"]["step_no"] == 3
    assert st["steps_done"] == 1     # only step_no 2 is both sent AND in-sequence


def test_fallback_to_count_when_sent_steps_absent():
    # A progress dict lacking sent_steps falls back to the append-only prefix
    # {1..steps_done}, so an older caller keeps working unchanged.
    st = cadence.enrollment_state(
        APPROVED_ENR, {"steps_done": 2}, _steps(1, 2, 3), CONTACT, CAMP)
    assert st["next_step"]["step_no"] == 3
    assert st["steps_done"] == 2


def test_parse_sent_steps_variants():
    assert cadence.parse_sent_steps({"sent_steps": None, "steps_done": 3}) == {1, 2, 3}
    assert cadence.parse_sent_steps({"sent_steps": "2,5,1"}) == {1, 2, 5}
    assert cadence.parse_sent_steps({"sent_steps": ""}) == set()
    assert cadence.parse_sent_steps({}) == set()


# -- 2. the view exposes the sent set --------------------------------------------

def _minimal(store, cid="camp"):
    now = now_iso()
    store.upsert_contact({"contact_id": "c1", "natural_key": "c1",
                          "campaign": "rome-2026", "first_name": "A",
                          "company": "Co", "email": "c1@x.com"}, now)
    store.create_campaign(cid, "C", now)
    store.enroll("c1", cid, "t", now)
    return int(store.find_enrollment("c1", cid)["enrollment_id"])


def test_view_sent_steps_matches_steps_done(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        eid = _minimal(s)
        for n in (1, 2):
            s.add_event(contact_id="c1", ts=f"2026-07-1{n}T09:00:00+00:00",
                        channel="email", direction="outbound", type="sent",
                        source="worker-auto", ext_key=attempt_key_for(eid, n),
                        campaign="camp", now=now_iso())
        row = dict(s.conn.execute(
            "SELECT steps_done, sent_steps FROM enrollment_progress "
            "WHERE enrollment_id = ?", (eid,)).fetchone())
        assert row["steps_done"] == 2
        assert cadence.parse_sent_steps(row) == {1, 2}


def test_schema_version_and_view_column(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        assert SCHEMA_VERSION >= 10
        assert s.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        cols = [r[1] for r in
                s.conn.execute("PRAGMA table_info(enrollment_progress)").fetchall()]
        assert "sent_steps" in cols


# -- 3. end-to-end: the claim path picks by identity, never re-sends -------------

def _build_three_step(store, cid="camp3"):
    now = "2026-07-14T09:00:00+00:00"
    store.upsert_contact({"contact_id": "c1", "natural_key": "c1",
                          "campaign": "rome-2026", "first_name": "Ann",
                          "company": "Acme", "email": "c1@x.com"}, now)
    store.create_campaign(cid, "Three", now)
    steps = _steps(1, 2, 3)
    for st in steps:
        store.save_template(st["template_key"], "email", "Hi {{first_name}}",
                            f"Body {st['template_key']} for {{company}}", "t", now)
    store.upsert_sequence(cid, "cold", "Cold", "auto-matthias", steps)
    store.enroll("c1", cid, "t", now)
    eid = int(store.find_enrollment("c1", cid)["enrollment_id"])
    store.set_degree(eid, "cold", "manual", "test")
    assert cadence.approve_campaign(store, cid, "t", cid, now=now)["ok"]
    assert cadence.start_sending(store, cid, "t", cid, now=now)["ok"]
    return cid, eid


def test_claim_picks_unsent_step_not_the_count_index(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        cid, eid = _build_three_step(s)
        # Steps 1 and 3 already landed (no attempt rows, just the events): the
        # non-prefix sent set {1,3} that a positional count (=2 -> steps[2] =
        # step_no 3) would mishandle by re-sending the already-sent step 3.
        for n in (1, 3):
            s.add_event(contact_id="c1", ts="2026-07-14T09:05:00+00:00",
                        channel="email", direction="outbound", type="sent",
                        source="worker-auto", ext_key=attempt_key_for(eid, n),
                        campaign=cid, now=now_iso())
        due = cadence.due_items(s, cid, IN_WINDOW)
        assert [i["step"]["step_no"] for i in due["emails"]] == [2]
        out = cadence.claim_sends(s, "w1", 10, at=IN_WINDOW)
        assert [c["step_no"] for c in out["claims"]] == [2]
        assert out["claims"][0]["template_key"] == "e2"
