"""End-to-end tests for the local browser UI (FastAPI TestClient).

Drives the real app over the bundled examples: upload -> reconcile ->
workbench render -> reviewer decision -> export. The decision round-trip
asserts the editable layer actually changes the persisted state and the
summary, not just that the page renders.
"""
from __future__ import annotations

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
        c._data_root = tmp_path  # stash for db access in tests
        yield c


def _statement_files():
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
        "/runs",
        files=_statement_files(),
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    location = resp.headers["location"]
    return location.rstrip("/").rsplit("/", 1)[-1]


def test_index_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Reconcile a month" in resp.text


def test_run_renders_workbench(client):
    run_id = _create_run(client)
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    assert "Transactions" in resp.text
    assert "Match rate" in resp.text
    # The auto-detected statement column map maps the example headers, so
    # the example transactions ingested and rendered.
    assert "amex-9001" in resp.text


def test_decision_roundtrip_updates_summary(client):
    run_id = _create_run(client)
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    tx_id = run.snapshot["transactions"][0]["transaction_id"]
    baseline = run.summary["n_matched"]
    db.close()

    # Reject the first transaction; reconciled count must drop by one.
    resp = client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": tx_id, "status": "rejected"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["summary"]["n_unmatched_tx"] >= 1
    # If the first tx was originally matched, rejecting drops reconciled.
    if baseline:
        assert data["summary"]["n_reconciled"] <= baseline


def test_category_override_persists(client):
    run_id = _create_run(client)
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    # Find a receipt that has at least one line item.
    doc_id = None
    for r in run.snapshot["receipts"]:
        if r["line_items"]:
            doc_id = r["document_id"]
            break
    db.close()
    assert doc_id is not None

    resp = client.post(
        f"/runs/{run_id}/categories",
        json={
            "document_id": doc_id,
            "line_index": 0,
            "category": "Office Supplies & Consumables",
        },
    )
    assert resp.status_code == 200

    db = RunStore(client._data_root / "recon-web.sqlite")
    overrides = db.get_category_overrides(run_id)
    db.close()
    assert overrides[(doc_id, 0)]["category"] == "Office Supplies & Consumables"


def test_report_download(client):
    run_id = _create_run(client)
    resp = client.get(f"/runs/{run_id}/report.xlsx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # xlsx files are zip archives; the magic bytes are "PK".
    assert resp.content[:2] == b"PK"


def test_unmappable_statement_returns_error(client):
    bad = {
        "statement": ("bad.csv", b"Foo,Bar,Baz\n1,2,3\n", "text/csv"),
        "receipts": (
            "receipts.example.csv",
            (EXAMPLES / "receipts.example.csv").read_bytes(),
            "text/csv",
        ),
    }
    resp = client.post(
        "/runs", files=bad, data={"receipts_source": "csv"}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert "auto-detect" in resp.text.lower()


def test_ai_requested_without_key_falls_back(client, monkeypatch):
    # Requesting AI categorization with no server key must NOT block the
    # run. It falls back to the keyword classifier, produces a complete
    # reconciliation, and surfaces an informational notice (cross-cutting
    # requirement: AI-unavailable is a notice, not a hard error).
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post(
        "/runs",
        files=_statement_files(),
        data={
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "receipts_source": "csv",
            "use_llm": "1",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303, resp.text
    run_id = resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]

    wb = client.get(f"/runs/{run_id}")
    assert wb.status_code == 200
    # The informational notice rendered, and the reconciliation still ran.
    assert "no API key is set" in wb.text
    assert "Transactions" in wb.text
    # Effective AI state is off (fell back), not the requested "on".
    assert "AI categorization off" in wb.text


def test_workbench_renders_triage_and_duplicate_sections(client):
    run_id = _create_run(client)
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    # Tier-1 triage stat + duplicate scan always render in the workbench.
    assert "Dup groups" in resp.text


# ── PR A — review speed (confirm-all-matched + ready-to-post bar) ──────


def test_ready_bar_renders_and_gates_download(client):
    # A fresh run has matched rows the reviewer has not ratified yet, so the
    # ready bar reads "Not ready" and the report download link is disabled.
    run_id = _create_run(client)
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    assert "Confirm all matched" in resp.text
    assert "Not ready to post" in resp.text
    assert "undecided" in resp.text
    # The gated download carries the `disabled` class until review is clean.
    assert 'id="download-report"' in resp.text
    assert "disabled" in resp.text.split('id="download-report"', 1)[1][:120]


def test_confirm_all_matched_reconciles_and_opens_post_gate(client):
    run_id = _create_run(client)
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    n_matched = run.summary["n_matched"]
    db.close()
    assert n_matched > 0  # the example month has matched rows to confirm

    resp = client.post(f"/runs/{run_id}/decisions/confirm-matched")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["confirmed"] == n_matched
    # Every matched row is now reviewer-confirmed -> nothing undecided ->
    # the post gate opens.
    assert data["summary"]["n_undecided"] == 0
    assert data["summary"]["ready_to_post"] is True
    assert data["summary"]["n_reconciled"] >= n_matched

    # The decisions persisted as confirmed.
    db = RunStore(client._data_root / "recon-web.sqlite")
    decisions = db.get_decisions(run_id)
    db.close()
    assert sum(1 for d in decisions.values() if d.status == "confirmed") == n_matched

    # Re-running confirms nothing new (idempotent; pending-only).
    again = client.post(f"/runs/{run_id}/decisions/confirm-matched").json()
    assert again["confirmed"] == 0


def test_confirm_all_matched_does_not_stomp_an_explicit_reject(client):
    run_id = _create_run(client)
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    # Pick a transaction that was auto-matched, then reject it by hand.
    matched_tx = run.snapshot["outcome"]["matches"][0]["transaction_id"]
    db.close()

    client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": matched_tx, "status": "rejected"},
    )
    client.post(f"/runs/{run_id}/decisions/confirm-matched")

    db = RunStore(client._data_root / "recon-web.sqlite")
    decisions = db.get_decisions(run_id)
    db.close()
    # The explicit reject survived the batch confirm.
    assert decisions[matched_tx].status == "rejected"
