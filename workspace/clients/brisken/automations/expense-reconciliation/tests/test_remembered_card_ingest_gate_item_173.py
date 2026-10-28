"""Item 173, second half: the INGEST stamp obeys the single-card gate too.

Item 173 gated the read-time half (`fill_remembered_cards`), which fills a
card for a month that was already ingested. The other door was left open. The
only writer of `Receipt.card_key` is `ExpenseMemory.apply` during
`generate_expenses`, and that stamp was ungated, so a month ingested AFTER a
multi-card brand had been corrected still carried the minority card into the
grid, where `resolve_batch_row_cards` reads it as the `learned` candidate and
the entity and the person ride it.

The two halves differ only in which month was created first, which is not a
rule anybody chose, so both now ask one question:
`MerchantRegistry.vouches_one_card`.

Pinned route-level, teaching BEFORE the month exists (the mirror image of
`test_remembered_card_read_time_item_169.py`, which creates it first):

* a one-card brand still takes its remembered card at ingest, so the gate is
  not simply switching the feature off;
* a two-card brand takes nothing, and the company and person it would have
  carried stay honestly empty;
* a brand the registry cannot resolve, and a run with no registry at all,
  take nothing either: no evidence of a second card is not evidence of one.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cli import generate_expenses  # noqa: E402
from expense_recon.learning.consult import (  # noqa: E402
    ExpenseMemory,
    FieldCorrectionLookup,
)
from expense_recon.learning.store import FieldCorrection  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.merchant_registry import (  # noqa: E402
    MerchantRegistry,
    drop_unvouched_remembered_cards,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0item173b-bytes"

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


def _merchant(*cards_seen: str) -> dict:
    return {
        "OpenAI": {
            "aliases": [],
            "category": "Software & Subscriptions",
            "zoho_account": None,
            "cards_seen": list(cards_seen),
        }
    }


ONE_CARD_MERCHANT = _merchant("corp-1672")
TWO_CARD_MERCHANT = _merchant("corp-1672", "cloud-9999")

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
        files.append(("files", (f"i173-{_SEQ[0]}.jpg", JPG + bytes([_SEQ[0] % 256, 11]),
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


def _teach_openai_card(client, monkeypatch, key="corp-1672") -> None:
    """Sign off a throwaway month whose single OpenAI row the reviewer fixed,
    which is how a card correction enters the learning store."""
    teaching = _create_batch(client, monkeypatch, _extraction(), label="Teaching")
    doc = _rows(client, teaching, "OpenAI")[0]["document_id"]
    resp = client.put(
        f"/api/runs/{teaching}/expenses/{doc}",
        json={"field": "card_key", "value": key},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/runs/{teaching}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text


# ── the month ingested after the correction ──────────────────────────


def test_a_one_card_brand_still_takes_its_remembered_card(client, monkeypatch):
    """The gate is not the feature switched off: this is the case item 87
    built the stamp for, and it still works."""
    client.put("/api/settings", json={"cards": CARDS, "merchants": ONE_CARD_MERCHANT})
    _teach_openai_card(client, monkeypatch)
    september = _create_batch(client, monkeypatch, _extraction())

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"]["key"] == "corp-1672"
    assert row["card_source"] == "learned"
    assert row["legal_entity_id"] == "Corporate Services"
    assert row["person"] == "Nicolas"


def test_a_two_card_brand_is_refused_at_ingest(client, monkeypatch):
    """The live case, arriving by the ingest door: Criss's one OpenAI fix
    taught the minority card, and a month ingested after it took the stamp
    regardless of what the registry had seen."""
    client.put("/api/settings", json={"cards": CARDS, "merchants": TWO_CARD_MERCHANT})
    _teach_openai_card(client, monkeypatch)
    september = _create_batch(client, monkeypatch, _extraction())

    row = _rows(client, september, "OpenAI")[0]
    assert (row["card"], row["card_source"]) == (None, "none")
    assert not str(row["legal_entity_id"] or "").strip()
    assert not str(row["person"] or "").strip()


def test_a_run_with_no_registry_is_refused_at_ingest(client, monkeypatch):
    """No evidence of a second card is not evidence of one card, and the
    read-time twin already answers this way, so the stamp must not put the
    card back by the other door."""
    client.put("/api/settings", json={"cards": CARDS})  # no merchants at all
    _teach_openai_card(client, monkeypatch)
    september = _create_batch(client, monkeypatch, _extraction())

    row = _rows(client, september, "OpenAI")[0]
    assert (row["card"], row["card_source"]) == (None, "none")


def test_a_printed_card_number_still_wins_at_ingest(client, monkeypatch):
    """The chain's precedence is untouched: the gate removes a remembered
    card, never a card the document names."""
    client.put("/api/settings", json={"cards": CARDS, "merchants": TWO_CARD_MERCHANT})
    _teach_openai_card(client, monkeypatch)
    september = _create_batch(
        client, monkeypatch, _extraction(payment_hint="VISA ending 9999")
    )

    row = _rows(client, september, "OpenAI")[0]
    assert row["card"]["key"] == "cloud-9999"
    assert row["card_source"] == "hint"


# ── the full-ingest path (the CLI's own generate_expenses) ───────────


def _memory_with_card(key: str) -> ExpenseMemory:
    """The learning store's answer, without a store: a card correction for
    OpenAI under the empty company, exactly what the reviewer's fix writes."""
    return ExpenseMemory(
        fields=FieldCorrectionLookup([
            FieldCorrection(
                legal_entity_id="", vendor_norm="openai", field="card_key",
                value=key, decision_count=1, last_confirmed_at=None,
                source_run=None,
            )
        ])
    )


