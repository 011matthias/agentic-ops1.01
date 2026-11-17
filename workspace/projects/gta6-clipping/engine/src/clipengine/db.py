"""SQLite state. Schema changes are numbered migrations keyed on user_version,
so later phases (signals, transcripts, moments, renders) add their tables
without touching an existing database.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIGRATIONS: list[str] = [
    # 1: p1.1 watch + discovery
    """
    CREATE TABLE streamers (
        login              TEXT PRIMARY KEY,      -- Twitch login, lowercase
        display_name       TEXT NOT NULL,
        twitch_id          TEXT,                  -- broadcaster_id, resolved on first watch
        youtube_channel_id TEXT,
        language           TEXT NOT NULL,
        layout             TEXT,
        priority           INTEGER NOT NULL DEFAULT 3,
        permission         TEXT NOT NULL DEFAULT 'unknown'
                           CHECK (permission IN ('unknown', 'yes', 'no')),
        active             INTEGER NOT NULL DEFAULT 1,  -- 0 once removed from the register
        last_watched_at    TEXT,
        updated_at         TEXT NOT NULL
    );

    CREATE TABLE videos (
        source         TEXT NOT NULL CHECK (source IN ('twitch', 'youtube')),
        ext_id         TEXT NOT NULL,
        streamer       TEXT NOT NULL REFERENCES streamers(login),
        title          TEXT,
        url            TEXT,
        created_at     TEXT,          -- stream start or publish time, UTC
        duration_s     INTEGER,       -- YouTube: filled by p1.2 from yt-dlp
        view_count     INTEGER,
        muted_segments TEXT,          -- Twitch JSON, NULL when nothing is muted
        status         TEXT NOT NULL DEFAULT 'new',
        attempts       INTEGER NOT NULL DEFAULT 0,
        last_error     TEXT,
        first_seen_at  TEXT NOT NULL,
        updated_at     TEXT NOT NULL,
        PRIMARY KEY (source, ext_id)
    );

    CREATE TABLE crowd_clips (
        clip_id       TEXT PRIMARY KEY,
        streamer      TEXT NOT NULL REFERENCES streamers(login),
        video_id      TEXT,           -- Twitch VOD id; NULL when the VOD is gone
        vod_offset    INTEGER,        -- seconds from VOD start; NULL when the VOD is gone
        duration_s    REAL NOT NULL,
        view_count    INTEGER NOT NULL,
        game_id       TEXT,
        language      TEXT,
        title         TEXT,
        creator_id    TEXT,
        url           TEXT,
        created_at    TEXT NOT NULL,
        status        TEXT NOT NULL DEFAULT 'new',
        first_seen_at TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    );
    CREATE INDEX crowd_clips_by_video ON crowd_clips(video_id);
    CREATE INDEX crowd_clips_by_streamer ON crowd_clips(streamer, created_at);

    CREATE TABLE suggestions (
        login            TEXT PRIMARY KEY,
        twitch_id        TEXT NOT NULL,
        display_name     TEXT NOT NULL,
        window_start     TEXT NOT NULL,
        window_end       TEXT NOT NULL,
        language         TEXT NOT NULL,   -- clip language the ranking used
        views            INTEGER NOT NULL,
        clips            INTEGER NOT NULL,
        clippers         INTEGER NOT NULL, -- distinct viewers who made the clips
        self_clips       INTEGER NOT NULL, -- clips the streamer made of themselves
        top_clip_url     TEXT,
        top_clip_views   INTEGER,
        top_clip_title   TEXT,
        broadcaster_type TEXT,
        followers        INTEGER,
        channel_language TEXT,
        status           TEXT NOT NULL DEFAULT 'open'
                         CHECK (status IN ('open', 'approved', 'rejected')),
        first_seen_at    TEXT NOT NULL,
        updated_at       TEXT NOT NULL
    );

    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """,
]


def utcnow() -> str:
    return iso(datetime.now(timezone.utc))


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    migrate(con)
    return con


def migrate(con: sqlite3.Connection) -> int:
    version = con.execute("PRAGMA user_version").fetchone()[0]
    for number, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        con.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {number};\nCOMMIT;")
    return con.execute("PRAGMA user_version").fetchone()[0]


# --- meta -----------------------------------------------------------------

def meta_get(con: sqlite3.Connection, key: str) -> Any:
    row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None


def meta_set(con: sqlite3.Connection, key: str, value: Any) -> None:
    with con:
        con.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )


# --- upserts ----------------------------------------------------------------
# Each returns True when the row is new. Mutable facts (views, titles, a VOD
# offset Twitch fills in later) are refreshed; pipeline state (status,
# attempts, first_seen_at) is never touched by a re-watch.

def upsert_video(con: sqlite3.Connection, row: dict[str, Any]) -> bool:
    now = utcnow()
    exists = con.execute(
        "SELECT 1 FROM videos WHERE source = ? AND ext_id = ?", (row["source"], row["ext_id"])
    ).fetchone()
    with con:
        con.execute(
            """
            INSERT INTO videos (source, ext_id, streamer, title, url, created_at, duration_s,
                                view_count, muted_segments, first_seen_at, updated_at)
            VALUES (:source, :ext_id, :streamer, :title, :url, :created_at, :duration_s,
                    :view_count, :muted_segments, :now, :now)
            ON CONFLICT(source, ext_id) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                duration_s = COALESCE(excluded.duration_s, videos.duration_s),
                view_count = COALESCE(excluded.view_count, videos.view_count),
                muted_segments = excluded.muted_segments,
                updated_at = excluded.updated_at
            """,
            {**_video_defaults(), **row, "now": now},
        )
    return exists is None


def _video_defaults() -> dict[str, Any]:
    return {"title": None, "url": None, "created_at": None, "duration_s": None,
            "view_count": None, "muted_segments": None}


def upsert_clip(con: sqlite3.Connection, row: dict[str, Any]) -> bool:
    now = utcnow()
    exists = con.execute("SELECT 1 FROM crowd_clips WHERE clip_id = ?", (row["clip_id"],)).fetchone()
    with con:
        con.execute(
            """
            INSERT INTO crowd_clips (clip_id, streamer, video_id, vod_offset, duration_s,
                                     view_count, game_id, language, title, creator_id, url,
                                     created_at, first_seen_at, updated_at)
            VALUES (:clip_id, :streamer, :video_id, :vod_offset, :duration_s, :view_count,
                    :game_id, :language, :title, :creator_id, :url, :created_at, :now, :now)
            ON CONFLICT(clip_id) DO UPDATE SET
                video_id = COALESCE(excluded.video_id, crowd_clips.video_id),
                vod_offset = COALESCE(excluded.vod_offset, crowd_clips.vod_offset),
                view_count = MAX(excluded.view_count, crowd_clips.view_count),
                title = excluded.title,
                updated_at = excluded.updated_at
            """,
            {**row, "now": now},
        )
    return exists is None
