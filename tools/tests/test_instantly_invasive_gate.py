"""instantly-invasive-gate (B5): mutating api.instantly.ai calls -> ask.

Reads pass through (any GET, plus the allowlisted read POST endpoints like
/leads/list and /campaigns/analytics). A -X POST/PUT/PATCH/DELETE to any other
path forces a permission stop. AGENTIC_OPS_SESSION_STATE is redirected so the
"ask"-path friction-candidate capture can't touch live state.
"""
from hooklib import permission_decision, run_hook


def _run(cmd, tmp_path):
    return run_hook(
        "instantly-invasive-gate.py",
        {"tool_input": {"command": cmd}},
        env={"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "s.json")},
    )


def test_non_instantly_passes(tmp_path):
    p = _run("curl -X POST https://api.example.com/x -d '{}'", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_plain_get_passes(tmp_path):
    p = _run("curl https://api.instantly.ai/api/v2/accounts", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_read_path_post_passes(tmp_path):
    p = _run("curl -X POST https://api.instantly.ai/api/v2/leads/list -d '{}'", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_mutating_post_asks(tmp_path):
    p = _run("curl -X POST https://api.instantly.ai/api/v2/campaigns -d '{}'", tmp_path)
    assert permission_decision(p.stdout) == "ask"


def test_mutating_delete_asks(tmp_path):
    p = _run("curl -X DELETE https://api.instantly.ai/api/v2/leads/123", tmp_path)
    assert permission_decision(p.stdout) == "ask"
