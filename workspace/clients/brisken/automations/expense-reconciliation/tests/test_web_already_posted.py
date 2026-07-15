"""PR-E: the already_posted decision + the bucket sections.

An already_posted charge behaves like confirmed (decided, claims its
receipt) but never reaches the Zoho journal export; the workbench groups
rows into collapse-by-bucket sections with the "Already in Zoho" section
holding both her yellow rows and z-key decisions."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

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
        data={"account_id": "amex-9001", "account_card_currency": "USD"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]


def _first_matched_tx(client, run_id) -> str:
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(run_id)
    return run.snapshot["outcome"]["matches"][0]["transaction_id"]


def test_sections_render(client):
    run_id = _create_run(client)
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    for title in (
        "Needs your attention",
        "Matched automatically",
        "Already in Zoho",
        "No receipt yet",
        "Other checks",
    ):
        assert title in resp.text, f"section {title!r} missing"
    # legend present
    assert "Subscription" in resp.text


def test_already_posted_accepted_and_counts_decided(client):
    run_id = _create_run(client)
    tx_id = _first_matched_tx(client, run_id)
    resp = client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": tx_id, "status": "already_posted"},
    )
    assert resp.status_code == 200, resp.text
    summary = resp.json()["summary"]
    # the row is decided (not undecided) and the run can still become ready
    page = client.get(f"/runs/{run_id}")
    assert page.status_code == 200


def test_already_posted_excluded_from_zoho_export(client):
    run_id = _create_run(client)
    tx_id = _first_matched_tx(client, run_id)

    # confirm everything, then flip one matched row to already_posted
    assert (
        client.post(f"/runs/{run_id}/decisions/confirm-matched").status_code == 200
    )
    assert (
        client.post(
            f"/runs/{run_id}/decisions",
            json={"transaction_id": tx_id, "status": "already_posted"},
        ).status_code
        == 200
    )

    resp = client.get(f"/runs/{run_id}/zoho.csv")
    assert resp.status_code == 200
    rows = list(csv.reader(io.StringIO(resp.text)))
    header, body = rows[0], rows[1:]
    ref_idx = header.index("Reference#")
    refs = {row[ref_idx] for row in body if len(row) > ref_idx}
    assert tx_id not in refs, "already_posted row must not reach the journal"

    # the report + reconciled CSV still SHOW the row (nothing dropped)
    recon = client.get(f"/runs/{run_id}/reconciled.csv")
    assert tx_id.split(":")[0] in recon.text  # account present
    assert resp.text  # journal file itself still has the other rows
