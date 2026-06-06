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
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / ".claude" / "hooks"
TOOLS = REPO / "tools"
FIXTURES = TOOLS / "fixtures"


def run_hook(
    script: str,
    payload: dict,
    cwd: Path | None = None,
    env: dict | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run .claude/hooks/<script> with `payload` as JSON on stdin.

    `cwd` overrides the working directory (used to neutralise hooks that shell
    out to git relative to cwd). `env` is merged over the inherited environment
    (used to redirect AGENTIC_OPS_SESSION_STATE so a gate's friction-candidate
    side effect cannot pollute the developer's live session state).
    """
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
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


def load_wire_hooks():
    """Import tools/wire-hooks.py (hyphenated, not importable by name) as a
    module so the suite reads its EXPECTED_HOOK_SCRIPTS / CANONICAL_HOOKS as the
    single source of truth."""
    path = TOOLS / "wire-hooks.py"
    spec = importlib.util.spec_from_file_location("wire_hooks", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
