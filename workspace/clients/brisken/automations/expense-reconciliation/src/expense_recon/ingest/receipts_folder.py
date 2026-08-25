"""Receipts folder ingest — slice 2.2 (vision OCR + PDF text layer).

Chris drops a folder of receipt files instead of hand-extracting them
into a CSV (BLUEPRINT 2.2 / 2.7). Per file:

* Images (.jpg/.jpeg/.png/.webp) → one vision-extraction LLM call.
* PDFs → the text layer is extracted with pypdf first. Digital PDFs
  (Uber email receipts, train tickets, booking confirmations) carry
  their content as text — a plain text-model call is cheaper and more
  accurate than rasterizing. Scanned PDFs with a thin/absent text
  layer fall back to rendering pages via pypdfium2 and the vision call.
* Anything else (including stray .md/.txt notes in the folder) lands
  in the issues list — visible in the Errors sheet, never silently
  dropped (reconciliation guarantee, v2 spec §25.5).

Extraction failures (LLM error, unreadable file) also land in issues;
the surrounding files continue. The extractor must never invent line
items (LD-2): no itemization → empty line_items → the Tier-2
vendor-fallback path triggers in categorization.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..llm.client import ExtractedReceipt, LLMClient
from ..matching.types import LineItem, Receipt
from ..vendor_names import clean_vendor_name
from ._common import ParseIssue, parse_date

logger = logging.getLogger("expense_recon")

IMAGE_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Below this many characters the PDF "text layer" is treated as absent
# (scanned document) and the file is rasterized for the vision call.
MIN_PDF_TEXT_CHARS = 64

# Cap on rendered pages per PDF — receipts are 1-2 pages; a long PDF
# in the folder is almost certainly not a receipt and the cap bounds
# vision cost.
MAX_PDF_PAGES = 4


def parse_receipts_folder(
    path: str | Path,
    legal_entity_id: str,
    client: LLMClient,
    default_currency: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Extract every receipt file in `path` into Receipt objects.

    Tolerant: per-file failures become ParseIssues (line_number 0 —
    there are no rows in an image); the rest of the folder continues.
    """
    path = Path(path)
    receipts: list[Receipt] = []
    issues: list[ParseIssue] = []

    files = sorted(p for p in path.iterdir() if p.is_file())
    if not files:
        issues.append(ParseIssue(path.name, 0, "receipts folder is empty"))
        return receipts, issues

    for file in files:
        if file.name.startswith("."):
            continue
        suffix = file.suffix.lower()
        if suffix not in IMAGE_MIME and suffix != ".pdf":
            issues.append(
                ParseIssue(file.name, 0, f"unsupported receipt file type {suffix!r} (skipped)")
            )
            continue

        try:
            extraction, ocr_text = _extract_file(file, suffix, client)
        except Exception as exc:  # noqa: BLE001 — per-file tolerance
            issues.append(
                ParseIssue(file.name, 0, f"extraction failed: {exc}")
            )
            continue

        receipts.append(
            _to_receipt(
                extraction,
                document_id=file.name,
                legal_entity_id=legal_entity_id,
                default_currency=default_currency,
                ocr_text=ocr_text,
            )
        )
        logger.debug(
            "extracted %s: %d line item(s), confidence %.2f",
            file.name, len(extraction.line_items), extraction.confidence,
        )

    return receipts, issues


def parse_receipt_file(
    file: str | Path,
    legal_entity_id: str,
    client: LLMClient,
    default_currency: str | None = None,
) -> Receipt:
    """Extract ONE receipt file (image or PDF) into a Receipt.

    The single-file twin of `parse_receipts_folder`, for receipts that
    arrive outside the ER export (e.g. emailed to the operator and
    uploaded from the workbench, 2026-07-24). Raises on an unsupported
    type or extraction failure — the caller surfaces the error to the
    operator instead of collecting ParseIssues.
    """
    file = Path(file)
    suffix = file.suffix.lower()
    if suffix not in IMAGE_MIME and suffix != ".pdf":
        raise ValueError(f"unsupported receipt file type {suffix!r}")
    extraction, ocr_text = _extract_file(file, suffix, client)
    return _to_receipt(
        extraction,
        document_id=file.name,
        legal_entity_id=legal_entity_id,
        default_currency=default_currency,
        ocr_text=ocr_text,
    )


