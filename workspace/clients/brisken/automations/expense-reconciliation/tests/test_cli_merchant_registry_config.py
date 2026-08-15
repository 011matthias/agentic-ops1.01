"""CLI merchant-registry wiring (backlog item 2).

The hosted app builds its MerchantRegistry from settings["merchants"];
CLI runs used to call generate_expenses() bare (registry=None), so
offline quality checks judged the tool WITHOUT the canonicalization
Criss actually gets. These tests pin the fix: a run config can carry
`expense.merchants` (inline) or `expense.merchants_path` (JSON file),
and the canonical name reaches the exported Zoho CSV.

CI-safe via MockLLMClient (no API key, no network).
"""
from __future__ import annotations

import json

import pytest

from expense_recon.cli import (
    ConfigError,
    _build_cli_merchant_registry,
    run,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient
from expense_recon.merchant_registry import MerchantRegistry

RAW_VENDOR = "MEGA CENTRO COMERCIAL LTDA"
CANONICAL = "Mega Centro Comercial"
MERCHANTS = {CANONICAL: {"aliases": [RAW_VENDOR]}}


def test_build_cli_merchant_registry_inline(tmp_path):
    cfg = {"expense": {"legal_entity_id": "e", "merchants": MERCHANTS}}

    registry = _build_cli_merchant_registry(cfg, tmp_path)

    assert isinstance(registry, MerchantRegistry)
    match = registry.resolve(None, RAW_VENDOR)
    assert match is not None and match.canonical_name == CANONICAL


def test_build_cli_merchant_registry_from_bare_map_file(tmp_path):
    (tmp_path / "merchants.json").write_text(json.dumps(MERCHANTS), encoding="utf-8")
    cfg = {"expense": {"merchants_path": "merchants.json"}}

    registry = _build_cli_merchant_registry(cfg, tmp_path)

    assert registry is not None
    assert registry.resolve(None, RAW_VENDOR).canonical_name == CANONICAL


def test_build_cli_merchant_registry_from_settings_shaped_file(tmp_path):
    """A full settings dump (the `/api/settings` shape) works unmodified,
    so prod settings can be pointed at directly for parity runs."""
    settings = {"entities": {}, "merchants": MERCHANTS}
    (tmp_path / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    cfg = {"expense": {"merchants_path": "settings.json"}}

    registry = _build_cli_merchant_registry(cfg, tmp_path)

    assert registry is not None
    assert registry.resolve(None, RAW_VENDOR).canonical_name == CANONICAL


def test_no_merchants_config_returns_none(tmp_path):
    assert _build_cli_merchant_registry({"expense": {}}, tmp_path) is None
    assert _build_cli_merchant_registry({}, tmp_path) is None


def test_unreadable_merchants_path_is_loud(tmp_path):
    """A configured-but-broken name book must FAIL the run, not silently
    judge the tool without the feature built to fix naming."""
    cfg = {"expense": {"merchants_path": "no-such-file.json"}}

    with pytest.raises(ConfigError, match="merchants_path"):
        _build_cli_merchant_registry(cfg, tmp_path)


def test_malformed_merchants_is_loud(tmp_path):
    cfg = {"expense": {"merchants": ["not", "a", "map"]}}

    with pytest.raises(ConfigError, match="merchants"):
        _build_cli_merchant_registry(cfg, tmp_path)


def test_cli_run_exports_canonical_vendor(tmp_path, monkeypatch):
    """End to end through run(): a CLI expense-generation run with a
    merchants block exports the CANONICAL vendor name in the Zoho CSV,
    not whatever spelling the extractor produced this time."""
    from expense_recon import cli as cli_module

    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "mega.jpg").write_bytes(b"fake-jpeg-bytes")

    mock_client = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-04-02", total="1350.00", currency="BRL",
            vendor=RAW_VENDOR, reference="461017", line_items=(),
            confidence=0.9, notes="",
        ),
    ])

    def fake_openai_client(*, model, api_key, cost_tracker, vision_model=None):
        mock_client.cost_tracker = cost_tracker
        return mock_client

    monkeypatch.setattr(cli_module, "OpenAIClient", fake_openai_client)
    monkeypatch.setenv("FAKE_KEY", "sk-fake-for-test")
    monkeypatch.delenv("EXPENSE_RECON_EXTRACTION_CACHE", raising=False)

    cfg = {
        "mode": "expense_generation",
        "expense": {"legal_entity_id": "brisken-llc", "merchants": MERCHANTS},
        "receipts": {"path": "receipts", "source": "folder"},
        "llm": {"provider": "openai", "api_key_env": "FAKE_KEY"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    export_path = run(config_path)

    csv_text = export_path.read_text(encoding="utf-8")
    assert CANONICAL in csv_text
    assert RAW_VENDOR not in csv_text
