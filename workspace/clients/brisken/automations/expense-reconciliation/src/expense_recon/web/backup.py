"""A copy of the ledger, off the machine (backlog item 119).

Every month, every mailed receipt and the learned memory live on ONE disk
in Frankfurt, under a personal hosting account, with five days of platform
snapshots and nothing else. A deleted month is gone after five days; a lost
disk takes the ten-year receipt archive with it; nobody has ever restored
one. This module is the copy Brisken itself holds.

What it does: zip the whole data folder and put it in a SharePoint folder
Brisken owns, through the app-only Graph credential the estate already has
(`rule_brisken_graph_first`, the same client-credentials path
`graph_notify` mints its token from). No mailbox is touched; this is the
drive API.

Three ways to run it:

  * `expense-recon backup --dry-run` says what it would upload and how big
    it is, reading nothing but the volume. The default, because uploading
    is the part that changes something.
  * `expense-recon backup --check` resolves the target and lists the
    folder. Read-only Graph, so it answers "would the upload land?"
    without writing anything.
  * `expense-recon backup --go`, or the in-app scheduler
    (`EXPENSE_RECON_BACKUP=1`, off by default), which is one daemon
    thread on the same pattern as the boot sweeps.

Deliberate shapes:

  * Live SQLite files are copied through SQLite's own backup API, not read
    off the disk. A byte copy of a database being written to is a torn
    file that restores as "database disk image is malformed", which is the
    worst possible failure for a backup: it looks like a backup until the
    day it is needed.
  * A folder bigger than the size ceiling REFUSES rather than uploading
    part of it. The data folder is about 95 MB today; a jump past the
    ceiling means something is wrong (or the ceiling needs raising on
    purpose), and half a ledger is not a backup.
  * Missing credentials, a missing target and an oversized folder are all
    plain refusals with a reason, never an exception into a boot thread.

The restore side is `docs/backup-and-restore.md`. No restore has been
rehearsed yet: that needs a throwaway app and the owner's go-ahead.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import graph_notify

log = logging.getLogger("expense_recon.backup")

GRAPH = "https://graph.microsoft.com/v1.0"
# The ceiling is a tripwire, not a budget: past it, look before uploading.
# Measured sizes: ~95 MB 2026-09-17, 144.0 MB 2026-09-21 (586 files; runs
# 87 MB, inbound 60 MB). The folder is ALREADY over this default, so the
# scheduler refuses every round until EXPENSE_RECON_BACKUP_MAX_BYTES is
# raised on purpose. That is the tripwire working, and it is also why
# turning the backup on is not just EXPENSE_RECON_BACKUP=1.
DEFAULT_MAX_BYTES = 100 * 1024 * 1024
DEFAULT_FOLDER = "Expense Reconciliation Backups"
DEFAULT_INTERVAL_HOURS = 24
# Graph wants upload-session chunks in multiples of 320 KiB.
CHUNK_BYTES = 8 * 320 * 1024 * 4   # 10 MiB
SIMPLE_UPLOAD_MAX = 4 * 1024 * 1024
# Never copy a half-written file or a previous archive into the archive.
SKIP_SUFFIXES = (".tmp", ".part", ".zip")
SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


@dataclass(frozen=True)
class BackupConfig:
    """Where the copy goes and how often, all from the environment so the
    hosted app and the CLI cannot disagree about the target."""

    site: str = ""            # "brisken.sharepoint.com:/sites/MARKETING"
    folder: str = DEFAULT_FOLDER
    enabled: bool = False
    interval_hours: float = DEFAULT_INTERVAL_HOURS
    max_bytes: int = DEFAULT_MAX_BYTES

    @classmethod
    def from_env(cls) -> "BackupConfig":
        def _num(key: str, default: float) -> float:
            try:
                v = float(os.environ.get(key, "") or default)
                return v if v > 0 else default
            except (TypeError, ValueError):
                return default

        return cls(
            site=(os.environ.get("EXPENSE_RECON_BACKUP_SITE", "") or "").strip(),
            folder=(
                os.environ.get("EXPENSE_RECON_BACKUP_FOLDER", "")
                or DEFAULT_FOLDER
            ).strip().strip("/"),
            enabled=os.environ.get("EXPENSE_RECON_BACKUP") == "1",
            interval_hours=_num(
                "EXPENSE_RECON_BACKUP_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS
            ),
            max_bytes=int(_num("EXPENSE_RECON_BACKUP_MAX_BYTES",
                               DEFAULT_MAX_BYTES)),
        )


# --------------------------------------------------------------- planning --

def _collect(data_root: Path) -> list[tuple[Path, int]]:
    """Every file the copy would carry, as (path relative to the data
    root, size). Sorted, so a plan reads the same twice."""
    root = Path(data_root)
    out: list[tuple[Path, int]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(SKIP_SUFFIXES):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        out.append((path.relative_to(root), size))
    return out


def archive_name(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"expense-recon-data-{stamp}.zip"


def plan(data_root: Path, cfg: BackupConfig | None = None) -> dict:
    """What the copy would carry, without reading a credential or the
    network. This is what `--dry-run` prints."""
    cfg = cfg or BackupConfig.from_env()
    files = _collect(data_root)
    total = sum(size for _, size in files)
    by_folder: dict[str, int] = {}
    for rel, size in files:
        top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        by_folder[top] = by_folder.get(top, 0) + size
    return {
        "data_root": str(Path(data_root).resolve()),
        "n_files": len(files),
        "total_bytes": total,
        "by_folder": dict(sorted(
            by_folder.items(), key=lambda kv: kv[1], reverse=True
        )),
        "files": [str(rel).replace("\\", "/") for rel, _ in files],
        "archive_name": archive_name(),
        "target": f"{cfg.site}/{cfg.folder}" if cfg.site else "",
        "max_bytes": cfg.max_bytes,
        "over_limit": total > cfg.max_bytes,
        "credentials": graph_notify.enabled(),
    }


# -------------------------------------------------------------- archiving --

def _snapshot_sqlite(src: Path, dest: Path) -> bool:
    """A consistent copy of a live database, through SQLite's own backup
    API. False when the file is not a database we can read, in which case
    the caller falls back to the bytes on disk."""
    try:
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        target = sqlite3.connect(str(dest))
        try:
            source.backup(target)
        finally:
            target.close()
    except sqlite3.Error:
        return False
    finally:
        source.close()
    return True


def build_archive(data_root: Path, dest: Path) -> dict:
    """Zip the data folder into `dest` (which must NOT live inside the
    data folder). Returns {n_files, bytes, sqlite_snapshots}."""
    root = Path(data_root)
    files = _collect(root)
    snapshots = 0
    with tempfile.TemporaryDirectory() as staging:
        stage = Path(staging)
        with zipfile.ZipFile(
            dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6,
        ) as zf:
            for rel, _size in files:
                src = root / rel
                arc = str(rel).replace("\\", "/")
                if src.suffix.lower() in SQLITE_SUFFIXES:
                    copy = stage / (arc.replace("/", "__"))
                    if _snapshot_sqlite(src, copy):
                        zf.write(copy, arcname=arc)
                        snapshots += 1
                        continue
                try:
                    zf.write(src, arcname=arc)
                except OSError:
                    log.warning("backup skipped unreadable file %s", arc)
    return {
        "n_files": len(files),
        "bytes": dest.stat().st_size,
        "sqlite_snapshots": snapshots,
    }


# ------------------------------------------------------------ the transport --

class GraphDrive:
    """The SharePoint document library the copy lands in.

    App-only Graph, the sanctioned credential path
    (`rule_brisken_graph_first`); no mailbox is involved. Nothing here
    logs a token or a secret."""

    def __init__(self, site: str, folder: str) -> None:
        self.site = site
        self.folder = folder.strip("/")
        self._drive_id: str | None = None

    # -- plumbing ---------------------------------------------------------
    def _token(self) -> str | None:
        return graph_notify._get_token()

    def _request(self, method: str, url: str, *, data: bytes | None = None,
                 headers: dict | None = None) -> tuple[int, bytes]:
        token = self._token()
        if not token:
            raise BackupError("could not mint a Graph token")
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Authorization": f"Bearer {token}", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            # The body carries Graph's own reason; a token never appears in
            # it, and the request headers are not echoed.
            raise BackupError(
                f"graph {method} answered {exc.code}: "
                f"{exc.read()[:400].decode('utf-8', 'replace')}"
            ) from None
        except (urllib.error.URLError, OSError) as exc:
            raise BackupError(f"graph {method} failed: {exc}") from None

    def _json(self, method: str, url: str, **kw) -> dict:
        _status, body = self._request(method, url, **kw)
        try:
            return json.loads(body or b"{}")
        except ValueError:
            raise BackupError("graph answered something that is not JSON") \
                from None

    # -- the two things this module needs ---------------------------------
    def drive_id(self) -> str:
        if self._drive_id:
            return self._drive_id
        site = self._json("GET", f"{GRAPH}/sites/{self.site}")
        site_id = site.get("id")
        if not site_id:
            raise BackupError(f"no SharePoint site at {self.site!r}")
        drive = self._json("GET", f"{GRAPH}/sites/{site_id}/drive")
        drive_id = drive.get("id")
        if not drive_id:
            raise BackupError("the site has no default document library")
        self._drive_id = str(drive_id)
        return self._drive_id

    def list_folder(self) -> list[dict]:
        """Read-only probe: what is in the backup folder today. An absent
        folder answers [] rather than raising, because "the folder is not
        there yet" is a normal first run, not a failure."""
        path = urllib.parse.quote(self.folder)
        try:
            body = self._json(
                "GET",
                f"{GRAPH}/drives/{self.drive_id()}/root:/{path}:/children"
                "?$select=name,size,lastModifiedDateTime&$top=50",
            )
        except BackupError as exc:
            if "answered 404" in str(exc):
                return []
            raise
        return [
            {
                "name": item.get("name", ""),
                "size": item.get("size", 0),
                "modified": item.get("lastModifiedDateTime", ""),
            }
            for item in body.get("value", [])
        ]

    def ensure_folder(self) -> None:
        """Create the backup folder when it is not there yet.

        Graph refuses an upload whose parent folder does not exist, and a
        first run by definition has none. Each segment is created with
        `conflictBehavior: fail`, so an existing folder answers 409 and is
        left exactly as it is; nothing here can replace a folder."""
        parent = ""
        for segment in [s for s in self.folder.split("/") if s]:
            if parent:
                url = (f"{GRAPH}/drives/{self.drive_id()}/root:/"
                       f"{urllib.parse.quote(parent)}:/children")
            else:
                url = f"{GRAPH}/drives/{self.drive_id()}/root/children"
            try:
                self._json("POST", url, data=json.dumps({
                    "name": segment, "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                }).encode(), headers={"Content-Type": "application/json"})
            except BackupError as exc:
                if "answered 409" not in str(exc):
                    raise
            parent = f"{parent}/{segment}".strip("/")

    def upload(self, local: Path, name: str) -> dict:
        self.ensure_folder()
        size = local.stat().st_size
        path = urllib.parse.quote(f"{self.folder}/{name}")
        base = f"{GRAPH}/drives/{self.drive_id()}/root:/{path}"
        if size <= SIMPLE_UPLOAD_MAX:
            item = self._json(
                "PUT", f"{base}:/content", data=local.read_bytes(),
                headers={"Content-Type": "application/zip"},
            )
            return {"name": item.get("name", name), "size": size}
        session = self._json(
            "POST", f"{base}:/createUploadSession",
            data=json.dumps({
                "item": {"@microsoft.graph.conflictBehavior": "replace"},
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        url = session.get("uploadUrl")
        if not url:
            raise BackupError("graph gave no upload URL")
        with local.open("rb") as fh:
            sent = 0
            while sent < size:
                chunk = fh.read(CHUNK_BYTES)
                if not chunk:
                    break
                end = sent + len(chunk) - 1
                # The session URL carries its own credential; sending the
                # app token alongside it is refused by Graph.
                req = urllib.request.Request(
                    url, data=chunk, method="PUT",
                    headers={
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {sent}-{end}/{size}",
                    },
                )
                try:
                    with urllib.request.urlopen(req, timeout=300):
                        pass
                except urllib.error.HTTPError as exc:
                    raise BackupError(
                        f"upload chunk {sent}-{end} answered {exc.code}"
                    ) from None
                except (urllib.error.URLError, OSError) as exc:
                    raise BackupError(f"upload chunk failed: {exc}") from None
                sent = end + 1
        return {"name": name, "size": size}


class BackupError(RuntimeError):
    """A refusal with a reason a human can act on."""


# ----------------------------------------------------------------- running --

def check_target(cfg: BackupConfig | None = None, drive=None) -> dict:
    """Read-only: can we reach the target, and what is already there?
    Writes nothing, so it is safe to run against the live tenant."""
    cfg = cfg or BackupConfig.from_env()
    if not cfg.site:
        return {"ok": False, "reason":
                "no SharePoint target configured (EXPENSE_RECON_BACKUP_SITE)"}
    if drive is None:
        if not graph_notify.enabled():
            return {"ok": False, "reason":
                    "graph credentials are not configured"}
        drive = GraphDrive(cfg.site, cfg.folder)
    try:
        items = drive.list_folder()
    except BackupError as exc:
        return {"ok": False, "reason": str(exc)}
    return {
        "ok": True,
        "target": f"{cfg.site}/{cfg.folder}",
        "n_existing": len(items),
        "existing": items,
    }


def run_backup(data_root: Path, cfg: BackupConfig | None = None, *,
               dry_run: bool = False, drive=None) -> dict:
    """Take one copy. Never raises: every refusal comes back as
    ``{"ok": False, "reason": ...}`` so a scheduler thread cannot die of
    a missing credential."""
    cfg = cfg or BackupConfig.from_env()
    planned = plan(data_root, cfg)
    if planned["over_limit"]:
        return {
            "ok": False,
            "reason": (
                f"the data folder is {planned['total_bytes']} bytes, over the "
                f"{cfg.max_bytes}-byte ceiling; raise "
                "EXPENSE_RECON_BACKUP_MAX_BYTES on purpose or look at what "
                "grew"
            ),
            **planned,
        }
    if dry_run:
        return {"ok": True, "dry_run": True, "uploaded": False, **planned}
    if not cfg.site:
        return {"ok": False, "reason":
                "no SharePoint target configured (EXPENSE_RECON_BACKUP_SITE)",
                **planned}
    if drive is None:
        if not graph_notify.enabled():
            return {"ok": False, "reason":
                    "graph credentials are not configured", **planned}
        drive = GraphDrive(cfg.site, cfg.folder)
    name = planned["archive_name"]
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / name
        built = build_archive(data_root, local)
        try:
            uploaded = drive.upload(local, name)
        except BackupError as exc:
            return {"ok": False, "reason": str(exc), **planned, **built}
    log.info("backup uploaded %s (%d bytes)", name, built["bytes"])
    return {
        "ok": True, "uploaded": True, "archive_name": name,
        "archive_bytes": built["bytes"],
        "sqlite_snapshots": built["sqlite_snapshots"],
        "n_files": built["n_files"],
        "target": f"{cfg.site}/{cfg.folder}",
        "remote": uploaded,
    }


def start_backup_thread(data_root: Path, cfg: BackupConfig | None = None):
    """The in-app schedule. Returns None unless EXPENSE_RECON_BACKUP=1, so
    the default is off and a deploy changes nothing until the owner turns
    it on. One daemon thread, the same shape as the boot sweeps; a failed
    round logs and waits for the next one."""
    cfg = cfg or BackupConfig.from_env()
    if not cfg.enabled:
        return None

    def _loop() -> None:
        interval = max(60.0, cfg.interval_hours * 3600.0)
        while True:
            try:
                result = run_backup(data_root, cfg)
                if not result.get("ok"):
                    log.warning("scheduled backup skipped: %s",
                                result.get("reason"))
            except Exception:  # noqa: BLE001 - a backup never kills the app
                log.exception("scheduled backup failed")
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True,
                              name="expense-recon-backup")
    thread.start()
    log.info("backup scheduler on, every %s h", cfg.interval_hours)
    return thread


# --------------------------------------------------------------------- CLI --

def _human(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon backup",
        description=(
            "Copy the data folder to Brisken's SharePoint. Dry run by "
            "default; --go is the only form that uploads."
        ),
    )
    parser.add_argument(
        "--data", type=Path,
        default=Path(os.environ.get("EXPENSE_RECON_WEB_DATA",
                                    "recon-web-data")),
        help="the data folder to copy (default: EXPENSE_RECON_WEB_DATA)",
    )
    parser.add_argument("--go", action="store_true",
                        help="actually upload the copy")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what would be uploaded (the default)")
    parser.add_argument(
        "--check", action="store_true",
        help="resolve the target and list the folder; read-only Graph",
    )
    args = parser.parse_args(argv)
    cfg = BackupConfig.from_env()

    if args.check:
        result = check_target(cfg)
        if not result.get("ok"):
            print(f"cannot reach the target: {result['reason']}")
            return 1
        print(f"target {result['target']}: {result['n_existing']} file(s)")
        for item in result["existing"][:10]:
            print(f"  {item['modified']}  {_human(item['size']):>10}  "
                  f"{item['name']}")
        return 0

    result = run_backup(args.data, cfg, dry_run=not args.go)
    if not result.get("ok"):
        print(f"backup refused: {result['reason']}")
        return 1
    if result.get("dry_run"):
        print(f"would upload {result['n_files']} file(s), "
              f"{_human(result['total_bytes'])} before compression")
        for folder, size in result["by_folder"].items():
            print(f"  {folder:<24} {_human(size):>10}")
        print(f"  as {result['archive_name']}")
        print(f"  to {result['target'] or '(no target configured)'}")
        print("  credentials: "
              + ("present" if result["credentials"] else "MISSING"))
        return 0
    print(f"uploaded {result['archive_name']} "
          f"({_human(result['archive_bytes'])}, {result['n_files']} files, "
          f"{result['sqlite_snapshots']} database snapshot(s)) "
          f"to {result['target']}")
    return 0
