"""Stage 2b, Holen: download only the most-viewed stretches, never a whole stream.

Finished Twitch VODs: the strongest intervals from `intervals.plan`, each
downloaded as one section with `yt-dlp --download-sections` in source quality.
A VOD that is still being recorded (its streamer is live with a stream that
began when the VOD did) is planned only up to 30 min before the live edge:
GTA6 launch streams run for days (KaiCenat's first one passed 30 h, 2026-11-19),
and their recorded part downloads like a finished VOD (checked live: 80 s from
hour 3 of that stream, 1080p60, full length). The VOD stays unfinished, so the
next run plans what was recorded since.

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
import signal
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
LIVE_SETTLE = timedelta(minutes=30)  # a recording VOD is planned up to this far behind live
MAX_ATTEMPTS = 3
DOWNLOAD_TIMEOUT_S = 600            # a 120 s section takes about 10 s; 2 h is not progress
DURATION_SLACK_S = 3.0              # section cuts snap to keyframes (~2 s apart on Twitch)
SEGMENT_LEAD_S = 10.5               # one Twitch HLS segment (10 s) of lead-in, end exact
# MPEG-TS timestamps are 33 bits at 90 kHz: they wrap after 2**33 / 90000 = 95443.7 s
# (26:30:43 h). Past that, ffmpeg opens the right segment but reads wrapped timestamps,
# waits for the target time that never comes and reads to the VOD's end (KaiCenat's 47.6 h
# VOD, 2026-11-20: 0 bytes at 26:49 h). 5 min margin for the stream's first timestamp
# (62 s there).
SEEKABLE_UNTIL_S = 2**33 / 90000 - 300


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


def kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    else:
        os.killpg(pid, signal.SIGKILL)


def run_killing_tree(args, *, timeout: float, **kw) -> subprocess.CompletedProcess:
    """subprocess.run, except that a timeout kills the whole process tree.

    subprocess.run kills only yt-dlp: its ffmpeg child lives on, holds the output pipes
    open, and run() waits on them for good (2026-11-20: the fetch stood 28 min on a
    0-byte section after the 600 s timeout had fired).
    """
    kw.pop("capture_output", None)
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=os.name != "nt", **kw) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            proc.communicate()  # the pipes close once the whole tree is gone
            raise
    return subprocess.CompletedProcess(args, proc.returncode, out, err)


class YtDlp:
    """yt-dlp from the engine's own environment, retried on transient failures."""

    def __init__(self, *, attempts: int = MAX_ATTEMPTS, sleep: Callable[[float], None] = time.sleep,
                 run: Callable[..., subprocess.CompletedProcess] | None = None) -> None:
        self.attempts, self.sleep, self.run = attempts, sleep, run or run_killing_tree

    def section(self, url: str, start: float, end: float, stem: Path) -> Path:
        # A VOD still being recorded is a live (EVENT) playlist: ffmpeg would open it at the
        # live edge, take that segment's time as zero and wait for a start it never reaches
        # (KaiCenat hour 8:35 of a 30 h stream hung with 0 bytes, 2026-11-19). Starting at
        # segment 0 seeks like a finished VOD (13 s; the clip sat where planned, corr 0.94).
        return self._download(url, stem, ["-f", "b", "--download-sections",
                                          f"*{start:.1f}-{end:.1f}",
                                          "--downloader-args", "ffmpeg_i:-live_start_index 0"])

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
            try:
                out = self.run(args, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=DOWNLOAD_TIMEOUT_S)
            except subprocess.TimeoutExpired:  # a hung download fails its section, not the run
                out = subprocess.CompletedProcess(args, 1, "",
                                                  f"timed out after {DOWNLOAD_TIMEOUT_S} s")
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
    recording: bool = False                      # VOD still being recorded: never "fetched"


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


