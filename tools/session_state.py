# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Session-scoped instrumentation: friction candidates + pressure counters.

Single source of truth for transient per-session state, shared by the
instrumentation hooks (`session-pressure-meter.py`, `gate-skip-detector.py`,
`no-auto-commit-gate.py`, `instantly-invasive-gate.py`) and drained by
/comd_checkpoint.

WHY THIS EXISTS
---------------
Two systems depended on agent RECALL where they should depend on
INSTRUMENTATION (spec: docs/spec-instrumentation-friction-pressure.md):

  1. Friction noticing -- gate-skip-detector already DETECTS skips but the
     tags died in a freeform log and /comd_checkpoint never read them.
  2. Session pressure -- rule_session-pressure.md literally said "mental
     count, no runtime state file needed"; thresholds can't be eyeballed.

Both collapse to one pattern: a meter maintains this file; the harness emits
an advisory when a band/signal crosses; CLASSIFICATION stays a judgment step.
Detection is automated; promotion of a candidate to the friction register is
not (a gate firing CORRECTLY is the system working, not friction).

DESIGN
------
- One JSON file in the OS temp dir (transient working state; never committed,
  per rule_no_file_bloat). Path: {tempdir}/agentic-ops-session-state.json.
- Session boundary is detected by the hook payload's `session_id`. A changed
  id => new session => reset (counts start at zero). An unchanged id across a
  compaction => counts PRESERVED. This is why there is no SessionStart reset
  hook: the meter self-manages the boundary.
- Best-effort file lock guards read-modify-write so a concurrent meter +
  gate-skip-detector on the same Bash call don't lose a candidate or an
  increment. If the lock can't be taken, we proceed anyway -- a rare lost
  increment is cheaper than a broken tool call.

DEFENSIVE CONTRACT
------------------
Every public function swallows its own errors and degrades to a no-op / empty
result. A hook importing this module must NEVER break the tool call it rides.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time
from datetime import datetime, timezone

# State-file path is overridable via env so smoke tests run in isolation
# without clobbering a live session's counters.
STATE_FILE = os.environ.get("AGENTIC_OPS_SESSION_STATE") or os.path.join(
    tempfile.gettempdir(), "agentic-ops-session-state.json"
)
LOCK_FILE = STATE_FILE + ".lock"

# Pressure thresholds, mirrored from rule_session-pressure.md. A band is
# crossed when EITHER the tool-call count OR the distinct-file count reaches
# the threshold (whichever trips first -- a read-heavy session trips on files,
# a build-heavy one on calls).
BANDS = (
    ("critical", 250, 80),
    ("high", 150, 50),
    ("moderate", 80, 30),
)
_BAND_RANK = {None: 0, "moderate": 1, "high": 2, "critical": 3}

