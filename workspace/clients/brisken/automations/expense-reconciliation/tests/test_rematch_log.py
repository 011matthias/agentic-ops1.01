"""The re-match log (backlog item 58, 2026-09-11): every commit of
`rematch_month` leaves one event, and the operator state exposes them.

The dev-side notifier used to ping on new runs only, so the 2026-09-10
uploads that reconciled 0 of 111 were invisible until Criss wrote. Now an
attach, a re-read, a mailed or dropped receipt, a card assignment, a
master-data refresh, a set-aside restore and a trip change each leave
`{event_id, at, trigger, counts}` on the month, and
`GET /api/operator/state` lists them as `rematches[]` for the notifier to
diff on `event_id`.

Route-level: the events are read back through the same endpoint the
notifier polls, after real attaches and adds.
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
from expense_recon.web.service import (  # noqa: E402
    REMATCH_LOG_CAP,
    append_rematch_event,
)

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
CHASE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
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


def _create_batch(client, label="August 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
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


def _add_receipt(client, batch_id, name="late.jpg", body=b"9"):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, JPG + body, "application/octet-stream"))],
    ))


def _rematches(client, batch_id=None):
    resp = client.get("/api/operator/state")
    assert resp.status_code == 200, resp.text
    events = resp.json()["rematches"]
    if batch_id is not None:
        events = [e for e in events if e["run_id"] == batch_id]
    return events


def test_no_event_before_the_first_match(client, monkeypatch):
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    assert _rematches(client, batch_id) == []
    assert "rematches" in client.get("/api/operator/state").json()


def test_every_rematch_path_leaves_one_event_with_its_counts(client, monkeypatch):
    """Attach, then a late receipt, then a re-read: three commits, three
    events, oldest first, each naming what caused it and the counts the
    notifier prints ("August 2026: 1 of 3, pool 0")."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)

    _attach_xlsx(client, batch_id)
    events = _rematches(client, batch_id)
    assert [e["trigger"] for e in events] == ["statement"]
    first = events[0]
    assert first["label"] == "August 2026"
    assert first["n_transactions"] == 3
    assert first["n_matched"] == 1
    assert first["n_receipts"] == 1
    assert first["n_unmatched_rec"] == 0
    assert first["match_rate"] == pytest.approx(33.3)
    assert first["event_id"] and first["at"]

    _add_receipt(client, batch_id)
    events = _rematches(client, batch_id)
    assert [e["trigger"] for e in events] == ["statement", "receipts"]
    assert events[1]["n_matched"] == 2
    assert events[1]["n_receipts"] == 2

    _done(client, client.post(f"/api/expense-batches/{batch_id}/statements/reread"))
    events = _rematches(client, batch_id)
    assert [e["trigger"] for e in events] == ["statement", "receipts", "reread"]
    assert len({e["event_id"] for e in events}) == 3, "ids are unique"
    assert [e["at"] for e in events] == sorted(e["at"] for e in events)


def test_a_card_assignment_leaves_its_own_event(client, monkeypatch):
    """The R3 F1 path: a card assignment re-matches the month, and that
    re-match is announced like any other."""
    resp = client.put("/api/settings", json={"cards": {
        "corp-2838": {
            "label": "Corporate card (Chase)",
            "digits": ["2838", "1672"],
            "entity": "Corporate Services",
        },
    }})
    assert resp.status_code == 200, resp.text
    ext = ExtractedReceipt(
        date="2026-08-31", total="15.00", currency="USD", vendor="Lovable Labs",
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint="Visa",
    )
    _wire(monkeypatch, ext)
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    resp = client.post(
        f"/api/expense-batches/{batch_id}/cards",
        json={"assignments": [{"hint": "Visa", "card": "corp-2838"}]},
    )
    assert resp.status_code == 200, resp.text
    triggers = [e["trigger"] for e in _rematches(client, batch_id)]
    assert triggers == ["statement", "cards"]


def test_the_log_is_capped_and_tolerates_junk():
    log = None
    for i in range(REMATCH_LOG_CAP + 5):
        log = append_rematch_event(log, {"event_id": f"e{i}"})
    assert len(log) == REMATCH_LOG_CAP
    assert log[0]["event_id"] == "e5"
    assert log[-1]["event_id"] == f"e{REMATCH_LOG_CAP + 4}"
    assert append_rematch_event("not a list", {"event_id": "x"}) == [{"event_id": "x"}]
    assert append_rematch_event([1, "junk", {"event_id": "a"}], {"event_id": "b"}) == [
        {"event_id": "a"}, {"event_id": "b"},
    ]


# ---------------------------------------------- an owed re-match (item 113) --
# 2026-09-17 voids audit: every arrival re-matches its month after the receipt
# is stored. A re-match that raised rode back in a result the mail and drop
# callers discard; one cut off by a restart left no trace at all; re-running
# the interrupted job found no new files and skipped the re-pairing. The month
# now carries `rematch_pending` until a re-match that read it commits.


def _owed(client, batch_id):
    resp = client.get("/api/operator/state")
    assert resp.status_code == 200, resp.text
    return [m for m in resp.json()["rematch_pending"] if m["run_id"] == batch_id]


