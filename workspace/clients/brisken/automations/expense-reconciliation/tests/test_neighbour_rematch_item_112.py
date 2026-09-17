"""A receipt arriving re-matches the neighbouring month it belongs to (item 112).

Since item 61 a month borrows the neighbouring months' receipts whose dates
fall inside its own statement period, but only when that month re-matches.
A receipt dated 07-31 that lands in July after August's last re-match sat
in July until something unrelated re-matched August, while a receipt joining
a trip already re-matched every month the trip spans.

Pinned through the HTTP routes:

1. An arrival in July dated inside August's statement period re-matches
   August (`rematch_log` trigger `adjacent_receipts`), and August's payload
   then shows the pairing, named as an adjacent borrow.
2. A receipt outside August's period re-matches nothing (the differential
   probe: one date moves, the answer moves).
3. A receipt joining a trip re-matches the month through the trip trigger
   alone, even when the trip's name reads as a month.
4. A neighbour re-match that fails (inside the match, or the entry point
   itself) leaves the add done and the debt recorded on the neighbour (item
   113's mark), and the next boot pays it.
5. A restart between the arrival and the neighbour's turn loses nothing: the
   debt was written with the arrival.
6. A month move into July re-matches August too.
"""
from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0item112-bytes"


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
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("71.64"),
                reasoning="same purchase",
            )
        ] * 40,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _receipt(vendor: str, total: str, date: str) -> ExtractedReceipt:
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


def _add(client, batch_id: str, name: str, body: bytes = b""):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, JPG + body, "application/octet-stream"))],
    ))


def _month(client, label: str, *, fname: str) -> str:
    """A company month created empty, with one receipt through the add route."""
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _add(client, batch_id, fname, fname.encode())
    return batch_id


def _csv(*rows: tuple[str, str, str]) -> bytes:
    body = "".join(f"{d},{a},{v}\n" for d, a, v in rows)
    return ("Date,Amount,Vendor\n" + body).encode()


def _attach(client, batch_id: str, body: bytes):
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.csv", body, "application/octet-stream",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
        },
    ))


# August's statement opens on 07-31, as Chase cuts it live; its 08-01 Google
# charge is the one whose receipt is printed the day before.
AUGUST_CSV = _csv(
    ("07/31/2026", "80.28", "OPENAI"),
    ("08/01/2026", "71.64", "GOOGLE WORKSPACE"),
    ("08/15/2026", "25.00", "LOVABLE"),
)


def _doc_named(client, batch_id: str, name: str) -> str:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        receipts = (store.get_run(batch_id).snapshot or {})["receipts"]
    return next(r["document_id"] for r in receipts if r.get("receipt_name") == name)


def _google_row(client, batch_id: str) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json()["rows"] if r["vendor"] == "GOOGLE WORKSPACE")


def _triggers(client, batch_id: str) -> list[str]:
    resp = client.get("/api/operator/state")
    assert resp.status_code == 200, resp.text
    return [e["trigger"] for e in resp.json()["rematches"] if e["run_id"] == batch_id]


def _owed(client, batch_id: str) -> list[dict]:
    resp = client.get("/api/operator/state")
    assert resp.status_code == 200, resp.text
    return [m for m in resp.json()["rematch_pending"] if m["run_id"] == batch_id]


