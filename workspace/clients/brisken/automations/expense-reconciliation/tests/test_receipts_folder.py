"""Slice 2.2 — receipts folder ingest (vision OCR + PDF text layer).

All tests run against MockLLMClient — CI-safe, no API key. The pypdf
text-extraction and pypdfium2 render paths are isolated behind
`_pdf_text` / `_pdf_page_images` and monkeypatched here; their real
behaviour is exercised by the live calibration run, not unit tests.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.ingest import receipts_folder
from expense_recon.ingest.receipts_folder import parse_receipts_folder
from expense_recon.llm.client import (
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-06-02",
        total="24.50",
        currency="USD",
        vendor="Uber",
        reference="TRIP-123",
        line_items=(),
        confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def test_image_goes_through_vision(tmp_path):
    (tmp_path / "r1.jpg").write_bytes(b"\xff\xd8fakejpeg")
    client = MockLLMClient(extraction_responses=[_extraction()])

    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert issues == []
    assert len(receipts) == 1
    r = receipts[0]
    assert r.document_id == "r1.jpg"
    assert r.detected_total == Decimal("24.50")
    assert r.detected_vendor == "Uber"
    assert r.detected_date.isoformat() == "2026-06-02"
    assert r.detected_reference == "TRIP-123"
    assert client.calls == [("extract_receipt", ("r1.jpg", "vision"))]


def test_pdf_with_text_layer_goes_through_text(tmp_path, monkeypatch):
    (tmp_path / "ticket.pdf").write_bytes(b"%PDF-fake")
    monkeypatch.setattr(
        receipts_folder, "_pdf_text",
        lambda f: "Deutsche Bahn Fahrkarte Gesamtpreis 49,90 EUR " * 3,
    )
    client = MockLLMClient(
        extraction_responses=[_extraction(total="49.90", currency="EUR", vendor="Deutsche Bahn")]
    )

    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert issues == []
    assert client.calls == [("extract_receipt", ("ticket.pdf", "text"))]
    # the text layer is preserved on ocr_text for later debugging
    assert "Fahrkarte" in receipts[0].ocr_text


def test_scanned_pdf_falls_back_to_render_and_vision(tmp_path, monkeypatch):
    (tmp_path / "scan.pdf").write_bytes(b"%PDF-fake")
    monkeypatch.setattr(receipts_folder, "_pdf_text", lambda f: "  \n ")  # thin layer
    monkeypatch.setattr(
        receipts_folder, "_pdf_page_images",
        lambda f: [(b"png-bytes", "image/png")],
    )
    client = MockLLMClient(extraction_responses=[_extraction()])

    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert issues == []
    assert client.calls == [("extract_receipt", ("scan.pdf", "vision"))]


def test_line_items_map_to_domain_types(tmp_path):
    (tmp_path / "amazon.png").write_bytes(b"fakepng")
    client = MockLLMClient(extraction_responses=[
        _extraction(
            vendor="Amazon",
            total="200.00",
            line_items=(
                ExtractedLineItem("Office chair", "150.00", quantity="1", unit_price="150.00"),
                ExtractedLineItem("Coffee beans 2kg", "30.00"),
                ExtractedLineItem("(illegible)", None),
            ),
        )
    ])

    receipts, _ = parse_receipts_folder(tmp_path, "brisken-llc", client)

    items = receipts[0].line_items
    assert [i.description for i in items] == ["Office chair", "Coffee beans 2kg", "(illegible)"]
    assert items[0].line_total == Decimal("150.00")
    assert items[0].quantity == Decimal("1")
    # unreadable amount → 0, item kept visible (never dropped)
    assert items[2].line_total == Decimal("0")


def test_no_itemization_yields_empty_line_items(tmp_path):
    (tmp_path / "taxi.jpg").write_bytes(b"fake")
    client = MockLLMClient(extraction_responses=[_extraction(line_items=())])

    receipts, _ = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert receipts[0].line_items == ()


def test_default_currency_applies_only_when_missing(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[
        _extraction(currency=None),
        _extraction(currency="eur"),
    ])

    receipts, _ = parse_receipts_folder(
        tmp_path, "brisken-llc", client, default_currency="USD"
    )

    by_id = {r.document_id: r for r in receipts}
    assert by_id["a.jpg"].detected_currency == "USD"
    assert by_id["b.jpg"].detected_currency == "EUR"  # normalized upper


def test_unsupported_file_lands_in_issues_not_silently_dropped(tmp_path):
    (tmp_path / "notes.md").write_text("not a receipt")
    (tmp_path / "r.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[_extraction()])

    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert len(receipts) == 1
    assert len(issues) == 1
    assert issues[0].file_name == "notes.md"
    assert "unsupported" in issues[0].message


def test_extraction_failure_is_per_file_tolerant(tmp_path):
    (tmp_path / "bad.jpg").write_bytes(b"x")
    (tmp_path / "good.jpg").write_bytes(b"x")

    class ExplodingClient(MockLLMClient):
        def extract_receipt(self, *, file_name, images=None, text=None):
            if file_name == "bad.jpg":
                raise RuntimeError("boom")
            return super().extract_receipt(
                file_name=file_name, images=images, text=text
            )

    client = ExplodingClient(extraction_responses=[_extraction()])
    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert [r.document_id for r in receipts] == ["good.jpg"]
    assert len(issues) == 1
    assert issues[0].file_name == "bad.jpg"
    assert "extraction failed" in issues[0].message


def test_empty_folder_is_an_issue(tmp_path):
    client = MockLLMClient()
    receipts, issues = parse_receipts_folder(tmp_path, "brisken-llc", client)
    assert receipts == []
    assert len(issues) == 1
    assert "empty" in issues[0].message


def test_garbled_date_and_total_become_none(tmp_path):
    (tmp_path / "r.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[
        _extraction(date="June the 2nd-ish", total="N/A")
    ])

    receipts, _ = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert receipts[0].detected_date is None
    assert receipts[0].detected_total is None


def test_tax_and_payment_hint_flow_through(tmp_path):
    """Receipt-first parity (2026-07-27): the OCR tax/VAT + paying-card hint
    reach the domain Receipt (tax → detected_tax, hint → payment_mode)."""
    (tmp_path / "r.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[
        _extraction(tax="3.80", tax_label="VAT", payment_hint="Visa ...1234")
    ])

    receipts, _ = parse_receipts_folder(tmp_path, "brisken-llc", client)

    r = receipts[0]
    assert r.detected_tax == Decimal("3.80")
    assert r.tax_label == "VAT"
    # folder OCR has no ER payment_mode; the hint fills it
    assert r.payment_mode == "Visa ...1234"


def test_tax_fields_absent_default_to_none(tmp_path):
    (tmp_path / "r.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[_extraction()])  # no tax fields

    receipts, _ = parse_receipts_folder(tmp_path, "brisken-llc", client)

    assert receipts[0].detected_tax is None
    assert receipts[0].tax_label is None


def test_receipt_tax_fields_round_trip():
    """The new tax fields survive a snapshot round-trip, and a pre-2026-07-27
    snapshot (no tax keys) still loads (back-compat via .get)."""
    from expense_recon.matching.types import Receipt
    from expense_recon.web.serialize import receipt_from_dict, receipt_to_dict

    r = Receipt(
        document_id="r1.jpg",
        legal_entity_id="brisken-llc",
        detected_date=None,
        detected_total=Decimal("24.50"),
        detected_currency="EUR",
        detected_vendor="Uber",
        detected_tax=Decimal("3.80"),
        tax_label="VAT",
    )
    back = receipt_from_dict(receipt_to_dict(r))
    assert back.detected_tax == Decimal("3.80")
    assert back.tax_label == "VAT"

    legacy = receipt_to_dict(r)
    del legacy["detected_tax"]
    del legacy["tax_label"]
    back_legacy = receipt_from_dict(legacy)
    assert back_legacy.detected_tax is None
    assert back_legacy.tax_label is None


def test_extract_receipt_rejects_both_or_neither_input():
    client = MockLLMClient()
    with pytest.raises(ValueError):
        client.extract_receipt(file_name="x.jpg")
    with pytest.raises(ValueError):
        client.extract_receipt(
            file_name="x.jpg", images=[(b"a", "image/png")], text="t"
        )


# ── CLI wiring (folder source) ───────────────────────────────────────


def test_cli_folder_source_requires_llm_block(tmp_path):
    from expense_recon.cli import ConfigError, _load_receipts

    folder = tmp_path / "receipts"
    folder.mkdir()
    cfg = {"receipts": {"path": "receipts"}}

    with pytest.raises(ConfigError, match="llm"):
        _load_receipts(cfg, tmp_path, "brisken-llc", llm_client=None)


def test_cli_infers_folder_mode_from_directory_path(tmp_path):
    from expense_recon.cli import _load_receipts

    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "r.jpg").write_bytes(b"x")
    client = MockLLMClient(extraction_responses=[_extraction()])

    receipts, issues = _load_receipts(
        {"receipts": {"path": "receipts", "default_currency": "USD"}},
        tmp_path, "brisken-llc", llm_client=client,
    )

    assert issues == []
    assert receipts[0].document_id == "r.jpg"


def test_cli_explicit_csv_source_on_directory_errors(tmp_path):
    from expense_recon.cli import ConfigError, _load_receipts

    folder = tmp_path / "receipts"
    folder.mkdir()

    with pytest.raises(ConfigError, match="directory"):
        _load_receipts(
            {"receipts": {"path": "receipts", "source": "csv"}},
            tmp_path, "brisken-llc", llm_client=MockLLMClient(),
        )
