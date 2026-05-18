#!/usr/bin/env python3
"""Stop hook: B1 reminder before allowing the agent to stop.

Before the agent's turn ends, inject a [B1] reminder asking it to verify
that its response did not defer work to the user (asking the user to do
something automatable, asking permission to ship when build passes, etc.).
See rule_behaviors.md B1 gate and 'Ship gate'.

Skips when stop_hook_active is true to avoid infinite loops.

Stop hooks signal "block" with a reason to feed text back to the agent;
the agent will then have one more turn to address the reminder. The
stop_hook_active guard ensures we only fire once per stop cycle.

Defensive: any error -> exit 0 silently (allow the stop).
"""
import datetime
import json
import os
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} stop-b1-gate {msg}\n")
    except Exception:
        pass


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    if event.get("stop_hook_active"):
        return 0

    log_fire("FIRE")
    print(json.dumps({
        "decision": "block",
        "reason": (
            "[B1] Before stopping: scan your final response. Are you asking the user to "
            "do, check, run, or confirm something you could do yourself? Common patterns "
            "to flag: 'should I push?', 'want me to merge?', 'shall I deploy?', 'can you "
            "verify X?', 'please run Y'. If the build passes, the answer is yes -- ship "
            "without asking. If you genuinely lack a tool, frame it as 'LIMITATION: ... "
            "USER ACTION NEEDED: ...' not as a choice. If your response was clean of "
            "deferrals, you can stop now -- just acknowledge briefly and stop."
        ),
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
