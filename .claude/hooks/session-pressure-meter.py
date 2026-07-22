#!/usr/bin/env python3
"""PostToolUse(all tools): session-pressure meter + background-work liveness.

Counts tool calls + distinct files this session and emits a band-crossing
advisory ONCE per band (moderate -> high -> critical), so the agent is told
when rule_session-pressure.md thresholds are reached instead of relying on a
mental count. Session boundary is keyed off the hook payload's `session_id`
(handled in session_state.ensure_session): a new id resets counts, an
unchanged id across a compaction preserves them.

It carries two more best-effort riders, both independent of the pressure logic:
the sibling-session heartbeat refresh (tools/session_registry.py) and the
background-work liveness check (tools/bg_watch.py). Both live HERE rather than
in hooks of their own because this hook already fires on every tool call with
`matcher: ""`; a second all-tools hook would double the subprocess spawns for
an entire session to reach the same payload. When a registered background watch
has gone silent past its expected interval, its advisory is emitted alongside
(or instead of) the pressure one. That per-tool-call cadence is the whole point:
the 2026-07-22 incident it exists for was 76 minutes of continued tool calls
after a verify fan-out had silently died.

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

# Optional: refresh this session's sibling-session heartbeat on every tool call
# (keeps a live session fresh so sibling-session-gate can detect it). Best-effort
# and independent of the pressure logic -- if it's unavailable, the meter still
# runs. See tools/session_registry.py.
try:
    import session_registry  # noqa: E402
except Exception:
    session_registry = None

# Optional: background-work liveness. Fires a loud advisory when work the agent
# registered with `tools/bg_watch.py watch` has gone silent past its expected
# interval. Best-effort and independent of the pressure logic. See bg_watch.py.
try:
    import bg_watch  # noqa: E402
except Exception:
    bg_watch = None

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

    # Refresh the sibling-session heartbeat (independent of pressure; never lets
    # a failure here break the meter or the tool call).
    if session_registry is not None and session_id:
        try:
            session_registry.heartbeat(session_id, cwd=payload.get("cwd"))
        except Exception:
            pass

    messages = []

    # Pressure half. Isolated so a failure here still lets the liveness half run.
    try:
        session_state.ensure_session(session_id)
        state = session_state.bump_tool(tool_name, file_path)
        band = session_state.pressure_band(state)
        emitted = state.get("pressure_band_emitted")
        if band and session_state.band_is_new(band, emitted):
            session_state.mark_band_emitted(band)
            messages.append(_ADVISORY[band].format(
                calls=state.get("tool_calls", 0),
                files=len(state.get("distinct_files", []) or []),
            ))
    except Exception:
        pass

    # Background-work liveness half. Silent unless a registered watch is overdue,
    # and rate-limited to one advisory per watch per bg_watch.RENOTIFY_SECONDS.
    if bg_watch is not None:
        try:
            messages.extend(bg_watch.due_advisories(cwd=payload.get("cwd")))
        except Exception:
            pass

    if messages:
        try:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n\n".join(messages),
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
