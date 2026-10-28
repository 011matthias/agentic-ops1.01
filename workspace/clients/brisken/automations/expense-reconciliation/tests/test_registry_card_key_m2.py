"""Note item M2 (owner, 2026-09-18): card-specific, exclusive vendor spend.

Measured on live July, August and September 2026 (128 rows, 60 display
vendors): 34 vendors were seen on exactly ONE card, 5 on several (the AI
vendors and the two spellings around them), 21 on none at all. So a merchant
whose spend is exclusively on one card can answer "which card paid" for a
receipt that prints nothing, and a merchant seen on two must not.

Pinned here, route-level through the FastAPI app:

* a registry `card_key` carries a receipt that prints no card, as the LAST
  link of the chain (`card_source: "merchant"`), and never outranks a printed
  number, a row pick, a settling charge or a remembered card;
* a key naming no defined card resolves nothing rather than stamping a card
  nobody has, and the private option stays open on a merchant-carded row;
* publishing accumulates `cards_seen` and writes `card_key` only while it
  holds exactly one card; a second card drops a LEARNED key and never a
  typed one; the learner never feeds its own card back;
* the CSV export names the same card the grid does.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes-m2"

CARDS = {
    "corp-1672": {
        "label": "Corporate card (Chase)",
        "digits": ["1672"],
        "entity": "Corporate Services",
        "person": "Nicolas",
        "zoho_account": "Chase 1672",
    },
    "cloud-9999": {
        "label": "Cloud card",
        "digits": ["9999"],
        "entity": "Cloud Services",
        "person": "Dirk",
        "zoho_account": "Chase 9999",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-07-10", total="42.50", currency="USD",
                vendor="Obsidian", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


_SEQ = [0]


def _month(client, monkeypatch, *extractions, label="July 2026") -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"m2-{_SEQ[0]}.jpg",
                                JPG + bytes([_SEQ[0] % 256, 11]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _rows(client, batch_id) -> list[dict]:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"]


def _row(client, batch_id, vendor: str) -> dict:
    rows = [e for e in _rows(client, batch_id)
            if vendor.lower() in e["vendor"]["display"].lower()]
    assert len(rows) == 1, [e["vendor"]["display"] for e in _rows(client, batch_id)]
    return rows[0]


def _settings(client) -> dict:
    return client.get("/api/settings").json()


def _put_merchants(client, merchants: dict) -> None:
    resp = client.put("/api/settings", json={"merchants": merchants})
    assert resp.status_code == 200, resp.text


def _merchant(client, name: str) -> dict:
    return (_settings(client).get("merchants") or {})[name]


def _publish(client, batch_id) -> dict:
    resp = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    memory = resp.json()["memory"]
    assert memory.get("saved") is True, memory
    return memory["learned"]


def _obsidian(card_key: str | None = None, **extra) -> dict:
    entry: dict = {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
    }
    if card_key is not None:
        entry["card_key"] = card_key
    entry.update(extra)
    return {"Obsidian": entry}


# ── the last link of the chain ─────────────────────────────────────────


def test_a_merchant_card_carries_a_receipt_that_prints_nothing(client, monkeypatch):
    """The whole point: Obsidian's spend is exclusively on the cloud card, so
    a receipt of Obsidian that prints no payment method at all takes that
    card, and with it the company and the person. Without the registry entry
    the same row resolves nothing."""
    client.put("/api/settings", json={"cards": CARDS})
    batch = _month(client, monkeypatch, _extraction())

    bare = _row(client, batch, "Obsidian")
    assert bare["card"] is None and bare["card_source"] == "none"
    assert bare["legal_entity_id"] == ""

    _put_merchants(client, _obsidian("cloud-9999"))
    carried = _row(client, batch, "Obsidian")
    assert carried["card_source"] == "merchant"
    assert carried["card"]["key"] == "cloud-9999"
    assert carried["legal_entity_id"] == "Cloud Services"
    assert carried["entity_source"] == "card"
    assert carried["person"] == "Dirk" and carried["person_source"] == "card"


def test_a_printed_card_number_outranks_the_merchant_card(client, monkeypatch):
    """Memory about the brand never overrides a number the document shows —
    the same guard item 87 put on a remembered card."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, _obsidian("cloud-9999"))
    batch = _month(client, monkeypatch, _extraction(payment_hint="VISA ...1672"))

    row = _row(client, batch, "Obsidian")
    assert row["card_source"] == "hint"
    assert row["card"]["key"] == "corp-1672"
    assert row["legal_entity_id"] == "Corporate Services"


def test_a_row_pick_outranks_the_merchant_card(client, monkeypatch):
    """The reviewer's own fix wins over everything, registry included."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, _obsidian("cloud-9999"))
    batch = _month(client, monkeypatch, _extraction())
    doc = _row(client, batch, "Obsidian")["document_id"]

    resp = client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "card_key", "value": "corp-1672"},
    )
    assert resp.status_code == 200, resp.text
    row = _row(client, batch, "Obsidian")
    assert row["card_source"] == "override"
    assert row["card"]["key"] == "corp-1672"


def test_a_key_naming_no_defined_card_resolves_nothing(client, monkeypatch):
    """Edit order must not matter, so the key is stored unchecked — and an
    unresolvable one leaves the row uncarded rather than stamping a card
    nobody has."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, _obsidian("no-such-card"))
    batch = _month(client, monkeypatch, _extraction())

    row = _row(client, batch, "Obsidian")
    assert row["card"] is None and row["card_source"] == "none"
    assert _merchant(client, "Obsidian")["card_key"] == "no-such-card"


