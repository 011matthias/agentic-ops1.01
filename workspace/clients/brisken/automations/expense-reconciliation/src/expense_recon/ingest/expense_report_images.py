"""Vision extraction of the receipt-IMAGE pages in a Zoho Expense report PDF
(WS2, 2026-07-21).

The `expense_report_pdf` adapter reads the machine-readable EXPENSE SUMMARY
table into the summary `Receipt` objects the matcher consumes; it deliberately
ignores the receipt-image pages that follow. But that summary table often
carries NO merchant for a line (verified on ER-00216: 9 of 20 rows have no
vendor -- every Food line, the two DB train tickets, the Annada toll), so the
categorizer has no signal and returns REVIEW/blank, leaving the report's own
(often wrong) GL account in place. This module closes that gap: it renders the
trailing receipt-image pages, runs the existing vision `extract_receipt` per
image to read each receipt's real merchant + line items off the actual receipt,
maps each vision reading back to its EXPENSE SUMMARY row, and attaches the
merchant (when the summary had none) + the line items so the categorizer takes
the vendor-aware / LINE path.

Two invariants keep the deterministic matcher intact:

* The EXPENSE SUMMARY row stays authoritative for MATCHING: the summary's
  amount / currency / date / reference are the matcher's inputs and are never
  overwritten by a vision reading. Only the merchant (when the summary had
  none) and the line items are taken from vision.
* On a vision-vs-summary amount / currency disagreement the summary value is
  KEPT and a short `data_quality_note` is recorded on the receipt for the
  reviewer, never a silent overwrite (the reconciliation guarantee).

Image -> summary-row mapping (resolved against the real ER-00216 page
structure): the primary key is the reference/Ref# the vision model reads off
the image matched to the summary row's `detected_reference`; the fallback is
amount + currency closeness with page order breaking ties. The join is greedy
and one-to-one -- a summary row takes at most one image reading and an image
reading is used at most once -- so no row is double-filled.

Never route a report PDF through `receipts_folder.py` (its 4-page cap + folder
semantics are for a folder of individual receipt files); this module is the
report-PDF-specific vision path.
"""
from __future__ import annotations

import io
import logging
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..llm.client import ExtractedReceipt, LLMClient
from ..matching.types import LineItem, Receipt
from ..vendor_names import clean_vendor_name
from ._common import ParseIssue

logger = logging.getLogger("expense_recon")

# The report's front matter + machine-readable summary table span from the
# first page through the page carrying this marker; every page AFTER it is a
# receipt image (or an end trailer). Keyed on the same text the summary parser
# uses, so the two adapters agree on the section boundary.
_SUMMARY_END_MARKER = "REPORT SUMMARY BY CURRENCY"
# An end trailer page ("Submitted By  Dirk Neumann ( US001 )") after the
# summary carries no receipt; skip it from vision so we don't burn a call.
_TRAILER_RE = re.compile(r"^\s*\d*\s*Submitted By\b", re.IGNORECASE)
_TRAILER_MAX_CHARS = 80

# Bound on vision calls: a report with more image pages than this is unusual,
# and the cap keeps a pathological upload from fanning out into a huge bill.
MAX_RENDER_PAGES = 60

# PNG render scale (matches receipts_folder._pdf_page_images).
_RENDER_SCALE = 2.0


def render_receipt_pages(pdf_path: str | Path) -> list[tuple[int, bytes]]:
    """Render the receipt-image pages of a Zoho Expense report PDF to PNG.

    Returns `[(page_index, png_bytes), ...]` for every page AFTER the EXPENSE
    SUMMARY / REPORT SUMMARY front matter, skipping the end trailer page.
    Empty when the PDF has no summary boundary (not a Zoho report) or no pages
    follow it -- vision then no-ops and the summary receipts are used as-is.
    """
    from pypdf import PdfReader

    path = Path(pdf_path)
    reader = PdfReader(str(path))
    n_pages = len(reader.pages)
    page_texts = [(reader.pages[i].extract_text() or "") for i in range(n_pages)]
    return _render_pages(path, _receipt_page_indices(page_texts, name=path.name))


def _receipt_page_indices(page_texts: list[str], *, name: str = "") -> list[int]:
    """The page indices that are receipt images: everything after the EXPENSE
    SUMMARY / REPORT SUMMARY front matter, minus the end trailer, capped.
    Empty when no summary boundary is found (not a Zoho report). Pure -- the
    page-selection logic, split out from PDF I/O so it is unit-testable."""
    summary_end = _summary_end_page(page_texts)
    if summary_end is None:
        # Not a recognizable Zoho report layout: don't guess which pages are
        # receipts. Vision no-ops; the deterministic summary is unchanged.
        return []
    candidates = [
        i
        for i in range(summary_end + 1, len(page_texts))
        if not _is_trailer(page_texts[i])
    ]
    if len(candidates) > MAX_RENDER_PAGES:
        logger.warning(
            "expense report %s has %d receipt-image pages; capping vision at %d",
            name, len(candidates), MAX_RENDER_PAGES,
        )
        candidates = candidates[:MAX_RENDER_PAGES]
    return candidates


