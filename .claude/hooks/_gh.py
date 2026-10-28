"""Shared GitHub PR-state helpers for hooks and tools.

One reading of a PR's merge readiness, used by no-auto-commit-gate (the
auto-merge band) and tools/repo-sweep.py (the sweep-PR decision table), so the
two cannot drift. `gh pr checks` alone exits 0 on a CONFLICTING PR whose checks
are green, which let the gate allow a merge GitHub then refused (#1638,
2026-10-28); `gh pr view --json mergeable,statusCheckRollup` carries both.
"""
from __future__ import annotations

import json
import subprocess

RED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED",
                   "STARTUP_FAILURE"}


def classify_rollup(rollup: list[dict]) -> str:
    """Overall check state from gh's statusCheckRollup: none|red|pending|green."""
    if not rollup:
        return "none"
    red = pending = False
    for c in rollup:
        if c.get("__typename") == "StatusContext":
            state = (c.get("state") or "").upper()
            if state in ("FAILURE", "ERROR"):
                red = True
            elif state in ("PENDING", "EXPECTED"):
                pending = True
        else:  # CheckRun
            conclusion = (c.get("conclusion") or "").upper()
            status = (c.get("status") or "").upper()
            if conclusion in RED_CONCLUSIONS:
                red = True
            elif status != "COMPLETED":
                pending = True
    if red:
        return "red"
    if pending:
        return "pending"
    return "green"


def merge_state(checks: str, mergeable: str) -> str:
    """Merge readiness: conflicting beats every check state.

    Returns conflicting|green|red|pending|none. MERGEABLE and UNKNOWN (GitHub
    still computing) defer to the checks; GitHub re-tests mergeability at merge
    time, so only a definite CONFLICTING overrides them.
    """
    if (mergeable or "").upper() == "CONFLICTING":
        return "conflicting"
    return checks


def pr_view(selector: str = "", timeout: int = 20, cwd: str | None = None) -> dict | None:
    """`gh pr view <selector> --json mergeable,statusCheckRollup`, or None on any error."""
    args = ["gh", "pr", "view"]
    if selector:
        args.append(selector)
    args += ["--json", "mergeable,statusCheckRollup"]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                             encoding="utf-8", errors="replace", cwd=cwd)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    try:
        data = json.loads(out.stdout)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def pr_merge_state(selector: str = "", timeout: int = 20) -> str | None:
    """conflicting|green|red|pending|none for a PR, or None when undeterminable."""
    data = pr_view(selector, timeout=timeout)
    if data is None:
        return None
    return merge_state(classify_rollup(data.get("statusCheckRollup") or []),
                       data.get("mergeable") or "UNKNOWN")
