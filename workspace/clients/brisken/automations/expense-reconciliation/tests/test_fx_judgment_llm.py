"""Tests for the FX-judgment LLM path (slice 2, D1b).

The hard case from Dirk's call: a EUR receipt against a USD card
transaction. The deterministic layer short-circuits these to
`judgment_required`; with an LLMClient wired, `judge_fx_match` returns a
real model verdict instead of the slice-1 stub. Every FX case stays in
review regardless of the verdict (call-outcomes D2).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.cli import _apply_ambiguous_judgment, _apply_judgment
from expense_recon.llm.client import (
    AmbiguousJudgmentResult,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.llm.cost import CostTracker
from expense_recon.matching.judgment import (
    STUB_REASON,
    judge_ambiguous,
    judge_fx_match,
)
from expense_recon.matching.types import (
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)


def _tx(**overrides) -> Transaction:
    base = dict(
        transaction_id="t1",
        legal_entity_id="le1",
        account_id="amex-usd",
        transaction_date=date(2026, 4, 12),
        posting_date=None,
        amount=Decimal("112.30"),          # USD posted to the card
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="HOTEL PARIS FR",
    )
    base.update(overrides)
    return Transaction(**base)


def _receipt(**overrides) -> Receipt:
    base = dict(
        document_id="r1",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 12),
        detected_total=Decimal("98.45"),    # EUR on the receipt
        detected_currency="EUR",
        detected_vendor="Hotel Paris",
        detected_reference=None,
    )
    base.update(overrides)
    return Receipt(**base)


# ── client path: verdict carried through ────────────────────────────


def test_fx_judge_with_client_uses_llm_verdict():
    """A confident LLM match becomes a FX_JUDGMENT Match carrying the
    model's confidence, still flagged for review, with the converted
    amount + reasoning surfaced in the reason."""
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=True,
            same_purchase_confidence=0.88,
            implied_rate=1.14,
            converted_amount=Decimal("112.23"),
            reasoning="EUR 98.45 at ~1.14 plus card fee matches USD 112.30; same hotel.",
        )
    ])

    judged = judge_fx_match(_tx(), _receipt(), client=mock)

    assert judged.match_type == MatchType.FX_JUDGMENT
    assert judged.requires_review is True
    assert judged.confidence == 0.88
    # Reason surfaces the converted amount and the model's reasoning.
    assert "112.23 USD" in judged.reason
    assert "same hotel" in judged.reason
    assert "review" in judged.reason.lower()


def test_fx_judge_rejection_still_requires_review():
    """When the model judges the pair is NOT the same purchase, the
    entry stays FX_JUDGMENT + requires_review (never silently dropped),
    with a low confidence. Reconciliation guarantee holds."""
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=False,
            same_purchase_confidence=0.12,
            implied_rate=1.14,
            converted_amount=Decimal("112.23"),
            reasoning="Converted amount lines up but the vendors are unrelated.",
        )
    ])

    judged = judge_fx_match(_tx(), _receipt(detected_vendor="Berlin Cafe"), client=mock)

    assert judged.match_type == MatchType.FX_JUDGMENT
    assert judged.requires_review is True
    assert judged.confidence == 0.12
    assert "NOT the same purchase" in judged.reason


# ── no-client path: slice-1 stub preserved ──────────────────────────


def test_fx_judge_no_client_returns_stub():
    """Backward compat: with no client, the stub Match is returned —
    same contract the slice-1 test relied on."""
    judged = judge_fx_match(_tx(), _receipt())  # no client kwarg

    assert judged.match_type == MatchType.FX_JUDGMENT
    assert judged.requires_review is True
    assert judged.reason == STUB_REASON
    assert judged.confidence == 0.5


# ── matching task uses vendor (NOT an LD-2 violation) ───────────────


def test_fx_judge_passes_vendor_to_client():
    """FX judgment is a matching task; vendor name IS a legitimate
    input (unlike LD-2 line-item categorization). The client receives
    both vendors."""
    mock = MockLLMClient()  # default heuristic
    judge_fx_match(_tx(), _receipt(), client=mock)

    assert len(mock.calls) == 1
    method, payload = mock.calls[0]
    assert method == "judge_fx_match"
    assert payload == ("HOTEL PARIS FR", "Hotel Paris")


def test_fx_judge_default_mock_matches_on_vendor_overlap():
    """Default mock heuristic: overlapping vendor names → is_match with
    an implied rate derived from the amount ratio."""
    judged = judge_fx_match(_tx(), _receipt(), client=MockLLMClient())
    # "hotel paris" overlaps "hotel paris fr" → mock says same purchase.
    assert judged.confidence == 0.8
    assert "likely same purchase" in judged.reason


# ── cost discipline ─────────────────────────────────────────────────


def test_fx_judge_records_one_cost_per_call():
    """Each FX judgment is exactly one tracked LLM call."""
    tracker = CostTracker()
    mock = MockLLMClient(cost_tracker=tracker)
    judge_fx_match(_tx(), _receipt(), client=mock)
    judge_fx_match(_tx(transaction_id="t2"), _receipt(document_id="r2"), client=mock)
    assert tracker.call_count == 2
    assert tracker.total_cost_usd == Decimal("0.002")  # 2 × $0.001 mock


# ── CLI wiring: _apply_judgment threads the client ──────────────────


def test_apply_judgment_threads_client_into_fx_calls():
    """The CLI helper replaces each judgment_required entry with the
    client's verdict (not the stub) when a client is supplied."""
    tx = _tx()
    rec = _receipt()
    outcome = MatchOutcome(
        judgment_required=[
            Match(
                transaction_id=tx.transaction_id,
                document_id=rec.document_id,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,
                reason="placeholder from deterministic layer",
                requires_review=True,
            )
        ]
    )
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=True, same_purchase_confidence=0.91,
            implied_rate=1.14, converted_amount=Decimal("112.23"),
            reasoning="match",
        )
    ])

    _apply_judgment(
        outcome,
        {tx.transaction_id: tx},
        {rec.document_id: rec},
        mock,
    )

    assert len(outcome.judgment_required) == 1
    assert outcome.judgment_required[0].confidence == 0.91
    assert mock.calls[0][0] == "judge_fx_match"


