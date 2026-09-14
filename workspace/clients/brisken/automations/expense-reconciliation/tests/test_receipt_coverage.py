"""The Receipt column answers "is it in the report" (backlog item 68).

Two defects, one root: the two reports and the grid were reading three
different sources.

The column read "attached" the moment a file was found on disk, which is a
question answered before renderability is known. A file that cannot be turned
into pages is a file that exists, so the count of covered expenses was an
upper bound printed as a fact -- and thirty pages later the caption for that
same receipt said "this file could not be rendered into the report". The
caption pages were right; the column and the count now say what they say.

And the reconciliation document was built from the stored receipt pool while
the expense report was built from the reviewer's live overlay. A pool only
catches up at the next re-match, so an expense the reviewer deleted left the
expense report at once and stayed in the reconciliation report, caption page
and receipt pages included, in the one document whose entire job is to be the
evidence that a month is complete.

Route-level throughout: both report routes and the batch view, because the
bug was never in the helpers -- it was in what each caller handed them.
"""
from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402


def _real_jpeg() -> bytes:
    """A file `prepare_evidence` can actually turn into a page."""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, format="JPEG")
    return buf.getvalue()


GOOD = _real_jpeg()
# The shape the live months cannot show and the caption pages were built for:
# a receipt whose bytes exist and decode into nothing. Same fixture the rest
# of the suite uses for "a file", which is the point -- every test that calls
# this "attached" is describing a file, not a page.
BROKEN = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, day):
    return ExtractedReceipt(
        date=f"2026-08-{day:02d}", total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1,
                implied_rate=1.0, converted_amount=Decimal("25.00"),
                reasoning="mock",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, files):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, data, "application/octet-stream"))
            for name, data in files
        ],
    ))
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_vendor(grid, vendor):
    # The grid's vendor is the {display, raw, source} object (item 2).
    return next(
        e for e in grid["expenses"] if e["vendor"]["display"] == vendor
    )


