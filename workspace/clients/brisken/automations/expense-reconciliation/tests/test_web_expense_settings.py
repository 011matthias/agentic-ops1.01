"""Phase 5: categories predetermined + legal entity definable.

Categories stay the fixed 8 and surface read-only in settings. Legal
entities become a settings REGISTRY (`settings["entities"]`) the UI can
edit: org_id/chart_path/scope_groups drive the COA gate (winning over the
/data provisioning file, which stays the fallback), `default_paid_through`
rides into each new batch's config, and `account_picks` curates the
account picker. The account picker otherwise reuses the scoped
postable-account labels the categorizer was constrained to — never the
full unscoped chart.
"""
from __future__ import annotations

import csv
import io
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.coa_provision import coa_validation_from_settings  # noqa: E402
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
COL_PAID_THROUGH = EXPENSE_COLUMNS.index("Paid Through")

# Same synthetic shape as test_coa_provision._COA_JSON (the real Books COA
# is sensitive client data, never in this repo).
_COA_JSON = {
    "822741658": {
        "org": {"name": "Corporate Services"},
        "accounts": [
            {"account_id": "1", "account_name": "Office Supplies",
             "account_code": "E500", "account_type": "expense",
             "parent_account_name": "MS | OpeEx", "is_active": True},
            {"account_id": "2", "account_name": "MS | OpeEx",
             "account_code": "E5", "account_type": "expense",
             "parent_account_name": None, "is_active": True},
        ],
    },
}

_FILE_PROVISION = {
    "chart_path": "/data/coa.json",
    "entities": {
        "Corporate Services": {
            "org_id": "FILE-ORG",
            "scope_groups": ["File Scope"],
        },
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
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


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, legal_entity="Corporate Services"):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": legal_entity},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return resp.json()["batch_id"]


# ── coa_validation_from_settings (unit) ─────────────────────────────


def test_settings_entry_wins_over_file_entity():
    settings = {"entities": {"Corporate Services": {
        "org_id": "SETTINGS-ORG", "scope_groups": ["Settings Scope"],
    }}}
    block = coa_validation_from_settings(
        "Corporate Services", settings, _FILE_PROVISION
    )
    assert block["org_id"] == "SETTINGS-ORG"
    assert block["scope_groups"] == ["Settings Scope"]
    # chart_path falls back to the file's when the entry names none.
    assert block["chart_path"] == "/data/coa.json"


def test_settings_only_entry_with_own_chart_path_needs_no_file():
    settings = {"entities": {"Corporate Services": {
        "org_id": "S", "chart_path": "/data/own.json",
    }}}
    block = coa_validation_from_settings("Corporate Services", settings, None)
    assert block["org_id"] == "S"
    assert block["chart_path"] == "/data/own.json"


def test_no_settings_entry_falls_back_to_file():
    block = coa_validation_from_settings(
        "Corporate Services", {"entities": {}}, _FILE_PROVISION
    )
    assert block["org_id"] == "FILE-ORG"


def test_settings_entry_without_org_id_falls_back_to_file():
    settings = {"entities": {"Corporate Services": {"scope_groups": ["X"]}}}
    block = coa_validation_from_settings(
        "Corporate Services", settings, _FILE_PROVISION
    )
    assert block["org_id"] == "FILE-ORG"


def test_settings_entry_without_any_chart_path_is_none():
    settings = {"entities": {"X": {"org_id": "S"}}}
    assert coa_validation_from_settings("X", settings, None) is None


# ── settings surface ────────────────────────────────────────────────


def test_settings_entities_roundtrip_and_readonly_categories(client):
    got = client.get("/api/settings").json()
    assert len(got["categories"]) == 8  # read-only, always present
    assert got["entities"] == {}

    resp = client.put("/api/settings", json={"entities": {
        "Corporate Services": {
            "org_id": "822741658",
            "default_paid_through": "1010 Chase Corporate",
            "scope_groups": ["MS | OpeEx"],
            "account_picks": ["E500 Office Supplies"],
        },
        "Cloud Services": {},
    }})
    assert resp.status_code == 200, resp.text
    got = client.get("/api/settings").json()
    assert got["entities"]["Corporate Services"]["org_id"] == "822741658"
    assert got["entities"]["Cloud Services"] == {}
    # `categories` in a PUT body is ignored, never persisted.
    resp = client.put("/api/settings", json={"categories": ["Hacked"]})
    assert resp.status_code == 200
    assert len(client.get("/api/settings").json()["categories"]) == 8


def test_settings_entities_validation(client):
    assert client.put(
        "/api/settings", json={"entities": ["not", "a", "dict"]}
    ).status_code == 400
    assert client.put(
        "/api/settings", json={"entities": {"X": "not-a-dict"}}
    ).status_code == 400
    assert client.put(
        "/api/settings", json={"entities": {"X": {"scope_groups": "not-a-list"}}}
    ).status_code == 400


# ── default_paid_through folds into new batches ─────────────────────


def test_entity_default_paid_through_reaches_export(client, monkeypatch):
    client.put("/api/settings", json={"entities": {
        "Corporate Services": {"default_paid_through": "1010 Chase Corporate"},
    }})
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[1][COL_PAID_THROUGH] == "1010 Chase Corporate"


def test_no_default_paid_through_exports_placeholder(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[1][COL_PAID_THROUGH] == "(paid-through - assign)"


# ── pickers: account_options + entity_options ───────────────────────


def test_account_picks_shortlist_drives_account_options(client, monkeypatch):
    client.put("/api/settings", json={"entities": {
        "Corporate Services": {"account_picks": ["E500 Office Supplies"]},
        "Cloud Services": {},
    }})
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["account_options"] == ["E500 Office Supplies"]
    assert grid["entity_options"] == ["Cloud Services", "Corporate Services"]


def test_chart_provisioning_drives_account_options(client, monkeypatch, tmp_path):
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps(_COA_JSON), encoding="utf-8")
    prov = tmp_path / "prov.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {"Corporate Services": {
            "org_id": "822741658", "scope_groups": ["MS | OpeEx"],
        }},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    # The scoped postable leaf, labelled exactly as the categorizer saw it.
    assert grid["account_options"] == ["E500 Office Supplies"]
    # The provisioned entity fills the picker even with an empty
    # settings['entities'] registry (the real Brisken case).
    assert "Corporate Services" in grid["entity_options"]


