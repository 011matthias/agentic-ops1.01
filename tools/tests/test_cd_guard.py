"""cd-guard (PreToolUse:Bash): blocks the `cd <subdir> && ...` cwd-leak pattern.

Four documented friction events (register 2026-05-18 #20, 2026-05-20 #9,
2026-05-25 #109, 2026-05-19 #100) motivated this hook. These tests pin its
block/allow boundary so a regex tweak can't silently reopen the hole.

A BLOCK is exit code 2 with a JSON {"decision": "block"} on stdout.
"""
import json

from hooklib import run_hook


def _run(cmd):
    return run_hook("cd-guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}})


def _is_block(p):
    if p.returncode != 2 or not p.stdout.strip():
        return False
    try:
        return json.loads(p.stdout.strip().splitlines()[-1]).get("decision") == "block"
    except (json.JSONDecodeError, IndexError):
        return False


def test_blocks_cd_subdir_chain():
    assert _is_block(_run("cd workspace/clients/brisken && ls"))


def test_allows_subshell():
    assert _run("( cd workspace/clients/brisken && ls )").returncode == 0


def test_allows_tool_flag_no_cd():
    assert _run("git -C workspace/clients/brisken status").returncode == 0


def test_allows_cd_dash():
    assert _run("cd - && ls").returncode == 0


def test_ignores_cd_inside_quotes():
    assert _run('echo "cd workspace/foo && bar"').returncode == 0


def test_non_bash_tool_passes():
    p = run_hook("cd-guard.py", {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}})
    assert p.returncode == 0
