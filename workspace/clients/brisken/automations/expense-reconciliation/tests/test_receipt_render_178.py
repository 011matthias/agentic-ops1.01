"""A receipt renders as an image whatever was stored (backlog item 178).

Three notes over 69 days ask for the same thing: #3 (2026-07-16) *Precisa ser
baixado a foto do recibo para ser usada*, #32 (2026-09-08) *recibo nao estar
abrindo*, #82 (2026-09-23) *Se possivel ter uma lupa para ampliar a foto do
recibo*. Item 52 already drove the live SPA for #32 and found its "View
receipt" button dead; these tests pin the half underneath it.

**The payload was the problem, not the viewer.** `/image` served the stored
file with its own media type, and 70 of September's 75 live receipts are
PDFs. A PDF cannot go in an `<img>`, so the only thing a browser-side viewer
could do with one is download it, which is note #3 word for word.

The negative cases are the contract, in both directions:

* WITHOUT `?as=png` the response must still be the original bytes with the
  original media type. Every existing caller relies on that, so a test that
  only proved the new path works would let the old one rot silently.
* WITH `?as=png` a PDF must come back as a real PNG. Asserting the header
  alone would pass if the route relabelled the PDF bytes, which is the one
  failure that would look fine in a header dump and break every viewer.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdfium2")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.receipt_render import (  # noqa: E402
    ReceiptRenderError,
    page_count,
    render_page_png,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _pdf_bytes(pages: int = 1) -> bytes:
    """A real, minimal PDF. Built rather than committed as a fixture so the
    page count is a parameter of the test and not a property of a blob.

    Each page gets its own size. Blank pages of equal size rasterize to
    identical PNG bytes, which would make the paging test pass whether or not
    `?page=` selected anything; differing sizes make "page 1 is not page 0" a
    real assertion without having to draw content.
    """
    import io

    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument.new()
    for i in range(pages):
        doc.new_page(200 + i * 40, 400)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=4):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client, name, blob, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, blob, "application/octet-stream"))],
    ))
    return batch_id


def _doc_id(client, batch_id) -> str:
    rows = client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    assert rows, "batch has no expense row"
    return rows[0]["document_id"]


# ── the helper, on its own ───────────────────────────────────────────────

def test_page_count_reads_a_real_pdf(tmp_path):
    p = tmp_path / "r.pdf"
    p.write_bytes(_pdf_bytes(pages=3))
    assert page_count(p) == 3


def test_page_count_is_one_for_an_image(tmp_path):
    p = tmp_path / "r.jpg"
    p.write_bytes(JPG)
    assert page_count(p) == 1


def test_page_count_never_raises_on_a_corrupt_pdf(tmp_path):
    """A wrong hint must not turn a servable receipt into an error."""
    p = tmp_path / "broken.pdf"
    p.write_bytes(b"not really a pdf")
    assert page_count(p) == 1


def test_render_page_png_returns_a_png(tmp_path):
    p = tmp_path / "r.pdf"
    p.write_bytes(_pdf_bytes())
    assert render_page_png(p).startswith(PNG_MAGIC)


def test_render_page_clamps_past_the_end(tmp_path):
    """A viewer asking for page 99 of a 2-page receipt gets the last page,
    not an error: paging is a hint, and a hint must not break the view."""
    p = tmp_path / "r.pdf"
    p.write_bytes(_pdf_bytes(pages=2))
    assert render_page_png(p, 99).startswith(PNG_MAGIC)


def test_render_page_raises_on_a_corrupt_pdf(tmp_path):
    p = tmp_path / "broken.pdf"
    p.write_bytes(b"not really a pdf")
    with pytest.raises(ReceiptRenderError):
        render_page_png(p)


# ── through the route, which is what actually had to change ──────────────

def test_pdf_receipt_serves_as_png_through_the_route(client, monkeypatch):
    """The item-178 case: the reviewer's receipt is a PDF and the screen
    needs an image. Note #32's month was exactly this."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", _pdf_bytes(pages=2))
    doc = _doc_id(client, batch)

    r = client.get(f"/api/runs/{batch}/receipts/{doc}/image", params={"as": "png"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    # The bytes, not the label: relabelled PDF bytes would pass a header check
    # and break every viewer.
    assert r.content.startswith(PNG_MAGIC)
    assert r.headers["X-Receipt-Pages"] == "2"


def test_second_page_differs_from_the_first(client, monkeypatch):
    """Paging has to actually page. Identical bytes would mean the parameter
    is decoration."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", _pdf_bytes(pages=2))
    doc = _doc_id(client, batch)
    url = f"/api/runs/{batch}/receipts/{doc}/image"

    one = client.get(url, params={"as": "png", "page": 0})
    two = client.get(url, params={"as": "png", "page": 1})
    assert one.status_code == two.status_code == 200
    assert one.content.startswith(PNG_MAGIC) and two.content.startswith(PNG_MAGIC)
    assert one.content != two.content


def test_without_the_param_the_old_behaviour_is_untouched(client, monkeypatch):
    """The negative case that matters most: existing callers get the stored
    file with its own media type, exactly as before."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", _pdf_bytes())
    doc = _doc_id(client, batch)

    r = client.get(f"/api/runs/{batch}/receipts/{doc}/image")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")


def test_an_image_receipt_is_served_as_itself_even_with_as_png(client, monkeypatch):
    """A JPEG already displays in an `<img>`; re-encoding it would cost
    quality and time for nothing. `as=png` promises displayable, not PNG."""
    _wire(monkeypatch)
    batch = _batch(client, "staples.jpg", JPG)
    doc = _doc_id(client, batch)

    r = client.get(f"/api/runs/{batch}/receipts/{doc}/image", params={"as": "png"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/jpeg")
    assert r.content == JPG
    assert r.headers["X-Receipt-Pages"] == "1"


def test_a_corrupt_pdf_falls_back_to_the_stored_bytes(client, monkeypatch):
    """Better a receipt the reviewer can download than one the tool claims
    does not exist. The header says the render failed so the SPA can say so."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", b"%PDF-1.4 truncated and broken")
    doc = _doc_id(client, batch)

    r = client.get(f"/api/runs/{batch}/receipts/{doc}/image", params={"as": "png"})
    assert r.status_code == 200, r.text
    assert r.headers.get("X-Receipt-Render") == "failed"
    assert r.content == b"%PDF-1.4 truncated and broken"


def test_path_escape_still_refused_with_the_new_param(client, monkeypatch):
    """The new query parameter must not open a way out of the run's tree."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", _pdf_bytes())
    r = client.get(
        f"/api/runs/{batch}/receipts/../recon-web.sqlite/image",
        params={"as": "png"},
    )
    assert r.status_code == 404, r.text


def test_unknown_as_value_is_treated_as_no_param(client, monkeypatch):
    """`?as=banana` must not become a second, undefined behaviour."""
    _wire(monkeypatch)
    batch = _batch(client, "invoice.pdf", _pdf_bytes())
    doc = _doc_id(client, batch)

    r = client.get(
        f"/api/runs/{batch}/receipts/{doc}/image", params={"as": "banana"}
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
