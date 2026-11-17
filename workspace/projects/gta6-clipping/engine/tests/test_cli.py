"""Caller-level tests: every case runs a real CLI command against the fake APIs."""

from __future__ import annotations

import json

from clipengine import cli, config, register
from clipengine.register import Streamer

from conftest import ago, make_clip
from test_twitch_youtube import FEED

CHANNEL = "UC" + "y" * 22


def run(argv, con, **inject):
    args = cli.build_parser().parse_args(argv)
    return cli.COMMANDS[args.command](args, con, **inject)


# --- watch ------------------------------------------------------------------

def seed_watch(helix, env):
    register.append(env, Streamer(name="Alpha", twitch="alpha", language="en", youtube=CHANNEL))
    register.append(env, Streamer(name="Beta", twitch="beta", language="en"))
    helix.add_user("1", "alpha", "Alpha")
    helix.add_user("2", "beta", "Beta")
    helix.videos["1"] = [
        {"id": "v1", "created_at": ago(20), "duration": "3h0m0s", "title": "GTA day 1",
         "url": "https://www.twitch.tv/videos/v1", "view_count": 900,
         "muted_segments": [{"duration": 30, "offset": 600}]},
        # began before the 7-day window, ran 30 h into it: its clips are in the window
        {"id": "v2", "created_at": ago(24 * 8), "duration": "30h0m0s", "title": "marathon"},
        {"id": "v0", "created_at": ago(24 * 10), "duration": "1h", "title": "too old"},
    ]
    helix.clips = [
        make_clip("a1", "1", "Alpha", 500, ago(19), video_id="v1", vod_offset=3600),
        make_clip("a2", "1", "Alpha", 40, ago(18), game="other-game"),
        make_clip("a3", "1", "Alpha", 999, ago(24 * 9)),          # outside the 7-day window
        make_clip("b1", "2", "Beta", 70, ago(2), video_id=None, vod_offset=None),
    ]
    helix.feeds[CHANNEL] = FEED.format(new=ago(5), old=ago(24 * 30))


def test_watch_stores_vods_clips_and_uploads(con, env, helix, twitch, http, capsys):
    seed_watch(helix, env)
    assert run(["watch"], con, twitch=twitch, http=http) == 0

    videos = {(r["source"], r["ext_id"]): r for r in con.execute("SELECT * FROM videos")}
    assert set(videos) == {("twitch", "v1"), ("twitch", "v2"), ("youtube", "abcDEF12345")}
    assert videos[("twitch", "v1")]["duration_s"] == 10800
    assert json.loads(videos[("twitch", "v1")]["muted_segments"]) == [{"duration": 30,
                                                                      "offset": 600}]
    clips = {r["clip_id"]: r for r in con.execute("SELECT * FROM crowd_clips")}
    assert set(clips) == {"a1", "a2", "b1"}
    assert (clips["a1"]["video_id"], clips["a1"]["vod_offset"]) == ("v1", 3600)
    assert clips["b1"]["video_id"] is None and clips["b1"]["vod_offset"] is None
    ids = {r["login"]: (r["twitch_id"], r["last_watched_at"]) for r in
           con.execute("SELECT * FROM streamers")}
    assert ids["alpha"][0] == "1" and ids["beta"][0] == "2" and ids["alpha"][1]
    assert "alpha" in capsys.readouterr().out


def test_rewatch_is_idempotent_and_refreshes_views(con, env, helix, twitch, http):
    seed_watch(helix, env)
    run(["watch"], con, twitch=twitch, http=http)
    helix.clips[0]["view_count"] = 800
    users_calls = sum(r.url.path.endswith("/users") for r in helix.helix_calls)
    run(["watch"], con, twitch=twitch, http=http)
    assert con.execute("SELECT COUNT(*) FROM crowd_clips").fetchone()[0] == 3
    assert con.execute("SELECT view_count FROM crowd_clips WHERE clip_id = 'a1'").fetchone()[0] \
        == 800
    # broadcaster ids are resolved once and remembered
    assert sum(r.url.path.endswith("/users") for r in helix.helix_calls) == users_calls


