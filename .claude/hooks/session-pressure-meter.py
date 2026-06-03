#!/usr/bin/env python3
"""PostToolUse(all tools): session-pressure meter.

Counts tool calls + distinct files this session and emits a band-crossing
advisory ONCE per band (moderate -> high -> critical), so the agent is told
when rule_session-pressure.md thresholds are reached instead of relying on a
mental count. Session boundary is keyed off the hook payload's `session_id`
(handled in session_state.ensure_session): a new id resets counts, an
unchanged id across a compaction preserves them.

Defensive: any error -> exit 0, no output. The meter must never break a tool
call, and a missed increment is cheaper than a broken session.
"""
import json
import os
import sys

# Import the shared session-state store from tools/ (repo-root-relative).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)

try:
    import session_state  # noqa: E402
except Exception:
    sys.exit(0)

_ADVISORY = {
    "moderate": (
        "[PRESSURE: MODERATE] {calls} tool calls, {files} distinct files this "
        "session. rule_session-pressure: shift to concise responses and "
        "recommend /comd_checkpoint --mini at the next natural breakpoint."
    ),
    "high": (
        "[PRESSURE: HIGH] {calls} tool calls, {files} distinct files this "
        "session. rule_session-pressure: strongly recommend /comd_checkpoint "
        "(or --mini) before continuing; prioritize finishing the current task "
        "over starting new work."
    ),
    "critical": (
        "[PRESSURE: CRITICAL] {calls} tool calls, {files} distinct files this "
        "session. rule_session-pressure: STOP starting new work and run "
        "/comd_checkpoint --mini now; then suggest a fresh /resume session."
    ),
}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    session_id = payload.get("session_id", "") or ""
    tool_name = payload.get("tool_name", "") or ""
    ti = payload.get("tool_input") or {}
    file_path = None
    if isinstance(ti, dict):
        file_path = ti.get("file_path") or ti.get("notebook_path")

    try:
        session_state.ensure_session(session_id)
        state = session_state.bump_tool(tool_name, file_path)
        band = session_state.pressure_band(state)
        emitted = state.get("pressure_band_emitted")
        if band and session_state.band_is_new(band, emitted):
            session_state.mark_band_emitted(band)
            msg = _ADVISORY[band].format(
                calls=state.get("tool_calls", 0),
                files=len(state.get("distinct_files", []) or []),
            )
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": msg,
                }
            }))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
