"""Stage 3, Analysieren (minimal): transcript, cut at sentence ends, review packages.

The laptop computes, Claude Code judges (owner, 2026-11-17: no API LLM cost).
For every fetched section this stage

1. transcribes it locally with faster-whisper (word timestamps, GPU),
2. cuts one F1 moment (15 to 60 s) around the most-viewed clip, moved out to
   sentence ends so no sentence is cut off,
3. writes a review package to data/review/{moment}/: transcript, 6 to 8
   stills, views, streamer. Claude Code reads it and answers with `judge`.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import db

MODEL = "large-v3"
F1_MIN_S, F1_MAX_S = 15.0, 60.0
SENTENCE_END = (".", "?", "!")
STILLS = 8


class AnalyzeError(Exception):
    pass


# --- transcription -------------------------------------------------------------

def _add_cuda_dll_dirs() -> None:
    """ctranslate2 on Windows finds cuBLAS / cuDNN only on the DLL search path;
    the nvidia-* wheels put them under site-packages/nvidia/*/bin."""
    if sys.platform != "win32":
        return
    for base in map(Path, sys.path):
        nvidia = base / "nvidia"
        if nvidia.is_dir():
            for bin_dir in nvidia.glob("*/bin"):
                os.add_dll_directory(str(bin_dir))
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def prefer_ipv4() -> None:
    """Resolve hosts to IPv4 for this process. Over IPv6 the laptop's line
    reset ~40 % of first requests on 2026-11-19, the Hugging Face model
    download included (fetch.py runs yt-dlp with --force-ipv4 for the same
    reason). Falls back to the normal lookup for IPv6-only hosts."""
    import socket

    if getattr(socket.getaddrinfo, "ipv4_first", False):
        return
    original = socket.getaddrinfo

    def ipv4_first(host, port, family=0, *args, **kwargs):
        if family in (0, socket.AF_UNSPEC):
            try:
                return original(host, port, socket.AF_INET, *args, **kwargs)
            except socket.gaierror:
                pass
        return original(host, port, family, *args, **kwargs)

    ipv4_first.ipv4_first = True  # type: ignore[attr-defined]
    socket.getaddrinfo = ipv4_first


@dataclass
class Transcript:
    words: list[dict]      # {"w", "s", "e", "p"}: word, start, end, probability (file time)
    segments: list[dict]   # {"s", "e", "t"}
    language: str
    audio_s: float
    run_s: float
    model: str


def load_audio(path: Path, rate: int = 16000):
    """Mono float32 samples via ffmpeg. faster-whisper's own decoder (PyAV)
    broke on 2026-11-19: av.open() no longer takes metadata_errors."""
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                          "-f", "s16le", "-"], capture_output=True, check=True, timeout=600).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def whisper_transcriber(model_name: str = MODEL, device: str = "cuda",
                        compute_type: str = "int8_float16") -> Callable[[Path, str], Transcript]:
    _add_cuda_dll_dirs()
    prefer_ipv4()
    from faster_whisper import WhisperModel  # heavy import, only when transcribing

    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(path: Path, language: str) -> Transcript:
        t0 = time.monotonic()
        segments, info = model.transcribe(load_audio(path), language=language,
                                          word_timestamps=True, vad_filter=True, beam_size=5)
        words, segs = [], []
        for seg in segments:
            segs.append({"s": round(seg.start, 2), "e": round(seg.end, 2), "t": seg.text.strip()})
            for w in seg.words or []:
                words.append({"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2),
                              "p": round(w.probability, 3)})
        return Transcript(words, segs, info.language, round(info.duration, 1),
                          round(time.monotonic() - t0, 1), model_name)

    return transcribe


# --- cutting -------------------------------------------------------------------

def cut_f1(words: list[dict], core: tuple[float, float], length: float, *,
           min_s: float = F1_MIN_S, max_s: float = F1_MAX_S) -> tuple[float, float]:
    """In and out point for one F1 moment around `core` (file seconds).

    Start: the first word after the last sentence end before the core.
    End: the first sentence end at or after the core's end. Then the moment is
    stretched to min_s (whole sentences after it) or cut back to max_s (at a
    sentence end inside the limit). Without speech the core is used as is.
    """
    lo, hi = max(0.0, core[0]), min(length, core[1])
    if not words:
        return _fit(lo, hi, length, min_s, max_s)
    ends = [i for i, w in enumerate(words) if w["w"].endswith(SENTENCE_END)]

    starts = [0] + [i + 1 for i in ends if i + 1 < len(words)]
    # the sentence the core starts in; if that one ended before the core, the next one
    first = max((i for i in starts if words[i]["s"] <= lo), default=0)
    its_end = next((i for i in ends if i >= first), len(words) - 1)
    if words[its_end]["e"] < lo:
        first = next((i for i in starts if i > first and words[i]["s"] < hi), first)
    a = min(lo, words[first]["s"] - 0.15)

    after = [i for i in ends if words[i]["e"] >= hi - 0.5]
    b = max(hi, words[after[0]]["e"] + 0.3) if after else hi

    if b - a < min_s:  # take whole following sentences until long enough
        for i in ends:
            if words[i]["e"] + 0.3 - a >= min_s:
                b = max(b, words[i]["e"] + 0.3)
                break
    if b - a > max_s:  # cut back to the last sentence end that fits
        fits = [words[i]["e"] + 0.3 for i in ends if a + min_s <= words[i]["e"] + 0.3 <= a + max_s]
        b = fits[-1] if fits else a + max_s
    return _fit(a, b, length, min_s, max_s)


