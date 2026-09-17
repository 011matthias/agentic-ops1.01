"""Item 138 (owner, 2026-09-17): "the output (PDF) is also not organized in
the different cards that were reconciled."

The reconciliation report was per card only in its coverage table and its
charge listing. The headline, the exceptions and the receipt pages ran across
every card at once, so a reader could not take one card's statement and its
pile of receipts and check them against each other. Now each card is a
section: its statement and figures, what needs attention on it, its charges,
then its receipt pages. Receipts with no card come last and are never dropped.

Route-level: a real month (settings cards, receipt upload, statement attach,
a card pick) read back through `GET /runs/{id}/reconciliation-report.pdf`.
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("reportlab")

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.output._pdf_common import (  # noqa: E402
    caption_mark,
    prepare_evidence,
    stitch,
)
from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _done,
    _expense,
    _extraction,
    _pick_card,
    _wire,
)

LABEL_2838 = "Credit Card Chase Visa - 2838"
LABEL_3645 = "Credit Card Chase Visa - 3645"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _png(color: str) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (300, 400), color).save(buf, format="PNG")
    return buf.getvalue()


def _month_with_images(client, colors: list[str]) -> str:
    """A month whose receipts are real images, so each renders to a page and
    the page order of the stitched document can be read."""
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch = resp.json()["batch_id"]
    files = [
        ("files", (f"receipt-{c}.png", _png(c), "image/png")) for c in colors
    ]
    _done(client, client.post(f"/api/expense-batches/{batch}/receipts", files=files))
    return batch


def _pages(pdf: bytes) -> list[str]:
    return [
        " ".join((p.extract_text() or "").split())
        for p in PdfReader(io.BytesIO(pdf)).pages
    ]


def _first(pages: list[str], needle: str, start: int = 0) -> int:
    for i in range(start, len(pages)):
        if needle in pages[i]:
            return i
    raise AssertionError(f"{needle!r} not found from page {start}: {pages}")


@pytest.fixture
def august(client, monkeypatch):
    """Two cards with charges; on 2838 a held receipt, a charge with no
    receipt and a receipt with no charge that PRINTS 2838; on 3645 the live
    LOVABLE case (held there, picked as 2838); and a receipt with no card."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(
        monkeypatch,
        _extraction("Pressmaster", "135.00", "2026-08-23"),
        _extraction("Zoom", "15.00", "2026-08-10", "Visa ending 2838"),
        _extraction("Lovable", "25.00", "2026-08-05"),
        _extraction("Taxi", "30.00", "2026-08-12"),
    )
    batch = _month_with_images(client, ["red", "green", "blue", "yellow"])
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
        ("2838", datetime(2026, 8, 14), "GITHUB", "Sale", -40.00),
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    ])
    lovable = _expense(client, batch, "Lovable")["document_id"]
    resp = _pick_card(client, batch, lovable, "corp-2838")
    assert resp.status_code == 200, resp.text
    resp = client.get(f"/runs/{batch}/reconciliation-report.pdf")
    assert resp.status_code == 200, resp.text
    return _pages(resp.content)


def test_each_card_is_a_section_in_coverage_order_and_no_card_comes_last(august):
    pages = august
    assert "3 charges · 2 matched (66.7%) · unreconciled USD 40.00" in pages[0]
    at_2838 = _first(pages, LABEL_2838, 1)
    at_3645 = _first(pages, LABEL_3645, at_2838 + 1)
    at_none = _first(pages, "No card", at_3645 + 1)
    assert pages[at_2838].startswith(LABEL_2838)
    assert pages[at_3645].startswith(LABEL_3645)
    assert pages[at_none].startswith("No card")

    card_2838 = pages[at_2838]
    assert "Statement: August2026.xlsx" in card_2838
    assert "2 charges · 1 matched" in card_2838
    assert "unreconciled USD 40.00" in card_2838
    assert "GITHUB" in card_2838 and "PRESSMASTER" in card_2838
    assert "LOVABLE" not in card_2838
    # The unheld receipt printing 2838 is this card's exception, nowhere else.
    assert "1 receipts with no charge" in card_2838 and "Zoom" in card_2838
    assert "Zoom" not in pages[at_3645] and "Zoom" not in pages[at_none]

    card_3645 = pages[at_3645]
    assert "LOVABLE" in card_3645 and "cards differ" in card_3645
    assert f"is on {LABEL_2838}, not this card" in card_3645

    no_card = pages[at_none]
    assert "Taxi" in no_card and "Taxi" not in card_2838


def test_each_cards_receipt_pages_follow_its_own_section(august):
    """A caption names the charge or says unmatched; the page right after it
    is the receipt image (no text layer), and every caption sits between its
    own card's heading and the next card's."""
    pages = august
    at_2838 = _first(pages, LABEL_2838, 1)
    at_3645 = _first(pages, LABEL_3645, at_2838 + 1)
    at_none = _first(pages, "No card", at_3645 + 1)
    captions = {
        "Charge 2026-08-23 · PRESSMASTER": (at_2838, at_3645),
        "Unmatched receipt · Zoom": (at_2838, at_3645),
        "Charge 2026-08-05 · LOVABLE": (at_3645, at_none),
        "Unmatched receipt · Taxi": (at_none, len(pages)),
    }
    for caption, (lo, hi) in captions.items():
        at = _first(pages, caption, 1)
        assert lo < at < hi, (caption, at, lo, hi)
        assert pages[at + 1] == "", (caption, pages[at + 1])
    lovable_caption = pages[_first(pages, "Charge 2026-08-05 · LOVABLE", 1)]
    assert f"the receipt's own card: {LABEL_2838}" in lovable_caption
    assert len(pages) == at_none + 1 + 2  # the no-card caption and its image


def test_a_caption_count_that_does_not_line_up_appends_rather_than_misfiles():
    """`stitch` with page marks that do not match the evidence still keeps
    every receipt, after the last page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate
    from reportlab.lib.styles import getSampleStyleSheet

    style = getSampleStyleSheet()["Normal"]
    marks: list[int] = []
    items = [{"label": "one", "data": _png("red")}, {"label": "two", "data": _png("blue")}]
    prepared = prepare_evidence(items)
    story = [Paragraph("head", style)]
    for item in items:
        story += [PageBreak(), caption_mark(marks), Paragraph(item["label"], style)]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4).build(story)
    assert marks == [2, 3]

    placed = _pages(stitch(buf.getvalue(), prepared, marks))
    assert placed == ["head", "one", "", "two", ""]
    appended = _pages(stitch(buf.getvalue(), prepared, marks[:1]))
    assert appended == ["head", "one", "two", "", ""]
