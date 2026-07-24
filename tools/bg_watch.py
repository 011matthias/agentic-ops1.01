# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Background-work liveness watches: detect "the phase I am waiting on is dead".

WHY THIS EXISTS
---------------
2026-07-22 (friction register, `sys` / verification-theater): a 10-lens
adversarial-verify fan-out was launched as a background Workflow and died about
5 minutes in. 8/10 lens batches returned 38 candidate findings; only 3 of the 38
verifications ever ran. The death went undetected for ~76 MINUTES, and the audit
was then presented as adversarially verified when 35 candidates never were. The
register's own words: "no structural detector exists for 'the background phase
you depend on is dead'; the Monitor tool would have caught it but nothing
prompts its use".

WHAT IS ACTUALLY DETECTABLE FROM HERE
-------------------------------------
Nothing in this repo can see the Claude Code harness's internal task registry,
so a background phase cannot be discovered. What CAN be done is cheap and
sufficient: the agent declares ONE line of intent ("I am waiting on X, expect
progress every N minutes"), and from then on the detection is automatic. The
PostToolUse meter (`session-pressure-meter.py`) already fires on every single
tool call, so the 76 minutes of continued work that followed the death are
exactly where the advisory lands. Registration is the only recall-dependent
step, and it is one call.

THE LIVENESS RULE (one rule, both shapes)
-----------------------------------------
    last_signal = mtime(heartbeat) if that file exists else registered_at
    OVERDUE when  now - last_signal >= eta_seconds

That single comparison covers both shapes without a second knob:
  - no heartbeat registered  -> a plain deadline, eta minutes after registration
  - heartbeat advancing      -> the deadline rolls forward, stays silent
  - heartbeat gone stale     -> fires eta minutes after the LAST real progress
and the "silent for N minutes" number in the advisory is honest either way.

DESIGN
------
- One JSON file in the OS temp dir (transient working state, never committed,
  per rule_no_file_bloat). Path: {tempdir}/agentic-ops-bg-watches.json,
  overridable via AGENTIC_OPS_BG_WATCHES so tests never touch a live session.
- Watches are keyed on the git working-tree ROOT (same keying as
  session_registry, reusing its resolver), so a watch registered in one worktree
  does not nag a session working in another. A watch with no resolvable root
  fires everywhere: fail-open, since a missed advisory is the failure this
  exists to prevent.
- Re-registering the same id REPLACES the record, so a refresh is idempotent and
  cannot accumulate duplicate nags.
- Once overdue, the advisory repeats at most every RENOTIFY_SECONDS. One line
  that scrolls past is how 76 minutes happen; a slow repeat is the point.
- No lock. Writes are atomic (temp + os.replace) but not serialized: a watch is
  registered by hand and re-notified at most once per 10 minutes, so the
  read-modify-write window is effectively never contended, and the worst case is
  one duplicated advisory. A lock on a per-tool-call read path would cost more
  than it protects.

DEFENSIVE CONTRACT
------------------
Every public function swallows its own errors and degrades to a no-op / empty
result. This module is imported by a PostToolUse hook and must NEVER break the
tool call it rides (mirrors tools/session_state.py and tools/session_registry.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time

# Overridable via env so tests run in isolation without clobbering a live
# session's watches.
WATCH_FILE = os.environ.get("AGENTIC_OPS_BG_WATCHES") or os.path.join(
    tempfile.gettempdir(), "agentic-ops-bg-watches.json"
)

# Default expectation when the caller does not say: 10 minutes of silence is
# already long enough that a dead fan-out is worth naming.
DEFAULT_ETA_MINUTES = 10
# Once overdue, repeat the advisory no more often than this.
RENOTIFY_SECONDS = 600
# Hard ceiling: a watch nobody ever cleared stops nagging after a day.
MAX_AGE_SECONDS = 86400

_SLUG = re.compile(r"[^a-z0-9]+")

# Working-tree resolution is shared with the sibling-session registry rather
# than re-implemented; absence of that module is not fatal (root becomes "",
# which means "fire everywhere").
try:
    import session_registry as _sr
except Exception:  # pragma: no cover - only when tools/ is off sys.path
    _sr = None


def _now() -> float:
    return time.time()


def _f(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _slugify(label: str) -> str:
    s = _SLUG.sub("-", (label or "").lower()).strip("-")
    return s[:32].rstrip("-") or "watch"


def _root(cwd: str | None) -> str:
    if _sr is None:
        return ""
    try:
        return _sr.find_worktree_root(cwd or os.getcwd()) or ""
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Store IO
# --------------------------------------------------------------------------
def _load() -> list[dict]:
    """Read the watch list, returning [] on any failure (missing file, truncated
    write, hand-edited garbage). Fail-open is deliberate: a corrupt store must
    never break the tool call the meter rides."""
    try:
        with open(WATCH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    watches = data.get("watches")
    if not isinstance(watches, list):
        return []
    return [w for w in watches if isinstance(w, dict) and w.get("id")]


def _save(watches: list[dict]) -> None:
    """Atomic write (temp + os.replace, atomic on Win and POSIX). Any failure
    leaves the previous file intact and removes the partial temp file."""
    tmp = WATCH_FILE + f".{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"watches": watches}, f, ensure_ascii=False)
        os.replace(tmp, WATCH_FILE)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _prune(watches: list[dict], now: float) -> list[dict]:
    return [w for w in watches if now - _f(w.get("registered")) <= MAX_AGE_SECONDS]


# --------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------
def _last_signal(watch: dict) -> tuple[float, str]:
    """(timestamp of the most recent proof of life, plain-language source).

    The heartbeat file's mtime when that file exists; otherwise the registration
    time, which is the honest answer for both "no heartbeat declared" and
    "declared one that never appeared"."""
    hb = watch.get("heartbeat") or ""
    if hb:
        try:
            return os.path.getmtime(hb), "heartbeat"
        except OSError:
            return _f(watch.get("registered")), "missing"
    return _f(watch.get("registered")), "none"


def status(watch: dict, now: float | None = None) -> dict:
    """Enrich a watch with its liveness verdict. Never raises."""
    now = _now() if now is None else now
    ts, source = _last_signal(watch)
    silent = max(0.0, now - ts)
    eta = _f(watch.get("eta_seconds"), DEFAULT_ETA_MINUTES * 60)
    out = dict(watch)
    out["silent_seconds"] = int(silent)
    out["signal_source"] = source
    out["overdue"] = silent >= eta
    return out


def _visible(watch: dict, root: str) -> bool:
    """A watch is visible to this session when it has no recorded root, when we
    cannot resolve our own, or when the two match. Fail-open on both unknowns."""
    wroot = watch.get("root") or ""
    return not wroot or not root or wroot == root


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def register(label: str, eta_minutes: float = DEFAULT_ETA_MINUTES,
             heartbeat: str | None = None, watch_id: str | None = None,
             cwd: str | None = None) -> dict | None:
    """Declare that this session is waiting on background work. Returns the
    record written, or None on failure. Re-registering an existing id replaces
    it (a refresh, not a duplicate)."""
    try:
        now = _now()
        wid = _slugify(watch_id or label)
        rec = {
            "id": wid,
            "label": (label or wid)[:200],
            "eta_seconds": max(1, int(_f(eta_minutes, DEFAULT_ETA_MINUTES) * 60)),
            "heartbeat": os.path.abspath(heartbeat) if heartbeat else "",
            "registered": now,
            "root": _root(cwd),
            "notified_at": 0.0,
        }
        watches = [w for w in _prune(_load(), now) if w.get("id") != wid]
        watches.append(rec)
        _save(watches)
        return rec
    except Exception:
        return None


def clear(watch_id: str | None = None, all_watches: bool = False) -> int:
    """Drop one watch (by id) or every watch. Returns how many were removed."""
    try:
        watches = _load()
        if all_watches:
            _save([])
            return len(watches)
        wid = _slugify(watch_id or "")
        keep = [w for w in watches if w.get("id") != wid]
        removed = len(watches) - len(keep)
        if removed:
            _save(keep)
        return removed
    except Exception:
        return 0


def listing(cwd: str | None = None, now: float | None = None,
            all_roots: bool = False) -> list[dict]:
    """Every visible watch with its liveness verdict, most-silent first."""
    try:
        now = _now() if now is None else now
        root = "" if all_roots else _root(cwd)
        out = [status(w, now) for w in _prune(_load(), now)
               if all_roots or _visible(w, root)]
        out.sort(key=lambda w: w.get("silent_seconds", 0), reverse=True)
        return out
    except Exception:
        return []


def overdue(cwd: str | None = None, now: float | None = None) -> list[dict]:
    """Visible watches whose work has gone silent past its expected interval."""
    return [w for w in listing(cwd=cwd, now=now) if w.get("overdue")]


def _dur(seconds: float) -> str:
    """Human duration. Minutes once there are any, seconds below that, so a
    short interval never renders as the meaningless '0 min'."""
    s = int(max(0, seconds))
    return f"{s} s" if s < 60 else f"{s // 60} min"


def _signal_clause(w: dict) -> str:
    src = w.get("signal_source")
    hb = w.get("heartbeat") or ""
    if src == "heartbeat":
        return f"its heartbeat file {hb} has not advanced since"
    if src == "missing":
        return f"the declared heartbeat file {hb} never appeared"
    return "no heartbeat file was registered, so registration is the last signal"


def advisory(items: list[dict]) -> str:
    """Format the loud advisory for a set of overdue watches."""
    lines = [
        "[BG-WATCH] Background work you registered has gone silent:",
    ]
    for w in items:
        lines.append(
            f'  - "{w.get("label")}" (id: {w.get("id")}) silent for '
            f'{_dur(w.get("silent_seconds", 0))}; expected progress at least '
            f'every {_dur(_f(w.get("eta_seconds")))}; {_signal_clause(w)}.'
        )
    lines.append(
        "Verify it is still alive BEFORE using any of its output: Monitor the "
        "task, stat the output path, or re-run the phase. Partial output from a "
        "dead phase read as a finished result is the B2 failure in "
        "rule_behaviors (2026-07-22: a verify fan-out died at 5 min, went "
        "unnoticed for 76, and 35 of 38 findings shipped unverified)."
    )
    lines.append(
        "Clear it once it has genuinely finished: "
        "uv run tools/bg_watch.py done <id>"
    )
    return "\n".join(lines)


def due_advisories(cwd: str | None = None, now: float | None = None) -> list[str]:
    """The hook entry point: zero or one advisory string, with the re-notify
    back-off applied and stamped. Never raises; [] on any failure."""
    try:
        now = _now() if now is None else now
        items = [w for w in overdue(cwd=cwd, now=now)
                 if now - _f(w.get("notified_at")) >= RENOTIFY_SECONDS]
        if not items:
            return []
        fired = {w["id"] for w in items}
        watches = _prune(_load(), now)
        for w in watches:
            if w.get("id") in fired:
                w["notified_at"] = now
        _save(watches)
        return [advisory(items)]
    except Exception:
        return []


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _print_list(items: list[dict], as_json: bool, empty_msg: str) -> int:
    if as_json:
        print(json.dumps(items, ensure_ascii=False))
        return 0
    if not items:
        print(f"[bg-watch] {empty_msg}")
        return 0
    for w in items:
        flag = "OVERDUE" if w.get("overdue") else "ok"
        print(f"  [{flag}] {w.get('id')}: \"{w.get('label')}\" "
              f"silent {_dur(w.get('silent_seconds', 0))} / "
              f"eta {_dur(_f(w.get('eta_seconds')))}")
    return 0


def main(argv: list[str]) -> int:
    # `--cwd` / `--json` live on every SUBparser, not on the top-level one.
    # argparse only accepts a top-level option BEFORE the subcommand, so
    # `bg_watch.py watch --label X --cwd Y` would be rejected outright, and
    # declaring them in both places lets the subparser's default clobber the
    # value the top level already parsed. One shared parent avoids both.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cwd", default=None,
                        help="resolve the working-tree root from here")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    ap = argparse.ArgumentParser(
        description="Background-work liveness watches (register, check, clear).")
    sub = ap.add_subparsers(dest="cmd")

    w = sub.add_parser("watch", parents=[common],
                       help="register background work you are waiting on")
    w.add_argument("--label", required=True, help="human description of the work")
    w.add_argument("--eta", type=float, default=DEFAULT_ETA_MINUTES,
                   help="minutes of silence that mean it is probably dead")
    w.add_argument("--heartbeat", default=None,
                   help="file the work touches as it progresses (optional)")
    w.add_argument("--id", default=None, help="explicit id (default: slug of label)")

    for name, helptext in (("list", "show every watch with its verdict"),
                           ("check", "show only the overdue ones")):
        p = sub.add_parser(name, parents=[common], help=helptext)
        p.add_argument("--all-roots", action="store_true",
                       help="include watches from other working trees")

    d = sub.add_parser("done", parents=[common], help="clear a finished watch")
    d.add_argument("id", nargs="?", default=None)
    d.add_argument("--all", action="store_true", help="clear every watch")

    args = ap.parse_args(argv)
    args.cwd = getattr(args, "cwd", None)
    args.json = getattr(args, "json", False)

    if args.cmd == "watch":
        rec = register(args.label, eta_minutes=args.eta, heartbeat=args.heartbeat,
                       watch_id=args.id, cwd=args.cwd)
        if args.json:
            print(json.dumps(rec, ensure_ascii=False))
        else:
            print(f"[bg-watch] watching \"{(rec or {}).get('label')}\" "
                  f"(id: {(rec or {}).get('id')}, "
                  f"eta {_dur(_f((rec or {}).get('eta_seconds')))}). "
                  f"Clear with: uv run tools/bg_watch.py done {(rec or {}).get('id')}")
        return 0

    if args.cmd == "done":
        n = clear(args.id, all_watches=args.all)
        print(json.dumps({"cleared": n}) if args.json
              else f"[bg-watch] cleared {n} watch(es).")
        return 0

    if args.cmd == "check":
        items = [w for w in listing(cwd=args.cwd, all_roots=args.all_roots)
                 if w.get("overdue")]
        if items and not args.json:
            print(advisory(items))
            return 0
        return _print_list(items, args.json, "no overdue watches.")

    # default + `list`
    all_roots = bool(getattr(args, "all_roots", False))
    return _print_list(listing(cwd=args.cwd, all_roots=all_roots), args.json,
                       "no background watches registered.")


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
