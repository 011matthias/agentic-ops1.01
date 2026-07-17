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
# A card-identifying digit run (last-4 / account number) inside a statement
# marker or a Zoho payment-mode label.
_DIGIT_RUN = re.compile(r"\d{3,}")


def _normalize(s: str) -> str:
    return _NON_ALNUM.sub(" ", s.lower()).strip()


def _card_keys(s: str | None) -> set[str]:
    """Normalized card identifiers found in a statement account id or a Zoho
    payment-mode label, so the two compare on the same key (2026-06-16).

    The Chase statement marks a charge's card with the cycle-marker number
    ("2838", "3645", "0340"); the Zoho expense's payment mode names it as a
    label ("1 - CorpServ 2838/1672 (Chase)", a mode whose last-4 is "340").
    Each digit run of 3+ contributes its leading-zero-stripped form and its
    leading-zero-stripped last-4, so "0340" and "340" land on the same key
    and "CorpServ 2838/1672" overlaps the "2838" marker. Empty when the
    string carries no card-like number (then no scoping is applied)."""
    if not s:
        return set()
    keys: set[str] = set()
    for run in _DIGIT_RUN.findall(s):
        keys.add(run.lstrip("0") or "0")
        keys.add(run[-4:].lstrip("0") or "0")
    return keys


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


def _vendor_score(tx: Transaction, receipt: Receipt, cfg: "MatchingConfig") -> float:
    """Vendor agreement in [0,1]. A confirmed alias (PR 2c memory) pins it
    to 1.0 — the bank's truncated string and the receipt's full name were
    confirmed the same merchant in a prior month, so the fuzzy ratio should
    not second-guess it. Otherwise the stdlib `difflib` similarity stands."""
    if cfg.is_alias(tx.legal_entity_id, tx.vendor_from_statement, receipt.detected_vendor):
        return 1.0
    return vendor_similarity(tx.vendor_from_statement, receipt.detected_vendor)


def _signal(tx: Transaction, receipt: Receipt, cfg: "MatchingConfig") -> tuple[float, float]:
    """(reference-match, vendor-score) tie-break signal for one candidate
    pair. Reference first because an exact reference hit is a stronger
    identity signal than fuzzy vendor text; vendor-score includes the
    learned-alias boost."""
    return (
        1.0 if reference_match(tx, receipt) else 0.0,
        _vendor_score(tx, receipt, cfg),
    )


# Plausible implied-rate bands per (receipt_ccy, tx_ccy), where the
# implied rate is `tx.amount / receipt.detected_total`. EVERY Brisken
# card settles in USD (confirmed 2026-06-12: there is no EU/UK card),
# so to_ccy is always USD and every non-USD receipt is an FX pair.
#
# These are NOT FX prices; they are deliberately wide plausibility
# windows whose only job is to stop a USD charge from pairing with a
# foreign receipt it could not possibly be (the O(N×M) cross-product,
# ANNEALING A1). The band is tight on the LOW side (a charge well below
# the receipt total is implausible) and generous on the HIGH side,
# because two effects only ever push the charge UP relative to a clean
# interbank conversion, and they compound:
#   * DCC markup — measured on real receipt scans at +3.5% (Worldline
#     Italy), +5.0% (SIBS/Nets Portugal & Denmark), up to +12.8%
#     (Brazil Mega Center).
#   * Tip added on the card in local currency BEFORE conversion —
#     measured up to +16.7% (Hostaria Pantheon EUR 60 -> 70), +14.3%
#     (Menina Moca EUR 35 -> 40); Denmark/Brazil smaller.
# A true EUR match can therefore land near interbank_high x 1.05 (DCC)
# x 1.17 (tip) ~= 1.45. The upper bound admits it; the LLM judgment
# layer + vendor/reference tie-break (3.9) + bipartite one-per-receipt
# (3.8) resolve precision, so a wide band costs review breadth, not
# correctness.
#
# Calibrated 2026-06-12 against four real travel months (Oct-24
# Copenhagen DKK, Nov-24 Lisbon EUR, Jun-25 Rome EUR, plus the
# Mar-May-26 admin BRL set). Dirk's call rule is upstream of this band:
# the OCR prefers the receipt's PRINTED USD amount when the receipt was
# DCC'd (then the pair is same-currency USD and matches exact, never
# reaching this band); the band only governs receipts that print local
# currency only. Brisken's reconciliation never trusts Zoho's internal
# per-line rate (observed off by up to 12.8%).
_DEFAULT_FX_RATE_BANDS: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    ("BRL", "USD"): (Decimal("0.15"), Decimal("0.26")),
    ("EUR", "USD"): (Decimal("1.00"), Decimal("1.45")),
    ("DKK", "USD"): (Decimal("0.13"), Decimal("0.18")),
}

