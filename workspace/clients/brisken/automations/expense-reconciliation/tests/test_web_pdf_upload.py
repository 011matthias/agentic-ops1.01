"""Web .pdf statement upload (2026-06-16, slice 2).

The browser could upload .csv / .xlsx statements (column-map auto-detected);
a Chase statement PDF was CLI-only. These cover the new web path: a .pdf
upload skips the column-map step, derives the account id per card from the
PDF's cycle markers, and preserves the foreign-currency detail.

Real Chase statements are client financial data and are never committed.
The byte->text extraction (`_extract_text`, pypdf) is stubbed with synthetic
Chase text — the same seam `parse_statement_text` exposes for the CLI tests —
so the whole web wiring runs without a real PDF binary.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import RunForm, _build_config, prepare_run  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# Synthetic two-card Chase statement: one plain charge + one foreign charge
# (with the two-line FX detail) on card 2838, one charge on card 3645. Mirrors
# the real statement's shape closely enough to exercise the full parser.
SYNTHETIC_PDF_TEXT = """\
Opening/Closing Date 01/04/26 - 02/03/26
ACCOUNT ACTIVITY
01/05 COFFEE SHOP NYC 5.75
01/06 HOTEL BERLIN 31.73
01/06 EURO
27.00 X 1.175185185 (EXCHG RATE)
TRANSACTIONS THIS CYCLE (CARD 2838) $37.48
01/10 AWS CLOUD SERVICES 100.00
TRANSACTIONS THIS CYCLE (CARD 3645) $100.00
"""


def _run_form(**kw) -> RunForm:
    base = dict(
        account_id="",
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


# ── unit: the config a PDF statement builds ──────────────────────────


def test_build_config_pdf_branch_omits_column_map():
    cfg = _build_config("chase.pdf", "receipts.csv", None, _run_form(), use_llm=False)
    stmt = cfg["statement"]
    assert "column_map" not in stmt          # PDF carries its own structure
    assert "account_id" not in stmt          # per-card id comes from the PDF
    assert stmt["legal_entity_id"]           # still derived from the account
    assert stmt["account_card_currency"] == "USD"


def test_build_config_csv_branch_keeps_column_map():
    cmap = {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"}
    cfg = _build_config("chase.csv", "receipts.csv", cmap, _run_form(account_id="amex"),
                        use_llm=False)
    stmt = cfg["statement"]
    assert stmt["column_map"] == cmap
    assert stmt["account_id"] == "amex"


def test_prepare_run_pdf_skips_column_map_autodetect(tmp_path):
    """A .pdf upload must not run (or fail) the CSV column-map auto-detect.
    prepare_run does not extract the PDF, so dummy bytes are fine here — the
    point is the branch builds a PDF-shaped config without raising."""
    prepared = prepare_run(
        tmp_path,
        statement_bytes=b"%PDF-1.4 dummy",
        statement_filename="chase-statement.pdf",
        receipts_bytes=(EXAMPLES / "receipts.example.csv").read_bytes(),
        receipts_filename="receipts.example.csv",
        form=_run_form(),
        now_iso="2026-06-16T00:00:00",
        operator=None,
    )
    assert "column_map" not in prepared.cfg["statement"]
    assert prepared.cfg["statement"]["legal_entity_id"]


# ── end-to-end: the web upload, extraction stubbed ───────────────────


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _snapshot(client, run_id) -> dict:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    db.close()
    return run


def test_web_pdf_upload_parses_multi_card_and_fx(client, monkeypatch):
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_text",
        lambda path: SYNTHETIC_PDF_TEXT,
    )
    files = {
        "statement": (
            "chase-statement.pdf",
            b"%PDF-1.4 synthetic",
            "application/pdf",
        ),
        "receipts": (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        ),
    }
    resp = client.post(
        "/runs",
        files=files,
        data={
            "account_id": "",  # no card name — the PDF supplies the cards
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    run_id = resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]

    run = _snapshot(client, run_id)
    # The statement was parsed by the PDF path, not the column-map path.
    assert "column_map" not in run.config["statement"]

    txs = run.snapshot["transactions"]
    assert len(txs) == 3
    # account ids came from the per-card cycle markers, not the (blank) form.
    assert {t["account_id"] for t in txs} == {"2838", "3645"}
    # the foreign charge kept its original-currency detail verbatim.
    fx = [t for t in txs if t["original_currency"]]
    assert len(fx) == 1
    assert fx[0]["original_currency"] == "EUR"
    assert fx[0]["original_amount"] == "27.00"
    assert fx[0]["fx_rate"] == "1.175185185"
