"""Item 192: /cards becomes an overview, so the roll-up counts receipts.

Owner, 2026-09-24, on the Cards page: "this should just be an overview and
not another gate to inside the months. we can insert more relevant data
though." Note #86 asks, per card and without knowing the month, which
receipts have no charge and which have no statement yet. Item 190 named the
months holding receipts on a card; this makes them figures: per month
`n_without_charge` and `statement`, per card `n_receipts`,
`n_receipts_without_charge` and `n_receipts_no_statement`.

The rule the roll-up keeps (item 185): a line here is the month's own
arithmetic, never a second derivation. So "without a charge" is stamped on
the Expenses page's rows from the same set its card tab counts, and the
tests below hold the two together through the routes.
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


def _receipt(date: str, total: str, vendor: str, hint: str | None) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


CORP = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "card-9693": {"label": "Credit Card Chase Visa - 9693",
                  "digits": ["9693"], "entity": "Cloud Services"},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Consumed in upload order, one receipt per upload.
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("2026-04-15", "42.50", "Staples", "Visa ...2838"),
            _receipt("2026-04-20", "19.00", "Perplexity", "Visa ...2838"),
            _receipt("2026-04-22", "7.25", "OpenAI", "Visa ...9693"),
            _receipt("2026-04-25", "12.00", "Zoom", None),
        ],
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


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, label: str, n_receipts: int) -> str:
    assert client.put("/api/settings", json={"cards": CORP}).status_code == 200
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    for i in range(n_receipts):
        # Distinct bytes: identical files are deduped at upload.
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (f"r{i}.jpg", b"\xff\xd8\xff\xe0" + bytes([i + 1]) * 64,
                              "application/octet-stream"))],
        ))
    return batch_id


def _statement(client, batch_id: str) -> None:
    """One charge on 2838, the Staples receipt's own date and amount."""
    body = b"Date,Amount,Vendor,Card\n2026-04-15,42.50,STAPLES,2838\n"
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("april.csv", body, "application/octet-stream")},
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


def _cards(payload: dict) -> dict[str, dict]:
    return {c["key"]: c for c in payload["cards"]}


def test_receipts_in_a_month_with_no_statement_wait_for_one(client):
    """September's shape: receipts, no statement. Every receipt is without a
    charge, and the card says they are waiting for a statement rather than
    leaving the page to infer it from a month list."""
    september = _month(client, "September 2026", 2)

    card = _cards(_status(client))["card-2838"]
    assert [
        (m["run_id"], m["n_expenses"], m["n_without_charge"], m["statement"])
        for m in card["receipt_months"]
    ] == [(september, 2, 2, False)]
    assert (
        card["n_receipts"], card["n_receipts_without_charge"],
        card["n_receipts_no_statement"],
    ) == (2, 2, 2)


def test_a_paired_receipt_is_not_without_a_charge(client):
    """April with its statement: the Staples receipt pairs the one charge,
    Perplexity has none. The month has a statement for 2838, so nothing on
    2838 is waiting for one; 9693 has no statement there, so its receipt is."""
    april = _month(client, "April 2026", 3)
    _statement(client, april)

    cards = _cards(_status(client))
    corp = cards["card-2838"]
    assert [
        (m["run_id"], m["n_expenses"], m["n_without_charge"], m["statement"])
        for m in corp["receipt_months"]
    ] == [(april, 2, 1, True)]
    assert (
        corp["n_receipts"], corp["n_receipts_without_charge"],
        corp["n_receipts_no_statement"],
    ) == (2, 1, 0)
    cloud = cards["card-9693"]
    assert (
        cloud["n_receipts"], cloud["n_receipts_without_charge"],
        cloud["n_receipts_no_statement"],
    ) == (1, 1, 1)


def test_the_figures_are_the_months_own(client):
    """Not a second derivation. The Expenses page stamps `without_charge` on
    each row; its card tab counts "{n} without a charge" from the same set;
    and the roll-up's month line equals both, per card."""
    april = _month(client, "April 2026", 3)
    _statement(client, april)

    view = client.get(f"/api/expense-batches/{april}").json()
    rows: dict[str, int] = {}
    for expense in view["expenses"]:
        if expense.get("counts_in_total") is False:
            continue
        assert isinstance(expense["without_charge"], bool)
        if expense["without_charge"]:
            key = expense["card_section"]
            rows[key] = rows.get(key, 0) + 1
    tabs = {
        s["key"]: s["n_receipts_without_charge"]
        for s in view["card_sections"] if s["n_receipts_without_charge"]
    }
    here = {
        c["key"]: m["n_without_charge"]
        for c in _status(client)["cards"] for m in c["receipt_months"]
        if m["run_id"] == april and m["n_without_charge"]
    }
    assert rows == tabs == here == {"card-2838": 1, "card-9693": 1}


def test_receipts_on_no_card_carry_the_count_too(client):
    """The overview's No card line: the fourth receipt names no card, and in
    a month with no statement it has no charge either."""
    september = _month(client, "September 2026", 4)

    no_card = _status(client)["no_card"]
    assert [
        (m["run_id"], m["n_expenses"], m["n_without_charge"])
        for m in no_card["months"]
    ] == [(september, 1, 1)]
    assert no_card["n_without_charge"] == 1
    assert "statement" not in no_card["months"][0], (
        "no card has no statement to hold, so the flag is not invented"
    )
