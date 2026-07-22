"""Every SPA run persists a self-contained `run.local.json` beside the
uploaded files, so pulling the run dir off the /data volume reconciles
locally with NO OpenAI call (the cost-free local test loop).

Covers: the file is written by POST /api/runs; its config drops the
`llm` / `coa_validation` blocks; and a copy of the run dir reconciles
end-to-end through the CLI with OPENAI_API_KEY unset.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.cli import run as cli_run  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import LOCAL_RUN_CONFIG_NAME  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # No API key in the env: the run must complete deterministically.
    # TestClient finishes the background job before the POST returns.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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


_DATA = {
    "account_id": "amex-9001",
    "legal_entity_id": "brisken-llc",
    "account_card_currency": "USD",
    "receipts_source": "csv",
}


def _api_run(client) -> str:
    resp = client.post("/api/runs", files=_files(), data=_DATA)
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def test_run_dir_gets_self_contained_local_config(client):
    run_id = _api_run(client)
    run_dir = client._data_root / "runs" / run_id
    cfg_path = run_dir / LOCAL_RUN_CONFIG_NAME
    assert cfg_path.exists(), "run.local.json not written into the run dir"

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    # No paid-API block, no /data-bound COA block: deterministic + local.
    assert "llm" not in cfg
    assert "coa_validation" not in cfg
    # The blocks the CLI needs to reconcile are present, with relative paths.
    assert cfg["statement"]["path"] == "statement.example.csv"
    assert cfg["receipts"]["path"] == "receipts.example.csv"
    assert cfg["output"]["path"]
    # The uploaded files sit beside the config (relative paths resolve).
    assert (run_dir / cfg["statement"]["path"]).exists()
    assert (run_dir / cfg["receipts"]["path"]).exists()


def test_pulled_run_dir_reconciles_locally_without_api_key(client, tmp_path, monkeypatch):
    run_id = _api_run(client)
    src = client._data_root / "runs" / run_id
    cfg = json.loads((src / LOCAL_RUN_CONFIG_NAME).read_text(encoding="utf-8"))

    # Simulate `flyctl sftp` pulling the run dir: copy ONLY the inputs + the
    # local config into a fresh directory (no pre-generated report), so a
    # produced report proves the LOCAL run made it.
    local = tmp_path / "pulled"
    local.mkdir()
    shutil.copy(src / LOCAL_RUN_CONFIG_NAME, local / LOCAL_RUN_CONFIG_NAME)
    shutil.copy(src / cfg["statement"]["path"], local / cfg["statement"]["path"])
    shutil.copy(src / cfg["receipts"]["path"], local / cfg["receipts"]["path"])

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = cli_run(local / LOCAL_RUN_CONFIG_NAME)
    assert report is not None and report.exists()
    # It landed inside the pulled dir (relative output path), self-contained.
    assert report.parent == local
