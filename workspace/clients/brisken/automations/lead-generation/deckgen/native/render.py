# /// script
# dependencies = ["pywin32", "python-pptx>=1.0.2"]
# ///
"""Render a composed native deck to PDF + per-slide QA PNGs via PowerPoint
COM, then run the structural checks and the banned-terms gate.

    uv run render.py <deck>

Differences from deckgen v2's render.py, on purpose: the native family ships
Century Gothic / Segoe UI as NAMED system fonts, not embedded (verified on
the Dirk-approved Overview: zero ppt/fonts parts). So the v2 embedded-font
gate is replaced by a stricter native gate: zero ppt/fonts parts AND every
run's typeface is in tokens.ALLOWED_FONTS.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import zipfile
from pathlib import Path

_here = Path(__file__).parent


def _load(name, path=None):
    spec = importlib.util.spec_from_file_location(name, path or (_here / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


T = _load("tokens")
common = _load("common", _here.parent / "common.py")
ops = _load("pptx_slide_ops", Path(__file__).resolve().parents[7] / "tools" / "pptx_slide_ops.py")


def native_font_gate(pptx: Path) -> list[str]:
    errs = []
    with zipfile.ZipFile(pptx) as z:
        names = z.namelist()
        font_parts = [n for n in names if n.startswith("ppt/fonts/")]
        if font_parts:
            errs.append(f"unexpected embedded font parts: {font_parts}")
        faces = set()
        for n in names:
            if n.startswith("ppt/slides/") and n.endswith(".xml"):
                faces |= set(re.findall(rb'typeface="([^"]+)"', z.read(n)))
        bad = {f.decode() for f in faces} - T.ALLOWED_FONTS
        if bad:
            errs.append(f"non-family fonts in slides: {sorted(bad)} "
                        f"(allowed: {sorted(T.ALLOWED_FONTS)})")
    return errs


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    deck = sys.argv[1]
    deck_dir = common.dist_dir() / deck
    pptxs = sorted(deck_dir.glob("*.pptx"))
    if not pptxs:
        print(f"no pptx in {deck_dir} — run compose.py first")
        return 1
    src = pptxs[0]
    qa = common.qa_dir() / deck
    qa.mkdir(parents=True, exist_ok=True)
    for old in qa.glob("*.png"):
        old.unlink()

    import win32com.client

    ppt = win32com.client.Dispatch("PowerPoint.Application")
    try:
        pres = ppt.Presentations.Open(str(src), ReadOnly=True, WithWindow=False)
        pdf_path = src.with_suffix(".pdf")
        pres.SaveAs(str(pdf_path), 32)
        n = pres.Slides.Count
        for i in range(1, n + 1):
            pres.Slides(i).Export(str(qa / f"s{i:02d}.png"), "PNG", 1600, 900)
        pres.Close()
    finally:
        ppt.Quit()

    font_errs = native_font_gate(src)
    rids = ops.validate_rids(src)
    hidden = [r["n"] for r in ops.roster(src) if r["hidden"]]
    print(f"rendered: {pdf_path.name} + {n} QA PNGs -> {qa}")
    print(f"fonts: {'OK' if not font_errs else font_errs}  "
          f"rIds: {'OK' if not rids else rids}  hidden: {hidden or 'none'}")
    if font_errs or rids or hidden:
        return 1

    validator = common.main_clone_root() / "tools" / "validate-demo-material.py"
    res = subprocess.run(
        ["uv", "run", str(validator), "--client", "brisken", "--dir", str(deck_dir)],
        capture_output=True, text=True,
    )
    print(res.stdout.strip())
    if res.returncode != 0:
        print(res.stderr.strip())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
