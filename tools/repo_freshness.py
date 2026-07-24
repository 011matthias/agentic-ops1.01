#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Stale-checkout detector: how far is this checkout behind origin/main?

Any tool that derives state from the WORKING TREE silently under-reports on
a checkout that is behind origin/main: `optimize_overview` said "1 closed
run" when the truth was 4 (13-PR-stale checkout, register 2026-07-22), a
parity audit ran against a stale #294 base while origin sat at #299
(register 2026-07-21), and a 2026-07-22 grep for PR #320's own code came
back empty because the checkout predated the PR. PR #320 fixed the one
tool; this helper generalizes the pattern so every working-tree-derived
tool (and SessionStart itself) can flag the condition in one line.

Library use (adopters: project_status.py --sweep-stale, check-index.py):

    rf = _load_repo_freshness()          # spec-load beside __file__
    n = rf.behind_count(repo_root)
    line = rf.staleness_banner(n, context="status sweep")
    if line: print(line, file=sys.stderr)

CLI (wired at SessionStart via wire-hooks.py, silent when current):

    uv run tools/repo_freshness.py --quiet --fetch
    uv run tools/repo_freshness.py --format json

Exit 0 always — this is an advisory sensor, never a gate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_BASE = "origin/main"


def _git(args: list[str], repo: str | Path, timeout: int = 10) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(repo), timeout=timeout,
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def behind_count(
    repo: str | Path = ".",
    base: str = DEFAULT_BASE,
    fetch: bool = False,
    fetch_timeout: int = 8,
) -> int | None:
    """Commits on `base` not reachable from HEAD, or None when undeterminable.

    With fetch=True the remote-tracking ref is refreshed first (bounded by
    fetch_timeout); on fetch failure the LOCAL ref is still compared, so the
    caller degrades to a lower-bound count rather than nothing.
    """
    if fetch:
        remote, _, branch = base.partition("/")
        if branch:
            _git(["fetch", "--quiet", remote, branch], repo, timeout=fetch_timeout)
    out = _git(["rev-list", "--count", f"HEAD..{base}"], repo)
    if out is None:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def staleness_banner(behind: int | None, context: str = "") -> str | None:
    """One-line STALE-CHECKOUT warning, or None when current/undeterminable."""
    if not behind:
        return None
    ctx = f" — {context}" if context else ""
    return (
        f"[STALE-CHECKOUT] this checkout is {behind} commit(s) behind "
        f"{DEFAULT_BASE}{ctx}. Working-tree-derived results under-report: "
        f"files, tools, and state added upstream are invisible here. "
        f"Compare against `git show {DEFAULT_BASE}:<path>` or pull before "
        f"trusting an absence."
    )


def warn_if_stale(
    context: str,
    repo: str | Path = ".",
    fetch: bool = False,
    out=sys.stderr,
) -> int | None:
    """Adopter convenience: compute, print the banner when stale, return count."""
    n = behind_count(repo, fetch=fetch)
    line = staleness_banner(n, context)
    if line:
        print(line, file=out)
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]),
                    help="repo root to inspect (default: this repo)")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--fetch", action="store_true",
                    help="refresh the remote-tracking ref first (bounded; "
                         "falls back to local refs on failure)")
    ap.add_argument("--quiet", action="store_true",
                    help="print nothing when current (SessionStart use)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--context", default="session start")
    args = ap.parse_args(argv)

    n = behind_count(args.repo, base=args.base, fetch=args.fetch)
    if args.format == "json":
        print(json.dumps({"behind": n, "base": args.base, "stale": bool(n)}))
        return 0
    line = staleness_banner(n, args.context)
    if line:
        print(line)
    elif not args.quiet:
        state = "current with" if n == 0 else "undeterminable vs"
        print(f"[repo-freshness] checkout {state} {args.base}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
