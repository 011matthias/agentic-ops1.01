# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""safe-edit.py — Edit-with-retry wrapper for the Windows+IDE EBUSY class.

Why this exists
---------------
Register #81 (2026-05-11): a batch of 7 sequential Edit calls to a file the
user had open in VS Code ALL failed with EBUSY before the agent noticed.
Edit has no built-in retry. The fallback was a passive "queued for when the
file unlocks" message, which led to register #83 (passive-queue agent-
deferred). Both pointed at the same fix: retry-with-backoff, then surface
LIMITATION clearly if exhausted.

This wrapper:
  - Reads `file`, finds exactly-one `old` occurrence (raises if 0 or 2+).
  - Writes the patched content with 5 retries x 500ms backoff on EBUSY /
    PermissionError / OSError(WinError 32).
  - On success: prints OK + path. Exit 0.
  - On exhaustion: prints LIMITATION: file locked. USER ACTION NEEDED:
    close the file in IDE. Exit 1.
  - On not-found / multi-match: exit 2 with a clear reason (mirrors Edit's
    own contract — same semantics, just with EBUSY tolerance).

Usage
-----
  uv run tools/safe-edit.py FILE OLD NEW
  uv run tools/safe-edit.py FILE --json '{"old": "...", "new": "..."}'

The JSON form avoids shell-quoting issues for multi-line replacements.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

MAX_RETRIES = 5
BACKOFF_SECONDS = 0.5


def is_lock_error(exc: BaseException) -> bool:
    """True if the exception looks like a Windows/POSIX file lock."""
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        # WinError 32 = ERROR_SHARING_VIOLATION. errno 16 = EBUSY.
        return getattr(exc, "winerror", None) == 32 or exc.errno in (16, 13)
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("old", nargs="?")
    p.add_argument("new", nargs="?")
    p.add_argument("--json", help='JSON {"old": "...", "new": "..."}')
    args = p.parse_args()

    if args.json:
        try:
            payload = json.loads(args.json)
            old = payload["old"]
            new = payload["new"]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"safe-edit: bad --json payload: {e}", file=sys.stderr)
            return 2
    elif args.old is not None and args.new is not None:
        old = args.old
        new = args.new
    else:
        print("usage: safe-edit.py FILE OLD NEW  |  --json '{old,new}'", file=sys.stderr)
        return 2

    path = Path(args.file)
    if not path.exists():
        print(f"safe-edit: file not found: {path}", file=sys.stderr)
        return 2

    # Read with retry (read can lock too on Windows when IDE is saving).
    content = None
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            content = path.read_text(encoding="utf-8")
            break
        except Exception as e:
            last_exc = e
            if is_lock_error(e) and attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
                continue
            print(
                f"LIMITATION: file locked for read after {attempt + 1} retries. "
                f"USER ACTION NEEDED: close {path} in IDE. (cause: {e})",
                file=sys.stderr,
            )
            return 1

    count = content.count(old)
    if count == 0:
        print(f"safe-edit: old_string not found in {path}", file=sys.stderr)
        return 2
    if count > 1:
        print(f"safe-edit: old_string matches {count} times in {path}; not unique", file=sys.stderr)
        return 2

    patched = content.replace(old, new, 1)

    # Write with retry.
    for attempt in range(MAX_RETRIES):
        try:
            path.write_text(patched, encoding="utf-8")
            print(f"OK: {path} ({len(old)}c -> {len(new)}c)")
            return 0
        except Exception as e:
            last_exc = e
            if is_lock_error(e) and attempt < MAX_RETRIES - 1:
                time.sleep(BACKOFF_SECONDS * (attempt + 1))
                continue
            print(
                f"LIMITATION: file locked for write after {attempt + 1} retries. "
                f"USER ACTION NEEDED: close {path} in IDE. (cause: {e})",
                file=sys.stderr,
            )
            return 1

    print(f"safe-edit: exhausted retries on {path}: {last_exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
