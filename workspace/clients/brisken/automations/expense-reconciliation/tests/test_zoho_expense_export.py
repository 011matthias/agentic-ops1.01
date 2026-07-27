"""Phase 3 (receipt-first): the Zoho Books "Expenses" import CSV builder —
one row per expense, statement-free. CI-safe (no API key)."""
from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal

import pytest

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)
from expense_recon.output.zoho_expense_export import (
    EXPENSE_COLUMNS,
    build_expense_rows,
    write_zoho_expense_export,
)


def _cat(category, account):
    return Categorization(
        category=category, zoho_account=account, confidence=0.9,
        source=ClassificationSource.LINE,
    )


def _receipt(doc="r1", vendor="Uber", total="24.50", currency="USD",
             items=None, entity="corp-services", **kw):
    return Receipt(
        document_id=doc, legal_entity_id=entity,
        detected_date=date(2026, 6, 2), detected_total=Decimal(total),
        detected_currency=currency, detected_vendor=vendor,
        line_items=tuple(items or ()), **kw,
    )


def _row(row):
    return dict(zip(EXPENSE_COLUMNS, row))


def test_one_categorized_expense_is_one_row():
    r = _receipt(items=[LineItem(
        "Uber trip", Decimal("24.50"),
        categorization=_cat("Travel & Transport", "E100010 - Travel Expense"),
    )])
    rows = build_expense_rows([r], default_paid_through="Chase Checking")
    assert len(rows) == 1
    row = _row(rows[0])
    assert row["Expense Date"] == "2026-06-02"
    assert row["Expense Account"] == "E100010 - Travel Expense"
    assert row["Amount"] == "24.50"
    assert row["Currency Code"] == "USD"
    assert row["Paid Through"] == "Chase Checking"
    assert row["Vendor Name"] == "Uber"
    assert row["Reference Number"] == "r1"  # falls back to document_id
    assert row["Legal Entity"] == "corp-services"


def test_uncategorized_expense_flags_account_and_paid_through():
    r = _receipt(items=[])  # no itemization, no default paid-through
    rows = build_expense_rows([r])
    row = _row(rows[0])
    # never guessed: both flagged for assignment (B4)
    assert row["Expense Account"] == "(uncategorized - assign)"
    assert row["Paid Through"] == "(paid-through - assign)"
    assert row["Amount"] == "24.50"


def test_paid_through_override_beats_default():
    rows = build_expense_rows(
        [_receipt()], default_paid_through="Default Bank",
        paid_through_by_doc={"r1": "Amex 1234"},
    )
    assert _row(rows[0])["Paid Through"] == "Amex 1234"


def test_reimbursable_disposition_redirects_paid_through():
    rows = build_expense_rows(
        [_receipt()], default_paid_through="Card",
        dispositions={"r1": "reimbursable_personal"},
        reimbursable_account="Owed to Employee",
    )
    assert _row(rows[0])["Paid Through"] == "Owed to Employee"


@pytest.mark.parametrize("disp", ["do_not_export", "personal_on_business_card"])
def test_withheld_disposition_emits_no_row(disp):
    assert build_expense_rows([_receipt()], dispositions={"r1": disp}) == []


def test_multi_account_receipt_splits_shares_ref_and_taxes_once():
    items = [
        LineItem("Hotel", Decimal("80.00"),
                 categorization=_cat("Travel & Transport", "Travel Acct")),
        LineItem("Dinner", Decimal("20.00"),
                 categorization=_cat("Meals & Entertainment", "Meals Acct")),
    ]
    r = _receipt(total="100.00", items=items,
                 detected_tax=Decimal("9.00"), tax_label="VAT")
    rows = build_expense_rows([r])
    assert len(rows) == 2
    by = {_row(x)["Expense Account"]: _row(x) for x in rows}
    assert by["Travel Acct"]["Amount"] == "80.00"
    assert by["Meals Acct"]["Amount"] == "20.00"
    # allocation sums back to the receipt total
    assert Decimal(by["Travel Acct"]["Amount"]) + Decimal(by["Meals Acct"]["Amount"]) \
        == Decimal("100.00")
    # one Reference# across the split; tax on exactly one row (never doubled)
    assert {_row(x)["Reference Number"] for x in rows} == {"r1"}
    tax_amounts = [_row(x)["Tax Amount"] for x in rows]
    assert tax_amounts.count("9.00") == 1 and tax_amounts.count("") == 1


