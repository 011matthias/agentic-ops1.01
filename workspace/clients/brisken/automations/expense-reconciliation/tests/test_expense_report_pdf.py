"""Tests for the Zoho Expense report PDF parser (2026-07-16).

These drive `parse_expense_report_text`, the text-layer core, with
synthetic report-shaped text. Real ER PDFs are client financial data
and are never committed as fixtures; the text shapes here mirror the
structures verified against 5 real Brisken ER PDFs (ER-00002, ER00009,
ER-D-0016, ER-00101, ER-00139, fetched via Graph 2026-07-16) -- all
five parsed clean (0 issues) and their parsed per-currency totals
matched the report's own printed Total Expense Amount to the cent.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.ingest._common import StatementParseError
from expense_recon.ingest.expense_report_pdf import (
    parse_expense_report_text,
    parse_expense_report_pdf_tolerant,
)


def _parse(text, **kw):
    kw.setdefault("file_name", "report.pdf")
    kw.setdefault("legal_entity_id", "brisken-llc")
    return parse_expense_report_text(text, **kw)


# Single currency (USD), numbered rows, one merchant wrapped across two
# lines ("Big City" / "Taxi") and one merchant sharing the amount line.
SINGLE_CCY = """Expense Report
ER-90001
EXPENSE SUMMARY

E100010-01 - Travel Expense: Ground Transport
S.No Expense Details Merchant Amount (USD)
1. 03/01/2026
Cab to the airport
Ref# : CONF-1
Payment Mode : Credit Card
Big City
Taxi
$50.00
2. 03/02/2026
Lunch with client
Payment Mode : Cash
Deli Shop $100.00
Sub Total $150.00
REPORT SUMMARY BY CURRENCY
TOTAL USD
Total Expense Amount 150.00
Non Reimbursable Amount (-) 0.00
Advance Amount Received (-) 0.00
Total Reimbursable Amount $150.00
"""

# Multi-currency (USD + EUR): an FX-detail row (merchant + original EUR
# amount, rate line, USD line alone) and a dual-column USD-native row.
MULTI_CCY = """Expense Report
ER-90002
EXPENSE SUMMARY

E200020-05 - Meals
S.No Expense Details Merchant Amount Amount (USD)
1. 04/10/2026
Team dinner
Payment Mode : Credit Card
Cafe Berlin €18,50
1 EUR = 1.100000 USD
$20.35
Non Reimbursable
2. 04/11/2026
Coffee run
Payment Mode : Cash
Corner Cafe $6.00 $6.00
Sub Total $26.35
REPORT SUMMARY BY CURRENCY
TOTAL USD EUR
Total Expense Amount 6.00 18,50
Non Reimbursable Amount (-) 20.35 (-) 0,00
Advance Amount Received (-) 0.00 (-) 0,00
Total Reimbursable Amount $6.00 €0,00
"""

# Per-diem EUR rows: bare "MM/DD/YY [n]" row starts, no merchant at all.
PER_DIEM = """Expense Report
ER-90003
EXPENSE SUMMARY

MWSt0 - 10 - Per Diem
Expense Details Merchant Amount (EUR)
  05/01/26 [1]
Per diem Name : Domestic Day Rate
Day(s) : 1.00 @ €12,00/day
Payment Mode : Bank Transfer
Location : Berlin
€12,00
  05/02/26 [1]
Per diem Name : Domestic Day Rate
Day(s) : 1.00 @ €12,00/day
Payment Mode : Bank Transfer
Location : Berlin
€12,00
Sub Total €24,00
REPORT SUMMARY BY CURRENCY
TOTAL EUR
Total Expense Amount 24,00
Non Reimbursable Amount (-) 0,00
Advance Amount Received (-) 0,00
Total Reimbursable Amount €24,00
"""

# Page-break regression (2026-07-16 real-data bug): the table header
# repeats immediately after a row's last content line, with NO blank
# line and NO page-number line between them (some pages omit the
# leading page-number literal). Must not be misread as a category
# header that swallows the row's amount.
PAGE_BREAK_NO_MARKER = """Expense Report
ER-90004
EXPENSE SUMMARY

