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


# --- fires: the seam's exit code decides ----------------------------------

def test_recon_deploy_with_check_passing_allows_silently(tmp_path):
    assert _silent(run(RECON_DEPLOY, tmp_path, exit_code=0))


def test_recon_deploy_with_drop_asks_with_output(tmp_path):
    p = run(RECON_DEPLOY, tmp_path, exit_code=1)
    assert permission_decision(p.stdout) == "ask"
    assert MARK in p.stdout
    assert "BELOW ITS BASELINE" in p.stdout


def test_recon_deploy_unmeasurable_asks(tmp_path):
    p = run(RECON_DEPLOY, tmp_path, exit_code=2)
    assert permission_decision(p.stdout) == "ask"
    assert "COULD NOT BE MEASURED" in p.stdout
    assert MARK in p.stdout


def test_bare_deploy_from_the_module_dir_fires(tmp_path):
    cwd = str(tmp_path / "workspace" / "clients" / "brisken" / "automations"
              / "expense-reconciliation")
    p = run("flyctl deploy", tmp_path, exit_code=1, cwd=cwd)
    assert permission_decision(p.stdout) == "ask"


def test_bare_deploy_naming_the_module_fires(tmp_path):
    cmd = ("( cd workspace/clients/brisken/automations/expense-reconciliation "
           "&& flyctl deploy )")
    p = run(cmd, tmp_path, exit_code=1)
    assert permission_decision(p.stdout) == "ask"


# --- Windows / PowerShell spelling is normalized ---------------------------

def test_powershell_call_operator_spelling_is_seen(tmp_path):
    p = run("& flyctl.exe deploy . -a brisken-expense-recon", tmp_path, exit_code=1)
    assert permission_decision(p.stdout) == "ask"
    assert MARK in p.stdout


def test_powershell_spelling_passes_when_check_passes(tmp_path):
    assert _silent(run("& flyctl.exe deploy . -a brisken-expense-recon",
                       tmp_path, exit_code=0))


# --- fail-open --------------------------------------------------------------

def test_unparseable_seam_fails_open(tmp_path):
    # A seam that cannot start is reported as unmeasurable (ask), never a crash.
    p = run_hook(
        HOOK, {"tool_input": {"command": RECON_DEPLOY}}, cwd=tmp_path,
        env={"RECON_ACCURACY_GATE_CMD": json.dumps(["no-such-program-4242"])},
    )
    assert p.returncode == 0
    assert permission_decision(p.stdout) == "ask"
    assert "COULD NOT BE MEASURED" in p.stdout
