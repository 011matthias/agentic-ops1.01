"""Read a month's stored receipts again (backlog item 240).

Item 239 made Gemini read every receipt that arrives; the ones already stored
keep the reading OpenAI gave them. `POST /api/runs/{id}/receipts/reread`
reads them again through the arrival's own path and takes only the fields
the item-239 A/B backs (date, total, currency, tax, document type, the card,
and a merchant that is a different merchant). A dry run measures the result
on a throwaway copy of the database; the real run writes the readings where
extraction readings live and re-matches the month, so the reviewer's own
edits, picks, rulings and confirmations stay on top.

Every test goes through the route. The fake reader answers by file name from
a table the test rewrites between the arrival and the re-read, which is the
whole difference between the two readers.
"""
from __future__ import annotations

import io
import sqlite3
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
from expense_recon.web.service import (  # noqa: E402
    EXTRACTED_RECEIPTS_KEY,
    REMATCH_LOG_KEY,
    REMATCH_PENDING_KEY,
)
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
ROWS = [
    (datetime(2026, 8, 30), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 12), "GITHUB", "Sale", -99.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
LABEL = "August 2026"


def _ext(**kw) -> ExtractedReceipt:
    base = dict(
        date=None, total=None, currency="USD", vendor=None, reference=None,
        line_items=(), confidence=0.9, notes="", payment_hint=None,
    )
    base.update(kw)
    return ExtractedReceipt(**base)


# What the first reader (OpenAI) stored.
FIRST = {
    "Lovable": _ext(date="2026-08-30", total="15.00", vendor="Lovable Labs Incorporated"),
    "GitHub": _ext(date="2026-08-12", total="99.00", vendor="Brisken LLC"),
}


class Reader(MockLLMClient):
    """Answers a receipt by the first table key its file name contains."""

    def __init__(self, table: dict, **kw):
        super().__init__(**kw)
        self.table = table

    def extract_receipt(self, *, file_name, images=None, text=None):
        self.calls.append(("extract_receipt", (file_name, "vision")))
        for key, answer in self.table.items():
            if key in file_name:
                return answer
        return _ext(notes="no answer queued")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _wire(monkeypatch, table: dict) -> Reader:
    reader = Reader(
        table,
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("15.00"), reasoning="same purchase",
            )
        ] * 24,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (reader, None))
    return reader


def _done(client, resp) -> dict:
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, *, files=("Lovable", "GitHub"), attach=True):
    table = dict(FIRST)
    reader = _wire(monkeypatch, table)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": LABEL})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (f"{name}-receipt.jpg", JPG + name.encode(), "application/octet-stream"))
               for name in files],
    ))
    if attach:
        wb = Workbook()
        ws = wb.active
        ws.append(list(HEADERS))
        for row in ROWS:
            ws.append(list(row))
        buf = io.BytesIO()
        wb.save(buf)
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/statement",
            files={"statement": (
                "August2026.xlsx", buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )},
            data={
                "account_id": "card-2838",
                "account_legal_entities": '{"card-2838": "Corporate Services"}',
                "account_card_currency": "USD",
            },
        ))
    return batch_id, reader


def _db(client) -> Path:
    return Path(client._data_root) / "recon-web.sqlite"


def _db_state(client) -> dict:
    """Every row of every table in both stores except the job log, as text."""
    out: dict = {}
    for name in ("recon-web.sqlite", "learning.sqlite"):
        path = Path(client._data_root) / name
        if not path.exists():
            out[name] = None
            continue
        con = sqlite3.connect(path)
        try:
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ) if r[0] != "jobs"]
            out[name] = {
                t: sorted(repr(row) for row in con.execute(f'SELECT * FROM "{t}"'))
                for t in tables
            }
        finally:
            con.close()
    return out


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(grid, key) -> dict:
    return next(e for e in grid["expenses"] if key in e["document_id"])


def _reread(client, batch_id, **body):
    return client.post(f"/api/runs/{batch_id}/receipts/reread", json=body)


def _result(client, batch_id, *, dry_run: bool) -> dict:
    job = _done(client, _reread(client, batch_id, confirm=LABEL, dry_run=dry_run))
    return job["result"]


def _snapshot(client, batch_id) -> dict:
    with RunStore(_db(client)) as store:
        return dict(store.get_run(batch_id).snapshot)


def _second_reading(reader: Reader, **answers) -> None:
    reader.table.clear()
    reader.table.update(FIRST)
    reader.table.update(answers)


# ── The dry run ─────────────────────────────────────────────────────────


