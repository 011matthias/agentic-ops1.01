"""p2 publish through the CLI: fixed slots, YouTube publishAt, the TikTok folder, no doubles."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from clipengine import cli, config
from clipengine.cli import UsageError

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)  # 16:00 German time, a Friday
CHANNEL = "UCtest"


def run(argv, con, **inject):
    args = cli.build_parser().parse_args(argv)
    return cli.COMMANDS[args.command](args, con, **inject)


def make_ready(vid, *, title="KaiCenat runs from the cops in GTA 6", category="chaos"):
    folder = config.data_dir() / "ready" / vid
    folder.mkdir(parents=True)
    (folder / f"{vid}.mp4").write_bytes(b"\0" * 64)
    (folder / "edl.json").write_text(json.dumps({"id": vid, "title": title, "category": category,
                                                 "display_name": "KaiCenat"}), encoding="utf-8")


class FakeYouTube:
    """Data API stand-in: uploads land in a store that videos() reads back."""

    def __init__(self, channel=CHANNEL, keep_publish_at=True):
        self.channel, self.keep = channel, keep_publish_at
        self.uploads: list[tuple[str, dict]] = []
        self.store: dict[str, dict] = {}

    def channel_id(self):
        return self.channel

    def upload(self, video, body):
        rid = f"yt{len(self.uploads) + 1}"
        self.uploads.append((video.name, body))
        status = {k: v for k, v in body["status"].items() if self.keep or k != "publishAt"}
        self.store[rid] = {"id": rid, "status": status,
                           "snippet": {**body["snippet"], "channelId": self.channel}}
        return rid

    def videos(self, ids):
        return [self.store[i] for i in ids if i in self.store]


@pytest.fixture
def pub(con, tmp_path, monkeypatch):
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID", CHANNEL)
    monkeypatch.setenv("CLIPENGINE_TIKTOK_DIR", str(tmp_path / "tiktok"))
    return con


def test_a_dry_run_plans_the_next_free_slots_and_touches_nothing(pub, tmp_path, capsys):
    make_ready("m1-f1")
    make_ready("m2-f1")
    yt = FakeYouTube()
    assert run(["publish", "m1-f1", "m2-f1"], pub, youtube=yt, now=NOW) == 0
    out = capsys.readouterr().out
    assert "m1-f1: Fri 2026-11-20 20:00 German time (2026-11-20T19:00:00Z)" in out
    assert "m2-f1: Sat 2026-11-21 00:00 German time (2026-11-20T23:00:00Z)" in out
    assert "dry run" in out
    assert yt.uploads == [] and not (tmp_path / "tiktok").exists()


def test_go_schedules_youtube_and_drops_the_same_slot_into_the_tiktok_folder(pub, tmp_path,
                                                                             capsys):
    make_ready("m1-f1", category="fail")
    yt = FakeYouTube()
    assert run(["publish", "m1-f1", "--go"], pub, youtube=yt, now=NOW) == 0
    ((name, body),) = yt.uploads
    assert name == "m1-f1.mp4"
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == "2026-11-20T19:00:00Z"
    text = "KaiCenat runs from the cops in GTA 6\n\n#gta6 #kaicenat #gta6fails #gta6clips"
    assert body["snippet"]["description"] == text  # owner 2026-11-19: no Twitch link
    drop = tmp_path / "tiktok"
    assert (drop / "2026-11-20 20-00 m1-f1.mp4").stat().st_size == 64
    assert text in (drop / "2026-11-20 20-00 m1-f1.txt").read_text(encoding="utf-8")
    rows = pub.execute("SELECT platform, remote_id, slot_utc FROM posts ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [
        ("youtube", "yt1", "2026-11-20T19:00:00Z"),
        ("tiktok", "2026-11-20 20-00 m1-f1.mp4", "2026-11-20T19:00:00Z")]
    assert "scheduled m1-f1 for 2026-11-20 20:00" in capsys.readouterr().out


def test_a_video_goes_up_once_and_its_slot_stays_booked(pub, capsys):
    make_ready("m1-f1")
    make_ready("m2-f1")
    yt = FakeYouTube()
    run(["publish", "m1-f1", "--go"], pub, youtube=yt, now=NOW)
    with pytest.raises(UsageError, match="m1-f1 is already on YouTube \\(yt1\\)"):
        run(["publish", "m1-f1", "--go"], pub, youtube=yt, now=NOW)
    capsys.readouterr()
    assert run(["publish", "m2-f1"], pub, youtube=yt, now=NOW) == 0
    assert "m2-f1: Sat 2026-11-21 00:00" in capsys.readouterr().out
    assert len(yt.uploads) == 1


def test_uploads_made_before_this_command_count_as_posted(pub):
    # 2026-11-19: the first six went up through a one-off script that kept publish/youtube.json
    make_ready("m1-f1")
    ledger = config.data_dir() / "publish" / "youtube.json"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(json.dumps({"m1-f1": {"video_id": "old", "title": "t"}}),
                      encoding="utf-8")
    with pytest.raises(UsageError, match="already on YouTube \\(old\\)"):
        run(["publish", "m1-f1", "--go"], pub, youtube=FakeYouTube(), now=NOW)


def test_a_token_for_another_channel_uploads_nothing(pub):
    make_ready("m1-f1")
    yt = FakeYouTube(channel="UCother")
    with pytest.raises(UsageError, match="not the configured channel"):
        run(["publish", "m1-f1", "--go"], pub, youtube=yt, now=NOW)
    assert yt.uploads == []
    assert pub.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0


@pytest.mark.parametrize("argv, now, said", [
    (["--slot", "2026-11-20 21:00"], NOW, "not a fixed slot"),
    (["--slot", "2026-11-20 02:00"], NOW, "less than"),          # already past
    (["--slot", "2026-11-20 20:00"],                             # 10 minutes away
     datetime(2026, 11, 20, 18, 50, tzinfo=timezone.utc), "less than"),
])
def test_a_slot_off_the_grid_or_too_close_is_refused(pub, argv, now, said):
    make_ready("m1-f1")
    with pytest.raises(UsageError, match=said):
        run(["publish", "m1-f1", *argv], pub, youtube=FakeYouTube(), now=now)


def test_a_slot_too_close_to_process_moves_to_the_next_one(pub, capsys):
    make_ready("m1-f1")
    late = datetime(2026, 11, 20, 18, 50, tzinfo=timezone.utc)  # 19:50 German time
    assert run(["publish", "m1-f1"], pub, youtube=FakeYouTube(), now=late) == 0
    assert "m1-f1: Sat 2026-11-21 00:00" in capsys.readouterr().out


def test_a_title_without_the_streamer_is_refused(pub):
    make_ready("m1-f1", title="Someone runs from the cops in GTA 6")
    with pytest.raises(UsageError, match="does not name KaiCenat"):
        run(["publish", "m1-f1"], pub, youtube=FakeYouTube(), now=NOW)


def test_a_read_back_without_the_slot_fails_the_run(pub, capsys):
    yt = FakeYouTube(keep_publish_at=False)
    make_ready("m1-f1")
    assert run(["publish", "m1-f1", "--go"], pub, youtube=yt, now=NOW) == 1
    assert "expected private / 2026-11-20T19:00:00Z" in capsys.readouterr().out
