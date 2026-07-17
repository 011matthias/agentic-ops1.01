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
import json
import os
import re
import subprocess
import sys

import yaml

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
    out = {"baseline": None, "best": None, "rounds": 0, "last_status": None}
    for row in rows[1:]:  # skip header
        if len(row) < 5:
            continue
        status = row[4]
        out["last_status"] = status
        if status == "baseline":
            out["baseline"] = row[2]
            out["best"] = row[2]
        elif status == "keep":
            out["best"] = row[2]
        if status not in ("baseline", "stopped"):
            out["rounds"] += 1
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="overview of all optimize runs")
    ap.add_argument("--project", help="only show runs for this project slug")
    args = ap.parse_args(argv)

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

    if warnings:
        print("\nWARNINGS")
        for w in warnings:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
