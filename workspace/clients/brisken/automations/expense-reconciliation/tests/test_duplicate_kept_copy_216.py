"""Which copy of a duplicate is the real expense (backlog item 216, notes
#89 / #90, owner 2026-09-25).

On September's Pressmaster pair the owner wrote: "the real expense should be
big and duplicate should be small so they should effectively switch places".
The tool kept a group's FIRST member by document id, so a Stripe vendor's
invoice (attached before its receipt) was kept and the receipt, the proof of
payment, was set aside, in 19 of 19 September pairs.

Now a re-match keeps the payment receipt over its invoice, except where a
charge already holds a copy: that copy stays kept, because a confirmed
decision names the exact document and swapping it would count both. A month
with a statement keeps its last re-match's choice until it next re-matches; a
month with no statement applies the rule as it is read.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import kept_member, payment_document_kind  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import DUPLICATE_KEPT_KEY  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
ROWS = [
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


def _extraction():
    return ExtractedReceipt(
        date="2026-08-31", total="15.00", currency="USD",
        vendor="Lovable Labs Incorporated", reference="", line_items=(),
        confidence=0.9, notes="", payment_hint=None,
    )


def _wire(monkeypatch):
    mock = MockLLMClient(
        extraction_responses=[_extraction(), _extraction()],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("15.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month_with_the_pair(client, monkeypatch, *, attach=True):
    """Stripe's real order: the invoice arrives first, so it sorts first."""
    _wire(monkeypatch)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "August 2026"})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("Invoice-HMVWDWIL-0029.jpg", JPG + b"1", "application/octet-stream")),
            ("files", ("Receipt-2167-5718.jpg", JPG + b"2", "application/octet-stream")),
        ],
    ))
    if attach:
        wb = Workbook()
        ws = wb.active
        ws.append(list(HEADERS))
        for row in ROWS:
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
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _copies(grid):
    inv = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    rec = next(e for e in grid["expenses"] if "Receipt-" in e["document_id"])
    return inv, rec


def _lovable(run):
    return next(r for r in run["rows"] if r["vendor"] == "LOVABLE")


def test_the_receipt_is_the_real_expense_and_its_invoice_the_copy(client, monkeypatch):
    """The Pressmaster shape: the receipt is kept, matched and counted; the
    invoice is the copy, set aside and out of the total."""
    batch_id = _month_with_the_pair(client, monkeypatch)

    run = _run(client, batch_id)
    row = _lovable(run)
    assert "Receipt-" in row["chosen_document_id"]
    assert run["summary"]["n_reconciled"] == 1
    (aside,) = run["copies_set_aside"]
    assert "Invoice-" in aside["document_id"]

    grid = _grid(client, batch_id)
    inv, rec = _copies(grid)
    assert rec["duplicate"]["is_extra"] is False
    assert rec["duplicate"]["of"] == rec["document_id"]
    assert rec.get("counts_in_total") is not False
    assert inv["duplicate"]["is_extra"] is True
    assert inv["duplicate"]["of"] == rec["document_id"]
    assert inv["counts_in_total"] is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "15.00"}


def test_a_copy_a_charge_already_holds_stays_the_real_expense(client, monkeypatch):
    """A reviewer's confirmed pick names the INVOICE (every month matched
    before this rule looks like this). A re-match keeps the invoice, so the
    decision never points at a set-aside copy and the total counts once."""
    batch_id = _month_with_the_pair(client, monkeypatch)
    tx_id = _lovable(_run(client, batch_id))["transaction_id"]
    invoice_id = _copies(_grid(client, batch_id))[0]["document_id"]
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": tx_id, "document_id": invoice_id},
    )
    assert resp.status_code == 200, resp.text

    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text

    run = _run(client, batch_id)
    assert _lovable(run)["chosen_document_id"] == invoice_id
    (aside,) = run["copies_set_aside"]
    assert "Receipt-" in aside["document_id"]
    assert run["unmatched_receipts"] == []

    grid = _grid(client, batch_id)
    inv, rec = _copies(grid)
    assert inv["duplicate"]["is_extra"] is False
    assert rec["duplicate"]["is_extra"] is True
    assert rec["counts_in_total"] is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "15.00"}, "counted once"


