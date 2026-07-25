"""FX comparison breakdown on cross-currency candidates (2026-07-25).

A reviewer working an uncertain FX pair should see, side by side, what the
bank statement charged, what the receipt says, and what the receipt is
worth under Zoho's own booked rate. `_fx_breakdown` builds that flat
comparison; these tests pin the math and the graceful-omission rules.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.types import Receipt, Transaction
from expense_recon.web.service import _fx_breakdown


def _tx(amount="77.05", ccy="USD") -> Transaction:
    return Transaction(
        transaction_id="t1",
        legal_entity_id="le1",
        account_id="2838",
        transaction_date=date(2026, 4, 6),
        posting_date=None,
        amount=Decimal(amount) if amount is not None else None,
        transaction_currency=ccy,
        account_card_currency="USD",
        vendor_from_statement="OPENAI *CHATGPT SUBSCR",
    )


def _rec(total="335.31", ccy="BRL", rate="0.196078", base="65.75") -> Receipt:
    return Receipt(
        document_id="ER-00215#004",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 8),
        detected_total=Decimal(total) if total is not None else None,
        detected_currency=ccy,
        detected_vendor="MEGA CENTER COMERCIO",
        exchange_rate=Decimal(rate) if rate is not None else None,
        base_amount=Decimal(base) if base is not None else None,
    )


def test_same_currency_returns_none():
    assert _fx_breakdown(_tx(ccy="USD"), _rec(ccy="USD")) is None


def test_missing_receipt_returns_none():
    assert _fx_breakdown(_tx(), None) is None


def test_missing_amount_returns_none():
    assert _fx_breakdown(_tx(amount=None), _rec()) is None
    assert _fx_breakdown(_tx(), _rec(total=None)) is None


def test_full_breakdown_with_zoho_conversion():
    fx = _fx_breakdown(_tx(), _rec())
    assert fx["charge_amount"] == "77.05"
    assert fx["charge_currency"] == "USD"
    assert fx["receipt_amount"] == "335.31"
    assert fx["receipt_currency"] == "BRL"
    assert fx["rate_label"] == "USD per BRL"
    # Zoho's booked rate is carried through; this pairing implies a higher
    # one (77.05 / 335.31 = 0.229787), which is the FX-coincidence tell.
    assert fx["zoho_rate"] == "0.196078"
    assert fx["implied_rate"] == "0.229787"
    # Zoho values the receipt at 65.75 USD; the charge is 77.05 USD.
    assert fx["zoho_converted"] == "65.75"
    assert fx["converted_gap"] == "11.30"
    assert fx["converted_gap_pct"] == 15  # 11.30 / 77.05


def test_breakdown_without_zoho_conversion():
    """A manual/emailed receipt carries no Zoho rate or base amount: the
    implied rate still renders, the Zoho columns are blank."""
    fx = _fx_breakdown(_tx(), _rec(rate=None, base=None))
    assert fx["implied_rate"] == "0.229787"
    assert fx["zoho_rate"] == ""
    assert fx["zoho_converted"] == ""
    assert fx["converted_gap"] == ""
    assert fx["converted_gap_pct"] is None
