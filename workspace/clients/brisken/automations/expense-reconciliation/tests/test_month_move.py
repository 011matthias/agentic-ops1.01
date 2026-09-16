"""A corrected date moves the receipt to its month (backlog item 77, note #34).

Criss, 2026-09-10, on batch `4ceaeb461386`: "A leitura da data está errada."
A Mercado Pago slip printing 04/07/26 was read as a January date, so the drop
created a "January 2026" month and filed it there. She corrected the date to
July; the receipt stayed in January, because a typed date is believed and
nothing else looks at where the row lives.

Pinned here through the HTTP routes:

1. A reviewer-typed date outside the batch's window offers the move
   (`expenses[].month_move`, `summary.n_month_moves`); a machine reading
   outside the window stays item 25's `date_outside_period` question, and a
   typed date inside the window offers nothing.
2. `POST .../expenses/{id}/move` files the receipt into its month, creating
   the month when it does not exist, carrying the reading, the file and the
   edits, and leaving the source row as a soft delete.
3. Moving into a month that is reconciling re-matches it (the caller-level
   test: the moved receipt settles the statement charge).
4. The amendment fields (`time`, `invoice_number`, `receipt_number`) reach the
   grid, absent rather than null when not read.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    MockLLMClient,
    _extraction_from_payload,
)
from expense_recon.web.app import create_app  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0item77-staples-slip"
DOC_ID = "0000__a.jpg"
JANUARY = "January 2026"
APRIL = "April 2026"
OFFICE = "Office Supplies & Consumables"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(day="2026-01-15", vendor="Staples", total="42.50", **extra):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="", **extra,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _month(client, label):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _add(client, batch_id, name="a.jpg", data=JPG):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, data, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _view(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _expense(client, batch_id, doc_id=DOC_ID):
    return next(
        (e for e in _view(client, batch_id)["expenses"]
         if e["document_id"] == doc_id),
        None,
    )


def _put(client, batch_id, field, value, doc_id=DOC_ID):
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}",
        json={"field": field, "value": value},
    )
    assert resp.status_code == 200, resp.text


def _move(client, batch_id, doc_id=DOC_ID, month=None):
    body = {"month": month} if month else None
    return client.post(f"/api/runs/{batch_id}/expenses/{doc_id}/move", json=body)


def _attach_statement(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json().get("job_id")
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"


def _misfiled_january(client, monkeypatch, *more, **extra):
    """A Staples slip read as 15 January, filed in January."""
    _wire(monkeypatch, _extraction(**extra), *more)
    january = _month(client, JANUARY)
    _add(client, january)
    return january


# --- 1. the offer -------------------------------------------------------


def test_a_typed_date_in_another_month_offers_the_move(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    row = _expense(client, january)
    assert "month_move" not in row
    assert _view(client, january)["summary"]["n_month_moves"] == 0

    _put(client, january, "date", "2026-04-15")
    row = _expense(client, january)
    assert row["month_move"] == {"month": "2026-04", "label": APRIL}
    assert _view(client, january)["summary"]["n_month_moves"] == 1
    # The typed date is still believed: the offer is not a review state.
    assert row["review"].get("reason_code") != "date_outside_period"


def test_a_typed_date_inside_the_window_offers_nothing(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    _put(client, january, "date", "2026-02-03")  # a neighbour month
    assert "month_move" not in _expense(client, january)
    assert _view(client, january)["summary"]["n_month_moves"] == 0


def test_a_machine_reading_outside_the_window_is_flagged_not_moved(
    client, monkeypatch
):
    january = _misfiled_january(client, monkeypatch, day="2026-04-15")
    row = _expense(client, january)
    assert "month_move" not in row
    assert row["review"]["reason_code"] == "date_outside_period"


def test_the_offer_names_the_month_it_would_join(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    april = _month(client, APRIL)
    _put(client, january, "date", "2026-04-15")
    assert _expense(client, january)["month_move"] == {
        "month": "2026-04", "label": APRIL, "batch_id": april,
    }


# --- 2. the move --------------------------------------------------------


def test_the_move_creates_the_month_and_carries_the_receipt(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch, time="23:56")
    _put(client, january, "date", "2026-04-15")
    _put(client, january, "vendor", "Staples Inc")
    _put(client, january, "category", OFFICE)

    resp = _move(client, january)
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["created_batch"] is True
    assert out["already_in_batch"] is False
    assert out["label"] == APRIL and out["month"] == "2026-04"
    assert out["source"] == {"batch_id": january, "n_expenses": 0}
    assert out["summary"]["n_expenses"] == 0

    april = out["batch_id"]
    moved = _expense(client, april, out["document_id"])
    assert moved is not None
    assert moved["date"] == "2026-04-15"
    assert "date" in moved["edited_fields"]
    assert moved["vendor"]["display"] == "Staples Inc"
    assert moved["posting_category"]["category"] == OFFICE
    assert moved["time"] == "23:56"
    assert "month_move" not in moved  # it is home now
    image = client.get(
        f"/api/runs/{april}/receipts/{out['document_id']}/image"
    )
    assert image.status_code == 200
    assert image.content == JPG

    assert _view(client, january)["expenses"] == []
    months = {
        b["batch_id"]: b for b in client.get("/api/expense-batches").json()["batches"]
    }
    assert months[april]["label"] == APRIL
    assert months[april]["created_by"] == "move"

    # Gone from January: no offer to take up, and a named month is refused.
    assert _move(client, january).status_code == 404
    again = _move(client, january, month="2026-04")
    assert again.status_code == 400
    assert "already removed" in again.json()["error"]


def test_the_move_joins_an_existing_month(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    april = _month(client, APRIL)
    _put(client, january, "date", "2026-04-15")

    out = _move(client, january).json()
    assert out["created_batch"] is False
    assert out["batch_id"] == april
    assert _view(client, april)["summary"]["n_expenses"] == 1
    assert len([
        b for b in client.get("/api/expense-batches").json()["batches"]
        if b["label"] == APRIL
    ]) == 1


def test_identical_bytes_already_in_the_month_are_not_added_twice(
    client, monkeypatch
):
    _wire(monkeypatch, _extraction(day="2026-04-15"), _extraction())
    april = _month(client, APRIL)
    _add(client, april)
    january = _month(client, JANUARY)
    _add(client, january)
    _put(client, january, "date", "2026-04-15")

    out = _move(client, january).json()
    assert out["already_in_batch"] is True
    assert out["document_id"] == DOC_ID
    assert _view(client, april)["summary"]["n_expenses"] == 1
    assert _view(client, january)["expenses"] == []


def test_a_typed_in_expense_moves_too(client, monkeypatch):
    _wire(monkeypatch)
    january = _month(client, JANUARY)
    added = client.post(
        f"/api/runs/{january}/expenses",
        json={"vendor": "Taxi Rio", "total": "80.00", "currency": "BRL",
              "date": "2026-04-20"},
    )
    assert added.status_code == 200, added.text
    doc = added.json()["document_id"]
    assert _expense(client, january, doc)["month_move"]["month"] == "2026-04"

    out = _move(client, january, doc).json()
    assert out["document_id"].startswith("manual:")
    moved = _expense(client, out["batch_id"], out["document_id"])
    assert moved["vendor"]["display"] == "Taxi Rio"
    assert moved["total"] == "80.00"
    assert _view(client, january)["expenses"] == []


def test_a_row_without_an_offer_needs_a_named_month(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    resp = _move(client, january)
    assert resp.status_code == 400
    assert "name a month" in resp.json()["error"]
    assert _move(client, january, month="2026-13").status_code == 400
    assert _move(client, january, month="2026-01").status_code == 400
    assert _move(client, january, "0099__nope.jpg", month="2026-04").status_code == 404


# --- 3. the caller: a reconciling month re-matches on arrival ------------


def test_moving_into_a_reconciling_month_settles_its_charge(client, monkeypatch):
    january = _misfiled_january(client, monkeypatch)
    april = _month(client, APRIL)
    _attach_statement(client, april)
    staples = next(
        r for r in client.get(f"/api/runs/{april}").json()["rows"]
        if "STAPLES" in r["vendor"]
    )
    assert not staples.get("chosen_document_id")

    _put(client, january, "date", "2026-04-15")
    out = _move(client, january).json()
    assert out["batch_id"] == april
    assert "rematch" in out
    staples = next(
        r for r in client.get(f"/api/runs/{april}").json()["rows"]
        if "STAPLES" in r["vendor"]
    )
    assert staples["chosen_document_id"] == out["document_id"]


# --- 4. the amendment fields ---------------------------------------------


def test_time_and_document_numbers_reach_the_grid_absent_when_unread(
    client, monkeypatch
):
    _wire(
        monkeypatch,
        _extraction(time="23:56", invoice_number="HMVWDWIL-0029"),
        _extraction(vendor="Uber", total="12.00"),
    )
    january = _month(client, JANUARY)
    _add(client, january)
    _add(client, january, name="b.jpg", data=JPG + b"-second")
    rows = {e["document_id"]: e for e in _view(client, january)["expenses"]}
    first, second = rows[DOC_ID], rows["0001__b.jpg"]
    assert first["time"] == "23:56"
    assert first["invoice_number"] == "HMVWDWIL-0029"
    assert "receipt_number" not in first
    for key in ("time", "invoice_number", "receipt_number"):
        assert key not in second


def test_a_time_that_is_not_a_clock_time_is_not_stored():
    def read(value):
        return _extraction_from_payload({"time": value}).time

    assert read("23:56") == "23:56"
    assert read("9:05") == "09:05"
    assert read("23:56:10") == "23:56"
    assert read("24:30") is None
    assert read("2026-07-04") is None
    assert read(None) is None
