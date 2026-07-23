# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Contact sheets (2x3 grids) from a rendered deck's QA PNGs, for the
slide-by-slide visual review that the approved Overview went through
(that loop caught 8+ real layout bugs before Dirk ever saw the deck).

    uv run inspect.py <deck>     # qa/<deck>/s*.png -> qa/<deck>/g*.png
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_here = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("common", _here.parent / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    qa = common.qa_dir() / sys.argv[1]
    pngs = sorted(qa.glob("s*.png"))
    if not pngs:
        print(f"no QA PNGs in {qa} — run render.py first")
        return 1
    for old in qa.glob("g*.png"):
        old.unlink()
    CW, CH, COLS, ROWS = 800, 450, 2, 3
    PER, GAP, LBL, PAD = COLS * ROWS, 18, 26, 16
    try:
        font = ImageFont.truetype("segoeuib.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    groups = [pngs[i:i + PER] for i in range(0, len(pngs), PER)]
    for gi, g in enumerate(groups):
        W = PAD * 2 + COLS * CW + (COLS - 1) * GAP
        H = PAD * 2 + ROWS * (CH + LBL) + (ROWS - 1) * GAP
        m = Image.new("RGB", (W, H), (44, 48, 52))
        d = ImageDraw.Draw(m)
        for i, p in enumerate(g):
            r, c = divmod(i, COLS)
            x = PAD + c * (CW + GAP)
            y = PAD + r * (CH + LBL + GAP)
            im = Image.open(p).convert("RGB")
            im.thumbnail((CW, CH))
            m.paste(im, (x + (CW - im.width) // 2, y + LBL))
            d.text((x, y + 2), p.stem.upper(), fill=(120, 230, 240), font=font)
        m.save(qa / f"g{gi + 1}.png")
        print(qa / f"g{gi + 1}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