def _generate(tmp_path, registry):
    """One OpenAI receipt through the whole CLI ingest, with a correction
    already taught. Returns the ingested receipt."""
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "openai.jpg").write_bytes(b"x")
    result = generate_expenses(
        {"expense": {"legal_entity_id": ""},
         "receipts": {"path": "receipts", "default_currency": "USD"}},
        tmp_path,
        llm_client=MockLLMClient(extraction_responses=[_extraction()]),
        expense_memory=_memory_with_card("corp-1672"),
        registry=registry,
    )
    assert len(result.receipts) == 1
    return result.receipts[0]


def test_the_full_ingest_keeps_a_one_card_brands_remembered_card(tmp_path):
    registry = MerchantRegistry.from_settings({"merchants": ONE_CARD_MERCHANT})
    assert _generate(tmp_path, registry).card_key == "corp-1672"


def test_the_full_ingest_drops_a_two_card_brands_remembered_card(tmp_path):
    registry = MerchantRegistry.from_settings({"merchants": TWO_CARD_MERCHANT})
    assert not _generate(tmp_path, registry).card_key


def test_the_full_ingest_drops_it_with_no_registry_at_all(tmp_path):
    assert not _generate(tmp_path, None).card_key


# ── the rule itself ──────────────────────────────────────────────────


class _Rcpt:
    """The three attributes the gate reads; it is duck-typed on purpose so
    the registry module never has to import the matching types."""

    def __init__(self, vendor, card_key):
        self.vendor_clean = vendor
        self.detected_vendor = vendor
        self.card_key = card_key

    def __eq__(self, other):  # replace() is not used on this stand-in
        return self is other


def test_the_gate_reads_cards_seen_off_the_registry_match():
    registry = MerchantRegistry.from_settings({"merchants": TWO_CARD_MERCHANT})
    match = registry.resolve("OpenAI", "OpenAI")
    assert match is not None
    assert sorted(match.cards_seen) == ["cloud-9999", "corp-1672"]
    assert registry.vouches_one_card("OpenAI", "OpenAI") is False

    one = MerchantRegistry.from_settings({"merchants": ONE_CARD_MERCHANT})
    assert one.vouches_one_card("OpenAI", "OpenAI") is True
    # A merchant the registry knows but has never seen a card for is vouched:
    # zero observations cannot contradict one card. An unknown vendor is not.
    bare = MerchantRegistry.from_settings({"merchants": _merchant()})
    assert bare.vouches_one_card("OpenAI", "OpenAI") is True
    assert bare.vouches_one_card("Hostinger", "Hostinger") is False


def test_a_receipt_with_no_remembered_card_is_returned_untouched():
    registry = MerchantRegistry.from_settings({"merchants": TWO_CARD_MERCHANT})
    r = _Rcpt("OpenAI", None)
    assert drop_unvouched_remembered_cards([r], registry) == [r]
    assert drop_unvouched_remembered_cards([r], None) == [r]