def test_a_failed_rematch_is_owed_recorded_and_paid_by_the_next_arrival(
    client, monkeypatch,
):
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    assert _owed(client, batch_id) == []

    from expense_recon.web import service
    real = service.rematch_month

    def _down(*a, **k):
        raise RuntimeError("model outage")

    monkeypatch.setattr(service, "rematch_month", _down)
    _add_receipt(client, batch_id)  # the job still reads done: the receipt landed
    owed = _owed(client, batch_id)
    assert len(owed) == 1, owed
    assert "model outage" in owed[0]["error"]
    assert owed[0]["attempts"] == 1
    assert owed[0]["failed_at"] and owed[0]["since"]
    assert [e["trigger"] for e in _rematches(client, batch_id)] == ["statement"]

    # The same file again: nothing new, but the owed re-match is paid.
    monkeypatch.setattr(service, "rematch_month", real)
    _add_receipt(client, batch_id)
    assert _owed(client, batch_id) == []
    events = _rematches(client, batch_id)
    assert [e["trigger"] for e in events] == ["statement", "receipts"]
    assert events[-1]["n_receipts"] == 2


def test_a_rematch_cut_off_by_a_restart_is_repaired_at_boot(
    client, monkeypatch, tmp_path,
):
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    import time

    from expense_recon.web import service
    real = service.rematch_after_change

    # The machine stops after the receipt is stored, before the re-pairing.
    monkeypatch.setattr(service, "rematch_after_change", lambda *a, **k: None)
    _add_receipt(client, batch_id)
    owed = _owed(client, batch_id)
    assert len(owed) == 1 and "error" not in owed[0], owed
    monkeypatch.setattr(service, "rematch_after_change", real)

    # The next boot re-pairs it.
    with TestClient(create_app(tmp_path)) as rebooted:
        deadline = time.monotonic() + 20
        while _owed(rebooted, batch_id) and time.monotonic() < deadline:
            time.sleep(0.2)
        assert _owed(rebooted, batch_id) == []
        events = _rematches(rebooted, batch_id)
        assert [e["trigger"] for e in events] == ["statement", "resume"]
        assert events[-1]["n_receipts"] == 2


def test_a_change_landing_mid_rematch_keeps_its_own_debt(client, monkeypatch):
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    from expense_recon.web import service
    real = service.rematch_month
    landed: dict = {}

    def _arrival_during(store, run, *a, **k):
        # Another change commits while this re-match runs: a new mark id.
        with service._BATCH_ADD_LOCK:
            fresh = store.get_run(run.run_id)
            snap = dict(fresh.snapshot)
            snap[service.REMATCH_PENDING_KEY] = service.rematch_pending_mark(
                snap, "receipts"
            )
            landed["id"] = snap[service.REMATCH_PENDING_KEY]["id"]
            store.update_run_snapshot(run.run_id, snap)
        return real(store, run, *a, **k)

    monkeypatch.setattr(service, "rematch_month", _arrival_during)
    _add_receipt(client, batch_id)
    owed = _owed(client, batch_id)
    assert [m["id"] for m in owed] == [landed["id"]]
    assert [e["trigger"] for e in _rematches(client, batch_id)] == [
        "statement", "receipts",
    ]


def test_an_older_rematch_does_not_clear_a_newer_changes_debt(client, monkeypatch):
    """Review finding 1: an arrival's re-match A is running; another change
    (an edit, a card) owes its own re-match B, which the machine never gets
    to run. A read the month before B's change, so A's commit keeps B's debt."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    from expense_recon.web import service
    real = service.rematch_month
    seen: dict = {}

    def _during(store, run, *a, **k):
        if not seen:
            seen["a_read"] = service.rematch_pending(run)["id"]
            service._ensure_rematch_pending(store, run.run_id, "expense_edit")
            seen["b"] = service.rematch_pending(store.get_run(run.run_id))["id"]
        return real(store, run, *a, **k)

    monkeypatch.setattr(service, "rematch_month", _during)
    _add_receipt(client, batch_id)
    assert seen["b"] != seen["a_read"]
    assert [m["id"] for m in _owed(client, batch_id)] == [seen["b"]]


def test_an_older_rematch_does_not_erase_a_newer_failure(client, monkeypatch):
    """Review finding 2: B's re-match raises while A runs; A's later commit
    must leave B's recorded failure for the operator state and the retry."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    from expense_recon.web import service
    real = service.rematch_month
    calls = {"n": 0}

    def _during(store, run, *a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            service.rematch_after_change(store, run.run_id, trigger="expense_edit")
            return real(store, run, *a, **k)
        raise RuntimeError("model outage during B")

    monkeypatch.setattr(service, "rematch_month", _during)
    _add_receipt(client, batch_id)
    owed = _owed(client, batch_id)
    assert len(owed) == 1, owed
    assert "model outage during B" in owed[0]["error"]


def test_a_failure_recorded_without_its_own_mark_survives_an_older_commit(
    client, monkeypatch,
):
    """The attach, re-read and unparseable-snapshot paths record a failure
    with no owed-mark written first; the record takes its own id, so the
    in-flight arrival re-match that read the month earlier keeps it."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    from expense_recon.web import service
    real = service.rematch_month

    def _during(store, run, *a, **k):
        service._record_rematch_failure(store, run.run_id, "reread", "boom")
        return real(store, run, *a, **k)

    monkeypatch.setattr(service, "rematch_month", _during)
    _add_receipt(client, batch_id)
    owed = _owed(client, batch_id)
    assert len(owed) == 1 and owed[0]["error"] == "boom", owed
