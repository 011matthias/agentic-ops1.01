"""T1: ingest truth fixes - campaign passthrough on captured events, the
unmatched-event queue (park, dedupe, operator link/dismiss, never auto-create
a contact), and the v11 migration that carries the new tables."""
from __future__ import annotations

import json
import sqlite3

from lead_desk.web.service import ingest_event, link_unmatched, now_iso
from lead_desk.web.store import SCHEMA_VERSION, ContactStore

NOW = "2026-07-15T00:00:00+00:00"


def _contact(store, cid, email):
    store.upsert_contact({"contact_id": cid, "natural_key": email,
                          "email": email}, now=NOW)
    return cid


# -- 1. campaign passthrough ---------------------------------------------------

def test_ingest_campaign_passthrough(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        c1 = _contact(s, "c1", "lead@acme.com")
        res = ingest_event(s, {"email": "lead@acme.com", "type": "sent",
                               "campaign": "mdh-2026",
                               "occurred_at": "2026-07-01T09:00:00+00:00"})
        assert res["ok"] and res["inserted"]
        assert s.get_events(c1)[0]["campaign"] == "mdh-2026"


def test_ingest_campaign_default_unchanged(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        c1 = _contact(s, "c1", "lead@acme.com")
        res = ingest_event(s, {"email": "lead@acme.com", "type": "sent",
                               "occurred_at": "2026-07-01T09:00:00+00:00"})
        assert res["ok"] and res["inserted"]
        assert s.get_events(c1)[0]["campaign"] == "rome-2026"


# -- 2. unmatched queue --------------------------------------------------------

def test_ingest_unmatched_persists_payload(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        payload = {"email": "stranger@new.com", "type": "reply",
                   "internet_message_id": "<u1@new.com>",
                   "subject": "RE: Rome", "occurred_at": "2026-07-14T08:00:00+00:00"}
        res = ingest_event(s, payload)
        assert res == {"ok": True, "queued": "unmatched", "email": "stranger@new.com"}
        assert s.count_events() == 0                    # nothing on a timeline
        rows = s.list_unmatched()
        assert len(rows) == 1
        assert rows[0]["email"] == "stranger@new.com"
        assert rows[0]["status"] == "open"
        assert rows[0]["seen_count"] == 1
        assert json.loads(rows[0]["payload"]) == payload


def test_unmatched_dedupes_on_event_hash(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        payload = {"email": "stranger@new.com", "type": "reply",
                   "internet_message_id": "<u1@new.com>",
                   "occurred_at": "2026-07-14T08:00:00+00:00"}
        ingest_event(s, payload)
        ingest_event(s, payload)                        # re-poll of the same message
        rows = s.list_unmatched()
        assert len(rows) == 1
        assert rows[0]["seen_count"] == 2


def test_unmatched_link_replays_event(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        ingest_event(s, {"email": "stranger@new.com", "type": "reply",
                         "internet_message_id": "<u1@new.com>",
                         "occurred_at": "2026-07-14T08:00:00+00:00"})
        # operator creates the contact AFTER the event was queued, then links
        c1 = _contact(s, "c1", "stranger@new.com")
        row_id = s.list_unmatched()[0]["id"]
        res = link_unmatched(s, row_id, c1, "matthias", now_iso())
        assert res["ok"] and res["replay"]["inserted"]
        events = s.get_events(c1)
        assert len(events) == 1 and events[0]["type"] == "reply"
        assert s.list_unmatched() == []                 # no longer open
        linked = s.list_unmatched(status="linked")
        assert len(linked) == 1
        assert linked[0]["resolved_contact_id"] == c1
        assert linked[0]["resolved_by"] == "matthias"


def test_unmatched_never_autocreates_contact(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as s:
        ingest_event(s, {"email": "stranger@new.com", "type": "reply",
                         "occurred_at": "2026-07-14T08:00:00+00:00"})
        assert s.count_contacts() == 0                  # queueing created nothing
        row_id = s.list_unmatched()[0]["id"]
        # linking to a contact that does not exist refuses; still no contact
        res = link_unmatched(s, row_id, "ghost", "matthias", now_iso())
        assert res["ok"] is False
        assert s.count_contacts() == 0
        assert s.list_unmatched()[0]["status"] == "open"


# -- 3. v11 migration ----------------------------------------------------------

V11_TABLES = {"unmatched_events", "suppression_entries", "truth_runs", "folder_cache"}


def _tables(store) -> set[str]:
    return {r["name"] for r in store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}


def test_migration_v11_from_v10(tmp_path):
    db = tmp_path / "t.sqlite"
    with ContactStore(db) as store:                     # fresh DB runs 1..11
        assert SCHEMA_VERSION == 11
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == 11
        assert V11_TABLES <= _tables(store)
    # simulate a v10 prod DB: new tables absent, user_version rolled to 10
    raw = sqlite3.connect(db)
    raw.executescript(
        "DROP TABLE unmatched_events;"
        "DROP TABLE suppression_entries;"
        "DROP TABLE truth_runs;"
        "DROP TABLE folder_cache;"
        "PRAGMA user_version = 10;"
    )
    raw.commit()
    raw.close()
    with ContactStore(db) as store:                     # next open applies v11
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == 11
        assert V11_TABLES <= _tables(store)
    with ContactStore(db) as store:                     # second open is a no-op
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == 11
        assert V11_TABLES <= _tables(store)
