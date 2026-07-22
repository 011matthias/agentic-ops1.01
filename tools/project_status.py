# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Per-project status-file tooling: scaffold new ones, flag stale/malformed ones.

Backs the project-status convention (rule_project_status.md + skil_project-status).
Each discrete workstream inside a client (or internal project) gets ONE
maintained status file under `workspace/clients/{client}/status/` or
`workspace/projects/{project}/status/`, a roll-up of the important elements
inside it. Shared context (a group's vision / marketing plan) lives in a group general
reference file in the same folder. This tool does the mechanical parts the
convention needs:

  - `--scaffold WORKSTREAM`  write a template status file (refuses to overwrite)
  - `--check`                list the status files, flag stale + malformed ones

WHY THIS EXISTS
---------------
There was no maintained per-project root file describing the status of the
individual elements inside a project; status was scattered across
PROJECT-BOUNDARIES.md (cross-project index), infrastructure.yaml (platform
state), spec frontmatter (spec lifecycle), and comms-log.md (the client
conversation). None roll up into "what are the moving parts of this workstream
and where does each stand." These files fill that gap as canonical operational
state (rule_no_file_bloat W1 §1), tracked outside the gitignored context/
(rule_file_placement W2). The tool keeps them honest: a status file that has
not been touched in N days is the thing the convention exists to prevent.

DESIGN
------
- Staleness is DATE-based (frontmatter `updated:` vs a reference date), not
  mtime-based: git checkouts reset mtimes, so an mtime rule would false-flag on
  every fresh clone. Date-based is deterministic and testable.
- Read-only `--check` never mutates; `--scaffold` writes one file and refuses to
  clobber an existing one (supersession is a human/agent edit, per W1 §4).
- Pure functions (`parse_frontmatter`, `compute_age_days`, `evaluate_file`) take
  their inputs explicitly so the test suite can pin "today" and avoid disk.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLIENTS_DIR = REPO_ROOT / "workspace" / "clients"
# Internal projects carry status files too (upwork-independence was the first,
# 2026-07-22). Same convention, second root; clients shadow projects on a slug
# collision, mirroring comd_resume's resolution order.
PROJECTS_DIR = REPO_ROOT / "workspace" / "projects"

# Core frontmatter keys every status file (workstream or general-ref) must carry.
REQUIRED_KEYS = ("project", "workstream", "state", "updated")
# States the convention recognizes; `--check` warns on anything else.
KNOWN_STATES = ("active", "blocked", "paused", "done", "live", "dormant", "not-started")
DEFAULT_MAX_AGE_DAYS = 21
# A status file does not need a daily heartbeat once its workstream is settled.
NON_DECAYING_STATES = ("done", "paused", "dormant")


def parse_frontmatter(content: str) -> dict:
    """Extract the leading `---` block and parse its flat `key: value` lines.

    Dependency-free on purpose (the bare pytest/CI env has no pyyaml, and the
    repo's tools lean zero-dep). Status-file frontmatter is intentionally flat —
    no nested structures — so a first-colon split is sufficient. Returns {} if
    the block is absent. Empty-key and comment lines are skipped, so malformed
    blocks degrade to {} rather than raising.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    out: dict = {}
    for line in match.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


def compute_age_days(updated, today: _dt.date) -> int | None:
    """Days between an `updated:` value and `today`. None if unparseable.

    Accepts a date object (PyYAML parses bare YYYY-MM-DD to a date) or a string.
    """
    if isinstance(updated, _dt.datetime):
        updated = updated.date()
    if isinstance(updated, _dt.date):
        return (today - updated).days
    if isinstance(updated, str):
        m = re.search(r"\d{4}-\d{2}-\d{2}", updated)
        if not m:
            return None
        try:
            d = _dt.date.fromisoformat(m.group(0))
        except ValueError:
            return None
        return (today - d).days
    return None


def evaluate_file(path: Path, today: _dt.date, max_age_days: int) -> dict:
    """Inspect one status file: state, age, staleness, and structural problems."""
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    missing = [k for k in REQUIRED_KEYS if k not in fm or fm.get(k) in (None, "")]
    if missing:
        problems.append("missing keys: " + ", ".join(missing))

    state = fm.get("state")
    if state is not None and state not in KNOWN_STATES:
        problems.append(f"unknown state: {state!r}")

    age = compute_age_days(fm.get("updated"), today)
    if "updated" in fm and age is None:
        problems.append("unparseable updated date")

    stale = (
        age is not None
        and age > max_age_days
        and state not in NON_DECAYING_STATES
    )

    return {
        "file": path.name,
        "workstream": fm.get("workstream"),
        "group": fm.get("group") or "",
        "state": state,
        "updated": str(fm.get("updated")) if fm.get("updated") is not None else None,
        "age_days": age,
        "stale": stale,
        "problems": problems,
    }


def _roots() -> tuple[Path, ...]:
    """Both status roots, clients first (comd_resume resolution order). Read
    live from the module globals so tests that repoint them are honored."""
    return (CLIENTS_DIR, PROJECTS_DIR)


def slug_dir(slug: str) -> Path | None:
    """Resolve a client OR internal-project slug. None if neither root has it."""
    for root in _roots():
        d = root / slug
        if d.is_dir():
            return d
    return None


def status_dir(client: str) -> Path:
    d = slug_dir(client)
    return (d / "status") if d else (CLIENTS_DIR / client / "status")


def _status_files_in(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*.md") if p.name.lower() != "readme.md")


def list_status_files(client: str) -> list[Path]:
    d = status_dir(client)
    if not d.is_dir():
        return []
    return _status_files_in(d)


def check(client: str, today: _dt.date, max_age_days: int) -> tuple[list[dict], int]:
    """Evaluate every status file. Returns (rows, exit_code). Non-zero if any
    file is stale or malformed."""
    d = status_dir(client)
    if not d.is_dir():
        return ([], 3)  # no status/ folder at all
    rows = [evaluate_file(p, today, max_age_days) for p in list_status_files(client)]
    bad = any(r["stale"] or r["problems"] for r in rows)
    return (rows, 1 if bad else 0)


TEMPLATE = """\
---
project: {client}
workstream: {workstream}
group: {group}
spec: {spec}
state: {state}
updated: {updated}{general_ref_line}
---

# {client} / {workstream}

One-line purpose of this workstream (replace this).

## Elements

| Element | State | Status | Next action | Blocker | Detail |
|---|---|---|---|---|---|
| (element) | not-started | (one line) | (next action) | (blocker or —) | (link) |

States: not-started · in-progress · blocked · done · live · paused

## Open decisions / gates

- (gate or decision this workstream waits on; link to the source doc)

## Pointers

- Spec: (link)
- Deliverables: (link)
- Context: (link)
"""


def scaffold(
    client: str,
    workstream: str,
    *,
    group: str = "",
    spec: str = "",
    state: str = "active",
    today: _dt.date,
    general_ref: str = "",
) -> Path:
    base = slug_dir(client)
    if base is None:
        raise SystemExit(
            f"no client or project folder named {client!r} under "
            f"{CLIENTS_DIR} or {PROJECTS_DIR}")
    d = base / "status"
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{workstream}.md"
    if dest.exists():
        raise SystemExit(f"refusing to overwrite existing file: {dest}")
    general_ref_line = f"\ngeneral_ref: {general_ref}" if general_ref else ""
    dest.write_text(
        TEMPLATE.format(
            client=client,
            workstream=workstream,
            group=group,
            spec=spec,
            state=state,
            updated=today.isoformat(),
            general_ref_line=general_ref_line,
        ),
        encoding="utf-8",
    )
    return dest


def _print_check(client: str, rows: list[dict], code: int, max_age_days: int) -> None:
    if code == 3:
        print(f"no status/ folder for client '{client}' ({status_dir(client)})")
        return
    if not rows:
        print(f"status/ exists for '{client}' but holds no status files")
        return
    print(f"project status - {client}  (stale threshold: {max_age_days}d)\n")
    for r in rows:
        flags = []
        if r["stale"]:
            flags.append(f"STALE ({r['age_days']}d)")
        if r["problems"]:
            flags.extend(r["problems"])
        tag = "  <-- " + "; ".join(flags) if flags else ""
        age = f"{r['age_days']}d" if r["age_days"] is not None else "?"
        print(f"  [{(r['state'] or '?'):<11}] {r['file']:<32} updated {r['updated'] or '?'} ({age}){tag}")
    print()
    print("OK" if code == 0 else "ISSUES FOUND (stale or malformed status files above)")


def sweep_stale(today: _dt.date, max_age_days: int = DEFAULT_MAX_AGE_DAYS) -> list[dict]:
    """Across every client AND internal project with a status/ folder, return
    the files that are stale or malformed (each row carries its slug under the
    'client' key). Empty list = everything fresh.

    This is what makes currency NOT depend on someone remembering to run --check:
    it is wired into SessionStart (see tools/wire-hooks.py) so rot surfaces on its
    own every session.
    """
    findings: list[dict] = []
    seen: set[str] = set()
    dirs: list[Path] = []
    for root in _roots():
        if not root.is_dir():
            continue
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            # Clients shadow projects on a slug collision (comd_resume order).
            if d.name in seen:
                continue
            seen.add(d.name)
            dirs.append(d)
    for client_dir in dirs:
        if not (client_dir / "status").is_dir():
            continue
        for p in _status_files_in(client_dir / "status"):
            row = evaluate_file(p, today, max_age_days)
            if not (row["stale"] or row["problems"]):
                continue
            # This sweep derives staleness from the WORKING TREE, so a checkout
            # behind origin/main nags about files somebody already refreshed.
            # Same defect class as the optimize overview's STALE CHECKOUT
            # blind spot; here it produces false positives rather than silent
            # under-reporting, which trains the reader to ignore the advisory.
            # Suppression is scoped to STALENESS only. A malformed file is
            # malformed in this checkout whatever origin/main holds, so it is
            # still reported even when the remote copy is newer.
            if row["stale"] and not row["problems"] \
                    and _fresher_on_origin(p, row["updated"]):
                continue
            findings.append({"client": client_dir.name, **row})
    return findings


def _fresher_on_origin(path: Path, local_updated: str | None) -> bool:
    """True when origin/main's copy carries a NEWER `updated:` than this one.

    Fail-open: any git problem, missing ref, or unparseable date means "cannot
    tell", and the finding is reported as normal. Never suppress on a guess.
    """
    if not local_updated:
        return False
    try:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"origin/main:{rel}"],
            capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    remote_updated = parse_frontmatter(proc.stdout).get("updated")
    if remote_updated is None:
        return False
    try:
        return _dt.date.fromisoformat(str(remote_updated)) > \
            _dt.date.fromisoformat(str(local_updated))
    except ValueError:
        return False


# Once-per-day stamp so the SessionStart sweep advises at most once per calendar
# day instead of on every session (mirrors friction-watch.py --once-per-day).
_SWEEP_STAMP = Path(tempfile.gettempdir()) / "agentic-ops-project-status-sweep.json"


def _already_swept_today(today: _dt.date) -> bool:
    """True if the once-per-day sweep already ran today. Fail-open: any error =>
    False (run the sweep) rather than silently skipping it."""
    try:
        return json.loads(_SWEEP_STAMP.read_text(encoding="utf-8")).get("last_sweep") == today.isoformat()
    except (OSError, ValueError):
        return False


def _mark_swept_today(today: _dt.date) -> None:
    try:
        _SWEEP_STAMP.write_text(json.dumps({"last_sweep": today.isoformat()}), encoding="utf-8")
    except OSError:
        pass


def _freshness_caveat() -> None:
    """One stderr line when this checkout is behind origin/main. The sweep
    derives staleness from the WORKING TREE, so status updates that landed
    upstream are invisible here and a file can read stale when it is not
    (stale-checkout blind spot, register 2026-07-21/22). Fail-open."""
    try:
        import importlib.util
        p = Path(__file__).resolve().parent / "repo_freshness.py"
        spec = importlib.util.spec_from_file_location("repo_freshness", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.warn_if_stale("project_status --sweep-stale", repo=REPO_ROOT)
    except Exception:
        pass


def _print_sweep(findings: list[dict]) -> None:
    n = len(findings)
    print(f"[project-status] {n} status file(s) stale or malformed. "
          "Update in place, or delete if the workstream is done (rule_no_file_bloat W1).")
    for f in findings:
        bits = []
        if f["stale"]:
            bits.append(f"stale {f['age_days']}d")
        if f["problems"]:
            bits.extend(f["problems"])
        print(f"  {f['client']}/{f['file']}: {'; '.join(bits)}")
    print("  (run: uv run tools/project_status.py --client <X> --check)")
    _freshness_caveat()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Per-project status-file tooling.")
    ap.add_argument("--client", help="client or project slug (workspace/clients/ "
                                     "first, then workspace/projects/)")
    ap.add_argument("--check", action="store_true", help="report status files, flag stale/malformed")
    ap.add_argument("--scaffold", metavar="WORKSTREAM", help="write a template status file")
    ap.add_argument("--group", default="", help="parent group for the scaffolded file")
    ap.add_argument("--spec", default="", help="related spec id(s) for the scaffolded file")
    ap.add_argument("--general-ref", default="", help="path to the group general-reference file")
    ap.add_argument("--state", default="active", help="initial state for the scaffolded file")
    ap.add_argument("--days", type=int, default=DEFAULT_MAX_AGE_DAYS, help="staleness threshold in days")
    ap.add_argument("--json", action="store_true", help="machine-readable output for --check")
    ap.add_argument("--sweep-stale", action="store_true",
                    help="scan ALL clients; advise on stale/malformed status files (exit 0 always)")
    ap.add_argument("--once-per-day", action="store_true",
                    help="with --sweep-stale: run at most once per calendar day (SessionStart use)")
    args = ap.parse_args(argv)

    today = _dt.date.today()

    if args.sweep_stale:
        # SessionStart-wired: never block a session. Fail-open, always exit 0.
        try:
            if args.once_per_day and _already_swept_today(today):
                return 0
            findings = sweep_stale(today, args.days)
            if args.once_per_day:
                _mark_swept_today(today)
            if findings:
                _print_sweep(findings)
        except Exception:
            pass
        return 0

    if args.scaffold:
        if not args.client:
            ap.error("--scaffold requires --client")
        dest = scaffold(
            args.client,
            args.scaffold,
            group=args.group,
            spec=args.spec,
            state=args.state,
            today=today,
            general_ref=args.general_ref,
        )
        print(f"wrote {dest}")
        return 0

    if args.check:
        if not args.client:
            ap.error("--check requires --client")
        rows, code = check(args.client, today, args.days)
        if args.json:
            print(json.dumps({"client": args.client, "rows": rows, "exit": code}, indent=2))
        else:
            _print_check(args.client, rows, code, args.days)
        return code

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
