"""Streamer suggestions: who gets the most viewer-clip views for GTA VI in one language.

Owner decision 2026-11-17: start streamers are picked by English clip views,
the owner signs off. Suggestions never enter the register on their own;
`clipengine approve` does that after the owner's yes.

Get Clips by game returns the most-viewed clips first and stops after about a
thousand per query, so the window is read in chunks (Twitch.clips_windowed):
each chunk yields its own top clips and busy launch days are not cut off at
the first thousand.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from . import db
from .twitch import Twitch


@dataclass
class Candidate:
    twitch_id: str
    display_name: str
    views: int = 0
    clips: int = 0
    clippers: set[str] = field(default_factory=set)
    self_clips: int = 0
    top_clip: dict | None = None
    login: str | None = None
    broadcaster_type: str | None = None
    followers: int | None = None
    channel_language: str | None = None
    lang: str = "en"

    @property
    def self_share(self) -> float:
        return self.self_clips / self.clips if self.clips else 0.0

    def flags(self) -> list[str]:
        """Warnings for the owner's review; they inform, they do not filter."""
        out = []
        if self.self_share > 0.5:
            out.append("mostly self-clipped")
        if len(self.clippers) < 3:
            out.append("fewer than 3 clippers")
        if self.channel_language and not self.channel_language.startswith(self.lang):
            out.append(f"channel language {self.channel_language}")
        return out


def collect(twitch: Twitch, *, game_id: str, start: datetime, end: datetime,
            chunk_hours: float, max_pages: int, lang: str) -> dict[str, Candidate]:
    cands: dict[str, Candidate] = {}
    for clip in twitch.clips_windowed(game_id=game_id, start=start, end=end,
                                      chunk_hours=chunk_hours, max_pages=max_pages):
        if not (clip.get("language") or "").startswith(lang):
            continue
        bid = clip["broadcaster_id"]
        cand = cands.setdefault(bid, Candidate(bid, clip["broadcaster_name"], lang=lang))
        cand.views += int(clip["view_count"])
        cand.clips += 1
        cand.clippers.add(clip.get("creator_id") or "")
        cand.self_clips += clip.get("creator_id") == bid
        if cand.top_clip is None or clip["view_count"] > cand.top_clip["view_count"]:
            cand.top_clip = clip
    return cands


def suggest(con: sqlite3.Connection, twitch: Twitch, *, game_id: str, start: datetime,
            end: datetime, chunk_hours: float = 6, max_pages: int = 10, lang: str = "en",
            top: int = 10) -> list[Candidate]:
    cands = collect(twitch, game_id=game_id, start=start, end=end, chunk_hours=chunk_hours,
                    max_pages=max_pages, lang=lang)

    registered_ids = {r["twitch_id"] for r in con.execute(
        "SELECT twitch_id FROM streamers WHERE twitch_id IS NOT NULL AND active = 1")}
    registered_logins = {r["login"] for r in con.execute(
        "SELECT login FROM streamers WHERE active = 1")}
    decided = {r["login"] for r in con.execute(
        "SELECT login FROM suggestions WHERE status IN ('approved', 'rejected')")}

    ranked = sorted((c for c in cands.values() if c.twitch_id not in registered_ids),
                    key=lambda c: (-c.views, -len(c.clippers), c.display_name.lower()))
    # Resolve logins for a margin beyond `top`, since some drop out as registered or decided.
    head = ranked[: top * 2 + 10]
    users = {u["id"]: u for u in twitch.users(ids=[c.twitch_id for c in head])}
    picked: list[Candidate] = []
    for cand in head:
        user = users.get(cand.twitch_id)
        if not user:
            continue
        cand.login = user["login"]
        cand.broadcaster_type = user.get("broadcaster_type") or "none"
        if cand.login in registered_logins or cand.login in decided:
            continue
        picked.append(cand)
        if len(picked) == top:
            break

    channels = {c["broadcaster_id"]: c for c in twitch.channels([c.twitch_id for c in picked])}
    for cand in picked:
        cand.channel_language = (channels.get(cand.twitch_id) or {}).get("broadcaster_language")
        cand.followers = twitch.follower_total(cand.twitch_id)
    _store(con, picked, start=start, end=end, lang=lang)
    return picked


def _store(con: sqlite3.Connection, picked: list[Candidate], *, start: datetime,
           end: datetime, lang: str) -> None:
    now = db.utcnow()
    with con:
        for c in picked:
            top = c.top_clip or {}
            con.execute(
                """
                INSERT INTO suggestions (login, twitch_id, display_name, window_start, window_end,
                    language, views, clips, clippers, self_clips, top_clip_url, top_clip_views,
                    top_clip_title, broadcaster_type, followers, channel_language,
                    first_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(login) DO UPDATE SET
                    display_name = excluded.display_name, window_start = excluded.window_start,
                    window_end = excluded.window_end, language = excluded.language,
                    views = excluded.views, clips = excluded.clips,
                    clippers = excluded.clippers, self_clips = excluded.self_clips,
                    top_clip_url = excluded.top_clip_url, top_clip_views = excluded.top_clip_views,
                    top_clip_title = excluded.top_clip_title,
                    broadcaster_type = excluded.broadcaster_type, followers = excluded.followers,
                    channel_language = excluded.channel_language, updated_at = excluded.updated_at
                """,
                (c.login, c.twitch_id, c.display_name, db.iso(start), db.iso(end), lang, c.views,
                 c.clips, len(c.clippers), c.self_clips, top.get("url"), top.get("view_count"),
                 top.get("title"), c.broadcaster_type, c.followers, c.channel_language, now, now),
            )


def render_report(picked: list[Candidate], *, start: datetime, end: datetime, lang: str) -> str:
    lines = [
        f"# Streamer suggestions, GTA VI, clip language '{lang}'",
        "",
        f"Window {db.iso(start)} to {db.iso(end)}. Ranked by total views of viewer clips "
        "in that window.",
        "",
        "| # | Streamer | Clip views | Clips | Clippers | Followers | Type | Flags | Top clip |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(picked, start=1):
        top = c.top_clip or {}
        title = (top.get("title") or "").replace("|", "/")[:60]
        followers = f"{c.followers:,}" if c.followers is not None else "?"
        lines.append(
            f"| {i} | [{c.display_name}](https://www.twitch.tv/{c.login}) | {c.views:,} | "
            f"{c.clips} | {len(c.clippers)} | {followers} | {c.broadcaster_type} | "
            f"{', '.join(c.flags()) or '-'} | [{top.get('view_count', 0):,}: {title}]"
            f"({top.get('url', '')}) |"
        )
    if not picked:
        lines.append("| - | no candidates in this window | | | | | | | |")
    return "\n".join(lines) + "\n"