def _extract_file(
    file: Path, suffix: str, client: LLMClient
) -> tuple[ExtractedReceipt, str]:
    """Route one file to the right extraction call. Returns the
    extraction plus the text we keep on Receipt.ocr_text (the PDF text
    layer when there is one; the model's notes otherwise)."""
    if suffix in IMAGE_MIME:
        raw = file.read_bytes()
        extraction = client.extract_receipt(
            file_name=file.name, images=[(raw, IMAGE_MIME[suffix])]
        )
        return extraction, extraction.notes

    text = _pdf_text(file)
    if len(text.strip()) >= MIN_PDF_TEXT_CHARS:
        extraction = client.extract_receipt(file_name=file.name, text=text)
        return extraction, text

    images = _pdf_page_images(file)
    extraction = client.extract_receipt(file_name=file.name, images=images)
    return extraction, extraction.notes


def _pdf_text(file: Path) -> str:
    """Concatenated text layer across pages (pypdf)."""
    from pypdf import PdfReader

    reader = PdfReader(str(file))
    parts = []
    for page in reader.pages[:MAX_PDF_PAGES]:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _pdf_page_images(file: Path) -> list[tuple[bytes, str]]:
    """Rasterize a scanned PDF's pages to PNG bytes (pypdfium2)."""
    import io
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(file))
    try:
        images: list[tuple[bytes, str]] = []
        for i in range(min(len(doc), MAX_PDF_PAGES)):
            page = doc[i]
            bitmap = page.render(scale=2.0)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            images.append((buf.getvalue(), "image/png"))
        if not images:
            raise ValueError("PDF has no pages")
        return images
    finally:
        doc.close()


def _to_receipt(
    extraction: ExtractedReceipt,
    *,
    document_id: str,
    legal_entity_id: str,
    default_currency: str | None,
    ocr_text: str,
) -> Receipt:
    currency = (extraction.currency or "").strip().upper() or default_currency

    return Receipt(
        document_id=document_id,
        legal_entity_id=legal_entity_id,
        detected_date=_parse_date_lenient(extraction.date),
        detected_total=_parse_decimal_lenient(extraction.total),
        detected_currency=currency,
        detected_vendor=extraction.vendor,
        vendor_clean=extraction.vendor_clean or clean_vendor_name(extraction.vendor),
        detected_reference=extraction.reference,
        detected_tax=_parse_decimal_lenient(extraction.tax),
        tax_label=extraction.tax_label,
        # Folder OCR has no ER "payment_mode"; the receipt's own card/tender
        # hint is the best paying-card signal for the Zoho Expenses export.
        payment_mode=_payment_mode(extraction),
        document_type=extraction.document_type or "receipt",
        ocr_text=ocr_text,
        line_items=tuple(
            LineItem(
                description=item.description,
                # None = model could not read the amount; 0 keeps the
                # item visible and the vague/illegible description
                # routes it to REVIEW downstream.
                line_total=_parse_decimal_lenient(item.line_total) or Decimal("0"),
                quantity=_parse_decimal_lenient(item.quantity),
                unit_price=_parse_decimal_lenient(item.unit_price),
            )
            for item in extraction.line_items
        ),
    )


def _payment_mode(extraction: ExtractedReceipt) -> str | None:
    """The paying-card signal the entity chain resolves against.

    Two readings of the same line disagree often (2026-08-24 measurement over
    the April batch): asked to transcribe four faded digits the model lands 2
    in 5 and invents the rest — "1234" came back three times, once for a
    receipt that plainly prints 1672 — while asked WHICH of the payer's own
    cards it can see it lands 4 in 5 with no false positives.

    So a confirmed pick replaces whatever digits the free-text hint carried,
    and the tender words are kept around it because they are what the receipt
    says and Criss reads them. With no confirmed pick the hint passes through
    untouched: an unlisted digit run resolves to no card anyway, and dropping
    it would hide a card the registry has not been told about yet.
    """
    hint = (extraction.payment_hint or "").strip()
    last4 = extraction.card_last4
    if not last4:
        return hint or None
    if not hint:
        return f"...{last4}"
    words = re.sub(r"[\dxX*•#]{2,}", "", hint).strip(" -:.,")
    return f"{words} ...{last4}".strip() if words else f"...{last4}"


def _parse_date_lenient(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        return parse_date(raw)
    except ValueError:
        return None


def _parse_decimal_lenient(raw: str | None) -> Decimal | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        return Decimal(str(raw).strip().replace(",", ""))
    except InvalidOperation:
        return None
