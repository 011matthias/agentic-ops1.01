#!/usr/bin/env python3
"""PreToolUse(Write|Edit) hook: reference-anchor reminder for client deliverables.

When the agent is about to write to a client-facing deliverable, inject a
[REFERENCE ANCHOR CHECK] reminder: extract patterns from any reference content,
do not copy reference text/data verbatim into the deliverable. See B4 gate
('client-facing content accuracy') in rule_behaviors.md and the deliverable
standards in rule_deliverables.md.

Non-blocking: emits additionalContext only.

Defensive: any error -> exit 0 silently.
"""
import datetime
import json
import os
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

DELIVERABLE_SEGMENTS = [
    "/deliverables/",
    "/hero-exports/",
    "/notion-pages/",
    "/platform/public/",
    "/platform/src/content/proposals/",
    "/doc-site/",
    "/comms-log",
    "/proposals/",
]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} reference-anchor-gate {msg}\n")
    except Exception:
        pass


def normalize(path: str) -> str:
    return (path or "").replace("\\", "/").lower()


def in_deliverable_scope(path: str) -> bool:
    p = normalize(path)
    if not p:
        return False
    if "workspace/clients/" in p and "/automations/" not in p and "/specs/" not in p and "/context/" not in p:
        return True
    return any(seg in p for seg in DELIVERABLE_SEGMENTS)


def emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }))


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") not in ("Write", "Edit"):
        return 0
    file_path = (event.get("tool_input") or {}).get("file_path", "")
    if not in_deliverable_scope(file_path):
        return 0

    log_fire(f"FIRE path={file_path}")
    emit(
        "[REFERENCE ANCHOR CHECK] You are about to write to a client-facing deliverable. "
        "Reference content (other proposals, examples, prior decks) should anchor PATTERNS "
        "and STRUCTURE -- never copy values, names, statistics, or claims into this file "
        "without verifying them against the actual source for THIS client. Every number, "
        "field name, and config value must trace to a queried source. Unverified -> 'TBD'. "
        "See rule_behaviors.md B4 gate."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
