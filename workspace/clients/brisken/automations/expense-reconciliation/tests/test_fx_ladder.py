"""The deterministic FX ladder + uniqueness gate (2026-07-23).

Pins the date+amount accuracy push: the base-amount path, self-derived
reference rates, the band-scoring fix, review-zone deferral, and the
bilateral-uniqueness demotion. Fixture numbers mirror the real April
month (BRL receipts on a USD card, Zoho rate ~0.1939).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.matching.deterministic import (
    MatchingConfig,
    derive_fx_reference_rates,
    match_month,
    match_one,
)
from expense_recon.matching.types import MatchType, Receipt, Transaction


def _tx(
    tx_id: str = "2838:1",
    amount: str = "9.69",
    day: int = 1,
    vendor: str = "ERICK SPORTS",
) -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        legal_entity_id="corpserv",
        account_id="2838",
        transaction_date=date(2026, 4, day),
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement=vendor,
    )


def _receipt(
    doc: str = "ER#001",
    total: str = "49.98",
    day: int = 1,
    base: str | None = "9.69",
    rate: str | None = "0.193945",
    vendor: str = "Erick Sports",
) -> Receipt:
    return Receipt(
        document_id=doc,
        legal_entity_id="corpserv",
        detected_vendor=vendor,
        detected_date=date(2026, 4, day),
        detected_total=Decimal(total),
        detected_currency="BRL",
        base_amount=Decimal(base) if base else None,
        exchange_rate=Decimal(rate) if rate else None,
    )


# ── base-amount rung ───────────────────────────────────────────────────


def test_base_amount_clean_resolves_deterministically():
    m = match_one(_tx(), _receipt(), MatchingConfig())
    assert m is not None
    assert m.match_type is MatchType.FX_BASE_AMOUNT
    assert not m.requires_review
    assert "Zoho's per-receipt rate" in m.reason


def test_base_amount_works_without_a_printed_total():
    """A receipt whose printed total failed to parse still resolves off
    Zoho's own conversion — previously structurally unmatchable."""
    r = _receipt(total="49.98")
    object.__setattr__(r, "detected_total", None)
    m = match_one(_tx(), r, MatchingConfig())
    assert m is not None and m.match_type is MatchType.FX_BASE_AMOUNT


def test_base_amount_review_zone_defers_to_judgment():
    """2-13% deviation is too loose to auto-match (the no_charge
    false-positive engine); it tees the pair up for judgment instead."""
    m = match_one(_tx(amount="10.30"), _receipt(), MatchingConfig())
    assert m is not None
    assert m.match_type is MatchType.FX_JUDGMENT
    assert m.requires_review


def test_unknown_currency_still_refused():
    r = _receipt()
    object.__setattr__(r, "detected_currency", None)
    assert match_one(_tx(), r, MatchingConfig()) is None


# ── self-derived rates ─────────────────────────────────────────────────


def test_receipt_median_rate_derives_at_min_samples():
    receipts = [
        _receipt(doc=f"ER#{i}", rate=r)
        for i, r in enumerate(["0.190", "0.194", "0.198"])
    ]
    out = derive_fx_reference_rates([_tx()], receipts, MatchingConfig())
    assert out[("BRL", "USD")][0] == Decimal("0.194")
    assert out[("BRL", "USD")][1] == "receipts"


def test_below_min_receipt_samples_derives_nothing():
    receipts = [_receipt(doc="ER#0"), _receipt(doc="ER#1")]
    out = derive_fx_reference_rates([_tx()], receipts, MatchingConfig())
    assert out == {}


def test_statement_fx_lines_outrank_receipt_median():
    tx = Transaction(
        transaction_id="2838:9",
        legal_entity_id="corpserv",
        account_id="2838",
        transaction_date=date(2026, 4, 2),
        posting_date=None,
        amount=Decimal("19.20"),
        transaction_currency="USD",
        account_card_currency="USD",
        vendor_from_statement="X",
        original_amount=Decimal("100.00"),
        original_currency="BRL",
        fx_rate=Decimal("0.192"),
    )
    receipts = [
        _receipt(doc=f"ER#{i}", rate="0.250") for i in range(3)
    ]  # in-band but different
    out = derive_fx_reference_rates([tx], receipts, MatchingConfig())
    assert out[("BRL", "USD")] == (Decimal("0.192"), "statement", 1)


