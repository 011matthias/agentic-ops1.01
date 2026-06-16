"""Matching precision (2026-06-16, slice 3).

Two refinements over the implied-rate-band FX path and the cross-card
candidate set:

1. Card-scoped matching: an expense whose Zoho payment mode names a card
   only reconciles against charges on that card (its statement account_id),
   keyed off the digit overlap between the marker and the payment-mode label.
2. Exact FX: when the Chase statement captured the charge's own original
   amount + currency (the two-line FX detail), and the receipt is in that
   currency, the match resolves deterministically on the original amount,
   never the implied-rate band and never the LLM.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import (
    MatchingConfig,
    _card_keys,
    match_month,
)
from expense_recon.matching.types import MatchType, Receipt, Transaction

LE = "brisken-us"


def _tx(tid, amount, account, *, currency="USD", txdate=date(2026, 1, 6),
        original_amount=None, original_currency=None, fx_rate=None, vendor="VENDOR"):
    return Transaction(
        transaction_id=tid, legal_entity_id=LE, account_id=account,
        transaction_date=txdate, posting_date=None,
        amount=Decimal(amount), transaction_currency=currency,
        account_card_currency="USD", vendor_from_statement=vendor,
        original_amount=Decimal(original_amount) if original_amount else None,
        original_currency=original_currency,
        fx_rate=Decimal(fx_rate) if fx_rate else None,
    )


def _receipt(rid, amount, *, currency="USD", rdate=date(2026, 1, 6),
             payment_mode=None, vendor="VENDOR"):
    return Receipt(
        document_id=rid, legal_entity_id=LE,
        detected_date=rdate, detected_total=Decimal(amount) if amount else None,
        detected_currency=currency, detected_vendor=vendor,
        payment_mode=payment_mode,
    )


# ── _card_keys normalization ─────────────────────────────────────────


def test_card_keys_overlap_marker_and_payment_mode():
    # the statement marker "2838" and the Zoho mode "...2838/1672..." overlap
    assert _card_keys("2838") & _card_keys("1 - CorpServ 2838/1672 (Chase)")
    # "0340" marker and a "...340..." last-4 land on the same key
    assert _card_keys("0340") & _card_keys("Amex ending 340")
    # no shared card -> no overlap
    assert not (_card_keys("3645") & _card_keys("1 - CorpServ 2838/1672 (Chase)"))
    # a label with no card number scopes nothing
    assert _card_keys("Cash") == set()
    assert _card_keys(None) == set()


# ── card-scoped matching ─────────────────────────────────────────────


def test_receipt_scoped_to_its_card_not_a_same_amount_charge_on_another():
    """Two cards each have a $100 charge on the same day; the receipt names
    card 2838 in its payment mode, so it matches the 2838 charge, not the
    equally-plausible 3645 charge."""
    txs = [
        _tx("2838:1", "100.00", "2838"),
        _tx("3645:1", "100.00", "3645"),
    ]
    rs = [_receipt("r1", "100.00", payment_mode="1 - CorpServ 2838/1672 (Chase)")]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert out.matches[0].transaction_id == "2838:1"   # scoped to its card
    assert out.matches[0].document_id == "r1"
    assert "3645:1" in out.unmatched_transactions       # the other card untouched


def test_scoping_falls_back_when_named_card_absent_from_statement():
    """A payment mode naming a card NOT in this statement (personal card)
    must not exclude the receipt entirely — it stays unscoped so a real
    same-card match is never lost to the guarantee. Here only card 3645 is
    present; the receipt names a 9999 card, so it is matched unscoped."""
    txs = [_tx("3645:1", "75.00", "3645")]
    rs = [_receipt("r1", "75.00", payment_mode="Personal Visa 9999")]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert out.matches[0].transaction_id == "3645:1"


def test_scoping_disabled_restores_cross_card_behaviour():
    txs = [_tx("2838:1", "100.00", "2838"), _tx("3645:1", "100.00", "3645")]
    rs = [_receipt("r1", "100.00", payment_mode="CorpServ 3645")]
    # With scoping on, the receipt only matches 3645. With it off, the greedy
    # assignment is free to pick either equally-scored charge.
    out_off = match_month(txs, rs, MatchingConfig(card_scoping=False))
    assert len(out_off.matches) == 1  # one receipt, one charge (cross-card allowed)


def test_receipt_without_payment_mode_is_unscoped():
    """A slice-1 receipt (no payment mode) matches as before — no scoping."""
    txs = [_tx("2838:1", "42.50", "2838")]
    rs = [_receipt("r1", "42.50")]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert out.matches[0].match_type == MatchType.EXACT


# ── exact FX on the statement's captured original amount ─────────────


def test_exact_fx_resolves_deterministically_not_via_llm():
    """The statement captured EUR 27.00 (posted USD 31.73); the receipt is
    EUR 27.00. The match is EXACT on the original amount — no FX_JUDGMENT,
    no LLM."""
    txs = [_tx("2838:1", "31.73", "2838",
               original_amount="27.00", original_currency="EUR", fx_rate="1.175185185")]
    rs = [_receipt("r1", "27.00", currency="EUR")]
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert not out.judgment_required          # did NOT fall to the LLM layer
    m = out.matches[0]
    assert m.match_type == MatchType.EXACT
    assert "original currency EUR" in m.reason


def test_exact_fx_probable_with_tip_on_original_amount():
    """A tip added in local currency keeps the pair a (review-flagged)
    PROBABLE match on the original amount, still deterministic."""
    txs = [_tx("2838:1", "47.00", "2838",
               original_amount="40.00", original_currency="EUR", fx_rate="1.175")]
    rs = [_receipt("r1", "35.00", currency="EUR")]  # printed before a 5 EUR tip
    out = match_month(txs, rs)
    assert len(out.matches) == 1
    assert out.matches[0].match_type == MatchType.PROBABLE
    assert not out.judgment_required


def test_exact_fx_decline_with_implausible_rate_is_unmatched_not_dropped():
    """When the receipt's amount disagrees with the captured original AND the
    implied USD->EUR rate is implausible (a different purchase entirely), there
    is no match: the charge and the receipt both surface as unmatched, never a
    silent drop and never a wrong pairing (reconciliation guarantee). The band
    path drops out-of-band pairs rather than handing them to the LLM; with the
    captured original amount in hand, an in-band same-currency receipt is
    already within tolerance of the original, so exact-FX subsumes it."""
    txs = [_tx("2838:1", "118.00", "2838",
               original_amount="100.00", original_currency="EUR", fx_rate="1.18")]
    rs = [_receipt("r1", "60.00", currency="EUR")]  # 118/60 = 1.97, out of band
    out = match_month(txs, rs)
    assert not out.matches
    assert not out.judgment_required
    assert out.unmatched_transactions == ["2838:1"]
    assert out.unmatched_receipts == ["r1"]


def test_exact_fx_only_when_currencies_agree():
    """Captured original is EUR but the receipt is BRL — the exact path does
    not fire (different currency); it routes to the band/judgment layer."""
    txs = [_tx("2838:1", "31.73", "2838",
               original_amount="27.00", original_currency="EUR", fx_rate="1.17")]
    rs = [_receipt("r1", "150.00", currency="BRL")]
    out = match_month(txs, rs)
    assert not out.matches
    # BRL has a band; the implied rate 31.73/150 = 0.21 is in [0.15, 0.26].
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].match_type == MatchType.FX_JUDGMENT
