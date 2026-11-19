"""Stage 5, Bearbeiten und Rendern: one cut list (EDL) in, one 1080x1920 video out.

Layout: the streamer's facecam on top (1080x640), gameplay below (1080x1280),
both cropped from the 1920x1080 source by the streamer's layout profile; the
gameplay window follows the main object (follow.py).
Captions come from the Whisper word times as ASS (2 to 4 words per line, the
spoken word highlighted), the hook sits on top for the first ~3 s, the
streamer's name is shown throughout. Audio is normalised to -14 LUFS in two
passes; video is encoded with h264_nvenc.
"""

from __future__ import annotations

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

from . import follow

W, H = 1080, 1920
CAM_H = 640                      # facecam band on top
GAME_H = H - CAM_H               # gameplay band below
FILLERS = {"uh", "um", "uhm", "erm", "hmm", "mm"}
TARGET_LUFS = -14.0

STYLE_SETS = {
    # name: (caption font, caption size, highlight colour BGR, hook box colour BGR)
    "a": ("Arial Black", 78, "00F0FF", "000000"),
    "b": ("Impact", 86, "4CE14C", "1A1A1A"),
    "c": ("Segoe UI Black", 76, "FFB43C", "101010"),
}


class RenderError(Exception):
    pass


# --- captions ------------------------------------------------------------------

def _ts(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _clean(word: str) -> str:
    return re.sub(r"[{}\\]", "", word).strip()


def caption_words(words: list[dict]) -> list[dict]:
    """Words for captions: fillers dropped, braces/backslashes removed."""
    out = []
    for w in words:
        text = _clean(w["w"])
        if text and text.lower().strip(".,!?") not in FILLERS:
            out.append({"w": text, "s": float(w["s"]), "e": float(w["e"])})
    return out


def chunk(words: list[dict], *, max_words: int = 4, max_gap: float = 0.6) -> list[list[dict]]:
    """2 to 4 words per line; a pause or a sentence end starts a new line."""
    lines: list[list[dict]] = []
    for w in words:
        cur = lines[-1] if lines else None
        if (cur is None or len(cur) >= max_words or w["s"] - cur[-1]["e"] > max_gap
                or cur[-1]["w"].endswith((".", "?", "!"))):
            lines.append([w])
        else:
            cur.append(w)
    # fold a lone trailing word into the line before when it fits
    merged: list[list[dict]] = []
    for line in lines:
        if merged and len(line) == 1 and len(merged[-1]) < max_words \
                and line[0]["s"] - merged[-1][-1]["e"] <= max_gap \
                and not merged[-1][-1]["w"].endswith((".", "?", "!")):
            merged[-1].extend(line)
        else:
            merged.append(line)
    return merged


def build_ass(edl: dict) -> str:
    font, size, hi, box = STYLE_SETS[edl.get("style", "a")]
    duration = edl["out_s"] - edl["in_s"]
    cap_y = CAM_H + 300  # upper gameplay band, clear of most HUDs (owner-approved spot)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,2,5,40,40,0,1
Style: Hook,{font},64,&H00FFFFFF,&H00FFFFFF,&H00{box},&H00{box},-1,0,0,0,100,100,0,0,3,18,0,8,60,60,70,1
Style: Name,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    words = caption_words(edl["words"])
    for line in chunk(words):
        for i, w in enumerate(line):
            start = w["s"]
            end = line[i + 1]["s"] if i + 1 < len(line) else max(w["e"], w["s"] + 0.25)
            text = " ".join(
                (f"{{\\c&H{hi}&\\fscx108\\fscy108}}{x['w'].upper()}{{\\r}}" if j == i
                 else x["w"].upper()) for j, x in enumerate(line))
            events.append(f"Dialogue: 1,{_ts(start)},{_ts(end)},Caption,,0,0,0,,"
                          f"{{\\pos({W // 2},{cap_y})}}{text}")
    if edl.get("hook"):
        hook_end = min(3.2, duration)
        events.append(f"Dialogue: 2,{_ts(0)},{_ts(hook_end)},Hook,,0,0,0,,"
                      f"{{\\fad(0,250)}}{_clean(edl['hook'])}")
    name = _clean(edl.get("display_name") or edl["streamer"])
    events.append(f"Dialogue: 0,{_ts(0)},{_ts(duration)},Name,,0,0,0,,"
                  f"{{\\pos(28,{CAM_H - 58})}}twitch.tv/{name}")
    return head + "\n".join(events) + "\n"


# --- ffmpeg --------------------------------------------------------------------

def _even(x: float) -> int:
    return int(round(x / 2)) * 2


def fit_crop(rect: list[int], aspect: float, src_w: int = 1920, src_h: int = 1080) -> tuple:
    """Grow `rect` (x, y, w, h) around its centre to `aspect` (w/h), inside the source."""
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    w, h = min(w, src_w), min(h, src_h)
    if w / h > aspect + 1e-6:
        w = h * aspect
    else:
        h = w / aspect
    x = min(max(0, cx - w / 2), src_w - w)
    y = min(max(0, cy - h / 2), src_h - h)
    return _even(w), _even(h), _even(x), _even(y)


FOLLOW_CMD = "follow.cmd"


def filter_graph(edl: dict) -> str:
    """Facecam band on top; below it a band-aspect window of the gameplay that fills
    the whole band and follows the main object.

    Owner 2026-11-19, in two steps: first the main object (the jet) must be completely
    visible (a fixed centre crop cut its wings off), then the gameplay must fill the
    whole band (no blurred bars, no letterbox). The window (912x1080 from a 1920x1080
    source) therefore moves: follow.plan gives its x per sample, render() writes one
    position per output frame to follow.cmd, sendcmd feeds it to the crop. The
    streamer's own cam inside the gameplay is blurred, he is shown above.
    """
    cam = fit_crop(edl["layout"]["facecam"], W / CAM_H)
    plan = edl.get("follow") or follow.static(edl["layout"])
    # blur only 40 px around the cam (the size the owner saw); the detector blanks wider
    bx, by, bw, bh = follow.cam_region(edl["layout"]["facecam"], 40, 40)
    move = f"sendcmd=f={FOLLOW_CMD}," if len(plan["x"]) > 1 else ""
    return (f"[0:v]split=3[a][b][c];"
            f"[a]crop={cam[0]}:{cam[1]}:{cam[2]}:{cam[3]},scale={W}:{CAM_H}:flags=lanczos,"
            f"setsar=1[cam];"
            f"[c]crop={bw}:{bh}:{bx}:{by},boxblur=24:3[camblur];"
            f"[b][camblur]overlay={bx}:{by},{move}"
            f"crop@follow=w={plan['crop_w']}:h={plan['crop_h']}:x={plan['x'][0]}:y={plan['y']},"
            f"scale={W}:{GAME_H}:flags=lanczos,setsar=1[game];"
            f"[cam][game]vstack=inputs=2,format=yuv420p,subtitles=edl.ass[v]")


def measure_loudness(src: Path, a: float, b: float) -> dict:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(src),
         "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:print_format=json",
         "-vn", "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", out.stderr, re.S)
    if not match:
        raise RenderError(f"loudnorm pass 1 failed: {out.stderr[-300:]}")
    return json.loads(match.group(0))


