#!/usr/bin/env python3
"""PreToolUse(Write|Edit): ask before an existing check configuration changes.

WHY THIS EXISTS
---------------
The cheapest way to turn a red check green is to edit the check: add an ignore
to ruff.toml, a filterwarnings or deselect to pytest.ini, drop a hook from
.pre-commit-config.yaml, or trim a step out of tools/preflight-hooks.py (the
local mirror of the CI `hooks` job). Each of those weakens the check for every
later change, and the diff reads as housekeeping. Ported from ECC's
config-protection hook (2026-09-17 audit, item 10), mechanism only.

WHAT IT DOES
------------
Protected: `ruff.toml` / `.ruff.toml`, `pytest.ini`, `.pre-commit-config.yaml`
(by file name, anywhere in the tree, case-insensitive) and
`tools/preflight-hooks.py`.

  - The file does not exist yet (first-time creation) -> silent allow.
  - The file exists -> permissionDecision "ask": fix the source, not the check.
    Approving the prompt is the path for a change the user wants.

Scorer and guard pins (`tools/scorers/**`, PINS.json, guard-pins.json) stay
with scorer-lock-gate / optimize-run-gate, which own their stricter contract.

Defensive: an unreadable payload exits 0 silently. A stat error other than
"not found" counts as existing, so the gate never weakens itself on a path it
cannot inspect.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

PROTECTED_NAMES = {
    "ruff.toml": "the ruff lint ruleset (the CI hooks job runs it)",
    ".ruff.toml": "the ruff lint ruleset (the CI hooks job runs it)",
    "pytest.ini": "pytest collection and warning policy for the enforcement suite",
    ".pre-commit-config.yaml": "the pre-commit hook set",
}
PROTECTED_SUFFIXES = {
    "tools/preflight-hooks.py": "the local mirror of the CI `hooks` job",
}

REASON = (
    "CONFIG PROTECTION: `{path}` is {what}. Editing it to get a failing check "
    "to pass weakens that check for every later change: fix the source, not "
    "the check. Approve only if the user asked for this config change or it "
    "tightens the check; otherwise cancel and fix the code the check flagged."
)


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} config-protection-gate {msg}\n")
    except Exception:
        pass


def protected(path: str) -> str | None:
    """What the file controls, or None when it is not protected."""
    norm = path.replace("\\", "/").lower()
    name = norm.rsplit("/", 1)[-1]
    if name in PROTECTED_NAMES:
        return PROTECTED_NAMES[name]
    for suffix, what in PROTECTED_SUFFIXES.items():
        if norm == suffix or norm.endswith("/" + suffix):
            return what
    return None


def exists(path: str) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return True  # cannot inspect -> treat as an existing config


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0
    if session_state is not None:
        session_state.bind_session(payload)
    ti = payload.get("tool_input") or {}
    path = ti.get("file_path") if isinstance(ti, dict) else None
    if not path:
        return 0
    what = protected(path)
    if what is None or not exists(path):
        return 0

    display = path.replace("\\", "/")
    log(f"ASK {payload.get('tool_name', '?')} {display}")
    if session_state is not None:
        try:
            session_state.add_candidate(
                "gate-fired-config-protection", "config-protection-gate",
                os.path.basename(display))
        except Exception:
            pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": REASON.format(path=display, what=what),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
