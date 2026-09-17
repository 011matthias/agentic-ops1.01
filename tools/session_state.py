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

# FALLBACK pressure thresholds, mirrored from rule_session-pressure.md. Used
# only when the transcript's context size cannot be read. A band is crossed
# when EITHER the tool-call count OR the distinct-file count reaches the
# threshold (whichever trips first -- a read-heavy session trips on files, a
# build-heavy one on calls).
BANDS = (
    ("critical", 250, 80),
    ("high", 150, 50),
    ("moderate", 80, 30),
)
_BAND_RANK = {None: 0, "moderate": 1, "high": 2, "critical": 3}

# PRIMARY pressure signal (2026-09-17, ECC port item 2): the real context size,
# read from the latest assistant `usage` record in the session transcript.
# Tool calls are a weak proxy (a few large reads fill the window in few calls),
# and the counters above live in ONE file shared by every session on the
# machine, so a sibling session resets them mid-session. The transcript is
# per-session by construction. Fractions of the window, calibrated on 120
# transcripts: median session peak 402k; 23 compactions (all manual) at
# 468k-920k, 2 of them below 500k, 18 at or below 700k.
CONTEXT_BANDS = (
    ("critical", 0.70),
    ("high", 0.50),
    ("moderate", 0.30),
)
_USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
# Transcripts reach 100+ MB, and the meter runs on every tool call, so only the
# tail is read: start small, grow 4x until a usage record turns up, give up
# (-> tool-call fallback) past the cap.
_TAIL_START = 256 * 1024
_TAIL_MAX = 8 * 1024 * 1024
# Per-session emitted-band memory survives the reset a sibling session causes;
# bounded so the shared file cannot grow without limit.
_BANDS_BY_SESSION_MAX = 20

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
        # B1 deferral priming: how many times stop-b1-gate blocked this
        # session, and how many of those have already been surfaced as a
        # pre-generation primer on a later turn. b1_blocks > b1_primed means
        # a block is waiting to prime the NEXT turn. See rule_behaviors.md B1.
        "b1_blocks": 0,
        "b1_primed": 0,
        # Latest measured context size (transcript usage), or None when the
        # transcript was unreadable. See read_context_usage().
        "context_tokens": None,
        "context_model": "",
        "context_measured_at": None,
        # {session_id: highest band advised}. Carried across the reset in
        # ensure_session so interleaved sibling sessions do not re-advise.
        "bands_by_session": {},
        # Transient tool failures (lock / 429 / 5xx / MCP transport) that
        # tool-failure-gate turned into an in-turn retry advisory.
        "transient_blocks": 0,
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
            fresh = _default_state(session_id)
            fresh["bands_by_session"] = _bounded_bands(state.get("bands_by_session"))
            return fresh
        if session_id and not state.get("session_id"):
            state["session_id"] = session_id
        return state
    return _modify(_fn)


def bump_tool(tool_name: str, file_path: str | None = None,
              context: dict | None = None) -> dict:
    """Increment the tool-call count; track a distinct file when relevant.
    `context` (a read_context_usage() result) records the measured context
    size in the same locked write; None leaves the last reading in place."""
    def _fn(state: dict) -> dict:
        state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
        if tool_name in _FILE_TOOLS and file_path:
            files = state.setdefault("distinct_files", [])
            if file_path not in files:
                files.append(file_path)
        if context:
            state["context_tokens"] = int(context.get("tokens", 0))
            state["context_model"] = context.get("model", "") or ""
            state["context_measured_at"] = _now_iso()
        return state
    return _modify(_fn)


def context_window() -> int:
    """Context window in tokens (AGENTIC_OPS_CONTEXT_WINDOW, default 1M).
    A malformed override falls back to the default rather than raising at
    import, which would silently unload the meter."""
    try:
        n = int(os.environ.get("AGENTIC_OPS_CONTEXT_WINDOW") or 1_000_000)
        return n if n > 0 else 1_000_000
    except ValueError:
        return 1_000_000


def _usage_line(raw: bytes) -> dict | None:
    """Parse one transcript line. Returns {"tokens", "model", "message_id"} for
    a main-thread assistant usage record, {"compact": True} for a compaction
    boundary, else None."""
    if b'"usage"' not in raw and b'"compact_boundary"' not in raw:
        return None  # cheap prefilter; most lines are neither
    try:
        entry = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(entry, dict):
        return None
    if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
        return {"compact": True}
    if entry.get("type") != "assistant" or entry.get("isSidechain"):
        return None
    msg = entry.get("message")
    usage = msg.get("usage") if isinstance(msg, dict) else None
    if not isinstance(usage, dict):
        return None
    try:
        tokens = sum(int(usage.get(k) or 0) for k in _USAGE_KEYS)
    except (TypeError, ValueError):
        return None
    if tokens <= 0:
        return None  # synthetic / error turns carry an all-zero usage
    return {"tokens": tokens, "model": msg.get("model", "") or "",
            "message_id": msg.get("id", "") or ""}


def read_context_usage(transcript_path: str) -> dict | None:
    """Current context size from the session transcript, or None if unknown.

    context = input_tokens + cache_read_input_tokens +
    cache_creation_input_tokens of the LATEST main-thread assistant record.
    Only the latest record matters, so no per-message.id dedupe is needed (that
    applies to summing session totals, which this does not do). A compaction
    boundary newer than any usage record means the last reading is pre-compact
    and stale: return None so the caller falls back instead of over-reporting.
    Claude Code writes the transcript asynchronously, so the reading can lag
    the in-flight turn by one response. Never raises."""
    if not transcript_path:
        return None
    try:
        size = os.path.getsize(transcript_path)
    except OSError:
        return None
    window = _TAIL_START
    try:
        with open(transcript_path, "rb") as f:
            while True:
                start = max(0, size - window)
                f.seek(start)
                lines = f.read(size - start).split(b"\n")
                if start > 0:
                    lines = lines[1:]  # first line is cut mid-record
                for raw in reversed(lines):
                    hit = _usage_line(raw)
                    if hit is None:
                        continue
                    return None if hit.get("compact") else hit
                if start == 0 or window >= _TAIL_MAX:
                    return None
                window *= 4
    except OSError:
        return None


