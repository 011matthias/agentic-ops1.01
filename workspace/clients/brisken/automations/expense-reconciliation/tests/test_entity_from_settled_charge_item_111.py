"""A receipt settling a charge takes its company and person (item 111).

July 2026 asked Criss for a company and a person on 33 receipts while 19 of
them already settled a bank charge whose card names both: the matching page
had decided the answer and the Expenses page asked the question again.

Pinned through the Expenses payload (`GET /api/expense-batches/{id}`):

1. A receipt with no card of its own that a charge of the month settles
   shows that charge's card, company and person (`card_source:
   "settled_charge"`), and leaves the company-or-person box.
2. Anything explicit on the receipt wins: a card picked on the row, or a
   card number the receipt prints.
3. A pair the reviewer rejected lends nothing.
4. A receipt with no pairing is unchanged.
5. The row is a company-card row: `can_mark_private` is false and the
   private-card route refuses it.
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

JPG = b"\xff\xd8\xff\xe0item111-bytes"

CARDS = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
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
CARD_ROWS = [
    ("2838", datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    ("3645", datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    ("3645", datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
]

# (file name, vendor, total, date, printed payment method)
RECEIPTS = [
    ("lovable.jpg", "Lovable Labs", "15.00", "2026-08-31", None),
    ("obsidian.jpg", "Obsidian", "96.00", "2026-08-30", "VISA"),
    ("pressmaster.jpg", "Pressmaster", "135.00", "2026-08-23", "Visa ...7777"),
    ("notion.jpg", "Notion", "8.00", "2026-08-10", None),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor, total, day, hint) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


def _wire(monkeypatch, *before: ExtractedReceipt):
    """The mock reads `before` first (another month's receipts), then
    August's four in `RECEIPTS` order."""
    mock = MockLLMClient(
        extraction_responses=[
            *before,
            *(_extraction(v, t, d, h) for _n, v, t, d, h in RECEIPTS),
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
    return {
        e["receipt_name"]: e for e in _grid(client, batch_id)["expenses"]
    }


def _charge(client, batch_id, vendor) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json()["rows"] if r["vendor"] == vendor)


def _decide(client, batch_id, tx_id, status, doc=None):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": status, "chosen_document_id": doc},
    )
    assert resp.status_code == 200, resp.text


def _august(client, monkeypatch, *, wired: bool = False) -> str:
    """August with four receipts and no company or person on any of them,
    then its Chase workbook: Lovable and Obsidian pair on their own.
    `wired`: the caller already put the cards and wired the mock."""
    if not wired:
        assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
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
    before = _grid(client, batch_id)
    if not wired:
        assert before["summary"]["n_needs_company_or_person"] == 4
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
    for vendor, name in (("LOVABLE", "lovable.jpg"), ("OBSIDIAN", "obsidian.jpg")):
        if wired and vendor == "OBSIDIAN":
            continue  # the caller's remembered card decides this pair
        row = _charge(client, batch_id, vendor)
        assert row["effective_bucket"] == "reconciled", row
        assert row["chosen_document_id"] == _rows(client, batch_id)[name]["document_id"]
    return batch_id


# ── the inheritance ──────────────────────────────────────────────────


def test_a_settled_receipt_takes_the_charges_company_and_person(client, monkeypatch):
    batch = _august(client, monkeypatch)
    grid = _grid(client, batch)
    rows = {e["receipt_name"]: e for e in grid["expenses"]}

    lovable = rows["lovable.jpg"]
    assert lovable["card_source"] == "settled_charge"
    assert lovable["card"]["key"] == "corp-2838"
    assert lovable["legal_entity_id"] == "Corporate Services"
    assert lovable["entity_source"] == "card"
    assert lovable["person"] == "Dirk" and lovable["person_source"] == "card"
    assert "needs_company_or_person" not in lovable["boxes"]
    assert "needs_entity" not in lovable["boxes"]
    # A tender word is not a card of its own: the statement's card answers.
    obsidian = rows["obsidian.jpg"]
    assert obsidian["card_source"] == "settled_charge"
    assert obsidian["card"]["key"] == "cloud-3645"
    assert obsidian["legal_entity_id"] == "Cloud Services"
    assert obsidian["person"] == "Nicolas"
    assert obsidian["suggested_private"] is False

    # The box counts drop by exactly the two inherited rows.
    assert grid["summary"]["n_needs_company_or_person"] == 2
    assert grid["summary"]["n_needs_entity"] == 2
    assert grid["summary"]["n_needs_person"] == 2


def test_a_receipt_with_no_pairing_is_unchanged(client, monkeypatch):
    batch = _august(client, monkeypatch)
    notion = _rows(client, batch)["notion.jpg"]
    assert notion["card"] is None and notion["card_source"] == "none"
    assert notion["legal_entity_id"] == "" and notion["person"] == ""
    assert "needs_company_or_person" in notion["boxes"]


def test_a_rejected_pair_lends_nothing(client, monkeypatch):
    batch = _august(client, monkeypatch)
    lovable = _charge(client, batch, "LOVABLE")
    _decide(client, batch, lovable["transaction_id"], "rejected")

    row = _rows(client, batch)["lovable.jpg"]
    assert row["card"] is None and row["card_source"] == "none"
    assert row["person"] == "" and row["legal_entity_id"] == ""
    assert "needs_company_or_person" in row["boxes"]
    assert _grid(client, batch)["summary"]["n_needs_company_or_person"] == 3


# ── explicit values win ──────────────────────────────────────────────


def test_a_card_picked_on_the_row_wins_over_the_settled_charge(client, monkeypatch):
    """Obsidian's charge is on 3645; the reviewer confirms the pair and picks
    2838 on the row. The pick is the row's card, the pair still stands."""
    batch = _august(client, monkeypatch)
    obsidian = _charge(client, batch, "OBSIDIAN")
    doc = _rows(client, batch)["obsidian.jpg"]["document_id"]
    _decide(client, batch, obsidian["transaction_id"], "confirmed", doc)
    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "card_key", "value": "corp-2838"},
    )
    assert resp.status_code == 200, resp.text
    assert _charge(client, batch, "OBSIDIAN")["chosen_document_id"] == doc

    row = _rows(client, batch)["obsidian.jpg"]
    assert row["card_source"] == "override"
    assert row["card"]["key"] == "corp-2838"
    assert row["person"] == "Dirk"


