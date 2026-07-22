"""Tests for .claude/hooks/git-stash-gate.py (G1 SS3 structural guard).

Decision matrix: stash CREATE and DESTROY forms -> permissionDecision "ask";
READ + DRAIN forms (`list`, `show`, `pop`, `apply`, `branch`) -> silent allow.
Quoted / heredoc mentions of `git stash` are not stashes.
"""
from __future__ import annotations

from hooklib import permission_decision, run_hook

HOOK = "git-stash-gate.py"
# Redirect the friction-candidate side effect away from live session state.
ENV = {"AGENTIC_OPS_SESSION_STATE": ""}


def decide(command: str, tool: str = "Bash") -> str | None:
    r = run_hook(HOOK, {"tool_name": tool, "tool_input": {"command": command}},
                 env=ENV)
    assert r.returncode == 0, r.stderr
    return permission_decision(r.stdout)


# ---- CREATE forms -> ask

def test_bare_stash_asks():
    assert decide("git stash") == "ask"


def test_stash_push_asks():
    assert decide('git stash push -m "wip before switch"') == "ask"


def test_stash_save_asks():
    assert decide("git stash save wip") == "ask"


def test_stash_with_flags_asks():
    assert decide("git stash -u") == "ask"


def test_stash_after_global_flags_asks():
    assert decide("git -C C:/Users/x/Repo/agentic-ops1 stash") == "ask"


def test_stash_in_chain_asks():
    assert decide("git add -A && git stash && git switch main") == "ask"


def test_powershell_exe_spelling_asks():
    assert decide('& "C:\\Program Files\\Git\\bin\\git.exe" stash',
                  tool="PowerShell") == "ask"


# ---- DESTROY forms -> ask (archive-first reason)

def test_stash_drop_asks_with_archive_reason():
    r = run_hook(HOOK, {"tool_name": "Bash",
                        "tool_input": {"command": "git stash drop stash@{0}"}},
                 env=ENV)
    assert permission_decision(r.stdout) == "ask"
    assert "archive" in r.stdout


def test_stash_clear_asks():
    assert decide("git stash clear") == "ask"


# ---- READ + DRAIN forms -> allow

def test_stash_list_allows():
    assert decide("git stash list") is None


def test_stash_show_allows():
    assert decide("git stash show -p stash@{0}") is None


def test_stash_pop_allows():
    assert decide("git stash pop") is None


def test_stash_apply_allows():
    assert decide("git stash apply stash@{1}") is None


def test_stash_branch_allows():
    assert decide("git stash branch wip/recovered stash@{0}") is None


# ---- non-stash / masked contexts -> allow

def test_commit_message_mention_allows():
    assert decide('git commit -m "docs: note that git stash is banned"') is None


def test_echo_mention_allows():
    assert decide('echo "never run git stash here"') is None


def test_heredoc_mention_allows():
    cmd = "cat <<'EOF'\nuse git stash never\nEOF"
    assert decide(cmd) is None


def test_unrelated_command_allows():
    assert decide("git status && git log --oneline -5") is None


def test_non_shell_tool_allows():
    r = run_hook(HOOK, {"tool_name": "Write",
                        "tool_input": {"command": "git stash"}}, env=ENV)
    assert permission_decision(r.stdout) is None
