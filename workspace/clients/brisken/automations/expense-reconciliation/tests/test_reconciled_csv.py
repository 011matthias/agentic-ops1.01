"""Flat reconciled CSV tests (2026-06-16) — the CSV twin of the xlsx
report. One row per statement line, enriched with its matched expense.

Synthetic data only; mirrors the test_zoho_export helper shapes.
"""
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
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.output.reconciled_csv import (
    RECONCILED_COLUMNS,
    build_reconciled_rows,
    write_reconciled_csv,
)

# Column indices resolved by name so the assertions survive a reorder.
_C = {name: i for i, name in enumerate(RECONCILED_COLUMNS)}


def _line(desc, amount, category="Meals & Entertainment") -> LineItem:
    return LineItem(
        description=desc,
        line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.9,
            source=ClassificationSource.LINE, reasoning="t",
        ),
    )


def _tx(tid="t1", amount="180", account="amex-usd", **kw) -> Transaction:
    base = dict(
        transaction_id=tid, legal_entity_id="le1", account_id=account,
        transaction_date=date(2026, 4, 7), posting_date=date(2026, 4, 9),
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
        raw_text="04/07 AMAZON MARKETPLACE 180.00",
    )
    base.update(kw)
    return Transaction(**base)


def _receipt(items, **kw) -> Receipt:
    base = dict(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        line_items=tuple(items),
    )
    base.update(kw)
    return Receipt(**base)


def _matched() -> MatchOutcome:
    return MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "amount+date", False, score=92)])


# ── grain + header ───────────────────────────────────────────────────


def test_header_and_one_row_per_statement_line(tmp_path):
    tx1 = _tx("t1")
    tx2 = _tx("t2")  # unmatched
    rec = _receipt([_line("widget", "180")])
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    out = write_reconciled_csv(outcome, [tx1, tx2], [rec], tmp_path / "reconciled.csv")
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == RECONCILED_COLUMNS
    # one row per transaction, in input (statement) order — nothing dropped.
    assert len(rows) == 3  # header + 2 statement lines
    assert all(len(r) == len(RECONCILED_COLUMNS) for r in rows)
    assert rows[1][_C["Match Status"]] == "MATCHED"
    assert rows[2][_C["Match Status"]] == "UNMATCHED"


def test_matched_row_carries_ai_category_and_account(tmp_path):
    """The tool's OWN category + posting account surface in the AI columns
    for a matched row, beside the report's own Zoho Category, and stay blank
    on an unmatched line."""
    matched_line = LineItem(
        description="Adobe subscription", line_total=Decimal("180"),
        categorization=Categorization(
            category="Software & Subscriptions",
            zoho_account="E600020-01 - Software & Subscriptions",
            confidence=0.95, source=ClassificationSource.VENDOR, reasoning="t",
        ),
    )
    rec = _receipt([matched_line], zoho_category="E100010-31 - Travel Expense | Food")
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    out = write_reconciled_csv(
        outcome, [_tx("t1"), _tx("t2")], [rec], tmp_path / "reconciled.csv"
    )
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    matched, unmatched = rows[1], rows[2]
    # The report's label and the tool's own label sit side by side.
    assert matched[_C["Zoho Category"]] == "E100010-31 - Travel Expense | Food"
    assert matched[_C["AI Category"]] == "Software & Subscriptions"
    assert matched[_C["AI Zoho Account"]] == "E600020-01 - Software & Subscriptions"
    assert matched[_C["AI Category Source"]] == ClassificationSource.VENDOR.value
    # Blank on the unmatched line (no receipt).
    assert unmatched[_C["AI Category"]] == ""
    assert unmatched[_C["AI Zoho Account"]] == ""
    assert unmatched[_C["AI Category Source"]] == ""


def test_matched_row_carries_expense_enrichment():
    tx = _tx()
    rec = _receipt(
        [_line("widget", "180")],
        report_number="ER-00220",
        receipt_url="https://expense.zoho.example/r/1001",
        zoho_category="E100010 - Travel Expense",
        payment_mode="1 - CorpServ 2838/1672 (Chase)",
        detected_total=Decimal("180"),
        detected_currency="USD",
        reimbursable=False,
    )
    row = build_reconciled_rows(_matched(), [tx], [rec])[0]
    assert row[_C["Match Status"]] == "MATCHED"
    assert row[_C["Match Type"]] == "exact"
    assert row[_C["Match Score"]] == "92"
    assert row[_C["Expense ID"]] == "r1"
    assert row[_C["Report Number"]] == "ER-00220"
    assert row[_C["Zoho Category"]] == "E100010 - Travel Expense"
    assert row[_C["Payment Mode"]] == "1 - CorpServ 2838/1672 (Chase)"
    assert row[_C["Receipt URL"]] == "https://expense.zoho.example/r/1001"
    assert row[_C["Receipt Total"]] == "180.00"
    assert row[_C["Reimbursable"]] == "No"