NVENC = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "12M",
         "-maxrate", "20M", "-bufsize", "24M", "-profile:v", "high"]
X264 = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"]


@lru_cache(maxsize=1)
def video_encoder() -> tuple[str, ...]:
    """NVENC when the driver can open it, else x264 on the CPU.

    ffmpeg 8.1 needs NVENC API 13.1 (driver 610+); the laptop's driver 560.94
    has 12.2, so on 2026-11-19 every NVENC open failed. One tiny test encode
    decides, so a driver update switches the renderer back without a code change.
    """
    test = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1",
                           *NVENC[:2], "-f", "null", "-"], capture_output=True, timeout=60)
    return tuple(NVENC if test.returncode == 0 else X264)


def render(edl: dict, src: Path, out: Path) -> Path:
    """Two-pass loudnorm, then one NVENC encode with layout, captions and hook."""
    work = out.parent
    work.mkdir(parents=True, exist_ok=True)
    (work / "edl.ass").write_text(build_ass(edl), encoding="utf-8")
    a, b = edl["in_s"], edl["out_s"]
    if edl.get("follow"):
        (work / FOLLOW_CMD).write_text(
            follow.sendcmd(edl["follow"], b - a, edl.get("fps", 60)), encoding="utf-8")
    m = measure_loudness(src, a, b)
    audio = (f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
             f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
             f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
             f"aresample=48000")
    cmd = ["ffmpeg", "-hide_banner", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
           "-i", str(src.resolve()), "-filter_complex", filter_graph(edl),
           "-map", "[v]", "-map", "0:a", "-af", audio, *video_encoder(),
           "-r", str(edl.get("fps", 60)), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", out.name]
    run = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=1800)
    if run.returncode != 0:
        raise RenderError(f"ffmpeg render failed: {run.stderr.strip()[-400:]}")
    return out
