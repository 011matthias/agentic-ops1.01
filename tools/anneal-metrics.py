#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Anneal metrics: convergence + toolkit-drift measurement for /comd_system-dev.

Supplies the "measure convergence" step the self-annealing loop was missing
(rule_behaviors.md Layers 1-3 describe the tactical loop; nothing tracked whether
the toolkit was getting SHARPER cycle-over-cycle or just bigger). Reuses
tools/friction-watch.py's register parser rather than reimplementing it.

Computes, deterministically, from live repo state + git:
  - asset counts (commands / skills / agents / tools / rules + rules-LOC)
  - friction register totals, recurrence rate, memory-fix share
  - documented-vs-actual drift (CLAUDE.md advertised counts vs reality)
  - change-set size since the previous anneal cycle (git)
  - net asset delta + "smaller change-set than last cycle?" (the convergence test)

The interpretive columns (Top Finding, the converging/oscillating verdict) are
left for the agent to fill during the /comd_system-dev cycle; this tool never
fabricates a judgment.

Usage:
    uv run tools/anneal-metrics.py                 # text report
    uv run tools/anneal-metrics.py --format json   # machine-readable
    uv run tools/anneal-metrics.py --append        # append a row to the ledger

Exit 0 always (advisory tool, not a gate).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO / "tools"

# Rules discipline (resolved 2026-06-18): there is no honest repo-wide LOC budget
# (the legacy "under 500" and DECISION-TREE's "250" both contradicted the real
# ~2.2k total). The discipline is now a PER-FILE soft ceiling plus "no duplicated
# bans across rules" (see DECISION-TREE.md). The tool surfaces per-file overages
# as an advisory, NOT as documented-vs-actual drift.
PER_FILE_RULE_CEILING = 250

LEDGER_COLUMNS = [
    "Date", "Cmds", "Skills(dir/adv)", "Agents", "Tools", "Rules(files/LOC)",
    "RegRows", "Unres", "Recur%", "Mem%", "Drift", "NetD", "ChangeSet",
    "Smaller?", "Top Finding",
]
LEDGER_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|")


