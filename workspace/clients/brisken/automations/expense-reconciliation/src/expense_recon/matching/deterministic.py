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

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotations only; the body imports Path itself
    from datetime import date
    from pathlib import Path

import difflib
import re
from dataclasses import dataclass, field, replace
from collections.abc import Mapping
from decimal import Decimal

from .types import Match, MatchOutcome, MatchType, Receipt, Transaction

# A month key in `fx_ecb_monthly_rates` (item 82): the ECB's TIME_PERIOD.
_MONTH_KEY = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
# A day key in `fx_daily_rates` (note #79): the provider's effectiveDate.
_DAY_KEY = re.compile(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")


_NON_ALNUM = re.compile(r"[^a-z0-9]+")
# A card-identifying digit run (last-4 / account number) inside a statement
# marker or a Zoho payment-mode label.
_DIGIT_RUN = re.compile(r"\d{3,}")
# Characters a printed card number is masked with. A digit run IMMEDIATELY
# FOLLOWED by one of these is the leading BIN, not an identifier (see
# `_card_keys`). A mask that PRECEDES the run ("******0340", "...9693") is
# the ordinary spelling of a last-4 and is left alone.
_MASK_CHARS = "Xx*#•●"


def _normalize(s: str) -> str:
    return _NON_ALNUM.sub(" ", s.lower()).strip()


def _is_reference_token(token: str) -> bool:
    """A normalized word that is a reference, not a merchant word (item X1,
    2026-09-18): four or more characters carrying at least three digits.
    "g173514057", "p3078900231", "1251593381", "x37l83bi5", "b013" and
    "2640" are references; "base44" (two digits) and "eleven" are words."""
    return len(token) >= 4 and sum(ch.isdigit() for ch in token) >= 3


def strip_reference_tokens(s: str | None) -> str:
    """The merchant words of a bank description, normalized, with its
    reference-shaped tokens taken out (item X1, 2026-09-18).

    Chase prints an order or invoice number inside the description
    ("Microsoft-G173514057", "LinkedIn SN P3078900231", "Wix.com 1251593381",
    "CASUALFOOD 2640 8"). `vendor_similarity` averages over the statement's
    tokens, so such a token halved the merchant score of a pair whose
    merchant words agreed exactly: live July 2026, the Microsoft invoice
    printing G173514057 scored 0.50 against "Microsoft-G173514057" and sat
    below the self-confirm floor (75) for a click it did not need. The
    reference is evidence in its own right (`reference_match`); it is not a
    merchant word. When nothing but references remain, the whole normalized
    string is returned, so a description that IS a number still compares."""
    norm = _normalize(s or "")
    kept = [t for t in norm.split() if not _is_reference_token(t)]
    return " ".join(kept) if kept else norm


def _card_keys(s: str | None) -> set[str]:
    """Normalized card identifiers found in a statement account id or a Zoho
    payment-mode label, so the two compare on the same key (2026-06-16).

    The Chase statement marks a charge's card with the cycle-marker number
    ("2838", "3645", "0340"); the Zoho expense's payment mode names it as a
    label ("1 - CorpServ 2838/1672 (Chase)", a mode whose last-4 is "340").
    Each digit run of 3+ contributes its leading-zero-stripped form and its
    leading-zero-stripped last-4, so "0340" and "340" land on the same key
    and "CorpServ 2838/1672" overlaps the "2838" marker. Empty when the
    string carries no card-like number (then no scoping is applied).

    Masked BIN (2026-09-15, backlog item 69 round B). A digit run
    IMMEDIATELY FOLLOWED by a mask character is the card's leading BIN,
    which names the ISSUER, not the card: "42463153XXXXXX38" prints the
    first 8 digits of a Visa and hides the rest, and the trailing "38" is
    too short to be a last-4. Read as an identifier it became a card the
    statement does not contain, so the card-contradiction gate demoted the
    receipt's true pair (the August SARL TRAIN'S billet) and the card chain
    read it as an absent card at the same time. Skipping the run makes the
    string carry NO card, which is what it actually says, and unknown-card
    is never evidence against a pair anywhere downstream. A mask that
    PRECEDES a run ("VISA - ******0340", "...9693") is untouched: that is
    the ordinary spelling of a last-4."""
    if not s:
        return set()
    keys: set[str] = set()
    for m in _DIGIT_RUN.finditer(s):
        if m.end() < len(s) and s[m.end()] in _MASK_CHARS:
            continue  # a masked BIN prefix: the issuer, not this card
        run = m.group()
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
    stmt_vendor = tx.vendor_from_statement
    # Item X1: the description's reference tokens are not merchant words.
    if cfg.vendor_ignore_reference_tokens:
        stmt_vendor = strip_reference_tokens(stmt_vendor)
    return vendor_similarity(stmt_vendor, receipt.detected_vendor)


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
    "fx_band_score_span_pct", "fx_ecb_match_pct",
})
_TUNABLE_INT = frozenset({
    "date_exact_window_days", "date_probable_window_days",
    "fx_date_window_days", "fx_daily_rate_max_gap_days",
    "fx_self_derived_min_statement_rates", "fx_self_derived_min_receipts",
})
_TUNABLE_FLOAT = frozenset({
    "high_confidence", "probable_confidence", "possible_confidence",
    "blend_amount_weight", "blend_date_weight", "blend_vendor_weight",
    "blend_card_weight", "fx_judgment_suggest_floor",
    "amount_probable_min_vendor_score",
    "uniqueness_vendor_dominance_min", "uniqueness_vendor_dominance_margin",
})
_TUNABLE_BOOL = frozenset({
    "card_scoping", "fx_self_derived_rates", "fx_self_derived_review",
    "uniqueness_spoken_for",
    "vendor_ignore_reference_tokens", "no_card_rival_review",
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
    # Item 82 (owner ruling 2026-09-16): the ECB's monthly average reference
    # rates, as the ECB publishes them, keyed by month:
    # {"2026-07": {"USD": Decimal("1.1417478"), "BRL": Decimal("5.8448957")}},
    # units of each currency per ONE EUR (series EXR/M.{CCY}.EUR.SP00.A). A
    # pair's rate is the cross through EUR, read for the CHARGE's own month:
    # card networks lock the rate at authorization, so the purchase month is
    # the right grain. The hosted surface fetches the table when a month is
    # created and when a statement is attached; empty keeps every pair on
    # the rungs above it, byte for byte. See `ecb_monthly_rate`.
    fx_ecb_monthly_rates: Mapping[str, Mapping[str, Decimal]] = field(
        default_factory=dict
    )
    # Feedback note #79 (owner 2026-09-23: "fx rates should be polled daily
    # via open tickers API"): the daily reference rates the app polls from
    # OpenTickers, the same shape as the ECB table but keyed by DAY:
    # {"2026-09-22": {"USD": Decimal("1.1463"), "BRL": Decimal("5.8726")}},
    # units per ONE EUR. A pair's rate is the cross through EUR on the
    # CHARGE's own date, or the nearest polled day within
    # `fx_daily_rate_max_gap_days` (a weekend or holiday has no fix; four
    # days spans Good Friday to Easter Monday), earlier winning a tie. Sits
    # one rung ABOVE the monthly average (a day is the grain the card locked
    # the rate at) and below a typed rate and the self-derived rates. The
    # hosted surface refreshes the table from its store on every re-match
    # (`service.apply_fx_daily_rates`); empty keeps every pair on the rungs
    # around it, byte for byte. See `daily_rate`.
    fx_daily_rates: Mapping[str, Mapping[str, Decimal]] = field(
        default_factory=dict
    )
    fx_daily_rate_max_gap_days: int = 4
    fx_reference_match_pct: Decimal = Decimal("0.03")
    fx_reference_review_pct: Decimal = Decimal("0.13")
    # Item 90 / 132 (owner ruling 2026-09-17: tighten the band first, then
    # the Settings rates go): the clean band for a pair whose rate is the
    # ECB monthly average, and for no other source. A typed Settings rate
    # and the self-derived rates keep `fx_reference_match_pct` (the S1
    # optimize run refuted 1.5% for the receipt-median path, which needs its
    # 3% headroom), so the scorer's bundles and every month still matched at
    # a Settings rate are untouched. `reference_match_pct` is the one home.
    # 0.02 measured 2026-09-17 with the Settings rates removed (DB copy at
    # v165, judgment from the snapshot cache): July 29 / 31 / 32 / 33 / 33
    # right at 3 / 2.5 / 2 / 1.75 / 1.5%, coincidental auto-matches 2 / 2 /
    # 1 / 1 / 1 (the last is Erste Fracht at +0.2%, which no band reaches),
    # August unchanged; the six bundles on ECB rates alone 68 / 70 / 70 / 70
    # / 69 of 95, 0 wrong. 1.5% loses a holdout pair, so a true pair sits
    # between 1.5 and 1.75%; 2% keeps headroom above it for a volatile month
    # at the price of one July receipt (E A LOCACOES) staying in review.
    fx_ecb_match_pct: Decimal = Decimal("0.02")

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

    # ── FX-judgment suggestion floor (2026-07-24) ──────────────────
    # A judged pair whose model same-purchase confidence lands AT OR BELOW
    # this floor is not shown as a suggestion (item 131, 2026-09-17: the
    # model answers exactly 0.20, and "below" let those rejections through
    # with "likely NOT the same purchase" as their reason). The one
    # exception, AT the floor only: a pair whose own rate arithmetic sits
    # in the clean band (`pair_reference_gap_band` == "match") stays in
    # review, the tool's reason first (`cli._apply_judgment`); below the
    # floor a rejection stays final. On the April 2026 hosted
    # run the workbench proposed a USD OpenAI subscription against a
    # BRL construction-materials receipt at p=0.10, with the model's own
    # reason saying "likely NOT the same purchase" (owner call
    # 2026-07-24: such pairs must not be suggested). The pair is unbound
    # instead: charge and receipt fall to the plain unmatched buckets,
    # so nothing is silently dropped and the reconciliation guarantee
    # holds. 0.0 disables the floor. The no-LLM stub verdict (0.5)
    # always passes, so offline no-API runs and the pinned scorer path
    # are byte-for-byte unaffected.
    fx_judgment_suggest_floor: float = 0.2

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

    # ── Vendor floor on the same-currency probable band (2026-09-15) ──
    # `amount_probable_tolerance_pct` is the restaurant-tip allowance: it
    # exists so a card charge that carries a tip still reaches the receipt
    # that printed before the tip. A tip does not change WHO was paid, so
    # a same-currency pair that spends that allowance must still agree on
    # the merchant. Without this floor the 20% band pairs any two
    # unrelated same-currency charges of similar size: on the real August
    # month it offered ADOBE 16.23 a Lovable 15.00 receipt and ANTHROPIC
    # 104.95 an Obsidian 96.00 one, and bound five such pairs outright.
    # Measured on that month, the two populations do not overlap: all 41
    # different-merchant pairs scored <= 0.40 and all 30 true
    # ANTHROPIC/"Anthropic, PBC" pairs scored exactly 1.00, and the cut is
    # flat (identical 30 keep / 41 drop) anywhere from 0.45 to 0.90, so
    # 0.50 sits in the middle of an empty gap rather than on a knee.
    # Applies ONLY to the same-currency band. FX pairs keep the band
    # untouched: the S1 optimize run measured vendor as non-separable
    # there (26/55 true pairs below 0.2, banks truncating foreign vendor
    # strings to aggregators), so the same floor would cost real recall.
    # A confirmed alias pins `_vendor_score` to 1.0, so once a reviewer
    # has accepted a truncated bank string for a merchant it keeps
    # matching. 0.0 disables the floor.
    amount_probable_min_vendor_score: float = 0.5

    # ── Two refinements of the bilateral-uniqueness gate (2026-09-15) ──
    # The gate withdraws a clean rate-derived pair's auto-resolution right
    # whenever ANY other clean rate-derived pair shares its receipt or its
    # charge. Measured on the six labelled bundles it demoted 36 of 95
    # receipts and on the two live months another 11, with the correct
    # charge already sitting first in review: the rival that blocked them
    # was usually not a rival at all.
    #
    # `uniqueness_spoken_for`: a rival that is already claimed by
    # bank-printed EXACT evidence elsewhere cannot also take this pairing,
    # so it does not block. False restores the pre-2026-09-15 gate.
    uniqueness_spoken_for: bool = True
    # `uniqueness_vendor_dominance_*`: a pair that still has a live rival
    # keeps its auto-resolution right when the merchant agrees on IT and on
    # no rival. Vendor only ever PROMOTES a pair that already carries clean
    # rate evidence; it never rejects one, which is the opposite direction
    # from the vendor floor the S1 optimize run refuted for FX (26 of 55
    # true FX pairs score below 0.2 because banks truncate foreign vendor
    # strings to an aggregator, so a floor would cost real recall — a
    # dominance rule leaves those pairs exactly where they are). A
    # confirmed alias pins `_vendor_score` to 1.0, so a reviewer's earlier
    # acceptance carries the merchant forward. `min` 0.0 disables the rule.
    uniqueness_vendor_dominance_min: float = 0.5
    uniqueness_vendor_dominance_margin: float = 0.25

    # ── The statement description counts (item X1, owner 2026-09-18) ──
    # `vendor_ignore_reference_tokens`: `_vendor_score` compares the
    # description's MERCHANT words (`strip_reference_tokens`), so an order
    # or invoice number Chase prints inside the description no longer
    # halves the merchant score of a pair whose words agree. Measured
    # 2026-09-18: live July's Microsoft invoice 0.50 -> 1.00 (crosses the
    # self-confirm floor), two bundle pairs 0.50 -> 1.00 and 0.43 -> 0.64,
    # no class moves, 0 wrong. False restores the raw comparison.
    vendor_ignore_reference_tokens: bool = True
    # `no_card_rival_review`: the review clause of the no-card fallback
    # (`card_evidence`, `NO_CARD_RIVAL_REVIEW`). A pair whose receipt names
    # no card at all keeps its match but asks for review when another
    # deterministic candidate for the same receipt sits on a DIFFERENT card
    # and is not spoken for by exact evidence elsewhere: the tool cannot say
    # which card paid, so a person does. Measured 2026-09-18 over July,
    # August and the six bundles: 0 pairs flagged (the one candidate, July
    # `0063` Marinho against GITHUB 10.00 on 2838, is spoken for). False
    # turns the clause off; the fallback itself (match across every card)
    # is not a knob.
    no_card_rival_review: bool = True

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
            elif key == "fx_ecb_monthly_rates":
                table: dict[str, dict[str, Decimal]] = {}
                for month, per_eur in value.items():
                    if not _MONTH_KEY.fullmatch(str(month)):
                        raise ValueError(
                            f"fx_ecb_monthly_rates key {month!r} must be 'YYYY-MM'"
                        )
                    table[str(month)] = {
                        str(ccy).upper(): Decimal(str(units))
                        for ccy, units in (per_eur or {}).items()
                    }
                kwargs[key] = table
            elif key == "fx_daily_rates":
                daily: dict[str, dict[str, Decimal]] = {}
                for day, per_eur in value.items():
                    if not _DAY_KEY.fullmatch(str(day)):
                        raise ValueError(
                            f"fx_daily_rates key {day!r} must be 'YYYY-MM-DD'"
                        )
                    daily[str(day)] = {
                        str(ccy).upper(): Decimal(str(units))
                        for ccy, units in (per_eur or {}).items()
                    }
                kwargs[key] = daily
            else:
                raise ValueError(
                    f"unknown matching-tuning key {key!r} "
                    f"(tunables: {sorted(_TUNABLE_DECIMAL | _TUNABLE_INT | _TUNABLE_FLOAT | _TUNABLE_BOOL | {'fx_rate_bands', 'fx_reference_rates', 'fx_ecb_monthly_rates', 'fx_daily_rates'})})"
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

    def reference_match_pct(self, source: str | None) -> Decimal:
        """The clean band for a reference-rate pair, by where its rate came
        from (`_reference_rate_for`'s source): `fx_ecb_match_pct` for
        `ecb_month` and for `opentickers_day` (both are central-bank
        reference rates, and the daily one is closer to the rate the card
        locked, never further), `fx_reference_match_pct` for every other
        source. The matcher, the band a reviewer sees (item 81) and the
        judgment layer's rejected-pair rule (item 131) all read it here."""
        if source in ("ecb_month", "opentickers_day"):
            return self.fx_ecb_match_pct
        return self.fx_reference_match_pct

    def daily_rate(
        self, from_ccy: str, to_ccy: str, on: "date | str | None"
    ) -> tuple[Decimal, str] | None:
        """Note #79: the polled daily reference rate for receipt->charge
        currency on the day of `on` (a date or 'YYYY-MM-DD'), as (rate, day
        used).

        The day itself when the table holds it with both currencies, else
        the nearest day that does within `fx_daily_rate_max_gap_days`
        (earlier wins a tie: a Saturday purchase reads Friday's fix). Cross
        rate through EUR (EUR is 1 unit per EUR), to six decimals, the
        precision a rate typed in Settings carries. None when `on` is
        missing or not a full date, the table is empty, or no day inside the
        window carries the pair; the caller then falls through to the
        monthly average."""
        if not self.fx_daily_rates or on is None:
            return None
        src, dst = (from_ccy or "").upper(), (to_ccy or "").upper()
        if not src or not dst or src == dst:
            return None
        from datetime import date as _date

        want = on if isinstance(on, str) else on.isoformat()
        if not _DAY_KEY.fullmatch(want):
            return None
        target = _date.fromisoformat(want)

        def _units(table: Mapping[str, Decimal], ccy: str) -> Decimal | None:
            if ccy == "EUR":
                return Decimal(1)
            units = table.get(ccy)
            return units if units is not None and units > 0 else None

        best: tuple[tuple[int, _date], str, Mapping[str, Decimal]] | None = None
        for day, table in self.fx_daily_rates.items():
            if _units(table, src) is None or _units(table, dst) is None:
                continue
            try:
                d = _date.fromisoformat(day)
            except ValueError:
                continue
            gap = abs((d - target).days)
            if gap > self.fx_daily_rate_max_gap_days:
                continue
            key = (gap, d)
            if best is None or key < best[0]:
                best = (key, day, table)
        if best is None:
            return None
        _key, day, table = best
        rate = (_units(table, dst) / _units(table, src)).quantize(
            Decimal("0.000001")
        )
        return (rate, day) if rate > 0 else None

    def ecb_monthly_rate(
        self, from_ccy: str, to_ccy: str, on: "date | str | None"
    ) -> tuple[Decimal, str] | None:
        """Item 82: the ECB monthly average rate for receipt->charge currency
        in the month of `on` (a date or 'YYYY-MM'), as (rate, month used).

        The month itself when the table holds it with both currencies, else
        the nearest month that does (earlier wins a tie): a charge dated the
        30th on next month's statement, or a month whose average the ECB has
        not published yet, reads its neighbour, and the returned month says
        which. Cross rate through EUR (EUR is 1 unit per EUR), to six
        decimals, the precision a rate typed in Settings carries. None when
        `on` is missing, the table is empty or no month carries the pair."""
        if not self.fx_ecb_monthly_rates or on is None:
            return None
        src, dst = (from_ccy or "").upper(), (to_ccy or "").upper()
        if not src or not dst or src == dst:
            return None
        want = on if isinstance(on, str) else on.strftime("%Y-%m")
        if not _MONTH_KEY.fullmatch(want):
            return None

        def _index(month: str) -> int:
            return int(month[:4]) * 12 + int(month[5:7])

        def _units(table: Mapping[str, Decimal], ccy: str) -> Decimal | None:
            if ccy == "EUR":
                return Decimal(1)
            units = table.get(ccy)
            return units if units is not None and units > 0 else None

        usable = [
            month for month, table in self.fx_ecb_monthly_rates.items()
            if _units(table, src) is not None and _units(table, dst) is not None
        ]
        if not usable:
            return None
        target = _index(want)
        month = min(usable, key=lambda m: (abs(_index(m) - target), _index(m)))
        table = self.fx_ecb_monthly_rates[month]
        rate = (_units(table, dst) / _units(table, src)).quantize(
            Decimal("0.000001")
        )
        return (rate, month) if rate > 0 else None

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


def _same_currency_band_allowed(
    tx: Transaction,
    receipt: Receipt,
    cfg: MatchingConfig,
    vendor_score: float,
) -> bool:
    """May a same-currency pair spend the probable (tip) amount band?

    Only when the two sides do not NAME different merchants. A tip
    explains a different amount; it never explains a different payee. So
    the band stays open when the vendors agree by the matcher's own
    comparison, and when either side names no vendor at all (nothing to
    contradict — an unnamed side is missing evidence, not conflicting
    evidence, and the reconciliation guarantee says never drop on
    absence). It closes when both sides name a merchant and they
    disagree. Exact-amount pairs never reach here; neither do FX pairs.
    """
    if cfg.amount_probable_min_vendor_score <= 0.0:
        return True
    if not (receipt.detected_vendor or "").strip():
        return True
    if not (tx.vendor_from_statement or "").strip():
        return True
    return vendor_score >= cfg.amount_probable_min_vendor_score


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

    # The tip band is merchant-scoped (2026-09-15, backlog item 63): a
    # same-currency pair that needs it must still agree on who was paid.
    if (
        amount_probable
        and fx_currency is None
        and not _same_currency_band_allowed(tx, receipt, cfg, vendor_score)
    ):
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
    on: "date | str | None" = None,
) -> tuple[Decimal, str, int] | None:
    """The best reference rate for a pair: configured (operator intent)
    wins, else this run's self-derived rate, else the polled daily rate for
    the day of `on` (the charge date, note #79), else the ECB monthly
    average for its month (item 82). Returns (rate, source, n) with source
    in {"configured", "statement", "receipts", "opentickers_day",
    "ecb_month"}, or None.

    The ECB rung sits BELOW the self-derived rates on the evidence: a
    statement's printed FX lines are the rate the card actually charged,
    and on the six labelled bundles the receipts' own booked rates resolved
    70 of 95 pairs against 68 at the ECB monthly average (2026-09-17). A
    hosted month has neither (the Chase export prints no FX columns and no
    mailed receipt carries a booked rate), so there the ECB rate is what
    fires whenever Settings holds none."""
    configured = cfg.fx_reference_rate(from_ccy, to_ccy)
    if configured is not None and configured > 0:
        return configured, "configured", 0
    if derived:
        hit = derived.get(((from_ccy or "").upper(), (to_ccy or "").upper()))
        if hit is not None:
            return hit
    daily = cfg.daily_rate(from_ccy, to_ccy, on)
    if daily is not None:
        return daily[0], "opentickers_day", 0
    ecb = cfg.ecb_monthly_rate(from_ccy, to_ccy, on)
    if ecb is not None:
        return ecb[0], "ecb_month", 0
    return None


def _pct_text(fraction: Decimal) -> str:
    """A band as a reason string prints it: 0.03 -> '3', 0.025 -> '2.5'.
    A whole percentage reads exactly as the old `:.0f` did."""
    return format((Decimal(fraction) * 100).normalize(), "f")


def reference_gap(
    charge_amount: Decimal,
    receipt_total: Decimal,
    rate: Decimal,
    match_pct: Decimal,
    review_pct: Decimal,
) -> tuple[Decimal, Decimal, str] | None:
    """A receipt converted at a reference rate, set against its charge:
    ``(converted, deviation, band)``, or None when nothing converts.

    converted = receipt total x rate; deviation = (charge - converted) /
    converted, signed and unrounded, the basis of ``match_one``'s ``ref_dev``;
    band is ``match`` within ``match_pct``, ``review`` within ``review_pct``,
    else ``outside``. This IS item 81's ``fx.reference_gap_band``: the view's
    ``_fx_reference_fields`` and the judgment layer's rejected-pair rule
    (item 131, ``cli._apply_judgment``) both read it here, so the band a
    reviewer sees and the band that keeps a pair in review cannot differ."""
    if receipt_total is None or receipt_total <= 0 or charge_amount is None:
        return None
    converted = receipt_total * rate
    if converted <= 0:
        return None
    deviation = (charge_amount - converted) / converted
    if abs(deviation) <= match_pct:
        band = "match"
    elif abs(deviation) <= review_pct:
        band = "review"
    else:
        band = "outside"
    return converted, deviation, band


def pair_reference_gap_band(
    tx: Transaction,
    receipt: Receipt,
    cfg: MatchingConfig,
    derived_rates: "Mapping[tuple[str, str], tuple[Decimal, str, int]] | None" = None,
) -> str | None:
    """Item 81's band for one cross-currency pair, at the rate the matcher
    uses for it (``_reference_rate_for``, on the charge date). None for a
    same-currency pair, a receipt with no total, or a pair with no rate."""
    rec_ccy = receipt.detected_currency
    if not rec_ccy or not tx.transaction_currency or rec_ccy == tx.transaction_currency:
        return None
    ref = _reference_rate_for(
        cfg, rec_ccy, tx.transaction_currency, derived_rates, on=tx.transaction_date,
    )
    if ref is None:
        return None
    gap = reference_gap(
        tx.amount, receipt.detected_total, ref[0],
        cfg.reference_match_pct(ref[1]), cfg.fx_reference_review_pct,
    )
    return gap[2] if gap is not None else None


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
            derived_rates, on=tx.transaction_date,
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
            if source == "opentickers_day":
                _rate, day = cfg.daily_rate(
                    receipt.detected_currency, tx.transaction_currency,
                    tx.transaction_date,
                )
                return f"OpenTickers daily reference rate {rate} ({day})"
            if source == "ecb_month":
                _rate, month = cfg.ecb_monthly_rate(
                    receipt.detected_currency, tx.transaction_currency,
                    tx.transaction_date,
                )
                return f"ECB monthly average rate {rate} ({month})"
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
                    f"the report's own per-receipt rate): deviation "
                    f"{float(base_dev) * 100:.1f}%."
                ),
            )
        ref_match_pct = cfg.reference_match_pct(ref[1] if ref is not None else None)
        if ref is not None and ref_dev is not None and ref_dev <= ref_match_pct:
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
                    f"loose to auto-match; a single per-line rate from the report can "
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
                    f"(above {_pct_text(ref_match_pct)}%; "
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
            if ref is not None and ref[1] in ("configured", "opentickers_day", "ecb_month"):
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


