"""p1.4 to p1.6 through the CLI: cut list, the real render() over a faked ffmpeg, checks."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from clipengine import cli, config, db, follow, register, render
from clipengine.cli import UsageError
from clipengine.register import Streamer

LAYOUTS = {"ohnepixel": {"facecam": [230, 700, 440, 380], "gameplay": [560, 0, 1360, 1080]}}
WORDS = [{"w": w, "s": 10.0 + i * 0.5, "e": 10.4 + i * 0.5, "p": 0.9}
         for i, w in enumerate("Ready to engage? What does that mean? Oh no no no!".split())]


def run(argv, con, **inject):
    args = cli.build_parser().parse_args(argv)
    return cli.COMMANDS[args.command](args, con, **inject)


@pytest.fixture
def kept(con, env, monkeypatch):
    return make_kept(con, env, monkeypatch)


def make_kept(con, env, monkeypatch):
    """One kept ohnePixel moment (8-30 s of a fetched VOD section) with a layout."""
    register.append(env, Streamer(name="ohnePixel", twitch="ohnepixel", language="en"))
    register.sync(con, register.load(env))
    now = db.utcnow()
    with con:
        con.execute("INSERT INTO sections (streamer, kind, video_id, top_clip_id, start_s, end_s, "
                    "win_start_s, win_end_s, views, clips, status, file, file_duration_s, "
                    "created_at, updated_at) VALUES ('ohnepixel', 'vod', 'v1', 'top', 1230, 1260,"
                    " 1220, 1270, 900, 3, 'fetched', 'ohnepixel/v1/sections/1220-1270.mp4', 50,"
                    " ?, ?)", (now, now))
        con.execute("INSERT INTO transcripts (section_id, model, words, segments, created_at) "
                    "VALUES (1, 'fake', ?, '[]', ?)", (json.dumps(WORDS), now))
        con.execute("INSERT INTO moments (section_id, in_s, out_s, status, category, hooks, title,"
                    " created_at, updated_at) VALUES (1, 8.0, 30.0, 'keep', 'fail', ?, "
                    "'ohnePixel tries to fly a jet through Vice City in GTA 6', ?, ?)",
                    (json.dumps(["He thought flying a jet through the city was a good idea",
                                 "b"]), now, now))
    monkeypatch.setattr("clipengine.produce.load_layouts", lambda path: LAYOUTS)
    return con


class FakeFfmpeg:
    """Stands in for subprocess.run inside render.py: no NVENC on this driver,
    a loudnorm measurement, and an encode that writes the output file."""

    def __init__(self):
        self.encodes: list[list[str]] = []

    def __call__(self, cmd, **kw):
        if "color=s=256x256:d=0.1" in cmd:  # the NVENC probe
            return subprocess.CompletedProcess(cmd, 1, b"", b"Driver does not support")
        if any("print_format=json" in str(c) for c in cmd):
            stats = {"input_i": "-20.1", "input_tp": "-3.0", "input_lra": "5.0",
                     "input_thresh": "-30.5", "target_offset": "0.1"}
            return subprocess.CompletedProcess(cmd, 0, "", "noise\n" + json.dumps(stats))
        self.encodes.append(cmd)
        (Path(kw["cwd"]) / cmd[-1]).write_bytes(b"\0")
        return subprocess.CompletedProcess(cmd, 0, "", "")


GOOD = {"width": 1080, "height": 1920, "fps": 60.0, "duration": 22.0, "lufs": -13.9,
        "silences": 0, "black": 0, "frozen": 0, "band_bars": []}
STILL = {"planner": lambda edl, src: follow.static(edl["layout"])}  # window in the middle


def heard(edl_words):
    return lambda video: [{"w": w["w"], "s": w["s"] + 0.03} for w in edl_words]


def test_render_through_the_cli_lands_in_ready(kept, monkeypatch, capsys):
    fake = FakeFfmpeg()
    monkeypatch.setattr(render.subprocess, "run", fake)
    render.video_encoder.cache_clear()
    shifted = [{"w": w["w"], "s": round(w["s"] - 8.0, 2)} for w in WORDS]
    assert run(["render", "1", "--style", "a"], kept, measurer=lambda v: GOOD,
               listener=heard(shifted), **STILL) == 0
    ready = config.data_dir() / "ready" / "m1-f1"
    assert (ready / "m1-f1.mp4").exists() and (ready / "edl.json").exists()
    edl = json.loads((ready / "edl.json").read_text(encoding="utf-8"))
    assert edl["words"][0] == {"w": "Ready", "s": 2.0, "e": 2.4}  # file time minus in_s
    assert (edl["in_s"], edl["out_s"], edl["source"]["vod_start_s"]) == (8.0, 30.0, 1228.0)
    ass = (config.data_dir() / "renders" / "m1-f1" / "edl.ass").read_text(encoding="utf-8")
    assert "WrapStyle: 0" in ass  # the hook ran off both edges with wrapping off
    assert "Hook,,0,0,0,,{\\fad(0,250)}He thought flying a jet" in ass
    assert "twitch.tv/ohnePixel" in ass
    (cmd,) = fake.encodes
    assert "libx264" in cmd and "h264_nvenc" not in cmd  # driver 560 cannot open NVENC
    graph = cmd[cmd.index("-filter_complex") + 1]
    # owner 2026-11-19: the gameplay fills the band; a still window sits in the middle of
    # the 1360x1080 gameplay rect, without a sendcmd script
    assert "crop@follow=w=912:h=1080:x=784:y=0,scale=1080:1280" in graph
    assert "sendcmd" not in graph
    assert "blur" not in graph  # owner 2026-11-19: no blur in the band, not even on the cam
    assert "READY" in capsys.readouterr().out
    render.video_encoder.cache_clear()


@pytest.mark.parametrize("bad, reason", [
    ({"silences": 1}, "silence over 2 s"),
    ({"lufs": -18.0}, "loudness"),
    ({"height": 1080}, "size"),
])
def test_a_failed_check_keeps_the_video_out_of_ready(kept, monkeypatch, capsys, bad, reason):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    assert run(["render", "1", "--no-caption-check"], kept,
               measurer=lambda v: {**GOOD, **bad}, **STILL) == 1
    assert not (config.data_dir() / "ready" / "m1-f1").exists()
    assert reason in capsys.readouterr().out
    render.video_encoder.cache_clear()


def test_caption_drift_over_0_2_s_fails(kept, monkeypatch, capsys):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    late = [{"w": w["w"], "s": round(w["s"] - 8.0 + 0.5, 2)} for w in WORDS]
    assert run(["render", "1"], kept, measurer=lambda v: GOOD, listener=lambda v: late,
               **STILL) == 1
    assert "captions drift 0.5" in capsys.readouterr().out
    render.video_encoder.cache_clear()


def test_only_kept_moments_with_a_layout_render(kept):
    with kept:
        kept.execute("UPDATE moments SET status = 'reject' WHERE id = 1")
    with pytest.raises(UsageError, match="only kept moments"):
        run(["render", "1", "--no-caption-check"], kept, **STILL)


def test_captions_run_two_to_four_words_and_drop_fillers():
    ws = [{"w": w, "s": i * 0.3, "e": i * 0.3 + 0.25} for i, w in
          enumerate("um so what does that even mean? uh okay".split())]
    lines = render.chunk(render.caption_words(ws))
    assert [[w["w"] for w in line] for line in lines] == [
        ["so", "what", "does", "that"], ["even", "mean?"], ["okay"]]
