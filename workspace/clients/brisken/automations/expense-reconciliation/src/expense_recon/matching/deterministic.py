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
`judgment_required`, `ambiguous`, `unmatched_transactions`, or (for
credits, 3.10 / LD-5 A5) `refunds`. No silent drops.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field, replace
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


def _tx_card_keys(tx: Transaction) -> set[str]:
    """Card identifiers for a charge (WS3, 2026-07-21).

    The per-row `card_last4` wins when the source printed one (the CSV /
    xlsx "Card" column); otherwise the account id carries the card, which
    is how the Chase PDF parser has always worked (`account_id` IS the
    cycle-marker card number). A source with neither returns the empty
    set, which means "unknown card" everywhere downstream — never
    "different card".
    """
    return _card_keys(tx.card_last4) or _card_keys(tx.account_id)


def _card_score(tx: Transaction, receipt: Receipt) -> float:
    """Card agreement in [0,1] between the charge and the receipt's Zoho
    payment mode (WS3, 2026-07-21).

    1.0 when the two name the same card, 0.0 when both name a card and
    they do not overlap, 0.5 when either side names none. The 0.5 middle
    is deliberate: an unknown card is not evidence against a pair, so it
    must not sort below a genuine card contradiction.

    Card scoping (`MatchingConfig.card_scoping`) already removes most
    contradicted pairs before they are scored. This score is what remains
    useful after it: the tie-break when scoping is off or when a receipt's
    payment mode names a card the statement does not contain, and the
    reviewer-facing "why did these two pair" signal on every Match.
    """
    tx_keys = _tx_card_keys(tx)
    rec_keys = _card_keys(receipt.payment_mode)
    if not tx_keys or not rec_keys:
        return 0.5
    return 1.0 if (tx_keys & rec_keys) else 0.0


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