def test_no_chart_and_no_picks_gives_empty_account_options(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["account_options"] == []
    assert grid["entity_options"] == ["Corporate Services"]  # batch default


# ── card registry over the API (Cards R1, 2026-08-21) ──────────────────


def test_settings_put_cards_roundtrip(client):
    resp = client.put("/api/settings", json={"cards": {
        "corp-2838": {
            "label": "Corporate card (Chase)",
            "digits": ["2838", "1672"],
            "aliases": ["CorpServ"],
            "entity": "Corporate Services",
            "zoho_account": "1010 Chase Corporate",
            "currency": "usd",
        },
    }})
    assert resp.status_code == 200
    stored = resp.json()["cards"]["corp-2838"]
    assert stored["digits"] == ["2838", "1672"]
    assert stored["currency"] == "USD"
    # GET surfaces the composed view, read-only.
    got = client.get("/api/settings").json()
    keys = [c["key"] for c in got["cards_effective"]]
    assert keys == ["corp-2838"]
    assert got["cards_effective"][0]["source"] == "settings"


def test_settings_put_cards_rejects_malformed(client):
    resp = client.put("/api/settings", json={"cards": {"a": {"digits": ["x"]}}})
    assert resp.status_code == 400
    assert "digits" in resp.json()["error"]


def test_api_cards_composes_legacy_maps(client):
    """GET /api/cards lays out every card identity, legacy maps included —
    the enumeration surface the SPA never had."""
    client.put("/api/settings", json={
        "card_entities": {"2838": "Corporate Services"},
        "card_accounts": {"2838": "1010 Chase Corporate"},
    })
    resp = client.get("/api/cards")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cards"]) == 1
    card = body["cards"][0]
    assert card["key"] == "card-2838"
    assert card["source"] == "legacy"
    assert card["entity"] == "Corporate Services"
    assert card["zoho_account"] == "1010 Chase Corporate"
    assert "Corporate Services" in body["entity_options"]


def test_batch_snapshot_flattens_settings_cards(client, monkeypatch):
    """A dual-digit settings card reaches the batch snapshot as both digit
    keys, so the export can resolve either identity of the card."""
    client.put("/api/settings", json={"cards": {
        "corp-2838": {"digits": ["2838", "1672"],
                      "zoho_account": "1010 Chase Corporate"},
    }})
    _patch_ocr(monkeypatch, _extraction())
    batch_id = _create_batch(client)
    cfg_path = (client._data_root / "runs" / batch_id / "run.local.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["expense"]["card_accounts"] == {
        "2838": "1010 Chase Corporate",
        "1672": "1010 Chase Corporate",
    }


def test_merchants_inert_names_account_without_category(client):
    """Cards R2 (feedback note 11): a merchant zoho_account without a
    category is a no-op (apply_registry_category skips it), which is why
    'the importance of zoho account is not evident'. GET names the inert
    entries so the UI can say so instead of showing a silently dead field."""
    client.put("/api/settings", json={"merchants": {
        "Uber": {"aliases": [], "zoho_account": "E100 Travel"},
        "Enilive": {"aliases": [], "category": "Travel & Transport",
                    "zoho_account": "E100 Travel"},
    }})
    got = client.get("/api/settings").json()
    assert got["merchants_inert"] == ["Uber"]
