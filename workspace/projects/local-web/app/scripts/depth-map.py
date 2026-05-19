# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "onnxruntime>=1.17",
#   "numpy>=1.26",
#   "pillow>=10.3",
#   "huggingface-hub>=0.23",
# ]
# ///
"""
depth-map.py — generate grayscale depth maps for the local-web hero photos.

Feeds the budgeted WebGL parallax hero (skil_web-build section 4b). One
still + one depth map; a tiny shader displaces the still by the depth so
the image separates into layers on pointer/gyro.

Model: onnx-community/depth-anything-v2-small (Depth-Anything-V2-Small,
ONNX, CPU). Downloaded once into the HF cache; the resulting PNGs are
committed so the Docker/Fly build stays hermetic (no model at deploy),
exactly like the Pexels imagery pipeline.

Convention: output PNG is 8-bit grayscale, NEAR = white (255), FAR = black
(0). The shader treats brighter = closer.

Usage:  uv run app/scripts/depth-map.py [slug ...]
        (no args = all sites with a hero.jpg)
Writes  src/assets/<slug>/hero-depth.png  next to hero.jpg.
"""
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from PIL import Image

REPO = "onnx-community/depth-anything-v2-small"
MODEL_FILE = "onnx/model.onnx"
APP = Path(__file__).resolve().parents[1]
ASSETS = APP / "src" / "assets"
# Depth-Anything-V2 image processor defaults.
SIZE = 518  # multiple of 14 (ViT patch)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(img: Image.Image) -> np.ndarray:
    im = img.convert("RGB").resize((SIZE, SIZE), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = (a - MEAN) / STD
    a = np.transpose(a, (2, 0, 1))[None]  # NCHW
    return np.ascontiguousarray(a, dtype=np.float32)


def main() -> int:
    slugs = sys.argv[1:] or sorted(
        p.parent.name for p in ASSETS.glob("*/hero.jpg")
    )
    if not slugs:
        print("no hero.jpg found under src/assets/*/")
        return 1

    print(f"resolving model {REPO}/{MODEL_FILE} ...")
    model_path = hf_hub_download(repo_id=REPO, filename=MODEL_FILE)
    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name

    for slug in slugs:
        hero = ASSETS / slug / "hero.jpg"
        if not hero.exists():
            print(f"SKIP {slug}: no hero.jpg")
            continue
        src = Image.open(hero)
        w, h = src.size
        depth = sess.run(None, {in_name: preprocess(src)})[0]
        depth = np.squeeze(depth).astype(np.float32)  # (SIZE, SIZE)

        # Normalize to 0..1, NEAR=high. Depth-Anything outputs inverse
        # depth (larger = closer) already, so just min-max stretch.
        d = depth - depth.min()
        d = d / (d.max() + 1e-6)
        dmap = Image.fromarray((d * 255.0).astype(np.uint8), mode="L")
        dmap = dmap.resize((w, h), Image.BICUBIC)

        out = ASSETS / slug / "hero-depth.png"
        dmap.save(out, optimize=True)
        print(f"OK   {slug}: {out.relative_to(APP)}  ({w}x{h})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
