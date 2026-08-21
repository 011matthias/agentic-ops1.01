"""Mail-body rendering for body-only intake mail (C2).

Two pure helpers behind the ``/api/inbound/{archive}/body`` and
``render-ingest`` endpoints: extract a readable text body from a raw
RFC-822 message (HTML stripped to text, entities resolved), and render
that text into a paginated image PDF. The PDF deliberately has no text
layer: it enters the NORMAL ingest path and is read by the same vision
extraction (and document-type quarantine) every scanned receipt gets,
so a rendered Uber forward is judged exactly like a photographed one.
"""
from __future__ import annotations

import io
import os
import re
import time
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser

# ~A4 at 150 dpi; generous margins keep the vision model's crop honest.
_PAGE_W, _PAGE_H = 1240, 1754
_MARGIN = 90
_FONT_SIZE = 24
_LINE_GAP = 10
MAX_BODY_CHARS = 15_000
# The vision reader consumes at most 4 PDF pages (ingest MAX_PDF_PAGES);
# rendering more would silently hide the tail from extraction, so cap at
# the same number and say so on the page instead.
MAX_PAGES = 4
_TRUNCATION_NOTE = "NOTE: long body, truncated in this rendering."


class _TextExtractor(HTMLParser):
    """HTML -> plain text: scripts/styles dropped, block tags become
    newlines, character references resolved by the parser itself."""

    _SKIP = {"script", "style", "head", "title", "template"}
    _BLOCK = {
        "p", "div", "br", "tr", "table", "li", "ul", "ol", "section",
        "article", "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
        "blockquote", "hr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):  # noqa: D102
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")
        elif tag == "td":
            self._chunks.append("  ")

    def handle_endtag(self, tag):  # noqa: D102
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data):  # noqa: D102
        if not self._skip_depth and data:
            self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed HTML: keep what parsed
        pass
    text = parser.text()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_body_text(raw: bytes) -> str:
    """Readable text body of a raw message: the plain part when present,
    else the HTML part stripped to text. Empty string when neither."""
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception:  # noqa: BLE001 - unparseable custody file
        return ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        content = part.get_content()
    except Exception:  # noqa: BLE001 - undecodable payload
        return ""
    if not isinstance(content, str):
        return ""
    if part.get_content_type() == "text/html":
        content = html_to_text(content)
    return content.strip()[:MAX_BODY_CHARS]


# Full-Latin font resolution. Pillow's embedded default (Aileron) has no
# glyphs for umlauts or the euro sign — on a German client's mail that
# turns "27,90 €" and "Gebühr" into tofu boxes and mangles what vision
# extracts. Prefer a real system font; the container installs
# fonts-dejavu-core (Dockerfile).
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Debian container
    "DejaVuSans.ttf",
    "arial.ttf",                                        # Windows dev box
)


def _font():
    from PIL import ImageFont

    override = os.environ.get("EXPENSE_RECON_BODY_FONT")
    for cand in ((override,) if override else ()) + _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(cand, _FONT_SIZE)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=_FONT_SIZE)
    except TypeError:  # Pillow < 10.1: fixed-size bitmap fallback
        return ImageFont.load_default()


def _wrap(draw, font, text: str, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines():
        if not para.strip():
            lines.append("")
            continue
        current = ""
        for word in para.split(" "):
            candidate = f"{current} {word}".strip()
            if current and draw.textlength(candidate, font=font) > width:
                lines.append(current)
                current = word
                # A single over-wide token (URLs) is hard-split by pixels.
                while draw.textlength(current, font=font) > width:
                    cut = max(1, int(len(current) * width /
                                     max(draw.textlength(current, font=font), 1)))
                    lines.append(current[:cut])
                    current = current[cut:]
            else:
                current = candidate
        lines.append(current)
    return lines


def render_body_pdf(
    header_lines: list[str], text: str,
    created: time.struct_time | None = None,
) -> bytes:
    """Render header + body text into a paginated image PDF (bytes).

    Byte-DETERMINISTIC for identical input: Pillow stamps wall-clock
    CreationDate/ModDate by default, which would make every re-render a
    digest-dedupe miss and let a retry double-ingest the same mail
    (adversarial review 2026-08-21 finding 1). ``created`` pins both
    stamps; callers pass the archive's receive stamp so the metadata
    stays audit-honest.
    """
    from PIL import Image, ImageDraw

    font = _font()
    probe = ImageDraw.Draw(Image.new("L", (8, 8), 255))
    usable_w = _PAGE_W - 2 * _MARGIN
    all_lines = _wrap(probe, font, "\n".join(header_lines), usable_w)
    all_lines += ["", "-" * 40, ""]
    all_lines += _wrap(probe, font, text, usable_w)

    line_h = _FONT_SIZE + _LINE_GAP
    per_page = max(1, (_PAGE_H - 2 * _MARGIN) // line_h)
    if len(all_lines) > per_page * MAX_PAGES:
        all_lines = [_TRUNCATION_NOTE, ""] + all_lines
    pages: list = []
    for start in range(0, len(all_lines), per_page):
        if len(pages) >= MAX_PAGES:
            break
        img = Image.new("L", (_PAGE_W, _PAGE_H), 255)
        draw = ImageDraw.Draw(img)
        y = _MARGIN
        for line in all_lines[start:start + per_page]:
            draw.text((_MARGIN, y), line, font=font, fill=0)
            y += line_h
        pages.append(img)
    if not pages:
        pages = [Image.new("L", (_PAGE_W, _PAGE_H), 255)]

    stamp = created or time.gmtime(0)
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:],
                  resolution=150, creationDate=stamp, modDate=stamp)
    return buf.getvalue()
