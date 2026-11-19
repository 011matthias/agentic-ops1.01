"""The gameplay window that fills the band and follows the main object (owner 2026-11-19)."""

from __future__ import annotations

import json
import subprocess

import pytest

from clipengine import config, follow, produce, render

from test_produce import GOOD, FakeFfmpeg, make_kept, run

JET = [700, 560, 1400, 780]   # a 700 px jet, centre 1050: the centre line runs through it


@pytest.fixture
def kept(con, env, monkeypatch):
    return make_kept(con, env, monkeypatch)


def test_window_is_the_band_aspect_at_full_height():
    assert follow.window(None) == (912, 1080, 0, 1920)
    assert follow.window([560, 0, 1360, 1080]) == (912, 1080, 560, 1920)


def test_a_box_through_the_centre_line_is_mirrored_and_the_window_stays_centred():
    # m5 at 24 s: the box held one wing (528-1203), the jet spans 540-1380
    plan = follow.plan_path([[528, 562, 1203, 747]] * 8)
    assert set(plan["x"]) == {504}            # (1920 - 912) / 2: the jet's right wing stays in
    assert plan["x"][0] + 912 >= 1380


def test_an_object_off_the_centre_line_pulls_the_window_and_stays_inside():
    boxes = [[1500 + 10 * i, 500, 1800 + 10 * i, 700] for i in range(12)]
    plan = follow.plan_path(boxes)
    assert follow.misses(plan) == []
    assert plan["x"][-1] == 1008              # clamped to the frame edge (1920 - 912)


def test_the_path_is_smooth_where_the_box_jitters():
    boxes = [[700 + (40 if i % 2 else 0), 560, 1300 + (40 if i % 2 else 0), 780]
             for i in range(20)]
    xs = follow.plan_path(boxes)["x"]
    assert max(abs(a - b) for a, b in zip(xs, xs[1:])) <= 20


def test_an_object_wider_than_the_window_is_flagged_not_cut_silently():
    plan = follow.plan_path([[300, 500, 1400, 700]] * 4)
    assert plan["too_wide"] == [True] * 4
    assert all(m["too_wide"] for m in follow.misses(plan))


def test_a_brief_other_object_does_not_take_the_camera():
    jet = {"box": JET, "score": 0.8, "cls": "airplane"}
    fighter = {"box": [100, 300, 400, 420], "score": 0.93, "cls": "airplane"}
    # the player's jet hides behind a tower for two samples, a smaller AI jet stays visible
    dets = [[jet], [jet], [fighter], [fighter], [jet], [jet]]
    assert follow.track(dets) == [JET, JET, None, None, JET, JET]


def test_a_new_main_object_takes_over_when_it_is_big_and_seen_twice():
    car = {"box": [800, 600, 1300, 900], "score": 0.9, "cls": "car"}
    other = {"box": [100, 200, 900, 500], "score": 0.9, "cls": "truck"}
    boxes = follow.track([[car], [car], [other], [other], [other]])
    assert boxes[:3] == [car["box"], car["box"], None] and boxes[3] == other["box"]


def test_a_one_sample_box_that_swallowed_a_building_is_despiked():
    wide = [600, 560, 1700, 780]
    assert follow.despike([JET, wide, JET])[1] == JET
    assert follow.despike([None, wide, None]) == [None, None, None]  # unconfirmed


def test_sendcmd_writes_one_position_per_change_of_x():
    plan = {"x": [100, 100, 140], "sample_fps": 4}
    script = follow.sendcmd(plan, duration=0.5, fps=8)
    lines = script.strip().splitlines()
    assert lines[0] == "0.0000 crop@follow x 100;"
    assert lines[-1].endswith("crop@follow x 140;") and len(lines) == 3


# --- through the CLI: the real planner over a faked detector ---------------------------

def fake_frames(n):
    def frames(src, a, b, *, blank=None):
        frames.blank = blank
        for i in range(n):
            yield i / 4, None
    return frames


