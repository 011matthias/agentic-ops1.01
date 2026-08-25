# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "imageio-ffmpeg"]
# ///
"""Render clip.html to MP4 by seeking a deterministic timeline frame by frame.

  uv run render.py preview          -> one PNG per scene, both ratios
  uv run render.py wide             -> calvin-clip-16x9-1080p.mp4
  uv run render.py square           -> calvin-clip-1x1-1080.mp4

No audio track: the clip is designed silent-first with burned-in captions.
"""
import pathlib
import subprocess
import sys

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
PAGE = (HERE / "clip.html").as_uri()
OUT = HERE.parent / "video"
FPS = 30
DURATION = 100.0  # 10s intro overview card + the original 90s story

RATIOS = {
    "wide": {"w": 1920, "h": 1080, "q": "", "name": "calvin-clip-16x9-1080p.mp4"},
    "square": {"w": 1080, "h": 1080, "q": "?ratio=square", "name": "calvin-clip-1x1-1080.mp4"},
}
# one representative frame per scene, mid-beat (intro card + the +10s-shifted story)
PREVIEW_TIMES = [4.0, 12.5, 22.0, 28.5, 40.0, 52.0, 64.0, 67.0, 78.0, 87.0, 96.0]


def open_page(pw, ratio):
    r = RATIOS[ratio]
    browser = pw.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": r["w"], "height": r["h"]}, device_scale_factor=1)
    page.goto(PAGE + r["q"])
    page.wait_for_function("window.__ready === true", timeout=15000)
    return browser, page


def preview():
    out = HERE / "preview"
    out.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        for ratio in RATIOS:
            browser, page = open_page(pw, ratio)
            for t in PREVIEW_TIMES:
                page.evaluate("t => window.__seek(t)", t)
                page.screenshot(path=str(out / f"{ratio}-{t:05.1f}s.png"))
            browser.close()
    print(f"preview frames -> {out}")


def encode(ratio):
    r = RATIOS[ratio]
    OUT.mkdir(exist_ok=True)
    dest = OUT / r["name"]
    frames = int(DURATION * FPS)

    ff = subprocess.Popen(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y",
            "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "slow", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(dest),
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    with sync_playwright() as pw:
        browser, page = open_page(pw, ratio)
        for i in range(frames):
            page.evaluate("t => window.__seek(t)", i / FPS)
            ff.stdin.write(page.screenshot(type="png"))
            if i % 300 == 0:
                print(f"  {ratio}: frame {i}/{frames}", flush=True)
        browser.close()

    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit(f"ffmpeg failed for {ratio}")
    print(f"{dest}  ({dest.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preview"
    preview() if mode == "preview" else encode(mode)
