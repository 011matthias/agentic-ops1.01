# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Behavior smoke test for the session-instrumentation layer.

Verifies (not just "compiles") the spec's acceptance criteria:

  1. session_state counters + pressure_band thresholds.
  2. Candidate add / dedup / list / clear.
  3. session_id boundary: a new id resets, an unchanged id preserves.
  4. The meter hook emits a band advisory ONCE per band (subprocess, real
     stdin payload), and stays silent on a same-band call.
  5. no-auto-commit-gate, when it fires "ask", ALSO records a candidate AND
     its decision output is unchanged (the capture is a pure side-effect).

Isolation: every step runs against a throwaway state file via the
AGENTIC_OPS_SESSION_STATE env var, so a live session's counters are untouched.

Run:  uv run tools/fixtures/session-state/smoke_test.py
Exit: 0 if all pass, 1 on first failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TOOLS = REPO / "tools"
HOOKS = REPO / ".claude" / "hooks"
METER = HOOKS / "session-pressure-meter.py"
NAC_GATE = HOOKS / "no-auto-commit-gate.py"

# Isolated state file for this test run.
_TMP_STATE = os.path.join(tempfile.gettempdir(), "agentic-ops-session-state.SMOKETEST.json")
os.environ["AGENTIC_OPS_SESSION_STATE"] = _TMP_STATE

