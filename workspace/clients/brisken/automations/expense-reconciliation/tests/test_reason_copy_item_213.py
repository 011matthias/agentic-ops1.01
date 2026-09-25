"""Item 213 (owner note #87, 2026-09-25): the review lines say one thing each.

The note sat on September's `waits_for_statement` line, which joined every
active card whose statements miss the row's date: all nine company cards,
404 characters, on 19 rows. Now the sentence names the cards only when one
or two are waiting, and says the plain fact otherwise; the full list stays
on `review.waits_for_statements` for anything that wants it.

The next-longest lines lose their explanation clauses and keep every
instruction: correct or keep a date, confirm private or assign the card, set
the entity on a row paid outside the cards.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    WAITS_NAMED_MAX,
    _expense_review,
    waits_for_statement_sentence,
)
from tests.test_case9_status_c9 import (  # noqa: E402
    CYCLE,
    FAMILY,
    JULY_EXPORT,
    _client,
    _done,
    _month,
    _receipt,
    _rows,
    _statement,
)

GENERIC = "No card on this receipt, and no statement is loaded for its date yet."


# ── the waiting line, through the route ─────────────────────────────────


def test_one_waiting_card_is_named_in_a_short_line(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-07-15", "88.00", "Acme Tools"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": {**FAMILY, **CYCLE}}).status_code == 200
        july = _month(client, "July 2026", 2)
        _done(client, _statement(client, july, JULY_EXPORT))
        review = _rows(client, july)["Acme Tools"]["review"]
        assert review["reason_code"] == "waits_for_statement"
        assert review["reason"] == (
            "No card on this receipt; waiting for the statement of "
            "BCS Chase Visa - 9693."
        )
        assert review["waits_for_statements"] == ["BCS Chase Visa - 9693"]


def test_every_card_waiting_names_none_and_keeps_the_list(tmp_path, monkeypatch):
    """July's export ends Aug 3, so an Aug 20 receipt waits on all three
    family cards: the line stops listing them, the field still carries all."""
    with _client(tmp_path, monkeypatch, [
        _receipt("2026-07-01", "42.50", "Staples"),
        _receipt("2026-08-20", "12.00", "Late Cafe"),
    ]) as client:
        assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
        july = _month(client, "July 2026", 1)
        _done(client, _statement(client, july, JULY_EXPORT))
        august = _month(client, "August 2026", 1)
        row = _rows(client, august)["Late Cafe"]
        labels = sorted(c["label"] for c in FAMILY.values())
        assert len(labels) > WAITS_NAMED_MAX
        assert row["review"]["reason_code"] == "waits_for_statement"
        assert row["review"]["reason"] == GENERIC
        assert not any(label in row["review"]["reason"] for label in labels)
        assert row["review"]["waits_for_statements"] == labels
        assert row["waits_for_statements"] == labels


def test_the_sentence_names_up_to_two_cards():
    assert waits_for_statement_sentence(["A - 1176", "B - 9693"]) == (
        "No card on this receipt; waiting for the statement of A - 1176, B - 9693."
    )
    nine = [f"Card - {n:04d}" for n in range(9)]
    assert waits_for_statement_sentence(nine) == GENERIC
    assert waits_for_statement_sentence([]) == GENERIC


# ── the other long lines keep their instruction, lose the rest ──────────


def _rec(**over):
    base = dict(
        document_id="doc-1", legal_entity_id="",
        detected_date=date(2026, 7, 4), detected_total=Decimal("15.00"),
        detected_currency="USD", detected_vendor="Shop",
    )
    base.update(over)
    return Receipt(**base)


def test_a_date_outside_the_month_says_what_to_do_in_one_sentence():
    review = _expense_review(
        _rec(detected_date=date(2022, 4, 26)), {},
        period=(date(2026, 7, 1), date(2026, 7, 31)),
    )
    assert review["reason_code"] == "date_outside_period"
    assert review["reason"] == (
        "Dated 2022-04-26, outside this batch's month. Check the receipt and "
        "correct the date, or leave it if it really is that old."
    )


def test_a_suggested_private_row_keeps_both_ways_out():
    review = _expense_review(_rec(), {}, entity="", suggested_private=True)
    assert review["reason_code"] == "suggested_private"
    assert review["reason"] == (
        "No company card matches this payment method, so it looks private. "
        "Confirm it as private and name who gets reimbursed, or assign or "
        "register the company card."
    )


def test_a_row_settled_outside_asks_for_the_entity_only():
    review = _expense_review(_rec(), {}, entity="", settled_outside=True)
    assert review["reason_code"] == "needs_entity_settled_outside"
    assert review["reason"] == (
        "This was settled outside the card system, so no card names the "
        "company. Set the legal entity on the row."
    )
