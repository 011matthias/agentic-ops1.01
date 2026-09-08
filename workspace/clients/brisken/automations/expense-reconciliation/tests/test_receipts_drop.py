"""The Receipts drop page (2026-09-08): receipt entry decoupled from month
creation.

Three coupled behaviors, each pinned here:

1. `POST /api/expense-batches` refuses receipt files on a COMPANY month
   (they enter through the drop) and creates the month EMPTY — the
   container a statement lands in. Trip creates keep create-with-receipt,
   and the service-level empty refusal stays the floor for callers that
   did not opt in (the mail materializer).
2. `POST /api/receipts` routes each dropped FILE to the month printed on
   it — same brain as mail routing (`resolve_receipt_month`), months
   materialize when absent (`created_by: "drop"`), a file with no
   readable date is `needs_month` and NOT ingested, and an explicit
   `month` override files everything in the call (a typed month is
   believed).
3. The per-file ledger rides the job row's `result`, read from
   GET /jobs/{id}.

Mock-queue budget (the mock has no extraction cache, so the drop pays the
queue twice per file exactly like mail): one read per file for the routing
pass, then one per file again for the batch ingest, in MONTH order
(oldest month files first)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import RunInputError, create_expense_batch  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000

# Dynamic fixture months (mirrors test_intake_mail): the plausibility clamp
# measures printed dates against TODAY, so literals would expire this file.
DAY_M1 = date.today().replace(day=1) - timedelta(days=20)   # last month
DAY_M2 = date.today().replace(day=1) - timedelta(days=50)   # two months back
MONTH_M1 = f"{DAY_M1.year:04d}-{DAY_M1.month:02d}"
MONTH_M2 = f"{DAY_M2.year:04d}-{DAY_M2.month:02d}"
LABEL_M1 = f"{calendar.month_name[DAY_M1.month]} {DAY_M1.year}"
LABEL_M2 = f"{calendar.month_name[DAY_M2.month]} {DAY_M2.year}"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(day: date, vendor="Staples", total="42.50") -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day.isoformat(), total=total, currency="EUR", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    """Empty queue answers a DATELESS extraction (routes nothing), so an
    under-budgeted test fails loudly instead of silently."""
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _drop(client, files, month: str | None = None):
    data = {"month": month} if month else {}
    resp = client.post(
        "/api/receipts",
        files=[("files", (n, b, "application/octet-stream")) for n, b in files],
        data=data,
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["result"]


def _batches(client) -> list[dict]:
    resp = client.get("/api/expense-batches")
    assert resp.status_code == 200
    body = resp.json()
    return body["batches"] if isinstance(body, dict) else body


# --- 1. month creation: empty container, no receipt injection ------------


def test_company_month_create_refuses_files(client):
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services", "label": LABEL_M1},
    )
    assert resp.status_code == 400
    assert "Receipts page" in resp.json()["error"]


def test_company_month_creates_empty(client, monkeypatch):
    _patch_ocr(monkeypatch)  # zero receipts -> zero extraction calls
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": LABEL_M1},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    view = client.get(f"/api/expense-batches/{body['batch_id']}").json()
    assert view["summary"]["n_expenses"] == 0
    assert view["label"] == LABEL_M1
    assert any(
        b.get("run_id", b.get("id")) == body["batch_id"]
        for b in _batches(client)
    )


def test_empty_month_takes_a_statement(client, monkeypatch):
    """The statement-first workflow the decoupling protects: January
    reality was 78 of 80 charges with no receipt."""
    from pathlib import Path

    _patch_ocr(monkeypatch)
    created = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": LABEL_M1},
    ).json()
    assert client.get(f"/jobs/{created['job_id']}").json()["status"] == "done"
    examples = Path(__file__).resolve().parent.parent / "examples"
    resp = client.post(
        f"/api/expense-batches/{created['batch_id']}/statement",
        files={"statement": (
            "statement.example.csv",
            (examples / "statement.example.csv").read_bytes(), "text/csv",
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
    view = client.get(f"/api/expense-batches/{created['batch_id']}").json()
    assert view["summary"].get("n_expenses") == 0


def test_service_empty_floor_unchanged(tmp_path):
    """The mail materializer's floor: no opt-in, no empty batch — and
    `allow_empty` never sanctions an upload whose every file was
    rejected."""
    with pytest.raises(RunInputError):
        create_expense_batch(
            tmp_path, files=[], legal_entity="", now_iso="2026-09-08T00:00:00",
            operator=None,
        )
    with pytest.raises(RunInputError):
        create_expense_batch(
            tmp_path, files=[("junk.txt", b"not a receipt")], legal_entity="",
            now_iso="2026-09-08T00:00:00", operator=None, allow_empty=True,
        )


def test_trip_create_with_files_still_works(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(DAY_M1))
    trip = client.post(
        "/api/trips",
        json={"name": "TEST drop trip", "start": DAY_M1.isoformat(),
              "end": (DAY_M1 + timedelta(days=4)).isoformat(),
              "travelers": ["A Person"]},
    ).json()
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("t.jpg", JPG, "application/octet-stream"))],
        data={"batch_type": "trip", "trip_id": trip["trip_id"]},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"


# --- 2. the drop: route by receipt month ---------------------------------


def test_drop_routes_two_files_to_two_new_months(client, monkeypatch):
    # Routing pass reads upload order (a then b); filing runs oldest month
    # first (M2 then M1), so the ingest reads pop in that order.
    _patch_ocr(
        monkeypatch,
        _extraction(DAY_M1),  # read a.jpg
        _extraction(DAY_M2),  # read b.jpg
        _extraction(DAY_M2),  # ingest M2 batch (b.jpg)
        _extraction(DAY_M1),  # ingest M1 batch (a.jpg)
    )
    result = _drop(client, [("a.jpg", JPG), ("b.jpg", JPG + b"2")])
    assert result["n_filed"] == 2, result
    by_file = {r["file"]: r for r in result["files"]}
    assert by_file["a.jpg"]["month"] == MONTH_M1
    assert by_file["a.jpg"]["month_source"] == "receipt"
    assert by_file["b.jpg"]["month"] == MONTH_M2
    months = {m["month"]: m for m in result["months"]}
    assert months[MONTH_M1]["created_batch"] is True
    assert months[MONTH_M1]["label"] == LABEL_M1
    assert months[MONTH_M2]["created_batch"] is True
    rows = _batches(client)
    labels = {b["label"] for b in rows}
    assert {LABEL_M1, LABEL_M2} <= labels
    for b in rows:
        if b["label"] in (LABEL_M1, LABEL_M2):
            assert b["summary"]["n_expenses"] == 1
            assert b["summary"].get("created_by") == "drop"


def test_drop_adds_to_existing_month(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(DAY_M1), _extraction(DAY_M1))
    created = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": LABEL_M1},
    ).json()
    assert client.get(f"/jobs/{created['job_id']}").json()["status"] == "done"
    result = _drop(client, [("a.jpg", JPG)])
    assert result["n_filed"] == 1
    entry = result["months"][0]
    assert entry["created_batch"] is False
    assert entry["batch_id"] == created["batch_id"]
    assert entry["n_added"] == 1
    view = client.get(f"/api/expense-batches/{created['batch_id']}").json()
    assert view["summary"]["n_expenses"] == 1


def test_drop_unreadable_date_rests_not_guesses(client, monkeypatch):
    _patch_ocr(monkeypatch)  # empty queue -> dateless extraction
    result = _drop(client, [("mystery.jpg", JPG)])
    assert result["n_filed"] == 0
    assert result["n_needs_month"] == 1
    row = result["files"][0]
    assert row["status"] == "needs_month"
    assert row["reason"] == "no-readable-date"
    assert _batches(client) == []  # nothing ingested, no month minted


def test_drop_month_override_is_believed(client, monkeypatch):
    _patch_ocr(monkeypatch, _extraction(DAY_M1))  # ingest read only
    result = _drop(client, [("mystery.jpg", JPG)], month=MONTH_M2)
    assert result["n_filed"] == 1
    row = result["files"][0]
    assert row["month"] == MONTH_M2
    assert row["month_source"] == "operator"
    assert result["months"][0]["label"] == LABEL_M2
    assert [b["label"] for b in _batches(client)] == [LABEL_M2]


def test_drop_rejects_unsupported_and_bad_override(client, monkeypatch):
    _patch_ocr(monkeypatch)
    result = _drop(client, [("notes.txt", b"some text")])
    row = result["files"][0]
    assert row["status"] == "rejected"
    assert row["reason"] == "unsupported-type"
    assert result["n_rejected"] == 1
    resp = client.post(
        "/api/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
        data={"month": "September 2026"},
    )
    assert resp.status_code == 400
    assert "YYYY-MM" in resp.json()["error"]


def test_drop_duplicate_bytes_are_skipped(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction(DAY_M1), _extraction(DAY_M1),  # first drop: read+ingest
        _extraction(DAY_M1),                        # second drop: read only
    )
    first = _drop(client, [("a.jpg", JPG)])
    assert first["months"][0]["created_batch"] is True
    second = _drop(client, [("a-again.jpg", JPG)])
    entry = second["months"][0]
    assert entry["created_batch"] is False
    assert entry["n_added"] == 0  # content dedupe, not a loss
    assert len(_batches(client)) == 1


def test_drop_takes_more_than_80_files(client, monkeypatch):
    """The 2026-09-08 cap raise: a backfill pile beyond the old 80-file
    bound files completely. Regressing FOLDER_MAX_FILES to 80 must turn
    this red (81st file skipped by the ingest cap)."""
    n = 81
    # Override month -> no routing reads; one ingest read per file.
    _patch_ocr(monkeypatch, *[_extraction(DAY_M1) for _ in range(n)])
    files = [(f"r{i:03d}.jpg", JPG + str(i).encode()) for i in range(n)]
    result = _drop(client, files, month=MONTH_M1)
    assert result["n_filed"] == n, result
    assert result["n_rejected"] == 0
    assert not any(r.get("reason") == "upload-cap" for r in result["files"])
    entry = result["months"][0]
    assert entry["created_batch"] is True
    assert entry["n_added"] == n
    view = client.get(f"/api/expense-batches/{entry['batch_id']}").json()
    assert view["summary"]["n_expenses"] == n


def test_drop_overflow_past_cap_is_ledgered_not_silent(client, monkeypatch):
    """A month group larger than FOLDER_MAX_FILES marks its overflow
    rejected/upload-cap in the drop ledger BEFORE the ingest call, whose
    internal cap would otherwise skip those files while their rows read
    "filed". Unwiring the pre-slice in route_dropped_receipts turns this
    red."""
    monkeypatch.setattr("expense_recon.web.service.FOLDER_MAX_FILES", 3)
    _patch_ocr(monkeypatch, *[_extraction(DAY_M1) for _ in range(3)])
    files = [(f"r{i}.jpg", JPG + str(i).encode()) for i in range(5)]
    result = _drop(client, files, month=MONTH_M1)
    by_file = {r["file"]: r for r in result["files"]}
    for name in ("r0.jpg", "r1.jpg", "r2.jpg"):
        assert by_file[name]["status"] == "filed"
    for name in ("r3.jpg", "r4.jpg"):
        assert by_file[name]["status"] == "rejected"
        assert by_file[name]["reason"] == "upload-cap"
        assert by_file[name]["limit"] == 3
    assert result["n_filed"] == 3
    assert result["n_rejected"] == 2
    entry = result["months"][0]
    assert entry["n_added"] == 3
    assert "issues" not in entry  # the ingest cap itself never fired
    view = client.get(f"/api/expense-batches/{entry['batch_id']}").json()
    assert view["summary"]["n_expenses"] == 3


# --- 3. the job ledger ----------------------------------------------------


def test_job_result_round_trips_through_store(tmp_path):
    with RunStore(tmp_path / "t.sqlite") as store:
        store.create_job("j1", None, "2026-09-08T00:00:00")
        store.set_job_status(
            "j1", "done", result='{"n_filed": 2}',
            updated_at="2026-09-08T00:00:01",
        )
        job = store.get_job("j1")
    assert job["status"] == "done"
    assert job["result"] == {"n_filed": 2}
