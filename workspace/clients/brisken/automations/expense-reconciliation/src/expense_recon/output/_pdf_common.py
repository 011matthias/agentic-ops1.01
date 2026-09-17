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
import tempfile
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


# One receipt must not decide how big the whole document gets. The report is
# assembled in the memory of a single 1024 MB machine, holding every receipt
# in the month plus the assembled document, and an individual upload may be
# 15 MB; a 900-page scan appended whole is how that machine runs out. Sixty
# pages is far above anything the two live months hold (the largest receipt
# there is an 11-page AWS invoice, 151 receipt pages across both months), so
# the cap bounds the pathological case without touching the real one.
MAX_RECEIPT_PAGES = 60


def probe_pdf(pdf_bytes: bytes) -> tuple[int | None, str]:
    """Do to a receipt exactly what assembly will do, and report what
    happened. Returns `(n_pages, note)`; `n_pages is None` means the file
    cannot be turned into pages and `note` says why, in words a caption can
    print.

    The point is that the probe opens no LESS than assembly opens.
    `PdfReader(...)` on its own parses the index and nothing else, so a
    password-protected receipt passed it and then raised at `add_page` while
    the document was being stitched, which lost the WHOLE month's report to a
    500 with nothing naming the file (`docs/electronic-storage-system-
    description.md` 7.3). Enumerating the pages and copying each one into a
    throwaway writer is the operation that fails, so failing it here is what
    makes the caption truthful. Ingest's own tolerance does not cover this:
    `receipts_folder._pdf_text` reads at most `MAX_PDF_PAGES` (4) pages, so a
    PDF damaged on page 5 is extracted fine and only breaks in the report.

    An encrypted file is reported rather than opened. Nothing here guesses a
    password, so the reviewer sees which file needs one instead of a report
    that silently dropped it.
    """
    from pypdf import PdfReader, PdfWriter

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted:
            return None, ("the file is password-protected, so the report "
                          "cannot open it")
        probe = PdfWriter()
        for page in list(reader.pages)[:MAX_RECEIPT_PAGES]:
            probe.add_page(page)
        n_pages = len(reader.pages)
    except Exception as exc:  # noqa: BLE001 - unreadable = not renderable
        return None, f"the file could not be read ({type(exc).__name__})"
    if n_pages > MAX_RECEIPT_PAGES:
        return n_pages, (
            f"{n_pages} pages; the first {MAX_RECEIPT_PAGES} are included "
            f"here, open the file in the app for the rest"
        )
    return n_pages, ""


def prepare_evidence(items: list[dict]) -> list[tuple[dict, bytes | None]]:
    """Decide renderability BEFORE captions are written, so a file that
    exists but cannot be turned into pages says so instead of leaving a
    caption with nothing behind it (which reads as "the receipt is here").

    Per item, the outcome is also written back onto the evidence dict:
    `receipt_render` is `"ok"` or `"failed"` (set only where the item has
    `data`, so an expense with no document keeps neither key), and
    `render_note` is the caption's reason. That is the channel the caller
    reads the result on: the builders return one `bytes`, and the count of
    receipts that produced no page is something the review screen has to be
    able to state without anyone reading a log.
    """
    prepared: list[tuple[dict, bytes | None]] = []
    for item in items:
        data = item.get("data")
        if not data:
            item.pop("receipt_render", None)
            item.pop("render_note", None)
            prepared.append((item, None))
            continue
        pdf_bytes = data if is_pdf(data) else image_to_pdf(data)
        if pdf_bytes is None:
            note = ("this file is not a readable image, so it could not be "
                    "rendered into the report")
        else:
            n_pages, note = probe_pdf(pdf_bytes)
            if n_pages is None:
                pdf_bytes = None
        item["receipt_render"] = "failed" if pdf_bytes is None else "ok"
        item["render_note"] = note
        prepared.append((item, pdf_bytes))
    return prepared


def caption_mark(pages: list[int]):
    """A zero-size flowable that records the page it lands on.

    Placed right after the `PageBreak` that opens an evidence caption, it
    tells `stitch` which page is that caption's, so receipt pages can sit
    INSIDE the document (item 138: each card's receipts follow that card's
    listing) instead of only after its last page."""
    from reportlab.platypus import Flowable

    class _Mark(Flowable):
        def wrap(self, *_args):
            return 0, 0

        def draw(self):
            pages.append(self.canv.getPageNumber())

    return _Mark()


def stitch(
    document_pdf: bytes,
    prepared: list[tuple[dict, bytes | None]],
    caption_pages: list[int] | None = None,
) -> bytes:
    """Interleave each caption page with its document's pages.

    Without `caption_pages` the caption pages are the LAST `len(prepared)`
    pages of `document_pdf`, one per evidence item. With it (the 1-based page
    of each item's caption, in `prepared` order, recorded by `caption_mark`)
    each document's pages follow its own caption wherever that sits, so a
    report can put a card's receipts behind that card's section. A caption
    must own its page (a `PageBreak` before it and before whatever follows
    its section). A mark count that does not line up with `prepared` would
    misfile every receipt, so it falls back to appending the documents after
    the last page: out of place, never dropped."""
    from pypdf import PdfReader, PdfWriter

    base = PdfReader(io.BytesIO(document_pdf))
    writer = PdfWriter()
    if caption_pages is not None and len(caption_pages) == len(prepared):
        after: dict[int, list[bytes | None]] = {}
        for page_no, (_item, pdf_bytes) in zip(caption_pages, prepared):
            after.setdefault(page_no, []).append(pdf_bytes)
        for i, page in enumerate(base.pages, start=1):
            writer.add_page(page)
            for pdf_bytes in after.get(i, []):
                _add_document_pages(writer, pdf_bytes)
        return _written(writer)
    if caption_pages is not None:
        for page in base.pages:
            writer.add_page(page)
        for _item, pdf_bytes in prepared:
            _add_document_pages(writer, pdf_bytes)
        return _written(writer)
    lead_end = len(base.pages) - len(prepared)
    for page in base.pages[:lead_end]:
        writer.add_page(page)
    for i, (_item, pdf_bytes) in enumerate(prepared):
        writer.add_page(base.pages[lead_end + i])
        _add_document_pages(writer, pdf_bytes)
    return _written(writer)