# Candidate context is truncated to keep the file small and dedup stable.
_CTX_MAX = 300
# Tools whose target file should count toward distinct-files-read pressure.
_FILE_TOOLS = {"Read", "Edit", "Write", "NotebookEdit"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state(session_id: str = "") -> dict:
    return {
        "session_id": session_id,
        "session_started": _now_iso(),
        "tool_calls": 0,
        "distinct_files": [],
        "pressure_band_emitted": None,
        "candidates": [],
    }


# --------------------------------------------------------------------------
# Locking + atomic IO
# --------------------------------------------------------------------------
def _acquire_lock(timeout: float = 1.0) -> str | None:
    """Best-effort exclusive lock via O_CREAT|O_EXCL, returning an owner token
    (or None if we gave up -- the caller then proceeds UNLOCKED rather than
    block the tool call). Portable (Win + POSIX), stdlib only.

    A stale lock (>5s old, i.e. orphaned by a process killed mid-write) is
    broken only after re-reading its token to confirm it has not changed,
    shrinking the window in which two waiters both break-and-acquire. The
    returned token lets _release_lock delete ONLY our own lock, so a slow
    process can never unlink a fresh lock another process just took."""
    token = f"{os.getpid()}.{time.monotonic_ns()}"
    start = time.monotonic()
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, token.encode("utf-8"))
            finally:
                os.close(fd)
            return token
        except FileExistsError:
            # Held by someone else. Break it only if provably a stale orphan.
            try:
                if time.time() - os.path.getmtime(LOCK_FILE) > 5:
                    with open(LOCK_FILE, "r", encoding="utf-8", errors="ignore") as lf:
                        t1 = lf.read()
                    time.sleep(0.005)
                    with open(LOCK_FILE, "r", encoding="utf-8", errors="ignore") as lf:
                        t2 = lf.read()
                    if t1 == t2:  # same orphan, still stale -> safe to break
                        os.unlink(LOCK_FILE)
                        continue  # retry immediately, skip back-off
            except OSError:
                pass
        except OSError:
            # Transient, NOT "lock held": e.g. on Windows the previous holder's
            # unlink is still in flight and os.open hits a sharing/permission
            # violation. Must RETRY until timeout -- giving up here would fall
            # through to an UNLOCKED write and clobber a concurrent holder
            # (this was the real cause of 2-way lost updates).
            pass
        # Shared back-off + timeout for both "held" and "transient" cases.
        if time.monotonic() - start > timeout:
            return None
        # Sub-millisecond jittered back-off: react as soon as the holder
        # (critical section ~ a few ms) releases, instead of napping a fixed
        # 10ms while the lock sits free. Jitter avoids a thundering herd of
        # waiters waking in lockstep.
        time.sleep(random.uniform(0.0005, 0.002))


def _release_lock(token: str | None) -> None:
    """Delete the lock only if it still carries OUR token (else a stale-break
    gave it to someone else; leave theirs alone)."""
    if not token:
        return
    try:
        with open(LOCK_FILE, "r", encoding="utf-8", errors="ignore") as lf:
            if lf.read() != token:
                return
        os.unlink(LOCK_FILE)
    except OSError:
        pass


