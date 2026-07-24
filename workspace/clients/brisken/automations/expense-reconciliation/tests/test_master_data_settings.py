"""Master data on the hosted surface (2026-07-22).

The 2026-07-22 hands-on test of the real April month (Chase activity CSV +
ER-00215) reconciled 0 of 94 transactions on the hosted app while the same
two files reconciled 29/36 locally from a config file. The cause was not the
matcher: the hosted run had nowhere to put the operator input the pipeline
needs, so the month's FX reference rates, the card -> legal-entity mapping,
and the card -> Zoho bank account were all absent from every hosted run.

These tests pin the three settings maps to the behaviour they restore.
"""
from __future__ import annotations

from decimal import Decimal

from expense_recon.web.service import (
    RunForm,
    apply_master_data,
    resolve_entity,
)


def _form(account_id: str = "2838", **kw) -> RunForm:
    base = dict(
        account_id=account_id,
        account_legal_entities={},
        account_card_currency="USD",
        sheet_name="",
        column_map_overrides={},
        receipts_source="expense_report_pdf",
        expense_column_map=None,
        receipts_default_currency="",
        use_llm=False,
    )
    base.update(kw)
    return RunForm(**base)


# ── card -> legal entity (the silent has_coa:false) ────────────────────


def test_entity_resolves_from_settings_map():
    """A typed card number maps to the entity whose chart guards the export.

    Without this the run resolved to the literal "2838", which matches no
    COA provisioning entity, so the gate never fired and the run came back
    has_coa:false with no warning."""
    settings = {"card_entities": {"2838": "Corporate Services"}}
    assert resolve_entity(_form("2838"), settings) == "Corporate Services"


def test_entity_matches_on_trailing_digits():
    """"card-2838" and "2838" name the same card."""
    settings = {"card_entities": {"2838": "Corporate Services"}}
    assert resolve_entity(_form("card-2838"), settings) == "Corporate Services"


def test_entity_falls_back_to_form_without_settings():
    """No master data => exactly the prior behaviour."""
    assert resolve_entity(_form("2838"), None) == "2838"
    assert resolve_entity(_form("2838"), {"card_entities": {}}) == "2838"


def test_entity_prefers_settings_over_form_mapping():
    form = _form("2838", account_legal_entities={"2838": "Stale Entity"})
    settings = {"card_entities": {"2838": "Corporate Services"}}
    assert resolve_entity(form, settings) == "Corporate Services"


# ── FX reference rates (the 0-of-94 cause) ─────────────────────────────


def test_fx_rates_inline_into_matching_block():
    """The month's rates ride in the run config, so they reach the matcher
    AND land in run.local.json for a faithful local repro."""
    settings = {"fx_reference_rates": {"BRL:USD": "0.192448"}}
    cfg = apply_master_data({"statement": {}}, _form(), settings)
    assert cfg["matching"]["fx_reference_rates"] == {"BRL:USD": "0.192448"}


def test_master_data_absent_leaves_config_untouched():
    cfg = {"statement": {}, "receipts": {}}
    assert apply_master_data(cfg, _form(), None) == cfg
    assert apply_master_data(cfg, _form(), {}) == cfg
    assert "matching" not in apply_master_data(cfg, _form(), {}), "no empty block"


def test_explicit_matching_block_is_not_clobbered():
    """An explicit run config wins over the stored default."""
    cfg = {"matching": {"fx_reference_rates": {"BRL:USD": "0.20"}}}
    out = apply_master_data(cfg, _form(), {"fx_reference_rates": {"BRL:USD": "0.19"}})
    assert out["matching"]["fx_reference_rates"] == {"BRL:USD": "0.20"}


# ── card -> Zoho bank account (the "card account unmapped" credit) ─────


def test_card_account_lands_in_zoho_block():
    settings = {"card_accounts": {"2838": "1010 Chase Corporate"}}
    cfg = apply_master_data({}, _form("2838"), settings)
    assert cfg["zoho"]["card_accounts"]["2838"] == "1010 Chase Corporate"
    # The fabricated block must declare "no chart source": without it,
    # _build_chart_of_accounts defaults to a live API pull and every hosted
    # upload dies on missing ZOHO_* credentials (2026-07-24 regression).
    assert cfg["zoho"]["coa_source"] == "none"


def test_card_account_ignores_a_different_card():
    settings = {"card_accounts": {"9999": "Other card"}}
    cfg = apply_master_data({}, _form("2838"), settings)
    assert "zoho" not in cfg


def test_card_account_keeps_an_explicit_chart_source():
    settings = {"card_accounts": {"2838": "1010 Chase Corporate"}}
    cfg = {"zoho": {"coa_source": "csv", "coa_csv_path": "chart.csv"}}
    out = apply_master_data(cfg, _form("2838"), settings)
    assert out["zoho"]["coa_source"] == "csv"


def test_master_data_zoho_block_skips_chart_pull(tmp_path, monkeypatch):
    """End-to-end pin: the settings-injected zoho block passes the chart
    builder without demanding Zoho API credentials, and card_accounts
    survives for the journal export."""
    from expense_recon.cli import _build_chart_of_accounts

    for var in (
        "ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN", "ZOHO_ORG_ID"
    ):
        monkeypatch.delenv(var, raising=False)
    settings = {"card_accounts": {"2838": "1010 Chase Corporate"}}
    cfg = apply_master_data({}, _form("2838"), settings)
    coa, zoho_cfg = _build_chart_of_accounts(cfg, tmp_path)
    assert coa is None
    assert zoho_cfg["card_accounts"]["2838"] == "1010 Chase Corporate"


# ── the matcher actually consumes an inline block ──────────────────────


def test_inline_rates_reach_matching_config():
    """The CLI reads inline `matching` keys, not only a tuning_path — the
    hosted surface has no tuning file on disk."""
    from expense_recon.matching.deterministic import MatchingConfig

    cfg = MatchingConfig.from_dict({"fx_reference_rates": {"BRL:USD": "0.192448"}})
    assert cfg.fx_reference_rates[("BRL", "USD")] == Decimal("0.192448")
