"""P0: the user_version-gated migration runner creates and refreshes the
derived views, so a definition change reaches an already-deployed prod DB."""
from __future__ import annotations

import sqlite3

from lead_desk.web.store import SCHEMA_VERSION, ContactStore

NOW = "2026-07-15T00:00:00+00:00"


def _views(store: ContactStore) -> set[str]:
    return {r["name"] for r in store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view'").fetchall()}


def test_fresh_db_reaches_schema_version_with_all_views(tmp_path):
    with ContactStore(tmp_path / "t.sqlite") as store:
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert _views(store) == {"contact_activity", "contact_stage", "enrollment_progress"}


def test_outreach_status_column_added(tmp_path):
    # v2 migration adds the sheet-status display column; upsert + read round-trips.
    with ContactStore(tmp_path / "t.sqlite") as store:
        cols = {r[1] for r in store.conn.execute("PRAGMA table_info(contacts)").fetchall()}
        assert "outreach_status" in cols
        store.upsert_contact({"contact_id": "c1", "natural_key": "a@x.com",
                              "email": "a@x.com", "outreach_status": "In conversation"},
                             now=NOW)
        assert store.get_contact("c1")["outreach_status"] == "In conversation"


def test_views_derive_stage(tmp_path):
    # Exercises contact_stage + contact_activity end to end.
    with ContactStore(tmp_path / "t.sqlite") as store:
        store.upsert_contact(
            {"contact_id": "c1", "natural_key": "a@x.com", "email": "a@x.com"}, now=NOW)
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="inbound", type="reply", now=NOW)
        rows = store.board_rows()
        assert rows[0]["stage"] == "replied"


def test_reopen_is_a_noop(tmp_path):
    db = tmp_path / "t.sqlite"
    with ContactStore(db):
        pass
    with ContactStore(db) as store:  # second open must not re-migrate or error
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert _views(store) == {"contact_activity", "contact_stage", "enrollment_progress"}


def test_frozen_legacy_view_is_refreshed(tmp_path):
    """The whole point of P0: a prod DB whose view was frozen by the old
    CREATE VIEW IF NOT EXISTS bootstrap (user_version still 0) gets the real
    definition on the next open."""
    db = tmp_path / "t.sqlite"
    with ContactStore(db):
        pass
    raw = sqlite3.connect(db)
    raw.executescript(
        "DROP VIEW contact_stage;"
        "CREATE VIEW contact_stage AS SELECT contact_id, 'FROZEN' AS stage FROM contacts;"
        "PRAGMA user_version = 0;"
    )
    raw.commit()
    raw.close()
    with ContactStore(db) as store:
        store.upsert_contact(
            {"contact_id": "c1", "natural_key": "a@x.com", "email": "a@x.com"}, now=NOW)
        store.add_event(contact_id="c1", ts=NOW, channel="email",
                        direction="inbound", type="reply", now=NOW)
        assert store.board_rows()[0]["stage"] == "replied"  # not 'FROZEN'
        assert store.conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
