"""Item 105 (audit draft #103): an invoice the reader calls a statement page.

Three real July invoices (AWS USD 3,352.59, Microsoft USD 718.20, Tricarico
BRL 27,203.34) were read as statement pages and left the month. Each stored
reading still carried a vendor, a total, its invoice number and its own line
items. Eight real statements read through the same reader (seven Chase card
statements, an SAP accounts-receivable statement) carried no reference and no
line items; two billing-notice emails carried no line items. So a "statement"
verdict with all four is kept as an expense with a note to check it, on both
entrances: a drop that creates its month (the create path) and a receipt
added to an open month (the add path). Every other shape stays set aside.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ClassificationResult,
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000
DAY = date.today().replace(day=1) - timedelta(days=20)
MONTH = f"{DAY.year:04d}-{DAY.month:02d}"
LABEL = f"{calendar.month_name[DAY.month]} {DAY.year}"
NOTE = "read as a statement page"

AWS_ITEMS = (
    ExtractedLineItem(description="Amazon Elastic Container Service",
                      line_total="2096.77"),
    ExtractedLineItem(description="AmazonCloudWatch", line_total="373.51"),
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c


def _reading(document_type="statement", vendor="Amazon Web Services, Inc.",
             total="3352.59", reference="2704896057", items=AWS_ITEMS):
    return ExtractedReceipt(
        date=DAY.isoformat(), total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=items, confidence=0.9, notes="",
        document_type=document_type,
    )


def _patch_ocr(monkeypatch, *readings, categories=None) -> None:
    mock = MockLLMClient(
        extraction_responses=list(readings), responses=categories,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _batch(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _open_month(client, monkeypatch) -> str:
    _patch_ocr(monkeypatch)
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": LABEL},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _add(client, batch_id, name="invoice.jpg") -> None:
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _kept_invoice(view: dict) -> dict:
    assert view["summary"]["n_expenses"] == 1, view["summary"]
    assert view.get("set_aside") in (None, []), view.get("set_aside")
    (expense,) = view["expenses"]
    assert NOTE in (expense.get("data_quality_note") or ""), expense
    return expense


def test_a_drop_that_creates_its_month_keeps_the_invoice(client, monkeypatch):
    _patch_ocr(monkeypatch, _reading())  # the month pick skips the date pass
    resp = client.post(
        "/api/receipts",
        files=[("files", ("aws.jpg", JPG, "application/octet-stream"))],
        data={"month": MONTH},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    entry = job["result"]["months"][0]
    assert entry["created_batch"] is True
    expense = _kept_invoice(_batch(client, entry["batch_id"]))
    assert str(expense["total"]).replace(",", "") == "3352.59", expense["total"]


def test_an_add_to_an_open_month_keeps_the_invoice(client, monkeypatch):
    batch_id = _open_month(client, monkeypatch)
    _patch_ocr(monkeypatch, _reading(
        vendor="RODRIGO TANURE TRICARICO CONSULTORIA", total="27203.34",
        reference="0018",
        items=(ExtractedLineItem(description="Consulting services",
                                 line_total="27503.34"),),
    ))
    _add(client, batch_id)
    view = _batch(client, batch_id)
    _kept_invoice(view)
    assert view["expense_ingest"]["n_added"] == 1
    assert not view["expense_ingest"].get("not_added")


@pytest.mark.parametrize("reading", [
    pytest.param(dict(vendor="Chase", total="6470.63", reference=None, items=()),
                 id="chase-statement"),
    pytest.param(dict(vendor=None, total="2226.97", reference=None, items=()),
                 id="sap-ar-statement"),
    pytest.param(dict(reference="351503119085", items=()),
                 id="billing-notice-no-items"),
    pytest.param(dict(reference=None), id="no-reference"),
    pytest.param(dict(total=None), id="no-total"),
    pytest.param(dict(vendor="  "), id="blank-vendor"),
    pytest.param(dict(document_type="report_summary"), id="report-summary"),
    pytest.param(dict(document_type="other"), id="other"),
    pytest.param(dict(total="0.00"), id="zero-balance"),
    pytest.param(
        dict(items=(ExtractedLineItem(description="(illegible)", line_total=None),)),
        id="items-without-amounts",
    ),
])
def test_everything_else_stays_set_aside(client, monkeypatch, reading):
    batch_id = _open_month(client, monkeypatch)
    _patch_ocr(monkeypatch, _reading(**reading))
    _add(client, batch_id)
    view = _batch(client, batch_id)
    assert view["summary"]["n_expenses"] == 0, view["summary"]
    assert [e["display"] for e in view["set_aside"]] == ["invoice.jpg"]


def test_a_kept_invoice_is_checked_until_its_category_is_confirmed(
    client, monkeypatch
):
    batch_id = _open_month(client, monkeypatch)
    # Both lines categorized from their own text (LINE), so without this
    # item the row would read ready.
    software = ClassificationResult(
        category="Software & Subscriptions", zoho_account=None,
        confidence=0.95, reasoning="cloud hosting",
    )
    _patch_ocr(monkeypatch, _reading(), categories=[[software, software]])
    _add(client, batch_id)
    (row,) = _batch(client, batch_id)["expenses"]
    assert row["review"]["state"] == "check", row["review"]
    assert row["review"]["reason_code"] == "invoice_read_as_statement"
    assert "ready" not in row["boxes"], row["boxes"]
    assert row["category_confirmable"] is True

    resp = client.post(
        f"/api/runs/{batch_id}/expenses/{row['document_id']}/confirm-category"
    )
    assert resp.status_code == 200, resp.text
    (row,) = _batch(client, batch_id)["expenses"]
    assert row["review"]["reason_code"] != "invoice_read_as_statement", row["review"]
    assert row["category_confirmable"] is False
    assert NOTE in row["data_quality_note"]  # the note stays as the record
