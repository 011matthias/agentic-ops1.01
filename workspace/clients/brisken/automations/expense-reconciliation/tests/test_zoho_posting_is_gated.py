"""Zoho posting exists again, and stays out of the hosted app's reach.

Supersedes `test_no_zoho_connection.py`, which enforced the 2026-08-22
directive ("zoho does not matter anymore, the app should have no connection
or ties to zoho anymore"). That directive is reversed: Dirk needs the
reconciled month imported into Zoho Books at month end, and the owner chose
API injection over a CSV hand-off (2026-09-22). So the client, the
idempotency ledger and the posting CLI are restored from `5e2ff99e^`.

Two of the old guard's four guarantees survive the reversal unchanged, and
they are the two that were load-bearing rather than vocabulary:

* **The hosted web app cannot post.** `web/` holds no Zoho import and reads
  no `ZOHO_*` credential, so nothing reachable from an HTTP request can
  write into Brisken's books. Posting is an operator-run CLI action behind
  the 4.8 gates. This is what keeps `feedback_recon_no_live_writes_criss_acts`
  and the invasive-action gate true in code rather than by intention: a
  deploy can never start writing to a client's live ledger.
* **A run config cannot pull a chart mid-run.** `coa_source: "api"` stays
  gone. The chart comes from a file the operator controls, so a month's
  account resolution is reproducible and cannot shift under a re-run.

What the old guard forbade and this one deliberately allows: an importable
`expense_recon.zoho` package, a Zoho host string, a `ZOHO_*` read in the CLI
layer, and the `zoho-post` subcommand. Those are the connection the owner
asked for.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "expense_recon"
WEB = SRC / "web"

# A network call to Zoho, or the credentials that would authorize one.
_ZOHO_SURFACE = (
    re.compile(r"zohoapis", re.I),
    re.compile(r"accounts\.zoho", re.I),
    re.compile(r"books\.zoho", re.I),
    re.compile(
        r"\bZOHO_(CLIENT_ID|CLIENT_SECRET|REFRESH_TOKEN|ORG_ID|DC|"
        r"API_DOMAIN|ACCOUNTS_DOMAIN|BOOKS_REFRESH_TOKEN)\b"
    ),
)
# The POSTING modules, reached by import from the web layer. Deliberately
# narrower than "any module with zoho in the name": the web layer imports
# `output.zoho_export` to serve the CSV download, which writes a file and
# reaches no network. What must never be importable from a request handler
# is the API client, the ledger, and the posting CLI.
_ZOHO_IMPORT = re.compile(
    r"^\s*(?:"
    r"from\s+\.*(?:expense_recon\.)?zoho(?:\.\w+)*\s+import"
    r"|import\s+(?:expense_recon\.)?zoho(?:\.\w+)*(?:\s|$)"
    r"|from\s+\.*(?:expense_recon\.)?zoho_post_cli\s+import"
    r"|import\s+(?:expense_recon\.)?zoho_post_cli\b"
    r")",
    re.M,
)


def _web_sources() -> list[Path]:
    return [p for p in WEB.rglob("*.py") if "__pycache__" not in p.parts]


def test_the_hosted_web_layer_never_reaches_zoho():
    """An HTTP request must not be able to write into Brisken's books."""
    hits: list[str] = []
    for path in _web_sources():
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in _ZOHO_SURFACE:
                if pattern.search(line):
                    hits.append(
                        f"{path.relative_to(SRC)}:{line_no}: {line.strip()[:100]}"
                    )
    assert not hits, (
        "the hosted web layer gained a Zoho connection surface:\n" + "\n".join(hits)
    )


def test_the_web_layer_does_not_import_the_posting_modules():
    hits: list[str] = []
    for path in _web_sources():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _ZOHO_IMPORT.search(text):
            hits.append(str(path.relative_to(SRC)))
    assert not hits, (
        "web modules import the Zoho posting path; posting must stay a "
        "CLI-only action behind the 4.8 gates:\n" + "\n".join(hits)
    )


def test_the_import_guard_discriminates():
    """The guard above is only worth its green if it can go red. A pattern
    that matched nothing would pass forever and protect nothing, and a
    pattern that matched everything would have to be deleted the first time
    the web layer touched the CSV export. Both directions are pinned here."""
    must_catch = (
        "from ..zoho.client import ZohoClient",
        "from ..zoho.idempotent import PostLedger",
        "from .zoho import client",
        "import expense_recon.zoho.client",
        "from ..zoho_post_cli import main",
    )
    must_ignore = (
        # The CSV artifact builder: writes a file, reaches no network.
        "from ..output.zoho_export import ZOHO_COLUMNS",
        "from ..output.zoho_expense_export import EXPENSE_COLUMNS",
        # Vocabulary, not a connection.
        "from ..learning.consult import ZOHO_SEED_PREFIX",
        '        "zoho.csv",',
    )
    for line in must_catch:
        assert _ZOHO_IMPORT.search(line), f"guard missed a real import: {line!r}"
    for line in must_ignore:
        assert not _ZOHO_IMPORT.search(line), f"guard false-positived on: {line!r}"


def test_a_run_config_cannot_ask_for_a_live_chart_pull():
    """`coa_source: "api"` was the one config value that reached out to Zoho
    mid-run. A chart comes from a file the operator controls, so a month's
    account resolution is reproducible across re-runs."""
    cli = (SRC / "cli.py").read_text(encoding="utf-8")
    assert 'source == "api"' not in cli
    assert "ZohoClient" not in cli


def test_posting_is_off_unless_every_gate_is_open():
    """The posting CLI must require all four gates, not any one of them:
    the config flag, the env flag, an org allowlist, and an explicit --go.
    Reading the source is the cheap half; `test_zoho_post_cli.py` drives the
    behavior."""
    cli = (SRC / "zoho_post_cli.py").read_text(encoding="utf-8")
    for token in ("zoho.post.enabled", "EXPENSE_RECON_ZOHO_POST", "--go"):
        assert token in cli, f"posting gate {token!r} is missing from the CLI"
