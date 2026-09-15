"""Backlog item 67: one unrenderable receipt used to cost the whole month.

The renderability test opened a PDF's index and nothing else, so a
password-protected or structurally damaged receipt passed it, then raised
while the document was being assembled. The request 500ed and the period
produced NO report at all: no caption, no partial output, nothing naming the
offending file, and the month stayed unreproducible until somebody removed
the file by hand (`docs/electronic-storage-system-description.md` 7.3).

Pinned here, all route-level through `GET /runs/{id}/expense-report.pdf`:

* The fixtures really do defeat the OLD check. `PdfReader(BytesIO(...))`
  constructs fine on both of them and only page access raises; a fixture that
  failed the constructor would prove nothing about this bug.
* A blocked receipt costs its own pages and nothing else: 200, the other
  receipt's pages present, a caption naming the file and the reason.
* The reviewer can see it from the screen: `expenses[].receipt_render` and
  `summary.n_receipts_unrenderable`, both ABSENT until a report was built,
  because renderability is not knowable before then.
* Assembly is bounded: a receipt with more pages than `MAX_RECEIPT_PAGES`
  contributes the cap, not its page count, and its caption says so.

Ingest tolerance does not cover any of this. `receipts_folder` already skips a
file whose extraction raises, and `_pdf_text` reads at most four pages, so a
PDF damaged on page five is extracted happily and only ever breaks here. The
fixtures damage the STORED bytes after ingest, which is the shape the failure
takes in production: a file that was readable when it arrived.
"""
from __future__ import annotations

import io
import re

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pypdf = pytest.importorskip("pypdf")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output._pdf_common import MAX_RECEIPT_PAGES  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _pdf(n_pages: int = 1, text: str = "RECEIPT") -> bytes:
    """A real receipt PDF. The line is long on purpose: over
    `receipts_folder.MIN_PDF_TEXT_CHARS` the text layer is enough and ingest
    never needs to rasterize."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(n_pages):
        c.drawString(
            60, 700,
            f"{text} page {i + 1}: total 42.50 USD, paid by card, thank you"
        )
        c.showPage()
    c.save()
    return buf.getvalue()


def _encrypted_pdf() -> bytes:
    """A password-protected receipt: the index reads, the pages do not. This
    is the file that used to take the month's report down."""
    w = pypdf.PdfWriter(clone_from=io.BytesIO(_pdf(text="SECRET")))
    w.encrypt("owner-password")
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _damaged_pdf() -> bytes:
    """A receipt whose page tree is broken: the first `/Kids` entry is
    repointed at an object that is not a page, in place, so every byte offset
    the xref holds stays valid and the trailer still parses."""
    good = _pdf(n_pages=2)
    m = re.search(rb"/Kids\s*\[\s*(\d+) 0 R", good)
    assert m is not None, "reportlab page tree shape changed"
    return good[:m.start(1)] + b"9" * len(m.group(1)) + good[m.end(1):]


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch_with_two_receipts(client, monkeypatch) -> str:
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Staples"),
        _extraction(vendor="Trenitalia", total="18.00"),
    )
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": "August 2026"})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"
    files = [
        ("files", ("staples.pdf", _pdf(text="STAPLES"), "application/pdf")),
        ("files", ("tren.pdf", _pdf(text="TRENITALIA"), "application/pdf")),
    ]
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"
    return batch_id


def _receipts_dir(client, batch_id):
    from pathlib import Path

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    return Path(run.work_dir) / "receipts"


def _replace_stored_bytes(client, batch_id, doc_id: str, data: bytes) -> None:
    (_receipts_dir(client, batch_id) / doc_id).write_bytes(data)


def _shown(doc_id: str) -> str:
    """The name a caption prints: the upload's own filename, without the
    spool prefix (`service._display_name`)."""
    return re.sub(r"^\d{4}__", "", doc_id)


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _docs(client, batch_id) -> list[str]:
    return [e["document_id"] for e in _grid(client, batch_id)["expenses"]]


def _text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


# ── the instrument: do the fixtures actually defeat the old check? ───────


def test_the_encrypted_fixture_passes_an_index_only_check():
    """The premise. A fixture that failed `PdfReader(...)` would be exercising
    the path that always worked."""
    enc = _encrypted_pdf()
    reader = pypdf.PdfReader(io.BytesIO(enc))  # the OLD renderability test
    assert reader.is_encrypted
    with pytest.raises(Exception):
        list(reader.pages)


def test_the_damaged_fixture_survives_everything_short_of_the_page_copy():
    """Sharper than the encrypted case, and the reason `probe_pdf` copies
    pages rather than counting them: this file constructs AND enumerates its
    pages. Only copying a page into a writer, which is the one thing assembly
    does, raises. A probe that stopped at `len(reader.pages)` would pass it
    and the month would still be losing its report."""
    dmg = _damaged_pdf()
    reader = pypdf.PdfReader(io.BytesIO(dmg))
    assert not reader.is_encrypted
    pages = list(reader.pages)  # enumerates fine
    assert pages
    with pytest.raises(Exception):
        writer = pypdf.PdfWriter()
        for page in pages:
            writer.add_page(page)


# ── the month survives ──────────────────────────────────────────────────


