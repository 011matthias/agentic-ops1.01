"""Flat reconciled CSV download from the workbench (2026-06-16).

The CSV twin of the .xlsx report download: one row per statement line,
with the reviewer's decisions applied. Covers the new route — it emits
the reconciled column shape, writes every statement line (matched +
unmatched, unlike the matched-only Zoho export), and reflects a
rejection (a rejected charge flips to UNMATCHED rather than dropping).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.output.reconciled_csv import RECONCILED_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _create_run(client) -> str:
    files = {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        ),
        "receipts": (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        ),
    }
    resp = client.post(
        "/runs",
        files=files,
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]


def _snapshot(client, run_id) -> dict:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    db.close()
    return run.snapshot


def test_reconciled_download_headers_and_one_row_per_charge(client):
    run_id = _create_run(client)
    client.post(f"/runs/{run_id}/decisions/confirm-matched")

    resp = client.get(f"/runs/{run_id}/reconciled.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    lines = resp.text.splitlines()
    assert lines[0] == ",".join(RECONCILED_COLUMNS)
    # Every statement line appears (matched + unmatched), unlike the Zoho
    # export which only carries matched charges.
    n_tx = len(_snapshot(client, run_id)["transactions"])
    assert len(lines) - 1 == n_tx


def _status_counts(body: str) -> tuple[int, int]:
    """(data row count, UNMATCHED count) from a reconciled CSV body."""
    import csv as _csv

    rows = list(_csv.reader(body.splitlines()))
    si = rows[0].index("Match Status")
    data = [r for r in rows[1:] if r]
    return len(data), sum(1 for r in data if r[si] == "UNMATCHED")


def test_reconciled_download_reflects_rejection(client):
    run_id = _create_run(client)
    client.post(f"/runs/{run_id}/decisions/confirm-matched")
    matches = _snapshot(client, run_id)["outcome"]["matches"]
    rejected_tx = matches[0]["transaction_id"]

    before_rows, before_unmatched = _status_counts(
        client.get(f"/runs/{run_id}/reconciled.csv").text
    )
    client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": rejected_tx, "status": "rejected"},
    )
    after_rows, after_unmatched = _status_counts(
        client.get(f"/runs/{run_id}/reconciled.csv").text
    )
    # The rejected charge is NOT dropped (the reconciliation guarantee:
    # nothing silently disappears) — the row count is unchanged and the
    # previously-matched charge has flipped to UNMATCHED.
    assert after_rows == before_rows
    assert after_unmatched == before_unmatched + 1
