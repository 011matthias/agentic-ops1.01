"""New YouTube uploads from the channel's public feed.

The feed needs no API key and no quota and lists the latest 15 uploads with
publish time (checked live 2026-11-17). Duration and the most-replayed curve
come later from yt-dlp metadata (p1.2).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

FEED = "https://www.youtube.com/feeds/videos.xml"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


class YouTubeError(RuntimeError):
    pass


def parse_feed(xml_text: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise YouTubeError(f"feed is not valid XML: {exc}") from exc
    out = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", default="", namespaces=NS)
        if not video_id:
            continue
        link = entry.find("atom:link", NS)
        stats = entry.find("media:group/media:community/media:statistics", NS)
        views = stats.get("views") if stats is not None else None
        out.append({
            "video_id": video_id,
            "title": entry.findtext("atom:title", default="", namespaces=NS),
            "published": entry.findtext("atom:published", default="", namespaces=NS),
            "url": link.get("href") if link is not None else
            f"https://www.youtube.com/watch?v={video_id}",
            "view_count": int(views) if views and views.isdigit() else None,
        })
    return out


def channel_uploads(client: httpx.Client, channel_id: str) -> list[dict]:
    try:
        r = client.get(FEED, params={"channel_id": channel_id})
    except httpx.HTTPError as exc:
        raise YouTubeError(f"feed request failed: {type(exc).__name__}") from exc
    if r.status_code != 200:
        raise YouTubeError(f"feed for {channel_id} -> HTTP {r.status_code}")
    return parse_feed(r.text)
