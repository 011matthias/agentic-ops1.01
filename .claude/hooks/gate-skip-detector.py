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

# Shared session-state store (tools/, repo-root-relative). Optional: if the
# import fails the detector still emits its advisories, it just doesn't persist
# the friction CANDIDATE for the /comd_checkpoint drain. Detection already
# worked here; this adds the structured pickup the checkpoint never had.
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools")
)
try:
    import session_state  # noqa: E402
except Exception:
    session_state = None


def _capture(signal: str, context: str) -> None:
    """Persist a friction candidate (not a register row). Never raises."""
    if session_state is None:
        return
    try:
        session_state.add_candidate(signal, "gate-skip-detector", context)
    except Exception:
        pass


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
    # F2a: the original set only recognized npm/pytest/tsc/validate-* as a
    # validation step, so behavioral / non-npm validation (the norm for hook
    # and tooling work) read as "no validation" and the pre-publish gate
    # false-fired. Confirmed FP twice in the 2026-05-19 F1 session after a
    # full py_compile + sandbox-test + json.load verification run.
    r"\bpy_compile\b",                       # python syntax check
    r"--check\b",                            # assertion-mode tools (wire-hooks --check)
    r"--dry-run\b",                          # dry-run validation
    r"\.claude/hooks/[\w.-]+\.py",           # invoking a hook directly = behavioral hook test
    r"\bjson\.load\b",                       # json.load(open(...)) JSON structural check
    r"\bjson\.tool\b",                       # python -m json.tool validation
    r"\b(smoke|sandbox)\w*\b",               # smoke / sandbox test phrasing
    r"\btests?[\\/]\w",                      # tests/ or test-harness path invocation
]
MCP_UPDATE_PATTERNS = [
    (r"scenarios_update", r"scenarios_get"),
    (r"n8n_update_full_workflow", r"n8n_get_workflow"),
]
# F2c: a repeated command only signals a stuck fix-then-test loop if it is a
# MUTATING / build attempt. Repeated read-only or idempotent commands (status
# checks, re-running an assertion that passes, data-prep reads, hook-test
# harness invocations) are not a fix loop -- firing iteration-3x on them was
# the documented misfire. These are excluded from the 3x count.
READONLY_PATTERNS = [
    r"^\s*(git\s+(status|log|diff|show|branch|fetch|cat-file|rev-parse)|ls|cat|head|tail|grep|rg|find|echo|pwd|wc|stat)\b",
    r"--check\b", r"--dry-run\b", r"--list\b",
    r"\.claude/hooks/[\w.-]+\.py",           # hook test harness re-runs
    r"\b(validate-|py_compile)\b",
    r"\bjson\.load\b", r"\bjson\.tool\b",
    r"(_get|_list)\b", r"\bscenarios_get\b", r"\bn8n_get_workflow\b",
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


_QUOTED = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'")
_HEREDOC = re.compile(r"<<-?\s*'?\w+'?.*?^\s*\w+\s*$", re.DOTALL | re.MULTILINE)


def publish_residue(cmd: str) -> str:
    """Return the part of `cmd` that can be a REAL publish invocation.

    F2b: a publish verb appearing only inside a quoted string, a heredoc
    body, or a hook-test payload is not a publish -- e.g. piping
    {"command":"git push"} into a stop-b1 test, or a heredoc PR body that
    mentions `gh pr merge`. Strip quoted spans + heredoc bodies; if the
    command invokes a .claude/hooks script at all, it is a hook test, not a
    publish -> return empty so PUBLISH_PATTERNS cannot match.
    """
    if ".claude/hooks/" in cmd:
        return ""
    residue = _HEREDOC.sub(" ", cmd)
    residue = _QUOTED.sub(" ", residue)
    return residue


def is_readonly(cmd: str) -> bool:
    """F2c: True if `cmd` is read-only / idempotent and so must not count
    toward the iteration-3x stuck-loop signal."""
    return any(re.search(p, cmd) for p in READONLY_PATTERNS)


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

    pub_scan = publish_residue(cmd)
    if pub_scan and any(re.search(p, pub_scan) for p in PUBLISH_PATTERNS):
        recent_text = "\n".join(buf[-BUFFER_MAX:])
        had_validate = any(re.search(vp, recent_text) for vp in VALIDATE_PATTERNS)
        if not had_validate:
            log_fire("friction-event:gate-skip-pre-publish cmd=" + cmd[:80])
            _capture("gate-skip-pre-publish", cmd[:300])
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
                _capture("gate-skip-live-system", f"{update_pat}: {cmd[:240]}")
                advisories.append(
                    f"[GATE-SKIP: live-system B1.5] Update operation '{update_pat}' "
                    f"with no prior '{get_pat}' in buffer. Read current state before "
                    "writing live-system changes. friction-event:gate-skip-live-system"
                )

    fp_count = sum(1 for ln in buf[-15:] if ln.startswith(fp + "\t"))
    if fp_count >= 3 and not is_readonly(cmd):
        log_fire(f"friction-event:gate-skip-iteration-3x fp={fp}")
        _capture("gate-skip-iteration-3x", cmd[:300])
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
