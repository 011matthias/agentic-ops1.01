"""Web wiring for PR 2a: the 'Commit to memory' action folds a finalized
run's confirmed decisions + reclassifications into the durable learning
store. Drives the real FastAPI app over the bundled example data."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.learning import LearningStore, normalize_vendor  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _create_run(client) -> str:
    resp = client.post(
        "/runs",
        files={
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
        },
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]


def test_commit_memory_writes_learning_store(client):
    run_id = _create_run(client)

    # Find the transaction the matcher paired with the coffee-shop receipt.
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    coffee = next(
        m for m in run.snapshot["outcome"]["matches"] if m["document_id"] == "rcpt-001"
    )
    tx_id = coffee["transaction_id"]
    db.close()

    # Reviewer confirms that match and reclassifies the coffee line.
    assert client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": tx_id, "status": "confirmed", "chosen_document_id": "rcpt-001"},
    ).status_code == 200
    assert client.post(
        f"/runs/{run_id}/categories",
        json={"document_id": "rcpt-001", "line_index": 0,
              "category": "Meals & Entertainment", "zoho_account": None},
    ).status_code == 200

    resp = client.post(f"/runs/{run_id}/commit-memory")
    assert resp.status_code == 200, resp.text
    learned = resp.json()["learned"]
    assert learned["confirmed_pairs"] >= 1
    assert learned["vendor_aliases"] >= 1
    assert learned["merchant_categories"] >= 1

    # The facts actually landed in the durable store.
    with LearningStore(client._data_root / "learning.sqlite") as ls:
        mc = ls.get_merchant_category("brisken-llc", normalize_vendor("Coffee Shop NYC"))
        assert mc is not None and mc.category == "Meals & Entertainment"
        aliases = ls.get_vendor_aliases("brisken-llc")
    assert any(a.receipt_vendor_norm == normalize_vendor("Coffee Shop NYC") for a in aliases)


def test_commit_memory_unknown_run_404(client):
    resp = client.post("/runs/nope/commit-memory")
    assert resp.status_code == 404
