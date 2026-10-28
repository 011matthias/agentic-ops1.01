"""Backlog item 122: the mailbox keeps taking receipts, and says how full
the disk is.

Before this round the intake refused EVERY message once the 1 GB volume
was half full (a flat 500 MiB floor), free space appeared nowhere, an
unrecognised sender could mail 25 MB two hundred times a day, and our own
people were held to 40 files a day, which a month-end backfill exceeds.

Everything here drives the real callers: the SMTP handler's `handle_DATA`
for the guards, `GET /healthz` over HTTP for the disk block, and the boot
sweep for the dismissed purge. `shutil.disk_usage` is the one thing
faked, because a test cannot conjure a 5 GB volume; both volume sizes the
live estate can have (1 GB today, 5 GB after the owner's extend) are
covered by the same code with no constant in between.
"""
from __future__ import annotations

import asyncio
import json
from email.message import EmailMessage
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web import intake_mail  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    DEFAULT_SENDER_DAILY_CAP,
    MIN_FREE_DISK_FLOOR_BYTES,
    STATUS_DISMISSED,
    DayBudget,
    IntakeConfig,
    disk_snapshot,
    free_disk_floor,
    normalize_intake_setting,
    read_log,
    sweep_dismissed,
)
from expense_recon.web.smtp_server import IntakeHandler  # noqa: E402

DOMAIN = "expenses.brisken.com"
INSIDE = "dirk.neumann@brisken.com"
OUTSIDE = "guest@example.org"
JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000  # big enough to not read as a logo

GB = 1024 * 1024 * 1024
MB = 1024 * 1024

# The two volume sizes this app actually runs on: the live 1 GB and the
# 5 GB the owner's `flyctl volumes extend` produces.
VOLUME_1GB = 1 * GB
VOLUME_5GB = 5 * GB


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _mail(
    from_addr: str,
    to_addr: str = f"receipts@{DOMAIN}",
    attachments: list[tuple[str, bytes]] | None = None,
    body: str = "receipt attached",
    subject: str = "July taxi",
) -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = "<test@brisken.com>"
    msg.set_content(body)
    for name, data in attachments or []:
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf") else ("image", "jpeg")
        )
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=name
        )
    return msg.as_bytes()


def _fake_volume(monkeypatch, total: int, free: int) -> None:
    """Pretend /data lives on a volume of this size with this much free.

    Patched on the intake module rather than on `shutil` globally, so the
    rest of the suite (and the app's own file writes) are untouched."""
    monkeypatch.setattr(
        intake_mail.shutil, "disk_usage",
        lambda path: SimpleNamespace(
            total=total, used=total - free, free=free,
        ),
    )


def _settings(client, **intake) -> None:
    """Write intake settings the way the operator does: through the real
    PUT route, so the validation edge is exercised too."""
    resp = client.put("/api/settings", json={"intake": intake})
    assert resp.status_code == 200, resp.text


def _deliver(client, monkeypatch, raw: bytes, mail_from: str,
             rcpt: str = f"receipts@{DOMAIN}", budget: DayBudget | None = None
             ) -> str:
    """Drive the SMTP handler's acceptance path and return its reply line.

    Routing is stubbed: everything under test happens BEFORE the 250."""
    from expense_recon.web import smtp_server as ss

    def fake_route(self, arch, parsed):  # noqa: ARG001 - signature match
        ss.end_route()

    monkeypatch.setattr(IntakeHandler, "_route", fake_route)
    monkeypatch.setattr(ss, "DAY_BUDGET", budget or DayBudget())
    state = client.app.state
    handler = IntakeHandler(state.db_path, state.learning_db_path,
                            state.data_root)
    envelope = SimpleNamespace(content=raw, rcpt_tos=[rcpt],
                               mail_from=mail_from)
    session = SimpleNamespace(peer=("203.0.113.9", 51000))
    return asyncio.run(handler.handle_DATA(None, session, envelope))


# ------------------------------------------------- the floor, both sizes --

def test_floor_is_200mb_on_a_1gb_volume_not_half_the_disk():
    """The live volume. The old flat 500 MiB was 51% of it, so refusals
    would have started at about 474 MB used."""
    floor = free_disk_floor(VOLUME_1GB)
    assert floor == MIN_FREE_DISK_FLOOR_BYTES == 200 * MB
    assert floor < 500 * MB  # the constant this item removed
    # Usable space roughly doubles: 800 MB rather than 500 MB.
    assert VOLUME_1GB - floor > 800 * MB


