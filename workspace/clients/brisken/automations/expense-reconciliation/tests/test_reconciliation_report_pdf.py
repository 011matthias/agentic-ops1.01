"""The statement reconciliation as a document.

Owner directive 2026-08-23: the reconciliation is not exported into any
application either, so the deliverable is evidence that the month is
complete — not a data file. These tests pin what makes it that: exceptions
come FIRST (they are the only part anyone must act on), the charge listing
states each charge's receipt and status, and a receipt nobody could place is
shown as unplaced rather than omitted.
"""
from __future__ import annotations

import io

import pytest

pytest.importorskip("reportlab")

from pypdf import PdfReader  # noqa: E402

from expense_recon.output.reconciliation_report_pdf import (  # noqa: E402
    build_reconciliation_report_pdf,
)


def _png(color: str = "red") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (400, 600), color).save(buf, format="PNG")
    return buf.getvalue()


def _text(pdf: bytes, page: int = 0) -> str:
    return PdfReader(io.BytesIO(pdf)).pages[page].extract_text() or ""


def _all_text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def _flat(pdf: bytes, page: int = 0) -> str:
    """Extracted text with the layout's line breaks collapsed: a table cell
    wraps mid-phrase, which is a rendering detail, not a content one."""
    return " ".join((_text(pdf, page)).split())


CLEAN_VIEW = {
    "summary": {"n_transactions": 2, "n_matched": 2, "match_rate": 100.0,
                "unreconciled_by_ccy": {}},
    "rows": [
        {"date": "2026-04-01", "vendor": "TRENITALIA", "amount": "42.50",
         "currency": "EUR", "status": "confirmed",
         "chosen_document_id": "d1", "effective_bucket": "matched",
         "candidates": [{"document_id": "d1", "receipt": {"vendor": "Trenitalia"}}],
         "posting_category": {"zoho_account": "Travel Expense"}},
        {"date": "2026-04-02", "vendor": "CAFE LISBOA", "amount": "18.00",
         "currency": "EUR", "status": "pending",
         "chosen_document_id": "d2", "effective_bucket": "matched",
         "candidates": [{"document_id": "d2", "receipt": {"vendor": "Cafe Lisboa"}}],
         "posting_category": {"category": "Meals & Entertainment"}},
    ],
    "unmatched_transactions": [],
    "unmatched_receipts": [],
    "duplicate_groups": [],
}

MESSY_VIEW = {
    "summary": {"n_transactions": 3, "n_matched": 1, "match_rate": 33.3,
                "unreconciled_by_ccy": {"EUR": "60.50"}},
    "rows": [
        CLEAN_VIEW["rows"][0],
        {"date": "2026-04-05", "vendor": "UNKNOWN CHARGE", "amount": "60.50",
         "currency": "EUR", "status": "pending", "chosen_document_id": None,
         "effective_bucket": "unmatched", "candidates": [],
         "posting_category": None},
    ],
    "unmatched_transactions": [
        {"date": "2026-04-05", "vendor": "UNKNOWN CHARGE", "amount": "60.50",
         "currency": "EUR"},
    ],
    "unmatched_receipts": [
        {"date": "2026-04-09", "vendor": "Orphan Receipt", "total": "12.00",
         "currency": "EUR"},
    ],
    "duplicate_groups": [{"group_id": "g1", "members": ["d1", "d3"]}],
}


def test_the_header_states_whether_the_month_is_reconciled():
    pdf = build_reconciliation_report_pdf(MESSY_VIEW, title="Reconciliation — April")
    page1 = _text(pdf)
    assert "Reconciliation — April" in page1
    assert "3 charges" in page1
    assert "1 matched" in page1
    assert "unreconciled EUR 60.50" in " ".join(page1.split())


def test_exceptions_come_before_the_listing():
    """The only part anyone must ACT on goes first. A reader who stops after
    page one must still have seen everything that is wrong."""
    pdf = build_reconciliation_report_pdf(MESSY_VIEW, title="April")
    page1 = _text(pdf)
    assert page1.index("What needs attention") < page1.index("All charges")
    assert "1 charges with no receipt" in page1
    assert "1 receipts with no charge" in page1
    assert "1 possible duplicate groups" in page1
    assert "UNKNOWN CHARGE" in page1
    assert "Orphan Receipt" in page1


def test_a_clean_month_says_so_plainly():
    """A reconciliation with nothing outstanding must SAY that; an empty
    section reads as a missing section."""
    pdf = build_reconciliation_report_pdf(CLEAN_VIEW, title="April")
    page1 = _text(pdf)
    assert "Nothing." in page1
    assert "Every charge has a receipt" in page1


def test_every_charge_carries_its_receipt_and_status():
    pdf = build_reconciliation_report_pdf(CLEAN_VIEW, title="April")
    page1 = _flat(pdf)
    assert "TRENITALIA" in page1
    assert "matched (confirmed)" in page1
    assert "Trenitalia" in page1        # the receipt behind the charge
    assert "Travel Expense" in page1


def test_a_charge_with_no_receipt_reads_as_no_receipt():
    pdf = build_reconciliation_report_pdf(MESSY_VIEW, title="April")
    assert "no receipt" in _flat(pdf)


def test_receipts_are_appended_and_the_unplaced_ones_are_labelled():
    """A receipt nobody could match is evidence too — the reader has to see
    what the tool could not place, not just what it could."""
    pdf = build_reconciliation_report_pdf(
        MESSY_VIEW, title="April",
        evidence=[
            {"label": "Charge 2026-04-01 · TRENITALIA",
             "detail": "42.50 EUR", "name": "tren.png", "data": _png()},
            {"label": "Unmatched receipt · Orphan Receipt",
             "detail": "no charge on the statement settles this receipt",
             "name": "orphan.png", "data": _png("blue")},
        ],
    )
    reader = PdfReader(io.BytesIO(pdf))
    # listing page(s) + 2 * (caption + image)
    assert len(reader.pages) >= 5
    text = _all_text(pdf)
    assert "Charge 2026-04-01" in text
    assert "Unmatched receipt" in text
    assert "no charge on the statement settles this receipt" in text


def test_an_empty_reconciliation_still_renders():
    pdf = build_reconciliation_report_pdf(
        {"summary": {}, "rows": []}, title="Empty",
    )
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 1
    assert "0 charges" in _text(pdf)
