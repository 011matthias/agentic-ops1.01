#!/usr/bin/env python3
"""PostToolUse(Bash) hook: detect skipped gates from recent command history.

Maintains a small ring buffer of recent Bash commands in a temp file.
Fires advisories when patterns suggest a gate was skipped:

  (a) git push / gh pr merge / vercel --prod with no prior `validate-*` run
      -> pre-publish validation gate skipped
  (b) MCP-style update commands (scenarios_update, n8n_update_full_workflow)
      with no prior matching `_get` -> live-system B1.5 gate skipped
      [Note: matcher is Bash so MCP tool calls won't fire this directly;
       included for completeness if the matcher is ever widened.]
  (c) Same fix attempted 3+ times in buffer -> iteration-3x gate

Each advisory is logged with tag `friction-event:gate-skip-{kind}` so the
checkpoint review can pick them up.

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
BUFFER_FILE = os.path.join(tempfile.gettempdir(), "agentic-ops-cmd-buffer.txt")
BUFFER_MAX = 30

PUBLISH_PATTERNS = [
    r"\bgit\s+push\b(?!\s+--dry-run)",
    r"\bgh\s+pr\s+merge\b",
    r"\bvercel\s+--prod\b",
    r"\bvercel\s+deploy\s+--prod\b",
]
VALIDATE_PATTERNS = [
    r"validate-",
    r"\bnpm\s+run\s+(build|typecheck|lint|test)\b",
    r"\bpytest\b",
    r"\buv\s+run\s+(pytest|tools/validate)",
    r"\btsc\b",
]
MCP_UPDATE_PATTERNS = [
    (r"scenarios_update", r"scenarios_get"),
    (r"n8n_update_full_workflow", r"n8n_get_workflow"),
]


def log_fire(msg: str) -> None:
    try:
        with open(HOOK_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} gate-skip-detector {msg}\n")
    except Exception:
        pass


def read_buffer():
    try:
        with open(BUFFER_FILE, "r", encoding="utf-8") as f:
            return [ln.rstrip("\n") for ln in f.readlines()]
    except Exception:
        return []


def write_buffer(lines):
    try:
        with open(BUFFER_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines[-BUFFER_MAX:]))
    except Exception:
        pass


def append_buffer(line: str):
    buf = read_buffer()
    buf.append(line)
    write_buffer(buf)
    return buf


def fingerprint(cmd: str) -> str:
    norm = re.sub(r"\s+", " ", cmd.strip())[:200]
    return hashlib.sha1(norm.encode("utf-8", errors="ignore")).hexdigest()[:12]


def emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        }
    }))


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0

    cmd = ""
    if event.get("tool_name") == "Bash":
        cmd = (event.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0

    fp = fingerprint(cmd)
    buf = append_buffer(f"{fp}\t{cmd[:300]}")

    advisories = []

    if any(re.search(p, cmd) for p in PUBLISH_PATTERNS):
        recent_text = "\n".join(buf[-BUFFER_MAX:])
        had_validate = any(re.search(vp, recent_text) for vp in VALIDATE_PATTERNS)
        if not had_validate:
            log_fire("friction-event:gate-skip-pre-publish cmd=" + cmd[:80])
            advisories.append(
                "[GATE-SKIP: pre-publish] You ran a publish-class command "
                "(push/merge/--prod) with no validation step in the recent buffer. "
                "Recommended: run validate-output.py / validate-html.py / build / "
                "tests BEFORE publishing. friction-event:gate-skip-pre-publish"
            )

    for update_pat, get_pat in MCP_UPDATE_PATTERNS:
        if re.search(update_pat, cmd):
            recent_text = "\n".join(buf[-BUFFER_MAX:])
            if not re.search(get_pat, recent_text):
                log_fire(f"friction-event:gate-skip-live-system pattern={update_pat}")
                advisories.append(
                    f"[GATE-SKIP: live-system B1.5] Update operation '{update_pat}' "
                    f"with no prior '{get_pat}' in buffer. Read current state before "
                    "writing live-system changes. friction-event:gate-skip-live-system"
                )

    fp_count = sum(1 for ln in buf[-15:] if ln.startswith(fp + "\t"))
    if fp_count >= 3:
        log_fire(f"friction-event:gate-skip-iteration-3x fp={fp}")
        advisories.append(
            "[GATE-SKIP: iteration-3x] You have run the same command (or near-identical) "
            "3+ times in the recent buffer. If this is a fix-then-test loop, you have "
            "hit the hard 3-iteration cap. Escalate now -- describe what you tried, "
            "what failed, what you'd try next. friction-event:gate-skip-iteration-3x"
        )

    if advisories:
        emit("\n\n".join(advisories))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
