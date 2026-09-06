"""Merchant registry on the web layer (2026-07-29): settings round-trip +
validation, and the registry driving a receipt-first batch (canonical vendor,
registry categorization that skips the LLM, reviewer-override precedence),
plus the self-improving upsert from corrections."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import registry_upserts_from_expense_run  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> MockLLMClient:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_batch(client, files=None, legal_entity="Corporate Services"):
    payload = [
        ("files", (n, d, "application/octet-stream"))
        for n, d in (files or [("a.jpg", JPG)])
    ]
    resp = client.post(
        "/api/expense-batches", files=payload, data={"legal_entity": legal_entity}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _row(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"][0]


# ── settings round-trip + validation ────────────────────────────────


def test_settings_merchants_roundtrip_and_validation(client):
    assert client.get("/api/settings").json()["merchants"] == {}

    resp = client.put("/api/settings", json={"merchants": {
        "Uber": {"aliases": ["UBER *EATS", "UBER *EATS"],
                 "category": "Travel & Transport", "zoho_account": "E1"},
    }})
    assert resp.status_code == 200
    got = client.get("/api/settings").json()["merchants"]
    assert got["Uber"]["category"] == "Travel & Transport"
    assert got["Uber"]["aliases"] == ["UBER *EATS"]      # deduped
    assert got["Uber"]["zoho_account"] == "E1"

    # Bad category / non-dict entry are rejected at the edge.
    assert client.put(
        "/api/settings", json={"merchants": {"X": {"category": "Nope"}}}
    ).status_code == 400
    assert client.put(
        "/api/settings", json={"merchants": {"X": "nope"}}
    ).status_code == 400

    # Whole-map replace: an empty map clears the registry.
    client.put("/api/settings", json={"merchants": {}})
    assert client.get("/api/settings").json()["merchants"] == {}


# ── registry driving a batch ────────────────────────────────────────


def test_registry_canonicalizes_and_categorizes_skipping_llm(client, monkeypatch):
    client.put("/api/settings", json={"merchants": {
        "Acme": {"aliases": ["ACME LTDA"],
                 "category": "Office Supplies & Consumables",
                 "zoho_account": "E200010 - Office Supplies"},
    }})
    mock = _patch_ocr(monkeypatch, _extraction(vendor="ACME LTDA", total="12.00"))
    batch = _create_batch(client)
    row = _row(client, batch)

    assert row["vendor"]["display"] == "Acme"
    assert row["vendor"]["raw"] == "ACME LTDA"
    assert row["vendor"]["source"] == "registry"
    assert row["posting_category"]["category"] == "Office Supplies & Consumables"
    assert row["posting_category"]["source"] == "registry"
    # Item 40 sharpened "done": category + entity are settled, so the one
    # thing left is that no card (hence no person) owns this expense.
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "needs_person"
    # Deterministic-first: the LLM classifier was never consulted for it.
    assert not any(c[0].startswith("classify") for c in mock.calls)


def test_reviewer_vendor_override_beats_registry(client, monkeypatch):
    client.put("/api/settings", json={"merchants": {
        "Acme": {"aliases": ["ACME LTDA"], "category": "Office Supplies & Consumables"},
    }})
    _patch_ocr(monkeypatch, _extraction(vendor="ACME LTDA"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]

    assert client.put(
        f"/api/runs/{batch}/expenses/{doc}",
        json={"field": "vendor", "value": "Acme Superstore"},
    ).status_code == 200
    row = _row(client, batch)
    assert row["vendor"]["display"] == "Acme Superstore"
    assert row["vendor"]["source"] == "override"
    assert row["vendor"]["raw"] == "ACME LTDA"


def test_registry_naming_only_lets_llm_categorize(client, monkeypatch):
    # A merchant in the registry for NAMING only (no default category): the
    # canonical name is applied, but the category still comes from the LLM.
    client.put("/api/settings", json={"merchants": {"Acme": {"aliases": ["ACME LTDA"]}}})
    mock = _patch_ocr(monkeypatch, _extraction(vendor="ACME LTDA"))
    batch = _create_batch(client)
    row = _row(client, batch)

    assert row["vendor"]["display"] == "Acme"
    assert row["vendor"]["source"] == "registry"
    assert any(c[0].startswith("classify") for c in mock.calls)   # LLM consulted
    pc = row["posting_category"]
    assert pc is None or pc["source"] != "registry"


# ── the self-improving upsert (pure) ────────────────────────────────


def _rec(doc, vendor, canonical=None):
    return Receipt(
        document_id=doc, legal_entity_id="e", detected_date=None,
        detected_total=None, detected_currency=None,
        detected_vendor=vendor, canonical_vendor=canonical,
    )


def test_upsert_learns_vendor_alias_and_category():
    new, summary = registry_upserts_from_expense_run(
        {},
        receipts=[_rec("d1", "Staples")],
        effective_receipts=[_rec("d1", "Staples Inc")],   # vendor edit applied
        field_overrides={"d1": {"vendor": "Staples Inc"}},
        category_overrides={("d1", 0): {
            "category": "Office Supplies & Consumables",
            "zoho_account": "E200",
        }},
    )
    assert "Staples" in new["Staples Inc"]["aliases"]
    assert new["Staples Inc"]["category"] == "Office Supplies & Consumables"
    assert new["Staples Inc"]["zoho_account"] == "E200"
    assert summary["aliases_added"] == 1 and summary["categories_set"] == 1


def test_upsert_category_conflict_is_skipped():
    new, summary = registry_upserts_from_expense_run(
        {},
        receipts=[_rec("d1", "Cafe"), _rec("d2", "Cafe")],
        effective_receipts=[_rec("d1", "Cafe"), _rec("d2", "Cafe")],
        field_overrides={},
        category_overrides={
            ("d1", 0): {"category": "Meals & Entertainment"},
            ("d2", 0): {"category": "Travel & Transport"},
        },
    )
    assert summary["skipped_conflict"] == 1
    assert new.get("Cafe", {}).get("category") is None


def test_upsert_no_edits_is_noop():
    seed = {"X": {"aliases": ["a"], "category": None, "zoho_account": None}}
    new, summary = registry_upserts_from_expense_run(
        seed,
        receipts=[_rec("d1", "Cafe")],
        effective_receipts=[_rec("d1", "Cafe")],
        field_overrides={},
        category_overrides={},
    )
    assert summary == {"aliases_added": 0, "categories_set": 0, "skipped_conflict": 0}
    assert new == seed
