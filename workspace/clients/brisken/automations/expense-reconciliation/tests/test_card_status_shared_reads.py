"""The all-months card roll-up reads shared inputs once (2026-09-25).

Owner, 2026-09-25: the months strip "is lagging and loading way later than
the rest", and "months are also pretty slow to open". `GET /api/cards/status`
builds every month's Expenses page, and each build re-read what every month
shares: the statement evidence of all months (once per month), and the card
registry's wording (once per payment hint and per alias). Live the route took
2.3 s against 0.2 s for the months list.

The fix reads each of those once. What it must never do is answer from an
old registry, so the reader tests below change the registry between calls.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.cards import (
    Card,
    positive_non_brisken_evidence,
    resolve_card,
)


# ── the card registry's derived wording ────────────────────────────────


def _cards(*cards: Card) -> dict[str, Card]:
    return {c.key: c for c in cards}


CHASE_CREDIT = Card(key="card-2838", label="Credit Card Chase Visa - 2838",
                    digits=("2838",))
CHASE_DEBIT = Card(key="card-4700", label="Chase Visa Debit - 4700",
                   digits=("4700",))


def test_a_debit_card_added_to_the_registry_changes_the_answer():
    """"Visa Debit" is evidence of someone else's card only while no Brisken
    card is a debit card. Asked again after one is added, the answer moves,
    and asked again after it is removed, it moves back."""
    credit_only = _cards(CHASE_CREDIT)
    with_debit = _cards(CHASE_CREDIT, CHASE_DEBIT)
    assert positive_non_brisken_evidence("Visa Debit", credit_only) == "kind"
    assert positive_non_brisken_evidence("Visa Debit", with_debit) is None
    assert positive_non_brisken_evidence("Visa Debit", credit_only) == "kind"


def test_a_deactivated_card_stops_counting():
    retired = Card(key="card-4700", label="Chase Visa Debit - 4700",
                   digits=("4700",), active=False)
    assert positive_non_brisken_evidence(
        "Visa Debit", _cards(CHASE_CREDIT, CHASE_DEBIT)) is None
    assert positive_non_brisken_evidence(
        "Visa Debit", _cards(CHASE_CREDIT, retired)) == "kind"


def test_an_issuer_renamed_in_settings_is_read_fresh():
    """An issuer only a card's wording names ("Nubank") is Brisken's while
    the card says so, and evidence against Brisken once it no longer does."""
    nubank = Card(key="card-1111", label="Nubank Mastercard 1111",
                  digits=("1111",))
    renamed = Card(key="card-1111", label="Chase Mastercard 1111",
                   digits=("1111",))
    assert positive_non_brisken_evidence(
        "Nubank", _cards(CHASE_CREDIT, nubank)) is None
    assert positive_non_brisken_evidence(
        "Nubank", _cards(CHASE_CREDIT, renamed)) == "issuer"


def test_an_alias_change_resolves_by_the_new_alias_only():
    before = Card(key="card-2838", label="Corporate", digits=("2838",),
                  aliases=("CorpServ",))
    after = Card(key="card-2838", label="Corporate", digits=("2838",),
                 aliases=("TravelDesk",))
    assert resolve_card("CorpServ", _cards(before)) == before
    assert resolve_card("CorpServ", _cards(after)) is None
    assert resolve_card("TravelDesk", _cards(after)) == after


def test_a_generic_tender_alias_still_never_resolves():
    card = Card(key="card-2838", label="Corporate", digits=("2838",),
                aliases=("Visa", "CorpServ"))
    assert resolve_card("Visa", _cards(card)) is None
    assert resolve_card("CorpServ", _cards(card)) == card


def test_digit_keys_is_a_fresh_set_every_call():
    card = Card(key="card-0340", label="Chase 0340", digits=("0340",))
    keys = card.digit_keys()
    assert keys == {"340"}
    keys.add("9999")
    assert card.digit_keys() == {"340"}
    other = Card(key="card-3645", label="Chase 3645", digits=("3645",))
    assert other.digit_keys() == {"3645"}


# ── the statement evidence, through the route ──────────────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402


def _receipt(vendor: str, hint: str | None) -> ExtractedReceipt:
    return ExtractedReceipt(
        date="2026-09-10", total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # One card-less receipt per month: a card-less row is what asks for
    # the statement evidence.
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("Perplexity", None),
            _receipt("Notion", None),
            _receipt("Figma", None),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 8,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _month(client, label: str, i: int) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i]) * 64,
                          "application/octet-stream"))],
    ))
    return batch_id


@pytest.fixture
def evidence_reads(monkeypatch):
    """How many times the all-months statement evidence is read."""
    import expense_recon.card_suggestion as cs

    reads = {"n": 0}
    real = cs.statement_evidence

    def counted(store):
        reads["n"] += 1
        return real(store)

    monkeypatch.setattr(cs, "statement_evidence", counted)
    return reads


def test_the_roll_up_reads_the_statement_evidence_once(client, evidence_reads):
    assert client.put("/api/settings", json={"cards": {
        "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                      "entity": "Corporate Services"},
    }}).status_code == 200
    months = [_month(client, label, i) for i, label in enumerate(
        ("July 2026", "August 2026", "September 2026"))]

    # Each month's own page asks once: the read is still made where needed.
    for batch_id in months:
        evidence_reads["n"] = 0
        assert client.get(f"/api/expense-batches/{batch_id}").status_code == 200
        assert evidence_reads["n"] == 1

    # The roll-up builds all three pages and reads the evidence once.
    evidence_reads["n"] = 0
    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    assert evidence_reads["n"] == 1
    no_card = {m["run_id"] for m in resp.json()["no_card"]["months"]}
    assert no_card == set(months)
