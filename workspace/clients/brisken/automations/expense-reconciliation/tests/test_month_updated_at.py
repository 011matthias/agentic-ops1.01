"""`updated_at`: when the month last changed, on both review payloads (2026-09-16).

The SPA renders `updated_at ?? created_at` as "Last updated", and neither the
run payload nor the batch payload carried a month-level `updated_at` (only a
trip's own). So every month printed its CREATION day: September 2026 read
Sep 07 while its last receipt arrived on 2026-09-16.

`service.month_updated_at` takes the latest of what the snapshot records
(creation, the last receipt add, statement uploads, re-match commits,
settled-outside dispositions, set-aside entries), the decisions the builder
is handed, and `edited_at`, which the two GET routes read off the edit tables
(`RunStore.latest_edit_at`). The last source is the one only a route can
supply: a field edit on a month without a statement writes
`expense_field_overrides` and nothing else.

Time is controlled by replacing the app's `_now_iso`, which every route in
these flows stamps with. The clock starts in 2031 so it outranks the one
stamp the app takes off the real clock (a re-match commit's `at`), which
keeps every "moves forward" assertion exact rather than approximate.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
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
from expense_recon.web.service import month_updated_at  # noqa: E402
from expense_recon.web.store import Decision, RunRow, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
T0 = datetime(2031, 1, 6, 9, 0, 0, tzinfo=timezone.utc)


class Clock:
    """A settable stand-in for `app._now_iso`, same output format."""

    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> str:
        return self.now.isoformat(timespec="seconds")

    def advance(self, **delta) -> str:
        self.now += timedelta(**delta)
        return self()


@pytest.fixture
def clock(monkeypatch):
    c = Clock(T0)
    monkeypatch.setattr("expense_recon.web.app._now_iso", c)
    return c


@pytest.fixture
def client(tmp_path, monkeypatch, clock):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-08-05", total="25.00", currency="USD",
                vendor="Lovable Labs", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ],
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
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create(client) -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    return resp.json()["batch_id"]


def _add_receipt(client, batch_id: str) -> None:
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("lovable.jpg", JPG, "application/octet-stream"))],
    ))


def _attach(client, batch_id: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    ws.append([datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00])
    ws.append([datetime(2026, 8, 19), "SUPABASE", "Sale", -92.70])
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


def _batch(client, batch_id: str) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run(client, batch_id: str) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_a_fresh_month_was_last_updated_when_it_was_created(client):
    batch_id = _create(client)
    view = _batch(client, batch_id)
    assert isinstance(view["updated_at"], str)
    assert _at(view["updated_at"]) == _at(view["created_at"]) == T0
    # The live format: seconds precision, explicit UTC offset.
    assert view["updated_at"] == "2031-01-06T09:00:00+00:00"


def test_a_receipt_add_moves_it_forward(client, clock):
    batch_id = _create(client)
    added = clock.advance(hours=1)
    _add_receipt(client, batch_id)

    view = _batch(client, batch_id)
    assert view["expense_ingest"]["at"] == added
    assert _at(view["created_at"]) == T0, "creation does not move"
    assert view["updated_at"] == added


def test_a_field_edit_on_a_month_without_a_statement_moves_it_forward(
    client, clock
):
    """The case only the edit tables can answer: PUT writes
    `expense_field_overrides` and the snapshot does not change at all."""
    batch_id = _create(client)
    added = clock.advance(hours=1)
    _add_receipt(client, batch_id)
    before = _batch(client, batch_id)
    doc = before["expenses"][0]["document_id"]
    assert before["updated_at"] == added

    edited = clock.advance(hours=2)
    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "vendor", "value": "Lovable (edited)"},
    )
    assert resp.status_code == 200, resp.text

    after = _batch(client, batch_id)
    assert after["expense_ingest"] == before["expense_ingest"], (
        "precondition: the edit left the snapshot alone"
    )
    assert after["updated_at"] == edited
    # GET /api/runs/{id} dispatches a statement-less batch to the same view.
    assert _run(client, batch_id)["updated_at"] == edited


def test_a_statement_month_reads_its_uploads_decisions_and_edits(client, clock):
    batch_id = _create(client)
    clock.advance(hours=1)
    _add_receipt(client, batch_id)
    clock.advance(hours=1)
    _attach(client, batch_id)

    view = _run(client, batch_id)
    assert view["statements"], "precondition: a statement month"
    assert isinstance(view["updated_at"], str)
    for entry in view["statements"]:
        assert _at(view["updated_at"]) >= _at(entry["uploaded_at"]), entry
    grid = _batch(client, batch_id)
    assert grid["updated_at"] == view["updated_at"], "one month, one answer"

    # A decision write moves it.
    supabase = next(r for r in view["rows"] if r["vendor"] == "SUPABASE")
    decided = clock.advance(hours=3)
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": supabase["transaction_id"], "status": "rejected"},
    )
    assert resp.status_code == 200, resp.text
    assert _run(client, batch_id)["updated_at"] == decided

    # A category override moves it too. It touches neither the snapshot nor
    # a decision, so only the route's read of the edit tables can see it.
    lovable = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    doc = next(c["document_id"] for c in lovable["candidates"] if c["is_chosen"])
    recategorized = clock.advance(hours=4)
    resp = client.post(
        f"/api/runs/{batch_id}/categories",
        json={"document_id": doc, "category": "Travel & Transport"},
    )
    assert resp.status_code == 200, resp.text
    assert _run(client, batch_id)["updated_at"] == recategorized


def test_an_unreadable_stamp_is_skipped_never_raised(client, clock):
    batch_id = _create(client)
    added = clock.advance(hours=1)
    _add_receipt(client, batch_id)

    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot)
        snapshot["rematch_log"] = [
            {"at": "not a timestamp"}, {"at": 12345}, {"at": ""}, "junk",
            {"at": "2031-13-45T99:00:00"},
        ]
        # Well-formed entries with unreadable stamps: a non-dict entry is
        # refused by `set_aside_view` before this field is ever built.
        snapshot["set_aside"] = [
            {"file": "x.jpg", "reason": "other", "at": "yesterday",
             "restored_at": None},
            {"file": "y.jpg", "reason": "other", "at": None,
             "restored": True, "restored_at": "2031-99-01"},
        ]
        snapshot["settled_outside"] = {
            "doc-x": {"how": "cash", "note": "", "at": "garbage"},
        }
        store.update_run_snapshot(batch_id, snapshot)
    finally:
        store.close()

    view = _batch(client, batch_id)
    assert view["updated_at"] == added

    # And the one stamp that decides it can itself be garbage.
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot)
        snapshot["expense_ingest"] = {**snapshot["expense_ingest"], "at": "soon"}
        store.update_run_snapshot(batch_id, snapshot)
    finally:
        store.close()
    assert _batch(client, batch_id)["updated_at"] == T0.isoformat()


def _row(created_at: str, snapshot: dict) -> RunRow:
    return RunRow(
        run_id="r", created_at=created_at, label="x", operator=None,
        summary={}, snapshot=snapshot, config={}, work_dir=".",
        llm_enabled=False, has_coa=False,
    )


def test_the_helper_normalizes_to_utc_seconds_and_falls_back_verbatim():
    """Naive reads as UTC, an offset is converted, sub-seconds are dropped,
    and a month whose every stamp is unreadable returns `created_at` exactly
    as stored rather than raising or inventing one."""
    snapshot = {
        "statements": [{"uploaded_at": "2031-02-01T12:00:00.987654"}, "junk"],
        "expense_ingest": {"at": "2031-02-01T13:30:00+02:00"},  # 11:30 UTC
    }
    assert month_updated_at(_row("2031-01-01T00:00:00", snapshot)) == (
        "2031-02-01T12:00:00+00:00"
    )
    decisions = {"t": Decision(status="confirmed", chosen_document_id=None,
                               updated_at="2031-03-01T00:00:00+00:00")}
    assert month_updated_at(
        _row("2031-01-01T00:00:00", snapshot), decisions=decisions,
        edits=[{"updated_at": "2031-02-15T00:00:00+00:00"}, "junk"],
        edited_at="2031-02-20T00:00:00+00:00",
    ) == "2031-03-01T00:00:00+00:00"
    assert month_updated_at(
        _row("not-a-date", {"expense_ingest": "junk", "statements": None}),
        edited_at="",
    ) == "not-a-date"
