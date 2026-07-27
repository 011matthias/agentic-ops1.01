# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Build the curated, normalized, TRANSPARENT customer-logo library that the
`customers` wall renders (Dirk's 2026-07-27 direction: transparent logos,
swappable per prospect).

Sources, all durable (gitignored client context, so the library is
re-derivable without .scratch):
  - SharePoint pull   context/decks/customer-logos/sharepoint-pull/   (Brisken
                      "CUSTOMER LOGOS" folder; pulled read-only via CDP)
  - web-sourced       context/decks/customer-logos/web-sourced/       (Commons
                      renders for Nestle/Sony/LG not in the folder)
  - reference deck    the four logos only the reference carries (accenture,
                      ab-inbev, medmix, entegris), extracted straight from the
                      pinned media so this script needs no other build step.

Each logo is white-keyed where its only source is boxed (medmix, entegris),
trimmed to its content bbox, padded, capped to MAXDIM, saved {name}.png. The
result is `customers` -> logosets.ALL_WALL_LOGOS, verified by assets.py.

    CDP_PORT=9223 uv run sp_pull_customer_logos ...   # (one-time raw pull)
    uv run build-logo-library.py                      # normalize -> library
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

_here = Path(__file__).parent
_cspec = importlib.util.spec_from_file_location("common", _here / "common.py")
common = importlib.util.module_from_spec(_cspec)
sys.modules["common"] = common
_cspec.loader.exec_module(common)
_aspec = importlib.util.spec_from_file_location("assets", _here / "native" / "assets.py")
assets = importlib.util.module_from_spec(_aspec)
sys.modules["assets"] = assets
_aspec.loader.exec_module(assets)

ROOT = common.main_clone_root()
CL = ROOT / "workspace/clients/brisken/context/decks/customer-logos"
SP, WEB, OUT = CL / "sharepoint-pull", CL / "web-sourced", CL / "normalized"
OUT.mkdir(parents=True, exist_ok=True)

# reference-only logos: name -> media file in the reference deck (invert the
# pinned CLIENT_LOGOS map so the mapping has one home).
_REF_MEDIA = {name: src for src, name in assets.CLIENT_LOGOS.items()}
REF_ONLY = {"accenture", "ab-inbev", "medmix", "entegris"}

# canonical brand -> source. "REF:<name>" pulls from the reference deck.
SOURCES = {
    "google": SP / "GOOGLE logo.png",
    "accenture": "REF:accenture",
    "equinor": SP / "EQUINOR logo.png",
    "nike": SP / "Nike-Logo-Transparent-Background-1.png",
    "adm": SP / "Archer_Daniels_Midland_logo.svg-transparent.png",
    "ab-inbev": "REF:ab-inbev",
    "sulzer": SP / "SULZER logo.png",
    "barry-callebaut": SP / "BARRY CALLEBAUT logo.png",
    "zespri": SP / "ZESPRI logo.png",
    "angus": SP / "ANGUS_Promo_Logo_Color@2x-1.png",
    "medmix": "REF:medmix",       # whitekey
    "entegris": "REF:entegris",   # whitekey
    "weyerhaeuser": SP / "WEYERHAEUSER logo.png",
    "southwire": SP / "SOUTHWIRE logo.png",
    "yeti": SP / "Yeti Logo transparent black.png",
    "sothebys": SP / "SOTHEBYS logo.png",
    "imax": SP / "IAMX logo.png",
    "ford": SP / "Ford-Motor-Company-Logo-transparent.png",
    "siemens-energy": SP / "Siemens_Energy_logo.svg-transparent.png",
    "asr-group": SP / "ASR-Group-logo transparent.png",
    "nestle": WEB / "nestle.png",
    "sony": WEB / "sony.png",
    "lge": WEB / "lge.png",
    "kaust": SP / "KAUST logo.png",
    "grupo-moura": SP / "baterias-moura-logo-vector.png",
}
WHITEKEY = {"medmix", "entegris"}
MAXDIM, PAD = 640, 8


def _load_ref(name: str) -> Image.Image:
    src = _REF_MEDIA[name]
    with zipfile.ZipFile(common.reference_path()) as z:
        return Image.open(io.BytesIO(z.read(f"ppt/media/{src}"))).convert("RGBA")


def whitekey(im: Image.Image) -> Image.Image:
    rgb = im.convert("RGB")
    S, (w, h) = (255, 0, 255), im.size
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
               (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        try:
            ImageDraw.floodfill(rgb, xy, S, thresh=40)
        except Exception:
            pass
    src, out = rgb.load(), im.convert("RGBA")
    px = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] == S:
                r, g, b, _ = px[x, y]
                px[x, y] = (r, g, b, 0)
    return out


def trim(im: Image.Image) -> Image.Image:
    bbox = im.split()[3].getbbox()
    return im.crop(bbox) if bbox else im


def main() -> int:
    built = {}
    for brand, src in SOURCES.items():
        if isinstance(src, str) and src.startswith("REF:"):
            im = _load_ref(src[4:])
        elif src.exists():
            im = Image.open(src).convert("RGBA")
        else:
            print(f"  MISSING SOURCE: {brand} <- {src}")
            continue
        if brand in WHITEKEY:
            im = whitekey(im)
        im = trim(im)
        w, h = im.size
        scale = MAXDIM / max(w, h)
        if scale < 1:
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
        w, h = im.size
        canvas = Image.new("RGBA", (w + 2 * PAD, h + 2 * PAD), (0, 0, 0, 0))
        canvas.alpha_composite(im, (PAD, PAD))
        canvas.save(OUT / f"{brand}.png")
        built[brand] = {"size": list(canvas.size), "whitekey": brand in WHITEKEY}
        print(f"  {brand:16} {canvas.size[0]}x{canvas.size[1]}")
    (OUT / "manifest.json").write_text(json.dumps(built, indent=2))
    print(f"\n{len(built)} logos -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
