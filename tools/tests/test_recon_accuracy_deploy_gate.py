"""recon-accuracy-deploy-gate: regression tests (backlog item 127).

The gate runs `tools/recon_accuracy_check.py real` before a `flyctl deploy`
of brisken-expense-recon and returns permissionDecision="ask" when the score
dropped (exit 1) or could not be measured (exit 2 / timeout). Tests drive it
through the production-never seam RECON_ACCURACY_GATE_CMD, a JSON argv list
run without a shell, so no uv / scorer / client data is touched and the seam
decides the verdict on any platform.

The negative cases are the contract: a non-deploy command, a deploy of another
app, and text that merely mentions a deploy never consult the check at all,
which is why every one of them runs with a seam that would ASK if consulted.
"""
from __future__ import annotations

import json
import sys

from hooklib import permission_decision, run_hook

HOOK = "recon-accuracy-deploy-gate.py"
MARK = "SEAM OUTPUT LINE 4242"


def seam(exit_code: int) -> str:
    code = f"print({MARK!r}); raise SystemExit({exit_code})"
    return json.dumps([sys.executable, "-c", code])


def run(cmd: str, tmp_path, exit_code: int = 1, cwd: str | None = None):
    payload = {"tool_input": {"command": cmd}}
    if cwd is not None:
        payload["cwd"] = cwd
    return run_hook(
        HOOK, payload, cwd=tmp_path,
        env={"RECON_ACCURACY_GATE_CMD": seam(exit_code)},
    )


def _silent(p) -> bool:
    return p.returncode == 0 and p.stdout.strip() == ""


RECON_DEPLOY = "flyctl deploy -a brisken-expense-recon"


# --- never fires ------------------------------------------------------------

def test_non_deploy_command_is_silent(tmp_path):
    assert _silent(run("git status", tmp_path))


def test_empty_command_is_silent(tmp_path):
    assert _silent(run("", tmp_path))


def test_deploy_of_another_app_is_silent(tmp_path):
    assert _silent(run("flyctl deploy -a brisken-lead-desk", tmp_path))
    assert _silent(run("fly deploy --app=one-assessment-demo", tmp_path))


def test_bare_deploy_outside_the_module_is_silent(tmp_path):
    # No app flag, no mention of the module, cwd elsewhere: not ours.
    assert _silent(run("flyctl deploy", tmp_path, cwd=str(tmp_path)))


def test_commit_message_mentioning_deploy_is_silent(tmp_path):
    cmd = 'git commit -m "note: run flyctl deploy -a brisken-expense-recon after"'
    assert _silent(run(cmd, tmp_path))


def test_echo_mentioning_deploy_is_silent(tmp_path):
    assert _silent(run('echo "flyctl deploy -a brisken-expense-recon"', tmp_path))


# --- job A: a direct deploy of the recon app is denied ---------------------

def test_direct_recon_deploy_is_denied_without_consulting_the_check(tmp_path):
    # exit_code=0 would allow if the check were consulted; deny must not be.
    p = run(RECON_DEPLOY, tmp_path, exit_code=0)
    assert permission_decision(p.stdout) == "deny"
    assert "deploy.py" in p.stdout and "origin/main" in p.stdout
    assert MARK not in p.stdout


def test_documented_stamped_deploy_is_denied(tmp_path):
    # The operating.md recipe before 2026-09-25: stamped, and still stale-able.
    cmd = ('M=C:/r/workspace/clients/brisken/automations/expense-reconciliation; '
           'MSYS_NO_PATHCONV=1 flyctl deploy "$M" --config "$M/fly.toml" '
           '-a brisken-expense-recon --remote-only --build-arg GIT_COMMIT=abc')
    assert permission_decision(run(cmd, tmp_path).stdout) == "deny"


def test_image_rollback_by_hand_is_denied(tmp_path):
    cmd = "flyctl deploy -a brisken-expense-recon -i registry.fly.io/brisken-expense-recon:x"
    assert permission_decision(run(cmd, tmp_path).stdout) == "deny"


