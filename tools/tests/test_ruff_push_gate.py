"""ruff-push-gate: regression tests for the local ruff-on-push check.

The gate runs the CI ruff step at `git push` time and, on failure, returns
permissionDecision="ask" with the ruff output inline. Tests drive it through
production-never env seams so no real uv/ruff/git is spawned for the verdict:

  RUFF_PUSH_GATE_FORCE_INSCOPE  "1"/"0" forces the scope decision.
  RUFF_PUSH_GATE_FORCE_RUFF     "pass"/"fail"/"<text>" forces the ruff verdict.
  RUFF_PUSH_GATE_ALLOW          "1" is the real deliberate-bypass override.

cwd = an isolated non-git tmp dir, so repo_root()'s `git rev-parse` fails
harmlessly (root=None) and the seams carry the decision.
"""
from hooklib import permission_decision, run_hook


def _run(cmd, tmp_path, inscope=None, ruff=None, allow=None):
    env = {}
    if inscope is not None:
        env["RUFF_PUSH_GATE_FORCE_INSCOPE"] = inscope
    if ruff is not None:
        env["RUFF_PUSH_GATE_FORCE_RUFF"] = ruff
    if allow is not None:
        env["RUFF_PUSH_GATE_ALLOW"] = allow
    return run_hook(
        "ruff-push-gate.py",
        {"tool_input": {"command": cmd}},
        cwd=tmp_path,
        env=env,
    )


def _allowed(p):
    return p.returncode == 0 and p.stdout.strip() == ""


# --- non-push commands never fire -----------------------------------------

def test_non_push_command_passes_silent(tmp_path):
    assert _allowed(_run("ls -la", tmp_path, inscope="1", ruff="fail"))


def test_read_class_git_does_not_fire(tmp_path):
    # `git log` must not be seen as a push even with a forced ruff failure.
    assert _allowed(_run("git log --oneline -5", tmp_path, inscope="1", ruff="fail"))


def test_git_commit_does_not_fire(tmp_path):
    assert _allowed(_run("git commit -m wip", tmp_path, inscope="1", ruff="fail"))


def test_empty_command_passes(tmp_path):
    assert _allowed(_run("", tmp_path))


# --- push out of ruff scope -> skip ---------------------------------------

def test_push_out_of_scope_passes_silent(tmp_path):
    # A docs-only / platform-only push (no .py in ruff scope) is not gated,
    # even if the tree would fail ruff.
    assert _allowed(_run("git push origin HEAD", tmp_path, inscope="0", ruff="fail"))


# --- push in scope, ruff clean -> allow ------------------------------------

def test_push_in_scope_ruff_clean_passes_silent(tmp_path):
    assert _allowed(_run("git push origin HEAD", tmp_path, inscope="1", ruff="pass"))


# --- push in scope, ruff fails -> ask --------------------------------------

def test_push_in_scope_ruff_fail_asks(tmp_path):
    p = _run("git push origin HEAD", tmp_path, inscope="1", ruff="fail")
    assert permission_decision(p.stdout) == "ask"


def test_ask_reason_carries_ruff_output(tmp_path):
    marker = "F401 [*] `widget` imported but unused"
    p = _run("git push origin HEAD", tmp_path, inscope="1", ruff=marker)
    assert permission_decision(p.stdout) == "ask"
    assert marker in p.stdout
    # And it names the local runner as the fix path.
    assert "preflight-hooks.py" in p.stdout


# --- Windows / PowerShell spelling is normalized ---------------------------

def test_windows_git_exe_push_is_seen_as_push(tmp_path):
    p = _run('git.exe push origin HEAD', tmp_path, inscope="1", ruff="fail")
    assert permission_decision(p.stdout) == "ask"


def test_force_push_still_linted(tmp_path):
    # Lint correctness is orthogonal to the ship band; a force push is linted too.
    p = _run("git push --force origin HEAD", tmp_path, inscope="1", ruff="fail")
    assert permission_decision(p.stdout) == "ask"


# --- explicit override bypasses --------------------------------------------

def test_allow_override_bypasses(tmp_path):
    assert _allowed(_run("git push origin HEAD", tmp_path,
                         inscope="1", ruff="fail", allow="1"))
