"""Item 129 (2026-09-18): a re-match happened silently. Neither the drop page
nor the month page said one ran, because neither month payload carried the
last commit (`rematch_log`, item 58) or the owed mark (`rematch_pending`,
item 113); only `GET /api/operator/state` served them, and the SPA cannot
render what the month payload does not hand it.

Both payloads (`GET /api/runs/{id}`, `GET /api/expense-batches/{id}`) now
carry `last_rematch` (the newest log event, or null) and `rematch_pending`
(the owed mark minus its id, or null), read off the stored snapshot by one
helper, `service.rematch_visibility`. Route-level: the fields are read back
through the two endpoints the SPA renders, after real attaches and adds, a
written mark, and a failed re-match. The fixtures are copies of the ones in
`tests/test_rematch_log.py` (a fixture is not imported across test modules;
CI ruff F811).
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
from expense_recon.web import service  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    REMATCH_LOG_KEY,
    REMATCH_PENDING_KEY,
    rematch_pending_mark,
    rematch_visibility,
)
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
CHASE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
LAST_KEYS = {
    "at", "trigger", "n_transactions", "n_matched", "n_review",
    "n_unmatched_tx", "n_receipts", "n_unmatched_rec", "event_id",
}


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


def _wire_two(monkeypatch):
    return _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )


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


def _run(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _both(client, batch_id) -> tuple[dict, dict]:
    return _run(client, batch_id), _grid(client, batch_id)


def _operator(client) -> dict:
    resp = client.get("/api/operator/state")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _edit_snapshot(client, batch_id, change) -> None:
    """Write straight into the stored snapshot, the way the pending-mark and
    unreadable-stamp tests do: the month as the store holds it, not as a
    route would shape it."""
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
        snapshot = dict(run.snapshot)
        change(snapshot)
        store.update_run_snapshot(batch_id, snapshot)


def test_a_fresh_month_reads_null_for_both_on_both_endpoints(client, monkeypatch):
    """(a) Before a statement, nothing has re-matched and nothing is owed:
    both keys PRESENT (the SPA must tell "never" from "an older build") and
    both null, on the run endpoint and the batch endpoint alike."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    for view in _both(client, batch_id):
        assert "last_rematch" in view and "rematch_pending" in view, sorted(view)
        assert view["last_rematch"] is None
        assert view["rematch_pending"] is None


def test_a_commit_is_visible_with_its_trigger_and_the_pages_own_count(
    client, monkeypatch,
):
    """(b) The attach is the month's first commit; a late receipt is the
    next. Each shows on both payloads with the trigger that caused it and
    the effective matched count the same payload's summary prints
    (`n_reconciled`, item 103), and it is the same event the notifier
    reads off the operator state, minus the fields the payload already
    carries."""
    _wire_two(monkeypatch)
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    run, grid = _both(client, batch_id)
    last = run["last_rematch"]
    assert last is not None, run
    assert set(last) == LAST_KEYS, last
    assert last["trigger"] == "statement"
    assert last["n_matched"] == run["summary"]["n_reconciled"] == 1
    assert last["n_transactions"] == run["summary"]["n_transactions"] == 3
    assert last["n_receipts"] == 1
    assert last["event_id"] and last["at"]
    assert grid["last_rematch"] == last, "one month, one answer"
    assert run["rematch_pending"] is None and grid["rematch_pending"] is None
    events = [e for e in _operator(client)["rematches"] if e["run_id"] == batch_id]
    assert {k: events[-1][k] for k in LAST_KEYS} == last
    for key in ("run_id", "label", "match_rate"):
        assert key in events[-1] and key not in last, key

    _add_receipt(client, batch_id)
    run, grid = _both(client, batch_id)
    again = run["last_rematch"]
    assert again["trigger"] == "receipts"
    assert again["event_id"] != last["event_id"]
    assert again["n_receipts"] == 2
    assert again["n_matched"] == run["summary"]["n_reconciled"] == 2
    assert grid["last_rematch"] == again
    assert run["rematch_pending"] is None


