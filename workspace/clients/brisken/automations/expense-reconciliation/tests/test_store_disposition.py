"""§17 disposition storage: upsert orthogonality + in-place migration.

The disposition verdict and the triage status share the `decisions` row
(grain `(run_id, transaction_id)`) but are independent layers: setting one
must never clobber the other. These cover that orthogonality both ways,
plus the idempotent `_migrate` ALTER on a database created before the
column existed (the live Fly `/data` volume upgrade path).
"""
from __future__ import annotations

import sqlite3

import pytest

from expense_recon.web.store import (
    DISPOSITION_DO_NOT_EXPORT,
    DISPOSITION_PERSONAL,
    DISPOSITION_REIMBURSABLE,
    STATUS_CONFIRMED,
    STATUS_PENDING,
    RunStore,
)


def _store(tmp_path) -> RunStore:
    return RunStore(tmp_path / "recon-web.sqlite")


def test_set_disposition_seeds_pending_status(tmp_path):
    with _store(tmp_path) as store:
        store.set_disposition("run1", "t1", DISPOSITION_PERSONAL, "2026-07-20T00:00:00")
        d = store.get_decisions("run1")["t1"]
    assert d.disposition == DISPOSITION_PERSONAL
    # A fresh row (no prior triage verdict) seeds status=pending.
    assert d.status == STATUS_PENDING
    assert d.chosen_document_id is None


def test_disposition_then_decision_preserves_disposition(tmp_path):
    """set_decision must NOT clear a disposition set earlier."""
    with _store(tmp_path) as store:
        store.set_disposition("run1", "t1", DISPOSITION_REIMBURSABLE, "2026-07-20T00:00:00")
        store.set_decision("run1", "t1", STATUS_CONFIRMED, "rcpt-9", "2026-07-20T01:00:00")
        d = store.get_decisions("run1")["t1"]
    assert d.status == STATUS_CONFIRMED
    assert d.chosen_document_id == "rcpt-9"
    # The disposition survived the triage write (ON CONFLICT excludes it).
    assert d.disposition == DISPOSITION_REIMBURSABLE


def test_decision_then_disposition_preserves_status(tmp_path):
    """set_disposition must NOT clear the status / chosen document."""
    with _store(tmp_path) as store:
        store.set_decision("run1", "t1", STATUS_CONFIRMED, "rcpt-9", "2026-07-20T00:00:00")
        store.set_disposition("run1", "t1", DISPOSITION_DO_NOT_EXPORT, "2026-07-20T01:00:00")
        d = store.get_decisions("run1")["t1"]
    assert d.disposition == DISPOSITION_DO_NOT_EXPORT
    # The triage verdict survived the disposition write (ON CONFLICT lists
    # only disposition + updated_at).
    assert d.status == STATUS_CONFIRMED
    assert d.chosen_document_id == "rcpt-9"


def test_disposition_reassignment_updates_in_place(tmp_path):
    with _store(tmp_path) as store:
        store.set_disposition("run1", "t1", DISPOSITION_PERSONAL, "2026-07-20T00:00:00")
        store.set_disposition("run1", "t1", DISPOSITION_REIMBURSABLE, "2026-07-20T02:00:00")
        d = store.get_decisions("run1")["t1"]
    assert d.disposition == DISPOSITION_REIMBURSABLE


def test_invalid_disposition_rejected(tmp_path):
    with _store(tmp_path) as store:
        with pytest.raises(ValueError):
            store.set_disposition("run1", "t1", "not_a_disposition", "2026-07-20T00:00:00")


def test_migrate_adds_disposition_column_to_preexisting_db(tmp_path):
    """A `decisions` table created before §17 (no disposition column) gains
    the column idempotently when RunStore opens it, and the existing row's
    disposition reads as None (which the service seeds to business)."""
    db_path = tmp_path / "recon-web.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE decisions (
            run_id             TEXT NOT NULL,
            transaction_id     TEXT NOT NULL,
            status             TEXT NOT NULL,
            chosen_document_id TEXT,
            updated_at         TEXT,
            PRIMARY KEY (run_id, transaction_id)
        );
        INSERT INTO decisions (run_id, transaction_id, status, chosen_document_id, updated_at)
        VALUES ('run1', 't1', 'confirmed', 'rcpt-1', '2026-07-01T00:00:00');
        """
    )
    conn.commit()
    conn.close()

    # Opening the store runs _migrate; the column is added and reads NULL.
    with RunStore(db_path) as store:
        cols = {
            r["name"]
            for r in store.conn.execute("PRAGMA table_info(decisions)").fetchall()
        }
        assert "disposition" in cols
        d = store.get_decisions("run1")["t1"]
        assert d.status == "confirmed"
        assert d.disposition is None
        # And the migrated DB can now accept a disposition write.
        store.set_disposition("run1", "t1", DISPOSITION_PERSONAL, "2026-07-20T00:00:00")
        assert store.get_decisions("run1")["t1"].disposition == DISPOSITION_PERSONAL


def test_migrate_is_idempotent(tmp_path):
    """Opening an already-migrated DB a second time must not error."""
    db_path = tmp_path / "recon-web.sqlite"
    RunStore(db_path).close()
    # Second open re-runs _migrate; the ADD COLUMN is guarded by a lookup.
    with RunStore(db_path) as store:
        store.set_disposition("run1", "t1", DISPOSITION_PERSONAL, "2026-07-20T00:00:00")
        assert store.get_decisions("run1")["t1"].disposition == DISPOSITION_PERSONAL
