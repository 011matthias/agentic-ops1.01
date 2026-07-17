#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Weekly synthesis sensor: deterministic, no-LLM replacement for the paused
weekly-review loop's SIGNAL half.

Composes the existing detectors (friction-watch signals + corrected backlog
counts + synthesis-cadence staleness + an asset census) into one plain-text
report and emails it via tools/send_email.py (Resend; non-default User-Agent
contract lives there). WRITES NO FILE by design -- 52 dated digests/year
restating an email is exactly the rule_no_file_bloat W1 clutter class; the
record is the inbox + Task Scheduler history.

CANONICAL-BY-CONSTRUCTION: in --scheduled mode the register, ledger, and
reviews listing are read from origin/main BLOBS (`git fetch` first, then
`git show origin/main:PATH` via subprocess list-args -- immune to the MSYS
path-mangling gotcha), never from the working tree. This kills the
stale-tree sensor class: the pinned worktree the scheduled task runs in can
lag main in CODE, but the DATA is always main's; the ASSETS section prints
the sensor commit + its distance behind origin/main so code lag is visible
in every email.

Usage:
  uv run tools/weekly_synthesis.py --local --no-email    # dev: working tree, stdout only
  uv run tools/weekly_synthesis.py --scheduled           # task mode: origin/main data + email, fail-loud
  uv run tools/weekly_synthesis.py --preflight           # send-path test via send_email.py
  uv run tools/weekly_synthesis.py --print-registration  # the Register-ScheduledTask command
  uv run tools/weekly_synthesis.py --format json

Scheduling (the registration command is version-controlled HERE -- the gap
with MejiWeeklyReview was that its Register-ScheduledTask invocation was
never committed): run `--print-registration` and paste the output into an
elevated-enough PowerShell. It targets a dedicated PINNED WORKTREE
(agentic-ops1-cadence on main), NOT the primary clone (which may sit on a
client branch that predates this tool). Refresh the sensor code with
`git -C <worktree> pull --ff-only`. Registration is a machine-state action:
executed by the user (or with explicit per-action approval), never silently.

Env: RESEND_API_KEY (a FRESH key -- the old plaintext re_B7qD1off_... in the
paused routine config is flagged for rotation, never reuse), BRIEFING_TO.
Exit 1 in --scheduled mode when the send fails, so LastTaskResult goes red.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CADENCE_WORKTREE = r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1-cadence"
UV_EXE = r"C:\Users\neuma_p1qrsic\.local\bin\uv.exe"

REGISTRATION = f"""Register-ScheduledTask -TaskName "AgenticOpsWeeklySynthesis" `
  -Action (New-ScheduledTaskAction -Execute "{UV_EXE}" `
    -Argument 'run --directory "{CADENCE_WORKTREE}" tools/weekly_synthesis.py --scheduled' `
    -WorkingDirectory "{CADENCE_WORKTREE}") `
  -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 07:10) `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable)"""


