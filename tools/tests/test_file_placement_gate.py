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
import time

import pytest

from hooklib import REPO, load_wire_hooks, permission_decision, run_hook


def _run(relpath: str, tool: str = "Write", env: dict | None = None):
    fp = str(REPO / relpath)
    return run_hook(
        "file-placement-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": fp}},
        cwd=REPO,
        env=env,
    )


def _run_raw(abs_path: str, tool: str = "Write"):
    # Pass a raw absolute path string (str(REPO)+...) so redundant slashes /
    # dot-segments reach the hook unnormalized — pathlib would collapse them.
    return run_hook(
        "file-placement-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": abs_path}},
        cwd=REPO,
    )


# git-down seam: force the static is_gitignored() fallback.
NO_GIT = {"FILE_PLACEMENT_GATE_NO_GIT": "1"}


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


# --- hardening regressions (2026-06-18 adversarial review) -----------------

# Env templates are committable — must PASS (incl. 3 already-tracked files).
def test_pass_env_example_template_subdir():
    assert _classify(_run("tools/.env.example")) == "pass"


def test_pass_env_example_tracked_platform():
    assert _classify(_run("platform/.env.example")) == "pass"


def test_pass_env_example_in_templates_tree():
    assert _classify(_run("workspace/templates/client-automation/.env.example")) == "pass"


def test_pass_env_example_at_root():
    assert _classify(_run(".env.example")) == "pass"


def test_deny_real_env_production_still():
    # .env.production is NOT gitignored (.gitignore only has `.env` + `*.env.local`),
    # so it lands tracked -> deny. (.env.local itself is globally gitignored, so the
    # gate correctly PASSES it — already protected, can't be committed.)
    assert _classify(_run("tools/.env.production")) == "deny"


def test_pass_env_local_is_gitignored():
    assert _classify(_run("tools/.env.local")) == "pass"


def test_deny_bare_config_env_still():
    assert _classify(_run("docs/config.env")) == "deny"


# Common root config / meta files must PASS at root.
def test_pass_root_makefile():
    assert _classify(_run("Makefile")) == "pass"


def test_pass_root_package_json():
    assert _classify(_run("package.json")) == "pass"


def test_pass_root_pyproject():
    assert _classify(_run("pyproject.toml")) == "pass"


def test_pass_root_changelog():
    assert _classify(_run("CHANGELOG.md")) == "pass"


def test_pass_root_vercel_json():
    assert _classify(_run("vercel.json")) == "pass"


def test_deny_root_stray_report_unchanged():
    # The allowlist expansion must not let a genuine stray artifact through.
    assert _classify(_run("results.json")) == "deny"


# Durable source/test/doc starting with debug-/snapshot-/temp- must PASS.
def test_pass_debug_prefixed_python_tool():
    assert _classify(_run("tools/debug-helper.py")) == "pass"


def test_pass_snapshot_prefixed_source():
    assert _classify(_run("platform/src/lib/snapshot-utils.ts")) == "pass"


def test_pass_temp_prefixed_tool():
    assert _classify(_run("tools/temp-converter.py")) == "pass"


def test_pass_debug_prefixed_doc_already_tracked():
    assert _classify(_run(".claude/skills/next-best-practices/debug-tricks.md")) == "pass"


def test_pass_pattern_rule_home():
    # .claude/patterns/ is a sanctioned W2 home (rule_file_placement §2).
    assert _classify(_run(".claude/patterns/warn-new-rule.md")) == "pass"


# ...but hard scratch (dumps / state / .tmp / .bak) still DENY in tracked dirs.
def test_deny_api_dump_json():
    assert _classify(_run("docs/api-dump.json")) == "deny"


def test_deny_tmp_artifact():
    assert _classify(_run("platform/src/build.tmp")) == "deny"


def test_deny_bak_artifact():
    assert _classify(_run("tools/helper.bak")) == "deny"


