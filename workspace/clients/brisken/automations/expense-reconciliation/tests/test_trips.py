"""Trips + declared batch type (backlog item 38, owner directive 2026-09-06).

The expense split's surface half: a batch is DECLARED at creation as a
company month or a trip (never inferred from content), the trip is an
entity of its own (named, date-ranged, VARIABLE roster of travelers) with
a list API beside /api/expense-batches, and month routing structurally
never lands mail in a trip batch — even one whose name parses as a month.

Contract rules exercised here: an ABSENT batch_type marker reads as a
company month AND an undeclared create stores no marker at all, so every
pre-split batch and every batch created by an un-updated caller keeps its
exact prior config shape (additive, api-contract rule 1).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    _open_batch_for_month,
    month_batch_states,
    open_batch,
)
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-07-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _make_trip(client, name="Rome 2026", start="2026-09-20",
               end="2026-10-03", travelers=("Dirk Neumann", "Criss")):
    resp = client.post("/api/trips", json={
        "name": name, "start": start, "end": end,
        "travelers": list(travelers),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_batch(client, files=None, data=None):
    payload = [
        ("files", (n, d, "application/octet-stream"))
        for n, d in (files or [("a.jpg", JPG)])
    ]
    resp = client.post("/api/expense-batches", files=payload, data=data or {})
    return resp


def _done(client, body):
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    return body["batch_id"]


# ── the trip entity ─────────────────────────────────────────────────


def test_trip_create_list_roundtrip(client):
    trip = _make_trip(client)
    assert trip["name"] == "Rome 2026"
    assert trip["travelers"] == ["Dirk Neumann", "Criss"]
    assert trip["batch_id"] is None
    assert trip["summary"] is None

    listing = client.get("/api/trips").json()["trips"]
    assert [t["trip_id"] for t in listing] == [trip["trip_id"]]
    assert listing[0]["start"] == "2026-09-20"
    assert listing[0]["end"] == "2026-10-03"


@pytest.mark.parametrize("payload,fragment", [
    ({"start": "2026-09-20", "end": "2026-09-21"}, "name"),
    ({"name": "X", "start": "not-a-date", "end": "2026-09-21"}, "YYYY-MM-DD"),
    ({"name": "X", "start": "2026-09-22", "end": "2026-09-21"}, "before"),
    ({"name": "X", "start": "2026-09-20", "end": "2026-09-21",
      "travelers": "Dirk"}, "list"),
])
def test_trip_create_validation(client, payload, fragment):
    resp = client.post("/api/trips", json=payload)
    assert resp.status_code == 400, resp.text
    assert fragment in resp.json()["error"]


def test_trip_roster_is_variable_and_replaced_whole(client):
    trip = _make_trip(client, travelers=("Dirk Neumann",))
    resp = client.put(f"/api/trips/{trip['trip_id']}", json={
        "travelers": ["Dirk Neumann", "Criss", "Matthias Silva"],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["travelers"] == [
        "Dirk Neumann", "Criss", "Matthias Silva",
    ]
    # untouched fields survive a partial update
    assert resp.json()["name"] == "Rome 2026"

    resp = client.put(f"/api/trips/{trip['trip_id']}", json={
        "travelers": [],
    })
    assert resp.status_code == 200
    assert resp.json()["travelers"] == []


def test_trip_delete_plain_and_with_batch(client, monkeypatch):
    trip = _make_trip(client)
    other = _make_trip(client, name="Berlin")
    # A trip with no batch deletes cleanly.
    assert client.delete(f"/api/trips/{other['trip_id']}").status_code == 200
    # One with a batch is refused, naming the batch.
    _patch_ocr(monkeypatch, _extraction(date="2026-09-21"))
    resp = _create_batch(client, data={
        "batch_type": "trip", "trip_id": trip["trip_id"],
    })
    assert resp.status_code == 200, resp.text
    batch_id = _done(client, resp.json())
    refused = client.delete(f"/api/trips/{trip['trip_id']}")
    assert refused.status_code == 409
    assert refused.json()["batch_id"] == batch_id


# ── the declared batch type ─────────────────────────────────────────


def test_undeclared_create_stores_no_marker_and_reads_company(
    client, monkeypatch,
):
    _patch_ocr(monkeypatch, _extraction())
    resp = _create_batch(client, data={"legal_entity": "Corporate Services"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["batch_type"] == "company-month"
    batch_id = _done(client, resp.json())

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["batch_type"] == "company-month"
    assert grid["trip"] is None

    # The additive half of the contract: an undeclared create must store
    # NO marker, so its config is byte-identical to the pre-split shape.
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    assert "batch_type" not in run.config
    assert "trip_id" not in run.config


def test_declared_company_month_reads_company(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction())
    resp = _create_batch(client, data={"batch_type": "company-month"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["batch_type"] == "company-month"


def test_batch_type_validation(client):
    assert _create_batch(
        client, data={"batch_type": "vacation"}
    ).status_code == 400
    assert _create_batch(
        client, data={"batch_type": "trip"}
    ).status_code == 400  # no trip_id
    assert _create_batch(
        client, data={"trip_id": "abc"}
    ).status_code == 400  # trip_id without the declared type
    assert _create_batch(
        client, data={"batch_type": "trip", "trip_id": "nope"}
    ).status_code == 404  # unknown trip


def test_trip_batch_create_and_one_batch_per_trip(client, monkeypatch):
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction(date="2026-09-21"))
    resp = _create_batch(client, data={
        "batch_type": "trip", "trip_id": trip["trip_id"],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # The label defaults to the trip's name; a trip is not addressed by
    # month, so the create reply carries no month and no month advisory.
    assert body["label"] == "Rome 2026"
    assert body["batch_type"] == "trip"
    assert body["month"] is None
    assert "advisory" not in body
    batch_id = _done(client, body)

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["batch_type"] == "trip"
    assert grid["trip"]["trip_id"] == trip["trip_id"]
    assert grid["trip"]["travelers"] == ["Dirk Neumann", "Criss"]
    assert grid["trip"]["start"] == "2026-09-20"

    # The trips list joins the batch; the months list does NOT carry it.
    rows = client.get("/api/trips").json()["trips"]
    assert rows[0]["batch_id"] == batch_id
    assert rows[0]["summary"]["n_expenses"] == 1
    months = client.get("/api/expense-batches").json()["batches"]
    assert batch_id not in [b["batch_id"] for b in months]
    # Company rows carry the parallel batch_type scalar.
    assert all(b["batch_type"] == "company-month" for b in months)

    second = _create_batch(client, data={
        "batch_type": "trip", "trip_id": trip["trip_id"],
    })
    assert second.status_code == 409
    assert second.json()["batch_id"] == batch_id


def test_statement_never_attaches_to_a_trip(client, monkeypatch):
    trip = _make_trip(client)
    _patch_ocr(monkeypatch, _extraction(date="2026-09-21"))
    resp = _create_batch(client, data={
        "batch_type": "trip", "trip_id": trip["trip_id"],
    })
    batch_id = _done(client, resp.json())
    attach = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={"account_id": "amex-9001", "account_card_currency": "USD"},
    )
    assert attach.status_code == 400
    assert "company months" in attach.json()["error"]


def test_no_period_suggestion_on_a_trip(client, monkeypatch):
    """Trips span month boundaries freely; the month-rename banner must
    never be offered on one, even when every receipt dates into one
    month (the consensus that triggers it on a company batch)."""
    trip = _make_trip(client, start="2026-07-01", end="2026-07-31")
    _patch_ocr(monkeypatch, *[
        _extraction(date=f"2026-07-0{i}", total=f"{i}0.00")
        for i in range(1, 6)
    ])
    resp = _create_batch(
        client,
        files=[(f"r{i}.jpg", JPG + bytes([i])) for i in range(5)],
        data={"batch_type": "trip", "trip_id": trip["trip_id"]},
    )
    batch_id = _done(client, resp.json())
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert grid["period_suggestion"] is None
    assert grid["summary"]["n_expenses"] == 5


# ── month routing can never see a trip ──────────────────────────────


def test_month_selectors_skip_trip_batches(client, monkeypatch):
    """A trip whose NAME parses as a month must still be invisible to
    every month selector: the pool claims by declared type, not by
    label. This is the structural half of 'declared, never inferred'."""
    trip = _make_trip(client, name="July 2026",
                      start="2026-07-01", end="2026-07-31")
    _patch_ocr(monkeypatch, _extraction(date="2026-07-02"))
    resp = _create_batch(client, data={
        "batch_type": "trip", "trip_id": trip["trip_id"],
    })
    assert resp.status_code == 200, resp.text
    _done(client, resp.json())

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert _open_batch_for_month(store, (2026, 7)) is None
        assert month_batch_states(store) == {}
        assert open_batch(store) is None
