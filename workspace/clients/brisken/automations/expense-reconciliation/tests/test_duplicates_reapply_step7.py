"""Re-apply the duplicate rules to a matched month (backlog item 223 step 7).

Which copy of a duplicated purchase counts is chosen when a month re-matches
and stored as `duplicate_kept`; a month with a statement keeps that choice
until its next natural re-match. `POST /api/runs/{id}/duplicates/reapply` is
the operator's way to run that re-match on purpose: a dry run that writes
nothing and answers the diff, then the real run as a job.

Every test goes through the route. The month is the item-217 fixture: a
Stripe `Invoice-*` / `Receipt-*` pair for one 15.00 USD purchase, with the
invoice first by document id.
"""
from __future__ import annotations

import io
import sqlite3
from datetime import datetime, timezone
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
    DUPLICATE_KEPT_KEY,
    REMATCH_PENDING_KEY,
)
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")
# A charge that holds the receipt (the item-217 month).
ROWS_HELD = [
    (datetime(2026, 8, 31), "LOVABLE", "Sale", -15.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
# No charge holds either copy: the pair a re-match is free to swap.
ROWS_FREE = [
    (datetime(2026, 8, 12), "GITHUB", "Sale", -99.00),
    (datetime(2026, 8, 4), "Payment Thank You-Mobile", "Payment", 7823.16),
]
LABEL = "August 2026"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction():
    return ExtractedReceipt(
        date="2026-08-31", total="15.00", currency="USD",
        vendor="Lovable Labs Incorporated", reference="", line_items=(),
        confidence=0.9, notes="", payment_hint=None,
    )


def _wire(monkeypatch):
    mock = MockLLMClient(
        extraction_responses=[_extraction(), _extraction()],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("15.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, *, rows=ROWS_FREE, attach=True):
    _wire(monkeypatch)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": LABEL})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", ("Invoice-HMVWDWIL-0029.jpg", JPG + b"1", "application/octet-stream")),
            ("files", ("Receipt-2167-5718.jpg", JPG + b"2", "application/octet-stream")),
        ],
    ))
    if attach:
        wb = Workbook()
        ws = wb.active
        ws.append(list(HEADERS))
        for row in rows:
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
    return batch_id


def _db(client) -> Path:
    return Path(client._data_root) / "recon-web.sqlite"


def _db_state(client) -> dict:
    """Every row of every table in both stores, as text: the dry run and
    every refusal must leave this byte-identical."""
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
            )]
            out[name] = {
                t: sorted(repr(row) for row in con.execute(f'SELECT * FROM "{t}"'))
                for t in tables
            }
        finally:
            con.close()
    return out


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _copies(grid):
    inv = next(e for e in grid["expenses"] if "Invoice-" in e["document_id"])
    rec = next(e for e in grid["expenses"] if "Receipt-" in e["document_id"])
    return inv, rec


def _stored_kept(client, batch_id) -> dict:
    with RunStore(_db(client)) as store:
        return dict(store.get_run(batch_id).snapshot.get(DUPLICATE_KEPT_KEY) or {})


def _force_kept(client, batch_id, document_id) -> str:
    """A month matched before item 217: its stored choice is the invoice."""
    with RunStore(_db(client)) as store:
        run = store.get_run(batch_id)
        snap = dict(run.snapshot)
        (gid,) = snap[DUPLICATE_KEPT_KEY]
        snap[DUPLICATE_KEPT_KEY] = {gid: document_id}
        assert store.update_run_snapshot(batch_id, snap)
    return gid


def _reapply(client, batch_id, **body):
    return client.post(f"/api/runs/{batch_id}/duplicates/reapply", json=body)


def _free_month_kept_on_the_invoice(client, monkeypatch):
    batch_id = _month(client, monkeypatch, rows=ROWS_FREE)
    inv, rec = _copies(_grid(client, batch_id))
    assert "transaction_id" not in inv and "transaction_id" not in rec, "no charge holds either"
    gid = _force_kept(client, batch_id, inv["document_id"])
    inv, rec = _copies(_grid(client, batch_id))
    assert inv.get("counts_in_total") is not False, "the stored choice counts the invoice"
    assert rec["counts_in_total"] is False
    return batch_id, gid, inv["document_id"], rec["document_id"]


# ── (a) the dry run ─────────────────────────────────────────────────────


def test_dry_run_reports_the_swap_and_writes_nothing(client, monkeypatch):
    batch_id, gid, inv_id, rec_id = _free_month_kept_on_the_invoice(client, monkeypatch)
    before = _db_state(client)

    resp = _reapply(client, batch_id, confirm=LABEL, dry_run=True)

    assert resp.status_code == 200, resp.text
    assert _db_state(client) == before, "a dry run writes nothing"
    out = resp.json()
    assert out["dry_run"] is True and out["run_id"] == batch_id and out["label"] == LABEL
    assert out["n_groups"] == 1
    (group,) = out["groups"]
    assert group["group_id"] == gid
    assert group["members"] == sorted([inv_id, rec_id])
    assert group["before"]["kept"] == inv_id
    assert group["after"]["kept"] == rec_id
    assert group["before"]["verdict"] == group["after"]["verdict"] == "copy"
    assert group["before"]["basis"] == group["after"]["basis"]
    assert out["counts_in_total"] == {"true_to_false": [inv_id], "false_to_true": [rec_id]}
    assert out["totals_by_ccy"] == {"before": {"USD": "15.00"}, "after": {"USD": "15.00"}}

    inv, rec = _copies(_grid(client, batch_id))
    assert inv.get("counts_in_total") is not False, "the page is as it was"
    assert _stored_kept(client, batch_id) == {gid: inv_id}


