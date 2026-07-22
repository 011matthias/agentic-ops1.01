"""Publish lifecycle on the JSON API: upload an intake -> operator runs it
-> publishes -> unpublish. Publish flips the intake status the dashboard
and the dev-side notifier read. Runs under the sync seam (conftest sets
EXPENSE_RECON_WEB_SYNC=1), so /api/intakes/{id}/run answers {run_id}
directly. Auth is covered in test_web_auth; these clients run ungated.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import (  # noqa: E402
    INTAKE_PROCESSING,
    INTAKE_READY,
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


def test_full_lifecycle(client):
    # 1. upload an intake (queued, nothing runs)
    resp = client.post(
        "/api/intakes",
        files=_files(),
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
    )
    assert resp.status_code == 200, resp.text
    intake_id = resp.json()["intake_id"]

    # 2. run the intake (sync seam -> the run id comes straight back)
    resp = client.post(
        f"/api/intakes/{intake_id}/run",
        data={"account_id": "amex-9001", "account_card_currency": "USD"},
    )
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.get_intake(intake_id)
        run = store.get_run(run_id)
    assert intake.status == INTAKE_PROCESSING
    assert run.intake_id == intake_id
    assert run.published is False

    # 3. the run is reviewable and publish flips run + intake state
    assert client.get(f"/api/runs/{run_id}").status_code == 200
    resp = client.post(f"/api/runs/{run_id}/publish")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "run_id": run_id, "published": True}

    with RunStore(client._data_root / "recon-web.sqlite") as store:
        intake = store.get_intake(intake_id)
        run = store.get_run(run_id)
    assert intake.status == INTAKE_READY
    assert intake.run_id == run_id
    assert run.published is True

    # 4. decisions still work on a published run
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(run_id)
    matches = run.snapshot["outcome"]["matches"]
    if matches:
        resp = client.post(
            f"/api/runs/{run_id}/decisions",
            json={"transaction_id": matches[0]["transaction_id"],
                  "status": "confirmed"},
        )
        assert resp.status_code == 200

    # 5. unpublish reverts run + intake state
    resp = client.post(f"/api/runs/{run_id}/unpublish")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "run_id": run_id, "published": False}
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        assert store.get_run(run_id).published is False
        assert store.get_intake(intake_id).status == INTAKE_PROCESSING


def test_publish_unknown_run_404(client):
    resp = client.post("/api/runs/nope/publish")
    assert resp.status_code == 404
    assert resp.json() == {"error": "run not found"}


def test_intake_without_receipts_cannot_run(client):
    files = {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        )
    }
    resp = client.post(
        "/api/intakes", files=files, data={"card_name": "Corp 2838"}
    )
    assert resp.status_code == 200, resp.text
    intake_id = resp.json()["intake_id"]
    resp = client.post(
        f"/api/intakes/{intake_id}/run", data={"account_id": "amex-9001"}
    )
    assert resp.status_code == 400
    assert "no receipts file yet" in resp.json()["error"]