def _held_by_clips(con: sqlite3.Connection, video_id: str) -> list[tuple[float, float]]:
    """Where on this VOD the clips sit that a fetched clip-path section already holds.

    A streamer without public VODs gets moments from clips alone (kind 'clip'). Once the
    VOD turns public, watch gives those clips a vod_offset and the VOD plan picked the
    same moments again (caseoh_ 2026-11-20: m40 = m9, m47 = m15, m53 = m18).
    """
    return [(r["vod_offset"] - r["duration_s"], float(r["vod_offset"])) for r in con.execute(
        "SELECT c.vod_offset, c.duration_s FROM sections s "
        "JOIN crowd_clips c ON c.clip_id = s.top_clip_id "
        "WHERE s.kind = 'clip' AND s.status = 'fetched' AND c.video_id = ? "
        "AND c.vod_offset IS NOT NULL", (video_id,))]


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
             max_len: float, until_s: float | None = None) -> SourceResult:
    """`until_s`: a recording VOD is planned only up to here (clips ending later wait)."""
    res = SourceResult(vod["streamer"], vod["ext_id"], recording=until_s is not None)
    clips = con.execute(
        "SELECT clip_id, vod_offset, duration_s, view_count FROM crowd_clips "
        "WHERE video_id = ? AND vod_offset IS NOT NULL AND game_id = ?",
        (vod["ext_id"], config.GTA6_GAME_ID)).fetchall()
    if until_s is not None:  # vod_offset is the clip's END (measured 2026-11-19)
        clips = [c for c in clips if c["vod_offset"] + pad <= until_s]
        res.note = (f"still live, planned up to {int(until_s // 3600)}:"
                    f"{int(until_s % 3600 // 60):02d} h of the recording")
    beyond = [c for c in clips if c["vod_offset"] + pad > SEEKABLE_UNTIL_S]
    if beyond:
        clips = [c for c in clips if c["vod_offset"] + pad <= SEEKABLE_UNTIL_S]
        res.note = ", ".join(filter(None, [
            res.note, f"{len(beyond)} clips past 26:25 h left out (the stream clock wraps "
                      f"at 26:30 h, ffmpeg's seek never arrives)"]))
    spans = [intervals.clip_span(c["clip_id"], c["vod_offset"], c["duration_s"], c["view_count"])
             for c in clips]
    muted = json.loads(vod["muted_segments"]) if vod["muted_segments"] else []
    vod_len = vod["duration_s"] if until_s is None else min(until_s, vod["duration_s"] or until_s)
    p = intervals.plan(spans, muted=muted, vod_len=vod_len, top=top,
                       min_views=min_views, pad=pad, max_len=max_len)
    res.muted_skipped = len(p.muted)
    if not p.chosen:
        res.note = ", ".join(filter(None, [
            res.note, f"no interval with {min_views}+ views ({len(clips)} GTA VI clips)"]))
    held = _held_by_clips(con, vod["ext_id"])
    dupes = 0
    for rank, iv in enumerate(p.chosen, start=1):
        if _covered(con, vod["ext_id"], iv):
            continue
        if any(a <= iv.end and iv.start <= b for a, b in held):
            dupes += 1
            continue
        res.chosen.add(iv.top_clip_id)
        _upsert(con, {"streamer": vod["streamer"], "kind": "vod", "video_id": vod["ext_id"],
                      "top_clip_id": iv.top_clip_id, "start_s": iv.start, "end_s": iv.end,
                      "win_start_s": iv.win_start, "win_end_s": iv.win_end, "views": iv.views,
                      "clips": iv.clips, "rank": rank})
    if dupes:
        res.note = ", ".join(filter(None, [
            res.note, f"{dupes} already fetched as clips before the VOD was public"]))
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
        lead = info.duration - want
        win_start = s["win_start_s"]
        if s["kind"] == "vod" and DURATION_SLACK_S < lead <= SEGMENT_LEAD_S:
            # From a live playlist ffmpeg starts at the HLS segment holding the start: the
            # end is exact, the extra seconds come first (KaiCenat 2026-11-19: a 126.9 s
            # file for 120 s, its clip 7.7 s later than planned). The window moves back.
            win_start = s["win_end_s"] - info.duration
        elif abs(lead) > DURATION_SLACK_S:
            raise FetchError(f"{path.name}: {info.duration:.1f} s, asked for {want:.1f} s")
        with con:
            con.execute(
                "UPDATE sections SET status = 'fetched', file = ?, file_duration_s = ?, "
                "width = ?, height = ?, win_start_s = ?, attempts = attempts + 1, "
                "last_error = NULL, updated_at = ? WHERE id = ?",
                (path.relative_to(data_dir).as_posix(), info.duration, info.width, info.height,
                 win_start, db.utcnow(), section_id))
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
            until_s = None
            if is_recording(vod, live):
                until_s = (now - _ts(vod["created_at"]) - LIVE_SETTLE).total_seconds()
            results.append(plan_vod(con, vod, top=top, min_views=min_views, pad=pad,
                                    max_len=max_len, until_s=until_s))
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
        for s in con.execute(f"SELECT * FROM sections WHERE {where} ORDER BY views DESC",
                             params).fetchall():
            if s["status"] != "fetched" and s["top_clip_id"] not in res.chosen:
                continue  # planned by an earlier run, no longer among the strongest
            if not dry_run and s["status"] != "fetched" and s["attempts"] < MAX_ATTEMPTS:
                s = download(con, s["id"], downloader=downloader, probe=probe, data_dir=data_dir)
            res.sections.append(dict(s))
        if res.sections and all(s["status"] == "fetched" for s in res.sections) \
                and res.source != "clips" and not res.recording:
            with con:
                con.execute("UPDATE videos SET status = 'fetched', updated_at = ? "
                            "WHERE source = 'twitch' AND ext_id = ?", (db.utcnow(), res.source))
    return results
