from __future__ import annotations

import httpx
import pytest

from clipengine import youtube
from clipengine.twitch import TokenStore, Twitch, TwitchError, parse_duration

from conftest import GTA, ago, make_clip


@pytest.mark.parametrize("text,seconds", [
    ("4h26m40s", 16000), ("59m3s", 3543), ("12s", 12), ("2h", 7200), ("", None),
    (None, None), ("abc", None),
])
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


def test_token_is_reused_across_runs_through_the_store(helix):
    saved = {}
    store = TokenStore(lambda: saved.get("t"), lambda v: saved.__setitem__("t", v))
    for _ in range(2):
        tw = Twitch("cid", "s", token_store=store, transport=httpx.MockTransport(helix.handler))
        tw.get("/users", [("login", "nobody")])
    assert helix.token_calls == 1


def test_401_refreshes_the_token_once(twitch, helix):
    helix.fail_next = [401]
    twitch.get("/users", [("login", "x")])
    assert helix.token_calls == 2
    assert helix.helix_calls[-1].headers["Authorization"] == "Bearer tok2"


def test_429_and_5xx_wait_then_retry(twitch, helix, sleeps):
    helix.fail_next = [429, 503]
    assert twitch.get("/users", [("login", "x")]) == {"data": []}
    assert len(sleeps) == 2


def test_gives_up_after_retries(twitch, helix):
    helix.fail_next = [500] * 10
    with pytest.raises(TwitchError, match="gave up"):
        twitch.get("/users", [("login", "x")])


def test_client_error_raises_with_status(twitch, helix):
    helix.fail_next = [400]
    with pytest.raises(TwitchError, match="HTTP 400"):
        twitch.get("/users", [("login", "x")])


def test_clips_follow_the_cursor_up_to_max_pages(twitch, helix):
    helix.clips = [make_clip(f"c{i}", "b1", "B", 1000 - i, ago(1)) for i in range(250)]
    got = twitch.clips(game_id=GTA, started_at=ago(5), ended_at=ago(0), max_pages=2)
    assert len(got) == 200 and got[0]["id"] == "c0"
    assert len(twitch.clips(game_id=GTA, started_at=ago(5), ended_at=ago(0), max_pages=9)) == 250


FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <title>Chan</title>
 <entry>
  <yt:videoId>abcDEF12345</yt:videoId>
  <title>GTA 6 first heist</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abcDEF12345"/>
  <published>{new}</published>
  <media:group><media:community><media:statistics views="4321"/></media:community></media:group>
 </entry>
 <entry>
  <yt:videoId>oldOLD12345</yt:videoId>
  <title>old upload</title>
  <published>{old}</published>
 </entry>
</feed>"""


def test_parse_feed():
    got = youtube.parse_feed(FEED.format(new="2026-11-19T10:00:00+00:00",
                                         old="2026-10-01T10:00:00+00:00"))
    assert got[0] == {"video_id": "abcDEF12345", "title": "GTA 6 first heist",
                      "published": "2026-11-19T10:00:00+00:00",
                      "url": "https://www.youtube.com/watch?v=abcDEF12345", "view_count": 4321}
    assert got[1]["url"] == "https://www.youtube.com/watch?v=oldOLD12345"
    assert got[1]["view_count"] is None


def test_feed_errors_are_youtube_errors(http):
    with pytest.raises(youtube.YouTubeError, match="404"):
        youtube.channel_uploads(http, "UCmissing")
    with pytest.raises(youtube.YouTubeError, match="XML"):
        youtube.parse_feed("<feed")
