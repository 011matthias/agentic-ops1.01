"""check-skill-map.py regression tests.

Runs the tool as a subprocess against (a) the real skill tree — which must be
clean, that IS the gate — and (b) a synthetic fixture skill seeded with one of
each finding class, asserting the tool actually detects what it claims to.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "check-skill-map.py"


def run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True, text=True, encoding="utf-8", cwd=str(REPO),
    )


def test_web_build_skill_is_clean():
    # The full first-party tree carries a known pre-existing drift backlog
    # (pack consolidations left dead cross-references; burned down fix-on-touch
    # via the post-write-gate advisory). The CI-clean contract starts with the
    # skill that introduced the tool.
    proc = run_tool(str(REPO / ".claude" / "skills" / "skil_web-build" / "SKILL.md"))
    assert proc.returncode == 0, f"skil_web-build has map drift:\n{proc.stdout}{proc.stderr}"


def test_detects_seeded_findings(tmp_path):
    # Build a fixture skill with one dead pointer, one unreachable module,
    # and a duplicated rule ID across two files.
    skill = tmp_path / ".claude" / "skills" / "skil_fixture"
    (skill / "modules").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "# Fixture\n\nLoad `modules/exists.md` and `modules/ghost.md`.\n"
        "<!-- rule:web-fixture-dup -->\n",
        encoding="utf-8",
    )
    (skill / "modules" / "exists.md").write_text("ok\n", encoding="utf-8")
    (skill / "modules" / "orphan.md").write_text(
        "<!-- rule:web-fixture-dup -->\n", encoding="utf-8"
    )

    # Point the tool at the fixture tree by running it with a patched repo:
    # the tool derives SKILLS from its own location, so run it via a copy.
    tool_copy_dir = tmp_path / "tools"
    tool_copy_dir.mkdir()
    (tool_copy_dir / "check-skill-map.py").write_text(
        TOOL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    proc = subprocess.run(
        [sys.executable, str(tool_copy_dir / "check-skill-map.py"), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path),
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    cats = payload["by_category"]
    assert cats.get("dead-pointer", 0) >= 1, payload          # ghost.md
    assert cats.get("unreachable-module", 0) >= 1, payload    # orphan.md
    assert cats.get("duplicate-rule-id", 0) >= 1, payload     # web-fixture-dup


def test_out_of_scope_path_is_clean_json():
    proc = run_tool(str(REPO / "tools" / "INDEX.md"), "--format", "json")
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["total"] == 0


def _run_fixture(tmp_path) -> dict:
    """Run a copy of the tool against a synthetic .claude/skills tree under tmp."""
    tool_copy_dir = tmp_path / "tools"
    tool_copy_dir.mkdir(exist_ok=True)
    (tool_copy_dir / "check-skill-map.py").write_text(
        TOOL.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(tool_copy_dir / "check-skill-map.py"), "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(tmp_path),
    )
    return json.loads(proc.stdout)


def test_pack_consumed_stub_module_not_flagged(tmp_path):
    # C1: a pack spine routes into a consolidation stub's module via a cross-skill
    # link; the module is reachable even though the stub's own SKILL.md never
    # names it. A genuine orphan (referenced by no spine anywhere) still fires.
    skills = tmp_path / ".claude" / "skills"
    pack = skills / "skil_pack"
    pack.mkdir(parents=True)
    (pack / "SKILL.md").write_text(
        "# Pack\n\nLoad `../skil_stub/modules/THING.md` for the detail.\n", encoding="utf-8")
    stub = skills / "skil_stub"
    (stub / "modules").mkdir(parents=True)
    (stub / "SKILL.md").write_text("# Stub\n\nConsolidated into skil_pack.\n", encoding="utf-8")
    (stub / "modules" / "THING.md").write_text("detail\n", encoding="utf-8")
    (stub / "modules" / "ORPHAN.md").write_text("nobody references me\n", encoding="utf-8")

    msgs = [h["message"] for h in _run_fixture(tmp_path)["hits"]]
    assert not any("THING.md exists but" in m for m in msgs), msgs   # reachable via pack
    assert any("ORPHAN.md exists but" in m for m in msgs), msgs       # genuine orphan


def test_illustrative_paths_skipped_real_drift_still_flagged(tmp_path):
    # C2: @-prefix imports, `Example:` lines, and fenced code blocks are
    # illustrative, not repo pointers; a plain-prose dead pointer still fires.
    skills = tmp_path / ".claude" / "skills"
    sk = skills / "skil_demo"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "# Demo\n\n"
        "Import with `@docs/file.md`.\n"            # @-prefix -> skipped
        "Example: `commands/ghost.md`.\n"           # Example: line -> skipped
        "```\n`fenced/ghost.md`\n```\n"             # fenced block -> skipped
        "Load `modules/real-ghost.md` now.\n",      # plain prose, missing -> flagged
        encoding="utf-8")
    dead = [h["message"] for h in _run_fixture(tmp_path)["hits"]
            if h["category"] == "dead-pointer"]
    assert len(dead) == 1 and "real-ghost.md" in dead[0], dead
