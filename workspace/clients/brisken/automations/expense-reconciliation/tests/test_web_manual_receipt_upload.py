"""Emailed-receipt upload (owner directive 2026-07-24).

Some receipts reach Criss by email instead of the Zoho ER export, so
their charges sit in unmatched with nothing to pair. The workbench can
upload such a file against one charge: it is stored under the run's
work dir, joins the snapshot receipt pool, and the pair records as a
confirmed decision (same mechanism as manual match). These runs have no
`llm:` block, so the bare-receipt path (filename as vendor) is what is
exercised; extraction with a live LLM only enriches the same Receipt.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import build_view  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _files():
    return {
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


def _create_run(client) -> str:
    resp = client.post(
        "/api/runs",
        files=_files(),
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


def _store(client) -> RunStore:
    return RunStore(client._data_root / "recon-web.sqlite")


def _view(client, run_id) -> dict:
    db = _store(client)
    run = db.get_run(run_id)
    decisions = db.get_decisions(run_id)
    overrides = db.get_category_overrides(run_id)
    db.close()
    return build_view(run, decisions, overrides)


def _upload(client, run_id, tx_id, name="uber-email.png", data=b"\x89PNG x"):
    return client.post(
        f"/api/runs/{run_id}/transactions/{tx_id}/receipt",
        files={"file": (name, data, "application/octet-stream")},
    )


def test_upload_attaches_pairs_and_persists(client):
    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    target_tx = run.snapshot["outcome"]["unmatched_transactions"][0]

    resp = _upload(client, run_id, target_tx)
    assert resp.status_code == 200, resp.text
    doc_id = resp.json()["document_id"]
    assert doc_id == f"manual:{target_tx}"
    assert resp.json()["summary"]["invariant_ok"] is True

    # The charge is now a reconciled pair with the uploaded receipt.
    view = _view(client, run_id)
    row = next(r for r in view["rows"] if r["transaction_id"] == target_tx)
    assert row["effective_bucket"] == "reconciled"

    # Receipt is in the pool; extra snapshot keys survived the rewrite;
    # the file itself sits under the run's work dir.
    db = _store(client)
    run2 = db.get_run(run_id)
    db.close()
    assert any(
        r["document_id"] == doc_id for r in run2.snapshot["receipts"]
    )
    assert set(run.snapshot.keys()) <= set(run2.snapshot.keys())
    stored = list((Path(run2.work_dir) / "manual-receipts").iterdir())
    assert len(stored) == 1 and stored[0].name.endswith("uber-email.png")


def test_reupload_replaces_prior_attachment(client):
    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    target_tx = run.snapshot["outcome"]["unmatched_transactions"][0]

    assert _upload(client, run_id, target_tx).status_code == 200
    assert _upload(
        client, run_id, target_tx, name="corrected.pdf", data=b"%PDF-1.4 x"
    ).status_code == 200

    db = _store(client)
    run2 = db.get_run(run_id)
    db.close()
    pool = [
        r
        for r in run2.snapshot["receipts"]
        if r["document_id"] == f"manual:{target_tx}"
    ]
    assert len(pool) == 1
    assert pool[0]["receipt_name"] == "corrected.pdf"


def test_upload_validation(client):
    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    target_tx = run.snapshot["outcome"]["unmatched_transactions"][0]

    # Unknown run -> 404; unknown tx -> 400; bad type -> 400; empty -> 400.
    assert _upload(client, "nope00000000", target_tx).status_code == 404
    assert _upload(client, run_id, "no-such-tx").status_code == 400
    assert (
        _upload(client, run_id, target_tx, name="notes.txt").status_code == 400
    )
    assert (
        _upload(client, run_id, target_tx, data=b"").status_code == 400
    )
