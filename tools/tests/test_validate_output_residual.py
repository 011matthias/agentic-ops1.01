"""validate-output.py residual fixes (2026-07-22 audit).

A2 — check_unsourced_claims dropped the flag when HEDGE_RE matched ANYWHERE
     on the line, even when the hedge modified a different clause
     ("Deliverability has dropped sharply; we should probably revisit X"
     went unflagged). The hedge test is now scoped to the clause/sentence
     containing the claim (split on . ; : ! ?, commas keep their hedge).

A4 — lines starting `> ` (blockquote) were exempt from ALL rules, so
     agent-authored blockquotes carried brand misspells and leaked
     placeholders through. Brand-spelling and placeholder rules now run on
     blockquoted lines; the em-dash/voice rules stay exempt (quoted inbound
     text legitimately contains them), and blockquotes stay out of the
     unsourced-claim eligible set (a quoted claim is the sender's).
"""
import importlib.util
import sys

from hooklib import TOOLS


def _load():
    path = TOOLS / "validate-output.py"
    spec = importlib.util.spec_from_file_location("validate_output_residual", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


vo = _load()


def _cats(text: str) -> list[str]:
    return [h["category"] for h in vo.check_text(text)]


# --- A2: hedge scoped to the claim's clause ----------------------------------

def test_hedge_in_other_clause_no_longer_shields():
    # The audit's exact escape shape: hedge modifies the follow-up clause.
    text = "Deliverability has dropped sharply; we should probably revisit the cadence.\n"
    assert "unsourced-claim" in _cats(text)


def test_hedge_after_sentence_end_no_longer_shields():
    text = "The campaign has tanked. We could look at the copy next week.\n"
    assert "unsourced-claim" in _cats(text)


def test_hedge_in_same_clause_still_exempts():
    # Comma-attached hedge lives in the same clause as the claim.
    assert "unsourced-claim" not in _cats("Deliverability has dropped sharply, probably.\n")


def test_leading_hedge_same_clause_still_exempts():
    assert "unsourced-claim" not in _cats("I suspect deliverability has dropped sharply.\n")


def test_comma_does_not_split_the_clause():
    # Hedge and claim in one sentence separated by a comma stay together.
    text = "Deliverability has dropped, which could be a tracking artifact.\n"
    assert "unsourced-claim" not in _cats(text)


def test_source_attribution_window_still_exempts():
    text = (
        "Per Instantly analytics pulled this morning:\n"
        "Deliverability has dropped sharply.\n"
    )
    assert "unsourced-claim" not in _cats(text)


def test_suppression_still_works():
    text = (
        "<!-- output-allow:unsourced-claim verified live 2026-07-22 -->\n"
        "Deliverability has dropped sharply; we should revisit the cadence.\n"
    )
    assert "unsourced-claim" not in _cats(text)


def test_flat_unhedged_claim_still_flags():
    assert "unsourced-claim" in _cats("Deliverability has dropped sharply.\n")


# --- A4: blockquotes keep voice exemption, lose brand/placeholder immunity ---

def test_blockquote_brand_misspell_flagged():
    assert "brand-misspell" in _cats("> Thanks for the intro to UnpausAI!\n")


def test_blockquote_placeholder_leak_flagged():
    assert "placeholder-leak" in _cats("> Hi {{first_name}}, quick question.\n")


def test_blockquote_hash_placeholder_flagged():
    assert "placeholder-leak" in _cats("> Dear ##CLIENT_NAME##,\n")


def test_blockquote_em_dash_still_exempt():
    cats = _cats("> Great work — really moved the needle.\n")
    assert "em-dash" not in cats and "em-dash-substitute" not in cats


def test_blockquote_llm_tell_still_exempt():
    assert "llm-tell" not in _cats("> Let's delve into the numbers together.\n")


def test_blockquote_claim_not_eligible_for_unsourced():
    # A quoted claim is the sender's assertion, not ours.
    assert "unsourced-claim" not in _cats("> Deliverability has dropped sharply.\n")


def test_blockquote_suppression_still_works():
    text = (
        "<!-- output-allow:brand-misspell quoting their typo verbatim -->\n"
        "> They wrote UnpausAI in the brief.\n"
    )
    assert "brand-misspell" not in _cats(text)


def test_plain_line_rules_unchanged():
    cats = _cats("UnpausAI ships — fast, we delve into {{topic}}.\n")
    assert {"brand-misspell", "em-dash", "llm-tell", "placeholder-leak"} <= set(cats)
