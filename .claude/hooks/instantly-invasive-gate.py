#!/usr/bin/env python3
"""PreToolUse(Bash): tripwire for invasive Instantly API calls.

Enforces rule_instantly_invasive.md (B5). A mutating call to api.instantly.ai
must never run silently. This hook detects state-changing calls and forces a
permission stop ("ask"), so the user is in the loop on every invasive action
even if the agent missed the scope-of-effects protocol.

Read calls pass through untouched:
  - any GET (plain curl with no mutating method / no body)
  - read-style POST endpoints: /leads/list, /campaigns/analytics, /analytics

Mutating (blocked -> ask): -X POST|PUT|PATCH|DELETE (or --request) to any other
path, which covers campaign create/start/pause/delete, lead import/edit/delete,
sequence edits, sends, mailbox/blocklist changes.

Non-blocking by design uses permissionDecision="ask" (not deny) so a genuinely
user-requested + confirmed action can still proceed via the prompt.
"""
import datetime
import json
import os
import re
import sys

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
READ_PATHS = ("/leads/list", "/campaigns/analytics", "/analytics")
MUTATING = re.compile(r"(-X\s*|--request\s+)(POST|PUT|PATCH|DELETE)", re.IGNORECASE)


def log(action: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} instantly-invasive-gate {action}\n")
    except Exception:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    cmd = ((payload.get("tool_input") or {}).get("command")) or ""
    if "api.instantly.ai" not in cmd:
        sys.exit(0)

    is_read_path = any(p in cmd for p in READ_PATHS)
    has_mutating_method = bool(MUTATING.search(cmd))

    # GET (no mutating method) or an allowlisted read endpoint -> let it run.
    if is_read_path or not has_mutating_method:
        log("allow:read")
        sys.exit(0)

    # Mutating call to a non-read path -> force a permission stop.
    log("ASK:invasive-instantly-call")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": (
                "INVASIVE INSTANTLY CALL detected (state-changing api.instantly.ai "
                "request). Per rule_instantly_invasive.md (B5): this must NOT run "
                "unless the user specifically asked for this exact action AND was "
                "first given a plain-language scope-of-effects explanation (what "
                "changes, who it touches in the real world, what is irreversible, "
                "reputation/credit/deliverability impact) and gave a clear yes. If "
                "that protocol was not completed, cancel and follow it first."
            ),
        }
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
