"""Serve any receipt file as something a browser can actually display.

Backlog item 178. Three feedback notes over 69 days say the same thing in
three ways: *Precisa ser baixado a foto do recibo para ser usada* (#3,
2026-07-16), *recibo nao estar abrindo* (#32, 2026-09-08), *Se possivel ter
uma lupa para ampliar a foto do recibo* (#82, 2026-09-23).

The cause is not the viewer, it is the payload. `/image` hands back the
stored file with its own media type, and **70 of September's 75 receipts are
PDFs**. A PDF cannot go in an `<img>`, so the only thing a browser-side
viewer can do with it is download it, which is note #3 word for word.

So the rendering decision moves to the server: ask for `?as=png` and you get
a raster of the page, whatever the stored file was. One URL, always an image,
and a viewer becomes an `<img>` plus a zoom control.

Kept deliberately narrow: this module decides only *what bytes represent page
N of a receipt file*. Path resolution, run lookup and authorization stay in
the route, which already does them.
"""

from __future__ import annotations

import io
import mimetypes
from pathlib import Path

# Render scale for PDF pages. Matches `receipts_folder._pdf_page_images` and
# `expense_report_images._RENDER_SCALE`, so a receipt looks the same however
# it reached the reviewer. 2.0 puts a 595pt A4 page at ~1190px wide, which is
# readable without zoom and still well under a megabyte.
RENDER_SCALE = 2.0

# A receipt is a receipt, not a book. The cap bounds the work one request can
# ask for; a PDF with more pages than this still renders its first pages.
MAX_PAGES = 60

_IMAGE_TYPES = {
    "image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp",
    "image/tiff",
}


class ReceiptRenderError(Exception):
    """The file exists but could not be turned into a viewable image."""


def guess_media_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def is_pdf(path: Path) -> bool:
    return guess_media_type(path) == "application/pdf"


def is_displayable_image(path: Path) -> bool:
    return guess_media_type(path) in _IMAGE_TYPES


def page_count(path: Path) -> int:
    """Pages in a PDF; 1 for anything else.

    A file that cannot be opened counts as 1 rather than raising: the caller
    uses this for a page-navigation hint, and a wrong hint must not turn a
    servable receipt into an error.
    """
    if not is_pdf(path):
        return 1
    try:
        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(str(path))
        try:
            return max(1, min(len(doc), MAX_PAGES))
        finally:
            doc.close()
    except Exception:
        return 1


def render_page_png(path: Path, page_index: int = 0) -> bytes:
    """Rasterize one page of a PDF to PNG bytes.

    `page_index` is 0-based and clamped into range, so a viewer that asks for
    a page past the end gets the last page instead of an error. Raises
    `ReceiptRenderError` when the file cannot be rendered at all.
    """
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(str(path))
    except Exception as exc:  # corrupt or not really a PDF
        raise ReceiptRenderError(f"cannot open PDF: {exc}") from exc
    try:
        n = len(doc)
        if n == 0:
            raise ReceiptRenderError("PDF has no pages")
        idx = max(0, min(int(page_index), min(n, MAX_PAGES) - 1))
        bitmap = doc[idx].render(scale=RENDER_SCALE)
        buf = io.BytesIO()
        bitmap.to_pil().save(buf, format="PNG")
        return buf.getvalue()
    except ReceiptRenderError:
        raise
    except Exception as exc:
        raise ReceiptRenderError(f"cannot render page {page_index}: {exc}") from exc
    finally:
        doc.close()
