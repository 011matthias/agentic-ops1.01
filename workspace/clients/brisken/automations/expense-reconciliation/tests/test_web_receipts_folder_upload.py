"""Bulk digital-receipt folder upload (2026-07-27).

Criss drops a whole FOLDER (or a .zip) of receipts she only has digitally
(not in the Zoho ER export). Each is OCR'd and the matcher proposes pairings
against the run's not-yet-decided charges, WITHOUT disturbing anything she
already confirmed. Unlike the single-file emailed-receipt attach, this does
not pre-assign: it re-runs the real matcher over the sub-universe of
{undecided charges} x {new + still-unmatched existing receipts} and merges
the suggestions back beside the untouched decided work.

The upload runs as a background job (vision over a folder is minutes of
work); the TestClient runs the background task in-process, so a POST then an
immediate /jobs poll sees it done. OCR is injected via MockLLMClient by
monkeypatching cli._build_llm_client (the service imports it lazily), so the
tests are CI-safe with no API key.

Example data (examples/statement.example.csv + receipts.example.csv):
five charges, four ER receipts; STAPLES NYC (42.50, 2026-04-15) is the one
charge left unmatched — the target for the matching tests.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import build_view  # noqa: E402
from expense_recon.web.store import STATUS_CONFIRMED, RunStore  # noqa: E402

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


def _run(client, run_id):
    db = _store(client)
    run = db.get_run(run_id)
    db.close()
    return run


def _view(client, run_id) -> dict:
    db = _store(client)
    run = db.get_run(run_id)
    decisions = db.get_decisions(run_id)
    overrides = db.get_category_overrides(run_id)
    db.close()
    return build_view(run, decisions, overrides)


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date="2026-04-15",
        total="42.50",
        currency="USD",
        vendor="Staples",
        reference="",
        line_items=(),
        confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    """Force the service's OCR client to a MockLLMClient returning the given
    extractions. The service does `from ..cli import _build_llm_client`
    lazily, so patching the cli attribute is what the lazy import picks up."""
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _upload_folder(client, run_id, files):
    """files: list of (name, bytes). Posted under the multi-valued 'files'."""
    return client.post(
        f"/api/runs/{run_id}/receipts/folder",
        files=[("files", (n, d, "application/octet-stream")) for n, d in files],
    )


JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


def _staples_tx(run) -> str:
    """The one example charge left unmatched — STAPLES NYC."""
    unmatched = run.snapshot["outcome"]["unmatched_transactions"]
    assert len(unmatched) == 1, unmatched
    return unmatched[0]


# ── no-LLM: everything still lands in a bucket (guarantee) ──────────


def test_folder_bare_no_llm_lands_every_receipt(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    run_id = _create_run(client)

    resp = _upload_folder(client, run_id, [("a.jpg", JPG), ("b.png", JPG + b"2")])
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job

    run = _run(client, run_id)
    ingest = run.snapshot["folder_ingest"]
    assert ingest["llm_source"] == "none"
    assert ingest["n_ingested"] == 2
    # No OCR => no amount/date => nothing can match => all unmatched, but every
    # receipt is in a bucket (reconciliation guarantee).
    assert ingest["n_unmatched_new"] == 2
    folder_docs = [
        r["document_id"]
        for r in run.snapshot["receipts"]
        if r["document_id"].startswith("folder:")
    ]
    assert len(folder_docs) == 2
    assert set(folder_docs) <= set(run.snapshot["outcome"]["unmatched_receipts"])
    assert _view(client, run_id)["summary"]["invariant_ok"] is True
    # Files landed under the run work dir.
    stored = list((Path(run.work_dir) / "folder-receipts").iterdir())
    assert len(stored) == 2


# ── the feature: OCR'd receipt pairs an unmatched charge ────────────


def test_folder_matches_unmatched_charge(client, monkeypatch):
    run_id = _create_run(client)
    staples = _staples_tx(_run(client, run_id))
    _patch_ocr(monkeypatch, _extraction())  # matches STAPLES exactly

    resp = _upload_folder(client, run_id, [("staples.jpg", JPG)])
    assert resp.status_code == 200
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    run = _run(client, run_id)
    ingest = run.snapshot["folder_ingest"]
    assert ingest["n_ingested"] == 1
    assert ingest["n_matched_new"] == 1
    assert ingest["n_unmatched_new"] == 0

    # The STAPLES charge now carries the folder receipt as its candidate.
    match = next(
        m for m in run.snapshot["outcome"]["matches"] if m["transaction_id"] == staples
    )
    assert match["document_id"].startswith("folder:")
    # And it shows in the review workbench on that row: a deterministic
    # auto-match renders "reconciled" (the tool holds a receipt), pending the
    # reviewer's ratify, chosen to the folder receipt.
    view = _view(client, run_id)
    row = next(r for r in view["rows"] if r["transaction_id"] == staples)
    assert row["effective_bucket"] == "reconciled"
    assert row["chosen_document_id"].startswith("folder:")


# ── the run view surfaces the ingest summary for the SPA ───────────


def test_folder_ingest_summary_on_run_view(client, monkeypatch):
    run_id = _create_run(client)
    # A run with no folder upload exposes folder_ingest as None (not missing).
    assert _view(client, run_id)["folder_ingest"] is None

    _patch_ocr(monkeypatch, _extraction())
    resp = _upload_folder(client, run_id, [("staples.jpg", JPG)])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    fi = _view(client, run_id)["folder_ingest"]
    assert fi is not None
    assert fi["n_ingested"] == 1
    assert fi["n_matched_new"] == 1
    assert fi["n_possible_duplicates"] == 0
    # llm_source + cost are carried so the SPA can show what the upload cost.
    assert fi["llm_source"] in {"run", "env-default", "none"}
    assert "cost_usd" in fi


# ── constraint 1: never disturb a decided charge ───────────────────


def test_folder_does_not_disturb_confirmed(client, monkeypatch):
    run_id = _create_run(client)
    run = _run(client, run_id)
    # Confirm the UBER auto-match (charge -> rcpt-003) as terminal.
    uber = next(
        m for m in run.snapshot["outcome"]["matches"] if m["document_id"] == "rcpt-003"
    )
    db = _store(client)
    db.set_decision(run_id, uber["transaction_id"], STATUS_CONFIRMED, "rcpt-003", "t0")
    db.close()

    # Upload a folder receipt whose OCR would ALSO match UBER (22.30 / 04-05).
    _patch_ocr(
        monkeypatch,
        _extraction(date="2026-04-05", total="22.30", vendor="Uber"),
    )
    resp = _upload_folder(client, run_id, [("uber-dup.jpg", JPG)])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    view = _view(client, run_id)
    row = next(
        r for r in view["rows"] if r["transaction_id"] == uber["transaction_id"]
    )
    # The confirmed pair is untouched: still reconciled to rcpt-003, NOT stolen
    # by the folder receipt.
    assert row["effective_bucket"] == "reconciled"
    assert row["chosen_document_id"] == "rcpt-003"
    assert view["summary"]["invariant_ok"] is True


# ── idempotent re-upload (content-addressed id) ─────────────────────


def test_folder_reupload_same_bytes_is_idempotent(client, monkeypatch):
    run_id = _create_run(client)
    _patch_ocr(monkeypatch, _extraction(), _extraction())

    assert _upload_folder(client, run_id, [("s.jpg", JPG)]).status_code == 200
    resp2 = _upload_folder(client, run_id, [("s-again.jpg", JPG)])
    assert client.get(f"/jobs/{resp2.json()['job_id']}").json()["status"] == "done"

    run = _run(client, run_id)
    folder_docs = [
        r["document_id"]
        for r in run.snapshot["receipts"]
        if r["document_id"].startswith("folder:")
    ]
    assert len(folder_docs) == 1  # same bytes -> same content id -> one receipt


# ── constraint 4: a receipt already in the ER is flagged, not dropped ─


def test_folder_flags_duplicate_of_existing_receipt(client, monkeypatch):
    run_id = _create_run(client)
    # OCR returns the exact content of rcpt-003 (Uber, 22.30, 2026-04-05, USD).
    _patch_ocr(
        monkeypatch,
        _extraction(date="2026-04-05", total="22.30", vendor="Uber"),
    )
    resp = _upload_folder(client, run_id, [("uber.jpg", JPG)])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    run = _run(client, run_id)
    assert run.snapshot["folder_ingest"]["n_possible_duplicates"] == 1
    # Still ingested (never silently dropped).
    assert run.snapshot["folder_ingest"]["n_ingested"] == 1
    # And surfaced in the view's §18 duplicate panel.
    groups = _view(client, run_id)["duplicate_groups"]
    assert any(
        any(m.startswith("folder:") for m in g["members"])
        and any(m == "rcpt-003" for m in g["members"])
        for g in groups
    )


# ── .zip expansion ─────────────────────────────────────────────────


def test_folder_zip_is_expanded(client, monkeypatch):
    run_id = _create_run(client)
    _patch_ocr(monkeypatch, _extraction(), _extraction(total="1.00", vendor="Misc"))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("r1.jpg", JPG)
        zf.writestr("r2.jpg", JPG + b"z")
    resp = _upload_folder(client, run_id, [("receipts.zip", buf.getvalue())])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    assert _run(client, run_id).snapshot["folder_ingest"]["n_ingested"] == 2


# ── image preview for a folder receipt ─────────────────────────────


def test_folder_receipt_image_serves(client, monkeypatch):
    run_id = _create_run(client)
    _patch_ocr(monkeypatch, _extraction())
    resp = _upload_folder(client, run_id, [("staples.jpg", JPG)])
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"

    run = _run(client, run_id)
    doc = next(
        r["document_id"]
        for r in run.snapshot["receipts"]
        if r["document_id"].startswith("folder:")
    )
    img = client.get(f"/api/runs/{run_id}/receipts/{doc}/image")
    assert img.status_code == 200, img.text
    assert img.content == JPG  # the stored file, byte for byte


# ── endpoint validation ────────────────────────────────────────────


def test_folder_endpoint_validation(client):
    run_id = _create_run(client)
    assert _upload_folder(client, "nope00000000", [("a.jpg", JPG)]).status_code == 404
    # No files at all -> 400.
    assert client.post(f"/api/runs/{run_id}/receipts/folder").status_code == 400
