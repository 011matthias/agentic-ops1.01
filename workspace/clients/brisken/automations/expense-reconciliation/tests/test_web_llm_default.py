"""Hosted runs use the LLM (and let the tool's own category + account win)
by default.

The SPA upload path used to run deterministic-only unless the operator ticked
a checkbox, which is why an uploaded run looked like it merely 'copied' the
report's categories. The hosted default is now LLM-on (a key is set on the
server) with `categorization.override_er_category`. These assert the wiring at
`prepare_run` / `_build_config` granularity, so NO real OpenAI call is made
(prepare_run resolves config but never runs the pipeline).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from expense_recon.web.service import (  # noqa: E402
    RunForm,
    _build_config,
    _default_llm_on,
    _override_er_category_on,
    prepare_run,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

_CMAP = {"transaction_date": "Date", "amount": "Amount", "vendor": "Merchant"}


def _run_form(**kw) -> RunForm:
    base = dict(
        account_id="amex-9001",
        account_legal_entities={},
        account_card_currency="USD",
        sheet_name=None,
        column_map_overrides={},
        receipts_source="csv",
        expense_column_map={},
        receipts_default_currency="",
        use_llm=False,
    )
    base.update(kw)
    return RunForm(**base)


def _prepare(tmp_path, **form_kw):
    return prepare_run(
        tmp_path,
        statement_bytes=(EXAMPLES / "statement.example.csv").read_bytes(),
        statement_filename="statement.example.csv",
        receipts_bytes=(EXAMPLES / "receipts.example.csv").read_bytes(),
        receipts_filename="receipts.example.csv",
        form=_run_form(**form_kw),
        now_iso="2026-07-21T00:00:00",
        operator=None,
    )


# ── env toggles ──────────────────────────────────────────────────────


def test_default_llm_on_unless_opted_out(monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_DEFAULT_LLM", raising=False)
    assert _default_llm_on() is True
    monkeypatch.setenv("EXPENSE_RECON_DEFAULT_LLM", "0")
    assert _default_llm_on() is False


def test_override_er_category_on_unless_opted_out(monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_OVERRIDE_ER_CATEGORY", raising=False)
    assert _override_er_category_on() is True
    monkeypatch.setenv("EXPENSE_RECON_OVERRIDE_ER_CATEGORY", "0")
    assert _override_er_category_on() is False


# ── _build_config block injection ────────────────────────────────────


def test_build_config_injects_categorization_when_overriding(monkeypatch):
    # WS2: vision_receipts is on by default alongside override_er_category
    # whenever the LLM is effective.
    monkeypatch.delenv("EXPENSE_RECON_VISION_RECEIPTS", raising=False)
    cfg = _build_config(
        "s.csv", "r.csv", _CMAP, _run_form(),
        use_llm=True, override_er_category=True,
    )
    # Two models on purpose (2026-08-24): reading a receipt and categorizing a
    # line of text are different calls, and only the reading was failing.
    assert cfg["llm"] == {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "vision_model": "gpt-5-mini",
    }
    assert cfg["categorization"] == {
        "override_er_category": True,
        "vision_receipts": True,
    }


def test_build_config_vision_receipts_opt_out(monkeypatch):
    """EXPENSE_RECON_VISION_RECEIPTS=0 drops vision from the categorization
    block while the override stays."""
    monkeypatch.setenv("EXPENSE_RECON_VISION_RECEIPTS", "0")
    cfg = _build_config(
        "s.csv", "r.csv", _CMAP, _run_form(),
        use_llm=True, override_er_category=True,
    )
    assert cfg["categorization"] == {"override_er_category": True}


def test_build_config_omits_both_blocks_by_default():
    cfg = _build_config("s.csv", "r.csv", _CMAP, _run_form(), use_llm=False)
    assert "llm" not in cfg
    assert "categorization" not in cfg


# ── prepare_run: default-on activates with a key, no OpenAI call ──────


def test_hosted_run_defaults_to_llm_with_key(tmp_path, monkeypatch):
    """Key present + checkbox NOT ticked -> the run uses the LLM AND overrides
    the ER category. No pipeline execution here, so the fake key is safe."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.delenv("EXPENSE_RECON_DEFAULT_LLM", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OVERRIDE_ER_CATEGORY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_VISION_RECEIPTS", raising=False)
    prepared = _prepare(tmp_path)  # use_llm=False
    assert prepared.use_llm_effective is True
    assert prepared.ai_unavailable is False  # not explicitly requested; key present
    assert prepared.cfg["llm"]["provider"] == "openai"
    # WS2: override + vision both default-on when the LLM is effective.
    assert prepared.cfg["categorization"] == {
        "override_er_category": True,
        "vision_receipts": True,
    }


def test_hosted_run_deterministic_without_key_no_notice(tmp_path, monkeypatch):
    """No key -> silent deterministic fallback; no llm/categorization blocks
    and NO 'AI unavailable' notice (the box was not ticked)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prepared = _prepare(tmp_path)  # use_llm=False, default-on
    assert prepared.use_llm_effective is False
    assert prepared.ai_unavailable is False  # not explicitly requested -> no banner
    assert "llm" not in prepared.cfg
    assert "categorization" not in prepared.cfg


def test_explicit_llm_request_without_key_flags_unavailable(tmp_path, monkeypatch):
    """Box ticked but no key -> deterministic + the 'AI unavailable' notice
    (the existing fall-back-when-no-key contract, unchanged)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prepared = _prepare(tmp_path, use_llm=True)
    assert prepared.use_llm_effective is False
    assert prepared.ai_unavailable is True


def test_default_llm_opt_out_stays_deterministic(tmp_path, monkeypatch):
    """EXPENSE_RECON_DEFAULT_LLM=0 + key present + box off -> deterministic."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    monkeypatch.setenv("EXPENSE_RECON_DEFAULT_LLM", "0")
    prepared = _prepare(tmp_path)
    assert prepared.use_llm_effective is False
    assert "llm" not in prepared.cfg
    assert "categorization" not in prepared.cfg
