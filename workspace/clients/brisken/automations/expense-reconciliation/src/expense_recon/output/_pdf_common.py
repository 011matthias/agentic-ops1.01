"""Shared primitives for the two report documents.

`month_report_pdf` (the month's expenses) and `reconciliation_report_pdf`
(the statement reconciliation) are different documents with the same bones:
a full-Latin font, receipts turned into pages, mini-HTML escaping, and one
paragraph style set so the two never drift into looking like different
products.
"""
from __future__ import annotations

import io
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

# The container installs fonts-dejavu-core (Dockerfile); a dev box usually
# has Arial. Only then do we fall back to a Latin-1 core font — reportlab's
# built-in Helvetica cannot render "Cartão" or "Gebühr", which is exactly
# where this client's receipts live.
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)
_FONT_NAME = "ReportBody"
_FONT_BOLD = "ReportBold"


def register_fonts() -> tuple[str, str]:
    """Register a full-Latin TTF pair with reportlab, or fall back to the
    core fonts. Returns the (body, bold) font names to use."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    override = os.environ.get("EXPENSE_RECON_REPORT_FONT")
    candidates = list(_FONT_CANDIDATES)
    if override:
        candidates = [override, override] + candidates
    regular = bold = None
    for path in candidates:
        if not Path(path).is_file():
            continue
        if regular is None:
            regular = path
        elif bold is None and path != regular:
            bold = path
    if regular is None:
        return "Helvetica", "Helvetica-Bold"
    try:
        pdfmetrics.registerFont(TTFont(_FONT_NAME, regular))
        pdfmetrics.registerFont(TTFont(_FONT_BOLD, bold or regular))
    except Exception:  # noqa: BLE001 - a broken font must not lose the report
        return "Helvetica", "Helvetica-Bold"
    return _FONT_NAME, _FONT_BOLD


def make_styles(body_font: str, bold_font: str) -> dict:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle

    muted = colors.HexColor("#444444")
    return {
        "title": ParagraphStyle(
            "title", fontName=bold_font, fontSize=17, leading=21, spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "sub", fontName=body_font, fontSize=10, leading=14,
            textColor=muted, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=bold_font, fontSize=12, leading=16,
            spaceBefore=12, spaceAfter=5,
        ),
        "cellhead": ParagraphStyle(
            "cellhead", fontName=bold_font, fontSize=8, leading=10,
            textColor=colors.white,
        ),
        "cell": ParagraphStyle("cell", fontName=body_font, fontSize=8, leading=10),
        "cellr": ParagraphStyle(
            "cellr", fontName=body_font, fontSize=8, leading=10, alignment=2,
        ),
        "caption": ParagraphStyle(
            "caption", fontName=bold_font, fontSize=12, leading=15, spaceAfter=4,
        ),
        "capsub": ParagraphStyle(
            "capsub", fontName=body_font, fontSize=9, leading=12, textColor=muted,
        ),
    }


def table_style():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f6f6f6")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def image_to_pdf(data: bytes) -> bytes | None:
    """One image -> one A4 page, fitted inside the margins, aspect kept."""
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:  # noqa: BLE001 - an unreadable file is reported, not fatal
        return None
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    page_w, page_h = 1240, 1754  # A4 at ~150 dpi
    margin = 60
    box_w, box_h = page_w - 2 * margin, page_h - 2 * margin
    scale = min(box_w / img.width, box_h / img.height, 1.0)
    img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))))
    page = Image.new("RGB", (page_w, page_h), "white")
    page.paste(img, ((page_w - img.width) // 2, (page_h - img.height) // 2))
    out = io.BytesIO()
    page.save(out, format="PDF", resolution=150.0)
    return out.getvalue()


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def prepare_evidence(items: list[dict]) -> list[tuple[dict, bytes | None]]:
    """Decide renderability BEFORE captions are written, so a file that
    exists but cannot be turned into pages says so instead of leaving a
    caption with nothing behind it (which reads as "the receipt is here")."""
    from pypdf import PdfReader

    prepared: list[tuple[dict, bytes | None]] = []
    for item in items:
        data = item.get("data")
        if not data:
            prepared.append((item, None))
            continue
        pdf_bytes = data if is_pdf(data) else image_to_pdf(data)
        if pdf_bytes is not None:
            try:
                PdfReader(io.BytesIO(pdf_bytes))
            except Exception:  # noqa: BLE001 - unreadable = not renderable
                pdf_bytes = None
        prepared.append((item, pdf_bytes))
    return prepared


def stitch(document_pdf: bytes, prepared: list[tuple[dict, bytes | None]]) -> bytes:
    """Interleave: the leading pages, then each caption page followed by its
    document's pages. The caption pages are the LAST `len(prepared)` pages of
    `document_pdf`, one per evidence item."""
    from pypdf import PdfReader, PdfWriter

    base = PdfReader(io.BytesIO(document_pdf))
    writer = PdfWriter()
    lead_end = len(base.pages) - len(prepared)
    for page in base.pages[:lead_end]:
        writer.add_page(page)
    for i, (_item, pdf_bytes) in enumerate(prepared):
        writer.add_page(base.pages[lead_end + i])
        if pdf_bytes is None:
            continue
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def esc(text) -> str:
    """Paragraph text is mini-HTML; a vendor called "A & B <Ltd>" must not
    become markup."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ── money: one parse, one sum, in Decimal (backlog item 65) ─────────