MWSt0 - 10 - Per Diem
Expense Details Merchant Amount (EUR)
  06/01/26 [1]
Per diem Name : Domestic Day Rate
Day(s) : 1.00 @ €15,00/day
Payment Mode : Bank Transfer
€15,00
Expense Details Merchant Amount (EUR)
  06/02/26 [1]
Per diem Name : Domestic Day Rate
Day(s) : 1.00 @ €15,00/day
Payment Mode : Bank Transfer
€15,00
Sub Total €30,00
REPORT SUMMARY BY CURRENCY
TOTAL EUR
Total Expense Amount 30,00
Non Reimbursable Amount (-) 0,00
Advance Amount Received (-) 0,00
Total Reimbursable Amount €30,00
"""

MISMATCHED_TOTAL = """Expense Report
ER-90007
EXPENSE SUMMARY

1. 07/01/2026
Something
Payment Mode : Cash
Vendor X $10.00
Sub Total $10.00
REPORT SUMMARY BY CURRENCY
TOTAL USD
Total Expense Amount 999.00
"""

# ISO-code-prefixed originals with US-format numbers (2026-07-17 real
# by-month bug, ER-00214 BRL / ER-00181 DKK): "BRL3,099.99" carries no
# symbol, so the old symbol-only money regex saw only the converted
# "$581.51" line and read the conversion as the original. Also covers
# the "Expense Location :" meta variant (normalized to Location).
ISO_PREFIXED = """Expense Report
ER-90008
EXPENSE SUMMARY

E100010 - Travel Expense
S.No Expense Details Merchant Amount Amount (USD)
1. 03/14/2026
Fan purchase
Ref# : 795234
Payment Mode : Credit Card
Expense Location : Recife, Brazil
MAGAZINE
LUIZA S/A
BRL3,099.99
1 BRL = 0.187586 USD
$581.51
Non Reimbursable
2. 10/02/2024
Hostel
Payment Mode : Credit Card
Cabinn Metro DKK35.00
1 DKK = 0.148401 USD
$5.19
Sub Total $586.70
REPORT SUMMARY BY CURRENCY
TOTAL BRL DKK
Total Expense Amount 3,099.99 35.00
Non Reimbursable Amount (-) 3,099.99 (-) 0.00
"""

# Inline numbered rows (2026-07-17 real by-month bug, one row silently
# dropped in 4 of 6 reports): a numbered row may carry merchant +
# amounts on the date line itself ("3. 05/17/2026 FLiX $155.61
# $155.61"), including the FX form with the merchant continuing on the
# line after a page break ("11. 06/27/2025 TARTUFI & €215,00 $251.99"
# / page header / "PANE, BURRO ET. NERO").
INLINE_ROWS = """Expense Report
ER-90009
EXPENSE SUMMARY

