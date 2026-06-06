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