def _signal(
    tx: Transaction, receipt: Receipt, cfg: "MatchingConfig"
) -> tuple[float, float, float]:
    """(reference-match, card-score, vendor-score) tie-break signal for one
    candidate pair, strongest identity signal first.

    Reference is an exact hit on a printed number. Card is a hard fact
    from two independent systems (the bank's card column and Zoho's
    payment mode), so it outranks the fuzzy vendor text, which banks
    truncate. Vendor-score last, including the learned-alias boost.
    """
    return (
        1.0 if reference_match(tx, receipt) else 0.0,
        _card_score(tx, receipt),
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
    "fx_reference_match_pct", "fx_reference_review_pct",
    "fx_base_amount_match_pct", "fx_base_amount_review_pct",
    "fx_band_score_span_pct",
})
_TUNABLE_INT = frozenset({
    "date_exact_window_days", "date_probable_window_days",
    "fx_date_window_days",
    "fx_self_derived_min_statement_rates", "fx_self_derived_min_receipts",
})
_TUNABLE_FLOAT = frozenset({
    "high_confidence", "probable_confidence", "possible_confidence",
    "blend_amount_weight", "blend_date_weight", "blend_vendor_weight",
    "blend_card_weight",
})
_TUNABLE_BOOL = frozenset({
    "card_scoping", "fx_self_derived_rates", "fx_self_derived_review",
})


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

    # ── Deterministic reference-rate FX (3.15 / 3.7 upgrade) ───────────
    # Monthly reference rates per (receipt_ccy, tx_ccy), e.g.
    # ("BRL","USD") -> 0.185. When a rate is configured for the pair, a
    # cross-currency candidate that survives the date gate is resolved
    # DETERMINISTICALLY before the band/LLM path: expected charge =
    # receipt total x rate; deviation <= fx_reference_match_pct is a
    # match, <= fx_reference_review_pct a match flagged for review,
    # beyond that it falls through to the implied-rate band / FX_JUDGMENT
    # exactly as before. Deviations reflect DCC markup + tip, which only
    # push the charge UP, but the check is symmetric for simplicity —
    # the band's asymmetry still guards the fall-through path. Unconfigured
    # pairs are byte-for-byte the old behaviour. Rates come from
    # config/match-tuning.json ("fx_reference_rates": {"BRL:USD": 0.185});
    # they are month-scoped operator input, never derived from Zoho's
    # per-line rate (measured wrong by up to 12.8%, LD-5).
    fx_reference_rates: Mapping[tuple[str, str], Decimal] = field(
        default_factory=dict
    )
    fx_reference_match_pct: Decimal = Decimal("0.03")
    fx_reference_review_pct: Decimal = Decimal("0.13")

    # ── Zoho base-amount deterministic FX (2026-07-23) ─────────────
    # The ER report prints Zoho's own per-receipt conversion ("1 BRL =
    # 0.193945 USD" -> Receipt.base_amount in the card currency). The
    # human label fixture was largely confirmed off exactly this signal
    # (E3, ±2%), yet the matcher never consulted it — the single biggest
    # measured accuracy hole (E3 tier: 0/92 deterministic at baseline).
    # Deviation is measured against the CHARGE (|amount - base| / amount,
    # mirroring labeling.evidence_for). LD-5 caveat: an individual Zoho
    # per-line rate can be off by up to 12.8%, so the clean threshold is
    # tight and the review level exists — and review-grade base-amount
    # ranks BELOW a clean reference-rate match in the ladder.
    # 0.01 (not the labeler's 0.02): tuned by optimize run
    # brisken-recon-tuning-v1 (2026-07-23). Tightening demoted a
    # coincidental rival into the review zone, which made a TRUE pair
    # bilaterally unique and promoted it — the knee is bracketed
    # (0.005 loses, 0.01 wins, 0.02 loses). Promoted into the dataclass
    # default because the hosted image ships only src/ and never reads
    # the tuning file.
    fx_base_amount_match_pct: Decimal = Decimal("0.01")
    fx_base_amount_review_pct: Decimal = Decimal("0.13")

    # ── Self-derived per-run reference rates (2026-07-23) ──────────
    # When no reference rate is configured for a pair, derive the month's
    # rate from the run's own inputs: median of the statement's printed
    # FX lines (bank-grade, n >= min_statement_rates) else median of the
    # receipts' Zoho exchange_rate lines (n >= min_receipts — the median
    # is the LD-5-safe aggregation). A derived rate outside the static
    # fx band for its pair is discarded (poisoned-median clamp).
    # Configured rates always win. `fx_self_derived_review` forces
    # receipt-median matches to review even when clean; statement-derived
    # rates are the bank's own numbers and stay clean.
    fx_self_derived_rates: bool = True
    fx_self_derived_min_statement_rates: int = 1
    fx_self_derived_min_receipts: int = 3
    fx_self_derived_review: bool = False

    # ── FX band amount-scoring span (2026-07-23) ───────────────────
    # Inside the implied-rate band, candidates are scored by amount
    # agreement under the best available rate (configured > learned
    # merchant mean > self-derived > band midpoint): score = 1 -
    # deviation/span. Replaces the midpoint-distance score under which a
    # junk pair near midpoint outranked a true pair near the band edge.
    fx_band_score_span_pct: Decimal = Decimal("0.15")

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
    # Card agreement in the triage blend (WS3, 2026-07-21). Ships at 0.0:
    # the card is a TIE-BREAK and a transparency field, and a non-zero
    # weight here would need the other three renormalized (they sum to
    # 1.0). Left tunable so the optimize loop can price the signal if a
    # month of multi-card data says it is worth folding into the sort.
    blend_card_weight: float = 0.0

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
            elif key == "fx_reference_rates":
                rates: dict[tuple[str, str], Decimal] = {}
                for pair, rate in value.items():
                    from_ccy, _, to_ccy = pair.partition(":")
                    if not from_ccy or not to_ccy:
                        raise ValueError(
                            f"fx_reference_rates key {pair!r} must be 'FROM:TO'"
                        )
                    rates[(from_ccy, to_ccy)] = Decimal(str(rate))
                kwargs[key] = rates
            else:
                raise ValueError(
                    f"unknown matching-tuning key {key!r} "
                    f"(tunables: {sorted(_TUNABLE_DECIMAL | _TUNABLE_INT | _TUNABLE_FLOAT | _TUNABLE_BOOL | {'fx_rate_bands', 'fx_reference_rates'})})"
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

    def fx_reference_rate(self, from_ccy: str, to_ccy: str) -> Decimal | None:
        """Monthly reference rate for receipt->transaction currency, or
        None when the pair has no configured rate (then the band/LLM path
        applies unchanged)."""
        return self.fx_reference_rates.get((from_ccy, to_ccy))

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
    card_score: float, cfg: MatchingConfig,
) -> int:
    """Blend the matching signals into a 0-100 triage score.

    Amount agreement is the strongest signal, then date proximity, then
    fuzzy vendor agreement (a corroborator, not a gate; bank exports
    truncate vendor names). Sorts the review workbench so the weakest
    matches surface first; it does NOT change which bucket a pair lands
    in (that stays deterministic via match_type / confidence). Weights
    live on MatchingConfig (default 0.55/0.30/0.15).

    Card agreement is carried too but ships at weight 0.0, so the score
    is byte-for-byte its pre-WS3 self until an operator prices it.
    """
    s = (cfg.blend_amount_weight * amount_score
         + cfg.blend_date_weight * date_score
         + cfg.blend_vendor_weight * vendor_score
         + cfg.blend_card_weight * card_score)
    return max(0, min(100, round(s * 100.0)))


