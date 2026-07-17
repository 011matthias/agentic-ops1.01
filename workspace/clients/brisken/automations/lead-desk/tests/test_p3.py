"""P3: board/contact legibility - stage labels, empty-column hiding, the
Needs-action chip + tier legend rendering, and one-click Mark replied."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web.app import create_app
from lead_desk.web.service import build_board, now_iso, recommended_action
from lead_desk.web.store import ContactStore

NOW = "2026-07-16T00:00:00+00:00"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_ACCESS_CODES", raising=False)  # gate off in tests
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def _seed_reply_needed(db):
    with ContactStore(db) as s:
        s.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
        s.upsert_contact({"contact_id": "c1", "natural_key": "j@x.com",
                          "first_name": "Jo", "last_name": "Lee", "email": "j@x.com",
                          "campaign": "rome-2026"}, now=NOW)
        s.enroll("c1", "rome-2026", "t", NOW)
        s.add_event(contact_id="c1", ts="2026-07-10T00:00:00+00:00", channel="email",
                    direction="outbound", type="sent", now=NOW)
        s.add_event(contact_id="c1", ts="2026-07-14T00:00:00+00:00", channel="email",
                    direction="inbound", type="reply", now=NOW)


# --- service-level data --------------------------------------------------------

def test_build_board_exposes_stage_labels_and_column_flags(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        s.create_campaign("rome-2026", "Rome 2026", NOW, status="done")
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com", "campaign": "rome-2026"}, now=NOW)
        v = build_board(s, {})
        assert v["stage_labels"]["sourced"] == "Not contacted"
        # no degrees, no cadence -> both columns hidden
        assert v["show_degree"] is False and v["show_step"] is False


def test_recommended_action_carries_reply_kind():
    row = {"stage": "replied", "last_in": "2026-07-14T15:00:00+00:00",
           "last_out": "2026-07-10T00:00:00+00:00"}
    from datetime import date
    rec = recommended_action(row, date(2026, 7, 16))
    assert rec["needed"] and rec["kind"] == "reply"


# --- HTTP: board renders + Mark replied ---------------------------------------

def test_board_renders_needs_action_chip_and_legend(client):
    _seed_reply_needed(client.db)
    r = client.get("/?campaign=rome-2026")
    assert r.status_code == 200
    assert "Needs action" in r.text
    assert "Tiers" in r.text                       # tier legend
    assert "Not contacted" not in r.text or "Contacted" in r.text  # stage labels in use


def test_mark_replied_clears_the_reply(client):
    _seed_reply_needed(client.db)
    # before: c1 owes a reply
    with ContactStore(client.db) as s:
        assert build_board(s, {})["buckets"]["needs_action"] == 1
    r = client.post("/contacts/c1/mark-replied", data={"back": "/?campaign=rome-2026"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/?campaign=rome-2026"
    # after: an outbound 'sent' landed, last_out is now newer -> no longer needed
    with ContactStore(client.db) as s:
        assert any(e["subject"] == "Replied" and e["direction"] == "outbound"
                   for e in s.get_events("c1"))
        assert build_board(s, {})["buckets"]["needs_action"] == 0


def test_mark_replied_unknown_contact_404(client):
    _seed_reply_needed(client.db)
    r = client.post("/contacts/ghost/mark-replied", data={}, follow_redirects=False)
    assert r.status_code == 404
