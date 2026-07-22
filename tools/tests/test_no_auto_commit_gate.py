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
# Names the override explicitly, which a non-green merge requires (a generic
# ship word must NOT authorize landing code the user never saw pass).
MERGE_ANYWAY = str(FX / "merge-anyway.jsonl")


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


def test_merge_ci_red_with_explicit_override_allows(tmp_path):
    # An order that NAMES the override ("merge anyway") clears a red merge.
    assert _allowed(_run("gh pr merge 5 --squash", MERGE_ANYWAY, tmp_path,
                         branch="feature", ci="red"))


def test_merge_ci_red_generic_ship_word_still_asks(tmp_path):
    """The 2026-07-22 incident, pinned.

    The transcript says "ok ship it to PR and merge" -- a generic ship order
    that authorizes every other gated-floor action. It must NOT authorize a
    NON-GREEN merge: that lands code the user never saw pass. Live cost: a
    stale "deploy" order (meant for a Vercel deploy) auto-merged a PR whose
    hooks job had just failed, turning main red.
    """
    assert permission_decision(
        _run("gh pr merge 5 --squash", AUTH, tmp_path,
             branch="feature", ci="red").stdout) == "ask"


def test_merge_ci_pending_generic_ship_word_asks(tmp_path):
    assert permission_decision(
        _run("gh pr merge 5 --squash", AUTH, tmp_path,
             branch="feature", ci="pending").stdout) == "ask"


def test_generic_ship_word_still_authorizes_other_floor_actions(tmp_path):
    """The narrowing is merge-specific: a push to main still clears on it."""
    assert _allowed(_run("git push origin main", AUTH, tmp_path, branch="main"))


def test_D_merge_missing_transcript_defaults_ask(tmp_path):
    # Non-green merge + no transcript -> floor -> ASK. CI forced red to stay
    # hermetic (no live `gh` call).
    assert permission_decision(_run("gh pr merge 99 --squash", "", tmp_path, branch="feature", ci="red").stdout) == "ask"


# --- 2026-07-10: PowerShell / .cmd spellings (normalized matching view) -----
# Recorded live bypasses: `& "$nodeDir\vercel.cmd" deploy --prod` ran through
# the PowerShell tool unseen. Detection now runs on _shell.normalize_command.

def test_ps_call_operator_vercel_cmd_deploy_asks(tmp_path):
    p = _run(
        '& "$nodeDir\\vercel.cmd" deploy --prod --yes --cwd platform 2>&1 '
        "| Select-Object -Last 8",
        NO_AUTH, tmp_path, branch="feature",
    )
    assert permission_decision(p.stdout) == "ask"


def test_ps_bare_vercel_cmd_deploy_asks(tmp_path):
    p = _run("vercel.cmd deploy --yes", NO_AUTH, tmp_path, branch="feature")
    assert permission_decision(p.stdout) == "ask"


def test_ps_flyctl_exe_deploy_asks(tmp_path):
    p = _run('& "$d\\flyctl.exe" deploy', NO_AUTH, tmp_path, branch="feature")
    assert permission_decision(p.stdout) == "ask"


def test_ps_git_exe_push_main_asks(tmp_path):
    p = _run("git.exe push origin main", NO_AUTH, tmp_path, branch="feature")
    assert permission_decision(p.stdout) == "ask"


def test_ps_npm_cmd_build_not_ship_class(tmp_path):
    # Negative FP pin: a normalized npm build is still not ship-class.
    assert _allowed(_run('& "$nodeDir\\npm.cmd" run build 2>&1', NO_AUTH, tmp_path, branch="feature"))


# --- optimize engine exemption (a ship verb inside --desc must not trip) ----

def test_optimize_engine_round_desc_mentioning_ship_verb_is_allowed(tmp_path):
    cmd = ('uv run tools/optimize_run.py round '
           '--desc "revert the git push --force change"')
    assert _allowed(_run(cmd, NO_AUTH, tmp_path, branch="optimize/t1"))


def test_optimize_engine_start_is_allowed(tmp_path):
    assert _allowed(_run("uv run tools/optimize_run.py start t1", NO_AUTH,
                         tmp_path, branch="optimize/t1"))


def test_real_git_push_still_gated_alongside_engine_exemption(tmp_path):
    # the exemption is program-scoped; a bare ship command is unaffected
    assert permission_decision(
        _run("git push origin main", NO_AUTH, tmp_path, branch="feature").stdout
    ) == "ask"
