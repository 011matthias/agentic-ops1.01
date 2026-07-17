"""optimize-run-gate: regression tests for the active-run file ACL.

Backs rule_optimize_loop.md. During an active optimize run the manifest's
asset globs are the only agent-writable repo surface; instructions, journal,
guards, scorers, and the enforcement machinery are locked. The shell arm
additionally closes scorer-lock-gate's acknowledged redirect bypass ALWAYS
(run or no run).

State fixtures are injected via the OPTIMIZE_RUN_STATE env seam; the hook
resolves rel-paths against the real repo (it only reads), so locked-path
cases use real repo paths.
"""
import importlib.util
import json

import pytest

from hooklib import HOOKS, REPO, permission_decision, run_hook

GATE = "optimize-run-gate.py"

ACTIVE_STATE = {
    "tag": "testrun",
    "branch": "optimize/testrun",
    "assets": ["workspace/demo/**"],
    "locked": [
        "docs/optimize/testrun/RUN.md",
        "docs/optimize/testrun/results.tsv",
        "tools/validate-html.py",
    ],
}

# Neutralize any ambient override seams so results are deterministic.
BASE_ENV = {"SCORER_LOCK_ALLOW": "", "OPTIMIZE_SCOPE_ALLOW": ""}


@pytest.fixture()
def state_file(tmp_path):
    p = tmp_path / "run.json"
    p.write_text(json.dumps(ACTIVE_STATE), encoding="utf-8")
    return str(p)


@pytest.fixture()
def no_state(tmp_path):
    return str(tmp_path / "absent.json")


@pytest.fixture()
def corrupt_state(tmp_path):
    p = tmp_path / "run.json"
    p.write_text("{not json", encoding="utf-8")
    return str(p)


def _env(state_path: str, **extra) -> dict:
    env = dict(BASE_ENV)
    env["OPTIMIZE_RUN_STATE"] = state_path
    env.update(extra)
    return env


def _file(relpath: str, state: str, tool: str = "Edit", **extra):
    return run_hook(
        GATE,
        {"tool_name": tool, "tool_input": {"file_path": str(REPO / relpath)}},
        cwd=REPO, env=_env(state, **extra),
    )


def _shell(cmd: str, state: str, tool: str = "Bash", **extra):
    return run_hook(
        GATE,
        {"tool_name": tool, "tool_input": {"command": cmd}},
        cwd=REPO, env=_env(state, **extra),
    )


def _classify(proc) -> str:
    d = permission_decision(proc.stdout)
    if d:
        return d
    out = proc.stdout.strip()
    if out:
        obj = json.loads(out)
        if (obj.get("hookSpecificOutput") or {}).get("additionalContext"):
            return "advise"
    return "pass"


# --- inactive: the everyday cost is one isfile check ------------------------

def test_inactive_pass_any_repo_path(no_state):
    assert _classify(_file("platform/src/app/page.tsx", no_state)) == "pass"


def test_inactive_pass_empty_payload(no_state):
    proc = run_hook(GATE, {}, cwd=REPO, env=_env(no_state))
    assert proc.returncode == 0 and _classify(proc) == "pass"


# --- shell arm, ALWAYS-on scorer surface (closes the v1 redirect bypass) ----

def test_always_deny_shell_redirect_into_scorer(no_state):
    proc = _shell("echo hacked > tools/scorers/page-weight.py", no_state)
    assert _classify(proc) == "deny"


def test_always_deny_shell_append_into_scorer(no_state):
    proc = _shell("echo x >> tools/scorers/page-weight.py", no_state)
    assert _classify(proc) == "deny"


def test_always_deny_sed_i_scorer(no_state):
    proc = _shell("sed -i 's/minimize/maximize/' tools/scorers/page-weight.py",
                  no_state)
    assert _classify(proc) == "deny"


def test_always_deny_ps_setcontent_scorer_backslash(no_state):
    proc = _shell(r"Set-Content -Path tools\scorers\page-weight.py -Value 'x'",
                  no_state, tool="PowerShell")
    assert _classify(proc) == "deny"


def test_always_deny_redirect_into_pins(no_state):
    proc = _shell("echo '{}' > tools/scorers/PINS.json", no_state)
    assert _classify(proc) == "deny"


def test_pass_running_scorer(no_state):
    proc = _shell("uv run tools/scorers/page-weight.py page.html", no_state)
    assert _classify(proc) == "pass"


def test_pass_reading_scorer_redirect_elsewhere(no_state):
    proc = _shell("cat tools/scorers/page-weight.py > .scratch/copy.py",
                  no_state)
    assert _classify(proc) == "pass"


def test_scorer_shell_write_advises_under_allow_seam(no_state):
    proc = _shell("echo fix > tools/scorers/page-weight.py", no_state,
                  SCORER_LOCK_ALLOW="1")
    assert _classify(proc) == "advise"


# --- corrupt state: must not become the unlock vector -----------------------

def test_corrupt_state_asks_on_repo_write(corrupt_state):
    assert _classify(_file("platform/src/x.ts", corrupt_state)) == "ask"


def test_corrupt_state_passes_out_of_repo(corrupt_state):
    proc = run_hook(
        GATE,
        {"tool_name": "Write",
         "tool_input": {"file_path": "C:/elsewhere/x.txt"}},
        cwd=REPO, env=_env(corrupt_state),
    )
    assert _classify(proc) == "pass"


