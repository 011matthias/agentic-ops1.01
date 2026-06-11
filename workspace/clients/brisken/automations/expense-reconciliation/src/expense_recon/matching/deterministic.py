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

from dataclasses import dataclass, field
from collections.abc import Mapping
from decimal import Decimal

from .types import Match, MatchOutcome, MatchType, Receipt, Transaction


# Plausible implied-rate bands per (receipt_ccy, tx_ccy), where the
# implied rate is `tx.amount / receipt.detected_total`. These are NOT
# FX prices; they are wide plausibility windows whose only job is to
# stop a USD transaction from pairing with a foreign receipt it could
# not possibly be (the O(N×M) cross-product, ANNEALING A1). A band is
# wide on purpose: it must absorb DCC markup (observed up to 12.8% on
# real Brisken receipts) plus intra-month rate drift, while still
# rejecting a coincidental amount collision at a wrong rate.
#
# Calibrated 2026-06-11 against 98 real BRL/EUR->USD pairs (3b run):
# observed BRL->USD implied rates ran ~0.17-0.215 (DCC pushed the top
# end), EUR->USD ~1.16-1.25. Bands below pad generously beyond both.
_DEFAULT_FX_RATE_BANDS: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    ("BRL", "USD"): (Decimal("0.15"), Decimal("0.24")),
    ("EUR", "USD"): (Decimal("1.00"), Decimal("1.30")),
}


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

    # ── FX candidate gating (3.7 / ANNEALING A1) ───────────────────
    # A currency-mismatch pair is only emitted as FX_JUDGMENT when it
    # is plausible: within `fx_date_window_days` AND (for a profiled
    # currency pair) inside the implied-rate band. Foreign charges can
    # post with more delay than same-currency ones, so this window is
    # independent of date_probable_window_days. An UNPROFILED pair
    # (no band entry) is gated on date only and still emitted — never
    # silently dropped, preserving the reconciliation guarantee for
    # currencies we have not yet measured.
    fx_date_window_days: int = 5
    fx_rate_bands: Mapping[tuple[str, str], tuple[Decimal, Decimal]] = field(
        default_factory=lambda: dict(_DEFAULT_FX_RATE_BANDS)
    )

    def fx_band(
        self, from_ccy: str, to_ccy: str
    ) -> tuple[Decimal, Decimal] | None:
        """Plausible implied-rate band for receipt->transaction currency,
        or None if the pair is unprofiled."""
        return self.fx_rate_bands.get((from_ccy, to_ccy))


def match_one(
    tx: Transaction, receipt: Receipt, cfg: MatchingConfig
) -> Match | None:
    """Score a single (transaction, receipt) candidate pair.

    Returns None when the candidate does not pass the minimum bar
    (no plausible amount or date relationship).
    """
    # Currency mismatch -> FX judgment layer, but ONLY for plausible
    # pairs. This is the EUR-on-USD-card case Dirk specified on the
    # call (call-outcomes "Matching approach"); the amount won't match
    # 1:1, so vendor / reference / FX reasoning is the LLM's job.
    #
    # 3.7 / ANNEALING A1: gate emission on date proximity AND (for a
    # profiled currency pair) implied-rate plausibility. Without this
    # gate every USD transaction pairs with every foreign receipt; the
    # 2026-06-11 calibration measured 5,064 such junk pairs in one
    # 119-transaction month (~50x the real FX-receipt count). The gate
    # keeps the real pairs and drops the cross-product. FX still goes
    # to the LLM (FX_JUDGMENT); we are filtering candidates, not
    # auto-resolving them here.
    if (
        receipt.detected_currency
        and receipt.detected_currency != tx.transaction_currency
    ):
        # Need a receipt amount + date to judge plausibility. Missing
        # either => no deterministic FX candidate; the receipt still
        # surfaces in `unmatched_receipts` for review (guarantee held).
        if receipt.detected_total is None or receipt.detected_date is None:
            return None
        if tx.amount <= 0 or receipt.detected_total <= 0:
            return None

        candidate_dates = [tx.transaction_date]
        if tx.posting_date and tx.posting_date != tx.transaction_date:
            candidate_dates.append(tx.posting_date)
        date_diff = min(
            abs((receipt.detected_date - d).days) for d in candidate_dates
        )
        if date_diff > cfg.fx_date_window_days:
            return None

        implied_rate = tx.amount / receipt.detected_total
        band = cfg.fx_band(receipt.detected_currency, tx.transaction_currency)
        if band is not None:
            lo, hi = band
            if not (lo <= implied_rate <= hi):
                # Implausible rate for this currency pair -> not the
                # same purchase. Drop the candidate.
                return None
            rate_note = (
                f"implied rate {implied_rate:.4f} within "
                f"{receipt.detected_currency}->{tx.transaction_currency} "
                f"band [{lo}, {hi}]"
            )
        else:
            # Unprofiled currency pair: keep the candidate (date-gated
            # only) so we never lose a real match for a currency we
            # have not measured. Add a band entry to tighten later.
            rate_note = (
                f"unprofiled {receipt.detected_currency}->"
                f"{tx.transaction_currency} pair; date-gated only"
            )

        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.FX_JUDGMENT,
            confidence=0.5,  # placeholder; LLM layer revises
            reason=(
                f"Currency mismatch: receipt {receipt.detected_currency} "
                f"vs transaction {tx.transaction_currency}, "
                f"date diff {date_diff}d, {rate_note}. Requires FX judgment."
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