#
# Amounts are carried as STRINGS from the extractor to the export so that no
# precision is lost on the way; the store sums them in Decimal
# (`store/reports.py::_currency_totals`). A report that re-sums them in
# binary float throws that away, which is what section 12 row 13 of
# `docs/electronic-storage-system-description.md` discloses. These four are
# the report side of that arithmetic, shared by both documents so the two
# can never drift into summing a month differently.
#
# The second half of row 13 is the silent drop: a row whose amount would not
# parse was skipped with `continue`, so a month could print a total short by
# one receipt with nothing on the page saying so. `sum_amounts` hands the
# unreadable rows BACK instead of swallowing them; the caller owes every one
# of them a visible place.

UNREADABLE_CAPTION = "amount unreadable, not in total"


def parse_amount(text) -> Decimal | None:
    """One amount cell to a Decimal, or None when it cannot be read.

    Blank reads as zero: an empty cell has always counted as nothing, and
    that is a different event from a cell nobody can parse. A non-finite
    value is unreadable rather than a number, because `Decimal("NaN")`
    parses happily and would turn a whole currency's total into "nan" --
    one bad row poisoning every good one is worse than one row dropped.
    """
    raw = str(text if text is not None else "").strip().replace(",", "")
    if not raw:
        return Decimal("0")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def sum_amounts(entries) -> tuple[dict[str, Decimal], list[int]]:
    """Per-currency totals in Decimal, plus the listing numbers of the rows
    whose amount could not be read.

    `entries` yields `(listing_number, currency, amount_text)` per row. An
    empty currency buckets under "?" rather than vanishing, the same way
    the store buckets one under "UNKNOWN".
    """
    totals: dict[str, Decimal] = {}
    unreadable: list[int] = []
    for number, currency, text in entries:
        value = parse_amount(text)
        if value is None:
            unreadable.append(int(number))
            continue
        ccy = str(currency or "") or "?"
        totals[ccy] = totals.get(ccy, Decimal("0")) + value
    return totals, unreadable


def format_totals(totals: dict[str, Decimal], empty: str) -> str:
    """The "EUR 1,234.56  ·  USD 20.00" line, or `empty` when nothing
    summed."""
    return "  ·  ".join(
        f"{ccy} {amount:,.2f}" for ccy, amount in sorted(totals.items())
    ) or empty


def excluded_note(numbers: list[int]) -> str:
    """The footer line that makes a dropped row visible, naming the expense
    numbers so the reader can find them. Empty when every amount read: a
    clean report says nothing rather than "0 receipts excluded"."""
    if not numbers:
        return ""
    listed = ", ".join(str(n) for n in sorted(set(numbers)))
    count = len(set(numbers))
    if count == 1:
        return f"1 receipt excluded from the total: expense {listed}."
    return f"{count} receipts excluded from the total: expenses {listed}."
