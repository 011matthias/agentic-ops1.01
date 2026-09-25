"""Front 5 (2026-09-25): pairs in Reconciled that still need a click.

Step 1, the FX judge judges the tool's evidence. Live July and August 2026
held 13 model verdicts: the prompt asked the model to estimate the exchange
rate itself, and it printed a conversion off tenfold, three inverse rates,
and "card numbers differ" where the tool's own card evidence read unknown.
Now the judge is handed the matcher's reference conversion, the card verdict
and the merchant agreement, the prompt says the rate is given, and the cache
key carries the prompt version so no verdict bought under the old prompt is
read back. A pair whose own evidence is clean and that went to judgment only
because a look-alike exists is not a question for the model: no call.

Every test drives the caller the change touched (`cli._apply_judgment`, or
the hosted re-match through the app), not only the helper it added.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.cli import _apply_judgment
from expense_recon.llm.client import FxJudgmentResult, MockLLMClient
from expense_recon.matching.deterministic import (
    UNIQUENESS_RIVAL_REVIEW,
    MatchingConfig,
    match_month,
)
from expense_recon.matching.types import MatchType, Receipt, Transaction

DAILY = {
    d: {"USD": "1.1660"}
    for d in ("2026-07-16", "2026-07-17", "2026-07-18", "2026-07-19", "2026-07-20")
}


def _cfg() -> MatchingConfig:
    return MatchingConfig.from_dict({"fx_daily_rates": DAILY})


def _charge(tx_id, day, amount, vendor, card="9693"):
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="corpserv",
        account_id=card,
        transaction_date=day,
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
        card_last4=card,
    )


def _receipt(doc, day, total, vendor, card="9693"):
    return Receipt(
        document_id=doc,
        legal_entity_id="corpserv",
        detected_vendor=vendor,
        detected_date=day,
        detected_total=Decimal(total),
        detected_currency="EUR",
        payment_mode=f"VISA ending {card}" if card else None,
    )


def _verdict(p=0.4):
    return FxJudgmentResult(
        is_match=p >= 0.5,
        same_purchase_confidence=p,
        implied_rate=0.018,
        converted_amount=Decimal("1.00"),
        reasoning="model text",
    )


def _judge(charges, receipts, mock, cfg=None):
    cfg = cfg or _cfg()
    out = match_month(charges, receipts, cfg)
    _apply_judgment(
        out,
        {t.transaction_id: t for t in charges},
        {r.document_id: r for r in receipts},
        mock,
        suggest_floor=cfg.fx_judgment_suggest_floor,
        cfg=cfg,
    )
    return out


def _fx_calls(mock) -> int:
    return sum(1 for c in mock.calls if c[0] == "judge_fx_match")


# ── the twins: clean evidence, a look-alike, no call ───────────────────


def _twins():
    charges = [
        _charge("t18", date(2026, 7, 18), "9.80", "POSTO SANTOS"),
        _charge("t19", date(2026, 7, 19), "9.80", "POSTO SANTOS"),
    ]
    receipts = [
        _receipt("r18", date(2026, 7, 18), "8.40", "Posto Santos"),
        _receipt("r19", date(2026, 7, 19), "8.40", "Posto Santos"),
    ]
    return charges, receipts


def test_a_clean_pair_held_only_by_a_look_alike_spends_no_model_call():
    charges, receipts = _twins()
    mock = MockLLMClient(fx_responses=[_verdict(0.85)] * 8)
    out = _judge(charges, receipts, mock)

    assert _fx_calls(mock) == 0
    held = [m for m in out.judgment_required if m.transaction_id == "t18"]
    assert held, "the twin pair must stay in review, not vanish"
    m = held[0]
    assert m.match_type is MatchType.FX_JUDGMENT
    assert m.requires_review
    assert m.review_code == UNIQUENESS_RIVAL_REVIEW
    # The reason names the rival, so the reviewer knows which two compete.
    assert "POSTO SANTOS 9.80 USD on 2026-07-19" in m.reason or "Posto Santos 8.40" in m.reason


def test_a_look_alike_with_a_weak_merchant_still_goes_to_the_model_with_evidence():
    charges = [
        _charge("s1", date(2026, 7, 18), "10.23", "SUPERMEC SAO JOSE"),
        _charge("s2", date(2026, 7, 19), "10.25", "SUPERMEC SAO JOSE"),
    ]
    receipts = [_receipt("m1", date(2026, 7, 18), "8.80", "Marinho Supermercado Ltda")]
    mock = MockLLMClient(fx_responses=[_verdict(0.4)] * 8)
    out = _judge(charges, receipts, mock)

    assert _fx_calls(mock) >= 1
    ev = mock.last_fx_evidence
    assert ev is not None
    assert ev.reference_rate == Decimal("1.166000")
    assert ev.reference_rate_source == "opentickers_day"
    assert ev.reference_gap_band == "match"
    assert ev.cards_differ is False  # printed 9693 on both sides
    assert ev.vendor_pct is not None and ev.vendor_pct < 75
    prompt = mock.last_fx_prompt
    assert "best estimate" not in prompt
    assert "do not estimate your own" in prompt
    assert "1.166000" in prompt
    # The verdict keeps why the matcher sent it and prints the TOOL's
    # conversion, never the model's tenfold-off 1.00.
    judged = [m for m in out.judgment_required if m.document_id == "m1"]
    assert judged and judged[0].review_code == UNIQUENESS_RIVAL_REVIEW
    assert "at the tool's rate 1.166000" in judged[0].reason
    assert "~1.00" not in judged[0].reason


def test_an_unknown_card_reaches_the_model_as_unknown_not_as_a_disagreement():
    charges = [
        _charge("f1", date(2026, 7, 18), "10.23", "SUPERMERCADO FENIX"),
        _charge("f2", date(2026, 7, 19), "10.25", "SUPERMERCADO FENIX"),
    ]
    receipts = [_receipt("x1", date(2026, 7, 18), "8.80", "Fenix", card=None)]
    mock = MockLLMClient(fx_responses=[_verdict(0.4)] * 8)
    _judge(charges, receipts, mock)

    assert mock.last_fx_evidence.cards_differ is None
    assert "unknown, which is not a disagreement" in mock.last_fx_prompt


def test_a_missing_total_reaches_the_model_as_unknown_not_zero():
    from expense_recon.llm.client import render_fx_judgment_prompt

    prompt = render_fx_judgment_prompt(
        tx_amount=Decimal("9.80"), tx_currency="USD", tx_date="2026-07-18",
        tx_vendor="X", receipt_amount=None, receipt_currency="EUR",
        receipt_date=None, receipt_vendor=None, receipt_reference=None,
    )
    assert "amount: (unknown) EUR" in prompt
    assert "none available" in prompt


def test_the_hosted_attach_hands_the_judge_the_tools_evidence(tmp_path, monkeypatch):
    """Route level: a statement attached through the app reaches the judge
    with the tool's evidence and the new prompt, not the rate-guessing one."""
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import tests.test_rematch_judgment_cache as rj
    from expense_recon.web.app import create_app

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = rj._mock([rj._eur_receipt()])
    rj._wire(monkeypatch, mock)
    with TestClient(create_app(tmp_path)) as client:
        client._data_root = tmp_path
        batch_id = rj._create_batch(client)
        rj._attach(client, batch_id)
    assert rj._fx_calls(mock) > 0
    assert mock.last_fx_evidence is not None
    assert mock.last_fx_evidence.receipt_card == "none"
    assert "best estimate" not in mock.last_fx_prompt
    assert "What the tool already established" in mock.last_fx_prompt


