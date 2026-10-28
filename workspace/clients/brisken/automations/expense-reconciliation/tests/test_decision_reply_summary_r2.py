"""Residual R2: a write's reply carries the summary a refetch would give.

The SPA renders the `summary` a decision route replies with until it refetches
the run. Those replies were built as `build_view(run, decisions, overrides)`:
no duplicate resolutions, no cross-month settlements, and above all no expense
FIELD overrides, which is where the month's header edits live. So a receipt
Criss had confirmed as a private expense read as still needing a charge
(`n_receipts_need_charge`, and `month_complete` with it) in every reply until
the next `GET /api/runs/{id}` put it right; the contract said so in prose
(api-contract, "The private half reads the expense header edits").

Route-level: make a header edit, then drive each write route and compare its
reply with what `GET /api/runs/{id}` answers immediately after.

Harness mirrors test_month_complete_publish_gate (fixtures copied, never
imported: a shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
LOVABLE = (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00)
OBSIDIAN = (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00)
PAYMENT = (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 111.00)
# The counts item 99 added, the ones a header edit moves.
COMPLETENESS = (
    "month_complete",
    "n_charges_need_receipt",
    "n_receipts_need_charge",
    "n_charges_category_guessed",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, date):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _attach(client, batch_id, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _view(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _month(client, monkeypatch, rows, *extractions) -> str:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
               for i in range(len(extractions))],
    ))
    _attach(client, batch_id, rows)
    return batch_id


def _doc_for(client, batch_id, vendor) -> str:
    """One receipt's document id, off the Expenses payload (which lists every
    receipt, matched or not)."""
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return next(
        e["document_id"] for e in resp.json()["expenses"]
        if vendor.lower() in (e["vendor"]["display"] or "").lower()
    )


def _mark_private(client, batch_id, vendor) -> str:
    """The header edit that closes a receipt: someone paid it themselves."""
    doc = _doc_for(client, batch_id, vendor)
    resp = client.post(
        f"/api/runs/{batch_id}/expenses/{doc}/private",
        json={"private": True, "reimburse_to": "Dirk"},
    )
    assert resp.status_code == 200, resp.text
    return doc


def _reply_matches_refetch(client, batch_id, resp) -> dict:
    assert resp.status_code == 200, resp.text
    reply = resp.json()["summary"]
    after = _view(client, batch_id)["summary"]
    # The comparison only means something while a header edit is actually
    # closing a receipt the reply would otherwise count.
    assert after["n_unmatched_rec"] > after["n_receipts_need_charge"], (
        "precondition: a confirmed private receipt is still listed and closed"
    )
    assert {k: reply.get(k) for k in COMPLETENESS} == {
        k: after.get(k) for k in COMPLETENESS
    }
    assert reply == after
    return after


def _pending_row(client, batch_id, vendor):
    return next(
        r for r in _view(client, batch_id)["rows"] if r["vendor"] == vendor
    )


def test_a_decision_reply_counts_a_private_receipt_the_way_the_run_does(
    client, monkeypatch
):
    """The live shape: one charge left to decide, one receipt confirmed
    private. The reply used to say the private receipt still needed a charge
    while the very next GET said it did not."""
    batch = _month(
        client, monkeypatch, [LOVABLE, OBSIDIAN, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Brauhaus Kuehler Krug", "140.00", "2026-08-12"),
    )
    _mark_private(client, batch, "Brauhaus")
    assert _view(client, batch)["summary"]["n_receipts_need_charge"] == 0

    row = _pending_row(client, batch, "LOVABLE")
    resp = client.post(
        f"/api/runs/{batch}/decisions",
        json={"transaction_id": row["transaction_id"], "status": "confirmed"},
    )
    summary = _reply_matches_refetch(client, batch, resp)
    assert summary["n_receipts_need_charge"] == 0, "the private receipt is closed"
    assert summary["n_unmatched_rec"] == 1, "and still listed, as it always was"


def test_every_write_route_answers_with_the_run_payloads_own_summary(
    client, monkeypatch
):
    """The sweep: each route that replies with a `summary` replies with the
    one `GET /api/runs/{id}` serves, so the SPA's counts never depend on
    which write produced them."""
    batch = _month(
        client, monkeypatch, [LOVABLE, OBSIDIAN, PAYMENT],
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Brauhaus Kuehler Krug", "140.00", "2026-08-12"),
        _extraction("Redis Inc.", "13200.00", "2026-08-12"),
    )
    _mark_private(client, batch, "Brauhaus")
    redis = _doc_for(client, batch, "Redis")
    lovable_doc = _doc_for(client, batch, "Lovable")

    obsidian = _pending_row(client, batch, "OBSIDIAN")["transaction_id"]
    _reply_matches_refetch(client, batch, client.post(
        f"/api/runs/{batch}/decisions/bulk",
        json={"transaction_ids": [obsidian], "status": "already_posted"},
    ))
    _reply_matches_refetch(client, batch, client.post(
        f"/api/runs/{batch}/disposition",
        json={"transaction_id": obsidian, "disposition": "business"},
    ))
    _reply_matches_refetch(client, batch, client.post(
        f"/api/runs/{batch}/decisions/confirm-ready",
    ))
    lovable = _pending_row(client, batch, "LOVABLE")["transaction_id"]
    _reply_matches_refetch(client, batch, client.post(
        f"/api/runs/{batch}/manual-match",
        json={"transaction_id": lovable, "document_id": lovable_doc},
    ))
    # The settled-outside write already dispatched on the run's mode; it too
    # was missing the header edits.
    _reply_matches_refetch(client, batch, client.post(
        f"/api/runs/{batch}/receipts/{redis}/settled-outside",
        json={"how": "bank_transfer"},
    ))
    _reply_matches_refetch(client, batch, client.delete(
        f"/api/runs/{batch}/receipts/{redis}/settled-outside",
    ))
