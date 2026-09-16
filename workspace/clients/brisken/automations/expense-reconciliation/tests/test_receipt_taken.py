"""A charge whose receipt another charge holds says so (backlog item 60).

Reported on 2026-09-11: a charge with waiting candidates rendered "No receipt
found" while the receipts showed elsewhere as awaiting a decision. The
mechanism: `candidates` come from the RAW outcome, which keeps every receipt
the matcher paired with this charge, while the bucket comes from the EFFECTIVE
verdict after `apply_decisions`, and one receipt settles exactly one charge.
When a receipt is reassigned, the charge that lost it keeps the candidate on
display and falls to `unmatched`, so a label derived from the bucket calls
that "no receipt" about a receipt sitting on another row.

The candidate now names its holder, so the SPA can say what is true. Absent,
not null, on a candidate nobody else holds, so a month with nothing contested
renders exactly as before.

Route-level: the steal goes through `POST /api/runs/{id}/manual-match`, which
is the documented way one charge takes a receipt another already had.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")

# LOVABLE matches the receipt; SUPABASE does not (different vendor, amount
# and day), so the month starts with exactly one settled pairing.
ROWS = [
    (datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    (datetime(2026, 8, 19), "SUPABASE", "Sale", -92.70),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1,
                implied_rate=1.0, converted_amount=Decimal("25.00"),
                reasoning="mock",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(vendor, total, date):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create_batch(client):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("lovable.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, rows=ROWS):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(view, vendor):
    return next(r for r in view["rows"] if r["vendor"] == vendor)


def _settled_month(client, monkeypatch):
    _wire(monkeypatch, _extraction("Lovable Labs", "25.00", "2026-08-05"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    view = _view(client, batch_id)
    assert _row(view, "LOVABLE")["effective_bucket"] == "reconciled"
    return batch_id, view


def test_the_dispossessed_charge_names_the_charge_that_took_its_receipt(
    client, monkeypatch
):
    """LOVABLE holds the receipt; the reviewer hand-matches it to SUPABASE.
    LOVABLE keeps the candidate on display and falls to `unmatched`, which is
    the reported state, and the candidate now says who has it."""
    batch_id, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    supabase = _row(view, "SUPABASE")
    doc = lovable["candidates"][0]["document_id"]

    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": supabase["transaction_id"], "document_id": doc},
    )
    assert resp.status_code == 200, resp.text

    view = _view(client, batch_id)
    lovable = _row(view, "LOVABLE")
    assert lovable["effective_bucket"] == "unmatched"
    assert lovable["candidates"], "the reported state: candidates on an unmatched row"
    held = lovable["candidates"][0]["held_by"]
    assert held["transaction_id"] == supabase["transaction_id"]
    assert held["vendor"] == "SUPABASE"
    assert held["amount"] == "92.70"
    assert held["date"] == "2026-08-19"
    # The holder's own candidate is not "taken": it is the holder.
    assert all("held_by" not in c for c in _row(view, "SUPABASE")["candidates"])
    assert view["summary"]["n_charges_receipt_taken"] == 1


def test_an_uncontested_month_carries_no_held_by_at_all(client, monkeypatch):
    """Parallel field: absent, not null, when nothing is contested."""
    _, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    assert lovable["candidates"]
    assert all("held_by" not in c for c in lovable["candidates"])
    assert view["summary"]["n_charges_receipt_taken"] == 0


def test_giving_the_receipt_back_clears_the_marker(client, monkeypatch):
    """The marker follows the EFFECTIVE verdict, not the matcher's first
    answer, so undoing the steal has to undo the marker."""
    batch_id, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    supabase = _row(view, "SUPABASE")
    doc = lovable["candidates"][0]["document_id"]
    _ = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": supabase["transaction_id"], "document_id": doc},
    )
    assert _view(client, batch_id)["summary"]["n_charges_receipt_taken"] == 1

    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": lovable["transaction_id"], "document_id": doc},
    )
    assert resp.status_code == 200, resp.text

    view = _view(client, batch_id)
    assert _row(view, "LOVABLE")["effective_bucket"] == "reconciled"
    assert all("held_by" not in c for c in _row(view, "LOVABLE")["candidates"])
    assert view["summary"]["n_charges_receipt_taken"] == 0
