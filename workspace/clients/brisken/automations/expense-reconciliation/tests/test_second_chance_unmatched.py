"""Second-chance LLM pass over the unmatched (WS3, 2026-07-21).

The deterministic FX path drops a cross-currency pair whose implied rate
falls outside the plausibility band for that currency pair. The band is
wide but fixed, so a real purchase with an unusual DCC markup plus a big
tip lands outside it and the receipt goes unmatched with no trace of why.

This pass asks the model about a bounded shortlist of leftovers. It ships
OFF, it never auto-matches, and it only ever moves an id from `unmatched`
to `judgment_required` — so the reconciliation guarantee (v2 spec §25.5)
holds whether it runs or not.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.cli import _apply_unmatched_judgment
from expense_recon.llm.client import FxJudgmentResult, MockLLMClient
from expense_recon.matching.deterministic import MatchingConfig
from expense_recon.matching.judgment import _second_chance_shortlist
from expense_recon.matching.types import MatchOutcome, Receipt, Transaction

LE = "brisken-corpserv"
ON = {"matching": {"llm_second_pass_unmatched": True}}


def _tx(tid="t1", amount="120.00", *, card="2838", txdate=date(2026, 5, 4),
        currency="USD", vendor="RISTORANTE ROMA", entity=LE):
    return Transaction(
        transaction_id=tid, legal_entity_id=entity,
        account_id="chase-2838-family", transaction_date=txdate,
        posting_date=None, amount=Decimal(amount),
        transaction_currency=currency, account_card_currency="USD",
        vendor_from_statement=vendor, card_last4=card,
    )


def _receipt(rid="r1", amount="80.00", *, currency="EUR",
             rdate=date(2026, 5, 4), payment_mode="1 - CorpServ 2838/1672 (Chase)",
             vendor="Ristorante Roma", entity=LE):
    return Receipt(
        document_id=rid, legal_entity_id=entity, detected_date=rdate,
        detected_total=Decimal(amount) if amount else None,
        detected_currency=currency, detected_vendor=vendor,
        detected_reference=None, payment_mode=payment_mode,
    )


def _outcome(tx_ids, doc_ids) -> MatchOutcome:
    out = MatchOutcome()
    out.unmatched_transactions.extend(tx_ids)
    out.unmatched_receipts.extend(doc_ids)
    return out


def _confident(p=0.82) -> FxJudgmentResult:
    return FxJudgmentResult(
        is_match=True, same_purchase_confidence=p,
        implied_rate=1.5, converted_amount=Decimal("120.00"),
        reasoning="Same card, same day, plausible rate with a large tip.",
    )


def _doubtful(p=0.2) -> FxJudgmentResult:
    return FxJudgmentResult(
        is_match=False, same_purchase_confidence=p,
        implied_rate=None, converted_amount=None,
        reasoning="Different cards; a subscription is not a restaurant bill.",
    )


# ── the bucket move ──────────────────────────────────────────────────


def test_confident_verdict_moves_unmatched_into_judgment():
    tx, receipt = _tx(), _receipt()
    out = _outcome([tx.transaction_id], [receipt.document_id])
    mock = MockLLMClient(fx_responses=[_confident()])

    _apply_unmatched_judgment(
        out, [tx], [receipt], mock, MatchingConfig(), ON
    )

    assert out.unmatched_transactions == []
    assert out.unmatched_receipts == []
    assert len(out.judgment_required) == 1
    rescued = out.judgment_required[0]
    assert rescued.transaction_id == "t1"
    assert rescued.document_id == "r1"
    # Never auto-matched: a rescue is a review item, not a decision.
    assert not out.matches
    assert rescued.requires_review


def test_doubtful_verdict_leaves_both_where_they_were():
    tx, receipt = _tx(), _receipt()
    out = _outcome([tx.transaction_id], [receipt.document_id])
    mock = MockLLMClient(fx_responses=[_doubtful()])

    _apply_unmatched_judgment(
        out, [tx], [receipt], mock, MatchingConfig(), ON
    )

    assert out.unmatched_transactions == ["t1"]
    assert out.unmatched_receipts == ["r1"]
    assert not out.judgment_required


def test_pass_is_off_by_default():
    """No `matching` block at all: not one call, nothing moves."""
    tx, receipt = _tx(), _receipt()
    out = _outcome([tx.transaction_id], [receipt.document_id])
    mock = MockLLMClient(fx_responses=[_confident()])

    _apply_unmatched_judgment(out, [tx], [receipt], mock, MatchingConfig(), {})

    assert mock.calls == []
    assert out.unmatched_transactions == ["t1"]
    assert not out.judgment_required


def test_no_client_is_a_no_op():
    tx, receipt = _tx(), _receipt()
    out = _outcome([tx.transaction_id], [receipt.document_id])

    _apply_unmatched_judgment(out, [tx], [receipt], None, MatchingConfig(), ON)

    assert out.unmatched_transactions == ["t1"]
    assert not out.judgment_required


def test_a_receipt_is_claimed_by_at_most_one_transaction():
    """Two charges, one plausible receipt, and a model that says yes to
    everything. The first claims it; the second must not double-bind."""
    txs = [_tx("t1"), _tx("t2", amount="121.00")]
    receipt = _receipt()
    out = _outcome(["t1", "t2"], ["r1"])
    mock = MockLLMClient(fx_responses=[_confident(), _confident()])

    _apply_unmatched_judgment(out, txs, [receipt], mock, MatchingConfig(), ON)

    assert [m.document_id for m in out.judgment_required] == ["r1"]
    assert out.unmatched_transactions == ["t2"]
    assert out.unmatched_receipts == []


def test_rescued_match_carries_sub_scores_for_the_workbench():
    """The amount sub-score is 0.0 on purpose — the deterministic amount
    test is exactly what this pair failed — so the blend sorts the riskiest
    rescues to the top of the review queue."""
    tx, receipt = _tx(), _receipt()
    out = _outcome([tx.transaction_id], [receipt.document_id])

    _apply_unmatched_judgment(
        out, [tx], [receipt], MockLLMClient(fx_responses=[_confident()]),
        MatchingConfig(), ON,
    )

    rescued = out.judgment_required[0]
    assert rescued.amount_score == 0.0
    assert rescued.date_score == 1.0
    assert rescued.card_score == 1.0
    assert rescued.vendor_score > 0.5
    assert rescued.score < 50


# ── the bounds ───────────────────────────────────────────────────────


def test_shortlist_excludes_other_entities_wrong_cards_and_far_dates():
    tx = _tx()
    keep = _receipt("keep")
    shortlist = _second_chance_shortlist(
        tx,
        [
            keep,
            _receipt("other-entity", entity="brisken-us"),
            _receipt("wrong-card", payment_mode="1 - CorpServ 3645/1672 (Chase)"),
            _receipt("far-date", rdate=date(2026, 6, 30)),
            _receipt("same-currency", currency="USD"),
            _receipt("no-amount", amount=None),
        ],
        MatchingConfig(),
        top_k=10,
        date_window_days=5,
    )
    assert [r.document_id for r in shortlist] == ["keep"]


def test_shortlist_keeps_a_receipt_with_no_payment_mode():
    """Unknown card is not disagreement — the receipt stays eligible."""
    shortlist = _second_chance_shortlist(
        _tx(), [_receipt("silent", payment_mode=None)],
        MatchingConfig(), top_k=10, date_window_days=5,
    )
    assert [r.document_id for r in shortlist] == ["silent"]


def test_shortlist_is_capped_and_ordered_by_proximity():
    tx = _tx()
    shortlist = _second_chance_shortlist(
        tx,
        [
            _receipt("d3", rdate=date(2026, 5, 7)),
            _receipt("d0", rdate=date(2026, 5, 4)),
            _receipt("d1", rdate=date(2026, 5, 5)),
        ],
        MatchingConfig(), top_k=2, date_window_days=5,
    )
    assert [r.document_id for r in shortlist] == ["d0", "d1"]


def test_call_budget_caps_the_spend():
    """Ten hopeless charges against a model that rejects everything: the
    budget stops the pass rather than paying for every pair."""
    txs = [_tx(f"t{i}") for i in range(10)]
    receipts = [_receipt(f"r{i}") for i in range(10)]
    out = _outcome([t.transaction_id for t in txs], [r.document_id for r in receipts])
    mock = MockLLMClient(fx_responses=[_doubtful() for _ in range(100)])

    _apply_unmatched_judgment(
        out, txs, receipts, mock, MatchingConfig(),
        {"matching": {
            "llm_second_pass_unmatched": True,
            "llm_second_pass_top_k": 3,
            "llm_second_pass_max_calls": 5,
        }},
    )

    assert len(mock.calls) <= 6  # the in-flight transaction finishes its top-K
    assert out.unmatched_transactions == [t.transaction_id for t in txs]
