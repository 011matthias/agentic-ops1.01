"""Tests for the Chase statement PDF parser (2026-06-16).

These drive `parse_statement_text`, the text-layer core, with synthetic
Chase-shaped statement text. Real statements are client financial data and
are never committed as fixtures; the text shapes here mirror the structures
verified against the real 2838 statements (per-card sums reconciled to the
printed cycle totals to the cent).
"""
from datetime import date
from decimal import Decimal

from expense_recon.ingest.statement_pdf import parse_statement_text


# Two cards. Card 2838: a payment (negative), a USD charge, a EUR charge
# with its FX detail, and a January charge (year boundary). Card 3645: a
# BRL charge whose FX rate line is separated from its currency line by
# page-header noise (the page-break case), plus a USD charge.
SYNTH = """Opening/Closing Date 12/05/25 - 01/04/26
Date of
Transaction Merchant  Name or Transaction Description $ Amount
12/12     Payment Thank You-Mobile -4,000.00
12/05     OPENAI *CHATGPT SUBSCR OPENAI.COM CA 159.60
12/15     CANVA* I04731-56029745 CANVA.COM DE 31.73
12/16    EURO
27.00 X 1.175185185 (EXCHG RATE)
01/02     LinkedIn P701251553 855-6535653 CA 575.61
DIRK NEUMANN
TRANSACTIONS THIS CYCLE (CARD  2838) $-3233.06
12/06     AUTO POSTO PIMENTEL BARREIROS 35.85
12/07    BRAZILIAN REAL
Year-to-date totals do not reflect any fee or interest refunds
Date of
Transaction Merchant  Name or Transaction Description $ Amount
190.87 X 0.187824173 (EXCHG RATE)
12/09     KEKES BREAKFAST CAFE S 904-4299144 FL 63.00
DIRK NEUMANN
TRANSACTIONS THIS CYCLE (CARD  3645) $98.85
"""


def _parse(text=SYNTH):
    return parse_statement_text(text, file_name="stmt.pdf", legal_entity_id="brisken-llc")


def test_multi_card_grouping():
    txs, issues = _parse()
    assert issues == []
    by_card = {}
    for t in txs:
        by_card.setdefault(t.account_id, []).append(t)
    assert set(by_card) == {"2838", "3645"}
    assert len(by_card["2838"]) == 4
    assert len(by_card["3645"]) == 2
    assert all(t.legal_entity_id == "brisken-llc" for t in txs)


def test_per_card_sums_reconcile_to_cycle_totals():
    txs, _ = _parse()
    sums = {}
    for t in txs:
        sums[t.account_id] = sums.get(t.account_id, Decimal("0")) + t.amount
    assert sums["2838"] == Decimal("-3233.06")
    assert sums["3645"] == Decimal("98.85")


def test_fx_detail_attached_same_block():
    txs, _ = _parse()
    canva = next(t for t in txs if t.vendor_from_statement.startswith("CANVA"))
    assert canva.amount == Decimal("31.73")          # USD posted
    assert canva.original_amount == Decimal("27.00")
    assert canva.original_currency == "EUR"
    assert canva.fx_rate == Decimal("1.175185185")
    # original * rate reconciles to the USD posted amount
    assert (canva.original_amount * canva.fx_rate).quantize(Decimal("0.01")) == canva.amount


def test_fx_detail_attached_across_page_break():
    # AUTO POSTO's currency line and rate line are separated by page-header
    # noise; the rate must still attach to the charge.
    txs, _ = _parse()
    auto = next(t for t in txs if t.vendor_from_statement.startswith("AUTO POSTO"))
    assert auto.original_currency == "BRL"
    assert auto.original_amount == Decimal("190.87")
    assert auto.fx_rate == Decimal("0.187824173")
    assert auto.account_id == "3645"


def test_year_resolution_across_boundary():
    txs, _ = _parse()
    canva = next(t for t in txs if t.vendor_from_statement.startswith("CANVA"))
    linkedin = next(t for t in txs if t.vendor_from_statement.startswith("LinkedIn"))
    assert canva.transaction_date == date(2025, 12, 15)
    assert linkedin.transaction_date == date(2026, 1, 2)


def test_payment_parsed_as_negative():
    txs, _ = _parse()
    pay = next(t for t in txs if "Payment" in t.vendor_from_statement)
    assert pay.amount == Decimal("-4000.00")
    assert pay.original_currency is None


def test_unmapped_currency_name_is_kept_and_flagged():
    text = (
        "Opening/Closing Date 12/05/25 - 01/04/26\n"
        "12/01     SOME NORDIC SHOP OSLO 1.10\n"
        "12/02    NORWEGIAN KRONE          \n"
        "10.00 X 0.110000000 (EXCHG RATE) \n"
        "TRANSACTIONS THIS CYCLE (CARD  9999) $1.10\n"
    )
    txs, issues = parse_statement_text(
        text, file_name="stmt.pdf", legal_entity_id="brisken-llc"
    )
    assert len(txs) == 1
    assert txs[0].original_currency == "NORWEGIAN KRONE"  # kept verbatim
    assert any("unmapped FX currency" in i.message for i in issues)


def test_charges_without_card_marker_flagged_unknown():
    text = (
        "Opening/Closing Date 12/05/25 - 01/04/26\n"
        "12/01     SOMETHING CA 5.00\n"
    )
    txs, issues = parse_statement_text(
        text, file_name="stmt.pdf", legal_entity_id="brisken-llc"
    )
    assert len(txs) == 1
    assert txs[0].account_id == "UNKNOWN"
    assert any("no trailing card marker" in i.message for i in issues)