def test_apply_judgment_without_client_keeps_stub():
    """No client → the helper still runs and leaves stub verdicts."""
    tx = _tx()
    rec = _receipt()
    outcome = MatchOutcome(
        judgment_required=[
            Match(
                transaction_id=tx.transaction_id,
                document_id=rec.document_id,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,
                reason="placeholder",
                requires_review=True,
            )
        ]
    )

    _apply_judgment(outcome, {tx.transaction_id: tx}, {rec.document_id: rec}, None)

    assert outcome.judgment_required[0].reason == STUB_REASON


def test_apply_judgment_suggest_floor_unbinds_rejected_pair():
    """A real verdict below the suggest floor is not kept as a suggestion:
    the pair is unbound and both ids land in the plain unmatched buckets
    (owner call 2026-07-24: the p=0.10 OpenAI-vs-construction-materials
    pair must not be proposed)."""
    tx = _tx()
    rec = _receipt()
    outcome = MatchOutcome(
        judgment_required=[
            Match(
                transaction_id=tx.transaction_id,
                document_id=rec.document_id,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,
                reason="placeholder",
                requires_review=True,
            )
        ]
    )
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=False, same_purchase_confidence=0.10,
            implied_rate=None, converted_amount=None,
            reasoning="amount and vendor do not line up",
        )
    ])

    _apply_judgment(
        outcome, {tx.transaction_id: tx}, {rec.document_id: rec}, mock,
        suggest_floor=0.2,
    )

    assert outcome.judgment_required == []
    assert outcome.unmatched_transactions == [tx.transaction_id]
    assert outcome.unmatched_receipts == [rec.document_id]


