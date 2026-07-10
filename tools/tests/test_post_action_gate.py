"""post-action-gate (PostToolUse:Bash|PowerShell): ship/B2/hard-limit advisories.

First behavioral suite for this hook (previously registry/compile-only).
Pins the decision boundaries incl. the PowerShell normalization arm: a
`& "...\\vercel.cmd" deploy --prod` via the PowerShell tool must produce the
same SHIP advisory a bash `vercel deploy --prod` does.

The 3-in-a-row streak counter lives in tempfile.gettempdir(); every test
redirects TMP/TEMP/TMPDIR to tmp_path so parallel runs and the developer's
live counter can't interfere.
"""
import json

from hooklib import run_hook


def _run(cmd, tmp_path, tool="Bash"):
    return run_hook(
        "post-action-gate.py",
        {"tool_name": tool, "tool_input": {"command": cmd}},
        env={
            "TMP": str(tmp_path),
            "TEMP": str(tmp_path),
            "TMPDIR": str(tmp_path),
        },
    )


def _context(p):
    out = p.stdout.strip()
    if not out:
        return ""
    try:
        return (json.loads(out).get("hookSpecificOutput") or {}).get(
            "additionalContext", ""
        )
    except json.JSONDecodeError:
        return ""


def test_bash_git_push_ship_advisory(tmp_path):
    assert "[SHIP GATE]" in _context(_run("git push origin feature", tmp_path))


def test_powershell_vercel_cmd_ship_advisory(tmp_path):
    # The normalization pin: recorded live-bypass shape via the PowerShell tool.
    p = _run('& "$nodeDir\\vercel.cmd" deploy --prod --yes --cwd platform',
             tmp_path, tool="PowerShell")
    assert "[SHIP GATE]" in _context(p)


def test_powershell_build_streak_hard_limit(tmp_path):
    cmd = "npm run build"
    assert "streak: 1/3" in _context(_run(cmd, tmp_path, tool="PowerShell"))
    assert "streak: 2/3" in _context(_run(cmd, tmp_path, tool="PowerShell"))
    third = _context(_run(cmd, tmp_path, tool="PowerShell"))
    assert "streak: 3/3" in third and "[HARD LIMIT]" in third


def test_different_build_command_resets_streak(tmp_path):
    _run("npm run build", tmp_path)
    _run("npm run build", tmp_path)
    # A DIFFERENT build/test command starts a fresh streak of 1.
    assert "streak: 1/3" in _context(_run("uv run pytest tools/tests", tmp_path))


def test_exempt_verification_does_not_advance_streak(tmp_path):
    _run("npm run build", tmp_path)
    _run("npm run build", tmp_path)
    # wire-hooks --check is a B2-exempt verification: nudge, no streak.
    exempt = _context(_run("uv run python tools/wire-hooks.py --check", tmp_path))
    assert "exempt from streak" in exempt
    # And the streak was reset: the next real build starts at 1 again.
    assert "streak: 1/3" in _context(_run("npm run build", tmp_path))


def test_powershell_backslash_hook_test_exempt(tmp_path):
    # Windows-spelled hook invocation must hit the (forward-slash-written)
    # `.claude/hooks/` exempt pattern via the normalized view. Without the
    # normalizer this counts as a real build step and advances the streak.
    p = _run('uv run python .claude\\hooks\\cd-guard.py', tmp_path, tool="PowerShell")
    assert "exempt from streak" in _context(p)


def test_edit_tool_silent(tmp_path):
    p = run_hook(
        "post-action-gate.py",
        {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}},
        env={"TMP": str(tmp_path), "TEMP": str(tmp_path), "TMPDIR": str(tmp_path)},
    )
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_plain_readonly_silent(tmp_path):
    p = _run("ls -la", tmp_path)
    assert p.returncode == 0 and p.stdout.strip() == ""
