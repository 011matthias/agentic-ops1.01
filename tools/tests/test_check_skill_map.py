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


def test_full_first_party_tree_is_clean():
    # The pack-consolidation drift backlog was burned down 2026-07-22, so the
    # CI-clean contract is now the WHOLE first-party tree, not one skill. A new
    # dead pointer or orphaned module fails here instead of accumulating.
    proc = run_tool()
    assert proc.returncode == 0, f"skill map drift:\n{proc.stdout}{proc.stderr}"


def test_web_build_skill_is_clean():
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


def _dead(tmp_path) -> list[str]:
    return [h["message"] for h in _run_fixture(tmp_path)["hits"]
            if h["category"] == "dead-pointer"]


def test_markdown_link_to_missing_file_fires(tmp_path):
    # L1: the blind spot this coverage closes. A markdown link is a routing
    # pointer exactly like a backticked path; a missing target fires, an
    # existing one does not.
    sk = tmp_path / ".claude" / "skills" / "skil_link"
    (sk / "modules").mkdir(parents=True)
    (sk / "modules" / "REAL.md").write_text("real\n", encoding="utf-8")
    (sk / "SKILL.md").write_text(
        "# Link\n\n"
        "Load [REAL](modules/REAL.md) for the detail.\n"    # exists -> quiet
        "Load [GHOST](modules/GHOST.md) for more.\n",       # missing -> fires
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "modules/GHOST.md" in dead[0], dead


def test_pack_prefix_loss_in_link_fires(tmp_path):
    # L2: the exact 2026-07-22 regression class. A pack spine routes into a
    # consolidation stub via a cross-skill link that dropped the `skil_`
    # prefix; the corrected link resolves and stays quiet.
    skills = tmp_path / ".claude" / "skills"
    (skills / "skil_stub" / "modules").mkdir(parents=True)
    (skills / "skil_stub" / "SKILL.md").write_text("# Stub\n", encoding="utf-8")
    (skills / "skil_stub" / "modules" / "THING.md").write_text("x\n", encoding="utf-8")
    pack = skills / "skil_pack"
    pack.mkdir(parents=True)
    (pack / "SKILL.md").write_text(
        "# Pack\n\n"
        "| Bad | [THING](../stub/modules/THING.md) |\n"        # prefix lost -> fires
        "| Good | [THING](../skil_stub/modules/THING.md) |\n",  # correct -> quiet
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "../stub/modules/THING.md" in dead[0], dead


def test_link_anchor_and_query_stripped_before_resolving(tmp_path):
    # L3: `FILE.md#section` is a pointer to FILE.md. The fragment (and any
    # query) is stripped before resolution, so a real file with an anchor is
    # quiet and a missing one still fires — reported by its bare path.
    sk = tmp_path / ".claude" / "skills" / "skil_anchor"
    (sk / "modules").mkdir(parents=True)
    (sk / "modules" / "REAL.md").write_text("real\n", encoding="utf-8")
    (sk / "SKILL.md").write_text(
        "# Anchor\n\n"
        "See [a](modules/REAL.md#step-3) and [b](modules/REAL.md?v=2).\n"  # quiet
        "See [c](modules/GHOST.md#step-3).\n",                             # fires
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1, dead
    assert "modules/GHOST.md" in dead[0] and "#step-3" not in dead[0], dead


def test_external_and_pure_anchor_links_never_fire(tmp_path):
    # L4: schemes and in-page anchors are not file pointers. Detection is by
    # URL scheme (`name:`), never a bare prefix — `http_api_integration.md`
    # starts with "http" but is a real sibling file, so it MUST be checked.
    sk = tmp_path / ".claude" / "skills" / "skil_ext"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "# Ext\n\n"
        "[a](https://example.com/x.md) [b](http://example.com/y.md)\n"
        "[c](mailto:admin@unpauseai.com) [d](tel:+4900) [e](#section)\n"
        "[f](/docs/site-absolute.md)\n"          # site-root, not a repo pointer
        "[g](http_api_integration.md)\n",        # NOT a scheme -> must fire
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "http_api_integration.md" in dead[0], dead


def test_image_links_are_checked_like_file_links(tmp_path):
    # L5: images are pointers too. A shipped diagram that resolves nowhere is
    # the same drift class as a missing module, and costs nothing to catch, so
    # `![alt](path)` is checked and image suffixes are in scope.
    sk = tmp_path / ".claude" / "skills" / "skil_img"
    (sk / "references").mkdir(parents=True)
    (sk / "references" / "flow.png").write_bytes(b"\x89PNG\r\n")
    (sk / "SKILL.md").write_text(
        "# Img\n\n"
        "![flow](references/flow.png)\n"      # exists -> quiet
        "![gone](references/gone.svg)\n",     # missing -> fires
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "references/gone.svg" in dead[0], dead


def test_same_path_backticked_and_linked_reported_once(tmp_path):
    # L6: ``[`x/Y.md`](x/Y.md)`` is one pointer written twice. Both extractors
    # see it; the line-level dedupe means it is reported once, not twice.
    sk = tmp_path / ".claude" / "skills" / "skil_dup"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "# Dup\n\nLoad [`modules/GHOST.md`](modules/GHOST.md) now.\n",
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "modules/GHOST.md" in dead[0], dead


def test_link_resolves_against_containing_dir_only(tmp_path):
    # L7: a link has ONE correct base — the dir of the file holding it — because
    # that is what a reader following it gets. `[SKILL.md](SKILL.md)` inside
    # modules/ is broken even though the spine exists one level up; backticked
    # prose keeps the permissive skill-dir/repo-root resolution.
    sk = tmp_path / ".claude" / "skills" / "skil_base"
    (sk / "modules").mkdir(parents=True)
    (sk / "SKILL.md").write_text("# Base\n\nmodules/A.md modules/B.md\n", encoding="utf-8")
    (sk / "modules" / "A.md").write_text(
        "- [spine](SKILL.md)\n", encoding="utf-8")        # wrong base -> fires
    (sk / "modules" / "B.md").write_text(
        "- [spine](../SKILL.md)\n"                        # correct -> quiet
        "- prose pointer `modules/A.md` resolves via the skill dir\n",
        encoding="utf-8")
    dead = _dead(tmp_path)
    assert len(dead) == 1 and "A.md: link target `SKILL.md`" in dead[0], dead


def test_runtime_created_paths_not_flagged(tmp_path):
    # C3: skil_prompt-queue documents `.claude/queue/pending.md` / `done.md` as
    # real pointers it creates on first use, so absence at rest is not drift. A
    # sibling path under the same dir that nothing creates still fires.
    sk = tmp_path / ".claude" / "skills" / "skil_queue"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "# Queue\n\n"
        "- `.claude/queue/pending.md` is the queue.\n"      # allowlisted -> skipped
        "- `.claude/queue/done.md` is the archive.\n"       # allowlisted -> skipped
        "- `.claude/queue/invented.md` is not real.\n",     # not allowlisted -> flagged
        encoding="utf-8")
    dead = [h["message"] for h in _run_fixture(tmp_path)["hits"]
            if h["category"] == "dead-pointer"]
    assert len(dead) == 1 and "invented.md" in dead[0], dead