def test_unmatched_row_has_blank_expense_columns_but_keeps_bank_data():
    tx = _tx("t2")
    outcome = MatchOutcome(unmatched_transactions=["t2"])
    row = build_reconciled_rows(outcome, [tx], [])[0]
    assert row[_C["Match Status"]] == "UNMATCHED"
    assert row[_C["Match Type"]] == ""
    assert row[_C["Expense ID"]] == ""
    assert row[_C["Report Number"]] == ""
    assert row[_C["Receipt URL"]] == ""
    # bank-side data is still present (Dirk: bank data stays as it was).
    assert row[_C["Statement Amount"]] == "180.00"
    assert row[_C["Currency"]] == "USD"
    assert row[_C["Description"]] == "AMAZON"
    assert row[_C["Statement Text"]] == "04/07 AMAZON MARKETPLACE 180.00"


# ── statement FX detail preserved verbatim ───────────────────────────


def test_fx_detail_preserved_on_the_statement_line():
    """A foreign charge keeps its original amount / currency / rate from
    the Chase PDF, at the bank's captured precision (Dirk: all bank data
    stays as it was)."""
    tx = _tx(
        "t1", amount="31.73",
        original_amount=Decimal("27.00"), original_currency="EUR",
        fx_rate=Decimal("1.175185185"),
    )
    rec = _receipt([_line("dinner", "31.73")], detected_total=Decimal("27.00"),
                   detected_currency="EUR")
    outcome = MatchOutcome(
        judgment_required=[Match("t1", "r1", MatchType.FX_JUDGMENT, 0.6, "FX EUR->USD", True)]
    )
    row = build_reconciled_rows(outcome, [tx], [rec])[0]
    assert row[_C["Match Status"]] == "NEEDS_REVIEW (FX)"
    assert row[_C["Original Amount"]] == "27.00"
    assert row[_C["Original Currency"]] == "EUR"
    assert row[_C["FX Rate"]] == "1.175185185"  # not rounded


def test_ambiguous_uses_top_candidate():
    tx = _tx("t1")
    rec_a = _receipt([_line("a", "180")], document_id="rA")
    rec_b = _receipt([_line("b", "180")], document_id="rB")
    outcome = MatchOutcome(ambiguous=[
        Match("t1", "rA", MatchType.AMBIGUOUS, 0.5, "tie A", True),
        Match("t1", "rB", MatchType.AMBIGUOUS, 0.5, "tie B", True),
    ])
    rows = build_reconciled_rows(outcome, [tx], [rec_a, rec_b])
    assert len(rows) == 1  # still one row per statement line
    assert rows[0][_C["Match Status"]] == "NEEDS_REVIEW (ambiguous)"
    assert rows[0][_C["Expense ID"]] == "rA"  # first (top) candidate


# ── enrichment-lookup override precedence (mirrors zoho_export) ───────


def test_wired_lookups_override_receipt_fields():
    tx = _tx()
    rec = _receipt([_line("widget", "180")],
                   report_number="ER-OLD", receipt_url=None, receipt_name="w.jpg")
    row = build_reconciled_rows(
        _matched(), [tx], [rec],
        receipt_urls={"r1": "/receipts/ab/abcd.jpg"},
        report_for={"r1": "ER-00220"}.get,
    )[0]
    assert row[_C["Receipt URL"]] == "/receipts/ab/abcd.jpg"
    assert row[_C["Report Number"]] == "ER-00220"


def test_wired_lookup_miss_is_blank_not_fabricated():
    tx = _tx()
    rec = _receipt([_line("widget", "180")],
                   report_number="ER-FALLBACK", receipt_url="https://fallback")
    row = build_reconciled_rows(
        _matched(), [tx], [rec],
        receipt_urls={},               # r1 absent → blank, not the fallback
        report_for=lambda doc: None,   # always unknown
    )[0]
    assert row[_C["Receipt URL"]] == ""
    assert row[_C["Report Number"]] == ""


