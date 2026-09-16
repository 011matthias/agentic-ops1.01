"""The statement re-read (2026-09-11): repairing a month whose stored
charges were parsed wrong, without doubling it.

Criss attached Chase workbooks to July and August 2026. The Excel parser
kept the bank's printed sign (purchases negative), so every charge reached
the matcher as -15.00 against a 15.00 receipt and both months reconciled 0
while the receipts sat in the pool. Two things had to be true afterwards:

* a workbook attached THROUGH THE ROUTE matches its receipts (the parser
  fix, exercised at the caller, not only at the parser), and
* the two live months can be rebuilt in place. Re-uploading the file
  cannot do that: `transaction_id` derives from the canonical amount, so the
  corrected rows would fold in beside the wrong ones. The re-read reads the
  stored files again, replaces the charge set, carries reviewer verdicts
  over by sheet row, and refuses outright rather than write anything
  partial.
"""
from __future__ import annotations

import io
from datetime import datetime
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
from expense_recon.web.store import DISPOSITION_PERSONAL, RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

# Criss's export shape: purchases printed NEGATIVE, the payment positive,
# a Type column saying which is which.
CHASE_HEADERS = ("Date", "Description", "Type", "Amount")
CHASE_ROWS = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 30), "OBSIDIAN", "Sale", -96.00),
    (datetime(2026, 8, 23), "PRESSMASTER DMCC", "Sale", -135.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
NO_TYPE_HEADERS = ("Date", "Description", "Amount")
NO_TYPE_ROWS = [(d, v, a) for d, v, _t, a in CHASE_ROWS]


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


def _attach_xlsx(client, batch_id, rows=CHASE_ROWS, headers=CHASE_HEADERS):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(rows, headers),
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


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _store(client) -> RunStore:
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


def _stored(client, batch_id) -> dict:
    with _store(client) as store:
        run = store.get_run(batch_id)
        return {
            "transactions": list((run.snapshot or {}).get("transactions") or []),
            "statements": list((run.snapshot or {}).get("statements") or []),
            "anchors": dict((run.snapshot or {}).get("statement_anchors") or {}),
            "decisions": store.get_decisions(batch_id),
            "work_dir": Path(run.work_dir),
        }


def _reread(client, batch_id):
    return client.post(f"/api/expense-batches/{batch_id}/statements/reread")


def _amount(row: dict) -> Decimal:
    return Decimal(str(row["amount"]).replace(",", ""))


# ── the parser fix, at the caller ────────────────────────────────────────


def test_a_chase_workbook_attached_through_the_route_matches_its_receipt(
    client, monkeypatch
):
    """The defect as Criss saw it, through the real attach: a Lovable
    15.00 receipt in the pool, a LOVABLE charge printed -15.00 in the
    workbook, and the tool linking the two. The payment is a credit in its
    own bucket, never a pairing candidate."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_xlsx(client, batch_id)

    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 1
    assert view["summary"]["n_refunds"] == 1
    assert view["summary"]["n_unmatched_rec"] == 0
    lovable = next(r for r in view["rows"] if r["vendor"] == "LOVABLE")
    assert _amount(lovable) == Decimal("15.00")
    assert lovable["candidates"], "the receipt never became a candidate"


# ── the re-read ─────────────────────────────────────────────────────────


def _attach_with_the_old_parser(client, batch_id):
    """Produce the pre-2026-09-11 state through the REAL attach path: no
    Type column in the workbook, and the majority inference switched off,
    which is exactly what the Excel parser did before the fix."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "expense_recon.ingest.statement_xlsx.infer_sign_flip",
            lambda amounts: False,
        )
        _attach_xlsx(client, batch_id, rows=NO_TYPE_ROWS, headers=NO_TYPE_HEADERS)


