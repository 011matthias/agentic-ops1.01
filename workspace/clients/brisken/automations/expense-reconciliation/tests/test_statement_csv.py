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
    # 3.10 / LD-5 A5: the fixture's negative row (the Amazon return) is a
    # credit — partitioned into its own refunds bucket, never left among
    # the unmatched purchases. Identified by which ROW it is rather than
    # by a literal id: ids are content-derived (PR 2a) and deliberately
    # carry no row number.
    by_id = {t.transaction_id: t for t in txs}
    assert len(outcome.refunds) == 1
    refunded = by_id[outcome.refunds[0]]
    assert refunded.source_row == 6
    assert refunded.amount < 0
    # The other 4 purchases in the fixture remain unmatched (no receipts
    # seeded for them), preserving the reconciliation guarantee invariant
    # (v2 spec §25.5): 2 matched + 4 unmatched + 1 refund = 7.
    assert len(outcome.unmatched_transactions) == 4


# ── 3.15 sign canonicalization ───────────────────────────────────────


TYPE_MAP = {**DEFAULT_MAP, "type": "Type"}


def test_type_column_canonicalizes_chase_activity_convention(tmp_path):
    """The Chase activity CSV prints purchases NEGATIVE (Type=Sale) and
    payments/returns positive. With a mapped Type column the sign is
    canonicalized per row: purchase = positive, credit = negative."""
    csv_text = (
        "Date,Description,Amount,Type\n"
        "04/01/2026,UBER TRIP,-10.32,Sale\n"
        "04/02/2026,PAYMENT THANK YOU,4000.00,Payment\n"
        "04/03/2026,AMAZON RETURN,15.00,Return\n"
    )
    src = tmp_path / "chase_activity.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map=TYPE_MAP,
        account_id="chase-2838",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    sale, payment, ret = txs
    assert sale.amount == Decimal("10.32") and not sale.is_credit
    assert payment.amount == Decimal("-4000.00") and payment.is_credit
    assert ret.amount == Decimal("-15.00") and ret.is_credit


def test_no_type_column_majority_negative_flips_with_warning(tmp_path):
    """Without a Type column, a majority-negative export is inferred to
    print purchases as negatives; all signs flip and a warning issue is
    emitted (never a silent flip)."""
    from expense_recon.ingest.statement_csv import parse_statement_csv_tolerant

    rows = "\n".join(
        f"04/{i:02d}/2026,VENDOR {i},-{i}.00" for i in range(1, 6)
    )
    csv_text = f"Date,Description,Amount\n{rows}\n04/09/2026,PAYMENT,500.00\n"
    src = tmp_path / "inverted.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs, issues = parse_statement_csv_tolerant(
        src,
        column_map=DEFAULT_MAP,
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    warnings = [i for i in issues if i.severity == "warning"]
    assert len(warnings) == 1 and "sign convention inferred" in warnings[0].message
    assert [t.amount for t in txs[:5]] == [Decimal(f"{i}.00") for i in range(1, 6)]
    assert all(not t.is_credit for t in txs[:5])
    payment = txs[5]
    assert payment.amount == Decimal("-500.00") and payment.is_credit


def test_no_type_column_canonical_file_untouched_but_credit_flagged():
    """A majority-positive export keeps its signs verbatim; the lone
    negative row (the Amazon return in the fixture) gets is_credit."""
    txs = parse_statement_csv(
        FIXTURE,
        column_map=DEFAULT_MAP,
        account_id="brisken-amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )
    credits = [t for t in txs if t.is_credit]
    assert [t.amount for t in credits] == [
        t.amount for t in txs if t.amount < 0
    ]
    assert all(not t.is_credit for t in txs if t.amount > 0)


def test_tiny_export_with_lone_refund_not_flipped(tmp_path):
    """A small export holding only a refund or two must not trip the
    majority inference (>= 3 negatives required)."""
    csv_text = "Date,Description,Amount\n04/01/2026,REFUND,(50.00)\n"
    src = tmp_path / "lone_refund.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map=DEFAULT_MAP,
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    assert txs[0].amount == Decimal("-50.00")
    assert txs[0].is_credit


def test_card_column_maps_to_per_row_card(tmp_path):
    """WS3: a tabular export prints the card beside every charge while the
    account id names the whole account. Mapping the column is what gives
    the matcher a real per-charge card identity."""
    csv_text = (
        "Transaction Date,Post Date,Description,Amount,Card,Type\n"
        "04/29/2026,04/30/2026,ADOBE  *800-833-6687,16.23,3645,Sale\n"
        "05/04/2026,05/05/2026,RISTORANTE,17.50,2838,Sale\n"
        "05/04/2026,05/05/2026,NO CARD PRINTED,9.00,,Sale\n"
    )
    src = tmp_path / "activity.csv"
    src.write_text(csv_text, encoding="utf-8")

    txs = parse_statement_csv(
        src,
        column_map={
            "transaction_date": "Transaction Date",
            "posting_date": "Post Date",
            "amount": "Amount",
            "vendor": "Description",
            "card": "Card",
            "type": "Type",
        },
        account_id="chase-2838-family",
        legal_entity_id="brisken-corpserv",
        account_card_currency="USD",
    )

    assert [t.card_last4 for t in txs] == ["3645", "2838", None]
    # The account id (and therefore the transaction id, which the store and
    # the reviewer's dispositions key on) is untouched by the card column.
    assert {t.account_id for t in txs} == {"chase-2838-family"}


def test_card_column_absent_leaves_card_unset(tmp_path):
    """An export with no card column parses exactly as before."""
    csv_text = "Date,Description,Amount\n04/01/2026,COFFEE,4.50\n"
    src = tmp_path / "no_card.csv"
    src.write_text(csv_text, encoding="utf-8")
    txs = parse_statement_csv(
        src,
        column_map=DEFAULT_MAP,
        account_id="x",
        legal_entity_id="x",
        account_card_currency="USD",
    )
    assert txs[0].card_last4 is None
