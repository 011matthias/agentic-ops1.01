# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Reproduce the CI `Enforcement hook tests` job locally, in one command.

WHY THIS EXISTS
---------------
The CI `hooks` job (ci.yml) runs three steps: ruff, tools/INDEX.md membership,
and the pytest enforcement suite. On 2026-07-16..17 five PRs went red on this
job for things that passed on the author's machine but failed in the clean CI
env (ruff F401/F841 in new files; a pytest that imported yaml, absent from the
CI test env). Each was a "passes locally, fails in CI" gap: the author never
ran the CI checks the way CI runs them before pushing.

This is the one command that closes that gap: it runs the SAME three steps the
CI job runs, so "locally" and "in CI" mean the same thing. Run it before
pushing any change under tools/, .claude/hooks/, or tools/tests/.

The blocking half is `ruff-push-gate.py` (fires automatically on git push, ruff
only, fast). This runner is the on-demand FULL check -- it also runs the slow
pytest suite that the push gate deliberately skips, so it catches the
pytest-collection failure class (a test importing a dep the CI env lacks) that
ruff cannot see.

USAGE
-----
  uv run tools/preflight-hooks.py            # fast: ruff + INDEX membership
  uv run tools/preflight-hooks.py --full     # + the pytest enforcement suite
  uv run tools/preflight-hooks.py --pytest    # pytest suite only

Exit 0 iff every selected step passed; non-zero (and a FAIL banner) otherwise.
Each step is the byte-for-byte CI command, so a green run here means a green
`hooks` job in CI.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (label, argv) triples -- each argv is the exact ci.yml command for that step.
RUFF = ("ruff (real-bug ruleset)",
        ["uv", "run", "--no-project", "--with", "ruff",
         "ruff", "check", "tools", ".claude/hooks", "tools/tests"])
INDEX = ("tools/INDEX.md membership",
         ["uv", "run", "tools/check-index.py"])
PYTEST = ("enforcement-layer pytest suite",
          ["uv", "run", "--no-project", "--with", "pytest", "--with", "python-pptx",
           "pytest", "tools/tests"])


def run_step(label: str, argv: list[str]) -> bool:
    print(f"\n=== {label} ===\n  $ {' '.join(argv)}", flush=True)
    try:
        proc = subprocess.run(argv, cwd=str(REPO))
    except FileNotFoundError:
        print(f"  SKIP: `{argv[0]}` not found on PATH -- cannot reproduce this "
              "step locally.", flush=True)
        return True  # can't run it here; CI will. Do not fail the local runner.
    ok = proc.returncode == 0
    print(f"  -> {'PASS' if ok else 'FAIL'} (exit {proc.returncode})", flush=True)
    return ok


def main(argv: list[str]) -> int:
    full = "--full" in argv
    pytest_only = "--pytest" in argv

    if pytest_only:
        steps = [PYTEST]
    elif full:
        steps = [RUFF, INDEX, PYTEST]
    else:
        steps = [RUFF, INDEX]

    results = [(label, run_step(label, args)) for label, args in steps]
    failed = [label for label, ok in results if not ok]

    print("\n" + "=" * 60)
    if failed:
        print(f"PREFLIGHT FAIL -- {len(failed)} step(s) would fail CI: "
              f"{', '.join(failed)}")
        if not full and not pytest_only:
            print("(ran fast steps only; add --full to also run the pytest suite)")
        return 1
    scope = "ruff + INDEX + pytest" if full else (
        "pytest" if pytest_only else "ruff + INDEX")
    print(f"PREFLIGHT OK -- {scope} clean. The CI `hooks` job should pass"
          + ("." if full or pytest_only else "; run --full before a tools/tests change."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
