"""The sign-off card learner reads the statement's own answer (item 171).

`_CARD_OBSERVATION_SOURCES` has listed `settled_charge` since item 111, so
publishing a month was always meant to learn the card the STATEMENT named for
a settled pair. It could not: the resolution `commit_to_memory` handed the
card learner was the one caller in the file that never passed `settled_cards`,
and that is the only input producing that source, so the branch was dead.

Pinned here through the publish route, because the helper being right proves
nothing about whether the route reaches it:

1. Publishing a statement month folds each settling charge's card into its
   merchant's `cards_seen`, and pins `card_key` while that holds exactly one.
2. A merchant the month settles on TWO cards is left unpinned. This is the
   case that decides the shape of the fix: measured on live July and August
   2026 (2026-09-24), confining the map to pairs a human confirmed by hand
   would have taught `Anthropic -> 3645` and nothing else, entering one of
   the three vendors item 154 forbids guessing into the registry as a
   single-card merchant. The full reconciled bucket sees both of Anthropic's
   cards and refuses to pin either. Under-observing this learner invents
   facts; over-observing it only makes it say nothing.
3. A rejected pair teaches nothing, and neither does a receipt with no pair.
4. A key an editor typed is never moved by the statement, though the
   observation is still recorded beside it.
5. A month with no statement teaches no card at all, which is every month
   before its first one.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0item171-bytes"

CARDS = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838"],
        "entity": "Corporate Services",
        "person": "Dirk",
        "zoho_account": "Chase 2838",
    },
    "cloud-3645": {
        "label": "Cloud card",
        "digits": ["3645"],
        "entity": "Cloud Services",
        "person": "Nicolas",
        "zoho_account": "Chase 3645",
    },
}

CARD_HEADERS = ("Card", "Date", "Description", "Type", "Amount")
# The live case was Lovable and Anthropic. Since item 183 half A those two
# (and OpenAI) are owner-gated in the merchant list, so Publish writes no
# card for them; the fixture uses ungated vendors in the same shape.
CARD_ROWS = [
    ("2838", datetime(2026, 8, 31), "CANVA", "Sale", -15.00),
    ("3645", datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    ("2838", datetime(2026, 8, 20), "FIGMA", "Sale", -20.00),
    ("3645", datetime(2026, 8, 18), "FIGMA", "Sale", -30.00),
]

# (file name, vendor, total, date)
RECEIPTS = [
    ("canva.jpg", "Canva Pty", "15.00", "2026-08-31"),
    ("obsidian.jpg", "Obsidian", "96.00", "2026-08-30"),
    ("figma-corp.jpg", "Figma", "20.00", "2026-08-20"),
    ("figma-cloud.jpg", "Figma", "30.00", "2026-08-18"),
    ("notion.jpg", "Notion", "8.00", "2026-08-10"),
]

PAIRED = {
    "canva.jpg": "corp-2838",
    "obsidian.jpg": "cloud-3645",
    "figma-corp.jpg": "corp-2838",
    "figma-cloud.jpg": "cloud-3645",
}


def _entry(*aliases: str, **extra) -> dict:
    entry: dict = {"aliases": list(aliases), "category": None, "zoho_account": None}
    entry.update(extra)
    return entry


MERCHANTS = {
    "Canva Pty": _entry("Canva Pty", "Canva"),
    "Obsidian": _entry("Obsidian"),
    "Figma": _entry("Figma"),
    "Notion": _entry("Notion"),
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _wire(monkeypatch) -> None:
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date=day, total=total, currency="USD", vendor=vendor,
                reference="", line_items=(), confidence=0.9, notes="",
                payment_hint=None,
            )
            for _name, vendor, total, day in RECEIPTS
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx_bytes(rows, headers) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, batch_id) -> dict[str, dict]:
    return {e["receipt_name"]: e for e in _grid(client, batch_id)["expenses"]}


def _charge(client, batch_id, vendor, amount) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    rows = [
        r for r in resp.json()["rows"]
        if r["vendor"] == vendor and str(amount) in str(r.get("amount"))
    ]
    assert len(rows) == 1, [(r["vendor"], r.get("amount")) for r in resp.json()["rows"]]
    return rows[0]


def _decide(client, batch_id, tx_id, status, doc=None):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": status, "chosen_document_id": doc},
    )
    assert resp.status_code == 200, resp.text


def _put_merchants(client, merchants: dict) -> None:
    resp = client.put("/api/settings", json={"merchants": merchants})
    assert resp.status_code == 200, resp.text


def _merchants(client) -> dict:
    return client.get("/api/settings").json().get("merchants") or {}


def _publish(client, batch_id) -> dict:
    resp = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    memory = resp.json()["memory"]
    assert memory.get("saved") is True, memory
    return memory["learned"]


def _august(client, monkeypatch, *, statement: bool = True) -> str:
    """August's five receipts, none carrying a card of its own, then its
    Chase workbook. Four of the five settle a charge; Notion settles none."""
    assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
    _put_merchants(client, MERCHANTS)
    _wire(monkeypatch)
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + name.encode(), "application/octet-stream"))
            for name, *_rest in RECEIPTS
        ],
    ))
    if not statement:
        return batch_id
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(CARD_ROWS, CARD_HEADERS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    # The four pairs the month rests on, stated before anything is asserted
    # about what they teach: a silently unpaired receipt would make every
    # "teaches nothing" test below pass for the wrong reason.
    rows = _rows(client, batch_id)
    for name, card_key in PAIRED.items():
        assert rows[name]["card_source"] == "settled_charge", rows[name]
        assert rows[name]["card"]["key"] == card_key, rows[name]
    assert rows["notion.jpg"]["card"] is None
    return batch_id


# ── what a publish learns ────────────────────────────────────────────


def test_publishing_learns_the_card_the_statement_named(client, monkeypatch):
    batch = _august(client, monkeypatch)
    assert not any(e.get("cards_seen") for e in _merchants(client).values())

    _publish(client, batch)

    after = _merchants(client)
    assert after["Canva Pty"]["cards_seen"] == ["corp-2838"]
    assert after["Canva Pty"]["card_key"] == "corp-2838"
    assert after["Canva Pty"]["card_key_learned"] is True
    assert after["Obsidian"]["cards_seen"] == ["cloud-3645"]
    assert after["Obsidian"]["card_key"] == "cloud-3645"


def test_a_merchant_the_month_settles_on_two_cards_is_left_unpinned(
    client, monkeypatch
):
    """Figma's two receipts (the live case is Anthropic's) settle charges on both cards. The learner
    records both and pins neither -- the live-measured reason the settled map
    is the full reconciled bucket rather than the confirmed-only subset."""
    batch = _august(client, monkeypatch)
    _publish(client, batch)

    anthropic = _merchants(client)["Figma"]
    assert anthropic["cards_seen"] == ["cloud-3645", "corp-2838"]
    assert "card_key" not in anthropic
    assert "card_key_learned" not in anthropic


def test_a_rejected_pair_teaches_no_card(client, monkeypatch):
    batch = _august(client, monkeypatch)
    lovable = _charge(client, batch, "CANVA", "15")
    _decide(client, batch, lovable["transaction_id"], "rejected")
    assert _rows(client, batch)["canva.jpg"]["card"] is None

    _publish(client, batch)

    assert not _merchants(client)["Canva Pty"].get("cards_seen")


def test_a_receipt_with_no_pairing_teaches_no_card(client, monkeypatch):
    batch = _august(client, monkeypatch)
    _publish(client, batch)

    assert not _merchants(client)["Notion"].get("cards_seen")


def test_a_typed_key_is_never_moved_by_the_statement(client, monkeypatch):
    """Obsidian's charge is on 3645 and an editor typed 2838. The person
    outranks the record: the key stays, the observation is still kept."""
    batch = _august(client, monkeypatch)
    typed = dict(MERCHANTS)
    typed["Obsidian"] = _entry("Obsidian", card_key="corp-2838")
    _put_merchants(client, typed)

    _publish(client, batch)

    obsidian = _merchants(client)["Obsidian"]
    assert obsidian["card_key"] == "corp-2838"
    assert obsidian.get("card_key_learned") is not True
    assert obsidian["cards_seen"] == ["cloud-3645"]


def test_a_month_with_no_statement_teaches_no_card(client, monkeypatch):
    """The common path, and the reason this costs nothing on it: with no
    charges there is no settled map and the learner is exactly as it was."""
    batch = _august(client, monkeypatch, statement=False)
    _publish(client, batch)

    assert not any(e.get("cards_seen") for e in _merchants(client).values())