def test_a_card_number_the_receipt_prints_wins_over_the_settled_charge(
    client, monkeypatch
):
    """Pressmaster prints card 7777, which no registry card has; the reviewer
    pairs it with the 3645 charge by hand. The printed number keeps its
    question instead of being overwritten by the statement's card."""
    batch = _august(client, monkeypatch)
    charge = _charge(client, batch, "PRESSMASTER DMCC")
    doc = _rows(client, batch)["pressmaster.jpg"]["document_id"]
    _decide(client, batch, charge["transaction_id"], "confirmed", doc)
    assert _charge(client, batch, "PRESSMASTER DMCC")["effective_bucket"] == "reconciled"

    row = _rows(client, batch)["pressmaster.jpg"]
    assert row["card"] is None and row["card_source"] == "none"
    assert row["suggested_private"] is True
    assert "needs_company_or_person" in row["boxes"]


def test_the_settled_charge_outranks_a_card_remembered_from_an_earlier_month(
    client, monkeypatch
):
    """July's Obsidian receipt was fixed to 2838 by hand and published, so
    August's Obsidian receipt remembers 2838. August's statement puts the
    Obsidian charge on 3645; once that pair settles (confirmed here), the
    statement's card is the row's card, and memory, which is no decision on
    this row, gives way."""
    assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
    _wire(monkeypatch, _extraction("Obsidian", "96.00", "2026-07-30", "VISA"))
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "July 2026"}
    )
    _done(client, resp)
    july = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{july}/receipts",
        files=[("files", ("obs-july.jpg", JPG + b"july", "application/octet-stream"))],
    ))
    july_doc = _rows(client, july)["obs-july.jpg"]["document_id"]
    assert client.put(
        f"/api/runs/{july}/expenses/{july_doc}",
        json={"field": "card_key", "value": "corp-2838"},
    ).status_code == 200
    published = client.post(f"/api/runs/{july}/publish", json={"override": True})
    assert published.status_code == 200, published.text

    batch = _august(client, monkeypatch, wired=True)
    doc = _rows(client, batch)["obsidian.jpg"]["document_id"]
    obsidian = _charge(client, batch, "OBSIDIAN")
    # Unpaired, memory answers (item 137 keeps a 2838 receipt off a 3645 charge).
    assert obsidian["effective_bucket"] == "unmatched"
    remembered = _rows(client, batch)["obsidian.jpg"]
    assert remembered["card_source"] == "learned"
    assert remembered["card"]["key"] == "corp-2838"
    _decide(client, batch, obsidian["transaction_id"], "confirmed", doc)

    row = _rows(client, batch)["obsidian.jpg"]
    assert row["card_source"] == "settled_charge"
    assert row["card"]["key"] == "cloud-3645"
    assert row["person"] == "Nicolas"
    assert row["can_mark_private"] is False


# ── a company-card row ───────────────────────────────────────────────


def test_an_inherited_company_card_row_cannot_be_marked_private(client, monkeypatch):
    batch = _august(client, monkeypatch)
    row = _rows(client, batch)["lovable.jpg"]
    assert row["can_mark_private"] is False
    # The unpaired row keeps the option.
    assert _rows(client, batch)["notion.jpg"]["can_mark_private"] is True

    resp = client.post(
        f"/api/runs/{batch}/expenses/{row['document_id']}/private",
        json={"private": True, "reimburse_to": "Dirk"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "company_card"
    assert resp.json()["card"]["key"] == "corp-2838"
