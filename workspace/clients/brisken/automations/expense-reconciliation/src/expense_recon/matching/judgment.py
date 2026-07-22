"""LLM judgment layer — v2 spec §15.2.

Invoked only when the deterministic layer returns FX_JUDGMENT,
AMBIGUOUS, or POSSIBLE. The common USD-on-USD case never reaches this
module.

`judge_fx_match` is wired to the provider-agnostic `LLMClient` (slice 2,
D1b). With a client, it asks the model to FX-convert the receipt into
the transaction currency and judge whether the two are the same
purchase, combining the converted amount with vendor / reference / date
signal. Without a client it returns the slice-1 stub Match, still
flagged for review.

Two invariants hold regardless of the verdict:

* **FX judgments always carry `requires_review=True`.** The FX rate is
  an approximation (the authoritative rate source is §38-TBD) and the
  call posture is "review everything for the first months"
  (call-outcomes D2).
* **The reconciliation guarantee (v2 spec §25.5) is preserved.** The
  entry stays in `judgment_required` whatever the verdict; a rejected
  candidate is surfaced for Chris to reject, never silently dropped.

`judge_ambiguous` remains a stub (BLUEPRINT 2.4) — D1b is FX only.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from ..llm.client import AmbiguousCandidate, LLMClient
from .deterministic import (
    MatchingConfig,
    _blend_score,
    _card_score,
    vendor_similarity,
)
from .types import Match, MatchType, Receipt, Transaction


STUB_REASON = (
    "[STUB] LLM judgment layer not wired for this run (no LLM client). "
    "Human review required."
)


def judge_fx_match(
    tx: Transaction,
    receipt: Receipt,
    *,
    client: LLMClient | None = None,
) -> Match:
    """Score an FX-mismatch candidate pair (v2 spec §15.2).

    With an `LLMClient`, returns a Match carrying the model's
    same-purchase confidence and a human-readable reason that includes
    the approximate converted amount, the implied rate, and the model's
    reasoning. Without a client, returns the slice-1 stub Match.

    The returned Match keeps `match_type=FX_JUDGMENT` so it stays in the
    `judgment_required` bucket, and `requires_review=True` always.
    """
    if client is None:
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.FX_JUDGMENT,
            confidence=0.5,
            reason=STUB_REASON,
            requires_review=True,
        )

    result = client.judge_fx_match(
        tx_amount=tx.amount,
        tx_currency=tx.transaction_currency,
        tx_date=tx.transaction_date.isoformat(),
        tx_vendor=tx.vendor_from_statement,
        receipt_amount=(
            receipt.detected_total
            if receipt.detected_total is not None
            else Decimal("0")
        ),
        receipt_currency=receipt.detected_currency or "",
        receipt_date=(
            receipt.detected_date.isoformat() if receipt.detected_date else None
        ),
        receipt_vendor=receipt.detected_vendor,
        receipt_reference=receipt.detected_reference,
        # WS3 (2026-07-21): the card is the signal that separates a real FX
        # pair from an FX coincidence. A USD software subscription and a EUR
        # meal receipt can sit inside the same implied-rate band by accident
        # (ADOBE $16.23 against a EUR 16.20 lunch on the 01-05-2026 corpserv
        # month), and amount alone cannot tell them apart. The bank's card
        # column and Zoho's payment mode are two independent records of who
        # paid, so handing both to the model lets it reject the pair on the
        # evidence rather than on vendor-name intuition.
        tx_card=tx.card_last4 or tx.account_id,
        receipt_payment_mode=receipt.payment_mode,
    )

    return Match(
        transaction_id=tx.transaction_id,
        document_id=receipt.document_id,
        match_type=MatchType.FX_JUDGMENT,
        confidence=result.same_purchase_confidence,
        reason=_fx_reason(tx, receipt, result),
        requires_review=True,
    )


def _fx_reason(tx: Transaction, receipt: Receipt, result: Any) -> str:
    """Human-readable judgment string for the review report."""
    verdict = "likely same purchase" if result.is_match else "likely NOT the same purchase"
    parts = [
        f"FX judgment: {verdict} "
        f"(p={result.same_purchase_confidence:.2f})."
    ]
    if result.converted_amount is not None:
        rate = (
            f" at ~{result.implied_rate}"
            if result.implied_rate is not None
            else ""
        )
        parts.append(
            f"~{result.converted_amount} {tx.transaction_currency} from "
            f"{receipt.detected_total} {receipt.detected_currency}{rate} "
            f"(approx rate, review)."
        )
    if result.reasoning:
        parts.append(result.reasoning)
    return " ".join(parts)


def judge_unmatched(
    tx: Transaction,
    receipts: list[Receipt],
    *,
    client: LLMClient,
    cfg: MatchingConfig,
    top_k: int,
    date_window_days: int,
    min_confidence: float,
) -> tuple[Match | None, int]:
    """Second-chance judgment for a transaction the matcher left unmatched
    (WS3, 2026-07-21). Returns `(accepted_match_or_None, llm_calls_used)`.

    The deterministic FX path drops a cross-currency pair whose implied
    rate falls outside the plausibility band for that currency pair. The
    band is deliberately wide, but it is still a fixed window, so a
    genuine purchase with an unusual DCC markup plus a large tip can land
    outside it and the receipt goes unmatched with no trace of why. This
    pass asks the model about the few most plausible leftovers instead.

    Three bounds keep it cheap and safe, in this order:

    * **Shortlist** — same legal entity, currency actually different (a
      same-currency pair that failed the amount test is not an FX rescue,
      it is a different purchase), no card contradiction, and inside the
      date window. Then the best `top_k` by date proximity, vendor
      similarity, card agreement.
    * **Threshold** — the model's own same-purchase confidence must reach
      `min_confidence`; the first candidate that clears it wins, in
      shortlist order.
    * **Bucket** — the caller only ever moves an id from `unmatched` to
      `judgment_required`. Nothing is auto-matched, everything found here
      is review-flagged, and the reconciliation guarantee is untouched.
    """
    shortlist = _second_chance_shortlist(
        tx, receipts, cfg, top_k=top_k, date_window_days=date_window_days
    )
    calls = 0
    for receipt in shortlist:
        judged = judge_fx_match(tx, receipt, client=client)
        calls += 1
        if judged.confidence < min_confidence:
            continue
        return _with_second_chance_scores(judged, tx, receipt, cfg), calls
    return None, calls


def _date_distance(tx: Transaction, receipt: Receipt) -> int | None:
    """Days between the receipt and the nearest of the charge's transaction
    / posting date, or None when the receipt carries no date."""
    if receipt.detected_date is None:
        return None
    candidate_dates = [tx.transaction_date]
    if tx.posting_date and tx.posting_date != tx.transaction_date:
        candidate_dates.append(tx.posting_date)
    return min(abs((receipt.detected_date - d).days) for d in candidate_dates)


def _second_chance_shortlist(
    tx: Transaction,
    receipts: list[Receipt],
    cfg: MatchingConfig,
    *,
    top_k: int,
    date_window_days: int,
) -> list[Receipt]:
    """The bounded candidate set for `judge_unmatched` (see its docstring
    for why each bound is there). Pure and deterministic — no LLM call —
    so the bounding can be tested without a model."""
    scored: list[tuple[tuple[float, float, float, str], Receipt]] = []
    for receipt in receipts:
        if receipt.legal_entity_id != tx.legal_entity_id:
            continue
        if receipt.detected_currency is None or receipt.detected_total is None:
            continue
        if receipt.detected_currency == tx.transaction_currency:
            continue
        if _card_score(tx, receipt) <= 0.0:
            continue  # the two systems name different cards
        distance = _date_distance(tx, receipt)
        if distance is None or distance > date_window_days:
            continue
        scored.append(
            (
                (
                    -float(distance),
                    vendor_similarity(
                        tx.vendor_from_statement, receipt.detected_vendor
                    ),
                    _card_score(tx, receipt),
                    # Document id last so an exact tie orders the same way
                    # on every run; a shortlist that reshuffles would make
                    # the LLM spend non-reproducible.
                    receipt.document_id,
                ),
                receipt,
            )
        )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [receipt for _, receipt in scored[:top_k]]


def _with_second_chance_scores(
    match: Match, tx: Transaction, receipt: Receipt, cfg: MatchingConfig
) -> Match:
    """Give a second-chance match the same sub-scores every other Match
    carries, so the workbench can sort and explain it.

    `amount_score` is 0.0 on purpose: the deterministic amount test is
    exactly what this pair failed, and the model's verdict lives in
    `confidence` and the reason string. The low blend sorts these to the
    top of the review queue, which is where the riskiest pairs belong.
    """
    distance = _date_distance(tx, receipt)
    date_score = (
        0.0 if distance is None
        else max(0.0, 1.0 - distance / max(1, cfg.fx_date_window_days))
    )
    vendor_score = vendor_similarity(
        tx.vendor_from_statement, receipt.detected_vendor
    )
    card_score = _card_score(tx, receipt)
    return replace(
        match,
        score=_blend_score(0.0, date_score, vendor_score, card_score, cfg),
        amount_score=0.0,
        date_score=date_score,
        vendor_score=vendor_score,
        card_score=card_score,
    )


def judge_ambiguous(
    tx: Transaction,
    candidates: list[Match],
    receipts_by_id: dict[str, Receipt],
    *,
    client: LLMClient | None = None,
) -> Match | None:
    """Pick the best of several tied candidates for one transaction.

    With an `LLMClient`, asks the model to break the tie on vendor /
    reference / date signal and returns the chosen candidate Match,
    annotated with the model's reasoning and `requires_review=True`.
    Returns None when there is no client (stub) or when the model
    declines to pick (`chosen_index=0`) — in which case the caller
    leaves every candidate in the ambiguous bucket for human review.

    This never drops a candidate; the caller keeps all of them and
    only promotes the pick to the front (reconciliation guarantee).
    """
    if client is None or not candidates:
        return None

    cand_inputs = [
        AmbiguousCandidate(
            document_id=m.document_id,
            amount=(rec.detected_total if (rec := receipts_by_id.get(m.document_id)) else None),
            currency=rec.detected_currency if rec else None,
            date=rec.detected_date.isoformat() if rec and rec.detected_date else None,
            vendor=rec.detected_vendor if rec else None,
            reference=rec.detected_reference if rec else None,
        )
        for m in candidates
    ]

    result = client.judge_ambiguous(
        tx_amount=tx.amount,
        tx_currency=tx.transaction_currency,
        tx_date=tx.transaction_date.isoformat(),
        tx_vendor=tx.vendor_from_statement,
        candidates=cand_inputs,
    )

    if not (1 <= result.chosen_index <= len(candidates)):
        return None  # model declined; tie stands

    chosen = candidates[result.chosen_index - 1]
    return replace(
        chosen,
        match_type=MatchType.AMBIGUOUS,
        confidence=result.confidence,
        reason=(
            f"Ambiguous pick (p={result.confidence:.2f}): "
            f"{result.reasoning}" if result.reasoning
            else f"Ambiguous pick (p={result.confidence:.2f})."
        ),
        requires_review=True,
    )
