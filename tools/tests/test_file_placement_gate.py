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
