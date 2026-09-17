"""Backlog item 119: a copy of the ledger leaves the machine.

Everything the tool holds lives on one 1 GB disk in Frankfurt with five
days of platform snapshots and no copy Brisken controls. These tests drive
the real callers: the `expense-recon backup` CLI, `run_backup` as the
scheduler calls it, and the app's own boot path for the schedule being off.

Graph is never contacted. The transport is one object (`GraphDrive`) and
the tests pass a recording fake in its place, so the archive, the refusals
and the upload call are all exercised without a credential or a socket.
The live read-only probe (`--check`) is a separate, manual act.
"""
from __future__ import annotations

import sqlite3
import threading
import zipfile
from pathlib import Path

import pytest

from expense_recon.cli import main as cli_main
from expense_recon.web import backup as backup_mod
from expense_recon.web.backup import (
    BackupConfig,
    BackupError,
    GraphDrive,
    build_archive,
    check_target,
    plan,
    run_backup,
    start_backup_thread,
)

SITE = "brisken.sharepoint.com:/sites/MARKETING"


class FakeDrive:
    """Records what the real GraphDrive would have been asked to do."""

    def __init__(self, existing: list[dict] | None = None,
                 fail: str | None = None) -> None:
        self.existing = existing or []
        self.fail = fail
        self.uploads: list[tuple[str, int, bytes]] = []
        self.listed = 0

    def list_folder(self) -> list[dict]:
        if self.fail:
            raise BackupError(self.fail)
        self.listed += 1
        return self.existing

    def upload(self, local: Path, name: str) -> dict:
        if self.fail:
            raise BackupError(self.fail)
        payload = local.read_bytes()
        self.uploads.append((name, len(payload), payload))
        return {"name": name, "size": len(payload)}


@pytest.fixture
def data_root(tmp_path) -> Path:
    """A data folder shaped like the live one: a run database, learned
    memory, a month folder and a mailed-receipt archive."""
    root = tmp_path / "data"
    (root / "runs" / "july").mkdir(parents=True)
    (root / "inbound" / "20260917T101500-abcd1234").mkdir(parents=True)
    (root / "runs" / "july" / "statement.xlsx").write_bytes(b"x" * 2048)
    (root / "inbound" / "20260917T101500-abcd1234" / "message.eml").write_bytes(
        b"From: dirk.neumann@brisken.com\r\n\r\nreceipt\r\n"
    )
    (root / "feedback.jsonl").write_bytes(b'{"note": "1"}\n')
    for name in ("recon-web.sqlite", "learning.sqlite"):
        conn = sqlite3.connect(root / name)
        conn.execute("CREATE TABLE t (k TEXT, v TEXT)")
        conn.execute("INSERT INTO t VALUES ('vendor', 'Staples')")
        conn.commit()
        conn.close()
    # Leftovers a copy must not carry.
    (root / "recon-web.sqlite.tmp").write_bytes(b"half written")
    return root


@pytest.fixture(autouse=True)
def _no_credentials(monkeypatch):
    """No test may depend on a credential being present on the machine."""
    for key in ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
                "BRISKEN_GRAPH_CLIENT_SECRET"):
        monkeypatch.delenv(key, raising=False)
    for key in ("EXPENSE_RECON_BACKUP", "EXPENSE_RECON_BACKUP_SITE",
                "EXPENSE_RECON_BACKUP_FOLDER",
                "EXPENSE_RECON_BACKUP_INTERVAL_HOURS",
                "EXPENSE_RECON_BACKUP_MAX_BYTES"):
        monkeypatch.delenv(key, raising=False)


# ------------------------------------------------------------ the dry run --

def test_the_dry_run_lists_the_right_files_and_their_size(data_root):
    planned = plan(data_root, BackupConfig(site=SITE))
    assert set(planned["files"]) == {
        "feedback.jsonl",
        "inbound/20260917T101500-abcd1234/message.eml",
        "learning.sqlite",
        "recon-web.sqlite",
        "runs/july/statement.xlsx",
    }
    assert planned["n_files"] == 5
    # The half-written leftover is not part of a copy.
    assert "recon-web.sqlite.tmp" not in planned["files"]
    assert planned["total_bytes"] == sum(
        (data_root / f).stat().st_size for f in planned["files"]
    )
    assert planned["by_folder"]["runs"] == 2048
    assert planned["target"] == f"{SITE}/Expense Reconciliation Backups"
    assert planned["over_limit"] is False
    assert planned["credentials"] is False
    assert planned["archive_name"].startswith("expense-recon-data-")
    assert planned["archive_name"].endswith(".zip")


