"""The streamer register (config/streamers.yaml): who the engine watches.

The file is edited by hand or by `clipengine approve`. Approval appends a
text block instead of re-dumping the YAML, so comments in the file survive.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

from .db import utcnow

PERMISSIONS = ("unknown", "yes", "no")
LOGIN_RE = re.compile(r"^[a-z0-9_]{2,25}$")
CHANNEL_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


class RegisterError(ValueError):
    pass


@dataclass(frozen=True)
class Streamer:
    name: str
    twitch: str
    language: str
    youtube: str | None = None
    layout: str | None = None
    priority: int = 3
    permission: str = "unknown"


def load(path: Path) -> list[Streamer]:
    if not path.exists():
        raise RegisterError(f"register not found: {path}")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise RegisterError("register must be a mapping with a 'streamers' key")
    entries = doc.get("streamers") or []
    if not isinstance(entries, list):
        raise RegisterError("'streamers' must be a list")

    problems: list[str] = []
    out: list[Streamer] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries, start=1):
        where = f"entry {i}"
        if not isinstance(entry, dict):
            problems.append(f"{where}: not a mapping")
            continue
        twitch = str(entry.get("twitch") or "").strip().lower()
        where = f"entry {i} ({twitch or entry.get('name') or '?'})"
        if not LOGIN_RE.match(twitch):
            problems.append(f"{where}: 'twitch' must be a Twitch login")
        elif twitch in seen:
            problems.append(f"{where}: listed twice")
        seen.add(twitch)
        language = str(entry.get("language") or "").strip().lower()
        if not re.match(r"^[a-z]{2}$", language):
            problems.append(f"{where}: 'language' must be a two-letter code such as en")
        youtube = entry.get("youtube")
        if youtube is not None and not CHANNEL_RE.match(str(youtube)):
            problems.append(f"{where}: 'youtube' must be a channel id starting with UC")
        permission = str(entry.get("permission") or "unknown")
        if permission not in PERMISSIONS:
            problems.append(f"{where}: 'permission' must be one of {', '.join(PERMISSIONS)}")
        priority = entry.get("priority", 3)
        if not isinstance(priority, int) or not 1 <= priority <= 5:
            problems.append(f"{where}: 'priority' must be a whole number from 1 to 5")
        if problems:
            continue
        out.append(Streamer(
            name=str(entry.get("name") or twitch),
            twitch=twitch,
            language=language,
            youtube=youtube,
            layout=entry.get("layout"),
            priority=priority,
            permission=permission,
        ))
    if problems:
        raise RegisterError("register has problems:\n  " + "\n  ".join(problems))
    return out


def append(path: Path, streamer: Streamer) -> None:
    """Add one streamer at the end of the file, then re-validate the whole file."""
    before = path.read_text(encoding="utf-8")
    if any(s.twitch == streamer.twitch for s in load(path)):
        raise RegisterError(f"{streamer.twitch} is already in the register")

    def q(value: str | None) -> str:
        return "null" if value is None else yaml.safe_dump(value, default_style='"').strip()

    block = (
        f"  - name: {q(streamer.name)}\n"
        f"    twitch: {streamer.twitch}\n"
        f"    youtube: {q(streamer.youtube)}\n"
        f"    language: {streamer.language}\n"
        f"    layout: {q(streamer.layout)}\n"
        f"    priority: {streamer.priority}\n"
        f"    permission: {streamer.permission}\n"
    )
    text = before if before.endswith("\n") else before + "\n"
    # An empty register is written as `streamers: []`; the first entry turns it into a block list.
    text = re.sub(r"(?m)^streamers:[ \t]*\[\][ \t]*$", "streamers:", text)
    path.write_text(text + block, encoding="utf-8")
    try:
        load(path)
    except RegisterError:
        path.write_text(before, encoding="utf-8")
        raise


def sync(con: sqlite3.Connection, streamers: list[Streamer]) -> None:
    """Mirror the register into SQLite; streamers dropped from it go inactive."""
    now = utcnow()
    with con:
        for s in streamers:
            con.execute(
                """
                INSERT INTO streamers (login, display_name, youtube_channel_id, language, layout,
                                       priority, permission, active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(login) DO UPDATE SET
                    display_name = excluded.display_name,
                    youtube_channel_id = excluded.youtube_channel_id,
                    language = excluded.language,
                    layout = excluded.layout,
                    priority = excluded.priority,
                    permission = excluded.permission,
                    active = 1,
                    updated_at = excluded.updated_at
                """,
                (s.twitch, s.name, s.youtube, s.language, s.layout, s.priority, s.permission, now),
            )
        logins = [s.twitch for s in streamers]
        marks = ",".join("?" * len(logins))
        con.execute(
            f"UPDATE streamers SET active = 0, updated_at = ? "
            f"WHERE active = 1 AND login NOT IN ({marks or 'NULL'})",
            (now, *logins),
        )
