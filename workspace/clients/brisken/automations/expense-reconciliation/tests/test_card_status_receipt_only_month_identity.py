"""A newest month holding only receipts must not blank a card's identity.

Live 2026-10-07: the months strip lost 2838's subcards. October was created
2026-10-01 with receipts and no statement, so it has no coverage rows, and
`list_runs` reads it first. Its receipts opened each card's slot from the
key alone (`card_key` "", `known` false, no digits), the first slot won, and
the tree (item 191) links through `card_key`, so no parent resolved: every
Chase card came back with `parent` "" and `subcards` [], and read as not in
Settings. 0340, which had no October receipt, kept its name.

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
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _receipt(day: str, vendor: str, hint: str | None) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total="42.50", currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Consumed in upload order: July's one receipt, then October's two.
    mock = MockLLMClient(
        extraction_responses=[
            _receipt("2026-07-15", "Staples", None),
            _receipt("2026-10-02", "Staples", "Visa ...2838"),
            _receipt("2026-10-03", "Uber", "Visa ...3645"),
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
        c._data_root = tmp_path
        yield c


# The live tree: 3645 and 0340 under 2838, 1176 alone; keys in both shapes.
REGISTRY = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "3645": {"label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
             "entity": "Corporate Services", "parent": "card-2838"},
    "card-0340": {"label": "Credit Card Chase Visa - 0340",
                  "digits": ["0340"], "entity": "Corporate Services",
                  "parent": "card-2838"},
    "card-1176": {"label": "Credit Card Chase Visa - 1176",
                  "digits": ["1176"], "entity": "Consulting"},
}

JULY = (
    ("2026-07-02", "42.50", "STAPLES", "2838"),
    ("2026-07-03", "12.00", "UBER", "3645"),
    ("2026-07-04", "13.00", "UBER", "3645"),
    ("2026-07-06", "9.99", "OBSIDIAN", "0340"),
    ("2026-07-07", "36.00", "GITHUB", "1176"),
)


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client, label: str) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    return resp.json()["batch_id"]


def _upload(client, batch_id: str, name: str, data: bytes) -> None:
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    ))


def _july(client) -> str:
    batch_id = _batch(client, "July 2026")
    _upload(client, batch_id, "a.jpg", JPG)
    body = "Date,Amount,Vendor,Card\n" + "".join(
        f"{d},{a},{v},{c}\n" for d, a, v, c in JULY
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


def _october(client) -> str:
    """October as it is live: receipts on 2838 and 3645, no statement, and
    the newest month, so the roll-up reads it first."""
    batch_id = _batch(client, "October 2026")
    # Distinct bytes: identical files are deduped at upload.
    _upload(client, batch_id, "o1.jpg", b"\xff\xd8\xff\xe0" + b"\x01" * 64)
    _upload(client, batch_id, "o2.jpg", b"\xff\xd8\xff\xe0" + b"\x02" * 64)
    # Both batches are created inside one second; state the order outright.
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        store.conn.execute(
            "UPDATE runs SET created_at = ? WHERE run_id = ?",
            ("2099-10-01T00:40:39+00:00", batch_id),
        )
        store.conn.commit()
        assert store.list_runs()[0].run_id == batch_id
    return batch_id


def _by_key(client) -> dict[str, dict]:
    resp = client.get("/api/cards/status")
    assert resp.status_code == 200, resp.text
    return {c["key"]: c for c in resp.json()["cards"]}


def test_a_receipt_only_newest_month_keeps_the_account_tree(client):
    assert client.put(
        "/api/settings", json={"cards": REGISTRY}
    ).status_code == 200
    _july(client)
    october = _october(client)

    cards = _by_key(client)
    # The precondition the live break needed: October's receipts are on the
    # account and on a subcard, read before July names either.
    for key in ("card-2838", "3645"):
        assert october in [m["run_id"] for m in cards[key]["receipt_months"]], key

    assert cards["card-2838"]["subcards"] == ["3645", "card-0340"]
    assert cards["3645"]["parent"] == "card-2838"
    assert cards["card-0340"]["parent"] == "card-2838"
    assert cards["card-1176"]["parent"] == ""


def test_a_receipt_only_newest_month_keeps_each_cards_name(client):
    """The strip prints the digits and dots a card not in Settings, so a
    blank identity reads `card-2838` with an amber dot."""
    assert client.put(
        "/api/settings", json={"cards": REGISTRY}
    ).status_code == 200
    _july(client)
    _october(client)

    cards = _by_key(client)
    for key, digits in (("card-2838", ["2838"]), ("3645", ["3645"])):
        assert cards[key]["card_key"] == key
        assert cards[key]["known"] is True
        assert cards[key]["digits"] == digits
        assert cards[key]["label"] == REGISTRY[key]["label"]
    assert "_named" not in cards["card-2838"]
