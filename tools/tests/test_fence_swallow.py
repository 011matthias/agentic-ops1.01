"""Unclosed-fence swallow (2026-07-22 blind-spot fix).

In both text validators a line starting ``` toggles in_fence; an unbalanced
fence used to exempt the whole rest of the file from every rule — a single
decorative ``` above a HIGH violation silenced it. Now an unclosed fence
triggers a rescan of the swallowed tail with fencing disabled, plus a LOW
`fence-unbalanced` advisory. Balanced fences must keep skipping code.
"""
import importlib.util
import sys

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


# --- validate-output.py -------------------------------------------------------

def test_vo_unclosed_fence_tail_is_rescanned():
    text = "intro line\n```\nThe brand is UnpausAI, misspelled in the tail.\n"
    hits = vo.check_text(text)
    cats = {h["category"] for h in hits}
    assert "brand-misspell" in cats  # HIGH violation must not hide
    assert "fence-unbalanced" in cats


def test_vo_fence_advisory_is_low_and_points_at_opener():
    text = "one\ntwo\n```\ntail\n"
    adv = [h for h in vo.check_text(text) if h["category"] == "fence-unbalanced"]
    assert len(adv) == 1
    assert adv[0]["severity"] == "LOW"
    assert adv[0]["line"] == 3


def test_vo_balanced_fence_still_skips_code():
    text = "```\nThe brand is UnpausAI inside a real code block.\n```\nafter\n"
    cats = {h["category"] for h in vo.check_text(text)}
    assert "brand-misspell" not in cats
    assert "fence-unbalanced" not in cats


def test_vo_violation_before_the_unclosed_fence_not_doubled():
    text = "UnpausAI before the fence.\n```\nUnpausAI after.\n"
    hits = [h for h in vo.check_text(text) if h["category"] == "brand-misspell"]
    assert [h["line"] for h in hits] == [1, 3]


# --- lint-comms-draft.py -------------------------------------------------------

def test_lc_unclosed_fence_tail_is_rescanned():
    text = "hi\n```\nIt's worth noting that this used to hide.\n"
    hits = lc.check_text(text, include_em_dash=False)
    cats = {h["category"] for h in hits}
    assert "llm-opener" in cats  # HIGH violation must not hide
    assert "fence-unbalanced" in cats


def test_lc_balanced_fence_still_skips_code():
    text = "```\nIt's worth noting that this is code.\n```\nafter\n"
    cats = {h["category"] for h in lc.check_text(text, include_em_dash=False)}
    assert "llm-opener" not in cats
    assert "fence-unbalanced" not in cats
