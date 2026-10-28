"""Item 243 (owner, 2026-09-28): a slip that prints the card's second number
must not cost the receipt its charge.

The Chase statement marks the corporate card's charges "2838" while its
plastic prints "1672" (`cards.py`: one card, several digit identities). In
item 240's July dry run two Karlsruhe dinners (EUR 30.00 and 47.00, charges
USD 34.39 and 53.80 on 2838) printed "...1672": the uniqueness gate read the
printed digits against the charge's 2838, called the card absent from the
statement and demoted both true pairs.

The gate keeps reading printed evidence (it was calibrated on it: 14 of 14
absent-card coincidences on the labelled fixture were wrong). The change is
what counts as printed: digits the card register resolves FROM THE PRINT
(`card_scope_source` "hint") carry the register card's other numbers with
them. A girocard no register card names, a remembered card and a picked card
change nothing here.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.deterministic import MatchingConfig, match_month  # noqa: E402
from expense_recon.matching.types import MatchType  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from tests.test_card_scope_item_137 import _row  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _expense,
    _extraction,
    _month,
    _wire,
)
from tests.test_fx_ladder import _receipt, _tx  # noqa: E402

PRINTED_1672 = "VISA CREDIT ...1672"


def _printed(mode: str, **scope):
    r = _receipt()
    object.__setattr__(r, "payment_mode", mode)
    return replace(r, **scope) if scope else r


def _demoted(outcome) -> bool:
    return outcome.matches == [] and any(
        m.match_type is MatchType.FX_JUDGMENT and "absent from this statement" in m.reason
        for m in outcome.judgment_required
    )


def test_second_number_the_register_does_not_know_is_still_demoted():
    """Today's live state (the register lists 2838 only): unchanged."""
    assert _demoted(match_month([_tx()], [_printed(PRINTED_1672)], MatchingConfig()))


def test_second_number_read_through_the_register_keeps_its_pair():
    r = _printed(PRINTED_1672, card_scope_keys=("1672", "2838"), card_scope_source="hint")
    outcome = match_month([_tx()], [r], MatchingConfig())
    assert [m.match_type for m in outcome.matches] == [MatchType.FX_BASE_AMOUNT]
    assert outcome.matches[0].card_score == 1.0
    assert not outcome.matches[0].requires_review


def test_a_foreign_card_is_still_demoted():
    """German girocard, no register card names it: the gate's own case."""
    assert _demoted(match_month([_tx()], [_printed("girocard ...6481")], MatchingConfig()))


@pytest.mark.parametrize("source", ["learned", "override"])
def test_a_remembered_or_picked_card_does_not_clear_a_printed_contradiction(source):
    """Only the print read through the register counts as printed evidence;
    item 137's resolved cards keep acting after the gate, as before."""
    r = _printed(PRINTED_1672, card_scope_keys=("2838",), card_scope_source=source)
    assert _demoted(match_month([_tx()], [r], MatchingConfig()))


def test_a_hint_word_prints_no_digits_and_stays_out_of_the_gate():
    """"Visa" assigned to 3645 for the batch (item 137) is not a printed
    card: the gate sees no card on the receipt, exactly as before, and the
    resolved card acts after it (review, never a drop)."""
    r = _printed("Visa", card_scope_keys=("3645",), card_scope_source="hint")
    outcome = match_month([_tx()], [r], MatchingConfig())
    assert not _demoted(outcome)
    assert [m.transaction_id for m in outcome.matches] == ["2838:1"]
    assert outcome.matches[0].requires_review


def test_the_register_resolving_the_print_to_another_card_still_contradicts():
    r = _printed(PRINTED_1672, card_scope_keys=("1672", "3645"), card_scope_source="hint")
    assert _demoted(match_month([_tx()], [r], MatchingConfig()))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _second_number_month(client, monkeypatch, digits):
    cards = {k: dict(v) for k, v in CARDS.items()}
    cards["corp-2838"]["digits"] = digits
    client.put("/api/settings", json={"cards": cards})
    _wire(monkeypatch, _extraction("Enchilada Karlsruhe", "30.00", "2026-08-05",
                                   PRINTED_1672, currency="EUR"))
    batch = _month(client, 1)
    _attach(client, batch, [("2838", datetime(2026, 8, 5), "Enchilada Karlsruhe", "Sale", -34.39)])
    return batch, _expense(client, batch, "Enchilada Karlsruhe")


def test_register_entry_with_the_second_number_resolves_the_slip(client, monkeypatch):
    """The settings half (Criss adds 1672 to the 2838 card): the printed
    second number resolves to that card as a hint, and the month's matcher
    no longer calls the card absent."""
    batch, row = _second_number_month(client, monkeypatch, ["2838", "1672"])
    assert row["card"]["key"] == "corp-2838" and row["card_source"] == "hint"
    tx = _row(client, batch, "2838")
    cand = next(c for c in tx["candidates"] if c["document_id"] == row["document_id"])
    assert "absent from this statement" not in cand["reason"]
    assert "cards_differ" not in tx


def test_without_the_register_entry_the_slip_names_no_card(client, monkeypatch):
    _, row = _second_number_month(client, monkeypatch, ["2838"])
    assert row["card"] is None