def test_render_plans_the_window_from_the_detector_and_feeds_the_crop(kept, monkeypatch, capsys):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    frames = fake_frames(88)  # 22 s at 4 fps
    monkeypatch.setattr(follow, "sample_frames", frames)
    # the car drives from the right edge towards the middle
    seen = iter(range(88))
    monkeypatch.setattr(follow, "yolox_detector", lambda model: lambda frame: [
        {"box": [1600 - 6 * (i := next(seen)), 600, 1880 - 6 * i, 800], "score": 0.9,
         "cls": "car"}])
    assert run(["render", "1", "--no-caption-check"], kept,
               measurer=lambda v: GOOD) == 0
    work = config.data_dir() / "renders" / "m1-f1"
    edl = json.loads((work / "edl.json").read_text(encoding="utf-8"))
    assert edl["follow"]["crop_w"] == 912 and follow.misses(edl["follow"]) == []
    assert frames.blank == follow.cam_region(edl["layout"]["facecam"])  # own cam blanked
    cmd = (work / "follow.cmd").read_text(encoding="utf-8").splitlines()
    xs = [int(line.split()[-1].rstrip(";")) for line in cmd]
    assert xs[0] == 1008 and xs[-1] < xs[0]   # starts at the right edge, follows left
    out = capsys.readouterr().out
    assert "follows the main object: seen in 88/88 samples" in out and "READY" in out
    render.video_encoder.cache_clear()


def test_the_band_is_filled_no_blurred_fill_behind_it(kept, monkeypatch):
    fake = FakeFfmpeg()
    monkeypatch.setattr(render.subprocess, "run", fake)
    render.video_encoder.cache_clear()
    plan = follow.plan_path([JET] * 88)
    assert run(["render", "1", "--no-caption-check"], kept, measurer=lambda v: GOOD,
               planner=lambda edl, src: {**plan, "crop_h": 1080, "y": 0}) == 0
    (cmd,) = fake.encodes
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "sendcmd=f=follow.cmd,crop@follow=w=912:h=1080" in graph
    assert "scale=1080:1280" in graph and "[bg]" not in graph and "eq=brightness" not in graph
    render.video_encoder.cache_clear()


def test_a_window_that_loses_the_main_object_fails_the_check(kept, monkeypatch, capsys):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    full = {"crop_w": 912, "crop_h": 1080, "y": 0, "sample_fps": 4,
            "x": [1008] * 4, "boxes": [JET] * 4, "too_wide": [False] * 4}
    assert run(["render", "1", "--no-caption-check"], kept, measurer=lambda v: GOOD,
               planner=lambda edl, src: full) == 1
    assert not (config.data_dir() / "ready" / "m1-f1").exists()
    assert "main object not completely in the window at 4 samples" in capsys.readouterr().out
    render.video_encoder.cache_clear()


def test_an_object_at_the_rect_edge_passes_with_a_written_reason(kept, monkeypatch):
    # owner 2026-11-19, KaiCenat m30: further left the band would show his cam and chat
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    full = {"crop_w": 912, "crop_h": 1080, "y": 0, "sample_fps": 4,
            "x": [1008] * 4, "boxes": [JET] * 4, "too_wide": [False] * 4}
    why = "Jason at the left edge of the rect, cam and chat beyond it (owner)"
    assert run(["render", "1", "--no-caption-check", "--accept-edge", why], kept,
               measurer=lambda v: GOOD, planner=lambda edl, src: full) == 0
    check = json.loads((config.data_dir() / "ready" / "m1-f1" / "check.json").read_text(
        encoding="utf-8"))
    assert check["measured"]["edge_accepted"] == why and len(check["measured"]["edge_s"]) == 4
    render.video_encoder.cache_clear()


def test_an_object_wider_than_the_window_keeps_the_band_filled_and_passes(kept, monkeypatch,
                                                                         capsys):
    # owner 2026-11-19 (seaplane stills): keep the band filled, cut the object's edges
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    full = {"crop_w": 912, "crop_h": 1080, "y": 0, "sample_fps": 4, "x": [400] * 4,
            "boxes": [[300, 500, 1400, 700]] * 4, "too_wide": [True] * 4}
    assert run(["render", "1", "--no-caption-check"], kept, measurer=lambda v: GOOD,
               planner=lambda edl, src: full) == 0
    assert "wider than the window at 4 samples, band kept filled" in capsys.readouterr().out
    check = json.loads((config.data_dir() / "ready" / "m1-f1" / "check.json")
                       .read_text(encoding="utf-8"))
    assert check["measured"]["object_wider_s"] == [0.0, 0.25, 0.5, 0.75]
    render.video_encoder.cache_clear()


