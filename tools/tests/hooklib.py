"""Shared helpers for the enforcement-layer hook test suite.

Invokes each hook script as a subprocess the way Claude Code does: a JSON
payload on stdin, cwd = repo root (unless overridden), then inspects exit
code + stdout. The wired runtime uses `uv run python .claude/hooks/X.py`, but
the hooks are stdlib-only to *run*, so `sys.executable` reproduces identical
behavior without per-test uv overhead.

This module is imported by the sibling test_*.py files (pytest prepend import
mode puts tools/tests on sys.path, so `import hooklib` resolves).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / ".claude" / "hooks"
TOOLS = REPO / "tools"
FIXTURES = TOOLS / "fixtures"


# Session state a hook writes when the test names no state file of its own.
# Named under the session-state prefix so session_state's stale sweep reaps it.
_ISOLATED_STATE = os.path.join(
    tempfile.gettempdir(), f"agentic-ops-session-state-hooklib-{os.getpid()}.json")


def run_hook(
    script: str,
    payload: dict,
    cwd: Path | None = None,
    env: dict | None = None,
    timeout: int = 30,
    isolate_state: bool = True,
) -> subprocess.CompletedProcess:
    """Run .claude/hooks/<script> with `payload` as JSON on stdin.

    `cwd` overrides the working directory (used to neutralise hooks that shell
    out to git relative to cwd). `env` is merged over the inherited environment
    (used to redirect AGENTIC_OPS_SESSION_STATE so a gate's friction-candidate
    side effect cannot pollute the developer's live session state).

    The suite often runs inside a live Claude session, so by default the hook
    never sees that session's CLAUDE_CODE_SESSION_ID and an unset or empty
    AGENTIC_OPS_SESSION_STATE points at a throwaway file. `isolate_state=False`
    leaves both alone, for tests of the per-session path resolution itself
    (those redirect TMP / TEMP instead).
    """
    full_env = dict(os.environ)
    if isolate_state:
        full_env.pop("CLAUDE_CODE_SESSION_ID", None)
    if env:
        full_env.update(env)
    if isolate_state and not full_env.get("AGENTIC_OPS_SESSION_STATE"):
        full_env["AGENTIC_OPS_SESSION_STATE"] = _ISOLATED_STATE
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or REPO),
        env=full_env,
    )


def permission_decision(stdout: str) -> str | None:
    """Extract hookSpecificOutput.permissionDecision from hook stdout, or None.

    Returns None when stdout is empty or not the permission-decision JSON shape
    (i.e. the hook allowed / stayed silent).
    """
    out = stdout.strip()
    if not out:
        return None
    try:
        obj = json.loads(out)
    except json.JSONDecodeError:
        return None
    return (obj.get("hookSpecificOutput") or {}).get("permissionDecision")


def load_hook(script: str):
    """Import .claude/hooks/<script> as a module for unit-level assertions.

    Hook filenames are hyphenated, so `import` cannot reach them. Use this when
    a decision helper (a fingerprint, a classifier) is worth pinning directly
    ALONGSIDE the subprocess-level behavioral tests — never instead of them:
    a helper-only suite cannot tell a wired fix from an unwired one
    (rule_behaviors B2, the 2026-08-24 verification-theater row).
    """
    path = HOOKS / script
    spec = importlib.util.spec_from_file_location(
        "hook_" + path.stem.replace("-", "_"), path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_wire_hooks():
    """Import tools/wire-hooks.py (hyphenated, not importable by name) as a
    module so the suite reads its EXPECTED_HOOK_SCRIPTS / CANONICAL_HOOKS as the
    single source of truth."""
    path = TOOLS / "wire-hooks.py"
    spec = importlib.util.spec_from_file_location("wire_hooks", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
