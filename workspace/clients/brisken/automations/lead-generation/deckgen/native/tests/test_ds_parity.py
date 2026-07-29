"""Parity gate: the native deck engine's base tokens must match the canonical
Brisken Design System (the `brisken-design` skill), so the deck surface can
never silently drift from the brand source Dirk codified with DesignSync.

    uv run --no-project --with 'pytest>=8.0' --with python-pptx \
        pytest -q native/tests/test_ds_parity.py

Scope: the shared base ramp + the `overview` palette, which mirror the DS brand
(ink + teal). The per-product deck accents (market-data-hub green, commodities
rust, ...) are engine-owned deck identities NOT present in the DS, so they are
deliberately excluded from the parity check.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

NATIVE = Path(__file__).resolve().parents[1]
REPO = NATIVE.parents[6]
COLORS_CSS = REPO / ".claude" / "skills" / "brisken-design" / "tokens" / "colors.css"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


T = _load("tokens", NATIVE / "tokens.py")

# engine base-token constant -> the DS custom-property it must equal
BASE_MAP = {
    "INK": "brisken-ink-900",
    "PAPER": "brisken-white",
    "NEUTRAL": "brisken-surface-100",
    "MUTED": "brisken-slate-600",
    "FAINT": "brisken-slate-400",
    "LINE": "brisken-line-200",
    "ONINK": "brisken-surface-050",
    "ONINK_SUB": "brisken-slate-300",
    "NEUTRAL_DK": "brisken-ink-800",
}
# the teal-brand "overview" palette -> the DS teal
OVERVIEW_MAP = {"accent": "brisken-teal-600", "bright": "brisken-teal-400"}

_VAR = re.compile(r"--([a-z0-9-]+):\s*#([0-9A-Fa-f]{6})")


def _ds_tokens() -> dict[str, str]:
    assert COLORS_CSS.is_file(), f"canonical DS tokens missing: {COLORS_CSS}"
    return {name: hexv.upper()
            for name, hexv in _VAR.findall(COLORS_CSS.read_text(encoding="utf-8"))}


@pytest.fixture(scope="module")
def ds() -> dict[str, str]:
    return _ds_tokens()


@pytest.mark.parametrize("const,var", sorted(BASE_MAP.items()))
def test_base_token_matches_ds(ds, const, var):
    assert var in ds, f"DS colors.css has no --{var}"
    engine = str(getattr(T, const)).upper()
    assert engine == ds[var], (
        f"{const}={engine} drifts from DS --{var}={ds[var]}; "
        "the brisken-design skill is canonical (align tokens.py + DESIGN.md)")


@pytest.mark.parametrize("field,var", sorted(OVERVIEW_MAP.items()))
def test_overview_palette_matches_ds(ds, field, var):
    assert var in ds, f"DS colors.css has no --{var}"
    engine = str(getattr(T.PALETTES["overview"], field)).upper()
    assert engine == ds[var], (
        f"overview.{field}={engine} drifts from DS --{var}={ds[var]}")