def test_an_owed_rematch_is_visible_until_the_next_arrival_pays_it(
    client, monkeypatch,
):
    """(c) A mark written with no commit (the way the item-113 tests write
    one) shows on both payloads: `since` and `changed_at` present, the
    trigger right, the mark's `id` withheld, and `last_rematch` exactly
    what it was. The next arrival pays it and the key goes back to null."""
    _wire_two(monkeypatch)
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    before = _run(client, batch_id)["last_rematch"]
    assert before["trigger"] == "statement"

    def _owe(snapshot):
        snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(snapshot, "expense_edit")

    _edit_snapshot(client, batch_id, _owe)
    run, grid = _both(client, batch_id)
    pending = run["rematch_pending"]
    assert pending is not None, run
    assert set(pending) == {"since", "changed_at", "trigger"}, pending
    assert pending["trigger"] == "expense_edit"
    assert isinstance(pending["since"], str) and pending["since"]
    assert isinstance(pending["changed_at"], str) and pending["changed_at"]
    assert grid["rematch_pending"] == pending
    assert run["last_rematch"] == before, "an owed re-match is not a commit"
    assert grid["last_rematch"] == before
    owed = [m for m in _operator(client)["rematch_pending"] if m["run_id"] == batch_id]
    assert len(owed) == 1 and owed[0]["id"], owed
    assert {k: v for k, v in owed[0].items() if k not in {"run_id", "label", "id"}} == (
        pending
    )

    _add_receipt(client, batch_id)
    run, grid = _both(client, batch_id)
    assert run["rematch_pending"] is None and grid["rematch_pending"] is None
    assert run["last_rematch"]["trigger"] == "receipts"
    assert run["last_rematch"]["event_id"] != before["event_id"]


def test_an_empty_absent_or_unreadable_log_reads_null_not_an_error(
    client, monkeypatch,
):
    """(d) The negative case: a statement month (so the run endpoint renders
    `build_view`, not the grid) whose `rematch_log` is an empty list is null
    on both endpoints, the row class a naive `[-1]` raises on. An absent key
    and junk read the same way, and the helper alone agrees."""
    _wire_two(monkeypatch)
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    assert _run(client, batch_id)["last_rematch"] is not None, "precondition"

    def _empty(snapshot):
        snapshot[REMATCH_LOG_KEY] = []

    _edit_snapshot(client, batch_id, _empty)
    for view in _both(client, batch_id):
        assert "last_rematch" in view
        assert view["last_rematch"] is None, view["last_rematch"]

    _edit_snapshot(client, batch_id, lambda s: s.pop(REMATCH_LOG_KEY, None))
    for view in _both(client, batch_id):
        assert view["last_rematch"] is None

    def _junk(snapshot):
        snapshot[REMATCH_LOG_KEY] = ["junk", 3]

    _edit_snapshot(client, batch_id, _junk)
    for view in _both(client, batch_id):
        assert view["last_rematch"] is None

    assert rematch_visibility(None) == {"last_rematch": None, "rematch_pending": None}
    assert rematch_visibility({REMATCH_LOG_KEY: "junk", REMATCH_PENDING_KEY: "junk"}) == {
        "last_rematch": None, "rematch_pending": None,
    }
    # A mark without an id is not a mark (the `rematch_pending` rule), and a
    # log whose junk entries precede a real one reads the real one.
    assert rematch_visibility({
        REMATCH_LOG_KEY: ["junk", {"event_id": "e1", "trigger": "reread"}],
        REMATCH_PENDING_KEY: {"since": "2026-09-18T00:00:00+00:00"},
    }) == {
        "last_rematch": {**dict.fromkeys(LAST_KEYS), "event_id": "e1", "trigger": "reread"},
        "rematch_pending": None,
    }


def test_a_recorded_failure_flows_through_and_clears_when_paid(client, monkeypatch):
    """(e) A re-match that raised leaves `error`, `failed_at` and `attempts`
    on the mark (item 113), and the month page can now print them; the
    failed attempt writes no event, so `last_rematch` stays on the attach.
    The next arrival pays the debt: null again, and a `receipts` commit."""
    _wire_two(monkeypatch)
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)
    real = service.rematch_month

    def _down(*a, **k):
        raise RuntimeError("model outage")

    monkeypatch.setattr(service, "rematch_month", _down)
    _add_receipt(client, batch_id)  # the receipt landed; the re-pairing did not
    run, grid = _both(client, batch_id)
    pending = run["rematch_pending"]
    assert pending is not None, run
    assert "model outage" in pending["error"]
    assert pending["attempts"] == 1
    assert isinstance(pending["failed_at"], str) and pending["failed_at"]
    assert pending["trigger"] == "receipts"
    assert "id" not in pending
    assert grid["rematch_pending"] == pending
    assert run["last_rematch"]["trigger"] == "statement", "a failure is not a commit"

    monkeypatch.setattr(service, "rematch_month", real)
    _add_receipt(client, batch_id)
    run, grid = _both(client, batch_id)
    assert run["rematch_pending"] is None and grid["rematch_pending"] is None
    assert run["last_rematch"]["trigger"] == "receipts"
    assert run["last_rematch"]["n_receipts"] == 2
