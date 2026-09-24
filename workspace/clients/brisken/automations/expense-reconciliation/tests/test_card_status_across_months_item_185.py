"""Item 185: the per-card filter, outside the months.

Owner, 2026-09-24, on feedback note #86: "the same per card filter system
inside the months should be outside of the months". The note itself is the
why: "I don't know which month it is on ... being able to select which card
I'm trying to find and then see what the status is on that card would be
pretty useful."

Inside a month the card strip already answers "what is open on this card".
`GET /api/cards/status` asks the estate the same question. The load-bearing
parts are not the sums, which are `month_coverage`'s own, but the two things
a per-month surface structurally cannot do:

1. name the MONTH a thing is on, and
2. say that a card has nothing in ANY month, which is the shape of the live
   gap: cards 9693, 0113, 6013 and 8311 have never carried a charge or a
   statement, and finding that out today means querying seven months by hand.

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
                date="2026-04-15", total="42.50", currency="USD",
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
        c._data_root = tmp_path
        yield c


def _cards(client, **cards) -> None:
    """Seed the registry BEFORE the batch is created: a batch snapshots the
    composed registry into its own config, and coverage reads that."""
    resp = client.put("/api/settings", json={"cards": cards})
    assert resp.status_code == 200, resp.text


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client, label) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _carded_csv(*rows: tuple[str, str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v},{c}\n" for d, a, v, c in rows)
    return ("Date,Amount,Vendor,Card\n" + body).encode()


def _upload(client, batch_id, body: bytes, name="statement.csv"):
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    ))


def _status(client) -> dict:
    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_key(payload: dict) -> dict[str, dict]:
    return {c["key"]: c for c in payload["cards"]}


CORP = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "card-9693": {"label": "Credit Card Chase Visa - 9693",
                  "digits": ["9693"], "entity": "Cloud Services"},
}


# ── 1. one card, one line, and the months it is on ──────────────────────


def test_a_card_spanning_two_months_is_one_line_naming_both(client):
    """The question the note opens with: "I don't know which month it is
    on". The card is one row and it names its months, which is the part no
    month page can render."""
    _cards(client, **CORP)
    april = _batch(client, "April 2026")
    _upload(client, april, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-05", "12.00", "AWS", "2838"),
    ), name="april.csv")
    may = _batch(client, "May 2026")
    _upload(client, may, _carded_csv(
        ("2026-05-09", "31.10", "UBER", "2838"),
    ), name="may.csv")

    payload = _status(client)
    # Both batches were created inside the same second, so `created_at`
    # ties and cannot order them. The order is the months' own spans.
    assert [m["label"] for m in payload["months"]] == [
        "May 2026", "April 2026",
    ], [(m["label"], m["created_at"], m["period_start"]) for m in payload["months"]]
    card = _by_key(payload)["card-2838"]
    assert card["n_transactions"] == 3
    assert card["n_months"] == 2
    assert [m["label"] for m in card["months"]] == ["May 2026", "April 2026"], (
        "newest month first"
    )
    assert [m["n_transactions"] for m in card["months"]] == [1, 2]
    assert (card["period_start"], card["period_end"]) == (
        "2026-04-03", "2026-05-09",
    ), "the card's span across the estate, not one month's"
    assert [s["file"] for s in card["statements"]] == ["may.csv", "april.csv"]
    assert [s["month"] for s in card["statements"]] == ["May 2026", "April 2026"]
    assert card["never_loaded"] is False


def test_the_sums_are_the_month_pages_own_numbers(client):
    """Not a second derivation. A card's line here and its row on each
    month page are the same arithmetic, or two screens report one card at
    two stages of done."""
    _cards(client, **CORP)
    ids = []
    for label, rows in (
        ("April 2026", (("2026-04-03", "42.50", "STAPLES", "2838"),)),
        ("May 2026", (("2026-05-09", "31.10", "UBER", "2838"),
                      ("2026-05-11", "9.00", "AWS", "2838"))),
    ):
        batch_id = _batch(client, label)
        _upload(client, batch_id, _carded_csv(*rows), name=f"{label[:3]}.csv")
        ids.append(batch_id)

    card = _by_key(_status(client))["card-2838"]
    per_month = {}
    for batch_id in ids:
        view = client.get(f"/api/runs/{batch_id}").json()
        row = next(c for c in view["coverage"] if c["key"] == "card-2838")
        per_month[batch_id] = row
    for field in ("n_transactions", "n_reconciled", "n_review",
                  "n_unmatched_tx", "n_refunds"):
        assert card[field] == sum(r[field] for r in per_month.values()), field


# ── 2. the gap: a card with nothing, anywhere ───────────────────────────


def test_a_card_with_nothing_in_any_month_reads_never_loaded(client):
    """The live shape of item 108's remaining half. Card 9693 is defined,
    carries no charge and no statement in any month, and nothing on the
    month pages says so in one place: each month can only report its own
    emptiness."""
    _cards(client, **CORP)
    april = _batch(client, "April 2026")
    _upload(client, april, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), name="april.csv")
    _batch(client, "May 2026")

    cards = _by_key(_status(client))
    assert cards["card-9693"]["never_loaded"] is True
    assert cards["card-9693"]["n_transactions"] == 0
    assert cards["card-9693"]["n_statements"] == 0
    assert cards["card-9693"]["months"] == [], (
        "a month that merely listed the card is not a month it is ON"
    )
    assert cards["card-9693"]["entity"] == "Cloud Services", (
        "the registry's entity survives a card with nothing in it"
    )
    assert cards["card-2838"]["never_loaded"] is False
    # The busiest card first, the empty ones last: the month strip's order.
    assert _status(client)["cards"][0]["key"] == "card-2838"
    assert _status(client)["cards"][-1]["never_loaded"] is True


# ── 3. one card, one line, even when it was defined halfway through ─────


def test_a_card_defined_after_a_month_is_still_one_line(client):
    """April ran before anybody defined 2838, so its charges sit under the
    bare digits; May ran after. Two rows for one piece of plastic is the
    one thing this surface must not do."""
    april = _batch(client, "April 2026")
    _upload(client, april, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
    ), name="april.csv")
    _cards(client, **CORP)
    may = _batch(client, "May 2026")
    _upload(client, may, _carded_csv(
        ("2026-05-09", "31.10", "UBER", "2838"),
    ), name="may.csv")

    cards = _by_key(_status(client))
    assert "digits:2838" not in cards, sorted(cards)
    card = cards["card-2838"]
    assert card["known"] is True
    assert card["n_transactions"] == 2
    assert sorted(m["label"] for m in card["months"]) == [
        "April 2026", "May 2026",
    ]


def test_an_undefined_card_with_no_twin_keeps_its_own_line(client):
    """The other direction, and the reason the fold is one-way. 4700 is a
    real card on a real statement that the registry has never met; folding
    it into anything would hide the gap it is evidence of."""
    _cards(client, **CORP)
    april = _batch(client, "April 2026")
    _upload(client, april, _carded_csv(
        ("2026-04-03", "42.50", "STAPLES", "2838"),
        ("2026-04-06", "17.25", "SHELL", "4700"),
    ), name="april.csv")

    cards = _by_key(_status(client))
    assert "digits:4700" in cards, sorted(cards)
    stray = cards["digits:4700"]
    assert stray["known"] is False
    assert stray["n_transactions"] == 1
    assert stray["label"] == "4700"
    assert [m["label"] for m in stray["months"]] == ["April 2026"]