# Secrets the original regex missed must now DENY into tracked paths.
def test_deny_yaml_credentials():
    assert _classify(_run("tools/credentials.yaml")) == "deny"


def test_deny_yml_secrets():
    assert _classify(_run("platform/src/secrets.yml")) == "deny"


def test_deny_ssh_private_key():
    assert _classify(_run("tools/id_rsa")) == "deny"


def test_deny_ed25519_key():
    assert _classify(_run("tools/id_ed25519")) == "deny"


def test_deny_deploy_key_extensionless():
    assert _classify(_run("scripts/deploy_key")) == "deny"


def test_deny_pkcs12_bundle():
    assert _classify(_run("tools/keystore.p12")) == "deny"


def test_deny_pfx_bundle():
    assert _classify(_run("platform/cert.pfx")) == "deny"


def test_deny_service_account_key():
    assert _classify(_run("tools/service-account.json")) == "deny"


def test_deny_service_account_camel_in_automations():
    assert _classify(_run("workspace/clients/brisken/automations/serviceAccountKey.json")) == "deny"


# ...but a public key and descriptively-named non-secret files must PASS.
def test_pass_public_ssh_key():
    assert _classify(_run("tools/id_rsa.pub")) == "pass"


def test_pass_api_key_python_module():
    assert _classify(_run("tools/api_key.py")) == "pass"


def test_pass_descriptive_secret_doc():
    assert _classify(_run("docs/references/secrets-rotation-guide.json")) == "pass"


# Token-bearing dotfiles -> ADVISE (not deny, not silent pass).
def test_advise_npmrc_in_tracked_subdir():
    assert _classify(_run("platform/.npmrc")) == "advise"


def test_advise_netrc():
    assert _classify(_run("tools/.netrc")) == "advise"


# Data/PII export -> ADVISE; a fixture export stays silent.
def test_advise_leads_export():
    assert _classify(_run("docs/leads-export.csv")) == "advise"


def test_pass_fixture_export_csv():
    assert _classify(_run("tools/fixtures/sample-export.csv")) == "pass"


# Path-trick: redundant slash / dot-segment must NOT downgrade root DENY.
def test_deny_double_slash_root():
    assert _classify(_run_raw(str(REPO) + "//results.json")) == "deny"


def test_deny_dot_segment_root():
    assert _classify(_run_raw(str(REPO) + "/./results.json")) == "deny"


# git-down static fallback must mirror the client-secret home (no false deny).
def test_nogit_secret_in_client_context_passes():
    assert _classify(_run("workspace/clients/brisken/context/token.json", env=NO_GIT)) == "pass"


def test_nogit_secret_in_context_portable_still_denies():
    # context/portable/ is the committable opt-in — a secret there is still denied.
    assert _classify(_run("workspace/clients/brisken/context/portable/token.json", env=NO_GIT)) == "deny"


def test_nogit_next_build_artifact_passes():
    assert _classify(_run("platform/.next/cache/snapshot-1.json", env=NO_GIT)) == "pass"


# --- registry consistency --------------------------------------------------

def test_gate_is_in_canonical_contract():
    mod = load_wire_hooks()
    assert "file-placement-gate.py" in mod.EXPECTED_HOOK_SCRIPTS
    wired = json.dumps(mod.CANONICAL_HOOKS)
    assert "file-placement-gate.py" in wired


# --- W1 new-file purpose check (rule_no_file_bloat §3) ---------------------
# Driven through the wired gate against a fixture tree: FILE_PLACEMENT_GATE_REPO
# points REPO at tmp_path, so the near-duplicate walk sees only the fixture.

