"""A decided copy leaves the month's listing and totals everywhere (backlog
item 94, owner ruling 2026-09-17).

Stripe-style vendors mail an invoice and a receipt for one charge. Since
items 56/74/83 the tool decides the second document is a copy and keeps it
out of the matching pool, yet the month report, the CSV, the cost-center
roll-up and the grid's totals still listed and summed both: August 2026
printed about 23 percent too much. One predicate (`decided_copies`) now
decides which documents do not count, and every surface reads it:

* the grid keeps the copy's row (marker and "Not a copy" undo included) but
  leaves it out of `n_expenses` and `totals_by_ccy`;
* the copy is in no Expenses box (item 84's `expenses[].boxes`), to-do boxes
  included, so every box count leaves it out and `n_categorized` +
  `n_uncategorized` == `n_expenses` (live August 2026 read EXPENSES 20 beside
  CATEGORIZED 23 + NEEDS CATEGORY 2);
* the months list counts the same expenses, and categorizes the same ones;
* the CSV writes no row for it and states it on one line under the rows;
* the month report PDF leaves it out of the listing and the header total,
  names it under the listing, and keeps its pages behind the original's;
* `GET /api/cost-centers/totals` leaves it out of every bucket and reports
  it as `copies_set_aside`.

"Not a copy" brings the document back on all of them, and so does a
reviewer hand-matching the copy to a charge of its own (the run payload
then renders it as that match, not as a copy set aside).

Route-level through the FastAPI app, the way `test_duplicate_collapse.py`
drives item 56.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import EXPENSE_BOXES  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
FILES = ["Invoice-HMVWDWIL.jpg", "Receipt-2167-5718.jpg", "train.jpg"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor, total, day, currency="USD"):
    return ExtractedReceipt(
        date=day, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch):
    """The August shape in miniature: the Lovable 15.00 invoice and its
    receipt (one purchase, two documents), plus one ordinary EUR expense so
    the totals carry two currencies and only one of them holds a copy."""
    mock = MockLLMClient(
        extraction_responses=[
            _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31"),
            _extraction("Lovable Labs Incorporated", "15.00", "2026-08-31"),
            _extraction("Petit Train Touristique de Colmar", "32.00",
                        "2026-08-23", currency="EUR"),
        ],
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


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _batch(client):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + str(i).encode(), "application/octet-stream"))
            for i, name in enumerate(FILES)
        ],
    ))
    return batch_id


def _attach(client, batch_id, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(list(CHASE_HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("August2026.xlsx", buf.getvalue(), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    return _done(client, resp)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _surfaces(client, batch_id) -> dict:
    """What every listing surface says about the month, read over HTTP."""
    grid = client.get(f"/api/expense-batches/{batch_id}")
    assert grid.status_code == 200, grid.text
    grid = grid.json()

    months = client.get("/api/expense-batches")
    assert months.status_code == 200, months.text
    (listed,) = [
        b for b in months.json()["batches"] if b["batch_id"] == batch_id
    ]

    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    lines = list(csv.reader(io.StringIO(resp.text)))
    header, body = lines[0], [line for line in lines[1:] if line]
    data_rows = [dict(zip(header, line)) for line in body if len(line) > 1]
    footer = [line[0] for line in body if len(line) == 1]

    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    reader = PdfReader(io.BytesIO(resp.content))
    listing = _norm(reader.pages[0].extract_text() or "")
    pdf_text = _norm("\n".join(p.extract_text() or "" for p in reader.pages))

    resp = client.get("/api/cost-centers/totals")
    assert resp.status_code == 200, resp.text
    roll_up = resp.json()

    return {
        "grid": grid,
        "rows": {e["document_id"]: e for e in grid["expenses"]},
        "months_n_expenses": listed["summary"]["n_expenses"],
        "months_summary": listed["summary"],
        "csv_rows": data_rows,
        "csv_footer": footer,
        "listing": listing,
        "pdf_text": pdf_text,
        "roll_up": roll_up,
    }


def _copy_id(grid) -> str:
    (copy,) = [
        e["document_id"] for e in grid["expenses"]
        if (e.get("duplicate") or {}).get("is_extra")
    ]
    return copy


def _assert_boxes_reconcile(s: dict, n_expenses: int) -> None:
    """Item 84's rule, which item 94 must keep: every box count on the grid
    is the rows carrying that box, and Categorized + Needs category are
    exactly the expenses the month counts. The months list categorizes the
    same expenses the batch page does."""
    summary, rows = s["grid"]["summary"], s["grid"]["expenses"]
    for box in EXPENSE_BOXES:
        if f"n_{box}" in summary:
            assert summary[f"n_{box}"] == sum(
                1 for e in rows if box in e["boxes"]
            ), box
    assert summary["n_expenses"] == n_expenses
    assert summary["n_categorized"] + summary["n_uncategorized"] == n_expenses
    months = s["months_summary"]
    assert months["n_categorized"] + months["n_uncategorized"] == n_expenses
    assert (months["n_categorized"], months["n_uncategorized"]) == (
        summary["n_categorized"], summary["n_uncategorized"],
    )


def _assert_copy_set_aside(s: dict, copy_id: str) -> None:
    grid, summary = s["grid"], s["grid"]["summary"]
    # Boxes: the copy is in none, to-dos included, and every counted row is
    # in Categorized or Needs category, so each box count leaves it out.
    assert s["rows"][copy_id]["boxes"] == []
    assert all(
        ("categorized" in e["boxes"]) != ("uncategorized" in e["boxes"])
        for d, e in s["rows"].items() if d != copy_id
    )
    _assert_boxes_reconcile(s, 2)
    # Grid: the row stays, marker and all, and leaves the count and totals.
    assert copy_id in s["rows"]
    assert s["rows"][copy_id]["duplicate"]["is_extra"] is True
    assert s["rows"][copy_id]["counts_in_total"] is False
    assert all(
        "counts_in_total" not in e
        for d, e in s["rows"].items() if d != copy_id
    )
    assert summary["n_expenses"] == 2
    assert summary["n_receipts"] == 3
    assert summary["n_copies_set_aside"] == 1
    assert summary["totals_by_ccy"] == {"EUR": "32.00", "USD": "15.00"}
    assert summary["copies_set_aside_by_ccy"] == {"USD": "15.00"}
    assert len(grid["expenses"]) == 3
    # Months list: the same count as the batch page.
    assert s["months_n_expenses"] == 2
    # CSV: no row for the copy, one line under the rows saying what it is.
    assert len(s["csv_rows"]) == 2
    assert sorted(r["Expense Amount"] for r in s["csv_rows"]) == ["15.00", "32.00"]
    (footer,) = s["csv_footer"]
    assert footer.startswith("Copies set aside, not counted above: 1 document")
    assert "(USD 15.00)" in footer
    assert "Lovable Labs Incorporated 2026-08-31 USD 15.00" in footer
    # PDF: two listed expenses, the header total without the copy, the
    # set-aside line naming the expense it repeats, and its pages captioned
    # as the copy.
    assert "2 expenses · EUR 32.00 · USD 15.00" in s["listing"]
    # Item 138: a month sectioned per card states its copies after the last
    # card's receipt pages, so the line is read off the whole document.
    assert "Copies set aside: 1 document repeats an expense listed above" in s["pdf_text"]
    assert "(USD 15.00)" in s["pdf_text"]
    lovable_no = next(
        n for n in (1, 2)
        if f"Expense {n} · Lovable" in s["pdf_text"]
    )
    assert f"copy of expense {lovable_no}" in s["pdf_text"]
    assert f"Expense {lovable_no} (copy set aside) · Lovable" in s["pdf_text"]
    # Cost centers: out of every bucket, on its own line.
    roll_up = s["roll_up"]
    assert roll_up["n_rows"] == 2
    assert roll_up["unassigned"]["n_rows"] == 2
    assert roll_up["unassigned"]["totals"] == {"EUR": "32.00", "USD": "15.00"}
    assert roll_up["copies_set_aside"] == {
        "n_rows": 1, "n_batches": 1, "totals": {"USD": "15.00"},
    }


def _assert_copy_counts(s: dict) -> None:
    summary = s["grid"]["summary"]
    assert all("counts_in_total" not in e for e in s["rows"].values())
    # Boxes: the document is back in every box it qualifies for.
    assert all(
        ("categorized" in e["boxes"]) != ("uncategorized" in e["boxes"])
        for e in s["rows"].values()
    )
    _assert_boxes_reconcile(s, 3)
    assert summary["n_expenses"] == 3
    assert summary["n_receipts"] == 3
    assert summary["n_copies_set_aside"] == 0
    assert summary["totals_by_ccy"] == {"EUR": "32.00", "USD": "30.00"}
    assert summary["copies_set_aside_by_ccy"] == {}
    assert s["months_n_expenses"] == 3
    assert len(s["csv_rows"]) == 3
    assert s["csv_footer"] == []
    assert "3 expenses · EUR 32.00 · USD 30.00" in s["listing"]
    assert "Copies set aside" not in s["pdf_text"]
    assert "(copy set aside)" not in s["pdf_text"]
    assert s["roll_up"]["n_rows"] == 3
    assert s["roll_up"]["unassigned"]["totals"] == {"EUR": "32.00", "USD": "30.00"}
    assert s["roll_up"]["copies_set_aside"] == {
        "n_rows": 0, "n_batches": 0, "totals": {},
    }


# ── a collecting month: the tool decides, the reviewer undoes ───────────


def test_a_decided_copy_leaves_every_listing_and_total(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    s = _surfaces(client, batch_id)
    (group,) = s["grid"]["duplicate_groups"]
    assert group["verdict"] == "copy" and group["decided_by"] == "tool"
    _assert_copy_set_aside(s, _copy_id(s["grid"]))
    # A to-do box leaves with the copy too. No row has a person yet, and
    # only the two expenses that count ask for one.
    summary = s["grid"]["summary"]
    assert summary["n_uncategorized"] == 2
    assert summary["n_needs_person"] == 2
    assert summary["n_needs_company_or_person"] == 2


def test_not_a_copy_brings_the_document_back_everywhere(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    copy_id = _copy_id(grid)
    assert grid["summary"]["n_needs_company_or_person"] == 2
    (group,) = grid["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    # The reply is the grid's own summary, and it already counts the copy.
    assert resp.json()["summary"]["n_expenses"] == 3

    s = _surfaces(client, batch_id)
    _assert_copy_counts(s)
    # Back in the boxes it qualifies for, the to-do ones included.
    assert s["rows"][copy_id]["boxes"] == [
        "uncategorized", "needs_person", "needs_company_or_person",
    ]
    assert s["grid"]["summary"]["n_needs_company_or_person"] == 3


# ── a reconciling month: the same set the run payload sets aside ────────


def test_a_reconciling_month_agrees_with_the_run_payload(client, monkeypatch):
    """The copy the matching view lists under `copies_set_aside` is exactly
    the one every listing leaves out. A reviewer who hand-matches that copy
    to a charge of its own makes it real spend again: it leaves
    `copies_set_aside` and counts on every surface."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, [
        (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
        (datetime(2026, 8, 30), "LOVABLE SEAT", "Sale", -16.00),
        (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
    ])
    view = client.get(f"/api/runs/{batch_id}").json()
    (set_aside,) = view["copies_set_aside"]
    s = _surfaces(client, batch_id)
    assert set_aside["document_id"] == _copy_id(s["grid"])
    _assert_copy_set_aside(s, set_aside["document_id"])

    seat = next(r for r in view["rows"] if r["vendor"] == "LOVABLE SEAT")
    resp = client.post(f"/api/runs/{batch_id}/decisions", json={
        "transaction_id": seat["transaction_id"],
        "status": "confirmed",
        "chosen_document_id": set_aside["document_id"],
    })
    assert resp.status_code == 200, resp.text

    view = client.get(f"/api/runs/{batch_id}").json()
    assert view["copies_set_aside"] == []
    _assert_copy_counts(_surfaces(client, batch_id))
