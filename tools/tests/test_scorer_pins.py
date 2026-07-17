"""Scorer pin registry (tools/scorers/PINS.json) - CI enforcement.

The registry is the merge-time half of the metric lock: the run engine
refuses a scorer whose live hash diverges from its pin, and THIS suite
refuses the merge that would legitimize a drifted pin. A scorer rewritten
through any write-time bypass (shell redirect, interpreter escape) cannot
both keep its pin AND pass here.

Hash = sha1 git-blob over CRLF->LF-normalized bytes (pin_scorer.blob_sha),
so Windows-CRLF checkouts and Ubuntu-LF CI agree.
"""
import importlib.util

from hooklib import REPO, TOOLS


def _pin_scorer_mod():
    spec = importlib.util.spec_from_file_location(
        "pin_scorer", TOOLS / "pin_scorer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PS = _pin_scorer_mod()
SCORERS = REPO / "tools" / "scorers"


def test_every_scorer_is_pinned():
    pins = PS.load_pins()
    unpinned = [n for n in PS.scorer_files() if n not in pins]
    assert not unpinned, (
        f"unpinned scorer(s) {unpinned}: run "
        "`SCORER_LOCK_ALLOW=1 uv run tools/pin_scorer.py pin <name>` "
        "with user approval and ship the PINS.json diff in this PR"
    )


def test_every_pin_matches_live_sha():
    pins = PS.load_pins()
    drift = {
        n: (e.get("sha"), PS.blob_sha(str(SCORERS / n)))
        for n, e in pins.items()
        if (SCORERS / n).is_file() and e.get("sha") != PS.blob_sha(str(SCORERS / n))
    }
    assert not drift, f"scorer content drifted from pin: {drift}"


def test_every_pin_direction_matches_header():
    pins = PS.load_pins()
    bad = {
        n: (PS.scorer_direction(str(SCORERS / n)), e.get("direction"))
        for n, e in pins.items()
        if (SCORERS / n).is_file()
        and PS.scorer_direction(str(SCORERS / n)) != e.get("direction")
    }
    assert not bad, f"direction header vs pin mismatch: {bad}"


def test_no_orphan_pins():
    pins = PS.load_pins()
    orphans = [n for n in pins if not (SCORERS / n).is_file()]
    assert not orphans, f"pins without scorer files: {orphans}"


def test_check_command_is_green():
    """The tool's own `check` verdict agrees with this suite (humans run it)."""
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, str(TOOLS / "pin_scorer.py"), "check"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
