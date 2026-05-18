#!/usr/bin/env python3
"""PostToolUse(Write|Edit): auto-strip em-dashes from human-to-human output.

Scope: client-facing deliverables, outbound drafts, proposals. These are the
human-to-human communication surfaces where the zero-em-dash client directive
(2026-05-08) applies strictly. Internal operator docs (workspace/clients/*/
context/*.md outside drafts/), session logs (docs/), rules, and code keep the
looser previous convention per the 2026-05-15 scope correction and are NOT
touched here.

Why a mutating hook and not advisory: the zero-em-dash rule needed post-hoc
validator cleanup three sessions running (missed-memory-recall x3). Advisory
depends on agent recall, which is the thing that kept failing. Auto-strip
removes the recall dependency entirely (Layer-1 self-anneal: tool over memory).

Non-blocking: runs tools/strip-em-dash.py, emits a systemMessage if it changed
anything, never exits 2.
"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
STRIP_TOOL = REPO / "tools" / "strip-em-dash.py"
HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")


def log_fire(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} em-dash-strip-gate {action}\n")
    except Exception:
        pass


def normalize_path(file_path: str) -> str:
    """/c/Users/... -> C:/Users/... (Git-Bash style to Windows)."""
    if not file_path:
        return file_path
    if len(file_path) >= 3 and file_path[0] == "/" and file_path[2] == "/" and file_path[1].isalpha():
        file_path = f"{file_path[1].upper()}:{file_path[2:]}"
    return file_path


def in_human_to_human_scope(file_path: str) -> bool:
    """Mirror post-write-gate's deliverable+comms scope: the client-facing set.

    Match: client deliverables, doc-site/platform-public HTML, outbound drafts,
    proposals. These are read verbatim by a client or external reader.
    Exclude (by omission): context/*.md outside drafts/, docs/, .claude/, code.
    """
    if not file_path:
        return False
    p = file_path.replace("\\", "/").lower()
    if not p.endswith((".html", ".htm", ".md", ".markdown", ".mdx")):
        return False
    deliverable = any(m in p for m in (
        "/platform/public/",
        "/deliverables/",
        "/hero-exports/",
        "/notion-pages/",
        "/doc-site/",
    ))
    comms = ("/context/drafts/" in p) or ("/proposals/" in p)
    return deliverable or comms


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}
    raw = tool_input.get("file_path") or tool_response.get("filePath") or ""
    file_path = normalize_path(raw)

    if not in_human_to_human_scope(file_path):
        sys.exit(0)
    if not Path(file_path).is_file() or not STRIP_TOOL.is_file():
        sys.exit(0)

    try:
        proc = subprocess.run(
            ["uv", "run", str(STRIP_TOOL), file_path],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, cwd=str(REPO),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log_fire(f"ERROR:{type(e).__name__}")
        sys.exit(0)

    out = (proc.stdout or "").strip()
    # strip-em-dash.py prints e.g. "Total: replaced 2, 0 em-dashes remain".
    m = re.search(r"replaced\s+(\d+)", out)
    changed = bool(m) and int(m.group(1)) > 0
    log_fire(f"ran:{Path(file_path).name}:{'changed' if changed else 'clean'}")

    if changed:
        msg = (
            f"em-dash-strip-gate: auto-stripped em-dashes from {Path(file_path).name} "
            f"(human-to-human scope). {out.splitlines()[-1] if out else ''}".strip()
        )
        print(json.dumps({
            "systemMessage": msg,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"NOTE: {Path(file_path).name} had em-dashes auto-stripped by the "
                    f"em-dash-strip-gate hook (client-facing scope, strict zero rule). "
                    f"The file on disk now differs from your last write. Re-read before "
                    f"further edits to that region."
                ),
            },
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
