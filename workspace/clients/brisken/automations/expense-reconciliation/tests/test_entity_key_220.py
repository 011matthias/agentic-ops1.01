"""Item 220 step 5 (front 2): two spellings of one company are one company.

Live August 2026: the LOVABLE 15.00 charge on card 2838 carries "Corporate
Services" (the card's company, the provisioning spelling), and its receipt
was picked as "Brisken Corp Services, LLC" (the settings registry's Zoho
name for the same org, 822741658). The matcher's entity scope and the
hand-match guard compared the strings, so the receipt never reached its own
charge, and the picker offered eight names for five companies.

Route-level: the pairing through the statement attach (which re-matches),
the guard through `POST .../manual-match`, the picker through the grid and
settings routes, and the per-row advisory through the attach job's warning.
Stored values are never rewritten: the row keeps the spelling it was given.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.entity_keys import entity_key, entity_key_map  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

from tests.test_charge_entity import (  # noqa: E402
    REGISTRY,
    _attach_xlsx,
    _create_batch,
    _grid,
    _put_cards,
    _view,
    _wire,
)

PROVISION = {
    "entities": {
        "Corporate Services": {"org_id": "822741658"},
        "Cloud Services": {"org_id": "697686691"},
    },
}
# The live registry, org ids included: Holding carries GmbH's org id there
# (Zoho's own Holding org is 813627567), so an org-only key would merge them.
ENTITIES = {
    "Brisken Corp Services, LLC": {"org_id": "822741658"},
    "Brisken Cloud Services, LLC": {"org_id": "697686691"},
    "Brisken GmbH": {"org_id": "696750461"},
    "Brisken Holding, LLC": {"org_id": "696750461"},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prov = tmp_path / "prov.json"
    prov.write_text(json.dumps(PROVISION), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        resp = c.put("/api/settings", json={"entities": ENTITIES})
        assert resp.status_code == 200, resp.text
        yield c


def _lovable():
    return ExtractedReceipt(
        date="2026-08-31", total="15.00", currency="USD", vendor="Lovable",
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _month_with_company(client, monkeypatch, company, extraction=None):
    _put_cards(client, REGISTRY)
    _wire(monkeypatch, extraction or _lovable())
    batch_id = _create_batch(client)
    doc = _grid(client, batch_id)["expenses"][0]["document_id"]
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity",
        json={"legal_entity": company},
    )
    assert resp.status_code == 200, resp.text
    return batch_id, doc


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


# ── the resolver ────────────────────────────────────────────────────────


def test_a_label_resolves_to_its_orgs_provisioning_spelling():
    keys = entity_key_map({"entities": ENTITIES}, PROVISION)
    assert entity_key("Brisken Corp Services, LLC", keys=keys) == "Corporate Services"
    assert entity_key("  brisken cloud services, llc ", keys=keys) == "Cloud Services"
    # Neither has a provisioning spelling: each stays itself, never merged.
    assert entity_key("Brisken GmbH", keys=keys) == "Brisken GmbH"
    assert entity_key("Brisken Holding, LLC", keys=keys) == "Brisken Holding, LLC"
    assert entity_key("Unknown Ltd", keys=keys) == "Unknown Ltd"
    assert entity_key("", keys=keys) == ""


# ── the matcher's entity scope, through the re-match ────────────────────


def test_the_long_spelling_pairs_with_its_own_charge(client, monkeypatch):
    batch_id, doc = _month_with_company(
        client, monkeypatch, "Brisken Corp Services, LLC",
    )
    _attach_xlsx(client, batch_id)
    view = _view(client, batch_id)
    lovable = _row(view, "LOVABLE")
    assert lovable["legal_entity_id"] == "Corporate Services"
    assert lovable["chosen_document_id"] == doc
    # The row keeps the spelling it was given; nothing is rewritten.
    grid = _grid(client, batch_id)
    assert grid["expenses"][0]["legal_entity_id"] == "Brisken Corp Services, LLC"


def test_another_companys_long_spelling_still_never_pairs(client, monkeypatch):
    batch_id, doc = _month_with_company(
        client, monkeypatch, "Brisken Cloud Services, LLC",
    )
    _attach_xlsx(client, batch_id)
    lovable = _row(_view(client, batch_id), "LOVABLE")
    assert lovable["chosen_document_id"] != doc


# ── the hand-match guard ────────────────────────────────────────────────


def test_hand_match_accepts_the_same_company_under_another_spelling(client, monkeypatch):
    batch_id, doc = _month_with_company(
        client, monkeypatch, "Brisken Corp Services, LLC",
    )
    _attach_xlsx(client, batch_id)
    lovable = _row(_view(client, batch_id), "LOVABLE")
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": lovable["transaction_id"], "document_id": doc},
    )
    assert resp.status_code == 200, resp.text


def test_hand_match_still_refuses_another_company(client, monkeypatch):
    batch_id, doc = _month_with_company(
        client, monkeypatch, "Brisken Cloud Services, LLC",
    )
    _attach_xlsx(client, batch_id)
    lovable = _row(_view(client, batch_id), "LOVABLE")
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": lovable["transaction_id"], "document_id": doc},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "entity_differs"


# ── the picker ──────────────────────────────────────────────────────────


def test_the_picker_offers_each_company_once(client, monkeypatch):
    client.put("/api/settings", json={"entity_order": [
        "Brisken Corp Services, LLC", "Corporate Services", "Brisken GmbH",
    ]})
    options = client.get("/api/settings").json()["entity_options"]
    assert options == [
        "Corporate Services", "Brisken GmbH",
        "Brisken Holding, LLC", "Cloud Services",
    ]
    # A month whose row holds the long spelling still offers it, at the
    # back, so that row's select renders its value instead of a blank.
    batch_id, _doc = _month_with_company(
        client, monkeypatch, "Brisken Corp Services, LLC",
    )
    grid = _grid(client, batch_id)
    assert grid["entity_options"] == [*options, "Brisken Corp Services, LLC"]


# ── the per-row advisory ────────────────────────────────────────────────


def test_a_receipt_naming_a_company_with_no_card_is_named(client, monkeypatch):
    batch_id, _doc = _month_with_company(
        client, monkeypatch, "Brisken GmbH",
        ExtractedReceipt(
            date="2026-08-22", total="38.20", currency="EUR",
            vendor="Moghul Mahal", reference="", line_items=(),
            confidence=0.9, notes="", payment_hint=None,
        ),
    )
    job = _attach_xlsx(client, batch_id)
    assert "1 receipt names a company no card belongs to" in job["stage"]
    assert "Moghul Mahal (Brisken GmbH)" in job["stage"]


def test_the_long_spelling_raises_no_warning(client, monkeypatch):
    batch_id, _doc = _month_with_company(
        client, monkeypatch, "Brisken Corp Services, LLC",
    )
    job = _attach_xlsx(client, batch_id)
    assert "no card belongs to" not in (job["stage"] or "")
    assert "nothing will match across entities" not in (job["stage"] or "")
