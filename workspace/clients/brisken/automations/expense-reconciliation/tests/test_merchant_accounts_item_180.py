"""Items 180/181: a merchant's GL account per company.

Pinned at the callers: the settings route that stores the map, a GL batch's
categorization that reads it, the receiptless-charge path, and the settings
read that names each code per company and lists the gaps. A client that
fails on any classify call proves the registry decided without the model.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.categorize_charges import categorize_charges  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.matching.types import MatchOutcome, Transaction  # noqa: E402
from expense_recon.merchant_registry import MerchantRegistry  # noqa: E402
from expense_recon.web import merchant_accounts  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
CLOUD_LONG = "Brisken Cloud Services, LLC"
ENTITY_ORGS = {CORP: CORP_ORG, CLOUD: CLOUD_ORG}
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _postable_here_not_there(here: str, there: str) -> str:
    codes = [c for c in sorted(curated_leaves.postable_codes(here))
             if not curated_leaves.is_postable(there, c)]
    assert codes, "fixture: every code is postable in both orgs"
    return codes[0]


CORP_CODE = _postable_here_not_there(CORP_ORG, CLOUD_ORG)
CLOUD_CODE = _postable_here_not_there(CLOUD_ORG, CORP_ORG)


class _NoModel(MockLLMClient):
    """Extracts as told; any categorization call is a test failure."""

    calls = 0

    def classify_line_items(self, *a, **k):
        type(self).calls += 1
        raise AssertionError("the model was asked")

    def classify_by_vendor(self, *a, **k):
        type(self).calls += 1
        raise AssertionError("the model was asked")


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": []},
        CLOUD_ORG: {"org": {"name": CLOUD}, "accounts": []},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    merchant_accounts._BOOKINGS_CACHE.clear()
    _NoModel.calls = 0
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        # The live shape: the settings registry spells Cloud Services long.
        r = c.put("/api/settings", json={"entities": {
            CLOUD_LONG: {"org_id": CLOUD_ORG}}})
        assert r.status_code == 200, r.text
        yield c


def _put_merchants(web, merchants: dict) -> dict:
    r = web.put("/api/settings", json={"merchants": merchants})
    assert r.status_code == 200, r.text
    return r.json()


def _batch(web, monkeypatch, entity, vendor, client_cls=_NoModel, responses=()):
    mock = client_cls(
        extraction_responses=[ExtractedReceipt(
            date="2026-10-02", total="40.00", currency="USD", vendor=vendor,
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=list(responses),
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    r = web.post("/api/expense-batches", data={"legal_entity": entity})
    assert r.status_code == 200, r.text
    batch_id = r.json()["batch_id"]
    r = web.post(f"/api/expense-batches/{batch_id}/receipts",
                 files=[("files", ("r.jpg", JPG, "application/octet-stream"))])
    assert r.status_code == 200, r.text
    assert web.get(f"/jobs/{r.json()['job_id']}").json()["status"] == "done"
    (row,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return batch_id, row


def _stored_cat(web, batch_id, doc) -> dict:
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    try:
        snap = json.loads(conn.execute(
            "SELECT snapshot FROM runs WHERE run_id = ?", (batch_id,)
        ).fetchone()[0])
    finally:
        conn.close()
    (rec,) = [r for r in snap["receipts"] if r["document_id"] == doc]
    return rec["line_items"][0]["categorization"]


ANTHROPIC = {
    "aliases": [], "category": "Software & Subscriptions", "zoho_account": None,
    # One entry keyed by the settings registry's long spelling of Cloud
    # Services: the save stores it under the spelling receipts carry.
    "accounts": {CORP: CORP_CODE, CLOUD_LONG: CLOUD_CODE},
}
STORED = {CLOUD: CLOUD_CODE, CORP: CORP_CODE}


def test_each_company_books_to_its_own_code_without_the_model(web, monkeypatch):
    body = _put_merchants(web, {"Anthropic": ANTHROPIC})
    assert body["merchants"]["Anthropic"]["accounts"] == STORED
    for entity, org, code in ((CORP, CORP_ORG, CORP_CODE),
                              (CLOUD, CLOUD_ORG, CLOUD_CODE)):
        batch_id, row = _batch(web, monkeypatch, entity, "Anthropic")
        cat = _stored_cat(web, batch_id, row["document_id"])
        assert cat["category"] == code, (entity, cat)
        assert cat["zoho_account"] == curated_leaves.binding(code, org).name
        assert cat["source"] == "REGISTRY"
        assert "refusal" not in cat
    assert _NoModel.calls == 0


def test_a_merchant_with_no_default_category_books_by_its_map(web, monkeypatch):
    _put_merchants(web, {"Wispr": {"aliases": [], "category": None,
                                   "accounts": {CORP: CORP_CODE}}})
    batch_id, row = _batch(web, monkeypatch, CORP, "Wispr")
    assert _stored_cat(web, batch_id, row["document_id"])["category"] == CORP_CODE
    assert _NoModel.calls == 0


def test_a_code_the_company_cannot_post_to_refuses_by_name(web, monkeypatch):
    entry = {**ANTHROPIC, "accounts": {CORP: CLOUD_CODE}}
    _put_merchants(web, {"Anthropic": entry})
    batch_id, row = _batch(web, monkeypatch, CORP, "Anthropic")
    cat = _stored_cat(web, batch_id, row["document_id"])
    assert cat["category"] is None
    assert cat["refusal"] == curated_leaves.refusal_reason(CORP_ORG, CLOUD_CODE)
    assert cat["refusal"] != ""
    assert _NoModel.calls == 0, "a person's account is never overruled"


def test_a_wholesale_save_that_omits_the_map_keeps_it(web):
    _put_merchants(web, {"Anthropic": ANTHROPIC})
    # What an editor that rebuilds merchants from the fields it knows sends.
    known_only = {k: v for k, v in ANTHROPIC.items() if k != "accounts"}
    body = _put_merchants(web, {"Anthropic": known_only, "Brave": {"aliases": []}})
    assert body["merchants"]["Anthropic"]["accounts"] == STORED
    got = web.get("/api/settings").json()["merchants"]["Anthropic"]
    assert got["accounts"] == STORED
    for clear in ({}, None):
        _put_merchants(web, {"Anthropic": ANTHROPIC})
        body = _put_merchants(web, {"Anthropic": {**known_only, "accounts": clear}})
        assert "accounts" not in body["merchants"]["Anthropic"], clear


def test_a_name_or_bucket_is_dropped_and_named_not_stored(web):
    label = next(lbl for lbl in curated_leaves.llm_leaf_labels(CORP_ORG)
                 if lbl.startswith(CORP_CODE + " "))
    body = _put_merchants(web, {"Anthropic": {**ANTHROPIC, "accounts": {
        CORP: label, CLOUD: "Software & Subscriptions"}}})
    assert body["merchants"]["Anthropic"]["accounts"] == {CORP: CORP_CODE}
    assert "merchants.Anthropic.accounts.Cloud Services" in body["ignored"]


def test_a_bucket_month_ignores_the_map(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    _NoModel.calls = 0
    with TestClient(create_app(tmp_path)) as client:
        client._data_root = tmp_path
        _put_merchants(client, {"Anthropic": ANTHROPIC})
        batch_id, row = _batch(client, monkeypatch, CORP, "Anthropic")
        assert client.get(f"/api/expense-batches/{batch_id}").json()[
            "category_vocabulary"] == "buckets"
        cat = _stored_cat(client, batch_id, row["document_id"])
    assert cat["category"] == "Software & Subscriptions"
    assert cat["zoho_account"] in (None, "")
    assert _NoModel.calls == 0


def test_a_receiptless_charge_takes_its_companys_account():
    reg = MerchantRegistry({"Anthropic": {**ANTHROPIC, "accounts": STORED}})

    def tx(tx_id, entity):
        return Transaction(
            transaction_id=tx_id, legal_entity_id=entity, account_id="card",
            transaction_date=date(2026, 10, 3), posting_date=None,
            amount=Decimal("20"), transaction_currency="USD",
            account_card_currency="USD", vendor_from_statement="ANTHROPIC",
        )

    txs = [tx("t1", CORP), tx("t2", CLOUD)]
    out = categorize_charges(
        MatchOutcome(unmatched_transactions=["t1", "t2"]), txs,
        client=_NoModel(), registry=reg, entity_orgs=ENTITY_ORGS,
    )
    assert out["t1"].category == CORP_CODE
    assert out["t2"].category == CLOUD_CODE


def test_the_refused_rerun_needs_a_typed_confirm_and_books_the_new_account(
    web, monkeypatch,
):
    """A GL month refused a merchant before it had an account; the operator
    route re-runs the engine on that refused row only, after a typed
    confirm, and the registry answers it without the model."""
    lovable = {"aliases": [], "category": "Software & Subscriptions",
               "zoho_account": None}
    _put_merchants(web, {"Lovable": lovable})
    batch_id, row = _batch(
        web, monkeypatch, CORP, "Lovable", client_cls=MockLLMClient,
        responses=[ClassificationResult("unsure", None, 0.2, "mock")])
    doc = row["document_id"]
    assert _stored_cat(web, batch_id, doc)["refusal"]
    label = web.get(f"/api/expense-batches/{batch_id}").json()["label"]

    _put_merchants(web, {"Lovable": {**lovable, "accounts": {CORP: CORP_CODE}}})
    monkeypatch.setattr("expense_recon.cli._build_llm_client",
                        lambda cfg: (_NoModel(), None))
    url = f"/api/runs/{batch_id}/recategorize-refused"
    assert web.post(url, json={}).json()["code"] == "rerun_confirm_required"
    assert web.post(url, json={"confirm": "nope"}).json()["code"] == \
        "rerun_confirm_mismatch"
    assert _stored_cat(web, batch_id, doc)["refusal"], "nothing ran unconfirmed"

    r = web.post(url, json={"confirm": label})
    assert r.status_code == 200, r.text
    job = web.get(f"/jobs/{r.json()['job_id']}").json()
    assert job["status"] == "done", job
    result = json.loads(job["result"]) if isinstance(job["result"], str) else job["result"]
    assert result["n_lines_resolved"] == 1, result
    cat = _stored_cat(web, batch_id, doc)
    assert cat["category"] == CORP_CODE and "refusal" not in cat
    assert _NoModel.calls == 0


def test_the_refused_rerun_refuses_a_bucket_month(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    with TestClient(create_app(tmp_path)) as client:
        client._data_root = tmp_path
        batch_id, _ = _batch(client, monkeypatch, CORP, "Anthropic",
                             client_cls=MockLLMClient)
        r = client.post(f"/api/runs/{batch_id}/recategorize-refused",
                        json={"confirm": batch_id})
    assert r.status_code == 409 and r.json()["code"] == "month_not_gl"


def test_settings_names_each_code_per_company_and_lists_the_gaps(web, monkeypatch):
    lovable = {"aliases": [], "category": "Software & Subscriptions",
               "zoho_account": None, "accounts": {CLOUD: CLOUD_CODE}}
    _put_merchants(web, {"Anthropic": ANTHROPIC, "Lovable": lovable})
    label = next(lbl for lbl in curated_leaves.llm_leaf_labels(CORP_ORG)
                 if lbl.startswith(CORP_CODE + " "))
    # Lovable has no Corporate Services account, so the model answers here.
    _batch(web, monkeypatch, CORP, "Lovable", client_cls=MockLLMClient,
           responses=[ClassificationResult(label, None, 0.9, "mock")])

    body = web.get("/api/settings").json()
    companies = {c["org_id"]: c for c in body["account_companies"]}
    assert set(companies) == {CORP_ORG, CLOUD_ORG}
    assert companies[CLOUD_ORG]["label"] == CLOUD
    assert companies[CLOUD_ORG]["labels"] == [CLOUD_LONG, CLOUD]

    rows = {r["org_id"]: r for r in body["merchant_accounts"]["Anthropic"]}
    assert rows[CLOUD_ORG]["company"] == CLOUD
    assert rows[CLOUD_ORG]["name"] == curated_leaves.binding(CLOUD_CODE, CLOUD_ORG).name
    assert rows[CORP_ORG]["postable"] is True

    gaps = [(g["merchant"], g["company"]) for g in body["needs_account"]]
    assert gaps == [("Lovable", CORP)], body["needs_account"]

    # Filling the gap clears it on the very next read, cache or not.
    _put_merchants(web, {"Anthropic": ANTHROPIC,
                         "Lovable": {**lovable, "accounts": {
                             CLOUD: CLOUD_CODE, CORP: CORP_CODE}}})
    assert web.get("/api/settings").json()["needs_account"] == []