def _fit(a: float, b: float, length: float, min_s: float, max_s: float) -> tuple[float, float]:
    a, b = max(0.0, a), min(length, b)
    if b - a < min_s:
        need = min_s - (b - a)
        a = max(0.0, a - need / 2)
        b = min(length, a + min_s)
    if b - a > max_s:
        b = a + max_s
    return round(a, 2), round(b, 2)


# --- review packages -----------------------------------------------------------

def hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def extract_stills(video: Path, out_dir: Path, a: float, b: float, n: int = STILLS) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(n):
        t = a + (b - a) * (i + 0.5) / n
        path = out_dir / f"{i + 1:02d}_{t:05.1f}s.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "4", str(path)],
                       check=True, timeout=60)
        paths.append(path)
    return paths


def write_package(pkg: Path, *, moment: dict, section: sqlite3.Row, clip: sqlite3.Row | None,
                  transcript: Transcript, stills: list[Path]) -> None:
    a, b = moment["in_s"], moment["out_s"]
    lines = [f"[{w['s']:6.2f}] {w['w']}" for w in transcript.words if a - 1 <= w["s"] <= b + 1]
    (pkg / "transcript.txt").write_text(
        " ".join(w["w"] for w in transcript.words if a <= w["s"] <= b) + "\n\n"
        + "\n".join(lines) + "\n", encoding="utf-8")
    meta = {
        "moment": moment["id"], "streamer": section["streamer"], "kind": section["kind"],
        "video_id": section["video_id"], "views": section["views"], "clips": section["clips"],
        "top_clip": {"id": section["top_clip_id"], "title": clip["title"] if clip else None,
                     "url": clip["url"] if clip else None,
                     "views": clip["view_count"] if clip else None},
        "file": section["file"], "in_s": a, "out_s": b, "duration_s": round(b - a, 2),
        "vod_time": (f"{hms(section['win_start_s'] + a)}-{hms(section['win_start_s'] + b)}"
                     if section["kind"] == "vod" else None),
        "stills": [p.name for p in stills],
        "answer_with": f"uv run clipengine judge {moment['id']} --file review.json",
    }
    (pkg / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                   encoding="utf-8")


def store_transcript(con: sqlite3.Connection, section_id: int, t: Transcript) -> None:
    with con:
        con.execute(
            "INSERT OR REPLACE INTO transcripts (section_id, model, language, words, segments, "
            "audio_s, run_s, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (section_id, t.model, t.language, json.dumps(t.words), json.dumps(t.segments),
             t.audio_s, t.run_s, db.utcnow()))


def load_transcript(con: sqlite3.Connection, section_id: int) -> Transcript | None:
    r = con.execute("SELECT * FROM transcripts WHERE section_id = ?", (section_id,)).fetchone()
    if not r:
        return None
    return Transcript(json.loads(r["words"]), json.loads(r["segments"]), r["language"],
                      r["audio_s"], r["run_s"], r["model"])


def core_of(con: sqlite3.Connection, s: sqlite3.Row) -> tuple[float, float]:
    """The most-viewed clip's stretch in section-file seconds."""
    if s["kind"] == "clip":
        return 0.0, float(s["file_duration_s"])
    c = con.execute("SELECT vod_offset, duration_s FROM crowd_clips WHERE clip_id = ?",
                    (s["top_clip_id"],)).fetchone()
    end = float(c["vod_offset"]) - s["win_start_s"]  # vod_offset is the clip END
    return max(0.0, end - float(c["duration_s"])), end


@dataclass
class AnalyzeResult:
    moment_id: int
    section: sqlite3.Row
    in_s: float
    out_s: float
    transcript: Transcript
    package: Path


