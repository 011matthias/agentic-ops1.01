#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "markdown-it-py>=3.0",
# ]
# ///
"""Convert a markdown deliverable to a print-styled PDF via Microsoft Edge.

Renders markdown -> styled HTML -> PDF using Edge's headless print engine
(Chromium). Edge ships with Windows, so there is nothing to install. The
HTML template is the styling source of truth -- edit the CSS block below
to change typography, palette, or page layout.

Toolchain decisions:

  - Edge headless chosen over fpdf2/weasyprint/wkhtmltopdf because:
      * fpdf2 cannot render real CSS -- spacing, page breaks, and table
        layout had to be coded by hand and still drifted from the doc site.
      * weasyprint on Windows needs the GTK runtime (pango/cairo).
      * wkhtmltopdf is unmaintained (last release 2020) and uses an old
        WebKit fork; modern CSS features misrender.
      * Edge is already on every Windows machine, supports the full
        modern CSS print spec (@page, page-break-*, running headers),
        and produces the same output as Print to PDF from the browser.

  - --headless=new + --user-data-dir=<tmp> so the call never attaches to
    the user's existing Edge session. Without --user-data-dir, launching
    Edge with an interactive profile already open just hands the URL to
    that window and the --print-to-pdf flag is silently ignored.

  - Paper size / margins are driven by CSS @page (A4, 18mm sides, 22mm
    top/bottom). Modern Chromium honors @page; we do not pass paper
    flags on the command line.

Usage:
    uv run tools/md-to-pdf.py INPUT.md [OUTPUT.pdf]
    uv run tools/md-to-pdf.py INPUT.md --title "Title" --footer "Footer"
    uv run tools/md-to-pdf.py INPUT.md --keep-html   # leave temp .html for debug

If OUTPUT.pdf is omitted, writes alongside the input with .pdf extension.
Override Edge path with EDGE_PATH env var if non-default install.
"""
from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt


# -------- Edge discovery --------


def find_edge() -> Path:
    """Locate msedge.exe. EDGE_PATH env var wins, then standard installs."""
    override = os.environ.get("EDGE_PATH")
    if override:
        p = Path(override)
        if p.is_file():
            return p
        raise SystemExit(f"ERROR: EDGE_PATH set but not a file: {p}")

    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge Dev\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge Beta\Application\msedge.exe"),
    ]
    # PATH fallback for non-Windows or unusual installs
    from_path = shutil.which("msedge") or shutil.which("microsoft-edge")
    if from_path:
        candidates.insert(0, Path(from_path))

    for c in candidates:
        if c.is_file():
            return c
    raise SystemExit(
        "ERROR: Microsoft Edge not found. Install Edge or set EDGE_PATH "
        "to the full msedge.exe path."
    )


def find_chrome() -> Path | None:
    """Locate chrome.exe as the fallback engine. Edge headless can fail
    silently (writes nothing, exits 0) when an Edge window is open even
    with an isolated --user-data-dir; Chrome takes the same flags."""
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    from_path = shutil.which("chrome") or shutil.which("google-chrome")
    if from_path:
        candidates.insert(0, Path(from_path))
    for c in candidates:
        if c.is_file():
            return c
    return None


# -------- HTML template --------


CSS = """
@page {
  size: A4;
  margin: 22mm 18mm 22mm 18mm;
}

* { box-sizing: border-box; }

html {
  font-size: 10.5pt;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

body {
  font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue",
               Arial, sans-serif;
  color: #0f172a;
  line-height: 1.5;
  margin: 0;
}

h1, h2, h3, h4 {
  color: #0f172a;
  line-height: 1.25;
  font-weight: 700;
  page-break-after: avoid;
  break-after: avoid;
}

/* A heading must never be the last thing on a page: keep it with the block
   that immediately follows (list, paragraph or sub-list), and keep that block
   from splitting away from its heading. Chrome still breaks a block that is
   genuinely taller than a page, so this is safe for long content too. */
h2 + ul, h2 + ol, h2 + p, h2 + h3, h2 + h4,
h3 + ul, h3 + ol, h3 + p,
h4 + ul, h4 + ol, h4 + p {
  page-break-inside: avoid;
  break-inside: avoid;
}
li { page-break-inside: avoid; break-inside: avoid; }

h1 {
  font-size: 22pt;
  margin: 0 0 0.4em 0;
  padding-top: 4pt;
  border-top: 3pt solid #2563eb;
  display: inline-block;
  padding-right: 12pt;
}

h2 {
  font-size: 14pt;
  color: #2563eb;
  margin: 0 0 0.5em 0;
  page-break-before: always;
  break-before: page;
}

h2:first-of-type {
  page-break-before: avoid;
  break-before: auto;
  margin-top: 1.4em;
}

h3 {
  font-size: 11.5pt;
  margin: 1em 0 0.3em 0;
}

p, li {
  font-size: 10.5pt;
  margin: 0 0 0.55em 0;
}

strong { color: #0f172a; font-weight: 700; }
em { font-style: italic; color: #1f2937; }

ul, ol {
  margin: 0 0 0.7em 0;
  padding-left: 1.3em;
}

li { margin-bottom: 0.25em; }
li::marker { color: #2563eb; }

hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 1.2em 0;
}

a {
  color: #1d4ed8;
  text-decoration: none;
}
a:hover { text-decoration: underline; }

blockquote {
  margin: 1em 0;
  padding: 0.6em 0.9em 0.6em 1em;
  background: #eff6ff;
  border-left: 3pt solid #2563eb;
  color: #475569;
  font-style: italic;
  page-break-inside: avoid;
}

code {
  font-family: "Cascadia Mono", "Consolas", "Menlo", monospace;
  font-size: 9.5pt;
  background: #f1f5f9;
  padding: 0.05em 0.35em;
  border-radius: 3px;
}

pre {
  background: #f1f5f9;
  padding: 0.7em 0.9em;
  border-radius: 4px;
  font-size: 9pt;
  line-height: 1.45;
  overflow-x: hidden;
  white-space: pre-wrap;
  word-wrap: break-word;
  page-break-inside: avoid;
}

pre code {
  background: none;
  padding: 0;
  font-size: inherit;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.9em 0 1.1em 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}

thead {
  background: #1e293b;
  color: #ffffff;
}

th {
  padding: 6pt 8pt;
  text-align: left;
  font-weight: 600;
  border: 1px solid #1e293b;
}

td {
  padding: 5pt 8pt;
  border: 1px solid #e2e8f0;
  vertical-align: top;
}

tbody tr:nth-child(even) {
  background: #f8fafc;
}

/* Footer via running element (page counter) */
@page {
  @bottom-center {
    content: "__FOOTER_TEXT__    |    page " counter(page);
    font-family: "Segoe UI", sans-serif;
    font-size: 8.5pt;
    color: #475569;
    padding-top: 6mm;
    border-top: 0.5pt solid #2563eb;
  }
}
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
__CSS__
</style>
</head>
<body>
__BODY__
</body>
</html>
"""


