"""The month's expense report PDF: listing first, then every receipt.

Owner directive 2026-08-23: nothing imports the output any more, so the
deliverable is a document — "an expense report like in Zoho with an organized
listing, then all the receipts". These tests pin the three properties that
make it one: the listing quotes the export rows (money cannot drift between
the file and the document), every expense's receipt is actually appended
behind its own caption, and an expense with no document says so instead of
vanishing.
"""
from __future__ import annotations

import io

import pytest

pytest.importorskip("reportlab")

from pypdf import PdfReader  # noqa: E402

from expense_recon.output.month_report_pdf import (  # noqa: E402
    build_expense_report_pdf,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402


def _row(**kw) -> list[str]:
    row = [""] * len(EXPENSE_COLUMNS)
    for key, value in kw.items():
        row[EXPENSE_COLUMNS.index(key)] = value
    return row


ROWS = [
    _row(**{"Expense Date": "2026-08-01", "Vendor": "Trenitalia",
            "Expense Account": "Travel Expense: Public Transport",
            "Legal Entity": "Corporate Services", "Expense Amount": "42.50",
            "Currency Code": "EUR", "Paid Through": "CHASE VISA - 2838"}),
    _row(**{"Expense Date": "2026-08-02", "Vendor": "Cafe Lisboa",
            "Expense Account": "Meals & Entertainment",
            "Legal Entity": "Cloud Services", "Expense Amount": "18.00",
            "Currency Code": "EUR", "Paid Through": "(paid-through - assign)"}),
]


def _png(color: str = "red") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (400, 600), color).save(buf, format="PNG")
    return buf.getvalue()


def _pdf_receipt(pages: int = 2) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    first = Image.new("RGB", (300, 400), "white")
    rest = [Image.new("RGB", (300, 400), "white") for _ in range(pages - 1)]
    first.save(buf, format="PDF", save_all=True, append_images=rest)
    return buf.getvalue()


def _text(pdf: bytes, page: int) -> str:
    return PdfReader(io.BytesIO(pdf)).pages[page].extract_text() or ""


def test_the_listing_quotes_the_export_rows():
    """The document and the CSV cannot disagree about money: the listing is
    rendered FROM the export rows, so every amount on page 1 is the amount
    the export writes."""
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026 expenses",
    )
    page1 = _text(pdf, 0)
    assert "April 2026 expenses" in page1
    for fragment in ("Trenitalia", "42.50", "Cafe Lisboa", "18.00",
                     "Corporate Services", "Cloud Services"):
        assert fragment in page1, fragment
    # Totals are stated per currency, summed from those same rows.
    assert "EUR 60.50" in page1
    assert "2 expenses" in page1


def test_every_receipt_is_appended_behind_its_own_caption():
    """"then all the receipts": each expense gets a caption page naming its
    number, and its document follows immediately."""
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "tren.png",
             "data": _png("red")},
            {"rows": [2], "label": "Cafe Lisboa", "name": "cafe.png",
             "data": _png("blue")},
        ],
    )
    reader = PdfReader(io.BytesIO(pdf))
    # 1 listing page + per expense (caption + 1 image page)
    assert len(reader.pages) == 1 + 2 * 2
    assert "Expense 1" in _text(pdf, 1)
    assert "Trenitalia" in _text(pdf, 1)
    assert "tren.png" in _text(pdf, 1)
    assert "Expense 2" in _text(pdf, 3)
    assert "cafe.png" in _text(pdf, 3)


def test_a_multipage_pdf_receipt_keeps_all_its_pages():
    """A PDF receipt is appended as delivered, not rasterized to one page:
    a two-page invoice stays two pages of evidence."""
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "invoice.pdf",
             "data": _pdf_receipt(pages=2)},
            {"rows": [2], "label": "Cafe Lisboa", "name": "cafe.png",
             "data": _png()},
        ],
    )
    # 1 listing + (caption + 2 invoice pages) + (caption + 1 image)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 1 + 3 + 2


def test_an_expense_without_a_receipt_says_so():
    """Honest gaps: a typed-in expense has no document, and the report states
    that on its caption page rather than quietly skipping the expense."""
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "tren.png",
             "data": _png()},
            {"rows": [2], "label": "Cafe Lisboa"},
        ],
    )
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1 + 2 + 1  # the second expense has no page
    caption = _text(pdf, 3)
    assert "Expense 2" in caption
    assert "No receipt document" in caption


def test_a_corrupt_receipt_loses_its_pages_not_the_report():
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "broken.png",
             "data": b"not an image at all"},
            {"rows": [2], "label": "Cafe Lisboa", "name": "broken.png",
             "data": b"not an image at all"},
        ],
    )
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1 + 2  # both captions survive
    assert "Expense 1" in _text(pdf, 1)
    # And the caption is honest about it: a caption with nothing behind it
    # reads as "the receipt is here" to anyone flipping through.
    assert "could not be rendered" in _text(pdf, 1)


def test_markup_in_a_vendor_name_is_escaped_not_rendered():
    """Paragraph text is mini-HTML; a real vendor called "A & B <Ltd>" must
    not corrupt the page (or vanish into an unknown tag)."""
    rows = [_row(**{"Vendor": "A & B <Ltd>", "Expense Amount": "9.99",
                    "Currency Code": "EUR", "Expense Date": "2026-08-03"})]
    pdf = build_expense_report_pdf(rows, EXPENSE_COLUMNS, title="Escaping")
    assert "A & B <Ltd>" in _text(pdf, 0)


def test_an_empty_month_still_produces_a_readable_report():
    pdf = build_expense_report_pdf([], EXPENSE_COLUMNS, title="Empty month")
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) == 1
    assert "no expenses" in _text(pdf, 0)


def test_a_split_receipt_appears_once_captioned_with_both_expenses():
    """A receipt booking to two accounts writes TWO listing rows and is ONE
    piece of evidence. Appending it per row would duplicate the pages and
    make the document disagree with itself about how many receipts exist."""
    rows = ROWS + [_row(**{"Expense Date": "2026-08-02", "Vendor": "Cafe Lisboa",
                           "Expense Account": "Office Supplies",
                           "Expense Amount": "5.00", "Currency Code": "EUR"})]
    pdf = build_expense_report_pdf(
        rows, EXPENSE_COLUMNS, title="Split month",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "tren.png",
             "data": _png("red")},
            {"rows": [2, 3], "label": "Cafe Lisboa", "name": "cafe.png",
             "data": _png("blue")},
        ],
    )
    reader = PdfReader(io.BytesIO(pdf))
    # 3 listing rows but only 2 documents: 1 listing + 2 * (caption + image)
    assert len(reader.pages) == 1 + 2 * 2
    assert "Expenses 2, 3" in _text(pdf, 3)


def test_the_receipt_column_states_attachment_not_a_page_number():
    """The listing is laid out before the caption pages exist, so it cannot
    know a receipt's page. It says whether a document is attached, which it
    does know; "p. 3" next to expense 3 was a number that looked like a page
    reference and was not one."""
    pdf = build_expense_report_pdf(
        ROWS, EXPENSE_COLUMNS, title="April 2026",
        evidence=[
            {"rows": [1], "label": "Trenitalia", "name": "tren.png",
             "data": _png()},
            {"rows": [2], "label": "Cafe Lisboa"},
        ],
    )
    page1 = _text(pdf, 0)
    assert "attached" in page1
    assert "none" in page1
    assert "p. 1" not in page1