def test_dry_run_lists_what_changes_and_writes_nothing(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    _second_reading(
        reader,
        GitHub=_ext(date="2026-08-12", total="99.00",
                    vendor="GitHub, Inc.", vendor_clean="GitHub"),
    )
    before = _db_state(client)
    out = _result(client, batch_id, dry_run=True)
    assert _db_state(client) == before, "a dry run leaves the month exactly as it was"

    readings = out["readings"]
    assert readings["n_read"] == 2
    assert readings["n_unchanged"] == 1, "Lovable read the same: omitted from the list"
    (change,) = readings["changes"]
    assert "GitHub" in change["document_id"]
    assert change["where"] == "expense"
    assert change["changes"] == {"vendor": {"before": "Brisken LLC", "after": "GitHub, Inc."}}

    effects = out["consequences"]
    (row,) = [r for r in effects["expenses"] if "GitHub" in r["document_id"]]
    assert "vendor" in row["fields"], "the copy's Expenses view shows the new merchant"
    # Stored as "Brisken LLC", the GitHub receipt could not pair with the
    # GITHUB charge; read as GitHub, the copy's re-match pairs it.
    assert (effects["pairs"]["n_before"], effects["pairs"]["n_after"]) == (1, 2)
    (paired,) = effects["pairs"]["changed"]
    assert paired["before"] is None and "GitHub" in paired["after"]
    assert effects["confirmed"] == []
    assert not any("transaction_id" in e for e in _grid(client, batch_id)["expenses"]
                   if "GitHub" in e["document_id"]), "the month itself did not pair it"


def test_a_confirmed_match_whose_total_moves_is_named(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    confirmed = client.post(f"/api/runs/{batch_id}/decisions/confirm-matched")
    assert confirmed.status_code == 200, confirmed.text
    _second_reading(
        reader,
        Lovable=_ext(date="2026-08-30", total="15.50", vendor="Lovable Labs Incorporated"),
    )
    out = _result(client, batch_id, dry_run=True)
    (change,) = out["readings"]["changes"]
    assert change["changes"]["total"] == {"before": "15.00", "after": "15.50"}
    reopening = [c for c in out["consequences"]["confirmed"] if "Lovable" in c["document_id"]]
    assert reopening and reopening[0]["reading_moves"] is True, (
        "a confirmed pair whose receipt total moves is listed, never silent"
    )


# ── The real run ────────────────────────────────────────────────────────


def test_apply_writes_the_reading_and_the_reviewer_edit_stays_on_top(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    lovable = _row(_grid(client, batch_id), "Lovable")["document_id"]
    edit = client.put(f"/api/runs/{batch_id}/expenses/{lovable}",
                      json={"field": "vendor", "value": "Lovable (Criss)"})
    assert edit.status_code == 200, edit.text
    with RunStore(_db(client)) as store:
        overrides_before = store.get_expense_field_overrides(batch_id)

    _second_reading(
        reader,
        Lovable=_ext(date="2026-08-29", total="15.00", vendor="Lovable Labs Incorporated"),
        GitHub=_ext(date="2026-08-12", total="99.00",
                    vendor="GitHub, Inc.", vendor_clean="GitHub"),
    )
    out = _result(client, batch_id, dry_run=False)
    assert sorted(d.split("__")[-1] for d in out["written"]) == [
        "GitHub-receipt.jpg", "Lovable-receipt.jpg"]

    grid = _grid(client, batch_id)
    assert _row(grid, "GitHub")["vendor"]["display"] == "GitHub, Inc."
    assert _row(grid, "Lovable")["vendor"]["display"] == "Lovable (Criss)", "her edit stays on top"
    assert _row(grid, "Lovable")["date"] == "2026-08-29"

    snap = _snapshot(client, batch_id)
    base = {d["document_id"]: d for d in snap[EXTRACTED_RECEIPTS_KEY]}
    assert base[lovable]["detected_date"] == "2026-08-29", "the baseline holds the new reading"
    assert base[lovable]["detected_vendor"] == "Lovable Labs Incorporated", (
        "the baseline holds the reading, never the reviewer's edit"
    )
    assert "read again" in (base[lovable]["data_quality_note"] or "")
    assert snap[REMATCH_LOG_KEY][-1]["trigger"] == "receipts_reread"
    assert REMATCH_PENDING_KEY not in snap, "the re-match paid its debt"
    (record,) = snap["receipts_reread"]
    assert len(record["documents"]) == 2
    with RunStore(_db(client)) as store:
        assert store.get_expense_field_overrides(batch_id) == overrides_before, (
            "a reading is never written as a correction"
        )


def test_fields_the_ab_does_not_back_are_compared_not_written(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    _second_reading(
        reader,
        Lovable=_ext(date="2026-08-30", total="15.00",
                     vendor="Lovable Labs Incorporated (@lovable)",
                     reference="INV-77", document_kind="invoice"),
    )
    base_before = _snapshot(client, batch_id)[EXTRACTED_RECEIPTS_KEY]
    out = _result(client, batch_id, dry_run=False)
    assert out["written"] == [] and out["readings"]["changes"] == []
    assert out["readings"]["not_taken"]["reference"] == 1
    assert out["readings"]["not_taken"]["document_kind"] == 1
    snap = _snapshot(client, batch_id)
    assert snap[EXTRACTED_RECEIPTS_KEY] == base_before, "no reading was written"
    assert snap["receipts_reread"][-1]["documents"] == []
    assert REMATCH_LOG_KEY not in snap or snap[REMATCH_LOG_KEY][-1]["trigger"] != "receipts_reread"


def test_a_blank_card_replaces_an_invented_one(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch, attach=False)
    reader.table["Lovable"] = _ext(date="2026-08-30", total="15.00",
                                   vendor="Lovable Labs Incorporated", card_last4="7696")
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("Lovable-2.jpg", JPG + b"L2", "application/octet-stream"))],
    ))
    _second_reading(
        reader, Lovable=_ext(date="2026-08-30", total="15.00",
                             vendor="Lovable Labs Incorporated", card_last4=None),
    )
    out = _result(client, batch_id, dry_run=False)
    cards = [c["changes"].get("card_last4") for c in out["readings"]["changes"]]
    assert {"before": "7696", "after": None} in cards


