"""Item 253 (owner 2026-10-07, "pair by card, book by note").

A company the sender's note set (item 250) decides where a receipt BOOKS,
never which charge it belongs to: the card that paid is unchanged by the
note. Before this, the matcher refused every cross-company pair, so the
2026-10-07 dry runs of item 252 would have left 5 live card charges showing
"no receipt" although the receipt was in the month.

Both places the matcher reads a receipt's company are pinned here: the
deterministic scope (`pair_in_scope`) and the FX second-chance shortlist.
The caller-level proof is `test_a_moved_company_rematches_and_keeps_its_cards_pair`
in `test_sender_note_backfill_252.py`.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import (
    MatchingConfig,
    pair_in_scope,
    pairing_entity,
)
from expense_recon.matching.judgment import _second_chance_shortlist
from expense_recon.matching.types import Receipt, Transaction

CORP = "Corporate Services"
CONSULTING = "Consulting"


def _tx(*, currency="USD", entity=CORP) -> Transaction:
    return Transaction(
        transaction_id="t1", legal_entity_id=entity, account_id="chase-2838",
        transaction_date=date(2026, 9, 21), posting_date=None,
        amount=Decimal("135.00"), transaction_currency=currency,
        account_card_currency="USD", vendor_from_statement="PRESSMASTER",
        card_last4="2838",
    )


def _receipt(*, currency="USD", note_entity="", entity=CONSULTING) -> Receipt:
    return Receipt(
        document_id="r1", legal_entity_id=entity, detected_date=date(2026, 9, 21),
        detected_total=Decimal("135.00") if currency == "USD" else Decimal("120.00"),
        detected_currency=currency, detected_vendor="PressMaster",
        detected_reference=None, payment_mode="Visa ending 2838",
        sender_note_entity=note_entity,
    )


def test_a_note_moved_receipt_pairs_under_no_company():
    moved = _receipt(note_entity=CONSULTING)
    assert pairing_entity(moved) is None
    assert pairing_entity(_receipt()) == CONSULTING


def test_the_deterministic_scope_keeps_the_cards_charge():
    tx = _tx()
    assert pair_in_scope(tx, _receipt(note_entity=CONSULTING), set(), None)
    assert pair_in_scope(tx, _receipt(note_entity=CONSULTING), set(), None,
                         entity_keys={CORP: "822741658", CONSULTING: "808232536"})
    # A company a person (or the card) set still scopes, exactly as before.
    assert not pair_in_scope(tx, _receipt(), set(), None)


def test_a_reviewer_pick_away_from_the_note_scopes_again():
    """Her own pick (a different company from the note's) is a decision
    about the booking AND stays the matcher's scope, as before item 250."""
    picked = replace(_receipt(note_entity=CONSULTING), legal_entity_id="Cloud Services")
    assert pairing_entity(picked) == "Cloud Services"
    assert not pair_in_scope(_tx(), picked, set(), None)


def test_the_fx_shortlist_keeps_a_note_moved_receipt():
    tx = _tx(currency="EUR")
    moved = _receipt(currency="USD", note_entity=CONSULTING)
    plain = replace(_receipt(currency="USD"), document_id="r2")
    shortlist = _second_chance_shortlist(
        tx, [moved, plain], MatchingConfig(), top_k=10, date_window_days=5,
    )
    assert [r.document_id for r in shortlist] == ["r1"]