def test_derived_rate_outside_band_is_discarded():
    """Poisoned-median clamp: an implausible median never becomes the
    month's rate."""
    receipts = [_receipt(doc=f"ER#{i}", rate="0.50") for i in range(3)]
    out = derive_fx_reference_rates([_tx()], receipts, MatchingConfig())
    assert out == {}


def test_kill_switch_restores_prior_behaviour():
    receipts = [_receipt(doc=f"ER#{i}") for i in range(3)]
    cfg = MatchingConfig(fx_self_derived_rates=False)
    assert derive_fx_reference_rates([_tx()], receipts, cfg) == {}


def test_derived_rate_resolves_via_reference_path():
    """No base_amount, no configured rate: the derived median still
    resolves the pair deterministically through FX_REFERENCE."""
    target = _receipt(doc="ER#T", total="50.00", base=None, rate=None)
    donors = [
        _receipt(doc=f"ER#{i}", day=20 + i, rate="0.194") for i in range(3)
    ]
    tx = _tx(amount="9.70")  # 50.00 * 0.194 = 9.70 exactly
    outcome = match_month([tx], [target] + donors, MatchingConfig())
    got = {(m.transaction_id, m.document_id) for m in outcome.matches}
    assert (tx.transaction_id, "ER#T") in got
    m = next(m for m in outcome.matches if m.document_id == "ER#T")
    assert m.match_type is MatchType.FX_REFERENCE
    assert "derived rate" in m.reason and "median of 3 receipt rates" in m.reason


# ── uniqueness gate ────────────────────────────────────────────────────


def test_contested_receipt_is_demoted_to_judgment():
    """Two charges agree equally cleanly with one receipt's base amount:
    neither may auto-match; both candidates defer."""
    t1, t2 = _tx("2838:1", "9.69"), _tx("2838:2", "9.69", vendor="OTHER")
    outcome = match_month([t1, t2], [_receipt()], MatchingConfig())
    assert outcome.matches == []
    assert {m.match_type for m in outcome.judgment_required} <= {
        MatchType.FX_JUDGMENT
    }
    assert any(
        "Demoted to judgment" in m.reason for m in outcome.judgment_required
    )


def test_charge_with_two_clean_receipts_is_demoted():
    r1 = _receipt("ER#1")
    r2 = _receipt("ER#2", vendor="Someone Else")
    outcome = match_month([_tx()], [r1, r2], MatchingConfig())
    assert outcome.matches == []


def test_unique_pair_keeps_its_deterministic_right():
    outcome = match_month([_tx()], [_receipt()], MatchingConfig())
    assert len(outcome.matches) == 1
    assert outcome.matches[0].match_type is MatchType.FX_BASE_AMOUNT


def test_exact_fx_is_not_subject_to_the_uniqueness_gate():
    """Statement-original-amount agreement is bank-printed on both sides;
    two exact-FX charges for one receipt go through the existing
    ambiguity machinery, not the demotion."""
    def mk(tx_id: str) -> Transaction:
        return Transaction(
            transaction_id=tx_id,
            legal_entity_id="corpserv",
            account_id="2838",
            transaction_date=date(2026, 4, 1),
            posting_date=None,
            amount=Decimal("9.69"),
            transaction_currency="USD",
            account_card_currency="USD",
            vendor_from_statement="ERICK SPORTS",
            original_amount=Decimal("49.98"),
            original_currency="BRL",
            fx_rate=Decimal("0.193945"),
        )

    outcome = match_month([mk("2838:1"), mk("2838:2")], [_receipt()], MatchingConfig())
    # One receipt, two identical exact-FX claimants -> the ambiguity
    # machinery owns it (one wins or it ties); never a silent demotion.
    assert len(outcome.matches) + len(outcome.ambiguous) >= 1


# ── card-contradiction gate (matcher-v2, 2026-07-23) ───────────────────


