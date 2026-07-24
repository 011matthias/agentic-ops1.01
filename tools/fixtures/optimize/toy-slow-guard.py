# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Toy guard that HANGS on a trigger value, for the guard-timeout tests.

Fast-passes normally, so a run can lock on with it declared, and sleeps far
past any sane guard budget when the asset contains the trigger line `-999`.
The trigger doubles as a score improvement under the toy scorer (sum of the
lines), which is what makes the guards run at all: the engine only guards a
round that already beat the best score.
"""
import sys
import time

if len(sys.argv) < 2:
    sys.exit(2)
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
except OSError:
    sys.exit(2)
if "-999" in lines:
    time.sleep(300)
sys.exit(0)
