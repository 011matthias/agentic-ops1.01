"""file-placement-gate (W2): regression tests for the deterministic floor.

Backs rule_file_placement.md. The gate classifies a Write target by path +
basename pattern and:
  DENY     new root file (not allowlisted) / never-commit-into-tracked /
           scratch-pattern-into-non-gitignored
  ADVISE   unknown top-level dir (no established home)
  PASS     known home / edits / correctly-gitignored ephemeral

Isolation: the gate shells out to `git check-ignore`, so paths are built
under the REAL repo root (hooklib.REPO) and cwd = REPO. That validates the
deny/pass split against the actual .gitignore (including the .scratch/ line
this change adds), not a mock. check-ignore does not require the file to
exist on disk, so nonexistent target paths classify correctly.
"""
import json

from hooklib import REPO, load_wire_hooks, permission_decision, run_hook


def _run(relpath: str, tool: str = "Write"):
    fp = str(REPO / relpath)
    return run_hook(
        "file-placement-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": fp}},
        cwd=REPO,
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


# --- DENY: the three hard-floor violations -------------------------------

def test_deny_new_root_file():
    assert _classify(_run("report.md")) == "deny"


def test_deny_root_generated_artifact():
    assert _classify(_run("output.json")) == "deny"


def test_deny_never_commit_into_tracked():
    # config.env is NOT matched by the literal `.env` gitignore rule, so it
    # would land tracked -> deny.
    assert _classify(_run("platform/src/config.env")) == "deny"


def test_deny_credentials_into_tracked():
    assert _classify(_run("tools/api-credentials.json")) == "deny"


def test_deny_scratch_pattern_in_tracked_spec_dir():
    assert _classify(_run("workspace/clients/brisken/specs/scratch-analysis.json")) == "deny"


def test_deny_state_dump_in_docs():
    assert _classify(_run("docs/state-2026-06-18.json")) == "deny"


# --- PASS: representative correct routings (the routing check) ------------

def test_pass_client_automation_code():
    assert _classify(_run("workspace/clients/brisken/automations/sync.py")) == "pass"


def test_pass_spec():
    assert _classify(_run("workspace/clients/brisken/specs/1-spec/p3-lead-gen.md")) == "pass"


def test_pass_internal_doc():
    assert _classify(_run("docs/sessions/2026-06-18.md")) == "pass"


def test_pass_client_deliverable():
    assert _classify(_run("workspace/clients/brisken/deliverables/statement.html")) == "pass"


def test_pass_repo_tool():
    assert _classify(_run("tools/new-helper.py")) == "pass"


def test_pass_data_fixture():
    assert _classify(_run("tools/fixtures/sample-rows.json")) == "pass"


def test_pass_scratch_home():
    # The whole point of .scratch/ — a debug render with a scratch name is fine.
    assert _classify(_run(".scratch/debug-render.html")) == "pass"


def test_pass_root_allowlisted_file():
    assert _classify(_run("README.md")) == "pass"


def test_pass_secret_in_gitignored_client_context():
    # token.json into the gitignored context/ tree is correctly hidden.
    assert _classify(_run("workspace/clients/brisken/context/api-credentials.json")) == "pass"


def test_pass_scratch_name_in_gitignored_area():
    assert _classify(_run("api-docs/tmp-dump.json")) == "pass"


def test_pass_edit_is_never_gated():
    # Editing an existing file — even a root-shaped path — is out of scope.
    assert _classify(_run("report.md", tool="Edit")) == "pass"


def test_pass_out_of_repo_write():
    fp = str(REPO.parent / "some-other-place" / "foo.py")
    proc = run_hook(
        "file-placement-gate.py",
        {"tool_name": "Write", "tool_input": {"file_path": fp}},
        cwd=REPO,
    )
    assert _classify(proc) == "pass"


# --- ADVISE: ambiguous / tolerated -----------------------------------------

def test_advise_unknown_top_level_dir():
    assert _classify(_run("data/raw-export.csv")) == "advise"


def test_advise_already_ignored_root_artifact():
    # /after-*.jpeg is an existing gitignore root-glob (shot tooling) — tolerate
    # but nudge to .scratch/. Not a deny.
    assert _classify(_run("after-hero.jpeg")) == "advise"


# --- registry consistency --------------------------------------------------

def test_gate_is_in_canonical_contract():
    mod = load_wire_hooks()
    assert "file-placement-gate.py" in mod.EXPECTED_HOOK_SCRIPTS
    wired = json.dumps(mod.CANONICAL_HOOKS)
    assert "file-placement-gate.py" in wired
