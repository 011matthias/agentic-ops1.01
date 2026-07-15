"""Durable background jobs: the jobs table survives the process, the poller
reads from SQLite, and the startup sweep marks interrupted jobs honestly
(Fly scale-to-zero can kill a background thread mid-run)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import (  # noqa: E402
    INTAKE_RECEIVED,
    JOB_ERROR,
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


def test_async_job_row_is_durable(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_WEB_SYNC", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/runs",
            files=_files(),
            data={"account_id": "amex-9001", "account_card_currency": "USD"},
        )
        assert resp.status_code == 200
        import re

        m = re.search(r'data-job-id="([0-9a-f]+)"', resp.text)
        assert m, "running page should carry the job id"
        job_id = m.group(1)
        # poll until done (TestClient runs background tasks on response close,
        # so by now the job has finished)
        status = c.get(f"/jobs/{job_id}").json()
        assert status["status"] == "done"
        assert status["run_id"]
    # the row is in SQLite, not process memory
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        job = store.get_job(job_id)
    assert job is not None and job["status"] == "done"


def test_unknown_job_404(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.get("/jobs/doesnotexist").status_code == 404


def test_startup_sweep_marks_interrupted_and_resets_intake(tmp_path):
    db = tmp_path / "recon-web.sqlite"
    with RunStore(db) as store:
        store.create_intake(
            intake_id="i1",
            created_at="2026-07-15T00:00:00+00:00",
            label="Corp 2838 2026-06",
            uploaded_by="user",
            statement_name="s.csv",
            receipts_name="r.csv",
            card_key=None,
            work_dir=str(tmp_path / "intakes" / "i1"),
            detect_note=None,
        )
        store.set_intake_status(
            "i1", "processing", updated_at="2026-07-15T00:01:00+00:00"
        )
        store.create_job("j1", "i1", "2026-07-15T00:01:00+00:00")
        assert store.get_job("j1")["status"] == JOB_RUNNING

    # app boot runs the sweep
    app = create_app(tmp_path)
    with TestClient(app) as c:
        status = c.get("/jobs/j1").json()
    assert status["status"] == JOB_ERROR
    assert "interrupted" in status["error"]
    with RunStore(db) as store:
        assert store.get_intake("i1").status == INTAKE_RECEIVED
