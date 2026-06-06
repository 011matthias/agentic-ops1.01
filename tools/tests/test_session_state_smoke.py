"""Run the existing hand-rolled session-instrumentation smoke test under pytest
so CI covers it too.

tools/fixtures/session-state/smoke_test.py already verifies the meter hook,
the no-auto-commit capture side effect, counters/bands, and lock contention.
It self-isolates its state file (AGENTIC_OPS_SESSION_STATE -> tempfile) and
exits non-zero on the first failure, so wrapping it is enough.
"""
import subprocess
import sys

from hooklib import REPO

SMOKE = REPO / "tools" / "fixtures" / "session-state" / "smoke_test.py"


def test_session_state_smoke_passes():
    p = subprocess.run(
        [sys.executable, str(SMOKE)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO),
    )
    assert p.returncode == 0, f"smoke test failed:\n{p.stdout}\n{p.stderr}"
