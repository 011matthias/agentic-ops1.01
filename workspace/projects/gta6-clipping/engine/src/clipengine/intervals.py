"""Stage 2a, where in a VOD the viewers looked, read from their clips.

Each viewer clip covers a stretch of the VOD. Overlapping clips are one
moment; its weight is the sum of their views. Only metadata is used here,
nothing is downloaded.

Where a clip sits, measured live 2026-11-19 by matching each clip's audio
against its VOD (three clips, two VODs, 6.4 / 17.6 / 33.7 s long): the clip
starts at ``vod_offset - duration``, within about 1 s. Twitch's API reference
calls ``vod_offset`` the clip's start; in practice it is the clip's end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ClipSpan:
    clip_id: str
    start: float
    end: float
    views: int


@dataclass
class Interval:
    start: float          # merged span on the VOD timeline, unpadded
    end: float
    views: int            # sum over the merged clips
    clips: int
    top_clip_id: str      # the most-viewed clip inside
    top_start: float
    top_end: float
    top_views: int
    win_start: float = 0.0  # padded download window, set by plan()
    win_end: float = 0.0


def clip_span(clip_id: str, vod_offset: float, duration: float, views: int) -> ClipSpan:
    """The stretch of the VOD a clip shows; vod_offset marks its END (see module doc)."""
    end = float(vod_offset)
    return ClipSpan(clip_id, max(0.0, end - float(duration)), end, int(views))


def merge(spans: Iterable[ClipSpan]) -> list[Interval]:
    """Overlapping or touching spans become one interval, weighted by summed views."""
    out: list[Interval] = []
    for s in sorted(spans, key=lambda s: (s.start, s.end)):
        cur = out[-1] if out else None
        if cur is not None and s.start <= cur.end:
            cur.end = max(cur.end, s.end)
            cur.views += s.views
            cur.clips += 1
            if s.views > cur.top_views:
                cur.top_clip_id, cur.top_start, cur.top_end = s.clip_id, s.start, s.end
                cur.top_views = s.views
        else:
            out.append(Interval(s.start, s.end, s.views, 1, s.clip_id, s.start, s.end, s.views))
    return out


def window(iv: Interval, *, pad: float, max_len: float, vod_len: float | None) -> tuple[float, float]:
    """The download window: the interval plus pad on both sides.

    A long chain of overlapping clips can span minutes; then the window keeps
    max_len seconds centred on the most-viewed clip, inside the padded span.
    """
    lo, hi = iv.start - pad, iv.end + pad
    if hi - lo > max_len:
        mid = (iv.top_start + iv.top_end) / 2
        a, b = mid - max_len / 2, mid + max_len / 2
        if a < lo:
            a, b = lo, lo + max_len
        if b > hi:
            a, b = hi - max_len, hi
        lo, hi = a, b
    lo = max(0.0, lo)
    if vod_len:
        hi = min(float(vod_len), hi)
    return round(lo, 1), round(hi, 1)


def overlaps_muted(start: float, end: float, muted: Iterable[dict]) -> bool:
    """Twitch muted_segments: [{"offset": s, "duration": s}], the audio removed there."""
    for seg in muted:
        m_start = float(seg["offset"])
        if start < m_start + float(seg["duration"]) and m_start < end:
            return True
    return False


@dataclass
class Plan:
    chosen: list[Interval]
    muted: list[Interval]     # strong enough, but the window touches muted audio
    total: int                # merged intervals before any filter


def plan(spans: Iterable[ClipSpan], *, muted: Iterable[dict] = (), vod_len: float | None,
         top: int, min_views: int, pad: float, max_len: float) -> Plan:
    """The strongest `top` intervals by views, muted stretches excluded."""
    muted = list(muted)
    merged = sorted(merge(spans), key=lambda iv: (-iv.views, iv.start))
    chosen: list[Interval] = []
    skipped: list[Interval] = []
    for iv in merged:
        if iv.views < min_views or len(chosen) >= top:
            break
        iv.win_start, iv.win_end = window(iv, pad=pad, max_len=max_len, vod_len=vod_len)
        if overlaps_muted(iv.win_start, iv.win_end, muted):
            skipped.append(iv)
            continue
        chosen.append(iv)
    return Plan(chosen, skipped, len(merged))


def group_clips_by_time(clips: Iterable[dict], *, within_s: float = 90) -> list[list[dict]]:
    """Clips with no VOD to place them on: clips made within `within_s` of a
    group's first clip are taken as one moment (a viewer can only clip the
    last ~90 s of a live stream). Input dicts need created_at (ISO, UTC)."""
    from datetime import datetime

    def ts(c: dict) -> float:
        return datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")).timestamp()

    groups: list[list[dict]] = []
    first = 0.0
    for c in sorted(clips, key=ts):
        t = ts(c)
        if groups and t - first <= within_s:
            groups[-1].append(c)
        else:
            groups.append([c])
            first = t
    return groups
