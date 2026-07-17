# /// script
# dependencies = ["pywin32", "python-pptx>=1.0.2"]
# ///
"""Render a composed deck to PDF + per-slide QA PNGs via PowerPoint COM,
then run the structural checks and the banned-terms gate over the folder
(now including the PDF — what the client actually opens).

    uv run render.py mdh-commodities

Requires desktop PowerPoint. The pptx is opened ReadOnly and never saved
back, so embedded-font edit restrictions cannot bite.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_here = Path(__file__).parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


common = _load("common", _here / "common.py")
ops = _load("pptx_slide_ops", Path(__file__).resolve().parents[6] / "tools" / "pptx_slide_ops.py")


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

    fonts = ops.check_embedded_fonts(src)
    rids = ops.validate_rids(src)
    hidden = [r["n"] for r in ops.roster(src) if r["hidden"]]
    print(f"rendered: {pdf_path.name} + {n} QA PNGs -> {qa}")
    print(f"fonts: {fonts['font_parts']} parts ok={fonts['ok']}  rIds: {'OK' if not rids else rids}  hidden: {hidden or 'none'}")
    if not fonts["ok"] or rids or hidden:
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