def test_bars_in_the_band_fail_the_check(kept, monkeypatch, capsys):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    plan = follow.plan_path([JET] * 88)
    assert run(["render", "1", "--no-caption-check"], kept,
               measurer=lambda v: {**GOOD, "band_bars": ["top", "bottom"]},
               planner=lambda edl, src: {**plan, "crop_h": 1080, "y": 0}) == 1
    assert "bars in the gameplay band (top, bottom)" in capsys.readouterr().out
    render.video_encoder.cache_clear()


def test_a_framed_cam_is_cut_inside_its_frame(kept, monkeypatch):
    # caseoh_ 2026-11-19: a 4:3 cam frame; growing it to 1080:640 took in gameplay beside it
    monkeypatch.setattr("clipengine.produce.load_layouts", lambda path: {"ohnepixel": {
        "facecam": [0, 134, 402, 302], "cam_crop": [0, 182, 402, 238],
        "gameplay": [0, 0, 1920, 1080]}})
    fake = FakeFfmpeg()
    monkeypatch.setattr(render.subprocess, "run", fake)
    render.video_encoder.cache_clear()
    assert run(["render", "1", "--no-caption-check"], kept, measurer=lambda v: GOOD,
               planner=lambda edl, src: follow.static(edl["layout"])) == 0
    (cmd,) = fake.encodes
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[a]crop=402:238:0:182,scale=1080:640" in graph       # top band: inside the frame
    assert "blur" not in graph   # owner 2026-11-19: "unten den blur weg"
    render.video_encoder.cache_clear()


# --- the bar measurement itself, on synthetic band frames ------------------------------

def band_frames(np, *, bars: bool, n: int = 10):
    """n frames of the band at quarter size: textured, or with flat strips top and bottom
    (the old fit layout: a sharp 16:9 picture between two blurred strips)."""
    rng = np.random.default_rng(1)
    h, w = render.GAME_H // 4, render.W // 4
    frames = rng.integers(40, 200, size=(n, h, w), dtype=np.uint8)
    if bars:
        frames[:, :84] = 90
        frames[:, -84:] = 70
    return frames.tobytes()


@pytest.mark.parametrize("bars, want", [(True, ["top", "bottom"]), (False, [])])
def test_band_bars_finds_flat_strips_only(monkeypatch, bars, want):
    np = pytest.importorskip("numpy")
    raw = band_frames(np, bars=bars)
    monkeypatch.setattr(produce.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, raw, b""))
    assert produce.band_bars(produce.band_frames("video.mp4")) == want


# --- black, paused and menu stretches inside the band (stage 6) -------------------------

def stretch_frames(np, middle: str, *, n_mid: int = 4):
    """4 samples of moving gameplay, n_mid samples of `middle`, 4 more of gameplay, at the
    band's quarter size. A paused frame repeats the last gameplay sample exactly."""
    rng = np.random.default_rng(2)
    h, w = render.GAME_H // 4, render.W // 4
    play = [rng.integers(40, 200, size=(h, w)) for _ in range(8)]
    mid = {
        "black": lambda i: np.zeros((h, w)),
        "paused": lambda i: play[3],
        "menu": lambda i: np.full((h, w), 100 + 2 * i),       # bright, smooth, slow
        "night": lambda i: rng.integers(0, 40, size=(h, w)),  # dark, but a picture
    }[middle]
    frames = play[:4] + [mid(i) for i in range(n_mid)] + play[4:]
    return np.array(frames, dtype=np.float32)


@pytest.mark.parametrize("middle, want", [
    ("black", [{"kind": "dark", "t": 1.0, "s": 1.0}]),
    ("paused", [{"kind": "frozen", "t": 1.0, "s": 1.0}]),
    ("menu", [{"kind": "menu", "t": 1.25, "s": 0.75}]),  # its first sample still changed a lot
    ("night", []),
])
def test_band_stretches_find_black_paused_and_menu_but_not_night(middle, want):
    np = pytest.importorskip("numpy")
    assert produce.band_stretches(stretch_frames(np, middle)) == want