def test_the_dry_run_uploads_nothing(data_root):
    drive = FakeDrive()
    result = run_backup(data_root, BackupConfig(site=SITE), dry_run=True,
                        drive=drive)
    assert result["ok"] is True
    assert result["uploaded"] is False
    assert drive.uploads == []
    assert result["total_bytes"] > 0


def test_the_cli_defaults_to_a_dry_run(data_root, capsys):
    assert cli_main(["backup", "--data", str(data_root)]) == 0
    out = capsys.readouterr().out
    assert "would upload 5 file(s)" in out
    assert "credentials: MISSING" in out
    assert "(no target configured)" in out


def test_the_cli_dry_run_names_the_target_when_one_is_set(
    data_root, capsys, monkeypatch
):
    monkeypatch.setenv("EXPENSE_RECON_BACKUP_SITE", SITE)
    monkeypatch.setenv("EXPENSE_RECON_BACKUP_FOLDER", "Finance/Backups")
    assert cli_main(["backup", "--data", str(data_root)]) == 0
    out = capsys.readouterr().out
    assert f"to {SITE}/Finance/Backups" in out


# ------------------------------------------------------------- refusals --

def test_it_refuses_when_the_credential_is_missing(data_root):
    result = run_backup(data_root, BackupConfig(site=SITE))
    assert result["ok"] is False
    assert result["reason"] == "graph credentials are not configured"


def test_it_refuses_when_no_target_is_configured(data_root):
    result = run_backup(data_root, BackupConfig())
    assert result["ok"] is False
    assert "no SharePoint target configured" in result["reason"]


def test_it_refuses_a_folder_over_the_ceiling(data_root):
    """Half a ledger is not a backup: past the ceiling it stops and says
    how big the folder got."""
    cfg = BackupConfig(site=SITE, max_bytes=100)
    result = run_backup(data_root, cfg, drive=FakeDrive())
    assert result["ok"] is False
    assert "over the 100-byte ceiling" in result["reason"]
    # Even the dry run says it, before anything is built.
    assert run_backup(data_root, cfg, dry_run=True)["ok"] is False


def test_a_transport_failure_is_a_refusal_not_an_exception(data_root):
    result = run_backup(data_root, BackupConfig(site=SITE),
                        drive=FakeDrive(fail="graph PUT answered 403"))
    assert result["ok"] is False
    assert "403" in result["reason"]