# ── Set aside ───────────────────────────────────────────────────────────


def test_a_page_set_aside_as_a_statement_joins_when_read_as_an_invoice(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    reader.table["AWS"] = _ext(date="2026-08-03", total="42.00", vendor="Amazon Web Services",
                               document_type="statement")
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("AWS-bill.jpg", JPG + b"AWS", "application/octet-stream"))],
    ))
    assert not any("AWS" in e["document_id"] for e in _grid(client, batch_id)["expenses"])

    _second_reading(reader, AWS=_ext(date="2026-08-03", total="42.00",
                                     vendor="Amazon Web Services", document_type="invoice"))
    dry = _result(client, batch_id, dry_run=True)
    (join,) = [c for c in dry["readings"]["changes"] if c["where"] == "set_aside"]
    assert join["joins_month"] is True and join["set_aside_reason"] == "statement"
    assert not any("AWS" in e["document_id"] for e in _grid(client, batch_id)["expenses"])

    out = _result(client, batch_id, dry_run=False)
    assert len(out["joined"]) == 1
    assert _row(_grid(client, batch_id), "AWS")["total"] in ("42.00", 42.0, "42")
    entry = next(e for e in _snapshot(client, batch_id)["set_aside"] if "AWS" in e["file"])
    assert entry["restored"] is True and entry["restored_by"] == "reread"


def test_an_expense_read_as_a_statement_is_listed_and_left(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    _second_reading(reader, GitHub=_ext(date="2026-08-12", total="120.00",
                                        vendor="Chase", document_type="statement"))
    out = _result(client, batch_id, dry_run=False)
    (listed,) = out["readings"]["reads_as_non_receipt"]
    assert "GitHub" in listed["document_id"] and listed["reads_as"] == "statement"
    assert out["written"] == []
    assert _row(_grid(client, batch_id), "GitHub")["vendor"]["raw"] == "Brisken LLC"


def test_one_merchant_written_two_ways_is_not_a_change(client, monkeypatch):
    batch_id, reader = _month(client, monkeypatch)
    _second_reading(reader, Lovable=_ext(date="2026-08-30", total="15.00",
                                         vendor="Lovable Labs Inc"))
    out = _result(client, batch_id, dry_run=True)
    assert out["readings"]["changes"] == []


# ── Refusals ────────────────────────────────────────────────────────────


def test_refusals(client, monkeypatch):
    batch_id, _reader = _month(client, monkeypatch)
    r = _reread(client, batch_id, dry_run=True)
    assert r.status_code == 400 and r.json()["code"] == "reread_confirm_required"
    r = _reread(client, batch_id, confirm="July 2026", dry_run=True)
    assert r.status_code == 400 and r.json()["code"] == "reread_confirm_mismatch"
    r = _reread(client, batch_id, confirm=LABEL, dry_run="yes")
    assert r.status_code == 400 and r.json()["code"] == "reread_dry_run_required"
    r = _reread(client, "nope", confirm=LABEL, dry_run=True)
    assert r.status_code == 404 and r.json()["code"] == "run_not_found"

    with RunStore(_db(client)) as store:
        snap = dict(store.get_run(batch_id).snapshot)
        snap[REMATCH_PENDING_KEY] = {"id": "abc123", "trigger": "receipts", "changed_at": "2099-01-01T00:00:00+00:00"}
        store.update_run_snapshot(batch_id, snap)
    r = _reread(client, batch_id, confirm=LABEL, dry_run=True)
    assert r.status_code == 409 and r.json()["code"] == "rematch_running"
    with RunStore(_db(client)) as store:
        snap.pop(REMATCH_PENDING_KEY)
        store.update_run_snapshot(batch_id, snap)

    pub = client.post(f"/api/runs/{batch_id}/publish", json={"override": True})
    assert pub.status_code == 200, pub.text
    r = _reread(client, batch_id, confirm=LABEL, dry_run=True)
    assert r.status_code == 409 and r.json()["code"] == "month_published"
