"""recon-feedback-coverage: which operator notes the backlog never filed.

Trigger: friction register 2026-09-16, 09-17 and 09-20. Notes were read
newest-first and the tail went unactioned for days; in each case the owner was
the detector. Note #34 sat five days while the matching backlog item was parked
in writing "until Criss reports one".

The negative cases are the contract: a bare `#881` is a PR number and must
never count as a note reference, and a malformed line must not shift the
numbering, because both would make the coverage report wrong in the direction
that reads as "all filed".
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "recon-feedback-coverage.py"
spec = importlib.util.spec_from_file_location("recon_feedback_coverage", TOOL)
cov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cov)


def write_notes(path: Path, n: int, extra_lines: list[str] | None = None) -> Path:
    lines = [
        json.dumps({"ts": f"2026-09-0{i % 9 + 1}T10:00:00", "operator": "criss",
                    "section": f"sec{i}", "comment": f"note body {i}"})
        for i in range(1, n + 1)
    ]
    lines.extend(extra_lines or [])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(tmp_path: Path, notes: int, backlog_text: str, *extra: str) -> int:
    fb = write_notes(tmp_path / "feedback.jsonl", notes)
    bl = tmp_path / "backlog.md"
    bl.write_text(backlog_text, encoding="utf-8")
    return cov.main(["--feedback", str(fb), "--backlog", str(bl), *extra])


# ---------------------------------------------------------------- references

@pytest.mark.parametrize(
    "text,expected",
    [
        ("addressed note #3 today", {3}),
        ("notes #4-#6 shipped", {4, 5, 6}),
        ("notes #7, #8 are done", {7, 8}),
        ("notes #9 and #10", {9, 10}),
        ("owner notes #54-#60 recorded", set(range(54, 61))),
        # Forms taken verbatim from the live backlog on 2026-09-21. The slash
        # and the second-# -less range both appear there; missing either
        # reports a filed note as unfiled, which is how an advisory earns a
        # reputation for crying wolf.
        ("notes #37/#41 cover it", {37, 41}),
        ("notes #41-45 shipped", {41, 42, 43, 44, 45}),
        ("notes #47, #50 open", {47, 50}),
        ("", set()),
    ],
)
def test_reference_forms(text, expected):
    assert cov.referenced(text) == expected


def test_a_bare_pr_number_is_not_a_note_reference():
    # The backlog is full of `#881`-style PR numbers. Counting one as a note
    # would silently mark that note filed.
    assert cov.referenced("shipped in #881 and #555") == set()
    assert cov.referenced("PR #881 closed item 42") == set()


def test_note_word_is_required_not_just_proximity():
    assert cov.referenced("item #42") == set()


# ------------------------------------------------------------------ numbering

def test_blank_and_malformed_lines_do_not_shift_numbering(tmp_path):
    fb = tmp_path / "f.jsonl"
    fb.write_text(
        json.dumps({"comment": "first"}) + "\n"
        "\n"
        "{not json at all\n"
        + json.dumps({"comment": "second"}) + "\n"
        "[1, 2, 3]\n"          # valid JSON, not an object: the app skips it
        + json.dumps({"comment": "third"}) + "\n",
        encoding="utf-8",
    )
    rows = cov.read_notes(fb)
    assert [r["comment"] for r in rows] == ["first", "second", "third"]


# -------------------------------------------------------------------- outcome

def test_unfiled_notes_exit_1_and_are_listed(tmp_path, capsys):
    rc = run(tmp_path, 5, "we did note #2 and notes #4-#5")
    out = capsys.readouterr().out
    assert rc == 1
    assert "5 notes" in out and "3 filed, 2 not" in out
    assert "#1" in out and "#3" in out
    assert "note body 1" in out


def test_everything_filed_exits_0(tmp_path, capsys):
    assert run(tmp_path, 3, "notes #1-#3 all handled") == 0
    assert "0 not" in capsys.readouterr().out


def test_since_floor_ignores_old_notes(tmp_path, capsys):
    assert run(tmp_path, 5, "notes #4, #5 done", "--since", "3") == 0


def test_stale_feedback_copy_is_refused(tmp_path, capsys):
    # The dangerous direction: a short file plus high citations would otherwise
    # report "all filed".
    rc = run(tmp_path, 5, "shipped note #99 last week")
    assert rc == 2
    assert "INPUTS DISAGREE" in capsys.readouterr().err


def test_missing_input_is_refused(tmp_path, capsys):
    bl = tmp_path / "b.md"
    bl.write_text("x", encoding="utf-8")
    assert cov.main(["--feedback", str(tmp_path / "nope.jsonl"), "--backlog", str(bl)]) == 2
