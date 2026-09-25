"""Item 206: a card that gives a row its company re-runs the engine for it.

On a GL month the engine answers per company, and a receipt that arrives
with no company is refused `entity_missing`. Setting the company re-ran the
engine (owner decision 2026-09-24), but most rows get their company through
the card chain instead: a per-row card fix, a card-hint assignment, a
statement charge that settles the receipt. None of those re-ran it, so the
row kept its refusal while the grid named a company.

Every assertion runs through a route, and reads back through the grid, the
stored categorization and the CSV: the card fix, a card change from one
company to another, a hint assignment, a statement attach, a re-match after
a date edit, a row that showed a company before this fix, and a bucket month
that must stay untouched.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.categorize import ENTITY_MISSING  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from expense_recon.zoho import curated_leaves  # noqa: E402

CORP, CLOUD = "Corporate Services", "Cloud Services"
CORP_ORG, CLOUD_ORG = "822741658", "697686691"
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
LEAF = re.compile(r"^E\d{6}(-\d{2})*$")
JPG = b"\xff\xd8\xff\xe0item206-bytes"
CARDS = {
    "corp-1672": {"label": "Corporate card", "digits": ["1672"], "entity": CORP,
                  "person": "Dirk", "zoho_account": "Chase 1672"},
    "cloud-9693": {"label": "Cloud card", "digits": ["9693"], "entity": CLOUD,
                   "person": "Nicolas", "zoho_account": "Chase 9693"},
}


def _only_in(org: str, other: str) -> str:
    """A code `org` can post to and `other` cannot, so the pick names the
    company the engine answered for. A leaf the model is offered, since it
    is never offered a parent (item 216 Build 2)."""
    return next(c for c in sorted(curated_leaves.postable_codes(org))
                if not curated_leaves.is_postable(other, c)
                and not curated_leaves.has_postable_children(org, c))


CORP_CODE, CLOUD_CODE = _only_in(CORP_ORG, CLOUD_ORG), _only_in(CLOUD_ORG, CORP_ORG)


class _Leaf(MockLLMClient):
    """Extracts from the mock's queue; classifies with the offered label of
    CORP_CODE or CLOUD_CODE, whichever the row's company offers."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.classified = 0

    def _pick(self, categories):
        self.classified += 1
        return next((c for c in categories
                     if c.split(None, 1)[0] in (CORP_CODE, CLOUD_CODE)),
                    categories[0])  # a bucket month offers buckets

    def classify_line_items(self, items, categories, chart_of_accounts=None, **_):
        return [ClassificationResult(self._pick(categories), None, 0.9, "fake")
                for _ in items]

    def classify_by_vendor(self, vendor, total, categories,
                           chart_of_accounts=None, **_):
        return ClassificationResult(self._pick(categories), None, 0.9, "fake")


def _chart_accounts(org: str) -> list[dict]:
    from expense_recon.zoho._curated_leaves_data import LEAVES

    return [
        {"account_id": b[org][0], "account_name": b[org][1], "account_code": code,
         "account_type": "expense", "is_active": True, "parent_account_name": None}
        for code, (_branch, b) in LEAVES.items() if org in b
    ]


def _provision(tmp_path: Path, monkeypatch) -> None:
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


def _app(tmp_path, monkeypatch, *, gl: bool):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    if gl:
        _provision(tmp_path, monkeypatch)
    client = TestClient(create_app(tmp_path))
    client._data_root = tmp_path
    return client


@pytest.fixture
def web(tmp_path, monkeypatch):
    with _app(tmp_path, monkeypatch, gl=True) as c:
        assert c.put("/api/settings", json={"cards": CARDS}).status_code == 200
        yield c


def _wire(monkeypatch, *receipts: tuple) -> _Leaf:
    """(vendor, total, date, printed payment method) per receipt, in order."""
    client = _Leaf(
        extraction_responses=[
            ExtractedReceipt(date=d, total=t, currency="USD", vendor=v,
                             reference="", line_items=(), confidence=0.9,
                             notes="", payment_hint=h)
            for v, t, d, h in receipts
        ],
        fx_responses=[FxJudgmentResult(
            is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
            converted_amount=Decimal("15.00"), reasoning="same purchase")] * 8,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client",
                        lambda cfg: (client, None))
    return client


