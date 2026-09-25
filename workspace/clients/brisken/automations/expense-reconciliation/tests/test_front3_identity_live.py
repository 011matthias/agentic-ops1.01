"""Front 3 step 1 (2026-09-25): a merchant's identity and its per-company
account are read from the merchant list as it is NOW, not from the stamp the
row got when it arrived.

Measured before the change on the live months: 64 receipts and 52 charges
resolve to a listed merchant today but read the raw spelling or the model's
guess, because `categorize_receipts_with_registry` stamps `canonical_vendor`
and the registry account at ingest and nothing re-reads it; the owner's
OpenAI and Anthropic accounts (item 219) answer 33 rows and agree with
Criss on all 33, yet none of them showed.

Pinned through the callers: the Expenses grid, the run payload's charge
rows, and `expenses.csv`, each after a settings write adds the merchant to a
month that already holds its receipt. A person's pick still wins, and
nothing stored changes.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

import pytest

from expense_recon.zoho import curated_leaves

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

CORP = "Corporate Services"
CORP_ORG = "822741658"
CODE = "criss-code-front3"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _leaves(org: str) -> list[str]:
    return sorted(
        c for c in curated_leaves.postable_codes(org)
        if not curated_leaves.has_postable_children(org, c)
    )


MODEL_LEAF = _leaves(CORP_ORG)[0]
LISTED_LEAF = _leaves(CORP_ORG)[1]


def _name(code: str) -> str:
    return curated_leaves.binding(code, CORP_ORG).name


def _label(code: str) -> str:
    return f"{code} {_name(code)}"


def _chart_accounts(org: str) -> list[dict]:
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b
    ]


@pytest.fixture
def web(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_OPERATOR_CODE", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODES", f"{CODE}:criss")
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        CORP_ORG: {"org": {"name": CORP}, "accounts": _chart_accounts(CORP_ORG)},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {CORP: {"org_id": CORP_ORG}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))
    with TestClient(create_app(tmp_path)) as c:
        login = c.post("/api/login", json={"code": CODE})
        assert login.status_code == 200, login.text
        c.headers.update({"Authorization": f"Bearer {login.json()['token']}"})
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _list_merchant(web, alias: str) -> None:
    r = web.put("/api/settings", json={"merchants": {"TEST- Acme Analytics": {
        "aliases": [alias], "category": None, "accounts": {CORP: LISTED_LEAF}}}})
    assert r.status_code == 200, r.text


def _csv_accounts(client, batch: str) -> list[str]:
    text = client.get(f"/runs/{batch}/expenses.csv").text
    return [r["Expense Account"] for r in csv.DictReader(io.StringIO(text))
            if r.get("Expense Date")]


def _receipt_month(web, monkeypatch) -> str:
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", confidence=0.9, notes="",
            line_items=(ExtractedLineItem("Analytics seat, August", "40.00"),))],
        responses=[ClassificationResult(_label(MODEL_LEAF), None, 0.9, "mock")],
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    _done(web, web.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("acme.jpg", JPG, "application/octet-stream"))]))
    return batch


def test_a_merchant_listed_after_the_receipt_arrived_names_it_and_decides_its_account(
    web, monkeypatch,
):
    batch = _receipt_month(web, monkeypatch)
    (before,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert before["vendor"] == {"display": "Acme", "raw": "Acme", "source": "extraction"}
    assert "merchant" not in before
    assert before["posting_category"] is None
    assert before["suggested_category"]["category"] == MODEL_LEAF, "precondition"
    assert _csv_accounts(web, batch) == [f"suggested: {_name(MODEL_LEAF)}"]

    _list_merchant(web, "Acme")

    (after,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    # The name, read now; what ingest stored stays beside it.
    assert after["vendor"] == {
        "display": "TEST- Acme Analytics", "raw": "Acme", "source": "registry",
        "stamped": {"display": "Acme", "source": "extraction"},
    }, after["vendor"]
    assert after["merchant"] == {"name": "TEST- Acme Analytics", "match": "exact"}
    # The account the list names for this company is the posting, a rule's;
    # the model's answer is no longer shown as anything but what it was.
    posting = after["posting_category"]
    assert (posting["category"], posting["origin"], posting["source"]) == (
        LISTED_LEAF, "rule", "registry"), posting
    assert posting["zoho_account"] == _name(LISTED_LEAF)
    assert (posting["stamped"]["category"], posting["stamped"]["origin"]) == (
        MODEL_LEAF, "suggestion"), posting["stamped"]
    assert "suggested_category" not in after
    assert after["category_confirmable"] is False
    (line,) = after["line_items"]
    assert line["provenance"] == f"merchant registry account for {CORP}"
    assert after["books_as"][0]["account"] == _name(LISTED_LEAF)
    assert "suggested" not in after["books_as"][0]
    # The file the poster reads says the same as the screen.
    assert _csv_accounts(web, batch) == [_name(LISTED_LEAF)]


def test_a_persons_pick_still_wins_over_the_listed_account(web, monkeypatch):
    batch = _receipt_month(web, monkeypatch)
    _list_merchant(web, "Acme")
    (row,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    r = web.put(f"/api/runs/{batch}/expenses/{row['document_id']}",
                json={"field": "category", "value": MODEL_LEAF})
    assert r.status_code == 200, r.text
    (after,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert (after["posting_category"]["category"], after["posting_category"]["origin"]) == (
        MODEL_LEAF, "person"), after["posting_category"]
    assert _csv_accounts(web, batch) == [_name(MODEL_LEAF)]


def _statement_month(web, monkeypatch, descriptor: str) -> str:
    mock = MockLLMClient(
        responses=[ClassificationResult(_label(MODEL_LEAF), None, 0.9, "mock")] * 8)
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP, "label": "August 2026"})
    _done(web, resp)
    batch = resp.json()["batch_id"]
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    ws.append([datetime(2026, 8, 12), descriptor, "Sale", -41.00])
    ws.append([datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 41.00])
    buf = io.BytesIO()
    wb.save(buf)
    _done(web, web.post(
        f"/api/expense-batches/{batch}/statement",
        files={"statement": (
            "August2026.xlsx", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"account_id": "card-2838",
              "account_legal_entities": json.dumps({"card-2838": CORP}),
              "account_card_currency": "USD"},
    ))
    return batch


def _charge_row(web, batch: str, descriptor: str) -> dict:
    view = web.get(f"/api/runs/{batch}").json()
    assert view["category_vocabulary"] == "gl", "precondition: a GL month"
    return next(r for r in view["rows"] if r["vendor"] == descriptor)


def test_a_receiptless_charge_takes_the_listed_account_on_the_run_payload(
    web, monkeypatch,
):
    batch = _statement_month(web, monkeypatch, "ACME ANALYTICS")

    def row():
        return _charge_row(web, batch, "ACME ANALYTICS")

    before = row()
    assert before["suggested_category"]["category"] == MODEL_LEAF, "precondition"
    assert before["posting_category"] is None
    assert "merchant" not in before

    _list_merchant(web, "ACME ANALYTICS")

    after = row()
    assert after["vendor"] == "ACME ANALYTICS", "the bank's text stays the bank's"
    assert after["merchant"] == {"name": "TEST- Acme Analytics", "match": "exact"}
    posting = after["posting_category"]
    assert (posting["category"], posting["origin"]) == (LISTED_LEAF, "rule"), posting
    assert posting["provenance"] == f"merchant registry account for {CORP}"
    assert (posting["stamped"]["category"], posting["stamped"]["origin"]) == (
        MODEL_LEAF, "suggestion"), posting
    assert "suggested_category" not in after
    assert after["charge_category"]["origin"] == "rule"


def test_a_bank_line_the_close_spelling_tier_misses_names_its_merchant_and_account(
    web, monkeypatch,
):
    """Step 2 through the caller: the descriptor tier puts a Chase-cut line
    on its listed merchant, so the per-company account reaches the charge."""
    batch = _statement_month(web, monkeypatch, "GOOGLE *Workspace_bris")
    assert "merchant" not in _charge_row(web, batch, "GOOGLE *Workspace_bris")
    r = web.put("/api/settings", json={"merchants": {"Google Workspace": {
        "aliases": [], "category": None, "accounts": {CORP: LISTED_LEAF}}}})
    assert r.status_code == 200, r.text
    after = _charge_row(web, batch, "GOOGLE *Workspace_bris")
    assert after["merchant"] == {"name": "Google Workspace", "match": "descriptor"}
    assert (after["posting_category"]["category"], after["posting_category"]["origin"]) == (
        LISTED_LEAF, "rule"), after["posting_category"]

# ── Steps 4 and 5: the model's answer re-read against today's refusals ──

ZOHO_ERP = "E500010-10"
PARENT = "E500010"


def _one_receipt(web, monkeypatch, vendor: str, answer: str) -> tuple[str, dict]:
    mock = MockLLMClient(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor=vendor,
            reference="", confidence=0.9, notes="",
            line_items=(ExtractedLineItem("Workspace seat, August", "40.00"),))],
        responses=[ClassificationResult(_label(answer), None, 0.9, "mock")],
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP})
    batch = resp.json()["batch_id"]
    _done(web, web.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("r.jpg", JPG, "application/octet-stream"))]))
    (row,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    return batch, row


def test_the_model_may_not_land_on_zoho_erp_for_a_vendor_that_is_not_zoho(
    web, monkeypatch,
):
    # The read-time re-read off, so the grid shows what ingest STORED.
    monkeypatch.setattr("expense_recon.categorize._stale_suggestion", lambda *a: None)
    _batch, row = _one_receipt(web, monkeypatch, "Acme Cloud", ZOHO_ERP)
    assert "suggested_category" not in row, row.get("suggested_category")
    assert row["posting_category"] is None
    assert row["review"]["refusal"] == "account_vendor_specific", row["review"]
    _batch, zoho = _one_receipt(web, monkeypatch, "Zoho Corporation", ZOHO_ERP)
    assert zoho["suggested_category"]["category"] == ZOHO_ERP, "Zoho's own account stands"


@pytest.mark.parametrize("answer, vendor, refusal", [
    (ZOHO_ERP, "Acme Cloud", "account_vendor_specific"),
    (PARENT, "Acme Cloud", "model_picked_parent"),
])
def test_a_suggestion_stored_before_the_rule_reads_as_its_refusal(
    web, monkeypatch, answer, vendor, refusal,
):
    """Stored before the guards existed (both switched off for the ingest
    only), read after: the grid and the file refuse it, nothing stored moved."""
    with monkeypatch.context() as m:
        m.setattr("expense_recon.categorize.vendor_may_post", lambda *a: True)
        m.setattr("expense_recon.categorize.curated_leaves.has_postable_children",
                  lambda *a: False)
        batch_id, _stored = _one_receipt(web, monkeypatch, vendor, answer)
    (row,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    assert "suggested_category" not in row, row.get("suggested_category")
    assert row["review"]["refusal"] == refusal, row["review"]
    assert row["line_items"][0]["category"] is None
    assert _csv_accounts(web, batch_id) != [f"suggested: {_name(answer)}"]