def _match_on_amount(
    tx: Transaction,
    receipt: Receipt,
    cfg: MatchingConfig,
    *,
    charge_amount: Decimal,
    vendor_score: float,
    card_score: float,
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
            score=_blend_score(amount_score, 0.5, vendor_score, card_score, cfg),
            amount_score=amount_score,
            date_score=0.5,
            vendor_score=vendor_score,
            card_score=card_score,
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
            score=_blend_score(
                amount_score, date_score, vendor_score, card_score, cfg
            ),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
            card_score=card_score,
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
            score=_blend_score(
                amount_score, date_score, vendor_score, card_score, cfg
            ),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
            card_score=card_score,
        )

    return None


def derive_fx_reference_rates(
    transactions: "list[Transaction]",
    receipts: "list[Receipt]",
    cfg: MatchingConfig,
) -> dict[tuple[str, str], tuple[Decimal, str, int]]:
    """Self-derive this run's reference rate per currency pair from the
    run's own inputs (2026-07-23). Returns {(from_ccy, to_ccy): (rate,
    source, n_samples)} where source is "statement" or "receipts".

    Two sources, in trust order:
      * statement — median of the statement's printed per-charge FX rates
        (`Transaction.fx_rate`, the Chase two-line detail). Bank-grade;
        accepted from `fx_self_derived_min_statement_rates` samples.
      * receipts — median of the ER report's per-receipt Zoho rates
        (`Receipt.exchange_rate`). An individual line can be off by up to
        12.8% (LD-5), the month's MEDIAN is not; accepted from
        `fx_self_derived_min_receipts` samples. The to-currency is the
        run's card currency (Zoho's base line converts into it).

    A derived rate outside the static fx band for its pair is discarded
    (poisoned-median clamp: one mis-parsed total cannot drag the month's
    rate somewhere implausible). Configured `fx_reference_rates` are NOT
    consulted here — the caller overlays them, so operator input always
    wins. `fx_self_derived_rates=false` disables the whole derivation.
    """
    if not cfg.fx_self_derived_rates:
        return {}
    from statistics import median

    stmt: dict[tuple[str, str], list[Decimal]] = {}
    for t in transactions:
        if (
            t.original_currency
            and t.fx_rate is not None
            and t.fx_rate > 0
            and t.original_currency != t.transaction_currency
        ):
            pair = (t.original_currency.upper(), t.transaction_currency.upper())
            stmt.setdefault(pair, []).append(t.fx_rate)

    # The receipts' Zoho conversion is into the card currency; take the
    # dominant card currency across the (already credit-free) charges.
    card_ccys = [t.account_card_currency.upper() for t in transactions
                 if t.account_card_currency]
    card_ccy = max(set(card_ccys), key=card_ccys.count) if card_ccys else "USD"
    rec: dict[tuple[str, str], list[Decimal]] = {}
    for r in receipts:
        if (
            r.detected_currency
            and r.exchange_rate is not None
            and r.exchange_rate > 0
            and r.detected_currency.upper() != card_ccy
        ):
            pair = (r.detected_currency.upper(), card_ccy)
            rec.setdefault(pair, []).append(r.exchange_rate)

    out: dict[tuple[str, str], tuple[Decimal, str, int]] = {}
    for pair, vals in stmt.items():
        if len(vals) >= cfg.fx_self_derived_min_statement_rates:
            out[pair] = (median(vals), "statement", len(vals))
    for pair, vals in rec.items():
        if pair not in out and len(vals) >= cfg.fx_self_derived_min_receipts:
            out[pair] = (median(vals), "receipts", len(vals))

    clamped: dict[tuple[str, str], tuple[Decimal, str, int]] = {}
    for pair, (rate, source, n) in out.items():
        band = cfg.fx_band(*pair)
        if band is not None:
            lo, hi = band
            if not (lo <= rate <= hi):
                continue  # implausible for the pair: discard, do not clamp-to-edge
        clamped[pair] = (rate, source, n)
    return clamped