def _july_and_august(client, monkeypatch, late_date: str) -> tuple[str, str]:
    """July (no statement) and August (statement attached), then the Google
    receipt printed on `late_date` still to come."""
    _wire(
        monkeypatch,
        _receipt("Stripe", "10.00", "2026-07-10"),
        _receipt("Lovable", "25.00", "2026-08-15"),
        _receipt("Google", "71.64", late_date),
    )
    july = _month(client, "July 2026", fname="jul.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    _attach(client, august, AUGUST_CSV)
    assert _google_row(client, august)["effective_bucket"] == "unmatched"
    assert _triggers(client, august) == ["statement"]
    return july, august


def _wait_owed_cleared(rebooted, batch_id: str) -> None:
    deadline = time.monotonic() + 20
    while _owed(rebooted, batch_id) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert _owed(rebooted, batch_id) == []


# ── the arrival ──────────────────────────────────────────────────────


def test_a_receipt_added_to_july_rematches_august_which_pairs_it(
    client, monkeypatch
):
    july, august = _july_and_august(client, monkeypatch, "2026-07-31")

    _add(client, july, "google.jpg", b"google")
    late = _doc_named(client, july, "google.jpg")

    assert _triggers(client, august) == ["statement", "adjacent_receipts"], (
        "July's arrival never re-matched August"
    )
    row = _google_row(client, august)
    assert row["chosen_document_id"] == late
    assert row["settled_by"] == {
        "run_id": july, "label": "July 2026", "kind": "adjacent",
    }
    assert _owed(client, august) == []
    # July has no statement: it re-matched nothing and owes nothing.
    assert _triggers(client, july) == []
    assert _owed(client, july) == []
    # July's own grid names the month that took the receipt.
    grid = client.get(f"/api/expense-batches/{july}").json()
    exp = next(e for e in grid["expenses"] if e["document_id"] == late)
    assert exp["settled_by"]["run_id"] == august


def test_a_receipt_dropped_on_the_receipts_page_rematches_august_too(
    client, monkeypatch
):
    """The drop entrance files into July through the same arrival, so it owes
    and pays August the same way (the mail intake shares that path too)."""
    _wire(
        monkeypatch,
        _receipt("Stripe", "10.00", "2026-07-10"),
        _receipt("Lovable", "25.00", "2026-08-15"),
        # A drop reads a file for routing and again for the month's ingest.
        _receipt("Google", "71.64", "2026-07-31"),
        _receipt("Google", "71.64", "2026-07-31"),
    )
    july = _month(client, "July 2026", fname="jul.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    _attach(client, august, AUGUST_CSV)

    resp = client.post(
        "/api/receipts",
        files=[("files", ("google.jpg", JPG + b"google", "application/octet-stream"))],
        data={"month": "2026-07"},
    )
    job = _done(client, resp)

    assert job["result"]["months"][0]["batch_id"] == july
    assert _triggers(client, august) == ["statement", "adjacent_receipts"]
    assert _google_row(client, august)["chosen_document_id"] == _doc_named(
        client, july, "google.jpg"
    )


def test_a_receipt_outside_the_neighbours_period_rematches_nothing(
    client, monkeypatch
):
    july, august = _july_and_august(client, monkeypatch, "2026-07-20")

    _add(client, july, "google.jpg", b"google")

    assert _triggers(client, august) == ["statement"]
    assert _owed(client, august) == []
    assert _google_row(client, august)["effective_bucket"] == "unmatched"
    grid = client.get(f"/api/expense-batches/{july}").json()
    assert grid["summary"]["n_receipts"] == 2


def test_a_trip_receipt_rematches_the_month_through_the_trip_trigger_only(
    client, monkeypatch
):
    """A trip batch named like a month ("TEST - July 2026 Rome" reads as July)
    is still a trip: its receipt re-matches August once, as `trip`."""
    _wire(
        monkeypatch,
        _receipt("Lovable", "25.00", "2026-08-15"),
        _receipt("Taxi", "30.00", "2026-07-26"),
        _receipt("Google", "71.64", "2026-07-31"),
    )
    august = _month(client, "August 2026", fname="aug.jpg")
    _attach(client, august, AUGUST_CSV)
    trip = client.post("/api/trips", json={
        "name": "TEST - July 2026 Rome", "start": "2026-07-25",
        "end": "2026-08-05", "travelers": ["Dirk"],
    })
    assert trip.status_code == 200, trip.text
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("taxi.jpg", JPG + b"taxi", "application/octet-stream"))],
        data={
            "legal_entity": "Corporate Services", "label": "",
            "batch_type": "trip", "trip_id": trip.json()["trip_id"],
        },
    )
    _done(client, resp)
    trip_batch = resp.json()["batch_id"]
    assert _triggers(client, august) == ["statement", "trip"]

    _add(client, trip_batch, "google.jpg", b"google")

    assert _triggers(client, august) == ["statement", "trip", "trip"]
    row = _google_row(client, august)
    assert row["chosen_document_id"] == _doc_named(client, trip_batch, "google.jpg")
    assert row["settled_by"]["run_id"] == trip_batch


# ── a failure is recorded, and paid ──────────────────────────────────


