#!/usr/bin/env python3
"""PostToolUse(Bash) hook: inject ship-gate / B2 / hard-limit advisories.

Pattern-matches the executed command:
  git push|commit / gh pr ...        -> [SHIP GATE] reminder
  npm run build / pytest / uv run    -> [B2] verification reminder
  3 consecutive build/test commands  -> [HARD LIMIT] (3-iteration cap)

The 3-in-a-row counter persists in a temp file. Counter resets on any
non-build/test bash command. See rule_behaviors.md 'Ship gate' and 'Build
escalation'.

Defensive: any error -> exit 0 silently.
"""
import datetime
import json
import os
import re
import sys
import tempfile

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
COUNTER_FILE = os.path.join(tempfile.gettempdir(), "agentic-ops-build-counter.txt")

SHIP_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+commit\b",
    r"\bgh\s+pr\s+(create|merge|edit)\b",
    r"\bvercel\s+(deploy|--prod)\b",
]
BUILD_TEST_PATTERNS = [
    r"\bnpm\s+run\s+build\b",
    r"\bnpm\s+test\b",
    r"\bpytest\b",
    r"\buv\s+run\s+(pytest|python)\b",
    r"\bnpm\s+run\s+typecheck\b",
    r"\btsc\b",
    r"\bgo\s+test\b",
    r"\bcargo\s+(build|test)\b",
]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} post-action-gate {msg}\n")
    except Exception:
        pass


def read_counter() -> int:
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip() or "0")
    except Exception:
        return 0


def write_counter(n: int) -> None:
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(n))
    except Exception:
        pass


def emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


def matches_any(cmd: str, patterns) -> bool:
    return any(re.search(p, cmd) for p in patterns)


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("tool_name") != "Bash":
        return 0
    cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0

    is_ship = matches_any(cmd, SHIP_PATTERNS)
    is_build = matches_any(cmd, BUILD_TEST_PATTERNS)

    advisories = []

    if is_ship:
        log_fire(f"SHIP cmd={cmd[:80]}")
        advisories.append(
            "[SHIP GATE] You just ran a ship-class command (push/commit/PR/deploy). "
            "If the build passed, continue the chain in this turn: commit -> push -> PR -> "
            "merge. Do NOT pause to ask 'should I merge?' / 'want me to push?' -- those are "
            "ship-gate violations. Only pause for force-push to main, prod data deletion, or "
            "no-undo actions. After deploy, run the deploy verification gate (WebFetch the URL, "
            "check 200 + key content)."
        )

    if is_build:
        n = read_counter() + 1
        write_counter(n)
        log_fire(f"B2 cmd={cmd[:80]} streak={n}")
        advisories.append(
            f"[B2] Build/test command executed (streak: {n}/3). Before declaring done: "
            "did you VERIFY behavior, not just config? Name the specific test performed "
            "(e.g., 'triggered webhook and got 200 with expected payload'). 'Compiles' != "
            "'works'. See rule_behaviors.md B2 gate."
        )
        if n >= 3:
            advisories.append(
                "[HARD LIMIT] You have hit 3 consecutive build/test commands. This is the "
                "iteration cap. STOP fixing. Escalate per ITERATION-LOOP.md Hard Gate: "
                "summarize what you tried, the current failure mode, and what you'd try "
                "next. Do not run another fix-then-test until the user weighs in."
            )
    else:
        if read_counter() != 0:
            write_counter(0)

    if advisories:
        emit("\n\n".join(advisories))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
