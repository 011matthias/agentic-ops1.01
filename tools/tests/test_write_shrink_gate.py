"""Tests for .claude/hooks/write-shrink-gate.py.

Decision matrix: a Write that materially shrinks an EXISTING file ->
permissionDecision "ask", quantifying the delta and naming the structural
anchors that disappear. Creation, growth, small trims, and exempt paths stay
silent.

The NEGATIVE cases are the contract. This gate sits on every Write, so a
false-positive rate above roughly nothing makes it a tax that gets overridden
reflexively -- at which point it protects nothing.

Reproduces both incidents it was built for:
  2026-08-23  a 598-line test module clobbered by a same-named write
  2026-08-24  a 504-line loop brief whose live open queue vanished
"""
from __future__ import annotations

import json

from hooklib import load_hook, permission_decision, run_hook

HOOK = "write-shrink-gate.py"
ENV = {"AGENTIC_OPS_SESSION_STATE": ""}


def decide(path, content: str, tool: str = "Write") -> str | None:
    r = run_hook(
        HOOK,
        {"tool_name": tool, "tool_input": {"file_path": str(path), "content": content}},
        env=ENV,
    )
    assert r.returncode == 0, r.stderr
    return permission_decision(r.stdout)


def reason(path, content: str) -> str:
    r = run_hook(
        HOOK,
        {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": content}},
        env=ENV,
    )
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]


def lines(n: int, prefix: str = "line") -> str:
    return "\n".join(f"{prefix} {i}" for i in range(n)) + "\n"


# ---- The two incidents ---------------------------------------------------

def test_clobbered_test_module_asks(tmp_path):
    """2026-08-23: a Write replaced 598 lines / 17 tests with an unrelated
    module of the same name."""
    f = tmp_path / "test_expense_report_pdf.py"
    f.write_text(
        "\n".join(f"def test_parser_case_{i}():\n    assert True" for i in range(300)),
        encoding="utf-8",
    )
    new = "\n".join(f"def test_render_case_{i}():\n    assert True" for i in range(8))
    assert decide(f, new) == "ask"


def test_clobber_reason_names_the_lost_tests(tmp_path):
    f = tmp_path / "test_expense_report_pdf.py"
    f.write_text(
        "\n".join(f"def test_parser_case_{i}():\n    assert True" for i in range(300)),
        encoding="utf-8",
    )
    text = reason(f, "def test_render_case_0():\n    assert True\n")
    assert "def test_parser_case_0():" in text
    assert "600 -> 2 lines" in text or "600 -> 2" in text


def test_loop_brief_open_queue_asks(tmp_path):
    """2026-08-24: a brief rewrite silently dropped 504 lines including the
    owner's live open queue."""
    f = tmp_path / "loop-brief.md"
    body = ["# Loop brief", ""]
    for section in ("Open queue", "Unapplied Lovable prompts",
                    "Card-registry data entry", "January 0-of-80 finding"):
        body.append(f"## {section}")
        body.extend(f"- item {i}" for i in range(130))
    f.write_text("\n".join(body) + "\n", encoding="utf-8")
    new = "# Loop brief\n\n## Current focus\n" + lines(20, "- item")
    assert decide(f, new) == "ask"


def test_loop_brief_reason_lists_the_vanishing_sections(tmp_path):
    f = tmp_path / "loop-brief.md"
    body = ["# Loop brief", ""]
    for section in ("Open queue", "Unapplied Lovable prompts",
                    "Card-registry data entry"):
        body.append(f"## {section}")
        body.extend(f"- item {i}" for i in range(130))
    f.write_text("\n".join(body) + "\n", encoding="utf-8")
    text = reason(f, "# Loop brief\n\n## Current focus\n" + lines(20, "- item"))
    assert "## Open queue" in text
    assert "## Unapplied Lovable prompts" in text
    assert "# Loop brief" not in text.split("Structure present now")[1].split("\n\n")[0]


# ---- Threshold behavior --------------------------------------------------

