"""Run management on the JSON API: rename + delete a run (F9), and
in-flight jobs surfaced in operator state (F3). Runs under the sync seam
(conftest sets EXPENSE_RECON_WEB_SYNC=1), so /api/intakes/{id}/run answers
{run_id} directly. Auth is covered in test_web_auth; these clients run
ungated.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import (  # noqa: E402
    INTAKE_RECEIVED,
    JOB_DONE,
    JOB_RUNNING,
    RunStore,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


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


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _make_run(client):
    resp = client.post(
        "/api/intakes",
        files=_files(),
        data={"card_name": "Corp 2838", "month": "2026-06"},
    )
    assert resp.status_code == 200, resp.text
    intake_id = resp.json()["intake_id"]
    resp = client.post(
        f"/api/intakes/{intake_id}/run",
        data={"account_id": "2838", "account_card_currency": "USD"},
    )
    assert resp.status_code == 200, resp.text
    return intake_id, resp.json()["run_id"]


# ── rename (F9) ───────────────────────────────────────────────────────────

def test_rename_run(client):
    _, run_id = _make_run(client)
    resp = client.post(f"/api/runs/{run_id}/rename", json={"label": "April final"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "run_id": run_id, "label": "April final"}
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert store.get_run(run_id).label == "April final"


def test_rename_empty_label_400(client):
    _, run_id = _make_run(client)
    resp = client.post(f"/api/runs/{run_id}/rename", json={"label": "   "})
    assert resp.status_code == 400
    assert resp.json() == {"error": "label is required"}


def test_rename_unknown_run_404(client):
    resp = client.post("/api/runs/nope/rename", json={"label": "x"})
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}


# ── delete (F9) ───────────────────────────────────────────────────────────

def test_delete_run_removes_db_and_disk(client):
    intake_id, run_id = _make_run(client)
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        work_dir = Path(store.get_run(run_id).work_dir)
    assert work_dir.is_dir()

    resp = client.post(f"/api/runs/{run_id}/delete")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "run_id": run_id, "deleted": True}

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert store.get_run(run_id) is None
        # The intake is back in the queue with no dangling run pointer.
        intake = store.get_intake(intake_id)
        assert intake.status == INTAKE_RECEIVED
        assert intake.run_id is None
    assert not work_dir.exists()


def test_delete_unknown_run_404(client):
    resp = client.post("/api/runs/nope/delete")
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}


def test_delete_does_not_escape_runs_dir(client, tmp_path):
    # A run whose work_dir points outside data_root/runs must never be
    # rmtree'd — the guard keeps deletion inside the volume's runs tree.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        store.create_run(
            run_id="danger",
            created_at="2026-07-23T00:00:00+00:00",
            label="x",
            operator=None,
            summary={},
            snapshot={},
            config={},
            work_dir=str(outside),
            llm_enabled=False,
            has_coa=False,
        )
    resp = client.post("/api/runs/danger/delete")
    assert resp.status_code == 200
    assert outside.exists() and (outside / "keep.txt").exists()


# ── in-flight jobs (F3) ───────────────────────────────────────────────────

def test_operator_state_processing(client):
    db = client._data_root / "recon-web.sqlite"
    with RunStore(db) as store:
        store.create_job("job-run", intake_id="i1", created_at="2026-07-23T00:00:00+00:00")
        store.set_job_status(
            "job-run", JOB_RUNNING, stage="matching",
            updated_at="2026-07-23T00:00:01+00:00",
        )
        store.create_job("job-done", intake_id="i2", created_at="2026-07-23T00:00:00+00:00")
        store.set_job_status(
            "job-done", JOB_DONE, run_id="r2",
            updated_at="2026-07-23T00:00:02+00:00",
        )

    resp = client.get("/api/operator/state")
    assert resp.status_code == 200
    processing = resp.json()["processing"]
    ids = {j["job_id"] for j in processing}
    assert "job-run" in ids
    assert "job-done" not in ids
    job = next(j for j in processing if j["job_id"] == "job-run")
    assert job["stage"] == "matching"
    assert job["intake_id"] == "i1"
