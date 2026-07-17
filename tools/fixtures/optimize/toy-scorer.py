# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# direction: minimize
"""Toy scorer for optimize-loop tests: SCORE = sum of integers in the asset.

Deterministic, instant, stdlib-only. One int per line; blank lines ignored.
Copied into throwaway test repos as tools/scorers/toy-scorer.py and pinned
there; NOT pinned in the real repo (it lives under tools/fixtures/).
"""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: toy-scorer.py <numbers-file>", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            total = sum(int(line) for line in f if line.strip())
    except (OSError, ValueError) as e:
        print(f"measurement failed: {e}", file=sys.stderr)
        return 2
    print(f"summed {sys.argv[1]}")
    print(f"SCORE: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
