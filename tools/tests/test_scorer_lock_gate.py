"""scorer-lock-gate: regression tests for the locked-scorer floor.

Backs tools/scorers/README.md (the /comd_optimize loop). The gate makes
goalpost-moving structural:
  DENY     Write/Edit on an EXISTING tools/scorers/*.py
  ADVISE   creating a NEW tools/scorers/*.py (authoring is allowed)
  ADVISE   scorer writes under the SCORER_LOCK_ALLOW=1 maintenance seam
  PASS     README under scorers/, other paths, other tools, out-of-repo

Existing-file cases use the real committed scorer (tools/scorers/
page-weight.py), so the suite also pins the convention that at least one
scorer ships with the gate.
"""
import json

from hooklib import REPO, permission_decision, run_hook

EXISTING = "tools/scorers/page-weight.py"


def _run(relpath: str, tool: str = "Edit", env: dict | None = None):
    return run_hook(
        "scorer-lock-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": str(REPO / relpath)}},
        cwd=REPO,
        env=env,
    )


def _classify(proc) -> str:
    if permission_decision(proc.stdout) == "deny":
        return "deny"
    out = proc.stdout.strip()
    if out:
        obj = json.loads(out)
        if (obj.get("hookSpecificOutput") or {}).get("additionalContext"):
            return "advise"
    return "pass"


# --- DENY: editing an existing scorer is goalpost-moving -------------------

def test_deny_edit_existing_scorer():
    assert _classify(_run(EXISTING, tool="Edit")) == "deny"


def test_deny_write_overwrite_existing_scorer():
    assert _classify(_run(EXISTING, tool="Write")) == "deny"


def test_deny_survives_backslash_path():
    proc = run_hook(
        "scorer-lock-gate.py",
        {"tool_name": "Edit",
         "tool_input": {"file_path": str(REPO) + "\\tools\\scorers\\page-weight.py"}},
        cwd=REPO,
    )
    assert _classify(proc) == "deny"


def test_deny_survives_redundant_slashes():
    proc = run_hook(
        "scorer-lock-gate.py",
        {"tool_name": "Edit",
         "tool_input": {"file_path": str(REPO) + "/tools//scorers/./page-weight.py"}},
        cwd=REPO,
    )
    assert _classify(proc) == "deny"


# --- ADVISE: authoring a new scorer / the maintenance seam ------------------

def test_new_scorer_creation_advises_not_denies():
    assert _classify(_run("tools/scorers/does-not-exist-yet.py", tool="Write")) == "advise"


def test_env_seam_allows_edit_with_advisory():
    proc = _run(EXISTING, tool="Edit", env={"SCORER_LOCK_ALLOW": "1"})
    assert _classify(proc) == "advise"


# --- PASS: everything outside the locked surface ----------------------------

def test_pass_scorers_readme():
    assert _classify(_run("tools/scorers/README.md", tool="Edit")) == "pass"


def test_pass_other_tools_path():
    assert _classify(_run("tools/validate-html.py", tool="Edit")) == "pass"


def test_pass_non_write_tool():
    assert _classify(_run(EXISTING, tool="Read")) == "pass"


def test_pass_out_of_repo_path():
    proc = run_hook(
        "scorer-lock-gate.py",
        {"tool_name": "Edit",
         "tool_input": {"file_path": "C:/elsewhere/tools/scorers/page-weight.py"}},
        cwd=REPO,
    )
    assert _classify(proc) == "pass"


def test_pass_empty_payload():
    proc = run_hook("scorer-lock-gate.py", {}, cwd=REPO)
    assert proc.returncode == 0 and _classify(proc) == "pass"