def _load_friction_watch():
    """Import the hyphenated tools/friction-watch.py as a module (single source
    of truth for register parsing). Mirrors hooklib.load_wire_hooks()."""
    path = TOOLS_DIR / "friction-watch.py"
    spec = importlib.util.spec_from_file_location("friction_watch", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def count_assets(repo: Path) -> dict:
    """Filesystem asset census. skills reports BOTH the skil_ dir count and the
    total dir count (the 34-vs-53 ambiguity is itself a finding)."""
    cmds = len(list((repo / ".claude" / "commands").glob("comd_*.md")))
    skills_root = repo / ".claude" / "skills"
    skill_dirs = [p for p in skills_root.iterdir() if p.is_dir()] if skills_root.is_dir() else []
    skill_total = len(skill_dirs)
    skill_skil = len([p for p in skill_dirs if p.name.startswith("skil_")])
    agents = len(list((repo / ".claude" / "agents").glob("*.md")))
    tools_root = repo / "tools"
    tools = len([p for p in tools_root.iterdir()
                 if p.is_file() and p.suffix in (".py", ".sh", ".cjs", ".mjs")]) if tools_root.is_dir() else 0
    rule_files = list((repo / ".claude" / "rules").glob("*.md"))
    rules = len(rule_files)
    per_file = sorted(
        ((p.name, len(p.read_text(encoding="utf-8", errors="replace").splitlines()))
         for p in rule_files),
        key=lambda t: t[1], reverse=True,
    )
    rules_loc = sum(loc for _, loc in per_file)
    rules_oversized = [(n, loc) for n, loc in per_file if loc > PER_FILE_RULE_CEILING]
    return {
        "cmds": cmds,
        "skills_skil": skill_skil,
        "skills_total": skill_total,
        "agents": agents,
        "tools": tools,
        "rules": rules,
        "rules_loc": rules_loc,
        "rules_oversized": rules_oversized,
    }


def _advertised(text: str, label: str) -> int | None:
    """Pull the count CLAUDE.md advertises, e.g. '**Commands** (29)'."""
    m = re.search(rf"\*\*{label}\*\*\s*\((\d+)\)", text)
    return int(m.group(1)) if m else None


def compute_drift(repo: Path, assets: dict) -> list[str]:
    """Documented-vs-actual drift: CLAUDE.md advertised counts vs reality. The
    rules-LOC budget is no longer a drift item (the per-file ceiling is an
    advisory; see oversized_rule_advisory)."""
    drift: list[str] = []
    claude_md = repo / "CLAUDE.md"
    if claude_md.is_file():
        text = claude_md.read_text(encoding="utf-8", errors="replace")
        checks = [
            ("Commands", assets["cmds"], str(assets["cmds"])),
            ("Skills", assets["skills_skil"],
             f"{assets['skills_skil']} skil_ dirs / {assets['skills_total']} total"),
            ("Agents", assets["agents"], str(assets["agents"])),
            ("Rules", assets["rules"], str(assets["rules"])),
        ]
        for label, actual, actual_str in checks:
            adv = _advertised(text, label)
            if adv is not None and adv != actual:
                drift.append(f"{label}: CLAUDE.md advertises {adv}, actual {actual_str}")
    return drift


def changeset_since(repo: Path, since_date: str | None) -> int | None:
    """Count distinct primitive files touched in git since `since_date`
    (the previous cycle). None when there is no prior cycle or git is unavailable."""
    if not since_date:
        return None
    try:
        proc = subprocess.run(
            ["git", "log", f"--since={since_date}", "--name-only",
             "--pretty=format:", "--", ".claude/", "tools/",
             "docs/friction-register.md"],
            cwd=str(repo), capture_output=True, text=True, timeout=15,
        )
        if proc.returncode != 0:
            return None
        files = {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}
        return len(files)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def asset_total(assets: dict) -> int:
    """The single number whose trend should stabilize or fall (skil_ basis)."""
    return (assets["cmds"] + assets["skills_skil"] + assets["agents"]
            + assets["tools"] + assets["rules"])


def last_ledger_row(ledger: Path) -> dict | None:
    """Parse the most recent data row of the ledger into a cell dict, or None."""
    if not ledger.is_file():
        return None
    rows = [ln for ln in ledger.read_text(encoding="utf-8", errors="replace").splitlines()
            if LEDGER_ROW_RE.match(ln)]
    if not rows:
        return None
    cells = [c.strip() for c in rows[-1].strip().strip("|").split("|")]
    if len(cells) < len(LEDGER_COLUMNS):
        return None
    return dict(zip(LEDGER_COLUMNS, cells))


def _lead_int(cell: str) -> int | None:
    m = re.match(r"\s*(\d+)", cell or "")
    return int(m.group(1)) if m else None


def build_metrics(repo: Path, today: str) -> dict:
    fw = _load_friction_watch()
    register_path = repo / "docs" / "friction-register.md"
    ledger_path = repo / "docs" / "anneal-ledger.md"
    assets = count_assets(repo)
    rows = fw.parse_register(register_path.read_text(encoding="utf-8", errors="replace")) if register_path.is_file() else []
    total_rows = len(rows)
    unresolved = sum(1 for r in rows if r["unresolved"])
    # Gate-held rows (friction-watch's hook_contained sub-bucket: Resolved
    # reads "No (caught by hook)" etc.) are permanently backstopped by a
    # live gate -- they can never flip to Yes, so counting them in the
    # convergence Unres made the metric monotonically rising bookkeeping.
    # Actionable = the backlog a cycle can actually shrink.
    gate_held = sum(1 for r in rows if r.get("hook_contained"))
    actionable = unresolved - gate_held
    recurrence = fw.find_recurrence(rows)
    recur_sigs = len(recurrence)
    distinct_sigs = len({(r["type"], " ".join(re.findall(r"\w+", r["desc"].lower())[:6])) for r in rows}) or 1
    recur_pct = round(100 * recur_sigs / distinct_sigs, 1)
    mem_rows = sum(1 for r in rows if "memory" in r["fix"].lower())
    mem_pct = round(100 * mem_rows / total_rows, 1) if total_rows else 0.0
    drift = compute_drift(repo, assets)

    prior = last_ledger_row(ledger_path)
    prior_date = prior["Date"] if prior else None
    changeset = changeset_since(repo, prior_date)

    total = asset_total(assets)
    net_delta = None
    smaller = None
    if prior:
        prior_total = sum(filter(None, [
            _lead_int(prior.get("Cmds", "")),
            _lead_int(prior.get("Skills(dir/adv)", "")),
            _lead_int(prior.get("Agents", "")),
            _lead_int(prior.get("Tools", "")),
            _lead_int(prior.get("Rules(files/LOC)", "")),
        ]))
        net_delta = total - prior_total
        prior_changeset = _lead_int(prior.get("ChangeSet", ""))
        if changeset is not None and prior_changeset is not None:
            smaller = changeset < prior_changeset

    return {
        "date": today,
        "assets": assets,
        "asset_total": total,
        "register": {"total_rows": total_rows, "unresolved": unresolved,
                     "gate_held": gate_held, "actionable": actionable},
        "recurrence_pct": recur_pct,
        "memory_fix_pct": mem_pct,
        "drift": drift,
        "changeset_size": changeset,
        "net_asset_delta": net_delta,
        "smaller_than_last": smaller,
        "prior_cycle_date": prior_date,
    }


def to_row(m: dict) -> str:
    a = m["assets"]
    cells = [
        m["date"],
        str(a["cmds"]),
        f"{a['skills_skil']}/{a['skills_total']}",
        str(a["agents"]),
        str(a["tools"]),
        f"{a['rules']}/{a['rules_loc']}",
        str(m["register"]["total_rows"]),
        # Leading int = ACTIONABLE unresolved (what a cycle can shrink);
        # gate-held rows are reported but excluded from the convergence
        # signal. _lead_int on prior rows keeps old plain-int cells readable.
        f"{m['register']['actionable']} (+{m['register']['gate_held']} held)",
        f"{m['recurrence_pct']}",
        f"{m['memory_fix_pct']}",
        str(len(m["drift"])),
        "-" if m["net_asset_delta"] is None else f"{m['net_asset_delta']:+d}",
        "-" if m["changeset_size"] is None else str(m["changeset_size"]),
        {None: "-", True: "yes", False: "no"}[m["smaller_than_last"]],
        "?",  # Top Finding - filled by the agent during the cycle
    ]
    return "| " + " | ".join(cells) + " |"


def render_text(m: dict) -> str:
    a = m["assets"]
    lines = [
        "=" * 64,
        "[ANNEAL-METRICS] convergence + toolkit drift",
        "=" * 64,
        f"  assets: {a['cmds']} cmds, {a['skills_skil']} skills "
        f"({a['skills_total']} dirs total), {a['agents']} agents, "
        f"{a['tools']} tools, {a['rules']} rules ({a['rules_loc']} LOC) "
        f"-> total {m['asset_total']}",
        f"  friction register: {m['register']['total_rows']} rows, "
        f"{m['register']['unresolved']} unresolved "
        f"({m['register']['actionable']} actionable, "
        f"{m['register']['gate_held']} gate-held); "
        f"recurrence {m['recurrence_pct']}%, "
        f"memory-fix {m['memory_fix_pct']}%",
    ]
    if m["net_asset_delta"] is not None:
        lines.append(
            f"  vs last cycle ({m['prior_cycle_date']}): net asset "
            f"{m['net_asset_delta']:+d}, change-set {m['changeset_size']} files, "
            f"smaller-than-last={ {None:'n/a',True:'yes',False:'no'}[m['smaller_than_last']] }"
        )
    else:
        lines.append("  vs last cycle: none (baseline row)")
    if m["drift"]:
        lines.append(f"  DRIFT ({len(m['drift'])}) - documented vs actual:")
        for d in m["drift"]:
            lines.append(f"    - {d}")
    else:
        lines.append("  drift: none")
    over = a.get("rules_oversized") or []
    if over:
        lines.append(
            f"  advisory: {len(over)} rule file(s) over the {PER_FILE_RULE_CEILING}-line "
            f"per-file ceiling (split candidates): "
            + ", ".join(f"{n} ({loc})" for n, loc in over)
        )
    lines.append("=" * 64)
    return "\n".join(lines)


def append_row(ledger: Path, row: str) -> None:
    if not ledger.is_file():
        # Defensive: the ledger should already exist; create a minimal one.
        header = (
            "# Anneal Ledger\n\n"
            "One row per /comd_system-dev (anneal) cycle. Generated by "
            "`tools/anneal-metrics.py --append`.\n\n"
            "| " + " | ".join(LEDGER_COLUMNS) + " |\n"
            "|" + "|".join(["---"] * len(LEDGER_COLUMNS)) + "|\n"
        )
        ledger.write_text(header, encoding="utf-8")
    with ledger.open("a", encoding="utf-8") as f:
        f.write(row + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--append", action="store_true",
                    help="append the computed row to docs/anneal-ledger.md")
    ap.add_argument("--date", default=None,
                    help="override the cycle date (YYYY-MM-DD); default today")
    ap.add_argument("--repo", default=None, help="repo root override (tests)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve() if args.repo else REPO
    today = args.date or date.today().isoformat()
    ledger_path = repo / "docs" / "anneal-ledger.md"

    m = build_metrics(repo, today)
    row = to_row(m)

    if args.append:
        append_row(ledger_path, row)

    if args.format == "json":
        print(json.dumps(m, ensure_ascii=False))
    else:
        print(render_text(m))
        if args.append:
            print(f"\nappended row to docs/anneal-ledger.md:\n{row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
