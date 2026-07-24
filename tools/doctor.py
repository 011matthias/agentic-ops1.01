#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Repo health-check aggregator: the whole checker battery, one command.

Before this tool, a full health pass meant ~14 manual invocations (the
2026-07-22 health-check pass ran exactly that fan-out by hand; slow-path is
the register's #2 friction class). doctor.py is PURE ORCHESTRATION — a
config list of existing checkers run concurrently with a severity-banded
table and a JSON report. It contains zero check logic of its own; every
line of judgment lives in the tools it shells.

    uv run tools/doctor.py                 # standard battery
    uv run tools/doctor.py --deep          # + preflight-hooks --full (pytest, ~3min)
    uv run tools/doctor.py --heal          # safe correctives first, then battery
    uv run tools/doctor.py --only NAME     # one check (see --list)
    uv run tools/doctor.py --format json   # machine-readable to stdout

JSON report also lands in .scratch/health-YYYY-MM-DD.json (gitignored; W1 —
the live battery is the state, the file is a diffable convenience).

--heal runs ONLY correctives that are safe unattended: `wire-hooks
--ensure` (enforcement self-repair) and `normalize-client-pages --apply`
(idempotent page corrector). Content-editing correctives (strip-em-dash on
flagged prose) stay manual — they change client-facing text.

Exit: 0 when every check passed, 1 when any check is RED (non-zero exit or
timeout). Checks whose non-zero exit means "findings present" (client-page
audit, platform content) are still RED — a finding IS unhealthy state.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as _dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRATCH = REPO / ".scratch"


@dataclass(frozen=True)
class Check:
    name: str
    args: tuple[str, ...]      # argv after `uv run`, repo-relative script first
    timeout: int
    group: str
    # Checks that only mean something in the session's home clone. The
    # enforcement wiring lives in the gitignored .claude/settings.local.json,
    # so a secondary worktree NEVER has it and wire-hooks --check would report
    # ENFORCEMENT LAYER DOWN there every single time. A health tool that cries
    # wolf in the place people run it from trains them to ignore it, so those
    # checks report SKIP outside the home clone instead of a false RED. In the
    # home clone the check runs normally, where a missing block IS a real RED.
    home_clone_only: bool = False


def in_home_clone() -> bool:
    """True when REPO is a primary clone (.git is a directory), False in a
    linked worktree (.git is a file holding a gitdir: pointer)."""
    return (REPO / ".git").is_dir()


CHECKS: tuple[Check, ...] = (
    # state — enforcement + checkout freshness
    Check("wire-hooks", ("tools/wire-hooks.py", "--check"), 60, "state",
          home_clone_only=True),
    Check("repo-freshness", ("tools/repo_freshness.py",), 60, "state"),
    Check("scorer-pins", ("tools/pin_scorer.py", "check"), 60, "state"),
    # integrity — registries + staleness
    Check("check-index", ("tools/check-index.py",), 60, "integrity"),
    Check("skill-map", ("tools/check-skill-map.py",), 120, "integrity"),
    Check("spec-staleness", ("tools/spec-staleness.py",), 120, "integrity"),
    Check("status-sweep", ("tools/project_status.py", "--sweep-stale"), 120, "integrity"),
    # content — client-facing surfaces
    Check("client-pages", ("tools/audit-client-pages.py", "--severity", "HIGH"), 300, "content"),
    Check("platform-content", ("tools/validate-platform-content.py",), 300, "content"),
    # metrics — process sensors (advisory by design, exit 0)
    Check("friction-watch", ("tools/friction-watch.py", "--quiet", "--format", "json"), 120, "metrics"),
    Check("anneal-metrics", ("tools/anneal-metrics.py", "--format", "json"), 180, "metrics"),
    Check("optimize-fleet", ("tools/optimize_overview.py",), 120, "metrics"),
)

DEEP_CHECK = Check("preflight-full", ("tools/preflight-hooks.py", "--full"), 900, "deep")

HEALS: tuple[Check, ...] = (
    Check("wire-hooks-ensure", ("tools/wire-hooks.py", "--ensure"), 120, "heal"),
    Check("normalize-pages", ("tools/normalize-client-pages.py", "--apply"), 600, "heal"),
)


def _run_check(check: Check) -> dict:
    if check.home_clone_only and not in_home_clone():
        return {
            "name": check.name, "group": check.group, "ok": True,
            "skipped": True, "exit": None, "timed_out": False, "seconds": 0.0,
            "tail": ["skipped: not the home clone (gitignored per-checkout state)"],
        }
    cmd = ["uv", "run", "--directory", str(REPO), str(REPO / check.args[0]),
           *check.args[1:]]
    started = _dt.datetime.now()
    try:
        proc = subprocess.run(
            cmd, cwd=str(REPO), timeout=check.timeout,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        exit_code, timed_out = proc.returncode, False
        out = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        exit_code, timed_out = None, True
        out = ((exc.stdout or b"").decode("utf-8", "replace")
               if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    except (FileNotFoundError, OSError) as exc:
        exit_code, timed_out = None, False
        out = f"launcher error: {exc}"
    seconds = (_dt.datetime.now() - started).total_seconds()
    tail_lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    return {
        "name": check.name,
        "group": check.group,
        "ok": exit_code == 0,
        "skipped": False,
        "exit": exit_code,
        "timed_out": timed_out,
        "seconds": round(seconds, 1),
        "tail": tail_lines[-3:],
    }


def _print_table(results: list[dict]) -> None:
    width = max(len(r["name"]) for r in results)
    for r in results:
        if r.get("skipped"):
            status = "SKIP"
        else:
            status = "PASS" if r["ok"] else ("TIMEOUT" if r["timed_out"] else "RED")
        line = f"  {r['name']:<{width}}  {status:<7} {r['seconds']:>6.1f}s"
        if (not r["ok"] or r.get("skipped")) and r["tail"]:
            line += f"  {r['tail'][-1][:100]}"
        print(line)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deep", action="store_true",
                    help="include preflight-hooks --full (pytest suite, ~3 min)")
    ap.add_argument("--heal", action="store_true",
                    help="run the safe correctives before the battery")
    ap.add_argument("--only", metavar="NAME", help="run a single check by name")
    ap.add_argument("--list", action="store_true", help="list checks and exit")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args(argv)

    checks = list(CHECKS) + ([DEEP_CHECK] if args.deep else [])
    if args.list:
        for c in checks:
            print(f"{c.name:<18} [{c.group}]  {' '.join(c.args)}")
        return 0
    if args.only:
        checks = [c for c in checks + [DEEP_CHECK] if c.name == args.only]
        if not checks:
            print(f"[doctor] no check named {args.only!r} (see --list)",
                  file=sys.stderr)
            return 2

    heal_results: list[dict] = []
    if args.heal:
        for h in HEALS:  # sequential: correctives mutate state
            heal_results.append(_run_check(h))

    with cf.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(_run_check, c): i for i, c in enumerate(checks)}
        results: list[dict | None] = [None] * len(checks)
        for fut, i in futures.items():
            results[i] = fut.result()
    results = [r for r in results if r]

    reds = [r for r in results if not r["ok"]]
    report = {
        "date": _dt.date.today().isoformat(),
        "deep": args.deep,
        "healed": heal_results,
        "checks": results,
        "red_count": len(reds),
    }
    try:
        SCRATCH.mkdir(exist_ok=True)
        out_path = SCRATCH / f"health-{report['date']}.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        out_path = None

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        if heal_results:
            print("[doctor] heal pass:")
            _print_table(heal_results)
        print(f"[doctor] battery ({len(results)} checks):")
        _print_table(results)
        verdict = "HEALTHY" if not reds else f"{len(reds)} RED"
        n_skipped = sum(1 for r in results if r.get("skipped"))
        if n_skipped:
            verdict += f" ({n_skipped} skipped)"
        where = f"  (report: {out_path})" if out_path else ""
        print(f"[doctor] {verdict}{where}")
    return 1 if reds else 0


if __name__ == "__main__":
    sys.exit(main())
