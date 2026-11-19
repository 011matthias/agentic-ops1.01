"""Stage 2b, Holen: download only the most-viewed stretches, never a whole stream.

Finished Twitch VODs: the strongest intervals from `intervals.plan`, each
downloaded as one section with `yt-dlp --download-sections` in source quality.
A VOD that is still being recorded (its streamer is live with a stream that
began when the VOD did) is skipped.

Streamers without public VODs (caseoh_, IShowSpeed): their clips carry no
vod_offset, so clips made within 90 s of each other count as one moment and
the most-viewed clip of each moment is downloaded itself.

Checked live 2026-11-19 with yt-dlp 2026.10.26: a 44 s section from the 23rd
hour of a 23 h VOD came down in about 7 s at 1080p60, and clips download as
well. Over IPv6 the laptop's line resets about 40 % of first requests
(WinError 10054, against Twitch and Hugging Face alike), over IPv4 none in 15
tries, so yt-dlp runs with --force-ipv4 and every download is still retried.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol

from . import config, db, intervals
from .twitch import Twitch

LIVE_MATCH = timedelta(minutes=15)  # live stream start vs VOD created_at
MAX_ATTEMPTS = 3
DURATION_SLACK_S = 3.0              # section cuts snap to keyframes (~2 s apart on Twitch)


class FetchError(Exception):
    pass


@dataclass(frozen=True)
class Probe:
    duration: float
    width: int | None
    height: int | None
    has_video: bool
    has_audio: bool


def ffprobe(path: Path) -> Probe:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise FetchError(f"ffprobe failed: {out.stderr.strip()[:200]}")
    info = json.loads(out.stdout or "{}")
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    return Probe(duration=float(info.get("format", {}).get("duration") or 0),
                 width=video.get("width"), height=video.get("height"),
                 has_video=bool(video),
                 has_audio=any(s.get("codec_type") == "audio" for s in streams))


class Downloader(Protocol):
    def section(self, url: str, start: float, end: float, stem: Path) -> Path: ...
    def clip(self, url: str, stem: Path) -> Path: ...


class YtDlp:
    """yt-dlp from the engine's own environment, retried on transient failures."""

    def __init__(self, *, attempts: int = MAX_ATTEMPTS, sleep: Callable[[float], None] = time.sleep,
                 run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self.attempts, self.sleep, self.run = attempts, sleep, run

    def section(self, url: str, start: float, end: float, stem: Path) -> Path:
        return self._download(url, stem, ["-f", "b", "--download-sections",
                                          f"*{start:.1f}-{end:.1f}"])

    def clip(self, url: str, stem: Path) -> Path:
        # Clips also come as Twitch's own auto-cropped "portrait-*" renditions.
        return self._download(url, stem, ["-f", "b[format_id!^=portrait]/b"])

    def _download(self, url: str, stem: Path, extra: list[str]) -> Path:
        stem.parent.mkdir(parents=True, exist_ok=True)
        # --force-ipv4: over IPv6 the laptop's line reset ~40 % of first requests
        # (WinError 10054); over IPv4 0 of 15 (2026-11-19).
        args = [sys.executable, "-m", "yt_dlp", "--force-ipv4", "--no-warnings", "--no-progress",
                "--retries", "5", "--fragment-retries", "5", "--force-overwrites",
                "--no-simulate", "--print", "after_move:filepath",
                *extra, "-o", f"{stem}.%(ext)s", url]
        last = ""
        for attempt in range(1, self.attempts + 1):
            out = self.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800)
            path = (out.stdout or "").strip().splitlines()[-1:] if out.returncode == 0 else []
            if path and Path(path[0]).exists():
                return Path(path[0])
            last = (out.stderr or out.stdout or "").strip().splitlines()[-1:] or ["no output"]
            last = last[0][:300]
            if attempt < self.attempts:
                self.sleep(5.0 * attempt)  # resets came in bursts; 3 s and 6 s were too short
        raise FetchError(f"yt-dlp gave up after {self.attempts} attempts: {last}")


def min_free_gb() -> float:
    return float(os.environ.get("CLIPENGINE_MIN_FREE_GB", "50"))


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / 1e9


@dataclass
class SourceResult:
    streamer: str
    source: str                      # VOD id, or "clips" for clip-only streamers
    note: str = ""
    sections: list[dict] = field(default_factory=list)
    muted_skipped: int = 0
    chosen: set[str] = field(default_factory=set)  # top_clip_ids picked by this run's plan
    skipped: bool = False                         # e.g. the VOD is still being recorded


def _ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def is_recording(vod: sqlite3.Row, live: dict[str, str]) -> bool:
    started = live.get(vod["streamer"])
    return bool(started and vod["created_at"]
                and abs(_ts(started) - _ts(vod["created_at"])) <= LIVE_MATCH)


