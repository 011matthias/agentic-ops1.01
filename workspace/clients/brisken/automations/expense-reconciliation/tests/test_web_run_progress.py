"""PR F — background run + status poll.

POST /api/runs validates synchronously, then runs the pipeline in a
background task and returns {job_id}; the SPA polls /jobs/{id} until the
job reports done. These tests delete the sync seam (set globally in
conftest) so they exercise the real async path.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402

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


def test_job_status_unknown_is_404(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.get("/jobs/nope").status_code == 404


def test_api_run_backgrounds_then_completes(tmp_path, monkeypatch):
    # The run kickoff: POST /api/runs returns a job_id; poll /jobs/{id} to
    # done, then read the JSON workbench.
    monkeypatch.delenv("EXPENSE_RECON_WEB_SYNC", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/api/runs",
            files=_files(),
            data={
                "account_id": "amex-9001",
                "account_card_currency": "USD",
                "receipts_source": "csv",
            },
        )
        assert resp.status_code == 200, resp.text
        job_id = resp.json()["job_id"]
        assert job_id

        status = None
        for _ in range(50):
            status = c.get(f"/jobs/{job_id}").json()
            if status["status"] != "running":
                break
        assert status["status"] == "done", status
        run_id = status["run_id"]

        wb = c.get(f"/api/runs/{run_id}")
        assert wb.status_code == 200
        assert wb.json()["run_id"] == run_id
        assert "rows" in wb.json()


def test_api_run_missing_file_is_json_400(tmp_path, monkeypatch):
    # An empty statement file is a user-fixable problem: JSON 400, never an
    # HTML form re-render.
    monkeypatch.delenv("EXPENSE_RECON_WEB_SYNC", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/api/runs",
            files={
                "statement": ("s.csv", b"", "text/csv"),
                "receipts": (
                    "receipts.example.csv",
                    (EXAMPLES / "receipts.example.csv").read_bytes(),
                    "text/csv",
                ),
            },
            data={"account_id": "amex-9001", "receipts_source": "csv"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]


def test_async_unmappable_statement_still_400(tmp_path, monkeypatch):
    # The cheap validation runs synchronously even on the async path, so a
    # bad column map is still a form error, not a backgrounded failure.
    monkeypatch.delenv("EXPENSE_RECON_WEB_SYNC", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        bad = {
            "statement": ("bad.csv", b"Foo,Bar,Baz\n1,2,3\n", "text/csv"),
            "receipts": (
                "receipts.example.csv",
                (EXAMPLES / "receipts.example.csv").read_bytes(),
                "text/csv",
            ),
        }
        resp = c.post("/api/runs", files=bad, data={"receipts_source": "csv"})
        assert resp.status_code == 400
        assert "auto-detect" in resp.json()["error"].lower()
