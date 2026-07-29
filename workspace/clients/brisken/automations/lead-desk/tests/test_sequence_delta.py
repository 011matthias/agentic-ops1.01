"""Live sequence editing via delta approval (increment 4, part 2).

apply_sequence_delta appends / inserts / swaps FUTURE (unsent) steps on an
approved-or-sending campaign WITHOUT demoting it to draft. Already-sent steps are
immutable history: the delta refuses any change to them. Send-safety is intact -
recipient pins + contacts hash untouched, every future step is re-pinned so
nothing goes out unpinned. Builds on part 1's step_no-keyed pointer.

Fixed clock (default window Mon-Fri 08:30-17:30 Europe/Berlin):
  BASE = 2026-07-14 (approval), WED = 07-15 11:00 Berlin, THU = 07-16 11:00.
"""
from __future__ import annotations

from datetime import datetime, timezone

from lead_desk.web import cadence
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

BASE = "2026-07-14T09:00:00+00:00"
WED = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)   # Wed 11:00 Berlin
THU = datetime(2026, 7, 16, 9, 0, tzinfo=timezone.utc)   # Thu 11:00 Berlin
CID = "camp"


def _tpl(store, key, body="Body {{first_name}}", subject="Hi {{first_name}}"):
    return store.save_template(key, "email", subject, body, "t", BASE)


def build(store, steps, cid=CID, start=True):
    """Campaign + one contact + a cold email sequence, approved (+started)."""
    store.upsert_contact({"contact_id": "c1", "natural_key": "c1",
                          "campaign": "rome-2026", "first_name": "Ann",
                          "company": "Acme", "email": "c1@x.com"}, BASE)
    store.create_campaign(cid, "C", BASE)
    for s in steps:
        _tpl(store, s["template_key"])
    store.upsert_sequence(cid, "cold", "Cold", "auto-matthias", steps)
    store.enroll("c1", cid, "t", BASE)
    eid = int(store.find_enrollment("c1", cid)["enrollment_id"])
    store.set_degree(eid, "cold", "manual", "test")
    assert cadence.approve_campaign(store, cid, "t", cid, now=BASE)["ok"]
    if start:
        assert cadence.start_sending(store, cid, "t", cid, now=BASE)["ok"]
    return eid


def _send_step_1(store, at=WED):
    claim = cadence.claim_sends(store, "w", 10, at=at)["claims"]
    assert [c["step_no"] for c in claim] == [1]
    res = cadence.resolve_result(store, {
        "attempt_key": claim[0]["attempt_key"], "lease_id": claim[0]["lease_id"],
        "status": "sent", "occurred_at": "2026-07-15T09:00:00+00:00"})
    assert res["ok"] and res["event_inserted"]


TWO = [{"step_no": 1, "channel": "email", "template_key": "e1", "day_offset": 0},
       {"step_no": 2, "channel": "email", "template_key": "e2", "day_offset": 3}]


# -- 1. append a step to a live campaign (stays sending) -------------------------

def test_append_step_keeps_sending_and_pins_new_template(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        _tpl(s, "e3")
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0},
            {"channel": "email", "template_key": "e2", "day_offset": 3},
            {"channel": "email", "template_key": "e3", "day_offset": 5}], "t")
        assert res["ok"], res
        assert res["frozen_count"] == 1
        assert s.get_campaign(CID)["status"] == "sending"     # NOT demoted
        seq = s.get_sequence(CID, "cold")
        assert [(x["step_no"], x["template_key"]) for x in seq["steps"]] == [
            (1, "e1"), (2, "e2"), (3, "e3")]
        assert s.get_pins(CID)["e3"] == 1                     # new key pinned


# -- 2. TRUE insert: a new step runs before an existing future step -------------

def test_insert_future_step_runs_before_the_old_next_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)                                       # sent = {1}
        _tpl(s, "eNEW")
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0},    # frozen
            {"channel": "email", "template_key": "eNEW", "day_offset": 1},  # inserted
            {"channel": "email", "template_key": "e2", "day_offset": 3}], "t")
        assert res["ok"], res
        assert s.get_campaign(CID)["status"] == "sending"
        seq = s.get_sequence(CID, "cold")
        assert [(x["step_no"], x["template_key"]) for x in seq["steps"]] == [
            (1, "e1"), (2, "eNEW"), (3, "e2")]
        # The inserted step is the next thing that goes out - NOT a re-send of e1,
        # NOT a skip to e2 (the part-1 corruption). eNEW off1 anchors on the
        # step-1 send (07-15) -> due 07-16.
        due = cadence.due_items(s, CID, THU)
        assert [(i["step"]["step_no"], i["step"]["template_key"])
                for i in due["emails"]] == [(2, "eNEW")]
        out = cadence.claim_sends(s, "w", 10, at=THU)
        assert [c["step_no"] for c in out["claims"]] == [2]
        assert out["claims"][0]["template_key"] == "eNEW"