def _covered(con: sqlite3.Connection, video_id: str, iv: intervals.Interval) -> bool:
    """A fetched section of the same VOD already holds this moment's top clip."""
    return con.execute(
        "SELECT 1 FROM sections WHERE kind = 'vod' AND video_id = ? AND status = 'fetched' "
        "AND win_start_s <= ? AND win_end_s >= ?", (video_id, iv.top_start, iv.top_end)
    ).fetchone() is not None


def _upsert(con: sqlite3.Connection, row: dict) -> int:
    now = db.utcnow()
    with con:
        con.execute(
            """
            INSERT INTO sections (streamer, kind, video_id, top_clip_id, start_s, end_s,
                                  win_start_s, win_end_s, views, clips, rank, created_at,
                                  updated_at)
            VALUES (:streamer, :kind, :video_id, :top_clip_id, :start_s, :end_s, :win_start_s,
                    :win_end_s, :views, :clips, :rank, :now, :now)
            ON CONFLICT(kind, top_clip_id) DO UPDATE SET
                start_s = excluded.start_s, end_s = excluded.end_s,
                win_start_s = CASE WHEN sections.status = 'fetched' THEN sections.win_start_s
                                   ELSE excluded.win_start_s END,
                win_end_s = CASE WHEN sections.status = 'fetched' THEN sections.win_end_s
                                 ELSE excluded.win_end_s END,
                views = excluded.views, clips = excluded.clips, rank = excluded.rank,
                updated_at = excluded.updated_at
            """, {**row, "now": now})
    return con.execute("SELECT id FROM sections WHERE kind = ? AND top_clip_id = ?",
                       (row["kind"], row["top_clip_id"])).fetchone()["id"]


def plan_vod(con: sqlite3.Connection, vod: sqlite3.Row, *, top: int, min_views: int, pad: float,
             max_len: float) -> SourceResult:
    res = SourceResult(vod["streamer"], vod["ext_id"])
    clips = con.execute(
        "SELECT clip_id, vod_offset, duration_s, view_count FROM crowd_clips "
        "WHERE video_id = ? AND vod_offset IS NOT NULL AND game_id = ?",
        (vod["ext_id"], config.GTA6_GAME_ID)).fetchall()
    spans = [intervals.clip_span(c["clip_id"], c["vod_offset"], c["duration_s"], c["view_count"])
             for c in clips]
    muted = json.loads(vod["muted_segments"]) if vod["muted_segments"] else []
    p = intervals.plan(spans, muted=muted, vod_len=vod["duration_s"], top=top,
                       min_views=min_views, pad=pad, max_len=max_len)
    res.muted_skipped = len(p.muted)
    if not p.chosen:
        res.note = f"no interval with {min_views}+ views ({len(clips)} GTA VI clips)"
    for rank, iv in enumerate(p.chosen, start=1):
        if _covered(con, vod["ext_id"], iv):
            continue
        res.chosen.add(iv.top_clip_id)
        _upsert(con, {"streamer": vod["streamer"], "kind": "vod", "video_id": vod["ext_id"],
                      "top_clip_id": iv.top_clip_id, "start_s": iv.start, "end_s": iv.end,
                      "win_start_s": iv.win_start, "win_end_s": iv.win_end, "views": iv.views,
                      "clips": iv.clips, "rank": rank})
    return res


def plan_clips(con: sqlite3.Connection, login: str, *, since: datetime, top: int,
               min_views: int) -> SourceResult | None:
    """Clips with no VOD behind them: each moment's most-viewed clip is the section."""
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM crowd_clips WHERE streamer = ? AND video_id IS NULL AND game_id = ? "
        "AND created_at >= ?", (login, config.GTA6_GAME_ID, db.iso(since)))]
    if not rows:
        return None
    res = SourceResult(login, "clips")
    moments = []
    for group in intervals.group_clips_by_time(rows):
        best = max(group, key=lambda c: c["view_count"])
        moments.append((sum(c["view_count"] for c in group), len(group), best))
    moments.sort(key=lambda m: -m[0])
    picked = [m for m in moments if m[0] >= min_views][:top]
    if not picked:
        res.note = f"no moment with {min_views}+ views ({len(rows)} clips without VOD)"
    for rank, (views, count, best) in enumerate(picked, start=1):
        res.chosen.add(best["clip_id"])
        _upsert(con, {"streamer": login, "kind": "clip", "video_id": None,
                      "top_clip_id": best["clip_id"], "start_s": 0.0,
                      "end_s": best["duration_s"], "win_start_s": 0.0,
                      "win_end_s": best["duration_s"], "views": views, "clips": count,
                      "rank": rank})
    return res