def _add_document_pages(writer, pdf_bytes: bytes | None) -> None:
    from pypdf import PdfReader

    if pdf_bytes is None:
        return
    # Per file, because the alternative is the whole month. One receipt
    # that raised here used to abort the assembly, so the request 500ed
    # and the period produced NO report at all: not a partial one, not a
    # caption, nothing naming the file. `probe_pdf` has already run these
    # same operations over these same bytes, so a failure reaching this
    # point is the residual case rather than the expected one; the caption
    # is laid out before stitching and cannot be rewritten from here,
    # which is why the decision belongs in `prepare_evidence` and this is
    # only the belt that keeps the rest of the document.
    try:
        pages = list(PdfReader(io.BytesIO(pdf_bytes)).pages)
        for page in pages[:MAX_RECEIPT_PAGES]:
            writer.add_page(page)
    except Exception:  # noqa: BLE001 - one receipt never costs the month
        return


def _written(writer) -> bytes:
    # Spooled, not `BytesIO().getvalue()`: that held the serialized document
    # twice at once, on the same machine this assembly already fills.
    with tempfile.TemporaryFile() as fh:
        writer.write(fh)
        fh.seek(0)
        return fh.read()


# ── per-card sections (backlog item 138) ────────────────────────────
#
# Owner, 2026-09-17: "the output (PDF) is also not organized in the
# different cards that were reconciled." A month is reconciled card by card,
# so both documents section on the same grouping, derived here once.

NO_CARD_SECTION_LABEL = "No card"


def card_name(entry: dict) -> str:
    """A coverage entry's name for a document: its label, with the digits
    beside it when they add something the label does not already say."""
    label = str(entry.get("label") or "").strip()
    digits = [str(d) for d in (entry.get("digits") or []) if str(d).strip()]
    extra = [d for d in digits if d not in label]
    return f"{label} ({'/'.join(extra)})" if label and extra else (label or "-")


def card_sections(
    view: dict, receipt_cards: dict[str, tuple[str, str]]
) -> list[dict]:
    """The month's per-card sections, in document order.

    `view` is `build_view`'s payload. `receipt_cards` is every receipt in
    the pool, in pool order: `{document_id: (card key, card label)}`, the
    card the tool resolved for it (item 137's chain) or `("", "")`.

    Charges group on `rows[].coverage_key`, which joins `coverage[].key`;
    the key is never parsed. A receipt a charge holds follows that charge's
    card, even where its own resolved card differs (the row's
    `cards_differ` names that inside the section rather than moving it). A
    receipt nobody holds goes to its resolved card. The last section,
    `key` "" and never dropped while it has content, takes the charges no
    coverage entry claims (and the "no card on the charge" entry) and the
    receipts with no card.

    Each section: `key`, `label`, `coverage` (the entry, or None; the last
    section carries the "no card on the charge" entry when there is one), `rows`
    (its charges, in payload order) and `receipt_docs` (held receipts in
    charge order, then the unheld ones in pool order). Sections with
    neither charges nor receipts are left out; a card with nothing this
    month is already a line in the coverage table.
    """
    coverage = {
        str(c.get("key") or ""): c for c in (view.get("coverage") or [])
    }
    order: list[str] = [k for k in coverage if k]
    labels: dict[str, str] = {k: card_name(c) for k, c in coverage.items() if k}
    rows_by: dict[str, list[dict]] = {}
    docs_by: dict[str, list[str]] = {}
    held: set[str] = set()
    for row in view.get("rows") or []:
        key = str(row.get("coverage_key") or "")
        if key not in labels:
            key = ""
        rows_by.setdefault(key, []).append(row)
        doc = str(row.get("chosen_document_id") or "")
        if doc and doc not in held:
            held.add(doc)
            docs_by.setdefault(key, []).append(doc)
    for doc, (card_key, card_label) in receipt_cards.items():
        if doc in held:
            continue
        key = str(card_key or "")
        if key and key not in labels:
            labels[key] = str(card_label or key)
            order.append(key)
        docs_by.setdefault(key, []).append(doc)
    out = []
    for key in [*order, ""]:
        if not (rows_by.get(key) or docs_by.get(key)):
            continue
        out.append({
            "key": key,
            "label": labels.get(key) or NO_CARD_SECTION_LABEL,
            # The "" entry is the charges with no card; its figures are the
            # same arithmetic as every card's, so the last section keeps them.
            "coverage": coverage.get(key),
            "rows": rows_by.get(key, []),
            "receipt_docs": docs_by.get(key, []),
        })
    return out


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
