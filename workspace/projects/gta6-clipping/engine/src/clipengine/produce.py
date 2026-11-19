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
        "layout": {"facecam": layout["facecam"], "gameplay": layout.get("gameplay")},
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


def measure(video: Path) -> dict:
    """One ffmpeg pass: loudness, silence, black and frozen stretches; plus ffprobe."""
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
    return {
        "width": stream["width"], "height": stream["height"],
        "fps": round(float(num) / float(den or 1), 2),
        "duration": float(probe["format"]["duration"]),
        "lufs": float(lufs[-1]) if lufs else None,
        "silences": len(re.findall(r"silence_start", err)),
        "black": len(re.findall(r"black_start", err)),
        "frozen": len(re.findall(r"freeze_start", err)),
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
    drift = caption_drift(edl, heard) if heard is not None else None
    measured = {**measured, "caption_drift_s": drift}
    if heard is not None and (drift is None or drift > CAPTION_MAX_DRIFT_S):
        f.append(f"captions drift {drift} s from the audio, want under 0.2 s")
    return CheckResult(not f, measured, f)


def produce(con: sqlite3.Connection, moment_id: int, *, data_dir: Path, layouts: dict,
            style: str | None = None,
            renderer: Callable[[dict, Path, Path], Path] = render_mod.render,
            measurer: Callable[[Path], dict] = measure,
            listener: Callable[[Path], list[dict]] | None = None) -> tuple[dict, Path, CheckResult]:
    """Compose, render and check one kept moment; a pass is copied to data/ready/."""
    edl = compose(con, moment_id, layouts=layouts, style=style)
    work = data_dir / "renders" / edl["id"]
    work.mkdir(parents=True, exist_ok=True)
    (work / "edl.json").write_text(json.dumps(edl, indent=2, ensure_ascii=False), encoding="utf-8")
    video = renderer(edl, data_dir / edl["source"]["file"], work / f"{edl['id']}.mp4")
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
