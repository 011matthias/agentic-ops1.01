#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Convert SVG files to PNG via Edge headless screenshot.

Wraps the SVG in a minimal HTML shell so the browser engine renders it with
real font fallback (Inter -> Segoe UI on Windows, system-ui elsewhere), then
captures a PNG at the SVG's intrinsic width/height (or a user-supplied size).

Why Edge headless: matches md-to-pdf.py toolchain decision. Available on
every Windows machine. Renders web fonts and CSS the same way browsers do.
Alternatives (cairosvg, rsvg-convert) either don't ship on Windows or
mis-render text without a custom font setup.

Usage:
    uv run tools/svg-to-png.py INPUT.svg [OUTPUT.png]
    uv run tools/svg-to-png.py INPUT.svg --size 1024x1024
    uv run tools/svg-to-png.py DIRECTORY/                 # batch mode
    uv run tools/svg-to-png.py DIRECTORY/ --size 1024x1024

Override Edge path with EDGE_PATH env var if non-default install.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_edge() -> Path:
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
    from_path = shutil.which("msedge") or shutil.which("microsoft-edge")
    if from_path:
        candidates.insert(0, Path(from_path))

    for c in candidates:
        if c.is_file():
            return c
    raise SystemExit(
        "ERROR: Microsoft Edge not found. Install Edge or set EDGE_PATH."
    )


def svg_dimensions(svg_text: str) -> tuple[int, int] | None:
    """Read width/height attrs from the <svg> root if present."""
    m = re.search(r"<svg\b[^>]*>", svg_text, re.IGNORECASE)
    if not m:
        return None
    tag = m.group(0)
    w = re.search(r'\bwidth\s*=\s*"(\d+(?:\.\d+)?)"', tag)
    h = re.search(r'\bheight\s*=\s*"(\d+(?:\.\d+)?)"', tag)
    if w and h:
        return int(float(w.group(1))), int(float(h.group(1)))
    # Fall back to viewBox
    vb = re.search(r'\bviewBox\s*=\s*"\s*([\d.\-eE\s]+)"', tag)
    if vb:
        parts = vb.group(1).split()
        if len(parts) == 4:
            return int(float(parts[2])), int(float(parts[3]))
    return None


HTML_WRAPPER = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
html, body { margin: 0; padding: 0; background: transparent; }
svg { display: block; }
</style>
</head><body>__SVG__</body></html>
"""


def render_svg_to_png(edge: Path, svg_path: Path, out_path: Path, size: tuple[int, int]) -> None:
    svg_text = svg_path.read_text(encoding="utf-8")
    html_str = HTML_WRAPPER.replace("__SVG__", svg_text)

    with tempfile.TemporaryDirectory(prefix="svg-to-png-") as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "page.html"
        html_path.write_text(html_str, encoding="utf-8")
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()

        cmd = [
            str(edge),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--user-data-dir={profile_dir}",
            f"--window-size={size[0]},{size[1]}",
            f"--screenshot={out_path}",
            html_path.as_uri(),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"ERROR: Edge headless timed out rendering {svg_path}")

        if result.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            raise SystemExit(f"ERROR: Edge failed to render {svg_path}")


def parse_size(s: str | None) -> tuple[int, int] | None:
    if not s:
        return None
    m = re.match(r"^\s*(\d+)\s*[xX,]\s*(\d+)\s*$", s)
    if not m:
        raise SystemExit(f"ERROR: --size must look like 1024x1024, got: {s!r}")
    return int(m.group(1)), int(m.group(2))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="SVG to PNG via Edge headless.")
    ap.add_argument("input", help="SVG file or directory containing SVGs.")
    ap.add_argument("output", nargs="?", help="PNG output path (single-file mode).")
    ap.add_argument("--size", default=None,
                    help="Output size as WxH (e.g. 1024x1024). Defaults to SVG intrinsic.")
    args = ap.parse_args(argv)

    in_path = Path(args.input).resolve()
    if not in_path.exists():
        sys.stderr.write(f"ERROR: input not found: {in_path}\n")
        return 2

    forced_size = parse_size(args.size)
    edge = find_edge()

    if in_path.is_file():
        if in_path.suffix.lower() != ".svg":
            sys.stderr.write(f"ERROR: not an SVG: {in_path}\n")
            return 2
        out_path = Path(args.output).resolve() if args.output else in_path.with_suffix(".png")
        size = forced_size or svg_dimensions(in_path.read_text(encoding="utf-8")) or (1024, 1024)
        render_svg_to_png(edge, in_path, out_path, size)
        sys.stdout.write(f"Wrote {out_path} ({size[0]}x{size[1]})\n")
        return 0

    # Directory mode
    if args.output:
        sys.stderr.write("ERROR: output arg only valid for single-file mode\n")
        return 2
    svgs = sorted(in_path.glob("*.svg"))
    if not svgs:
        sys.stderr.write(f"ERROR: no .svg files in {in_path}\n")
        return 2
    for svg in svgs:
        out_path = svg.with_suffix(".png")
        size = forced_size or svg_dimensions(svg.read_text(encoding="utf-8")) or (1024, 1024)
        render_svg_to_png(edge, svg, out_path, size)
        sys.stdout.write(f"Wrote {out_path} ({size[0]}x{size[1]})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
