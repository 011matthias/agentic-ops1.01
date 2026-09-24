"""Item 191: the months strip nests a card's subcards under it.

Owner, 2026-09-24: the subcards of 2838 should "not be next to the 2838 tab
but rather only appear once viewer clicks on 2838. maintain their filter
function".

The strip is `GET /api/cards/status`, and until now it carried no tree: the
registry has held a `parent` since item 147, but only the month pages and
the PDFs read it. `cards[].parent` and `cards[].subcards` are parallel
fields; every figure stays the card's own, so filtering on a subcard or on
the account itself answers exactly what it did before.

Everything here runs through the FastAPI app.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-07-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * 8,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


# The live registry's keys, which mix both shapes: `3645` and `card-0340`.
ACCOUNT = {"label": "Credit Card - 2838", "digits": ["2838"],
           "entity": "Corporate Services"}


def _registry(*, parented: bool, with_account: bool = True) -> dict:
    parent = {"parent": "card-2838"} if parented else {}
    cards = {
        "3645": {"label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
                 "entity": "Corporate Services", **parent},
        "card-0340": {"label": "Credit Card Chase Visa - 0340",
                      "digits": ["0340"], "entity": "Corporate Services",
                      **parent},
        "card-1176": {"label": "Credit Card Chase Visa - 1176",
                      "digits": ["1176"], "entity": "Consulting"},
    }
    if with_account:
        cards["card-2838"] = ACCOUNT
    return cards


def _put_cards(client, cards: dict) -> None:
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


# July's shape: one statement file carrying the account and two of its
# subcards, plus a card that stands alone. 3645 is the busiest, so the strip
# order is not the registry's.
JULY = (
    ("2026-07-02", "42.50", "STAPLES", "2838"),
    ("2026-07-03", "12.00", "UBER", "3645"),
    ("2026-07-04", "13.00", "UBER", "3645"),
    ("2026-07-05", "14.00", "LYFT", "3645"),
    ("2026-07-06", "9.99", "OBSIDIAN", "0340"),
    ("2026-07-07", "36.00", "GITHUB", "1176"),
)


def _july(client, rows=JULY) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "July 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    body ="Date,Amount,Vendor,Card\n" + "".join(
        f"{d},{a},{v},{c}\n" for d, a, v, c in rows
    )
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("July2026.csv", body.encode(),
                             "application/octet-stream")},
        data={
            "account_id": "chase-2838",
            "account_legal_entities": '{"chase-2838": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    ))
    return batch_id


def _by_key(client) -> dict[str, dict]:
    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    return {c["key"]: c for c in resp.json()["cards"]}


def test_subcards_name_their_account_and_the_account_names_them(client):
    """The owner's tree: 3645 and 0340 under 2838, 1176 alone. The account
    lists its subcards in the strip's order (busiest first), which is the
    order the second row renders them in."""
    _put_cards(client, _registry(parented=True))
    _july(client)

    cards = _by_key(client)
    assert cards["3645"]["parent"] == "card-2838"
    assert cards["card-0340"]["parent"] == "card-2838"
    assert cards["card-2838"]["parent"] == ""
    assert cards["card-1176"]["parent"] == ""
    assert cards["card-2838"]["subcards"] == ["3645", "card-0340"]
    for key in ("3645", "card-0340", "card-1176"):
        assert cards[key]["subcards"] == [], key


def test_every_figure_stays_the_cards_own(client):
    """Nesting is presentation. The account's count is its own charge, not
    the account's total, and a subcard still carries its own months, so the
    filter answers what it did before on either tab."""
    _put_cards(client, _registry(parented=True))
    july = _july(client)

    cards = _by_key(client)
    assert cards["card-2838"]["n_transactions"] == 1
    assert cards["3645"]["n_transactions"] == 3
    assert cards["card-0340"]["n_transactions"] == 1
    assert [m["run_id"] for m in cards["3645"]["months"]] == [july]


def test_no_parent_anywhere_is_a_flat_strip(client):
    """Today's live registry: nobody has set a parent, so every card stands
    alone and the strip renders exactly as it did."""
    _put_cards(client, _registry(parented=False))
    _july(client)

    for key, card in _by_key(client).items():
        assert card["parent"] == "", key
        assert card["subcards"] == [], key


def test_the_tree_is_the_live_registrys_not_the_months(client):
    """July was created before anybody set a parent, and a month keeps the
    registry it was created with. The strip reads the live one, so setting
    the parents in Settings nests the tabs without touching the month, and
    clearing them flattens the tabs again."""
    _put_cards(client, _registry(parented=False))
    _july(client)
    assert _by_key(client)["card-2838"]["subcards"] == []

    _put_cards(client, _registry(parented=True))
    assert _by_key(client)["card-2838"]["subcards"] == ["3645", "card-0340"]

    _put_cards(client, _registry(parented=False))
    assert _by_key(client)["card-2838"]["subcards"] == []


def test_a_subcard_never_nests_under_a_tab_the_strip_does_not_show(client):
    """2838 defined after July with no charge anywhere is on no month, so it
    has no tab. A subcard pointing at it stays on the top row rather than
    vanishing behind a tab nobody can click."""
    _put_cards(client, _registry(parented=False, with_account=False))
    _july(client, rows=[r for r in JULY if r[3] != "2838"])
    _put_cards(client, _registry(parented=True))

    cards = _by_key(client)
    assert "card-2838" not in cards, sorted(cards)
    assert cards["3645"]["parent"] == ""
    assert cards["card-0340"]["parent"] == ""
