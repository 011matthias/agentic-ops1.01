"""Stages 4 and 6: the cut list (EDL) for one kept moment, and the checks on its render.

The EDL is the only input to the renderer (stage 5), so a video can be
rendered again without analysing again. A render reaches data/ready/ only
when every check passes; otherwise it stays in data/renders/ with the reasons.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from . import follow
from . import render as render_mod

F1_RANGE = (15.0, 60.0)
LUFS_TOLERANCE = 1.0
CAPTION_MAX_DRIFT_S = 0.2


class ProduceError(Exception):
    pass


def load_layouts(path: Path) -> dict:
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


def compose(con: sqlite3.Connection, moment_id: int, *, layouts: dict,
            style: str | None = None) -> dict:
    m = con.execute(
        "SELECT m.*, s.streamer, s.file, s.kind, s.video_id, s.win_start_s, s.top_clip_id, "
        "st.display_name FROM moments m JOIN sections s ON s.id = m.section_id "
        "JOIN streamers st ON st.login = s.streamer WHERE m.id = ?", (moment_id,)).fetchone()
    if m is None:
        raise ProduceError(f"no moment {moment_id}")
    if m["status"] != "keep":
        raise ProduceError(f"moment {moment_id} is '{m['status']}', only kept moments render")
    layout = layouts.get(m["streamer"])
    if not layout or not layout.get("facecam"):
        raise ProduceError(f"no layout profile for {m['streamer']} in config/layouts.yaml")
    t = con.execute("SELECT words FROM transcripts WHERE section_id = ?",
                    (m["section_id"],)).fetchone()
    a, b = m["in_s"], m["out_s"]
    words = [{"w": w["w"], "s": round(w["s"] - a, 2), "e": round(min(w["e"], b) - a, 2)}
             for w in (json.loads(t["words"]) if t else []) if a <= w["s"] < b]
    hooks = json.loads(m["hooks"] or "[]")
    sets = sorted(render_mod.STYLE_SETS)
    return {
        "id": f"m{moment_id}-f1", "format": "F1", "moment": moment_id,
        "streamer": m["streamer"], "display_name": m["display_name"],
        "source": {"file": m["file"], "kind": m["kind"], "video_id": m["video_id"],
                   "top_clip_id": m["top_clip_id"],
                   "vod_start_s": (m["win_start_s"] + a) if m["kind"] == "vod" else None},
        "in_s": a, "out_s": b, "words": words,
        "layout": {"facecam": layout["facecam"], "gameplay": layout.get("gameplay"),
                   "cam_crop": layout.get("cam_crop")},
        "hook": hooks[0] if hooks else None, "hooks": hooks, "title": m["title"],
        "category": m["category"],
        "style": style or sets[moment_id % len(sets)],  # rotate sets, no single template
        "fps": 60,
    }


# --- checks (stage 6) ------------------------------------------------------------

@dataclass
class CheckResult:
    passed: bool
    measured: dict
    failures: list[str] = field(default_factory=list)


# strip sharpness / middle sharpness below this in 90 % of frames = a bar. Calibrated
# 2026-11-19 on m5-f1: fit layout with blurred bars top 0.096 / bottom 0.082 (p90),
# filled band top 0.41 / bottom 1.98 / left 1.29 / right 1.39
BAR_RATIO = 0.2
BAR_STRIPS = {"top": (slice(0, 48), slice(None)), "bottom": (slice(-48, None), slice(None)),
              "left": (slice(None), slice(0, 40)), "right": (slice(None), slice(-40, None))}


BAND_FPS = 4.0


def band_frames(video: Path, *, fps: float = BAND_FPS):
    """The gameplay band alone, gray, quarter size, `fps` frames a second (numpy array
    n x 320 x 270). Measured without the facecam band above: it is bright and sharp and
    hid the pause map and the dark bush from whole-frame checks on 2026-11-19."""
    import numpy as np

    w, h = render_mod.W // 4, render_mod.GAME_H // 4
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf",
         f"fps={fps},crop={render_mod.W}:{render_mod.GAME_H}:0:{render_mod.CAM_H},"
         f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, timeout=900).stdout
    n = len(raw) // (w * h)
    return np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w).astype(np.float32)


def _laplacian(frames):
    import numpy as np

    return np.abs(4 * frames[:, 1:-1, 1:-1] - frames[:, :-2, 1:-1] - frames[:, 2:, 1:-1]
                  - frames[:, 1:-1, :-2] - frames[:, 1:-1, 2:])


def band_bars(frames) -> list[str]:
    """Edges of the gameplay band that look like a bar in nearly every frame.

    A bar (letterbox black, or the blurred fill of the old fit layout) has almost no
    fine detail in every frame; real gameplay at an edge (sky, clouds, a wall) has
    some in most frames. sharpness = mean |Laplacian| of a strip / of the band's
    middle, per frame, 90th percentile over the video, below BAR_RATIO = bar.
    """
    import numpy as np

    if not len(frames):
        return []
    h, w = frames.shape[1:]
    lap = _laplacian(frames)
    mid = lap[:, h // 4:3 * h // 4, w // 4:3 * w // 4].mean(axis=(1, 2)) + 1e-3
    bars = []
    for name, (rows, cols) in BAR_STRIPS.items():
        ratio = lap[:, rows, cols].mean(axis=(1, 2)) / mid
        if np.percentile(ratio, 90) < BAR_RATIO:
            bars.append(name)
    return bars


# Stretches where the band shows no playable picture. Per sample at 4 fps, gray 0-255,
# quarter size. Calibrated 2026-11-19 on 21 fetched sections and clips (7,260 samples):
# fades and black screens, PS5 / title / load screens, pause and save menus, two maps and
# a shop menu, the m5 weapon wheel; against night and dusk driving, dim red interiors and
# the clean parts of m5-f1 and m15-f1.
DARK_P95 = 10.0       # 95 % of the pixels darker than this = black. Fades measure 0; the
                      # darkest night-driving sample 14.6 (mean brightness could not
                      # separate them: night 8-29, a dim red club 11-18, the bush 5-12)
FROZEN_DIFF = 0.25    # mean change from the sample before below this = the game stands
                      # still: paused map, pause / save / load menu, title or shop screen.
                      # Paused screens 0-0.1; night driving 0.30 at its stillest
MENU_LUMA, MENU_SHARP, MENU_DIFF = 60.0, 6.0, 4.0
                      # bright, blurred and slow = a menu over the blurred game (weapon
                      # wheel: brightness 99, sharpness 5.2, change 2.6; driving in daylight
                      # never under sharpness 7.4). Dark scenes stay out by brightness
MIN_SAMPLES = 3       # 3 samples in a row (0.75 s): a stretch under 0.5 s never holds 3
CAPTION_ROWS = slice((300 - 100) // 4, (300 + 100) // 4)  # captions sit at band y 300;
                      # their word-by-word highlight would make a paused map look moving


def band_stretches(frames, *, fps: float = BAND_FPS) -> list[dict]:
    """Stretches of at least MIN_SAMPLES where the band shows no playable picture:
    "dark" (fade to black, black screen), "frozen" (the game paused: map, menu, title or
    load screen), "menu" (a menu over the blurred game: weapon wheel, pause menu).

    A short flash passes: m15's camera crossed a bush for 0.45 s (measured at 30 fps).
    Not caught: a map the streamer is zooming or scrolling (moving, sharp, mid-bright,
    like ohnePixel's at the start of section 17573); the contact sheet shows it in judge.
    """
    import numpy as np

    n = len(frames)
    if not n:
        return []
    keep = np.ones(frames.shape[1], bool)
    keep[CAPTION_ROWS] = False
    picture = frames[:, keep]
    luma = picture.mean(axis=(1, 2))
    p95 = np.percentile(picture.reshape(n, -1), 95, axis=1)
    sharp = _laplacian(frames)[:, keep[1:-1]].mean(axis=(1, 2))
    diff = np.r_[np.inf, np.abs(np.diff(picture, axis=0)).mean(axis=(1, 2))]
    kinds = ["dark" if p95[i] < DARK_P95
             else "frozen" if diff[i] < FROZEN_DIFF
             else "menu" if (luma[i] > MENU_LUMA and sharp[i] < MENU_SHARP
                             and diff[i] < MENU_DIFF)
             else None for i in range(n)]
    found, i = [], 0
    while i < n:
        j = i
        while j < n and kinds[j]:
            j += 1
        if j - i >= MIN_SAMPLES:
            run = kinds[i:j]
            found.append({"kind": max(set(run), key=run.count), "t": round(i / fps, 2),
                          "s": round((j - i) / fps, 2)})
        i = max(j, i + 1)
    return found


def measure(video: Path) -> dict:
    """One ffmpeg pass: loudness, silence, black and frozen stretches; plus ffprobe;
    plus one look at the gameplay band: bars at its edges, dark or menu stretches."""
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,avg_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout)
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
         "-af", "ebur128=framelog=quiet,silencedetect=n=-50dB:d=2",
         "-vf", "blackdetect=d=0.5:pix_th=0.10,freezedetect=n=0.003:d=2",
         "-f", "null", "-"], capture_output=True, text=True, timeout=900).stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    stream = probe["streams"][0]
    num, den = (stream.get("avg_frame_rate") or "0/1").split("/")
    band = band_frames(video)
    return {
        "width": stream["width"], "height": stream["height"],
        "fps": round(float(num) / float(den or 1), 2),
        "duration": float(probe["format"]["duration"]),
        "lufs": float(lufs[-1]) if lufs else None,
        "silences": len(re.findall(r"silence_start", err)),
        "black": len(re.findall(r"black_start", err)),
        "frozen": len(re.findall(r"freeze_start", err)),
        "band_bars": band_bars(band),
        "band_stretches": band_stretches(band),
    }


def caption_drift(edl: dict, heard: list[dict], sample: int = 12) -> float | None:
    """Median gap between caption word starts and the same words heard again in
    the rendered audio (matched in order on normalised text)."""
    def norm(w: str) -> str:
        return re.sub(r"[^a-z0-9']", "", w.lower())
    gaps, j = [], 0
    for w in render_mod.caption_words(edl["words"]):
        key = norm(w["w"])
        for k in range(j, min(j + 6, len(heard))):
            if key and norm(heard[k]["w"]) == key:
                gaps.append(abs(heard[k]["s"] - w["s"]))
                j = k + 1
                break
        if len(gaps) >= sample:
            break
    if not gaps:
        return None
    gaps.sort()
    return round(gaps[len(gaps) // 2], 3)


def check(edl: dict, video: Path, *, measured: dict,
          heard: list[dict] | None) -> CheckResult:
    f = []
    want = edl["out_s"] - edl["in_s"]
    if (measured["width"], measured["height"]) != (render_mod.W, render_mod.H):
        f.append(f"size {measured['width']}x{measured['height']}, want 1080x1920")
    if not (F1_RANGE[0] <= measured["duration"] <= F1_RANGE[1] + 0.1):
        f.append(f"duration {measured['duration']:.1f} s outside F1 15-60 s")
    if abs(measured["duration"] - want) > 0.25:
        f.append(f"duration {measured['duration']:.2f} s, cut list says {want:.2f} s")
    if measured["lufs"] is None or abs(measured["lufs"] - render_mod.TARGET_LUFS) > LUFS_TOLERANCE:
        f.append(f"loudness {measured['lufs']} LUFS, want -14 +-1")
    for key, label in (("silences", "silence over 2 s"), ("black", "black stretch"),
                       ("frozen", "frozen stretch over 2 s")):
        if measured[key]:
            f.append(f"{measured[key]} x {label}")
    if measured["band_bars"]:
        f.append(f"bars in the gameplay band ({', '.join(measured['band_bars'])}), "
                 f"want it filled")
    for s in measured.get("band_stretches") or []:
        what = {"dark": "black", "frozen": "game paused (map, menu or loading screen)",
                "menu": "menu over the game"}[s["kind"]]
        f.append(f"{what} in the gameplay band at t={s['t']} s for {s['s']} s: "
                 f"move the cut or drop the moment")
    plan = edl.get("follow")
    if plan:
        step = 1 / plan["sample_fps"]
        wide = [round(i * step, 2) for i, w in enumerate(plan["too_wide"]) if w]
        if wide:
            f.append(f"main object wider than the window at {len(wide)} samples "
                     f"(t={wide[:6]} s): owner decides, fill the band or show it whole")
        out = [m["t"] for m in follow.misses(plan) if not m["too_wide"]]
        if out:
            f.append(f"main object not completely in the window at {len(out)} samples "
                     f"(t={out[:6]} s)")
    drift = caption_drift(edl, heard) if heard is not None else None
    measured = {**measured, "caption_drift_s": drift}
    if heard is not None and (drift is None or drift > CAPTION_MAX_DRIFT_S):
        f.append(f"captions drift {drift} s from the audio, want under 0.2 s")
    return CheckResult(not f, measured, f)


def follow_planner(data_dir: Path) -> Callable[[dict, Path], dict]:
    """The real planner: YOLOX on the CPU over the moment's samples (follow.py)."""
    def plan(edl: dict, src: Path) -> dict:
        detector = follow.yolox_detector(follow.model_path(data_dir))
        return follow.plan(src, edl["in_s"], edl["out_s"], layout=edl["layout"],
                           detector=detector)
    return plan


def produce(con: sqlite3.Connection, moment_id: int, *, data_dir: Path, layouts: dict,
            style: str | None = None,
            renderer: Callable[[dict, Path, Path], Path] = render_mod.render,
            measurer: Callable[[Path], dict] = measure,
            listener: Callable[[Path], list[dict]] | None = None,
            planner: Callable[[dict, Path], dict] | None = None,
            ) -> tuple[dict, Path, CheckResult]:
    """Compose, plan the gameplay window, render and check one kept moment; a pass is
    copied to data/ready/."""
    edl = compose(con, moment_id, layouts=layouts, style=style)
    src = data_dir / edl["source"]["file"]
    edl["follow"] = (planner or follow_planner(data_dir))(edl, src)
    work = data_dir / "renders" / edl["id"]
    work.mkdir(parents=True, exist_ok=True)
    (work / "edl.json").write_text(json.dumps(edl, indent=2, ensure_ascii=False), encoding="utf-8")
    video = renderer(edl, src, work / f"{edl['id']}.mp4")
    result = check(edl, video, measured=measurer(video),
                   heard=listener(video) if listener else None)
    (work / "check.json").write_text(json.dumps(
        {"passed": result.passed, "failures": result.failures, "measured": result.measured},
        indent=2), encoding="utf-8")
    if result.passed:
        ready = data_dir / "ready" / edl["id"]
        ready.mkdir(parents=True, exist_ok=True)
        for name in (video.name, "edl.json", "check.json"):
            shutil.copy2(work / name, ready / name)
        video = ready / video.name
    return edl, video, result
