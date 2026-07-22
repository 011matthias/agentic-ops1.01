"""branch-isolation-gate (G1): regression tests for the advisory guard.

Backs rule_branch_isolation_and_shared_ledger.md §2. The gate ADVISES (never
denies) when a Write/Edit targets a tracked workspace/clients/{X}/** file and
the current branch is not a branch for client X. Gitignored targets and
non-client paths pass silently.

Isolation: the branch is forced via the BRANCH_ISOLATION_GATE_BRANCH test
seam and the gitignore verdict via BRANCH_ISOLATION_GATE_IGNORED, so the
tests are independent of the developer's live checkout state. One test runs
without the ignore seam to validate the real `git check-ignore` path against
the actual .gitignore (client context/ is ignored).
"""
import json

from hooklib import REPO, permission_decision, run_hook


def _run(relpath: str, branch: str, tool: str = "Write", ignored: str = "0"):
    fp = str(REPO / relpath)
    env = {
        "BRANCH_ISOLATION_GATE_BRANCH": branch,
        "BRANCH_ISOLATION_GATE_IGNORED": ignored,
    }
    return run_hook(
        "branch-isolation-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": fp}},
        cwd=REPO,
        env=env,
    )


def _classify(proc) -> str:
    assert permission_decision(proc.stdout) is None, "gate must never deny"
    out = proc.stdout.strip()
    if out:
        obj = json.loads(out)
        if (obj.get("hookSpecificOutput") or {}).get("additionalContext"):
            return "advise"
    return "pass"


CLIENT_FILE = "workspace/clients/brisken/status/p2-rome.md"


# --- ADVISE: the G1 violations -------------------------------------------

def test_advise_client_file_on_main():
    proc = _run(CLIENT_FILE, branch="main")
    assert _classify(proc) == "advise"
    assert "client/brisken/" in proc.stdout


def test_advise_client_file_on_other_clients_branch():
    proc = _run(CLIENT_FILE, branch="client/meji-media/warm-rebuild")
    assert _classify(proc) == "advise"


def test_advise_client_file_on_system_branch():
    assert _classify(_run(CLIENT_FILE, branch="sys/doctor-runner")) == "advise"


def test_advise_client_file_on_docs_branch():
    # Ledger branches must not carry client-file edits (G1 §1).
    assert _classify(_run(CLIENT_FILE, branch="docs/ledger-sync")) == "advise"


def test_advise_fires_for_edit_tool_too():
    assert _classify(_run(CLIENT_FILE, branch="main", tool="Edit")) == "advise"


# --- PASS: matching branch families --------------------------------------

def test_pass_on_canonical_client_branch():
    assert _classify(_run(CLIENT_FILE, branch="client/brisken/rome-t3")) == "pass"


def test_pass_on_legacy_client_prefix_branch():
    assert _classify(_run(CLIENT_FILE, branch="brisken/recon-guide-refresh")) == "pass"


def test_pass_on_sanctioned_extra_family():
    # brisken's leadgen/task-N session branches are sanctioned (memory
    # project_brisken_rome_leadgen_task_branches).
    assert _classify(_run(CLIENT_FILE, branch="leadgen/task-6")) == "pass"


def test_client_match_is_case_insensitive():
    assert _classify(_run(CLIENT_FILE, branch="client/Brisken/x")) == "pass"


# --- PASS: out-of-scope targets ------------------------------------------

def test_pass_non_client_path_on_main():
    assert _classify(_run("tools/doctor.py", branch="main")) == "pass"


def test_pass_gitignored_client_target():
    # context/ is the gitignored client home — never commits, no advisory.
    proc = _run(
        "workspace/clients/brisken/context/comms-log.md",
        branch="main",
        ignored="1",
    )
    assert _classify(proc) == "pass"


def test_pass_gitignored_verdict_from_real_git():
    # No ignore seam: the real .gitignore marks client context/ as ignored.
    fp = str(REPO / "workspace/clients/brisken/context/comms-log.md")
    proc = run_hook(
        "branch-isolation-gate.py",
        {"tool_name": "Write", "tool_input": {"file_path": fp}},
        cwd=REPO,
        env={"BRANCH_ISOLATION_GATE_BRANCH": "main"},
    )
    assert _classify(proc) == "pass"


def test_pass_other_tools():
    assert _classify(_run(CLIENT_FILE, branch="main", tool="Bash")) == "pass"


def test_pass_detached_head():
    assert _classify(_run(CLIENT_FILE, branch="HEAD")) == "pass"


def test_pass_empty_payload():
    proc = run_hook("branch-isolation-gate.py", {}, cwd=REPO)
    assert proc.returncode == 0
    assert _classify(proc) == "pass"
