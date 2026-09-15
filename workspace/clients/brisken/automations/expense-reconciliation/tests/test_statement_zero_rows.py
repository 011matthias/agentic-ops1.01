"""A statement that holds no charge is refused, not reported as success
(item 51).

Found by a drill while reproducing item 50: the attach returned
`200 {"ok": true}`, the job finished `done`, and the month recorded
`statements[{"n_rows": 0, "n_new": 0}]`. The file was a valid workbook whose
columns mapped cleanly and whose rows the parser read as nothing, which is
what a wrong worksheet, a header row below the first row, and a date format
the parser rejects all look like from here. The column-map 400 does not
catch it: that guard fires on a MISSING required column, and this file has
every column it needs.

Two things made it worse than "nothing happened". The month did not stay
where it was: `rematch_month` stamps `has_statement: True` on commit, so a
month that took an empty file graduated to the reconciliation workbench
holding zero charges, and on screen that is indistinguishable from a month
whose statement reconciled. And the same shape reaches the RE-READ, where
it does not merely add nothing: the re-read REPLACES the charge set, so a
stored file that used to hold rows and now reads none takes its charges
out of a live month with no message.

The negative cases are the contract here. Zero NEW charges is the ordinary
result of the same file arriving twice, which the fold exists to absorb, so
the guard keys on `n_rows` and never on `n_new`; and a re-read whose files
are intact is untouched by it.
"""
from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

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
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADER = "Date,Amount,Vendor\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, n=4):
    mock = MockLLMClient(
        extraction_responses=[
            ExtractedReceipt(
                date="2026-04-15", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="", payment_hint=None,
            )
        ] * n,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("42.50"), reasoning="same purchase",
            )
        ] * 24,
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


def _batch(client, label="April 2026"):
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("a.jpg", JPG, "application/octet-stream"))],
    ))
    return batch_id


def _csv(*rows: tuple[str, str, str]) -> bytes:
    return (HEADER + "".join(f"{d},{a},{v}\n" for d, a, v in rows)).encode()


def _xlsx(rows, sheet_title="Sheet") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    ws.append(["Date", "Amount", "Vendor"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _attach(client, batch_id, body: bytes, name="statement.csv", **extra):
    """The real route, all the way through the background job. Returns the
    job row, whatever its status, because the refusal IS a job status."""
    form = {
        "account_id": "amex-9001",
        "account_legal_entities": '{"amex-9001": "Corporate Services"}',
        "account_card_currency": "USD",
        "map_transaction_date": "Date",
        "map_amount": "Amount",
        "map_vendor": "Vendor",
    }
    form.update({k: v for k, v in extra.items() if v is not None})
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (name, body, "application/octet-stream")},
        data=form,
    )
    assert resp.status_code == 200, resp.text
    return client.get(f"/jobs/{resp.json()['job_id']}").json()


def _reread(client, batch_id):
    resp = client.post(f"/api/expense-batches/{batch_id}/statements/reread")
    assert resp.status_code == 200, resp.text
    return client.get(f"/jobs/{resp.json()['job_id']}").json()


def _stored(client, batch_id) -> dict:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(batch_id)
    snap = run.snapshot or {}
    return {
        "transactions": list(snap.get("transactions") or []),
        "statements": list(snap.get("statements") or []),
        "summary": dict(run.summary or {}),
        "work_dir": Path(run.work_dir),
    }


# ── the attach ──────────────────────────────────────────────────────────


def test_a_statement_holding_no_charge_is_refused(client, monkeypatch):
    """The drill's own file: valid, every required column present, not one
    row the parser can read as a charge. Before the guard this job said
    `done`."""
    _wire(monkeypatch)
    batch_id = _batch(client)

    job = _attach(client, batch_id, _csv(), name="empty.csv")

    assert job["status"] == "error", job
    assert "empty.csv" in job["error"]
    assert "no charge" in job["error"]


def test_the_refused_month_is_left_exactly_as_it_was(client, monkeypatch):
    """Nothing partial. No charge, no `statements[]` entry, and above all
    no graduation: the month is still an open expense batch, not a
    reconciliation holding zero charges."""
    _wire(monkeypatch)
    batch_id = _batch(client)

    _attach(client, batch_id, _csv(), name="empty.csv")

    stored = _stored(client, batch_id)
    assert stored["transactions"] == []
    assert stored["statements"] == []
    assert not stored["summary"].get("has_statement")
    listed = client.get("/api/expense-batches").json()
    row = next(
        r for r in listed["batches"] if r.get("batch_id") == batch_id
    )
    assert row["has_statement"] is False


def test_a_reconciling_month_keeps_its_charges_when_an_empty_file_lands(
    client, monkeypatch
):
    """The dangerous version: the month already reconciles, and Criss
    attaches the wrong sheet of the next card's workbook. Her existing
    charges and her existing statement record survive it."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")))

    job = _attach(client, batch_id, _csv(), name="wrong-sheet.csv")

    assert job["status"] == "error", job
    stored = _stored(client, batch_id)
    assert len(stored["transactions"]) == 1
    assert [e["file"] for e in stored["statements"]] == ["statement.csv"]


def test_a_re_upload_that_adds_nothing_new_is_still_accepted(
    client, monkeypatch
):
    """The negative case that keeps the guard honest, and the reason it
    reads `n_rows` rather than `n_new`. The same file twice contributes no
    NEW charge and is a perfectly ordinary thing to do; refusing it would
    break the living month."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    body = _csv(("2026-04-03", "42.50", "STAPLES"))
    _attach(client, batch_id, body)

    job = _attach(client, batch_id, body, name="again.csv")

    assert job["status"] == "done", job
    entries = _stored(client, batch_id)["statements"]
    assert [e["n_rows"] for e in entries] == [1, 1]
    assert [e["n_new"] for e in entries] == [1, 0]


def test_the_refusal_names_the_worksheet_that_was_read(client, monkeypatch):
    """The wrong worksheet is the likeliest cause, so the message says
    which one was read rather than leaving the operator to guess."""
    _wire(monkeypatch)
    batch_id = _batch(client)

    job = _attach(
        client, batch_id, _xlsx([], sheet_title="Summary"),
        name="August2026.xlsx", sheet_name="Summary",
    )

    assert job["status"] == "error", job
    assert "Summary" in job["error"]


# ── the re-read ─────────────────────────────────────────────────────────


def test_a_re_read_refuses_a_stored_file_that_now_reads_none(
    client, monkeypatch
):
    """Worse than the attach, because the re-read REPLACES the charge set:
    a file that held rows and now reads none would take them out of a live
    month. Deny-by-default, like a missing file."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")))
    stored = _stored(client, batch_id)
    (stored["work_dir"] / stored["statements"][0]["file"]).write_bytes(_csv())

    job = _reread(client, batch_id)

    assert job["status"] == "error", job
    assert "now reads none" in job["error"]
    after = _stored(client, batch_id)
    assert len(after["transactions"]) == 1


def test_a_re_read_of_intact_files_is_untouched_by_the_guard(
    client, monkeypatch
):
    """The negative case for the re-read half: the repair path still
    repairs."""
    _wire(monkeypatch)
    batch_id = _batch(client)
    _attach(client, batch_id, _csv(("2026-04-03", "42.50", "STAPLES")))

    job = _reread(client, batch_id)

    assert job["status"] == "done", job
    assert len(_stored(client, batch_id)["transactions"]) == 1
