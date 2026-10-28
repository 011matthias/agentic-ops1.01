"""A trip lifecycle change owes its borrowing months a re-match (R4.1).

R4 made a month's candidate pool span overlapping trips. What it never
did was tell those months when the TRIP itself changed. Measured on a
copy of the live store on 2026-09-21: moving a trip's dates off July, and
deleting the trip's batch, each left July untouched, still reporting 33
charges reconciled where 31 was true and still rendering "Settled by
trip ..." badges naming a run that no longer existed. Nothing corrupts
(the claims are released, and July's next re-match heals it completely);
nothing schedules that next re-match either, so the month stays wrong
until something unrelated happens to touch it.

Owner ruling 2026-09-21: "must be done because later on if expenses and
items in statement dont line up we will have a problem."

Every test drives a ROUTE, because the defect was never in the helper:
`rematch_months_after_trip_change` did its job whenever it was called,
and the bug was the paths that never called it. The fixtures repeat
`test_trip_settlement.py`'s recipe rather than importing it, because
`tests/` is a package and no sibling cross-imports.
"""
from __future__ import annotations

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


def _extraction(vendor="Staples", total="42.50", date="2026-04-15"):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
    )


def _wire(monkeypatch, *extractions, n_fx=12):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("42.50"),
                reasoning="same purchase",
            )
        ] * n_fx,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_trip(client, name="TEST - Rome", start="2026-04-01",
                 end="2026-04-20", travelers=("Dirk",)):
    resp = client.post("/api/trips", json={
        "name": name, "start": start, "end": end,
        "travelers": list(travelers),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["trip_id"]


def _create_batch(client, label="April 2026", *, files=None, extra=None,
                  fname="a.jpg", body=b""):
    payload = files or [
        ("files", (fname, JPG + body, "application/octet-stream"))
    ]
    data = {
        "legal_entity": "Corporate Services", "label": label,
        **(extra or {}),
    }
    if data.get("batch_type") == "trip":
        resp = client.post("/api/expense-batches", files=payload, data=data)
        assert resp.status_code == 200, resp.text
        assert client.get(
            f"/jobs/{resp.json()['job_id']}"
        ).json()["status"] == "done"
        return resp.json()["batch_id"]
    resp = client.post("/api/expense-batches", data=data)
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"
    added = client.post(
        f"/api/expense-batches/{batch_id}/receipts", files=payload
    )
    assert added.status_code == 200, added.text
    assert client.get(
        f"/jobs/{added.json()['job_id']}"
    ).json()["status"] == "done"
    return batch_id


def _create_trip_batch(client, trip_id, *, files=None):
    return _create_batch(
        client, label="TEST - Rome receipts", files=files,
        extra={"batch_type": "trip", "trip_id": trip_id},
    )


def _attach(client, batch_id):
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
    job_id = resp.json().get("job_id") if resp.status_code == 200 else None
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _store(client) -> RunStore:
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


def _snapshot(client, batch_id) -> dict:
    with _store(client) as store:
        return store.get_run(batch_id).snapshot or {}


def _matches(client, batch_id) -> list[dict]:
    return (_snapshot(client, batch_id).get("outcome") or {}).get(
        "matches"
    ) or []


def _rematch_log(client, run_id) -> list[dict]:
    return _snapshot(client, run_id).get("rematch_log") or []


def _pending(client, run_id):
    return _snapshot(client, run_id).get("rematch_pending")


def _settled_rows(client, run_id) -> list[dict]:
    view = client.get(f"/api/runs/{run_id}").json()
    return [r for r in view["rows"] if r.get("settled_by")]


def _trip_settles_month(client, monkeypatch):
    """A trip whose Staples receipt settles April's STAPLES charge.
    Returns (trip_id, trip_batch, month, document_id)."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    assert any(m["document_id"] == doc for m in _matches(client, month)), (
        "harness: the trip receipt never settled the month's charge"
    )
    return trip_id, trip_batch, month, doc


# ── the date edit ────────────────────────────────────────────────────


def test_moving_a_trip_off_a_month_rematches_that_month(client, monkeypatch):
    """The measured defect. Moving the range so it no longer overlaps
    April must re-match April and take the borrowed receipt back out."""
    trip_id, _trip_batch, month, doc = _trip_settles_month(
        client, monkeypatch
    )
    before = len(_rematch_log(client, month))

    resp = client.put(f"/api/trips/{trip_id}", json={
        "start": "2026-06-01", "end": "2026-06-10",
    })
    assert resp.status_code == 200, resp.text

    log = _rematch_log(client, month)
    assert len(log) > before, "the month was never re-matched"
    assert log[-1]["trigger"] == "trip"
    assert [m["run_id"] for m in resp.json()["months_rematched"]] == [month]
    assert not any(m["document_id"] == doc for m in _matches(client, month))
    assert _settled_rows(client, month) == []
    with _store(client) as store:
        assert store.get_claims_by_run(month) == []


def test_moving_a_trip_onto_a_month_rematches_it(client, monkeypatch):
    """The other half of the union: a month the trip did NOT overlap
    before must pick the receipts up when the range moves onto it."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    trip_id = _create_trip(client, start="2026-06-01", end="2026-06-10")
    trip_batch = _create_trip_batch(client, trip_id)
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    assert not any(m["document_id"] == doc for m in _matches(client, month))

    resp = client.put(f"/api/trips/{trip_id}", json={
        "start": "2026-04-01", "end": "2026-04-20",
    })
    assert resp.status_code == 200, resp.text
    assert any(m["document_id"] == doc for m in _matches(client, month)), (
        "the month never picked the trip's receipt up"
    )
    assert _rematch_log(client, month)[-1]["trigger"] == "trip"


def test_a_roster_or_cost_center_edit_owes_nothing(client, monkeypatch):
    """Only a DATE change moves which months may borrow. A roster edit
    must not re-match anything: the grid resolves the roster live."""
    trip_id, _batch, month, _doc = _trip_settles_month(client, monkeypatch)
    before = len(_rematch_log(client, month))

    resp = client.put(f"/api/trips/{trip_id}", json={
        "travelers": ["Dirk", "Ana"], "cost_center": "Brazil",
    })
    assert resp.status_code == 200, resp.text
    assert "months_rematched" not in resp.json()
    assert len(_rematch_log(client, month)) == before


# ── the rename ───────────────────────────────────────────────────────


def test_a_rename_carries_onto_the_batch_label_and_the_badge(
    client, monkeypatch
):
    """The 2026-09-21 drive found the badge still naming the trip's
    creation-time name after a rename, and the delete confirm keyed on
    it. The batch label follows the trip."""
    trip_id, trip_batch, month, _doc = _trip_settles_month(
        client, monkeypatch
    )
    assert client.get(
        f"/api/expense-batches/{trip_batch}"
    ).json()["label"].startswith("TEST - Rome")

    resp = client.put(f"/api/trips/{trip_id}", json={"name": "TEST - Milan"})
    assert resp.status_code == 200, resp.text

    label = client.get(f"/api/expense-batches/{trip_batch}").json()["label"]
    assert label.startswith("TEST - Milan"), label
    row = _settled_rows(client, month)[0]
    assert row["settled_by"]["label"] == "TEST - Milan"
    assert client.post(
        f"/api/runs/{trip_batch}/delete", json={"confirm": label}
    ).status_code == 200


# ── the deletions ────────────────────────────────────────────────────


def test_deleting_a_trip_batch_rematches_the_borrowing_month(
    client, monkeypatch
):
    """The second measured defect: the month kept the settlement and the
    count after the batch it borrowed from was deleted."""
    _trip_id, trip_batch, month, doc = _trip_settles_month(
        client, monkeypatch
    )
    label = client.get(f"/api/expense-batches/{trip_batch}").json()["label"]
    before = len(_rematch_log(client, month))

    resp = client.post(
        f"/api/runs/{trip_batch}/delete", json={"confirm": label}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["months_rematched"], resp.text

    log = _rematch_log(client, month)
    assert len(log) > before, "the borrowing month was never re-matched"
    assert log[-1]["trigger"] == "trip"
    assert not any(m["document_id"] == doc for m in _matches(client, month))
    assert _settled_rows(client, month) == [], (
        "the month still names a run that no longer exists"
    )
    assert doc not in (_snapshot(client, month).get("receipt_sources") or {})
    with _store(client) as store:
        assert store.get_claims_by_run(month) == []


def test_deleting_a_trip_receipt_rematches_the_borrowing_month(
    client, monkeypatch
):
    """Same debt, one receipt rather than the whole batch. A trip has no
    statement, so the ordinary `has_statement` re-match never fired."""
    _trip_id, trip_batch, month, doc = _trip_settles_month(
        client, monkeypatch
    )
    before = len(_rematch_log(client, month))

    resp = client.delete(f"/api/runs/{trip_batch}/expenses/{doc}")
    assert resp.status_code == 200, resp.text

    log = _rematch_log(client, month)
    assert len(log) > before, "the borrowing month was never re-matched"
    assert log[-1]["trigger"] == "trip"
    assert not any(m["document_id"] == doc for m in _matches(client, month))
    assert _settled_rows(client, month) == []


# ── durability and robustness ────────────────────────────────────────


def _add_receipt(client, batch_id, fname, body):
    """The GRADUAL-add entrance (`POST .../receipts`), which is a
    different wire from create-with-receipt and needs its own coverage."""
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (fname, JPG + body, "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    return resp


def test_a_receipt_added_to_a_trip_rematches_the_month(client, monkeypatch):
    """The gradual-add entrance: a receipt joining an EXISTING trip batch
    is a pool change for every month the trip spans."""
    _wire(
        monkeypatch,
        _extraction("Other Vendor", "9.99"),
        _extraction("Late Vendor", "17.00"),
        _extraction(),
    )
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    before = len(_rematch_log(client, month))

    resp = _add_receipt(client, trip_batch, "s.jpg", b"7")
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "done"

    log = _rematch_log(client, month)
    assert len(log) > before, "the add never re-matched the month"
    assert log[-1]["trigger"] == "trip"
    staples = [
        r["document_id"] for r in _snapshot(client, trip_batch)["receipts"]
        if "Staples" in str(r.get("detected_vendor") or "")
    ]
    assert staples, "harness: the added receipt was not the Staples one"
    assert any(
        m["document_id"] == staples[0] for m in _matches(client, month)
    ), "the month never picked the added receipt up"


def test_the_debt_survives_a_restart_before_the_loop_runs(
    client, monkeypatch
):
    """The pre-mark, on the ADD path (the entrance that owes inside its
    own lock span). Kill the paying loop after the add has committed: the
    month must still be CARRYING the debt, so `resume_pending_rematches`
    finishes it at boot."""
    from expense_recon.web import service

    _wire(
        monkeypatch,
        _extraction("Other Vendor", "9.99"),
        _extraction("Late Vendor", "17.00"),
        _extraction(),
    )
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    assert _pending(client, month) is None, "harness: a debt was already owed"

    def _killed(*a, **k):
        raise RuntimeError("killed after the commit")

    monkeypatch.setattr(service, "rematch_trip_months", _killed)
    resp = client.post(
        f"/api/expense-batches/{trip_batch}/receipts",
        files=[("files", ("s.jpg", JPG + b"7", "application/octet-stream"))],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "error", "harness: the loop was not killed"

    mark = _pending(client, month)
    assert mark, "the month was left owing nothing after the add committed"
    assert mark.get("trigger") == "trip"


def test_the_debt_survives_a_restart_on_the_create_path(client, monkeypatch):
    """The same pre-mark for create-with-receipt, whose owe happens
    inside `owe_trip_month_rematches` rather than the add's lock span."""
    from expense_recon.web import service

    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    trip_id = _create_trip(client)

    def _killed(*a, **k):
        raise RuntimeError("killed after the commit")

    monkeypatch.setattr(service, "rematch_trip_months", _killed)
    resp = client.post("/api/expense-batches", files=[
        ("files", ("a.jpg", JPG, "application/octet-stream"))
    ], data={
        "legal_entity": "Corporate Services", "label": "TEST - Rome receipts",
        "batch_type": "trip", "trip_id": trip_id,
    })
    assert resp.status_code == 200, resp.text
    assert client.get(
        f"/jobs/{resp.json()['job_id']}"
    ).json()["status"] == "error"

    mark = _pending(client, month)
    assert mark, "the month was left owing nothing after the create committed"
    assert mark.get("trigger") == "trip"


def test_one_failing_month_does_not_abort_the_others(client, monkeypatch):
    """The loop had no per-month try/except, so a raise on the first
    month skipped every month after it. The failure is recorded on that
    month's mark and the rest are still paid."""
    from expense_recon.web import service

    _wire(
        monkeypatch,
        _extraction(),
        _extraction("Late Vendor", "17.00"),
        _extraction("Other Vendor", "9.99"),
    )
    month_a = _create_batch(
        client, label="April 2026", fname="m.jpg", body=b"9"
    )
    month_b = _create_batch(
        client, label="April 2026 again", fname="n.jpg", body=b"8"
    )
    _attach(client, month_a)
    _attach(client, month_b)

    real = service.rematch_after_change
    seen: list[str] = []

    def flaky(store, run_id, **kw):
        seen.append(run_id)
        if len(seen) == 1:
            raise RuntimeError("boom")
        return real(store, run_id, **kw)

    monkeypatch.setattr(service, "rematch_after_change", flaky)

    trip_id = _create_trip(client)
    _create_trip_batch(client, trip_id)

    assert len(seen) == 2, f"the loop stopped after {len(seen)} month(s)"
    failed = _pending(client, seen[0])
    assert failed and failed.get("error"), "the failure was not recorded"


def test_a_legacy_statement_mode_run_is_never_selected(client, monkeypatch):
    """The candidate filter. Only expense-generation runs can borrow from
    a trip, so a legacy run overlapping it is not work to redo."""
    from expense_recon.web import service

    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)

    with _store(client) as store:
        batch = store.get_run(trip_batch)
        assert [r.run_id for r in service.trip_months_covering(
            store, batch
        )] == [month], "harness: the month was not selectable to begin with"
        run = store.get_run(month)
        cfg = dict(run.config or {})
        cfg["mode"] = "reconcile"
        store.update_run_config(month, cfg)
        assert service.trip_months_covering(store, batch) == []


# ── the slot leak ────────────────────────────────────────────────────


def test_a_failed_trip_create_releases_its_slot(client, monkeypatch):
    """The slot was released only on `RunInputError`; any other failure
    held it for the life of the process, so every later create answered
    409 `trip_batch_being_created`."""
    from expense_recon.web import app as web_app

    trip_id = _create_trip(client)
    real = web_app.create_expense_batch

    def _boom(*a, **k):
        raise OSError("disk went away")

    monkeypatch.setattr(web_app, "create_expense_batch", _boom)
    with pytest.raises(OSError):
        client.post("/api/expense-batches", files=[
            ("files", ("a.jpg", JPG, "application/octet-stream"))
        ], data={
            "legal_entity": "Corporate Services",
            "label": "TEST - Rome receipts",
            "batch_type": "trip", "trip_id": trip_id,
        })

    monkeypatch.setattr(web_app, "create_expense_batch", real)
    _wire(monkeypatch, _extraction())
    resp = client.post("/api/expense-batches", files=[
        ("files", ("b.jpg", JPG + b"2", "application/octet-stream"))
    ], data={
        "legal_entity": "Corporate Services",
        "label": "TEST - Rome receipts",
        "batch_type": "trip", "trip_id": trip_id,
    })
    assert resp.status_code == 200, (
        f"the slot leaked: {resp.status_code} {resp.text}"
    )
