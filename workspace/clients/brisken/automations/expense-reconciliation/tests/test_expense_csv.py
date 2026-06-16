"""Tests for the Zoho Expense CSV ingest adapter (BLUEPRINT 8.1).

Synthetic Zoho-Expense-shaped fixtures, written inline per test. The
exact real export headers are not pinned (no live export header has
been shared — owner-clarified 2026-06-12); the adapter is column-map
driven, so these tests exercise the mapping, not a fixed header set.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.ingest.expense_csv import (
    parse_expense_csv,
    parse_expense_csv_tolerant,
)
from expense_recon.ingest._common import StatementParseError
from expense_recon.ingest.statement_csv import parse_statement_csv
from expense_recon.matching.deterministic import match_month


# A Zoho-Expense-shaped export: report-grouped lines, a per-line id, a
# foreign-currency line, a receipt URL on one row and only a filename on
# another (the 8.1 design fork), and a blank trailing row.
ZOHO_HEADER = (
    "Expense Date,Amount,Merchant,Currency,Report Number,"
    "Reference,Expense ID,Receipt URL,Receipt Name"
)
ZOHO_ROWS = [
    "2026-03-28,233.64,Mega Center,USD,ER-00214,REF-1,EXP-9001,"
    "https://expense.zoho.com/r/9001,",
    "2026-04-26,16.12,Versailles Lisbon,USD,ER-00215,,EXP-9002,,versailles.jpg",
    "2026-05-02,408.54,casualfood Frankfurt,EUR,ER-00216,RT-3,EXP-9003,,",
    ",,,,,,,,",  # blank-ish trailing row (all fields empty) -> skipped
]

FULL_MAP = {
    "expense_date": "Expense Date",
    "amount": "Amount",
    "vendor": "Merchant",
    "currency": "Currency",
    "report_number": "Report Number",
    "reference": "Reference",
    "document_id": "Expense ID",
    "receipt_url": "Receipt URL",
    "receipt_name": "Receipt Name",
}


def _write(tmp_path: Path, header: str, rows: list[str], name: str = "expense.csv") -> Path:
    path = tmp_path / name
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def test_parses_zoho_style_export(tmp_path):
    """Happy path: 3 data rows -> 3 Receipts with fields mapped."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    receipts = parse_expense_csv(path, "brisken-us", FULL_MAP, default_currency="USD")

    assert len(receipts) == 3
    first = receipts[0]
    assert first.document_id == "EXP-9001"
    assert first.legal_entity_id == "brisken-us"
    assert first.detected_date == date(2026, 3, 28)
    assert isinstance(first.detected_total, Decimal)
    assert first.detected_total == Decimal("233.64")
    assert first.detected_vendor == "Mega Center"
    assert first.detected_currency == "USD"
    assert first.report_number == "ER-00214"
    assert first.detected_reference == "REF-1"
    # line_items stays empty -> Tier-2 vendor-fallback categorization
    assert first.line_items == ()


def test_per_row_currency_overrides_default(tmp_path):
    """A row's mapped currency wins; the default fills the rest."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    receipts = parse_expense_csv(path, "brisken-us", FULL_MAP, default_currency="USD")
    by_id = {r.document_id: r for r in receipts}
    assert by_id["EXP-9003"].detected_currency == "EUR"  # foreign line
    assert by_id["EXP-9001"].detected_currency == "USD"


def test_default_currency_when_no_currency_column(tmp_path):
    """With no currency in the map, every receipt takes the default."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    no_cur_map = {k: v for k, v in FULL_MAP.items() if k != "currency"}
    receipts = parse_expense_csv(path, "brisken-us", no_cur_map, default_currency="USD")
    assert {r.detected_currency for r in receipts} == {"USD"}


def test_receipt_url_fork_carries_url(tmp_path):
    """Design fork side A: a row with a URL populates receipt_url and
    leaves receipt_name None."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    receipts = parse_expense_csv(path, "brisken-us", FULL_MAP, default_currency="USD")
    by_id = {r.document_id: r for r in receipts}
    assert by_id["EXP-9001"].receipt_url == "https://expense.zoho.com/r/9001"
    assert by_id["EXP-9001"].receipt_name is None


def test_receipt_name_fallback_when_no_url(tmp_path):
    """Design fork side B: a row with only a filename populates
    receipt_name and leaves receipt_url None (8.4 resolves it later)."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    receipts = parse_expense_csv(path, "brisken-us", FULL_MAP, default_currency="USD")
    by_id = {r.document_id: r for r in receipts}
    assert by_id["EXP-9002"].receipt_name == "versailles.jpg"
    assert by_id["EXP-9002"].receipt_url is None