def download(con: sqlite3.Connection, section_id: int, *, downloader: Downloader,
             probe: Callable[[Path], Probe], data_dir: Path) -> sqlite3.Row:
    s = con.execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()
    try:
        if s["kind"] == "vod":
            url = con.execute("SELECT url FROM videos WHERE source = 'twitch' AND ext_id = ?",
                              (s["video_id"],)).fetchone()["url"]
            stem = (data_dir / s["streamer"] / s["video_id"] / "sections"
                    / f"{int(s['win_start_s'])}-{int(s['win_end_s'])}")
            path = downloader.section(url, s["win_start_s"], s["win_end_s"], stem)
        else:
            url = con.execute("SELECT url FROM crowd_clips WHERE clip_id = ?",
                              (s["top_clip_id"],)).fetchone()["url"]
            path = downloader.clip(url, data_dir / s["streamer"] / "clips" / s["top_clip_id"])
        info = probe(path)
        want = s["win_end_s"] - s["win_start_s"]
        if not (info.has_video and info.has_audio):
            raise FetchError(f"{path.name}: missing {'video' if not info.has_video else 'audio'}")
        if abs(info.duration - want) > DURATION_SLACK_S:
            raise FetchError(f"{path.name}: {info.duration:.1f} s, asked for {want:.1f} s")
        with con:
            con.execute(
                "UPDATE sections SET status = 'fetched', file = ?, file_duration_s = ?, "
                "width = ?, height = ?, attempts = attempts + 1, last_error = NULL, "
                "updated_at = ? WHERE id = ?",
                (path.relative_to(data_dir).as_posix(), info.duration, info.width, info.height,
                 db.utcnow(), section_id))
    except FetchError as exc:
        with con:
            con.execute("UPDATE sections SET status = 'failed', attempts = attempts + 1, "
                        "last_error = ?, updated_at = ? WHERE id = ?",
                        (str(exc), db.utcnow(), section_id))
    return con.execute("SELECT * FROM sections WHERE id = ?", (section_id,)).fetchone()


def fetch(con: sqlite3.Connection, twitch: Twitch, *, downloader: Downloader,
          probe: Callable[[Path], Probe] = ffprobe, data_dir: Path | None = None,
          streamers: list[str] | None = None, video_ids: list[str] | None = None,
          days: float = 2, top: int = 5, min_views: int = 50, pad: float = 5,
          max_len: float = 120, dry_run: bool = False,
          now: datetime | None = None) -> list[SourceResult]:
    data_dir = data_dir or config.data_dir()
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    logins = [r["login"] for r in con.execute(
        "SELECT login FROM streamers WHERE active = 1 ORDER BY priority, login")
        if not streamers or r["login"] in streamers]
    live = twitch.live_streams(logins) if logins else {}

    results: list[SourceResult] = []
    for login in logins:
        if video_ids:
            vods = con.execute(
                f"SELECT * FROM videos WHERE source = 'twitch' AND streamer = ? AND ext_id IN "
                f"({','.join('?' * len(video_ids))})", (login, *video_ids)).fetchall()
        else:
            vods = con.execute(
                "SELECT * FROM videos WHERE source = 'twitch' AND streamer = ? AND "
                "datetime(created_at, '+' || COALESCE(duration_s, 0) || ' seconds') "
                ">= datetime(?) ORDER BY created_at", (login, db.iso(since))).fetchall()
        for vod in vods:
            if is_recording(vod, live):
                results.append(SourceResult(login, vod["ext_id"], skipped=True,
                                            note="still live, recording not finished"))
                continue
            results.append(plan_vod(con, vod, top=top, min_views=min_views, pad=pad,
                                    max_len=max_len))
        if not video_ids:
            clip_res = plan_clips(con, login, since=since, top=top, min_views=min_views)
            if clip_res:
                results.append(clip_res)

    if not dry_run:
        free = free_gb(data_dir)
        if free < min_free_gb():
            raise FetchError(f"only {free:.0f} GB free under {data_dir}, downloads need "
                             f"{min_free_gb():.0f} GB")
    for res in results:
        where = ("kind = 'clip' AND streamer = ? AND video_id IS NULL" if res.source == "clips"
                 else "kind = 'vod' AND streamer = ? AND video_id = ?")
        params = (res.streamer,) if res.source == "clips" else (res.streamer, res.source)
        if res.skipped:
            continue
        for s in con.execute(f"SELECT * FROM sections WHERE {where} ORDER BY views DESC",
                             params).fetchall():
            if s["status"] != "fetched" and s["top_clip_id"] not in res.chosen:
                continue  # planned by an earlier run, no longer among the strongest
            if not dry_run and s["status"] != "fetched" and s["attempts"] < MAX_ATTEMPTS:
                s = download(con, s["id"], downloader=downloader, probe=probe, data_dir=data_dir)
            res.sections.append(dict(s))
        if res.sections and all(s["status"] == "fetched" for s in res.sections) \
                and res.source != "clips":
            with con:
                con.execute("UPDATE videos SET status = 'fetched', updated_at = ? "
                            "WHERE source = 'twitch' AND ext_id = ?", (db.utcnow(), res.source))
    return results