# File-loadable tunables (MatchingConfig.from_dict), grouped by type.
_TUNABLE_DECIMAL = frozenset({
    "amount_exact_tolerance", "amount_probable_tolerance_pct",
})
_TUNABLE_INT = frozenset({
    "date_exact_window_days", "date_probable_window_days",
    "fx_date_window_days",
})
_TUNABLE_FLOAT = frozenset({
    "high_confidence", "probable_confidence", "possible_confidence",
    "blend_amount_weight", "blend_date_weight", "blend_vendor_weight",
})
_TUNABLE_BOOL = frozenset({"card_scoping"})


@dataclass(frozen=True)
class MatchingConfig:
    """Configurable tolerances. Starting values; exact thresholds
    TBD per v2 spec §15.5 / §38 — to be tuned with Chris against
    real Brisken data."""

    amount_exact_tolerance: Decimal = Decimal("0.00")
    # Probable-tolerance covers a tip added on the card after the receipt
    # prints. One global value, not a per-region profile: every Brisken
    # card is USD (no EU/UK card — ANNEALING A6 closed 2026-06-12) and
    # the same US cardholder tips everywhere, so tip size tracks the
    # person, not the country. Real travel receipts show tips up to 16.7%
    # (Hostaria Pantheon) even in the EU, so 20% is the floor that keeps
    # those as probable rather than dropping them to unmatched. Probable
    # matches are review-flagged anyway. For FX pairs the tip is absorbed
    # by the implied-rate band's high side instead.
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

    # ── Learned memory (PR 2c) ─────────────────────────────────────
    # Both default empty => the matcher is byte-for-byte its old self.
    # They feed SCORING/TIE-BREAK only, never the band membership test or
    # which bucket a pair lands in, so the reconciliation guarantee holds.
    #   vendor_aliases: confirmed (legal_entity, stmt-norm, receipt-norm).
    #   merchant_fx: (legal_entity, vendor-norm, from_ccy, to_ccy) -> mean
    #     observed implied rate; re-centers the FX amount sub-score within
    #     the band toward this merchant's DCC pattern (never widens it).
    vendor_aliases: frozenset[tuple[str, str, str]] = frozenset()
    merchant_fx: Mapping[tuple[str, str, str, str], Decimal] = field(
        default_factory=dict
    )

    # ── Card-scoped matching (2026-06-16) ──────────────────────────
    # An expense whose Zoho payment mode names a specific Brisken card only
    # reconciles against charges on THAT card (its statement account_id).
    # Scoping is applied only when the payment mode names a card actually
    # present in this statement; a mode naming no present card (personal /
    # cash, or an unmapped label) is left unscoped so a real match is never
    # excluded (reconciliation guarantee). Kill switch for parity with the
    # pre-2026-06-16 cross-card behaviour.
    card_scoping: bool = True

    # ── Review-triage blend weights (2026-07-17, optimize-loop prep) ──
    # Weights for the 0-100 workbench sort score (_blend_score). They
    # order the review queue only; bucket membership stays deterministic
    # via match_type / confidence. Externalized so the tuning file can
    # move them without a code change.
    blend_amount_weight: float = 0.55
    blend_date_weight: float = 0.30
    blend_vendor_weight: float = 0.15

    @classmethod
    def from_dict(cls, data: Mapping) -> "MatchingConfig":
        """Build a config from a tuning dict (the optimize-loop asset).

        Only the scalar tunables and fx_rate_bands are file-loadable;
        learned memory (vendor_aliases / merchant_fx) is runtime state
        and is merged by the caller via dataclasses.replace. Unknown
        keys raise: a typo silently reverting to a default would make a
        tuning run measure nothing.
        """
        kwargs: dict = {}
        for key, value in data.items():
            if key in _TUNABLE_DECIMAL:
                kwargs[key] = Decimal(str(value))
            elif key in _TUNABLE_INT:
                kwargs[key] = int(value)
            elif key in _TUNABLE_FLOAT:
                kwargs[key] = float(value)
            elif key in _TUNABLE_BOOL:
                kwargs[key] = bool(value)
            elif key == "fx_rate_bands":
                bands: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
                for pair, (lo, hi) in value.items():
                    from_ccy, _, to_ccy = pair.partition(":")
                    if not from_ccy or not to_ccy:
                        raise ValueError(
                            f"fx_rate_bands key {pair!r} must be 'FROM:TO'"
                        )
                    bands[(from_ccy, to_ccy)] = (
                        Decimal(str(lo)), Decimal(str(hi))
                    )
                kwargs[key] = bands
            else:
                raise ValueError(
                    f"unknown matching-tuning key {key!r} "
                    f"(tunables: {sorted(_TUNABLE_DECIMAL | _TUNABLE_INT | _TUNABLE_FLOAT | _TUNABLE_BOOL | {'fx_rate_bands'})})"
                )
        return cls(**kwargs)

    @classmethod
    def from_file(cls, path: "str | Path") -> "MatchingConfig":
        """Load the tuning JSON (see config/match-tuning.json)."""
        import json
        from pathlib import Path as _Path

        return cls.from_dict(
            json.loads(_Path(path).read_text(encoding="utf-8"))
        )

    def fx_band(
        self, from_ccy: str, to_ccy: str
    ) -> tuple[Decimal, Decimal] | None:
        """Plausible implied-rate band for receipt->transaction currency,
        or None if the pair is unprofiled."""
        return self.fx_rate_bands.get((from_ccy, to_ccy))

    def is_alias(
        self, legal_entity_id: str, stmt_vendor: str | None, receipt_vendor: str | None
    ) -> bool:
        if not self.vendor_aliases:
            return False
        return (
            legal_entity_id,
            _normalize(stmt_vendor or ""),
            _normalize(receipt_vendor or ""),
        ) in self.vendor_aliases

    def merchant_fx_mean(
        self, legal_entity_id: str, vendor: str | None, from_ccy: str, to_ccy: str
    ) -> Decimal | None:
        if not self.merchant_fx:
            return None
        return self.merchant_fx.get(
            (legal_entity_id, _normalize(vendor or ""), from_ccy, to_ccy)
        )


