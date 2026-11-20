"""p2 publish: schedule a READY video on YouTube for a fixed slot and drop the same file,
with its text, into the owner's iCloud TikTok folder under that slot.

Owner 2026-11-19: TikTok and YouTube stay in sync (same video, same slot); descriptions
carry no Twitch link. Owner 2026-11-20: three a day at the best times for reach.
Only explicitly named videos, one post per video and platform, dry run unless --go.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from . import db

TZ = ZoneInfo("Europe/Berlin")
# 20:00, 00:00, 02:00 German time = 14, 18, 20 h US Eastern: Sprout TikTok 2-6 pm,
# Buffer TikTok 6-11 pm, Buffer YouTube 7-9 pm (research 2026-11-19)
SLOTS = (time(20, 0), time(0, 0), time(2, 0))
LEAD = timedelta(minutes=20)  # the upload has to be processed before it goes public
SCENE = {"fail": "gta6fails"}  # every other category: gta6funny
TAGS = ["gta 6", "gta6", "grand theft auto 6", "gta 6 gameplay", "gta 6 funny"]


class PublishError(Exception):
    pass


class YouTube(Protocol):
    def channel_id(self) -> str: ...
    def upload(self, video: Path, body: dict) -> str: ...
    def videos(self, ids: list[str]) -> list[dict]: ...


@dataclass
class Plan:
    video: str          # ready id, e.g. m23-f1
    file: Path
    slot: datetime      # aware, German time
    title: str
    description: str
    tags: list[str]

    @property
    def slot_utc(self) -> str:
        return db.iso(self.slot)

    @property
    def tiktok_name(self) -> str:
        return f"{self.slot:%Y-%m-%d %H-%M} {self.video}"


def texts(edl: dict) -> tuple[str, str, list[str]]:
    """Title, description and tags; the description is also the TikTok caption."""
    title, name = edl["title"], edl["display_name"]
    if name.lower() not in title.lower():
        raise PublishError(f"{edl['id']}: title does not name {name}")
    tag = re.sub(r"[^a-z0-9]", "", name.lower())
    scene = SCENE.get(edl.get("category") or "", "gta6funny")
    description = f"{title}\n\n#gta6 #{tag} #{scene} #gta6clips"
    if "twitch.tv" in title or "twitch.tv" in description:
        raise PublishError(f"{edl['id']}: no Twitch link in the text (owner 2026-11-19)")
    return title, description, [*TAGS, name, f"{name} gta 6"]


def slot_times(now: datetime, days: int = 14):
    """Every fixed slot after now + LEAD, in order."""
    start = now.astimezone(TZ).date()
    for offset in range(days):
        day = start + timedelta(days=offset)
        for t in sorted(SLOTS):
            moment = datetime.combine(day, t, tzinfo=TZ)
            if moment > now + LEAD:
                yield moment


def parse_slot(text: str, now: datetime) -> datetime:
    """'2026-11-21 02:00' in German time; must be one of the fixed slots, in the future."""
    try:
        moment = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError as exc:
        raise PublishError(f"slot '{text}': use 'YYYY-MM-DD HH:MM' (German time)") from exc
    if moment.timetz().replace(tzinfo=None) not in SLOTS:
        raise PublishError(f"slot '{text}' is not a fixed slot "
                           f"({', '.join(f'{t:%H:%M}' for t in SLOTS)})")
    if moment <= now + LEAD:
        raise PublishError(f"slot '{text}' is less than {LEAD} away")
    return moment


def taken_slots(con: sqlite3.Connection) -> set[str]:
    return {r["slot_utc"] for r in con.execute(
        "SELECT slot_utc FROM posts WHERE platform = 'youtube' AND slot_utc IS NOT NULL")}


def import_ledger(con: sqlite3.Connection, path: Path) -> int:
    """Uploads made by hand before this command (publish/youtube.json) count as posted."""
    if not path.exists():
        return 0
    added = 0
    with con:
        for video, entry in json.loads(path.read_text(encoding="utf-8")).items():
            cur = con.execute(
                "INSERT OR IGNORE INTO posts (video, platform, remote_id, slot_utc, title, "
                "created_at) VALUES (?, 'youtube', ?, ?, ?, ?)",
                (video, entry["video_id"], entry.get("publish_at"), entry["title"], db.utcnow()))
            added += cur.rowcount
    return added


def plan(con: sqlite3.Connection, videos: list[str], *, data_dir: Path, now: datetime,
         slot: str | None = None) -> list[Plan]:
    if slot and len(videos) != 1:
        raise PublishError("--slot takes exactly one video")
    taken, plans = taken_slots(con), []
    free = (s for s in slot_times(now) if db.iso(s) not in taken)
    for video in videos:
        posted = con.execute("SELECT remote_id FROM posts WHERE video = ? AND platform = "
                             "'youtube'", (video,)).fetchone()
        if posted:
            raise PublishError(f"{video} is already on YouTube ({posted['remote_id']})")
        folder = data_dir / "ready" / video
        file, edl_path = folder / f"{video}.mp4", folder / "edl.json"
        if not file.exists() or not edl_path.exists():
            raise PublishError(f"{video} is not READY (no {file.name} or edl.json)")
        title, description, tags = texts(json.loads(edl_path.read_text(encoding="utf-8")))
        when = parse_slot(slot, now) if slot else next(free)
        if db.iso(when) in taken:
            raise PublishError(f"slot {when:%Y-%m-%d %H:%M} is already booked")
        taken.add(db.iso(when))
        plans.append(Plan(video, file, when, title, description, tags))
    return plans


def body(p: Plan) -> dict:
    return {
        "snippet": {"title": p.title, "description": p.description, "categoryId": "20",
                    "tags": p.tags, "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private", "publishAt": p.slot_utc,
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False,
                   "embeddable": True},
    }


def drop_tiktok(p: Plan, dest: Path) -> Path:
    """The same file plus a copy-ready caption, named so the owner sees when to post."""
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"{p.tiktok_name}.mp4"
    shutil.copyfile(p.file, target)
    text = f"TITEL\n{p.title}\n\nBESCHREIBUNG\n{p.description}\n"
    (dest / f"{p.tiktok_name}.txt").write_text(text, encoding="utf-8", newline="\r\n")
    if target.stat().st_size != p.file.stat().st_size:
        raise PublishError(f"{target.name}: copy size differs from {p.file.name}")
    return target


def publish(con: sqlite3.Connection, plans: list[Plan], *, youtube: YouTube, channel: str,
            tiktok_dir: Path) -> list[str]:
    """Upload, record, drop, then read every upload back; returns the read-back problems."""
    mine = youtube.channel_id()
    if mine != channel:
        raise PublishError(f"the YouTube token is for {mine}, not the configured channel")
    uploaded: dict[str, Plan] = {}
    for p in plans:
        remote = youtube.upload(p.file, body(p))
        with con:
            con.execute("INSERT INTO posts (video, platform, remote_id, slot_utc, title, "
                        "created_at) VALUES (?, 'youtube', ?, ?, ?, ?)",
                        (p.video, remote, p.slot_utc, p.title, db.utcnow()))
        uploaded[remote] = p
        target = drop_tiktok(p, tiktok_dir)
        with con:
            con.execute("INSERT INTO posts (video, platform, remote_id, slot_utc, title, "
                        "created_at) VALUES (?, 'tiktok', ?, ?, ?, ?)",
                        (p.video, target.name, p.slot_utc, p.title, db.utcnow()))
    problems = []
    back = {v["id"]: v for v in youtube.videos(list(uploaded))}
    for remote, p in uploaded.items():
        v = back.get(remote)
        if v is None:
            problems.append(f"{p.video}: {remote} not found on read-back")
            continue
        st, sn = v["status"], v["snippet"]
        if st.get("privacyStatus") != "private" or st.get("publishAt") != p.slot_utc:
            problems.append(f"{p.video}: read back {st.get('privacyStatus')} / "
                            f"{st.get('publishAt')}, expected private / {p.slot_utc}")
        if sn.get("channelId") != channel or "twitch.tv" in sn.get("description", ""):
            problems.append(f"{p.video}: wrong channel or a Twitch link on read-back")
    return problems


class GoogleYouTube:
    """The YouTube Data API with the owner's OAuth token (youtube.upload scope)."""

    def __init__(self, token: Path):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(token))
        if "https://www.googleapis.com/auth/youtube.upload" not in (creds.scopes or []):
            raise PublishError(f"{token.name} lacks the youtube.upload scope")
        self.api = build("youtube", "v3", credentials=creds)

    def channel_id(self) -> str:
        items = self.api.channels().list(part="id", mine=True).execute().get("items", [])
        return ",".join(i["id"] for i in items)

    def upload(self, video: Path, body: dict) -> str:
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(video), mimetype="video/mp4", resumable=True,
                                chunksize=8 * 1024 * 1024)
        req = self.api.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
        return resp["id"]

    def videos(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        return self.api.videos().list(part="snippet,status",
                                      id=",".join(ids)).execute().get("items", [])


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
