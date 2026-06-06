"""no-auto-commit-gate (B6): regression tests for the automatic three-band model.

Bands (see rule_no_auto_commit.md and the fixture README):
- Autonomous: feature-branch commit / non-main non-force push / gh pr create.
- Auto-merge (CI-gated): gh pr merge fires when CI is green, else falls to floor.
- Gated floor: push-to-main, force push, commit-on-main, deploy, tag, release,
  subtree push, pr-close, plus any non-green merge -> explicit order or ASK.

Isolation: the gate shells out to git (`git diff --cached`, `git rev-parse`),
so each hook subprocess runs with cwd = an isolated NON-git tmp dir. There the
prototype carve-out is inert and `git rev-parse` fails, so the branch is forced
explicitly via NO_AUTO_COMMIT_GATE_BRANCH and the CI verdict via
NO_AUTO_COMMIT_GATE_CI (both production-never test seams). Transcripts are
absolute paths, so cwd never affects their reading. AGENTIC_OPS_SESSION_STATE
is redirected into the tmp dir so the ask-path friction capture can't touch
live session state.
"""
from hooklib import FIXTURES, permission_decision, run_hook

FX = FIXTURES / "no-auto-commit-gate"
AUTH = str(FX / "auth.jsonl")        # user message: "ok ship it to PR and merge"
NO_AUTH = str(FX / "no-auth.jsonl")  # user message with no ship-order keyword


def _run(cmd, transcript, tmp_path, branch=None, ci=None):
    env = {"AGENTIC_OPS_SESSION_STATE": str(tmp_path / "sstate.json")}
    if branch is not None:
        env["NO_AUTO_COMMIT_GATE_BRANCH"] = branch
    if ci is not None:
        env["NO_AUTO_COMMIT_GATE_CI"] = ci
    return run_hook(
        "no-auto-commit-gate.py",
        {"tool_input": {"command": cmd}, "transcript_path": transcript},
        cwd=tmp_path,
        env=env,
    )


def _allowed(p):
    return p.returncode == 0 and p.stdout.strip() == ""


# --- non-ship-class / read-class ------------------------------------------

def test_A_non_ship_class_passes_silent(tmp_path):
    assert _allowed(_run("ls -la", "", tmp_path))


def test_E_read_class_git_does_not_fire(tmp_path):
    # The critical negative: a too-greedy ship regex would false-fire on reads.
    assert _allowed(_run("git log --oneline -5", "", tmp_path))


# --- Band 1: autonomous feature-branch lane --------------------------------

def test_commit_on_feature_branch_autonomous(tmp_path):
    assert _allowed(_run("git commit -m wip", NO_AUTH, tmp_path, branch="feature"))


def test_push_feature_branch_autonomous(tmp_path):
    assert _allowed(_run("git push origin HEAD", NO_AUTH, tmp_path, branch="feature"))


def test_pr_create_autonomous(tmp_path):
    assert _allowed(_run("gh pr create --title x --body y", NO_AUTH, tmp_path, branch="feature"))


# --- Band 3 floor: trunk / force / deploy / subtree ------------------------

def test_B_commit_on_main_asks(tmp_path):
    assert permission_decision(_run("git commit -m test", NO_AUTH, tmp_path, branch="main").stdout) == "ask"


def test_push_to_main_asks(tmp_path):
    assert permission_decision(_run("git push origin main", NO_AUTH, tmp_path, branch="feature").stdout) == "ask"


def test_force_push_asks(tmp_path):
    assert permission_decision(_run("git push --force origin feature", NO_AUTH, tmp_path, branch="feature").stdout) == "ask"


def test_deploy_command_asks(tmp_path):
    assert permission_decision(_run("vercel deploy --prod", NO_AUTH, tmp_path, branch="feature").stdout) == "ask"


def test_subtree_push_asks(tmp_path):
    cmd = "git subtree push --prefix=workspace/clients/x/automations repo main"
    assert permission_decision(_run(cmd, NO_AUTH, tmp_path, branch="feature").stdout) == "ask"


def test_C_floor_with_explicit_order_allows(tmp_path):
    # push-to-main is floor; the auth transcript carries an explicit order.
    assert _allowed(_run("git push origin main", AUTH, tmp_path, branch="feature"))


# --- Band 2: auto-merge gated on CI ----------------------------------------

def test_merge_ci_green_auto(tmp_path):
    assert _allowed(_run("gh pr merge 5 --squash", NO_AUTH, tmp_path, branch="feature", ci="green"))


def test_merge_ci_red_asks(tmp_path):
    assert permission_decision(_run("gh pr merge 5 --squash", NO_AUTH, tmp_path, branch="feature", ci="red").stdout) == "ask"


def test_merge_ci_red_with_explicit_order_allows(tmp_path):
    # "merge anyway" override: CI red but the user explicitly authorized.
    assert _allowed(_run("gh pr merge 5 --squash", AUTH, tmp_path, branch="feature", ci="red"))


def test_D_merge_missing_transcript_defaults_ask(tmp_path):
    # Non-green merge + no transcript -> floor -> ASK. CI forced red to stay
    # hermetic (no live `gh` call).
    assert permission_decision(_run("gh pr merge 99 --squash", "", tmp_path, branch="feature", ci="red").stdout) == "ask"
