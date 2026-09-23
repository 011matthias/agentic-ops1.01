"""Merchant registry on the web layer (2026-07-29): settings round-trip +
validation, and the registry driving a receipt-first batch (canonical vendor,
registry categorization that skips the LLM, reviewer-override precedence),
plus the self-improving upsert from corrections."""
from __future__ import annotations

import copy

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import registry_upserts_from_expense_run  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
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
    # 2026-09-08 split: empty company-month create + receipt add. Registry
    # canonicalization / categorization run on the add path now.
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": legal_entity}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    resp = client.post(
        f"/api/expense-batches/{body['batch_id']}/receipts",
        files=[
            ("files", (n, d, "application/octet-stream"))
            for n, d in (files or [("a.jpg", JPG)])
        ],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
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

    # A non-dict entry is still rejected at the edge; a category from
    # neither live vocabulary is DROPPED and named in `ignored`. The save
    # replaces the whole map, so refusing it would have 400'd the cards and
    # entities tabs too, over a value the editor never touched.
    resp = client.put(
        "/api/settings", json={"merchants": {"X": {"category": "Nope"}}}
    )
    assert resp.status_code == 200, resp.text
    assert "merchants.X.category" in resp.json()["ignored"]
    assert client.get(
        "/api/settings").json()["merchants"]["X"]["category"] is None
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
    seed = {
        "X": {"aliases": ["a"], "category": None, "zoho_account": None},
        "Amazon": {"aliases": [], "category": None, "zoho_account": None,
                   "multi_category": True, "cost_center": "Rome 26"},
    }
    new, summary = registry_upserts_from_expense_run(
        copy.deepcopy(seed),
        receipts=[_rec("d1", "Cafe")],
        effective_receipts=[_rec("d1", "Cafe")],
        field_overrides={},
        category_overrides={},
    )
    assert summary == {"aliases_added": 0, "categories_set": 0, "skipped_conflict": 0}
    assert new == seed


# ── item 116: sign-off carries every merchant entry whole ───────────
#
# Publishing a month (and the "Save corrections to memory" button) rewrote
# the whole registry from a copy holding only aliases / category / account,
# so `multi_category`, `cost_center` and any other key vanished from every
# merchant. Route-level: the settings map read back after the save is the
# assertion, not the helper's return value.

_REGISTRY_116 = {
    "Acme": {
        "aliases": ["ACME LTDA"], "category": None, "zoho_account": None,
        "multi_category": True, "cost_center": "Rome 26",
    },
    "Globex": {
        "aliases": ["GLOBEX CORP"], "category": "Software & Subscriptions",
        "zoho_account": "E300 - Software", "cost_center": "Operations",
        # A key the settings editor does not know yet must survive as well.
        "owner_note": "annual plan, renews in March",
    },
}


def _seed_registry(client, merchants: dict) -> dict:
    # Straight into the store (the PUT edge would drop `owner_note`), then
    # read back through the API so the comparison is what the screen sees.
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        store.set_settings({"merchants": copy.deepcopy(merchants)}, "2026-09-17T00:00:00")
    got = client.get("/api/settings").json()["merchants"]
    assert got == merchants, "precondition: the seeded registry reads back whole"
    return got


def test_publishing_a_month_with_no_edits_leaves_the_registry_whole(client, monkeypatch):
    before = _seed_registry(client, _REGISTRY_116)
    _patch_ocr(monkeypatch, _extraction(vendor="Staples"))
    batch = _create_batch(client)

    # No statement on this month: since item 100 publish needs the override.
    resp = client.post(f"/api/runs/{batch}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    memory = resp.json()["memory"]
    assert memory["saved"] is True
    assert memory["learned"]["registry"] == {
        "aliases_added": 0, "categories_set": 0, "skipped_conflict": 0,
        # Note item M2: the same reply now also counts the card
        # observations of the month. No card resolves on this month, so
        # the registry keeps its exact stored shape either way.
        "cards_seen": 0, "card_keys_learned": 0, "card_keys_dropped": 0,
        # Item 118: and the month's cost-centre picks. No centre is defined
        # on this month, so the fold has nothing to learn and the registry
        # keeps its exact stored shape here too.
        "cost_centers_set": 0, "cost_centers_skipped_conflict": 0,
    }
    assert client.get("/api/settings").json()["merchants"] == before


def test_saving_corrections_changes_only_what_the_edits_touched(client, monkeypatch):
    before = _seed_registry(client, _REGISTRY_116)
    _patch_ocr(monkeypatch, _extraction(vendor="Staples"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    for body in (
        {"field": "vendor", "value": "Acme"},
        {"field": "category", "value": "Office Supplies & Consumables"},
    ):
        resp = client.put(f"/api/runs/{batch}/expenses/{doc}", json=body)
        assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert resp.json()["learned"]["registry"] == {
        "aliases_added": 1, "categories_set": 1, "skipped_conflict": 0,
        "cards_seen": 0, "card_keys_learned": 0, "card_keys_dropped": 0,
        "cost_centers_set": 0, "cost_centers_skipped_conflict": 0,
    }

    after = client.get("/api/settings").json()["merchants"]
    assert list(after) == list(before)
    assert after["Globex"] == before["Globex"], "an untouched merchant changed"
    assert after["Acme"] == {
        **before["Acme"],
        "aliases": ["ACME LTDA", "Staples"],
        "category": "Office Supplies & Consumables",
    }, "the touched merchant lost a key or changed beyond its edits"

    # Saving the same corrections again changes nothing, and the reply says
    # so: the counts name what was written, not what was re-affirmed.
    resp = client.post(f"/api/runs/{batch}/commit-memory")
    assert resp.status_code == 200, resp.text
    assert resp.json()["learned"]["registry"] == {
        "aliases_added": 0, "categories_set": 0, "skipped_conflict": 0,
        "cards_seen": 0, "card_keys_learned": 0, "card_keys_dropped": 0,
        "cost_centers_set": 0, "cost_centers_skipped_conflict": 0,
    }
    assert client.get("/api/settings").json()["merchants"] == after
