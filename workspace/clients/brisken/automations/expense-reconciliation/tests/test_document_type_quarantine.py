"""Non-receipt quarantine (2026-08-13): a bank-statement page or an
expense-report summary page uploaded among the receipts must NOT become
an expense row.

Real trigger: Criss's May 2026 upload held 27 files, 7 of them Chase
statement PDFs; and the ER-00215 image set opens with the report's own
SUMMARY page, which the pipeline turned into a phantom 8,796.35 BRL
"expense" (1,837.51 USD on an earlier build — same page, either total).
The vision extractor now classifies every file (`document_type`) and
`generate_expenses` + the incremental batch add exclude any non-receipt
with a loud parse issue instead of exporting it.

Exclusion is deny-by-default in the SAFE direction: only an explicit
non-receipt classification excludes. An absent or junk classification
stays "receipt" — a phantom row is visible and deletable; a silently
dropped real receipt is money lost. Statement-mode `reconcile()` never
reads the field.
"""
from __future__ import annotations

import pytest

from expense_recon.cli import generate_expenses
from expense_recon.llm.client import (
    ExtractedReceipt,
    MockLLMClient,
    _extraction_from_payload,
)
from expense_recon.output.zoho_expense_export import build_expense_rows
from expense_recon.web.serialize import receipt_from_dict, receipt_to_dict


def _extraction(vendor="Uber", total="24.50", **overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-06-02", total=total, currency="USD", vendor=vendor,
        reference=None, line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _folder(tmp_path, names):
    folder = tmp_path / "receipts"
    folder.mkdir()
    for n in names:
        (folder / n).write_bytes(b"x")
    return folder


CFG = {
    "expense": {"legal_entity_id": "brisken-llc"},
    "receipts": {"path": "receipts", "default_currency": "USD"},
}


# ── payload parsing ──────────────────────────────────────────────────


def _payload(**overrides) -> dict:
    base = dict(
        date="2026-06-02", total="10.00", currency="USD", vendor="X",
        vendor_clean=None, reference=None, tax=None, tax_label=None,
        payment_hint=None, line_items=[], confidence=0.9, notes="",
    )
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("receipt", "receipt"),
        ("statement", "statement"),
        ("report_summary", "report_summary"),
        ("other", "other"),
        ("STATEMENT", "statement"),      # case-tolerant
        (None, "receipt"),               # absent -> safe default
        ("", "receipt"),
        ("invoice_maybe", "receipt"),    # junk -> safe default
        (42, "receipt"),
    ],
)
def test_payload_document_type_whitelist(raw, expected):
    payload = _payload()
    if raw is not None:
        payload["document_type"] = raw
    assert _extraction_from_payload(payload).document_type == expected


def test_extracted_receipt_defaults_to_receipt():
    """Old constructors (mocks, ER-image path) that never pass the field
    keep full pre-quarantine behavior."""
    assert _extraction().document_type == "receipt"


# ── generate_expenses: the quarantine itself ─────────────────────────


def test_generate_expenses_quarantines_non_receipts(tmp_path):
    """A statement page and a report-summary page in the folder produce
    NO expense rows; the one real receipt does. Each excluded file lands
    in parse_errors as a warning naming the file."""
    _folder(tmp_path, ["a_receipt.jpg", "b_statement.jpg", "c_summary.jpg"])
    client = MockLLMClient(extraction_responses=[
        _extraction(vendor="Uber"),
        _extraction(vendor=None, total="8796.35", document_type="statement"),
        _extraction(vendor=None, total="1837.51", document_type="report_summary"),
    ])

    result = generate_expenses(CFG, tmp_path, llm_client=client)

    assert [r.document_id for r in result.receipts] == ["a_receipt.jpg"]
    assert result.outcome.unmatched_receipts == ["a_receipt.jpg"]

    flagged = {f: (msg, sev) for f, _line, msg, sev in result.parse_errors}
    assert set(flagged) == {"b_statement.jpg", "c_summary.jpg"}
    for msg, sev in flagged.values():
        assert "not a purchase receipt" in msg
        assert "excluded" in msg
        assert sev == "warning"

    # The export sees only the real receipt: exactly one row, no phantom
    # 8,796.35 statement total anywhere.
    rows = build_expense_rows(result.receipts)
    assert len(rows) == 1
    assert not any("8796.35" in cell for row in rows for cell in row)


