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
    assert set(server) == {
        "machine", "region", "app", "commit", "image", "started_at", "uptime_s",
    }
    assert server["uptime_s"] >= 0
    assert server["started_at"]


def test_the_machine_identity_is_absent_not_invented_off_fly(client, monkeypatch):
    """Off Fly the identity is empty, never a plausible-looking id: a local
    row must not read like a production one (B4)."""
    server = client.get("/healthz").json()["server"]
    assert server["machine"] == "" and server["region"] == ""


# --- build identity: which commit is this (backlog item 120) -----------
#
# These go through /healthz rather than through machine.py, because the
# thing worth pinning is the WIRING. A green machine.py proves a helper
# works; it does not prove the health route carries what the helper
# returns, and the route is the only surface an emergency actually reads.


def test_healthz_reports_the_commit_the_image_was_built_from(client, monkeypatch):
    """The item's headline ask: the running app says which commit it is.

    The value is read from the environment the image baked it into, so
    this asserts the whole path the deploy uses, not a constant.
    """
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "0123456789abcdef0123456789abcdef01234567")
    server = client.get("/healthz").json()["server"]
    assert server["commit"] == "0123456789abcdef0123456789abcdef01234567"


def test_healthz_reports_the_image_fly_actually_booted(client, monkeypatch):
    """`image` is the join back to a release: it is the same string
    `flyctl releases --image` prints, so a running process can be tied to
    the release that produced it without correlating timestamps."""
    ref = "registry.fly.io/brisken-expense-recon:deployment-01TESTTESTTESTTESTTEST"
    monkeypatch.setenv("FLY_IMAGE_REF", ref)
    server = client.get("/healthz").json()["server"]
    assert server["image"] == ref


def test_an_unstamped_build_says_nothing_rather_than_guessing(client, monkeypatch):
    """The one failure this design still allows is absence, and absence has
    to read as absence.

    A deploy that omits --build-arg bakes an empty string. Reporting ""
    tells the reader "I cannot say"; reporting a git read from the
    container, or a plausible-looking default, would tell them something
    false in the one place they are trusting to be literal. Wrong identity
    is worse than no identity, so this pins the blank.
    """
    monkeypatch.delenv("EXPENSE_RECON_COMMIT", raising=False)
    monkeypatch.delenv("FLY_IMAGE_REF", raising=False)
    server = client.get("/healthz").json()["server"]
    assert server["commit"] == ""
    assert server["image"] == ""


def test_build_identity_does_not_disturb_the_uptime_probe_contract(client, monkeypatch):
    """House rule 1, parallel fields only. tools/recon_uptime_probe.py reads
    `status`, `disk.available`, `disk.intake_refusing` and `disk.free_pct`
    every ten minutes and opens an issue when they are wrong; the SPA reads
    this endpoint too. Adding build identity must leave all of that with
    the same names, types and meanings."""
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "deadbeef")
    body = client.get("/healthz").json()
    assert body["status"] == "ok"
    disk = body["disk"]
    assert isinstance(disk["available"], bool)
    assert isinstance(disk["intake_refusing"], bool)
    assert isinstance(disk["free_pct"], (int, float))


def test_the_failure_list_names_the_build_reading_it(client, monkeypatch):
    """One source, so the two surfaces can never disagree.

    Both /healthz and this list stamp machine.snapshot(), so the build
    identity an investigator reads beside the failures is the same string
    the health probe reports, with no second stamp to keep in step.

    `server` here is the process READING the rows. Which build served each
    individual failure is on the row itself (`server_commit`), stamped when
    the report arrived; the two are different questions and the next block
    pins the difference.
    """
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "cafebabe0000111122223333444455556666aaaa")
    _report(client, kind="fetch-failed", seconds_ago=5)
    out = _rows(client)
    assert out["client_errors"], "the report should have landed"
    assert out["server"]["commit"] == "cafebabe0000111122223333444455556666aaaa"


# --- which build served the failure (item 120, 2026-09-21) -------------
#
# Until this shipped a stored row carried `machine` and
# `process_started_at` but no build identity, so "which build was the
# browser talking to when this broke" was answerable only while the
# serving process was still up. Once it restarted the route was
# correlating a timestamp against Fly's release list by hand, which is the
# exact work /healthz.server.commit was added to end.
#
# These go through the routes for the same reason the rest of this module
# does: a green store proves the column exists, not that the handler fills
# it from the serving process.