def _summary_end_page(page_texts: list[str]) -> int | None:
    """Index of the last page carrying the REPORT SUMMARY BY CURRENCY marker,
    or None when no page does (not a Zoho Expense report PDF)."""
    for i in range(len(page_texts) - 1, -1, -1):
        if _SUMMARY_END_MARKER in page_texts[i]:
            return i
    return None


def _is_trailer(text: str) -> bool:
    stripped = text.strip()
    return bool(_TRAILER_RE.match(stripped)) and len(stripped) <= _TRAILER_MAX_CHARS


def _render_pages(path: Path, page_indices: list[int]) -> list[tuple[int, bytes]]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    try:
        out: list[tuple[int, bytes]] = []
        n = len(doc)
        for i in page_indices:
            if i >= n:
                continue
            bitmap = doc[i].render(scale=_RENDER_SCALE)
            buf = io.BytesIO()
            bitmap.to_pil().save(buf, format="PNG")
            out.append((i, buf.getvalue()))
        return out
    finally:
        doc.close()


def extract_receipt_images(
    pdf_path: str | Path,
    *,
    client: LLMClient,
    summary_receipts: list[Receipt],
    file_name: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Vision-read the report's receipt images and enrich the summary receipts.

    Renders the receipt-image pages, runs one `extract_receipt` per image,
    maps each reading to its EXPENSE SUMMARY row, and returns a new receipt
    list (same order / document_ids as `summary_receipts`) where mapped rows
    carry the vision merchant (when the summary had none) + line items, plus a
    `data_quality_note` when the image disagreed with the summary. Per-image
    extraction failures and image readings that mapped to no row land in the
    returned issues (Errors sheet), never a silent drop.

    Pure: does not mutate `summary_receipts` (frozen dataclasses, rebuilt via
    `replace`). No-op (returns the input unchanged) when there are no receipt
    pages.
    """
    path = Path(pdf_path)
    name = file_name or path.name
    issues: list[ParseIssue] = []

    pages = render_receipt_pages(path)
    if not pages:
        return list(summary_receipts), issues

    extractions: list[tuple[int, ExtractedReceipt]] = []
    for page_index, png in pages:
        try:
            extraction = client.extract_receipt(
                file_name=f"{name} p{page_index + 1}",
                images=[(png, "image/png")],
            )
        except Exception as exc:  # noqa: BLE001 -- per-image tolerance
            issues.append(
                ParseIssue(name, page_index + 1, f"receipt-image extraction failed: {exc}")
            )
            continue
        extractions.append((page_index, extraction))

    enriched, unmapped = _map_and_merge(summary_receipts, extractions)

    for page_index, extraction in unmapped:
        # Only flag a reading that actually carried content; a blank/garbage
        # render mapping to nothing is expected, not worth Errors-sheet noise.
        if extraction.vendor or extraction.total or extraction.line_items:
            issues.append(
                ParseIssue(
                    name,
                    page_index + 1,
                    "receipt image did not map to any expense row "
                    f"(vendor={extraction.vendor!r}, total={extraction.total!r}); "
                    "left unattached",
                    severity="warning",
                )
            )

    n_enriched = sum(
        1 for a, b in zip(summary_receipts, enriched) if a.line_items != b.line_items
        or a.detected_vendor != b.detected_vendor
    )
    logger.info(
        "vision receipts: %d image(s) read, %d of %d summary row(s) enriched",
        len(extractions), n_enriched, len(summary_receipts),
    )
    return enriched, issues


def _map_and_merge(
    summary_receipts: list[Receipt],
    extractions: list[tuple[int, ExtractedReceipt]],
) -> tuple[list[Receipt], list[tuple[int, ExtractedReceipt]]]:
    """Join vision readings to summary rows and merge. Returns the enriched
    receipt list (input order preserved) plus the readings that mapped to no
    row. Greedy, one-to-one: reference match first, then amount + currency
    with page order breaking ties."""
    # receipt index -> (page index, reading); the page rides along so the
    # merged receipt can record where its image lives (preview, 2026-07-25).
    assigned: dict[int, tuple[int, ExtractedReceipt]] = {}
    used: set[int] = set()                        # extraction position used

    # Phase A -- reference match. A reading's reference must resolve to exactly
    # one still-free summary row (an ambiguous ref falls through to amounts).
    ref_to_rows: dict[str, list[int]] = {}
    for i, r in enumerate(summary_receipts):
        nref = _norm_ref(r.detected_reference)
        if nref:
            ref_to_rows.setdefault(nref, []).append(i)
    for pos, (page, ext) in enumerate(extractions):
        nref = _norm_ref(ext.reference)
        if not nref:
            continue
        free = [i for i in ref_to_rows.get(nref, []) if i not in assigned]
        if len(free) == 1:
            assigned[free[0]] = (page, ext)
            used.add(pos)

    # Phase B -- amount + currency, page order. Readings are already in page
    # order; each takes the earliest still-free row whose amount (and currency,
    # when both known) agrees. Earliest-free tie-break aligns the two orders.
    for pos, (page, ext) in enumerate(extractions):
        if pos in used:
            continue
        ext_total = _to_decimal(ext.total)
        if ext_total is None:
            continue
        ext_ccy = _norm_ccy(ext.currency)
        for i, r in enumerate(summary_receipts):
            if i in assigned:
                continue
            if not _amount_close(ext_total, r.detected_total):
                continue
            row_ccy = _norm_ccy(r.detected_currency)
            if ext_ccy and row_ccy and ext_ccy != row_ccy:
                continue
            assigned[i] = (page, ext)
            used.add(pos)
            break

    enriched = [
        _merge_receipt(r, *assigned[i]) if i in assigned else r
        for i, r in enumerate(summary_receipts)
    ]
    unmapped = [
        (page, ext) for pos, (page, ext) in enumerate(extractions) if pos not in used
    ]
    return enriched, unmapped


def render_receipt_page(pdf_path: str | Path, page_index: int) -> bytes | None:
    """Render ONE page of the report PDF to PNG bytes (per-receipt preview,
    2026-07-25). None when the page does not exist."""
    out = _render_pages(Path(pdf_path), [page_index])
    return out[0][1] if out else None


def _merge_receipt(receipt: Receipt, page: int, ext: ExtractedReceipt) -> Receipt:
    """Attach a vision reading to one summary row. The summary keeps ownership
    of amount / currency / date / reference (the matcher's inputs); vision
    contributes the merchant (only when the summary had none) and the line
    items, plus a data-quality note on any amount/currency disagreement."""
    line_items = tuple(
        LineItem(
            description=item.description,
            line_total=_to_decimal(item.line_total) or Decimal("0"),
            quantity=_to_decimal(item.quantity),
            unit_price=_to_decimal(item.unit_price),
        )
        for item in ext.line_items
        if (item.description or "").strip()
    )

    # Vision line items win (they drive the LINE categorization path); an empty
    # vision read leaves the summary's own (empty) items so the vendor path
    # still runs on the now-known merchant.
    new_items = line_items or receipt.line_items
    # Fill the merchant only when the summary lacked one -- the summary vendor,
    # when present, is deterministic and stays the backbone. The short brand
    # follows the effective vendor: when the summary owns it, clean the
    # summary name; when vision supplied it, prefer the model's own brand.
    if receipt.detected_vendor:
        vendor = receipt.detected_vendor
        vendor_clean = receipt.vendor_clean or clean_vendor_name(receipt.detected_vendor)
    else:
        vendor = ext.vendor or None
        vendor_clean = ext.vendor_clean or clean_vendor_name(ext.vendor)

    notes: list[str] = []
    ext_total = _to_decimal(ext.total)
    if (
        ext_total is not None
        and receipt.detected_total is not None
        and not _amount_close(ext_total, receipt.detected_total)
    ):
        notes.append(
            f"receipt image total {ext_total} differs from report "
            f"{receipt.detected_total} (report amount kept for matching)"
        )
    ext_ccy = _norm_ccy(ext.currency)
    row_ccy = _norm_ccy(receipt.detected_currency)
    if ext_ccy and row_ccy and ext_ccy != row_ccy:
        notes.append(
            f"receipt image currency {ext_ccy} differs from report {row_ccy} "
            "(report currency kept for matching)"
        )
    note = "; ".join(notes) or None

    from dataclasses import replace

    return replace(
        receipt,
        detected_vendor=vendor,
        vendor_clean=vendor_clean,
        line_items=new_items,
        ocr_text=receipt.ocr_text or ext.notes,
        data_quality_note=note or receipt.data_quality_note,
        receipt_image_page=page,
    )


# ── small parse helpers ─────────────────────────────────────────────


def _norm_ref(ref: str | None) -> str | None:
    """Normalize a reference for matching: lowercase, strip everything but
    letters + digits. `"335 536 4010"` and `"3355364010"` compare equal."""
    if not ref:
        return None
    norm = re.sub(r"[^a-z0-9]", "", ref.lower())
    return norm or None


def _norm_ccy(ccy: str | None) -> str | None:
    if not ccy:
        return None
    c = ccy.strip().upper()
    return c or None


def _to_decimal(raw: str | Decimal | None) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, Decimal):
        return raw
    s = str(raw).strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _amount_close(a: Decimal | None, b: Decimal | None) -> bool:
    """True when two amounts agree within the larger of 0.02 or 1% of the
    reference. Loose enough for a vision misread of the last cent, tight
    enough to separate distinct small receipts."""
    if a is None or b is None:
        return False
    tolerance = max(Decimal("0.02"), abs(b) * Decimal("0.01"))
    return abs(a - b) <= tolerance
