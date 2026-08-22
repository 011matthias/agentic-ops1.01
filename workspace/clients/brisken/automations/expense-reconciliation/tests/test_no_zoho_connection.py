"""The app holds no live connection to Zoho (owner directive 2026-08-22:
"zoho does not matter anymore, the app should have no connection or ties to
zoho anymore").

This guard is about the CONNECTION, not the vocabulary. What it forbids:

* an HTTP client aimed at a Zoho host (`zohoapis`, `accounts.zoho`),
* reading `ZOHO_*` credentials from the environment,
* an importable `expense_recon.zoho` package or a journal-posting CLI.

What it deliberately allows, for now: the words "zoho" and `zoho_account` in
field names, export filenames, and the chart-of-accounts file the operator
supplies. Those are naming, they are read by the SPA, and renaming them is a
coordinated round with its own Lovable prompt. The connection is what had to
go first, and it is what this test keeps gone.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "expense_recon"

# A network call to Zoho, or the credentials that would authorize one.
FORBIDDEN = (
    re.compile(r"zohoapis", re.I),
    re.compile(r"accounts\.zoho", re.I),
    re.compile(r"books\.zoho", re.I),
    re.compile(r"\bZOHO_(CLIENT_ID|CLIENT_SECRET|REFRESH_TOKEN|ORG_ID|DC|"
               r"API_DOMAIN|ACCOUNTS_DOMAIN|BOOKS_REFRESH_TOKEN)\b"),
)


def _sources() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_module_talks_to_a_zoho_host_or_reads_zoho_credentials():
    hits: list[str] = []
    for path in _sources():
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in FORBIDDEN:
                if pattern.search(line):
                    rel = path.relative_to(SRC)
                    hits.append(f"{rel}:{line_no}: {line.strip()[:100]}")
    assert not hits, "live Zoho connection surface still present:\n" + "\n".join(hits)


def test_the_zoho_api_package_is_gone():
    assert not (SRC / "zoho").exists(), "src/expense_recon/zoho/ still exists"
    assert not (SRC / "zoho_post_cli.py").exists(), "zoho_post_cli.py still exists"
    with pytest.raises(ModuleNotFoundError):
        __import__("expense_recon.zoho.client")


def test_no_cli_subcommand_posts_to_or_seeds_from_zoho():
    # The QUOTED literal is the command's registration or dispatch; the name
    # in backticks is prose recording that it used to exist, which must stay
    # readable in the module docstring.
    cli = (SRC / "cli.py").read_text(encoding="utf-8")
    assert '"zoho-post"' not in cli, "the zoho-post subcommand still dispatches"
    memory_cli = (SRC / "learning_cli.py").read_text(encoding="utf-8")
    assert '"seed-zoho"' not in memory_cli, "the seed-zoho subcommand still exists"


def test_a_run_config_cannot_ask_for_a_live_chart_pull():
    """`coa_source: "api"` was the one config value that reached out to Zoho
    mid-run. A chart now comes from a file the operator controls, or not at
    all."""
    cli = (SRC / "cli.py").read_text(encoding="utf-8")
    assert 'source == "api"' not in cli
    assert "ZohoClient" not in cli
