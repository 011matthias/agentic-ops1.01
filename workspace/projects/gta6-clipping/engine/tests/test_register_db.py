from __future__ import annotations

import pytest

from clipengine import db, register
from clipengine.register import RegisterError, Streamer

from conftest import ENGINE


def test_shipped_register_loads_empty():
    assert register.load(ENGINE / "config" / "streamers.yaml") == []


def test_append_turns_empty_list_into_entries_and_keeps_comments(env):
    register.append(env, Streamer(name="LIRIK", twitch="lirik", language="en"))
    register.append(env, Streamer(name='Kai "C"', twitch="kaicenat", language="en",
                                  youtube="UC" + "a" * 22, priority=1))
    text = env.read_text(encoding="utf-8")
    assert text.startswith("# Streamer-Register")
    got = register.load(env)
    assert [s.twitch for s in got] == ["lirik", "kaicenat"]
    assert got[1].name == 'Kai "C"' and got[1].priority == 1 and got[1].permission == "unknown"


def test_append_refuses_duplicate(env):
    register.append(env, Streamer(name="LIRIK", twitch="lirik", language="en"))
    with pytest.raises(RegisterError, match="already"):
        register.append(env, Streamer(name="Lirik", twitch="lirik", language="en"))


def test_append_rolls_back_an_invalid_entry(env):
    before = env.read_text(encoding="utf-8")
    with pytest.raises(RegisterError, match="youtube"):
        register.append(env, Streamer(name="X", twitch="someone", language="en",
                                      youtube="not-a-channel"))
    assert env.read_text(encoding="utf-8") == before


def test_load_reports_every_problem(tmp_path):
    path = tmp_path / "r.yaml"
    path.write_text(
        "streamers:\n"
        "  - {twitch: 'Bad Login!', language: en}\n"
        "  - {twitch: ok_one, language: english, permission: maybe}\n"
        "  - {twitch: ok_two, language: en, priority: 9}\n", encoding="utf-8")
    with pytest.raises(RegisterError) as err:
        register.load(path)
    msg = str(err.value)
    for needle in ("Twitch login", "two-letter", "permission", "priority"):
        assert needle in msg


def test_sync_deactivates_removed_streamers(con):
    a = Streamer(name="A", twitch="aaa", language="en")
    b = Streamer(name="B", twitch="bbb", language="en")
    register.sync(con, [a, b])
    register.sync(con, [a])
    active = {r["login"]: r["active"] for r in con.execute("SELECT login, active FROM streamers")}
    assert active == {"aaa": 1, "bbb": 0}


def test_migrations_run_once(con, env):
    from clipengine import config
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    again = db.connect(config.db_path())
    assert db.migrate(again) == len(db.MIGRATIONS)
    again.close()


def test_clip_rewatch_refreshes_facts_and_keeps_pipeline_state(con):
    register.sync(con, [Streamer(name="A", twitch="aaa", language="en")])
    row = {"clip_id": "c1", "streamer": "aaa", "video_id": None, "vod_offset": None,
           "duration_s": 30.0, "view_count": 10, "game_id": "g", "language": "en",
           "title": "t", "creator_id": "u", "url": "x", "created_at": "2026-11-19T00:00:00Z"}
    assert db.upsert_clip(con, row) is True
    con.execute("UPDATE crowd_clips SET status = 'fetched' WHERE clip_id = 'c1'")
    assert db.upsert_clip(con, {**row, "view_count": 50, "video_id": "v9", "vod_offset": 77}) \
        is False
    assert db.upsert_clip(con, {**row, "view_count": 40}) is False  # a lower read never wins
    got = con.execute("SELECT * FROM crowd_clips WHERE clip_id = 'c1'").fetchone()
    assert (got["view_count"], got["video_id"], got["vod_offset"], got["status"]) == \
        (50, "v9", 77, "fetched")
