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

from dataclasses import replace
from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import (
    MatchingConfig,
    _card_keys,
    _card_score,
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


# ── WS3 (2026-07-21): the card as a first-class signal ───────────────
#
# The 01-05-2026 corpserv month is the case these cover. Its CSV export
# prints a "Card" column spanning 2838 / 3645 / 3876 / 0340 while the run
# config named one account id for the whole file, so every charge looked
# like it was on the same card. Software subscriptions on 3645 were then
# free to FX-false-pair with EUR meal receipts paid on 2838, purely
# because $16.23 and EUR 16.20 sit inside the EUR->USD plausibility band.


def _tx_carded(tid, amount, card, *, account="chase-2838-family", **kw):
    """A charge whose card comes from the export's per-row Card column,
    not from the account id (the tabular-statement shape)."""
    tx = _tx(tid, amount, account, **kw)
    return replace(tx, card_last4=card)


def test_card_score_reads_agreement_disagreement_and_silence():
    tx_3645 = _tx_carded("t1", "16.23", "3645")
    same = _receipt("r1", "16.20", currency="EUR",
                    payment_mode="1 - CorpServ 3645/1672 (Chase)")
    other = _receipt("r2", "16.20", currency="EUR",
                     payment_mode="1 - CorpServ 2838/1672 (Chase)")
    silent = _receipt("r3", "16.20", currency="EUR", payment_mode=None)

    assert _card_score(tx_3645, same) == 1.0
    assert _card_score(tx_3645, other) == 0.0
    # Unknown is not disagreement: it must sort above a contradiction so a
    # receipt with no payment mode is never pushed below a wrong-card pair.
    assert _card_score(tx_3645, silent) == 0.5
    assert _card_score(tx_3645, silent) > _card_score(tx_3645, other)


def test_per_row_card_stops_the_software_vs_food_fx_false_pair():
    """The ADOBE case. A USD software charge on card 3645 and a EUR meal
    receipt paid on card 2838 convert into each other's range, so amount
    and date alone pair them into judgment_required. The per-row card is
    what rejects it.

    The statement carries a 2838 charge as well, which is what the real
    export looks like and what lets scoping act: the receipt's card is
    present in this statement, so the receipt is scoped to it and the 3645
    charge is not a candidate at all."""
    adobe = _tx_carded("chase-2838-family:44", "16.23", "3645",
                       vendor="ADOBE  *800-833-6687")
    other_card_charge = _tx_carded("chase-2838-family:9", "500.00", "2838",
                                   vendor="HOTEL")
    lunch = _receipt("ER-00216#004", "16.20", currency="EUR",
                     payment_mode="1 - CorpServ 2838/1672 (Chase)",
                     vendor=None)

    out = match_month([adobe, other_card_charge], [lunch])
    assert not out.matches
    assert not out.judgment_required
    assert sorted(out.unmatched_transactions) == [
        "chase-2838-family:44", "chase-2838-family:9",
    ]
    assert out.unmatched_receipts == ["ER-00216#004"]


def test_receipt_card_absent_from_statement_stays_unscoped_but_scores_zero():
    """The conservative half of the design. When the receipt's card is not
    in this statement at all (a single-card export, a partial download), the
    receipt is deliberately left UNSCOPED so a real match is never excluded
    on evidence we do not have. The pair still forms, but it carries
    `card_score=0.0`, which is what demotes it in the tie-break and what the
    FX judgment layer then hands the model as evidence to reject it."""
    adobe = _tx_carded("chase-2838-family:44", "16.23", "3645",
                       vendor="ADOBE  *800-833-6687")
    lunch = _receipt("ER-00216#004", "16.20", currency="EUR",
                     payment_mode="1 - CorpServ 2838/1672 (Chase)")

    out = match_month([adobe], [lunch])
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].card_score == 0.0


def test_without_the_card_column_the_false_pair_still_forms():
    """The same two rows, ingested from a config that never mapped the Card
    column: `card_last4` is None, both sides fall back to the single account
    id, and the pair reaches judgment. This is the pre-WS3 behaviour and the
    reason the run config's column map matters."""
    adobe = _tx("chase-2838-family:44", "16.23", "chase-2838-family",
                vendor="ADOBE  *800-833-6687")
    lunch = _receipt("ER-00216#004", "16.20", currency="EUR",
                     payment_mode="1 - CorpServ 2838/1672 (Chase)")

    out = match_month([adobe], [lunch])
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].match_type == MatchType.FX_JUDGMENT


def test_matching_card_still_pairs():
    """The guard must not cost a real match: same charge, same receipt, but
    the expense report names the card the charge is actually on."""
    charge = _tx_carded("chase-2838-family:12", "17.50", "2838", vendor="RISTORANTE")
    receipt = _receipt("ER-00216#004", "16.20", currency="EUR",
                       payment_mode="1 - CorpServ 2838/1672 (Chase)",
                       vendor="Ristorante")

    out = match_month([charge], [receipt])
    assert len(out.judgment_required) == 1
    assert out.judgment_required[0].card_score == 1.0


def test_card_score_rides_on_every_match_for_the_reviewer():
    """A plain same-currency match carries the card verdict too, so the
    workbench can explain the pairing without re-deriving it."""
    charge = _tx_carded("chase-2838-family:12", "42.50", "2838")
    receipt = _receipt("r1", "42.50",
                       payment_mode="1 - CorpServ 2838/1672 (Chase)")
    out = match_month([charge], [receipt])
    assert out.matches[0].match_type == MatchType.EXACT
    assert out.matches[0].card_score == 1.0


def test_card_breaks_the_tie_when_scoping_is_off():
    """With `card_scoping` off (the pre-2026-06-16 parity switch) nothing
    filters cross-card pairs, so two receipts that agree on amount, date,
    and vendor would tie and land in `ambiguous` for a human. The card
    separates them instead: the one on the charge's own card wins and the
    transaction resolves without review of a false ambiguity."""
    cfg = MatchingConfig(card_scoping=False)
    charge = _tx_carded("chase-2838-family:12", "42.50", "3645")
    right = _receipt("r-right", "42.50",
                     payment_mode="1 - CorpServ 3645/1672 (Chase)")
    wrong = _receipt("r-wrong", "42.50",
                     payment_mode="1 - CorpServ 2838/1672 (Chase)")

    out = match_month([charge], [right, wrong], cfg)
    assert not out.ambiguous
    assert [m.document_id for m in out.matches] == ["r-right"]
    assert out.unmatched_receipts == ["r-wrong"]
