# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Per-session heartbeat registry: detect LIVE sibling sessions sharing one git
working tree, so the SessionStart guard can advise worktree isolation.

WHY THIS EXISTS
---------------
Multiple Claude sessions running against ONE clone share HEAD, the index, and
the stash. Concurrent commits + edits collide: session-log frontmatter bumped
under another session mid-edit, drafts landing in the wrong mailbox, cherry-pick
recoveries. The failure was named SIX times across 2026-07-09..07-11 session
logs ("sibling-guard still unbuilt (6th occurrence)"). The FIX has a memory --
`feedback_worktree_for_concurrent_sessions` (each git worktree has its OWN
index/HEAD, so no collision) -- but nothing DETECTED the collision at session
start, so the memory kept losing to whichever session got there first. This
registry is the sensor; `.claude/hooks/sibling-session-gate.py` is the advisory.

DESIGN
------
- One heartbeat file per session: {dir}/{session_id}.json, holding
  {session_id, root, branch, pid, ts}. Dir: {tempdir}/agentic-ops-sessions/
  (transient working state; never committed, per rule_no_file_bloat).
- "Sibling" == another session whose heartbeat is FRESH (ts within the TTL)
  AND whose `root` equals ours. Keying on the working-tree ROOT (not the shared
  .git dir) is deliberate: two worktrees of one repo have DIFFERENT roots and
  isolated indexes, so they are NOT collision siblings and must NOT warn. Two
  sessions in the SAME working tree share one index -> warn. This is exactly
  why "use a worktree" is the fix the advisory points at.
- Freshness (TTL, default 20 min) is what makes a crashed session's stale
  heartbeat stop counting; the PostToolUse pressure meter refreshes ours every
  tool call, so a genuinely active session never ages out.

DEFENSIVE CONTRACT
------------------
Every public function swallows its own errors and degrades to a no-op / empty
result. A hook importing this module must NEVER break the tool call or the
session start it rides (mirrors tools/session_state.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Heartbeat dir is overridable via env so smoke tests run in isolation without
# clobbering a live machine's registry.
HEARTBEAT_DIR = os.environ.get("AGENTIC_OPS_SESSION_DIR") or os.path.join(
    tempfile.gettempdir(), "agentic-ops-sessions"
)

_SAFE = re.compile(r"[^A-Za-z0-9._-]")
# Working-tree root is stable for a given cwd within a process; cache the walk.
_ROOT_CACHE: dict[str, str | None] = {}


def _ttl() -> int:
    """Seconds a heartbeat stays 'live'. Env-overridable for tests."""
    try:
        return int(os.environ.get("AGENTIC_OPS_SESSION_TTL", "1200"))
    except (TypeError, ValueError):
        return 1200


def _now() -> float:
    return time.time()


# --------------------------------------------------------------------------
# Working-tree resolution (pure-Python; no subprocess -- this rides a per-tool
# hook, a `git` fork per call would be far too costly)
# --------------------------------------------------------------------------
def find_worktree_root(start: str | None) -> str | None:
    """Walk up from `start` to the dir that CONTAINS a `.git` entry (file OR
    dir). A worktree's `.git` is a FILE (a gitdir pointer); a primary clone's is
    a DIR. Either way, the containing dir is that working tree's root. Returns
    an absolute path str, or None if not inside a git tree."""
    try:
        if not start:
            return None
        cur = str(Path(start).resolve())
    except Exception:
        return None
    if cur in _ROOT_CACHE:
        return _ROOT_CACHE[cur]
    p = Path(cur)
    root: str | None = None
    for _ in range(60):  # bounded parent walk
        try:
            if (p / ".git").exists():
                root = str(p)
                break
        except OSError:
            pass
        if p.parent == p:
            break
        p = p.parent
    _ROOT_CACHE[cur] = root
    return root


def read_branch(root: str) -> str:
    """Resolve the current branch of the working tree at `root` WITHOUT a
    subprocess: read HEAD, following the worktree gitdir pointer when `.git` is
    a file. Returns a branch name, 'detached@<sha7>', or '' on any failure."""
    try:
        gitpath = Path(root) / ".git"
        if gitpath.is_dir():
            head = gitpath / "HEAD"
        elif gitpath.is_file():
            txt = gitpath.read_text(encoding="utf-8", errors="ignore").strip()
            if "gitdir:" not in txt:
                return ""
            head = Path(txt.split("gitdir:", 1)[1].strip()) / "HEAD"
        else:
            return ""
        content = head.read_text(encoding="utf-8", errors="ignore").strip()
        if content.startswith("ref:"):
            ref = content[4:].strip()
            return ref.split("refs/heads/", 1)[-1] if "refs/heads/" in ref else ref
        return f"detached@{content[:7]}" if content else ""
    except OSError:
        return ""


# --------------------------------------------------------------------------
# Heartbeat IO
# --------------------------------------------------------------------------
def _hb_path(session_id: str) -> str:
    name = _SAFE.sub("_", session_id or "unknown")[:120] + ".json"
    return os.path.join(HEARTBEAT_DIR, name)


def heartbeat(session_id: str, cwd: str | None = None,
              root: str | None = None) -> dict | None:
    """Best-effort write/refresh of THIS session's heartbeat. Atomic (temp +
    os.replace). Returns the record written, or None if we are not in a git
    tree / on any failure. Never raises."""
    tmp = None
    try:
        if not session_id:
            return None
        if root is None:
            root = find_worktree_root(cwd or os.getcwd())
        if not root:
            return None  # not in a git tree -> nothing to collide over
        os.makedirs(HEARTBEAT_DIR, exist_ok=True)
        rec = {
            "session_id": session_id,
            "root": root,
            "branch": read_branch(root),
            "pid": os.getpid(),
            "ts": _now(),
        }
        path = _hb_path(session_id)
        tmp = path + f".{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, path)
        tmp = None
        _prune_opportunistic()
        return rec
    except Exception:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return None


def _read_all() -> list[dict]:
    out: list[dict] = []
    try:
        names = os.listdir(HEARTBEAT_DIR)
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(HEARTBEAT_DIR, name), "r", encoding="utf-8") as f:
                rec = json.load(f)
            if isinstance(rec, dict) and rec.get("session_id"):
                out.append(rec)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return out


