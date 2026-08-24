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

from hooklib import load_hook, run_hook


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


# --------------------------------------------------------------------- F3a
# Streak identity: the 2026-08-24 false-positive cluster (6 iteration-3x
# advisories in one session, none a fix-then-test loop). The old fingerprint
# hashed the first 200 chars only, so a long shared prefix made distinct
# commands identical. These pin the two shapes that actually misfired.

# 223 chars: the script NAME lands past char 200, which is what collided.
LONG_PREFIX = (
    'uv run --directory "/c/Users/neuma_p1qrsic/Repo/agentic-ops1-recon" '
    "--all-extras python /c/Users/neuma_p1qrsic/Repo/agentic-ops1-recon/workspace/"
    "clients/brisken/automations/expense-recon/.scratch/recon-item25/"
)

# >200 chars of shared heredoc boilerplate before the bodies diverge.
HEREDOC_PREAMBLE = (
    "python - <<'PYEOF'\n"
    "import pathlib, re, sys\n"
    "SRC = pathlib.Path('workspace/clients/brisken/automations/expense-recon/app/ingest.py')\n"
    "text = SRC.read_text(encoding='utf-8')\n"
    "# one-shot in-place edit against the live source tree\n"
)


def test_long_prefix_distinct_scripts_do_not_collide(tmp_path):
    assert len(LONG_PREFIX) > 200, "fixture must exceed the old 200-char window"
    ctxs = [
        _context(_run(LONG_PREFIX + name, tmp_path))
        for name in ("probe_dates.py", "measure_a.py", "measure_b.py", "check_ocr.py")
    ]
    assert not any("iteration-3x" in c for c in ctxs), (
        "four distinct one-shot scripts under one long prefix are four "
        "different commands, not a 3x fix loop"
    )


def test_distinct_heredoc_bodies_do_not_collide(tmp_path):
    assert len(HEREDOC_PREAMBLE) > 200, "fixture must exceed the old 200-char window"
    ctxs = [
        _context(_run(HEREDOC_PREAMBLE + body + "\nPYEOF", tmp_path))
        for body in ("print('alpha')", "print('beta')", "print('gamma')")
    ]
    assert not any("iteration-3x" in c for c in ctxs), (
        "three unrelated heredoc edits sharing a preamble are not a 3x fix loop"
    )


def test_iteration_3x_still_fires_on_identical_long_command(tmp_path):
    # The narrowing must not disable real detection: the SAME long command run
    # three times is still the stuck fix-then-test loop the gate exists for.
    cmd = LONG_PREFIX + "probe_dates.py"
    _run(cmd, tmp_path)
    _run(cmd, tmp_path)
    assert "iteration-3x" in _context(_run(cmd, tmp_path))


def test_command_identity_separates_script_paths():
    hook = load_hook("gate-skip-detector.py")
    a = hook.fingerprint(LONG_PREFIX + "measure_a.py")
    b = hook.fingerprint(LONG_PREFIX + "measure_b.py")
    assert a != b


def test_command_identity_separates_heredoc_bodies():
    hook = load_hook("gate-skip-detector.py")
    a = hook.fingerprint(HEREDOC_PREAMBLE + "print('alpha')\nPYEOF")
    b = hook.fingerprint(HEREDOC_PREAMBLE + "print('beta')\nPYEOF")
    assert a != b
    # The body digest is an explicit part of the identity, so a future
    # re-truncation of the normalized command cannot silently re-collide them.
    assert "HEREDOC:" in hook.command_identity(HEREDOC_PREAMBLE + "x\nPYEOF")


# --------------------------------------------------------------------- F3b
# Pre-publish: CI-green IS the validation gate for a merge (rule_no_auto_commit
# Band 2). Two docs-only merges that waited on `gh pr checks --watch` in the
# same chain still tripped the advisory on 2026-08-24.


def test_gh_pr_checks_same_chain_satisfies_pre_publish(tmp_path):
    p = _run(
        "gh pr checks 601 --watch --fail-fast && "
        "gh pr merge 601 --squash --delete-branch",
        tmp_path,
    )
    assert "gate-skip-pre-publish" not in _context(p)


def test_gh_pr_checks_in_recent_buffer_satisfies_pre_publish(tmp_path):
    _run("gh pr checks 601 --watch", tmp_path)
    p = _run("gh pr merge 601 --squash --delete-branch", tmp_path)
    assert "gate-skip-pre-publish" not in _context(p)


def test_merge_with_no_validation_anywhere_still_fires(tmp_path):
    # The negative control: without a CI/validation signal the gate must still
    # fire, or the fix would have disabled the rule instead of narrowing it.
    p = _run("gh pr merge 601 --squash --delete-branch", tmp_path)
    assert "gate-skip-pre-publish" in _context(p)