# ── the cache key carries the prompt version (through the re-match) ────


def test_a_prompt_version_bump_makes_the_rematch_re_judge(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from expense_recon.web import judgment_cache
    from expense_recon.web.judgment_cache import JudgmentCache

    kwargs = {"tx_amount": Decimal("9.80"), "tx_currency": "USD"}
    before = judgment_cache.call_key("judge_fx_match", kwargs, "m")
    amb_before = judgment_cache.call_key("judge_ambiguous", kwargs, "m")
    monkeypatch.setattr("expense_recon.llm.client.FX_JUDGMENT_PROMPT_VERSION", "999")
    assert judgment_cache.call_key("judge_fx_match", kwargs, "m") != before
    # The ambiguous judge's prompt did not change: its stored keys hold.
    assert judgment_cache.call_key("judge_ambiguous", kwargs, "m") == amb_before

    # And through the caching client the judgment layer calls.
    charges = [
        _charge("s1", date(2026, 7, 18), "10.23", "SUPERMEC SAO JOSE"),
        _charge("s2", date(2026, 7, 19), "10.25", "SUPERMEC SAO JOSE"),
    ]
    receipts = [_receipt("m1", date(2026, 7, 18), "8.80", "Marinho Supermercado Ltda")]
    mock = MockLLMClient(fx_responses=[_verdict(0.4)] * 16)
    cache = JudgmentCache(model="m")
    _judge(charges, receipts, cache.wrap(mock))
    bought = _fx_calls(mock)
    assert bought >= 1
    _judge(charges, receipts, cache.wrap(mock))
    assert _fx_calls(mock) == bought, "same prompt version: answered from cache"
    monkeypatch.setattr("expense_recon.llm.client.FX_JUDGMENT_PROMPT_VERSION", "1000")
    _judge(charges, receipts, cache.wrap(mock))
    assert _fx_calls(mock) == 2 * bought, "a new prompt version must re-judge"