def test_the_run_id_confirms_as_well_as_the_label(client, monkeypatch):
    batch_id, _gid, _inv, _rec = _free_month_kept_on_the_invoice(client, monkeypatch)
    resp = _reapply(client, batch_id, confirm=batch_id, dry_run=True)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["groups"]) == 1


# ── (b) the real run ────────────────────────────────────────────────────


def test_real_run_swaps_the_kept_copy_and_logs_its_trigger(client, monkeypatch):
    batch_id, gid, inv_id, rec_id = _free_month_kept_on_the_invoice(client, monkeypatch)

    resp = _reapply(client, batch_id, confirm=LABEL, dry_run=False)

    assert resp.json()["dry_run"] is False
    job = _done(client, resp)
    result = job["result"]
    assert [g["after"]["kept"] for g in result["preview"]["groups"]] == [rec_id]
    (applied,) = result["applied"]["groups"]
    assert applied["group_id"] == gid
    assert (applied["before"]["kept"], applied["after"]["kept"]) == (inv_id, rec_id)
    assert result["applied"]["counts_in_total"] == {
        "true_to_false": [inv_id], "false_to_true": [rec_id],
    }
    assert result["applied"]["totals_by_ccy"]["after"] == {"USD": "15.00"}

    grid = _grid(client, batch_id)
    inv, rec = _copies(grid)
    assert rec.get("counts_in_total") is not False, "the receipt is the counted copy"
    assert inv["counts_in_total"] is False
    assert inv["duplicate"]["of"] == rec_id
    assert grid["summary"]["totals_by_ccy"] == {"USD": "15.00"}
    assert grid["last_rematch"]["trigger"] == "duplicates_reapply"
    assert _stored_kept(client, batch_id) == {gid: rec_id}

    # Applied once, there is nothing left to move.
    again = _reapply(client, batch_id, confirm=LABEL, dry_run=True).json()
    assert again["groups"] == [] and again["n_groups"] == 1


# ── (c) a copy a charge holds stays kept ────────────────────────────────


def test_a_copy_a_charge_holds_does_not_move(client, monkeypatch):
    batch_id = _month(client, monkeypatch, rows=ROWS_HELD)
    tx_id = next(r for r in _run(client, batch_id)["rows"] if r["vendor"] == "LOVABLE")["transaction_id"]
    inv_id = _copies(_grid(client, batch_id))[0]["document_id"]
    resp = client.post(
        f"/api/runs/{batch_id}/manual-match",
        json={"transaction_id": tx_id, "document_id": inv_id},
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/api/expense-batches/{batch_id}/refresh-master-data")
    assert resp.status_code == 200, resp.text
    (gid,) = _stored_kept(client, batch_id)
    assert _stored_kept(client, batch_id) == {gid: inv_id}, "the held invoice is kept"

    preview = _reapply(client, batch_id, confirm=LABEL, dry_run=True).json()
    assert preview["n_groups"] == 1
    assert preview["groups"] == [], "rule 1: a held copy never moves"
    assert preview["counts_in_total"] == {"true_to_false": [], "false_to_true": []}

    job = _done(client, _reapply(client, batch_id, confirm=LABEL, dry_run=False))
    assert job["result"]["applied"]["groups"] == []
    run = _run(client, batch_id)
    lovable = next(r for r in run["rows"] if r["vendor"] == "LOVABLE")
    assert lovable["chosen_document_id"] == inv_id, "the confirmed pick still names the invoice"
    inv, rec = _copies(_grid(client, batch_id))
    assert inv.get("counts_in_total") is not False
    assert rec["counts_in_total"] is False
    assert _stored_kept(client, batch_id) == {gid: inv_id}


# ── (d) a reviewer's "Not a copy" survives ──────────────────────────────


def test_a_not_a_copy_ruling_survives_the_real_run(client, monkeypatch):
    batch_id, gid, _inv_id, _rec_id = _free_month_kept_on_the_invoice(client, monkeypatch)
    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": gid, "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    assert grid["summary"]["totals_by_ccy"] == {"USD": "30.00"}, "two purchases"

    job = _done(client, _reapply(client, batch_id, confirm=LABEL, dry_run=False))

    assert job["result"]["applied"]["groups"] == []
    with RunStore(_db(client)) as store:
        assert store.get_duplicate_resolutions(batch_id) == {gid: "ignore"}
    grid = _grid(client, batch_id)
    (group,) = [g for g in grid["duplicate_groups"] if g["group_id"] == gid]
    assert (group["verdict"], group["decided_by"]) == ("distinct", "reviewer")
    inv, rec = _copies(grid)
    assert inv.get("counts_in_total") is not False
    assert rec.get("counts_in_total") is not False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "30.00"}
    assert grid["last_rematch"]["trigger"] == "duplicates_reapply"