def test_a_stored_failure_names_the_build_that_served_it(client, monkeypatch):
    """The row answers the question on its own, with no release list."""
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "1111111111111111111111111111111111111111")
    monkeypatch.setenv(
        "FLY_IMAGE_REF",
        "registry.fly.io/brisken-expense-recon:deployment-01AAAA",
    )
    _report(client, message="Failed to fetch", seconds_ago=2.0)
    row = _rows(client)["client_errors"][0]
    assert row["server_commit"] == "1111111111111111111111111111111111111111"
    assert row["server_image"] == (
        "registry.fly.io/brisken-expense-recon:deployment-01AAAA"
    )


def test_the_row_keeps_the_build_that_served_it_when_a_later_one_reads(
    client, monkeypatch,
):
    """THE property, and the only one worth the migration.

    A failure is investigated after the fact, from a process that is by
    then a different build. If the row were stamped at read time it would
    name the build doing the reading and send the investigation to the
    wrong release, which is worse than the blank it replaced. So: report
    under build A, redeploy to build B, read. The row must still say A
    while `server` says B.
    """
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    _report(client, message="Failed to fetch", seconds_ago=2.0)

    # The deploy: same process, a new build answering from here on.
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    out = _rows(client)
    assert out["server"]["commit"] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    assert out["client_errors"][0]["server_commit"] == (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


def test_an_unstamped_build_stores_blank_rather_than_a_guess(client, monkeypatch):
    """Same trade as /healthz: absence reads as absence.

    A deploy that omits --build-arg bakes an empty string, and the row says
    so. Writing a plausible-looking commit into a diagnostic row would be
    wrong identity, which costs an investigation more than no identity
    does.
    """
    monkeypatch.delenv("EXPENSE_RECON_COMMIT", raising=False)
    monkeypatch.delenv("FLY_IMAGE_REF", raising=False)
    _report(client, message="Failed to fetch", seconds_ago=2.0)
    row = _rows(client)["client_errors"][0]
    assert row["server_commit"] == ""
    assert row["server_image"] == ""


def test_rows_written_before_the_column_read_empty_not_back_filled(
    tmp_path, monkeypatch,
):
    """The live volume's own path: a database whose `client_errors` predates
    the column, carrying rows nothing can attribute.

    Built by creating the table with the OLD definition before the app ever
    opens the file, so `CREATE TABLE IF NOT EXISTS` skips it and the
    migration is what has to add the columns; that is exactly what happens
    on `/data` at the next deploy.

    The legacy row must read empty. Back-filling it could only write the
    build doing the back-fill, which is a false answer in the one place an
    investigation is trusting to be literal.
    """
    import sqlite3

    db = tmp_path / "recon-web.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE client_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            received_ts REAL NOT NULL,
            operator TEXT NOT NULL,
            caller TEXT NOT NULL,
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            method TEXT NOT NULL,
            message TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            seconds_ago REAL,
            duration_ms INTEGER,
            online INTEGER,
            detail TEXT NOT NULL,
            machine TEXT NOT NULL,
            region TEXT NOT NULL,
            process_started_at TEXT NOT NULL,
            uptime_s REAL NOT NULL,
            process_predates_failure INTEGER
        )
        """
    )
    conn.execute(
        "INSERT INTO client_errors (received_at, received_ts, operator, "
        "caller, kind, url, method, message, occurred_at, detail, machine, "
        "region, process_started_at, uptime_s) VALUES "
        "('2026-09-10T10:00:00Z', 1.0, 'operator', '1.2.3.4', "
        "'fetch-failed', '/api/x', 'POST', 'Failed to fetch', "
        "'2026-09-10T10:00:00Z', '', '148e...', 'fra', "
        "'2026-09-10T09:00:00Z', 3600.0)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.setenv("EXPENSE_RECON_COMMIT", "cccccccccccccccccccccccccccccccccccccccc")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        rows = c.get("/api/client-errors").json()["client_errors"]
        assert len(rows) == 1
        # The column exists (the read did not raise) and says nothing.
        assert rows[0]["server_commit"] == ""
        assert rows[0]["server_image"] == ""
        assert rows[0]["message"] == "Failed to fetch"  # the row survived

        # And a NEW report on the migrated database is stamped.
        assert c.post("/api/client-errors", json={"message": "new"}).status_code == 200
        fresh = c.get("/api/client-errors").json()["client_errors"][0]
        assert fresh["server_commit"] == "cccccccccccccccccccccccccccccccccccccccc"


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