def test_bare_deploy_from_the_module_dir_is_denied(tmp_path):
    cwd = str(tmp_path / "workspace" / "clients" / "brisken" / "automations"
              / "expense-reconciliation")
    p = run("flyctl deploy", tmp_path, exit_code=0, cwd=cwd)
    assert permission_decision(p.stdout) == "deny"


def test_bare_deploy_naming_the_module_is_denied(tmp_path):
    cmd = ("( cd workspace/clients/brisken/automations/expense-reconciliation "
           "&& flyctl deploy )")
    assert permission_decision(run(cmd, tmp_path, exit_code=0).stdout) == "deny"


def test_powershell_call_operator_spelling_is_denied(tmp_path):
    p = run("& flyctl.exe deploy . -a brisken-expense-recon", tmp_path, exit_code=0)
    assert permission_decision(p.stdout) == "deny"


# --- job B: a deploy.py run is scored; the seam's exit code decides --------

SCRIPT = ("uv run C:/r/workspace/clients/brisken/automations/"
          "expense-reconciliation/deploy.py")


def test_script_deploy_with_check_passing_allows_silently(tmp_path):
    assert _silent(run(SCRIPT, tmp_path, exit_code=0))


def test_script_deploy_with_drop_asks_with_output(tmp_path):
    p = run(SCRIPT, tmp_path, exit_code=1)
    assert permission_decision(p.stdout) == "ask"
    assert MARK in p.stdout
    assert "BELOW ITS BASELINE" in p.stdout


def test_script_deploy_unmeasurable_asks(tmp_path):
    p = run(SCRIPT, tmp_path, exit_code=2)
    assert permission_decision(p.stdout) == "ask"
    assert "COULD NOT BE MEASURED" in p.stdout
    assert MARK in p.stdout


def test_script_via_variable_and_env_prefix_is_scored(tmp_path):
    cmd = ('M="C:/r/workspace/clients/brisken/automations/expense-reconciliation"; '
           'MSYS_NO_PATHCONV=1 uv run "$M/deploy.py"')
    assert permission_decision(run(cmd, tmp_path, exit_code=1).stdout) == "ask"


def test_powershell_script_spelling_is_scored(tmp_path):
    cmd = ('& uv run "C:\\r\\workspace\\clients\\brisken\\automations\\'
           'expense-reconciliation\\deploy.py"')
    assert permission_decision(run(cmd, tmp_path, exit_code=1).stdout) == "ask"


def test_script_dry_run_and_image_rollback_are_not_scored(tmp_path):
    assert _silent(run(SCRIPT + " --dry-run", tmp_path, exit_code=1))
    assert _silent(run(SCRIPT + " --image registry.fly.io/x:1", tmp_path, exit_code=1))


def test_script_mentioned_not_run_is_silent(tmp_path):
    for cmd in (
        "git add workspace/clients/brisken/automations/expense-reconciliation/deploy.py",
        "cat workspace/clients/brisken/automations/expense-reconciliation/deploy.py",
        'git commit -m "add expense-reconciliation/deploy.py"',
        "uv run pytest workspace/clients/brisken/automations/"
        "expense-reconciliation/tests/test_deploy_script.py",
    ):
        assert _silent(run(cmd, tmp_path, exit_code=1)), cmd


def test_another_projects_deploy_script_is_silent(tmp_path):
    assert _silent(run("uv run tools/local-web-deploy.py", tmp_path, exit_code=1))
    assert _silent(run("python C:/other/app/deploy.py", tmp_path, exit_code=1))


# --- fail-open --------------------------------------------------------------

def test_unparseable_seam_fails_open(tmp_path):
    # A seam that cannot start is reported as unmeasurable (ask), never a crash.
    p = run_hook(
        HOOK, {"tool_input": {"command": SCRIPT}}, cwd=tmp_path,
        env={"RECON_ACCURACY_GATE_CMD": json.dumps(["no-such-program-4242"])},
    )
    assert p.returncode == 0
    assert permission_decision(p.stdout) == "ask"
    assert "COULD NOT BE MEASURED" in p.stdout
