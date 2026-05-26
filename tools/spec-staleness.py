# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""spec-staleness.py — surface in-flight specs that have gone stale.

Why this exists
---------------
The agentic-ops spec pipeline has stages 1-spec / 2-build / 3-test / 4-live.
Several clients have specs that sit in 2-build or 3-test with `updated:`
dates 70-100 days old. They are reported as in-flight by /comd_status-check
but are almost certainly either dormant (client handed off, work stopped)
or actually complete-without-frontmatter-update.

Rather than unilaterally mutating spec frontmatter, this script REPORTS
the offenders so the user (or a /system-dev step) can decide:
  (a) close out -- move to 4-live + update frontmatter, OR
  (b) archive  -- add `dormant: true` to frontmatter, OR
  (c) actually work them -- the staleness was a real backlog signal

Usage
-----
  uv run tools/spec-staleness.py [--days N] [--format json]
  Default: report any 2-build or 3-test spec with updated > 30 days old,
  ranked by staleness.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLIENTS = REPO / "workspace" / "clients"
STAGES_INPROGRESS = ("2-build", "3-test")
TODAY = date.today()


def parse_frontmatter(text: str) -> dict:
    """Return frontmatter dict from a markdown file. Loose YAML parsing --
    keys we care about (stage, updated, needs_fixes) are simple scalars."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    fm: dict = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            # strip surrounding quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            fm[key] = val
    return fm


def parse_date(s: str) -> date | None:
    if not s:
        return None
    s = s.strip().strip('"').strip("'")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def scan(days_threshold: int) -> list[dict]:
    if not CLIENTS.is_dir():
        return []
    hits: list[dict] = []
    for client_dir in sorted(CLIENTS.iterdir()):
        if not client_dir.is_dir():
            continue
        specs_dir = client_dir / "specs"
        if not specs_dir.is_dir():
            continue
        for stage_name in STAGES_INPROGRESS:
            stage_dir = specs_dir / stage_name
            if not stage_dir.is_dir():
                continue
            for spec_file in stage_dir.glob("*.md"):
                try:
                    text = spec_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                fm = parse_frontmatter(text)
                upd = parse_date(fm.get("updated", ""))
                if upd is None:
                    continue
                age = (TODAY - upd).days
                if age < days_threshold:
                    continue
                hits.append({
                    "client": client_dir.name,
                    "stage": stage_name,
                    "spec_id": fm.get("id", "?"),
                    "file": str(spec_file.relative_to(REPO)).replace("\\", "/"),
                    "updated": upd.isoformat(),
                    "age_days": age,
                    "needs_fixes": fm.get("needs_fixes", "").lower() == "true",
                    "dormant_marker": fm.get("dormant", "").lower() == "true",
                })
    hits.sort(key=lambda h: (-h["age_days"], h["client"]))
    return hits


def emit_text(hits: list[dict], days_threshold: int) -> None:
    if not hits:
        print(f"No in-flight specs older than {days_threshold} days. Clean.")
        return
    print(f"{len(hits)} in-flight spec(s) older than {days_threshold} days:")
    print()
    print(f"  {'client':<24} {'stage':<8} {'id':<8} {'updated':<12} {'age':>5}  flags")
    print(f"  {'-'*24} {'-'*8} {'-'*8} {'-'*12} {'-'*5}  {'-'*20}")
    for h in hits:
        flags = []
        if h["needs_fixes"]:
            flags.append("needs_fixes")
        if h["dormant_marker"]:
            flags.append("dormant")
        flag_str = " ".join(flags)
        print(f"  {h['client']:<24} {h['stage']:<8} {h['spec_id']:<8} "
              f"{h['updated']:<12} {h['age_days']:>5}d  {flag_str}")
        print(f"    -> {h['file']}")
    print()
    print("Decide per spec: close out (move to 4-live), archive (set dormant: true), or work it.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="Staleness threshold (default 30)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    hits = scan(args.days)
    if args.format == "json":
        print(json.dumps({"total": len(hits), "hits": hits, "threshold_days": args.days}))
    else:
        emit_text(hits, args.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