def test_document_id_synthesized_from_report_and_row(tmp_path):
    """With no document_id mapped, the id is '<report>:<row>' and stays
    unique per row."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    no_id_map = {k: v for k, v in FULL_MAP.items() if k != "document_id"}
    receipts = parse_expense_csv(path, "brisken-us", no_id_map, default_currency="USD")
    ids = [r.document_id for r in receipts]
    assert ids == ["ER-00214:2", "ER-00215:3", "ER-00216:4"]


def test_synthesized_id_without_report_uses_exp_prefix(tmp_path):
    """No document_id and no report_number -> 'EXP:<row>' fallback."""
    header = "Expense Date,Amount,Merchant"
    rows = ["2026-03-01,10.00,A", "2026-03-02,20.00,B"]
    path = _write(tmp_path, header, rows)
    minimal_map = {"expense_date": "Expense Date", "amount": "Amount", "vendor": "Merchant"}
    receipts = parse_expense_csv(path, "brisken-us", minimal_map)
    assert [r.document_id for r in receipts] == ["EXP:2", "EXP:3"]


def test_column_map_missing_required_key_raises(tmp_path):
    """vendor is required; omitting it fails early (header-level)."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    bad_map = {"expense_date": "Expense Date", "amount": "Amount"}  # no vendor
    with pytest.raises(StatementParseError) as exc:
        parse_expense_csv(path, "brisken-us", bad_map)
    assert "vendor" in str(exc.value)


def test_csv_missing_mapped_column_raises(tmp_path):
    """A map pointing at an absent column fails with the name visible."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    bad_map = {**FULL_MAP, "amount": "NotAColumn"}
    with pytest.raises(StatementParseError) as exc:
        parse_expense_csv(path, "brisken-us", bad_map)
    assert "NotAColumn" in str(exc.value)


def test_no_header_raises(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(StatementParseError):
        parse_expense_csv(path, "brisken-us", FULL_MAP)


def test_bad_amount_is_row_issue_not_fatal(tmp_path):
    """Tolerant mode collects a row-level bad amount and keeps the rest;
    the issue carries the 1-indexed line number."""
    rows = [
        "2026-03-01,10.00,Good,USD,ER-1,,EXP-1,,",
        "2026-03-02,NOT_A_NUMBER,Bad,USD,ER-1,,EXP-2,,",
        "2026-03-03,30.00,AlsoGood,USD,ER-1,,EXP-3,,",
    ]
    path = _write(tmp_path, ZOHO_HEADER, rows)
    receipts, issues = parse_expense_csv_tolerant(
        path, "brisken-us", FULL_MAP, default_currency="USD"
    )
    assert [r.document_id for r in receipts] == ["EXP-1", "EXP-3"]
    assert len(issues) == 1
    assert issues[0].line_number == 3
    assert issues[0].file_name == "expense.csv"


def test_duplicate_document_id_is_row_issue(tmp_path):
    """A repeated mapped document_id is a row-level issue; the first
    instance survives, the duplicate is flagged with both rows."""
    rows = [
        "2026-03-01,10.00,A,USD,ER-1,,EXP-DUP,,",
        "2026-03-02,20.00,B,USD,ER-1,,EXP-DUP,,",
    ]
    path = _write(tmp_path, ZOHO_HEADER, rows)
    receipts, issues = parse_expense_csv_tolerant(
        path, "brisken-us", FULL_MAP, default_currency="USD"
    )
    assert [r.document_id for r in receipts] == ["EXP-DUP"]
    assert len(issues) == 1
    assert "duplicate" in issues[0].message


def test_blank_trailing_row_skipped(tmp_path):
    """The all-empty trailing row in the fixture does not become a
    receipt or an issue."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)
    receipts, issues = parse_expense_csv_tolerant(
        path, "brisken-us", FULL_MAP, default_currency="USD"
    )
    assert len(receipts) == 3
    assert issues == []


