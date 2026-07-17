"""MatchingConfig file-loading (2026-07-17, optimize-loop prep).

The shipped config/match-tuning.json is the optimize-loop's writable
asset; these tests pin its contract: it loads, it exactly mirrors the
code defaults (drift alarm), unknown keys refuse, and the blend
weights actually steer the triage score.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from expense_recon.matching.deterministic import MatchingConfig, _blend_score

TUNING_FILE = (
    Path(__file__).parent.parent / "config" / "match-tuning.json"
)


def test_shipped_tuning_file_mirrors_code_defaults():
    """The asset file and the dataclass defaults are two spellings of
    one truth; if a default moves without the file (or vice versa),
    this is the alarm."""
    assert MatchingConfig.from_file(TUNING_FILE) == MatchingConfig()


def test_from_dict_parses_types():
    cfg = MatchingConfig.from_dict(
        {
            "amount_probable_tolerance_pct": "0.10",
            "date_probable_window_days": 7,
            "blend_amount_weight": 0.70,
            "fx_rate_bands": {"EUR:USD": ["1.05", "1.30"]},
            "card_scoping": False,
        }
    )
    assert cfg.amount_probable_tolerance_pct == Decimal("0.10")
    assert cfg.date_probable_window_days == 7
    assert cfg.blend_amount_weight == 0.70
    assert cfg.fx_band("EUR", "USD") == (Decimal("1.05"), Decimal("1.30"))
    assert cfg.fx_band("BRL", "USD") is None  # file bands REPLACE defaults
    assert cfg.card_scoping is False
    # untouched fields keep their defaults
    assert cfg.date_exact_window_days == 1


def test_from_dict_rejects_unknown_key():
    with pytest.raises(ValueError, match="unknown matching-tuning key"):
        MatchingConfig.from_dict({"amount_exact_tolerancy": "0.00"})


def test_from_dict_rejects_malformed_band_key():
    with pytest.raises(ValueError, match="FROM:TO"):
        MatchingConfig.from_dict({"fx_rate_bands": {"EURUSD": ["1", "2"]}})


def test_blend_weights_steer_triage_score():
    base = MatchingConfig()
    assert _blend_score(1.0, 0.0, 0.0, base) == 55
    all_amount = replace(
        base, blend_amount_weight=1.0, blend_date_weight=0.0,
        blend_vendor_weight=0.0,
    )
    assert _blend_score(1.0, 0.0, 0.0, all_amount) == 100
    assert _blend_score(0.0, 1.0, 1.0, all_amount) == 0
