"""Residual R1: the Expenses grid's `books_as` runs the export's chart gate.

Item 95 made the chart gate keep a line's category and clear only its
account, so the CSV stopped printing `(uncategorized - assign)` for rows the
screen shows categorized. The grid's own depiction still never ran the gate:
`build_expense_view` called `expense_posting_parts` on its receipts while the
export called it on GATED receipts, with the chart. A line whose account the
company's chart rejects therefore read as that account on screen and as its
category (or `(account unmapped - assign)`) in the document, for the same
purchase. No live row differed on 2026-09-17 (July and August agree today,
checked through `GET /runs/{id}/expenses.csv`), because live accounts are the
tool's own category labels, which the two paths render alike.

Route-level: the grid payload's `books_as` is compared with the CSV the same
month downloads, in the two shapes a live batch takes -- a batch that names
one company (a single `CoaGate` WITH a chart) and one that does not (the
many-entity gate, no chart) -- plus the unprovisioned negative case.

Harness mirrors test_mixed_entity_export (fixtures copied, never imported:
a shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import csv
import io
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.output.zoho_expense_export import EXPENSE_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
COL_ACCOUNT = EXPENSE_COLUMNS.index("Expense Account")
COL_AMOUNT = EXPENSE_COLUMNS.index("Expense Amount")
COL_VENDOR = EXPENSE_COLUMNS.index("Vendor")
PLACEHOLDER = "(uncategorized - assign)"
UNMAPPED = "(account unmapped - assign)"
# An account no chart in this test holds: the shape of a category edit that
# names an account (item 70) the company's books do not carry.
PHANTOM = "E900 Phantom"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_COA_PROVISION", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="100.00", currency="USD", vendor="Airline",
                reference="", line_items=(), confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _provision_charts(tmp_path, monkeypatch) -> None:
    """A provisioned Corporate Services chart holding one real account and
    none of the tool's category labels: the live shape."""
    chart = tmp_path / "coa.json"
    chart.write_text(json.dumps({
        "822741658": {"org": {"name": "Corporate Services"}, "accounts": [
            {"account_id": "1", "account_name": "Office Supplies",
             "account_code": "E500", "account_type": "expense",
             "parent_account_name": None, "is_active": True}]},
    }), encoding="utf-8")
    prov = tmp_path / "coa-provision.json"
    prov.write_text(json.dumps({
        "chart_path": str(chart),
        "entities": {"Corporate Services": {"org_id": "822741658"}},
    }), encoding="utf-8")
    monkeypatch.setenv("EXPENSE_RECON_COA_PROVISION", str(prov))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _batch_with_one_receipt(client, monkeypatch, entity: str) -> tuple[str, str]:
    mock = MockLLMClient(extraction_responses=[_extraction()])
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": entity, "label": "August 2026"}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("airline.jpg", JPG, "application/octet-stream"))],
    ))
    (row,) = client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return batch_id, row["document_id"]


def _categorize(client, batch_id, doc, account: str | None) -> None:
    """The item-70 reclassify, with an explicit account when one is given."""
    body = {"document_id": doc, "category": "Travel & Transport"}
    if account is not None:
        body["zoho_account"] = account
    resp = client.post(f"/api/runs/{batch_id}/categories", json=body)
    assert resp.status_code == 200, resp.text


def _assign_entity(client, batch_id, doc, entity: str) -> None:
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}/entity", json={"legal_entity": entity}
    )
    assert resp.status_code == 200, resp.text


def _books_as(client, batch_id) -> list[tuple[str, str]]:
    (row,) = client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
    return [
        (PLACEHOLDER if b["unassigned"] else b["account"], b["amount"].replace(",", ""))
        for b in row["books_as"]
    ]


def _csv_rows(client, batch_id) -> list[tuple[str, str]]:
    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == list(EXPENSE_COLUMNS)
    return [(r[COL_ACCOUNT], r[COL_AMOUNT].replace(",", "")) for r in rows[1:]]


def test_a_named_company_gates_the_screen_the_way_it_gates_the_csv(
    client, monkeypatch
):
    """A batch that names its company carries a single `CoaGate` WITH that
    company's chart. An account the chart does not hold books as
    `(account unmapped - assign)` in the CSV; the screen said `E900 Phantom`."""
    _provision_charts(client._data_root, monkeypatch)
    batch_id, doc = _batch_with_one_receipt(client, monkeypatch, "Corporate Services")
    _categorize(client, batch_id, doc, PHANTOM)

    assert _csv_rows(client, batch_id) == [(UNMAPPED, "100.00")]
    assert _books_as(client, batch_id) == _csv_rows(client, batch_id)


def test_a_many_company_month_gates_the_screen_the_way_it_gates_the_csv(
    client, monkeypatch
):
    """A month that names no company carries one gate per company (the live
    July / August shape, no chart on the gate). The rejected account is
    cleared and the line books as `(account unmapped - assign)`, on both
    surfaces. It booked as its CATEGORY until item 5 (owner: everywhere)."""
    _provision_charts(client._data_root, monkeypatch)
    batch_id, doc = _batch_with_one_receipt(client, monkeypatch, "")
    _categorize(client, batch_id, doc, PHANTOM)
    # Un-stamped, the many-entity gate judges nothing: both sides print the
    # account as typed, and they already agree.
    assert _books_as(client, batch_id) == _csv_rows(client, batch_id) == [
        (PHANTOM, "100.00")
    ]

    _assign_entity(client, batch_id, doc, "Corporate Services")
    assert _csv_rows(client, batch_id) == [(UNMAPPED, "100.00")]
    assert _books_as(client, batch_id) == _csv_rows(client, batch_id)


def test_with_no_chart_provisioned_the_screen_prints_what_was_typed(
    client, monkeypatch
):
    """The negative case: no provisioning, no gate, nothing invented. The
    account the reviewer named survives to both surfaces, and a row nobody
    categorized reads as the placeholder on both."""
    batch_id, doc = _batch_with_one_receipt(client, monkeypatch, "Corporate Services")
    assert _books_as(client, batch_id) == _csv_rows(client, batch_id) == [
        (PLACEHOLDER, "100.00")
    ]

    _categorize(client, batch_id, doc, PHANTOM)
    assert _books_as(client, batch_id) == _csv_rows(client, batch_id) == [
        (PHANTOM, "100.00")
    ]
