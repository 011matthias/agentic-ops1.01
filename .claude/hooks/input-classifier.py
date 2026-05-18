#!/usr/bin/env python3
"""UserPromptSubmit hook: classify input as exploratory vs directive.

If the prompt looks like brainstorming (>=2 exploratory signals, 0 directive
signals), inject a [GATE] advisory reminding the agent not to treat
brainstorming examples as a hard spec. See rule_behaviors.md "Input
interpretation" gate.

Defensive: any error -> exit 0 silently so a broken hook never blocks the agent.
"""
import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")

EXPLORATORY = [
    r"\bmaybe\b",
    r"\bwhat if\b",
    r"\bthinking about\b",
    r"\bcould we\b",
    r"\bcould you\b",
    r"\bwondering\b",
    r"\bperhaps\b",
    r"\bi('?| a)m thinking\b",
    r"\bnot sure\b",
    r"\bbrainstorm",
]

DIRECTIVE = [
    r"\bdo (this|that|the)\b",
    r"\bfix\b",
    r"\bbuild\b",
    r"\bship\b",
    r"\bdeploy\b",
    r"\brun\b",
    r"\bmake (it|sure|the)\b",
    r"\badd\b",
    r"\bremove\b",
    r"\bdelete\b",
    r"\bcreate\b",
    r"\bimplement\b",
    r"\brestore\b",
    r"\bmerge\b",
    r"\bcommit\b",
    r"\bpush\b",
]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} input-classifier {msg}\n")
    except Exception:
        pass


def emit(additional_context: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }))


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    prompt = (event.get("prompt") or "").lower()
    if not prompt:
        return 0

    explor = sum(1 for p in EXPLORATORY if re.search(p, prompt))
    direct = sum(1 for p in DIRECTIVE if re.search(p, prompt))

    if explor >= 2 and direct == 0:
        log_fire(f"GATE explor={explor} direct={direct}")
        emit(
            "[GATE] This prompt reads as exploratory (brainstorming / thinking-aloud), "
            "not directive. Extract INTENT and strategic direction. Restate interpreted "
            "intent before acting. Do not treat any examples in the message as a spec, "
            "and do not start building until you have confirmed the actual goal. "
            "See rule_behaviors.md 'Input interpretation'."
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
