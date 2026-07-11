"""gate-skip-detector (PostToolUse:Bash|PowerShell): skipped-gate advisories.

First behavioral suite for this hook (previously registry/compile-only).
Pins: pre-publish advisory on the normalized PowerShell `vercel.cmd deploy`
shape, the validate-in-buffer negative, the iteration-3x boundary incl. the
PS-statement-prefix read-only fix, and the quoted-publish-residue exemption.

The ring buffer lives in tempfile.gettempdir(); every test redirects
TMP/TEMP/TMPDIR to tmp_path for isolation. AGENTIC_OPS_SESSION_STATE is
redirected so friction-candidate capture can't touch live session state.
"""
import json

from hooklib import run_hook


def _run(cmd, tmp_path, tool="Bash"):
    return run_hook(
        "gate-skip-detector.py",
        {"tool_name": tool, "tool_input": {"command": cmd}},
        env={
            "TMP": str(tmp_path),
            "TEMP": str(tmp_path),
            "TMPDIR": str(tmp_path),
            "AGENTIC_OPS_SESSION_STATE": str(tmp_path / "s.json"),
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


def test_powershell_vercel_cmd_pre_publish_fires(tmp_path):
    # Fresh buffer + normalized `vercel deploy --prod` via PowerShell -> the
    # pre-publish advisory (no validation step in buffer).
    p = _run('& "$nodeDir\\vercel.cmd" deploy --prod --yes', tmp_path, tool="PowerShell")
    assert "gate-skip-pre-publish" in _context(p)


def test_validate_in_buffer_suppresses_pre_publish(tmp_path):
    _run("uv run --no-project --with pytest pytest tools/tests", tmp_path)
    p = _run("git push origin feature", tmp_path)
    assert "gate-skip-pre-publish" not in _context(p)


def test_iteration_3x_on_repeated_mutating_command(tmp_path):
    cmd = "uv run python scripts/fix_thing.py"
    _run(cmd, tmp_path)
    _run(cmd, tmp_path)
    p = _run(cmd, tmp_path)
    assert "gate-skip-iteration-3x" in _context(p)


def test_iteration_3x_skips_readonly(tmp_path):
    for _ in range(2):
        _run("git status", tmp_path)
    p = _run("git status", tmp_path)
    assert "iteration-3x" not in _context(p)


def test_iteration_3x_skips_readonly_with_ps_statement_prefix(tmp_path):
    # The `^`-anchored read-only pattern used to be defeated by a PowerShell
    # statement prefix; the (?:^|[;\n]) anchor fix pins this.
    cmd = "$x = 1; git status"
    for _ in range(2):
        _run(cmd, tmp_path, tool="PowerShell")
    p = _run(cmd, tmp_path, tool="PowerShell")
    assert "iteration-3x" not in _context(p)


def test_publish_verb_inside_quotes_does_not_fire(tmp_path):
    p = _run('echo "run git push when ready"', tmp_path)
    assert "gate-skip-pre-publish" not in _context(p)


def test_edit_tool_silent(tmp_path):
    p = run_hook(
        "gate-skip-detector.py",
        {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}},
        env={"TMP": str(tmp_path), "TEMP": str(tmp_path), "TMPDIR": str(tmp_path)},
    )
    assert p.returncode == 0 and p.stdout.strip() == ""


def test_powershell_tool_processed(tmp_path):
    # A PowerShell publish command IS processed (was silently ignored before).
    p = _run("git push origin main", tmp_path, tool="PowerShell")
    assert "gate-skip-pre-publish" in _context(p)
