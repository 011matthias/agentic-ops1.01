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


def _run(cmd, tmp_path, tool="Bash", pr_files=None):
    env = {
        "TMP": str(tmp_path),
        "TEMP": str(tmp_path),
        "TMPDIR": str(tmp_path),
    }
    if pr_files is not None:
        # Seam: bypass the `gh pr view --json files` network call. 'ERROR'
        # forces the undeterminable branch.
        env["POST_ACTION_GATE_PR_FILES"] = pr_files
    return run_hook(
        "post-action-gate.py",
        {"tool_name": tool, "tool_input": {"command": cmd}},
        env=env,
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


# ---- platform-merge-is-not-live marker (rule_behaviors sub-clause) ----
#
# The advisory used to fire on EVERY `gh pr merge` with the platform condition
# stated as prose, which made it noise rather than a marker. It is now scoped
# to merges that actually touched platform/ paths, and it persists until
# tools/vercel-force-deploy.sh runs.

PLATFORM_FILES = "platform/src/app/(public)/page.tsx\ndocs/INDEX.md"
DOCS_FILES = "docs/INDEX.md\ntools/foo.py"


def test_platform_merge_fires_not_live(tmp_path):
    ctx = _context(_run("gh pr merge 352 --squash", tmp_path, pr_files=PLATFORM_FILES))
    assert "[MERGE-NOT-LIVE]" in ctx and "PR #352" in ctx


def test_non_platform_merge_stays_quiet(tmp_path):
    ctx = _context(_run("gh pr merge 351 --squash", tmp_path, pr_files=DOCS_FILES))
    assert "[SHIP GATE]" in ctx
    assert "MERGE-NOT-LIVE" not in ctx


def test_undeterminable_pr_files_still_warns(tmp_path):
    # Fail-open to warning: precision must never become a new blind spot.
    ctx = _context(_run("gh pr merge 353 --squash", tmp_path, pr_files="ERROR"))
    assert "[MERGE-NOT-LIVE]" in ctx and "could not be read" in ctx


def test_marker_persists_on_later_ship_command(tmp_path):
    _run("gh pr merge 352 --squash", tmp_path, pr_files=PLATFORM_FILES)
    ctx = _context(_run("git push origin feature", tmp_path))
    assert "[PLATFORM NOT LIVE]" in ctx and "PR #352" in ctx


def test_no_marker_after_non_platform_merge(tmp_path):
    _run("gh pr merge 351 --squash", tmp_path, pr_files=DOCS_FILES)
    ctx = _context(_run("git push origin feature", tmp_path))
    assert "PLATFORM NOT LIVE" not in ctx


def test_force_deploy_clears_the_marker(tmp_path):
    _run("gh pr merge 352 --squash", tmp_path, pr_files=PLATFORM_FILES)
    cleared = _context(_run("bash tools/vercel-force-deploy.sh --dir platform", tmp_path))
    assert "[PLATFORM DEPLOY]" in cleared and "PR #352" in cleared
    # And the marker is gone for every later ship command.
    assert "PLATFORM NOT LIVE" not in _context(_run("git push origin feature", tmp_path))


def test_force_deploy_without_pending_marker_is_quiet(tmp_path):
    ctx = _context(_run("bash tools/vercel-force-deploy.sh", tmp_path))
    assert "PLATFORM DEPLOY" not in ctx


def test_gh_merge_wrapper_is_ship_class_and_marks(tmp_path):
    # tools/gh-merge.sh is the safe `gh pr merge` wrapper. The hook's
    # `"gh-merge" in view` branch was unreachable before: the wrapper matched
    # no SHIP pattern, so a merge through it produced no advisory at all.
    ctx = _context(_run("bash tools/gh-merge.sh 352 --squash", tmp_path,
                        pr_files=PLATFORM_FILES))
    assert "[MERGE-NOT-LIVE]" in ctx and "PR #352" in ctx


def test_merge_without_pr_number_degrades_label(tmp_path):
    # `gh pr merge --squash` resolves the PR from the current branch.
    ctx = _context(_run("gh pr merge --squash", tmp_path, pr_files=PLATFORM_FILES))
    assert "[MERGE-NOT-LIVE]" in ctx and "the merged PR" in ctx
