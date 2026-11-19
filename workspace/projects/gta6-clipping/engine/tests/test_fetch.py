"""p1.2 fetch: interval planning, then section downloads, mostly through the CLI.

No network and no ffmpeg: the downloader and ffprobe are fakes that write
small files and report the duration that was asked for.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from clipengine import cli, config, db, intervals, register
from clipengine.fetch import FetchError, Probe, YtDlp
from clipengine.register import Streamer

from conftest import ago, make_clip


def run(argv, con, **inject):
    args = cli.build_parser().parse_args(argv)
    return cli.COMMANDS[args.command](args, con, **inject)


class FakeDownloader:
    """Writes an empty .mp4 per call and remembers the duration it should have."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.durations: dict[Path, float] = {}

    def _write(self, stem: Path, duration: float) -> Path:
        path = Path(f"{stem}.mp4")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\0")
        self.durations[path] = duration
        return path

    def section(self, url, start, end, stem):
        self.calls.append(("section", url, start, end))
        return self._write(stem, end - start)

    def clip(self, url, stem):
        self.calls.append(("clip", url))
        return self._write(stem, 30.0)

    def probe(self, path: Path) -> Probe:
        return Probe(self.durations[path], 1920, 1080, True, True)


# --- interval rules ----------------------------------------------------------

def test_vod_offset_marks_the_clip_end():
    # live 2026-11-19: a 33.7 s xQc clip with vod_offset 83165 starts at 83132 in the VOD
    span = intervals.clip_span("c", 83165, 33.7, 10)
    assert (round(span.start, 1), span.end) == (83131.3, 83165.0)


def test_overlapping_clips_merge_and_sum_views():
    spans = [intervals.clip_span("a", 100, 30, 500), intervals.clip_span("b", 120, 30, 900),
             intervals.clip_span("c", 400, 20, 50)]
    merged = intervals.merge(spans)
    assert [(m.start, m.end, m.views, m.clips, m.top_clip_id) for m in merged] == [
        (70.0, 120.0, 1400, 2, "b"), (380.0, 400.0, 50, 1, "c")]


def test_long_chain_keeps_max_len_around_the_top_clip():
    spans = [intervals.clip_span(f"c{i}", 100 + 25 * i, 30, 10) for i in range(20)]
    spans.append(intervals.clip_span("peak", 400, 30, 5000))
    (iv,) = intervals.merge(spans)
    lo, hi = intervals.window(iv, pad=5, max_len=120, vod_len=None)
    assert hi - lo == 120 and lo <= 370 and hi >= 400


def test_window_is_clamped_to_the_vod():
    (iv,) = intervals.merge([intervals.clip_span("a", 20, 30, 1)])
    assert intervals.window(iv, pad=5, max_len=120, vod_len=22) == (0.0, 22.0)


# --- fetch through the CLI ---------------------------------------------------

def seed(helix, env, con, twitch, http):
    for name in ("Alpha", "Beta", "Gamma"):
        register.append(env, Streamer(name=name, twitch=name.lower(), language="en"))
    helix.add_user("1", "alpha", "Alpha")
    helix.add_user("2", "beta", "Beta")
    helix.add_user("3", "gamma", "Gamma")
    beta_start = ago(2)
    helix.videos["1"] = [{"id": "v1", "created_at": ago(20), "duration": "3h0m0s",
                          "title": "GTA", "url": "https://www.twitch.tv/videos/v1",
                          "muted_segments": [{"offset": 1000, "duration": 360}]}]
    helix.videos["2"] = [{"id": "v2", "created_at": beta_start, "duration": "2h0m0s",
                          "title": "live GTA", "url": "https://www.twitch.tv/videos/v2"}]
    helix.live = [{"user_login": "beta", "started_at": beta_start}]
    t = datetime.now(timezone.utc) - timedelta(hours=3)
    helix.clips = [
        # one moment clipped twice: spans 3570-3600 and 3590-3620
        make_clip("a1", "1", "Alpha", 500, ago(19), video_id="v1", vod_offset=3600, duration=30),
        make_clip("a2", "1", "Alpha", 300, ago(19), video_id="v1", vod_offset=3620, duration=30),
        # strongest, but inside the muted stretch 1000-1360
        make_clip("b1", "1", "Alpha", 1000, ago(19), video_id="v1", vod_offset=1200, duration=20),
        make_clip("c1", "1", "Alpha", 100, ago(18), video_id="v1", vod_offset=7000, duration=10),
        make_clip("d1", "1", "Alpha", 5000, ago(18), video_id="v1", vod_offset=8000,
                  game="other-game"),
        make_clip("e1", "1", "Alpha", 10, ago(18), video_id="v1", vod_offset=9000, duration=10),
        # Beta is live 2 h into v2: l1 is long recorded, l2 sits in the last 30 min
        make_clip("l1", "2", "Beta", 900, ago(1), video_id="v2", vod_offset=600),
        make_clip("l2", "2", "Beta", 2000, ago(0.2), video_id="v2", vod_offset=6000),
        # no VOD: g1 and g2 are one moment (made 30 s apart), g3 is too weak alone
        make_clip("g1", "3", "Gamma", 70, db.iso(t), video_id=None, vod_offset=None),
        make_clip("g2", "3", "Gamma", 20, db.iso(t + timedelta(seconds=30)), video_id=None,
                  vod_offset=None),
        make_clip("g3", "3", "Gamma", 5, ago(10), video_id=None, vod_offset=None),
    ]
    assert run(["watch", "--days", "2"], con, twitch=twitch, http=http) == 0


