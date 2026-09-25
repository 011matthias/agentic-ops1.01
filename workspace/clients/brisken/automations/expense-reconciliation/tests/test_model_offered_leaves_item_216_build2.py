"""Item 216 Build 2, step 1: the model is offered leaves only.

Measured on the 2026-09-25 03:05 backup: the model was handed every postable
account, 11 to 13 of them per company roll-ups with postable accounts under
them (Dirk's chart makes a parent postable outside COGS by design), and it
took one 58 times in 164 where Criss took one once in 152. Owner ruling
2026-09-25: a model pick may not land on a parent with postable children; a
person or a rule may.

The structure: `curated_leaves.llm_leaf_labels` offers no such parent, and
`categorize._gl_model_result` refuses one the model names anyway
(`model_picked_parent`). Pinned through the callers: a receipt upload and a
GL month's statement charges, where the merchant list and Criss still pick a
parent and keep it.
"""
from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from expense_recon.zoho import curated_leaves
from expense_recon.zoho.posting_resolution import MODEL_PICKED_PARENT

CORP = "Corporate Services"
CORP_ORG = "822741658"
CLOUD_ORG = "697686691"
CONSULTING_ORG = "808232536"
PARENT = "E500010"  # IT: Computer and Internet Expenses, the model's favourite
CODE = "criss-code-216b2"

# Read off the chart's parent names (compiled 2026-09-24). The prefix test the
# sizing first used got four of these wrong in each company: it called
# `E600010-10-20 Conferences: Registration (Consulting)` a parent (its
# `-10-20-*` "children" are CRM travel) and missed `E600010-20 Business Travel
# Expenses - CRM`, plus Corporate Services' two roots.
PARENTS_PIN = {
    CLOUD_ORG: {
        "E100010", "E500010", "E500030", "E600010", "E600010-05",
        "E600010-10", "E600010-10-50", "E600010-20", "E600010-30",
        "E600060", "E600060-05",
    },
    CONSULTING_ORG: {
        "E100010", "E500010", "E500030", "E600010", "E600010-05",
        "E600010-10", "E600010-10-50", "E600010-20", "E600010-30",
        "E600060", "E600060-05",
    },
    CORP_ORG: {
        "E100000", "E100010", "E100020", "E500000", "E500010", "E500030",
        "E600010", "E600010-05", "E600010-10", "E600010-10-50",
        "E600010-20", "E600010-30", "E600060",
    },
}


def _parents(org: str) -> set[str]:
    return {c for c in curated_leaves.postable_codes(org)
            if curated_leaves.has_postable_children(org, c)}


def test_the_parents_are_read_from_the_chart_branches_not_the_code_prefix():
    for org, want in PARENTS_PIN.items():
        assert _parents(org) == want, (org, _parents(org) ^ want)
    # The two prefix traps, named.
    assert not curated_leaves.has_postable_children(CLOUD_ORG, "E600010-10-20")
    assert curated_leaves.has_postable_children(CLOUD_ORG, "E600010-20")
    # Per company: Management Services has postable children in Cloud
    # Services and none in Corporate Services, where it is a leaf.
    assert curated_leaves.has_postable_children(CLOUD_ORG, "E600060-05")
    assert not curated_leaves.has_postable_children(CORP_ORG, "E600060-05")
    # An uncovered org and an unknown code are never parents.
    assert not curated_leaves.has_postable_children("999", PARENT)
    assert not curated_leaves.has_postable_children(CORP_ORG, "E999999")


def test_the_model_is_offered_every_postable_account_except_a_parent():
    for org in PARENTS_PIN:
        offered = {lbl.split(None, 1)[0] for lbl in curated_leaves.llm_leaf_labels(org)}
        assert offered == curated_leaves.postable_codes(org) - PARENTS_PIN[org], org
    assert len(curated_leaves.llm_leaf_labels(CORP_ORG)) == 68 - 13
    assert len(curated_leaves.llm_leaf_labels(CLOUD_ORG)) == 64 - 11
    assert len(curated_leaves.llm_leaf_labels(CONSULTING_ORG)) == 62 - 11


# ── through the callers ────────────────────────────────────────────────

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
GUESSED = (datetime(2026, 8, 12), "ACME ANALYTICS", "Sale", -41.00)
RULED = (datetime(2026, 8, 14), "FIGMA", "Sale", -45.00)
PICKED = (datetime(2026, 8, 18), "PRESSMASTER FZCO", "Sale", -220.00)
PAYMENT = (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 306.00)