def test_a_flash_under_half_a_second_passes():
    # m15-f1 at 8.4 s: the camera crossed a bush, 0.45 s of black; 2 samples at 4 fps
    np = pytest.importorskip("numpy")
    assert produce.band_stretches(stretch_frames(np, "black", n_mid=2)) == []


def test_changing_captions_do_not_hide_a_paused_map():
    np = pytest.importorskip("numpy")
    frames = stretch_frames(np, "paused")
    for i in range(4, 8):  # the word highlight moves over the paused picture
        frames[i, produce.CAPTION_ROWS] = 30 * i
    assert produce.band_stretches(frames) == [{"kind": "frozen", "t": 1.0, "s": 1.0}]


class MeasuringFfmpeg(FakeFfmpeg):
    """FakeFfmpeg for the render, plus the three reads of measure(): ffprobe, the
    loudness / blackdetect pass over the whole frame, and the band's raw frames."""

    def __init__(self, band: bytes):
        super().__init__()
        self.band = band

    def __call__(self, cmd, **kw):
        if cmd[0] == "ffprobe":
            return subprocess.CompletedProcess(cmd, 0, json.dumps({
                "streams": [{"width": 1080, "height": 1920, "avg_frame_rate": "60/1"}],
                "format": {"duration": "22.0"}}), "")
        if "rawvideo" in cmd:
            return subprocess.CompletedProcess(cmd, 0, self.band, b"")
        if any("ebur128" in str(c) for c in cmd):  # whole-frame checks: the bright
            # facecam band hides the black gameplay band from blackdetect
            return subprocess.CompletedProcess(cmd, 0, "", "I: -14.0 LUFS\n")
        return super().__call__(cmd, **kw)


def test_a_black_stretch_in_the_band_keeps_the_render_out_of_ready(kept, monkeypatch, capsys):
    np = pytest.importorskip("numpy")
    band = stretch_frames(np, "black").astype(np.uint8).tobytes()
    monkeypatch.setattr(render.subprocess, "run", MeasuringFfmpeg(band))
    render.video_encoder.cache_clear()
    assert run(["render", "1", "--no-caption-check"], kept,
               planner=lambda edl, src: follow.static(edl["layout"])) == 1
    assert "black in the gameplay band at t=1.0 s for 1.0 s" in capsys.readouterr().out
    assert not (config.data_dir() / "ready" / "m1-f1").exists()
    check = json.loads((config.data_dir() / "renders" / "m1-f1" / "check.json")
                       .read_text(encoding="utf-8"))
    assert check["measured"]["band_stretches"] == [{"kind": "dark", "t": 1.0, "s": 1.0}]
    render.video_encoder.cache_clear()


def test_a_menu_stretch_in_the_band_fails_through_the_cli(kept, monkeypatch, capsys):
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    menu = [{"kind": "menu", "t": 34.5, "s": 0.75}]  # m5-f1's weapon wheel, measured
    assert run(["render", "1", "--no-caption-check"], kept,
               measurer=lambda v: {**GOOD, "band_stretches": menu},
               planner=lambda edl, src: follow.static(edl["layout"])) == 1
    assert "menu over the game in the gameplay band at t=34.5 s" in capsys.readouterr().out
    render.video_encoder.cache_clear()


def test_an_accepted_menu_passes_with_its_reason_on_record(kept, monkeypatch, capsys):
    # owner 2026-11-19: a menu that is part of the joke may pass, per video, with a reason
    monkeypatch.setattr(render.subprocess, "run", FakeFfmpeg())
    render.video_encoder.cache_clear()
    menu = [{"kind": "frozen", "t": 21.0, "s": 3.0}]
    assert run(["render", "1", "--no-caption-check", "--accept-band", "respray shop is the setup"],
               kept, measurer=lambda v: {**GOOD, "band_stretches": menu},
               planner=lambda edl, src: follow.static(edl["layout"])) == 0
    assert "1 band stretch(es) accepted: respray shop is the setup" in capsys.readouterr().out
    check = json.loads((config.data_dir() / "ready" / "m1-f1" / "check.json")
                       .read_text(encoding="utf-8"))
    assert check["measured"]["band_accepted"] == "respray shop is the setup"
    assert check["measured"]["band_stretches"] == menu
    render.video_encoder.cache_clear()
