"""Twitch Helix client: app access token, retries, pagination.

Surface checked live 2026-11-17: Get Clips returns clips sorted by view count
with language, vod_offset and video_id; Get Videos returns muted_segments;
Get Channel Followers answers the total with an app token. Clips carry the
display name only, so logins come from Get Users.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timedelta
from typing import Any

import httpx

from .db import iso

HELIX = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"


class TwitchError(RuntimeError):
    pass


class TokenStore:
    """Where a minted app token is kept between runs (the SQLite meta table)."""

    def __init__(self, get: Callable[[], Any], put: Callable[[Any], None]):
        self.get, self.put = get, put


def parse_duration(text: str | None) -> int | None:
    """Twitch video duration '4h26m40s' -> seconds."""
    if not text:
        return None
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if not match or not any(match.groups()):
        return None
    h, m, s = (int(g or 0) for g in match.groups())
    return h * 3600 + m * 60 + s


def window_chunks(start: datetime, end: datetime, hours: float) -> list[tuple[datetime, datetime]]:
    out, cursor, step = [], start, timedelta(hours=hours)
    while cursor < end:
        out.append((cursor, min(cursor + step, end)))
        cursor += step
    return out


def _chunks(items: list[str], size: int) -> Iterator[list[str]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


class Twitch:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        token_store: TokenStore | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        max_retries: int = 3,
    ):
        self._id, self._secret = client_id, client_secret
        self._store = token_store
        self._http = httpx.Client(timeout=30, transport=transport)
        self._sleep, self._clock = sleep, clock
        self._max_retries = max_retries
        self._token: str | None = None
        self._expires = 0.0
        self.calls = 0

    # --- auth ---------------------------------------------------------------

    def _access_token(self, *, force: bool = False) -> str:
        now = self._clock()
        if not force and self._token and self._expires - 300 > now:
            return self._token
        if not force and self._store:
            cached = self._store.get()
            if cached and cached.get("expires_at", 0) - 300 > now:
                self._token, self._expires = cached["token"], cached["expires_at"]
                return self._token
        r = self._http.post(TOKEN_URL, data={
            "client_id": self._id, "client_secret": self._secret,
            "grant_type": "client_credentials",
        })
        if r.status_code != 200:
            raise TwitchError(f"app token request failed: HTTP {r.status_code}")
        body = r.json()
        self._token, self._expires = body["access_token"], now + float(body.get("expires_in", 0))
        if self._store:
            self._store.put({"token": self._token, "expires_at": self._expires})
        return self._token

    # --- requests -----------------------------------------------------------

    def get(self, path: str, params: Any) -> dict[str, Any]:
        refreshed = False
        last = None
        for attempt in range(self._max_retries + 1):
            headers = {"Client-Id": self._id,
                       "Authorization": f"Bearer {self._access_token(force=False)}"}
            self.calls += 1
            try:
                r = self._http.get(HELIX + path, params=params, headers=headers)
            except httpx.TransportError as exc:
                last = type(exc).__name__
                self._sleep(2 ** attempt)
                continue
            last = r.status_code
            if r.status_code == 200:
                return r.json()
            if r.status_code == 401 and not refreshed:
                self._access_token(force=True)
                refreshed = True
                continue
            if r.status_code == 429:
                reset = float(r.headers.get("Ratelimit-Reset", self._clock() + 1))
                self._sleep(min(max(reset - self._clock(), 1.0), 60.0))
                continue
            if r.status_code >= 500:
                self._sleep(2 ** attempt)
                continue
            raise TwitchError(f"GET {path} -> HTTP {r.status_code}: {r.text[:200]}")
        raise TwitchError(f"GET {path}: gave up after {self._max_retries} retries (last {last})")

    def paged(self, path: str, params: dict[str, Any], *, max_pages: int) -> Iterator[dict]:
        cursor = None
        for _ in range(max_pages):
            page_params = {**params, "first": 100}
            if cursor:
                page_params["after"] = cursor
            body = self.get(path, page_params)
            yield from body.get("data", [])
            cursor = (body.get("pagination") or {}).get("cursor")
            if not cursor:
                return

    # --- endpoints ----------------------------------------------------------

    def users(self, *, logins: Iterable[str] = (), ids: Iterable[str] = ()) -> list[dict]:
        keys = [("login", x) for x in logins] + [("id", x) for x in ids]
        out: list[dict] = []
        for batch in _chunks(keys, 100):  # type: ignore[arg-type]
            out.extend(self.get("/users", batch).get("data", []))
        return out

    def channels(self, ids: Iterable[str]) -> list[dict]:
        out: list[dict] = []
        for batch in _chunks(list(ids), 100):
            out.extend(self.get("/channels", [("broadcaster_id", x) for x in batch]).get("data", []))
        return out

    def follower_total(self, broadcaster_id: str) -> int | None:
        return self.get("/channels/followers", {"broadcaster_id": broadcaster_id}).get("total")

    def live_streams(self, logins: Iterable[str]) -> dict[str, str]:
        """login -> started_at for those of `logins` that are live right now."""
        out: dict[str, str] = {}
        for batch in _chunks(list(logins), 100):
            params = [("user_login", x) for x in batch] + [("first", "100")]
            for s in self.get("/streams", params).get("data", []):
                out[s["user_login"].lower()] = s["started_at"]
        return out

    def archive_videos(self, user_id: str, *, max_pages: int = 1) -> list[dict]:
        return list(self.paged("/videos", {"user_id": user_id, "type": "archive"},
                               max_pages=max_pages))

    def clips(self, *, started_at: str, ended_at: str, max_pages: int,
              broadcaster_id: str | None = None, game_id: str | None = None) -> list[dict]:
        if bool(broadcaster_id) == bool(game_id):
            raise ValueError("pass exactly one of broadcaster_id or game_id")
        params: dict[str, Any] = {"started_at": started_at, "ended_at": ended_at}
        params["broadcaster_id" if broadcaster_id else "game_id"] = broadcaster_id or game_id
        return list(self.paged("/clips", params, max_pages=max_pages))

    def clips_windowed(self, *, start: datetime, end: datetime, chunk_hours: float,
                       max_pages: int, broadcaster_id: str | None = None,
                       game_id: str | None = None) -> list[dict]:
        """Clips over a long window, split into chunks and de-duplicated.

        Measured 2026-11-17 on KaiCenat, 7 days: one query returned ~800
        distinct clips and a different ~800 on the next run (union 1,097),
        24 h chunks 1,413, 6 h chunks 1,965. Each query stops near 1,000
        results and repeats some across pages, so smaller windows see more.
        """
        seen: set[str] = set()
        out: list[dict] = []
        for chunk_start, chunk_end in window_chunks(start, end, chunk_hours):
            for clip in self.clips(started_at=iso(chunk_start), ended_at=iso(chunk_end),
                                   max_pages=max_pages, broadcaster_id=broadcaster_id,
                                   game_id=game_id):
                if clip["id"] not in seen:
                    seen.add(clip["id"])
                    out.append(clip)
        return out