def test_parsed_receipt_is_matcher_ready(tmp_path):
    """End-to-end: an expense line and an identical statement charge
    reconcile through match_month, and the receipt is never dropped
    (reconciliation guarantee)."""
    exp_path = _write(
        tmp_path,
        ZOHO_HEADER,
        ["2026-04-07,180.00,Amazon,USD,ER-9,,EXP-A,,"],
        name="expense.csv",
    )
    receipts = parse_expense_csv(exp_path, "brisken-us", FULL_MAP, default_currency="USD")

    stmt_path = tmp_path / "statement.csv"
    stmt_path.write_text(
        "Date,Amount,Description\n2026-04-07,180.00,Amazon\n", encoding="utf-8"
    )
    txs = parse_statement_csv(
        stmt_path,
        column_map={"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        account_id="amex-usd",
        legal_entity_id="brisken-us",
        account_card_currency="USD",
    )

    outcome = match_month(txs, receipts)
    bound = {m.document_id for m in outcome.matches}
    assert "EXP-A" in bound  # confident pairing on identical date/amount/vendor
    # reconciliation guarantee: nothing silently dropped
    assert "EXP-A" not in outcome.unmatched_receipts


# --------------------------------------------------------------------------
# Full Zoho Expense report fields (2026-06-16): payment mode, paid through,
# GL category, FX rate, book amount, reimbursable flag, location. Shapes from
# ER-00214 so the tool's data holds the same information as the report.
# --------------------------------------------------------------------------

ZOHO_FULL_HEADER = (
    "Expense Date,Amount,Merchant,Currency,Report Number,Reference,Expense ID,"
    "Receipt URL,Receipt Name,Payment Mode,Paid Through,Category,"
    "Exchange Rate,Amount (USD),Reimbursable,Expense Location"
)
ZOHO_FULL_ROW = (
    '2026-03-14,3099.99,MAGAZINE LUIZA S/A,BRL,ER-00214,795234,EXP-1,,,'
    '1 - CorpServ 2838/1672 (Chase),ZZZ | Cash In Hand | DO NOT USE 2,'
    'E100010 - Travel Expense,0.187586,581.51,Non Reimbursable,"Recife, Brazil"'
)
ZOHO_FULL_MAP = {
    "expense_date": "Expense Date", "amount": "Amount", "vendor": "Merchant",
    "currency": "Currency", "report_number": "Report Number", "reference": "Reference",
    "document_id": "Expense ID", "receipt_url": "Receipt URL", "receipt_name": "Receipt Name",
    "payment_mode": "Payment Mode", "paid_through": "Paid Through", "category": "Category",
    "exchange_rate": "Exchange Rate", "amount_base": "Amount (USD)",
    "reimbursable": "Reimbursable", "location": "Expense Location",
}


def test_parses_full_zoho_report_fields(tmp_path):
    path = _write(tmp_path, ZOHO_FULL_HEADER, [ZOHO_FULL_ROW])
    r = parse_expense_csv(path, "brisken-us", ZOHO_FULL_MAP)[0]
    assert r.payment_mode == "1 - CorpServ 2838/1672 (Chase)"
    assert r.paid_through == "ZZZ | Cash In Hand | DO NOT USE 2"
    assert r.zoho_category == "E100010 - Travel Expense"
    assert r.exchange_rate == Decimal("0.187586")
    assert r.base_amount == Decimal("581.51")
    assert r.reimbursable is False
    assert r.expense_location == "Recife, Brazil"
    assert r.detected_currency == "BRL"
    assert r.detected_total == Decimal("3099.99")


def test_absent_optional_column_is_skipped_not_fatal(tmp_path):
    """The default map lists Payment Mode etc.; an export lacking those
    columns must ingest cleanly (lenient optional), only present fields fill."""
    path = _write(tmp_path, ZOHO_HEADER, ZOHO_ROWS)  # no Payment Mode / Category
    receipts = parse_expense_csv(
        path,
        "brisken-us",
        {**FULL_MAP, "payment_mode": "Payment Mode",
         "category": "Category", "reimbursable": "Reimbursable"},
        default_currency="USD",
    )
    assert len(receipts) == 3
    assert receipts[0].payment_mode is None
    assert receipts[0].zoho_category is None
    assert receipts[0].reimbursable is None


def test_reimbursable_flag_parsing(tmp_path):
    header = "Expense Date,Amount,Merchant,Reimbursable"
    rows = [
        "2026-03-01,10.00,A,Reimbursable",
        "2026-03-02,20.00,B,Non Reimbursable",
        "2026-03-03,30.00,C,",
    ]
    path = _write(tmp_path, header, rows)
    m = {
        "expense_date": "Expense Date", "amount": "Amount",
        "vendor": "Merchant", "reimbursable": "Reimbursable",
    }
    receipts = parse_expense_csv(path, "brisken-us", m)
    assert [r.reimbursable for r in receipts] == [True, False, None]


def test_zoho_category_carried_as_posting_account():
    """categorize_receipts carries the Zoho GL category onto the line's
    zoho_account (the posting account); the AI/keyword category is the verify
    pass left alongside it."""
    from expense_recon.categorize import categorize_receipts
    from expense_recon.matching.types import Receipt

    r = Receipt(
        document_id="EXP-1", legal_entity_id="brisken-us",
        detected_date=date(2026, 3, 14), detected_total=Decimal("581.51"),
        detected_currency="USD", detected_vendor="MAGAZINE LUIZA",
        zoho_category="E100010 - Travel Expense",
    )
    out = categorize_receipts([r])  # no client -> keyword stub
    cat = out[0].line_items[0].categorization
    assert cat is not None
    assert cat.zoho_account == "E100010 - Travel Expense"