def live_siblings(session_id: str, cwd: str | None = None,
                  root: str | None = None, ttl: int | None = None) -> list[dict]:
    """Other sessions sharing THIS working tree with a FRESH heartbeat. Keyed on
    the working-tree root, so sessions isolated in separate worktrees (distinct
    roots, isolated indexes) are deliberately NOT returned. Each result carries
    an added `age_seconds`. Sorted most-recent-first. Never raises; [] on any
    failure."""
    try:
        if ttl is None:
            ttl = _ttl()
        if root is None:
            root = find_worktree_root(cwd or os.getcwd())
        if not root:
            return []
        now = _now()
        sibs: list[dict] = []
        for rec in _read_all():
            if rec.get("session_id") == session_id:
                continue
            if rec.get("root") != root:
                continue
            ts = rec.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            age = now - ts
            if age < 0 or age > ttl:
                continue
            enriched = dict(rec)
            enriched["age_seconds"] = int(age)
            sibs.append(enriched)
        sibs.sort(key=lambda r: r.get("ts", 0), reverse=True)
        return sibs
    except Exception:
        return []


def _prune_opportunistic(ttl: int | None = None) -> None:
    """Delete heartbeat files older than 2x the TTL (orphans from crashed
    sessions), keyed on mtime so it costs one stat per file, no read. A live
    session's os.replace refreshes its mtime every tool call, so it is never a
    prune target. Best-effort; never raises."""
    try:
        if ttl is None:
            ttl = _ttl()
        cutoff = _now() - (ttl * 2)
        for name in os.listdir(HEARTBEAT_DIR):
            if not name.endswith(".json"):
                continue
            fp = os.path.join(HEARTBEAT_DIR, name)
            try:
                if os.path.getmtime(fp) < cutoff:
                    os.unlink(fp)
            except OSError:
                pass
    except OSError:
        pass


# --------------------------------------------------------------------------
# CLI (inspection + tests; the hooks import the module directly)
# --------------------------------------------------------------------------
def _cmd_check(session_id: str, cwd: str | None, as_json: bool) -> int:
    sibs = live_siblings(session_id, cwd=cwd)
    if as_json:
        print(json.dumps(sibs, ensure_ascii=False))
        return 0
    if not sibs:
        print("[session-registry] no live sibling sessions on this working tree.")
        return 0
    print(f"[session-registry] {len(sibs)} live sibling session(s) sharing this tree:")
    for s in sibs:
        print(f"  - {(s.get('session_id') or '')[:8]} branch={s.get('branch') or '?'} "
              f"age={s.get('age_seconds')}s pid={s.get('pid')}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Per-session heartbeat registry.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--heartbeat", action="store_true", help="write/refresh this session's heartbeat")
    g.add_argument("--check", action="store_true", help="list live siblings on this working tree")
    g.add_argument("--list", action="store_true", help="dump all heartbeats")
    g.add_argument("--prune", action="store_true", help="delete stale heartbeats now")
    ap.add_argument("--session-id", default=os.environ.get("CLAUDE_SESSION_ID", ""))
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.heartbeat:
        rec = heartbeat(args.session_id, cwd=args.cwd)
        print(json.dumps(rec, ensure_ascii=False) if args.json else f"[session-registry] {rec}")
        return 0
    if args.list:
        print(json.dumps(_read_all(), ensure_ascii=False) if args.json else _read_all())
        return 0
    if args.prune:
        _prune_opportunistic()
        print("[session-registry] pruned.")
        return 0
    # default + --check
    return _cmd_check(args.session_id, args.cwd, args.json)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
