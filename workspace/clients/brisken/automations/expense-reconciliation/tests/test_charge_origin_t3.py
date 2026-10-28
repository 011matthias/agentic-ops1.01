"""Note item T3 (2026-09-18): the receipt-to-line link survives as a record.

Item 150 gave the statement UPLOAD an identity. This is the other half: a
booked expense can name the statement line it settles, and a stored verdict
still names that line after the month has been re-read and its charges have
new ids.

Three records get it. The payloads carry the charge's origin
(`statement_file`, `statement_id`, and `source_row` for a workbook line or
`source_page` for a PDF one) on `rows[]` and, through the settling charge,
on `expenses[]`. The `decisions`, `decision_history` and `receipt_claims`
tables carry the `statement_id` beside the transaction id, because a
transaction id is content-derived and moves when a file is re-parsed while
the statement it was printed on does not.

Everything here runs through the FastAPI app.
"""
from __future__ import annotations

import hashlib
import io
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.ingest.statement_pdf import (  # noqa: E402
    _page_starts,
    parse_statement_text,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.statement_origin import origins_from_snapshot  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

HEADERS = ("Date", "Description", "Type", "Amount")
# Row 2 of the sheet is the first charge (row 1 is the header).
ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    (datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
]

ATTACH_FORM = {
    "account_id": "card-2838",
    "account_legal_entities": '{"card-2838": "Corporate Services"}',
    "account_card_currency": "USD",
}

# A two-page Chase statement, split where a real one splits: the charges run
# past the page break and the cycle marker lands on page 2.
PDF_PAGE_1 = """\
Opening/Closing Date 07/04/26 - 08/03/26
ACCOUNT ACTIVITY
07/05 COFFEE SHOP NYC 5.75
"""
PDF_PAGE_2 = """\
Page 2 of 2
07/10 AWS CLOUD SERVICES 100.00
TRANSACTIONS THIS CYCLE (CARD 1176) $105.75
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock = MockLLMClient(extraction_responses=[
        ExtractedReceipt(
            date="2026-08-30", total="96.00", currency="USD", vendor="Obsidian",
            reference="", line_items=(), confidence=0.9, notes="",
            payment_hint=None,
        ),
    ])
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _create_batch(client, label="August 2026") -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("obsidian.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, payload: bytes, filename="August2026.xlsx"):
    return _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            filename, payload,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data=dict(ATTACH_FORM),
    ))


def _expected_id(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:16]


def _run(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row_for(view: dict, vendor: str) -> dict:
    hits = [r for r in view["rows"] if vendor in r["vendor"].upper()]
    assert len(hits) == 1, [r["vendor"] for r in view["rows"]]
    return hits[0]


def _db(client) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(client._data_root) / "recon-web.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def _snapshot(client, batch_id) -> dict:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return store.get_run(batch_id).snapshot or {}


# ── the charge side, on both payloads ─────────────────────────────────


def test_a_workbook_charge_names_its_upload_and_its_sheet_row(client):
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)

    run = _run(client, batch_id)
    (entry,) = run["statements"]
    rows = {r["vendor"]: r for r in run["rows"]}
    assert len(rows) == 3

    # The header is sheet row 1, so the three charges are rows 2, 3 and 4 in
    # the order the file prints them.
    assert [rows[v]["source_row"] for v in ("LOVABLE", "OBSIDIAN",
                                            "PRESSMASTER DMCC")] == [2, 3, 4]
    for row in rows.values():
        assert row["statement_file"] == entry["file"]
        assert row["statement_id"] == _expected_id(payload) == entry["statement_id"]
        assert "source_page" not in row, "a workbook line has no page"


def test_a_charge_from_a_month_with_no_statement_carries_no_origin(client):
    batch_id = _create_batch(client)
    grid = _grid(client, batch_id)
    assert not grid["has_statement"]
    (expense,) = grid["expenses"]
    # Absent, never null: nothing has been recorded, and a reader must be
    # able to tell that from "recorded as nothing".
    for key in ("statement_file", "statement_id", "source_row",
                "source_page", "transaction_id"):
        assert key not in expense, key


def test_a_month_recorded_before_the_origins_key_still_resolves_its_rows(client):
    """The live months on 2026-09-18. `statement_origins` did not exist when
    their statements were attached, so the anchors are the only record of
    which upload printed which charge, and they still answer for a
    workbook. The `statement_id` stays absent until the next re-read, which
    is exactly what item 150 says about those entries."""
    batch_id = _create_batch(client)
    _attach(client, batch_id, _xlsx_bytes(ROWS))

    path = Path(client._data_root) / "recon-web.sqlite"
    with RunStore(path) as store:
        run = store.get_run(batch_id)
        aged = dict(run.snapshot)
        aged.pop("statement_origins")
        aged["statements"] = [
            {k: v for k, v in e.items() if k != "statement_id"}
            for e in aged["statements"]
        ]
        store.update_run_snapshot(batch_id, aged)

    run = _run(client, batch_id)
    row = _row_for(run, "OBSIDIAN")
    assert row["source_row"] == 3, "recovered from the writeback anchors"
    assert row["statement_file"] == "August2026.xlsx"
    assert "statement_id" not in row, "not recorded until the next re-read"


def test_a_pdf_charge_records_the_page_it_was_printed_on(client, monkeypatch):
    """A PDF statement has no tabular row, so until this the three August
    2026 charges from `20260804-statements-1176-.pdf` had no place on their
    statement at all. The anchors cannot hold them (they are the
    writeback's row map, and a PDF's is deliberately empty), so the origins
    record is what names their upload as well as their page."""
    monkeypatch.setattr(
        "expense_recon.ingest.statement_pdf._extract_pages",
        lambda path: [PDF_PAGE_1, PDF_PAGE_2],
    )
    batch_id = _create_batch(client)
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("chase.pdf", b"%PDF-1.4 synthetic",
                             "application/pdf")},
        data=dict(ATTACH_FORM),
    ))

    run = _run(client, batch_id)
    coffee, aws = _row_for(run, "COFFEE SHOP"), _row_for(run, "AWS CLOUD")
    assert coffee["source_page"] == 1
    assert aws["source_page"] == 2, "the charge past the page break"
    for row in (coffee, aws):
        assert row["statement_file"] == "chase.pdf"
        assert row["statement_id"] == _expected_id(b"%PDF-1.4 synthetic")
        assert "source_row" not in row, "a PDF line has no sheet row"


def test_page_starts_indexes_the_join_the_parser_reads(client):
    """The page map has to be an index over the SAME join the parser splits,
    or every page number is off by the number of pages before it."""
    pages = [PDF_PAGE_1, PDF_PAGE_2]
    joined = "\n".join(pages)
    starts = _page_starts(pages)
    lines = joined.splitlines()
    assert lines[starts[0]].startswith("Opening/Closing Date")
    assert lines[starts[1]] == "Page 2 of 2"

    # And with no map at all (synthetic text, every CLI test), no page is
    # invented.
    txs, _ = parse_statement_text(
        joined, file_name="x.pdf", legal_entity_id="Corporate Services",
    )
    assert txs and all(t.source_page is None for t in txs)


# ── the receipt side: a booked expense names its line ─────────────────


def _pair(client, batch_id, tx_id, document_id):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": "confirmed",
              "chosen_document_id": document_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_a_booked_expense_carries_the_statement_line_it_settles(client):
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)

    run = _run(client, batch_id)
    charge = _row_for(run, "OBSIDIAN")
    grid = _grid(client, batch_id)
    (expense,) = grid["expenses"]
    _pair(client, batch_id, charge["transaction_id"], expense["document_id"])

    booked = _grid(client, batch_id)["expenses"][0]
    assert booked["transaction_id"] == charge["transaction_id"]
    assert booked["statement_id"] == _expected_id(payload)
    assert booked["source_row"] == 3
    assert booked["statement_file"] == "August2026.xlsx"


def test_a_released_expense_loses_the_charge_side_again(client):
    """The charge side is read from the month's EFFECTIVE settlement, not
    from the raw outcome, so a rejected pairing takes the statement line
    off the expense the way it takes the receipt off the charge. Reading
    the raw matches here would re-open the split item 103 closed."""
    batch_id = _create_batch(client)
    _attach(client, batch_id, _xlsx_bytes(ROWS))
    charge = _row_for(_run(client, batch_id), "OBSIDIAN")
    settled = _grid(client, batch_id)["expenses"][0]
    assert settled["transaction_id"] == charge["transaction_id"], (
        "the matcher paired the 96.00 receipt with the 96.00 charge"
    )

    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": charge["transaction_id"],
              "status": "rejected", "chosen_document_id": None},
    )
    assert resp.status_code == 200, resp.text

    released = _grid(client, batch_id)["expenses"][0]
    for key in ("transaction_id", "statement_id", "source_row",
                "statement_file"):
        assert key not in released, key


# ── the stored records ────────────────────────────────────────────────


def test_a_decision_a_history_line_and_a_claim_all_name_the_statement(client):
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)
    sid = _expected_id(payload)

    run = _run(client, batch_id)
    charge = _row_for(run, "OBSIDIAN")
    (expense,) = _grid(client, batch_id)["expenses"]
    _pair(client, batch_id, charge["transaction_id"], expense["document_id"])

    with _db(client) as conn:
        decision = conn.execute(
            "SELECT statement_id FROM decisions WHERE run_id = ? "
            "AND transaction_id = ?",
            (batch_id, charge["transaction_id"]),
        ).fetchone()
        assert decision["statement_id"] == sid

        line = conn.execute(
            "SELECT row_key, row_kind, statement_id FROM decision_history "
            "WHERE run_id = ? AND field = 'decision' ORDER BY id DESC LIMIT 1",
            (batch_id,),
        ).fetchone()
        assert line["row_key"] == charge["transaction_id"]
        assert line["statement_id"] == sid, "the ledger line names the document"

        claim = conn.execute(
            "SELECT transaction_id, statement_id FROM receipt_claims "
            "WHERE claimed_by_run_id = ?", (batch_id,),
        ).fetchone()
        assert claim["transaction_id"] == charge["transaction_id"]
        assert claim["statement_id"] == sid


def test_a_history_line_about_a_receipt_names_the_charge_it_is_booked_against(
    client,
):
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)

    run = _run(client, batch_id)
    charge = _row_for(run, "OBSIDIAN")
    (expense,) = _grid(client, batch_id)["expenses"]
    _pair(client, batch_id, charge["transaction_id"], expense["document_id"])

    resp = client.post(
        f"/api/runs/{batch_id}/categories",
        json={"document_id": expense["document_id"], "line_index": 0,
              # A real bucket: since item 3c a string from neither
              # vocabulary is dropped under `ignored`, not stored.
              "category": "Software & Subscriptions"},
    )
    assert resp.status_code == 200, resp.text

    with _db(client) as conn:
        line = conn.execute(
            "SELECT row_kind, statement_id FROM decision_history "
            "WHERE run_id = ? AND field = 'receipt_category' "
            "ORDER BY id DESC LIMIT 1", (batch_id,),
        ).fetchone()
    assert line is not None, "item 104 records a category change"
    assert line["row_kind"] == "receipt"
    assert line["statement_id"] == _expected_id(payload)


# ── end to end: the link survives a re-read ───────────────────────────


def test_the_link_survives_a_re_read_that_rekeys_every_charge(client):
    """The whole point. A re-read re-parses the stored files, so a charge's
    content-derived id can change and `rekey_decisions` moves the verdict
    onto the new one. The statement the line was printed on does not change,
    so the booked expense still resolves to the same receipt, the same
    upload and the same sheet row."""
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)
    sid = _expected_id(payload)

    run = _run(client, batch_id)
    charge = _row_for(run, "OBSIDIAN")
    (expense,) = _grid(client, batch_id)["expenses"]
    document_id = expense["document_id"]
    _pair(client, batch_id, charge["transaction_id"], document_id)

    before = _grid(client, batch_id)["expenses"][0]
    assert (before["statement_id"], before["source_row"]) == (sid, 3)

    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/statements/reread"
    ))

    after = _grid(client, batch_id)["expenses"][0]
    assert after["document_id"] == document_id, "the same receipt"
    assert after["statement_id"] == sid, "the same upload, same bytes"
    assert after["source_row"] == 3, "the same sheet row"
    assert after["transaction_id"] == charge["transaction_id"], (
        "the same file re-parsed gives the same content id"
    )

    with _db(client) as conn:
        decision = conn.execute(
            "SELECT statement_id FROM decisions WHERE run_id = ? "
            "AND transaction_id = ?", (batch_id, after["transaction_id"]),
        ).fetchone()
    assert decision["statement_id"] == sid

    # And the re-read rebuilt the record itself rather than leaving the
    # attach's copy behind.
    origins = origins_from_snapshot(_snapshot(client, batch_id))
    assert origins[after["transaction_id"]]["source_row"] == 3
    assert origins[after["transaction_id"]]["statement_id"] == sid


def test_a_decision_row_written_before_the_column_gains_the_id_on_the_next_verdict(
    client,
):
    """Every decision row on the live volume is NULL here, because the column
    did not exist when they were written. The next verdict on that charge
    fills it in.

    This is also the only case that exercises `set_decision`'s own stamp.
    Blanking the column first is what makes the reviewer's write the one
    under test: without it the row already carries the id from the attach.

    Corrected 2026-09-20 (backlog item 158): this said the matcher's
    `set_tool_decision` had already written a verdict for every charge on a
    fresh month. It has not. THIS fixture's charges pair with nothing, so the
    month ends with no `decided_by='tool'` row at all and `set_tool_decision`
    was the one `decisions` writer no fixture reached. The route that does
    reach it is the self-confirm rule, and it is covered now in
    `tests/test_tool_decision_statement_id_158.py`.
    """
    batch_id = _create_batch(client)
    payload = _xlsx_bytes(ROWS)
    _attach(client, batch_id, payload)
    sid = _expected_id(payload)

    charge = _row_for(_run(client, batch_id), "OBSIDIAN")
    (expense,) = _grid(client, batch_id)["expenses"]

    with _db(client) as conn:
        conn.execute("UPDATE decisions SET statement_id = NULL WHERE run_id = ?",
                     (batch_id,))
        conn.commit()
        assert conn.execute(
            "SELECT COUNT(*) c FROM decisions WHERE run_id = ? "
            "AND statement_id IS NOT NULL", (batch_id,),
        ).fetchone()["c"] == 0, "the premise: nothing is stamped"

    _pair(client, batch_id, charge["transaction_id"], expense["document_id"])

    with _db(client) as conn:
        row = conn.execute(
            "SELECT statement_id FROM decisions WHERE run_id = ? "
            "AND transaction_id = ?", (batch_id, charge["transaction_id"]),
        ).fetchone()
        untouched = conn.execute(
            "SELECT COUNT(*) c FROM decisions WHERE run_id = ? "
            "AND transaction_id != ? AND statement_id IS NOT NULL",
            (batch_id, charge["transaction_id"]),
        ).fetchone()["c"]
    assert row["statement_id"] == sid, "the reviewer's own write stamped it"
    assert untouched == 0, "and stamped only the charge it was about"