@pytest.fixture
def w1_tree(tmp_path):
    files = [
        "workspace/clients/acme/context/piece1-status.md",
        "workspace/clients/acme/context/rollout-plan.md",
        "workspace/clients/acme/context/state-2026-05-20.json",
        "workspace/clients/acme/deliverables/README.md",
        "workspace/clients/acme/context/corpus-cache/rollout-plan.md",
        "workspace/clients/acme/automations/sync/rollout-plan.md",
        "workspace/projects/lab/notes/rollout-plan.md",
    ]
    for f in files:
        p = tmp_path / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return tmp_path


def _w1(root, rel, tool="Write"):
    return run_hook(
        "file-placement-gate.py",
        {"tool_name": tool, "tool_input": {"file_path": str(root / rel)}},
        cwd=root,
        env={"FILE_PLACEMENT_GATE_REPO": str(root), "FILE_PLACEMENT_GATE_NO_GIT": "1"},
    )


def _reason(proc):
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


def test_w1_asks_on_revision_of_existing_file(w1_tree):
    p = _w1(w1_tree, "workspace/clients/acme/deliverables/rollout-plan-v2.md")
    assert permission_decision(p.stdout) == "ask"
    reason = _reason(p)
    assert "workspace/clients/acme/context/rollout-plan.md" in reason
    assert "does an existing file already fit" in reason
    # cache dirs and automations/ are not candidates; other projects are not either
    assert "corpus-cache" not in reason and "automations" not in reason
    assert "projects/lab" not in reason


@pytest.mark.parametrize("name", ["rollout-plan-2026-09-17.md", "rollout-plan-final.md",
                                  "rollout plan copy.md", "Rollout_Plan_v3.md"])
def test_w1_asks_on_dated_final_and_copy_variants(w1_tree, name):
    p = _w1(w1_tree, f"workspace/clients/acme/context/{name}")
    assert permission_decision(p.stdout) == "ask"


def test_w1_asks_on_snapshot_shape_without_duplicate(w1_tree):
    p = _w1(w1_tree, "workspace/projects/lab/notes/lead-analysis.md")
    assert permission_decision(p.stdout) == "ask"
    assert "snapshot-shaped" in _reason(p)


def test_w1_silent_on_a_genuinely_new_file(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/vendor-contacts.md")) == "pass"


def test_w1_different_piece_is_not_a_duplicate(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/piece2-status.md")) == "pass"


def test_w1_other_kind_is_not_a_duplicate(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/rollout-plan.py")) == "pass"


def test_w1_generic_stem_is_exempt(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/README.md")) == "pass"


def test_w1_skips_automations_and_scratch(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/automations/sync/rollout-plan-v2.md")) == "pass"
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/.scratch/rollout-plan-v2.md")) == "pass"


def test_w1_overwrite_of_existing_file_is_silent(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/rollout-plan.md")) == "pass"


def test_w1_edit_is_never_gated(w1_tree):
    assert _classify(_w1(w1_tree, "workspace/clients/acme/context/rollout-plan-v2.md", tool="Edit")) == "pass"


def test_w1_outside_client_and_project_trees_is_silent(w1_tree):
    assert _classify(_w1(w1_tree, "docs/rollout-plan-v2.md")) == "pass"


def test_w1_placement_deny_still_wins(w1_tree):
    # A scratch-shaped name in a non-gitignored path is a W2 deny, not a W1 ask.
    p = _w1(w1_tree, "workspace/clients/acme/deliverables/rollout-plan-dump.json")
    assert permission_decision(p.stdout) == "deny"


def test_w1_budget_on_a_large_tree(tmp_path):
    ctx = tmp_path / "workspace" / "clients" / "big" / "context"
    for i in range(3000):
        d = ctx / f"dir{i % 30}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"note-{i}-{i * 7919 % 1000}.md").write_text("x", encoding="utf-8")
    start = time.perf_counter()
    p = _w1(tmp_path, "workspace/clients/big/context/fresh-topic.md")
    elapsed = time.perf_counter() - start
    assert _classify(p) == "pass"
    assert elapsed < 2.0, f"{elapsed:.3f}s"  # loose: includes interpreter startup on CI
