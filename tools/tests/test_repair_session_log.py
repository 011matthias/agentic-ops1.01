"""repair-session-log: rebuild a day file that concurrent checkpoints mangled.

Each `checkpoint_scaffold finalize` writes the whole frontmatter and numbers its
entry from its own view of the file, so N sessions on one day merge into a file
with duplicated header keys, stray key blocks between entries, and several
entries all called "Session 1". Merging a repaired branch forward then keeps both
sides of an identical entry.

The negative cases are the contract: an already-clean file is left byte-identical,
and a genuine collision (same title, different bodies) is refused rather than
resolved by a tool.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "repair_session_log", TOOLS / "repair-session-log.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rsl = _load()


def entry(title: str, work: str = "client-dev", projects: str = "", friction: str = "0") -> str:
    return (
        f"### Session 1 — {title}\n"
        f"**Type:** {work}\n"
        f"**Focus:** focus for {title}\n"
        + (f"**Projects:** {projects}\n" if projects else "")
        + f"**Built:** built for {title}\n"
        f"**Friction:** {friction} - something\n"
        f"**Gates:** B1:0 B2:0 B3:0 skipped:0\n"
        f"**Autonomy:** 0 human interventions\n"
        f"**Outcome:** outcome for {title}\n"
    )


CLEAN_HEADER = (
    "---\n"
    "date: 2026-09-09\n"
    "sessions: 1\n"
    "projects_touched: [alpha]\n"
    "friction_events: 2\n"
    "work_types: [client-dev]\n"
    "---\n\n"
)


def test_renumbers_sequentially_and_emits_one_header():
    mangled = (
        "---\n"
        "date: 2026-09-09\n"
        "sessions: 1\n"
        "projects_touched: [alpha]\n"
        "friction_events: 2\n"
        "work_types: [client-dev]\n"
        "sessions: 1\n"
        "projects_touched: [beta]\n"
        "friction_events: 3\n"
        "work_types: [misc]\n"
        "---\n\n"
        + entry("Alpha Work", "client-dev", "alpha", "2")
        + "projects_touched: []\n"
        "friction_events: 3\n"
        "work_types: [misc]\n"
        "---\n\n"
        + entry("Beta Work", "misc", "beta", "3")
    )
    out = rsl.repair(mangled, "2026-09-09")

    assert out.count("\n---\n") == 1, "exactly one frontmatter block"
    assert "### Session 1 — Alpha Work" in out
    assert "### Session 2 — Beta Work" in out
    assert "sessions: 2" in out
    assert "friction_events: 5" in out, "friction sums across sessions"
    assert "projects_touched: [alpha, beta]" in out
    assert "work_types: [client-dev, misc]" in out
    # the stranded key block is gone from the body
    body = out.split("---\n", 2)[2]
    assert "projects_touched:" not in body


def test_already_clean_file_is_unchanged():
    clean = CLEAN_HEADER + entry("Alpha Work", "client-dev", "alpha", "2")
    once = rsl.repair(clean, "2026-09-09")
    assert rsl.repair(once, "2026-09-09") == once, "repair is idempotent"


def test_identical_duplicate_entry_collapses():
    dup = entry("Alpha Work", "client-dev", "alpha", "2")
    mangled = CLEAN_HEADER + dup + "\n" + dup
    out = rsl.repair(mangled, "2026-09-09")
    headings = [ln for ln in out.split("\n") if ln.startswith("### Session")]
    assert headings == ["### Session 1 — Alpha Work"]
    assert "sessions: 1" in out
    assert "friction_events: 2" in out, "a collapsed duplicate is not double-counted"


def test_same_title_different_body_is_refused():
    a = entry("Alpha Work", "client-dev", "alpha", "2")
    b = entry("Alpha Work", "client-dev", "alpha", "9")
    with pytest.raises(rsl.RepairRefused, match="different bodies"):
        rsl.repair(CLEAN_HEADER + a + "\n" + b, "2026-09-09")


def test_last_moves_one_entry_to_the_end():
    mangled = (
        CLEAN_HEADER
        + entry("Alpha Work", "client-dev", "alpha", "1")
        + entry("Mine Here", "misc", "beta", "1")
        + entry("Gamma Work", "misc", "gamma", "1")
    )
    out = rsl.repair(mangled, "2026-09-09", last="Mine")
    assert "### Session 3 — Mine Here" in out
    assert "### Session 1 — Alpha Work" in out
    assert "### Session 2 — Gamma Work" in out


def test_last_matching_nothing_is_refused():
    text = CLEAN_HEADER + entry("Alpha Work", "client-dev", "alpha", "1")
    with pytest.raises(rsl.RepairRefused, match="matched 0 entries"):
        rsl.repair(text, "2026-09-09", last="Nope")


def test_no_entries_is_refused_not_silently_emptied():
    with pytest.raises(rsl.RepairRefused, match="no '### Session"):
        rsl.repair(CLEAN_HEADER, "2026-09-09")


def test_bodies_are_preserved_verbatim():
    body_line = "**Built:** a very specific thing; with punctuation, and 42 numbers"
    text = (
        CLEAN_HEADER
        + "### Session 1 — Alpha Work\n"
        + "**Type:** client-dev\n"
        + body_line
        + "\n**Friction:** 1 - x\n"
    )
    out = rsl.repair(text, "2026-09-09")
    assert body_line in out


# --- damage(): the checker half. A healthy file must stay silent. -----------


def test_damage_silent_on_a_sound_file():
    sound = CLEAN_HEADER + entry("Alpha Work", "client-dev", "alpha", "2")
    assert rsl.damage(sound) == []


def test_damage_ignores_whitespace_and_header_value_drift():
    """The 2026-09-07 false positive: structurally fine, blank lines differ.

    A checker that fires here trains the reader to ignore it.
    """
    sound = CLEAN_HEADER + entry("Alpha Work", "client-dev", "alpha", "2")
    spaced = sound.replace("\n### Session", "\n\n### Session")
    assert rsl.damage(spaced) == []
    drifted = sound.replace("friction_events: 2", "friction_events: 99")
    assert rsl.damage(drifted) == []


def test_damage_catches_duplicate_header_keys():
    broken = CLEAN_HEADER.replace(
        "work_types: [client-dev]\n", "work_types: [client-dev]\nsessions: 2\n"
    ) + entry("Alpha Work")
    faults = rsl.damage(broken)
    assert any("duplicate frontmatter key" in f for f in faults)


def test_damage_catches_stranded_key_block_in_body():
    broken = (
        CLEAN_HEADER
        + entry("Alpha Work")
        + "projects_touched: []\nfriction_events: 3\n---\n\n"
        + entry("Beta Work")
    )
    faults = rsl.damage(broken)
    assert any("stranded in the body" in f for f in faults)


def test_damage_catches_non_sequential_numbering():
    broken = CLEAN_HEADER + entry("Alpha Work") + entry("Beta Work")
    assert any("not sequential" in f for f in rsl.damage(broken))


def test_damage_catches_repeated_titles():
    dup = entry("Alpha Work")
    broken = CLEAN_HEADER + dup + dup.replace("Session 1", "Session 2")
    assert any("repeated entry title" in f for f in rsl.damage(broken))
