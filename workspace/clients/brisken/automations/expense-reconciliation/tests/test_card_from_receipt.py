"""The paying card, read off the scan (2026-08-24).

Backlog item 28. The card decides which company an expense books to, and the
April batch showed the extractor could not read it: asked to transcribe four
faded digits it landed 2 in 5 and INVENTED the rest -- "1234" came back three
separate times, once for a receipt that plainly prints 1672, and once for one
that prints 0340. Repeat reads were no help: three reads of each problem image
returned the identical wrong answer every time, so the misreads are stable, not
noisy, and no amount of re-asking finds them.

What worked is changing the question. The answer only ever has to be one of the
handful of cards Brisken holds, so the extractor is handed those last-4s and
asked WHICH ONE it can see, or none. Measured over the same images: 4 of 5 real
cards found with ZERO false positives on the two receipts that print no
readable card, and the invented 1234 became the correct 1672.

Pinned here: the confirmed pick replaces whatever digits the free-text hint
carried, a hint with no confirmed pick passes through untouched, and a partly
read number never reaches the entity chain.
"""
from __future__ import annotations

import pytest

from expense_recon.cli import _known_card_digits
from expense_recon.ingest.receipts_folder import _payment_mode
from expense_recon.llm.client import (
    _card_last4,
    _temperature_for,
    _extraction_from_payload,
)


def _extraction(**over):
    base = {
        "date": "2026-04-02", "total": "42.50", "currency": "BRL",
        "vendor": "MEGA CENTER", "vendor_clean": "MEGA CENTER", "reference": "",
        "tax": None, "tax_label": None, "payment_hint": None,
        "card_last4": None, "line_items": [], "confidence": 0.9, "notes": "",
        "document_type": "receipt",
    }
    base.update(over)
    return _extraction_from_payload(base)


# -- what counts as an answer -----------------------------------------


def test_only_four_digits_are_a_card():
    # Masking survives; the digits are the answer.
    assert _card_last4("0340") == "0340"
    assert _card_last4("****0340") == "0340"
    assert _card_last4("xxxxxxxxxxxx1672") == "1672"
    # Everything that is not four digits is not an answer to the question.
    for junk in (None, "", "none", "Visa", "Cartão de Crédito", "034",
                 "12345", "4****0340"):
        assert _card_last4(junk) is None, junk


def test_a_partly_read_number_never_reaches_the_chain():
    """The failure this guards: "CREDITO 4****0340" reads like a card and is
    five digits. Parsing it generously would hand the entity chain a number
    nobody printed."""
    assert _extraction(card_last4="4****0340").card_last4 is None
    assert _extraction(card_last4="0340").card_last4 == "0340"


# -- the hint the entity chain resolves against ------------------------


def test_a_confirmed_card_replaces_the_digits_the_hint_guessed():
    """receipt_03 verbatim: the receipt prints VISA CREDIT ...1672 and the
    free-text hint came back "Visa ...1234". The confirmed pick wins, and the
    tender words survive because they are what the receipt says."""
    assert _payment_mode(_extraction(payment_hint="Visa ...1234",
                                     card_last4="1672")) == "Visa ...1672"
    # receipt_34: the hint dropped the digits entirely; the pick supplies them.
    assert _payment_mode(_extraction(payment_hint="VISA (CREDITO)",
                                     card_last4="0340")) == "VISA (CREDITO) ...0340"
    # A masked run inside the hint is not left beside the confirmed one.
    assert _payment_mode(_extraction(payment_hint="CREDITO 4****0340",
                                     card_last4="0340")) == "CREDITO ...0340"


def test_a_hint_with_no_confirmed_card_passes_through_untouched():
    """An unlisted digit run resolves to no card anyway, and dropping it would
    hide a card the registry has not been told about yet -- which is exactly
    the live 0340 case (8 April rows, no registry entry)."""
    assert _payment_mode(_extraction(payment_hint="Visa ...9340")) == "Visa ...9340"
    assert _payment_mode(
        _extraction(payment_hint="Cartão de Crédito")
    ) == "Cartão de Crédito"
    assert _payment_mode(_extraction(payment_hint=None)) is None


def test_a_confirmed_card_with_no_hint_still_identifies_the_card():
    assert _payment_mode(_extraction(payment_hint=None, card_last4="2838")) == "...2838"


def test_the_confirmed_card_actually_reaches_the_receipt():
    """Wiring, not the helper. Everything above calls `_payment_mode`
    directly, so it would all still pass if the ingest never called it --
    which is how a card fix ships doing nothing. This goes through the
    function that builds the Receipt the entity chain resolves against."""
    from expense_recon.ingest.receipts_folder import _to_receipt

    receipt = _to_receipt(
        _extraction(payment_hint="Visa ...1234", card_last4="1672"),
        document_id="receipt_03_p9.png",
        legal_entity_id="",
        default_currency=None,
        ocr_text="",
    )
    assert receipt.payment_mode == "Visa ...1672"


# -- the list the model chooses from -----------------------------------


def test_every_digit_identity_of_every_active_card_is_offered():
    """One physical card carries several identities: the Chase statement
    prints 2838 and the plastic prints 1672. A receipt shows whichever the
    terminal knows, so both have to be on the list or half the reads miss."""
    cfg = {"expense": {"cards": {
        "corp": {"label": "Corporate (Chase)", "digits": ["2838", "1672"],
                 "entity": "Corporate Services"},
        "cloud": {"label": "Cloud", "digits": ["0340"], "entity": "Cloud Services"},
    }}}
    assert _known_card_digits(cfg) == ["2838", "1672", "0340"]


def test_a_retired_card_is_not_offered():
    cfg = {"expense": {"cards": {
        "live": {"label": "L", "digits": ["2838"], "entity": "X"},
        "dead": {"label": "D", "digits": ["9999"], "entity": "X", "active": False},
    }}}
    assert _known_card_digits(cfg) == ["2838"]


def test_no_registry_means_no_list_and_no_pick():
    """Deny by default: with nothing to choose from, the extractor is told to
    return null rather than transcribe digits blind."""
    assert _known_card_digits({}) == []
    assert _known_card_digits({"expense": {}}) == []
    assert _known_card_digits({"expense": {"cards": {}}}) == []


# -- the model that reads them ----------------------------------------


def test_the_card_list_is_part_of_the_cache_key():
    """The same photo asked against a different set of cards is a different
    question. Serving the stored answer would pin a card the payer no longer
    holds -- and with no list the key stays exactly what it was."""
    pytest.importorskip("openai")
    from expense_recon.llm.client import OpenAIClient

    none = OpenAIClient(api_key="k", known_cards=None)
    some = OpenAIClient(api_key="k", known_cards=["2838"])
    more = OpenAIClient(api_key="k", known_cards=["2838", "0340"])
    assert none.known_cards == []
    assert some.known_cards == ["2838"]
    assert more.known_cards != some.known_cards


def test_gpt5_is_not_sent_a_temperature_it_rejects():
    """gpt-5 400s on temperature at all, and it is the model that reads these
    receipts; determinism is worth less than reading them correctly."""
    assert _temperature_for("gpt-4o-mini") == {"temperature": 0}
    assert _temperature_for("gpt-5-mini") == {}
    assert _temperature_for("gpt-5") == {}