def test_reread_repairs_a_month_stored_with_printed_signs(client, monkeypatch):
    """July and August 2026 as they sat on the volume: every purchase a
    negative amount, zero reconciled, the receipt in the pool. The re-read
    rebuilds the charges from the stored workbook, re-matches, keeps the
    upload's own record, and carries the reviewer's verdict to the id the
    same sheet row now has."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)

    before = _stored(client, batch_id)
    stale_ids = [t["transaction_id"] for t in before["transactions"]]
    assert _view(client, batch_id)["summary"]["n_reconciled"] == 0
    assert all(
        Decimal(t["amount"]) < 0
        for t in before["transactions"]
        if t["vendor_from_statement"] != "Payment Thank You-Mobile"
    ), "the fixture did not reproduce the pre-fix state"
    # A verdict on the stale LOVABLE row (sheet row 2).
    stale_lovable = next(
        t for t in before["transactions"] if t["vendor_from_statement"] == "LOVABLE"
    )
    with _store(client) as store:
        store.set_disposition(
            batch_id, stale_lovable["transaction_id"], DISPOSITION_PERSONAL,
            "2026-09-11T00:00:00",
        )

    _done(client, _reread(client, batch_id))

    after = _stored(client, batch_id)
    new_ids = [t["transaction_id"] for t in after["transactions"]]
    assert len(new_ids) == len(stale_ids)
    assert not set(new_ids) & set(stale_ids), "the sign fix changes every id"
    assert all(
        Decimal(t["amount"]) > 0
        for t in after["transactions"]
        if t["vendor_from_statement"] != "Payment Thank You-Mobile"
    )
    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 1
    assert view["summary"]["n_transactions"] == len(stale_ids), "no doubling"
    assert view["summary"]["n_refunds"] == 1
    # The upload record survives as the same upload, rebuilt, not appended.
    assert len(after["statements"]) == 1
    assert after["statements"][0]["file"] == before["statements"][0]["file"]
    assert after["statements"][0]["uploaded_at"] == before["statements"][0]["uploaded_at"]
    assert after["statements"][0]["n_rows"] == len(stale_ids)
    assert set(after["anchors"][after["statements"][0]["file"]]) == set(new_ids)
    # The verdict rode over by sheet row.
    new_lovable = next(
        t for t in after["transactions"] if t["vendor_from_statement"] == "LOVABLE"
    )
    assert stale_lovable["transaction_id"] not in after["decisions"]
    assert after["decisions"][new_lovable["transaction_id"]].disposition == DISPOSITION_PERSONAL


def test_a_receipt_arriving_after_the_reread_still_reconciles(client, monkeypatch):
    """The living month after the repair: a receipt injected later (mail,
    drop) is re-matched against the rebuilt charges. This is the flow the
    owner described on 2026-09-11 and the one the sign defect had made
    inert."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs", "15.00", "2026-08-31"),
        _extraction("Obsidian", "96.00", "2026-08-30"),
    )
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)
    _done(client, _reread(client, batch_id))
    assert _view(client, batch_id)["summary"]["n_reconciled"] == 1

    _add_receipt(client, batch_id)

    view = _view(client, batch_id)
    assert view["summary"]["n_reconciled"] == 2
    assert view["summary"]["n_unmatched_rec"] == 0


def test_reread_refuses_when_a_statement_file_is_missing(client, monkeypatch):
    """Deny-by-default: nothing partial. A month whose stored workbook is
    gone keeps exactly the charges it had."""
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    _attach_with_the_old_parser(client, batch_id)
    before = _stored(client, batch_id)
    (before["work_dir"] / before["statements"][0]["file"]).unlink()

    resp = _reread(client, batch_id)
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "error"
    assert "missing" in job["error"]

    after = _stored(client, batch_id)
    assert [t["transaction_id"] for t in after["transactions"]] == [
        t["transaction_id"] for t in before["transactions"]
    ]
    assert after["statements"] == before["statements"]


def test_reread_needs_a_statement(client, monkeypatch):
    _wire(monkeypatch, _extraction("Lovable Labs", "15.00", "2026-08-31"))
    batch_id = _create_batch(client)
    resp = _reread(client, batch_id)
    assert resp.status_code == 400
    assert "no statement" in resp.json()["error"]
