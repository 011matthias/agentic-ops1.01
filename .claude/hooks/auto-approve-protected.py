#!/usr/bin/env python3
"""PermissionRequest(Edit|Write) hook: auto-approve writes inside protected dirs.

Auto-approves Write/Edit tool calls whose file_path falls inside any of:
  .claude/        tools/        workspace/        docs/        platform/
  the user's MEMORY.md directory (~/.claude/projects/.../memory/)

For matching paths -> emit approve decision.
For non-matching paths -> exit silently (defer to normal permission flow).

Outputs both legacy `{decision: "approve"}` and modern PreToolUse-style
`{hookSpecificOutput: {permissionDecision: "allow"}}` so it works whether
the harness invokes this as a PermissionRequest event or a PreToolUse hook.

Defensive: any error -> exit 0 silently (no decision -> normal flow).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _scope  # canonical path->category scope predicates (shared)
except Exception:  # never let a missing shared lib brick the hook
    _scope = None

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} auto-approve-protected {msg}\n")
    except Exception:
        pass


def normalize(path: str) -> str:
    return (path or "").replace("\\", "/")


def is_protected(file_path: str) -> bool:
    if not file_path:
        return False
    p = normalize(file_path)
    p_lower = p.lower()

    # Memory-dir special case (auto-approve-specific): ~/.claude/projects/**/memory/**
    home = os.path.expanduser("~").replace("\\", "/").lower()
    if home and home in p_lower and "/.claude/projects/" in p_lower and "/memory/" in p_lower:
        return True

    # Protected-tree membership (.claude / tools / workspace / docs / platform).
    return bool(_scope) and _scope.in_protected_segment(p)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") not in ("Write", "Edit"):
        return 0
    file_path = (event.get("tool_input") or {}).get("file_path", "")
    if not is_protected(file_path):
        return 0

    log_fire(f"APPROVE path={file_path}")
    out = {
        "decision": "approve",
        "hookSpecificOutput": {
            "hookEventName": event.get("hook_event_name", "PreToolUse"),
            "permissionDecision": "allow",
            "permissionDecisionReason": "auto-approved: write inside protected workspace dir",
        },
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