# The evidence classes the bilateral-uniqueness gate governs. Exact
# evidence (same-currency EXACT / PROBABLE, statement-original-amount
# exact-FX) is bank-printed on both sides and is never subject to it.
RATE_DERIVED_TYPES = (MatchType.FX_BASE_AMOUNT, MatchType.FX_REFERENCE)

_WHY_CARD = (
    "the receipt's payment card is absent from this statement "
    "(paid on another card)"
)
_WHY_RIVAL = "another charge or receipt agrees just as cleanly"


@dataclass(frozen=True)
class UniquenessVerdict:
    """What the bilateral-uniqueness gate decided about ONE rate-derived
    candidate pair, and why.

    `keep` is the auto-resolution right, nothing else: a demoted pair, its
    scores and its reason all survive into the judgment layer, only the
    right to resolve without a human is withdrawn. `basis` names why a kept
    pair was kept ("unique" when it never had a rival, so the reason string
    is left exactly as it was); `kind` names which gate demoted it. `note`
    is the clause to append to the reason, empty when there is nothing to
    add.
    """

    keep: bool
    basis: str
    kind: str
    note: str
    rival_txs: tuple[str, ...]
    rival_docs: tuple[str, ...]
    vendor_signal: float
    best_rival_vendor: float


def uniqueness_verdicts(
    candidates: "list[tuple[str, str, MatchType, float, float]]",
    cfg: MatchingConfig,
) -> dict[tuple[str, str], UniquenessVerdict]:
    """The bilateral-uniqueness gate, over the FULL candidate set of a run.

    One rule, two callers: `match_month` applies these verdicts, and
    `tools/recon-match-attribution.py` reads them to classify a receipt. The
    tool used to mirror the rules by hand, which is exactly how a
    measurement drifts away from the thing it measures.

    `candidates` is every (tx_id, document_id, match_type, card_signal,
    vendor_signal) the matcher generated BEFORE assignment — exact
    candidates included, because they are what makes a rival "spoken for".
    The returned map covers the rate-derived pairs only; every other type
    is ungated.

    The gate, in the order it decides:

    1. **Card contradiction.** The charge's card and the receipt's Zoho
       payment mode both name a card and they differ: demoted, always, and
       neither refinement below can rescue it. A surviving contradiction
       means the receipt was paid on a card absent from this statement, so
       the clean rate agreement is a same-vendor / same-day coincidence
       (14/14 no_charge auto-matches on the labelled fixture carry an
       absent card; 0/55 true pairs do).
    2. **Unique.** No other rate-derived candidate shares the receipt or
       the charge: kept, reason untouched.
    3. **Spoken for** (`uniqueness_spoken_for`). A rival CHARGE that holds
       an EXACT candidate with some receipt, or a rival RECEIPT that holds
       an EXACT candidate with some charge, is already accounted for by
       bank-printed evidence and will take that pairing in the assignment;
       it cannot also take this one, so it does not block. When every rival
       is spoken for, the pair is effectively unique and is kept.
    4. **Vendor dominance** (`uniqueness_vendor_dominance_*`). A pair with a
       live rival left is kept when the merchant agrees on it
       (>= `min`) and beats every rate-derived rival by at least `margin`.
       Vendor PROMOTES a pair that already carries clean rate evidence; it
       never rejects one.
    5. Otherwise demoted.
    """
    claimants_by_doc: dict[str, set[str]] = {}
    docs_by_tx: dict[str, set[str]] = {}
    vendor_of: dict[tuple[str, str], float] = {}
    exact_txs: set[str] = set()
    exact_docs: set[str] = set()
    for tx_id, doc, match_type, _card, vendor in candidates:
        if match_type is MatchType.EXACT:
            exact_txs.add(tx_id)
            exact_docs.add(doc)
        if match_type in RATE_DERIVED_TYPES:
            claimants_by_doc.setdefault(doc, set()).add(tx_id)
            docs_by_tx.setdefault(tx_id, set()).add(doc)
            vendor_of[(tx_id, doc)] = vendor

    out: dict[tuple[str, str], UniquenessVerdict] = {}
    for tx_id, doc, match_type, card, vendor in candidates:
        if match_type not in RATE_DERIVED_TYPES:
            continue
        rival_txs = tuple(sorted(claimants_by_doc[doc] - {tx_id}))
        rival_docs = tuple(sorted(docs_by_tx[tx_id] - {doc}))
        rival_vendors = [vendor_of[(r, doc)] for r in rival_txs]
        rival_vendors += [vendor_of[(tx_id, d)] for d in rival_docs]
        best_rival = max(rival_vendors) if rival_vendors else 0.0

        def _v(keep: bool, basis: str, kind: str, note: str) -> UniquenessVerdict:
            return UniquenessVerdict(
                keep=keep,
                basis=basis,
                kind=kind,
                note=note,
                rival_txs=rival_txs,
                rival_docs=rival_docs,
                vendor_signal=vendor,
                best_rival_vendor=best_rival,
            )

        key = (tx_id, doc)
        if cfg.card_scoping and card == 0.0:
            out[key] = _v(False, "", "card", _WHY_CARD)
            continue
        if not rival_txs and not rival_docs:
            out[key] = _v(True, "unique", "", "")
            continue
        if cfg.uniqueness_spoken_for:
            blocking = [r for r in rival_txs if r not in exact_txs]
            blocking += [d for d in rival_docs if d not in exact_docs]
            if not blocking:
                out[key] = _v(
                    True, "spoken_for", "", "the rival pairing is spoken for"
                )
                continue
        if (
            cfg.uniqueness_vendor_dominance_min > 0.0
            and vendor >= cfg.uniqueness_vendor_dominance_min
            and best_rival <= vendor - cfg.uniqueness_vendor_dominance_margin
        ):
            out[key] = _v(
                True,
                "vendor_dominance",
                "",
                f"the merchant agrees ({vendor:.2f}) and no rival's does "
                f"(best {best_rival:.2f})",
            )
            continue
        out[key] = _v(False, "", "uniqueness", _WHY_RIVAL)
    return out


