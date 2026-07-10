#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Friction register watcher: push-based trigger for /system-dev.

Reads docs/friction-register.md and surfaces patterns that should fire
a /system-dev session NOW rather than waiting for the user to manually
invoke /comd_review.

The self-annealing loop documented in rule_behaviors.md is pull-based:
it only fires when the user types /system-dev or /review. This script
makes it push-based by detecting:

  1. N+ unresolved entries of the same type (concentration)
  2. Same friction recurring after being marked Resolved=Yes (regression)
  3. Fix=memory entries accumulating (fragile-fix sprawl)
  4. Items aged >7 days unresolved (stale backlog)
  5. Synthesis-cadence staleness: no anneal-ledger row for >21 days, or
     docs/reviews/ never written (cadence)

Unresolved counting (2026-07-10): a row is unresolved when the Resolved
cell starts with "no" or "partial" -- INCLUDING annotated forms like
"No (caught by hook)". The old exact-match counting silently classified
the hook-contained cluster as resolved, understating the true backlog
(67 vs ~130) -- exactly the trend-flattering undercount the Goodhart
guard in comd_system-dev forbids. Hook-contained rows are reported as a
separate sub-bucket: they stay in the unresolved total and in
concentration (a contained cluster is still a consolidation trigger),
but are EXCLUDED from the stale signal (their age is meaningless; the
enforcement layer already backstops them, and letting them flood the
SessionStart advisory is noise).

Output is plain text suitable for SessionStart hook injection or terminal
display. JSON mode for programmatic consumption.

Usage:
    uv run tools/friction-watch.py
    uv run tools/friction-watch.py --format json
    uv run tools/friction-watch.py --threshold 3 --age-days 7
    uv run tools/friction-watch.py --quiet  # only output if signals present

Exit 0 always (advisory tool, not a gate).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTER = REPO / "docs" / "friction-register.md"

ROW_RE = re.compile(
    r"^\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*(?P<client>[^|]+?)\s*"
    r"\|\s*(?P<type>[^|]+?)\s*"
    r"\|\s*(?P<desc>.+?)\s*"
    r"\|\s*(?P<resolved>[^|]+?)\s*"
    r"\|\s*(?P<fix>[^|]+?)\s*\|\s*$"
)