# --- active run: asset scope is the only writable surface -------------------

def test_active_pass_asset_glob(state_file):
    assert _classify(_file("workspace/demo/index.html", state_file)) == "pass"


def test_active_pass_asset_backslash_path(state_file):
    proc = run_hook(
        GATE,
        {"tool_name": "Edit",
         "tool_input": {"file_path": str(REPO) + r"\workspace\demo\css\a.css"}},
        cwd=REPO, env=_env(state_file),
    )
    assert _classify(proc) == "pass"


def test_active_pass_redundant_slashes(state_file):
    proc = run_hook(
        GATE,
        {"tool_name": "Edit",
         "tool_input": {"file_path": f"{REPO}/workspace//demo/./x.css"}},
        cwd=REPO, env=_env(state_file),
    )
    assert _classify(proc) == "pass"


def test_active_deny_outside_scope_names_tag(state_file):
    proc = _file("platform/src/app/page.tsx", state_file)
    assert _classify(proc) == "deny"
    assert "testrun" in proc.stdout


def test_active_deny_manifest(state_file):
    assert _classify(_file("docs/optimize/testrun/RUN.md", state_file)) == "deny"


def test_active_deny_results_tsv(state_file):
    proc = _file("docs/optimize/testrun/results.tsv", state_file, tool="Write")
    assert _classify(proc) == "deny"


def test_active_deny_guard_file(state_file):
    assert _classify(_file("tools/validate-html.py", state_file)) == "deny"


def test_active_deny_command_file(state_file):
    proc = _file(".claude/commands/comd_optimize.md", state_file)
    assert _classify(proc) == "deny"


def test_active_deny_hooks_dir(state_file):
    proc = _file(".claude/hooks/optimize-run-gate.py", state_file)
    assert _classify(proc) == "deny"


def test_active_deny_wire_hooks(state_file):
    assert _classify(_file("tools/wire-hooks.py", state_file)) == "deny"


def test_active_deny_canonical_state_path(state_file):
    proc = _file(".claude/optimize/run.json", state_file, tool="Write")
    assert _classify(proc) == "deny"


def test_active_pass_scratch(state_file):
    assert _classify(_file(".scratch/notes.txt", state_file, tool="Write")) == "pass"


def test_active_pass_out_of_repo(state_file):
    proc = run_hook(
        GATE,
        {"tool_name": "Write",
         "tool_input": {"file_path": "C:/elsewhere/scratch.txt"}},
        cwd=REPO, env=_env(state_file),
    )
    assert _classify(proc) == "pass"


def test_active_scope_allow_downgrades_to_advise(state_file):
    proc = _file("platform/src/app/page.tsx", state_file,
                 OPTIMIZE_SCOPE_ALLOW="1")
    assert _classify(proc) == "advise"


def test_active_star_does_not_cross_directories(tmp_path):
    state = dict(ACTIVE_STATE, assets=["workspace/demo/*.html"])
    p = tmp_path / "run.json"
    p.write_text(json.dumps(state), encoding="utf-8")
    assert _classify(_file("workspace/demo/sub/x.html", str(p))) == "deny"
    assert _classify(_file("workspace/demo/x.html", str(p))) == "pass"


# --- active run, shell arm ---------------------------------------------------

def test_active_deny_tee_append_journal(state_file):
    proc = _shell("echo row | tee -a docs/optimize/testrun/results.tsv",
                  state_file)
    assert _classify(proc) == "deny"


def test_active_deny_git_checkout_locked_pathspec(state_file):
    proc = _shell("git checkout HEAD~3 -- tools/validate-html.py", state_file)
    assert _classify(proc) == "deny"


def test_active_pass_redirect_into_run_logs(state_file):
    proc = _shell(
        "uv run tools/scorers/page-weight.py x.html "
        "> docs/optimize/testrun/logs/r1.log 2>&1", state_file)
    assert _classify(proc) == "pass"


def test_active_deny_ps_remove_item_journal(state_file):
    proc = _shell("Remove-Item docs/optimize/testrun/results.tsv -Force",
                  state_file, tool="PowerShell")
    assert _classify(proc) == "deny"


# --- _globs.py unit behavior (the scope-widening trap) -----------------------

def _globs():
    spec = importlib.util.spec_from_file_location("_globs", HOOKS / "_globs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_globs_doublestar_crosses_segments():
    g = _globs()
    assert g.match_one("a/**/z.txt", "a/b/c/z.txt")
    assert g.match_one("a/**", "a/b/c/z.txt")
    assert g.match_one("a/**/z.txt", "a/z.txt")  # ** matches zero segments


def test_globs_single_star_stays_in_segment():
    g = _globs()
    assert g.match_one("a/*.txt", "a/z.txt")
    assert not g.match_one("a/*.txt", "a/b/z.txt")


def test_globs_trailing_slash_means_subtree():
    g = _globs()
    assert g.match_one("a/b/", "a/b/c/d.txt")
    assert not g.match_one("a/b/", "a/bc/d.txt")


def test_globs_question_mark_one_char():
    g = _globs()
    assert g.match_one("a/file?.txt", "a/file1.txt")
    assert not g.match_one("a/file?.txt", "a/file12.txt")
