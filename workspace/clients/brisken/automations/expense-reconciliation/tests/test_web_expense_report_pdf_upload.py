"""Web .pdf RECEIPTS upload (2026-07-16, ER-PDF ingest).

The browser could only upload a receipts .csv; Chris's real artifact is
often the Zoho Expense report PDF. These cover the new web path: a
.pdf receipts upload is sniffed at `prepare_run` time and routed to the
`expense_report_pdf` source with no column map and no receipts_source
form flip required, mirroring the existing statement-PDF web wiring
(2026-06-16, test_web_pdf_upload.py).

Real ER PDFs are client financial data and are never committed; the
byte->text extraction (`_extract_text`, pypdf) is stubbed with
synthetic report text, verified against 5 real Brisken ER PDFs in
`test_expense_report_pdf.py`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import RunForm, prepare_run  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

SYNTHETIC_REPORT_TEXT = """\
Expense Report
ER-77001
EXPENSE SUMMARY

E100010-01 - Travel Expense: Ground Transport
S.No Expense Details Merchant Amount (USD)
1. 03/01/2026
Cab to the airport
Payment Mode : Credit Card
City Cab $50.00
Sub Total $50.00
REPORT SUMMARY BY CURRENCY
TOTAL USD
Total Expense Amount 50.00
Non Reimbursable Amount (-) 0.00
Advance Amount Received (-) 0.00
Total Reimbursable Amount $50.00
"""


def _run_form(**kw) -> RunForm:
    base = dict(
        account_id="amex",
        account_legal_entities={},
        account_card_currency="USD",
        sheet_name=None,
        column_map_overrides={},
        receipts_source="csv",  # deliberately wrong -- the .pdf sniff must override it
        expense_column_map={},
        receipts_default_currency="",
        use_llm=False,
    )
    base.update(kw)
    return RunForm(**base)


def test_prepare_run_sniffs_pdf_receipts_to_expense_report_pdf_source(tmp_path):
    prepared = prepare_run(
        tmp_path,
        statement_bytes=(EXAMPLES / "statement.example.csv").read_bytes(),
        statement_filename="statement.example.csv",
        receipts_bytes=b"%PDF-1.4 dummy",
        receipts_filename="expense-report.pdf",
        form=_run_form(),
        now_iso="2026-07-16T00:00:00",
        operator=None,
    )
    assert prepared.cfg["receipts"]["source"] == "expense_report_pdf"
    assert "column_map" not in prepared.cfg["receipts"]


def test_prepare_run_keeps_csv_source_for_csv_receipts(tmp_path):
    prepared = prepare_run(
        tmp_path,
        statement_bytes=(EXAMPLES / "statement.example.csv").read_bytes(),
        statement_filename="statement.example.csv",
        receipts_bytes=(EXAMPLES / "receipts.example.csv").read_bytes(),
        receipts_filename="receipts.example.csv",
        form=_run_form(),
        now_iso="2026-07-16T00:00:00",
        operator=None,
    )
    assert prepared.cfg["receipts"]["source"] == "csv"


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


def test_web_pdf_receipts_upload_parses_expense_summary(client, monkeypatch):
    monkeypatch.setattr(
        "expense_recon.ingest.expense_report_pdf._extract_text",
        lambda path: SYNTHETIC_REPORT_TEXT,
    )
    files = {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        ),
        "receipts": (
            "expense-report.pdf",
            b"%PDF-1.4 synthetic",
            "application/pdf",
        ),
    }
    resp = client.post(
        "/runs",
        files=files,
        data={
            "account_id": "amex",
            "account_card_currency": "USD",
            "receipts_source": "csv",  # must be overridden by the .pdf sniff
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    run_id = resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]

    run = _snapshot(client, run_id)
    assert run.config["receipts"]["source"] == "expense_report_pdf"

    receipts = run.snapshot["receipts"]
    assert len(receipts) == 1
    assert receipts[0]["report_number"] == "ER-77001"
    assert receipts[0]["detected_total"] == "50.00"
    assert receipts[0]["detected_currency"] == "USD"
    assert receipts[0]["detected_vendor"] == "City Cab"
