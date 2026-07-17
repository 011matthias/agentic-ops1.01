# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Toy guard for optimize-loop tests: PASS iff the asset has >= 3 non-empty
lines. Models evo's gate rule: an experiment that fails a guard is discarded
even when its score beats the current best."""
import sys

if len(sys.argv) < 2:
    sys.exit(2)
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]
except OSError:
    sys.exit(2)
sys.exit(0 if len(lines) >= 3 else 1)
