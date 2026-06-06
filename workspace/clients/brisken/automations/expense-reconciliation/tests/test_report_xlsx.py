"""Report-writer unit tests (E1) + the --explain sheet (A8)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from openpyxl import load_workbook

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.output.report_xlsx import write_report


def _categorized(desc, amount, category) -> LineItem:
    return LineItem(
        description=desc,
        line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.95,
            source=ClassificationSource.LINE, reasoning="test",
        ),
    )


def _matched_tx() -> Transaction:
    return Transaction(
        transaction_id="t1", legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("180"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )


def _unmatched_tx() -> Transaction:
    return Transaction(
        transaction_id="t2", legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 9), posting_date=None,
        amount=Decimal("42"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="MYSTERY LLC",
    )


def _receipt() -> Receipt:
    return Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        line_items=(
            _categorized("Herman Miller chair", "150", "Equipment & Hardware"),
            _categorized("Coffee beans 2kg", "30", "Office Supplies & Consumables"),
        ),
    )


def _outcome() -> MatchOutcome:
    return MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "exact", False)],
        unmatched_transactions=["t2"],
    )


def test_report_has_canonical_sheets(tmp_path):
    out = write_report(
        _outcome(), [_matched_tx(), _unmatched_tx()], [_receipt()],
        tmp_path / "report.xlsx",
        parse_errors=[("amex.csv", 5, "bad row")],
    )
    wb = load_workbook(out)
    assert "Summary" in wb.sheetnames
    assert "amex-usd" in wb.sheetnames          # per-card tab
    assert "Needs Review" in wb.sheetnames
    assert "Unmatched" in wb.sheetnames
    assert "Errors" in wb.sheetnames
    assert "Explain" not in wb.sheetnames        # not requested


def test_matched_lines_expand_to_one_row_each(tmp_path):
    out = write_report(_outcome(), [_matched_tx(), _unmatched_tx()], [_receipt()], tmp_path / "r.xlsx")
    ws = load_workbook(out)["amex-usd"]
    descriptions = [row[2] for row in ws.iter_rows(min_row=2, values_only=True) if row[2]]
    assert "Herman Miller chair" in descriptions
    assert "Coffee beans 2kg" in descriptions


def test_parse_errors_land_in_errors_sheet(tmp_path):
    out = write_report(
        _outcome(), [_matched_tx()], [_receipt()], tmp_path / "r.xlsx",
        parse_errors=[("amex.csv", 5, "unparseable amount")],
    )
    ws = load_workbook(out)["Errors"]
    cells = [c for row in ws.iter_rows(values_only=True) for c in row]
    assert "unparseable amount" in cells


def test_explain_sheet_present_only_when_requested(tmp_path):
    out = write_report(
        _outcome(), [_matched_tx(), _unmatched_tx()], [_receipt()],
        tmp_path / "r.xlsx", explain=True,
    )
    wb = load_workbook(out)
    assert "Explain" in wb.sheetnames
    ws = wb["Explain"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    by_tx = {r[2]: r[5] for r in rows}  # vendor -> Outcome
    assert by_tx["AMAZON"] == "MATCHED"
    assert by_tx["MYSTERY LLC"] == "UNMATCHED"
