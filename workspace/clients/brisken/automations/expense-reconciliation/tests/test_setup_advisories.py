"""Missing master data announces itself (2026-07-22).

The real April run came back 0-matched with `has_coa: false` and nothing on
screen connecting either fact to a setting that was never configured, so the
tool read as broken rather than unconfigured. `_setup_advisories` names the
setting and what its absence cost the run.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.types import Receipt, Transaction
from expense_recon.web.service import _setup_advisories


def _tx() -> Transaction:
    return Transaction(
        transaction_id="2838:1",
        legal_entity_id="e",
        account_id="2838",
        transaction_date=date(2026, 4, 1),
        posting_date=None,
        amount=Decimal("10.00"),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="V",
    )


def _receipt(currency: str, doc: str = "d1") -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="e",
        detected_vendor="V",
        detected_date=date(2026, 4, 1),
        detected_total=Decimal("50.00"),
        detected_currency=currency,
    )


def _settings_for(rates: dict | None = None, card_account: bool = False) -> dict:
    cfg: dict = {}
    if rates:
        cfg["matching"] = {"fx_reference_rates": rates}
    if card_account:
        cfg["zoho"] = {"card_accounts": {"2838": "1010 Chase"}}
    return cfg


def _settings(advisories: list[dict]) -> set[str]:
    return {a["setting"] for a in advisories}


def test_missing_fx_rate_is_named_with_its_cost():
    out = _setup_advisories(
        _settings_for(), [_tx()], [_receipt("BRL")], has_coa=True
    )
    fx = [a for a in out if a["setting"] == "fx_reference_rates"]
    assert len(fx) == 1
    assert "BRL" in fx[0]["message"]
    assert "Settings" in fx[0]["message"], "says where to fix it"


def test_configured_rate_produces_no_fx_advisory():
    out = _setup_advisories(
        _settings_for({"BRL:USD": "0.192448"}),
        [_tx()],
        [_receipt("BRL")],
        has_coa=True,
    )
    assert "fx_reference_rates" not in _settings(out)


def test_same_currency_receipts_need_no_rate():
    out = _setup_advisories(
        _settings_for(), [_tx()], [_receipt("USD")], has_coa=True
    )
    assert "fx_reference_rates" not in _settings(out)


def test_absent_coa_is_announced():
    out = _setup_advisories(_settings_for(), [_tx()], [], has_coa=False)
    assert "card_entities" in _settings(out)


def test_resolved_coa_and_card_account_are_silent():
    out = _setup_advisories(
        _settings_for(card_account=True), [_tx()], [], has_coa=True
    )
    assert out == []


def test_unmapped_card_account_is_announced():
    out = _setup_advisories(_settings_for(), [_tx()], [], has_coa=True)
    assert "card_accounts" in _settings(out)


def test_each_missing_currency_is_counted_once():
    receipts = [_receipt("BRL", "d1"), _receipt("BRL", "d2"), _receipt("EUR", "d3")]
    out = _setup_advisories(_settings_for(), [_tx()], receipts, has_coa=True)
    fx = [a for a in out if a["setting"] == "fx_reference_rates"]
    assert len(fx) == 2, "one advisory per currency, not per receipt"
    assert "2 receipt(s)" in next(a["message"] for a in fx if "BRL" in a["message"])