# ── the preview's pool is the re-match's pool ───────────────────────────


def test_a_receipt_another_month_settled_stays_out_of_the_preview_too(client, monkeypatch):
    """`rematch_month` drops a receipt another run has settled before it
    picks the kept copy, so the receipt cannot become the kept one there.
    The preview drops it the same way and agrees with what the run applies."""
    batch_id, _gid, _inv_id, rec_id = _free_month_kept_on_the_invoice(client, monkeypatch)
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "July 2026"})
    _done(client, resp)
    other = resp.json()["batch_id"]
    con = sqlite3.connect(_db(client))
    try:
        con.execute(
            "INSERT INTO receipt_claims (receipt_run_id, document_id, "
            "claimed_by_run_id, transaction_id, claimed_at) VALUES (?, ?, ?, ?, ?)",
            (batch_id, rec_id, other, "tx-july", "2026-09-27T10:00:00+00:00"),
        )
        con.commit()
    finally:
        con.close()

    preview = _reapply(client, batch_id, confirm=LABEL, dry_run=True).json()
    assert preview["n_groups"] == 1
    assert preview["groups"] == [], "the settled receipt is not in the pool to keep"

    job = _done(client, _reapply(client, batch_id, confirm=LABEL, dry_run=False))
    assert job["result"]["applied"]["groups"] == preview["groups"]
    assert job["result"]["applied"]["counts_in_total"] == preview["counts_in_total"]


# ── (e) refusals write nothing ──────────────────────────────────────────


def _refused(client, batch_id, status, code, **body):
    before = _db_state(client)
    resp = _reapply(client, batch_id, **body)
    assert resp.status_code == status, resp.text
    assert resp.json()["code"] == code
    assert _db_state(client) == before, f"{code} wrote something"


def test_an_unknown_run_is_404(client):
    _refused(client, "no-such-run", 404, "run_not_found", confirm="no-such-run", dry_run=True)


def test_confirm_and_dry_run_are_required(client, monkeypatch):
    batch_id, _gid, _inv, _rec = _free_month_kept_on_the_invoice(client, monkeypatch)
    _refused(client, batch_id, 400, "reapply_confirm_required", dry_run=False)
    _refused(client, batch_id, 400, "reapply_confirm_required", confirm="  ", dry_run=True)
    _refused(client, batch_id, 400, "reapply_confirm_mismatch", confirm="July 2026", dry_run=False)
    _refused(client, batch_id, 400, "reapply_confirm_mismatch", confirm="July 2026", dry_run=True)
    _refused(client, batch_id, 400, "reapply_dry_run_required", confirm=LABEL)
    _refused(client, batch_id, 400, "reapply_dry_run_required", confirm=LABEL, dry_run="false")


def test_a_month_with_no_statement_is_refused(client, monkeypatch):
    batch_id = _month(client, monkeypatch, attach=False)
    _refused(client, batch_id, 409, "reapply_no_statement", confirm=LABEL, dry_run=False)
    _refused(client, batch_id, 409, "reapply_no_statement", confirm=LABEL, dry_run=True)


def test_a_published_month_is_refused(client, monkeypatch):
    batch_id, _gid, _inv, _rec = _free_month_kept_on_the_invoice(client, monkeypatch)
    with RunStore(_db(client)) as store:
        store.set_run_published(batch_id, True, "2026-09-27T10:00:00+00:00")
    _refused(client, batch_id, 409, "month_published", confirm=LABEL, dry_run=False)
    _refused(client, batch_id, 409, "month_published", confirm=LABEL, dry_run=True)


def _mark(client, batch_id, **mark):
    with RunStore(_db(client)) as store:
        snap = dict(store.get_run(batch_id).snapshot)
        snap[REMATCH_PENDING_KEY] = {"id": "abc123", "trigger": "receipts", **mark}
        assert store.update_run_snapshot(batch_id, snap)


def test_a_rematch_in_flight_is_refused_and_a_failed_one_is_not(client, monkeypatch):
    batch_id, _gid, _inv, _rec = _free_month_kept_on_the_invoice(client, monkeypatch)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _mark(client, batch_id, since=now, changed_at=now)
    _refused(client, batch_id, 409, "rematch_running", confirm=LABEL, dry_run=False)
    _refused(client, batch_id, 409, "rematch_running", confirm=LABEL, dry_run=True)

    # The last attempt failed: owed, not running, and a re-apply is its retry.
    _mark(client, batch_id, since=now, changed_at=now, failed_at=now,
          error="RuntimeError: model outage", attempts=1)
    resp = _reapply(client, batch_id, confirm=LABEL, dry_run=True)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["groups"]) == 1