class _Recording(MockLLMClient):
    """The mock, recording the choice list every classify call was handed.
    Its canned reply names a parent whatever it was offered: a model that
    names one anyway, which the backstop exists for."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.offered: list[list[str]] = []

    def classify_line_items(self, items, categories, *a, **kw):
        self.offered.append(list(categories))
        return super().classify_line_items(items, categories, *a, **kw)

    def classify_by_vendor(self, vendor, total, categories, *a, **kw):
        self.offered.append(list(categories))
        return super().classify_by_vendor(vendor, total, categories, *a, **kw)


def _parent_label() -> str:
    return "%s %s" % (PARENT, curated_leaves.binding(PARENT, CORP_ORG).name)


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
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _assert_offered_no_parent(mock: _Recording):
    assert mock.offered, "precondition: the model was asked"
    for labels in mock.offered:
        codes = {lbl.split(None, 1)[0] for lbl in labels}
        assert codes == curated_leaves.postable_codes(CORP_ORG) - PARENTS_PIN[CORP_ORG]


def test_a_receipt_line_the_model_answers_with_a_parent_refuses(web, monkeypatch):
    mock = _Recording(
        extraction_responses=[ExtractedReceipt(
            date="2026-08-01", total="40.00", currency="USD", vendor="Acme",
            reference="", line_items=(), confidence=0.9, notes="")],
        responses=[ClassificationResult(_parent_label(), None, 0.9, "mock")],
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP})
    assert resp.status_code == 200, resp.text
    batch = resp.json()["batch_id"]
    _done(web, web.post(
        f"/api/expense-batches/{batch}/receipts",
        files=[("files", ("acme.jpg", JPG, "application/octet-stream"))]))

    _assert_offered_no_parent(mock)
    (expense,) = web.get(f"/api/expense-batches/{batch}").json()["expenses"]
    assert expense["review"]["reason_code"] == "category_refused", expense["review"]
    assert expense["review"]["refusal"] == MODEL_PICKED_PARENT
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    try:
        snap = json.loads(conn.execute(
            "SELECT snapshot FROM runs WHERE run_id = ?", (batch,)).fetchone()[0])
    finally:
        conn.close()
    (cat,) = [li["categorization"] for r in snap["receipts"] for li in r["line_items"]]
    assert cat["category"] is None and cat["zoho_account"] is None, cat
    assert cat["refusal"] == MODEL_PICKED_PARENT
    assert PARENT in cat["reasoning"], "the refusal names what the model said"


def test_a_charge_guess_on_a_parent_refuses_while_a_rule_and_a_person_keep_theirs(
    web, monkeypatch,
):
    mock = _Recording(
        responses=[ClassificationResult(_parent_label(), None, 0.9, "mock")] * 8)
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    # The merchant list maps FIGMA to the parent for this company: a rule may.
    r = web.put("/api/settings", json={"merchants": {"Figma": {
        "aliases": ["FIGMA"], "category": PARENT, "accounts": {CORP: PARENT}}}})
    assert r.status_code == 200, r.text
    resp = web.post("/api/expense-batches", data={"legal_entity": CORP, "label": "August 2026"})
    _done(web, resp)
    batch = resp.json()["batch_id"]
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in (GUESSED, RULED, PICKED, PAYMENT):
        ws.append(list(row))
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
    view = web.get(f"/api/runs/{batch}").json()
    assert view["category_vocabulary"] == "gl", "precondition: a GL month"
    _assert_offered_no_parent(mock)

    rows = {r["vendor"]: r for r in view["rows"]}
    guessed = rows["ACME ANALYTICS"]
    assert not (guessed.get("charge_category") or {}).get("category"), guessed["charge_category"]
    assert guessed["review"]["refusal"] == MODEL_PICKED_PARENT, guessed["review"]
    ruled = rows["FIGMA"]["charge_category"]
    assert (ruled["category"], ruled["source"]) == (PARENT, "REGISTRY"), ruled

    # Criss picks the parent by hand: a person may.
    tx = rows["PRESSMASTER FZCO"]["transaction_id"]
    r = web.put(f"/api/runs/{batch}/charges/{tx}/category", json={"category": PARENT})
    assert r.status_code == 200, r.text
    rows = {r["vendor"]: r for r in web.get(f"/api/runs/{batch}").json()["rows"]}
    picked = rows["PRESSMASTER FZCO"]["charge_category"]
    assert (picked["category"], picked["source"]) == (PARENT, "EDITED"), picked
