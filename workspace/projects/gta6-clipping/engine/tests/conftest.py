"""A fake Twitch Helix + YouTube feed behind httpx.MockTransport.

It answers the shapes checked live on 2026-11-17: clips sorted by views,
cursor pagination, users by login or id, followers total, channel language.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from clipengine import db
from clipengine.twitch import Twitch

ENGINE = Path(__file__).resolve().parents[1]
GTA = "1867279146"


def ago(hours: float) -> str:
    return db.iso(datetime.now(timezone.utc) - timedelta(hours=hours))


def make_clip(cid: str, bid: str, name: str, views: int, created: str, *, lang: str = "en",
              game: str = GTA, creator: str = "viewer1", video_id: str = "v100",
              vod_offset: int | None = 120, duration: float = 30.0) -> dict:
    return {"id": cid, "broadcaster_id": bid, "broadcaster_name": name, "view_count": views,
            "created_at": created, "language": lang, "game_id": game, "creator_id": creator,
            "video_id": video_id, "vod_offset": vod_offset, "duration": duration,
            "title": f"clip {cid}", "url": f"https://clips.twitch.tv/{cid}"}


class FakeHelix:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.videos: dict[str, list[dict]] = {}
        self.clips: list[dict] = []
        self.followers: dict[str, int] = {}
        self.channels: dict[str, dict] = {}
        self.feeds: dict[str, str] = {}
        self.live: list[dict] = []  # Get Streams rows: user_login, started_at
        self.fail_next: list[int] = []
        self.clip_cap: int | None = None  # live Twitch stops each clip query near 1,000
        self.token_calls = 0
        self.helix_calls: list[httpx.Request] = []

    def add_user(self, uid: str, login: str, name: str | None = None,
                 btype: str = "affiliate", lang: str = "en", followers: int = 1000) -> None:
        self.users[uid] = {"id": uid, "login": login, "display_name": name or login,
                           "broadcaster_type": btype}
        self.channels[uid] = {"broadcaster_id": uid, "broadcaster_language": lang}
        self.followers[uid] = followers

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        if url.host == "id.twitch.tv":
            self.token_calls += 1
            return httpx.Response(200, json={"access_token": f"tok{self.token_calls}",
                                             "expires_in": 5_000_000, "token_type": "bearer"})
        if url.host == "www.youtube.com":
            feed = self.feeds.get(url.params.get("channel_id", ""))
            return httpx.Response(200, text=feed) if feed else httpx.Response(404)
        assert url.host == "api.twitch.tv", url
        self.helix_calls.append(request)
        if self.fail_next:
            return httpx.Response(self.fail_next.pop(0), headers={"Ratelimit-Reset": "0"},
                                  json={"error": "fake"})
        path, q = url.path.removeprefix("/helix"), url.params
        if path == "/users":
            logins, ids = q.get_list("login"), q.get_list("id")
            return httpx.Response(200, json={"data": [
                u for u in self.users.values() if u["login"] in logins or u["id"] in ids]})
        if path == "/videos":
            return self._page(self.videos.get(q["user_id"], []), q)
        if path == "/clips":
            if "broadcaster_id" in q:
                pool = [c for c in self.clips if c["broadcaster_id"] == q["broadcaster_id"]]
            else:
                pool = [c for c in self.clips if c["game_id"] == q["game_id"]]
            pool = [c for c in pool if q["started_at"] <= c["created_at"] < q["ended_at"]]
            pool = sorted(pool, key=lambda c: -c["view_count"])[:self.clip_cap]
            return self._page(pool, q)
        if path == "/streams":
            logins = q.get_list("user_login")
            return httpx.Response(200, json={"data": [s for s in self.live
                                                      if s["user_login"] in logins],
                                             "pagination": {}})
        if path == "/channels/followers":
            return httpx.Response(200, json={"total": self.followers.get(q["broadcaster_id"], 0),
                                             "data": [], "pagination": {}})
        if path == "/channels":
            ids = q.get_list("broadcaster_id")
            return httpx.Response(200, json={"data": [self.channels[i] for i in ids
                                                      if i in self.channels]})
        return httpx.Response(404, json={"error": "no route"})

    @staticmethod
    def _page(items: list[dict], q) -> httpx.Response:
        first, start = int(q.get("first", 20)), int(q.get("after", 0))
        nxt = start + first
        return httpx.Response(200, json={
            "data": items[start:nxt],
            "pagination": {"cursor": str(nxt)} if nxt < len(items) else {}})


@pytest.fixture
def helix() -> FakeHelix:
    return FakeHelix()


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def twitch(helix, sleeps) -> Twitch:
    return Twitch("cid", "secret", transport=httpx.MockTransport(helix.handler),
                  sleep=sleeps.append)


@pytest.fixture
def http(helix) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(helix.handler))


@pytest.fixture
def env(tmp_path, monkeypatch) -> Path:
    """Isolated data dir and an empty register with the shipped header comments.

    The shipped register holds the real start streamers, so tests build their
    own empty one from its header instead of copying it.
    """
    shipped = (ENGINE / "config" / "streamers.yaml").read_text(encoding="utf-8")
    header = shipped.split("\nstreamers:", 1)[0].rstrip("\n")
    reg = tmp_path / "streamers.yaml"
    reg.write_text(header + "\n\nstreamers: []\n", encoding="utf-8")
    monkeypatch.setenv("CLIPENGINE_REGISTER", str(reg))
    monkeypatch.setenv("CLIPENGINE_DATA_DIR", str(tmp_path / "data"))
    return reg


@pytest.fixture
def con(env):
    from clipengine import config
    c = db.connect(config.db_path())
    yield c
    c.close()
