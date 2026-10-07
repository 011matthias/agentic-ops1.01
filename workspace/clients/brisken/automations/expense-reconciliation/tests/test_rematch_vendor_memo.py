"""A duplicate click re-matches the month; the vendor work must scale with the
NAMES in it, not with charges x receipts (2026-10-07).

"Removing duplicates takes way too long to load." Every "Delete this copy"
and "Not a copy" re-matches the month inside the request, and `match_one`
scores the vendor of every charge x receipt pair before its date and amount
gates. On September (216 charges, 112 receipts) that was 26,163
`vendor_similarity` calls over 3,710 distinct string pairs, run twice per
re-match (item 74), and 7 of the 14 s the click took locally. The merchant
registry did the same: 700 `resolve` calls for 274 names.

These tests go through `match_month` and `MerchantRegistry.resolve`, the
callers the fix changed, and pin two things: the work is done once per
distinct input, and the answer is the one the uncached functions give.
"""
from __future__ import annotations

import difflib
from datetime import date, timedelta
from decimal import Decimal

import expense_recon.matching.deterministic as det
import expense_recon.merchant_registry as mr
from expense_recon.matching.deterministic import MatchingConfig, match_month
from expense_recon.matching.types import Receipt, Transaction

# Three bank lines and three receipt spellings, repeated across a month the
# way real months repeat a subscription. The receipt spellings differ as raw
# strings but share their words, which is the case the word-level cache is for.
STATEMENT = ["OPENAI *CHATGPT SUBSCR", "GOOGLE *Workspace_bris", "LOVABLE LABS"]
RECEIPTS = ["OpenAI, LLC", "OPENAI LLC", "Lovable Labs Incorporated"]


def _month(n_tx: int = 60, n_rec: int = 45):
    start = date(2026, 9, 1)
    txs = [
        Transaction(
            f"t{i}", "ent", "card-2838", start + timedelta(days=i % 28), None,
            Decimal(20 + i % 7), "USD", "USD", STATEMENT[i % len(STATEMENT)],
        )
        for i in range(n_tx)
    ]
    recs = [
        Receipt(
            f"d{i}", "ent", start + timedelta(days=i % 28), Decimal(20 + i % 7),
            "USD", RECEIPTS[i % len(RECEIPTS)],
        )
        for i in range(n_rec)
    ]
    return txs, recs


def _clear_caches():
    for fn in (det.vendor_similarity, det._token_ratio, det.strip_reference_tokens):
        getattr(fn, "cache_clear", lambda: None)()


def _summary(outcome):
    return (
        sorted(
            (m.transaction_id, m.document_id, m.match_type, m.score,
             m.vendor_score, m.requires_review)
            for m in outcome.matches
        ),
        sorted(outcome.unmatched_transactions),
        sorted(outcome.unmatched_receipts),
    )


def test_a_rematch_normalizes_each_vendor_once_not_once_per_pair(monkeypatch):
    """Two passes over 60 x 45 pairs name 3 + 3 vendors. Uncached, the
    vendor score normalized both strings for every pair of both passes
    (2 x 2,700 x 2 = 10,800 calls); cached, once per distinct pair."""
    txs, recs = _month()
    _clear_caches()
    calls = {"n": 0}
    real = det._normalize

    def counting(s):
        calls["n"] += 1
        return real(s)

    monkeypatch.setattr(det, "_normalize", counting)
    match_month(txs, recs, MatchingConfig())
    match_month(txs, recs, MatchingConfig())  # the re-match's second pass
    distinct_pairs = len(STATEMENT) * len(RECEIPTS)
    assert calls["n"] <= 4 * distinct_pairs + 2 * len(STATEMENT), calls["n"]


def test_word_pairs_are_compared_once_across_spellings(monkeypatch):
    """'OpenAI, LLC' and 'OPENAI LLC' are two vendor strings with the same
    words; each statement word is compared with each receipt word once."""
    txs, recs = _month()
    _clear_caches()
    made = {"n": 0}
    real = difflib.SequenceMatcher

    class Counting(real):
        def __init__(self, *a, **kw):
            made["n"] += 1
            super().__init__(*a, **kw)

    monkeypatch.setattr(det.difflib, "SequenceMatcher", Counting)
    match_month(txs, recs, MatchingConfig())
    s_words = {w for s in STATEMENT for w in det._normalize(s).split() if len(w) >= 3}
    r_words = {w for s in RECEIPTS for w in det._normalize(s).split() if len(w) >= 3}
    assert made["n"] <= len(s_words) * len(r_words), made["n"]


def test_the_cached_matcher_answers_what_the_uncached_one_did(monkeypatch):
    txs, recs = _month()
    _clear_caches()
    cached = _summary(match_month(txs, recs, MatchingConfig()))

    def uncached_ratio(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio()

    monkeypatch.setattr(det, "vendor_similarity",
                        getattr(det.vendor_similarity, "__wrapped__", det.vendor_similarity))
    monkeypatch.setattr(det, "_token_ratio", uncached_ratio)
    monkeypatch.setattr(det, "strip_reference_tokens",
                        getattr(det.strip_reference_tokens, "__wrapped__", det.strip_reference_tokens))
    assert _summary(match_month(txs, recs, MatchingConfig())) == cached
    assert cached[0], "the fixture month must produce matches to compare"


REGISTRY = {
    "OpenAI": {"aliases": ["OpenAI LLC"], "category": "Software"},
    "Lovable Labs": {"aliases": []},
    "Google Workspace": {"aliases": []},
}


def test_a_registry_resolves_a_repeated_name_once(monkeypatch):
    """Every tier starts from `_probe_pairs`, so counting it counts the
    resolutions actually computed, whichever tier answers."""
    reg = mr.MerchantRegistry(REGISTRY)
    probed = {"n": 0}
    real = mr.MerchantRegistry._probe_pairs

    def counting(self, *a, **kw):
        probed["n"] += 1
        return real(self, *a, **kw)

    monkeypatch.setattr(mr.MerchantRegistry, "_probe_pairs", counting)
    for name in ("LOVABLE*LABS INC", "Unknown Cafe"):  # a hit and a miss
        first = reg.resolve(None, name)
        for _ in range(20):
            assert reg.resolve(None, name) == first
    assert probed["n"] == 2


def test_a_registry_answer_matches_an_uncached_registry():
    names = ["OpenAI, LLC", "LOVABLE*LABS INC", "GOOGLE *Workspace_bris", "Unknown Cafe"]
    warm = mr.MerchantRegistry(REGISTRY)
    for n in names:
        warm.resolve(None, n)
    for n in names:
        assert warm.resolve(None, n) == mr.MerchantRegistry(REGISTRY)._resolve(None, n)


def test_distinctive_hands_back_a_list_the_caller_may_keep():
    words = ["lovable", "labs", "inc"]
    got = mr._distinctive(words)
    expected = list(got)
    assert "lovable" in expected and "inc" not in expected
    got.append("mutated")
    assert mr._distinctive(words) == expected
