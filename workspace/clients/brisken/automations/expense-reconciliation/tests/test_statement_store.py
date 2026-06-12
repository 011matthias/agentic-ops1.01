"""BLUEPRINT 8.2 — bank-statement table + dedup. All offline."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.matching.types import Transaction
from expense_recon.store import (
    IngestResult,
    StatementConflictError,
    StatementStore,
    fingerprint,
)


def _tx(
    row: int,
    *,
    account_id: str = "0340",
    txdate: str = "2026-01-05",
    posting: str | None = None,
    amount: str = "50.00",
    currency: str = "USD",
    vendor: str = "STARBUCKS",
) -> Transaction:
    return Transaction(
        transaction_id=f"{account_id}:{row}",
        legal_entity_id="brisken-llc",
        account_id=account_id,
        transaction_date=date.fromisoformat(txdate),
        posting_date=date.fromisoformat(posting) if posting else None,
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement=vendor,
        raw_text=f"row{row}",
    )


# ── fingerprint ─────────────────────────────────────────────────────


def test_fingerprint_stable_across_row_index_and_amount_formatting():
    # Same charge, different parser row index AND different amount
    # formatting -> identical fingerprint (dedup survives re-export).
    a = _tx(2, amount="50")
    b = _tx(99, amount="50.00")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_differs_on_real_field_changes():
    base = _tx(1)
    assert fingerprint(base) != fingerprint(_tx(1, amount="51.00"))
    assert fingerprint(base) != fingerprint(_tx(1, txdate="2026-01-06"))
    assert fingerprint(base) != fingerprint(_tx(1, vendor="PEETS"))
    assert fingerprint(base) != fingerprint(_tx(1, account_id="3645"))


def test_fingerprint_preserves_sign_refund_vs_charge():
    # A -50 refund must not collapse into the +50 charge.
    assert fingerprint(_tx(1, amount="50.00")) != fingerprint(_tx(1, amount="-50.00"))


# ── ingest + dedup ──────────────────────────────────────────────────


def test_fresh_ingest_counts_all_new(tmp_path):
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        res = store.ingest_transactions(
            [_tx(2), _tx(3, amount="12.00"), _tx(4, amount="9.50")],
            statement_id="chase-0340-2026-01",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        assert res == IngestResult("chase-0340-2026-01", inserted=3, duplicates=0)
        assert res.total == 3
        assert store.count() == 3


def test_reingest_identical_batch_is_idempotent(tmp_path):
    db = tmp_path / "stmt.sqlite"
    txs = [_tx(2), _tx(3, amount="12.00")]
    with StatementStore(db) as store:
        store.ingest_transactions(txs, statement_id="s1", ingested_at="2026-06-12T00:00:00+00:00")
        # Same id, same content (rows reordered) -> no new rows, no error.
        res = store.ingest_transactions(
            list(reversed(txs)), statement_id="s1", ingested_at="2026-06-12T01:00:00+00:00"
        )
        assert res.inserted == 0
        assert res.duplicates == 2
        assert store.count() == 2
        assert len(store.batches()) == 1  # still one batch row


def test_overlapping_periods_dedup_globally(tmp_path):
    # Jan and the historic export both contain the same two Jan charges;
    # the historic export adds one more. Dedup is global by fingerprint.
    db = tmp_path / "stmt.sqlite"
    jan = [_tx(2, txdate="2026-01-05"), _tx(3, txdate="2026-01-09", amount="12.00")]
    historic = jan + [_tx(4, txdate="2026-02-01", amount="80.00")]
    with StatementStore(db) as store:
        store.ingest_transactions(jan, statement_id="jan", ingested_at="2026-06-12T00:00:00+00:00")
        res = store.ingest_transactions(
            historic, statement_id="historic", ingested_at="2026-06-12T02:00:00+00:00"
        )
        assert res.inserted == 1  # only the Feb charge is new
        assert res.duplicates == 2
        assert store.count() == 3  # union, each counted once


# ── statement-number validation ─────────────────────────────────────


def test_same_id_changed_content_conflicts(tmp_path):
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        store.ingest_transactions([_tx(2)], statement_id="s1", ingested_at="2026-06-12T00:00:00+00:00")
        with pytest.raises(StatementConflictError):
            store.ingest_transactions(
                [_tx(2), _tx(3, amount="99.00")],
                statement_id="s1",
                ingested_at="2026-06-12T01:00:00+00:00",
            )
        # The rejected batch left no partial state.
        assert store.count() == 1


def test_replace_true_updates_batch_and_adds_new_tx(tmp_path):
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        store.ingest_transactions([_tx(2)], statement_id="s1", ingested_at="2026-06-12T00:00:00+00:00")
        res = store.ingest_transactions(
            [_tx(2), _tx(3, amount="99.00")],
            statement_id="s1",
            ingested_at="2026-06-12T03:00:00+00:00",
            replace=True,
        )
        assert res.inserted == 1  # the new charge; the unchanged one is a dup
        assert store.count() == 2
        batch = store.get_batch("s1")
        assert batch.n_transactions == 2
        assert batch.ingested_at == "2026-06-12T03:00:00+00:00"


# ── reconstruction + provenance ─────────────────────────────────────


def test_transactions_roundtrip_with_stable_unique_id(tmp_path):
    db = tmp_path / "stmt.sqlite"
    src = _tx(2, amount="50.00", posting="2026-01-06", currency="USD", vendor="STARBUCKS")
    with StatementStore(db) as store:
        store.ingest_transactions([src], statement_id="s1", ingested_at="2026-06-12T00:00:00+00:00")
        out = store.transactions()
        assert len(out) == 1
        got = out[0]
        assert got.amount == Decimal("50.00")
        assert got.transaction_date == date(2026, 1, 5)
        assert got.posting_date == date(2026, 1, 6)
        assert got.account_card_currency == "USD"
        assert got.vendor_from_statement == "STARBUCKS"
        # Reconstructed id is account-prefixed and stable across reads.
        assert got.transaction_id.startswith("0340:")
        assert store.transactions()[0].transaction_id == got.transaction_id


def test_transactions_filter_by_account(tmp_path):
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        store.ingest_transactions(
            [_tx(2, account_id="0340"), _tx(3, account_id="3645", amount="20.00")],
            statement_id="mixed",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        assert store.count() == 2
        assert store.count("0340") == 1
        assert {t.account_id for t in store.transactions("3645")} == {"3645"}


def test_multi_account_batch_records_null_batch_account(tmp_path):
    # The Chase export carries 6 cards in one file -> batch account is
    # ambiguous (None), but each transaction keeps its own account_id.
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        store.ingest_transactions(
            [_tx(2, account_id="0340"), _tx(3, account_id="3645", amount="20.00")],
            statement_id="chase-multi",
            source_path="Chase2838_historic_Activity.xlsx",
            ingested_at="2026-06-12T00:00:00+00:00",
        )
        batch = store.get_batch("chase-multi")
        assert batch.account_id is None
        assert batch.source_path == "Chase2838_historic_Activity.xlsx"
        assert batch.period_start == "2026-01-05"
        assert batch.period_end == "2026-01-05"


def test_persists_across_reopen(tmp_path):
    db = tmp_path / "stmt.sqlite"
    with StatementStore(db) as store:
        store.ingest_transactions([_tx(2)], statement_id="s1", ingested_at="2026-06-12T00:00:00+00:00")
    # Reopen: the table survives (the source-of-truth-that-outlives-Zoho property).
    with StatementStore(db) as store:
        assert store.count() == 1
        assert len(store.transactions()) == 1
