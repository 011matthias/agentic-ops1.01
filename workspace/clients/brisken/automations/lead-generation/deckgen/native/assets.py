# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Deterministic asset extraction for the native deck family.

Reads `ppt/media/*` straight out of the reference mirror
(`context/decks/reference-2026/OnePilot Solutions Overview 2026.pptx`,
re-fetchable via deckgen/fetch-reference.py) and writes the build assets to
`.scratch/deckgen-v2/assets-native/` in the MAIN clone.

Identity tripwire (mirror of deckgen v2's RENAMES tripwire): the three
brand-critical assets are md5-pinned. If Dirk re-uploads a restructured
reference and the media indices shift, extraction FAILS LOUDLY naming the
asset instead of silently shipping the wrong art. The historical trap this
kills: image34 is the Fortitude Re art, image12 is the real
"SAP Certified" badge (an earlier session shipped image34 by mistake).

    uv run assets.py            # extract + verify
    uv run assets.py --debug    # also emit a candidate strip of every media
                                # image, for re-picking after reference drift
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

from PIL import Image

_here = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("common", _here.parent / "common.py")
common = importlib.util.module_from_spec(_spec)
sys.modules["common"] = common
_spec.loader.exec_module(common)

_lspec = importlib.util.spec_from_file_location("logosets", _here / "logosets.py")
logosets = importlib.util.module_from_spec(_lspec)
sys.modules["logosets"] = logosets
_lspec.loader.exec_module(logosets)

# media name in the reference -> (output name, pinned md5 or None)
BRAND_ASSETS = {
    "image1.png": ("brisken_reversed.png", "27082c129947dc47401648d9fb218674"),
    "image2.png": ("brisken_dark.png", "59dd8ab2dd699fd32b30375853b768e3"),
    "image12.png": ("sap_certified.png", "0a4e1f2466238d0723f83a4edb2d9475"),
}

# 20 customer logos off the reference logo wall (slide 4), friendly names.
CLIENT_LOGOS = {
    "image14.png": "google", "image15.png": "accenture", "image16.png": "equinor",
    "image17.png": "imax", "image18.png": "weyerhaeuser", "image19.png": "sothebys",
    "image20.png": "barry-callebaut", "image21.png": "zespri", "image22.png": "sulzer",
    "image23.png": "southwire", "image24.png": "global-brands", "image25.png": "beautycounter",
    "image26.jpeg": "asr-group", "image27.png": "nike", "image28.png": "yeti",
    "image29.jpeg": "angus-chemical", "image30.png": "medmix", "image31.tiff": "entegris",
    "image32.png": "ab-inbev", "image33.jpeg": "adm",
}


def assets_dir() -> Path:
    d = common.main_clone_root() / ".scratch/deckgen-v2/assets-native"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure(force: bool = False) -> Path:
    """Extract assets from the reference mirror; verify md5 pins. Idempotent."""
    out = assets_dir()
    logos = out / "logos"
    logos.mkdir(exist_ok=True)
    ref = common.reference_path()
    if not ref.exists():
        raise SystemExit(f"reference mirror missing: {ref} — run deckgen/fetch-reference.py")

    done_marker = out / ".complete"
    if not (done_marker.exists() and not force):
        with zipfile.ZipFile(ref) as z:
            media = {Path(n).name: n for n in z.namelist() if n.startswith("ppt/media/")}
            for src, (dst, pin) in BRAND_ASSETS.items():
                if src not in media:
                    raise SystemExit(f"ASSET TRIPWIRE: {src} missing from reference media — "
                                     f"reference restructured? Re-pick with --debug.")
                data = z.read(media[src])
                got = hashlib.md5(data).hexdigest()
                if pin and got != pin:
                    raise SystemExit(f"ASSET TRIPWIRE: {src} -> {dst} md5 {got} != pinned {pin}. "
                                     f"Reference media shifted; re-verify identity with --debug "
                                     f"before re-pinning.")
                (out / dst).write_bytes(data)
            for src, name in CLIENT_LOGOS.items():
                if src not in media:
                    raise SystemExit(f"ASSET TRIPWIRE: logo source {src} ({name}) missing from "
                                     f"reference media — reference restructured?")
                im = Image.open(io.BytesIO(z.read(media[src]))).convert("RGBA")
                im.save(logos / f"{name}.png")
        done_marker.write_text("ok")

    # The `customers` wall renders the curated TRANSPARENT library (Dirk's
    # 2026-07-27 direction), not the boxed reference extraction above. Overlay
    # runs every ensure() (cheap copies) so the wall always reflects the
    # current library; reference-extracted logos remain as provenance/fallback.
    _overlay_curated(out)
    _verify_pins(out)
    return out


def _overlay_curated(out: Path) -> None:
    """Copy the curated transparent customer logos over the reference set and
    tripwire if any wall logo is missing."""
    import shutil
    curated = common.customer_logos_dir()
    logos = out / "logos"
    if not curated.exists():
        raise SystemExit(f"curated customer-logo library missing: {curated} — run "
                         f"deckgen/build-logo-library.py to (re)build it")
    for p in sorted(curated.glob("*.png")):
        shutil.copyfile(p, logos / p.name)
    missing = [n for n in logosets.ALL_WALL_LOGOS if not (logos / f"{n}.png").exists()]
    if missing:
        raise SystemExit(f"ASSET TRIPWIRE: wall logos missing from curated library after "
                         f"overlay: {missing} — build-logo-library.py")


def _verify_pins(out: Path) -> None:
    for _, (dst, pin) in BRAND_ASSETS.items():
        p = out / dst
        if not p.exists():
            raise SystemExit(f"asset missing after extraction: {p}")
        got = hashlib.md5(p.read_bytes()).hexdigest()
        if pin and got != pin:
            raise SystemExit(f"ASSET TRIPWIRE: on-disk {dst} md5 {got} != pinned {pin}")
    for name in logosets.ALL_WALL_LOGOS:
        if not (out / "logos" / f"{name}.png").exists():
            raise SystemExit(f"wall logo missing after ensure: {name}.png")


def debug_strip() -> None:
    """Contact strip of every reference media image, for re-picking pins
    after a reference re-upload shifts indices."""
    ref = common.reference_path()
    out = assets_dir()
    cells = []
    with zipfile.ZipFile(ref) as z:
        for n in sorted(z.namelist()):
            if not n.startswith("ppt/media/"):
                continue
            try:
                im = Image.open(io.BytesIO(z.read(n))).convert("RGB")
            except Exception:
                continue
            im.thumbnail((260, 140))
            cells.append((Path(n).name, im))
    cols = 6
    cw, ch, lbl = 270, 150, 18
    rows = (len(cells) + cols - 1) // cols
    strip = Image.new("RGB", (cols * cw, rows * (ch + lbl)), (60, 60, 60))
    from PIL import ImageDraw
    d = ImageDraw.Draw(strip)
    for i, (name, im) in enumerate(cells):
        r, c = divmod(i, cols)
        x, y = c * cw, r * (ch + lbl)
        strip.paste(im, (x + (cw - im.width) // 2, y + lbl + (ch - im.height) // 2))
        d.text((x + 4, y + 2), name, fill=(255, 255, 100))
    p = out / "_media_candidates.png"
    strip.save(p)
    print(p)


if __name__ == "__main__":
    if "--debug" in sys.argv:
        debug_strip()
    d = ensure(force="--force" in sys.argv)
    print(f"assets ok: {d}")
