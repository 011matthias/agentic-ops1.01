"""GET /api/events - the machine-readable event-log slice.

Auth mirrors /sync (session cookie OR the ingest bearer); every filter maps
to an indexed column; limit is capped at 1000 so one page can never pull the
whole log. Feeds the capture-adequacy verify mode in
tools/brisken-truth-sweep.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lead_desk.web import auth
from lead_desk.web.app import create_app
from lead_desk.web.store import ContactStore

NOW = "2026-07-15T00:00:00+00:00"
HDRS = {"Authorization": "Bearer isecret"}


def _seed(db_path):
    with ContactStore(db_path) as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com"}, now=NOW)
        s.upsert_contact({"contact_id": "c2", "natural_key": "b@y.com",
                          "email": "b@y.com", "campaign": "mdh-2026"}, now=NOW)
        s.add_event(contact_id="c1", ts="2026-07-10T09:00:00Z",
                    channel="email", direction="outbound", type="sent",
                    subject="hello", source="graph-auto",
                    ext_key="<im-1@x>", now=NOW)
        s.add_event(contact_id="c1", ts="2026-07-11T09:00:00Z",
                    channel="email", direction="inbound", type="reply",
                    subject="RE: hello", source="graph-auto",
                    ext_key="<im-2@x>", now=NOW)
        s.add_event(contact_id="c2", ts="2026-07-12T09:00:00Z",
                    channel="email", direction="outbound", type="sent",
                    subject="mdh", source="graph-auto",
                    ext_key="<im-3@y>", campaign="mdh-2026", now=NOW)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_INGEST_SECRET", "isecret")
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-hmac")  # gate ON
    c = TestClient(create_app(tmp_path))
    _seed(tmp_path / "lead-desk.sqlite")
    return c


# -- auth ----------------------------------------------------------------------

def test_unauthenticated_is_closed(client):
    assert client.get("/api/events").status_code == 401


def test_wrong_bearer_is_closed(client):
    r = client.get("/api/events",
                   headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_ingest_bearer_reads(client):
    r = client.get("/api/events", headers=HDRS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3 and len(body["events"]) == 3
    # rows are full outreach_events dicts, oldest first
    assert body["events"][0]["ext_key"] == "<im-1@x>"
    assert body["events"][0]["contact_id"] == "c1"


def test_session_cookie_reads(client):
    client.cookies.set(auth.COOKIE_NAME,
                       auth.issue_token("matthias.silva@brisken.com"))
    r = client.get("/api/events")
    assert r.status_code == 200 and r.json()["total"] == 3


# -- filters -------------------------------------------------------------------

@pytest.mark.parametrize("query, expected_keys", [
    ({"direction": "outbound"}, {"<im-1@x>", "<im-3@y>"}),
    ({"type": "reply"}, {"<im-2@x>"}),
    ({"campaign": "mdh-2026"}, {"<im-3@y>"}),
    ({"contact_id": "c1"}, {"<im-1@x>", "<im-2@x>"}),
    ({"ext_key": "<im-2@x>"}, {"<im-2@x>"}),
    ({"since": "2026-07-11T00:00:00Z"}, {"<im-2@x>", "<im-3@y>"}),
    ({"since": "2026-07-11T00:00:00Z", "direction": "outbound"},
     {"<im-3@y>"}),
])
def test_filters(client, query, expected_keys):
    r = client.get("/api/events", headers=HDRS, params=query)
    assert r.status_code == 200
    body = r.json()
    assert {e["ext_key"] for e in body["events"]} == expected_keys
    assert body["total"] == len(expected_keys)


# -- paging + limit cap --------------------------------------------------------

def test_offset_pages_with_stable_total(client):
    r = client.get("/api/events", headers=HDRS,
                   params={"limit": 1, "offset": 1})
    body = r.json()
    assert body["total"] == 3
    assert [e["ext_key"] for e in body["events"]] == ["<im-2@x>"]


def test_limit_is_capped_at_1000(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_DESK_INGEST_SECRET", "isecret")
    monkeypatch.setenv("LEAD_DESK_AUTH_SECRET", "test-hmac")
    client = TestClient(create_app(tmp_path))
    with ContactStore(tmp_path / "lead-desk.sqlite") as s:
        s.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                          "email": "a@x.com"}, now=NOW)
        # bulk insert (one commit) - 1005 add_event round-trips are slow
        s.conn.executemany(
            "INSERT INTO outreach_events (contact_id, campaign, ts, channel,"
            " direction, type, source, created_at, event_hash)"
            " VALUES ('c1', 'rome-2026', ?, 'email', 'outbound', 'sent',"
            " 'graph-auto', ?, ?)",
            [(f"2026-07-10T09:00:{i % 60:02d}Z", NOW, f"h{i}")
             for i in range(1005)])
        s.conn.commit()
    r = client.get("/api/events", headers=HDRS, params={"limit": 999999})
    body = r.json()
    assert body["total"] == 1005
    assert len(body["events"]) == 1000  # cap held


def test_limit_floor_is_one(client):
    r = client.get("/api/events", headers=HDRS, params={"limit": -5})
    assert len(r.json()["events"]) == 1
