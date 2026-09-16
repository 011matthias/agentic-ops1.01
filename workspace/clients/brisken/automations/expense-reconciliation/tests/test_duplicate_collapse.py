"""An invoice and its receipt are ONE candidate (backlog item 56, owner
ruling 2026-09-11: collapse automatically).

Stripe-style vendors (Lovable, Anthropic, Pressmaster) mail both an invoice
PDF and a receipt PDF for one purchase. Both land, both carry the same
merchant + date + total + currency, and the matcher saw two
indistinguishable candidates for one charge and filed the pairing as
AMBIGUOUS. In August 23 of 31 receipts sat in such pairs, so the reviewer
was asked to pick between two copies of the same document a dozen times a
month.

The pool now holds the first copy of every unresolved or confirmed
duplicate group. Nothing is dropped: the extra copy stays in the snapshot,
the counts and the exports, surfaces as unmatched, and keeps its duplicate
marker. A group the reviewer rules "not a duplicate" (`ignore`) is not
collapsed, and that ruling re-matches the month.
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

CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
CHASE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]


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
        payment_hint=None,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create_batch_with_the_pair(client, label="August 2026"):
    """The real shape: an invoice PDF and a receipt PDF for one purchase,
    both read as Lovable 15.00 on 2026-08-31."""
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("Invoice-HMVWDWIL.jpg", JPG + b"1", "application/octet-stream")),
            ("files", ("Receipt-2167-5718.jpg", JPG + b"2", "application/octet-stream")),
        ],
    ))
    return batch_id


def _xlsx_bytes(rows, headers) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach_xlsx(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(CHASE_ROWS, CHASE_HEADERS),
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


def _lovable_row(view):
    return next(r for r in view["rows"] if r["vendor"] == "LOVABLE")


def _pair(client, batch_id, monkeypatch):
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31"),
        _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31"),
    )
    return batch_id


# ── the ruling ──────────────────────────────────────────────────────────


def test_an_invoice_and_its_receipt_make_one_exact_match(client, monkeypatch):
    """Before: two candidates, `ambiguous`, the reviewer picks. After: one
    candidate, exact, reconciled without a click. The extra copy is still
    in the month, unmatched and marked as a duplicate."""
    _pair(client, None, monkeypatch)
    batch_id = _create_batch_with_the_pair(client)
    _attach_xlsx(client, batch_id)

    view = _view(client, batch_id)
    summary = view["summary"]
    assert summary["n_reconciled"] == 1
    assert summary["n_review"] == 0, "the pair no longer needs a human pick"
    row = _lovable_row(view)
    assert len(row["candidates"]) == 1
    assert row["candidates"][0]["match_type"] == "exact"

    # Nothing was dropped: both copies are still expenses of this month,
    # the extra one unmatched and still flagged as the copy it is.
    assert summary["n_receipts"] == 2
    assert summary["n_duplicate_groups"] == 1
    assert summary["n_duplicate_copies"] == 1
    assert summary["n_unmatched_rec"] == 1
    extra = view["unmatched_receipts"][0]
    assert extra["duplicate"]["is_extra"] is True
    assert extra["duplicate"]["n_copies"] == 2
    # Reconciliation guarantee on the receipt side: every receipt in the
    # pool is either paired or listed as unmatched, none silently absent.
    paired = {c["receipt"]["document_id"] for r in view["rows"] for c in r["candidates"]}
    assert len(paired | {extra["document_id"]}) == 2


def test_not_a_duplicate_puts_the_second_copy_back_in_the_pool(client, monkeypatch):
    """Two real purchases, same merchant, same day, same amount: the
    reviewer rules the group `ignore`, and the ruling re-matches the month
    rather than sitting there recorded and inert."""
    _pair(client, None, monkeypatch)
    batch_id = _create_batch_with_the_pair(client)
    _attach_xlsx(client, batch_id)
    view = _view(client, batch_id)
    group_id = view["duplicate_groups"][0]["group_id"]
    assert len(_lovable_row(view)["candidates"]) == 1

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group_id, "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("rematch") is not None, "the ruling must re-match"

    view = _view(client, batch_id)
    row = _lovable_row(view)
    assert len(row["candidates"]) == 2, "both copies compete again"
    assert row["effective_bucket"] == "review"
    # The dismissal also clears the row markers, as it always did: the
    # group is still DETECTED (it is listed, carrying the ruling), but no
    # row is a redundant copy any more.
    assert view["summary"]["n_duplicate_copies"] == 0
    assert view["duplicate_groups"][0]["resolution"] == "ignore"
    assert all(not r.get("duplicate") for r in view["unmatched_receipts"])


def test_confirmed_stays_collapsed(client, monkeypatch):
    """Acknowledging a duplicate is not un-duplicating it."""
    _pair(client, None, monkeypatch)
    batch_id = _create_batch_with_the_pair(client)
    _attach_xlsx(client, batch_id)
    group_id = _view(client, batch_id)["duplicate_groups"][0]["group_id"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group_id, "resolution": "confirmed"},
    )
    assert resp.status_code == 200, resp.text

    view = _view(client, batch_id)
    assert len(_lovable_row(view)["candidates"]) == 1
    assert view["summary"]["n_reconciled"] == 1


def test_a_pre_statement_batch_takes_the_resolution_without_a_rematch(client, monkeypatch):
    """The grid can resolve a group too, and a batch with no statement has
    nothing to re-match: it must answer with its OWN summary shape, not the
    workbench's, and not fail."""
    _pair(client, None, monkeypatch)
    batch_id = _create_batch_with_the_pair(client)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    group_id = grid["duplicate_groups"][0]["group_id"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group_id, "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "rematch" not in body
    assert "n_expenses" in body["summary"], "the grid's own shape"


def test_the_collapse_is_receipt_side_only(client, monkeypatch):
    """Two charges to one vendor are two charges (item 74, owner ruling
    2026-09-15): the statement is the truth of what was charged, so neither
    the collapse nor any duplicate marker touches the charge side, and no
    charge group is raised at all."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31"),
    )
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    rows = [
        (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
        (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    ]
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(rows, CHASE_HEADERS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    _done(client, resp)

    view = _view(client, batch_id)
    assert view["summary"]["n_transactions"] == 2, "both charges are still there"
    assert view["summary"]["n_duplicate_groups"] == 0
    assert view["duplicate_charges"] == []
    assert [g for g in view["duplicate_groups"] if g["kind"] == "charge"] == []
    assert [r for r in view["rows"] if r.get("duplicate")] == []
