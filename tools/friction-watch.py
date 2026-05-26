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
        d["unresolved"] = d["resolved"].lower() in ("no", "partially", "")
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
    """Unresolved entries older than age_days."""
    today = date.today()
    stale = []
    for r in rows:
        if not r["unresolved"]:
            continue
        age = (today - r["_parsed_date"]).days
        if age >= age_days:
            r["_age_days"] = age
            stale.append(r)
    return sorted(stale, key=lambda r: -r["_age_days"])


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
    }

    report = {
        "signals": {
            "concentration": [(t, n, [r["_parsed_date"].isoformat() for r in rs]) for t, n, rs in signals["concentration"]],
            "memory_sprawl": signals["memory_sprawl"],
            "stale": [{"date": r["_parsed_date"].isoformat(), "client": r["client"],
                       "type": r["type"], "age_days": r["_age_days"],
                       "desc": r["desc"][:120]} for r in signals["stale"]],
            "recurrence": signals["recurrence"],
        },
        "params": {
            "threshold": args.threshold,
            "age_days": args.age_days,
            "memory_threshold": args.memory_threshold,
        },
        "total_rows": len(rows),
        "unresolved_rows": sum(1 for r in rows if r["unresolved"]),
    }

    if args.format == "json":
        print(json.dumps(report))
        return 0

    out = render_text({"signals": signals, "params": report["params"]})
    if out:
        print(out)
    elif not args.quiet:
        print(f"[FRICTION-WATCH] No signals. Rows: {report['total_rows']} total, {report['unresolved_rows']} unresolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
