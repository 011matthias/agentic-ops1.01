"""P6: operator features - merge-duplicate (tombstone + redirect), the context
brief / merge candidates, and the board inline quick-edit route plumbing."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web.app import create_app
from lead_desk.web.service import build_contact_view, now_iso
from lead_desk.web.store import ContactStore

NOW = "2026-07-16T00:00:00+00:00"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_DESK_ACCESS_CODES", raising=False)
    c = TestClient(create_app(tmp_path))
    c.db = tmp_path / "lead-desk.sqlite"
    return c


def _two_dupes(store):
    store.create_campaign("rome-2026", "Rome", NOW, status="done")
    store.upsert_contact({"contact_id": "surv", "natural_key": "s@x.com", "email": "s@x.com",
                          "first_name": "Jo", "last_name": "Lee", "company": "Acme",
                          "campaign": "rome-2026"}, now=NOW)
    store.upsert_contact({"contact_id": "lose", "natural_key": "anon:jo", "first_name": "Jo",
                          "last_name": "Lee", "company": "Acme", "email": "l@x.com",
                          "suppressed": 1, "suppress_reason": "no_consent",
                          "campaign": "rome-2026"}, now=NOW)
    store.enroll("surv", "rome-2026", "t", NOW)
    store.enroll("lose", "rome-2026", "t", NOW)
    store.add_event(contact_id="lose", ts=NOW, channel="email", direction="inbound",
                    type="reply", detail="loser reply", now=NOW)


def test_merge_repoints_and_tombstones(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _two_dupes(s)
        res = s.merge_contacts("surv", "lose", NOW)
        assert res["ok"] and res["events_moved"] == 1
        # loser is a suppressed duplicate pointing at the survivor
        lose = s.get_contact("lose")
        assert lose["suppressed"] == 1 and lose["suppress_reason"] == "duplicate"
        assert lose["merged_into"] == "surv"
        # the reply moved to the survivor
        assert any(e["detail"] == "loser reply" for e in s.get_events("surv"))
        # most-restrictive suppression (no_consent) folded onto the survivor
        assert s.get_contact("surv")["suppress_reason"] == "no_consent"
        # enrollment deduped to one
        assert s.conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE campaign_id='rome-2026'").fetchone()[0] == 1


def test_find_by_email_follows_tombstone(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _two_dupes(s)
        s.merge_contacts("surv", "lose", NOW)
        # a capture for the loser's address now resolves to the survivor
        assert s.find_by_email("l@x.com")["contact_id"] == "surv"


def test_merge_candidates_surfaced(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        _two_dupes(s)
        view = build_contact_view(s, "surv")
        assert [c["contact_id"] for c in view["merge_candidates"]] == ["lose"]
        # after merge, the tombstone is no longer offered as a candidate
        s.merge_contacts("surv", "lose", NOW)
        assert build_contact_view(s, "surv")["merge_candidates"] == []


def test_merge_route(client):
    with ContactStore(client.db) as s:
        _two_dupes(s)
    r = client.post("/contacts/lose/merge", data={"survivor": "surv"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/contacts/surv"
    with ContactStore(client.db) as s:
        assert s.get_contact("lose")["merged_into"] == "surv"


def test_sync_does_not_resurrect_a_merged_tombstone(tmp_path):
    """The regression the design turns on: after a merge, re-importing the
    loser's sheet row must NOT bring it back as an active contact."""
    from openpyxl import Workbook

    from lead_desk.migrate import import_workbook
    with ContactStore(tmp_path / "t.sqlite") as s:
        _two_dupes(s)
        s.merge_contacts("surv", "lose", NOW)
        # a sheet that still lists the loser's email row
        wb = Workbook()
        ws = wb.active
        ws.title = "Master contacts"
        ws.append(["email", "first_name", "last_name", "company"])
        ws.append(["l@x.com", "Jo", "Lee", "Acme"])
        xlsx = tmp_path / "master.xlsx"
        wb.save(xlsx)
        import_workbook(s, xlsx, "rome-2026", {}, preserve_app_fields=True)
        lose = s.get_contact("lose")
        assert lose["merged_into"] == "surv"        # still a tombstone
        assert lose["suppress_reason"] == "duplicate"  # not resurrected as active


def test_inline_next_step_edit_stays_on_board(client):
    with ContactStore(client.db) as s:
        _two_dupes(s)
    r = client.post("/contacts/surv/fields",
                    data={"next_step": "Call Tuesday", "back": "/?campaign=rome-2026"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/?campaign=rome-2026"
    with ContactStore(client.db) as s:
        assert s.get_contact("surv")["next_step"] == "Call Tuesday"
