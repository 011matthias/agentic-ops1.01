"""Testing-mode publish lifecycle: user uploads -> operator runs the intake
-> publishes -> the user reviews the published run -> unpublish hides it.
Runs under the sync seam (conftest sets EXPENSE_RECON_WEB_SYNC=1)."""
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

USER_CODE = "user-code-1"
OP_CODE = "operator-code-1"


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
def app_env(monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_ACCESS_CODE", USER_CODE)
    monkeypatch.setenv("EXPENSE_RECON_OPERATOR_CODE", OP_CODE)
    monkeypatch.setenv("EXPENSE_RECON_INSECURE_COOKIE", "1")


def _client(app):
    return TestClient(app)


def _login(client, code):
    resp = client.post("/login", data={"code": code}, follow_redirects=False)
    assert resp.status_code == 303


def test_full_lifecycle(tmp_path, app_env):
    app = create_app(tmp_path)

    # 1. user uploads
    user = _client(app)
    _login(user, USER_CODE)
    resp = user.post(
        "/intakes",
        files=_files(),
        data={"card_name": "Corporate card 2838", "month": "2026-06"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    resp = user.get("/")
    assert "Received" in resp.text

    with RunStore(tmp_path / "recon-web.sqlite") as store:
        intake_id = store.list_intakes()[0].intake_id

    # 2. operator runs the intake (sync seam -> 303 to workbench)
    op = _client(app)
    _login(op, OP_CODE)
    prep = op.get(f"/intakes/{intake_id}/prepare")
    assert prep.status_code == 200
    assert "statement.example.csv" in prep.text
    resp = op.post(
        f"/intakes/{intake_id}/run",
        data={"account_id": "amex-9001", "account_card_currency": "USD"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    run_id = resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]

    with RunStore(tmp_path / "recon-web.sqlite") as store:
        intake = store.get_intake(intake_id)
        run = store.get_run(run_id)
    assert intake.status == INTAKE_PROCESSING
    assert run.intake_id == intake_id
    assert run.published is False

    # 3. user cannot see the unpublished run (404, id unconfirmable)
    assert user.get(f"/runs/{run_id}").status_code == 404
    assert user.get(f"/runs/{run_id}/report.xlsx").status_code == 404
    assert (
        user.post(
            f"/runs/{run_id}/decisions",
            json={"transaction_id": "x", "status": "confirmed"},
        ).status_code
        == 404
    )

    # 4. operator reviews + publishes
    wb = op.get(f"/runs/{run_id}")
    assert wb.status_code == 200
    assert "Publish for review" in wb.text
    resp = op.post(f"/runs/{run_id}/publish", follow_redirects=False)
    assert resp.status_code == 303

    with RunStore(tmp_path / "recon-web.sqlite") as store:
        intake = store.get_intake(intake_id)
        run = store.get_run(run_id)
    assert intake.status == INTAKE_READY
    assert intake.run_id == run_id
    assert run.published is True

    # 5. user sees + fully reviews the published run
    home = user.get("/")
    assert "Ready to review" in home.text
    wb = user.get(f"/runs/{run_id}")
    assert wb.status_code == 200
    assert "Publish for review" not in wb.text  # operator control hidden
    assert "Commit to memory" not in wb.text
    # decisions work for the user (no LLM involved)
    tx_id = None
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        run = store.get_run(run_id)
    for m in run.snapshot["outcome"]["matches"]:
        tx_id = m["transaction_id"]
        break
    if tx_id is not None:
        resp = user.post(
            f"/runs/{run_id}/decisions",
            json={"transaction_id": tx_id, "status": "confirmed"},
        )
        assert resp.status_code == 200

    # 6. unpublish hides it again
    resp = op.post(f"/runs/{run_id}/unpublish", follow_redirects=False)
    assert resp.status_code == 303
    assert user.get(f"/runs/{run_id}").status_code == 404
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        assert store.get_intake(intake_id).status == INTAKE_PROCESSING


def test_publish_unknown_run_404(tmp_path, app_env):
    app = create_app(tmp_path)
    op = _client(app)
    _login(op, OP_CODE)
    assert op.post("/runs/nope/publish").status_code == 404


def test_intake_without_receipts_cannot_run(tmp_path, app_env):
    app = create_app(tmp_path)
    user = _client(app)
    _login(user, USER_CODE)
    files = {
        "statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(),
            "text/csv",
        )
    }
    resp = user.post(
        "/intakes", files=files, data={"card_name": "Corp 2838"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        intake_id = store.list_intakes()[0].intake_id
    op = _client(app)
    _login(op, OP_CODE)
    resp = op.post(f"/intakes/{intake_id}/run", data={"account_id": "amex-9001"})
    assert resp.status_code == 400
    assert "no receipts file yet" in resp.text
