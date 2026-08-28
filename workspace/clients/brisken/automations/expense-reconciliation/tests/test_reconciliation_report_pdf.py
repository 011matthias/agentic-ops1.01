"""The statement reconciliation as a document.

Owner directive 2026-08-23: the reconciliation is not exported into any
application either, so the deliverable is evidence that the month is
complete — not a data file. These tests pin what makes it that: exceptions
come FIRST (they are the only part anyone must act on), the charge listing
states each charge's receipt and status, and a receipt nobody could place is
shown as unplaced rather than omitted.

PR 3 adds a card axis, and the tests for it are about what the document
does with a month that spans several cards: a coverage table, and a charge
listing sectioned by card. Both stay silent on a one-card month, because a
table and a heading that restate the headline are structure the content
does not earn.
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
    "summary": {"n_transactions": 2, "n_reconciled": 2, "match_rate": 100.0,
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
    "summary": {"n_transactions": 3, "n_reconciled": 1, "match_rate": 33.3,
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
    assert "1 possible duplicate group" in page1
    assert "1 possible duplicate groups" not in page1
    assert "UNKNOWN CHARGE" in page1
    assert "Orphan Receipt" in page1


def test_the_headline_counts_what_the_rate_is_computed_from():
    """The two halves of the headline have to describe one thing.

    `n_reconciled` is what a `build_view` payload calls the matched count and
    what `match_rate` divides; `n_matched` is the STORED pipeline summary's
    name for the pre-decision count and is never on the payload this document
    is built from. Reading the stored key first printed "0 matched (13.8%)"
    on every reconciliation the app produced, and the fixtures here carried
    the stored key so nothing failed. A caller that genuinely hands over a
    stored summary still gets its number.
    """
    page1 = _flat(build_reconciliation_report_pdf(MESSY_VIEW, title="April"))
    assert "3 charges · 1 matched (33.3%)" in page1

    stored_shape = {**MESSY_VIEW, "summary": {
        "n_transactions": 3, "n_matched": 1, "match_rate": 33.3}}
    assert "1 matched" in _flat(
        build_reconciliation_report_pdf(stored_shape, title="April"))


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


# ── the card axis (PR 3) ─────────────────────────────────────────────
#
# The rows are deliberately INTERLEAVED across the two cards (chase, amex,
# chase) while `coverage` lists chase first. Flat, the listing prints them in
# payload order; sectioned, both chase charges print before the amex one.
# Reading the vendor ORDER out of the page is therefore what tells a document
# that groups by card from one that only says it does. An assertion on the
# card NAMES could not: the coverage table prints those either way.

TWO_CARD_VIEW = {
    "summary": {"n_transactions": 3, "n_matched": 0, "match_rate": 0.0,
                "unreconciled_by_ccy": {"USD": "600.00"}},
    "coverage": [
        {"key": "chase-2838", "card_key": "chase-2838",
         "label": "Corporate card", "digits": ["2838"], "known": True,
         "statements": ["chase-april.xlsx"], "period_start": "2026-04-01",
         "period_end": "2026-04-03", "n_transactions": 2, "n_reconciled": 0,
         "n_review": 0, "n_unmatched_tx": 2, "n_refunds": 0,
         "unreconciled_by_ccy": {"USD": "500.00"}},
        {"key": "9001", "card_key": "", "label": "amex-9001",
         "digits": ["9001"], "known": False, "statements": ["amex.csv"],
         "period_start": "2026-04-02", "period_end": "2026-04-02",
         "n_transactions": 1, "n_reconciled": 0, "n_review": 0,
         "n_unmatched_tx": 1, "n_refunds": 0,
         "unreconciled_by_ccy": {"USD": "100.00"}},
    ],
    "rows": [
        {"date": "2026-04-01", "vendor": "ALPHAVENDOR", "amount": "400.00",
         "currency": "USD", "status": "pending", "chosen_document_id": None,
         "effective_bucket": "unmatched", "candidates": [],
         "posting_category": None, "coverage_key": "chase-2838"},
        {"date": "2026-04-02", "vendor": "BRAVOVENDOR", "amount": "100.00",
         "currency": "USD", "status": "pending", "chosen_document_id": None,
         "effective_bucket": "unmatched", "candidates": [],
         "posting_category": None, "coverage_key": "9001"},
        {"date": "2026-04-03", "vendor": "CHARLIEVENDOR", "amount": "100.00",
         "currency": "USD", "status": "pending", "chosen_document_id": None,
         "effective_bucket": "unmatched", "candidates": [],
         "posting_category": None, "coverage_key": "chase-2838"},
    ],
    "unmatched_transactions": [],
    "unmatched_receipts": [],
    "duplicate_groups": [],
}


def _one_card_view() -> dict:
    view = dict(TWO_CARD_VIEW)
    view["coverage"] = [TWO_CARD_VIEW["coverage"][0]]
    view["rows"] = [r for r in TWO_CARD_VIEW["rows"]
                    if r["coverage_key"] == "chase-2838"]
    return view


def test_a_multi_card_month_states_its_coverage_per_card():
    """A single unreconciled figure spread over three cards says nothing
    about which pile of receipts to go and find. The table splits it."""
    page1 = _flat(build_reconciliation_report_pdf(TWO_CARD_VIEW, title="April"))
    assert "Coverage by card" in page1
    assert "Corporate card" in page1
    assert "chase-april.xlsx" in page1
    assert "2026-04-01 to 2026-04-03" in page1
    assert "USD 500.00" in page1
    assert "amex-9001" in page1


def test_the_charge_listing_is_sectioned_by_card():
    """Sectioned, both of the corporate card's charges print before the amex
    one even though the payload interleaves them; flat, they print in payload
    order. That ordering is the only thing that distinguishes the two."""
    page1 = _flat(build_reconciliation_report_pdf(TWO_CARD_VIEW, title="April"))
    listing = page1[page1.index("All charges"):]
    assert listing.index("CHARLIEVENDOR") < listing.index("BRAVOVENDOR")
    assert listing.index("ALPHAVENDOR") < listing.index("CHARLIEVENDOR")


def test_a_charge_on_no_listed_card_is_still_printed():
    """A listing that silently drops charges is worse than an ugly one. A row
    whose card the coverage list does not carry gets its own section rather
    than disappearing between two that it does."""
    view = dict(TWO_CARD_VIEW)
    view["rows"] = TWO_CARD_VIEW["rows"] + [
        {"date": "2026-04-09", "vendor": "ORPHANVENDOR", "amount": "7.00",
         "currency": "USD", "status": "pending", "chosen_document_id": None,
         "effective_bucket": "unmatched", "candidates": [],
         "posting_category": None, "coverage_key": "not-a-card"},
    ]
    page1 = _flat(build_reconciliation_report_pdf(view, title="April"))
    assert "Other charges" in page1
    assert "ORPHANVENDOR" in page1


def test_a_one_card_month_gets_neither_a_table_nor_sections():
    """The headline already says it. A coverage table restating one row, and a
    section heading over the only table, are structure the content does not
    earn."""
    page1 = _flat(build_reconciliation_report_pdf(_one_card_view(), title="April"))
    assert "Coverage by card" not in page1
    assert "Corporate card" not in page1
    assert "All charges" in page1
    assert "ALPHAVENDOR" in page1
    assert "CHARLIEVENDOR" in page1


def test_a_payload_with_no_coverage_renders_as_it_always_did():
    """Every run created before PR 3 carries no `coverage` at all, and the
    document it produces has to be the one it produced yesterday."""
    page1 = _flat(build_reconciliation_report_pdf(MESSY_VIEW, title="April"))
    assert "Coverage by card" not in page1
    assert "TRENITALIA" in page1
    assert "UNKNOWN CHARGE" in page1