E100010 - Travel Expense
S.No Expense Details Merchant Amount Amount (USD)
1. 05/16/2026
Train
Payment Mode : Credit Card
DB €111,99
1 EUR = 1.163307 USD
$130.28
2. 05/17/2026 FLiX $155.61 $155.61
3
S.No Expense Details Merchant Amount Amount (USD)
Buss
3. 06/27/2025 TARTUFI & €215,00 $251.99
PANE, BURRO ET. NERO
Sub Total $537.88
REPORT SUMMARY BY CURRENCY
TOTAL EUR USD
Total Expense Amount 326,99 155.61
"""


def test_single_currency_report_parses_clean():
    receipts, issues = _parse(SINGLE_CCY)
    assert issues == []
    assert len(receipts) == 2

    cab, lunch = receipts
    assert cab.document_id == "ER-90001#001"
    assert cab.report_number == "ER-90001"
    assert cab.detected_date == date(2026, 3, 1)
    assert cab.detected_total == Decimal("50.00")
    assert cab.detected_currency == "USD"
    assert cab.detected_vendor == "Big City Taxi"
    assert cab.detected_reference == "CONF-1"
    assert cab.payment_mode == "Credit Card"
    assert cab.reimbursable is True
    assert cab.zoho_category == "E100010-01 - Travel Expense: Ground Transport"

    assert lunch.detected_vendor == "Deli Shop"
    assert lunch.detected_total == Decimal("100.00")


def test_multi_currency_fx_row_carries_original_and_base_amount():
    receipts, issues = _parse(MULTI_CCY)
    assert issues == []
    dinner, coffee = receipts

    # detected_total/currency stay in the ORIGINAL currency (matches the
    # by-month OCR ground-truth convention), base_amount/exchange_rate
    # carry the report's own USD conversion.
    assert dinner.detected_total == Decimal("18.50")
    assert dinner.detected_currency == "EUR"
    assert dinner.base_amount == Decimal("20.35")
    assert dinner.exchange_rate == Decimal("1.100000")
    assert dinner.detected_vendor == "Cafe Berlin"
    assert dinner.reimbursable is False  # "Non Reimbursable" marker

    # Dual-column USD-native row: original == base, no FX rate.
    assert coffee.detected_total == Decimal("6.00")
    assert coffee.detected_currency == "USD"
    assert coffee.base_amount == Decimal("6.00")
    assert coffee.exchange_rate is None
    assert coffee.reimbursable is True


def test_per_diem_rows_have_no_merchant():
    receipts, issues = _parse(PER_DIEM)
    assert issues == []
    assert len(receipts) == 2
    assert all(r.detected_vendor is None for r in receipts)
    assert all(r.detected_currency == "EUR" for r in receipts)
    assert {r.detected_total for r in receipts} == {Decimal("12.00")}
    assert receipts[0].detected_date == date(2026, 5, 1)  # 2-digit year


def test_page_break_with_no_leading_marker_does_not_swallow_row():
    receipts, issues = _parse(PAGE_BREAK_NO_MARKER)
    assert issues == []
    assert len(receipts) == 2
    assert [r.detected_total for r in receipts] == [Decimal("15.00"), Decimal("15.00")]


def test_document_ids_unique_and_stable():
    receipts, _ = _parse(SINGLE_CCY)
    ids = [r.document_id for r in receipts]
    assert ids == sorted(set(ids), key=ids.index)  # no duplicates, stable order
    assert len(set(ids)) == len(ids)


def test_printed_total_mismatch_surfaces_as_issue():
    receipts, issues = _parse(MISMATCHED_TOTAL)
    assert len(receipts) == 1  # the row itself parsed fine
    assert any("does not match" in i.message for i in issues)


def test_iso_prefixed_amounts_keep_original_currency():
    receipts, issues = _parse(ISO_PREFIXED)
    assert issues == []
    fan, hostel = receipts

    # BRL3,099.99 (US-format, no symbol) is the ORIGINAL; $581.51 is
    # the report's conversion and lands in base_amount.
    assert fan.detected_currency == "BRL"
    assert fan.detected_total == Decimal("3099.99")
    assert fan.base_amount == Decimal("581.51")
    assert fan.exchange_rate == Decimal("0.187586")
    assert fan.detected_vendor == "MAGAZINE LUIZA S/A"
    # "Expense Location :" normalizes to the Location meta.
    assert fan.expense_location == "Recife, Brazil"

    assert hostel.detected_currency == "DKK"
    assert hostel.detected_total == Decimal("35.00")
    assert hostel.base_amount == Decimal("5.19")
    assert hostel.detected_vendor == "Cabinn Metro"


def test_inline_numbered_rows_are_not_dropped():
    receipts, issues = _parse(INLINE_ROWS)
    assert issues == []
    assert len(receipts) == 3

    train, bus, tartufi = receipts
    assert train.detected_total == Decimal("111.99")
    assert train.detected_currency == "EUR"

    # "2. 05/17/2026 FLiX $155.61 $155.61" -- inline dual-column row,
    # merchant continues after the page break ("Buss").
    assert bus.detected_date == date(2026, 5, 17)
    assert bus.detected_total == Decimal("155.61")
    assert bus.detected_currency == "USD"
    assert bus.base_amount == Decimal("155.61")
    assert "FLiX" in (bus.detected_vendor or "")

    # Inline FX row: EUR original + USD conversion on the date line.
    assert tartufi.detected_total == Decimal("215.00")
    assert tartufi.detected_currency == "EUR"
    assert tartufi.base_amount == Decimal("251.99")
    for frag in ("TARTUFI &", "PANE, BURRO ET. NERO"):
        assert frag in (tartufi.detected_vendor or "")


def test_bare_date_with_trailing_text_is_content_not_a_row():
    # A continuation line that happens to start with a date must not
    # open a new row (only the NUMBERED form may carry inline content).
    text = """Expense Report