def test_a_statement_month_keeps_its_last_rematch_choice(client, monkeypatch):
    """A month matched before this rule has no stored choice; its page keeps
    the first copy, the one its matches were made against, until the month
    next re-matches. Then the stored choice is the receipt."""
    batch_id = _month_with_the_pair(client, monkeypatch)
    db = Path(client._data_root) / "recon-web.sqlite"
    with RunStore(db) as store:
        run = store.get_run(batch_id)
        snap = dict(run.snapshot)
        assert "Receipt-" in next(iter(snap[DUPLICATE_KEPT_KEY].values()))
        snap.pop(DUPLICATE_KEPT_KEY)
        assert store.update_run_snapshot(batch_id, snap)

    inv, rec = _copies(_grid(client, batch_id))
    assert inv["duplicate"]["is_extra"] is False, "no stored choice: first copy"
    assert rec["duplicate"]["is_extra"] is True

    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text
    inv, rec = _copies(_grid(client, batch_id))
    assert rec["duplicate"]["is_extra"] is False
    assert inv["duplicate"]["is_extra"] is True


def test_a_month_with_no_statement_applies_the_rule_as_it_is_read(client, monkeypatch):
    batch_id = _month_with_the_pair(client, monkeypatch, attach=False)
    grid = _grid(client, batch_id)
    inv, rec = _copies(grid)
    assert rec["duplicate"]["is_extra"] is False
    assert inv["duplicate"]["is_extra"] is True
    assert inv["counts_in_total"] is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "15.00"}


# ── the rule itself ─────────────────────────────────────────────────────


def _r(doc, total="15.00", ccy="USD", **kw):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 9, 23),
        detected_total=Decimal(total) if total is not None else None,
        detected_currency=ccy, detected_vendor="Pressmaster FZCO", **kw,
    )


@pytest.mark.parametrize(
    ("receipts", "held", "kept"),
    [
        # the Pressmaster pair, by file name (the stored months)
        ([_r("0078__Invoice-B2EA98DF-0021.pdf"), _r("0079__Receipt-2179-5147.pdf")],
         set(), "0079__Receipt-2179-5147.pdf"),
        # by the extraction's own numbers (receipts read since 2026-09-16)
        ([_r("0001__a.pdf", invoice_number="B2EA98DF0021"),
          _r("0002__b.pdf", receipt_number="21795147")], set(), "0002__b.pdf"),
        # a charge holds the invoice: it stays kept
        ([_r("0078__Invoice-X.pdf"), _r("0079__Receipt-Y.pdf")],
         {"0078__Invoice-X.pdf"}, "0078__Invoice-X.pdf"),
        # both held: nothing moves
        ([_r("0078__Invoice-X.pdf"), _r("0079__Receipt-Y.pdf")],
         {"0078__Invoice-X.pdf", "0079__Receipt-Y.pdf"}, "0078__Invoice-X.pdf"),
        # two photos of one slip: nothing to prefer
        ([_r("0029__photo-1.jpg"), _r("0030__photo-2.jpg")], set(), "0029__photo-1.jpg"),
        # two receipts: nothing to prefer
        ([_r("0001__Receipt-1.pdf"), _r("0002__Receipt-2.pdf")], set(), "0001__Receipt-1.pdf"),
        # amounts differ: never swap
        ([_r("0078__Invoice-X.pdf", total="135.00"), _r("0079__Receipt-Y.pdf", total="13.50")],
         set(), "0078__Invoice-X.pdf"),
        # an unread amount: never swap
        ([_r("0078__Invoice-X.pdf", total=None), _r("0079__Receipt-Y.pdf", total=None)],
         set(), "0078__Invoice-X.pdf"),
    ],
)
def test_kept_member(receipts, held, kept):
    by_id = {r.document_id: r for r in receipts}
    assert kept_member([r.document_id for r in receipts], by_id, held) == kept


def test_payment_document_kind_reads_numbers_before_names():
    assert payment_document_kind(_r("0001__Invoice-1.pdf", receipt_number="9")) == "receipt"
    assert payment_document_kind(_r("0001__Receipt-1.pdf", invoice_number="9")) == "invoice"
    assert payment_document_kind(_r("0001__rendered-body.pdf")) is None