def _reference_rate_for(
    cfg: MatchingConfig,
    from_ccy: str,
    to_ccy: str,
    derived: "Mapping[tuple[str, str], tuple[Decimal, str, int]] | None",
) -> tuple[Decimal, str, int] | None:
    """The best reference rate for a pair: configured (operator intent)
    wins, else this run's self-derived rate. Returns (rate, source, n)
    with source in {"configured", "statement", "receipts"}, or None."""
    configured = cfg.fx_reference_rate(from_ccy, to_ccy)
    if configured is not None and configured > 0:
        return configured, "configured", 0
    if derived:
        hit = derived.get(((from_ccy or "").upper(), (to_ccy or "").upper()))
        if hit is not None:
            return hit
    return None


def match_one(
    tx: Transaction,
    receipt: Receipt,
    cfg: MatchingConfig,
    derived_rates: "Mapping[tuple[str, str], tuple[Decimal, str, int]] | None" = None,
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
    # Card agreement (WS3) rides along on every Match for the tie-break and
    # the reviewer; it enters the blended score only at a non-zero weight.
    card_score = _card_score(tx, receipt)

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
                card_score=card_score,
                fx_currency=tx.original_currency,
            )
            if exact_fx is not None:
                return exact_fx

        # Every FX path is date-gated: without a receipt date no FX
        # candidate is emitted (the receipt still surfaces in
        # `unmatched_receipts` — guarantee held). The receipt TOTAL is no
        # longer required up front (2026-07-23): the base-amount rung needs
        # only Zoho's converted base_amount, so a receipt whose printed
        # total failed to parse can still resolve deterministically.
        if receipt.detected_date is None or tx.amount <= 0:
            return None

        candidate_dates = [tx.transaction_date]
        if tx.posting_date and tx.posting_date != tx.transaction_date:
            candidate_dates.append(tx.posting_date)
        date_diff = min(
            abs((receipt.detected_date - d).days) for d in candidate_dates
        )
        if date_diff > cfg.fx_date_window_days:
            return None
        date_score = max(0.0, 1.0 - date_diff / max(1, cfg.fx_date_window_days))

        def _fx_det_match(
            match_type: MatchType,
            *,
            clean: bool,
            amount_score: float,
            reason: str,
            force_review: bool = False,
        ) -> Match:
            return Match(
                transaction_id=tx.transaction_id,
                document_id=receipt.document_id,
                match_type=match_type,
                confidence=(
                    cfg.high_confidence if clean else cfg.probable_confidence
                ),
                reason=reason,
                requires_review=(not clean) or force_review,
                score=_blend_score(
                    amount_score, date_score, vendor_score, card_score, cfg
                ),
                amount_score=amount_score,
                date_score=date_score,
                vendor_score=vendor_score,
                card_score=card_score,
            )

        # Zoho base-amount deviation, measured against the CHARGE — the
        # same formula the labeling E3 tier uses (labeling.evidence_for),
        # so matcher and fixture agree on what "agrees" means.
        base_dev: Decimal | None = None
        if receipt.base_amount is not None and receipt.base_amount > 0:
            base_dev = abs(tx.amount - receipt.base_amount) / tx.amount

        # Reference-rate deviation under the best available rate:
        # configured (operator intent) wins, else this run's self-derived
        # median (statement FX lines, else receipt Zoho rates).
        ref = _reference_rate_for(
            cfg, receipt.detected_currency, tx.transaction_currency,
            derived_rates,
        )
        ref_dev: Decimal | None = None
        if (
            ref is not None
            and receipt.detected_total is not None
            and receipt.detected_total > 0
        ):
            expected = receipt.detected_total * ref[0]
            if expected > 0:
                ref_dev = abs(tx.amount - expected) / expected

        def _rate_phrase() -> str:
            rate, source, n = ref
            if source == "configured":
                return f"monthly reference rate {rate}"
            unit = (
                "statement FX lines" if source == "statement"
                else "receipt rates"
            )
            return f"derived rate {rate} (median of {n} {unit})"

        # The deterministic FX ladder (2026-07-23). Clean evidence always
        # outranks review-grade evidence, and at the same grade Zoho's
        # per-receipt conversion outranks a month rate (it is
        # per-purchase). LD-5's up-to-12.8% per-line error is exactly why
        # base-amount REVIEW still sits BELOW a CLEAN rate match.
        if base_dev is not None and base_dev <= cfg.fx_base_amount_match_pct:
            return _fx_det_match(
                MatchType.FX_BASE_AMOUNT,
                clean=True,
                amount_score=max(
                    0.0,
                    1.0 - float(base_dev) / float(cfg.fx_base_amount_review_pct),
                ),
                reason=(
                    f"Charge {tx.amount} {tx.transaction_currency} vs the ER "
                    f"report's own conversion {receipt.base_amount} "
                    f"{tx.transaction_currency} (receipt "
                    f"{receipt.detected_total} {receipt.detected_currency} at "
                    f"Zoho's per-receipt rate): deviation "
                    f"{float(base_dev) * 100:.1f}%."
                ),
            )
        if ref is not None and ref_dev is not None and ref_dev <= cfg.fx_reference_match_pct:
            return _fx_det_match(
                MatchType.FX_REFERENCE,
                clean=True,
                force_review=(
                    ref[1] == "receipts" and cfg.fx_self_derived_review
                ),
                amount_score=max(
                    0.0,
                    1.0 - float(ref_dev) / float(cfg.fx_reference_review_pct),
                ),
                reason=(
                    f"Charge {tx.amount} {tx.transaction_currency} vs receipt "
                    f"{receipt.detected_total} {receipt.detected_currency} at "
                    f"{_rate_phrase()}: deviation {float(ref_dev) * 100:.1f}%."
                ),
            )
        # Review-zone evidence (clean-threshold .. review_pct) DEFERS to the
        # judgment bucket rather than resolving deterministically
        # (2026-07-23, measured on the labelled fixture): treating the
        # review zone as a match turned every coincidental within-13%
        # charge into a deterministic pairing — 38 of the 46 receipts
        # human-labelled "no charge exists" got auto-matched. Precision
        # owns the matches bucket; the review zone tees the candidate up
        # for the FX judgment layer / reviewer with its scores and reason.
        if base_dev is not None and base_dev <= cfg.fx_base_amount_review_pct:
            amount_score = max(
                0.0,
                1.0 - float(base_dev) / float(cfg.fx_base_amount_review_pct),
            )
            return Match(
                transaction_id=tx.transaction_id,
                document_id=receipt.document_id,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,  # placeholder; LLM layer revises
                reason=(
                    f"Charge {tx.amount} {tx.transaction_currency} vs the ER "
                    f"report's own conversion {receipt.base_amount}: deviation "
                    f"{float(base_dev) * 100:.1f}% (above "
                    f"{float(cfg.fx_base_amount_match_pct) * 100:.0f}% — too "
                    f"loose to auto-match; a single Zoho per-line rate can "
                    f"drift). Requires FX judgment."
                ),
                requires_review=True,
                score=_blend_score(
                    amount_score, date_score, vendor_score, card_score, cfg
                ),
                amount_score=amount_score,
                date_score=date_score,
                vendor_score=vendor_score,
                card_score=card_score,
            )
        if ref is not None and ref_dev is not None and ref_dev <= cfg.fx_reference_review_pct:
            amount_score = max(
                0.0,
                1.0 - float(ref_dev) / float(cfg.fx_reference_review_pct),
            )
            return Match(
                transaction_id=tx.transaction_id,
                document_id=receipt.document_id,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,  # placeholder; LLM layer revises
                reason=(
                    f"Charge {tx.amount} {tx.transaction_currency} vs receipt "
                    f"{receipt.detected_total} {receipt.detected_currency} at "
                    f"{_rate_phrase()}: deviation {float(ref_dev) * 100:.1f}% "
                    f"(above {float(cfg.fx_reference_match_pct) * 100:.0f}%; "
                    f"DCC markup / tip territory). Requires FX judgment."
                ),
                requires_review=True,
                score=_blend_score(
                    amount_score, date_score, vendor_score, card_score, cfg
                ),
                amount_score=amount_score,
                date_score=date_score,
                vendor_score=vendor_score,
                card_score=card_score,
            )

        # No deterministic FX evidence. The band / FX_JUDGMENT path below
        # needs a printed receipt total to compute an implied rate.
        if receipt.detected_total is None or receipt.detected_total <= 0:
            return None

        implied_rate = tx.amount / receipt.detected_total
        band = cfg.fx_band(receipt.detected_currency, tx.transaction_currency)
        if band is not None:
            lo, hi = band
            if not (lo <= implied_rate <= hi):
                # Implausible rate for this currency pair -> not the
                # same purchase. Drop the candidate.
                return None
            # amount sub-score (2026-07-23): amount agreement under the
            # best available rate — configured reference > learned
            # per-merchant mean (in-band, PR 2c) > self-derived month
            # median > band midpoint as the last resort. The old score
            # measured distance to the band MIDPOINT, under which a junk
            # pair whose implied rate happened to sit mid-band outranked a
            # true pair near the band edge under the month's real rate.
            # Only the SCORE changes; the lo/hi membership test above is
            # untouched, so bucket membership is byte-for-byte identical.
            learned_mean = cfg.merchant_fx_mean(
                tx.legal_entity_id, receipt.detected_vendor,
                receipt.detected_currency, tx.transaction_currency,
            )
            if ref is not None and ref[1] == "configured":
                score_rate = ref[0]
                score_src = _rate_phrase()
            elif learned_mean is not None and lo <= learned_mean <= hi:
                score_rate = learned_mean
                score_src = (
                    f"learned {receipt.detected_currency}->"
                    f"{tx.transaction_currency} mean {float(learned_mean):.4f}"
                )
            elif ref is not None:
                score_rate = ref[0]
                score_src = _rate_phrase()
            else:
                score_rate = (lo + hi) / 2
                score_src = "band midpoint (no rate available)"
            expected_band = receipt.detected_total * score_rate
            band_dev = (
                abs(tx.amount - expected_band) / expected_band
                if expected_band > 0
                else Decimal("1")
            )
            amount_score = max(
                0.0, 1.0 - float(band_dev) / float(cfg.fx_band_score_span_pct)
            )
            rate_note = (
                f"implied rate {implied_rate:.4f} within "
                f"{receipt.detected_currency}->{tx.transaction_currency} "
                f"band [{lo}, {hi}]; scored at {score_src}, amount "
                f"deviation {float(band_dev) * 100:.1f}%"
            )
        else:
            # Unprofiled currency pair: keep the candidate (date-gated
            # only) so we never lose a real match for a currency we
            # have not measured. Add a band entry to tighten later.
            rate_note = (
                f"unprofiled {receipt.detected_currency}->"
                f"{tx.transaction_currency} pair; date-gated only"
            )
            amount_score = 0.5

        # date_score computed once with the ladder above.
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
            score=_blend_score(
                amount_score, date_score, vendor_score, card_score, cfg
            ),
            amount_score=amount_score,
            date_score=date_score,
            vendor_score=vendor_score,
            card_score=card_score,
        )

    # Same-currency path: compare the receipt total to the posted amount.
    return _match_on_amount(
        tx,
        receipt,
        cfg,
        charge_amount=tx.amount,
        vendor_score=vendor_score,
        card_score=card_score,
        fx_currency=None,
    )