# Import the module under test AFTER setting the env var.
sys.path.insert(0, str(TOOLS))
import session_state  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  PASS  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def run_hook(path: Path, payload: dict) -> tuple[str, str]:
    """Invoke a hook script with a JSON payload on stdin; return (stdout, stderr)."""
    env = dict(os.environ)
    proc = subprocess.run(
        [sys.executable, str(path)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30, env=env, cwd=str(REPO),
    )
    return proc.stdout.strip(), proc.stderr.strip()


def main() -> int:
    print("[smoke] session-instrumentation behavior test")
    print(f"[smoke] isolated state: {_TMP_STATE}")

    # ---- 1. counters + bands -------------------------------------------
    print("\n1. counters + pressure bands")
    session_state.reset()
    st = session_state.load()
    check("reset -> zero", st["tool_calls"] == 0 and st["candidates"] == [])
    session_state.ensure_session("S1")
    for _ in range(30):
        session_state.bump_tool("Bash")
    st = session_state.load()
    check("30 calls -> no band (calls<80, files=0)", session_state.pressure_band(st) is None,
          f"band={session_state.pressure_band(st)}")
    # 30 distinct files alone trips moderate.
    for i in range(30):
        session_state.bump_tool("Read", f"/tmp/f{i}.py")
    st = session_state.load()
    check("30 distinct files -> moderate", session_state.pressure_band(st) == "moderate",
          f"band={session_state.pressure_band(st)} files={len(st['distinct_files'])}")
    check("distinct files deduped", len(st["distinct_files"]) == 30,
          f"files={len(st['distinct_files'])}")
    # re-reading the same files must not inflate the count
    session_state.bump_tool("Read", "/tmp/f0.py")
    st = session_state.load()
    check("re-read same file not double-counted", len(st["distinct_files"]) == 30,
          f"files={len(st['distinct_files'])}")

    # ---- 2. band escalation logic --------------------------------------
    print("\n2. band escalation (once per band)")
    check("None->moderate is new", session_state.band_is_new("moderate", None))
    check("moderate->moderate not new", not session_state.band_is_new("moderate", "moderate"))
    check("moderate->high is new", session_state.band_is_new("high", "moderate"))
    check("high->moderate not new (no downgrade)", not session_state.band_is_new("moderate", "high"))
    check("high->critical is new", session_state.band_is_new("critical", "high"))

    # ---- 3. candidates --------------------------------------------------
    print("\n3. candidate add / dedup / clear")
    session_state.reset()
    a1 = session_state.add_candidate("gate-skip-pre-publish", "test", "git push")
    a2 = session_state.add_candidate("gate-skip-pre-publish", "test", "git push")  # dup
    a3 = session_state.add_candidate("gate-skip-iteration-3x", "test", "other")
    check("first add returns True", a1 is True)
    check("duplicate add returns False", a2 is False)
    check("distinct signal add returns True", a3 is True)
    st = session_state.load()
    check("2 candidates stored (dedup worked)", len(st["candidates"]) == 2,
          f"n={len(st['candidates'])}")
    n = session_state.clear_candidates()
    check("clear returns count", n == 2, f"n={n}")
    check("candidates empty after clear", session_state.load()["candidates"] == [])

    # ---- 4. session boundary -------------------------------------------
    print("\n4. session_id boundary")
    session_state.reset()
    session_state.ensure_session("A")
    session_state.bump_tool("Bash")
    session_state.add_candidate("x", "test", "ctx")
    session_state.ensure_session("A")  # same id -> preserve
    st = session_state.load()
    check("same session_id preserves counts", st["tool_calls"] == 1 and len(st["candidates"]) == 1)
    session_state.ensure_session("B")  # new id -> reset
    st = session_state.load()
    check("new session_id resets", st["tool_calls"] == 0 and st["candidates"] == [] and st["session_id"] == "B")

    # ---- 5. meter hook (subprocess, real behavior) ---------------------
    print("\n5. meter hook emits once per band")
    # Pre-seed to one call below the moderate threshold (79 calls), no band emitted.
    session_state.reset()
    session_state.ensure_session("MTR")
    for _ in range(79):
        session_state.bump_tool("Bash")
    out, err = run_hook(METER, {"session_id": "MTR", "tool_name": "Bash", "tool_input": {}})
    crossed = "PRESSURE: MODERATE" in out
    check("80th call emits MODERATE advisory", crossed, f"stdout={out[:160]!r} stderr={err[:120]!r}")
    # Same band again -> silent.
    out2, _ = run_hook(METER, {"session_id": "MTR", "tool_name": "Bash", "tool_input": {}})
    check("81st call stays silent (no re-emit)", out2 == "", f"stdout={out2[:160]!r}")
    st = session_state.load()
    check("meter incremented past threshold", st["tool_calls"] >= 81, f"calls={st['tool_calls']}")

    # ---- 6. gate capture + decision integrity --------------------------
    print("\n6. no-auto-commit-gate captures candidate AND keeps decision")
    session_state.reset()
    session_state.ensure_session("GATE")
    empty_tx = os.path.join(tempfile.gettempdir(), "smoketest-empty-transcript.jsonl")
    Path(empty_tx).write_text("", encoding="utf-8")
    # `git tag` is ship-class and never hits the prototype carve-out (which
    # only special-cases commit/push/PR), so the ask branch fires regardless
    # of repo git state.
    out, err = run_hook(NAC_GATE, {
        "tool_input": {"command": "git tag smoke-test-v0"},
        "transcript_path": empty_tx,
    })
    decided_ask = '"permissionDecision": "ask"' in out
    check("gate still returns ask (decision unchanged)", decided_ask, f"stdout={out[:160]!r}")
    cands = session_state.load()["candidates"]
    captured = any(c["signal"] == "gate-fired-no-auto-commit" for c in cands)
    check("gate recorded a friction candidate", captured, f"candidates={cands}")

    # ---- 7. lock under contention --------------------------------------
    # The lock is best-effort BY CONTRACT (docstring: a rare lost increment is
    # cheaper than a stalled/broken tool call -> timeout 1s, then proceed
    # unlocked). So we assert two different bars:
    #   7a. The REAL concurrency model is exactly 2 writers (session-pressure-
    #       meter.py + gate-skip-detector.py firing on the same Bash call).
    #       That MUST be zero-loss.
    #   7b. Pathological N-way sustained contention (never happens in the real
    #       hook model) need only meet the best-effort bar: no corruption, and
    #       loss stays small. Raising the timeout to force zero-loss here would
    #       trade a lost COUNT for a multi-second STALL on a tool call, which
    #       is strictly worse for instrumentation -- so we do NOT.
    import threading

    def run_contention(n_threads, per_thread):
        session_state.reset()
        session_state.ensure_session("CONC")
        barrier = threading.Barrier(n_threads)

        def worker():
            barrier.wait()  # start together to maximize contention
            for _ in range(per_thread):
                session_state.bump_tool("Bash")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return session_state.load()["tool_calls"]

    print("\n7a. REAL model (2 concurrent writers) -> zero loss")
    got = run_contention(2, 100)
    check("2x100 concurrent increments == 200 (real hook model, must be exact)",
          got == 200, f"got {got}")

    print("\n7b. pathological 8-way contention -> best-effort (small loss, no corruption)")
    got = run_contention(8, 25)
    st_after = session_state.load()  # must still be valid/parseable
    check("8x25 stays within best-effort bar (>=95% retained, no corruption)",
          isinstance(st_after, dict) and 190 <= got <= 200, f"got {got}")

    # ---- cleanup --------------------------------------------------------
    for p in (_TMP_STATE, _TMP_STATE + ".lock", empty_tx):
        try:
            os.unlink(p)
        except OSError:
            pass

    print(f"\n[smoke] {_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
