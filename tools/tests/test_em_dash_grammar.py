"""Em-dash input-grammar coverage (2026-07-22 blind-spot fixes).

The validators and the corrective strip tool only matched the space-padded
forms (` — `, ` -- `), so tight `word—word`, the `&mdash;` entity, and tight
`word--word` shipped unflagged and unstripped. These tests pin the widened
grammar across all three tools:

  tools/validate-output.py     RULES em-dash / em-dash-substitute
  tools/lint-comms-draft.py    EM_DASH_RULES
  tools/strip-em-dash.py       spaced -> `; `, tight -> `, `, idempotent
"""
import importlib.util
import sys
from pathlib import Path

from hooklib import TOOLS


def _load(name: str, module_name: str):
    path = TOOLS / name
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


vo = _load("validate-output.py", "validate_output")
lc = _load("lint-comms-draft.py", "lint_comms_draft")
se = _load("strip-em-dash.py", "strip_em_dash")


# --- validate-output.py RULES ----------------------------------------------

def _vo_cats(text: str) -> list[str]:
    return [h["category"] for h in vo.check_text(text)]


def test_vo_tight_unicode_em_dash_flagged():
    assert "em-dash" in _vo_cats("Ships well—fast turnaround.\n")


def test_vo_mdash_entity_flagged():
    assert "em-dash" in _vo_cats("Ships well &mdash; fast.\n")


def test_vo_tight_double_hyphen_flagged():
    assert "em-dash-substitute" in _vo_cats("Ships well--fast.\n")


def test_vo_spaced_em_dash_fires_exactly_once():
    # The spaced form must not double-fire now that a tight rule exists.
    hits = [c for c in _vo_cats("Ships well — fast.\n") if c == "em-dash"]
    assert hits == ["em-dash"]


def test_vo_cli_flag_is_not_a_substitute():
    # ` --format` has no word char before the hyphens; not an em-dash shape.
    assert "em-dash-substitute" not in _vo_cats("Run with --format json.\n")


def test_vo_plain_hyphen_clean():
    assert "em-dash" not in _vo_cats("A well-known client-facing build.\n")


# --- lint-comms-draft.py EM_DASH_RULES --------------------------------------

def _lc_cats(text: str) -> list[str]:
    return [h["category"] for h in lc.check_text(text, include_em_dash=True)]


def test_lc_tight_unicode_em_dash_flagged():
    assert "em-dash" in _lc_cats("Ships well—fast turnaround.\n")


def test_lc_mdash_entity_flagged():
    assert "em-dash" in _lc_cats("Ships well&mdash;fast.\n")


def test_lc_tight_double_hyphen_flagged():
    assert "em-dash-substitute" in _lc_cats("Ships well--fast.\n")


def test_lc_skip_em_dash_still_skips_all_forms():
    text = "well—fast &mdash; well--fast — done\n"
    cats = [h["category"] for h in lc.check_text(text, include_em_dash=False)]
    assert "em-dash" not in cats
    assert "em-dash-substitute" not in cats


# --- strip-em-dash.py --------------------------------------------------------

def _strip(tmp_path: Path, body: str):
    f = tmp_path / "draft.md"
    f.write_text(body, encoding="utf-8")
    rep, rem = se.strip_em_dashes(f)
    return f.read_text(encoding="utf-8"), rep, rem


def test_strip_spaced_em_dash_to_semicolon(tmp_path):
    text, rep, rem = _strip(tmp_path, "Phase 1 — ready for review.\n")
    assert text == "Phase 1; ready for review.\n"
    assert (rep, rem) == (1, 0)


def test_strip_tight_em_dash_to_comma(tmp_path):
    text, rep, rem = _strip(tmp_path, "Ships well—fast turnaround.\n")
    assert text == "Ships well, fast turnaround.\n"
    assert (rep, rem) == (1, 0)


def test_strip_tight_entity_to_comma(tmp_path):
    text, rep, rem = _strip(tmp_path, "Ships well&mdash;fast.\n")
    assert text == "Ships well, fast.\n"
    assert (rep, rem) == (1, 0)


def test_strip_spaced_entity_to_semicolon(tmp_path):
    text, rep, rem = _strip(tmp_path, "Phase 1 &mdash; ready.\n")
    assert text == "Phase 1; ready.\n"
    assert (rep, rem) == (1, 0)


def test_strip_is_idempotent(tmp_path):
    f = tmp_path / "draft.md"
    f.write_text("A — b, c—d, e &mdash; f, g&mdash;h.\n", encoding="utf-8")
    rep1, _ = se.strip_em_dashes(f)
    first = f.read_text(encoding="utf-8")
    rep2, _ = se.strip_em_dashes(f)
    assert rep1 == 4
    assert rep2 == 0
    assert f.read_text(encoding="utf-8") == first


def test_strip_tight_double_hyphen_left_for_review(tmp_path):
    # Deliberately NOT auto-stripped (CLI flags, filenames); validators flag it.
    text, rep, _ = _strip(tmp_path, "Ships well--fast.\n")
    assert text == "Ships well--fast.\n"
    assert rep == 0


def test_strip_fenced_code_untouched(tmp_path):
    body = "```\nx — y and a—b\n```\n"
    text, rep, _ = _strip(tmp_path, body)
    assert text == body
    assert rep == 0
