"""Spaced sending: per-day new-contact ramp, per-mailbox cap across campaigns,
and the projected-schedule preview.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import cadence
from lead_desk.web.app import create_app
from lead_desk.web.service import now_iso
from lead_desk.web.store import ContactStore

BASE = "2026-07-14T09:00:00+00:00"
IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)  # Wed
WORKER = "w"


def _store(tmp_path) -> ContactStore:
    data = tmp_path / "data"
    data.mkdir()
    return ContactStore(data / "lead-desk.sqlite")


def make_campaign(store, cid, emails, *, ramp=None, from_addr=None, daily_cap=40):
    opts = {"daily_cap": daily_cap}
    if from_addr:
        opts["from_address"] = from_addr
    store.create_campaign(cid, cid, BASE, **opts)
    key = f"{cid}t"
    store.save_template(key, "email", "Hi {{first_name}}", "Body {{company}}", "t", BASE)
    store.upsert_sequence(cid, "cold", "cold", "auto-matthias",
                          [{"step_no": 1, "channel": "email",
                            "template_key": key, "day_offset": 0}])
    for i, email in enumerate(emails, 1):
        c = f"{cid}c{i}"
        store.upsert_contact({"contact_id": c, "natural_key": c, "campaign": "rome-2026",
                              "first_name": f"F{i}", "last_name": f"L{i}",
                              "company": f"Co{i}", "email": email}, now_iso())
        store.enroll(c, cid, "t", BASE)
        enr = store.find_enrollment(c, cid)
        store.set_degree(enr["enrollment_id"], "cold", "manual", "t")
    assert cadence.approve_campaign(store, cid, "t", cid, now=BASE)["ok"]
    assert cadence.start_sending(store, cid, "t", cid, now=BASE)["ok"]
    if ramp is not None:
        store.update_campaign(cid, {"ramp_per_day": ramp}, BASE)
    return cid


def test_ramp_caps_first_step_sends_per_day(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, "camp1", [f"a{i}@example.com" for i in range(5)], ramp=2)
    claims = cadence.claim_sends(store, WORKER, 10, at=IN_WINDOW)["claims"]
    assert len(claims) == 2  # 5 due, but only 2 fresh contacts start today


def test_no_ramp_sends_all_due(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, "camp1", [f"a{i}@example.com" for i in range(5)])
    claims = cadence.claim_sends(store, WORKER, 10, at=IN_WINDOW)["claims"]
    assert len(claims) == 5


def test_mailbox_cap_spans_campaigns(tmp_path):
    store = _store(tmp_path)
    # Both campaigns send from the same (default) warm mailbox.
    make_campaign(store, "campA", ["a1@example.com", "a2@example.com"])
    make_campaign(store, "campB", ["b1@example.com", "b2@example.com"])
    store.set_state("mailbox_daily_cap", "3", BASE)
    claims = cadence.claim_sends(store, WORKER, 10, at=IN_WINDOW)["claims"]
    assert len(claims) == 3  # 4 due across two campaigns, mailbox cap holds at 3


def test_mailbox_cap_is_per_mailbox(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, "campA", ["a1@example.com", "a2@example.com"])
    make_campaign(store, "campB", ["b1@example.com", "b2@example.com"],
                  from_addr="dirk.neumann@brisken.com")
    store.set_state("mailbox_daily_cap", "1", BASE)
    claims = cadence.claim_sends(store, WORKER, 10, at=IN_WINDOW)["claims"]
    # 1 from each mailbox = 2 total (the cap is per mailbox, not global)
    assert len(claims) == 2
    assert {c["from"] for c in claims} == {
        "matthias.silva@brisken.com", "dirk.neumann@brisken.com"}


def test_project_schedule_spreads_by_ramp(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, "camp1", [f"a{i}@example.com" for i in range(10)], ramp=3)
    sched = cadence.project_schedule(store, "camp1", at=IN_WINDOW)
    assert sum(d["count"] for d in sched) == 10          # every contact projected
    assert sched[0] == {"date": "2026-07-15", "count": 3}  # ramp holds day 1 to 3
    # Wed/Thu/Fri get 3 each, weekend skipped, Monday mops up the last 1.
    assert [d["date"] for d in sched] == [
        "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-20"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def test_schedule_route_sets_ramp(client):
    with ContactStore(client.db) as s:
        s.create_campaign("camp1", "C", BASE)
    r = client.post("/campaigns/camp1/schedule",
                    data={"start_not_before": "", "ramp_per_day": "5"},
                    follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(client.db) as s:
        assert s.get_campaign("camp1")["ramp_per_day"] == 5


def test_mailbox_cap_route(client):
    r = client.post("/settings/mailbox-cap",
                    data={"mailbox_daily_cap": "120"}, follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(client.db) as s:
        assert s.get_state("mailbox_daily_cap") == "120"
