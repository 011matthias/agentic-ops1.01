"""Deterministic matching engine — v2 spec §15.1.

Matches receipts to transactions using amount, date, currency, and
account signals. The common case (USD card + USD receipt, same date,
same amount) returns a high-confidence match without involving the
LLM. The FX case (different currencies) short-circuits to
`judgment_required` for the LLM layer to handle.

Dirk's call directive (call-outcomes "Matching approach"): "does not
want AI where a deterministic match works." The deterministic layer
is the first line; LLM is invoked only when this layer cannot
resolve.

The reconciliation guarantee (v2 spec §25.5) is preserved: every
input transaction lands in exactly one of `matches`,
`judgment_required`, `ambiguous`, or `unmatched_transactions`. No
silent drops.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .types import Match, MatchOutcome, MatchType, Receipt, Transaction


@dataclass(frozen=True)
class MatchingConfig:
    """Configurable tolerances. Starting values; exact thresholds
    TBD per v2 spec §15.5 / §38 — to be tuned with Chris against
    real Brisken data."""

    amount_exact_tolerance: Decimal = Decimal("0.00")
    # Probable-tolerance default covers restaurant tips (typically 15-20% in US)
    # and small service fees. Probable matches require review anyway, so being
    # slightly loose here just means Chris glances at a few extras; being too
    # tight means valid tip-cases fall into `unmatched` and she hunts manually.
    # Final value to tune with Chris against real Brisken data (v2 spec §15.5).
    amount_probable_tolerance_pct: Decimal = Decimal("0.20")
    date_exact_window_days: int = 1                            # purchase vs posting day
    date_probable_window_days: int = 5                         # weekend / bank delay
    high_confidence: float = 0.99
    probable_confidence: float = 0.85
    possible_confidence: float = 0.60


def match_one(
    tx: Transaction, receipt: Receipt, cfg: MatchingConfig
) -> Match | None:
    """Score a single (transaction, receipt) candidate pair.

    Returns None when the candidate does not pass the minimum bar
    (no plausible amount or date relationship).
    """
    # Currency mismatch -> short-circuit to FX judgment layer.
    # This is the EUR-on-USD-card case Dirk specified on the call
    # (call-outcomes "Matching approach"). The amount won't match
    # 1:1; vendor / reference / mock-FX is the LLM's job, not this
    # layer's.
    if (
        receipt.detected_currency
        and receipt.detected_currency != tx.transaction_currency
    ):
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.FX_JUDGMENT,
            confidence=0.5,  # placeholder; LLM layer revises
            reason=(
                f"Currency mismatch: receipt {receipt.detected_currency} "
                f"vs transaction {tx.transaction_currency}. "
                f"Requires FX judgment."
            ),
            requires_review=True,
        )

    # No amount on the receipt -> can't deterministically match.
    if receipt.detected_total is None:
        return None

    diff = abs(tx.amount - receipt.detected_total)
    amount_exact = diff <= cfg.amount_exact_tolerance
    amount_probable = (
        not amount_exact
        and tx.amount > 0
        and (diff / tx.amount) <= cfg.amount_probable_tolerance_pct
    )
    if not (amount_exact or amount_probable):
        return None

    if receipt.detected_date is None:
        # Without a receipt date we lean on amount alone — downgrade.
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.POSSIBLE,
            confidence=cfg.possible_confidence,
            reason="Amount match without receipt date; review required.",
            requires_review=True,
        )

    candidate_dates = [tx.transaction_date]
    if tx.posting_date and tx.posting_date != tx.transaction_date:
        candidate_dates.append(tx.posting_date)
    date_diff = min(
        abs((receipt.detected_date - d).days) for d in candidate_dates
    )
    date_exact = date_diff <= cfg.date_exact_window_days
    date_probable = (
        not date_exact and date_diff <= cfg.date_probable_window_days
    )

    if amount_exact and date_exact:
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.EXACT,
            confidence=cfg.high_confidence,
            reason=(
                f"Exact amount, date within {cfg.date_exact_window_days} "
                f"day(s), same currency."
            ),
        )

    if (amount_exact or amount_probable) and (date_exact or date_probable):
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.PROBABLE,
            confidence=cfg.probable_confidence,
            reason=(
                f"Amount diff {diff} (tolerance up to "
                f"{cfg.amount_probable_tolerance_pct * 100}%), "
                f"date diff {date_diff} day(s)."
            ),
            requires_review=True,
        )

    return None


def match_month(
    transactions: list[Transaction],
    receipts: list[Receipt],
    cfg: MatchingConfig | None = None,
) -> MatchOutcome:
    """Match a month of transactions against a folder of receipts.

    Implements v2 spec §15.1. Downstream LLM layer (§15.2) handles
    entries returned in `judgment_required`. Tenant / legal-entity
    scope is enforced at the candidate-pair level.
    """
    cfg = cfg or MatchingConfig()
    outcome = MatchOutcome()

    by_tx: dict[str, list[Match]] = {}
    for tx in transactions:
        for receipt in receipts:
            if receipt.legal_entity_id != tx.legal_entity_id:
                continue  # entity scope per v2 spec §4.2
            scored = match_one(tx, receipt, cfg)
            if scored is not None:
                by_tx.setdefault(tx.transaction_id, []).append(scored)

    matched_receipts: set[str] = set()

    for tx in transactions:
        candidates = by_tx.get(tx.transaction_id, [])
        if not candidates:
            outcome.unmatched_transactions.append(tx.transaction_id)
            continue

        fx_only = [c for c in candidates if c.match_type == MatchType.FX_JUDGMENT]
        determ = [c for c in candidates if c.match_type != MatchType.FX_JUDGMENT]

        if determ:
            determ.sort(key=lambda c: c.confidence, reverse=True)
            best = determ[0]
            tied = [
                c for c in determ
                if abs(c.confidence - best.confidence) < 0.001
            ]
            if len(tied) > 1:
                outcome.ambiguous.extend(tied)
                continue
            outcome.matches.append(best)
            matched_receipts.add(best.document_id)
        elif fx_only:
            outcome.judgment_required.extend(fx_only)

    for r in receipts:
        if r.document_id in matched_receipts:
            continue
        in_judgment = any(
            j.document_id == r.document_id for j in outcome.judgment_required
        )
        in_ambiguous = any(
            a.document_id == r.document_id for a in outcome.ambiguous
        )
        if not (in_judgment or in_ambiguous):
            outcome.unmatched_receipts.append(r.document_id)

    return outcome