def test_encrypted_receipt_does_not_cost_the_month_its_report(
    client, monkeypatch
):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    _replace_stored_bytes(client, batch_id, docs[0], _encrypted_pdf())

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text[:400]
    text = _text(resp.content)
    # the file is named, with the reason, on its own caption page
    assert _shown(docs[0]) in text
    assert "password-protected" in text
    # and the OTHER receipt's own page still made it into the document
    assert "TRENITALIA page 1" in text


def test_damaged_receipt_does_not_cost_the_month_its_report(
    client, monkeypatch
):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    _replace_stored_bytes(client, batch_id, docs[1], _damaged_pdf())

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text[:400]
    text = _text(resp.content)
    assert _shown(docs[1]) in text
    assert "could not be read" in text
    assert "STAPLES page 1" in text


def test_a_month_whose_every_receipt_is_blocked_still_reports(
    client, monkeypatch
):
    """The listing is the part an auditor needs most, and it does not depend
    on any receipt opening."""
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    for doc in _docs(client, batch_id):
        _replace_stored_bytes(client, batch_id, doc, _encrypted_pdf())

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text[:400]
    text = _text(resp.content)
    assert "Staples" in text and "Trenitalia" in text  # the listing rows
    assert text.count("password-protected") == 2


def test_a_file_the_probe_misses_still_cannot_500_the_month(
    client, monkeypatch
):
    """The belt, on its own. `probe_pdf` is what makes the caption truthful,
    so with it working nothing reaches the per-file guard in `stitch` and the
    guard looks decorative. It is not: it is the answer to a file that fails
    at assembly for a reason the probe did not reproduce, and a residual can
    only be exercised by forcing one. Neutering the probe is that force.

    Without the guard this request is a 500 and the month has no report at
    all, which is the entire defect."""
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    _replace_stored_bytes(client, batch_id, docs[0], _encrypted_pdf())
    monkeypatch.setattr(
        "expense_recon.output._pdf_common.probe_pdf",
        lambda _data: (1, ""),
    )

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text[:400]
    # the blocked file contributes no pages, and everything else is intact
    text = _text(resp.content)
    assert "SECRET page 1" not in text
    assert "TRENITALIA page 1" in text
    assert "Staples" in text and "Trenitalia" in text


# ── the reviewer can see it without opening the PDF ─────────────────────


def test_render_state_is_absent_until_a_report_was_built(client, monkeypatch):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    _replace_stored_bytes(
        client, batch_id, _docs(client, batch_id)[0], _encrypted_pdf()
    )
    grid = _grid(client, batch_id)
    assert all("receipt_render" not in e for e in grid["expenses"])
    assert "n_receipts_unrenderable" not in grid["summary"]


def test_the_blocked_file_reaches_the_grid(client, monkeypatch):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    _replace_stored_bytes(client, batch_id, docs[0], _encrypted_pdf())

    assert client.get(
        f"/runs/{batch_id}/expense-report.pdf"
    ).status_code == 200
    grid = _grid(client, batch_id)
    by_doc = {e["document_id"]: e for e in grid["expenses"]}
    assert by_doc[docs[0]]["receipt_render"] == "failed"
    assert by_doc[docs[1]]["receipt_render"] == "ok"
    assert grid["summary"]["n_receipts_unrenderable"] == 1


def test_a_healthy_month_reports_zero_after_a_build(client, monkeypatch):
    """0 means "a report was built and every receipt is in it", which is a
    different statement from the absent key above."""
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    assert client.get(
        f"/runs/{batch_id}/expense-report.pdf"
    ).status_code == 200
    grid = _grid(client, batch_id)
    assert grid["summary"]["n_receipts_unrenderable"] == 0
    assert all(e["receipt_render"] == "ok" for e in grid["expenses"])


def test_the_grid_follows_the_file_back_to_healthy(client, monkeypatch):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    _replace_stored_bytes(client, batch_id, docs[0], _encrypted_pdf())
    client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert _grid(client, batch_id)["summary"]["n_receipts_unrenderable"] == 1

    _replace_stored_bytes(client, batch_id, docs[0], _pdf())
    client.get(f"/runs/{batch_id}/expense-report.pdf")
    grid = _grid(client, batch_id)
    assert grid["summary"]["n_receipts_unrenderable"] == 0
    by_doc = {e["document_id"]: e for e in grid["expenses"]}
    assert by_doc[docs[0]]["receipt_render"] == "ok"


# ── bounded assembly ────────────────────────────────────────────────────


def test_a_huge_receipt_contributes_the_cap_not_its_page_count(
    client, monkeypatch
):
    batch_id = _batch_with_two_receipts(client, monkeypatch)
    docs = _docs(client, batch_id)
    n_pages = MAX_RECEIPT_PAGES + 12
    _replace_stored_bytes(client, batch_id, docs[0], _pdf(n_pages=n_pages))

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text[:400]
    reader = pypdf.PdfReader(io.BytesIO(resp.content))
    text = _text(resp.content)
    # the caption says what was left out, and the file still counts as ok:
    # its pages ARE in the report, just not all of them
    assert f"{n_pages} pages" in text
    assert f"first {MAX_RECEIPT_PAGES}" in text
    assert _grid(client, batch_id)["summary"]["n_receipts_unrenderable"] == 0
    # listing + 2 caption pages + the capped receipt + the other receipt
    assert MAX_RECEIPT_PAGES < len(reader.pages) <= MAX_RECEIPT_PAGES + 8
