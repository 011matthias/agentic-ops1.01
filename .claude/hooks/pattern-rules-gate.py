#!/usr/bin/env python3
"""Generic runtime for declarative pattern rules (`.claude/patterns/*.md`).

One hook, four arms, chosen by the payload's `hook_event_name`:

  PreToolUse Bash|PowerShell  -> event `bash`   (command, via _shell.py view)
  PreToolUse Write|Edit       -> event `file`   (file_path, new_text, old_text)
  UserPromptSubmit            -> event `prompt` (user_prompt, code stripped)
  Stop                        -> event `stop`   (final_text, code stripped)

Actions: `warn` -> additionalContext; `ask` -> permissionDecision "ask";
`block` -> permissionDecision "deny" (PreToolUse) or decision "block"
(UserPromptSubmit / Stop). Several matching rules collapse to the strongest
action, with every matching message in the reason.

Stop has no additionalContext channel, so a stop-event `warn` is parked in a
small tempdir store keyed by session_id and delivered by THIS hook's
UserPromptSubmit arm on the next turn (the same shape as the B1 primer). A
stop `block` honors `stop_hook_active`, so it costs one turn and cannot wedge.

Rule format, parsing and matching live in `_pattern_rules.py`; authoring and
lint in `tools/pattern_rules.py`. Why the whole mechanism exists: see the
module docstring there.

Defensive: a malformed rule file is skipped and logged to hook-log.txt; any
other error exits 0 silently. A broken rule must never break a tool call.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
import tempfile

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HOOK_DIR))
# Test seam (PATTERN_RULES_HOOK_LOG): keeps the suite out of the live log.
HOOK_LOG = os.environ.get("PATTERN_RULES_HOOK_LOG") or os.path.join(HOOK_DIR, "hook-log.txt")
PENDING_FILE = os.environ.get("PATTERN_RULES_PENDING") or os.path.join(
    tempfile.gettempdir(), "agentic-ops-pattern-pending.json"
)
# Bound the stop-arm transcript read: the final message is at the tail, and a
# long session's transcript runs to tens of MB.
TAIL_BYTES = 2_000_000
PENDING_MAX = 5

sys.path.insert(0, HOOK_DIR)
try:
    import _pattern_rules as pr  # noqa: E402
except Exception:  # a broken library must not break the tool call
    sys.exit(0)

try:
    from _shell import normalize_command  # noqa: E402
except Exception:  # pragma: no cover - normalization is a nice-to-have
    def normalize_command(cmd: str) -> str:
        return cmd


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} pattern-rules-gate {msg}\n")
    except Exception:
        pass


def _strip_code():
    """stop-b1-gate's strip_code, loaded from its file so the quoted-example
    exemption (2026-05-19 self-referential false positive) has one source."""
    path = os.path.join(HOOK_DIR, "stop-b1-gate.py")
    spec = importlib.util.spec_from_file_location("stop_b1_gate_for_patterns", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.strip_code


def last_assistant_text(transcript_path: str) -> str:
    """Text of the final assistant entry, read from the transcript tail."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            if size > TAIL_BYTES:
                fh.seek(size - TAIL_BYTES)
                fh.readline()  # drop the partial first line
            lines = fh.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        msg = obj.get("message") if isinstance(obj, dict) else None
        role = obj.get("type") or (msg or {}).get("role")
        if role != "assistant" or not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        return ""
    return ""


# --------------------------------------------------------------------------
# Pending stop-warn store
# --------------------------------------------------------------------------
def _read_pending() -> dict:
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_pending(data: dict) -> None:
    try:
        tmp = PENDING_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, PENDING_FILE)
    except Exception:
        pass


def park_warnings(session_id: str, texts: list[str]) -> None:
    data = _read_pending()
    queue = (data.get(session_id) or []) + texts
    data[session_id] = queue[-PENDING_MAX:]
    _write_pending(data)


def pop_warnings(session_id: str) -> list[str]:
    data = _read_pending()
    queue = data.pop(session_id, None)
    if queue:
        _write_pending(data)
    return list(queue or [])


# --------------------------------------------------------------------------
# Output shapes
# --------------------------------------------------------------------------
def emit(obj: dict) -> None:
    print(json.dumps(obj))


def pre_tool_output(hits: list) -> dict:
    action = pr.strongest(hits)
    text = "\n\n".join(h.render() for h in hits)
    if action == "block":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": text,
        }}
    if action == "ask":
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": text,
        }}
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}


def event_fields(payload: dict) -> tuple[str | None, dict]:
    """Map a hook payload to (pattern event, fields). (None, {}) = not ours."""
    hook = payload.get("hook_event_name", "")
    if hook == "PreToolUse":
        tool = payload.get("tool_name", "")
        ti = payload.get("tool_input") or {}
        if not isinstance(ti, dict):
            return None, {}
        if tool in ("Bash", "PowerShell"):
            return "bash", {"command": normalize_command(str(ti.get("command", "")))}
        if tool in ("Write", "Edit"):
            new_text = ti.get("content") if tool == "Write" else ti.get("new_string")
            return "file", {
                "file_path": str(ti.get("file_path", "")).replace("\\", "/"),
                "new_text": str(new_text or ""),
                "old_text": str(ti.get("old_string", "") or ""),
            }
        return None, {}
    if hook == "UserPromptSubmit":
        return "prompt", {"user_prompt": str(payload.get("prompt", "") or "")}
    if hook == "Stop":
        return "stop", {}
    return None, {}


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    event, fields = event_fields(payload)
    if event is None:
        return 0
    session_id = str(payload.get("session_id", "") or "")

    rules, errors = pr.load_rules(pr.rules_dir(REPO))
    for path, err in errors:
        log_fire(f"SKIP malformed {os.path.basename(path)}: {err}")
    wanted = [r for r in rules if r.enabled and r.event == event]

    parked = pop_warnings(session_id) if event == "prompt" and session_id else []
    if not wanted and not parked:
        return 0

    if event == "stop":
        text = last_assistant_text(payload.get("transcript_path", ""))
        if not text.strip():
            return 0
        fields = {"final_text": _strip_code()(text)}
    elif event == "prompt" and wanted:
        fields = {"user_prompt": _strip_code()(fields["user_prompt"])}

    hits = pr.evaluate(wanted, event, fields)
    for h in hits:
        log_fire(f"MATCH event={event} rule={h.name} action={h.action}")

    if event in ("bash", "file"):
        if hits:
            emit(pre_tool_output(hits))
        return 0

    if event == "stop":
        blocks = [h for h in hits if h.action == "block"]
        warns = [h for h in hits if h.action != "block"]
        if warns and session_id:
            park_warnings(session_id, [
                "[from your previous closing message] " + h.render() for h in warns
            ])
        if blocks and not payload.get("stop_hook_active"):
            emit({"decision": "block",
                  "reason": "\n\n".join(h.render() for h in blocks)})
        return 0

    # prompt
    blocks = [h for h in hits if h.action == "block"]
    if blocks:
        emit({"decision": "block", "reason": "\n\n".join(h.render() for h in blocks)})
        return 0
    context = parked + [h.render() for h in hits]
    if context:
        emit({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(context),
        }})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        log_fire(f"ERROR {type(exc).__name__}: {exc}")
        sys.exit(0)
