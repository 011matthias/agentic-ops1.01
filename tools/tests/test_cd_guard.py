"""cd-guard (PreToolUse:Bash): blocks the `cd <subdir> && ...` cwd-leak pattern.

Four documented friction events (register 2026-05-18 #20, 2026-05-20 #9,
2026-05-25 #109, 2026-05-19 #100) motivated this hook. These tests pin its
block/allow boundary so a regex tweak can't silently reopen the hole.

A BLOCK is exit code 2 with a JSON {"decision": "block"} on stdout.
"""
import json
import shutil
import subprocess

import pytest

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


# --- 2026-09-17: auto-mode rewrite -------------------------------------------
# Under permission_mode "auto" a Bash cd chain is rewritten into a subshell via
# updatedInput. Never with a permissionDecision: a hook "allow" skips the
# approval the command would need (live-probed 2026-09-17, memory
# reference_pretooluse_updatedinput_semantics). Other modes keep the block; in
# "default" a `( ... )` loses prefix-rule matching and would prompt instead.

NON_AUTO_MODES = ["default", "acceptEdits", "plan", "dontAsk", "bypassPermissions", None]


def _run_mode(cmd, mode, tool="Bash", **extra):
    payload = {"tool_name": tool, "tool_input": {"command": cmd, **extra}}
    if mode is not None:
        payload["permission_mode"] = mode
    return run_hook("cd-guard.py", payload)


def _output(p):
    lines = p.stdout.strip().splitlines()
    return json.loads(lines[-1]) if lines else {}


def _updated_input(p):
    return (_output(p).get("hookSpecificOutput") or {}).get("updatedInput")


def test_auto_rewrites_cd_chain_into_subshell():
    p = _run_mode("cd platform && npm run build", "auto")
    assert p.returncode == 0
    assert _updated_input(p)["command"] == "( cd platform && npm run build )"


def test_auto_rewrite_carries_full_tool_input():
    p = _run_mode("cd platform && npm test", "auto",
                  description="run tests", timeout=60000, run_in_background=True)
    assert _updated_input(p) == {
        "command": "( cd platform && npm test )",
        "description": "run tests",
        "timeout": 60000,
        "run_in_background": True,
    }


def test_auto_rewrite_tells_agent_the_cd_did_not_persist():
    p = _run_mode('cd "$WT" && git status', "auto")
    note = _output(p)["hookSpecificOutput"]["additionalContext"]
    assert "does NOT persist" in note and 'cd "$WT"' in note


def test_auto_rewrite_emits_no_permission_decision():
    out = _output(_run_mode("cd platform; gh pr create", "auto"))
    assert set(out) == {"hookSpecificOutput"}
    assert "permissionDecision" not in out["hookSpecificOutput"]
    assert "updatedInput" in out["hookSpecificOutput"]


_CORPUS_BASH = [
    "cd platform && npm run build",
    "cd platform; gh pr create",
    'cd "$WT"\ngit commit -m x\ngit push',
    "cd platform && npm test # smoke",
    "cd platform && cat > x.txt <<'EOF'\nbody\nEOF",
    "cd platform | cat",
    "cd platform",
    "cd platform 2>/dev/null",
    "( cd platform && ls )",
    "git -C platform status",
    "cd ~/Repo; ls",
]
_CORPUS_PS = [
    "Set-Location platform; npm run build",
    "cd platform; npm run build",
    "Push-Location platform; npm run build; Pop-Location",
]


@pytest.mark.parametrize("mode", NON_AUTO_MODES + ["auto"])
@pytest.mark.parametrize("tool,cmd", [("Bash", c) for c in _CORPUS_BASH]
                         + [("PowerShell", c) for c in _CORPUS_PS])
def test_never_permission_decision_alongside_updated_input(tool, cmd, mode):
    p = _run_mode(cmd, mode, tool=tool)
    out = _output(p)
    spec = out.get("hookSpecificOutput") or {}
    assert "permissionDecision" not in spec
    if "updatedInput" in spec:
        assert tool == "Bash" and mode == "auto"
        assert p.returncode == 0 and "decision" not in out


@pytest.mark.parametrize("mode", NON_AUTO_MODES)
def test_non_auto_modes_keep_the_block(mode):
    assert _is_block(_run_mode("cd platform && npm run build", mode))


@pytest.mark.parametrize("cmd", [
    "cd platform",
    "cd platform 2>/dev/null",
    "cd platform;",
    "cd platform &",
    "ls\ncd platform",
])
def test_auto_blocks_a_cd_nothing_in_the_call_uses(cmd):
    # Wrapped, these would be silent no-ops and the next call would run in a
    # directory the agent did not expect.
    assert _is_block(_run_mode(cmd, "auto"))


def test_auto_block_names_the_stranded_cd():
    p = _run_mode("cd a && make\ncd b", "auto")
    assert _is_block(p)
    assert "`cd b && ...`" in _output(p)["reason"]


def test_auto_keeps_powershell_block():
    # PS parentheses do not scope Set-Location, so there is nothing to wrap.
    assert _is_block(_run_mode("Set-Location platform; npm run build", "auto", tool="PowerShell"))


def test_auto_existing_subshell_passes_silently():
    p = _run_mode("( cd platform && ls )", "auto")
    assert p.returncode == 0 and not p.stdout.strip()


def test_auto_comment_puts_parens_on_own_lines():
    p = _run_mode("cd platform && npm test # smoke", "auto")
    assert _updated_input(p)["command"] == "(\ncd platform && npm test # smoke\n)"


def _real_bash():
    bash = shutil.which("bash")
    # System32\bash.exe is the WSL launcher, not a shell for this cwd.
    if not bash or "system32" in bash.lower():
        pytest.skip("no POSIX bash on PATH")
    return bash


@pytest.mark.parametrize("cmd,content", [
    ("cd sub && printf hi > inner.txt", "hi"),
    ("cd sub && printf hi > inner.txt # note", "hi"),
    ("cd sub && cat > inner.txt <<'EOF'\nhello\nEOF", "hello\n"),
])
def test_rewritten_command_runs_in_bash_and_the_cd_does_not_leak(tmp_path, cmd, content):
    bash = _real_bash()
    (tmp_path / "sub").mkdir()
    rewritten = _updated_input(_run_mode(cmd, "auto"))["command"]
    baseline = subprocess.run([bash, "-c", "pwd"], cwd=tmp_path,
                              capture_output=True, text=True).stdout.strip()
    r = subprocess.run([bash, "-c", rewritten + "\npwd"], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == baseline
    assert (tmp_path / "sub" / "inner.txt").read_text() == content
