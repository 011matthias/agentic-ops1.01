"""The org allowlist admits the sandbox without loosening production.

TEST-BTS was added 2026-09-22 so integration runs can write real
expenses and read them back without touching live books. The risk that
buys is narrow but real: the sandbox is a CLONE of a production org, so
nothing about its id or its chart announces that it is not production.
These tests pin the properties that keep the addition safe.
"""
from __future__ import annotations

from expense_recon.zoho.idempotent import (
    DEFAULT_ORG_ALLOWLIST,
    PRODUCTION_ORG_IDS,
    SANDBOX_ORG_ID,
)


def test_sandbox_is_allowed():
    assert SANDBOX_ORG_ID in DEFAULT_ORG_ALLOWLIST


def test_the_two_production_orgs_are_still_allowed():
    assert {"822741658", "697686691"} <= DEFAULT_ORG_ALLOWLIST


def test_the_sandbox_is_not_a_production_org():
    """The two sets stay disjoint, so code that needs to treat a
    rehearsal differently from the real books has something to ask."""
    assert SANDBOX_ORG_ID not in PRODUCTION_ORG_IDS


def test_the_allowlist_is_exactly_these_three():
    """An allowlist is only as good as its smallness. A fourth org
    appearing here should fail a test, not slip through review."""
    assert DEFAULT_ORG_ALLOWLIST == {"822741658", "697686691", "822116290"}


def test_a_run_config_can_only_narrow_the_allowlist():
    """The CLI intersects rather than unions, so a config file cannot add
    an org the code never reviewed. Pinned because the whole safety
    argument for naming orgs in code rests on it."""
    src = __import__("pathlib").Path(
        __file__
    ).resolve().parent.parent / "src" / "expense_recon" / "zoho_post_cli.py"
    text = src.read_text(encoding="utf-8")
    assert "allowlist &= frozenset(" in text, (
        "the run config must INTERSECT the default allowlist; a union or "
        "replacement would let a config file authorize a new org"
    )
