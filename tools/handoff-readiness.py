# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""handoff-readiness.py — score a client's handoff-ready state.

Why this exists
---------------
Several clients sit dormant under `workspace/clients/{client}/automations/`.
Whether a given client is *actually* ready to hand off (or is just stale and
needs work) is a judgement call the spec-staleness tool flags but doesn't
answer. This script gives a structured readiness scorecard so decisions
("close out", "archive dormant", "actually work it") are made from facts,
not memory of when you last touched the folder.

Checks
------
  1) ALL specs in 4-live/ or _archive/ (none stuck in 2-build/3-test)
  2) infrastructure.yaml present + has a `status:` field or equivalent
  3) automations/ has at least one shipped automation directory
  4) comms-log.md present (handoff requires recent client agreement)
  5) Last comms-log entry within N days (default 14)

Output
------
  text:  scorecard + a single READY / NOT READY verdict + reasons
  json:  {client, ready, score, checks: [{name, passed, detail}]}

Exit 0 either way -- treat as report, not gate.

Usage
-----
  uv run tools/handoff-readiness.py {client}
  uv run tools/handoff-readiness.py {client} --comms-staleness-days 14 --format json
  uv run tools/handoff-readiness.py --all              # all clients
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLIENTS_DIR = REPO / "workspace" / "clients"
TODAY = date.today()


def parse_frontmatter_stage(text: str) -> str:
    """Best-effort extraction of a `stage:` value from a frontmatter block."""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 4)
    if end < 0:
        return ""
    for line in text[4:end].splitlines():
        m = re.match(r"^stage\s*:\s*(.*)$", line)
        if m:
            v = m.group(1).strip().strip('"').strip("'").lower()
            return v
    return ""


def find_last_date(text: str) -> date | None:
    """Most-recent YYYY-MM-DD anywhere in the file (comms-log format).
    Returns the maximum date found, or None."""
    dates: list[date] = []
    for m in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text):
        try:
            dates.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            continue
    return max(dates) if dates else None


def assess(client_dir: Path, comms_staleness_days: int) -> dict:
    checks: list[dict] = []
    specs_dir = client_dir / "specs"
    in_flight_specs: list[str] = []
    if specs_dir.is_dir():
        for stage_folder in ("2-build", "3-test"):
            sf = specs_dir / stage_folder
            if sf.is_dir():
                for spec_file in sf.glob("*.md"):
                    if spec_file.name == "README.md":
                        continue
                    in_flight_specs.append(
                        str(spec_file.relative_to(REPO)).replace("\\", "/"))
    checks.append({
        "name": "specs-completed",
        "passed": len(in_flight_specs) == 0,
        "detail": (f"{len(in_flight_specs)} spec(s) in 2-build/3-test"
                   if in_flight_specs else "all specs out of in-progress stages"),
        "data": in_flight_specs[:5],
    })

    infra = client_dir / "infrastructure.yaml"
    has_infra = infra.is_file()
    infra_has_status = False
    if has_infra:
        try:
            text = infra.read_text(encoding="utf-8", errors="replace")
            infra_has_status = bool(re.search(r"^status\s*:", text, re.MULTILINE))
        except OSError:
            pass
    checks.append({
        "name": "infrastructure-yaml-present",
        "passed": has_infra,
        "detail": "infrastructure.yaml " + ("present" if has_infra else "MISSING"),
    })
    checks.append({
        "name": "infrastructure-yaml-status-field",
        "passed": infra_has_status,
        "detail": ("status: field present" if infra_has_status
                   else "status: field missing (add `status: live|paused|dormant`)"),
    })

    automations = client_dir / "automations"
    auto_dirs: list[str] = []
    if automations.is_dir():
        for d in automations.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                auto_dirs.append(d.name)
    checks.append({
        "name": "automations-present",
        "passed": len(auto_dirs) > 0,
        "detail": (f"{len(auto_dirs)} automation dir(s): {', '.join(auto_dirs[:5])}"
                   if auto_dirs else "no automations/ directory or empty"),
    })

    comms_log = client_dir / "context" / "comms-log.md"
    comms_present = comms_log.is_file()
    last_comms: date | None = None
    if comms_present:
        try:
            text = comms_log.read_text(encoding="utf-8", errors="replace")
            last_comms = find_last_date(text)
        except OSError:
            pass
    checks.append({
        "name": "comms-log-present",
        "passed": comms_present,
        "detail": "comms-log.md " + ("present" if comms_present else "MISSING"),
    })

    if comms_present and last_comms is not None:
        age = (TODAY - last_comms).days
        fresh = age <= comms_staleness_days
        checks.append({
            "name": "comms-log-fresh",
            "passed": fresh,
            "detail": (f"last entry {last_comms.isoformat()} ({age} days ago, "
                       f"threshold {comms_staleness_days})"),
        })
    else:
        checks.append({
            "name": "comms-log-fresh",
            "passed": False,
            "detail": "no parseable date in comms-log (or comms-log absent)",
        })

    score = sum(1 for c in checks if c["passed"])
    ready = score == len(checks)
    return {
        "client": client_dir.name,
        "ready": ready,
        "score": f"{score}/{len(checks)}",
        "checks": checks,
    }


def emit_text(payload: dict) -> None:
    verdict = "READY" if payload["ready"] else "NOT READY"
    print(f"\n== {payload['client']} ==  verdict: {verdict}  ({payload['score']})")
    for c in payload["checks"]:
        mark = "[x]" if c["passed"] else "[ ]"
        print(f"  {mark} {c['name']:<35} -- {c['detail']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("client", nargs="?", help="client name (or use --all)")
    ap.add_argument("--all", action="store_true", help="check every client")
    ap.add_argument("--comms-staleness-days", type=int, default=14)
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    if args.all:
        clients = [d for d in sorted(CLIENTS_DIR.iterdir()) if d.is_dir()] if CLIENTS_DIR.is_dir() else []
    elif args.client:
        d = CLIENTS_DIR / args.client
        if not d.is_dir():
            print(f"ERROR: no client folder {d}", file=sys.stderr)
            return 2
        clients = [d]
    else:
        print("usage: handoff-readiness.py {client} | --all", file=sys.stderr)
        return 2

    results = [assess(c, args.comms_staleness_days) for c in clients]
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            emit_text(r)
        if args.all:
            ready_count = sum(1 for r in results if r["ready"])
            print(f"\n{ready_count}/{len(results)} client(s) READY for handoff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
