"""PR E — Zoho journal-entry CSV download from the workbench.

The browser could only download the .xlsx review report; the Zoho import
file was CLI-only. These cover the new route: it emits the Zoho column
shape and reflects the reviewer's decisions (a rejected charge drops out).
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.output.zoho_export import ZOHO_COLUMNS  # noqa: E402
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
        "/api/runs",
        files=files,
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def _matches(client, run_id) -> list[dict]:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    db.close()
    return run.snapshot["outcome"]["matches"]


def test_zoho_download_headers_and_matched_rows(client):
    run_id = _create_run(client)
    client.post(f"/api/runs/{run_id}/decisions/confirm-matched")

    resp = client.get(f"/runs/{run_id}/zoho.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text
    assert body.splitlines()[0] == ",".join(ZOHO_COLUMNS)
    # A confirmed transaction's id is the journal Reference#.
    assert _matches(client, run_id)[0]["transaction_id"] in body


def test_zoho_download_reflects_rejection(client):
    run_id = _create_run(client)
    client.post(f"/api/runs/{run_id}/decisions/confirm-matched")
    matches = _matches(client, run_id)
    rejected_tx = matches[0]["transaction_id"]
    kept_tx = matches[1]["transaction_id"]

    client.post(
        f"/api/runs/{run_id}/decisions",
        json={"transaction_id": rejected_tx, "status": "rejected"},
    )
    body = client.get(f"/runs/{run_id}/zoho.csv").text
    # The rejected charge is withheld; the others still export.
    assert rejected_tx not in body
    assert kept_tx in body


# ── §16 export-approved gate (end-to-end) ────────────────────────────


def test_settings_endpoint_get_default_and_put(client):
    # GET returns the default (gate off).
    assert client.get("/api/settings").json()["export_approved_only"] is False
    # PUT (operator) flips it and GET reflects the change.
    r = client.put("/api/settings", json={"export_approved_only": True})
    assert r.status_code == 200
    assert r.json()["export_approved_only"] is True
    assert client.get("/api/settings").json()["export_approved_only"] is True


def test_export_approved_gate_withholds_pending(client):
    # Turn the policy ON before the run, so the run snapshots policy=on.
    client.put("/api/settings", json={"export_approved_only": True})
    run_id = _create_run(client)

    # Nothing confirmed yet -> the journal has no data rows (header only).
    lines = [ln for ln in client.get(f"/runs/{run_id}/zoho.csv").text.splitlines() if ln.strip()]
    assert lines[0] == ",".join(ZOHO_COLUMNS)
    assert len(lines) == 1

    # Confirm exactly one matched charge -> only it exports; a still-pending
    # sibling stays withheld under the gate.
    matches = _matches(client, run_id)
    confirmed = matches[0]["transaction_id"]
    pending = matches[1]["transaction_id"]
    client.post(
        f"/api/runs/{run_id}/decisions",
        json={
            "transaction_id": confirmed,
            "status": "confirmed",
            "chosen_document_id": matches[0]["document_id"],
        },
    )
    body = client.get(f"/runs/{run_id}/zoho.csv").text
    assert confirmed in body
    assert pending not in body


def test_export_gate_default_off_exports_matched(client):
    # With the policy left at its default (off), confirm-all still exports
    # every matched charge -- the gate is inert unless switched on.
    run_id = _create_run(client)
    client.post(f"/api/runs/{run_id}/decisions/confirm-matched")
    body = client.get(f"/runs/{run_id}/zoho.csv").text
    assert _matches(client, run_id)[0]["transaction_id"] in body