def parse_register(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        d = m.groupdict()
        if d["date"] == "Date" or d["date"].startswith("---"):
            continue
        try:
            d["_parsed_date"] = datetime.strptime(d["date"], "%Y-%m-%d").date()
        except ValueError:
            continue
        d["client"] = d["client"].strip()
        d["type"] = d["type"].strip()
        d["resolved"] = d["resolved"].strip()
        d["fix"] = d["fix"].strip()
        resolved_lower = d["resolved"].lower()
        # Prefix match, word-boundary safe: "No (caught by hook)" and
        # "Partially (...)" are unresolved; "not applicable" is not
        # ("no" needs a word boundary; "partial" catches "partially").
        d["unresolved"] = resolved_lower == "" or bool(
            re.match(r"(no\b|partial)", resolved_lower)
        )
        # Sub-bucket: unresolved but already backstopped by a hook/gate.
        d["hook_contained"] = d["unresolved"] and bool(
            re.search(r"\b(caught|hook|gate)\b", resolved_lower)
        )
        rows.append(d)
    return rows


def find_concentration(rows: list[dict], threshold: int) -> list[tuple[str, int, list[dict]]]:
    """Friction types with N+ unresolved entries."""
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["unresolved"]:
            by_type[r["type"]].append(r)
    return [(t, len(rs), rs) for t, rs in by_type.items() if len(rs) >= threshold]


def find_memory_sprawl(rows: list[dict], threshold: int = 5) -> list[tuple[str, int]]:
    """Friction types where Fix=memory dominates (fragile remediation)."""
    by_type_total: Counter = Counter()
    by_type_memory: Counter = Counter()
    for r in rows:
        by_type_total[r["type"]] += 1
        if "memory" in r["fix"].lower():
            by_type_memory[r["type"]] += 1
    flagged = []
    for t, mem_count in by_type_memory.items():
        if mem_count >= threshold and (mem_count / by_type_total[t]) >= 0.6:
            flagged.append((t, mem_count))
    return sorted(flagged, key=lambda x: -x[1])


def find_stale(rows: list[dict], age_days: int) -> list[dict]:
    """Unresolved entries older than age_days. Hook-contained rows are
    excluded: the enforcement layer already backstops them, so their age
    carries no signal and would flood the advisory."""
    today = date.today()
    stale = []
    for r in rows:
        if not r["unresolved"] or r.get("hook_contained"):
            continue
        age = (today - r["_parsed_date"]).days
        if age >= age_days:
            r["_age_days"] = age
            stale.append(r)
    return sorted(stale, key=lambda r: -r["_age_days"])


def find_cadence(repo: Path | None = None, cadence_days: int = 21,
                 today: date | None = None) -> dict | None:
    """Synthesis-cadence staleness: fires when the newest anneal-ledger row
    is older than cadence_days, or docs/reviews/ has never been written.

    Reads the ledger from origin/main's blob WITHOUT fetching (last-fetched
    remote-tracking ref; days-scale lag is irrelevant against a 21-day
    threshold, and it sidesteps any stale working-tree copy). Falls back to
    the local file, then fail-open (None) -- advisory tool, never a gate.
    """
    repo = repo or REPO
    today = today or date.today()
    ledger_text = ""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "show", "origin/main:docs/anneal-ledger.md"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            ledger_text = out.stdout
    except Exception:
        pass
    if not ledger_text:
        try:
            ledger_text = (repo / "docs" / "anneal-ledger.md").read_text(
                encoding="utf-8", errors="replace")
        except Exception:
            ledger_text = ""

    dates = re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", ledger_text, re.MULTILINE)
    last = max(dates) if dates else None
    age = None
    if last:
        try:
            age = (today - datetime.strptime(last, "%Y-%m-%d").date()).days
        except ValueError:
            last = None

    reviews_exist = False
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "origin/main", "docs/reviews/"],
            capture_output=True, text=True, timeout=10,
        )
        reviews_exist = bool(out.stdout.strip())
    except Exception:
        pass
    if not reviews_exist:
        rv = repo / "docs" / "reviews"
        reviews_exist = rv.is_dir() and any(rv.glob("*.md"))

    breaches = []
    if last is None:
        breaches.append("no anneal-ledger row found -- run /comd_system-dev")
    elif age is not None and age > cadence_days:
        breaches.append(
            f"no anneal-ledger row for {age}d (>{cadence_days}d) -- run /comd_system-dev")
    if not reviews_exist:
        breaches.append("docs/reviews/ never written -- run /comd_review --save")
    if not breaches:
        return None
    return {"last_ledger_row": last, "ledger_age_days": age,
            "reviews_exist": reviews_exist, "breaches": breaches}


def find_recurrence(rows: list[dict]) -> list[tuple[str, str, int]]:
    """Same (type, description-prefix) appearing 2+ times.

    Description prefix is first 6 words; rough but catches most repeats
    without needing an embedding.
    """
    sig: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        prefix_words = re.findall(r"\w+", r["desc"].lower())[:6]
        prefix = " ".join(prefix_words)
        sig[(r["type"], prefix)].append(r)
    return [(t, p, len(rs)) for (t, p), rs in sig.items() if len(rs) >= 2]