def test_hard_floor_absolute_removal_asks(tmp_path):
    f = tmp_path / "big.py"
    f.write_text(lines(1000), encoding="utf-8")
    assert decide(f, lines(800)) == "ask"   # 200 removed, only 20% of the file


def test_ratio_removal_asks(tmp_path):
    f = tmp_path / "mid.md"
    f.write_text(lines(140), encoding="utf-8")
    assert decide(f, lines(80)) == "ask"    # 60 removed = 43%


def test_small_trim_below_both_thresholds_allows(tmp_path):
    f = tmp_path / "mid.md"
    f.write_text(lines(900), encoding="utf-8")
    assert decide(f, lines(870)) is None    # 30 lines, 3%


def test_ratio_hit_but_too_few_lines_allows(tmp_path):
    f = tmp_path / "small.md"
    f.write_text(lines(60), encoding="utf-8")
    assert decide(f, lines(35)) is None     # 25 removed: 42% but under SOFT floor


def test_tiny_file_never_asks(tmp_path):
    f = tmp_path / "stub.py"
    f.write_text(lines(20), encoding="utf-8")
    assert decide(f, "x = 1\n") is None


# ---- NEGATIVE cases: the contract ---------------------------------------

def test_new_file_allows(tmp_path):
    assert decide(tmp_path / "brand-new.md", lines(500)) is None


def test_growth_allows(tmp_path):
    f = tmp_path / "grow.md"
    f.write_text(lines(100), encoding="utf-8")
    assert decide(f, lines(400)) is None


def test_identical_content_allows(tmp_path):
    f = tmp_path / "same.md"
    f.write_text(lines(500), encoding="utf-8")
    assert decide(f, lines(500)) is None


def test_edit_tool_allows(tmp_path):
    """Edit is surgical by construction; this gate is about whole-file Write."""
    f = tmp_path / "x.md"
    f.write_text(lines(500), encoding="utf-8")
    assert decide(f, lines(10), tool="Edit") is None


def test_scratch_path_exempt(tmp_path):
    d = tmp_path / ".scratch"
    d.mkdir()
    f = d / "probe.py"
    f.write_text(lines(500), encoding="utf-8")
    assert decide(f, lines(10)) is None


def test_lockfile_exempt(tmp_path):
    f = tmp_path / "package-lock.json"
    f.write_text(lines(5000), encoding="utf-8")
    assert decide(f, lines(10)) is None


def test_binary_file_allows(tmp_path):
    f = tmp_path / "image.bin"
    f.write_bytes(b"\x00\xff" * 5000)
    assert decide(f, lines(2)) is None


def test_missing_content_field_allows(tmp_path):
    f = tmp_path / "x.md"
    f.write_text(lines(500), encoding="utf-8")
    r = run_hook(HOOK, {"tool_name": "Write", "tool_input": {"file_path": str(f)}},
                 env=ENV)
    assert r.returncode == 0
    assert permission_decision(r.stdout) is None


def test_override_env_allows(tmp_path):
    f = tmp_path / "x.md"
    f.write_text(lines(500), encoding="utf-8")
    r = run_hook(
        HOOK,
        {"tool_name": "Write", "tool_input": {"file_path": str(f), "content": lines(10)}},
        env={**ENV, "WRITE_SHRINK_GATE_ALLOW": "1"},
    )
    assert permission_decision(r.stdout) is None


# ---- Unit-level pins -----------------------------------------------------

mod = load_hook(HOOK)


def test_should_ask_matrix():
    assert mod.should_ask(1000, 800) is True     # hard floor
    assert mod.should_ask(140, 80) is True       # ratio + soft floor
    assert mod.should_ask(900, 870) is False     # below both
    assert mod.should_ask(60, 35) is False       # under soft floor
    assert mod.should_ask(20, 1) is False        # file too small
    assert mod.should_ask(500, 900) is False     # growth


def test_lost_anchors_ignores_survivors():
    old = "## Keep\nbody\n## Drop\nbody\ndef f():\n    pass\n"
    new = "## Keep\nbody\ndef f():\n    pass\n"
    assert mod.lost_anchors(old, new) == ["## Drop"]