def build_html(md_text: str, title: str, footer_text: str) -> str:
    md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": False})
    md.enable("table")
    body_html = md.render(md_text)

    css = CSS.replace("__FOOTER_TEXT__", html.escape(footer_text, quote=True))
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", html.escape(title))
        .replace("__CSS__", css)
        .replace("__BODY__", body_html)
    )


# -------- PDF generation --------


class EngineProducedNothing(Exception):
    """The browser exited 0 but wrote no PDF (silent-failure mode)."""


def run_engine_to_pdf(engine: Path, html_path: Path, out_path: Path) -> None:
    """Invoke a Chromium engine headless to print HTML to PDF.

    Prints to a fresh temp file and only then replaces out_path, so a
    pre-existing PDF at out_path can never masquerade as a successful
    render when the engine silently writes nothing."""
    tmp_out = out_path.with_name(out_path.name + ".tmp")
    tmp_out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="md-to-pdf-engine-") as tmp_profile:
        cmd = [
            str(engine),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={tmp_profile}",
            f"--print-to-pdf={tmp_out}",
            html_path.as_uri(),
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise SystemExit(f"ERROR: {engine.name} headless timed out after 120s")

        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            tmp_out.unlink(missing_ok=True)
            raise SystemExit(f"ERROR: {engine.name} exited with code {result.returncode}")

        if not tmp_out.is_file() or tmp_out.stat().st_size == 0:
            tmp_out.unlink(missing_ok=True)
            raise EngineProducedNothing(engine.name)

    os.replace(tmp_out, out_path)


# -------- main --------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Convert a markdown file to a print-styled PDF via Edge headless."
    )
    ap.add_argument("input", help="Path to markdown input file.")
    ap.add_argument("output", nargs="?",
                    help="Optional PDF output path. Defaults to INPUT with .pdf suffix.")
    ap.add_argument("--title", default=None,
                    help="Override title used in HTML <title> (default: H1 from input).")
    ap.add_argument("--footer", default=None,
                    help="Override footer text (default: '{title}  |  Confidential').")
    ap.add_argument("--keep-html", action="store_true",
                    help="Leave the intermediate HTML file next to the PDF for debugging.")
    args = ap.parse_args(argv)

    in_path = Path(args.input).resolve()
    if not in_path.is_file():
        sys.stderr.write(f"ERROR: input not found: {in_path}\n")
        return 2

    out_path = Path(args.output).resolve() if args.output else in_path.with_suffix(".pdf")

    md_text = in_path.read_text(encoding="utf-8")

    title = args.title
    if not title:
        title = in_path.stem.replace("-", " ").replace("_", " ").title()
        for line in md_text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

    footer_text = args.footer if args.footer is not None else f"{title}  |  Confidential"

    edge = find_edge()
    html_str = build_html(md_text, title=title, footer_text=footer_text)

    used_engine = edge

    def render(html_path: Path) -> None:
        nonlocal used_engine
        try:
            run_engine_to_pdf(edge, html_path, out_path)
        except EngineProducedNothing:
            chrome = find_chrome()
            if chrome is None:
                raise SystemExit(
                    f"ERROR: {edge.name} ran but produced no PDF (silent "
                    "headless failure; close open Edge windows or install "
                    "Chrome as fallback)."
                )
            sys.stderr.write(
                f"WARN: {edge.name} produced no PDF; retrying with {chrome}\n"
            )
            used_engine = chrome
            run_engine_to_pdf(chrome, html_path, out_path)

    if args.keep_html:
        html_path = out_path.with_suffix(".html")
        html_path.write_text(html_str, encoding="utf-8")
        render(html_path)
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".html",
            prefix="md-to-pdf-", delete=False,
        ) as f:
            f.write(html_str)
            html_path = Path(f.name)
        try:
            render(html_path)
        finally:
            try:
                html_path.unlink()
            except OSError:
                pass

    pages = "?"
    try:
        with out_path.open("rb") as f:
            data = f.read()
        pages = str(data.count(b"/Type /Page") - data.count(b"/Type /Pages"))
    except OSError:
        pass

    sys.stdout.write(f"Wrote {out_path}\n")
    sys.stdout.write(f"  pages: {pages}\n")
    sys.stdout.write(f"  engine: {used_engine.name} ({used_engine})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