def render_text(report: dict) -> str:
    lines = []
    sigs = report["signals"]

    if not any(sigs.values()):
        return ""

    lines.append("=" * 64)
    lines.append("[FRICTION-WATCH] Push-based /system-dev trigger")
    lines.append("=" * 64)

    if sigs["concentration"]:
        lines.append("\nCONCENTRATION (N+ unresolved entries of same type):")
        for t, n, _rows in sigs["concentration"]:
            lines.append(f"  - {t}: {n} unresolved -> consider /comd_system-dev to resolve as a batch")

    if sigs["memory_sprawl"]:
        lines.append("\nMEMORY-SPRAWL (Fix=memory dominates, fragile remediation):")
        for t, n in sigs["memory_sprawl"]:
            lines.append(f"  - {t}: {n} memory-only fixes -> upgrade to hook/tool per rule_behaviors Layer 1")

    if sigs["stale"]:
        lines.append(f"\nSTALE BACKLOG (>{report['params']['age_days']} days unresolved):")
        for r in sigs["stale"][:5]:
            lines.append(f"  - [{r['_parsed_date']}] {r['client']}/{r['type']} ({r['_age_days']}d) -- {r['desc'][:80]}...")
        if len(sigs["stale"]) > 5:
            lines.append(f"  ... and {len(sigs['stale']) - 5} more")

    if sigs["recurrence"]:
        lines.append("\nRECURRENCE (same friction signature 2+ times):")
        for t, prefix, n in sigs["recurrence"][:5]:
            lines.append(f"  - {t} / '{prefix}...' ({n}x)")

    if sigs.get("cadence"):
        lines.append("\nCADENCE (synthesis loop staleness):")
        for b in sigs["cadence"]["breaches"]:
            lines.append(f"  - {b}")

    lines.append("\nRECOMMENDATION: run /comd_system-dev --audit-only to triage.")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--threshold", type=int, default=3,
                    help="N+ unresolved of same type triggers concentration signal (default 3)")
    ap.add_argument("--age-days", type=int, default=7,
                    help="Stale threshold in days (default 7)")
    ap.add_argument("--memory-threshold", type=int, default=5,
                    help="N+ memory-only fixes triggers sprawl signal (default 5)")
    ap.add_argument("--cadence-days", type=int, default=21,
                    help="Anneal-ledger staleness threshold in days (default 21)")
    ap.add_argument("--quiet", action="store_true",
                    help="Only print when signals present (good for hooks)")
    ap.add_argument("--once-per-day", action="store_true",
                    help="No-op if this flag was passed within the last 24h. "
                         "Use for SessionStart wiring so multiple sessions/day "
                         "don't re-emit the same advisory.")
    args = ap.parse_args()

    if args.once_per_day:
        import os, tempfile, time
        marker = os.path.join(tempfile.gettempdir(), "agentic-ops-friction-last")
        try:
            last = os.path.getmtime(marker) if os.path.exists(marker) else 0
        except OSError:
            last = 0
        if time.time() - last < 24 * 3600:
            return 0  # rate-limited, silent
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write(str(int(time.time())))
        except OSError:
            pass

    if not REGISTER.is_file():
        if args.format == "json":
            print(json.dumps({"signals": {}, "params": vars(args)}))
        return 0

    text = REGISTER.read_text(encoding="utf-8", errors="replace")
    rows = parse_register(text)

    signals = {
        "concentration": find_concentration(rows, args.threshold),
        "memory_sprawl": find_memory_sprawl(rows, args.memory_threshold),
        "stale": find_stale(rows, args.age_days),
        "recurrence": find_recurrence(rows),
        "cadence": find_cadence(cadence_days=args.cadence_days),
    }

    report = {
        "signals": {
            "concentration": [(t, n, [r["_parsed_date"].isoformat() for r in rs]) for t, n, rs in signals["concentration"]],
            "memory_sprawl": signals["memory_sprawl"],
            "stale": [{"date": r["_parsed_date"].isoformat(), "client": r["client"],
                       "type": r["type"], "age_days": r["_age_days"],
                       "desc": r["desc"][:120]} for r in signals["stale"]],
            "recurrence": signals["recurrence"],
            "cadence": signals["cadence"],
        },
        "params": {
            "threshold": args.threshold,
            "age_days": args.age_days,
            "memory_threshold": args.memory_threshold,
            "cadence_days": args.cadence_days,
        },
        "total_rows": len(rows),
        "unresolved_rows": sum(1 for r in rows if r["unresolved"]),
        "hook_contained_rows": sum(1 for r in rows if r.get("hook_contained")),
    }

    if args.format == "json":
        print(json.dumps(report))
        return 0

    out = render_text({"signals": signals, "params": report["params"]})
    if out:
        print(out)
    elif not args.quiet:
        print(f"[FRICTION-WATCH] No signals. Rows: {report['total_rows']} total, "
              f"{report['unresolved_rows']} unresolved "
              f"(of which {report['hook_contained_rows']} hook-contained).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