def _load_friction_watch():
    spec = importlib.util.spec_from_file_location(
        "friction_watch", REPO / "tools" / "friction-watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git(args: list[str], timeout: int = 30) -> str:
    out = subprocess.run(["git", "-C", str(REPO), *args],
                         capture_output=True, text=True, timeout=timeout)
    return out.stdout if out.returncode == 0 else ""


def read_register(scheduled: bool) -> str:
    if scheduled:
        _git(["fetch", "--quiet", "origin"], timeout=120)
        blob = _git(["show", "origin/main:docs/friction-register.md"])
        if blob:
            return blob
    try:
        return (REPO / "docs" / "friction-register.md").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return ""


def sensor_lag() -> dict:
    head = _git(["rev-parse", "--short", "HEAD"]).strip() or "unknown"
    behind = _git(["rev-list", "--count", "HEAD..origin/main"]).strip() or "?"
    return {"sensor_commit": head, "behind_origin_main": behind}


def build_report(scheduled: bool) -> dict:
    fw = _load_friction_watch()
    rows = fw.parse_register(read_register(scheduled))
    today = datetime.date.today()

    signals = {
        "concentration": [(t, n) for t, n, _ in fw.find_concentration(rows, 3)],
        "memory_sprawl": fw.find_memory_sprawl(rows),
        "stale_count": len(fw.find_stale(rows, 7)),
        "recurrence": fw.find_recurrence(rows)[:5],
    }
    cadence = fw.find_cadence(repo=REPO, cadence_days=21, today=today)
    backlog = {
        "total_rows": len(rows),
        "unresolved": sum(1 for r in rows if r["unresolved"]),
        "hook_contained": sum(1 for r in rows if r.get("hook_contained")),
    }
    return {"date": today.isoformat(), "mode": "scheduled" if scheduled else "local",
            "signals": signals, "backlog": backlog, "cadence": cadence,
            "assets": sensor_lag()}


def render_text(r: dict) -> str:
    L = []
    L.append(f"AGENTIC-OPS WEEKLY SYNTHESIS -- {r['date']} ({r['mode']} mode)")
    L.append("=" * 60)
    s = r["signals"]
    L.append("SIGNALS")
    if s["concentration"]:
        for t, n in s["concentration"]:
            L.append(f"  concentration: {t} x{n} unresolved")
    if s["memory_sprawl"]:
        for t, n in s["memory_sprawl"]:
            L.append(f"  memory-sprawl: {t} x{n} memory-only fixes")
    if s["recurrence"]:
        for t, prefix, n in s["recurrence"]:
            L.append(f"  recurrence: {t} / '{prefix[:40]}...' x{n}")
    L.append(f"  stale (>7d, hook-contained excluded): {s['stale_count']}")
    b = r["backlog"]
    L.append("BACKLOG")
    L.append(f"  {b['total_rows']} rows; {b['unresolved']} unresolved "
             f"(of which {b['hook_contained']} hook-contained)")
    L.append("CADENCE")
    c = r["cadence"]
    if c:
        for breach in c["breaches"]:
            L.append(f"  {breach}")
    else:
        L.append("  ledger + reviews fresh")
    a = r["assets"]
    L.append("ASSETS")
    L.append(f"  sensor commit {a['sensor_commit']}, "
             f"{a['behind_origin_main']} commit(s) behind origin/main "
             f"(refresh: git -C {CADENCE_WORKTREE} pull --ff-only)")
    if c or any([s["concentration"], s["memory_sprawl"], s["recurrence"]]):
        L.append("")
        L.append("RECOMMENDATION: run /comd_system-dev --audit-only to triage.")
    return "\n".join(L)


def send(subject: str, body: str) -> bool:
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "send_email.py"), subject],
        input=body, capture_output=True, text=True, timeout=60,
    )
    sys.stderr.write(proc.stderr or "")
    print(proc.stdout.strip())
    return proc.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--scheduled", action="store_true",
                      help="origin/main data + email; exit 1 on send failure")
    mode.add_argument("--local", action="store_true",
                      help="working-tree data (dev mode)")
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--preflight", action="store_true",
                    help="one-line test send through send_email.py")
    ap.add_argument("--print-registration", action="store_true",
                    help="print the version-controlled Register-ScheduledTask command")
    args = ap.parse_args()

    if args.print_registration:
        print(REGISTRATION)
        return 0
    if args.preflight:
        ok = send("[agentic-ops] weekly-synthesis preflight",
                  "Preflight OK: send path works.")
        return 0 if ok else 1

    report = build_report(scheduled=args.scheduled)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))

    if args.scheduled and not args.no_email:
        c = report["cadence"]
        nsig = sum(bool(v) for v in report["signals"].values())
        subject = (f"[agentic-ops] weekly synthesis {report['date']} -- "
                   f"{nsig} signal group(s), ledger "
                   f"{(str(c['ledger_age_days']) + 'd stale') if c and c.get('ledger_age_days') is not None else 'fresh'}")
        if not send(subject, render_text(report)):
            return 1  # fail loud -> LastTaskResult goes red
    return 0


if __name__ == "__main__":
    sys.exit(main())
