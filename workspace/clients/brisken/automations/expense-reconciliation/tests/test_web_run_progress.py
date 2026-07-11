"""PR F — background run + status poll.

By default POST /runs validates synchronously, then runs the pipeline in a
background task and returns a polling page; the workbench opens once the
job reports done. These tests delete the sync seam (set globally in
conftest) so they exercise the real async path.
"""
from __future__ import annotations

import re
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


def test_async_run_backgrounds_then_completes(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPENSE_RECON_WEB_SYNC", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.post(
            "/runs",
            files=_files(),
            data={
                "account_id": "amex-9001",
                "legal_entity_id": "brisken-llc",
                "account_card_currency": "USD",
                "receipts_source": "csv",
            },
            follow_redirects=False,
        )
        # Not the workbench redirect; a polling page carrying the job id.
        assert resp.status_code == 200
        assert "Reconciling" in resp.text
        m = re.search(r'data-job-id="([^"]+)"', resp.text)
        assert m, resp.text
        job_id = m.group(1)

        # The background task runs within the TestClient request lifecycle,
        # so the job is already done; re-check defensively.
        status = None
        for _ in range(50):
            status = c.get(f"/jobs/{job_id}").json()
            if status["status"] != "running":
                break
        assert status["status"] == "done", status
        run_id = status["run_id"]

        wb = c.get(f"/runs/{run_id}")
        assert wb.status_code == 200
        assert "Transactions" in wb.text
        assert "amex-9001" in wb.text


def test_job_status_unknown_is_404(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        assert c.get("/jobs/nope").status_code == 404


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
        resp = c.post(
            "/runs", files=bad, data={"receipts_source": "csv"}, follow_redirects=False
        )
        assert resp.status_code == 400
        assert "auto-detect" in resp.text.lower()