def test_floor_grows_with_a_5gb_volume():
    """After the owner's extend the same code asks for more headroom,
    because the floor is a share of the disk and nothing is written down
    per volume size."""
    floor = free_disk_floor(VOLUME_5GB)
    assert floor == int(VOLUME_5GB * intake_mail.MIN_FREE_DISK_FRACTION)
    assert floor > free_disk_floor(VOLUME_1GB)
    assert VOLUME_5GB - floor > 4 * GB


def test_floor_never_takes_more_than_half_a_small_volume():
    """A 100 MB volume must not refuse mail from empty just because the
    fixed floor is bigger than the disk."""
    assert free_disk_floor(100 * MB) == 50 * MB
    assert free_disk_floor(0) == 0


@pytest.mark.parametrize("total", [VOLUME_1GB, VOLUME_5GB])
def test_mail_is_accepted_where_the_old_flat_floor_refused(
    client, monkeypatch, total
):
    """450 MB free: the old 500 MiB floor turned this away on both volume
    sizes. It is a normal, healthy disk on either."""
    _fake_volume(monkeypatch, total=total, free=450 * MB)
    reply = _deliver(
        client, monkeypatch,
        _mail(INSIDE, attachments=[("taxi.jpg", JPG)]), INSIDE,
    )
    assert reply.startswith("250"), reply


@pytest.mark.parametrize(
    "total,free",
    [(VOLUME_1GB, 100 * MB), (VOLUME_5GB, 200 * MB)],
)
def test_mail_is_still_refused_under_the_floor(client, monkeypatch, total, free):
    """The guard is not gone, only moved: under the floor the listener
    still answers a temporary error, so the sender's own MTA retries."""
    _fake_volume(monkeypatch, total=total, free=free)
    reply = _deliver(
        client, monkeypatch,
        _mail(INSIDE, attachments=[("taxi.jpg", JPG)]), INSIDE,
    )
    assert reply.startswith("452"), reply
    assert "storage low" in reply


def test_an_unreadable_volume_never_refuses_mail(client, monkeypatch):
    """A failed measurement must not bounce receipts (the posture this
    guard has always had)."""
    def boom(path):
        raise OSError("no such volume")

    monkeypatch.setattr(intake_mail.shutil, "disk_usage", boom)
    assert disk_snapshot(client._data_root) == {"available": False}
    reply = _deliver(
        client, monkeypatch,
        _mail(INSIDE, attachments=[("taxi.jpg", JPG)]), INSIDE,
    )
    assert reply.startswith("250"), reply


# ------------------------------------------------- free space on /healthz --

def test_healthz_reports_free_space_and_the_floor(client, monkeypatch):
    _fake_volume(monkeypatch, total=VOLUME_1GB, free=768 * MB)
    body = client.get("/healthz").json()
    assert body["status"] == "ok"           # unchanged, still the only field
    disk = body["disk"]
    assert disk["available"] is True
    assert disk["total_bytes"] == VOLUME_1GB
    assert disk["free_bytes"] == 768 * MB
    assert disk["used_bytes"] == VOLUME_1GB - 768 * MB
    assert disk["free_pct"] == 75.0
    assert disk["floor_bytes"] == 200 * MB
    assert disk["intake_refusing"] is False


def test_healthz_says_when_the_mailbox_is_refusing(client, monkeypatch):
    """The point of putting it here: a monitor can see the refusal that
    used to announce itself only as bounced receipts."""
    _fake_volume(monkeypatch, total=VOLUME_1GB, free=100 * MB)
    disk = client.get("/healthz").json()["disk"]
    assert disk["intake_refusing"] is True
    assert disk["free_pct"] < 10


def test_healthz_disk_on_a_real_volume(client):
    """No fake: the block is readable on whatever disk the test runs on,
    so the route cannot pass only against a mock."""
    disk = client.get("/healthz").json()["disk"]
    assert disk["available"] is True
    assert disk["total_bytes"] > 0
    assert 0 <= disk["free_pct"] <= 100
    assert disk["floor_bytes"] <= disk["total_bytes"] // 2


# --------------------------------------- an unknown sender's size budget --

