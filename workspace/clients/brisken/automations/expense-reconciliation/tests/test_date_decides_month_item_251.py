"""The date decides the month (backlog item 251, owner 2026-10-07).

Owner, verbatim: "the baseline data on the dates that is extracted from
receipts is the foundation for how the receipts get sent to months. So if
user changes date, then the month changes accordingly."

Triggered by notes #114 / #117 (2026-10-07): a second copy of the Parada
slip was read as January on upload (2026-09-23), filed in January, re-read
as 4 July on 2026-09-28, and stayed in January, because item 77 only OFFERED
a move and only on a typed date.

Pinned here through the HTTP routes:

1. A date edit (typed or cleared) that names another calendar month moves
   the receipt there in the same request; `moved` on the reply.
2. Moving back into the month a receipt left brings it back, rather than
   finding its own deleted copy and losing it.
3. A date the drop would not file (a year away, in the future) moves
   nothing, and a published month at either end holds the move.
4. The caller: an edit into a reconciling month settles that month's charge.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0item251-staples-slip"
DOC_ID = "0000__a.jpg"
JANUARY = "January 2026"
FEBRUARY = "February 2026"
APRIL = "April 2026"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(day="2026-01-15"):
    return ExtractedReceipt(
        date=day, total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _month(client, label):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _add(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"


def _rows(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"]


def _put_date(client, batch_id, value, doc_id=DOC_ID):
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc_id}",
        json={"field": "date", "value": value},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _months(client):
    return {
        b["label"]: b for b in client.get("/api/expense-batches").json()["batches"]
    }


def _slip_in(client, monkeypatch, label=JANUARY, day="2026-01-15"):
    """A Staples slip read as `day`, filed in the month `label` names."""
    _wire(monkeypatch, _extraction(day))
    batch = _month(client, label)
    _add(client, batch)
    return batch


# --- 1. the edit moves the receipt --------------------------------------


def test_a_typed_date_in_another_month_moves_the_receipt(client, monkeypatch):
    january = _slip_in(client, monkeypatch)
    reply = _put_date(client, january, "2026-04-15")

    moved = reply["moved"]
    assert moved["label"] == APRIL and moved["month"] == "2026-04"
    assert moved["created_batch"] is True
    assert reply["summary"]["n_expenses"] == 0, "the summary is the month it left"
    assert _rows(client, january) == []

    april = moved["batch_id"]
    assert _months(client)[APRIL]["batch_id"] == april
    (row,) = _rows(client, april)
    assert row["document_id"] == moved["document_id"]
    assert row["date"] == "2026-04-15"
    assert "date" in row["edited_fields"]
    assert "month_move" not in row, "it is home now"
    image = client.get(f"/api/runs/{april}/receipts/{row['document_id']}/image")
    assert image.status_code == 200 and image.content == JPG


def test_a_date_in_the_neighbour_month_moves_too(client, monkeypatch):
    """The window that decides the OFFER is not the rule for an edit: the
    calendar month is, as for every receipt the drop files."""
    january = _slip_in(client, monkeypatch)
    moved = _put_date(client, january, "2026-02-03")["moved"]
    assert moved["label"] == FEBRUARY
    assert _rows(client, january) == []


def test_a_date_inside_the_month_moves_nothing(client, monkeypatch):
    january = _slip_in(client, monkeypatch)
    reply = _put_date(client, january, "2026-01-28")
    assert "moved" not in reply
    (row,) = _rows(client, january)
    assert row["date"] == "2026-01-28"
    assert APRIL not in _months(client)


def test_clearing_a_typed_date_files_it_by_the_reading(client, monkeypatch):
    """The reading (January) is the baseline; the typed April date put it in
    April; clearing the typed date hands the decision back to the reading."""
    january = _slip_in(client, monkeypatch)
    moved = _put_date(client, january, "2026-04-15")["moved"]
    back = _put_date(client, moved["batch_id"], "", doc_id=moved["document_id"])
    assert back["moved"]["batch_id"] == january
    assert _rows(client, moved["batch_id"]) == []
    (row,) = _rows(client, january)
    assert row["date"] == "2026-01-15"


# --- 2. moving back into the month a receipt left ------------------------


def test_correcting_a_wrong_date_brings_the_receipt_back(client, monkeypatch):
    """Item 77's same-bytes check found the receipt's own soft-deleted copy in
    January and kept that dead row: the receipt vanished from both months."""
    january = _slip_in(client, monkeypatch)
    moved = _put_date(client, january, "2026-04-15")["moved"]
    back = _put_date(
        client, moved["batch_id"], "2026-01-20", doc_id=moved["document_id"],
    )["moved"]
    assert back["batch_id"] == january
    assert back["already_in_batch"] is False
    (row,) = _rows(client, january)
    assert row["document_id"] == back["document_id"]
    assert row["date"] == "2026-01-20"
    assert _rows(client, moved["batch_id"]) == []
    image = client.get(f"/api/runs/{january}/receipts/{row['document_id']}/image")
    assert image.status_code == 200 and image.content == JPG


# --- 3. dates that do not route, months that hold ------------------------


def test_a_date_a_year_away_moves_nothing(client, monkeypatch):
    january = _slip_in(client, monkeypatch)
    reply = _put_date(client, january, "2024-06-01")
    assert "moved" not in reply
    (row,) = _rows(client, january)
    assert row["date"] == "2024-06-01"
    assert "month_move" not in row
    assert set(_months(client)) == {JANUARY}


def test_a_future_date_moves_nothing(client, monkeypatch):
    today = datetime.now(timezone.utc).date()
    label = f"{calendar.month_name[today.month]} {today.year}"
    batch = _slip_in(client, monkeypatch, label=label, day=today.isoformat())
    later = today + timedelta(days=45)
    reply = _put_date(client, batch, later.isoformat())
    assert "moved" not in reply
    (row,) = _rows(client, batch)
    assert row["date"] == later.isoformat()
    assert set(_months(client)) == {label}


def test_a_day_month_swap_is_held_not_moved(client, monkeypatch):
    """Owner 2026-10-07: July's NORMANDIE SEINE toll (file 2026-07-05) was
    typed as 2026-05-07. Read day-first it is 5 July, this month, so the
    typed date is kept and the move waits for a click."""
    july = _slip_in(client, monkeypatch, label="July 2026", day="2026-07-05")
    reply = _put_date(client, july, "2026-05-07")
    assert "moved" not in reply
    assert reply["move_held"] == {
        "held": "day_month_swap", "month": "2026-05", "label": "May 2026",
        "date": "2026-05-07", "swap": "2026-07-05",
    }
    (row,) = _rows(client, july)
    assert row["date"] == "2026-05-07"
    assert row["month_move"] == {"month": "2026-05", "label": "May 2026"}
    assert set(_months(client)) == {"July 2026"}


def test_a_held_swap_in_the_neighbour_month_still_offers_the_move(
    client, monkeypatch
):
    """2026-08-07 typed in July (swap = 8 July) sits inside the item-25
    window, where a READ date gets no offer; a typed one still here was held,
    so it keeps its one click."""
    july = _slip_in(client, monkeypatch, label="July 2026", day="2026-07-08")
    reply = _put_date(client, july, "2026-08-07")
    assert reply["move_held"]["held"] == "day_month_swap"
    (row,) = _rows(client, july)
    assert row["month_move"]["month"] == "2026-08"


def test_a_day_past_twelve_has_no_swap_and_moves(client, monkeypatch):
    july = _slip_in(client, monkeypatch, label="July 2026", day="2026-07-05")
    assert _put_date(client, july, "2026-05-13")["moved"]["label"] == "May 2026"


def test_a_swap_into_a_third_month_moves(client, monkeypatch):
    """2026-06-03 swaps to 6 March, which is not July either: moved as typed."""
    july = _slip_in(client, monkeypatch, label="July 2026", day="2026-07-05")
    assert _put_date(client, july, "2026-06-03")["moved"]["label"] == "June 2026"


def test_a_published_month_holds_the_move(client, monkeypatch):
    january = _slip_in(client, monkeypatch)
    april = _month(client, APRIL)
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        store.set_run_published(april, True, "2026-10-07T00:00:00+00:00")
    reply = _put_date(client, january, "2026-04-15")
    assert "moved" not in reply
    assert reply["move_held"]["held"] == "month_published"
    assert reply["move_held"]["batch_id"] == april
    (row,) = _rows(client, january)
    assert row["date"] == "2026-04-15"
    assert row["month_move"]["batch_id"] == april, "the offer stays on the row"
    assert _rows(client, april) == []


# --- 4. the caller: a reconciling month re-matches on arrival ------------


def test_an_edit_into_a_reconciling_month_settles_its_charge(client, monkeypatch):
    january = _slip_in(client, monkeypatch)
    april = _month(client, APRIL)
    resp = client.post(
        f"/api/expense-batches/{april}/statement",
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
    if resp.json().get("job_id"):
        job = client.get(f"/jobs/{resp.json()['job_id']}").json()
        assert job["status"] == "done"

    def staples():
        return next(
            r for r in client.get(f"/api/runs/{april}").json()["rows"]
            if "STAPLES" in r["vendor"]
        )

    assert not staples().get("chosen_document_id")
    moved = _put_date(client, january, "2026-04-15")["moved"]
    assert moved["batch_id"] == april
    assert staples()["chosen_document_id"] == moved["document_id"]
