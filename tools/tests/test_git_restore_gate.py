"""Tests for .claude/hooks/git-restore-gate.py (2026-08-24 intake_mail.py kill).

Decision matrix: worktree-overwriting git forms (`checkout -- path`,
`restore path`, `reset --hard`, `clean -f`, force switch/checkout) ->
permissionDecision "ask" when the targeted paths are dirty or the state is
undeterminable; silent allow when they are provably clean.

The NEGATIVE cases are the contract: read-class git, `restore --staged`,
branch switches, dry-run cleans, and quoted mentions must stay silent, or the
gate becomes a tax on ordinary git use and gets disabled.

GIT_RESTORE_GATE_STATUS is the porcelain seam -- it makes the matrix testable
without building throwaway repositories.
"""
from __future__ import annotations

from hooklib import load_hook, permission_decision, run_hook

HOOK = "git-restore-gate.py"
DIRTY = " M workspace/clients/brisken/automations/expense_recon/intake_mail.py"
UNTRACKED = "?? .scratch/probe.py"


def _env(status: str) -> dict:
    # Redirect the friction-candidate side effect away from live session state.
    return {"AGENTIC_OPS_SESSION_STATE": "", "GIT_RESTORE_GATE_STATUS": status}


def decide(command: str, status: str = DIRTY, tool: str = "Bash") -> str | None:
    r = run_hook(
        HOOK,
        {"tool_name": tool, "tool_input": {"command": command}},
        env=_env(status),
    )
    assert r.returncode == 0, r.stderr
    return permission_decision(r.stdout)


def reason(command: str, status: str = DIRTY) -> str:
    import json

    r = run_hook(
        HOOK,
        {"tool_name": "Bash", "tool_input": {"command": command}},
        env=_env(status),
    )
    obj = json.loads(r.stdout)
    return obj["hookSpecificOutput"]["permissionDecisionReason"]


# ---- The incident itself -------------------------------------------------

def test_checkout_double_dash_on_dirty_path_asks():
    """The exact 2026-08-24 command shape that destroyed intake_mail.py."""
    assert decide(
        "uv run pytest tests/ -q; git checkout -- "
        "workspace/clients/brisken/automations/expense_recon/intake_mail.py"
    ) == "ask"


def test_incident_reason_names_the_file_and_the_backup_trap():
    text = reason("git checkout -- expense_recon/intake_mail.py")
    assert "intake_mail.py" in text          # the file at risk is listed
    assert "backup" in text.lower()          # cp-from-backup, not git
    assert ".scratch/pre-restore" in text    # archive-first remedy


# ---- Worktree-overwriting forms -> ask when dirty -------------------------

def test_checkout_from_ref_with_paths_asks():
    assert decide("git checkout HEAD -- src/app.py") == "ask"


def test_checkout_dot_asks():
    assert decide("git checkout .") == "ask"


def test_checkout_bare_path_without_separator_asks():
    assert decide("git checkout tools/session_state.py") == "ask"


def test_restore_asks():
    assert decide("git restore tools/session_state.py") == "ask"


def test_restore_with_source_asks():
    assert decide("git restore --source=HEAD~2 tools/x.py") == "ask"


def test_reset_hard_asks():
    assert decide("git reset --hard origin/main") == "ask"


def test_clean_force_asks_on_untracked():
    assert decide("git clean -fd", status=UNTRACKED) == "ask"


def test_checkout_force_asks():
    assert decide("git checkout -f main") == "ask"


def test_switch_discard_changes_asks():
    assert decide("git switch --discard-changes main") == "ask"


def test_global_flags_do_not_evade():
    assert decide("git -C C:/Users/x/Repo/agentic-ops1 checkout -- a/b.py") == "ask"


def test_powershell_exe_spelling_asks():
    assert decide(
        '& "C:\\Program Files\\Git\\bin\\git.exe" reset --hard',
        tool="PowerShell",
    ) == "ask"


def test_chained_command_asks():
    assert decide("npm run build && git checkout -- src/") == "ask"


# ---- Clean tree -> silent allow (nothing to lose) ------------------------

def test_checkout_on_clean_path_allows():
    assert decide("git checkout -- src/app.py", status="") is None


def test_reset_hard_on_clean_tree_allows():
    assert decide("git reset --hard origin/main", status="") is None


def test_clean_ignores_tracked_modifications():
    """`git clean` only removes UNTRACKED files, so a tracked modification is
    not part of its risk set and must not trigger the prompt."""
    assert decide("git clean -fd", status=DIRTY) is None


# ---- Undeterminable state -> ask (never a new blind spot) ----------------

def test_unreadable_status_asks():
    assert decide("git checkout -- src/app.py", status="ERROR") == "ask"


def test_unreadable_status_says_so():
    text = reason("git checkout -- src/app.py", status="ERROR")
    assert "could NOT be read" in text


# ---- NEGATIVE cases: the contract ---------------------------------------

def test_restore_staged_only_allows():
    """`--staged` alone rewrites the index; the working tree is untouched."""
    assert decide("git restore --staged tools/x.py") is None


def test_restore_staged_with_worktree_asks():
    assert decide("git restore --staged --worktree tools/x.py") == "ask"


def test_plain_branch_switch_allows():
    assert decide("git checkout main") is None


def test_switch_branch_allows():
    assert decide("git switch client/brisken/deckgen-native") is None


def test_checkout_new_branch_allows():
    assert decide("git checkout -b sys/new-guards") is None


def test_clean_dry_run_allows():
    assert decide("git clean -nd", status=UNTRACKED) is None


def test_clean_without_force_allows():
    assert decide("git clean -d", status=UNTRACKED) is None


def test_reset_soft_allows():
    assert decide("git reset --soft HEAD~1") is None


def test_reset_default_allows():
    assert decide("git reset HEAD -- file.py") is None


def test_read_class_git_allows():
    for cmd in ("git status --porcelain", "git diff -- src/", "git log --oneline",
                "git show HEAD:tools/x.py", "git branch -v"):
        assert decide(cmd) is None, cmd


def test_quoted_mention_allows():
    assert decide('echo "run git checkout -- file to revert"') is None


def test_commit_message_mention_allows():
    assert decide('git commit -m "document git reset --hard recovery"') is None


def test_non_git_command_allows():
    assert decide("npm run build && uv run pytest -q") is None


def test_non_shell_tool_allows():
    assert decide("git checkout -- x.py", tool="Write") is None


# ---- Unit-level pins on the classifier ----------------------------------

mod = load_hook(HOOK)


def test_classify_extracts_paths_after_separator():
    kind, paths, _ = mod.classify("git checkout HEAD -- a/b.py c/d.py")
    assert kind == "checkout-paths"
    assert paths == ["a/b.py", "c/d.py"]


def test_classify_whole_tree_for_reset_hard():
    kind, paths, _ = mod.classify("git reset --hard")
    assert kind == "reset-hard"
    assert paths == []


def test_classify_none_for_branch_checkout():
    assert mod.classify("git checkout main") is None