# Item 137: where a receipt's resolved card came from (`Receipt.card_scope_source`).
CARD_SCOPE_PICKED = "override"
CARD_SCOPE_SOURCES = frozenset({CARD_SCOPE_PICKED, "hint", "learned"})
# A pair whose cards differ keeps its evidence but ranks below every clean
# deterministic candidate (POSSIBLE is the lowest, 0.60), so a charge on the
# receipt's own card always wins the receipt first.
CARDS_DIFFER_CONFIDENCE = 0.55
# Tie-break signal for a pair on the card the tool resolved: above an unknown
# card (0.5), below a card the receipt itself printed (1.0), so between two
# receipts for one charge the printed card still wins (live August 2026:
# ZOHO Corporation printing ...2838 over a Zoho Books copy picked as 2838).
RESOLVED_CARD_SIGNAL = 0.75


def receipt_card_scope(
    receipt: Receipt, present_keys: set[str], cfg: MatchingConfig
) -> set[str] | None:
    """The card keys a receipt is scoped to, or None when it is unscoped:
    scoping is off, its payment mode names no card, or the card it names is
    not PRESENT among the statement's charges (``present_keys``). The one
    rule ``match_month`` scopes by, public so the duplicate statement check
    (item 74) reads the same scope instead of a copy of it.

    Item 137: a card picked by hand on the row (``card_scope_source``
    "override") scopes the receipt to THAT card, over whatever the document
    printed and whether or not the card has charges here. ``match_month``
    falls back to the other cards' charges only when the picked card offers
    no candidate at all (``cards_differ``), so a wrong pick never silently
    removes the one real match."""
    if not cfg.card_scoping:
        return None
    if receipt.card_scope_source == CARD_SCOPE_PICKED and receipt.card_scope_keys:
        return set(receipt.card_scope_keys)
    pm_keys = _card_keys(receipt.payment_mode)
    if not pm_keys or not (pm_keys & present_keys):
        return None
    return pm_keys


