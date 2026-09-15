"""A rejected pairing says so, and says how to take it back (item 16).

Noted 2026-07-27: rejecting a match sends the charge back to unmatched and is
reversible until export, but nothing in the payload recorded that a candidate
had been turned down. `candidates` come from the RAW outcome, so every receipt
the reviewer just pushed away re-renders underneath the row exactly as it did
before the reject, offered again as if it were still on the table, and no
affordance could answer "what now".

`rows[].candidates[].rejected` is that missing fact, and
`summary.n_rejected_pairings` counts them. Both read the CURRENT verdict, so
the reversal clears them.

The reversal is not new: `POST /api/runs/{id}/decisions` with
`"status": "pending"` already resets a charge, under the batch lock, with the
claim re-derived by `sync_claim_for_decision`. What was missing was the
payload saying there was anything to reverse. `test_the_undo_path_is_the_same
_route_with_pending` is the proof that the existing route really does undo,
rather than an assertion that it ought to.

Route-level throughout: the verdict goes through the decision routes the SPA
calls, and every assertion reads `GET /api/runs/{id}`.
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

# LOVABLE matches the receipt; SUPABASE does not (different vendor, amount and
# day), so the month starts with exactly one settled pairing to reject.
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


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
    """A month where LOVABLE holds its receipt, ready to be rejected."""
    _wire(monkeypatch, _extraction("Lovable Labs", "25.00", "2026-08-05"))
    batch_id = _create_batch(client)
    _attach(client, batch_id)
    view = _view(client, batch_id)
    assert _row(view, "LOVABLE")["effective_bucket"] == "reconciled"
    return batch_id, view


def _decide(client, batch_id, tx_id, status, doc=None):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={
            "transaction_id": tx_id, "status": status, "chosen_document_id": doc,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_a_rejected_candidate_says_it_was_rejected(client, monkeypatch):
    """The reported state: the charge falls back to unmatched and keeps the
    receipt on display. The candidate now carries the verdict that put it
    there, so the SPA can stop offering it as a fresh option."""
    batch_id, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    doc = lovable["candidates"][0]["document_id"]
    assert all("rejected" not in c for c in lovable["candidates"])

    _decide(client, batch_id, lovable["transaction_id"], "rejected", doc)

    view = _view(client, batch_id)
    lovable = _row(view, "LOVABLE")
    assert lovable["status"] == "rejected"
    assert lovable["effective_bucket"] == "unmatched"
    assert lovable["candidates"], "the reported state: candidates on a rejected row"
    assert lovable["candidates"][0]["document_id"] == doc
    assert lovable["candidates"][0]["rejected"] is True
    assert view["summary"]["n_rejected_pairings"] == 1
    # The receipt really is free again: it is back in the pool, which is what
    # makes the "what now" question answerable at all.
    assert doc in [r["document_id"] for r in view["unmatched_receipts"]]


def test_a_month_with_no_reject_carries_no_flag_at_all(client, monkeypatch):
    """Parallel field: absent, not false, so a month nobody rejected in
    renders byte-identically to before this shipped."""
    _, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    assert lovable["candidates"]
    assert all("rejected" not in c for c in lovable["candidates"])
    assert all(
        "rejected" not in c for r in view["rows"] for c in r["candidates"]
    )
    assert view["summary"]["n_rejected_pairings"] == 0


def test_the_undo_path_is_the_same_route_with_pending(client, monkeypatch):
    """The "what now" answer. No new route was needed: resetting the charge to
    `pending` on the decision route clears the verdict, the flag, the count,
    and gives the charge its receipt back. Asserting the whole reversal, not
    just the flag, is what proves the affordance the SPA is about to offer
    actually works."""
    batch_id, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")
    tx_id = lovable["transaction_id"]
    doc = lovable["candidates"][0]["document_id"]

    _decide(client, batch_id, tx_id, "rejected", doc)
    assert _view(client, batch_id)["summary"]["n_rejected_pairings"] == 1

    _decide(client, batch_id, tx_id, "pending", None)

    view = _view(client, batch_id)
    lovable = _row(view, "LOVABLE")
    assert lovable["status"] == "pending"
    assert lovable["effective_bucket"] == "reconciled"
    assert lovable["chosen_document_id"] == doc
    assert all("rejected" not in c for c in lovable["candidates"])
    assert view["summary"]["n_rejected_pairings"] == 0
    assert doc not in [r["document_id"] for r in view["unmatched_receipts"]]


def test_a_bulk_reject_marks_its_pairings_too(client, monkeypatch):
    """`bulk_decisions` writes `chosen_document_id` NULL on a reject, so a
    flag keyed on the named document would leave the commonest path
    unmarked. The verdict is charge-level; so is the flag."""
    batch_id, view = _settled_month(client, monkeypatch)
    lovable = _row(view, "LOVABLE")

    resp = client.post(
        f"/api/runs/{batch_id}/decisions/bulk",
        json={"transaction_ids": [lovable["transaction_id"]], "status": "rejected"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["updated"] == 1

    view = _view(client, batch_id)
    lovable = _row(view, "LOVABLE")
    assert lovable["chosen_document_id"] is None
    assert lovable["candidates"][0]["rejected"] is True
    assert view["summary"]["n_rejected_pairings"] == 1


def test_a_rejected_charge_with_no_candidate_counts_no_pairing(
    client, monkeypatch
):
    """Pairings, not rows. SUPABASE has no candidate, so rejecting it refuses
    nothing and the count stays at zero; the name has to keep answering its
    one question."""
    batch_id, view = _settled_month(client, monkeypatch)
    supabase = _row(view, "SUPABASE")
    assert supabase["candidates"] == []

    _decide(client, batch_id, supabase["transaction_id"], "rejected", None)

    view = _view(client, batch_id)
    assert _row(view, "SUPABASE")["status"] == "rejected"
    assert view["summary"]["n_rejected_pairings"] == 0