def test_tax_currency_and_exchange_rate_columns():
    r = _receipt(currency="eur", detected_tax=Decimal("3.80"), tax_label="VAT",
                 exchange_rate=Decimal("1.08"),
                 items=[LineItem("Lunch", Decimal("24.50"),
                        categorization=_cat("Meals & Entertainment", "Meals"))])
    row = _row(build_expense_rows([r])[0])
    assert row["Currency Code"] == "EUR"   # normalized upper
    assert row["Tax Name"] == "VAT"
    assert row["Tax Amount"] == "3.80"
    assert row["Exchange Rate"] == "1.08"


def test_write_csv_has_header_and_rows(tmp_path):
    r = _receipt(items=[LineItem("Lunch", Decimal("24.50"),
                 categorization=_cat("Meals & Entertainment", "Meals"))])
    out = tmp_path / "expenses.csv"
    write_zoho_expense_export([r], out, default_paid_through="Bank")
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == EXPENSE_COLUMNS
    assert len(rows) == 2
    assert rows[1][EXPENSE_COLUMNS.index("Amount")] == "24.50"


def test_generate_expenses_to_zoho_csv_end_to_end(tmp_path):
    """The receipt-first path: OCR folder -> expenses -> Zoho CSV, no statement."""
    from expense_recon.cli import generate_expenses
    from expense_recon.llm.client import (
        ExtractedLineItem,
        ExtractedReceipt,
        MockLLMClient,
    )

    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "uber.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-06-02", total="24.50", currency="USD", vendor="Uber",
        reference=None,
        line_items=(ExtractedLineItem("Uber trip downtown", "24.50"),),
        confidence=0.9, notes="",
    )])
    cfg = {
        "expense": {"legal_entity_id": "corp"},
        "receipts": {"path": "receipts", "default_currency": "USD"},
    }

    result = generate_expenses(cfg, tmp_path, llm_client=client)
    out = tmp_path / "out.csv"
    write_zoho_expense_export(result.receipts, out, default_paid_through="Bank")

    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == EXPENSE_COLUMNS
    assert len(rows) == 2
    data = _row(rows[1])
    assert data["Vendor Name"] == "Uber"
    assert data["Amount"] == "24.50"
    assert data["Expense Account"] == "Travel & Transport"  # mock categorized


def test_run_expense_mode_dispatch_writes_csv(tmp_path):
    """run() routes mode=expense_generation to the receipt-first branch and
    writes the Zoho Expenses CSV (csv receipts source: no LLM, CI-safe)."""
    from expense_recon.cli import run

    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor,detected_currency\n"
        "r1,2026-06-02,24.50,Uber,USD\n",
        encoding="utf-8",
    )
    cfg = {
        "mode": "expense_generation",
        "expense": {"legal_entity_id": "corp", "default_paid_through": "Bank"},
        "receipts": {"path": "receipts.csv", "source": "csv",
                     "default_currency": "USD"},
        "output": {"expenses_csv": "expenses.csv"},
    }
    (tmp_path / "run.json").write_text(json.dumps(cfg), encoding="utf-8")

    out = run(tmp_path / "run.json")

    assert out is not None and out.name == "expenses.csv"
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == EXPENSE_COLUMNS
    assert len(rows) == 2
    data = _row(rows[1])
    assert data["Vendor Name"] == "Uber"
    assert data["Amount"] == "24.50"
    assert data["Paid Through"] == "Bank"