def analyze(con: sqlite3.Connection, *, data_dir: Path,
            transcriber: Callable[[], Callable[[Path, str], Transcript]],
            stills: Callable[[Path, Path, float, float], list[Path]] = extract_stills,
            section_ids: list[int] | None = None, redo: bool = False) -> list[AnalyzeResult]:
    """Transcribe, cut and package every fetched section without a moment.

    `transcriber` is a factory, so the Whisper model loads only when a section
    actually needs transcribing.
    """
    query = ("SELECT s.* FROM sections s LEFT JOIN moments m ON m.section_id = s.id "
             "WHERE s.status = 'fetched'")
    params: list = []
    if section_ids:
        query += f" AND s.id IN ({','.join('?' * len(section_ids))})"
        params += section_ids
    elif not redo:
        query += " AND m.id IS NULL"
    rows = con.execute(query + " ORDER BY s.views DESC", params).fetchall()

    model = None
    out: list[AnalyzeResult] = []
    for s in rows:
        t = load_transcript(con, s["id"])  # --redo re-cuts; Whisper runs once per section
        if t is None:
            model = model or transcriber()
            lang = con.execute("SELECT language FROM streamers WHERE login = ?",
                               (s["streamer"],)).fetchone()
            t = model(data_dir / s["file"], lang["language"] if lang else "en")
            store_transcript(con, s["id"], t)
        a, b = cut_f1(t.words, core_of(con, s), float(s["file_duration_s"]))
        now = db.utcnow()
        with con:
            con.execute(
                "INSERT INTO moments (section_id, in_s, out_s, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(section_id) DO UPDATE SET "
                "in_s = excluded.in_s, out_s = excluded.out_s, updated_at = excluded.updated_at",
                (s["id"], a, b, now, now))
        mid = con.execute("SELECT id FROM moments WHERE section_id = ?",
                          (s["id"],)).fetchone()["id"]
        pkg = data_dir / "review" / str(mid)
        pkg.mkdir(parents=True, exist_ok=True)
        for old in pkg.glob("*.jpg"):  # a rebuilt package must not mix in stale stills
            old.unlink()
        shots = stills(data_dir / s["file"], pkg, a, b)
        clip = con.execute("SELECT * FROM crowd_clips WHERE clip_id = ?",
                           (s["top_clip_id"],)).fetchone()
        write_package(pkg, moment={"id": mid, "in_s": a, "out_s": b}, section=s, clip=clip,
                      transcript=t, stills=shots)
        with con:
            con.execute("UPDATE moments SET package = ? WHERE id = ?",
                        (pkg.relative_to(data_dir).as_posix(), mid))
        out.append(AnalyzeResult(mid, s, a, b, t, pkg))
    return out


# --- judgment (written by Claude Code after reading a package) -------------------

CATEGORIES = ("funny", "chaos", "skill", "discovery", "fail", "rage", "story")


def judge(con: sqlite3.Connection, moment_id: int, answer: dict) -> sqlite3.Row:
    """Store Claude Code's verdict on one review package; refuse incomplete ones."""
    m = con.execute("SELECT m.*, s.streamer, s.file_duration_s FROM moments m "
                    "JOIN sections s ON s.id = m.section_id WHERE m.id = ?",
                    (moment_id,)).fetchone()
    if m is None:
        raise AnalyzeError(f"no moment {moment_id}")
    verdict = answer.get("verdict")
    if verdict not in ("keep", "reject"):
        raise AnalyzeError("verdict must be 'keep' or 'reject'")
    adult = answer.get("adult", "none")
    if adult not in ("none", "defuse", "reject"):
        raise AnalyzeError("adult must be none, defuse or reject")
    hooks = answer.get("hooks") or []
    title = (answer.get("title") or "").strip()
    in_s = float(answer.get("in_s", m["in_s"]))
    out_s = float(answer.get("out_s", m["out_s"]))
    if verdict == "keep":
        if answer.get("spoiler") is not False or answer.get("cutscene") is not False:
            raise AnalyzeError("keep needs spoiler: false and cutscene: false")
        if adult == "reject":
            raise AnalyzeError("adult 'reject' cannot be kept")
        if answer.get("category") not in CATEGORIES:
            raise AnalyzeError(f"category must be one of {', '.join(CATEGORIES)}")
        if not 2 <= len(hooks) <= 3:
            raise AnalyzeError("keep needs 2 to 3 hooks")
        name = con.execute("SELECT display_name FROM streamers WHERE login = ?",
                           (m["streamer"],)).fetchone()["display_name"]
        if name.lower() not in title.lower():  # channel promise: every title names the streamer
            raise AnalyzeError(f"title must name the streamer ({name})")
        if not (0 <= in_s < out_s <= m["file_duration_s"] + 0.05
                and F1_MIN_S <= out_s - in_s <= F1_MAX_S):
            raise AnalyzeError(f"cut {in_s}-{out_s} must lie in the file and last "
                               f"{F1_MIN_S:.0f} to {F1_MAX_S:.0f} s")
    with con:
        con.execute(
            "UPDATE moments SET status = ?, spoiler = ?, cutscene = ?, adult = ?, category = ?, "
            "hooks = ?, title = ?, notes = ?, in_s = ?, out_s = ?, reviewed_at = ?, "
            "updated_at = ? WHERE id = ?",
            (verdict, int(bool(answer.get("spoiler"))), int(bool(answer.get("cutscene"))), adult,
             answer.get("category"), json.dumps(hooks, ensure_ascii=False), title or None,
             answer.get("notes"), in_s, out_s, db.utcnow(), db.utcnow(), moment_id))
    return con.execute("SELECT * FROM moments WHERE id = ?", (moment_id,)).fetchone()
