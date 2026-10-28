"""Item 137 (owner, 2026-09-17): "the expense to statement matching is not
separated by cards."

Before, a receipt was scoped to a card only when its own payment mode PRINTED
a card present on the statement. The card the tool resolved for it (a pick on
the row, a hint word assigned to a card, a card remembered from an earlier
month) never reached the matcher, so an unprinted receipt competed for every
card's charges. Now:

* a card picked by hand scopes the receipt to that card in any contest;
* when the picked card has no candidate at all, the other card's charge is
  kept but flagged "the cards differ" and asks for review (live August 2026:
  LOVABLE 25.00 on 3645, the bank's line, with a receipt picked as 2838);
* a hint or remembered card never drops a pair: a pair on another card asks
  for review and ranks below a pair on the receipt's own card;
* a held pair whose cards disagree carries `rows[].cards_differ`, counted in
  `summary.n_cards_differ`, confirmed pairs included.

Route-level: every assertion reads `GET /api/runs/{id}` after the real upload,
statement attach, card pick and re-match routes.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.deterministic import MatchingConfig, match_month  # noqa: E402
from expense_recon.matching.types import Receipt, Transaction  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from tests.test_feedback_notes_52_53_62_63 import (  # noqa: E402
    CARDS,
    _attach,
    _expense,
    _extraction,
    _month,
    _pick_card,
    _wire,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _row(client, batch, card: str) -> dict:
    view = client.get(f"/api/runs/{batch}").json()
    rows = [r for r in view["rows"] if card in r["coverage_key"]]
    assert len(rows) == 1, [(r["vendor"], r["coverage_key"]) for r in view["rows"]]
    return rows[0]


def _summary(client, batch) -> dict:
    return client.get(f"/api/runs/{batch}").json()["summary"]


def test_a_picked_card_decides_between_two_cards_charges(client, monkeypatch):
    """Same merchant, same amount on two cards. Unscoped, the same-day 2838
    charge took the receipt; the reviewer's pick of 3645 now sends it to the
    3645 charge and off the 2838 one entirely."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("2838", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
        ("3645", datetime(2026, 8, 7), "LOVABLE", "Sale", -25.00),
    ])
    doc = _expense(client, batch, "Lovable")["document_id"]
    assert _row(client, batch, "2838")["chosen_document_id"] == doc

    resp = _pick_card(client, batch, doc, "corp-3645")
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text

    on_3645 = _row(client, batch, "3645")
    on_2838 = _row(client, batch, "2838")
    assert on_3645["chosen_document_id"] == doc
    assert "cards_differ" not in on_3645
    assert on_2838["chosen_document_id"] is None
    assert all(c["document_id"] != doc for c in on_2838["candidates"])
    assert _summary(client, batch)["n_cards_differ"] == 0