def test_watch_reports_an_unknown_login_and_keeps_going(con, env, helix, twitch, http, capsys):
    seed_watch(helix, env)
    register.append(env, Streamer(name="Gone", twitch="gone_user", language="en"))
    assert run(["watch"], con, twitch=twitch, http=http) == 1
    assert "Twitch login 'gone_user' not found" in capsys.readouterr().out
    assert con.execute("SELECT COUNT(*) FROM crowd_clips").fetchone()[0] == 3


def test_watch_reads_past_the_per_query_cap_of_a_busy_streamer(con, env, helix, twitch, http):
    """Live 2026-11-17: one 7-day query saw ~800 of ~2,000 KaiCenat clips."""
    register.append(env, Streamer(name="Busy", twitch="busy", language="en"))
    helix.add_user("5", "busy", "Busy")
    helix.clip_cap = 100
    helix.clips = [make_clip(f"k{d}-{i}", "5", "Busy", 10 + i, ago(24 * d + 1), creator=f"u{i}")
                   for d in range(3) for i in range(60)]
    assert run(["watch"], con, twitch=twitch, http=http) == 0
    assert con.execute("SELECT COUNT(*) FROM crowd_clips").fetchone()[0] == 180


def test_watch_with_empty_register_does_nothing(con, env, capsys):
    assert run(["watch"], con) == 0
    assert "register is empty" in capsys.readouterr().out


def test_list_shows_what_watch_stored(con, env, helix, twitch, http, capsys):
    seed_watch(helix, env)
    run(["watch"], con, twitch=twitch, http=http)
    capsys.readouterr()
    assert run(["list", "--streamer", "alpha"], con) == 0
    out = capsys.readouterr().out
    assert "v1" in out and "muted" in out and "vod v1@3600" in out and "GTA6" in out
    assert "marathon" in out and "too old" not in out


# --- suggest / approve / reject ---------------------------------------------

def seed_suggest(helix):
    helix.add_user("10", "bigstreamer", "BigStreamer", btype="partner", followers=2_000_000)
    helix.add_user("11", "midstreamer", "MidStreamer")
    helix.add_user("12", "germanone", "GermanOne", lang="de")
    helix.add_user("13", "selfclipper", "SelfClipper", btype="")
    helix.clips = [
        make_clip("s1", "10", "BigStreamer", 900, ago(3), creator="u1"),
        make_clip("s2", "10", "BigStreamer", 300, ago(4), creator="u2"),
        make_clip("s3", "10", "BigStreamer", 100, ago(30), creator="u3"),
        make_clip("s4", "11", "MidStreamer", 600, ago(5), creator="u4"),
        make_clip("s5", "12", "GermanOne", 5000, ago(2), lang="de", creator="u5"),
        make_clip("s6", "13", "SelfClipper", 50, ago(6), creator="13"),
        make_clip("s7", "13", "SelfClipper", 40, ago(7), creator="13"),
        make_clip("s8", "11", "MidStreamer", 10, ago(1), game="other-game"),
    ]


def test_suggest_ranks_english_clip_views_and_writes_a_report(con, env, helix, twitch, capsys):
    seed_suggest(helix)
    assert run(["suggest", "--since", "48h"], con, twitch=twitch) == 0
    rows = con.execute("SELECT * FROM suggestions ORDER BY views DESC").fetchall()
    assert [r["login"] for r in rows] == ["bigstreamer", "midstreamer", "selfclipper"]
    big = rows[0]
    assert (big["views"], big["clips"], big["clippers"], big["followers"]) == \
        (1300, 3, 3, 2_000_000)
    assert big["broadcaster_type"] == "partner" and big["top_clip_views"] == 900
    self_row = rows[2]
    assert (self_row["self_clips"], self_row["broadcaster_type"]) == (2, "none")
    out = capsys.readouterr().out
    assert "mostly self-clipped" in out and "GermanOne" not in out
    reports = list((config.data_dir() / "reports").glob("suggest-*.md"))
    assert len(reports) == 1 and "BigStreamer" in reports[0].read_text(encoding="utf-8")


