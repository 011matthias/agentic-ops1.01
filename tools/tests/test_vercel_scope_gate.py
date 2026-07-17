"""vercel-scope-gate: regression tests for the akkton-session project boundary.

The gate restricts agent-issued Vercel commands to the platform project
(unpauseai.com) or the user's own scope; foreign akkton projects (lydar-app,
webvorschau-ka) force ask. Target-based, not verb-based: reads pass, foreign
markers always ask, unresolved mutations fail toward ask.
"""
import json

from hooklib import run_hook


def _run(cmd, tmp_path):
    env = {"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "sstate.json")}
    return run_hook(
        "vercel-scope-gate.py",
        {"tool_input": {"command": cmd}},
        cwd=tmp_path,
        env=env,
    )


def _allowed(p):
    return p.returncode == 0 and p.stdout.strip() == ""


def _asked(p):
    if p.returncode != 0 or not p.stdout.strip():
        return False
    out = json.loads(p.stdout)
    return out["hookSpecificOutput"]["permissionDecision"] == "ask"


# --- no vercel signal: silent pass ---

def test_non_vercel_command_passes(tmp_path):
    assert _allowed(_run("git status", tmp_path))


def test_unrelated_curl_passes(tmp_path):
    assert _allowed(_run("curl -s https://example.com", tmp_path))


# --- layer A: foreign-project tripwire ---

def test_lydar_by_name_asks(tmp_path):
    assert _asked(_run("vercel ls lydar-app --scope akktons-projects", tmp_path))


def test_lydar_by_project_id_asks(tmp_path):
    assert _asked(_run(
        'vercel api "/v9/projects/prj_Zk3VdKvdg4GGG9rzXXXXXXXX" --scope akktons-projects',
        tmp_path))


def test_lydar_by_domain_asks(tmp_path):
    assert _asked(_run("curl https://api.vercel.com/x?domain=app.lydar.com.br", tmp_path))


def test_webvorschau_asks(tmp_path):
    assert _asked(_run("vercel inspect webvorschau-ka", tmp_path))


def test_foreign_beats_platform_marker(tmp_path):
    # naming both projects still asks: the foreign tripwire is absolute
    assert _asked(_run(
        "vercel promote lydar-app --scope akktons-projects --project platform",
        tmp_path))


# --- layer B: user's own scope passes ---

def test_own_scope_deploy_passes(tmp_path):
    assert _allowed(_run(
        "vercel deploy --prod --scope matthias-neumanns-projects", tmp_path))


# --- layer C: explicit platform target passes ---

def test_platform_project_flag_passes(tmp_path):
    assert _allowed(_run(
        "vercel link --yes --project platform --scope akktons-projects", tmp_path))


def test_platform_project_id_passes(tmp_path):
    assert _allowed(_run(
        'vercel api "/v9/projects/prj_xMUV3AVgiAq9uXC9YaX0tMxQdAvl/env" --scope akktons-projects',
        tmp_path))


def test_unpauseai_domain_passes(tmp_path):
    assert _allowed(_run(
        "bash tools/vercel-force-deploy.sh --dir platform --domain unpauseai.com",
        tmp_path))


def test_projects_platform_api_path_passes(tmp_path):
    assert _allowed(_run(
        'vercel api "/v9/projects/platform" --scope akktons-projects', tmp_path))


# --- layer D: unresolved mutations ask; linked cwd passes ---

def test_bare_prod_deploy_unlinked_cwd_asks(tmp_path):
    assert _asked(_run("vercel --prod --force --yes", tmp_path))


def test_bare_promote_unlinked_cwd_asks(tmp_path):
    assert _asked(_run("vercel promote platform-abc123-akktons.vercel.app --yes", tmp_path))


def test_env_add_unlinked_cwd_asks(tmp_path):
    assert _asked(_run("vercel env add SOME_VAR production", tmp_path))


def test_bare_prod_deploy_platform_linked_cwd_passes(tmp_path):
    link = tmp_path / ".vercel"
    link.mkdir()
    (link / "project.json").write_text(json.dumps(
        {"projectId": "prj_xMUV3AVgiAq9uXC9YaX0tMxQdAvl", "orgId": "team_x"}),
        encoding="utf-8")
    assert _allowed(_run("vercel --prod --force --yes", tmp_path))


def test_mutating_api_call_without_marker_asks(tmp_path):
    assert _asked(_run(
        'curl -X DELETE "https://api.vercel.com/v9/projects/something?teamId=team_z"',
        tmp_path))


# --- layer E: reads pass ---

def test_whoami_passes(tmp_path):
    assert _allowed(_run("vercel whoami", tmp_path))


def test_teams_list_passes(tmp_path):
    assert _allowed(_run("vercel teams list", tmp_path))


def test_bare_ls_passes(tmp_path):
    assert _allowed(_run("vercel ls", tmp_path))


def test_api_get_read_passes(tmp_path):
    assert _allowed(_run(
        'vercel api "/v6/deployments?limit=5" --scope akktons-projects', tmp_path))
