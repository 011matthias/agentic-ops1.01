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
