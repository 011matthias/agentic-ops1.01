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

import difflib
import re
from dataclasses import dataclass, field
from collections.abc import Mapping
from decimal import Decimal

from .types import Match, MatchOutcome, MatchType, Receipt, Transaction


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(s: str) -> str:
    return _NON_ALNUM.sub(" ", s.lower()).strip()


def vendor_similarity(stmt_vendor: str | None, receipt_vendor: str | None) -> float:
    """Fuzzy similarity in [0,1] between a statement vendor string and a
    receipt's detected vendor (ANNEALING A3 / 3.9).

    Robust to the truncation banks apply: the Chase export prints
    "MEGA CENTE CONSTR" for a receipt whose vendor is "Mega Center
    Comercio De Materiais De Construcao Ltda". For each statement token
    we take the best ratio against any receipt token and average over
    statement tokens, so a truncated token ("cente") still scores high
    against its full form ("center"). stdlib `difflib` only — no new
    dependency until month-2 data proves it insufficient. Returns 0.0
    when either side is missing.
    """
    if not stmt_vendor or not receipt_vendor:
        return 0.0
    s_tokens = [t for t in _normalize(stmt_vendor).split() if len(t) >= 3]
    r_tokens = [t for t in _normalize(receipt_vendor).split() if len(t) >= 3]
    if not s_tokens or not r_tokens:
        return difflib.SequenceMatcher(
            None, _normalize(stmt_vendor), _normalize(receipt_vendor)
        ).ratio()
    total = 0.0
    for st in s_tokens:
        total += max(
            difflib.SequenceMatcher(None, st, rt).ratio() for rt in r_tokens
        )
    return total / len(s_tokens)


def reference_match(tx: Transaction, receipt: Receipt) -> bool:
    """True when the receipt's reference number appears in the statement
    text (ANNEALING A3 / 3.9). Chase exports rarely carry a reference,
    so this fires for banks that do (and for future statement formats);
    it is a tie-break bonus, never a gate. 12/13 real receipts carried a
    reference, so the signal exists on the receipt side already."""
    ref = receipt.detected_reference
    if not ref:
        return False
    ref_norm = _NON_ALNUM.sub("", ref.lower())
    if len(ref_norm) < 4:  # too short to be a confident signal
        return False
    haystack = _NON_ALNUM.sub(
        "", f"{tx.vendor_from_statement} {tx.raw_text}".lower()
    )
    return ref_norm in haystack


def _signal(tx: Transaction, receipt: Receipt) -> tuple[float, float]:
    """(reference-match, vendor-similarity) tie-break signal for one
    candidate pair. Reference first because an exact reference hit is a
    stronger identity signal than fuzzy vendor text."""
    return (
        1.0 if reference_match(tx, receipt) else 0.0,
        vendor_similarity(tx.vendor_from_statement, receipt.detected_vendor),
    )


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


@dataclass(frozen=True)
class _Candidate:
    """A scored (tx, receipt) pair plus the 3.9 tie-break signal, used
    by the 3.8 bipartite assignment."""

    match: Match
    is_determ: bool
    ref_signal: float
    vendor_signal: float

    @property
    def sort_key(self) -> tuple[int, float, float, float]:
        # Deterministic matches outrank FX for the same receipt; then
        # confidence; then reference hit; then vendor similarity.
        return (
            1 if self.is_determ else 0,
            self.match.confidence,
            self.ref_signal,
            self.vendor_signal,
        )


def _ties(a: _Candidate, b: _Candidate) -> bool:
    """Two candidates are a genuine tie only when confidence AND both
    3.9 signals match — i.e. the vendor / reference tie-break could not
    separate them. Such a tx is ambiguous; a human picks."""
    return (
        a.is_determ == b.is_determ
        and abs(a.match.confidence - b.match.confidence) < 0.001
        and abs(a.ref_signal - b.ref_signal) < 0.001
        and abs(a.vendor_signal - b.vendor_signal) < 0.01
    )


