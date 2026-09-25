"""Item 197: a statement's printed FX line no longer prices every pair.

Live on 2026-09-24: attaching the 9693 Chase PDF to August brought one
printed FX line (SAP SE WALLDORF, 2026-07-16, EUR 437.00 billed USD 500.93
at 1.146292906). The self-derived `statement` rung outranked the charge-day
rate for EVERY EUR pair in the month, at the wider 3% band, so two clean
2838 pairs (ANTHROPIC* CLAUDE SUB 104.95 / 108.53 against EUR 90.00 / 93.07)
each agreed with both receipts and fell to judgment. The numbers below are
those rows; the day rate is a fixture value.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import MatchingConfig, match_month
from expense_recon.matching.types import MatchType, Receipt, Transaction

DAILY = {"2026-08-28": {"USD": "1.1660"}, "2026-08-29": {"USD": "1.1660"}}


def _charge(tx_id, day, amount, vendor, account="2838", **fx):
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="corpserv",
        account_id=account,
        transaction_date=day,
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        **fx,
    )


def _receipt(doc, day, total):
    return Receipt(
        document_id=doc,
        legal_entity_id="corpserv",
        # The name the live Anthropic invoices extract to (52% against
        # "ANTHROPIC* CLAUDE SUB"). Plain "Anthropic" scores 38%, and item 204
        # step 6 would hold these no-card pairs in review, which is not what
        # this test is about.
        detected_vendor="Anthropic, PBC",
        detected_date=day,
        detected_total=Decimal(total),
        detected_currency="EUR",
    )


def _august():
    sap = _charge(
        "9693:sap", date(2026, 7, 16), "500.93", "SAP SE WALLDORF", account="9693",
        original_amount=Decimal("437.00"), original_currency="EUR",
        fx_rate=Decimal("1.146292906"),
    )
    charges = [
        sap,
        _charge("2838:a28", date(2026, 8, 28), "104.95", "ANTHROPIC* CLAUDE SUB"),
        _charge("2838:a29", date(2026, 8, 29), "108.53", "ANTHROPIC* CLAUDE SUB"),
    ]
    receipts = [
        _receipt("r90", date(2026, 8, 28), "90.00"),
        _receipt("r93", date(2026, 8, 29), "93.07"),
    ]
    return charges, receipts


def test_the_printed_sap_line_no_longer_makes_the_august_anthropic_pairs_ambiguous():
    charges, receipts = _august()
    out = match_month(charges, receipts, MatchingConfig.from_dict({"fx_daily_rates": DAILY}))

    paired = {m.transaction_id: m for m in out.matches}
    assert paired["2838:a28"].document_id == "r90"
    assert paired["2838:a29"].document_id == "r93"
    for tx_id in ("2838:a28", "2838:a29"):
        assert paired[tx_id].match_type is MatchType.FX_REFERENCE
        assert not paired[tx_id].requires_review
        assert "OpenTickers daily reference rate" in paired[tx_id].reason
    assert not out.judgment_required
    assert not out.ambiguous


def test_a_month_with_no_daily_table_still_reads_its_printed_lines():
    """The CLI bundles carry no daily table; for them the statement median
    keeps its place above the ECB average, exactly as before."""
    charges, receipts = _august()
    out = match_month(charges, receipts, MatchingConfig())
    reasons = [m.reason for m in out.matches + out.judgment_required + out.ambiguous
               if m.transaction_id.startswith("2838:")]
    assert reasons
    assert all("median of 1 statement FX lines" in r for r in reasons if "rate" in r)
