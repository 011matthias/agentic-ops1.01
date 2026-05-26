#!/usr/bin/env python3
"""PostToolUse(Bash) hook: inject ship-gate / B2 / hard-limit advisories.

Pattern-matches the executed command:
  git push|commit / gh pr ...        -> [SHIP GATE] reminder
  npm run build / pytest / uv run    -> [B2] verification reminder
  3 consecutive build/test commands  -> [HARD LIMIT] (3-iteration cap)

The 3-in-a-row counter persists in a temp file. The counter increments only
on REAL fix-then-test loops -- the same command (or near-identical, fuzzy by
fingerprint) repeated -- not on a sweep of DIFFERENT verification commands
hitting the build-test pattern set. This mirrors the gate-skip-detector
READONLY exemption and closes the 2026-05-26 false-positive: a behavioral
test sweep of 4 different inputs to a new hook tripped HARD LIMIT 3/3
even though each input was a distinct test, not a fix-retry.

See rule_behaviors.md 'Ship gate' and 'Build escalation'.

Defensive: any error -> exit 0 silently.
"""
import datetime
import hashlib
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
# Commands that LOOK like build/test (match BUILD_TEST_PATTERNS) but are
# really read-only / behavioral verification / hook tests. These never count
# toward the streak — mirrors gate-skip-detector READONLY_PATTERNS so a sweep
# of validators or hook-tests doesn't false-fire iteration-3x.
EXEMPT_PATTERNS = [
    r"\.claude/hooks/[\w.-]+\.py",          # invoking a hook directly = hook test
    r"\btools/(?:validate|wire-hooks|friction-watch|spec-staleness|safe-edit|gh-merge|rename-chat)\b",
    r"--check\b", r"--dry-run\b", r"--list\b", r"--help\b", r"-h\b",
    r"\bpy_compile\b",
    r"\bjson\.tool\b", r"\bjson\.load\b",
    r"echo\s+'?\{",                         # piping a JSON event into a hook = hook test
]


def is_exempt(cmd: str) -> bool:
    return any(re.search(p, cmd) for p in EXEMPT_PATTERNS)


def fingerprint(cmd: str) -> str:
    norm = re.sub(r"\s+", " ", cmd.strip())[:200]
    return hashlib.sha1(norm.encode("utf-8", errors="ignore")).hexdigest()[:12]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} post-action-gate {msg}\n")
    except Exception:
        pass


def read_state() -> tuple[int, str]:
    """Counter file now stores 'count\\tlast_fingerprint'. Backwards-compatible
    with the older int-only format."""
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except Exception:
        return 0, ""
    if not raw:
        return 0, ""
    if "\t" in raw:
        n_str, fp = raw.split("\t", 1)
        try:
            return int(n_str), fp
        except ValueError:
            return 0, ""
    try:
        return int(raw), ""
    except ValueError:
        return 0, ""


def write_state(n: int, fp: str) -> None:
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(f"{n}\t{fp}")
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
        if is_exempt(cmd):
            # A hook test or read-only verification: emit the B2 nudge but
            # do NOT advance the streak (would false-fire HARD LIMIT during
            # behavioral test sweeps). Reset to zero so a real loop after
            # exempt commands starts fresh.
            prev_n, _ = read_state()
            if prev_n != 0:
                write_state(0, "")
            log_fire(f"B2 EXEMPT cmd={cmd[:80]}")
            advisories.append(
                "[B2] Verification command (exempt from streak). Before declaring "
                "done: did you VERIFY behavior, not just config? Name the specific "
                "test performed. 'Compiles' != 'works'. See rule_behaviors.md B2 gate."
            )
        else:
            fp = fingerprint(cmd)
            prev_n, prev_fp = read_state()
            # Streak only advances when the fingerprint matches the prior
            # build/test command. Different command = fresh streak of 1.
            n = (prev_n + 1) if fp == prev_fp else 1
            write_state(n, fp)
            log_fire(f"B2 cmd={cmd[:80]} streak={n} fp={fp}")
            advisories.append(
                f"[B2] Build/test command executed (streak: {n}/3). Before declaring done: "
                "did you VERIFY behavior, not just config? Name the specific test performed "
                "(e.g., 'triggered webhook and got 200 with expected payload'). 'Compiles' != "
                "'works'. See rule_behaviors.md B2 gate."
            )
            if n >= 3:
                advisories.append(
                    "[HARD LIMIT] You have run the SAME build/test command 3 times in a row. "
                    "This is a fix-then-test loop. STOP fixing. Escalate per ITERATION-LOOP.md "
                    "Hard Gate: summarize what you tried, the current failure mode, and what "
                    "you'd try next. Do not run another fix-then-test until the user weighs in."
                )
    else:
        prev_n, _ = read_state()
        if prev_n != 0:
            write_state(0, "")

    if advisories:
        emit("\n\n".join(advisories))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