def test_reimbursable_tri_state():
    tx = _tx()
    for flag, expected in ((True, "Yes"), (False, "No"), (None, "")):
        rec = _receipt([_line("widget", "180")], reimbursable=flag)
        row = build_reconciled_rows(_matched(), [tx], [rec])[0]
        assert row[_C["Reimbursable"]] == expected


# ── §17 disposition column ───────────────────────────────────────────


def test_disposition_defaults_to_business():
    """Every line carries a Disposition; absent from the map => business,
    never blank, never dropped."""
    tx = _tx()
    rec = _receipt([_line("widget", "180")])
    row = build_reconciled_rows(_matched(), [tx], [rec])[0]
    assert row[_C["Disposition"]] == "business"


def test_disposition_reflects_map():
    tx1, tx2 = _tx("t1"), _tx("t2")
    rec = _receipt([_line("widget", "180")])
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    rows = build_reconciled_rows(
        outcome, [tx1, tx2], [rec],
        dispositions={"t1": "reimbursable_personal", "t2": "do_not_export"},
    )
    # An unmatched line still surfaces WITH its disposition (never dropped).
    assert rows[0][_C["Disposition"]] == "reimbursable_personal"
    assert rows[1][_C["Disposition"]] == "do_not_export"


# ── CLI wiring: output.reconciled_csv ────────────────────────────────


def _write_run_config(tmp_path, *, with_csv: bool) -> "tuple":
    statement_csv = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE SHOP NYC,5.75,M\n"
    )
    receipts_csv = (
        'document_id,detected_date,detected_total,detected_currency,'
        'detected_vendor,detected_reference,line_items\n'
        'rcpt-001,2026-04-01,5.75,USD,Coffee Shop NYC,,'
        '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    output = {"path": "report.xlsx"}
    if with_csv:
        output["reconciled_csv"] = "reconciled.csv"
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "amex-usd",
            "legal_entity_id": "brisken-llc", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": output,
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_cli_writes_reconciled_csv_when_configured(tmp_path):
    from expense_recon.cli import run

    config_path = _write_run_config(tmp_path, with_csv=True)
    run(config_path)

    out = tmp_path / "reconciled.csv"
    assert out.exists()
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == RECONCILED_COLUMNS
    # one statement line in, one reconciled row out.
    assert len(rows) == 2
    assert rows[1][_C["Statement Amount"]] == "5.75"


def test_cli_skips_reconciled_csv_when_absent(tmp_path):
    from expense_recon.cli import run

    config_path = _write_run_config(tmp_path, with_csv=False)
    result = run(config_path)
    assert result is not None
    assert not (tmp_path / "reconciled.csv").exists()


# ── Slice 10: charge-categorization columns on unmatched lines ───────


def test_unmatched_line_carries_charge_categorization():
    tx = _tx("t2", vendor_from_statement="ANTHROPIC")
    outcome = MatchOutcome(unmatched_transactions=["t2"])
    cat = Categorization(
        category="Software & Subscriptions",
        zoho_account="Other Infra and IT Costs for Cloud Business",
        confidence=1.0, source=ClassificationSource.LEARNED,
        reasoning="from your Zoho Books posting history",
    )
    rows = build_reconciled_rows(
        outcome, [tx], [], charge_categorizations={"t2": cat}
    )
    row = rows[0]
    assert row[_C["Match Status"]] == "UNMATCHED"
    assert row[_C["Charge Category"]] == "Software & Subscriptions"
    assert row[_C["Charge Zoho Account"]] == "Other Infra and IT Costs for Cloud Business"
    assert row[_C["Charge Category Source"]] == "LEARNED"


def test_matched_line_charge_columns_blank():
    tx = _tx()
    rec = _receipt([_line("widget", "180")])
    rows = build_reconciled_rows(_matched(), [tx], [rec])
    row = rows[0]
    assert row[_C["Charge Category"]] == ""
    assert row[_C["Charge Zoho Account"]] == ""
    assert row[_C["Charge Category Source"]] == ""


def test_review_no_signal_charge_stays_blank_not_noise():
    tx = _tx("t2")
    outcome = MatchOutcome(unmatched_transactions=["t2"])
    cat = Categorization(
        category=None, zoho_account=None, confidence=0.0,
        source=ClassificationSource.REVIEW, reasoning="no signal",
    )
    rows = build_reconciled_rows(
        outcome, [tx], [], charge_categorizations={"t2": cat}
    )
    assert rows[0][_C["Charge Category"]] == ""
    assert rows[0][_C["Charge Category Source"]] == ""