def test_a_merchant_carded_row_can_still_be_marked_private(client, monkeypatch):
    """A registry card is memory about the brand, not a decision about this
    row, so the reviewer keeps the private-card exit — exactly as she does on
    a remembered card (`learned`)."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, _obsidian("cloud-9999"))
    batch = _month(client, monkeypatch, _extraction())

    row = _row(client, batch, "Obsidian")
    assert row["card_source"] == "merchant"
    assert row["can_mark_private"] is True


def test_the_settings_put_round_trips_the_three_card_fields(client):
    """The Settings editor replaces the whole map, so a field it drops is
    erased. All three survive a round trip; `card_key_learned` only beside a
    key, and `cards_seen` deduped and sorted."""
    _put_merchants(client, {"Obsidian": {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
        "card_key": "cloud-9999", "card_key_learned": True,
        "cards_seen": ["cloud-9999", " corp-1672 ", "cloud-9999"],
    }})
    entry = _merchant(client, "Obsidian")
    assert entry["card_key"] == "cloud-9999"
    assert entry["card_key_learned"] is True
    assert entry["cards_seen"] == ["cloud-9999", "corp-1672"]

    _put_merchants(client, {"Obsidian": {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
        "card_key_learned": True,
    }})
    entry = _merchant(client, "Obsidian")
    assert "card_key" not in entry and "card_key_learned" not in entry


# ── what publishing learns ─────────────────────────────────────────────


def test_publishing_learns_the_card_of_a_single_card_merchant(client, monkeypatch):
    """Two Obsidian receipts, both printing the cloud card. At sign-off the
    registry records the observation and, because it is the only card the
    merchant has been seen on, writes it as the entry's `card_key` and marks
    it machine-written."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, _obsidian())
    batch = _month(
        client, monkeypatch,
        _extraction(payment_hint="VISA ...9999"),
        _extraction(payment_hint="VISA ...9999", total="19.00"),
    )

    learned = _publish(client, batch)
    assert learned["registry"]["cards_seen"] == 1
    assert learned["registry"]["card_keys_learned"] == 1
    assert learned["registry"]["card_keys_dropped"] == 0

    entry = _merchant(client, "Obsidian")
    assert entry["cards_seen"] == ["cloud-9999"]
    assert entry["card_key"] == "cloud-9999"
    assert entry["card_key_learned"] is True


def test_a_second_card_drops_a_learned_key_but_never_a_typed_one(client, monkeypatch):
    """Two cards are a fact about the merchant, not a conflict to resolve by
    guessing: the learned key goes and the row goes back to asking. A key an
    editor typed carries no machine mark and survives the same observation."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, {"Obsidian": {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
        "card_key": "cloud-9999", "card_key_learned": True,
        "cards_seen": ["cloud-9999"],
    }})
    batch = _month(
        client, monkeypatch, _extraction(payment_hint="VISA ...1672"),
        label="August 2026",
    )
    learned = _publish(client, batch)
    assert learned["registry"]["card_keys_dropped"] == 1

    entry = _merchant(client, "Obsidian")
    assert entry["cards_seen"] == ["cloud-9999", "corp-1672"]
    assert "card_key" not in entry and "card_key_learned" not in entry

    # The same month again, against a key a person typed: untouched.
    _put_merchants(client, {"Obsidian": {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
        "card_key": "cloud-9999", "cards_seen": ["cloud-9999"],
    }})
    batch2 = _month(
        client, monkeypatch, _extraction(payment_hint="VISA ...1672"),
        label="September 2026",
    )
    learned2 = _publish(client, batch2)
    assert learned2["registry"]["card_keys_dropped"] == 0
    entry2 = _merchant(client, "Obsidian")
    assert entry2["card_key"] == "cloud-9999"
    assert entry2["cards_seen"] == ["cloud-9999", "corp-1672"]


def test_the_learner_never_feeds_the_registrys_own_card_back(client, monkeypatch):
    """A receipt carried by the registry card is not evidence about the
    merchant: the month observes nothing, so `cards_seen` stays as it was and
    one lent card can never harden into a fact."""
    client.put("/api/settings", json={"cards": CARDS})
    _put_merchants(client, {"Obsidian": {
        "aliases": ["Obsidian"], "category": None, "zoho_account": None,
        "card_key": "cloud-9999",
    }})
    batch = _month(client, monkeypatch, _extraction())
    assert _row(client, batch, "Obsidian")["card_source"] == "merchant"

    learned = _publish(client, batch)
    assert learned["registry"]["cards_seen"] == 0
    assert learned["registry"]["card_keys_learned"] == 0
    assert "cards_seen" not in _merchant(client, "Obsidian")


# ── the export agrees with the grid ────────────────────────────────────


def test_the_csv_names_the_same_card_the_grid_does(client, monkeypatch):
    """Grid == export by construction. The CSV resolves its rows through the
    same chain, so a merchant-carded row books to that card's account instead
    of falling through to the batch default."""
    client.put("/api/settings", json={"cards": CARDS})
    batch = _month(client, monkeypatch, _extraction())
    before = client.get(f"/runs/{batch}/expenses.csv")
    assert before.status_code == 200, before.text
    assert "Chase 9999" not in before.text

    _put_merchants(client, _obsidian("cloud-9999"))
    assert _row(client, batch, "Obsidian")["card"]["key"] == "cloud-9999"
    after = client.get(f"/runs/{batch}/expenses.csv")
    assert after.status_code == 200, after.text
    assert "Chase 9999" in after.text
