"""Item 225 (note #91, operator 2026-09-25): what "Save corrections to memory"
shows has to read as concrete changes. On April 2026 it read "erick sports ·
Brisken Holding, LLC · card_key -> card-8311" and "This also updates 16
merchants", which two people who made those corrections could not follow.

Route-level through `GET /api/runs/{id}/memory-plan`:

* a remembered card is named the way Settings names it, with its person,
  never by its key, and the vendor as the receipt prints it;
* a merchant-list card change says what the next receipt gets and names the
  receipts it was seen on (`sources`), read from the same observations the
  card learner reads, so the list shown is the list taught;
* a merchant seen on two cards says no card is filled in, naming both.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-225"
CARDS = {
    "corp-1672": {
        "label": "Corporate card (Chase)", "digits": ["1672"],
        "entity": "Corporate Services", "person": "Nicolas",
        "zoho_account": "Chase 1672",
    },
    "cloud-9999": {
        "label": "Cloud card", "digits": ["9999"],
        "entity": "Cloud Services", "person": "Dirk",
        "zoho_account": "Chase 9999",
    },
}
MERCHANTS = {"Obsidian": {"aliases": ["Obsidian"], "category": None, "zoho_account": None}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        resp = c.put("/api/settings", json={"cards": CARDS, "merchants": MERCHANTS})
        assert resp.status_code == 200, resp.text
        yield c


def _month(client, monkeypatch, n: int) -> tuple[str, list[str]]:
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date=f"2026-07-1{i}", total=f"4{i}.50", currency="USD", vendor="OBSIDIAN",
            reference="", line_items=(), confidence=0.9, notes="",
        )
        for i in range(n)
    ])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "July 2026"})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    resp = client.post(f"/api/expense-batches/{batch}/receipts", files=[
        ("files", (f"o{i}.jpg", JPG + bytes([i, 7]) * (i + 1), "application/octet-stream"))
        for i in range(n)
    ])
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    rows = client.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return batch, [r["document_id"] for r in rows]


def _pick(client, batch, doc, key) -> None:
    resp = client.put(f"/api/runs/{batch}/expenses/{doc}",
                      json={"field": "card_key", "value": key})
    assert resp.status_code == 200, resp.text


def _lessons(client, batch) -> list[dict]:
    resp = client.get(f"/api/runs/{batch}/memory-plan")
    assert resp.status_code == 200, resp.text
    return resp.json()["lessons"]


def _one(lessons, **match) -> dict:
    hits = [lsn for lsn in lessons if all(lsn.get(k) == v for k, v in match.items())]
    assert len(hits) == 1, [(lsn["id"], lsn["description"]) for lsn in lessons]
    return hits[0]


def test_a_remembered_card_is_named_as_settings_names_it(client, monkeypatch):
    batch, (doc,) = _month(client, monkeypatch, 1)
    _pick(client, batch, doc, "corp-1672")

    lessons = _lessons(client, batch)
    card = next(lsn for lsn in lessons
                if lsn["table"] == "field_correction" and lsn["key"]["field"] == "card_key")
    text = card["description"]
    assert "paid with Corporate card (Chase) (Nicolas)" in text, text
    assert "OBSIDIAN" in text, text
    assert "corp-1672" not in text and "card_key" not in text, text
    assert [s["document_id"] for s in card["sources"]] == [doc]


def test_a_merchant_list_card_names_what_the_next_receipt_gets_and_its_receipts(
    client, monkeypatch,
):
    batch, (doc,) = _month(client, monkeypatch, 1)
    _pick(client, batch, doc, "corp-1672")

    reg = _one(_lessons(client, batch), id="registry:Obsidian")
    text = reg["description"]
    assert ("paid with Corporate card (Chase) (Nicolas), so its next receipt gets "
            "that card") in text, text
    assert "Seen on 1 receipt: OBSIDIAN 40.50 USD 2026-07-10." in text, text
    assert "corp-1672" not in text, text
    assert [s["document_id"] for s in reg["sources"]] == [doc]


def test_a_merchant_seen_on_two_cards_says_no_card_is_filled_in(client, monkeypatch):
    batch, (a, b) = _month(client, monkeypatch, 2)
    _pick(client, batch, a, "corp-1672")
    _pick(client, batch, b, "cloud-9999")

    reg = _one(_lessons(client, batch), id="registry:Obsidian")
    text = reg["description"]
    assert ("paid with Cloud card (Dirk) and Corporate card (Chase) (Nicolas), "
            "so no card is filled in for it") in text, text
    assert "Seen on 2 receipts" in text, text
    assert sorted(s["document_id"] for s in reg["sources"]) == sorted([a, b])