def _blend_score(
    amount_score: float, date_score: float, vendor_score: float,
    cfg: MatchingConfig,
) -> int:
    """Blend the three matching signals into a 0-100 triage score.

    Amount agreement is the strongest signal, then date proximity, then
    fuzzy vendor agreement (a corroborator, not a gate; bank exports
    truncate vendor names). Sorts the review workbench so the weakest
    matches surface first; it does NOT change which bucket a pair lands
    in (that stays deterministic via match_type / confidence). Weights
    live on MatchingConfig (default 0.55/0.30/0.15).
    """
    s = (cfg.blend_amount_weight * amount_score
         + cfg.blend_date_weight * date_score
         + cfg.blend_vendor_weight * vendor_score)
    return max(0, min(100, round(s * 100.0)))


def _match_on_amount(
    tx: Transaction,
    receipt: Receipt,
    cfg: MatchingConfig,
    *,
    charge_amount: Decimal,
    vendor_score: float,
    fx_currency: str | None,
) -> Match | None:
    """Exact/probable match comparing the receipt total to `charge_amount`
    in a SINGLE currency. Returns None below the minimum amount bar.

    Two callers share this logic:
      * same-currency (`fx_currency=None`): `charge_amount` is `tx.amount`.
      * exact-FX (`fx_currency` set): `charge_amount` is the statement's
        captured original (foreign) amount (Chase PDF two-line FX detail).
        The posted USD vs the receipt's foreign currency differ only because
        the card settled USD; the underlying purchase currency agrees, so
        this is an apples-to-apples comparison that resolves deterministically
        with no implied-rate band and no LLM.
    """
    if receipt.detected_total is None:
        return None

    diff = abs(charge_amount - receipt.detected_total)
    amount_exact = diff <= cfg.amount_exact_tolerance
    amount_probable = (
        not amount_exact
        and charge_amount > 0
        and (diff / charge_amount) <= cfg.amount_probable_tolerance_pct
    )
    if not (amount_exact or amount_probable):
        return None

    if amount_exact:
        amount_score = 1.0
    else:
        span = float(charge_amount) * float(cfg.amount_probable_tolerance_pct)
        amount_score = max(0.0, 1.0 - float(diff) / span) if span else 0.0

    ccy_phrase = (
        "original currency {} (statement FX detail)".format(fx_currency)
        if fx_currency is not None
        else "same currency"
    )

    if receipt.detected_date is None:
        # Without a receipt date we lean on amount alone — downgrade.
        reason = (
            "Amount match without receipt date; review required."
            if fx_currency is None
            else f"Amount match in {ccy_phrase} without receipt date; review required."
        )
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.POSSIBLE,
            confidence=cfg.possible_confidence,
            reason=reason,
            requires_review=True,
            score=_blend_score(amount_score, 0.5, vendor_score, cfg),
            amount_score=amount_score,
            date_score=0.5,
            vendor_score=vendor_score,
        )

    candidate_dates = [tx.transaction_date]
    if tx.posting_date and tx.posting_date != tx.transaction_date:
        candidate_dates.append(tx.posting_date)
    date_diff = min(
        abs((receipt.detected_date - d).days) for d in candidate_dates
    )
    date_exact = date_diff <= cfg.date_exact_window_days
    date_probable = not date_exact and date_diff <= cfg.date_probable_window_days
    date_score = max(0.0, 1.0 - date_diff / max(1, cfg.date_probable_window_days))

    if amount_exact and date_exact:
        reason = (
            f"Exact amount, date within {cfg.date_exact_window_days} day(s), same currency."
            if fx_currency is None
            else f"Exact amount in {ccy_phrase}, date within {cfg.date_exact_window_days} day(s)."
        )
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.EXACT,
            confidence=cfg.high_confidence,
            reason=reason,
            score=_blend_score(amount_score, date_score, vendor_score, cfg),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
        )

    if (amount_exact or amount_probable) and (date_exact or date_probable):
        reason = (
            f"Amount diff {diff} (tolerance up to "
            f"{cfg.amount_probable_tolerance_pct * 100}%), "
            f"date diff {date_diff} day(s)."
            if fx_currency is None
            else f"Amount diff {diff} in {ccy_phrase} (tolerance up to "
            f"{cfg.amount_probable_tolerance_pct * 100}%), "
            f"date diff {date_diff} day(s)."
        )
        return Match(
            transaction_id=tx.transaction_id,
            document_id=receipt.document_id,
            match_type=MatchType.PROBABLE,
            confidence=cfg.probable_confidence,
            reason=reason,
            requires_review=True,
            score=_blend_score(amount_score, date_score, vendor_score, cfg),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
        )

    return None