def test_a_strangers_big_message_is_refused_permanently(client, monkeypatch):
    big = _mail(OUTSIDE, attachments=[("dump.jpg", b"\xff\xd8" + b"x" * (6 * MB))])
    assert len(big) > 5 * MB
    reply = _deliver(client, monkeypatch, big, OUTSIDE)
    assert reply.startswith("552"), reply
    assert "unrecognised sender" in reply
    # Refused before custody: nothing was written to the volume.
    assert read_log(client._data_root) == []


def test_our_own_people_may_still_mail_a_big_receipt(client, monkeypatch):
    """The cap is about strangers. A scanned invoice from inside the
    tenant is exactly the mail this must not touch."""
    big = _mail(INSIDE, attachments=[("scan.jpg", b"\xff\xd8" + b"x" * (6 * MB))])
    reply = _deliver(client, monkeypatch, big, INSIDE)
    assert reply.startswith("250"), reply


def test_a_listed_private_address_counts_as_our_own(client, monkeypatch):
    """`intake.known_senders` is the operator's own list of the private
    addresses our people mail from; it decides the limits too."""
    private = "dirk_.neumann@icloud.com"
    _settings(client, known_senders=[private])
    big = _mail(private, attachments=[("scan.jpg", b"\xff\xd8" + b"x" * (6 * MB))])
    assert _deliver(client, monkeypatch, big, private).startswith("250")


def test_strangers_share_a_daily_byte_budget(client, monkeypatch):
    """One afternoon of junk can no longer reach the disk floor. The
    budget is global across unrecognised senders on purpose: From is
    forgeable, so a per-sender one is walked past by rotating it."""
    payload = [("r.jpg", b"\xff\xd8" + b"x" * (1 * MB))]
    # Budget sized from the real message: two fit, the third does not.
    # (A MIME message is bigger than its attachment; the guard counts the
    # bytes that actually land on the volume, so the test does too.)
    size = len(_mail(OUTSIDE, attachments=payload))
    _settings(client, unknown_daily_bytes=size * 2 + 1024)
    budget = DayBudget()
    first = _deliver(client, monkeypatch, _mail(OUTSIDE, attachments=payload),
                     OUTSIDE, budget=budget)
    assert first.startswith("250"), first
    # A different stranger, and the same budget: rotating the From buys
    # nothing.
    other = "stranger@example.net"
    second = _deliver(client, monkeypatch, _mail(other, attachments=payload),
                      other, budget=budget)
    assert second.startswith("250"), second
    third = _deliver(client, monkeypatch, _mail(other, attachments=payload),
                     other, budget=budget)
    assert third.startswith("452"), third
    assert "daily submission limit" in third
    # And our own people are unaffected by a budget strangers exhausted.
    inside = _deliver(client, monkeypatch, _mail(INSIDE, attachments=payload),
                      INSIDE, budget=budget)
    assert inside.startswith("250"), inside


def test_the_byte_budget_survives_a_restart(client, monkeypatch):
    """A fresh process re-seeds today's unknown-sender bytes from the
    acceptance log, so a restart is not a refill."""
    payload = [("r.jpg", b"\xff\xd8" + b"x" * (1 * MB))]
    size = len(_mail(OUTSIDE, attachments=payload))
    _settings(client, unknown_daily_bytes=size * 2 + 1024)
    for _ in range(2):
        assert _deliver(
            client, monkeypatch, _mail(OUTSIDE, attachments=payload), OUTSIDE,
            budget=DayBudget(),   # a new process each time
        ).startswith("250")
    rows = read_log(client._data_root)
    assert [r["known_sender"] for r in rows] == [False, False]
    assert all(r["n_bytes"] >= 1 * MB for r in rows)
    # The third message meets a budget that remembers the first two.
    assert _deliver(
        client, monkeypatch, _mail(OUTSIDE, attachments=payload), OUTSIDE,
        budget=DayBudget(),
    ).startswith("452")


def test_only_strangers_bytes_are_charged_when_seeding(client, monkeypatch):
    """The budget bounds what STRANGERS spend. A big scan from one of our
    own people, and a row written before this round (which carries
    neither field), must not eat a stranger's allowance after a restart:
    charging them would bounce real receipts, which is the failure this
    item exists to remove."""
    payload = [("r.jpg", b"\xff\xd8" + b"x" * (1 * MB))]
    size = len(_mail(OUTSIDE, attachments=payload))
    _settings(client, unknown_daily_bytes=size + 1024)  # room for one
    now = intake_mail._now_iso()
    intake_mail._append_log(client._data_root, {
        "at": now, "from": INSIDE, "subject": "a big scan", "n_files": 1,
        "n_bytes": size * 5, "known_sender": True, "status": "ingested",
        "archive": "known",
    })
    intake_mail._append_log(client._data_root, {
        "at": now, "from": "someone@example.com", "subject": "old",
        "n_files": 1, "status": "ingested", "archive": "legacy",
    })
    reply = _deliver(
        client, monkeypatch, _mail(OUTSIDE, attachments=payload), OUTSIDE,
        budget=DayBudget(),   # a fresh process, seeding from that log
    )
    assert reply.startswith("250"), reply


