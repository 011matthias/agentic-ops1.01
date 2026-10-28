"""Switching a bucket-era month onto the Zoho accounts (owner directive
2026-09-25: July, August and September re-categorized "with the new Zoho
logic"; the reviewer's bucket picks are ignored, the engine decides).

Everything runs through `POST /api/runs/{id}/convert-to-gl` and the job it
starts, then reads the month back the way the SPA and the export do.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
BUCKET, HER_PICK = "Office Supplies & Consumables", "Meals & Entertainment"


def _code(org: str, i: int = 0) -> str:
    """A leaf the model is offered (never a parent, item 216 Build 2)."""
    return [c for c in sorted(curated_leaves.postable_codes(org))
            if not curated_leaves.has_postable_children(org, c)][i]


def _name(org: str, code: str) -> str:
    return curated_leaves.binding(code, org).name


class _LeafClient:
    """Answers every classification with the label whose code is `code`."""

    def __init__(self, code: str):
        self.code, self.calls = code, 0

    def _pick(self, categories):
        self.calls += 1
        return next(c for c in categories if c.split(None, 1)[0] == self.code)

    def classify_line_items(self, items, categories, chart_of_accounts=None, **_):
        return [ClassificationResult(self._pick(categories), None, 0.9, "fake")
                for _ in items]

    def classify_by_vendor(self, vendor, total, categories,
                           chart_of_accounts=None, **_):
        return ClassificationResult(self._pick(categories), None, 0.9, "fake")


class _ExhaustedClient(_LeafClient):
    def _pick(self, categories):
        raise RuntimeError("429 credit_balance_exhausted")


def _chart_accounts(org: str) -> list[dict]:
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b
    ]


def _provision(tmp_path: Path, monkeypatch) -> None:
    """What production holds today: both companies provisioned. Set only
    AFTER the month exists, so the month is created bucket-era."""
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": _chart_accounts(CORP_ORG)},
        CLOUD_ORG: {"org": {"name": CLOUD}, "accounts": _chart_accounts(CLOUD_ORG)},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}, CLOUD: {"org_id": CLOUD_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))


def _use(monkeypatch, client) -> None:
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (client, None))


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _bucket_month_with_her_pick(web, monkeypatch):
    """A month created before the GL engine: one receipt the tool filed under
    a bucket, which the reviewer then moved to another bucket by hand."""
    _use(monkeypatch, MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=[ClassificationResult(BUCKET, None, 0.9, "mock")],
    ))
    batch_id = web.post("/api/expense-batches",
                        data={"legal_entity": CORP, "label": "August 2026"}).json()["batch_id"]
    resp = web.post(f"/api/expense-batches/{batch_id}/receipts",
                    files=[("files", ("acme.jpg", JPG, "application/octet-stream"))])
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    body = web.get(f"/api/expense-batches/{batch_id}").json()
    assert body["category_vocabulary"] == "buckets", "precondition: bucket-era"
    (row,) = body["expenses"]
    r = web.post(f"/api/runs/{batch_id}/categories", json={
        "document_id": row["document_id"], "line_index": 0, "category": HER_PICK})
    assert r.status_code == 200, r.text
    assert _row(web, batch_id)["posting_category"]["category"] == HER_PICK
    return batch_id, row["document_id"], body["label"]


def _row(web, batch_id):
    (row,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return row


def _convert(web, batch_id, label):
    r = web.post(f"/api/runs/{batch_id}/convert-to-gl", json={"confirm": label})
    assert r.status_code == 200, r.text
    return web.get(f"/jobs/{r.json()['job_id']}").json()


def _db(web):
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def _overrides(web, batch_id) -> list:
    conn = _db(web)
    try:
        return conn.execute("SELECT * FROM category_overrides WHERE run_id = ?",
                            (batch_id,)).fetchall()
    finally:
        conn.close()


def _snapshot(web, batch_id) -> dict:
    conn = _db(web)
    try:
        return json.loads(conn.execute("SELECT snapshot FROM runs WHERE run_id = ?",
                                       (batch_id,)).fetchone()["snapshot"])
    finally:
        conn.close()


def test_a_bucket_month_is_switched_and_her_pick_is_set_aside(web, monkeypatch):
    batch_id, doc, label = _bucket_month_with_her_pick(web, monkeypatch)
    _provision(web._data_root, monkeypatch)
    code = _code(CORP_ORG, 3)
    _use(monkeypatch, _LeafClient(code))

    job = _convert(web, batch_id, label)

    assert job["status"] == "done", job
    result = job["result"]
    assert result["n_overrides_retired"] == 1 and result["n_lines_categorized"] == 1
    body = web.get(f"/api/expense-batches/{batch_id}").json()
    assert body["category_vocabulary"] == "gl"
    assert body["gl_accounts"][CORP], "the picker now offers the company's accounts"
    row = body["expenses"][0]
    # Item 216 Build 2 step 2: the engine's answer is the model's, so it is
    # the row's suggestion until she confirms it; her old pick is gone.
    assert row["posting_category"] is None, "her pick is gone"
    assert row["suggested_category"]["category"] == code, "the engine suggests"
    assert row["suggested_category"]["zoho_account"] == _name(CORP_ORG, code)
    assert row["suggested_category"]["source"] != "override"
    assert _overrides(web, batch_id) == []
    archive = _snapshot(web, batch_id)["gl_conversion"]
    (kept,) = archive["category_overrides"]
    assert (kept["document_id"], kept["category"]) == (doc, HER_PICK)
    assert archive["receipt_categorizations"]["receipts"][doc][0]["category"] == BUCKET

    csv_rows = list(csv.reader(io.StringIO(web.get(f"/runs/{batch_id}/expenses.csv").text)))
    assert [r[COL_ACCOUNT] for r in csv_rows[1:]] == [f"suggested: {_name(CORP_ORG, code)}"]


def test_a_row_whose_company_comes_from_its_card_is_categorized_for_it(
    web, monkeypatch,
):
    """Most live rows: no company stamped on the receipt, the one the screen
    shows comes from the card chain. The switch categorizes for THAT company
    rather than refusing the row as having none."""
    web.put("/api/settings", json={"cards": {"corp-1672": {
        "label": "Corporate card", "digits": ["1672"], "entity": CORP,
        "person": "Nicolas", "zoho_account": "Chase 1672"}}})
    _use(monkeypatch, MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=[ClassificationResult(BUCKET, None, 0.9, "mock")],
    ))
    batch_id = web.post("/api/expense-batches",
                        data={"legal_entity": "", "label": "July 2026"}).json()["batch_id"]
    resp = web.post(f"/api/expense-batches/{batch_id}/receipts",
                    files=[("files", ("acme.jpg", JPG, "application/octet-stream"))])
    assert web.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    doc = _row(web, batch_id)["document_id"]
    web.put(f"/api/runs/{batch_id}/expenses/{doc}",
            json={"field": "card_key", "value": "corp-1672"})
    assert _row(web, batch_id)["legal_entity_id"] == CORP
    _provision(web._data_root, monkeypatch)
    code = _code(CORP_ORG, 5)
    _use(monkeypatch, _LeafClient(code))

    assert _convert(web, batch_id, "July 2026")["status"] == "done"

    row = _row(web, batch_id)
    # Item 216 Build 2 step 2: the model's answer is the row's suggestion.
    assert row["suggested_category"]["category"] == code
    assert row["suggested_category"]["zoho_account"] == _name(CORP_ORG, code)


def test_the_switch_asks_for_the_label_and_runs_once(web, monkeypatch):
    batch_id, _doc, label = _bucket_month_with_her_pick(web, monkeypatch)
    _provision(web._data_root, monkeypatch)
    _use(monkeypatch, _LeafClient(_code(CORP_ORG)))
    url = f"/api/runs/{batch_id}/convert-to-gl"
    assert web.post(url, json={}).json()["code"] == "convert_confirm_required"
    assert web.post(url, json={"confirm": "July 2026"}).json()["code"] == "convert_confirm_mismatch"
    assert web.post("/api/runs/nope/convert-to-gl", json={"confirm": label}).status_code == 404
    assert len(_overrides(web, batch_id)) == 1, "a refused call changes nothing"

    assert _convert(web, batch_id, label)["status"] == "done"
    again = web.post(url, json={"confirm": label})
    assert again.status_code == 409 and again.json()["code"] == "month_already_gl"


@pytest.mark.parametrize("client, code", [
    (None, "llm_unavailable"),
    (_ExhaustedClient("x"), None),
])
def test_no_model_leaves_the_month_exactly_as_it_was(web, monkeypatch, client, code):
    batch_id, _doc, label = _bucket_month_with_her_pick(web, monkeypatch)
    _provision(web._data_root, monkeypatch)
    before = _snapshot(web, batch_id)
    _use(monkeypatch, client)

    job = _convert(web, batch_id, label)

    assert job["status"] == "error", job
    if code:
        assert job["error"].startswith(code), job
    assert web.get(f"/api/expense-batches/{batch_id}").json()["category_vocabulary"] == "buckets"
    assert _snapshot(web, batch_id) == before
    assert len(_overrides(web, batch_id)) == 1


def test_without_a_provisioned_company_nothing_is_switched(web, monkeypatch):
    batch_id, _doc, label = _bucket_month_with_her_pick(web, monkeypatch)
    _use(monkeypatch, _LeafClient(_code(CORP_ORG)))
    job = _convert(web, batch_id, label)
    assert job["status"] == "error" and job["error"].startswith("gl_not_provisioned"), job
    assert len(_overrides(web, batch_id)) == 1


def test_a_receiptless_charge_is_switched_for_its_own_company(tmp_path, monkeypatch):
    from expense_recon.matching.types import (
        Categorization,
        ClassificationSource,
        MatchOutcome,
        Transaction,
    )
    from expense_recon.web.serialize import categorization_to_dict, snapshot_to_dict
    from expense_recon.web.store import RunStore

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    tx = Transaction(
        transaction_id="tx1", legal_entity_id=CLOUD, account_id="card-9693",
        transaction_date=date(2026, 8, 3), posting_date=None,
        amount=Decimal("-12.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="SOME SAAS")
    snapshot = snapshot_to_dict([tx], [], MatchOutcome(
        matches=[], unmatched_transactions=["tx1"], unmatched_receipts=[],
        ambiguous=[]), [])
    snapshot["charge_categorizations"] = {"tx1": categorization_to_dict(Categorization(
        category="Software & Subscriptions", zoho_account=None, confidence=0.9,
        source=ClassificationSource.VENDOR, reasoning="bucket era"))}
    store = RunStore(tmp_path / "recon-web.sqlite")
    store.create_run(
        run_id="aug", created_at="2026-09-07T00:00:00", label="August 2026",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir=str(tmp_path), llm_enabled=True, has_coa=False)
    store.close()
    _provision(tmp_path, monkeypatch)
    code = _code(CLOUD_ORG, 2)
    _use(monkeypatch, _LeafClient(code))
    with TestClient(create_app(tmp_path)) as client:
        r = client.put("/api/runs/aug/charges/tx1/category",
                       json={"category": "Travel & Transport"})
        assert r.status_code == 200, r.text
        r = client.post("/api/runs/aug/convert-to-gl", json={"confirm": "August 2026"})
        job = client.get(f"/jobs/{r.json()['job_id']}").json()
        assert job["status"] == "done", job
        assert job["result"]["n_charges_categorized"] == 1
        (row,) = [x for x in client.get("/api/runs/aug").json()["rows"]
                  if x["transaction_id"] == "tx1"]
        # Item 216 Build 2 step 2: the model's guess is the row's suggestion.
        assert row["posting_category"] is None, row["posting_category"]
        assert row["suggested_category"]["category"] == code
        assert row["suggested_category"]["zoho_account"] == _name(CLOUD_ORG, code)