def test_a_neighbour_rematch_error_leaves_the_add_done_and_the_debt_recorded(
    client, monkeypatch, tmp_path
):
    july, august = _july_and_august(client, monkeypatch, "2026-07-31")

    from expense_recon.web import service
    real = service.rematch_month

    def _august_down(store, run, *a, **k):
        if run.run_id == august:
            raise RuntimeError("model outage")
        return real(store, run, *a, **k)

    monkeypatch.setattr(service, "rematch_month", _august_down)
    _add(client, july, "google.jpg", b"google")  # the job reads done
    late = _doc_named(client, july, "google.jpg")

    grid = client.get(f"/api/expense-batches/{july}").json()
    assert late in {e["document_id"] for e in grid["expenses"]}
    owed = _owed(client, august)
    assert len(owed) == 1, owed
    assert owed[0]["trigger"] == "adjacent_receipts"
    assert "model outage" in owed[0]["error"]
    assert owed[0]["attempts"] == 1
    assert _triggers(client, august) == ["statement"]

    monkeypatch.setattr(service, "rematch_month", real)
    with TestClient(create_app(tmp_path)) as rebooted:
        _wait_owed_cleared(rebooted, august)
        assert _triggers(rebooted, august) == ["statement", "resume"]
        assert _google_row(rebooted, august)["chosen_document_id"] == late


def test_a_neighbour_rematch_that_raises_outright_is_recorded_too(
    client, monkeypatch
):
    """The entry point itself raising (not the match inside it) still never
    fails the add, and still lands on August's mark."""
    july, august = _july_and_august(client, monkeypatch, "2026-07-31")

    from expense_recon.web import service
    real = service.rematch_after_change

    def _august_raises(store, run_id, *a, **k):
        if run_id == august:
            raise OSError("database is locked")
        return real(store, run_id, *a, **k)

    monkeypatch.setattr(service, "rematch_after_change", _august_raises)
    _add(client, july, "google.jpg", b"google")

    owed = _owed(client, august)
    assert len(owed) == 1, owed
    assert owed[0]["trigger"] == "adjacent_receipts"
    assert "database is locked" in owed[0]["error"]


def test_a_restart_before_the_neighbours_turn_keeps_its_debt(
    client, monkeypatch, tmp_path
):
    july, august = _july_and_august(client, monkeypatch, "2026-07-31")

    from expense_recon.web import service
    real = service.rematch_neighbour_months

    # The machine stops after July's receipt is stored, before August's turn.
    monkeypatch.setattr(service, "rematch_neighbour_months", lambda *a, **k: [])
    _add(client, july, "google.jpg", b"google")
    late = _doc_named(client, july, "google.jpg")
    owed = _owed(client, august)
    assert len(owed) == 1 and "error" not in owed[0], owed
    assert owed[0]["trigger"] == "adjacent_receipts"
    monkeypatch.setattr(service, "rematch_neighbour_months", real)

    with TestClient(create_app(tmp_path)) as rebooted:
        _wait_owed_cleared(rebooted, august)
        assert _triggers(rebooted, august) == ["statement", "resume"]
        assert _google_row(rebooted, august)["chosen_document_id"] == late


# ── the month move ───────────────────────────────────────────────────


def test_a_month_move_into_july_rematches_august(client, monkeypatch):
    """June's Google receipt read as 06-15; the reviewer types 07-31 and moves
    it into July. July and June re-match (neither has a statement), and so
    does August, whose statement opens on 07-31."""
    _wire(
        monkeypatch,
        _receipt("Google", "71.64", "2026-06-15"),
        _receipt("Stripe", "10.00", "2026-07-10"),
        _receipt("Lovable", "25.00", "2026-08-15"),
    )
    june = _month(client, "June 2026", fname="jun.jpg")
    july = _month(client, "July 2026", fname="jul.jpg")
    august = _month(client, "August 2026", fname="aug.jpg")
    _attach(client, august, AUGUST_CSV)
    doc = _doc_named(client, june, "jun.jpg")
    resp = client.put(
        f"/api/runs/{june}/expenses/{doc}",
        json={"field": "date", "value": "2026-07-31"},
    )
    assert resp.status_code == 200, resp.text

    moved = client.post(
        f"/api/runs/{june}/expenses/{doc}/move", json={"month": "2026-07"}
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["batch_id"] == july
    assert _triggers(client, august) == ["statement", "adjacent_receipts"]
    row = _google_row(client, august)
    assert row["chosen_document_id"] == moved.json()["document_id"]
    assert row["settled_by"]["run_id"] == july
    assert [m["run_id"] for m in moved.json()["months_rematched"]] == [august]