# ------------------------------------ our own people and the 40-file cap --

def test_a_known_sender_passes_the_per_sender_file_cap(tmp_path):
    """A month-end backfill from Criss or Dirk exceeds 40 files. The cap
    was never a security boundary (From is forgeable); the global cap is
    what bounds a day's vision spend, and it still binds everyone."""
    budget = DayBudget()
    cfg = IntakeConfig(global_daily_cap=500)
    assert budget.reserve(
        tmp_path, INSIDE, DEFAULT_SENDER_DAILY_CAP + 20, cfg, known=True,
    ) is True
    # The same message from a stranger: still capped.
    assert budget.reserve(
        tmp_path, OUTSIDE, DEFAULT_SENDER_DAILY_CAP + 20, cfg, known=False,
    ) is False


def test_a_month_end_backfill_from_inside_lands_over_the_cap(
    client, monkeypatch
):
    """The same rule through the real caller: today's log already shows
    this sender at the 40-file cap, and their next mail still lands."""
    now = intake_mail._now_iso()
    intake_mail._append_log(client._data_root, {
        "at": now, "from": INSIDE, "subject": "backfill so far",
        "n_files": DEFAULT_SENDER_DAILY_CAP, "n_bytes": 1000,
        "known_sender": True, "status": "ingested", "archive": "earlier",
    })
    intake_mail._append_log(client._data_root, {
        "at": now, "from": OUTSIDE, "subject": "a busy stranger",
        "n_files": DEFAULT_SENDER_DAILY_CAP, "n_bytes": 1000,
        "known_sender": False, "status": "ingested", "archive": "earlier2",
    })
    inside = _deliver(
        client, monkeypatch, _mail(INSIDE, attachments=[("41.jpg", JPG)]),
        INSIDE, budget=DayBudget(),
    )
    assert inside.startswith("250"), inside
    # A stranger at the same count is still capped: the bypass follows
    # who we recognise, not the cap disappearing.
    outside = _deliver(
        client, monkeypatch, _mail(OUTSIDE, attachments=[("41.jpg", JPG)]),
        OUTSIDE, budget=DayBudget(),
    )
    assert outside.startswith("452"), outside


def test_the_global_file_cap_still_binds_our_own_people(tmp_path):
    budget = DayBudget()
    cfg = IntakeConfig(global_daily_cap=10)
    assert budget.reserve(tmp_path, INSIDE, 9, cfg, known=True) is True
    assert budget.reserve(tmp_path, INSIDE, 5, cfg, known=True) is False


def test_a_refused_message_consumes_no_budget(tmp_path):
    """All-or-nothing: a message refused on bytes must not have spent
    file units on the way out."""
    budget = DayBudget()
    cfg = IntakeConfig(unknown_daily_bytes=1 * MB, global_daily_cap=10)
    assert budget.reserve(
        tmp_path, OUTSIDE, 3, cfg, known=False, n_bytes=2 * MB,
    ) is False
    assert budget.reserve(
        tmp_path, OUTSIDE, 3, cfg, known=False, n_bytes=0,
    ) is True


# --------------------------------------------- the dismissed-mail purge --