def load() -> dict:
    """Read state, returning a default dict on any failure."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_state()
        # Heal any missing keys from a prior schema.
        base = _default_state(data.get("session_id", ""))
        base.update({k: data[k] for k in base if k in data})
        return base
    except (OSError, json.JSONDecodeError, ValueError):
        return _default_state()


def save(state: dict) -> None:
    """Atomic write: temp file + os.replace (atomic on Win and POSIX). On any
    write failure, remove the partial temp file so it can't accumulate (the
    pid-keyed name is reused by the next save, but a failed write must not
    leave residue behind)."""
    tmp = STATE_FILE + f".{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except OSError:
        try:
            os.unlink(tmp)  # replace never happened -> tmp is orphaned residue
        except OSError:
            pass


def _modify(fn):
    """Run fn(state) -> state under the lock, persisting the result.
    Returns the (possibly modified) state; never raises."""
    token = _acquire_lock()
    try:
        state = load()
        try:
            new = fn(state)
        except Exception:
            return state
        if isinstance(new, dict):
            save(new)
            return new
        return state
    finally:
        _release_lock(token)


# --------------------------------------------------------------------------
# Public API (used by hooks)
# --------------------------------------------------------------------------
def ensure_session(session_id: str) -> dict:
    """Reset counters if the session_id changed (new session). A blank id or
    an unchanged id is a no-op (compaction keeps the same id => preserve)."""
    def _fn(state: dict) -> dict:
        if session_id and state.get("session_id") != session_id:
            return _default_state(session_id)
        if session_id and not state.get("session_id"):
            state["session_id"] = session_id
        return state
    return _modify(_fn)


def bump_tool(tool_name: str, file_path: str | None = None) -> dict:
    """Increment the tool-call count; track a distinct file when relevant."""
    def _fn(state: dict) -> dict:
        state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
        if tool_name in _FILE_TOOLS and file_path:
            files = state.setdefault("distinct_files", [])
            if file_path not in files:
                files.append(file_path)
        return state
    return _modify(_fn)


def add_candidate(signal: str, source: str, context: str = "") -> bool:
    """Append a friction CANDIDATE (not a register row). Dedupes on
    (signal, context) within the session. Returns True if newly added."""
    ctx = (context or "")[:_CTX_MAX]
    added = {"flag": False}

    def _fn(state: dict) -> dict:
        cands = state.setdefault("candidates", [])
        for c in cands:
            if c.get("signal") == signal and c.get("context") == ctx:
                return state  # already captured this exact signal+context
        cands.append({
            "ts": _now_iso(),
            "signal": signal,
            "source_hook": source,
            "context": ctx,
        })
        added["flag"] = True
        return state

    _modify(_fn)
    return added["flag"]


def pressure_band(state: dict | None = None) -> str | None:
    """Highest band crossed given current counts, or None."""
    st = state if state is not None else load()
    calls = int(st.get("tool_calls", 0))
    files = len(st.get("distinct_files", []) or [])
    for name, call_thr, file_thr in BANDS:  # critical-first
        if calls >= call_thr or files >= file_thr:
            return name
    return None


def mark_band_emitted(band: str | None) -> dict:
    """Record the highest band already advised on (dedup per band)."""
    def _fn(state: dict) -> dict:
        state["pressure_band_emitted"] = band
        return state
    return _modify(_fn)


def band_is_new(band: str | None, emitted: str | None) -> bool:
    """True if `band` is a strict escalation over what was already emitted."""
    return _BAND_RANK.get(band, 0) > _BAND_RANK.get(emitted, 0)


def clear_candidates() -> int:
    """Drop all candidates (after checkpoint reconciliation). Returns count
    removed; preserves counters."""
    removed = {"n": 0}

    def _fn(state: dict) -> dict:
        removed["n"] = len(state.get("candidates", []) or [])
        state["candidates"] = []
        return state

    _modify(_fn)
    return removed["n"]


def reset() -> dict:
    """Full reset (new session)."""
    return _modify(lambda _s: _default_state())


# --------------------------------------------------------------------------
# CLI (used by /comd_checkpoint and ad-hoc inspection)
# --------------------------------------------------------------------------
def _cmd_status(as_json: bool) -> int:
    st = load()
    band = pressure_band(st)
    if as_json:
        print(json.dumps({
            "session_id": st.get("session_id", ""),
            "tool_calls": st.get("tool_calls", 0),
            "distinct_files": len(st.get("distinct_files", []) or []),
            "pressure_band": band,
            "pressure_band_emitted": st.get("pressure_band_emitted"),
            "candidates": len(st.get("candidates", []) or []),
        }))
    else:
        print(f"[session-state] band={band or 'none'} "
              f"calls={st.get('tool_calls', 0)} "
              f"files={len(st.get('distinct_files', []) or [])} "
              f"candidates={len(st.get('candidates', []) or [])}")
    return 0


def _cmd_list(as_json: bool) -> int:
    st = load()
    cands = st.get("candidates", []) or []
    if as_json:
        print(json.dumps(cands, ensure_ascii=False))
        return 0
    if not cands:
        print("[session-state] no friction candidates this session.")
        return 0
    print(f"[session-state] {len(cands)} friction candidate(s) -- "
          "classify each (promote to register OR discard as a gate working "
          "correctly), then run --clear-candidates:")
    for i, c in enumerate(cands, 1):
        print(f"  {i}. [{c.get('signal')}] via {c.get('source_hook')} "
              f"@ {c.get('ts')}")
        if c.get("context"):
            print(f"     ctx: {c['context']}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Session-state instrumentation store.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--status", action="store_true", help="print band + counts")
    g.add_argument("--list-candidates", action="store_true",
                   help="list friction candidates for checkpoint reconciliation")
    g.add_argument("--clear-candidates", action="store_true",
                   help="drop all candidates (after reconciliation)")
    g.add_argument("--reset", action="store_true", help="full reset (new session)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.list_candidates:
        return _cmd_list(args.json)
    if args.clear_candidates:
        n = clear_candidates()
        print(json.dumps({"cleared": n}) if args.json
              else f"[session-state] cleared {n} candidate(s).")
        return 0
    if args.reset:
        reset()
        print(json.dumps({"reset": True}) if args.json
              else "[session-state] reset.")
        return 0
    # default + --status
    return _cmd_status(args.json)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)
