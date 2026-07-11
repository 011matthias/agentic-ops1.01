"""_shell.normalize_command: the PowerShell/.cmd matching-view normalizer.

Pins the two recorded live bypasses (2026-07-10 audit) and the negative
guarantees: bash text round-trips unchanged, background `&` is never
stripped, and the transform is idempotent.
"""
import importlib.util

from hooklib import HOOKS


def _load():
    spec = importlib.util.spec_from_file_location("_shell", HOOKS / "_shell.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_shell = _load()
norm = _shell.normalize_command


def test_real_bypass_vercel_cmd_call_operator():
    # Recorded live bypass #1 (settings.local.json allowlist history).
    got = norm('& "$nodeDir\\vercel.cmd" deploy --prod --yes --cwd platform')
    assert "vercel deploy --prod" in got


def test_bare_cmd_suffix():
    assert norm("vercel.cmd deploy --yes").startswith("vercel deploy")


def test_exe_suffix_with_path():
    assert "git push origin main" in norm("C:\\Program Files\\Git\\git.exe push origin main")


def test_quoted_path_with_spaces():
    got = norm('& "C:\\Program Files\\nodejs\\npm.cmd" run build')
    assert got.startswith("npm run build")


def test_dollar_var_path():
    assert norm("$nodeDir\\flyctl.exe deploy").startswith("flyctl deploy")


def test_bash_command_round_trips():
    cmd = "git push origin feature && uv run pytest tools/tests"
    assert norm(cmd) == cmd


def test_bash_background_amp_not_stripped():
    # `foo & bar` (bash background) must NOT be treated as a call operator.
    cmd = "sleep 5 & echo done"
    assert norm(cmd) == cmd


def test_sh_extension_not_reduced():
    # vercel-force-deploy.sh is itself a ship pattern -- .sh must survive.
    cmd = "bash tools/vercel-force-deploy.sh"
    assert "vercel-force-deploy.sh" in norm(cmd)


def test_backslash_paths_become_forward():
    assert norm("python .claude\\hooks\\cd-guard.py") == "python .claude/hooks/cd-guard.py"


def test_idempotent():
    raw = '& "$nodeDir\\vercel.cmd" deploy --prod'
    once = norm(raw)
    assert norm(once) == once


def test_message_only_quoted_path_not_whole_token_untouched():
    # A quoted span that is NOT exactly a program path keeps its quotes.
    cmd = 'git commit -m "fix vercel.cmd handling in docs"'
    assert '"fix vercel' in norm(cmd)