def pair_in_scope(
    tx: Transaction,
    receipt: Receipt,
    tx_keys: set[str],
    scope: set[str] | None,
) -> bool:
    """Whether a (charge, receipt) pair may be scored at all: a receipt
    that NAMES another legal entity never pairs (an empty entity on either
    side is unscoped), and a receipt scoped to a card (``receipt_card_scope``)
    pairs only with charges on that card (``tx_keys``, the charge's
    ``_tx_card_keys``)."""
    if (
        receipt.legal_entity_id
        and tx.legal_entity_id
        and receipt.legal_entity_id != tx.legal_entity_id
    ):
        return False
    if scope is not None and not (scope & tx_keys):
        return False
    return True


def cards_differ(tx_keys: set[str], receipt: Receipt) -> bool | None:
    """Whether the card the tool resolved for a receipt (item 137) and the
    charge's card (``_tx_card_keys``) disagree: True when both name a card
    and they do not overlap, False when they overlap, None when either side
    names none (unknown is never evidence either way). Public so the month
    view flags a held pair by the same test the matcher demotes by."""
    if not receipt.card_scope_keys or not tx_keys:
        return None
    return not (set(receipt.card_scope_keys) & tx_keys)


# Item X1 (owner 2026-09-18): where each side of a pair got its card, the ONE
# definition of "the card cannot be identified" the matcher, the month page
# and the documents read. Receipt: a card picked on the row, resolved from the
# printed method or an assigned hint word, remembered from an earlier month
# (`Receipt.card_scope_source`, which is also where a per-merchant card fact
# arrives once memory learns one), printed digits no registry card names, or
# none. Charge: the statement's own card column on the row, the upload's
# account when the row names none (the Chase PDF's cycle marker and a
# single-card export both land here: the account IS that card), or none.
RECEIPT_CARD_EVIDENCE = ("override", "hint", "learned", "printed", "none")
CHARGE_CARD_EVIDENCE = ("row", "account", "none")
# `Match.review_code` when the no-card fallback's review clause fired.
NO_CARD_RIVAL_REVIEW = "no_card_rival_on_other_card"


