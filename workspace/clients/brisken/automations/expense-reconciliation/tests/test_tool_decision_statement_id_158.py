"""The TOOL's own verdict carries the statement id too (backlog item 158).

Item 152 (note item T3) put `statement_id` on `decisions`, `decision_history`
and `receipt_claims`, and wired the stamp into all five writers that touch
`decisions`. Four of the five were covered. `set_tool_decision` was not: the
T3 fixture attaches a workbook whose charges pair with nothing, so its month
ends with no `decided_by='tool'` row at all, and the one wire nobody reached
is the one nobody knew was working.

A transaction id is content-derived and MOVES when a file is re-parsed; the
statement it was printed on does not. That is the whole point of the column,
and a verdict the TOOL wrote is the most common kind on a real month: the
self-confirm rule (item 76) decides every clean exact pair without anyone
clicking. An unstamped tool verdict would be exactly the row a reader could
not trace back to its line.

The route that reaches it is the self-confirm rule, which runs inside
`rematch_month`, which runs on statement attach. So the fixture here is the
one from `tests/test_self_confirm.py`: a receipt that pairs exactly with the
example statement's STAPLES NYC charge, and a merchant registry entry that
settles the category so the row's review state is `ready`. Everything runs
through the FastAPI app.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
STATEMENT = EXAMPLES / "statement.example.csv"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
DOC_ID = "0000__a.jpg"
OFFICE = "Office Supplies & Consumables"
OFFICE_ACCOUNT = "6100 Office Supplies"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _job_done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job


def _month(client, monkeypatch) -> str:
    """A month whose attach ends in a tool verdict, per `test_self_confirm`."""
    assert client.put("/api/settings", json={"merchants": {
        "Staples": {"aliases": ["STAPLES NYC"], "category": OFFICE,
                    "zoho_account": OFFICE_ACCOUNT},
    }}).status_code == 200
    mock = MockLLMClient(extraction_responses=[ExtractedReceipt(
        date="2026-04-15", total="42.50", currency="USD", vendor="STAPLES NYC",
        reference="", line_items=(), confidence=0.9, notes="",
    )])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "April 2026"},
    )
    _job_done(client, resp)
    batch_id = resp.json()["batch_id"]
    _job_done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG + b"a.jpg", "application/octet-stream"))],
    ))
    _job_done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv", STATEMENT.read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))
    return batch_id


def _db(client) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(client._data_root) / "recon-web.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def _expected_id() -> str:
    return hashlib.sha256(STATEMENT.read_bytes()).hexdigest()[:16]


def _tool_rows(client, batch_id) -> list[sqlite3.Row]:
    with _db(client) as conn:
        return conn.execute(
            "SELECT transaction_id, status, chosen_document_id, decided_by, "
            "decided_rule, statement_id FROM decisions "
            "WHERE run_id = ? AND decided_by = 'tool' ORDER BY transaction_id",
            (batch_id,),
        ).fetchall()


def test_the_fixture_really_reaches_the_tools_writer(client, monkeypatch):
    """The premise, asserted before the thing it is the premise for.

    The T3 round assumed a fresh month already held a tool verdict and it did
    not, which is how the wire went uncovered. If a later change stops the
    self-confirm rule from firing here, this test says so plainly instead of
    letting the stamp test below pass over an empty table.
    """
    batch_id = _month(client, monkeypatch)

    rows = _tool_rows(client, batch_id)
    assert len(rows) == 1, [dict(r) for r in rows]
    (row,) = rows
    assert row["decided_by"] == "tool"
    assert row["status"] == "confirmed"
    assert row["chosen_document_id"] == DOC_ID
    assert row["decided_rule"] == "exact_vendor_75", (
        "written by the self-confirm rule, not by a person"
    )

    # And the row the page shows agrees, so the DB row under test is the
    # verdict the reviewer actually sees.
    view = client.get(f"/api/runs/{batch_id}").json()
    shown = next(r for r in view["rows"] if "STAPLES" in r["vendor"])
    assert shown["decided_by"] == "tool"
    assert shown["transaction_id"] == row["transaction_id"]


def test_a_tool_verdict_names_the_statement_it_was_printed_on(
    client, monkeypatch
):
    """The item itself: `set_tool_decision`'s stamp, exercised at last."""
    batch_id = _month(client, monkeypatch)

    (row,) = _tool_rows(client, batch_id)
    assert row["statement_id"] == _expected_id(), (
        "the tool's own verdict carries the id of the upload it was read from"
    )

    # The id is the upload's, not a value invented for the row: the month's
    # statement entry names the same one.
    run = client.get(f"/api/runs/{batch_id}").json()
    (entry,) = run["statements"]
    assert entry["statement_id"] == row["statement_id"]


def test_the_tools_verdict_is_stamped_the_same_way_a_persons_is(
    client, monkeypatch
):
    """A person's later verdict on the same charge leaves the id alone.

    The two writers stamp from one source (`_charge_origins`), so a row that
    changes hands keeps naming the line it was printed on. This is the
    regression that would bite if a future writer stamped from the caller's
    arguments instead of from the snapshot.
    """
    batch_id = _month(client, monkeypatch)
    (before,) = _tool_rows(client, batch_id)

    resp = client.post(f"/api/runs/{batch_id}/decisions", json={
        "transaction_id": before["transaction_id"],
        "status": "rejected",
        "chosen_document_id": None,
    })
    assert resp.status_code == 200, resp.text

    with _db(client) as conn:
        after = conn.execute(
            "SELECT decided_by, status, statement_id FROM decisions "
            "WHERE run_id = ? AND transaction_id = ?",
            (batch_id, before["transaction_id"]),
        ).fetchone()
    assert after["decided_by"] != "tool", "the person took it over"
    assert after["status"] == "rejected"
    assert after["statement_id"] == before["statement_id"] == _expected_id()