def _dismissed_archive(client, monkeypatch, age_days: int) -> str:
    """One archive in the terminal `dismissed` state, dismissed `age_days`
    ago."""
    from datetime import datetime, timedelta, timezone

    _deliver(client, monkeypatch, _mail(INSIDE, attachments=[("r.jpg", JPG)]),
             INSIDE)
    arch = max(
        (p for p in intake_mail.inbound_root(client._data_root).iterdir()
         if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
    )
    when = datetime.now(timezone.utc) - timedelta(days=age_days)
    intake_mail._update_meta(arch, {
        "status": STATUS_DISMISSED, "dismissed_at": when.isoformat(),
    })
    return arch.name


def test_the_purge_is_off_by_default(client, monkeypatch):
    """Deleting Brisken's mail is the owner's call, so the sweep ships
    inert and one settings write turns it on."""
    name = _dismissed_archive(client, monkeypatch, age_days=400)
    assert IntakeConfig.from_settings({}).dismissed_purge_days == 0
    assert sweep_dismissed(client.app.state.db_path, client._data_root) == 0
    assert (intake_mail.inbound_root(client._data_root) / name).exists()


def test_the_purge_deletes_long_dismissed_archives_when_turned_on(
    client, monkeypatch
):
    old = _dismissed_archive(client, monkeypatch, age_days=120)
    _settings(client, dismissed_purge_days=90)
    assert sweep_dismissed(client.app.state.db_path, client._data_root) == 1
    assert not (intake_mail.inbound_root(client._data_root) / old).exists()


def test_the_purge_leaves_a_recent_dismissal_and_live_mail(client, monkeypatch):
    """The grace period is for the mis-click, and a purge must never
    touch mail that is not dismissed."""
    recent = _dismissed_archive(client, monkeypatch, age_days=3)
    _deliver(client, monkeypatch, _mail(INSIDE, attachments=[("b.jpg", JPG)]),
             INSIDE)
    _settings(client, dismissed_purge_days=90)
    assert sweep_dismissed(client.app.state.db_path, client._data_root) == 0
    assert (intake_mail.inbound_root(client._data_root) / recent).exists()
    archives = [
        p for p in intake_mail.inbound_root(client._data_root).iterdir()
        if p.is_dir()
    ]
    assert len(archives) == 2


def test_the_purge_runs_at_boot(client, monkeypatch, tmp_path):
    """Where it actually fires: the same startup path that already runs
    the retention sweep, so a scale-to-zero machine purges without anyone
    calling anything."""
    old = _dismissed_archive(client, monkeypatch, age_days=120)
    _settings(client, dismissed_purge_days=90)
    assert (intake_mail.inbound_root(client._data_root) / old).exists()
    with TestClient(create_app(client._data_root)):   # a restart
        pass
    assert not (intake_mail.inbound_root(client._data_root) / old).exists()


# ----------------------------------------------------- the settings edge --

def test_settings_accept_the_new_limits_and_refuse_nonsense():
    cleaned = normalize_intake_setting({
        "unknown_max_message_bytes": 2 * MB,
        "unknown_daily_bytes": 30 * MB,
        "dismissed_purge_days": 90,
    })
    assert cleaned["unknown_max_message_bytes"] == 2 * MB
    assert cleaned["unknown_daily_bytes"] == 30 * MB
    assert cleaned["dismissed_purge_days"] == 90
    # 0 is legal for the purge (never) and not for a byte cap.
    assert normalize_intake_setting({"dismissed_purge_days": 0})[
        "dismissed_purge_days"] == 0
    with pytest.raises(ValueError):
        normalize_intake_setting({"dismissed_purge_days": -1})
    with pytest.raises(ValueError):
        normalize_intake_setting({"unknown_daily_bytes": 0})


def test_the_limits_round_trip_through_the_settings_route(client):
    resp = client.put("/api/settings", json={"intake": {
        "unknown_max_message_bytes": 3 * MB,
        "unknown_daily_bytes": 20 * MB,
        "dismissed_purge_days": 45,
    }})
    assert resp.status_code == 200, resp.text
    stored = client.get("/api/settings").json()["intake"]
    assert stored["unknown_max_message_bytes"] == 3 * MB
    assert stored["unknown_daily_bytes"] == 20 * MB
    assert stored["dismissed_purge_days"] == 45
    cfg = IntakeConfig.from_settings({"intake": stored})
    assert cfg.unknown_max_message_bytes == 3 * MB
    assert cfg.dismissed_purge_days == 45


def test_a_hand_edited_blob_never_takes_the_mailbox_down():
    """Same drop-don't-raise posture the other intake keys carry."""
    cfg = IntakeConfig.from_settings({"intake": {
        "unknown_daily_bytes": "lots", "dismissed_purge_days": "soon",
    }})
    assert cfg.unknown_daily_bytes == intake_mail.DEFAULT_UNKNOWN_DAILY_BYTES
    assert cfg.dismissed_purge_days == 0


def test_json_of_the_healthz_block_is_serializable(client):
    """The block crosses the wire; a stray Path or float('inf') would
    only show up here."""
    json.dumps(disk_snapshot(client._data_root))
