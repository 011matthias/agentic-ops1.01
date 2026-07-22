# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Optimize-run overview: one oversight surface for every run, every project.

Read-only companion to tools/optimize_run.py. Two live sources, no
hand-maintained index (an index file would rot; this derives):

1. Journaled runs: every docs/optimize/<tag>/ directory on THIS checkout
   (merged history) - RUN.md frontmatter + results.tsv.
2. Active runs: every git worktree whose .claude/optimize/run.json exists
   (the engine allows one active run per checkout, so parallel runs across
   projects live in parallel worktrees). Their journals are read from the
   worktree's own tree, since the run branch is checked out there.

Grouping key: the manifest's optional `project:` frontmatter field
(convention: client slug, `sys`, `platform`, `local-web`; see
docs/optimize/RECIPES.md "Many projects" section). The engine ignores
unknown frontmatter keys, so `project:` is pure convention - old manifests
without it group under "(unassigned)".

Statuses:
  ACTIVE       run.json present in some worktree (shows where + round + best)
  CLOSED       journal ends with a `stopped` row (the run finished cleanly)
  INTERRUPTED  journal exists but no `stopped` row and no active state -
               the run died without cleanup; `resume` or `stop` it from its
               worktree/branch (warning section lists these)

Usage:
  uv run tools/optimize_overview.py [--project SLUG]

Exit 0 always (report, not a gate).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Once-per-day stamp so the SessionStart sweep advises at most once per
# calendar day instead of on every session (mirrors project_status.py).
_SWEEP_STAMP = Path(tempfile.gettempdir()) / "agentic-ops-optimize-sweep.json"


def _already_swept_today(today: _dt.date) -> bool:
    """True if today's sweep already ran. Fail-open: any error => False (run
    the sweep) rather than silently skipping it."""
    try:
        return json.loads(_SWEEP_STAMP.read_text(
            encoding="utf-8")).get("last_sweep") == today.isoformat()
    except (OSError, ValueError):
        return False


