"""Stage 1, Beobachten: new VODs, uploads and viewer clips of the register.

Every watch re-reads the whole lookback window. Clip view counts keep growing
after a clip is made and Twitch fills vod_offset in late, so re-reading is
what keeps the ranking in p1.2 current; the upserts make it idempotent.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

from . import db, youtube
from .twitch import Twitch, TwitchError, parse_duration


@dataclass
class WatchResult:
    login: str
    vods: int = 0
    new_vods: int = 0
    clips: int = 0
    new_clips: int = 0
    uploads: int = 0
    new_uploads: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _resolve_twitch_id(con: sqlite3.Connection, twitch: Twitch, login: str) -> str | None:
    row = con.execute("SELECT twitch_id FROM streamers WHERE login = ?", (login,)).fetchone()
    if row and row["twitch_id"]:
        return row["twitch_id"]
    users = twitch.users(logins=[login])
    if not users:
        return None
    with con:
        con.execute("UPDATE streamers SET twitch_id = ? WHERE login = ?", (users[0]["id"], login))
    return users[0]["id"]


def clip_row(login: str, clip: dict) -> dict:
    return {
        "clip_id": clip["id"],
        "streamer": login,
        "video_id": clip.get("video_id") or None,
        "vod_offset": clip.get("vod_offset"),
        "duration_s": float(clip["duration"]),
        "view_count": int(clip["view_count"]),
        "game_id": clip.get("game_id") or None,
        "language": clip.get("language") or None,
        "title": clip.get("title"),
        "creator_id": clip.get("creator_id"),
        "url": clip.get("url"),
        "created_at": clip["created_at"],
    }


def vod_ends_after(video: dict, since: datetime) -> bool:
    """A VOD counts when any part of it lies in the window, not only its start:
    a 35-hour marathon begun the day before the window still carries clips
    inside it (KaiCenat, 2026-11-09, found in the 2026-11-17 live run)."""
    start = _parse_time(video["created_at"])
    length = parse_duration(video.get("duration")) or 0
    return start + timedelta(seconds=length) >= since


def watch_streamer(con: sqlite3.Connection, twitch: Twitch, http: httpx.Client, login: str,
                   *, since: datetime, until: datetime, max_pages: int,
                   chunk_hours: float = 6) -> WatchResult:
    res = WatchResult(login)
    streamer = con.execute("SELECT * FROM streamers WHERE login = ?", (login,)).fetchone()

    try:
        broadcaster_id = _resolve_twitch_id(con, twitch, login)
        if broadcaster_id is None:
            res.errors.append(f"Twitch login '{login}' not found")
        else:
            for video in twitch.archive_videos(broadcaster_id):
                if not vod_ends_after(video, since):
                    continue
                res.vods += 1
                res.new_vods += db.upsert_video(con, {
                    "source": "twitch",
                    "ext_id": video["id"],
                    "streamer": login,
                    "title": video.get("title"),
                    "url": video.get("url"),
                    "created_at": video["created_at"],
                    "duration_s": parse_duration(video.get("duration")),
                    "view_count": video.get("view_count"),
                    "muted_segments": json.dumps(video["muted_segments"])
                    if video.get("muted_segments") else None,
                })
            clips = twitch.clips_windowed(broadcaster_id=broadcaster_id, start=since, end=until,
                                          chunk_hours=chunk_hours, max_pages=max_pages)
            for clip in clips:
                res.clips += 1
                res.new_clips += db.upsert_clip(con, clip_row(login, clip))
    except TwitchError as exc:
        res.errors.append(f"Twitch: {exc}")

    channel = streamer["youtube_channel_id"] if streamer else None
    if channel:
        try:
            for upload in youtube.channel_uploads(http, channel):
                if not upload["published"] or _parse_time(upload["published"]) < since:
                    continue
                res.uploads += 1
                res.new_uploads += db.upsert_video(con, {
                    "source": "youtube",
                    "ext_id": upload["video_id"],
                    "streamer": login,
                    "title": upload["title"],
                    "url": upload["url"],
                    "created_at": upload["published"],
                    "view_count": upload["view_count"],
                })
        except youtube.YouTubeError as exc:
            res.errors.append(f"YouTube: {exc}")

    if not res.errors:
        with con:
            con.execute("UPDATE streamers SET last_watched_at = ? WHERE login = ?",
                        (db.iso(until), login))
    return res


def watch(con: sqlite3.Connection, twitch: Twitch, http: httpx.Client, *, days: float,
          max_pages: int, chunk_hours: float = 6, only: list[str] | None = None,
          now: datetime | None = None) -> list[WatchResult]:
    until = now or datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    rows = con.execute(
        "SELECT login FROM streamers WHERE active = 1 ORDER BY priority, login").fetchall()
    logins = [r["login"] for r in rows if not only or r["login"] in only]
    return [watch_streamer(con, twitch, http, login, since=since, until=until,
                           max_pages=max_pages, chunk_hours=chunk_hours) for login in logins]