def test_fetch_downloads_only_the_most_viewed_stretches(con, env, helix, twitch, http, capsys):
    seed(helix, env, con, twitch, http)
    dl = FakeDownloader()
    assert run(["fetch"], con, twitch=twitch, downloader=dl, probe=dl.probe) == 0

    assert sorted(dl.calls) == sorted([
        ("section", "https://www.twitch.tv/videos/v1", 3565.0, 3625.0),  # a1+a2, 5 s pad
        ("section", "https://www.twitch.tv/videos/v1", 6985.0, 7005.0),  # c1
        ("section", "https://www.twitch.tv/videos/v2", 565.0, 605.0),    # l1, recorded part
        ("clip", "https://clips.twitch.tv/g1"),                          # Gamma, no VOD
    ])
    rows = {r["top_clip_id"]: r for r in con.execute("SELECT * FROM sections")}
    assert set(rows) == {"a1", "c1", "l1", "g1"}
    assert (rows["a1"]["views"], rows["a1"]["clips"], rows["a1"]["rank"]) == (800, 2, 1)
    assert rows["a1"]["file"] == "alpha/v1/sections/3565-3625.mp4"
    assert (config.data_dir() / rows["a1"]["file"]).exists()
    assert (rows["g1"]["views"], rows["g1"]["file"]) == (90, "gamma/clips/g1.mp4")
    assert all(r["status"] == "fetched" for r in rows.values())
    assert con.execute("SELECT status FROM videos WHERE ext_id = 'v1'").fetchone()[0] == "fetched"
    # still recording: never marked done, so the next run plans what was recorded since
    assert con.execute("SELECT status FROM videos WHERE ext_id = 'v2'").fetchone()[0] != "fetched"
    out = capsys.readouterr().out
    assert "1 muted skipped" in out
    assert "beta v2: still live, planned up to 1:30 h of the recording" in out

    # idempotent: a second run downloads nothing new
    dl2 = FakeDownloader()
    assert run(["fetch"], con, twitch=twitch, downloader=dl2, probe=dl.probe) == 0
    assert dl2.calls == []


def test_fetch_dry_run_plans_without_downloading(con, env, helix, twitch, http, capsys):
    seed(helix, env, con, twitch, http)
    dl = FakeDownloader()
    assert run(["fetch", "--dry-run", "--streamer", "Alpha"], con, twitch=twitch,
               downloader=dl, probe=dl.probe) == 0
    assert dl.calls == []
    assert {r["status"] for r in con.execute("SELECT status FROM sections")} == {"planned"}
    assert "dry run" in capsys.readouterr().out


def test_fetch_refuses_downloads_when_disk_is_low(con, env, helix, twitch, http, monkeypatch):
    seed(helix, env, con, twitch, http)
    monkeypatch.setenv("CLIPENGINE_MIN_FREE_GB", "1000000")
    dl = FakeDownloader()
    with pytest.raises(FetchError, match="GB free"):
        run(["fetch"], con, twitch=twitch, downloader=dl, probe=dl.probe)
    assert dl.calls == []


def test_fetch_marks_a_short_file_failed(con, env, helix, twitch, http, capsys):
    seed(helix, env, con, twitch, http)
    dl = FakeDownloader()

    def short(path):
        return Probe(5.0, 1920, 1080, True, True)

    assert run(["fetch", "--streamer", "alpha"], con, twitch=twitch, downloader=dl,
               probe=short) == 1
    row = con.execute("SELECT * FROM sections WHERE top_clip_id = 'a1'").fetchone()
    assert row["status"] == "failed" and "asked for 60.0 s" in row["last_error"]
    assert row["attempts"] == 1


def test_ytdlp_retries_a_reset_connection_through_the_cli(con, env, helix, twitch, http):
    seed(helix, env, con, twitch, http)
    calls, sleeps = [], []

    def fake_run(args, **kw):
        calls.append(args)
        if len(calls) == 1:  # Twitch reset the first playlist request, as seen live
            return subprocess.CompletedProcess(args, 1, "", "ERROR: [WinError 10054] reset")
        template = args[args.index("-o") + 1]
        path = Path(template.replace("%(ext)s", "mp4"))
        path.write_bytes(b"\0")
        return subprocess.CompletedProcess(args, 0, f"{path}\n", "")

    ytdlp = YtDlp(run=fake_run, sleep=sleeps.append)

    def probe(path):
        return Probe(60.0, 1920, 1080, True, True)

    assert run(["fetch", "--video", "v1", "--top", "1"], con, twitch=twitch, downloader=ytdlp,
               probe=probe) == 0
    assert len(calls) == 2 and sleeps == [5.0]
    assert "--download-sections" in calls[1] and "*3565.0-3625.0" in calls[1]
    assert "--force-ipv4" in calls[1]  # IPv6 reset ~40 % of first requests live
    # a recording VOD's playlist is live: ffmpeg must start at segment 0, not the live edge
    i = calls[1].index("--downloader-args")
    assert calls[1][i + 1] == "ffmpeg_i:-live_start_index 0"
    row = con.execute("SELECT status, file FROM sections").fetchone()
    assert tuple(row) == ("fetched", "alpha/v1/sections/3565-3625.mp4")


def test_a_hung_download_fails_its_section_not_the_run(con, env, helix, twitch, http, capsys):
    seed(helix, env, con, twitch, http)

    def hang(args, **kw):
        raise subprocess.TimeoutExpired(args, kw["timeout"])

    ytdlp = YtDlp(run=hang, sleep=lambda s: None)
    assert run(["fetch", "--video", "v1", "--top", "1"], con, twitch=twitch, downloader=ytdlp,
               probe=lambda p: Probe(60.0, 1920, 1080, True, True)) == 1
    row = con.execute("SELECT status, attempts, last_error FROM sections").fetchone()
    assert row["status"] == "failed" and row["attempts"] == 1
    assert "timed out after 600 s" in row["last_error"]
    assert "timed out" in capsys.readouterr().out
