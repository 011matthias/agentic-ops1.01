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


# ── receipt preview endpoint (2026-07-25) ──────────────────────────


PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
    b"?\x00\x05\xfe\x02\xfe\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_receipt_image_serves_manual_upload(client):
    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    target_tx = run.snapshot["outcome"]["unmatched_transactions"][0]
    assert _upload(
        client, run_id, target_tx, name="uber.png", data=PNG_1PX
    ).status_code == 200

    resp = client.get(f"/api/runs/{run_id}/receipts/manual:{target_tx}/image")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == PNG_1PX


def test_receipt_image_404_when_no_image(client):
    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    # CSV-sourced receipts carry no vision page mapping -> 404.
    doc = run.snapshot["receipts"][0]["document_id"]
    assert (
        client.get(f"/api/runs/{run_id}/receipts/{doc}/image").status_code
        == 404
    )
    assert (
        client.get(f"/api/runs/{run_id}/receipts/ghost/image").status_code
        == 404
    )
    assert (
        client.get("/api/runs/nope00000000/receipts/x/image").status_code
        == 404
    )


def test_receipt_image_renders_mapped_er_pdf_page(client):
    """A snapshot receipt with a vision-mapped page serves a PNG render of
    that page from the stored receipts PDF."""
    from pypdf import PdfWriter

    run_id = _create_run(client)
    db = _store(client)
    run = db.get_run(run_id)

    # Stand in for the uploaded ER PDF: a one-page PDF in the work dir,
    # pointed to by config.receipts.path, with page 0 mapped to a receipt.
    pdf_path = Path(run.work_dir) / "er.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as fh:
        w.write(fh)
    snap = dict(run.snapshot)
    receipts = [dict(r) for r in snap["receipts"]]
    receipts[0]["receipt_image_page"] = 0
    snap["receipts"] = receipts
    db.update_run_snapshot(run_id, snap)
    db.conn.execute(
        "UPDATE runs SET config = json_set(config, '$.receipts.path', 'er.pdf') "
        "WHERE run_id = ?",
        (run_id,),
    )
    db.conn.commit()
    doc = receipts[0]["document_id"]
    db.close()

    resp = client.get(f"/api/runs/{run_id}/receipts/{doc}/image")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"