def match_month(
    transactions: list[Transaction],
    receipts: list[Receipt],
    cfg: MatchingConfig | None = None,
) -> MatchOutcome:
    """Match a month of transactions against a folder of receipts.

    Implements v2 spec §15.1 with the 3.8 bipartite assignment: each
    receipt is assigned to AT MOST ONE transaction (ANNEALING A2 — no
    double-binding). Assignment is greedy by (deterministic-first,
    confidence, reference-hit, vendor-similarity); the 3.9 signal
    (ANNEALING A3) breaks ties and decides which transaction wins a
    contested receipt. Genuine ties (confidence + both signals equal)
    surface as ambiguous for human pick rather than an arbitrary
    assignment.

    Downstream LLM layer (§15.2) handles entries returned in
    `judgment_required`. Tenant / legal-entity scope is enforced at the
    candidate-pair level. The reconciliation guarantee (v2 spec §25.5)
    holds: every transaction lands in exactly one of matches /
    judgment_required / ambiguous / unmatched_transactions.
    """
    cfg = cfg or MatchingConfig()
    outcome = MatchOutcome()

    cands_by_tx: dict[str, list[_Candidate]] = {}
    for tx in transactions:
        for receipt in receipts:
            if receipt.legal_entity_id != tx.legal_entity_id:
                continue  # entity scope per v2 spec §4.2
            scored = match_one(tx, receipt, cfg)
            if scored is None:
                continue
            ref_sig, vendor_sig = _signal(tx, receipt)
            cands_by_tx.setdefault(tx.transaction_id, []).append(
                _Candidate(
                    match=scored,
                    is_determ=scored.match_type != MatchType.FX_JUDGMENT,
                    ref_signal=ref_sig,
                    vendor_signal=vendor_sig,
                )
            )

    # Pass 1: detect genuinely ambiguous transactions (top deterministic
    # candidates tie even after the 3.9 signal). These are excluded from
    # assignment so an arbitrary pick is never made; the receipts they
    # tie over are left free for other transactions.
    ambiguous_tx_ids: set[str] = set()
    for tx_id, cands in cands_by_tx.items():
        determ = [c for c in cands if c.is_determ]
        if not determ:
            continue
        determ.sort(key=lambda c: c.sort_key, reverse=True)
        tied = [c for c in determ if _ties(c, determ[0])]
        if len(tied) > 1:
            ambiguous_tx_ids.add(tx_id)
            outcome.ambiguous.extend(c.match for c in tied)

    # Pass 2: greedy bipartite assignment over all candidates from
    # non-ambiguous transactions, highest sort_key first. A transaction
    # and a receipt are each consumed at most once.
    assignable: list[_Candidate] = [
        c
        for tx_id, cands in cands_by_tx.items()
        if tx_id not in ambiguous_tx_ids
        for c in cands
    ]
    assignable.sort(key=lambda c: c.sort_key, reverse=True)

    assigned_tx: set[str] = set()
    assigned_rec: set[str] = set()
    for c in assignable:
        if c.match.transaction_id in assigned_tx:
            continue
        if c.match.document_id in assigned_rec:
            continue
        if c.is_determ:
            outcome.matches.append(c.match)
        else:
            outcome.judgment_required.append(c.match)
        assigned_tx.add(c.match.transaction_id)
        assigned_rec.add(c.match.document_id)

    # Every transaction not assigned and not ambiguous is unmatched —
    # either it had no candidate, or every candidate receipt was claimed
    # by a higher-ranked transaction.
    for tx in transactions:
        if (
            tx.transaction_id not in assigned_tx
            and tx.transaction_id not in ambiguous_tx_ids
        ):
            outcome.unmatched_transactions.append(tx.transaction_id)

    # Receipts not consumed by an assignment surface as unmatched, unless
    # they are still referenced by an ambiguous tie awaiting a human pick.
    ambiguous_docs = {a.document_id for a in outcome.ambiguous}
    for r in receipts:
        if r.document_id in assigned_rec:
            continue
        if r.document_id in ambiguous_docs:
            continue
        outcome.unmatched_receipts.append(r.document_id)

    return outcome