def test_apply_judgment_suggest_floor_keeps_stub_and_confident_pairs():
    """The floor never touches the no-client stub (0.5), and a verdict at
    or above the floor stays in review."""
    tx = _tx()
    rec = _receipt()

    def _outcome() -> MatchOutcome:
        return MatchOutcome(
            judgment_required=[
                Match(
                    transaction_id=tx.transaction_id,
                    document_id=rec.document_id,
                    match_type=MatchType.FX_JUDGMENT,
                    confidence=0.5,
                    reason="placeholder",
                    requires_review=True,
                )
            ]
        )

    # Stub path: no client, floor set — entry stays.
    stub = _outcome()
    _apply_judgment(
        stub, {tx.transaction_id: tx}, {rec.document_id: rec}, None,
        suggest_floor=0.2,
    )
    assert len(stub.judgment_required) == 1

    # Real verdict at the floor — stays as a suggestion.
    kept = _outcome()
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=False, same_purchase_confidence=0.20,
            implied_rate=None, converted_amount=None,
            reasoning="borderline",
        )
    ])
    _apply_judgment(
        kept, {tx.transaction_id: tx}, {rec.document_id: rec}, mock,
        suggest_floor=0.2,
    )
    assert len(kept.judgment_required) == 1
    assert kept.unmatched_transactions == []


# ── judge_ambiguous (tie-break) ─────────────────────────────────────


def _ambiguous_setup():
    """One tx, two tied candidate receipts (same amount/date, different
    vendor). Returns (tx, rec_by_id, [candidate Matches])."""
    tx = _tx(vendor_from_statement="STARBUCKS #4471")
    r1 = _receipt(
        document_id="r1", detected_total=Decimal("112.30"),
        detected_currency="USD", detected_vendor="Whole Foods",
    )
    r2 = _receipt(
        document_id="r2", detected_total=Decimal("112.30"),
        detected_currency="USD", detected_vendor="Starbucks",
    )
    cand = [
        Match(tx.transaction_id, "r1", MatchType.EXACT, 0.99, "exact", False),
        Match(tx.transaction_id, "r2", MatchType.EXACT, 0.99, "exact", False),
    ]
    return tx, {"r1": r1, "r2": r2}, cand


def test_judge_ambiguous_picks_candidate():
    tx, rec_by_id, cand = _ambiguous_setup()
    mock = MockLLMClient(ambiguous_responses=[
        AmbiguousJudgmentResult(chosen_index=2, confidence=0.82, reasoning="vendor Starbucks matches the statement"),
    ])
    pick = judge_ambiguous(tx, cand, rec_by_id, client=mock)
    assert pick is not None
    assert pick.document_id == "r2"
    assert pick.match_type == MatchType.AMBIGUOUS
    assert pick.requires_review is True
    assert pick.confidence == 0.82
    assert "Starbucks" in pick.reason


def test_judge_ambiguous_declines_returns_none():
    tx, rec_by_id, cand = _ambiguous_setup()
    mock = MockLLMClient(ambiguous_responses=[
        AmbiguousJudgmentResult(chosen_index=0, confidence=0.0, reasoning="genuinely indistinguishable"),
    ])
    assert judge_ambiguous(tx, cand, rec_by_id, client=mock) is None


def test_judge_ambiguous_no_client_returns_none():
    tx, rec_by_id, cand = _ambiguous_setup()
    assert judge_ambiguous(tx, cand, rec_by_id) is None  # stub


def test_apply_ambiguous_judgment_promotes_pick_but_keeps_all():
    """Reconciliation guarantee: the pick is promoted to the front, but
    EVERY candidate stays in the bucket — no receipt silently dropped."""
    tx, rec_by_id, cand = _ambiguous_setup()
    outcome = MatchOutcome(ambiguous=list(cand))
    mock = MockLLMClient(ambiguous_responses=[
        AmbiguousJudgmentResult(chosen_index=2, confidence=0.82, reasoning="Starbucks"),
    ])

    _apply_ambiguous_judgment(outcome, {tx.transaction_id: tx}, rec_by_id, mock)

    # Both receipts still present (guarantee), pick is first.
    assert {m.document_id for m in outcome.ambiguous} == {"r1", "r2"}
    assert len(outcome.ambiguous) == 2
    assert outcome.ambiguous[0].document_id == "r2"
    assert outcome.ambiguous[0].requires_review is True


