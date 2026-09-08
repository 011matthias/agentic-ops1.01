"""Decision-matrix tests for .claude/hooks/msys-mangle-gate.py.

The gate is ADVISORY (additionalContext, never deny): it flags
MSYS-mangle-prone argument shapes on the Bash tool and names the
MSYS_NO_PATHCONV=1 remedy. Register rows 2026-07-22 + 2026-08-24 (x2)
spec the two shapes: <ref>:<path> git pathspecs and leading-slash
server-relative arguments. The negative cases here are the contract:
ordinary POSIX paths, drive-letter forms, URLs, and redirects must stay
silent, or the advisory becomes noise and gets ignored.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "hooks" / "msys-mangle-gate.py"
)


def run_hook(command: str, tool_name: str = "Bash") -> str:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }),
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def advisory(out: str) -> str | None:
    if not out:
        return None
    data = json.loads(out)
    return data["hookSpecificOutput"]["additionalContext"]


# --- advise: the two documented mangle shapes -------------------------------

def test_git_colon_pathspec_advises():
    out = advisory(run_hook("git show HEAD:docs/friction-register.md"))
    assert out and "[MSYS-MANGLE]" in out
    assert "HEAD:docs/friction-register.md" in out
    assert "MSYS_NO_PATHCONV=1" in out


def test_git_diff_treeish_pathspec_advises():
    out = advisory(run_hook("git diff abc1234:tools/foo.py def5678:tools/foo.py"))
    assert out and "abc1234:tools/foo.py" in out


def test_leading_slash_server_relative_advises():
    # The 2026-07-09 sp_upload.py shape from reference_repo_tooling_gotchas.
    out = advisory(run_hook(
        'uv run .scratch/sp_upload.py folders "/sites/MARKETING/Shared Documents"'
    ))
    assert out and "/sites/MARKETING/" in out


def test_option_assigned_leading_slash_advises():
    out = advisory(run_hook("mytool.exe --path=/sites/MARKETING/docs"))
    assert out and "/sites/MARKETING/docs" in out


# --- silent: remedy already applied ----------------------------------------

def test_no_pathconv_prefix_silent():
    assert run_hook(
        "MSYS_NO_PATHCONV=1 git show HEAD:docs/friction-register.md"
    ) == ""


# --- silent: shapes where conversion is intended or harmless ----------------

def test_posix_internal_dirs_silent():
    for cmd in (
        "ls /tmp/foo/bar",
        "cat /etc/hosts",
        "echo hi > /dev/null 2>&1",
        "/usr/bin/env python x.py",
        "rm -f /var/log/app/x.log",
    ):
        assert run_hook(cmd) == "", cmd


def test_drive_letter_form_silent():
    assert run_hook("grep foo /c/Users/x/Repo/file.txt") == ""


def test_unc_double_slash_silent():
    assert run_hook("ls //server/share/folder") == ""


def test_url_silent():
    assert run_hook("curl -s https://api.example.com/v2/users/list") == ""


def test_plain_git_silent():
    for cmd in (
        "git log --oneline -5",
        "git checkout main -- docs/file.md",
        "git grep -n 'foo/bar' HEAD",
        "git log --format=%H:%an",
        "git clone git@github.com:akkton/agentic-ops--x.git",
    ):
        assert run_hook(cmd) == "", cmd


def test_docker_volume_drive_silent():
    assert run_hook("docker run -v /c/foo:/app img") == ""


def test_ssh_host_colon_path_silent():
    assert run_hook("scp file.txt user@host:/remote/path") == ""


# --- silent: wrong tool / malformed input ----------------------------------

def test_powershell_tool_silent():
    assert run_hook("git show HEAD:docs/x.md", tool_name="PowerShell") == ""


def test_malformed_stdin_silent():
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json", capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