def _done(web, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = web.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(web, monkeypatch, hint=None, *, day="2026-08-31") -> tuple[str, str, _Leaf]:
    """The live shape: a month created with no company, and one Lovable
    receipt, USD 15.00."""
    client = _wire(monkeypatch, ("Lovable Labs", "15.00", day, hint))
    resp = web.post("/api/expense-batches",
                    data={"legal_entity": "", "label": "August 2026"})
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    _done(web, web.post(f"/api/expense-batches/{batch_id}/receipts",
                        files=[("files", ("lovable.jpg", JPG, "application/octet-stream"))]))
    return batch_id, _row(web, batch_id)["document_id"], client


def _row(web, batch_id) -> dict:
    (row,) = web.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return row


def _stored(web, batch_id) -> dict:
    conn = sqlite3.connect(Path(web._data_root) / "recon-web.sqlite")
    try:
        snap = json.loads(conn.execute(
            "SELECT snapshot FROM runs WHERE run_id = ?", (batch_id,)).fetchone()[0])
    finally:
        conn.close()
    (rec,) = snap["receipts"]
    return rec["line_items"][0]["categorization"]


def _csv_accounts(web, batch_id) -> list[str]:
    resp = web.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    return [r[COL_ACCOUNT] for r in list(csv.reader(io.StringIO(resp.text)))[1:]]


def _refused_without_a_company(web, batch_id) -> None:
    row = _row(web, batch_id)
    assert not row["legal_entity_id"], "precondition: no company shown"
    assert _stored(web, batch_id)["refusal"] == ENTITY_MISSING
    assert not (row["posting_category"] or {}).get("category")


def _answers_for(web, batch_id, company, org, code, *, csv_too=True) -> None:
    row = _row(web, batch_id)
    assert row["legal_entity_id"] == company
    assert row["entity_source"] != "override", "the company came from the card"
    # Item 216 Build 2 step 2: the engine's answer here is the model's, so it
    # is the row's suggestion, never its posting, and the CSV labels it.
    assert row["posting_category"] is None, row["posting_category"]
    category = row["suggested_category"]["category"]
    assert LEAF.match(category) and curated_leaves.is_postable(org, category)
    assert category == code
    assert row["review"].get("reason_code") != "category_refused"
    assert "refusal" not in _stored(web, batch_id)
    if csv_too:
        assert _csv_accounts(web, batch_id) == [
            f"suggested: {curated_leaves.binding(code, org).name}"]


def test_a_card_fix_that_gives_the_row_its_company_re_runs_the_engine(web, monkeypatch):
    batch_id, doc, _client = _month(web, monkeypatch)
    _refused_without_a_company(web, batch_id)

    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "card_key", "value": "corp-1672"})

    assert r.status_code == 200, r.text
    assert r.json()["recategorized"] == {
        "document_id": doc, "entity": CORP, "refusals": []}
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)


def test_a_card_change_to_another_company_re_runs_for_the_new_one(web, monkeypatch):
    batch_id, doc, client = _month(web, monkeypatch, "Visa ...1672")
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)  # stamped at ingest

    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "card_key", "value": "cloud-9693"})

    assert r.status_code == 200, r.text
    assert [x["entity"] for x in r.json()["recategorized_rows"]] == [CLOUD]
    # Not the CSV: the export's chart gate still checks the receipt's stamped
    # company (Corporate Services, from the printed card), not the one the row
    # shows, and blanks a Cloud-only account. Backlog item 210, owner's call.
    _answers_for(web, batch_id, CLOUD, CLOUD_ORG, CLOUD_CODE, csv_too=False)

    # The same card again moves nothing, so nothing is re-run.
    calls = client.classified
    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "card_key", "value": "cloud-9693"})
    assert "recategorized_rows" not in r.json()
    assert client.classified == calls