def test_apply_ambiguous_judgment_no_client_is_noop():
    tx, rec_by_id, cand = _ambiguous_setup()
    outcome = MatchOutcome(ambiguous=list(cand))
    _apply_ambiguous_judgment(outcome, {tx.transaction_id: tx}, rec_by_id, None)
    assert [m.document_id for m in outcome.ambiguous] == ["r1", "r2"]  # unchanged


# ── WS3 (2026-07-21): the card reaches the model ─────────────────────


def test_fx_judgment_hands_the_model_both_cards():
    """The card is the evidence that separates a real FX pair from an FX
    coincidence, so both systems' records of it have to reach the model:
    the statement's card column and the Zoho payment mode."""
    mock = MockLLMClient()
    tx = _tx(card_last4="3645", vendor_from_statement="ADOBE  *800-833-6687")
    receipt = _receipt(payment_mode="1 - CorpServ 2838/1672 (Chase)")

    judge_fx_match(tx, receipt, client=mock)

    assert mock.last_fx_cards == ("3645", "1 - CorpServ 2838/1672 (Chase)")


def test_fx_judgment_falls_back_to_the_account_id_for_the_card():
    """A statement that names the card in its account id rather than a
    per-row column (the Chase PDF path, whose cycle markers ARE the
    account id) still tells the model which card paid."""
    mock = MockLLMClient()
    judge_fx_match(_tx(account_id="3645"), _receipt(), client=mock)

    tx_card, payment_mode = mock.last_fx_cards
    assert tx_card == "3645"
    assert payment_mode is None


def test_fx_judgment_prompt_carries_the_cards():
    """The prompt template must actually render both cards; a kwarg that
    never reaches the text would be silent."""
    from expense_recon.llm.client import _FX_JUDGMENT_PROMPT_TEMPLATE

    prompt = _FX_JUDGMENT_PROMPT_TEMPLATE.format(
        tx_amount="16.23", tx_currency="USD", tx_date="2026-04-29",
        tx_vendor="ADOBE  *800-833-6687",
        receipt_amount="16.20", receipt_currency="EUR",
        receipt_date="2026-05-04", receipt_vendor="(unknown)",
        receipt_reference="(none)",
        tx_card="3645",
        receipt_payment_mode="1 - CorpServ 2838/1672 (Chase)",
    )
    assert "3645" in prompt
    assert "1 - CorpServ 2838/1672 (Chase)" in prompt


def test_apply_judgment_keeps_the_deterministic_sub_scores():
    """The judgment layer builds a fresh Match around the model's verdict.
    The matcher's sub-scores have to survive that, or every FX row reaches
    the workbench scoring 0/100 on amount, date, vendor, and card: the
    review queue cannot sort them and the reviewer cannot see why the pair
    was proposed. The verdict fields still come from the judgment."""
    tx, rec = _tx(), _receipt()
    scored = Match(
        transaction_id=tx.transaction_id,
        document_id=rec.document_id,
        match_type=MatchType.FX_JUDGMENT,
        confidence=0.5,
        reason="placeholder from deterministic layer",
        requires_review=True,
        score=64,
        amount_score=0.71,
        date_score=1.0,
        vendor_score=0.83,
        card_score=1.0,
    )
    outcome = MatchOutcome(judgment_required=[scored])
    mock = MockLLMClient(fx_responses=[
        FxJudgmentResult(
            is_match=True, same_purchase_confidence=0.91,
            implied_rate=1.14, converted_amount=Decimal("112.23"),
            reasoning="match",
        )
    ])

    _apply_judgment(outcome, {tx.transaction_id: tx}, {rec.document_id: rec}, mock)

    judged = outcome.judgment_required[0]
    assert judged.confidence == 0.91          # the verdict
    assert judged.score == 64                 # the matcher's work, preserved
    assert judged.amount_score == 0.71
    assert judged.date_score == 1.0
    assert judged.vendor_score == 0.83
    assert judged.card_score == 1.0
