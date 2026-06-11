"""Tests for the deterministic matching engine.

Synthetic fixtures only for this first session. Real Brisken-month
fixtures land once Chris provides a representative month (see
../README.md "Data we need from Chris").
"""
from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import (
    MatchingConfig,
    match_month,
)
from expense_recon.matching.types import (
    MatchType,
    Receipt,
    Transaction,
)

LE = "brisken-us"
ACCOUNT_USD = "brisken-amex-usd"


def tx(
    tid: str,
    amount: str,
    txdate: date,
    posting: date | None = None,
    currency: str = "USD",
    vendor: str = "VENDOR",
) -> Transaction:
    return Transaction(
        transaction_id=tid,
        legal_entity_id=LE,
        account_id=ACCOUNT_USD,
        transaction_date=txdate,
        posting_date=posting,
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def receipt(
    rid: str,
    amount: str | None,
    rdate: date | None,
    currency: str | None = "USD",
    vendor: str | None = "VENDOR",
) -> Receipt:
    return Receipt(
        document_id=rid,
        legal_entity_id=LE,
        detected_date=rdate,
        detected_total=Decimal(amount) if amount else None,
        detected_currency=currency,
        detected_vendor=vendor,
    )


def test_exact_match_usd_on_usd_returns_high_confidence():
    """The common case Dirk cited as ~99%: USD card + USD expense,
    same date, same amount."""
    txs = [tx("t1", "42.50", date(2026, 4, 12))]
    rs = [receipt("r1", "42.50", date(2026, 4, 12))]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    m = out.matches[0]
    assert m.match_type == MatchType.EXACT
    assert m.confidence >= 0.99
    assert not out.unmatched_transactions
    assert not out.unmatched_receipts


def test_posting_date_within_tolerance_still_matches():
    """Purchase date Friday, posting date Monday — common bank delay."""
    txs = [
        tx("t1", "100.00", date(2026, 4, 10), posting=date(2026, 4, 13))
    ]
    rs = [receipt("r1", "100.00", date(2026, 4, 10))]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert out.matches[0].match_type == MatchType.EXACT


def test_eur_receipt_on_usd_card_routes_to_judgment_layer():
    """The FX hard case Dirk specified on the call — handed to the LLM
    judgment layer, not auto-resolved."""
    txs = [tx("t1", "112.30", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", date(2026, 4, 15), currency="EUR")]
    out = match_month(txs, rs)
    assert not out.matches
    assert len(out.judgment_required) == 1
    j = out.judgment_required[0]
    assert j.match_type == MatchType.FX_JUDGMENT
    assert "Currency mismatch" in j.reason
    assert j.requires_review


def test_unmatched_transaction_when_no_receipt():
    """Reconciliation guarantee (v2 spec §25.5): the system surfaces
    every unmatched transaction; never silently drops them."""
    txs = [tx("t1", "9.99", date(2026, 4, 20))]
    rs: list[Receipt] = []
    out = match_month(txs, rs)
    assert out.unmatched_transactions == ["t1"]
    assert not out.matches


def test_unmatched_receipt_when_no_transaction():
    """Mirror invariant: orphan receipts surface, never silently dropped."""
    txs: list[Transaction] = []
    rs = [receipt("r1", "20.00", date(2026, 4, 20))]
    out = match_month(txs, rs)
    assert out.unmatched_receipts == ["r1"]


def test_amount_within_tip_tolerance_probable():
    """Restaurant tip causes a small receipt/card mismatch — still a
    probable match, flagged for review."""
    txs = [tx("t1", "57.50", date(2026, 4, 22))]
    rs = [receipt("r1", "50.00", date(2026, 4, 22))]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    m = out.matches[0]
    assert m.match_type == MatchType.PROBABLE
    assert m.requires_review


def test_ambiguous_when_two_identical_receipts():
    """Two equally-strong candidates — surface as ambiguous, do not
    auto-pick. Per v2 spec §15.4 ambiguous outcome."""
    txs = [tx("t1", "20.00", date(2026, 4, 25))]
    rs = [
        receipt("r1", "20.00", date(2026, 4, 25)),
        receipt("r2", "20.00", date(2026, 4, 25)),
    ]
    out = match_month(txs, rs)
    assert not out.matches
    assert len(out.ambiguous) == 2


def test_entity_scope_prevents_cross_entity_match():
    """v2 spec §4.2: legal entity is a row-level access field.
    A receipt belonging to a different entity does not match."""
    txs = [tx("t1", "10.00", date(2026, 4, 26))]
    other_entity_receipt = Receipt(
        document_id="r_other",
        legal_entity_id="brisken-uk",
        detected_date=date(2026, 4, 26),
        detected_total=Decimal("10.00"),
        detected_currency="USD",
        detected_vendor="VENDOR",
    )
    out = match_month(txs, [other_entity_receipt])
    assert out.unmatched_transactions == ["t1"]
    assert out.unmatched_receipts == ["r_other"]


def test_reconciliation_guarantee_invariant_holds():
    """v2 spec §25.5: every transaction ends up in exactly one of
    matches / judgment_required / ambiguous / unmatched_transactions.
    Never silently dropped."""
    txs = [
        tx("t-exact", "10.00", date(2026, 4, 1)),
        tx("t-fx", "112.30", date(2026, 4, 2)),
        tx("t-unmatched", "9.99", date(2026, 4, 3)),
    ]
    rs = [
        receipt("r-exact", "10.00", date(2026, 4, 1)),
        receipt("r-fx", "100.00", date(2026, 4, 2), currency="EUR"),
    ]
    out = match_month(txs, rs)

    accounted = set()
    accounted.update(m.transaction_id for m in out.matches)
    accounted.update(m.transaction_id for m in out.judgment_required)
    accounted.update(m.transaction_id for m in out.ambiguous)
    accounted.update(out.unmatched_transactions)
    assert accounted == {"t-exact", "t-fx", "t-unmatched"}


# ── FX candidate gating (3.7 / ANNEALING A1) ────────────────────────
# The 2026-06-11 calibration measured ~50x cross-product overshoot:
# every USD transaction paired with every foreign receipt. These tests
# pin the gate that keeps the plausible FX pairs and drops the rest.


def test_fx_implausible_rate_is_dropped_not_judged():
    """A BRL receipt whose implied rate is nowhere near the BRL->USD
    band is not the same purchase: no FX_JUDGMENT candidate. The
    receipt still surfaces (guarantee), it just isn't paired here."""
    # 50 USD / 100 BRL = implied 0.5 — far outside the [0.15, 0.24] band.
    txs = [tx("t1", "50.00", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", date(2026, 4, 15), currency="BRL")]
    out = match_month(txs, rs)
    assert not out.judgment_required
    assert out.unmatched_transactions == ["t1"]
    assert out.unmatched_receipts == ["r1"]


def test_fx_plausible_rate_emits_judgment():
    """A BRL receipt converting at a plausible rate (implied ~0.19)
    on the same date stays an FX_JUDGMENT candidate for the LLM."""
    # 19 USD / 100 BRL = implied 0.19 — inside [0.15, 0.24].
    txs = [tx("t1", "19.00", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", date(2026, 4, 15), currency="BRL")]
    out = match_month(txs, rs)
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].match_type == MatchType.FX_JUDGMENT


def test_fx_date_too_far_is_dropped():
    """In-band amount but the receipt date is outside the FX window:
    not a candidate (a foreign charge does not post 10 days early)."""
    txs = [tx("t1", "117.00", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", date(2026, 4, 1), currency="EUR")]  # 14d off
    out = match_month(txs, rs)
    assert not out.judgment_required
    assert out.unmatched_receipts == ["r1"]


def test_fx_unprofiled_pair_is_date_gated_but_still_emitted():
    """A currency pair with no band entry must NOT be silently dropped
    (reconciliation guarantee for unmeasured currencies). It is gated
    on date only and still handed to the LLM."""
    txs = [tx("t1", "130.00", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", date(2026, 4, 15), currency="GBP")]
    out = match_month(txs, rs)
    assert len(out.judgment_required) == 1
    assert "unprofiled" in out.judgment_required[0].reason


def test_fx_dateless_receipt_is_not_a_candidate():
    """No receipt date => cannot judge FX plausibility => no candidate.
    The receipt lands in unmatched_receipts, never silently dropped."""
    txs = [tx("t1", "117.00", date(2026, 4, 15))]
    rs = [receipt("r1", "100.00", None, currency="EUR")]
    out = match_month(txs, rs)
    assert not out.judgment_required
    assert out.unmatched_receipts == ["r1"]


# ── Bipartite assignment (3.8 / A2) + vendor signal (3.9 / A3) ───────


def test_bipartite_receipt_not_double_bound():
    """A2: one receipt cannot match two transactions. A $100 EXACT and a
    $98 PROBABLE both want the single $100 receipt; the receipt goes to
    the EXACT tx, the other transaction is left unmatched (not a second
    Matches row on the same receipt)."""
    txs = [
        tx("t-exact", "100.00", date(2026, 4, 10), vendor="AMAZON"),
        tx("t-probable", "98.00", date(2026, 4, 10), vendor="AMAZON"),
    ]
    rs = [receipt("r1", "100.00", date(2026, 4, 10), vendor="AMAZON")]
    out = match_month(txs, rs)
    assert [m.document_id for m in out.matches] == ["r1"]
    assert out.matches[0].transaction_id == "t-exact"
    assert out.unmatched_transactions == ["t-probable"]
    # The receipt is used exactly once across the whole outcome.
    used = [m.document_id for m in out.matches]
    assert used.count("r1") == 1


def test_vendor_signal_breaks_tie_instead_of_ambiguous():
    """3.9: two same-amount same-date receipts that would otherwise tie
    are separated by vendor similarity, so each transaction takes its
    own vendor's receipt — no ambiguous bucket, no double-binding."""
    txs = [
        tx("t-amzn", "100.00", date(2026, 4, 12), vendor="AMAZON MKTP"),
        tx("t-uber", "100.00", date(2026, 4, 12), vendor="UBER TRIP"),
    ]
    rs = [
        receipt("r-amzn", "100.00", date(2026, 4, 12), vendor="Amazon"),
        receipt("r-uber", "100.00", date(2026, 4, 12), vendor="Uber"),
    ]
    out = match_month(txs, rs)
    assert not out.ambiguous
    pairs = {m.transaction_id: m.document_id for m in out.matches}
    assert pairs == {"t-amzn": "r-amzn", "t-uber": "r-uber"}


def test_truly_identical_receipts_still_ambiguous():
    """When the 3.9 signal cannot separate two candidates (same amount,
    date, AND vendor), the tx stays ambiguous — bipartite must not pick
    arbitrarily."""
    txs = [tx("t1", "20.00", date(2026, 4, 25), vendor="KIOSK")]
    rs = [
        receipt("r1", "20.00", date(2026, 4, 25), vendor="Kiosk"),
        receipt("r2", "20.00", date(2026, 4, 25), vendor="Kiosk"),
    ]
    out = match_month(txs, rs)
    assert not out.matches
    assert {a.document_id for a in out.ambiguous} == {"r1", "r2"}


def test_fx_receipt_assigned_to_single_best_transaction():
    """3.8 over FX: a foreign receipt that is in-band for several USD
    transactions is handed to the LLM for ONE best transaction (the
    vendor-closest), not as a pair against every candidate. This is the
    ~50x -> ~1x collapse the calibration targeted."""
    txs = [
        tx("t-near", "19.00", date(2026, 4, 15), vendor="MEGA CENTER"),
        tx("t-far", "19.00", date(2026, 4, 15), vendor="SOME OTHER SHOP"),
    ]
    rs = [receipt("r-brl", "100.00", date(2026, 4, 15), currency="BRL",
                  vendor="Mega Center Comercio")]
    out = match_month(txs, rs)
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].transaction_id == "t-near"
    assert out.judgment_required[0].document_id == "r-brl"
    # The other transaction has no other candidate -> unmatched.
    assert out.unmatched_transactions == ["t-far"]
