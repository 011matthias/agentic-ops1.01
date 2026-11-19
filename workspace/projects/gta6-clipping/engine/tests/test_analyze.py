"""p1.3 analyze + judge through the CLI, with a fake Whisper and fake stills."""

from __future__ import annotations

import json

import pytest

from clipengine import analyze, cli, config, db, register
from clipengine.cli import UsageError
from clipengine.register import Streamer


def run(argv, con, **inject):
    args = cli.build_parser().parse_args(argv)
    return cli.COMMANDS[args.command](args, con, **inject)


def words(text: str, start: float, step: float = 0.5) -> list[dict]:
    return [{"w": w, "s": round(start + i * step, 2), "e": round(start + i * step + 0.4, 2),
             "p": 0.9} for i, w in enumerate(text.split())]


# 0-10 s: two sentences, 10-20 s: the moment, 20-30 s: a closing sentence
SPEECH = (words("Okay we go now. Look at that plane.", 0.0)
          + words("Ready to engage? What does that mean? Oh no no no!", 10.0)
          + words("That was the worst flight ever.", 22.0))


def test_cut_starts_and_ends_at_sentence_boundaries():
    # core starts inside "Ready to engage?" and ends inside "Oh no no no!"
    a, b = analyze.cut_f1(SPEECH, (11.2, 14.0), 40.0, min_s=5, max_s=60)
    assert a == pytest.approx(10.0 - 0.15) and b == pytest.approx(SPEECH[18]["e"] + 0.3)


def test_cut_skips_a_sentence_that_ended_before_the_core():
    # core starts in the pause after "plane." (ends 3.9): begin at "Ready", not at "Look"
    a, _ = analyze.cut_f1(SPEECH, (6.0, 14.0), 40.0, min_s=5, max_s=60)
    assert a == pytest.approx(6.0)  # min(core start, "Ready" at 10.0 - 0.15)


def test_cut_stretches_to_the_minimum_with_whole_sentences():
    a, b = analyze.cut_f1(SPEECH, (11.2, 14.0), 40.0, min_s=15, max_s=60)
    assert a == pytest.approx(9.85) and b == pytest.approx(SPEECH[-1]["e"] + 0.3)


def test_cut_without_speech_keeps_the_core_and_minimum():
    assert analyze.cut_f1([], (5.0, 25.0), 120.0) == (5.0, 25.0)
    assert analyze.cut_f1([], (5.0, 8.0), 120.0) == (0.0, 15.0)


@pytest.fixture
def seeded(con, env):
    register.append(env, Streamer(name="ohnePixel", twitch="ohnepixel", language="en"))
    register.sync(con, register.load(env))
    now = db.utcnow()
    with con:
        # top clip: vod_offset 1260 is its END, 30 s long -> 1230-1260 in the VOD
        con.execute("INSERT INTO crowd_clips (clip_id, streamer, video_id, vod_offset, duration_s, "
                    "view_count, created_at, first_seen_at, updated_at, title, url) VALUES "
                    "('top', 'ohnepixel', 'v1', 1260, 30, 900, ?, ?, ?, 'jet', 'u')",
                    (now, now, now))
        con.execute("INSERT INTO sections (streamer, kind, video_id, top_clip_id, start_s, end_s, "
                    "win_start_s, win_end_s, views, clips, rank, status, file, file_duration_s, "
                    "created_at, updated_at) VALUES ('ohnepixel', 'vod', 'v1', 'top', 1230, 1260, "
                    "1220, 1270, 900, 3, 1, 'fetched', 'ohnepixel/v1/sections/1220-1270.mp4', "
                    "50, ?, ?)", (now, now))
    return con


class FakeWhisper:
    def __init__(self, speech):
        self.speech, self.loads, self.calls = speech, 0, []

    def factory(self):
        self.loads += 1

        def transcribe(path, language):
            self.calls.append((path.name, language))
            return analyze.Transcript(self.speech, [], language, 50.0, 1.0, "fake")
        return transcribe


def fake_stills(video, pkg, a, b):
    paths = [pkg / f"{i:02d}.jpg" for i in range(1, 9)]
    for p in paths:
        p.write_bytes(b"\0")
    return paths


def test_analyze_cuts_around_the_top_clip_and_writes_a_package(seeded, capsys):
    # the top clip lies at 10-40 s of the section file (1230-1260 minus window start 1220);
    # it starts inside "Ready to engage?" (9.0-10.4), so the cut goes back to "Ready"
    speech = words("Hello there. Ready to engage? Oh no.", 8.0) + words("Wasted again.", 39.5)
    fake = FakeWhisper(speech)
    assert run(["analyze"], seeded, transcriber=fake.factory, stills=fake_stills) == 0
    m = seeded.execute("SELECT * FROM moments").fetchone()
    assert (m["in_s"], m["status"]) == (pytest.approx(8.85), "review")
    assert m["out_s"] == pytest.approx(speech[-1]["e"] + 0.3)
    pkg = config.data_dir() / m["package"]
    meta = json.loads((pkg / "meta.json").read_text(encoding="utf-8"))
    assert meta["streamer"] == "ohnepixel" and meta["views"] == 900
    assert meta["vod_time"] == "0:20:28-0:21:00"
    assert "Ready to engage?" in (pkg / "transcript.txt").read_text(encoding="utf-8")
    assert fake.calls == [("1220-1270.mp4", "en")]
    # a second run reuses the stored moment: no model load
    assert run(["analyze"], seeded, transcriber=fake.factory, stills=fake_stills) == 0
    assert fake.loads == 1


def judged(con, tmp_path, moment, **answer):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(answer), encoding="utf-8")
    return run(["judge", str(moment), "--file", str(path)], con)


KEEP = {"verdict": "keep", "spoiler": False, "cutscene": False, "adult": "none",
        "category": "fail", "hooks": ["a", "b"],
        "title": "ohnePixel tries to fly a jet in GTA 6"}


def test_judge_stores_a_keep_and_refuses_unsafe_ones(seeded, tmp_path):
    fake = FakeWhisper(SPEECH)
    run(["analyze"], seeded, transcriber=fake.factory, stills=fake_stills)
    with pytest.raises(UsageError, match="spoiler"):
        judged(seeded, tmp_path, 1, **{**KEEP, "spoiler": True})
    with pytest.raises(UsageError, match="name the streamer"):
        judged(seeded, tmp_path, 1, **{**KEEP, "title": "Guy flies a jet"})
    with pytest.raises(UsageError, match="2 to 3 hooks"):
        judged(seeded, tmp_path, 1, **{**KEEP, "hooks": ["a"]})
    assert judged(seeded, tmp_path, 1, **KEEP) == 0
    row = seeded.execute("SELECT * FROM moments WHERE id = 1").fetchone()
    assert (row["status"], row["category"], json.loads(row["hooks"])) == ("keep", "fail",
                                                                         ["a", "b"])
    assert judged(seeded, tmp_path, 1, verdict="reject", adult="reject") == 0
    assert seeded.execute("SELECT status FROM moments WHERE id = 1").fetchone()[0] == "reject"
