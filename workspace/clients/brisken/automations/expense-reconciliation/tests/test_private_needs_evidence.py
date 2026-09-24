"""A private expense is suggested only on positive evidence.

Owner ruling 2026-09-24 (card-attribution case 6), answering whether
unrecognised payment phrases belong with the receipts that wait for the
statement and vendor memory: "yes very good, that is excellent". A private
expense is suggested ONLY on positive evidence that the payment did not come
from Brisken: a card number or two-digit ending no Brisken card has, cash, a
card network / kind Brisken's cards do not carry, or an issuer that is not
Brisken's. Every other payment text waits for the statement charge, the
remembered card, the merchant's card and Criss's assignment in the
unknown-cards panel, including phrases nobody has seen yet. Supersedes item
41's trigger ("not defined in the system" became "positively not
Brisken's"); the rest of item 41 stands.

Pinned here:
* the classification table (`cards.positive_non_brisken_evidence`) over
  every live hint of 2026-09-24 plus the ruling's own examples;
* the tokenizer that reads glued words ("CreditCard", "girocardOLV") and its
  negatives;
* the vocabulary that keeps "Link" / "saved payment method" from becoming
  card aliases while an unknown identifying word is still learned;
* the route: the batch payload's `suggested_private`, the strip, and the
  learn path.

Harness mirrors test_card_type_not_private (fixtures copied, never
imported: a shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import pytest

from expense_recon.cards import (
    CASH_WORDS,
    cards_from_setting,
    is_generic_tender,
    learnable_hint_tokens,
    payment_words,
    positive_non_brisken_evidence,
    registry_issuers,
)

# The live registry's wording (2026-09-24), cut to the shapes that matter:
# Chase Visa credit cards, and 0113's Apple card from GSBANK spelt "Master
# Card" in its account, plus the United co-brand.
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
        "zoho_account": "GSBANK Apple Master Card 0113 | Dirk Neumann",
    },
    "card-8311": {
        "label": "Credit Card - 8311",
        "digits": ["8311"],
        "entity": "Cloud Services",
        "zoho_account": "Chase United Visa 8311 | business expenses",
    },
}
CARDS = cards_from_setting(LIVE_CARDS)

# ── the classification table (the contract) ─────────────────────────

SUGGESTS_PRIVATE = [
    # live 2026-09-24, printed numbers naming no Brisken card
    ("VISA ***2598", "number"),
    ("COMPRA CREDITO VISA ********1340", "number"),
    ("VISA CREDIT xxxxxxxxxxxx4167", "number"),
    ("CARTAO: XXXXXXXXXXXX3976", "number"),
    ("CARTAO: xxxxxxxxxxxx3076", "number"),
    ("DEBIT-MASTERCARD ***** ***** ***** 3281", "number"),
    ("...2544", "number"),
    ("0501-1462-9129", "number"),
    ("Revolut ****1234", "number"),
    # a masked two-digit ending no Brisken card ends in
    ("Mastercard xxxx.xxxx.xxxx.78", "ending"),
    # cash
    ("DINHEIRO", "cash"),
    ("Bar", "cash"),
    ("Cash", "cash"),
    ("pago em espécie", "cash"),
    # a network or kind Brisken's cards do not carry, anywhere in the hint
    ("girocard", "network"),
    ("girocardOLV", "network"),
    ("EC-Karte", "network"),
    ("Zahlung mit girocard", "network"),
    ("Maestro", "network"),
    ("American Express", "network"),
    ("DEBIT", "kind"),
    ("Visa Debit", "kind"),
    # an issuer that is not Brisken's
    ("Nubank", "issuer"),
    ("Pago com cartão Nubank", "issuer"),
    ("Apple Pay Nubank", "issuer"),
]

WAITS = [
    # live 2026-09-24: the rows that lose the suggestion
    "VENDA CREDITO VISA", "Link", "OUTRO", "CreditCard",
    "saved payment method",
    "We have billed your Visa card ending with the last two digits: 38",
    "Kartenzahlung erhalten",
    # case 5, unchanged: a Brisken card type
    "VISA CREDIT", "Cartão de Crédito", "CARTAO TEF", "TEF", "VISA",
    "credit card", "Cartao Credito 30 Dias", "Mastercard",
    # a Brisken issuer, a Brisken number, a Brisken ending
    "Chase Visa", "Visa ...3645", "United Business Card ...8311", "xx45",
    # conflict means wait
    "credit or debit card", "Visa ou Dinheiro", "Chase or Nubank",
    # acquirers and wallets are neutral
    "CIELO", "PagSeguro", "Apple Pay", "Stripe", "SumUp", "Google Pay",
    # never a bank: DB on these receipts is Deutsche Bahn
    "DB Fernverkehr", "Deutsche Bank",
    # fragments that only name a network in the registry's own wording
    "Express checkout", "Club",
    # tokenizer negatives: no split, no evidence
    "Barbecue", "Caspari", "Paypalito", "Visagem", "Decathlon",
    # a phrase nobody has seen yet
    "paid via the usual method",
    "",
]


@pytest.mark.parametrize("hint,reason", SUGGESTS_PRIVATE)
def test_positive_evidence_suggests_private(hint, reason):
    assert positive_non_brisken_evidence(hint, CARDS) == reason, hint


@pytest.mark.parametrize("hint", WAITS)
def test_everything_else_waits(hint):
    assert positive_non_brisken_evidence(hint, CARDS) is None, hint


def test_brisken_issuers_come_from_the_registry_wording():
    assert registry_issuers(CARDS) == frozenset(
        {"chase", "goldman", "apple", "united"})
    with_nubank = cards_from_setting({**LIVE_CARDS, "nu-4242": {
        "label": "Nubank Visa 4242", "digits": ["4242"], "entity": "X"}})
    assert positive_non_brisken_evidence("Nubank", with_nubank) is None, (
        "an issuer Brisken's own registry names is Brisken's")


def test_the_cash_words_are_the_settled_outside_chips():
    """Two lists name cash: this one and the settled-outside chip's tender
    pattern. They must not drift apart."""
    from expense_recon.web.service import suggested_settled_outside

    for spelling in ("cash", "dinheiro", "espèces", "contanti", "bargeld",
                     "em espécie"):
        hit = suggested_settled_outside(spelling)
        assert hit is not None and hit["how"] == "cash", spelling
        assert positive_non_brisken_evidence(spelling, CARDS) == "cash", spelling
    assert {w for w in CASH_WORDS if w != "bar"} == {
        "cash", "dinheiro", "especes", "contanti", "bargeld"}
    assert positive_non_brisken_evidence("cashback", CARDS) is None


# ── the tokenizer ────────────────────────────────────────────────────


@pytest.mark.parametrize("text,words", [
    ("CreditCard", ["credit", "card"]),
    ("CREDITCARD", ["credit", "card"]),
    ("girocardOLV", ["girocard", "olv"]),
    ("girocardolv", ["girocard", "olv"]),
    ("Cartão de Crédito", ["cartao", "de", "credito"]),
    ("PayPal", ["paypal"]),
    ("PagSeguro", ["pagseguro"]),
    ("Kreditkarte", ["kreditkarte"]),
    ("creditos", ["creditos"]),
    ("EC-Karte", ["ec", "karte"]),
])
def test_glued_words_are_read(text, words):
    assert payment_words(text) == words


@pytest.mark.parametrize("word", [
    "Barbecue", "Caspari", "Paypalito", "Visagem", "Decathlon",
])
def test_short_words_never_split_off_a_longer_one(word):
    assert payment_words(word) == [word.lower()]
    assert not is_generic_tender(word)


# ── the vocabulary: "a card was used" never becomes a card alias ──────


@pytest.mark.parametrize("hint", [
    "saved payment method", "Link", "VENDA CREDITO VISA", "OUTRO",
    "Kartenzahlung erhalten", "CreditCard", "girocardOLV",
    "forma de pagamento", "Pagamento recebido", "stored wallet",
    "paid", "received", "outros",
])
def test_card_was_used_phrases_are_generic(hint):
    assert is_generic_tender(hint), hint
    digit, alias, refusal = learnable_hint_tokens(hint)
    assert (digit, alias) == (None, None) and refusal, hint


def test_an_unknown_identifying_word_is_still_learned():
    assert learnable_hint_tokens("CorpServ") == (None, "CorpServ", None)


# ── the route: the batch payload the screen reads ────────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


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
    base = dict(date="2026-09-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _batch(client, monkeypatch, hints, *, label="September 2026") -> str:
    """A month whose receipts print `hints`, created AFTER the registry is
    set, because a month snapshots the registry when it is created."""
    resp = client.put("/api/settings", json={"cards": LIVE_CARDS})
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
        files=[("files", (f"r{i}.jpg", JPG + bytes([i]),
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


def test_the_batch_payload_suggests_only_on_evidence(client, monkeypatch):
    batch = _batch(client, monkeypatch,
                   ("saved payment method", "girocardOLV", "Nubank"))
    grid = _grid(client, batch)
    rows = _by_hint(grid)

    waiting = rows["saved payment method"]
    assert waiting["suggested_private"] is False
    assert waiting["can_mark_private"] is True, (
        "the tool stops SUGGESTING private; Criss can still say so")
    assert "suggested_private" not in waiting["boxes"]
    assert waiting["review"]["reason_code"] != "suggested_private"
    assert waiting["card"] is None

    for hint in ("girocardOLV", "Nubank"):
        assert rows[hint]["suggested_private"] is True, hint
        assert rows[hint]["review"]["reason_code"] == "suggested_private", hint

    assert grid["summary"]["n_suggested_private"] == 2
    assert grid["card_review"]["n_suggested_private"] == 2
    strip = {e["hint"]: e for e in grid["card_review"]["unresolved_hints"]}
    entry = strip["saved payment method"]
    assert entry["digits"] is None and entry["generic"] is True, (
        "listed under 'No card number on the receipt'")
    assert entry["suggested_private"] is False, "without the private note"
    assert strip["girocardOLV"]["suggested_private"] is True


def test_remember_does_not_learn_link_but_learns_an_identifying_word(
    client, monkeypatch
):
    batch = _batch(client, monkeypatch, ("Link", "CorpServ"))
    resp = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": "Link", "card": "3645"},
                        {"hint": "CorpServ", "card": "3645"}],
        "learn": True,
    })
    assert resp.status_code == 200, resp.text
    results = {r["hint"]: r for r in resp.json()["results"]}
    assert results["Link"]["learned"] is False and results["Link"]["note"]
    assert results["CorpServ"]["learned"] is True

    stored = client.get("/api/settings").json()["cards"]["3645"]
    assert "CorpServ" in stored.get("aliases", [])
    assert "Link" not in stored.get("aliases", [])

    rows = _by_hint(_grid(client, batch))
    assert rows["Link"]["card"]["key"] == "3645", "the month-only assignment"
    assert rows["Link"]["card_source"] == "hint"