def test_generate_expenses_keeps_unclassified_files(tmp_path):
    """No classification (old mock, degraded model output) means NO
    exclusion: both files stay expenses. Exclusion must be earned by an
    explicit non-receipt classification."""
    _folder(tmp_path, ["a.jpg", "b.jpg"])
    client = MockLLMClient(extraction_responses=[
        _extraction(vendor="Uber"), _extraction(vendor="Amazon"),
    ])

    result = generate_expenses(CFG, tmp_path, llm_client=client)

    assert len(result.receipts) == 2
    assert result.parse_errors == []


def test_quarantined_file_never_reaches_the_categorizer(tmp_path):
    """The excluded file must not spend LLM categorization calls: the
    partition happens before the categorize pass."""
    _folder(tmp_path, ["a.jpg", "b_statement.jpg"])
    client = MockLLMClient(extraction_responses=[
        _extraction(vendor="Uber"),
        _extraction(vendor=None, document_type="statement"),
    ])

    generate_expenses(CFG, tmp_path, llm_client=client)

    categorize_calls = [
        args for name, args in client.calls if name == "classify_by_vendor"
    ]
    assert all("Uber" in str(args) for args in categorize_calls)


# ── snapshot round-trip ──────────────────────────────────────────────


# ── web layer: batch create + incremental add ────────────────────────


@pytest.fixture
def web_client(tmp_path, monkeypatch):
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def test_web_batch_create_quarantines_statement_page(web_client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Staples", total="42.50"),
        _extraction(vendor=None, total="8796.35", document_type="report_summary"),
    )
    resp = web_client.post(
        "/api/expense-batches",
        files=[
            ("files", ("a.jpg", JPG, "application/octet-stream")),
            ("files", ("summary.jpg", JPG + b"2", "application/octet-stream")),
        ],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    job = web_client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    grid = web_client.get(f"/api/expense-batches/{resp.json()['batch_id']}").json()
    assert grid["summary"]["n_expenses"] == 1
    assert {e["vendor"]["display"] for e in grid["expenses"]} == {"Staples"}
    quarantine = [
        i for i in grid["parse_issues"] if "not a purchase receipt" in i["message"]
    ]
    assert len(quarantine) == 1
    assert "summary.jpg" in quarantine[0]["file"]


def test_web_incremental_add_quarantines_statement_page(web_client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(vendor="Staples"))
    resp = web_client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
    )
    batch_id = resp.json()["batch_id"]
    job = web_client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    _patch_ocr(
        monkeypatch,
        _extraction(vendor=None, total="1234.00", document_type="statement"),
    )
    resp = web_client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("chase_page.jpg", JPG + b"3", "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    job = web_client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    grid = web_client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["summary"]["n_expenses"] == 1  # the statement page never joined
    ingest = grid["expense_ingest"]
    assert ingest["n_added"] == 0
    assert any("not a purchase receipt" in i for i in ingest["issues"])


# ── snapshot round-trip ──────────────────────────────────────────────


def _receipt_dict(**overrides) -> dict:
    base = dict(
        document_id="x.jpg", legal_entity_id="e", detected_date=None,
        detected_total=None, detected_currency=None, detected_vendor=None,
        detected_reference=None, line_items=[],
    )
    base.update(overrides)
    return base


def test_serialize_round_trips_document_type():
    r = receipt_from_dict(
        receipt_to_dict(receipt_from_dict(_receipt_dict(document_type="statement")))
    )
    assert r.document_type == "statement"


def test_serialize_defaults_legacy_snapshots_to_receipt():
    """Pre-2026-08-13 snapshots have no document_type key; they must load
    as plain receipts."""
    assert receipt_from_dict(_receipt_dict()).document_type == "receipt"
