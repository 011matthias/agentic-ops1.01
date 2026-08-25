"""Vacation-aware scheduling: campaigns.start_not_before.

A nullable 'no earlier than' date holds a campaign's first wave until contacts
are back, so a wave can be approved now and sent later. The claim path sends
nothing before the date, and step 1 anchors on max(approved_at, start_not_before)
so day-offset math counts from the real start.
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
IN_WINDOW = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)   # Wed
AFTER = datetime(2026, 7, 20, 9, 0, tzinfo=timezone.utc)       # Mon, in window
WORKER = "w"


def _store(tmp_path) -> ContactStore:
    data = tmp_path / "data"
    data.mkdir()
    return ContactStore(data / "lead-desk.sqlite")


def make_campaign(store, cid="camp1", *, emails):
    store.create_campaign(cid, "Sched", BASE, daily_cap=40)
    store.save_template("t1", "email", "Hi {{first_name}}", "Body {{company}}", "t", BASE)
    store.upsert_sequence(cid, "cold", "cold seq", "auto-matthias",
                          [{"step_no": 1, "channel": "email",
                            "template_key": "t1", "day_offset": 0}])
    for i, email in enumerate(emails, 1):
        c = f"c{i}"
        store.upsert_contact({"contact_id": c, "natural_key": c, "campaign": "rome-2026",
                              "first_name": f"F{i}", "last_name": f"L{i}",
                              "company": f"Co{i}", "email": email}, now_iso())
        store.enroll(c, cid, "t", BASE)
        enr = store.find_enrollment(c, cid)
        store.set_degree(enr["enrollment_id"], "cold", "manual", "t")
    assert cadence.approve_campaign(store, cid, "t", cid, now=BASE)["ok"]
    assert cadence.start_sending(store, cid, "t", cid, now=BASE)["ok"]
    return cid


def test_holds_before_date_then_releases(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    store.update_campaign("camp1", {"start_not_before": "2026-07-18"}, BASE)
    # 2026-07-15 is before the start date: nothing claims.
    assert cadence.claim_sends(store, WORKER, 5, at=IN_WINDOW)["claims"] == []
    # 2026-07-20 is on/after it: the first step is due and claims.
    res = cadence.claim_sends(store, WORKER, 5, at=AFTER)
    assert [c["to"] for c in res["claims"]] == ["a@example.com"]


def test_no_start_date_sends_immediately(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    assert len(cadence.claim_sends(store, WORKER, 5, at=IN_WINDOW)["claims"]) == 1


def test_first_step_anchors_on_start_date(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    store.update_campaign("camp1", {"start_not_before": "2026-07-20"}, BASE)
    # peek at AFTER shows the step due exactly from the start date, not approval.
    peek = cadence.claim_sends(store, WORKER, 5, at=AFTER, peek=True)["claims"]
    assert len(peek) == 1


def test_scope_text_mentions_start_date(tmp_path):
    store = _store(tmp_path)
    make_campaign(store, emails=["a@example.com"])
    store.update_campaign("camp1", {"start_not_before": "2026-08-18"}, BASE)
    rep = cadence.approval_report(store, "camp1")
    assert "Starts no earlier than 2026-08-18" in rep["scope_text"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_AUTH_SECRET", raising=False)
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def test_schedule_route_sets_clears_and_validates(client):
    with ContactStore(client.db) as s:
        s.create_campaign("camp1", "C", BASE)
    r = client.post("/campaigns/camp1/schedule",
                    data={"start_not_before": "2026-08-18"}, follow_redirects=False)
    assert r.status_code == 303
    with ContactStore(client.db) as s:
        assert s.get_campaign("camp1")["start_not_before"] == "2026-08-18"
    # blank clears it
    client.post("/campaigns/camp1/schedule",
                data={"start_not_before": ""}, follow_redirects=False)
    with ContactStore(client.db) as s:
        assert s.get_campaign("camp1")["start_not_before"] is None
    # a malformed date is rejected
    r = client.post("/campaigns/camp1/schedule",
                    data={"start_not_before": "not-a-date"}, follow_redirects=False)
    assert r.status_code == 400
