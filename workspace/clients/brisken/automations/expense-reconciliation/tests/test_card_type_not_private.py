"""A Brisken card TYPE on a receipt is not a private-expense signal.

Owner ruling 2026-09-24 (card-attribution case 5): "widen Item 1 to be
receipt shows a brisken card number or card type (like VISA CREDIT) ... the
alternative logic for this case is to wait for data in statement to match the
expense to a card, but expense does not get labeled as potential private
expense". Brisken's own cards are Visa credit cards, so a receipt printing
only "VISA CREDIT", "Cartão de Crédito" or "TEF" says nothing about a
non-Brisken card. Item 111 measured it: 15 rows July's statement settled had
been suggested private on exactly such words.

This supersedes the digit-less "Cartao de Credito" example of item 41
(2026-09-06). The rest of item 41 holds: a payment method Brisken does not
have (girocard, EC-Karte, DEBIT, cash) still suggests private.

Pinned here:
* a generic hint naming only a network / kind the registry's ACTIVE cards
  carry (derived from their `label` + `zoho_account` wording) suggests
  nothing, keeps `can_mark_private`, selects NO card, and falls to the
  ordinary company / person question;
* a network or kind no active card carries, and a non-card tender word,
  still suggest private;
* an empty registry, or one whose wording names no network and no kind,
  behaves exactly as before the ruling;
* the rest of the card chain (an assigned hint) is untouched.

Harness mirrors test_private_expense (fixtures copied, never imported: a
shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    cards_from_setting,
    positive_non_brisken_evidence,
    registry_card_types,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# The live registry's wording (2026-09-24), cut to one card per shape:
# "Visa" + "Credit" in a label, and 0113's Mastercard spelt with a space
# ("Master Card") in its account, where nothing else says Mastercard.
LIVE_CARDS = {
    "3645": {
        "label": "Credit Card Chase Visa - 3645",
        "digits": ["3645"],
        "entity": "Corporate Services",
        "zoho_account": "Credit Card - 2838",
    },
    "card-0113": {
        "label": "Apple Credit Card - 0113",
        "digits": ["0113"],
        "entity": "Cloud Services",
        "person": "Dirk",
        "zoho_account": "GSBANK Apple Master Card 0113",
    },
}
VISA_ONLY = {"3645": LIVE_CARDS["3645"]}

BRISKEN_TYPES = (
    "VISA CREDIT", "Cartão de Crédito", "CARTAO TEF", "credit card",
    "Cartao Credito 30 Dias", "VISA", "TEF", "Mastercard",
)
NOT_BRISKEN = (
    "girocard", "DEBIT", "EC-Karte", "Bar", "DINHEIRO", "Maestro", "Amex",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch(client, monkeypatch, hints, *, cards=None, label="August 2026",
           seed=0) -> str:
    """A month whose receipts print `hints`, created AFTER the registry is
    set, because a month snapshots the registry when it is created."""
    if cards is not None:
        resp = client.put("/api/settings", json={"cards": cards})
        assert resp.status_code == 200, resp.text
    mock = MockLLMClient(extraction_responses=[
        _extraction(vendor=f"Vendor {i}", total=f"{10 + i}.00",
                    payment_hint=hint)
        for i, hint in enumerate(hints)
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client",
                        lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"r{i}.jpg", JPG + bytes([i, seed]),
                          "application/octet-stream"))
               for i in range(len(hints))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_hint(grid: dict) -> dict:
    rows = {e["payment_hint"]: e for e in grid["expenses"]}
    assert len(rows) == len(grid["expenses"]), "hints must be distinct"
    return rows


# ── the route: the batch payload the screen reads ────────────────────


def test_a_brisken_card_type_is_not_suggested_private(client, monkeypatch):
    batch = _batch(client, monkeypatch, BRISKEN_TYPES + NOT_BRISKEN,
                   cards=LIVE_CARDS)
    grid = _grid(client, batch)
    rows = _by_hint(grid)

    for hint in BRISKEN_TYPES:
        row = rows[hint]
        assert row["suggested_private"] is False, hint
        assert row["can_mark_private"] is True, (
            hint, "the tool stops SUGGESTING private; Criss can still say so")
        assert "suggested_private" not in row["boxes"], hint
        # Item 204: with no statement loaded the company question reads as
        # waiting for the statements; either way it is not the private one.
        assert row["review"]["reason_code"] in ("needs_entity", "waits_for_statement"), (
            hint, "the ordinary company question, not the private one")
        assert row["card"] is None and row["card_source"] == "none", (
            hint, "a type word never selects a card (ruling 2026-08-21)")
        assert row["reimburse_to_prefill"] == "", hint

    for hint in NOT_BRISKEN:
        row = rows[hint]
        assert row["suggested_private"] is True, hint
        assert "suggested_private" in row["boxes"], hint
        assert row["review"]["reason_code"] == "suggested_private", hint

    assert grid["summary"]["n_suggested_private"] == len(NOT_BRISKEN)
    assert grid["card_review"]["n_suggested_private"] == len(NOT_BRISKEN)
    strip = {e["hint"]: e for e in grid["card_review"]["unresolved_hints"]}
    assert strip["VISA CREDIT"]["suggested_private"] is False
    assert strip["VISA CREDIT"]["generic"] is True
    assert strip["girocard"]["suggested_private"] is True


def test_the_private_option_still_works_on_a_card_type_row(client, monkeypatch):
    batch = _batch(client, monkeypatch, ("VISA CREDIT",), cards=LIVE_CARDS)
    (row,) = _grid(client, batch)["expenses"]
    assert row["suggested_private"] is False

    resp = client.post(
        f"/api/runs/{batch}/expenses/{row['document_id']}/private",
        json={"private": True, "reimburse_to": "Dirk"},
    )
    assert resp.status_code == 200, resp.text
    (row,) = _grid(client, batch)["expenses"]
    assert row["private"] is True and row["reimburse_to"] == "Dirk"
    assert row["person"] == "Dirk" and row["person_source"] == "private"


def test_an_empty_registry_has_no_visa(client, monkeypatch):
    """With no cards, Brisken carries no network, so VISA CREDIT is a card
    Brisken does not have. CARTAO TEF names no network, kind or issuer at
    all and waits (case 6, positive evidence only)."""
    batch = _batch(client, monkeypatch, ("VISA CREDIT", "CARTAO TEF"))
    rows = _by_hint(_grid(client, batch))
    assert rows["VISA CREDIT"]["suggested_private"] is True
    assert rows["CARTAO TEF"]["suggested_private"] is False


def test_a_registry_that_names_no_card_type(client, monkeypatch):
    """Cards exist, but no label or account says Visa, Mastercard, credit or
    debit: the registry carries no Visa, so VISA CREDIT still suggests, and a
    bare "card" is no evidence at all (case 6) and waits."""
    batch = _batch(client, monkeypatch, ("VISA CREDIT", "card"), cards={
        "corp-1672": {"label": "Corporate card (Chase)", "digits": ["1672"],
                      "entity": "Corporate Services",
                      "zoho_account": "Chase 1672"},
    })
    rows = _by_hint(_grid(client, batch))
    assert rows["VISA CREDIT"]["suggested_private"] is True
    assert rows["card"]["suggested_private"] is False


def test_mastercard_follows_the_registry(client, monkeypatch):
    """Without the Apple card the registry has no Mastercard, so the word is
    evidence of a card Brisken does not have; with it ("Master Card", with a
    space, in its account), it is not."""
    visa_only = _batch(client, monkeypatch, ("Mastercard", "VISA CREDIT"),
                       cards=VISA_ONLY, label="July 2026", seed=1)
    rows = _by_hint(_grid(client, visa_only))
    assert rows["Mastercard"]["suggested_private"] is True
    assert rows["VISA CREDIT"]["suggested_private"] is False

    both = _batch(client, monkeypatch, ("Mastercard",), cards=LIVE_CARDS,
                  label="August 2026", seed=2)
    (row,) = _grid(client, both)["expenses"]
    assert row["suggested_private"] is False


def test_one_visa_card_is_still_not_selected_but_an_assigned_hint_is(
    client, monkeypatch
):
    """Only one card has the network, and the word still picks nothing; the
    operator's explicit hint assignment (the card chain) resolves it."""
    batch = _batch(client, monkeypatch, ("VISA",), cards=VISA_ONLY)
    (row,) = _grid(client, batch)["expenses"]
    assert row["card"] is None and row["legal_entity_id"] == ""
    assert row["suggested_private"] is False

    resp = client.post(f"/api/expense-batches/{batch}/cards",
                       json={"assignments": [{"hint": "VISA", "card": "3645"}]})
    assert resp.status_code == 200, resp.text
    (row,) = _grid(client, batch)["expenses"]
    assert row["card"]["key"] == "3645" and row["card_source"] == "hint"
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["suggested_private"] is False
    assert row["can_mark_private"] is False, "a company card paid it"


# ── the classifier ───────────────────────────────────────────────────


def test_the_registry_types_come_from_label_and_account_wording():
    assert registry_card_types(cards_from_setting(LIVE_CARDS)) == (
        frozenset({"visa", "mastercard"}), frozenset({"credit"}),
    )
    assert registry_card_types({}) == (frozenset(), frozenset())
    inactive = dict(LIVE_CARDS)
    inactive["card-0113"] = {**LIVE_CARDS["card-0113"], "active": False}
    assert registry_card_types(cards_from_setting(inactive)) == (
        frozenset({"visa"}), frozenset({"credit"}),
    ), "an inactive card carries nothing"


def test_a_brisken_card_type_is_no_evidence():
    """Case 5 inside case 6's classifier (the full table is pinned in
    test_private_needs_evidence)."""
    cards = cards_from_setting(LIVE_CARDS)
    for hint in BRISKEN_TYPES:
        assert positive_non_brisken_evidence(hint, cards) is None, hint
    for hint in NOT_BRISKEN + ("Visa Debit", "cash"):
        assert positive_non_brisken_evidence(hint, cards) is not None, hint
