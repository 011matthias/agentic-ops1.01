"""Item 50: the probe that makes the next "Failed to fetch" provable.

Criss's September failure could not be explained because a fetch that
rejects never reaches the app: no server log could contain it, and the
machine that served that hour was replaced with its logs. The hosting
theory (a cold start) died when the live machine turned out to be pinned
always-on, leaving the failure unexplained and the probe as the open half.

These tests go through the routes, never through `machine.py` or the store
directly, so what they pin is the WIRING: the report lands, this process's
identity and age are stamped on it, and the decisive comparison
(`process_predates_failure`) is computed and stored.

The test that matters most is the one where the process is YOUNGER than the
failure: that is the machine-was-replaced signature, and it is the answer
the September incident could not produce.
"""
from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web import machine  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402


def _process_age(monkeypatch, seconds: float) -> None:
    """Make this process read as `seconds` old.

    Moves the clock only; every line of the comparison stays real. A
    test process is milliseconds old, so without this the honest answer
    to "was the process already running half a second ago" is no, and a
    test asserting otherwise would be asserting an untruth about its own
    environment rather than pinning the code.
    """
    monkeypatch.setattr(machine, "_STARTED_MONOTONIC", time.monotonic() - seconds)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _report(client, **body):
    resp = client.post("/api/client-errors", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(client, **params):
    resp = client.get("/api/client-errors", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- healthz says what this process is ---------------------------------


def test_healthz_keeps_status_and_gains_the_server_block(client):
    """Parallel field (contract rule 1): `status` is untouched, so a caller
    that only reads it sees exactly what it saw before."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    server = body["server"]
    assert set(server) == {"machine", "region", "app", "started_at", "uptime_s"}
    assert server["uptime_s"] >= 0
    assert server["started_at"]


def test_the_machine_identity_is_absent_not_invented_off_fly(client, monkeypatch):
    """Off Fly the identity is empty, never a plausible-looking id: a local
    row must not read like a production one (B4)."""
    server = client.get("/healthz").json()["server"]
    assert server["machine"] == "" and server["region"] == ""


# --- the report lands, stamped with this process ------------------------


def test_a_failure_report_is_stored_with_the_serving_process_stamped(client):
    out = _report(
        client,
        kind="fetch-failed",
        url="https://brisken-expense-recon.fly.dev/api/expense-batches/x/statement",
        method="post",
        message="Failed to fetch",
        occurred_at="2026-09-10T10:00:43Z",
        seconds_ago=4.0,
        duration_ms=1200,
        online=True,
        detail={"dialog": "attach-statement", "file": "August2026.xlsx"},
    )
    assert out["ok"] is True and out["recorded"] is True
    assert out["server"]["uptime_s"] >= 0

    row = _rows(client)["client_errors"][0]
    assert row["message"] == "Failed to fetch"
    assert row["method"] == "POST"  # normalized
    assert row["occurred_at"] == "2026-09-10T10:00:43Z"
    assert row["seconds_ago"] == 4.0
    assert row["duration_ms"] == 1200
    assert row["online"] == 1
    assert "August2026.xlsx" in row["detail"]
    # The stamp: which process took the report, and how old it was.
    assert row["process_started_at"] and row["uptime_s"] >= 0
    assert row["received_at"]


def test_a_process_older_than_the_failure_did_not_restart(client, monkeypatch):
    """The common case, and the one that must NOT read as a restart: the
    failure was a moment ago and this process was already running."""
    _process_age(monkeypatch, 3600)
    out = _report(client, message="Failed to fetch", seconds_ago=0.5)
    assert out["process_predates_failure"] == 1
    assert _rows(client)["client_errors"][0]["process_predates_failure"] == 1


def test_a_process_younger_than_the_failure_proves_a_replacement(
    client, monkeypatch,
):
    """THE signature. A failure a full day ago cannot predate a process
    started seconds ago, so the machine that served it is gone. This is the
    answer September could not produce, and it is computed from the row
    alone rather than from logs that die with the machine."""
    _process_age(monkeypatch, 30)
    out = _report(client, message="Failed to fetch", seconds_ago=86_400.0)
    assert out["process_predates_failure"] == 0
    assert _rows(client)["client_errors"][0]["process_predates_failure"] == 0


def test_an_unknown_failure_time_never_reads_as_a_restart(client):
    """Unknown must stay unknown. A false "the machine restarted" would
    send the next investigation back to the hosting theory that already
    cost this item a cycle."""
    out = _report(client, message="Failed to fetch")
    assert out["process_predates_failure"] is None
    assert _rows(client)["client_errors"][0]["process_predates_failure"] is None

    # A garbage, negative or non-finite elapsed time is unknown too, never
    # a restart. JSON has no NaN literal, so the string is the shape a
    # client could actually send; float("nan") parses it happily.
    for bad in ("soon", -5, "nan"):
        _report(client, message="Failed to fetch", seconds_ago=bad)
    assert all(
        r["process_predates_failure"] is None
        for r in _rows(client)["client_errors"][:3]
    )


# --- the probe must never become a second failure -----------------------


def test_a_malformed_report_is_accepted_rather_than_erroring(client):
    """The caller is a browser that has already hit one failure; answering
    it with a second one helps nobody. Anything parses to a row."""
    resp = client.post("/api/client-errors", content=b"not json at all",
                       headers={"Content-Type": "application/json"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["recorded"] is True

    resp = client.post("/api/client-errors", json=["a", "list"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["recorded"] is True

    row = _rows(client)["client_errors"][0]
    assert row["kind"] == "fetch-failed"  # the default, not an empty row


def test_oversized_fields_are_capped_not_rejected(client):
    _report(client, url="u" * 4000, message="m" * 4000, kind="k" * 400,
            detail={"blob": "x" * 9000})
    row = _rows(client)["client_errors"][0]
    assert len(row["url"]) == 500
    assert len(row["message"]) == 500
    assert len(row["kind"]) == 40
    assert len(row["detail"]) <= 2000


def test_a_retry_loop_is_dropped_so_it_cannot_erase_the_signal(client):
    """A broken client can retry forever; an unbounded loop would push the
    interesting older rows out of a bounded table."""
    first = _report(client, message="Failed to fetch", seconds_ago=1.0)
    assert first["recorded"] is True
    outs = [_report(client, message="flood") for _ in range(25)]
    assert any(o["recorded"] is False for o in outs)
    dropped = [o for o in outs if o["recorded"] is False]
    assert dropped[0]["reason"] == "rate-limited"
    # Dropped reports still answer 200 with the server block, so the
    # client never sees the probe itself fail.
    assert dropped[0]["server"]["uptime_s"] >= 0
    # The first, real report survived the flood.
    assert any(
        r["message"] == "Failed to fetch"
        for r in _rows(client, limit=100)["client_errors"]
    )


# --- reading them back --------------------------------------------------


def test_the_list_is_newest_first_and_carries_the_stated_limit(client):
    for i in range(3):
        _report(client, message=f"failure {i}", seconds_ago=1.0)
    out = _rows(client)
    assert [r["message"] for r in out["client_errors"][:3]] == [
        "failure 2", "failure 1", "failure 0",
    ]
    assert "not proof that nothing failed" in out["note"]
    assert out["server"]["started_at"]


def test_an_empty_log_says_so_without_implying_nothing_failed(client):
    out = _rows(client)
    assert out["client_errors"] == []
    assert "not proof that nothing failed" in out["note"]


def test_the_probe_is_behind_the_same_gate_as_every_other_api_route(
    tmp_path, monkeypatch,
):
    """The failures worth catching happen inside a live session, so the
    gate costs no coverage and keeps an unauthenticated write off a public
    host."""
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", "test-code-1234")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.post("/api/client-errors", json={}).status_code == 401
        assert c.get("/api/client-errors").status_code == 401
        # /healthz stays open: a health probe that needs a session is not
        # a health probe.
        assert c.get("/healthz").status_code == 200

        token = c.post("/api/login", json={"code": "test-code-1234"}).json()["token"]
        head = {"Authorization": f"Bearer {token}"}
        assert c.post("/api/client-errors", json={"message": "x"},
                      headers=head).status_code == 200
        rows = c.get("/api/client-errors", headers=head).json()["client_errors"]
        # The session's own operator label rides the row, so a recurrence
        # names who hit it.
        assert rows[0]["operator"]