def test_suggest_window_chunks_reach_past_the_page_cap(con, env, helix, twitch):
    """A busy hour must not crowd a quieter streamer out of the whole window."""
    helix.add_user("20", "busy", "Busy")
    helix.add_user("21", "quiet", "Quiet")
    helix.clips = [make_clip(f"b{i}", "20", "Busy", 1000 + i, ago(1), creator=f"u{i}")
                   for i in range(120)]
    helix.clips.append(make_clip("q1", "21", "Quiet", 500, ago(30), creator="q"))
    run(["suggest", "--since", "48h", "--max-pages", "1", "--chunk-hours", "6"], con,
        twitch=twitch)
    assert {r["login"] for r in con.execute("SELECT login FROM suggestions")} == {"busy", "quiet"}


def test_registered_and_rejected_streamers_are_not_suggested(con, env, helix, twitch, capsys):
    seed_suggest(helix)
    run(["suggest"], con, twitch=twitch)
    assert run(["approve", "bigstreamer", "--priority", "1"], con, twitch=twitch) == 0
    assert run(["reject", "selfclipper"], con) == 0
    entry = register.load(env)[0]
    assert (entry.twitch, entry.name, entry.priority, entry.language) == \
        ("bigstreamer", "BigStreamer", 1, "en")

    con.execute("DELETE FROM suggestions WHERE status = 'open'")
    con.commit()
    capsys.readouterr()
    run(["suggest", "--no-report"], con, twitch=twitch)
    shown = capsys.readouterr().out  # the list the owner is asked to sign off
    assert "MidStreamer" in shown
    assert "BigStreamer" not in shown and "SelfClipper" not in shown
    open_rows = {r["login"] for r in con.execute(
        "SELECT login FROM suggestions WHERE status = 'open'")}
    assert open_rows == {"midstreamer"}
    status = dict(con.execute("SELECT login, status FROM suggestions").fetchall())
    assert status["bigstreamer"] == "approved" and status["selfclipper"] == "rejected"


def test_a_registered_streamer_who_renamed_is_still_not_suggested(con, env, helix, twitch,
                                                                  capsys):
    """The register keeps the old login; the stable Twitch id still matches."""
    seed_suggest(helix)
    register.append(env, Streamer(name="Big", twitch="oldbigname", language="en"))
    register.sync(con, register.load(env))
    con.execute("UPDATE streamers SET twitch_id = '10' WHERE login = 'oldbigname'")
    con.commit()
    run(["suggest", "--no-report"], con, twitch=twitch)
    shown = capsys.readouterr().out
    assert "MidStreamer" in shown and "BigStreamer" not in shown


def test_approve_resolves_a_login_that_was_never_suggested(con, env, helix, twitch):
    helix.add_user("30", "freshone", "FreshOne")
    assert run(["approve", "FreshOne", "--youtube", CHANNEL], con, twitch=twitch) == 0
    entry = register.load(env)[0]
    assert (entry.twitch, entry.name, entry.youtube) == ("freshone", "FreshOne", CHANNEL)


def test_parse_when():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
    assert cli.parse_when("48h", now=now) == datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    assert cli.parse_when("1.5d", now=now) == datetime(2026, 11, 19, 0, tzinfo=timezone.utc)
    assert cli.parse_when("2026-11-19", now=now) == datetime(2026, 11, 19, tzinfo=timezone.utc)
    assert cli.parse_when("2026-11-19T06:00Z", now=now).hour == 6


def test_main_reports_missing_credentials(env, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CLIPENGINE_ENV_FILE", str(tmp_path / "missing.env"))
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)
    assert cli.main(["suggest"]) == 2
    assert "Twitch credentials missing" in capsys.readouterr().err


def test_env_file_parsing_ignores_comments_and_quotes():
    assert config.parse_env('# c\nTWITCH_CLIENT_ID="abc"\n\nX = y\nnoequals\n') == \
        {"TWITCH_CLIENT_ID": "abc", "X": "y"}