def test_the_cli_reports_a_refusal_and_exits_nonzero(data_root, capsys,
                                                     monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_BACKUP_SITE", SITE)
    assert cli_main(["backup", "--data", str(data_root), "--go"]) == 1
    assert "backup refused: graph credentials are not configured" in \
        capsys.readouterr().out


# -------------------------------------------------------- the copy itself --

def test_the_upload_carries_every_file(data_root, tmp_path):
    drive = FakeDrive()
    result = run_backup(data_root, BackupConfig(site=SITE), drive=drive)
    assert result["ok"] is True and result["uploaded"] is True
    assert len(drive.uploads) == 1
    name, size, payload = drive.uploads[0]
    assert name == result["archive_name"] and size == result["archive_bytes"]
    out = tmp_path / "got.zip"
    out.write_bytes(payload)
    with zipfile.ZipFile(out) as zf:
        assert set(zf.namelist()) == {
            "feedback.jsonl",
            "inbound/20260917T101500-abcd1234/message.eml",
            "learning.sqlite",
            "recon-web.sqlite",
            "runs/july/statement.xlsx",
        }
        assert zf.read("feedback.jsonl") == b'{"note": "1"}\n'


def test_databases_are_copied_through_sqlite_not_off_the_disk(
    data_root, tmp_path
):
    """A byte copy of a database being written to restores as "disk image
    is malformed", which looks like a backup right up to the day it is
    needed. The copy is taken with a writer holding the database open."""
    live = sqlite3.connect(data_root / "recon-web.sqlite")
    live.execute("INSERT INTO t VALUES ('open', 'transaction')")
    live.commit()
    try:
        dest = tmp_path / "copy.zip"
        built = build_archive(data_root, dest)
    finally:
        live.close()
    assert built["sqlite_snapshots"] == 2
    restored = tmp_path / "restored"
    restored.mkdir()
    with zipfile.ZipFile(dest) as zf:
        zf.extractall(restored)
    conn = sqlite3.connect(restored / "recon-web.sqlite")
    rows = conn.execute("SELECT k, v FROM t ORDER BY k").fetchall()
    conn.close()
    assert ("vendor", "Staples") in rows
    assert ("open", "transaction") in rows


def test_the_archive_is_written_outside_the_data_folder(data_root, tmp_path):
    """A zip written INTO the folder it is zipping is the classic way to
    copy a copy; the run builds it in a temp dir and leaves nothing."""
    before = {p.name for p in data_root.iterdir()}
    run_backup(data_root, BackupConfig(site=SITE), drive=FakeDrive())
    assert {p.name for p in data_root.iterdir()} == before


# ----------------------------------------------------- the read-only probe --

def test_the_check_probe_only_reads(data_root):
    drive = FakeDrive(existing=[
        {"name": "expense-recon-data-20260916T030000Z.zip", "size": 1,
         "modified": "2026-09-16T03:00:00Z"},
    ])
    result = check_target(BackupConfig(site=SITE), drive=drive)
    assert result["ok"] is True
    assert result["n_existing"] == 1
    assert drive.listed == 1
    assert drive.uploads == []


def test_the_check_probe_refuses_without_a_credential():
    result = check_target(BackupConfig(site=SITE))
    assert result["ok"] is False
    assert result["reason"] == "graph credentials are not configured"


# ------------------------------------------- the transport, without Graph --

class _Recorder:
    """A GraphDrive with its one HTTP call replaced, so the request shapes
    are testable without a token or a socket."""

    def __init__(self, folder: str, conflicts: bool = False) -> None:
        self.drive = GraphDrive("brisken.sharepoint.com:/sites/X", folder)
        self.drive._drive_id = "drive-1"
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.conflicts = conflicts
        self.drive._request = self._request  # type: ignore[assignment]

    def _request(self, method, url, *, data=None, headers=None):
        self.calls.append((method, url, data))
        if self.conflicts and method == "POST" and "children" in url:
            raise BackupError("graph POST answered 409: nameAlreadyExists")
        return 200, b'{"id": "item-1", "name": "x"}'


def test_the_first_run_creates_the_backup_folder(tmp_path):
    """The folder does not exist on the live site yet, and Graph refuses
    an upload into a parent that is not there."""
    rec = _Recorder("Finance/Backups")
    local = tmp_path / "copy.zip"
    local.write_bytes(b"zip")
    rec.drive.upload(local, "copy.zip")
    creates = [c for c in rec.calls if c[0] == "POST"]
    assert len(creates) == 2                      # one per path segment
    assert b'"name": "Finance"' in creates[0][2]
    assert b'"name": "Backups"' in creates[1][2]
    assert b'"@microsoft.graph.conflictBehavior": "fail"' in creates[0][2]
    uploads = [c for c in rec.calls if c[0] == "PUT"]
    assert len(uploads) == 1
    assert uploads[0][1].endswith("root:/Finance/Backups/copy.zip:/content")
    assert uploads[0][2] == b"zip"


def test_an_existing_folder_is_left_alone(tmp_path):
    """A 409 means the folder is already there; that is not a failure and
    must never turn into a replace."""
    rec = _Recorder("Backups", conflicts=True)
    local = tmp_path / "copy.zip"
    local.write_bytes(b"zip")
    rec.drive.upload(local, "copy.zip")
    assert [c[0] for c in rec.calls] == ["POST", "PUT"]


# -------------------------------------------------------- the scheduler --

def test_the_scheduler_is_off_by_default(data_root):
    assert BackupConfig.from_env().enabled is False
    assert start_backup_thread(data_root) is None


def test_the_scheduler_starts_only_when_it_is_turned_on(data_root,
                                                        monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_BACKUP", "1")
    monkeypatch.setenv("EXPENSE_RECON_BACKUP_SITE", SITE)
    monkeypatch.setenv("EXPENSE_RECON_BACKUP_INTERVAL_HOURS", "6")
    cfg = BackupConfig.from_env()
    assert cfg.enabled is True and cfg.interval_hours == 6
    ran = threading.Event()
    calls: list[str] = []

    def _fake(root, c=None, **kw):
        calls.append(str(root))
        ran.set()
        return {"ok": True}

    monkeypatch.setattr(backup_mod, "run_backup", _fake)
    thread = start_backup_thread(data_root, cfg)
    assert thread is not None and thread.daemon is True
    assert ran.wait(timeout=5) is True   # the first round ran on its own
    assert calls == [str(data_root)]


def test_the_app_does_not_start_a_backup_by_default(tmp_path, monkeypatch):
    """Route-level: booting the app with the flag unset starts nothing."""
    pytest.importorskip("fastapi")
    from expense_recon.web.app import create_app

    monkeypatch.delenv("EXPENSE_RECON_BACKUP", raising=False)
    app = create_app(tmp_path)
    assert app.state.backup is None


def test_the_app_starts_the_backup_when_it_is_turned_on(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_BACKUP", "1")
    monkeypatch.setattr(backup_mod, "run_backup",
                        lambda root, c=None, **kw: {"ok": True})
    app = create_app(tmp_path)
    assert app.state.backup is not None