ER-90010
EXPENSE SUMMARY

1. 07/01/2026
Refund note
Payment Mode : Cash
06/30/2026 store credit memo
Vendor Y $10.00
Sub Total $10.00
REPORT SUMMARY BY CURRENCY
TOTAL USD
Total Expense Amount 10.00
"""
    receipts, issues = _parse(text)
    assert issues == []
    assert len(receipts) == 1
    assert receipts[0].detected_total == Decimal("10.00")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("60.85", "60.85"),        # US decimal
        ("3,099.99", "3099.99"),   # US thousands + decimal
        ("10,943.33", "10943.33"),
        ("18,50", "18.50"),        # EU decimal comma
        ("1.950,00", "1950.00"),   # EU thousands + decimal
        ("1,950", "1950"),         # bare groups-of-3: thousands
        ("1.950", "1950"),
        ("35.00", "35.00"),
        ("0,00", "0.00"),
    ],
)
def test_parse_amount_sniffs_format_per_token(raw, expected):
    from expense_recon.ingest.expense_report_pdf import _parse_amount

    assert _parse_amount(raw) == Decimal(expected)


def test_report_number_variants():
    for text, expected in [
        (SINGLE_CCY, "ER-90001"),
        ("Expense Report\nER00009\nEXPENSE SUMMARY\n \nREPORT SUMMARY BY CURRENCY\n", "ER00009"),
        ("Expense Report\nER-D-0016\nEXPENSE SUMMARY\n \nREPORT SUMMARY BY CURRENCY\n", "ER-D-0016"),
    ]:
        receipts, issues = _parse(text)
        if receipts:
            assert receipts[0].report_number == expected
        else:
            # empty-body variants still need to resolve the id without raising
            assert any(i.message.startswith("No expense rows") for i in issues)


def test_no_expense_summary_section_raises():
    with pytest.raises(StatementParseError, match="EXPENSE SUMMARY"):
        _parse("Expense Report\nER-90005\nJust some random text\n")


def test_truncated_report_with_no_currency_summary_raises():
    with pytest.raises(StatementParseError, match="REPORT SUMMARY BY CURRENCY"):
        _parse("Expense Report\nER-90006\nEXPENSE SUMMARY\n \n1. 01/01/2026\nSomething\n$1.00\n")


def test_not_a_report_pdf_raises_clean_error():
    with pytest.raises(StatementParseError, match="Zoho Expense report"):
        _parse("Just a random PDF with no report structure at all.\n")


# ── CLI wiring (routing) ───────────────────────────────────────────


def test_cli_infers_expense_report_pdf_from_pdf_suffix(tmp_path, monkeypatch):
    from expense_recon.cli import _load_receipts
    import expense_recon.ingest.expense_report_pdf as erp

    monkeypatch.setattr(erp, "_extract_text", lambda path: SINGLE_CCY)
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4 synthetic")

    receipts, issues = _load_receipts(
        {"receipts": {"path": "report.pdf"}}, tmp_path, "brisken-llc",
    )
    assert issues == []
    assert len(receipts) == 2
    assert receipts[0].report_number == "ER-90001"


def test_cli_explicit_expense_report_pdf_source_on_directory_errors(tmp_path):
    from expense_recon.cli import ConfigError, _load_receipts

    folder = tmp_path / "reports"
    folder.mkdir()
    with pytest.raises(ConfigError, match="directory"):
        _load_receipts(
            {"receipts": {"path": "reports", "source": "expense_report_pdf"}},
            tmp_path, "brisken-llc",
        )


def test_expense_report_pdf_tolerant_missing_file_raises(tmp_path):
    with pytest.raises(StatementParseError, match="not found"):
        parse_expense_report_pdf_tolerant(
            tmp_path / "missing.pdf", legal_entity_id="brisken-llc"
        )