def test_absent_card_coincidence_is_demoted_to_judgment():
    """A bilaterally-unique clean base-amount pair whose receipt was paid on
    a card ABSENT from this statement is a same-vendor/same-day coincidence,
    not a match: its true charge is on the other card's statement. Demote to
    judgment even though (date, amount) agree cleanly and uniquely. This is
    the 14/14 no_charge false-positive class on the labelled fixture."""
    tx = _tx()  # account_id "2838" is the only card present
    r = _receipt()
    object.__setattr__(r, "payment_mode", "3 - Cloud 6013 / 2155 (Chase)")
    outcome = match_month([tx], [r], MatchingConfig())
    assert outcome.matches == []
    assert any(
        m.match_type is MatchType.FX_JUDGMENT
        and "absent from this statement" in m.reason
        for m in outcome.judgment_required
    )


def test_same_card_unique_pair_still_auto_resolves():
    """Control: the identical unique clean pair, but the receipt's payment
    mode names the card the charge is on. Card corroborates — it keeps its
    deterministic right. Guards against the gate over-firing on true pairs
    (0/55 true fixture pairs were lost to it)."""
    tx = _tx()  # card 2838
    r = _receipt()
    object.__setattr__(r, "payment_mode", "1 - CorpServ 2838/1672 (Chase)")
    outcome = match_month([tx], [r], MatchingConfig())
    assert len(outcome.matches) == 1
    assert outcome.matches[0].match_type is MatchType.FX_BASE_AMOUNT


def test_card_gate_inert_when_card_scoping_off():
    """The contradiction gate rides the same trust switch as card scoping:
    a run that declares card data untrustworthy (card_scoping=False) does
    not apply the contradiction either, so the absent-card pair keeps its
    prior uniqueness-only behaviour."""
    tx = _tx()
    r = _receipt()
    object.__setattr__(r, "payment_mode", "3 - Cloud 6013 / 2155 (Chase)")
    outcome = match_month([tx], [r], MatchingConfig(card_scoping=False))
    assert len(outcome.matches) == 1
    assert outcome.matches[0].match_type is MatchType.FX_BASE_AMOUNT


# ── band-scoring fix ───────────────────────────────────────────────────


def test_true_pair_at_band_edge_outscores_junk_at_midpoint():
    """Configured rate 0.16 (near the BRL band's low edge): the pair that
    agrees with the RATE must outscore the pair whose implied rate merely
    sits at the band midpoint. Fails under the old midpoint-distance
    scoring."""
    cfg = MatchingConfig(
        fx_reference_rates={("BRL", "USD"): Decimal("0.16")},
        fx_reference_match_pct=Decimal("0.001"),  # force both to the band
        fx_reference_review_pct=Decimal("0.011"),
    )
    true_pair = match_one(
        _tx(amount="16.08"), _receipt(total="100.00", base=None), cfg
    )  # implied 0.1608, dev vs rate 0.5% -> above match_pct, above review -> band
    junk_pair = match_one(
        _tx(tx_id="2838:2", amount="20.50", vendor="ZZZ"),
        _receipt(doc="ER#2", total="100.00", base=None, vendor="Unrelated"),
        cfg,
    )  # implied 0.2050 ~ midpoint of [0.15, 0.26]
    assert true_pair is not None and junk_pair is not None
    assert true_pair.match_type is MatchType.FX_JUDGMENT
    assert junk_pair.match_type is MatchType.FX_JUDGMENT
    assert true_pair.amount_score > junk_pair.amount_score
    assert true_pair.score > junk_pair.score


# ── tunables round-trip ────────────────────────────────────────────────


def test_new_tunables_load_from_dict():
    cfg = MatchingConfig.from_dict({
        "fx_base_amount_match_pct": "0.01",
        "fx_base_amount_review_pct": "0.10",
        "fx_band_score_span_pct": "0.20",
        "fx_self_derived_rates": False,
        "fx_self_derived_min_receipts": 5,
        "fx_self_derived_min_statement_rates": 2,
        "fx_self_derived_review": True,
    })
    assert cfg.fx_base_amount_match_pct == Decimal("0.01")
    assert cfg.fx_self_derived_min_receipts == 5
    assert cfg.fx_self_derived_rates is False


def test_unknown_tunable_still_raises():
    with pytest.raises(ValueError):
        MatchingConfig.from_dict({"fx_base_amount_typo_pct": "0.01"})