# -- 3. swap a future step's template VERSION (re-pin only the changed key) ------

def test_swap_future_template_version_repins_only_that_key(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        assert s.get_pins(CID) == {"e1": 1, "e2": 1}
        assert _tpl(s, "e2", body="V2 {{first_name}}") == 2   # new version of e2
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0},
            {"channel": "email", "template_key": "e2", "day_offset": 3}], "t")
        assert res["ok"], res
        # e2 (a future-only key) bumps to latest; e1 (frozen) keeps its pin.
        assert s.get_pins(CID)["e2"] == 2
        assert s.get_pins(CID)["e1"] == 1
        assert res["added_pins"] == {"e2": 2}


# -- 4. refuse any change to an already-sent step -------------------------------

def test_refuse_changing_a_sent_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        _tpl(s, "eX")
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "eX", "day_offset": 0},   # !=e1
            {"channel": "email", "template_key": "e2", "day_offset": 3}], "t")
        assert res["ok"] is False
        assert any("already been sent" in e for e in res["errors"])
        # Nothing changed: sequence + status intact.
        assert s.get_campaign(CID)["status"] == "sending"
        seq = s.get_sequence(CID, "cold")
        assert seq["steps"][0]["template_key"] == "e1"


def test_refuse_removing_a_sent_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        # An empty (or too-short) submission would drop the already-sent step 1.
        res = cadence.apply_sequence_delta(s, CID, "cold", [], "t")
        assert res["ok"] is False
        assert any("cannot be removed" in e for e in res["errors"])


# -- 5. a draft campaign is not a delta target ----------------------------------

def test_refuse_delta_on_draft(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO, start=False)
        s.update_campaign(CID, {"status": "draft"}, now_iso())
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0}], "t")
        assert res["ok"] is False
        assert any("draft" in e for e in res["errors"])


# -- 6. an approved-but-unsent campaign can be fully re-sequenced, stays approved -

def test_delta_on_approved_unsent_rewrites_all_steps(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO, start=False)                     # approved, nothing sent
        assert s.get_campaign(CID)["status"] == "approved"
        _tpl(s, "eA")
        res = cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "eA", "day_offset": 0},
            {"channel": "email", "template_key": "e2", "day_offset": 2}], "t")
        assert res["ok"] and res["frozen_count"] == 0
        assert s.get_campaign(CID)["status"] == "approved"    # still frozen-ready
        seq = s.get_sequence(CID, "cold")
        assert [(x["step_no"], x["template_key"]) for x in seq["steps"]] == [
            (1, "eA"), (2, "e2")]


# -- 7. send-safety survives a delta: recipient-drift still blocks ---------------

def test_recipient_pin_still_enforced_after_delta(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        _tpl(s, "eNEW")
        assert cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0},
            {"channel": "email", "template_key": "eNEW", "day_offset": 1},
            {"channel": "email", "template_key": "e2", "day_offset": 3}], "t")["ok"]
        # The daily sheet-sync overwrites the contact's email AFTER approval; the
        # recipient pin (untouched by the delta) must still block the drifted send.
        s.update_fields("c1", {"email": "attacker@evil.com"}, now_iso())
        out = cadence.claim_sends(s, "w", 10, at=THU)
        assert out["claims"] == []
        alert = s.get_state(f"send_guard_alert:{CID}")
        assert alert is not None and "recipient_drift" in alert


# -- 8. every future step is pinned -> the unpinned-template guard never fires ---

def test_delta_pins_every_future_step(tmp_path):
    with ContactStore(tmp_path / "db.sqlite") as s:
        build(s, TWO)
        _send_step_1(s)
        _tpl(s, "eNEW")
        assert cadence.apply_sequence_delta(s, CID, "cold", [
            {"channel": "email", "template_key": "e1", "day_offset": 0},
            {"channel": "email", "template_key": "eNEW", "day_offset": 1},
            {"channel": "email", "template_key": "e2", "day_offset": 3}], "t")["ok"]
        pins = s.get_pins(CID)
        seq = s.get_sequence(CID, "cold")
        for st in seq["steps"]:
            assert st["template_key"] in pins    # nothing can send unpinned
