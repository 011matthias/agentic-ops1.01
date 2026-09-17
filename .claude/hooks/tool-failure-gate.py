#!/usr/bin/env python3
"""PostToolUseFailure(all tools): turn a TRANSIENT failure into an in-turn retry.

WHY THIS EXISTS
---------------
2026-05-11 (friction register, two rows): 7 then 8 Edit calls to a file the
user had open in VS Code failed with EBUSY. The agent reported "8 edits queued
for when the file unlocks" and stopped; the user had to re-prompt before the
same edits applied cleanly. The block was transient the whole time. The fix was
a memory (feedback_active_retry_on_transient_blocks), which depends on recall
at exactly the moment the agent is looking at an error. This hook fires AT the
failure, so the classification no longer depends on recall.

WHAT IT DOES
------------
Classifies the failure text (`tool_error`) into one of four transient classes:

  file-lock       EBUSY / EPERM / "resource busy" / Windows sharing violation
  rate-limit      HTTP 429 / "Too Many Requests" / "rate limit"
  upstream        HTTP 502/503/504 / ECONNRESET / network timeouts
  mcp-connection  MCP transport closed / not connected / failed to connect

On a match it emits `[TRANSIENT] {class}: retry with backoff in this turn; do
not queue it for the user` (plus a one-line how-to for the class) as
additionalContext and increments `transient_blocks` in session state. Every
other failure stays silent: a permanent failure (missing file, bad argument,
a real test failure) is not something a retry fixes.

Precision choices: HTTP codes count only in a status-code context, because a
bare `429` also matches a pytest line number; a local "Command timed out" from
the Bash tool is NOT upstream (the command itself was slow, and re-running it
in the foreground repeats the wait).

The event is non-blocking (the tool already failed); this hook only adds
context. Defensive: any error -> exit 0, no output.

VERIFIED ON CLAUDE CODE 2.1.212 (2026-09-17, live, hook-log evidence)
-----------------------------------------------------------------
Delivered for Bash (non-zero exit), Read (missing file, EBUSY) and Write
(EBUSY) failures. The failure text arrives as `error`, not the `tool_error`
the hooks docs name, so both are read. NOT delivered for an Edit that fails
with EBUSY (`Error calling tool (Edit): EBUSY ...`, two trials against a file
held with FileShare.None): that path bypasses the event, and it is the exact
2026-05-11 incident tool. Edit lock failures still depend on
feedback_active_retry_on_transient_blocks until the harness delivers them.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None

HOOK_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-log.txt")
_SCAN_MAX = 20_000  # failure text can be a whole command transcript

_HTTP_CTX = r"(?:HTTP(?:/\d(?:\.\d)?)?|status(?:\s*code)?|error|code|response)[\s:=/#-]*"

CLASSES: tuple[tuple[str, re.Pattern], ...] = (
    ("file-lock", re.compile(
        r"\bEBUSY\b|\bEPERM\b|resource busy|being used by another process"
        r"|sharing violation|\bfile is locked\b",
        re.IGNORECASE)),
    ("rate-limit", re.compile(
        rf"{_HTTP_CTX}429\b|\b429\s+Too Many Requests|too many requests"
        r"|\brate[- ]?limit(?:ed|ing)?\b",
        re.IGNORECASE)),
    ("mcp-connection", re.compile(
        r"MCP error -32000|MCP server [^\n]{0,80}(?:not connected|disconnected|failed)"
        r"|(?:mcp|transport)[^\n]{0,40}connection closed",
        re.IGNORECASE)),
    ("upstream", re.compile(
        rf"{_HTTP_CTX}50[234]\b|\b50[234]\s+(?:Bad Gateway|Service Unavailable|Gateway Time-?out)"
        r"|\bECONNRESET\b|\bETIMEDOUT\b|\bESOCKETTIMEDOUT\b|\bEAI_AGAIN\b"
        r"|connection (?:reset|timed out)|read timed out|connect(?:ion)? timeout"
        r"|gateway time-?out|temporarily unavailable",
        re.IGNORECASE)),
)

# The Bash tool's own timeout: the command was slow, not the upstream flaky.
_LOCAL_TIMEOUT = re.compile(r"^\s*Command timed out after", re.IGNORECASE)
# An MCP tool that fails to reach its server says so in many shapes; only
# connection-shaped text on an mcp__ tool counts, never its business errors.
_MCP_TOOL_CONN = re.compile(
    r"connection (?:closed|refused|lost)|not connected|failed to connect"
    r"|\bECONNREFUSED\b|disconnected|server (?:is )?unavailable",
    re.IGNORECASE)

HOWTO = {
    "file-lock": ("poll until the file is writable (Bash run_in_background "
                  "until-loop, 2s sleep), then re-apply the SAME edit."),
    "rate-limit": ("back off (30s, then 60s, then 120s) and retry the same call; "
                   "keep doing non-blocked work meanwhile."),
    "upstream": ("retry after 5s, 15s, 45s; escalate as LIMITATION only after "
                 "~10 minutes of failed retries."),
    "mcp-connection": ("retry the call once after a short wait; if the server "
                       "stays down, state it once and use the CLI/API path, "
                       "never re-probe in a loop."),
}


def log(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} tool-failure-gate {msg}\n")
    except Exception:
        pass


def failure_text(payload: dict) -> str:
    """The failure message: `error` on 2.1.212, `tool_error` per the docs,
    `tool_response` as a last resort."""
    for key in ("error", "tool_error", "tool_response"):
        val = payload.get(key)
        if val is None or val == "":
            continue
        if not isinstance(val, str):
            try:
                val = json.dumps(val, ensure_ascii=False)
            except Exception:
                val = str(val)
        return val[:_SCAN_MAX]
    return ""


def classify(tool_name: str, text: str) -> str | None:
    if not text or _LOCAL_TIMEOUT.search(text):
        return None
    for name, rx in CLASSES:
        if rx.search(text):
            return name
    if tool_name.startswith("mcp__") and _MCP_TOOL_CONN.search(text):
        return "mcp-connection"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_name = str(payload.get("tool_name") or "")
    cls = classify(tool_name, failure_text(payload))
    sid = str(payload.get("session_id") or "")[:8]
    # Every delivery is logged (class=none included): the log line is the
    # evidence that this event reaches the hook at all on a given build.
    log(f"fired tool={tool_name} class={cls or 'none'} session={sid} "
        f"keys={sorted(payload.keys())}")
    if not cls:
        return 0

    if session_state is not None:
        try:
            session_state.bump_transient_block()
        except Exception:
            pass

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUseFailure",
            "additionalContext": (
                f"[TRANSIENT] {cls}: retry with backoff in this turn; do not "
                f"queue it for the user. How: {HOWTO[cls]}"
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
