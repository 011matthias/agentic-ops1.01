#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Auto-rename the current Claude Code chat to '{scope}--{task-desc}'.

Per rule_session-start.md, the agent calls this at session start to make
sessions findable in chat history. The chat title file is platform-specific;
we write to a known location that Claude Code reads.

If the rename mechanism isn't available (no IDE integration, headless run,
or the title file isn't writable), the script logs the intent and exits 0
so the calling skill doesn't fail.

Usage:
    python tools/rename-chat.py "{scope}--{task-desc}"

Examples:
    python tools/rename-chat.py "sys--system-dev"
    python tools/rename-chat.py "meji-media--module-54-bcc"
    python tools/rename-chat.py "platform--oauth-fix"
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "hook-log.txt"


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} rename-chat {msg}\n")
    except Exception:
        pass


def write_title_marker(title: str) -> bool:
    """Write the title to a marker file the IDE can pick up.

    Claude Code reads `.claude/chat-title` at session start when present.
    This is a best-effort hook; if it doesn't take effect, the agent at least
    has a record of the intended name.
    """
    repo = Path(__file__).resolve().parent.parent
    marker = repo / ".claude" / "chat-title"
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(title, encoding="utf-8")
        return True
    except OSError as e:
        log(f"ERROR: cannot write {marker}: {e}")
        return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: rename-chat.py '{scope}--{task-desc}'", file=sys.stderr)
        return 2
    title = sys.argv[1].strip()
    if not title:
        return 2

    ok = write_title_marker(title)
    log(f"{'WROTE' if ok else 'SKIPPED'} title='{title}'")

    # Emit a structured line the agent can parse if needed.
    print(json.dumps({"title": title, "marker_written": ok}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
