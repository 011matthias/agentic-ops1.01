"""em-dash-strip-gate (PostToolUse:Write|Edit): strips em-dashes from in-scope
client-facing files only.

Unit-tests the scope classifier (the part most likely to regress when the
deliverable/comms path set changes), plus two end-to-end tests: an in-scope
file with a spaced em-dash gets it stripped on disk; an out-of-scope file is
left untouched and the hook stays silent.

The end-to-end strip path shells out to `uv run tools/strip-em-dash.py`, so it
requires uv on PATH (CI installs it; local dev has it).
"""
import importlib.util

from hooklib import HOOKS, run_hook

_spec = importlib.util.spec_from_file_location(
    "em_dash_strip_gate", HOOKS / "em-dash-strip-gate.py"
)
edg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(edg)


def test_scope_includes_deliverables_and_comms():
    assert edg.in_human_to_human_scope("/x/platform/public/clients/foo/index.html")
    assert edg.in_human_to_human_scope("/x/proposals/p001.md")
    assert edg.in_human_to_human_scope("/x/workspace/clients/c/context/drafts/d.md")


def test_scope_excludes_internal_and_code():
    assert not edg.in_human_to_human_scope("/x/workspace/clients/c/context/notes.md")
    assert not edg.in_human_to_human_scope("/x/tools/foo.py")
    assert not edg.in_human_to_human_scope("/x/docs/sessions/2026-06-06.md")
    assert not edg.in_human_to_human_scope("")


def test_normalize_path_gitbash_drive():
    assert edg.normalize_path("/c/Users/x/file.md") == "C:/Users/x/file.md"


def test_end_to_end_strips_in_scope(tmp_path):
    d = tmp_path / "proposals"
    d.mkdir()
    f = d / "draft.md"
    f.write_text("Phase 1 — ready for your review.\n", encoding="utf-8")
    run_hook("em-dash-strip-gate.py", {"tool_input": {"file_path": str(f)}})
    assert "—" not in f.read_text(encoding="utf-8")


def test_end_to_end_skips_out_of_scope(tmp_path):
    f = tmp_path / "notes.md"  # path carries no deliverable/comms scope marker
    f.write_text("Phase 1 — ready.\n", encoding="utf-8")
    p = run_hook("em-dash-strip-gate.py", {"tool_input": {"file_path": str(f)}})
    assert "—" in f.read_text(encoding="utf-8")  # untouched
    assert p.stdout.strip() == ""
