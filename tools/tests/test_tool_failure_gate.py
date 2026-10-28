"""Tests for .claude/hooks/tool-failure-gate.py (ECC port item 3).

PostToolUseFailure: transient failures (file lock, 429, 5xx / network timeout,
MCP transport) -> "[TRANSIENT] {class}: retry with backoff in this turn; do not
queue it for the user" + transient_blocks++. Everything else stays silent.
Every test runs the hook as a subprocess with a real payload (the caller the
fix changed), with session state redirected to a temp file.

The `error` key is the shape Claude Code 2.1.212 actually delivered in the
2026-09-17 live proof; `tool_error` is the documented one. Both are covered.
"""
from __future__ import annotations

import json

import pytest

from hooklib import load_wire_hooks, run_hook

HOOK = "tool-failure-gate.py"
PREFIX = "retry with backoff in this turn; do not queue it for the user"


@pytest.fixture
def env(tmp_path):
    return {"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "state.json")}


def fire(env, text: str, tool: str = "Bash", key: str = "error"):
    payload = {
        "hook_event_name": "PostToolUseFailure",
        "session_id": "s-test",
        "tool_name": tool,
        "tool_input": {},
        key: text,
    }
    r = run_hook(HOOK, payload, env=env)
    assert r.returncode == 0, r.stderr
    out = r.stdout.strip()
    if not out:
        return None
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUseFailure"
    return hso["additionalContext"]


def transient_blocks(env) -> int:
    try:
        with open(env["AGENTIC_OPS_SESSION_STATE"], encoding="utf-8") as f:
            return int(json.load(f).get("transient_blocks", 0))
    except FileNotFoundError:
        return 0


# ---- transient classes -> advisory ---------------------------------------

@pytest.mark.parametrize("tool,text,cls", [
    # file lock: the 2026-05-11 shape, plus the Windows sharing violation
    ("Write", "EBUSY: resource busy or locked, open 'C:\\x\\video-script.md'", "file-lock"),
    ("Read", "EBUSY: resource busy or locked, open 'C:\\x\\a.md'", "file-lock"),
    ("Bash", "Command exited with code 1: EPERM: operation not permitted, rename", "file-lock"),
    ("PowerShell", "The process cannot access the file because it is being used by another process.",
     "file-lock"),
    # rate limit
    ("Bash", "Command exited with code 22: curl: (22) The requested URL returned error: 429", "rate-limit"),
    ("WebFetch", "Request failed with status code 429", "rate-limit"),
    ("Bash", "HTTP/1.1 429 Too Many Requests", "rate-limit"),
    ("Bash", "openai.RateLimitError: rate limited, retry later", "rate-limit"),
    # transient upstream
    ("WebFetch", "Request failed with status code 503", "upstream"),
    ("Bash", "502 Bad Gateway", "upstream"),
    ("Bash", "Error: read ECONNRESET", "upstream"),
    ("Bash", "requests.exceptions.ReadTimeout: Read timed out. (read timeout=30)", "upstream"),
    # MCP transport
    ("mcp__github__get_file_contents", "MCP error -32000: Connection closed", "mcp-connection"),
    ("mcp__playwright__browser_navigate", "Server playwright not connected", "mcp-connection"),
])
def test_transient_failures_advise_and_count(env, tool, text, cls):
    ctx = fire(env, text, tool)
    assert ctx is not None, f"expected {cls} advisory"
    assert ctx.startswith(f"[TRANSIENT] {cls}: {PREFIX}")
    assert transient_blocks(env) == 1


def test_documented_tool_error_key_also_classifies(env):
    ctx = fire(env, "EBUSY: resource busy or locked", "Write", key="tool_error")
    assert ctx.startswith("[TRANSIENT] file-lock:")


def test_counter_accumulates(env):
    fire(env, "EBUSY: resource busy or locked", "Write")
    fire(env, "Request failed with status code 503", "WebFetch")
    assert transient_blocks(env) == 2


# ---- everything else -> silent -------------------------------------------

@pytest.mark.parametrize("tool,text", [
    ("Read", "File does not exist. Note: your current working directory is C:\\x"),
    ("Bash", "Command exited with code 2: ls: cannot access '/x': No such file or directory"),
    ("Edit", "String to replace not found in file."),
    # a real test failure whose line number happens to be 429 / 503
    ("Bash", "Command exited with code 1: tools/tests/test_x.py:429: AssertionError"),
    ("Bash", "Command exited with code 1: FAILED tests/test_api.py::test_retry - line 503"),
    # the Bash tool's own timeout is a slow command, not a flaky upstream
    ("Bash", "Command timed out after 2m 0s"),
    # an MCP tool's business error is not a transport failure
    ("mcp__github__get_file_contents", "Not Found: path does not exist in repository"),
    ("Bash", ""),
])
def test_permanent_failures_stay_silent(env, tool, text):
    assert fire(env, text, tool) is None
    assert transient_blocks(env) == 0


def test_malformed_stdin_is_silent_exit_0(env):
    import subprocess
    import sys

    from hooklib import HOOKS
    r = subprocess.run([sys.executable, str(HOOKS / HOOK)], input="{not json",
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == ""


# ---- wiring ----------------------------------------------------------------

def test_wired_under_post_tool_use_failure_all_tools():
    wh = load_wire_hooks()
    entries = wh.CANONICAL_HOOKS.get("PostToolUseFailure") or []
    wired = [(e.get("matcher"), h.get("command", ""))
             for e in entries for h in e.get("hooks", [])]
    assert any(m == ".*" and "tool-failure-gate.py" in cmd for m, cmd in wired), wired
    assert "tool-failure-gate.py" in wh.EXPECTED_HOOK_SCRIPTS