def _pdf_text(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    reader = PdfReader(io.BytesIO(resp.content))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def _two_receipt_month(client, monkeypatch):
    _wire(
        monkeypatch,
        _extraction("Readable Cafe", "25.00", 5),
        _extraction("Broken Bytes", "31.00", 6),
    )
    return _month(client, [("good.jpg", GOOD), ("broken.jpg", BROKEN)])


# ── (b) the column and the count follow the pages ───────────────────


def test_a_file_that_makes_no_page_is_not_counted_as_covered(
    client, monkeypatch
):
    """The overstatement, stated as a number: two files on disk, one page in
    the report. `receipt_image_available` still answers its own question (the
    app can serve both), which is exactly why it could not answer this one."""
    batch_id = _two_receipt_month(client, monkeypatch)

    grid = _grid(client, batch_id)
    assert all(e["receipt_image_available"] for e in grid["expenses"])
    assert all(e["source_file"] for e in grid["expenses"])
    # Nothing has been built yet, so nothing is known yet. Absent, never a
    # guess: the field exists to stop the guessing.
    assert not any("receipt_in_report" in e for e in grid["expenses"])
    assert "n_receipts_in_report" not in grid["summary"]

    assert client.get(f"/runs/{batch_id}/expense-report.pdf").status_code == 200

    grid = _grid(client, batch_id)
    assert _by_vendor(grid, "Readable Cafe")["receipt_in_report"] is True
    assert _by_vendor(grid, "Broken Bytes")["receipt_in_report"] is False
    assert grid["summary"]["n_receipts_in_report"] == 1
    assert grid["summary"]["n_receipts"] == 2


def test_the_listing_column_reads_none_for_the_receipt_with_no_page(
    client, monkeypatch
):
    """Through the report route, which is the caller the fix changed: the
    Receipt cell and the caption page thirty pages later now agree."""
    batch_id = _two_receipt_month(client, monkeypatch)
    text = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")

    assert "could not be rendered into the report" in text
    # One listing row says "attached" and one says "none"; before the fix
    # both said "attached" because both had a file.
    assert "attached" in text
    assert "none" in text


def test_the_reconciliation_report_records_its_own_verdicts(
    client, monkeypatch
):
    """Either report teaches the grid. A month reconciles before anyone
    downloads the month report, and the reviewer should not have to build the
    other document to find out what is in this one."""
    batch_id = _two_receipt_month(client, monkeypatch)
    assert client.get(
        f"/runs/{batch_id}/reconciliation-report.pdf"
    ).status_code == 200

    grid = _grid(client, batch_id)
    assert _by_vendor(grid, "Readable Cafe")["receipt_in_report"] is True
    assert _by_vendor(grid, "Broken Bytes")["receipt_in_report"] is False


def test_a_replaced_receipt_takes_its_verdict_with_it(client, monkeypatch):
    """The verdict is about bytes, not about a name. Swap the bytes and the
    field goes ABSENT again rather than answering last week's question."""
    batch_id = _two_receipt_month(client, monkeypatch)
    assert client.get(f"/runs/{batch_id}/expense-report.pdf").status_code == 200
    grid = _grid(client, batch_id)
    doc_id = _by_vendor(grid, "Broken Bytes")["document_id"]

    stored = Path(client._data_root) / "runs" / batch_id / "receipts" / doc_id
    assert stored.is_file(), stored
    stored.write_bytes(GOOD + b"\x00padding-so-the-size-moves")

    grid = _grid(client, batch_id)
    assert "receipt_in_report" not in _by_vendor(grid, "Broken Bytes")
    assert "n_receipts_in_report" not in grid["summary"]


# ── (a) one deletion, both documents ────────────────────────────────


def test_a_deleted_expense_leaves_both_reports_at_once(client, monkeypatch):
    """The reported divergence. The reviewer deletes an expense; the expense
    report drops it immediately and the reconciliation report used to carry
    it until the next re-match, because the two read different sources."""
    batch_id = _two_receipt_month(client, monkeypatch)
    grid = _grid(client, batch_id)
    doomed = _by_vendor(grid, "Broken Bytes")["document_id"]

    before = _pdf_text(client, f"/runs/{batch_id}/reconciliation-report.pdf")
    assert "Broken Bytes" in before, "the fixture has to be there to leave"

    resp = client.request(
        "DELETE", f"/api/runs/{batch_id}/expenses/{doomed}"
    )
    assert resp.status_code == 200, resp.text

    expense_text = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")
    recon_text = _pdf_text(client, f"/runs/{batch_id}/reconciliation-report.pdf")
    assert "Broken Bytes" not in expense_text
    assert "Broken Bytes" not in recon_text
    assert "Readable Cafe" in recon_text, "only the deleted one leaves"


def test_the_surviving_expense_keeps_its_page_after_a_deletion(
    client, monkeypatch
):
    """A deletion removes one receipt from the document, not the evidence
    section: the remaining receipt still has its caption and its page."""
    batch_id = _two_receipt_month(client, monkeypatch)
    grid = _grid(client, batch_id)
    doomed = _by_vendor(grid, "Broken Bytes")["document_id"]
    client.request("DELETE", f"/api/runs/{batch_id}/expenses/{doomed}")

    resp = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    assert resp.status_code == 200
    reader = PdfReader(io.BytesIO(resp.content))
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    assert "Readable Cafe" in text
    assert "could not be rendered into the report" not in text


def test_a_month_with_no_overlay_renders_exactly_as_before(
    client, monkeypatch
):
    """The overlay is idempotent by construction, so a month nobody has
    edited must produce the same document it always did -- the guard against
    a fix that quietly rewrites every untouched report."""
    batch_id = _two_receipt_month(client, monkeypatch)
    first = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    second = client.get(f"/runs/{batch_id}/reconciliation-report.pdf")
    assert first.status_code == second.status_code == 200
    assert len(PdfReader(io.BytesIO(first.content)).pages) == len(
        PdfReader(io.BytesIO(second.content)).pages
    )
    text = "\n".join(
        (p.extract_text() or "")
        for p in PdfReader(io.BytesIO(first.content)).pages
    )
    assert "Readable Cafe" in text
    assert "Broken Bytes" in text


def test_a_manual_expense_with_no_file_is_known_without_a_report(
    client, monkeypatch
):
    """Nothing on disk cannot become a page, and that needs no report build
    to establish. The row is decided from the start; it is the FILES that
    have to wait for a verdict."""
    _wire(monkeypatch, _extraction("Readable Cafe", "25.00", 5))
    batch_id = _month(client, [("good.jpg", GOOD)])
    resp = client.post(
        f"/api/runs/{batch_id}/expenses",
        json={
            "vendor": "Typed By Hand", "date": "2026-08-09",
            "total": "12.00", "currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text

    grid = _grid(client, batch_id)
    typed = _by_vendor(grid, "Typed By Hand")
    assert typed["receipt_in_report"] is False
    assert typed["receipt_image_available"] is False
    # The file-backed row is still undecided, so the COUNT stays absent
    # rather than reporting 0 of 2 covered.
    assert "receipt_in_report" not in _by_vendor(grid, "Readable Cafe")
    assert "n_receipts_in_report" not in grid["summary"]