def test_setting_the_company_the_card_already_shows_still_re_runs(web, monkeypatch):
    """Owner decision 2026-09-24: assigning the company categorizes the
    receipt, even where its card already showed that company."""
    batch_id, doc, client = _month(web, monkeypatch, "Visa ...1672")
    calls = client.classified

    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}/entity",
                json={"legal_entity": CORP})

    assert r.status_code == 200, r.text
    assert r.json()["recategorized"]["entity"] == CORP
    assert client.classified == calls + 1


def test_a_card_hint_assignment_re_runs_the_rows_it_gives_a_company(web, monkeypatch):
    batch_id, doc, _client = _month(web, monkeypatch, "Firmenkarte")
    _refused_without_a_company(web, batch_id)

    r = web.post(f"/api/expense-batches/{batch_id}/cards",
                 json={"assignments": [{"hint": "Firmenkarte", "card": "corp-1672"}]})

    assert r.status_code == 200, r.text
    assert [x["document_id"] for x in r.json()["recategorized_rows"]] == [doc]
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Card", "Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(web, batch_id) -> None:
    _done(web, web.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx",
            _xlsx([("1672", datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00)]),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"account_id": "card-1672",
              "account_legal_entities": json.dumps({"card-1672": CORP}),
              "account_card_currency": "USD"},
    ))


def test_a_statement_charge_that_settles_the_receipt_re_runs_the_engine(
    web, monkeypatch,
):
    batch_id, _doc, _client = _month(web, monkeypatch)
    _refused_without_a_company(web, batch_id)

    _attach(web, batch_id)

    assert _row(web, batch_id)["card_source"] == "settled_charge"
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)


def test_a_re_match_that_pairs_the_receipt_re_runs_the_engine(web, monkeypatch):
    """The receipt's date is misread, so the attach pairs nothing; fixing the
    date re-matches the month, the charge now settles it, and the re-match
    re-runs the engine for the company that lends."""
    batch_id, doc, _client = _month(web, monkeypatch, day="2026-03-02")
    _attach(web, batch_id)
    _refused_without_a_company(web, batch_id)

    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "date", "value": "2026-08-31"})

    assert r.status_code == 200, r.text
    assert [x["entity"] for x in r.json()["recategorized_rows"]] == [CORP]
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)


def test_a_row_that_already_shows_a_company_is_swept_at_its_next_edit(
    web, monkeypatch,
):
    """A row given its card before this fix shows a company and is still
    refused. The next edit that reads the card chain re-runs it."""
    batch_id, doc, _client = _month(web, monkeypatch)
    with RunStore(Path(web._data_root) / "recon-web.sqlite") as store:
        store.set_expense_field_override(
            batch_id, doc, "card_key", "corp-1672", "2026-09-25T00:00:00")
    assert _row(web, batch_id)["legal_entity_id"] == CORP
    assert _stored(web, batch_id)["refusal"] == ENTITY_MISSING

    r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                json={"field": "vendor", "value": "Lovable"})

    assert r.status_code == 200, r.text
    _answers_for(web, batch_id, CORP, CORP_ORG, CORP_CODE)


def test_a_bucket_month_is_left_untouched(tmp_path, monkeypatch):
    with _app(tmp_path, monkeypatch, gl=False) as web:
        assert web.put("/api/settings", json={"cards": CARDS}).status_code == 200
        client = _wire(monkeypatch, ("Lovable Labs", "15.00", "2026-08-31", None))
        batch_id = web.post("/api/expense-batches",
                            data={"legal_entity": ""}).json()["batch_id"]
        _done(web, web.post(f"/api/expense-batches/{batch_id}/receipts",
                            files=[("files", ("lovable.jpg", JPG, "application/octet-stream"))]))
        body = web.get(f"/api/expense-batches/{batch_id}").json()
        assert body["category_vocabulary"] == "buckets", "precondition: a bucket month"
        before, calls = _stored(web, batch_id), client.classified
        doc = body["expenses"][0]["document_id"]

        r = web.put(f"/api/runs/{batch_id}/expenses/{doc}",
                    json={"field": "card_key", "value": "corp-1672"})

        assert r.status_code == 200, r.text
        assert "recategorized" not in r.json()
        assert "recategorized_rows" not in r.json()
        assert _row(web, batch_id)["legal_entity_id"] == CORP
        assert _stored(web, batch_id) == before
        assert client.classified == calls