def card_evidence(tx: Transaction, receipt: Receipt) -> tuple[str, str]:
    """`(receipt_source, charge_source)` from `RECEIPT_CARD_EVIDENCE` x
    `CHARGE_CARD_EVIDENCE`. "none" on the receipt side is the no-card
    fallback: such a receipt is matched across every card's charges on
    amount, date, currency, the reference and the uniqueness gate, exactly
    as one that names a card the statement does not carry."""
    if receipt.card_scope_keys and receipt.card_scope_source in CARD_SCOPE_SOURCES:
        rec = receipt.card_scope_source
    elif _card_keys(receipt.payment_mode):
        rec = "printed"
    else:
        rec = "none"
    if _card_keys(tx.card_last4):
        chg = "row"
    elif _card_keys(tx.account_id):
        chg = "account"
    else:
        chg = "none"
    return rec, chg


def _no_card_rival_note(rival: Transaction, rival_keys: set[str]) -> str:
    return (
        f"the receipt names no card and a charge on another card also fits "
        f"({rival.vendor_from_statement} {rival.amount} {rival.transaction_currency} "
        f"on {'/'.join(sorted(rival_keys))})"
    )


def _cards_differ_note(tx_keys: set[str], receipt: Receipt) -> str:
    how = {
        CARD_SCOPE_PICKED: "picked by hand",
        "hint": "from its payment method",
        "learned": "remembered from an earlier month",
    }.get(receipt.card_scope_source, "resolved")
    return (
        f"the cards differ: the receipt's card is "
        f"{'/'.join(sorted(receipt.card_scope_keys))} ({how}), the charge is "
        f"on {'/'.join(sorted(tx_keys))}"
    )