def _mark_swept_today(today: _dt.date) -> None:
    try:
        _SWEEP_STAMP.write_text(json.dumps({"last_sweep": today.isoformat()}),
                                encoding="utf-8")
    except OSError:
        pass

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """RUN.md YAML frontmatter as a dict; {} if absent or invalid."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def tsv_summary(text: str) -> dict:
    """Summarize a results.tsv: baseline, best kept score, rounds, last status.

    Kept scores only ratchet (the engine reverts losers), so the LAST `keep`
    row's score IS the best. `rounds` counts experiment rows (not baseline,
    not the final `stopped` row).
    """
    rows = [ln.split("\t") for ln in text.splitlines() if ln.strip()]
    out = {"baseline": None, "best": None, "rounds": 0, "keeps": 0,
           "last_status": None, "minutes": None}
    stamps: list[_dt.datetime] = []
    for row in rows[1:]:  # skip header
        if len(row) < 5:
            continue
        # Column 7 (timestamp) was added 2026-07-22. Runs closed before that
        # have six-column rows, so its absence is normal, not a defect: the
        # timing block is simply omitted for them.
        if len(row) >= 7:
            try:
                stamps.append(_dt.datetime.fromisoformat(row[6]))
            except ValueError:
                pass
        status = row[4]
        out["last_status"] = status
        if status == "baseline":
            out["baseline"] = row[2]
            out["best"] = row[2]
        elif status == "keep":
            out["best"] = row[2]
            out["keeps"] += 1
        if status not in ("baseline", "stopped"):
            out["rounds"] += 1
    if len(stamps) >= 2:
        out["minutes"] = (max(stamps) - min(stamps)).total_seconds() / 60.0
    return out


def classify(tag: str, summary: dict | None, active: dict | None) -> str:
    if active is not None:
        return "ACTIVE"
    if summary and summary["last_status"] == "stopped":
        return "CLOSED"
    return "INTERRUPTED"


def repo_root() -> str:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print("not inside a git repository", file=sys.stderr)
        sys.exit(2)
    return proc.stdout.strip()


def origin_run_tags(repo: str) -> set[str] | None:
    """Run tags present under docs/optimize/ on origin/main, or None when
    that ref is unavailable (no remote, fresh fixture repo, offline clone).

    This view derives from the CHECKOUT's working tree, so a checkout behind
    origin/main silently under-reports closed runs with no signal at all -
    the audit that motivated this tool hit exactly that (a 13-PR-stale main
    showed 1 of 4 closed runs, and every derived metric was wrong by the same
    factor). Comparing against the remote costs one cheap plumbing call.
    """
    proc = subprocess.run(
        ["git", "-C", repo, "ls-tree", "-d", "--name-only",
         "origin/main:docs/optimize"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return {ln.strip().rstrip("/") for ln in proc.stdout.splitlines()
            if ln.strip()}


def worktree_paths(repo: str) -> list[str]:
    proc = subprocess.run(["git", "-C", repo, "worktree", "list", "--porcelain"],
                          capture_output=True, text=True)
    paths = []
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            p = line[len("worktree "):].strip()
            if os.path.isdir(p):
                paths.append(p)
    return paths


def active_runs(repo: str) -> dict[str, dict]:
    """tag -> {state..., 'worktree': path} for every worktree with run.json."""
    found: dict[str, dict] = {}
    for wt in worktree_paths(repo):
        p = os.path.join(wt, ".claude", "optimize", "run.json")
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            found[f"<unparseable:{wt}>"] = {"worktree": wt, "corrupt": True}
            continue
        state["worktree"] = wt
        found[state.get("tag", f"<untagged:{wt}>")] = state
    return found


def journaled_runs(root: str) -> dict[str, dict]:
    """tag -> {'meta':..., 'summary':..., 'has_summary':...} from a tree."""
    base = os.path.join(root, "docs", "optimize")
    runs: dict[str, dict] = {}
    if not os.path.isdir(base):
        return runs
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        manifest = os.path.join(d, "RUN.md")
        if not os.path.isdir(d) or not os.path.isfile(manifest):
            continue
        with open(manifest, encoding="utf-8") as f:
            meta = parse_frontmatter(f.read())
        summary = None
        tsv = os.path.join(d, "results.tsv")
        if os.path.isfile(tsv):
            with open(tsv, encoding="utf-8") as f:
                summary = tsv_summary(f.read())
        runs[name] = {
            "meta": meta,
            "summary": summary,
            "has_summary": os.path.isfile(os.path.join(d, "SUMMARY.md")),
        }
    return runs


PLANNING_MODEL_RE = re.compile(r"^workspace/projects/[^/]+/[^/]+\.json$",
                               re.IGNORECASE)


def asset_kind(meta: dict) -> str:
    """'planning-model' when every declared asset is a workspace/projects
    JSON model the agent authored for the run itself; 'production' when the
    run touches a real shipped artifact (page, source file, config); '?' when
    the manifest declares no assets.

    The split matters more than any score: a harness that only ever optimizes
    its own planning JSON is advising itself, and no other metric surfaces
    that drift.
    """
    assets = [str(a).replace("\\", "/") for a in (meta.get("assets") or [])]
    if not assets:
        return "?"
    return ("planning-model" if all(PLANNING_MODEL_RE.match(a) for a in assets)
            else "production")


def print_scoreboard(runs: dict[str, dict], active: dict[str, dict],
                     stale: set[str], origin_known: bool) -> None:
    """The loop's own metrics, derived from the same artifacts as the fleet
    view. Measures the HARNESS, not the assets it optimizes."""
    total = len(runs)
    statuses = {tag: classify(tag, info["summary"], active.get(tag))
                for tag, info in runs.items()}
    closed = [t for t, s in statuses.items() if s == "CLOSED"]
    rounds = keeps = 0
    for info in runs.values():
        s = info["summary"]
        if not s:
            continue
        rounds += s["rounds"]
        keeps += s["keeps"]
    kinds: dict[str, int] = {}
    scorers: dict[str, int] = {}
    for info in runs.values():
        kinds[asset_kind(info["meta"])] = kinds.get(asset_kind(info["meta"]), 0) + 1
        sc = str(info["meta"].get("scorer") or "?").rsplit("/", 1)[-1]
        scorers[sc] = scorers.get(sc, 0) + 1

    print("\nSCOREBOARD (the loop measuring itself)")
    print(f"  runs                  {total} total | "
          + " | ".join(f"{n} {s}" for s, n in sorted(
              {s: list(statuses.values()).count(s)
               for s in set(statuses.values())}.items())))
    print(f"  experiment rounds     {rounds}")
    print("  keep rate             "
          + (f"{keeps}/{rounds} ({100 * keeps / rounds:.0f}%)"
             if rounds else "n/a (no rounds)"))
    print("  rounds per run        "
          + (f"{rounds / total:.1f} avg" if total else "n/a"))
    timed = [(t, i["summary"]) for t, i in runs.items()
             if i["summary"] and i["summary"].get("minutes") is not None
             and i["summary"]["rounds"]]
    if timed:
        per = sorted(s["minutes"] / s["rounds"] for _, s in timed)
        med = per[len(per) // 2]
        print(f"  minutes per round     {med:.1f} median over {len(timed)}"
              f"/{total} timed run(s)")
    else:
        print(f"  minutes per round     n/a (0/{total} runs carry timestamps)")
    print("  closed with SUMMARY   "
          + (f"{sum(1 for t in closed if runs[t]['has_summary'])}/{len(closed)}"
             if closed else "n/a (none closed)"))
    prod = kinds.get("production", 0)
    print(f"  asset kind            {prod}/{total} production"
          f" ({', '.join(f'{n} {k}' for k, n in sorted(kinds.items()))})")
    print("                        production = any asset outside "
          "workspace/projects/*/*.json")
    reused = [f"{s}x{n}" for s, n in sorted(scorers.items()) if n > 1]
    print(f"  scorer reuse          {len(scorers)} scorer(s) over {total} run(s)"
          + (f"; reused: {', '.join(reused)}" if reused
             else "; none reused across runs"))
    if not origin_known:
        completeness = "UNKNOWN (no origin/main ref to compare against)"
    elif stale:
        completeness = f"MISSING {len(stale)} run(s) present on origin/main"
    else:
        completeness = "matches origin/main"
    print(f"  checkout completeness {completeness}")


def run_sweep(once_per_day: bool) -> int:
    """SessionStart sweep: surface only what needs a human decision.

    The fleet view was wired into no hook, no command and no sweep, so
    INTERRUPTED runs and closed-without-SUMMARY runs surfaced only if someone
    remembered to invoke it - the exact recall dependency the rest of the
    harness designs around. Silent when the fleet is clean, so it costs a
    session nothing to have running. Fail-open: any error exits 0 quietly.
    """
    today = _dt.date.today()
    if once_per_day and _already_swept_today(today):
        return 0
    try:
        repo = repo_root()
        active = active_runs(repo)
        runs = journaled_runs(repo)
        for tag, state in active.items():
            if not state.get("corrupt"):
                runs.setdefault(tag, {"meta": {}, "summary": None,
                                      "has_summary": False})
        notes: list[str] = []
        for tag, info in sorted(runs.items()):
            status = classify(tag, info["summary"], active.get(tag))
            if status == "ACTIVE":
                a = active[tag]
                notes.append(f"{tag}: ACTIVE at r{a.get('round', '?')} "
                             f"(best={a.get('best_score')}) in "
                             f"{a.get('worktree', '?')}")
            elif status == "INTERRUPTED":
                notes.append(f"{tag}: INTERRUPTED - no `stopped` row and no "
                             f"run state; `resume` or `stop` it from "
                             f"optimize/{tag}")
            elif status == "CLOSED" and not info["has_summary"]:
                notes.append(f"{tag}: closed without SUMMARY.md - write it "
                             "from results.tsv before shipping")
        for state in active.values():
            if state.get("corrupt"):
                notes.append(f"{state['worktree']}: unparseable run.json - "
                             "repair or `stop` from that worktree")
        if notes:
            print(f"[optimize] {len(notes)} run(s) need attention "
                  "(uv run tools/optimize_overview.py for the full view):")
            for n in notes:
                print(f"  - {n}")
    except Exception:
        return 0  # fail-open: a sweep must never block a session
    if once_per_day:
        _mark_swept_today(today)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="overview of all optimize runs")
    ap.add_argument("--project", help="only show runs for this project slug")
    ap.add_argument("--scoreboard", action="store_true",
                    help="also print the loop's own metrics (keep rate, "
                         "rounds/run, production-vs-planning asset split)")
    ap.add_argument("--sweep", action="store_true",
                    help="SessionStart mode: print a one-line advisory ONLY "
                         "when something needs attention (active run, "
                         "interrupted run, closed run missing SUMMARY), "
                         "silent otherwise. Always exits 0.")
    ap.add_argument("--once-per-day", action="store_true",
                    help="with --sweep: advise at most once per calendar day")
    args = ap.parse_args(argv)

    if args.sweep:
        return run_sweep(args.once_per_day)

    repo = repo_root()
    active = active_runs(repo)

    # Journaled runs on this checkout, then overlay each ACTIVE run's journal
    # read from its own worktree (its docs live on the run branch there).
    runs = journaled_runs(repo)
    for tag, state in active.items():
        if state.get("corrupt"):
            continue
        wt_runs = journaled_runs(state["worktree"])
        if tag in wt_runs:
            runs[tag] = wt_runs[tag]
        runs.setdefault(tag, {"meta": {}, "summary": None,
                              "has_summary": False})

    grouped: dict[str, list[tuple[str, dict]]] = {}
    for tag, info in sorted(runs.items()):
        project = str(info["meta"].get("project") or "(unassigned)")
        if args.project and project != args.project:
            continue
        grouped.setdefault(project, []).append((tag, info))

    print(f"OPTIMIZE RUNS OVERVIEW  (repo: {repo})")
    if not grouped:
        print("  no runs found"
              + (f" for project {args.project!r}" if args.project else ""))
    warnings: list[str] = []
    for project in sorted(grouped):
        print(f"\nproject: {project}")
        for tag, info in grouped[project]:
            s = info["summary"]
            a = active.get(tag)
            status = classify(tag, s, a)
            meta = info["meta"]
            direction = meta.get("direction", "?")
            bits = [f"  {tag:<28} {status:<12}"]
            if a:
                bits.append(f"r{a.get('round', '?')} best={a.get('best_score')}"
                            f" ({direction}) worktree={a['worktree']}")
            elif s:
                bits.append(f"{s['rounds']} round(s)  {s['baseline']} -> "
                            f"{s['best']} ({direction})"
                            f"  summary={'yes' if info['has_summary'] else 'NO'}")
            else:
                bits.append("(no journal)")
            print(" ".join(bits))
            if status == "INTERRUPTED":
                warnings.append(
                    f"{tag}: journal has no `stopped` row and no active state - "
                    f"`resume` or `stop` it from branch optimize/{tag}")
            if status == "CLOSED" and not info["has_summary"]:
                warnings.append(f"{tag}: closed without SUMMARY.md - write it "
                                "from results.tsv before shipping")
    for tag, state in active.items():
        if state.get("corrupt"):
            warnings.append(f"{state['worktree']}: unparseable run.json - "
                            "repair or `stop` from that worktree")

    origin_tags = origin_run_tags(repo)
    stale = (origin_tags - set(runs)) if origin_tags else set()
    if stale:
        warnings.append(
            f"STALE CHECKOUT: {len(stale)} run(s) exist on origin/main but "
            f"not in this checkout, so every count above under-reports: "
            f"{', '.join(sorted(stale))}. Fix with `git fetch && git merge "
            "origin/main`, or read one directly via `git show "
            "origin/main:docs/optimize/<tag>/results.tsv`.")

    if args.scoreboard:
        # scope the metrics to whatever the fleet view just showed, so
        # --project narrows both consistently
        shown = {tag: info for rows in grouped.values() for tag, info in rows}
        print_scoreboard(shown, active, stale, origin_tags is not None)

    if warnings:
        print("\nWARNINGS")
        for w in warnings:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
