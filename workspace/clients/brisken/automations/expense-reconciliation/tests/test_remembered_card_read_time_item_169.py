"""Item 169: a remembered card reaches a month that was ingested BEFORE the
correction was taught.

Measured on the live store 2026-09-23, before anything was changed. September
2026 held 75 receipts, 26 of them with no card, 25 with no legal entity and 25
with no person; every entity-less and person-less row in all three live months
was a card-less row, so the card is the root of three columns at once. The
correction `('', 'openai') -> 3645` had been saved that morning, named a card
the batch holds, and matched 12 of those card-less rows on a key that already
lined up. It reached none of them.

The cause is not the key and not the card. `resolve_batch_row_cards` takes its
`learned` candidate off `Receipt.card_key`, and the only writer of that field
is `ExpenseMemory.apply` inside `generate_expenses`. A correction is therefore
frozen at the moment a month was ingested: it reaches months ingested after it
and can never reach the ones ingested before. Every link beside it is read
live -- the reviewer's pick, the batch's hints, the settled charge, and the
merchant registry, whose note says so in as many words.

Pinned here route-level, through the grid and the CSV export, because those
are the two surfaces Cards R3 requires to name the same card for one receipt:

* a month ingested BEFORE the correction takes it, and its company and person
  arrive with it;
* the chain's precedence is untouched: a printed card number still wins;
* the export files the receipt under the card the grid showed;
* with no learning store, every receipt passes through unchanged.
"""
from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import fill_remembered_cards  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

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

# Item 173: a remembered card applies only to a brand the registry vouches is
# paid on ONE card. `cards_seen` is the machine-kept record note item M2's own
# card learner already gates on; these mirror it.
ONE_CARD_MERCHANT = {
    "OpenAI": {
        "aliases": [],
        "category": "Software & Subscriptions",
        "zoho_account": None,
        "cards_seen": ["corp-1672"],
    }
}
TWO_CARD_MERCHANT = {
    "OpenAI": {
        "aliases": [],
        "category": "Software & Subscriptions",
        "zoho_account": None,
        "cards_seen": ["corp-1672", "cloud-9999"],
    }
}

_SEQ = [0]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-09-10", total="80.04", currency="USD",
                vendor="OpenAI", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, monkeypatch, *extractions, label="September 2026") -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    files = []
    for _ in extractions:
        _SEQ[0] += 1
        files.append(("files", (f"r{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 11]),
                                "application/octet-stream")))
    resp = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, batch_id, vendor: str) -> list[dict]:
    return [
        e for e in _grid(client, batch_id)["expenses"]
        if (e["vendor"] or {}).get("display") == vendor
    ]


def _fix(client, batch_id, doc, key):
    return client.put(
        f"/api/runs/{batch_id}/expenses/{doc}", json={"field": "card_key", "value": key}
    )


def _publish(client, batch_id) -> dict:
    resp = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    return resp.json()["memory"]


def _teach_openai_card(client, monkeypatch, key="corp-1672") -> None:
    """Sign off a throwaway month whose single OpenAI row the reviewer fixed,
    which is how a card correction enters the learning store."""
    teaching = _create_batch(client, monkeypatch, _extraction(), label="Teaching")
    doc = _rows(client, teaching, "OpenAI")[0]["document_id"]
    assert _fix(client, teaching, doc, key).status_code == 200
    _publish(client, teaching)


# ── the month that was already there ─────────────────────────────────


