"""Scorer contract (tools/scorers/README.md) - executable enforcement.

The contract's clauses were prose only: nothing checked them before merge, so
the first machine execution of a new scorer was the post-merge `start`
baseline. A nonconformance discovered there costs a second SCORER_LOCK_ALLOW
seam touch plus a second PR, on top of an aborted lock-on.

test_scorer_pins.py already binds each scorer to a reviewed content hash.
This suite checks the clauses that hash cannot see:

  clause 3  the last stdout line is `SCORE: <number>`   (emission, static)
  clause 4  exit 0 ONLY on a successful measurement     (behavioral)
  clause 5  a `# direction: minimize|maximize` header   (static)

Clause 4 is checked by running each scorer against a deliberately
nonexistent asset: whatever a scorer measures, it cannot have measured THAT,
so a zero exit is a contract violation. This is universal in a way a
no-arguments probe is not (a future scorer may legitimately take no
arguments). It matters because the engine treats exit 0 as "this is a real
score" - a scorer that exits 0 on a broken input can hand the loop a number
that means nothing.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hooklib import REPO

SCORERS_DIR = REPO / "tools" / "scorers"
SCORER_FILES = sorted(p for p in SCORERS_DIR.glob("*.py") if p.is_file())

DIRECTION_RE = re.compile(r"^#\s*direction:\s*(minimize|maximize)\s*$",
                          re.MULTILINE)
SCORE_EMIT_RE = re.compile(r"SCORE:")
NONZERO_EXIT_RE = re.compile(
    r"(?:return\s+[1-9]\d*|sys\.exit\(\s*[1-9]\d*\s*\)|raise\s+SystemExit)")

# A path no scorer can possibly measure. Kept obviously bogus so a failure
# reads as "the scorer accepted garbage", not "the fixture was wrong".
BOGUS_ASSET = "__no_such_asset_for_contract_test__.nope"


def test_at_least_one_scorer_exists():
    """Guard the parametrization: an empty glob would make every test below
    vacuously pass and silently retire this suite."""
    assert SCORER_FILES, f"no scorers found under {SCORERS_DIR}"


@pytest.mark.parametrize("scorer", SCORER_FILES, ids=lambda p: p.name)
def test_declares_a_direction_header(scorer: Path):
    src = scorer.read_text(encoding="utf-8", errors="replace")
    assert DIRECTION_RE.search(src), (
        f"{scorer.name} has no `# direction: minimize|maximize` header "
        "(tools/scorers/README.md clause 5). The engine triple-matches this "
        "against PINS.json and the run manifest, so a scorer without it can "
        "never lock on.")


@pytest.mark.parametrize("scorer", SCORER_FILES, ids=lambda p: p.name)
def test_emits_a_score_line(scorer: Path):
    src = scorer.read_text(encoding="utf-8", errors="replace")
    assert SCORE_EMIT_RE.search(src), (
        f"{scorer.name} never emits `SCORE:` (clause 3). The engine parses "
        "the last `SCORE: <number>` line of stdout; without one every round "
        "is journaled as a crash.")


@pytest.mark.parametrize("scorer", SCORER_FILES, ids=lambda p: p.name)
def test_has_a_nonzero_exit_path(scorer: Path):
    src = scorer.read_text(encoding="utf-8", errors="replace")
    assert NONZERO_EXIT_RE.search(src), (
        f"{scorer.name} has no non-zero exit path (clause 4). A scorer that "
        "can only exit 0 cannot signal a failed measurement, and the engine "
        "would accept whatever it printed as a real score.")


@pytest.mark.parametrize("scorer", SCORER_FILES, ids=lambda p: p.name)
def test_refuses_an_unmeasurable_asset(scorer: Path):
    """Clause 4, behaviorally: exit 0 means 'this is a real measurement'."""
    proc = subprocess.run(
        [sys.executable, str(scorer), BOGUS_ASSET],
        capture_output=True, text=True, timeout=120, cwd=str(REPO))
    assert proc.returncode != 0, (
        f"{scorer.name} exited 0 for a nonexistent asset ({BOGUS_ASSET}). "
        "Exit 0 tells the engine the score is real, so this would feed the "
        "hill-climb a meaningless number.\n"
        f"stdout: {proc.stdout[-800:]}\nstderr: {proc.stderr[-800:]}")
