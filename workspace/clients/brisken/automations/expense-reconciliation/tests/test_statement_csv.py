"""Tests for the CSV statement parser.

Synthetic Amex-shaped fixture only for this first session. Real
Brisken-month fixtures land when Chris provides a representative
month (see ../README.md "Data we need from Chris").
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.ingest.statement_csv import (
    StatementParseError,
    parse_statement_csv,
)
from expense_recon.matching.deterministic import match_month
from expense_recon.matching.types import MatchType, Receipt


FIXTURE = Path(__file__).parent / "fixtures" / "sample_amex_export.csv"

DEFAULT_MAP = {
    "transaction_date": "Date",
    "amount": "Amount",
    "vendor": "Description",
}


def test_parses_well_formed_csv():
    """Happy path: 7 data rows -> 7 Transactions; types correct."""
    txs = parse_statement_csv(
        FIXTURE,
        column_map=DEFAULT_MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    assert len(txs) == 7
    first = txs[0]
    assert first.transaction_date == date(2026, 4, 1)
    assert isinstance(first.amount, Decimal)
    assert first.amount == Decimal("5.75")
    assert first.account_card_currency == "USD"
    assert first.transaction_currency == "USD"
    assert first.legal_entity_id == "brisken-us"
    assert first.posting_date is None  # not in this fixture
    assert first.vendor_from_statement == "COFFEE SHOP NYC"


def test_column_map_missing_required_key_raises():
    """Vendor is a required key; omitting it must fail early."""
    bad_map = {"transaction_date": "Date", "amount": "Amount"}  # no vendor
    with pytest.raises(StatementParseError) as exc:
        parse_statement_csv(
            FIXTURE,
            column_map=bad_map,
            account_id="x",
            legal_entity_id="x",
            account_card_currency="USD",
        )
    assert "vendor" in str(exc.value)


def test_csv_missing_mapped_column_raises():
    """If the CSV doesn't have a column the map points at, fail
    with the column name visible to the caller."""
    bad_map = {**DEFAULT_MAP, "amount": "TotallyNotAColumn"}
    with pytest.raises(StatementParseError) as exc:
        parse_statement_csv(
            FIXTURE,
            column_map=bad_map,
            account_id="x",
            legal_entity_id="x",
            account_card_currency="USD",
        )
    assert "TotallyNotAColumn" in str(exc.value)


def test_negative_amount_and_whitespace_preserved_correctly():
    """Refund row has negative amount; description has leading +
    trailing whitespace that should be stripped."""
    txs = parse_statement_csv(
        FIXTURE,
        column_map=DEFAULT_MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    refund = next(t for t in txs if t.amount < 0)
    assert refund.amount == Decimal("-15.00")
    assert refund.vendor_from_statement == "AMAZON RETURN"


def test_malformed_amount_raises_with_line_number(tmp_path):
    """Reconciliation-guarantee posture (v2 spec §25.5): never
    silently drop a row. Surface the offending line number."""
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "Date,Description,Amount\n"
        "04/01/2026,COFFEE,5.75\n"
        "04/02/2026,RESTAURANT,not-a-number\n",
        encoding="utf-8",
    )
    with pytest.raises(StatementParseError) as exc:
        parse_statement_csv(
            bad_csv,
            column_map=DEFAULT_MAP,
            account_id="x",
            legal_entity_id="x",
            account_card_currency="USD",
        )
    assert exc.value.line_number == 3  # header is line 1; second data row is line 3


def test_posting_date_optional_when_mapped(tmp_path):
    """Caller can map an optional posting_date column; blank cells
    yield posting_date=None on that row."""
    csv_text = (
        "Date,Post Date,Description,Amount\n"
        "04/01/2026,04/03/2026,COFFEE,5.75\n"
        "04/02/2026,,RESTAURANT,20.00\n"
    )
    src = tmp_path / "with_posting.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map={**DEFAULT_MAP, "posting_date": "Post Date"},
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    assert txs[0].posting_date == date(2026, 4, 3)
    assert txs[1].posting_date is None


def test_blank_rows_skipped(tmp_path):
    """Trailing blank rows at EOF (common in CSV exports) are
    ignored, not surfaced as errors."""
    csv_text = (
        "Date,Description,Amount\n"
        "04/01/2026,COFFEE,5.75\n"
        ",,\n"
        "04/02/2026,RESTAURANT,20.00\n"
    )
    src = tmp_path / "blanks.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map=DEFAULT_MAP,
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    assert len(txs) == 2


def test_accounting_style_negative_parses(tmp_path):
    """Some exports use `(50.00)` instead of `-50.00`. Accept both."""
    csv_text = (
        "Date,Description,Amount\n"
        "04/01/2026,REFUND,(50.00)\n"
    )
    src = tmp_path / "accounting_neg.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map=DEFAULT_MAP,
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    assert txs[0].amount == Decimal("-50.00")


def test_integration_parser_to_matcher_happy_path():
    """End-to-end: CSV -> Transaction list -> match_month with
    synthetic receipts. Both seeded receipts produce EXACT matches."""
    txs = parse_statement_csv(
        FIXTURE,
        column_map=DEFAULT_MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    receipts = [
        Receipt(
            document_id="r-coffee",
            legal_entity_id="brisken-us",
            detected_date=date(2026, 4, 1),
            detected_total=Decimal("5.75"),
            detected_currency="USD",
            detected_vendor="COFFEE SHOP",
        ),
        Receipt(
            document_id="r-staples",
            legal_entity_id="brisken-us",
            detected_date=date(2026, 4, 15),
            detected_total=Decimal("42.50"),
            detected_currency="USD",
            detected_vendor="STAPLES",
        ),
    ]
    outcome = match_month(txs, receipts)
    assert len(outcome.matches) == 2
    assert all(m.match_type == MatchType.EXACT for m in outcome.matches)
    # The other 5 transactions in the fixture remain unmatched
    # (no receipts seeded for them), preserving the reconciliation
    # guarantee invariant (v2 spec §25.5).
    assert len(outcome.unmatched_transactions) == 5