def test_a_month_ingested_before_the_correction_takes_it(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    # September exists FIRST, with nothing taught yet.
    september = _create_batch(
        client, monkeypatch,
        _extraction(total="80.04", date="2026-09-10"),
        _extraction(total="82.15", date="2026-09-22"),
    )
    before = _grid(client, september)
    assert [r["card"] for r in before["expenses"]] == [None, None]
    assert before["summary"]["n_needs_company_or_person"] == 2

    _teach_openai_card(client, monkeypatch)

    after = _grid(client, september)
    rows = [e for e in after["expenses"] if (e["vendor"] or {}).get("display") == "OpenAI"]
    assert len(rows) == 2
    for row in rows:
        assert row["card"]["key"] == "corp-1672"
        assert row["card_source"] == "learned"
        # The card is the root of three columns: company and person ride it.
        assert row["legal_entity_id"] == "Corporate Services"
        assert row["entity_source"] == "card"
        assert row["person"] == "Nicolas"
        assert row["person_source"] == "card"
        assert "needs_company_or_person" not in row["boxes"]
    assert after["summary"]["n_needs_company_or_person"] == 0


def test_a_printed_card_number_still_wins_over_the_memory(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    september = _create_batch(
        client, monkeypatch,
        _extraction(payment_hint="VISA ending 9999"),
    )
    _teach_openai_card(client, monkeypatch, key="corp-1672")

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"]["key"] == "cloud-9999"
    assert row["card_source"] == "hint"
    assert row["person"] == "Dirk"


def test_a_reviewer_pick_on_the_row_still_wins(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    september = _create_batch(client, monkeypatch, _extraction())
    _teach_openai_card(client, monkeypatch, key="corp-1672")
    doc = _rows(client, september, "OpenAI")[0]["document_id"]
    assert _fix(client, september, doc, "cloud-9999").status_code == 200

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"]["key"] == "cloud-9999" and row["card_source"] == "override"


def test_the_export_files_it_under_the_card_the_grid_showed(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    september = _create_batch(client, monkeypatch, _extraction())
    _teach_openai_card(client, monkeypatch)
    assert _rows(client, september, "OpenAI")[0]["card"]["key"] == "corp-1672"

    resp = client.get(f"/runs/{september}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    openai_rows = [r for r in rows if "OpenAI" in " ".join(r.values())]
    assert openai_rows, rows
    # Cards R3: the file names the same company the screen did.
    assert any("Corporate Services" in " ".join(r.values()) for r in openai_rows)


# ── the quiet cases ──────────────────────────────────────────────────


def test_without_a_learning_store_every_receipt_passes_through(tmp_path):
    from expense_recon.matching.deterministic import Receipt

    receipts = [
        Receipt(document_id="a.pdf", legal_entity_id="", detected_date=None,
                detected_total=None, detected_currency="USD",
                detected_vendor="OpenAI", detected_reference=""),
    ]
    assert fill_remembered_cards(receipts, None) == receipts
    assert fill_remembered_cards(receipts, tmp_path / "nope.sqlite") == receipts
    assert fill_remembered_cards(receipts, None, ONE_CARD_MERCHANT) == receipts


def test_a_multi_card_brand_is_refused_the_remembered_card(client, monkeypatch):
    """Item 173, the owner's ruling. The live case: Criss's one OpenAI fix
    taught card 3645 while the hard evidence showed OpenAI on card-9693 eight
    times and 3645 once, and 12 September rows took the minority card. A brand
    the registry has seen on two cards lends neither."""
    client.put("/api/settings", json={"cards": CARDS, "merchants": TWO_CARD_MERCHANT})
    september = _create_batch(client, monkeypatch, _extraction())
    _teach_openai_card(client, monkeypatch, key="corp-1672")

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"] is None and row["card_source"] == "none"
    # And the two columns that ride the card stay honestly empty rather than
    # taking a company and a person off a card nobody vouched for.
    assert not str(row["legal_entity_id"] or "").strip()
    assert not str(row["person"] or "").strip()


def test_a_brand_the_registry_cannot_resolve_is_refused(client, monkeypatch):
    """No evidence of a second card is not evidence of one card. The vendor
    that motivated the ruling is exactly this case: OpenAI is not in the live
    registry at all, and adding it is the owner's call."""
    client.put("/api/settings", json={"cards": CARDS})  # no merchants at all
    september = _create_batch(client, monkeypatch, _extraction())
    _teach_openai_card(client, monkeypatch, key="corp-1672")

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"] is None and row["card_source"] == "none"


def test_a_month_with_no_correction_for_its_vendor_is_untouched(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    september = _create_batch(client, monkeypatch, _extraction(vendor="Hostinger"))
    _teach_openai_card(client, monkeypatch)

    row = _rows(client, september, "Hostinger")[0]
    assert row["card"] is None and row["card_source"] == "none"
