"""WS2 vision receipt-image extraction + image->summary-row mapping tests.

MockLLMClient-based, no live OpenAI and no real PDF fixture (the real ER PDFs
are sensitive client data). The page-selection boundary logic and the
image->row join are pure functions exercised directly; the end-to-end
`extract_receipt_images` is driven with `render_receipt_pages` monkeypatched to
return synthetic page bytes so the whole extract -> map -> merge -> issues flow
runs offline.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.ingest import expense_report_images as eri
from expense_recon.ingest.expense_report_images import (
    _amount_close,
    _map_and_merge,
    _norm_ref,
    _receipt_page_indices,
    extract_receipt_images,
)
from expense_recon.llm.client import ExtractedLineItem, ExtractedReceipt, MockLLMClient
from expense_recon.matching.types import Receipt


def _summary(document_id, *, ref=None, total, ccy="EUR", vendor=None, category="Cat") -> Receipt:
    return Receipt(
        document_id=document_id,
        legal_entity_id="le",
        detected_date=date(2026, 5, 1),
        detected_total=Decimal(total),
        detected_currency=ccy,
        detected_vendor=vendor,
        detected_reference=ref,
        report_number="ER-00216",
        zoho_category=category,
    )


def _ext(*, vendor=None, total=None, ccy=None, ref=None, items=(), notes="") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=None, total=total, currency=ccy, vendor=vendor, reference=ref,
        line_items=tuple(
            ExtractedLineItem(description=d, line_total=t) for d, t in items
        ),
        confidence=0.9, notes=notes,
    )


# ── page-selection boundary ─────────────────────────────────────────


def test_receipt_page_indices_skips_summary_and_trailer():
    # 0-1 summary; 2 REPORT SUMMARY end; 3 "Submitted By" trailer; 4-5 images.
    texts = [
        "EXPENSE SUMMARY\nS.No Expense Details ...",
        "S.No Expense Details ... Sub Total $10",
        "REPORT SUMMARY BY CURRENCY\nTotal Expense Amount 10",
        "5\nSubmitted By  Dirk Neumann ( US001 )",
        "1\n",            # a bare receipt-image page (page-number-only text)
        "Pizzeria Roma\nMargherita 8,00",
    ]
    assert _receipt_page_indices(texts) == [4, 5]


def test_receipt_page_indices_empty_without_summary_boundary():
    # No REPORT SUMMARY BY CURRENCY marker -> not a recognizable report -> [].
    assert _receipt_page_indices(["some scanned page", "another page"]) == []


def test_receipt_page_indices_caps(monkeypatch):
    monkeypatch.setattr(eri, "MAX_RENDER_PAGES", 3)
    texts = ["REPORT SUMMARY BY CURRENCY"] + ["img"] * 10
    assert _receipt_page_indices(texts) == [1, 2, 3]


# ── small helpers ───────────────────────────────────────────────────


def test_norm_ref_strips_noise():
    assert _norm_ref("335 536 4010") == "3355364010"
    assert _norm_ref("  ") is None
    assert _norm_ref(None) is None


def test_amount_close_tolerance():
    assert _amount_close(Decimal("16.20"), Decimal("16.20"))
    assert _amount_close(Decimal("16.21"), Decimal("16.20"))       # within 0.02
    assert not _amount_close(Decimal("16.60"), Decimal("16.20"))   # 0.40 apart
    assert not _amount_close(None, Decimal("1"))


# ── image -> summary-row join ───────────────────────────────────────


def test_map_prefers_reference_over_amount():
    rows = [
        _summary("r1", ref="998", total="1.90"),
        _summary("r2", ref="997", total="2.50"),
    ]
    # This reading's AMOUNT is closest to r1 (1.90) but its REFERENCE is 997 ->
    # must bind to r2 by reference, not r1 by amount.
    ext = _ext(vendor="Autostrade", total="1.90", ccy="EUR", ref="997",
               items=[("Toll", "2.50")])
    enriched, unmapped = _map_and_merge(rows, [(5, ext)])
    assert not unmapped
    assert enriched[0].detected_vendor is None            # r1 untouched
    assert enriched[1].detected_vendor == "Autostrade"    # r2 got the reading
    assert enriched[1].line_items[0].description == "Toll"


def test_map_falls_back_to_amount_currency_page_order():
    rows = [
        _summary("r1", total="6.60", vendor=None),   # Food, no vendor
        _summary("r2", total="7.10", vendor=None),
    ]
    e1 = _ext(vendor="Bar Uno", total="6.60", ccy="EUR", items=[("Espresso", "6.60")])
    e2 = _ext(vendor="Cafe Due", total="7.10", ccy="EUR", items=[("Cappuccino", "7.10")])
    enriched, unmapped = _map_and_merge(rows, [(5, e1), (6, e2)])
    assert not unmapped
    assert enriched[0].detected_vendor == "Bar Uno"
    assert enriched[1].detected_vendor == "Cafe Due"
    # line items attached -> categorization takes the LINE path downstream.
    assert enriched[0].line_items[0].description == "Espresso"


def test_map_keeps_summary_vendor_when_present():
    rows = [_summary("r1", total="111.99", vendor="DB")]
    ext = _ext(vendor="Deutsche Bahn AG", total="111.99", ccy="EUR",
               items=[("ICE Fahrkarte", "111.99")])
    enriched, _ = _map_and_merge(rows, [(13, ext)])
    # Summary vendor is the deterministic backbone; it is NOT overwritten.
    assert enriched[0].detected_vendor == "DB"
    # but the vision line items are still attached.
    assert enriched[0].line_items[0].description == "ICE Fahrkarte"


def test_map_records_data_quality_note_on_amount_disagreement():
    # Map by reference so a vision amount/currency disagreement does not block
    # the join, then assert the summary values are kept + a note is recorded.
    rows = [_summary("r1", ref="X1", total="20.00", ccy="EUR", vendor=None)]
    ext = _ext(vendor="Shop", total="23.50", ccy="USD", ref="X1",
               items=[("Thing", "23.50")])
    enriched, _ = _map_and_merge(rows, [(5, ext)])
    r = enriched[0]
    # summary amount + currency KEPT (deterministic backbone).
    assert r.detected_total == Decimal("20.00")
    assert r.detected_currency == "EUR"
    assert r.data_quality_note and "differs" in r.data_quality_note


def test_map_leaves_unmapped_reading():
    rows = [_summary("r1", total="6.60")]
    matched = _ext(vendor="A", total="6.60", ccy="EUR")
    orphan = _ext(vendor="Mystery", total="999.00", ccy="EUR")
    enriched, unmapped = _map_and_merge(rows, [(5, matched), (6, orphan)])
    assert [e.vendor for _, e in unmapped] == ["Mystery"]
    assert enriched[0].detected_vendor == "A"


# ── end-to-end extract -> map -> merge -> issues ────────────────────


def test_extract_receipt_images_enriches_and_reports(monkeypatch):
    rows = [
        _summary("r1", total="6.60", vendor=None),
        _summary("r2", total="7.10", vendor=None),
    ]
    monkeypatch.setattr(
        eri, "render_receipt_pages", lambda p: [(5, b"png-a"), (6, b"png-b")]
    )
    client = MockLLMClient(extraction_responses=[
        _ext(vendor="Bar Uno", total="6.60", ccy="EUR", items=[("Espresso", "6.60")]),
        _ext(vendor="Cafe Due", total="7.10", ccy="EUR", items=[("Latte", "7.10")]),
    ])
    enriched, issues = extract_receipt_images(
        "fake.pdf", client=client, summary_receipts=rows
    )
    assert not issues
    assert enriched[0].detected_vendor == "Bar Uno"
    assert enriched[1].detected_vendor == "Cafe Due"
    # two vision calls, one per rendered page.
    assert sum(1 for c in client.calls if c[0] == "extract_receipt") == 2


def test_extract_receipt_images_no_pages_is_noop(monkeypatch):
    rows = [_summary("r1", total="6.60", vendor=None)]
    monkeypatch.setattr(eri, "render_receipt_pages", lambda p: [])
    client = MockLLMClient()
    enriched, issues = extract_receipt_images(
        "fake.pdf", client=client, summary_receipts=rows
    )
    assert enriched == rows and not issues
    assert not client.calls  # no vision call when there are no receipt pages


def test_extract_receipt_images_tolerates_per_image_failure(monkeypatch):
    rows = [_summary("r1", total="6.60", vendor=None)]
    monkeypatch.setattr(eri, "render_receipt_pages", lambda p: [(5, b"bad")])

    class _Boom:
        calls: list = []

        def extract_receipt(self, **kw):
            raise RuntimeError("vision 500")

    enriched, issues = extract_receipt_images(
        "fake.pdf", client=_Boom(), summary_receipts=rows
    )
    # The failing image becomes an Errors-sheet issue; the row is unchanged.
    assert enriched[0].detected_vendor is None
    assert len(issues) == 1
    assert "extraction failed" in issues[0].message
