"""A duplicate click's reply can carry the month it just re-matched
(2026-10-07, "removing duplicates takes way too long to load").

After "Delete this copy" or "Not a copy" the Expenses page waited for the
re-match, then refetched `GET /api/expense-batches/{id}` and
`GET /api/runs/{id}`, building the month twice more on the one machine. With
`?views=1` the reply carries both payloads under `views` (`batch`, `run`),
equal to what those GETs serve at that moment, so the page can cache them
instead. Without it the reply is unchanged.
"""
from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from tests.test_copies_out_of_totals import (  # noqa: E402
    _attach,
    _batch,
    _copy_id,
    _wire,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        yield c

STATEMENT = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "LOVABLE SEAT", "Sale", -16.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]


def _gets(client, batch_id):
    batch = client.get(f"/api/expense-batches/{batch_id}")
    run = client.get(f"/api/runs/{batch_id}")
    assert batch.status_code == 200 and run.status_code == 200
    return batch.json(), run.json()


def _assert_views_are_the_gets(client, batch_id, reply):
    batch, run = _gets(client, batch_id)
    assert reply["views"]["batch"] == batch
    assert reply["views"]["run"] == run
    return batch, run


def test_delete_this_copy_replies_with_the_reconciled_month(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, STATEMENT)
    copy_id = _copy_id(client.get(f"/api/expense-batches/{batch_id}").json())

    resp = client.delete(f"/api/runs/{batch_id}/expenses/{copy_id}?views=1")
    assert resp.status_code == 200, resp.text
    reply = resp.json()
    assert "rematch" in reply, "a statement month re-matches on delete"
    batch, _run = _assert_views_are_the_gets(client, batch_id, reply)
    assert reply["summary"] == batch["summary"]
    assert copy_id not in {e["document_id"] for e in batch["expenses"]}


def test_not_a_copy_replies_with_the_collecting_month(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    (group,) = client.get(f"/api/expense-batches/{batch_id}").json()["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve?views=1",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    reply = resp.json()
    batch, _run = _assert_views_are_the_gets(client, batch_id, reply)
    # Unchanged meaning: the grid's own summary, already counting the copy.
    assert reply["summary"] == batch["summary"]
    assert reply["summary"]["n_expenses"] == 3


def test_not_a_copy_replies_with_the_reconciled_month(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, STATEMENT)
    (group,) = client.get(f"/api/expense-batches/{batch_id}").json()["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve?views=1",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    reply = resp.json()
    _batch_view, run = _assert_views_are_the_gets(client, batch_id, reply)
    # A reconciling month keeps replying with the run's summary.
    assert reply["summary"] == run["summary"]


def test_without_the_flag_the_reply_is_unchanged(client, monkeypatch):
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, STATEMENT)
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    (group,) = grid["duplicate_groups"]

    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200 and "views" not in resp.json()
    resp = client.delete(f"/api/runs/{batch_id}/expenses/{_copy_id(grid)}")
    assert resp.status_code == 200 and "views" not in resp.json()
    _batch_view, run = _gets(client, batch_id)
    assert resp.json()["summary"] == _batch_view["summary"]