@dataclass(frozen=True)
class _Candidate:
    """A scored (tx, receipt) pair plus the 3.9 tie-break signal, used
    by the 3.8 bipartite assignment."""

    match: Match
    is_determ: bool
    ref_signal: float
    card_signal: float
    vendor_signal: float

    @property
    def sort_key(self) -> tuple[int, float, int, float, float, float]:
        # Deterministic matches outrank FX for the same receipt; then
        # confidence; then the 0-100 blended score (amount + date own
        # 0.85 of the blend — added 2026-07-23: without it every
        # FX_JUDGMENT candidate tied at confidence 0.5 and every EXACT at
        # 0.99, so contested receipts were decided by vendor fuzz and
        # card instead of by amount/date agreement, directly against the
        # owner's date+amount-first directive); then reference hit; then
        # card agreement; then vendor similarity.
        return (
            1 if self.is_determ else 0,
            self.match.confidence,
            self.match.score,
            self.ref_signal,
            self.card_signal,
            self.vendor_signal,
        )


def _ties(a: _Candidate, b: _Candidate) -> bool:
    """Two candidates are a genuine tie only when confidence AND every
    tie-break signal match — i.e. reference, card, and vendor could not
    separate them. Such a tx is ambiguous; a human picks."""
    return (
        a.is_determ == b.is_determ
        and abs(a.match.confidence - b.match.confidence) < 0.001
        and a.match.score == b.match.score
        and abs(a.ref_signal - b.ref_signal) < 0.001
        and abs(a.card_signal - b.card_signal) < 0.001
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
    judgment_required / ambiguous / unmatched_transactions / refunds.
    """
    cfg = cfg or MatchingConfig()
    outcome = MatchOutcome()

    # Refund partition (3.10 / LD-5 A5): credits are split out BEFORE
    # candidate generation, so no purchase receipt can ever pair-match a
    # credit and no credit competes in the bipartite assignment. They are
    # their own review bucket; the receipts pool is untouched.
    outcome.refunds.extend(
        tx.transaction_id for tx in transactions if tx.is_credit
    )
    transactions = [tx for tx in transactions if not tx.is_credit]

    # Card-scoped candidate gating (2026-06-16): a receipt whose Zoho payment
    # mode names a specific card only reconciles against charges on that card.
    # We scope a receipt only to cards actually PRESENT in this statement; a
    # payment mode that names no present card (personal / cash, or a label we
    # can't map) is left unscoped so a real match is never excluded (the
    # reconciliation guarantee). The reimbursement routing for personal/cash
    # is a separate, Dirk-gated path. Keyed off the digit overlap between the
    # charge's card and the payment-mode label (see `_card_keys`).
    #
    # WS3 (2026-07-21): scoping now keys on the CHARGE's card keys
    # (`_tx_card_keys`: the per-row `card_last4` when the source printed a
    # card column, else the account id) instead of the account id alone.
    # Identical behaviour for a single-account source, since there the two
    # are the same string; on a multi-card tabular export it is the
    # difference between scoping working and being a no-op.
    tx_card_keys = {tx.transaction_id: _tx_card_keys(tx) for tx in transactions}
    present_keys: set[str] = set()
    for keys in tx_card_keys.values():
        present_keys |= keys

    receipt_scope: dict[str, set[str]] = {}
    if cfg.card_scoping:
        for r in receipts:
            pm_keys = _card_keys(r.payment_mode)
            if not pm_keys:
                continue
            if pm_keys & present_keys:
                receipt_scope[r.document_id] = pm_keys

    # Self-derived per-run reference rates (2026-07-23): computed once for
    # the month from the run's own inputs, consulted by match_one wherever
    # no configured rate covers a pair. Derivation is a pure function of
    # the inputs; provenance rides in every reason string.
    derived_rates = derive_fx_reference_rates(transactions, receipts, cfg)

    cands_by_tx: dict[str, list[_Candidate]] = {}
    for tx in transactions:
        for receipt in receipts:
            if receipt.legal_entity_id != tx.legal_entity_id:
                continue  # entity scope per v2 spec §4.2
            scope = receipt_scope.get(receipt.document_id)
            if scope is not None and not (scope & tx_card_keys[tx.transaction_id]):
                continue  # receipt's payment mode names a different card
            scored = match_one(tx, receipt, cfg, derived_rates)
            if scored is None:
                continue
            ref_sig, card_sig, vendor_sig = _signal(tx, receipt, cfg)
            cands_by_tx.setdefault(tx.transaction_id, []).append(
                _Candidate(
                    match=scored,
                    is_determ=scored.match_type != MatchType.FX_JUDGMENT,
                    ref_signal=ref_sig,
                    card_signal=card_sig,
                    vendor_signal=vendor_sig,
                )
            )

    # Bilateral-uniqueness gate on rate-derived FX evidence (2026-07-23).
    # A clean FX_BASE_AMOUNT / FX_REFERENCE candidate resolves
    # deterministically ONLY when the pairing is exclusive both ways: the
    # receipt has no other clean rate-derived claimant, and the charge no
    # other clean rate-derived candidate. This is the labeled fixture's
    # own AUTO criterion (labeling.auto_pairs): base-amount agreement was
    # never conclusive evidence by itself — measured on the fixture,
    # without this gate 26 of the June-2025 month's 31 receipts labelled
    # "no charge exists" sat within 2% of SOME charge in a ±5-day window
    # and auto-matched. Contested pairs are demoted to FX_JUDGMENT (the
    # candidate, its scores and its reason survive for the judgment layer
    # / reviewer; only the auto-resolution right is withdrawn). Exact
    # evidence (same-currency EXACT/PROBABLE, statement-original-amount
    # exact-FX) is bank-printed on both sides and is NOT subject to this
    # gate — its baseline precision was clean.
    _RATE_DERIVED = (MatchType.FX_BASE_AMOUNT, MatchType.FX_REFERENCE)
    claimants_by_doc: dict[str, set[str]] = {}
    docs_by_tx: dict[str, set[str]] = {}
    for tx_id, cands in cands_by_tx.items():
        for c in cands:
            if c.match.match_type in _RATE_DERIVED:
                claimants_by_doc.setdefault(c.match.document_id, set()).add(tx_id)
                docs_by_tx.setdefault(tx_id, set()).add(c.match.document_id)
    for tx_id, cands in cands_by_tx.items():
        for i, c in enumerate(cands):
            if c.match.match_type not in _RATE_DERIVED:
                continue
            doc = c.match.document_id
            unique = (
                len(claimants_by_doc.get(doc, ())) == 1
                and len(docs_by_tx.get(tx_id, ())) == 1
            )
            # Card-contradiction gate (2026-07-23, matcher-v2). A rate-derived
            # pair also forfeits its auto-resolution right when the charge's
            # card and the receipt's Zoho payment mode both name a card and
            # they DIFFER (card_signal == 0.0). Card scoping (above) has already
            # dropped contradicted pairs whose receipt names a card PRESENT in
            # the statement, so a surviving 0.0 here means the receipt was paid
            # on a card entirely ABSENT from this statement — its true charge
            # sits on another card's statement, and the clean base-amount hit to
            # a present-card charge is a same-vendor / same-day coincidence
            # (measured: 14/14 no_charge auto-matches on the labelled fixture
            # carry an absent card; 0/55 true deterministic pairs do). payment_mode
            # is an independent, always-present Zoho field — never part of the
            # labeling evidence tiers E1–E4 — so this is a real signal, not a
            # re-derivation of the base-amount agreement the fixture was built on.
            card_contradicts = cfg.card_scoping and c.card_signal == 0.0
            if unique and not card_contradicts:
                continue  # bilaterally unique, card not contradicted: keep it
            why = (
                "the receipt's payment card is absent from this statement "
                "(paid on another card)"
                if card_contradicts
                else "another charge or receipt agrees just as cleanly"
            )
            demoted = replace(
                c.match,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,
                requires_review=True,
                reason=(
                    c.match.reason.rstrip(".")
                    + f". Demoted to judgment: this rate-derived pairing is "
                    f"not conclusive ({why})."
                ),
            )
            cands[i] = _Candidate(
                match=demoted,
                is_determ=False,
                ref_signal=c.ref_signal,
                card_signal=c.card_signal,
                vendor_signal=c.vendor_signal,
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
