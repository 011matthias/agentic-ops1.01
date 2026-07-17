# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# direction: minimize
"""Toy scorer that never finishes in time: proves the per-score timeout
kills the process tree and journals the round as crash."""
import sys
import time

time.sleep(300)
print("SCORE: 1")
sys.exit(0)