def context_band(tokens: int | None, window: int | None = None) -> str | None:
    """Highest context band crossed by `tokens`, or None."""
    if not tokens:
        return None
    w = window or context_window()
    for name, frac in CONTEXT_BANDS:  # critical-first
        if tokens >= frac * w:
            return name
    return None


def format_tokens(n: int) -> str:
    """312456 -> '312k', 1000000 -> '1M'."""
    if n >= 1_000_000 and n % 1_000_000 == 0:
        return f"{n // 1_000_000}M"
    return f"{round(n / 1000)}k"


def _bounded_bands(bands) -> dict:
    if not isinstance(bands, dict):
        return {}
    items = list(bands.items())[-_BANDS_BY_SESSION_MAX:]
    return dict(items)


def bump_b1_block() -> dict:
    """Record that stop-b1-gate blocked a stop this session.

    The Stop hook is a POST-hoc catch: it fires after the deferring response
    already exists, costing a full turn redo, and 608 blocks against 2554
    clean stops (2026-07-22 hook-log census, ~19% of turns, flat across July)
    show it contains the behavior without changing the disposition. 92% of
    those blocks land in bursts (2+ within an hour of each other), so the
    leverage is priming the NEXT turn rather than catching it again."""
    def _fn(state: dict) -> dict:
        state["b1_blocks"] = int(state.get("b1_blocks", 0)) + 1
        return state
    return _modify(_fn)


def bump_transient_block() -> dict:
    """Record a transient tool failure (tool-failure-gate). The 2026-05-11
    EBUSY incident queued 8 edits for the user instead of retrying; the count
    makes a session that keeps hitting transient blocks visible at checkpoint."""
    def _fn(state: dict) -> dict:
        state["transient_blocks"] = int(state.get("transient_blocks", 0)) + 1
        return state
    return _modify(_fn)


def b1_priming_due(state: dict | None = None) -> int:
    """Blocks recorded but not yet surfaced as a primer (0 = nothing due)."""
    st = state if state is not None else load()
    return max(0, int(st.get("b1_blocks", 0)) - int(st.get("b1_primed", 0)))


def mark_b1_primed() -> dict:
    """Mark every recorded block as primed, so one block primes exactly one
    later turn instead of nagging on every subsequent prompt."""
    def _fn(state: dict) -> dict:
        state["b1_primed"] = int(state.get("b1_blocks", 0))
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


def emitted_band(state: dict, session_id: str = "") -> str | None:
    """Highest band already advised for `session_id` (falls back to the
    unkeyed field for callers without a session id)."""
    if session_id:
        bands = state.get("bands_by_session")
        if isinstance(bands, dict) and session_id in bands:
            return bands[session_id]
    return state.get("pressure_band_emitted")


def mark_band_emitted(band: str | None, session_id: str = "") -> dict:
    """Record the highest band already advised on (dedup per band). With a
    session id the record is keyed, so it survives a sibling-session reset.
    Lowering it (band below the previous one) is how a compaction re-arms the
    advisories."""
    def _fn(state: dict) -> dict:
        state["pressure_band_emitted"] = band
        if session_id:
            bands = state.get("bands_by_session")
            bands = dict(bands) if isinstance(bands, dict) else {}
            bands.pop(session_id, None)  # re-insert last -> most recent survives pruning
            bands[session_id] = band
            state["bands_by_session"] = _bounded_bands(bands)
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
    ctx = st.get("context_tokens")
    window = context_window()
    if ctx:
        band, signal = context_band(ctx, window), "context"
    else:
        band, signal = pressure_band(st), "tool-calls"
    sid = st.get("session_id", "") or ""
    if as_json:
        print(json.dumps({
            "session_id": sid,
            "tool_calls": st.get("tool_calls", 0),
            "distinct_files": len(st.get("distinct_files", []) or []),
            "pressure_band": band,
            "pressure_signal": signal,
            "pressure_band_emitted": emitted_band(st, sid),
            "context_tokens": ctx,
            "context_window": window,
            "context_model": st.get("context_model", ""),
            "context_measured_at": st.get("context_measured_at"),
            "candidates": len(st.get("candidates", []) or []),
            "b1_blocks": st.get("b1_blocks", 0),
            "b1_priming_due": b1_priming_due(st),
            "transient_blocks": st.get("transient_blocks", 0),
        }))
    else:
        ctx_txt = (f"{format_tokens(ctx)}/{format_tokens(window)}" if ctx
                   else "unread")
        # The state file is shared by every session on this machine: the
        # session prefix shows whose reading this is.
        print(f"[session-state] session={sid[:8] or '-'} "
              f"band={band or 'none'} ({signal}) context={ctx_txt} "
              f"calls={st.get('tool_calls', 0)} "
              f"files={len(st.get('distinct_files', []) or [])} "
              f"candidates={len(st.get('candidates', []) or [])} "
              f"b1_blocks={st.get('b1_blocks', 0)} "
              f"transient_blocks={st.get('transient_blocks', 0)}")
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
