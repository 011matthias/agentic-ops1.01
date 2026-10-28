"""Tests for .claude/hooks/config-protection-gate.py (ECC port item 10).

Existing ruff.toml / .ruff.toml / pytest.ini / .pre-commit-config.yaml /
tools/preflight-hooks.py -> permissionDecision "ask" ("fix the source, not the
check"); first-time creation and every other path stay silent. All tests run
the hook as a subprocess with a real payload.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from hooklib import HOOKS, REPO, load_hook, load_wire_hooks, permission_decision, run_hook

HOOK = "config-protection-gate.py"


@pytest.fixture
def env(tmp_path):
    return {"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "state.json")}


def decide(env, path, tool: str = "Edit"):
    r = run_hook(HOOK, {"tool_name": tool, "tool_input": {"file_path": str(path)}}, env=env)
    assert r.returncode == 0, r.stderr
    return permission_decision(r.stdout), r.stdout


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("rel", [
    "ruff.toml", ".ruff.toml", "pytest.ini", ".pre-commit-config.yaml",
    "tools/preflight-hooks.py",
    # a nested subproject's config weakens its own checks the same way
    "workspace/clients/acme/automations/pytest.ini",
])
@pytest.mark.parametrize("tool", ["Edit", "Write"])
def test_existing_protected_file_asks(env, tmp_path, rel, tool):
    decision, out = decide(env, touch(tmp_path / rel), tool)
    assert decision == "ask"
    assert "fix the source, not the check" in out


def test_real_repo_configs_ask(env):
    for rel in ("ruff.toml", "pytest.ini", "tools/preflight-hooks.py"):
        path = REPO / rel
        if path.exists():
            assert decide(env, path)[0] == "ask", rel


def test_case_variant_asks(env, tmp_path):
    touch(tmp_path / "RUFF.TOML")
    assert decide(env, str(tmp_path / "RUFF.TOML"))[0] == "ask"


def test_backslash_spelling_matches_the_protected_set():
    # Pattern half, portable: a Windows spelling is recognised on any OS.
    gate = load_hook(HOOK)
    assert gate.protected("C:\\Repo\\x\\tools\\preflight-hooks.py")
    assert gate.protected("C:\\Repo\\x\\.pre-commit-config.yaml")
    assert gate.protected("C:\\Repo\\x\\tools\\other.py") is None


@pytest.mark.skipif(os.name != "nt", reason="a backslash path only names a real file on Windows")
def test_backslash_path_asks_on_windows(env, tmp_path):
    touch(tmp_path / "tools" / "preflight-hooks.py")
    assert decide(env, str(tmp_path / "tools" / "preflight-hooks.py").replace("/", "\\"))[0] == "ask"


@pytest.mark.parametrize("rel", [
    "ruff.toml", "pytest.ini", ".pre-commit-config.yaml", "tools/preflight-hooks.py",
])
def test_first_time_creation_passes(env, tmp_path, rel):
    assert decide(env, tmp_path / "fresh" / rel, "Write")[0] is None


@pytest.mark.parametrize("rel", [
    "pyproject.toml", "ruff.toml.md", "tools/other-preflight-hooks.py",
    "tools/preflight-hooks.py.bak", "docs/pytest.ini.notes",
    # scorer + guard pins belong to scorer-lock-gate / optimize-run-gate
    "tools/scorers/PINS.json", "tools/guard-pins.json",
])
def test_unprotected_existing_files_stay_silent(env, tmp_path, rel):
    assert decide(env, touch(tmp_path / rel))[0] is None


def test_gate_fire_records_friction_candidate(env, tmp_path):
    decide(env, touch(tmp_path / "pytest.ini"))
    with open(env["AGENTIC_OPS_SESSION_STATE"], encoding="utf-8") as f:
        cands = json.load(f)["candidates"]
    assert any(c["signal"] == "gate-fired-config-protection" and c["context"] == "pytest.ini"
               for c in cands)


def test_malformed_or_pathless_payload_is_silent():
    r = subprocess.run([sys.executable, str(HOOKS / HOOK)], input="{nope",
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == ""
    r = run_hook(HOOK, {"tool_name": "Edit", "tool_input": {}})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_wired_on_pretooluse_write_edit():
    wh = load_wire_hooks()
    wired = [(e.get("matcher"), h.get("command", ""))
             for e in wh.CANONICAL_HOOKS["PreToolUse"] for h in e.get("hooks", [])]
    assert any(m == "Write|Edit" and "config-protection-gate.py" in c for m, c in wired)
    assert "config-protection-gate.py" in wh.EXPECTED_HOOK_SCRIPTS
