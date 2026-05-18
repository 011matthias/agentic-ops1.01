#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["Pillow>=10", "pillow-heif>=0.18"]
# ///
"""Convert HEIC/HEIF images to PNG or JPG.

Word on Windows refuses to insert .heic files without the paid Microsoft
HEVC Video Extensions codec. Converting to PNG sidesteps that entirely.

Usage:
    uv run tools/heic-to-png.py INPUT.heic [OUTPUT.png]
    uv run tools/heic-to-png.py DIRECTORY/                 # batch mode
    uv run tools/heic-to-png.py INPUT.heic --jpg           # write JPG instead
    uv run tools/heic-to-png.py INPUT.heic --quality 90    # JPG quality (default 92)

PNG is the default (lossless, alpha support). JPG is smaller and
universally compatible. Output sits next to the input by default.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()


def convert_one(src: Path, out: Path, fmt: str, quality: int) -> None:
    img = Image.open(src)
    if fmt == "jpg":
        img = img.convert("RGB")
        img.save(out, format="JPEG", quality=quality, optimize=True)
    else:
        img.save(out, format="PNG", optimize=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="HEIC/HEIF to PNG (or JPG).")
    ap.add_argument("input", help="HEIC file or directory containing HEIC files.")
    ap.add_argument("output", nargs="?", help="Output path (single-file mode).")
    ap.add_argument("--jpg", action="store_true", help="Write JPG instead of PNG.")
    ap.add_argument("--quality", type=int, default=92, help="JPG quality (default 92).")
    args = ap.parse_args(argv)

    fmt = "jpg" if args.jpg else "png"
    suffix = ".jpg" if fmt == "jpg" else ".png"

    in_path = Path(args.input).resolve()
    if not in_path.exists():
        sys.stderr.write(f"ERROR: input not found: {in_path}\n")
        return 2

    if in_path.is_file():
        if in_path.suffix.lower() not in {".heic", ".heif"}:
            sys.stderr.write(f"ERROR: not a HEIC/HEIF file: {in_path}\n")
            return 2
        out_path = Path(args.output).resolve() if args.output else in_path.with_suffix(suffix)
        convert_one(in_path, out_path, fmt, args.quality)
        sys.stdout.write(f"Wrote {out_path}\n")
        return 0

    if args.output:
        sys.stderr.write("ERROR: output arg only valid for single-file mode\n")
        return 2
    heics = sorted([p for p in in_path.iterdir() if p.suffix.lower() in {".heic", ".heif"}])
    if not heics:
        sys.stderr.write(f"ERROR: no .heic/.heif files in {in_path}\n")
        return 2
    for h in heics:
        out_path = h.with_suffix(suffix)
        convert_one(h, out_path, fmt, args.quality)
        sys.stdout.write(f"Wrote {out_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
