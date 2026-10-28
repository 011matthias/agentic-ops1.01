"""The all-months card roll-up, kept while nothing it reads has changed.

Owner, 2026-09-25: the months card strip lags the rest of the page, and the
owner chose "memo + warm-up": keep the finished `GET /api/cards/status`
body in memory while nothing it reads has changed, and rebuild it in the
background once edits go quiet, so the strip is ready before it is asked for.

The roll-up builds every month's Expenses page, so it reads nearly the whole
data folder: the web store, the learning store (remembered cards) and the
chart / provisioning files beside them, plus the card presets file when one
is configured. The key is therefore the whole folder, read cheaply:

- each SQLite file's own file change counter (header bytes 24-27), which
  SQLite increments on every committed write in rollback-journal mode, from
  any connection or process. A database in WAL mode does not keep it per
  commit, so a WAL database turns the memo off rather than risk a stale
  answer.
- every other top-level file's name, mtime and size (journal files are
  transient and left out).
- the calendar day, so nothing dated can outlive its day.

A write anywhere in the folder is a new key, including writes that change
nothing the roll-up shows (a job's progress, a login): those cost a rebuild,
never a wrong answer. The key is read BEFORE the build, so a body built
across a write sits under a key that is already out of date; it is also
dropped then, since the key after the build no longer matches (the rule
#1397 set for the account index). Reading the key after the build instead
would pair pre-write data with the post-write key, the one failure here.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date
from pathlib import Path
from typing import Callable

log = logging.getLogger("expense_recon.card_status_memo")

# Transient companions of a SQLite file; their coming and going is not data.
_TRANSIENT_SUFFIXES = ("-journal", "-wal", "-shm")


class _Uncacheable(Exception):
    """The folder is in a state the key cannot describe exactly."""


def _sqlite_counter(path: Path) -> tuple:
    with open(path, "rb") as f:
        head = f.read(100)
    if len(head) < 28:
        # A database no write has reached yet.
        return ("empty", len(head))
    if head[18] == 2 or head[19] == 2:
        raise _Uncacheable(f"{path.name} is in WAL mode")
    return ("counter", int.from_bytes(head[24:28], "big"))


def data_version(data_root: Path, extra_files: tuple[Path, ...] = ()) -> tuple | None:
    """The key for everything the roll-up reads, or None when it cannot be
    stated exactly (then nothing is kept)."""
    try:
        parts: list[tuple] = [("day", date.today().isoformat())]
        for entry in sorted(os.scandir(data_root), key=lambda e: e.name):
            if not entry.is_file() or entry.name.endswith(_TRANSIENT_SUFFIXES):
                continue
            path = Path(entry.path)
            if entry.name.endswith(".sqlite"):
                parts.append((entry.name, *_sqlite_counter(path)))
            else:
                st = entry.stat()
                parts.append((entry.name, st.st_mtime_ns, st.st_size))
        for path in extra_files:
            try:
                st = path.stat()
                parts.append((str(path), st.st_mtime_ns, st.st_size))
            except FileNotFoundError:
                parts.append((str(path), "absent"))
        return tuple(parts)
    except (_Uncacheable, OSError) as exc:
        log.debug("card status memo off for this read: %s", exc)
        return None


class CardStatusMemo:
    """One response body, reused while `version()` is unchanged.

    Builds are serialized: requests that arrive while one is building wait
    for it and then read its body, instead of each building their own on the
    one machine."""

    def __init__(self, version: Callable[[], tuple | None], build: Callable[[], bytes]):
        self.version = version
        self._build = build
        self._lock = threading.Lock()
        self._build_lock = threading.Lock()
        self._key: tuple | None = None
        self._body: bytes | None = None
        self.builds = 0

    def holds(self, key: tuple | None) -> bool:
        with self._lock:
            return key is not None and self._key == key

    def _hit(self, key: tuple | None) -> bytes | None:
        with self._lock:
            if key is not None and self._key == key:
                return self._body
        return None

    def get(self) -> bytes:
        hit = self._hit(self.version())
        if hit is not None:
            return hit
        with self._build_lock:
            key = self.version()
            hit = self._hit(key)
            if hit is not None:
                return hit
            body = self._build()
            self.builds += 1
            if key is not None and self.version() == key:
                with self._lock:
                    self._key, self._body = key, body
            return body


class CardStatusWarmer:
    """Rebuilds the memo once the folder has been quiet for `quiet_s`.

    Polls the key every `poll_s`: a write resets the quiet clock, and a key
    that has held for `quiet_s` without a body is built. A job writing
    progress keeps the folder busy, so nothing is rebuilt under a running
    job; the day rolling over is a new key, so the first open of a day is
    warm too."""

    def __init__(self, memo: CardStatusMemo, *, quiet_s: float = 20.0,
                 poll_s: float = 5.0, enabled: Callable[[], bool] = lambda: True):
        self.memo = memo
        self.quiet_s = quiet_s
        self.poll_s = poll_s
        self.enabled = enabled
        self._last_key: object = object()
        self._changed_at = 0.0

    def step(self, now: float) -> bool:
        """One poll; True when it built."""
        if not self.enabled():
            return False
        key = self.memo.version()
        if key != self._last_key:
            self._last_key, self._changed_at = key, now
            return False
        if key is None or now - self._changed_at < self.quiet_s or self.memo.holds(key):
            return False
        self.memo.get()
        return True

    def start(self) -> threading.Thread:
        def loop() -> None:
            while True:
                time.sleep(self.poll_s)
                try:
                    self.step(time.monotonic())
                except Exception:  # noqa: BLE001 - a warm-up never takes the app down
                    log.warning("card status warm-up failed", exc_info=True)

        thread = threading.Thread(target=loop, name="card-status-warmer", daemon=True)
        thread.start()
        return thread
