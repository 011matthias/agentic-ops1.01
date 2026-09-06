"""Backlog item 40 (owner directive 2026-09-06): every expense belongs to
a person, THROUGH THE CARD.

Owner ruling, near-verbatim: "The person attribution should really only
happen depending on what card was used. Each card is attributed to a name
and therefore every expense can be attributed to a person. Even the ones
injected via email."

Pinned here:
* `person` round-trips all five card code points: normalize_cards_setting
  (the settings edge), cards_to_setting (the batch snapshot at creation),
  Card/_card_from_setting (the read side), card_to_dict (GET /api/cards),
  and refresh-master-data (settings edits reaching an existing batch).
* Rows carry `person` + `person_source` as PARALLEL fields; the resolved
  person is the LAST link of the existing card chain.
* A row that would otherwise be ready reads check/`needs_person` while
  its card carries no person; `n_needs_person` counts those rows beside
  MISSING ENTITY on both the summary and the card_review strip.
* NO sender-based attribution, ever: `submitted_by` is ingest provenance
  (a claim about who MAILED a file) and never becomes the expense's
  person — the owner said the card decides, even for mailed receipts.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cards import (  # noqa: E402
    Card,
    card_to_dict,
    cards_from_setting,
    cards_to_setting,
    normalize_cards_setting,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CARD_WITH_PERSON = {
    "corp-1672": {
        "label": "Corporate card (Chase)",
        "digits": ["1672"],
        "entity": "Corporate Services",
        "person": "Nicolas",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, n_files=1, label="August 2026"):
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
        for i in range(n_files)
    ]
    resp = client.post("/api/expense-batches", files=files,
                       data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── unit: the field round-trips the card model ───────────────────────


def test_person_round_trips_the_card_model():
    cleaned = normalize_cards_setting(CARD_WITH_PERSON)
    assert cleaned["corp-1672"]["person"] == "Nicolas"
    cards = cards_from_setting(cleaned)
    assert cards["corp-1672"].person == "Nicolas"
    assert card_to_dict(cards["corp-1672"])["person"] == "Nicolas"
    # snapshot serialization (what create_expense_batch stamps) keeps it
    assert cards_to_setting(cards)["corp-1672"]["person"] == "Nicolas"
    # blank person is dropped at the edge, not stored as ""
    cleaned = normalize_cards_setting({"c": {"person": "  "}})
    assert "person" not in cleaned["c"]
    assert Card(key="c").person == ""


# ── through the caller: settings -> snapshot -> row ──────────────────


def test_row_person_resolves_from_the_card_chain(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARD_WITH_PERSON})
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="Visa ...1672"),
        _extraction(vendor="Cash Corner", total="5.00"),  # no hint
    )
    batch = _create_batch(client, n_files=2)
    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}
    attributed = by_vendor["Staples"]
    assert attributed["person"] == "Nicolas"
    assert attributed["person_source"] == "card"
    assert attributed["card"]["person"] == "Nicolas"
    unattributed = by_vendor["Cash Corner"]
    assert unattributed["person"] == ""
    assert unattributed["person_source"] == "none"
    assert grid["summary"]["n_needs_person"] == 1
    assert grid["card_review"]["n_needs_person"] == 1
    # GET /api/cards carries the person column for the settings editor
    cards = client.get("/api/cards").json()["cards"]
    assert {c["key"]: c["person"] for c in cards}["corp-1672"] == "Nicolas"


def test_needs_person_fires_only_on_otherwise_ready_rows(client, monkeypatch):
    # card known, entity known, NO person yet
    client.put("/api/settings", json={"cards": {
        "corp-1672": {"digits": ["1672"], "entity": "Corporate Services"},
    }})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _grid(client, batch)["expenses"][0]["document_id"]

    # uncategorized: the more actionable per-row exception wins
    assert _grid(client, batch)["expenses"][0]["review"]["reason_code"] in (
        "uncategorized", "partial_uncategorized",
    )
    r = client.post(f"/api/runs/{batch}/categories", json={
        "document_id": doc, "line_index": 0,
        "category": "Software & Subscriptions",
    })
    assert r.status_code == 200, r.text

    row = _grid(client, batch)["expenses"][0]
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "needs_person"
    assert row["review"]["reason"]  # rule 5: the human label rides beside

    # the fifth code point: a settings person reaches the existing batch
    # ONLY through refresh-master-data (snapshot discipline) ...
    client.put("/api/settings", json={"cards": {
        "corp-1672": {
            "digits": ["1672"], "entity": "Corporate Services",
            "person": "Nicolas",
        },
    }})
    before = _grid(client, batch)["expenses"][0]
    assert before["person"] == ""  # snapshot still authoritative

    resp = client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    assert resp.status_code == 200, resp.text
    changes = {c["field"]: c for c in resp.json()["changes"]}
    assert "cards" in changes
    assert changes["row_persons"]["n_rows_changed"] == 1

    after = _grid(client, batch)["expenses"][0]
    assert after["person"] == "Nicolas"
    assert after["review"]["state"] == "ready"
    assert _grid(client, batch)["summary"]["n_needs_person"] == 0


def test_submitted_by_never_becomes_the_person(client, monkeypatch):
    """The anti-generalization pin: sender identity is provenance, not
    attribution. A mailed receipt's person comes from the CARD; a mailed
    receipt with no card gets NO person — never the sender."""
    client.put("/api/settings", json={"cards": CARD_WITH_PERSON})
    _patch_ocr(
        monkeypatch,
        _extraction(payment_hint="Visa ...1672"),
        _extraction(vendor="No Card Co", total="7.00"),
    )
    batch = _create_batch(client, n_files=2)
    grid = _grid(client, batch)
    docs = {e["vendor"]["display"]: e["document_id"] for e in grid["expenses"]}

    # simulate mail provenance the way the intake stamps it
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        run = store.get_run(batch)
        snapshot = dict(run.snapshot or {})
        snapshot["intake_provenance"] = {
            doc: {"person": "Dirk", "source": "alias",
                  "address": "dirk.neumann@brisken.com",
                  "received_at": "2026-08-02T09:00:00"}
            for doc in docs.values()
        }
        store.update_run_snapshot(batch, snapshot)
    finally:
        store.close()

    grid = _grid(client, batch)
    by_vendor = {e["vendor"]["display"]: e for e in grid["expenses"]}
    assert by_vendor["Staples"]["submitted_by"]["person"] == "Dirk"
    assert by_vendor["Staples"]["person"] == "Nicolas"  # the card decides
    assert by_vendor["No Card Co"]["submitted_by"]["person"] == "Dirk"
    assert by_vendor["No Card Co"]["person"] == ""  # never the sender
    assert by_vendor["No Card Co"]["person_source"] == "none"


def test_assign_with_person_attributes_the_rows(client, monkeypatch):
    """The strip's Assign-with-person path: a new card created at
    assignment time carries its person into the batch registry, so the
    assigned rows attribute in the same click."""
    _patch_ocr(monkeypatch, _extraction(payment_hint="****0340"))
    batch = _create_batch(client)
    resp = client.post(f"/api/expense-batches/{batch}/cards", json={
        "assignments": [{"hint": "****0340", "card": "card-0340"}],
        "new_cards": {"card-0340": {
            "label": "Visa 0340", "entity": "Cloud Services",
            "person": "Criss",
        }},
        "learn": True,
    })
    assert resp.status_code == 200, resp.text
    row = _grid(client, batch)["expenses"][0]
    assert row["person"] == "Criss"
    assert row["person_source"] == "card"
    # learn=True persisted the person into settings for the next batch
    settings_cards = client.get("/api/cards").json()["cards"]
    assert {c["key"]: c["person"] for c in settings_cards}["card-0340"] == "Criss"
