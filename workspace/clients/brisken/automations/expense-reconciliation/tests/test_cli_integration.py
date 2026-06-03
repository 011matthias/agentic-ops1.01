"""End-to-end test for the slice-1 CLI with LD-2/LD-3 layout.

Fixtures are written inline into `tmp_path` to keep the test
self-contained.

Outcome coverage:

  - Coffee Shop  $5.75  + line-item "Latte"  → EXACT, Tier 1 LINE (Meals)
  - Delancey     $57.50 → EXACT match with NO line items → Tier 2 VENDOR
                          fallback (Delancey not in vendor map → REVIEW)
  - Uber         $22.30 → EXACT match, NO line items → Tier 2 VENDOR
                          (vendor "Uber" hits VENDOR keyword → Travel)
  - Amazon       $200   + 3 line items (chair / coffee / cable) → EXACT,
                          Tier 1 LINE on each of 3 rows
  - Staples      $42.50 → UNMATCHED transaction (no receipt provided)

Tests both:
  (a) the LD-2 strict line-item rule (LINE vs VENDOR vs REVIEW tiers)
  (b) the LD-3 5+N sheet structure (Summary / per-card tab / Needs
      Review / Unmatched / Errors)
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from expense_recon.cli import ConfigError, run
from expense_recon.matching.judgment import STUB_REASON, judge_fx_match
from expense_recon.matching.types import (
    ClassificationSource,
    MatchType,
    Receipt,
    Transaction,
)


STATEMENT_CSV = (
    "Date,Description,Amount,Card Member\n"
    "04/01/2026,COFFEE SHOP NYC,5.75,MATTHIAS NEUMANN\n"
    "04/03/2026,DELANCEY TAVERN,57.50,MATTHIAS NEUMANN\n"
    "04/05/2026,UBER * TRIP,22.30,MATTHIAS NEUMANN\n"
    "04/07/2026,AMAZON.COM,200.00,MATTHIAS NEUMANN\n"
    "04/15/2026,STAPLES NYC,42.50,MATTHIAS NEUMANN\n"
)

# Receipts CSV with the new line_items JSON column.
#   rcpt-001: itemized (latte) → Tier 1 LINE on "coffee" keyword
#   rcpt-002: NO line items → Tier 2 VENDOR fallback (Delancey misses vendor map)
#   rcpt-003: NO line items → Tier 2 VENDOR fallback (Uber hits vendor map)
#   rcpt-004: 3 line items → 3 Tier 1 LINE rows on Amazon ($150+$30+$20=$200)
RECEIPTS_CSV = (
    'document_id,detected_date,detected_total,detected_currency,'
    'detected_vendor,detected_reference,line_items\n'
    'rcpt-001,2026-04-01,5.75,USD,Coffee Shop NYC,,'
    '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    'rcpt-002,2026-04-03,57.50,USD,Delancey Tavern,table-12,\n'
    'rcpt-003,2026-04-05,22.30,USD,Uber,,\n'
    'rcpt-004,2026-04-07,200.00,USD,Amazon,RT3-9923,'
    '"[{""description"":""Herman Miller chair"",""line_total"":""150.00""},'
    '{""description"":""Coffee beans 2kg"",""line_total"":""30.00""},'
    '{""description"":""HDMI cable"",""line_total"":""20.00""}]"\n'
)


def _write_run(tmp_path: Path, out_name: str = "report.xlsx") -> Path:
    """Write statement, receipts, and config into tmp_path; return config path."""
    statement_path = tmp_path / "statement.csv"
    statement_path.write_text(STATEMENT_CSV, encoding="utf-8")

    receipts_path = tmp_path / "receipts.csv"
    receipts_path.write_text(RECEIPTS_CSV, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {
            "path": "receipts.csv",
            "default_currency": "USD",
        },
        "output": {"path": out_name},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


# ── LD-3 sheet structure tests ──────────────────────────────────────


def test_workbook_has_expected_sheets(tmp_path: Path):
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    assert report_path.exists()
    assert report_path.suffix == ".xlsx"

    wb = openpyxl.load_workbook(report_path)
    # One card → 5 sheets: Summary + 1 card tab + Needs Review + Unmatched + Errors
    assert wb.sheetnames == ["Summary", "amex-9001", "Needs Review", "Unmatched", "Errors"]


def test_summary_counts(tmp_path: Path):
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    summary = wb["Summary"]
    label_to_value = {
        row[0]: row[1]
        for row in summary.iter_rows(values_only=True)
        if row and row[0] is not None and len(row) > 1
    }

    # 5 transactions, 4 receipts, 4 matched, 1 unmatched tx.
    assert label_to_value["Transactions"] == 5
    assert label_to_value["Receipts"] == 4
    assert label_to_value["Matched"] == 4
    assert label_to_value["Unmatched transactions"] == 1
    assert label_to_value["Unmatched receipts"] == 0
    assert label_to_value["Reconciliation invariant"] == "OK"


def test_card_tab_has_per_line_item_rows(tmp_path: Path):
    """Amazon's 3 line items become 3 separate rows on the card tab.
    Total of 6 rows (coffee + delancey + uber + amazon×3) plus subtotals.
    """
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    card = wb["amex-9001"]

    # Pull rows with a line-item description (skip header + subtotals).
    line_item_descriptions = []
    for row in card.iter_rows(min_row=2, values_only=True):
        if row[2] and not str(row[2]).startswith("("):
            # column C is "Line item"
            if row[2] not in ("Subtotals",):
                line_item_descriptions.append(row[2])

    assert "Latte" in line_item_descriptions
    assert "Herman Miller chair" in line_item_descriptions
    assert "Coffee beans 2kg" in line_item_descriptions
    assert "HDMI cable" in line_item_descriptions


def test_tier_distribution_on_card_tab(tmp_path: Path):
    """LD-4 source coloring is driven by the Source column.

    Expected source distribution on the amex-9001 tab:
      LINE rows:    Latte (coffee), chair, coffee beans (≥1) → at least 3
      VENDOR rows:  Uber (vendor keyword), Delancey (vendor map miss → REVIEW)
      REVIEW rows:  Staples unmatched + Delancey vendor-miss + possibly cable
    """
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    card = wb["amex-9001"]

    source_col_idx = 7  # column G in CARD_TAB_COLUMNS
    sources = []
    for row in card.iter_rows(min_row=2, values_only=True):
        if row[source_col_idx - 1]:
            sources.append(row[source_col_idx - 1])

    assert "LINE" in sources, f"Expected at least one LINE row; got: {sources}"
    assert "VENDOR ⚠" in sources, f"Expected vendor fallback (Uber); got: {sources}"
    assert "REVIEW" in sources, f"Expected review row (Staples unmatched); got: {sources}"


def test_needs_review_contains_vendor_and_review_rows(tmp_path: Path):
    """Needs Review sheet aggregates Tier 2 (VENDOR ⚠) + Tier 3 (REVIEW)
    across all cards. LINE rows must NOT appear here.
    """
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    review = wb["Needs Review"]

    source_col_idx = 8  # column H in NEEDS_REVIEW_COLUMNS (Card + 9 card cols → Source is at idx 8)
    sources = []
    for row in review.iter_rows(min_row=2, values_only=True):
        if row[source_col_idx - 1]:
            sources.append(row[source_col_idx - 1])

    assert sources, "Needs Review sheet should have rows"
    assert "LINE" not in sources, "LINE-tier rows must NOT appear in Needs Review"
    assert any(s in ("VENDOR ⚠", "REVIEW") for s in sources)


def test_unmatched_sheet_lists_staples(tmp_path: Path):
    """Staples has no receipt → appears in Unmatched (top section) AND
    in Needs Review as a row with note 'Unmatched transaction'.
    """
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    unmatched = wb["Unmatched"]

    vendors_seen = []
    for row in unmatched.iter_rows(values_only=True):
        if row and len(row) >= 3 and row[2]:  # Vendor column
            vendors_seen.append(str(row[2]))

    assert any("STAPLES" in v for v in vendors_seen)


def test_errors_sheet_empty_in_clean_run(tmp_path: Path):
    """Errors sheet exists but has only a header row in a clean run."""
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    errors = wb["Errors"]
    # Just the header row.
    assert errors.max_row == 1


# ── LD-2 contract tests (strict line-item rule) ────────────────────


def test_amazon_receipt_produces_three_distinct_rows(tmp_path: Path):
    """LD-2: one receipt → N journal entries. Amazon's 3 line items
    must each have their own row, not be aggregated.
    """
    config_path = _write_run(tmp_path)
    report_path = run(config_path)

    wb = openpyxl.load_workbook(report_path)
    card = wb["amex-9001"]

    amazon_rows = []
    for row in card.iter_rows(min_row=2, values_only=True):
        if row[1] and "AMAZON" in str(row[1]).upper():
            amazon_rows.append(row)

    assert len(amazon_rows) == 3, f"Expected 3 Amazon rows; got: {amazon_rows}"
    amounts = sorted(float(r[4]) for r in amazon_rows)
    assert amounts == [20.0, 30.0, 150.0]


# ── FX stub contract tests ──────────────────────────────────────────


def test_fx_judgment_stub_returns_review_match_with_stub_reason():
    """The FX stub must never silently resolve a case as auto-matched.
    Slice-1 contract: every FX entry stays for human review until the
    real Claude call lands in slice 2.
    """
    tx = Transaction(
        transaction_id="t1",
        legal_entity_id="le1",
        account_id="acct",
        transaction_date=date(2026, 4, 12),
        posting_date=None,
        amount=Decimal("112.30"),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="HOTEL PARIS FR",
    )
    receipt = Receipt(
        document_id="r1",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 12),
        detected_total=Decimal("98.45"),
        detected_currency="EUR",
        detected_vendor="Hotel Paris",
    )

    judged = judge_fx_match(tx, receipt)

    assert judged.match_type == MatchType.FX_JUDGMENT
    assert judged.requires_review is True
    assert judged.reason == STUB_REASON


# ── CLI plumbing tests ──────────────────────────────────────────────


def test_out_override_takes_precedence(tmp_path: Path):
    config_path = _write_run(tmp_path, out_name="config-report.xlsx")
    override = tmp_path / "override-report.xlsx"
    report_path = run(config_path, out_override=override)

    assert report_path == override.resolve()
    assert override.exists()
    assert not (tmp_path / "config-report.xlsx").exists()


def test_missing_config_raises_configerror(tmp_path: Path):
    with pytest.raises(ConfigError):
        run(tmp_path / "does-not-exist.json")


def test_unsupported_statement_extension_raises(tmp_path: Path):
    bad_statement = tmp_path / "statement.txt"
    bad_statement.write_text("not a real statement", encoding="utf-8")
    receipts_path = tmp_path / "receipts.csv"
    receipts_path.write_text(RECEIPTS_CSV, encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.txt",
            "account_id": "x",
            "legal_entity_id": "y",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv"},
        "output": {"path": "r.xlsx"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ConfigError, match=r"\.csv / \.xlsx"):
        run(config_path)


def test_duplicate_receipt_document_id_lands_in_errors_sheet(tmp_path: Path):
    """B1 + B5 ANNEALING: tolerant mode — the dup row lands in the Errors
    sheet (with file name + line number + message), the first
    occurrence still parses successfully, and the run completes.
    """
    bad_receipts = tmp_path / "receipts.csv"
    bad_receipts.write_text(
        "document_id,detected_date,detected_total,detected_vendor\n"
        "rcpt-001,2026-04-01,5.75,Coffee\n"
        "rcpt-001,2026-04-02,10.00,Lunch\n",
        encoding="utf-8",
    )
    statement_path = tmp_path / "statement.csv"
    statement_path.write_text(STATEMENT_CSV, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "r.xlsx"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    report_path = run(config_path)
    assert report_path is not None
    assert report_path.exists()

    wb = openpyxl.load_workbook(report_path)
    errors = wb["Errors"]

    # Header row + at least one error row for the duplicate.
    assert errors.max_row >= 2
    error_messages = []
    for row in errors.iter_rows(min_row=2, values_only=True):
        if row[0]:  # File column
            error_messages.append((row[0], row[1], row[2]))

    assert any(
        "receipts.csv" in str(file)
        and line == 3
        and "duplicate" in str(msg).lower()
        for file, line, msg in error_messages
    ), f"Expected dup-id error on receipts.csv:3; got: {error_messages}"


def test_bad_row_in_receipts_collects_to_errors_continues_with_good_rows(
    tmp_path: Path,
):
    """B1: a malformed row (bad date) lands in Errors, surrounding good
    rows still parse and reconcile.
    """
    receipts_with_bad_row = (
        "document_id,detected_date,detected_total,detected_vendor,"
        "detected_currency,detected_vendor,detected_reference,line_items\n"
        "rcpt-001,2026-04-01,5.75,USD,Coffee Shop,Coffee Shop,,\n"
        "rcpt-bad,not-a-date,99.00,USD,Bad Vendor,Bad Vendor,,\n"
        "rcpt-003,2026-04-05,22.30,USD,Uber,Uber,,\n"
    )
    # Note: above has a duplicated 'detected_vendor' column header which
    # csv.DictReader handles by overwriting; we want a CLEAN bad-row
    # case so rewrite with proper headers and only a date issue.
    receipts_with_bad_row = (
        "document_id,detected_date,detected_total,detected_currency,"
        "detected_vendor,detected_reference,line_items\n"
        "rcpt-001,2026-04-01,5.75,USD,Coffee Shop,,\n"
        "rcpt-bad,not-a-date,99.00,USD,Bad Vendor,,\n"
        "rcpt-003,2026-04-05,22.30,USD,Uber,,\n"
    )
    statement_path = tmp_path / "statement.csv"
    statement_path.write_text(STATEMENT_CSV, encoding="utf-8")
    receipts_path = tmp_path / "receipts.csv"
    receipts_path.write_text(receipts_with_bad_row, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "r.xlsx"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    report_path = run(config_path)
    assert report_path is not None

    wb = openpyxl.load_workbook(report_path)

    # Errors sheet has the bad-date row.
    errors = wb["Errors"]
    error_messages = [
        row for row in errors.iter_rows(min_row=2, values_only=True) if row[0]
    ]
    assert any(
        "receipts.csv" in str(r[0]) and r[1] == 3 and "date" in str(r[2]).lower()
        for r in error_messages
    ), f"Expected bad-date error on receipts.csv:3; got: {error_messages}"

    # Good rows still reconciled — Summary should show 2 matched
    # (rcpt-001 → coffee, rcpt-003 → uber).
    summary = wb["Summary"]
    label_to_value = {
        row[0]: row[1]
        for row in summary.iter_rows(values_only=True)
        if row and row[0] is not None and len(row) > 1
    }
    assert label_to_value["Receipts"] == 2  # rcpt-bad was skipped
    assert label_to_value["Matched"] == 2


def test_bad_row_in_statement_collects_to_errors_continues(tmp_path: Path):
    """B1: malformed statement row → Errors sheet, good rows still reconcile."""
    bad_statement = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE SHOP NYC,5.75,M\n"
        "04/02/2026,BAD AMOUNT TX,not-a-number,M\n"
        "04/05/2026,UBER * TRIP,22.30,M\n"
    )
    statement_path = tmp_path / "statement.csv"
    statement_path.write_text(bad_statement, encoding="utf-8")
    receipts_path = tmp_path / "receipts.csv"
    receipts_path.write_text(RECEIPTS_CSV, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "r.xlsx"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    report_path = run(config_path)
    assert report_path is not None

    wb = openpyxl.load_workbook(report_path)
    errors = wb["Errors"]
    error_messages = [
        row for row in errors.iter_rows(min_row=2, values_only=True) if row[0]
    ]
    assert any(
        "statement.csv" in str(r[0]) and r[1] == 3 and "number" in str(r[2]).lower()
        for r in error_messages
    ), f"Expected bad-amount error on statement.csv:3; got: {error_messages}"


def test_dry_run_skips_xlsx_and_prints_summary(tmp_path: Path, capsys):
    """B4: --dry-run path returns None and writes counts to stdout."""
    config_path = _write_run(tmp_path)
    result = run(config_path, dry_run=True)

    assert result is None  # no xlsx
    # Default output path should NOT exist.
    assert not (tmp_path / "report.xlsx").exists()

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "Transactions:" in captured.out
    assert "Matched:" in captured.out
