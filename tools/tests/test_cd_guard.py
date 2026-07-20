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


# --- 2026-06-09 hardening: the quoted-path root gap (register #16) ---
# `residue()` used to DELETE quoted spans, so `cd "$WT"` lost its path token
# and slipped through -- the exact pattern that bricked the hook layer.

def test_blocks_quoted_var_path_chain():
    assert _is_block(_run('cd "$WT" && git commit -m x'))


def test_blocks_quoted_path_newline_row16():
    # The register #16 incident verbatim: quoted cd on its own line.
    assert _is_block(_run('cd "$WT"\ngit commit -m x\ngit push'))


def test_blocks_quoted_path_with_space():
    assert _is_block(_run('cd "some dir" && ls'))


def test_blocks_bare_cd_whole_command():
    # A bare `cd <path>` still drifts the cwd into the next call -> block.
    assert _is_block(_run("cd workspace/clients/brisken"))


def test_blocks_newline_first_line():
    # Plain (unquoted) newline-first-line cd -- regression pin.
    assert _is_block(_run("cd workspace/clients/brisken\nls"))


def test_allows_cd_home_tilde():
    assert _run("cd ~\nls").returncode == 0


def test_allows_cd_home_var():
    assert _run("cd $HOME && ls").returncode == 0


def test_allows_cd_home_subpath():
    assert _run("cd ~/Repo\nls").returncode == 0


def test_allows_npm_prefix_no_cd():
    assert _run("npm --prefix workspace/x ci").returncode == 0


def test_block_reason_shows_original_quoted_path():
    # The reason must surface the ORIGINAL text, not the masked 'XXXXX'.
    p = _run('cd "$WT" && git commit -m x')
    reason = json.loads(p.stdout.strip().splitlines()[-1])["reason"]
    assert 'cd "$WT"' in reason


# --- 2026-07-20: trailing-boundary lookahead (register 07-15/07-16 gaps) -----
# The old consuming trailing group `(?:\s+&&|\s*\n|\s+;|\s*$)` required a
# SPACE before `;` and had no case for a redirect after the path, so
# `cd X; cmd` and `cd X 2>/dev/null` both bypassed. Now a non-consuming
# `(?=[\s;&|]|$)` (PS-arm parity).

def test_blocks_semicolon_chain_no_space():
    # The 2026-07-16 live bypass verbatim shape: `cd X; gh pr create`.
    assert _is_block(_run("cd platform; gh pr create"))


def test_blocks_redirect_after_path():
    # The 2026-07-15 shape: bare cd with a stderr redirect after the path.
    assert _is_block(_run("cd workspace/clients/brisken 2>/dev/null"))


def test_blocks_pipe_chain():
    assert _is_block(_run("cd platform | cat"))


def test_still_allows_home_subpath_with_chain():
    assert _run("cd ~/Repo; ls").returncode == 0


# --- 2026-07-10: PowerShell arm ---------------------------------------------
# The PowerShell tool persists cwd exactly like Bash, but Set-Location ran
# unguarded (recorded live bypass). These pin the PS block/allow boundary.

def _run_ps(cmd):
    return run_hook(
        "cd-guard.py", {"tool_name": "PowerShell", "tool_input": {"command": cmd}}
    )


def test_ps_blocks_set_location():
    # Recorded live-bypass shape, verbatim.
    assert _is_block(_run_ps("Set-Location platform"))


def test_ps_blocks_set_location_chained_semicolon():
    assert _is_block(_run_ps(
        '$env:Path = "$nodeDir;$env:Path"; Set-Location platform; '
        '& "$nodeDir\\vercel.cmd" deploy --yes'
    ))


def test_ps_blocks_sl_alias():
    assert _is_block(_run_ps("sl platform"))


def test_ps_blocks_chdir_alias():
    assert _is_block(_run_ps("chdir platform"))


def test_ps_blocks_cd():
    assert _is_block(_run_ps("cd platform; npm run build"))


def test_ps_blocks_set_location_path_param():
    assert _is_block(_run_ps("Set-Location -Path platform"))


def test_ps_allows_home_tilde():
    assert _run_ps("Set-Location ~").returncode == 0


def test_ps_allows_home_var():
    assert _run_ps("Set-Location $HOME").returncode == 0


def test_ps_allows_env_userprofile():
    assert _run_ps("Set-Location $env:USERPROFILE").returncode == 0


def test_ps_allows_push_location_stack():
    # Push-Location is the recommended remediation -- must never block.
    assert _run_ps("Push-Location platform; npm run build; Pop-Location").returncode == 0


def test_ps_allows_set_location_inside_herestring():
    body = "git commit -m @'\nnotes: run Set-Location platform later\n'@"
    assert _run_ps(body).returncode == 0


def test_ps_allows_plain_cmdlets():
    assert _run_ps("Get-ChildItem -Recurse platform").returncode == 0


def test_ps_block_reason_recommends_push_location():
    p = _run_ps("Set-Location platform")
    reason = json.loads(p.stdout.strip().splitlines()[-1])["reason"]
    assert "Push-Location" in reason