def scored_pairs(
    transactions: list[Transaction],
    receipts: list[Receipt],
    cfg: MatchingConfig,
    derived_rates=None,
) -> list[tuple[Transaction, Receipt, Match]]:
    """Every (charge, receipt) pair ``match_month`` scores, in its order: the
    entity and card scope (``pair_in_scope`` over ``receipt_card_scope``),
    then ``match_one``. Credits must already be partitioned out.

    Item 137: a receipt scoped by a card picked by hand that finds NO
    candidate on that card is offered the other cards' charges after all,
    appended last; ``match_month`` demotes each one (``cards_differ``). A
    pick is the reviewer's word in any contest between cards, but it never
    silently removes the only real match: live August 2026, LOVABLE 25.00
    on card 3645 is the bank's line for a receipt picked as 2838.

    Public so ``tools/recon-match-attribution.py`` traces the matcher's
    own scope instead of a copy of it."""
    tx_card_keys = {tx.transaction_id: _tx_card_keys(tx) for tx in transactions}
    present_keys: set[str] = set()
    for keys in tx_card_keys.values():
        present_keys |= keys
    receipt_scope = {
        r.document_id: scope
        for r in receipts
        if (scope := receipt_card_scope(r, present_keys, cfg)) is not None
    }
    out: list[tuple[Transaction, Receipt, Match]] = []
    in_scope: set[str] = set()
    off_card: dict[str, list[Transaction]] = {}
    for tx in transactions:
        for receipt in receipts:
            doc = receipt.document_id
            # Entity scope per v2 spec §4.2: a receipt that NAMES another
            # entity never pairs with this charge. An UNKNOWN entity (the
            # empty string) is unscoped rather than a mismatch: receipts
            # mailed or dropped into a month carry no entity until a card
            # hint or the reviewer assigns one, and the classic path
            # (`reconcile()`) stamps the config entity on every receipt, so
            # nothing there changes. Before 2026-09-11 the bare inequality
            # dropped every entity-less receipt from every pairing, and a
            # month whose receipts came in by mail reconciled 0 no matter
            # what the statement said. The card half: a receipt whose
            # payment mode names a different card never pairs either.
            if not pair_in_scope(
                tx, receipt, tx_card_keys[tx.transaction_id],
                receipt_scope.get(doc),
            ):
                if (
                    receipt.card_scope_source == CARD_SCOPE_PICKED
                    and doc in receipt_scope
                    and pair_in_scope(tx, receipt, tx_card_keys[tx.transaction_id], None)
                ):
                    off_card.setdefault(doc, []).append(tx)
                continue
            scored = match_one(tx, receipt, cfg, derived_rates)
            if scored is None:
                continue
            in_scope.add(doc)
            out.append((tx, receipt, scored))
    by_doc = {r.document_id: r for r in receipts}
    for doc, txs in off_card.items():
        if doc in in_scope:
            continue
        for tx in txs:
            scored = match_one(tx, by_doc[doc], cfg, derived_rates)
            if scored is not None:
                out.append((tx, by_doc[doc], scored))
    return out