def test_a_pick_with_no_charge_on_its_card_keeps_the_pair_and_flags_it(client, monkeypatch):
    """The live LOVABLE case: the only LOVABLE 25.00 charge is on 3645, the
    receipt is picked as 2838. The pair is not dropped; it asks for review,
    says why, and the row names both cards."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05"))
    batch = _month(client, 1)
    _attach(client, batch, [
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
        ("2838", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
    ])
    doc = _expense(client, batch, "Lovable")["document_id"]
    row = _row(client, batch, "3645")
    assert row["chosen_document_id"] == doc and "cards_differ" not in row

    resp = _pick_card(client, batch, doc, "corp-2838")
    assert resp.status_code == 200 and "rematch" in resp.json(), resp.text

    row = _row(client, batch, "3645")
    assert row["chosen_document_id"] == doc
    assert row["effective_bucket"] == "reconciled"
    cand = next(c for c in row["candidates"] if c["document_id"] == doc)
    assert cand["requires_review"] is True
    assert "the cards differ" in cand["reason"], cand["reason"]
    assert row["cards_differ"] == {
        "document_id": doc,
        "charge_card": "3645",
        "receipt_card": "2838",
        "receipt_card_key": "corp-2838",
        "receipt_card_label": "Credit Card Chase Visa - 2838",
        "receipt_card_source": "override",
    }
    # A pair that asks for review never confirms itself (item 76).
    assert row["status"] == "pending" and "decided_by" not in row
    assert _summary(client, batch)["n_cards_differ"] == 1


def test_a_confirmed_pair_is_flagged_when_the_cards_disagree(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05"))
    batch = _month(client, 1)
    _attach(client, batch, [("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00)])
    doc = _expense(client, batch, "Lovable")["document_id"]
    tx = _row(client, batch, "3645")["transaction_id"]
    resp = client.post(f"/api/runs/{batch}/decisions", json={
        "transaction_id": tx, "status": "confirmed", "chosen_document_id": doc,
    })
    assert resp.status_code == 200, resp.text

    assert _pick_card(client, batch, doc, "corp-2838").status_code == 200

    row = _row(client, batch, "3645")
    assert row["status"] == "confirmed" and row["chosen_document_id"] == doc
    assert row["cards_differ"]["receipt_card"] == "2838"
    assert row["cards_differ"]["charge_card"] == "3645"
    assert _summary(client, batch)["n_cards_differ"] == 1

    # Picking the charge's own card clears the flag.
    assert _pick_card(client, batch, doc, "corp-3645").status_code == 200
    assert "cards_differ" not in _row(client, batch, "3645")
    assert _summary(client, batch)["n_cards_differ"] == 0


def _hinted_month(client, monkeypatch, rows) -> tuple[str, str]:
    """A month whose one receipt printed only "Visa", assigned to 2838 for
    this batch (a tender word is never learned), then the statement."""
    client.put("/api/settings", json={"cards": CARDS})
    _wire(monkeypatch, _extraction("Lovable", "25.00", "2026-08-05", "Visa"))
    batch = _month(client, 1)
    resp = client.post(
        f"/api/expense-batches/{batch}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}], "learn": False},
    )
    assert resp.status_code == 200, resp.text
    row = _expense(client, batch, "Lovable")
    assert row["card"]["key"] == "corp-2838" and row["card_source"] == "hint"
    _attach(client, batch, rows)
    return batch, row["document_id"]


def test_a_hint_card_takes_its_own_charge_over_a_closer_one_on_another_card(client, monkeypatch):
    """Unscoped, the same-day 3645 charge (exact) beat the 2838 charge two
    days later (probable). The hinted card now wins it."""
    batch, doc = _hinted_month(client, monkeypatch, [
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
        ("2838", datetime(2026, 8, 7), "LOVABLE", "Sale", -25.00),
    ])
    on_2838 = _row(client, batch, "2838")
    assert on_2838["chosen_document_id"] == doc
    assert "cards_differ" not in on_2838
    assert _row(client, batch, "3645")["chosen_document_id"] is None


def test_a_hint_card_never_drops_the_only_charge(client, monkeypatch):
    """A hint is weaker than a pick: with no charge on its card, the charge on
    the other card keeps the receipt and asks for review."""
    batch, doc = _hinted_month(client, monkeypatch, [
        ("3645", datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    ])
    row = _row(client, batch, "3645")
    assert row["chosen_document_id"] == doc
    cand = next(c for c in row["candidates"] if c["document_id"] == doc)
    assert cand["requires_review"] is True
    assert "the cards differ" in cand["reason"]
    assert "from its payment method" in cand["reason"]
    assert row["cards_differ"]["receipt_card_source"] == "hint"
    assert _summary(client, batch)["n_cards_differ"] == 1


def _tx(tx_id: str, card: str, day: int) -> Transaction:
    return Transaction(
        transaction_id=tx_id, account_id="card-2838", legal_entity_id="",
        transaction_date=date(2026, 8, day), posting_date=None,
        amount=Decimal("25.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="LOVABLE",
        card_last4=card,
    )


def test_a_remembered_card_settles_which_card_takes_the_receipt():
    """Two charges the receipt cannot tell apart go to whichever the
    assignment meets first (the 2838 one). A card remembered from an earlier
    month sends the receipt to its own card instead."""
    from dataclasses import replace

    txs = [_tx("t-2838", "2838", 5), _tx("t-3645", "3645", 5)]
    base = Receipt(
        document_id="r1", legal_entity_id="", detected_date=date(2026, 8, 5),
        detected_total=Decimal("25.00"), detected_currency="USD",
        detected_vendor="LOVABLE",
    )
    unscoped = match_month(txs, [base], MatchingConfig())
    assert [m.transaction_id for m in unscoped.matches] == ["t-2838"]

    learned = replace(base, card_scope_keys=("3645",), card_scope_source="learned")
    out = match_month(txs, [learned], MatchingConfig())
    assert [(m.transaction_id, m.requires_review) for m in out.matches] == [("t-3645", False)]
    assert out.matches[0].card_score == 1.0
    assert "t-2838" in out.unmatched_transactions


def test_a_printed_card_still_beats_a_picked_one_for_the_same_charge():
    """Live August 2026: ZOHOCORP 576.00 on 2838, with two receipts for it,
    ZOHO Corporation printing ...2838 and a Zoho Books copy picked as 2838.
    The printed card keeps its edge, so the pick does not turn the charge
    into a tie a human must break."""
    from dataclasses import replace

    tx = replace(
        _tx("zoho", "2838", 30), amount=Decimal("576.00"), vendor_from_statement="ZOHOCORP"
    )
    printed = Receipt(
        document_id="printed", legal_entity_id="", detected_date=date(2026, 8, 30),
        detected_total=Decimal("576.00"), detected_currency="USD",
        detected_vendor="ZOHO", payment_mode="credit card ending with ...2838",
    )
    picked = replace(
        printed, document_id="picked", payment_mode=None,
        card_scope_keys=("2838",), card_scope_source="override",
    )
    out = match_month([tx], [picked, printed], MatchingConfig())
    assert not out.ambiguous
    assert [m.document_id for m in out.matches] == ["printed"]
