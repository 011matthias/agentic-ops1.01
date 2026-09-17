"""Skill-run telemetry (session-pressure-meter rider) + skill_stocktake.py.

The write side is driven THROUGH the wired meter as a subprocess with a real
PostToolUse payload (rule_behaviors B2: a helper-only suite cannot tell a wired
rider from an unwired one). Every state store the meter touches is redirected
to tmp so the suite never writes the developer's live session state.
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from hooklib import TOOLS, run_hook

sys.path.insert(0, str(TOOLS))
import telemetry_store  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    tel = tmp_path / "telemetry"
    e = {
        "AGENTIC_OPS_TELEMETRY_DIR": str(tel),
        "AGENTIC_OPS_SESSION_STATE": str(tmp_path / "state.json"),
        "AGENTIC_OPS_BG_WATCHES": str(tmp_path / "watches.json"),
        "AGENTIC_OPS_SESSION_DIR": str(tmp_path / "sessions"),
    }
    monkeypatch.setenv("AGENTIC_OPS_TELEMETRY_DIR", str(tel))
    return {"env": e, "runs": tel / "skill-runs.jsonl"}


def _meter(env, tool_name, tool_input, tool_response=None):
    payload = {"hook_event_name": "PostToolUse", "session_id": "sess-1",
               "tool_name": tool_name, "tool_input": tool_input}
    if tool_response is not None:
        payload["tool_response"] = tool_response
    p = run_hook("session-pressure-meter.py", payload, env=env["env"])
    assert p.returncode == 0
    return p


def _records(env):
    if not env["runs"].is_file():
        return []
    return [json.loads(line) for line in env["runs"].read_text(encoding="utf-8").splitlines()]


# ------------------------------------------------------------- write side
def test_skill_call_is_recorded_through_the_meter(env):
    _meter(env, "Skill", {"skill": "comd_checkpoint", "args": "--mini"})
    recs = _records(env)
    assert len(recs) == 1
    r = recs[0]
    assert (r["kind"], r["name"], r["ok"], r["session_id"]) == ("skill", "comd_checkpoint", True, "sess-1")
    assert set(r) == {"ts", "session_id", "kind", "name", "ok"}


def test_agent_call_is_recorded_with_default_type(env):
    _meter(env, "Agent", {"subagent_type": "agnt_done-verifier", "prompt": "verify x"})
    _meter(env, "Agent", {"prompt": "no type given"})
    assert [(r["kind"], r["name"]) for r in _records(env)] == [
        ("agent", "agnt_done-verifier"), ("agent", "general-purpose")]


def test_prompt_and_args_text_are_never_persisted(env):
    secret = "customer IBAN DE89370400440532013000 and a long free-text brief"
    _meter(env, "Skill", {"skill": "skil_client-comms", "args": secret})
    _meter(env, "Agent", {"subagent_type": "Explore", "prompt": secret, "description": secret})
    raw = env["runs"].read_text(encoding="utf-8")
    assert "IBAN" not in raw and "brief" not in raw


def test_non_identifier_name_is_dropped(env):
    _meter(env, "Skill", {"skill": "not an id; rm -rf /"})
    _meter(env, "Skill", {"skill": "x" * 200})
    assert _records(env) == []


def test_other_tools_record_nothing(env):
    _meter(env, "Read", {"file_path": "C:/x/y.md"})
    _meter(env, "Bash", {"command": "echo hi"})
    assert _records(env) == []


def test_error_response_records_ok_false(env):
    _meter(env, "Skill", {"skill": "comd_deploy"}, tool_response={"is_error": True})
    assert _records(env)[0]["ok"] is False


def test_unwritable_telemetry_dir_never_breaks_the_meter(env, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a directory should be", encoding="utf-8")
    env["env"]["AGENTIC_OPS_TELEMETRY_DIR"] = str(blocker / "sub")
    p = _meter(env, "Skill", {"skill": "comd_resume"})
    assert p.returncode == 0


# -------------------------------------------------------------- stocktake
def _tree(root):
    skills = root / ".claude" / "skills"
    (skills / "skil_alpha").mkdir(parents=True)
    (skills / "skil_alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Build alpha widgets for the alpha pipeline when asked to.\n---\nbody\n",
        encoding="utf-8")
    (skills / "skil_beta").mkdir()
    (skills / "skil_beta" / "SKILL.md").write_text(
        "---\nname: beta\ndescription:\n  Folded multi-line description that is long enough\n"
        "  to route on without any trouble at all.\n---\n" + "line\n" * 600,
        encoding="utf-8")
    (skills / "skil_stub").mkdir()
    (skills / "skil_stub" / "SKILL.md").write_text(
        "---\nname: stub\ndescription: \"Consolidated into skil_alpha. See alpha.\"\n---\n",
        encoding="utf-8")
    (skills / "skil_host").mkdir()
    (skills / "skil_host" / "SKILL.md").write_text(
        "---\nname: host\ndescription: \"Consolidated into skil_alpha.\"\n---\n", encoding="utf-8")
    (skills / "skil_host" / "modules").mkdir()
    (skills / "skil_host" / "modules" / "m.md").write_text("m", encoding="utf-8")
    cmds = root / ".claude" / "commands"
    cmds.mkdir(parents=True)
    (cmds / "comd_gamma.md").write_text("---\ndescription: Short\n---\n", encoding="utf-8")
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "agnt_delta.md").write_text(
        "---\nname: agnt_delta\ndescription: Verifies delta claims before they are surfaced to the user.\n---\n",
        encoding="utf-8")
    return root


def _stocktake(root, env, fmt="json"):
    p = subprocess.run([sys.executable, str(TOOLS / "skill_stocktake.py"), "--repo", str(root),
                        "--format", fmt], capture_output=True, text=True, timeout=60,
                       env={**__import__("os").environ, **env["env"]})
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout) if fmt == "json" else p.stdout


def _seed_runs(env, entries):
    env["runs"].parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    with env["runs"].open("a", encoding="utf-8") as fh:
        for days_ago, kind, name, ok in entries:
            ts = (now - timedelta(days=days_ago)).isoformat(timespec="seconds")
            fh.write(json.dumps({"ts": ts, "session_id": "s", "kind": kind, "name": name, "ok": ok}) + "\n")


def _verdicts(out):
    return {r["name"]: (r["verdict"], r["reason"]) for r in out["rows"]}


def test_zero_data_retires_nothing_and_says_so(tmp_path, env):
    root = _tree(tmp_path / "repo")
    out = _stocktake(root, env)
    assert out["meta"]["total_runs_90d"] == 0
    assert out["meta"]["retire_verdicts_enabled"] is False
    assert all(v != "Retire" for v, _ in _verdicts(out).values())
    text = _stocktake(root, env, fmt="text")
    assert "no Retire verdicts" in text and "not measured yet" in text


def test_static_verdicts(tmp_path, env):
    v = _verdicts(_stocktake(_tree(tmp_path / "repo"), env))
    assert v["skil_stub"][0] == "Merge" and "skil_alpha" in v["skil_stub"][1]
    assert v["skil_host"][0] == "Keep"          # stub that hosts modules stays
    assert v["skil_beta"][0] == "Improve"       # folded description parsed; 600+ lines
    assert "500-line" in v["skil_beta"][1]
    assert v["comd_gamma"][0] == "Improve"      # description too short
    assert v["skil_alpha"][0] == "Keep"


def test_retire_needs_coverage_and_zero_runs(tmp_path, env):
    root = _tree(tmp_path / "repo")
    # 45 days of history; alpha and delta used, gamma failing, nothing else used
    _seed_runs(env, [(45, "skill", "skil_alpha", True), (2, "skill", "alpha", True),
                     (10, "agent", "agnt_delta", True),
                     (1, "skill", "comd_gamma", False), (1, "skill", "comd_gamma", False),
                     (1, "skill", "comd_gamma", True),
                     (3, "skill", "document-skills:pdf", True)])
    out = _stocktake(root, env)
    v = _verdicts(out)
    rows = {r["name"]: r for r in out["rows"]}
    assert out["meta"]["retire_verdicts_enabled"] is True
    assert rows["skil_alpha"]["runs_90d"] == 2 and rows["skil_alpha"]["runs_30d"] == 1  # alias joined
    assert v["skil_alpha"][0] == "Keep"
    assert v["agnt_delta"][0] == "Keep"
    assert v["comd_gamma"][0] in ("Improve",)    # short desc wins over failure share; still Improve
    assert v["skil_beta"][0] == "Retire"         # zero runs across 45 days
    assert "skill:document-skills:pdf (1)" in out["meta"]["invoked_not_in_inventory"]


def test_failure_share_flags_improve(tmp_path, env):
    root = _tree(tmp_path / "repo")
    _seed_runs(env, [(40, "agent", "agnt_delta", False), (2, "agent", "agnt_delta", False),
                     (1, "agent", "agnt_delta", True)])
    v = _verdicts(_stocktake(root, env))
    assert v["agnt_delta"] == ("Improve", "2/3 recorded runs failed")


def test_telemetry_store_read_window_and_coverage(env):
    _seed_runs(env, [(100, "skill", "a", True), (5, "skill", "b", True)])
    assert [r["name"] for r in telemetry_store.read(telemetry_store.SKILL_RUNS, since_days=90)] == ["b"]
    assert 99 < telemetry_store.coverage_days(telemetry_store.SKILL_RUNS) < 101