def _merchant_precedence(
    cands_by_tx: "dict[str, list[_Candidate]]",
    rec_by_id: "Mapping[str, Receipt]",
    transactions: "list[Transaction]",
    cfg: MatchingConfig,
    ambiguous_tx_ids: "set[str]" = frozenset(),
) -> None:
    """Item 133 rule (b), in place: demote an exact-amount same-currency pair
    whose merchant disagrees when another charge's pair for the same receipt
    has a merchant that agrees (see the call site in `match_month`). A rival
    counts only when this receipt is that charge's top-ranked candidate and
    the charge is not ambiguous: a rival charge that will take a better
    receipt of its own is spoken for (round B's `uniqueness_spoken_for`
    idea), and demoting against it would only flag, or strand, the receipt.
    Every verdict is taken on the candidates as they stood before any
    demotion, so the order of charges cannot change the result."""
    tx_ccy = {tx.transaction_id: tx.transaction_currency for tx in transactions}
    floor = cfg.uniqueness_vendor_dominance_min
    margin = cfg.uniqueness_vendor_dominance_margin
    by_doc: dict[str, list[tuple[str, _Candidate]]] = {}
    top_key: dict[str, tuple] = {}
    for tx_id, cands in cands_by_tx.items():
        if cands:
            top_key[tx_id] = max(c.sort_key for c in cands)
        for c in cands:
            by_doc.setdefault(c.match.document_id, []).append((tx_id, c))

    def exact_same_currency(tx_id: str, c: _Candidate) -> bool:
        receipt = rec_by_id.get(c.match.document_id)
        return (
            c.match.match_type in (MatchType.EXACT, MatchType.PROBABLE)
            and c.match.amount_score == 1.0
            and receipt is not None
            and receipt.detected_currency == tx_ccy.get(tx_id)
        )

    demote: dict[tuple[str, str], str] = {}
    for doc, pairs in by_doc.items():
        for tx_id, c in pairs:
            if not exact_same_currency(tx_id, c) or c.vendor_signal >= floor:
                continue
            rivals = [
                (r_tx, r) for r_tx, r in pairs
                if r_tx != tx_id
                and r_tx not in ambiguous_tx_ids
                and r.sort_key == top_key.get(r_tx)
                and r.is_determ
                and r.match.confidence > CARDS_DIFFER_CONFIDENCE
                and r.vendor_signal >= floor
                and r.vendor_signal >= c.vendor_signal + margin
            ]
            if rivals:
                best = max(rivals, key=lambda p: p[1].vendor_signal)[1]
                demote[(tx_id, doc)] = (
                    f"the merchants differ ({round(c.vendor_signal * 100)}%) while "
                    f"another charge's merchant matches this receipt "
                    f"({round(best.vendor_signal * 100)}%)"
                )
    for tx_id, cands in cands_by_tx.items():
        for i, c in enumerate(cands):
            note = demote.get((tx_id, c.match.document_id))
            if note is None:
                continue
            cands[i] = replace(
                c,
                match=replace(
                    c.match,
                    confidence=min(c.match.confidence, CARDS_DIFFER_CONFIDENCE),
                    requires_review=True,
                    reason=c.match.reason.rstrip(".") + f". Review: {note}.",
                ),
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
    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}

    # Self-derived per-run reference rates (2026-07-23): computed once for
    # the month from the run's own inputs, consulted by match_one wherever
    # no configured rate covers a pair. Derivation is a pure function of
    # the inputs; provenance rides in every reason string.
    derived_rates = derive_fx_reference_rates(transactions, receipts, cfg)

    cands_by_tx: dict[str, list[_Candidate]] = {}
    for tx, receipt, scored in scored_pairs(transactions, receipts, cfg, derived_rates):
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
    #
    # The rules live in `uniqueness_verdicts` (above), which is also what
    # `tools/recon-match-attribution.py` reads, so the measurement and the
    # matcher cannot drift apart. Round B (2026-09-15) added the two
    # refinements it documents: a rival already spoken for by bank-printed
    # EXACT evidence does not block, and a pair whose merchant agrees while
    # no rival's does keeps its auto-resolution right.
    verdicts = uniqueness_verdicts(
        [
            (tx_id, c.match.document_id, c.match.match_type,
             c.card_signal, c.vendor_signal)
            for tx_id, cands in cands_by_tx.items()
            for c in cands
        ],
        cfg,
    )
    for tx_id, cands in cands_by_tx.items():
        for i, c in enumerate(cands):
            verdict = verdicts.get((tx_id, c.match.document_id))
            if verdict is None:
                continue  # not rate-derived: ungated
            if verdict.keep:
                if not verdict.note:
                    continue  # bilaterally unique all along; say nothing new
                # Kept by a round-B refinement. The pair stays exactly the
                # deterministic match it was; only the reason gains the
                # sentence that says WHY the rival did not stop it, because
                # the workbench renders `reason` verbatim.
                cands[i] = _Candidate(
                    match=replace(
                        c.match,
                        reason=(
                            c.match.reason.rstrip(".")
                            + f". Kept deterministic: {verdict.note}."
                        ),
                    ),
                    is_determ=c.is_determ,
                    ref_signal=c.ref_signal,
                    card_signal=c.card_signal,
                    vendor_signal=c.vendor_signal,
                )
                continue
            demoted = replace(
                c.match,
                match_type=MatchType.FX_JUDGMENT,
                confidence=0.5,
                requires_review=True,
                reason=(
                    c.match.reason.rstrip(".")
                    + f". Demoted to judgment: this rate-derived pairing is "
                    f"not conclusive ({verdict.note})."
                ),
            )
            cands[i] = _Candidate(
                match=demoted,
                is_determ=False,
                ref_signal=c.ref_signal,
                card_signal=c.card_signal,
                vendor_signal=c.vendor_signal,
            )

    # Item 137: the card the tool resolved for a receipt (a pick, a hint, a
    # remembered card; `Receipt.card_scope_keys`) takes part in matching the
    # way a printed card always has. A pair on the same card wins a tie over
    # an unknown card (`RESOLVED_CARD_SIGNAL`), though not over a card the
    # receipt printed. A pair on another card is kept, never dropped: it
    # asks for review, says why, cannot confirm itself (item 76 skips
    # `requires_review`), and ranks below every clean deterministic
    # candidate, so a charge on the receipt's own card takes the receipt
    # first. Applied after the uniqueness gate, which keeps reading the
    # printed evidence it was calibrated on.
    if cfg.card_scoping:
        for tx_id, cands in cands_by_tx.items():
            tx_keys = tx_card_keys[tx_id]
            for i, c in enumerate(cands):
                receipt = rec_by_id[c.match.document_id]
                differ = cards_differ(tx_keys, receipt)
                if differ is None:
                    continue
                if not differ:
                    cands[i] = replace(
                        c,
                        card_signal=max(c.card_signal, RESOLVED_CARD_SIGNAL),
                        match=replace(c.match, card_score=1.0),
                    )
                    continue
                cands[i] = replace(
                    c,
                    card_signal=0.0,
                    match=replace(
                        c.match,
                        confidence=min(c.match.confidence, CARDS_DIFFER_CONFIDENCE),
                        requires_review=True,
                        card_score=0.0,
                        reason=(
                            c.match.reason.rstrip(".")
                            + f". Review: {_cards_differ_note(tx_keys, receipt)}."
                        ),
                    ),
                )

    # Pass 1: detect genuinely ambiguous transactions (top deterministic
    # candidates tie even after the 3.9 signal). These are excluded from
    # assignment so an arbitrary pick is never made.
    #
    # Item 103 (2026-09-17): the receipts a tie lists are HELD by it, the way
    # `apply_decisions` holds them for the pending pick. Until then they were
    # left free, so pass 2 could also hand one to another charge: one receipt
    # stored against two charges, the stored counts reporting the second
    # pairing while the page dropped whichever pairing came later in
    # statement order (live August 2026 at round B: `0023` Anthropic 52.59
    # matched to ANTHROPIC 52.46 AND tied on ANTHROPIC 50.52). Two rules:
    #
    # 1. Spoken for (`uniqueness_spoken_for`, round B's rule carried into
    #    tie detection): a tied receipt that holds a CLEAN EXACT candidate on
    #    another charge, while its candidate here is not one, is claimed by
    #    bank-printed evidence and does not sustain the tie. When fewer than
    #    two tied receipts remain the charge is not ambiguous and goes to the
    #    assignment like any other. This only ever dissolves a tie; a charge
    #    whose top candidate stood alone before still stands alone. Clean,
    #    because the card pass above leaves a cards-differ EXACT at
    #    confidence 0.55, below every clean deterministic candidate: it is
    #    not the stronger claim elsewhere this rule reasons from. Two EXACT
    #    twins tying over two identical charges are each other's equal, so
    #    neither is spoken for and the pick stays with the human (live July
    #    2026: two GOOGLE Workspace 71.64 charges on 07-01).
    # 2. Held: every receipt a surviving tie lists is skipped by pass 2.
    exact_txs_by_doc: dict[str, set[str]] = {}
    if cfg.uniqueness_spoken_for:
        for tx_id, cands in cands_by_tx.items():
            for c in cands:
                if c.match.match_type is MatchType.EXACT and not c.match.requires_review:
                    exact_txs_by_doc.setdefault(c.match.document_id, set()).add(tx_id)
    ambiguous_tx_ids: set[str] = set()
    held_by_tie: set[str] = set()
    for tx_id, cands in cands_by_tx.items():
        determ = [c for c in cands if c.is_determ]
        if not determ:
            continue
        determ.sort(key=lambda c: c.sort_key, reverse=True)
        tied = [c for c in determ if _ties(c, determ[0])]
        if len(tied) > 1 and exact_txs_by_doc:
            tied = [
                c for c in tied
                if (
                    c.match.match_type is MatchType.EXACT
                    and not c.match.requires_review
                )
                or not (exact_txs_by_doc.get(c.match.document_id, set()) - {tx_id})
            ]
        if len(tied) > 1:
            ambiguous_tx_ids.add(tx_id)
            outcome.ambiguous.extend(c.match for c in tied)
            held_by_tie.update(c.match.document_id for c in tied)

    # Item 133 rule (b), 2026-09-17: a same-currency pair on the exact amount
    # does not consult the merchant, so a same-day charge from another
    # merchant (EXACT, 0.99) outranked the receipt's own merchant a few days
    # later (PROBABLE, 0.85), held the receipt, and left the right charge with
    # no candidate. Such a pair yields only to a rival for the SAME receipt
    # whose merchant agrees, by round B's dominance test (rival >= the
    # dominance minimum and ahead by the margin), and only when that receipt
    # is the rival charge's own first choice and the rival is not awaiting a
    # human pick: it keeps its evidence, asks for review, says why, and ranks
    # at the cards-differ confidence. Applied after pass 1, so it never breaks
    # a tie a person should settle. With no such rival nothing changes, which
    # is every exact-amount pair on the eight measured datasets (Network
    # Solutions, the Google twins, August `0025`).
    if cfg.uniqueness_vendor_dominance_min > 0.0:
        _merchant_precedence(cands_by_tx, rec_by_id, transactions, cfg, ambiguous_tx_ids)

    # Item X1 (owner 2026-09-18): the no-card fallback's review clause. A
    # receipt that names no card (`card_evidence` "none": nothing printed,
    # picked, assigned or remembered) is matched across every card's charges
    # on the other criteria, and that is the right default; what it cannot
    # do is say which card paid. So when another deterministic candidate for
    # the SAME receipt sits on a DIFFERENT card, the pair keeps its match and
    # its rank but asks for review, says why, and carries the code, so the
    # row can show it and it never confirms itself (item 76). A rival that
    # holds clean EXACT evidence with some other receipt is spoken for (round
    # B's rule) and does not count; a rival already demoted below the clean
    # candidates (cards differ, merchant precedence) does not either. A pair
    # with card evidence on both sides is never reviewed for this reason.
    # Applied after pass 1, so a tie a person should settle stays a tie.
    if cfg.no_card_rival_review:
        exact_elsewhere: dict[str, set[str]] = {}
        for tx_id, cands in cands_by_tx.items():
            for c in cands:
                if c.match.match_type is MatchType.EXACT and not c.match.requires_review:
                    exact_elsewhere.setdefault(tx_id, set()).add(c.match.document_id)
        for tx_id, cands in cands_by_tx.items():
            if tx_id in ambiguous_tx_ids:
                continue
            tx_keys = tx_card_keys[tx_id]
            for i, c in enumerate(cands):
                doc = c.match.document_id
                if card_evidence(tx_by_id[tx_id], rec_by_id[doc])[0] != "none":
                    continue
                rival: Transaction | None = None
                rival_keys: set[str] = set()
                for other_id, others in cands_by_tx.items():
                    if other_id == tx_id or other_id in ambiguous_tx_ids:
                        continue
                    other_keys = tx_card_keys[other_id]
                    if not other_keys or (other_keys & tx_keys):
                        continue
                    if exact_elsewhere.get(other_id, set()) - {doc}:
                        continue  # spoken for by bank-printed evidence elsewhere
                    if any(
                        o.match.document_id == doc
                        and o.is_determ
                        and o.match.confidence > CARDS_DIFFER_CONFIDENCE
                        for o in others
                    ):
                        rival, rival_keys = tx_by_id[other_id], other_keys
                        break
                if rival is None:
                    continue
                cands[i] = replace(
                    c,
                    match=replace(
                        c.match,
                        requires_review=True,
                        review_code=NO_CARD_RIVAL_REVIEW,
                        reason=(
                            c.match.reason.rstrip(".")
                            + f". Review: {_no_card_rival_note(rival, rival_keys)}."
                        ),
                    ),
                )

    # Pass 2: greedy bipartite assignment over all candidates from
    # non-ambiguous transactions, highest sort_key first. A transaction
    # and a receipt are each consumed at most once, and a receipt a tie
    # holds (pass 1) is not consumed here at all.
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
        if c.match.document_id in held_by_tie:
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