def match_one(
    tx: Transaction, receipt: Receipt, cfg: MatchingConfig
) -> Match | None:
    """Score a single (transaction, receipt) candidate pair.

    Returns None when the candidate does not pass the minimum bar
    (no plausible amount or date relationship).
    """
    # Unknown receipt currency (Dirk 2026-06-16: "if we really do not know
    # the currency, then we should say so"). We refuse to silently treat an
    # unknown currency as the card's currency; doing so would let a foreign
    # receipt amount-match a USD charge as if it were same-currency and post
    # as a trusted EXACT. No deterministic candidate is produced, so the
    # receipt surfaces in `unmatched_receipts`, flagged "currency unknown" in
    # the workbench for the reviewer to set before it can reconcile.
    if receipt.detected_currency is None:
        return None

    # Vendor similarity feeds the graded 0-100 triage score in every
    # branch (3.9 signal reused); a confirmed alias (PR 2c) pins it to 1.0.
    vendor_score = _vendor_score(tx, receipt, cfg)

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
        # Exact-FX first (2026-06-16): the Chase statement carries this
        # charge's OWN original amount + currency (the two-line FX detail).
        # When the receipt's currency equals that captured original currency,
        # compare the receipt total to the statement's original amount
        # directly — a same-currency match that resolves deterministically
        # (EXACT / PROBABLE), no implied-rate band and no LLM. The posted-USD
        # vs receipt-foreign mismatch is only the card settling USD. A
        # non-agreeing original amount falls through to the band / FX_JUDGMENT
        # path below (the receipt may be a different foreign purchase).
        if (
            tx.original_currency is not None
            and tx.original_amount is not None
            and receipt.detected_currency == tx.original_currency
        ):
            exact_fx = _match_on_amount(
                tx,
                receipt,
                cfg,
                charge_amount=tx.original_amount,
                vendor_score=vendor_score,
                fx_currency=tx.original_currency,
            )
            if exact_fx is not None:
                return exact_fx

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
            # amount sub-score: how close the implied rate sits to the
            # expected center. The center is the band midpoint by default,
            # but a learned per-merchant FX mean (PR 2c) re-centers it on
            # THIS merchant's known DCC pattern when one exists and sits in
            # band — so a charge matching that merchant's history scores
            # higher. Memory refines the score WITHIN the band; it never
            # moves the lo/hi membership test above, so buckets are unchanged.
            learned_mean = cfg.merchant_fx_mean(
                tx.legal_entity_id, receipt.detected_vendor,
                receipt.detected_currency, tx.transaction_currency,
            )
            if learned_mean is not None and lo <= learned_mean <= hi:
                center = float(learned_mean)
                rate_note = (
                    f"implied rate {implied_rate:.4f} vs learned "
                    f"{receipt.detected_currency}->{tx.transaction_currency} "
                    f"mean {float(learned_mean):.4f} (band [{lo}, {hi}])"
                )
            else:
                center = (float(lo) + float(hi)) / 2.0
                rate_note = (
                    f"implied rate {implied_rate:.4f} within "
                    f"{receipt.detected_currency}->{tx.transaction_currency} "
                    f"band [{lo}, {hi}]"
                )
            half = ((float(hi) - float(lo)) / 2.0) or 1.0
            amount_score = max(0.0, 1.0 - abs(float(implied_rate) - center) / half)
        else:
            # Unprofiled currency pair: keep the candidate (date-gated
            # only) so we never lose a real match for a currency we
            # have not measured. Add a band entry to tighten later.
            rate_note = (
                f"unprofiled {receipt.detected_currency}->"
                f"{tx.transaction_currency} pair; date-gated only"
            )
            amount_score = 0.5

        date_score = max(0.0, 1.0 - date_diff / max(1, cfg.fx_date_window_days))
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
            score=_blend_score(amount_score, date_score, vendor_score, cfg),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
        )

    # Same-currency path: compare the receipt total to the posted amount.
    return _match_on_amount(
        tx,
        receipt,
        cfg,
        charge_amount=tx.amount,
        vendor_score=vendor_score,
        fx_currency=None,
    )


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

    # Card-scoped candidate gating (2026-06-16): a receipt whose Zoho payment
    # mode names a specific card only reconciles against charges on that card.
    # We scope a receipt only to cards actually PRESENT in this statement; a
    # payment mode that names no present card (personal / cash, or a label we
    # can't map) is left unscoped so a real match is never excluded (the
    # reconciliation guarantee). The reimbursement routing for personal/cash
    # is a separate, Dirk-gated path. Keyed off the digit overlap between the
    # marker account_id and the payment-mode label (see `_card_keys`).
    receipt_scope: dict[str, set[str]] = {}
    if cfg.card_scoping:
        account_keys = {tx.account_id: _card_keys(tx.account_id) for tx in transactions}
        for r in receipts:
            pm_keys = _card_keys(r.payment_mode)
            if not pm_keys:
                continue
            scope = {
                acct for acct, akeys in account_keys.items() if akeys & pm_keys
            }
            if scope:
                receipt_scope[r.document_id] = scope

    cands_by_tx: dict[str, list[_Candidate]] = {}
    for tx in transactions:
        for receipt in receipts:
            if receipt.legal_entity_id != tx.legal_entity_id:
                continue  # entity scope per v2 spec §4.2
            scope = receipt_scope.get(receipt.document_id)
            if scope is not None and tx.account_id not in scope:
                continue  # receipt's payment mode names a different card
            scored = match_one(tx, receipt, cfg)
            if scored is None:
                continue
            ref_sig, vendor_sig = _signal(tx, receipt, cfg)
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
