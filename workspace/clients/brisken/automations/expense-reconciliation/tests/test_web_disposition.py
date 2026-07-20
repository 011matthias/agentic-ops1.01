"""§17 disposition: the web endpoint + the reimbursable seeding in build_view.

Two layers:
* the JSON endpoint (POST /api/runs/{id}/disposition and its /runs/{id}
  sibling) records a disposition and returns the fresh summary; and
* `build_view` / `effective_disposition` seed the default from a matched
  receipt's Zoho `reimbursable` flag, with an explicit reviewer verdict
  overriding the seed.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import build_view, effective_disposition  # noqa: E402
from expense_recon.web.store import Decision, RunRow, RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


# ── endpoint ─────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _create_run(client) -> str:
    files = {
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
    resp = client.post(
        "/runs",
        files=files,
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


def _a_transaction_id(client, run_id) -> str:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    db.close()
    return run.snapshot["transactions"][0]["transaction_id"]


def test_disposition_endpoint_records_and_returns_summary(client):
    run_id = _create_run(client)
    tx_id = _a_transaction_id(client, run_id)

    resp = client.post(
        f"/api/runs/{run_id}/disposition",
        json={"transaction_id": tx_id, "disposition": "personal_on_business_card"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert "summary" in body

    # The recorded disposition surfaces on the transaction's workbench row.
    view = client.get(f"/api/runs/{run_id}").json()
    row = next(r for r in view["rows"] if r["transaction_id"] == tx_id)
    assert row["disposition"] == "personal_on_business_card"


def test_disposition_endpoint_also_on_bare_runs_path(client):
    run_id = _create_run(client)
    tx_id = _a_transaction_id(client, run_id)
    resp = client.post(
        f"/runs/{run_id}/disposition",
        json={"transaction_id": tx_id, "disposition": "do_not_export"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True


def test_disposition_endpoint_rejects_invalid_value(client):
    run_id = _create_run(client)
    tx_id = _a_transaction_id(client, run_id)
    resp = client.post(
        f"/api/runs/{run_id}/disposition",
        json={"transaction_id": tx_id, "disposition": "nope"},
    )
    assert resp.status_code == 400


def test_disposition_does_not_clobber_triage_status(client):
    """A disposition write leaves a prior confirm intact (store orthogonality
    exercised through the HTTP surface)."""
    run_id = _create_run(client)
    client.post(f"/runs/{run_id}/decisions/confirm-matched")
    tx_id = _a_transaction_id(client, run_id)

    client.post(
        f"/api/runs/{run_id}/disposition",
        json={"transaction_id": tx_id, "disposition": "reimbursable_personal"},
    )
    view = client.get(f"/api/runs/{run_id}").json()
    row = next(r for r in view["rows"] if r["transaction_id"] == tx_id)
    assert row["disposition"] == "reimbursable_personal"
    # The confirm survived (the matched row is still reconciled, not reset).
    assert row["status"] == "confirmed"


# ── seed-from-reimbursable (service level) ───────────────────────────


def _reimbursable_run(work_dir) -> RunRow:
    """A run with one matched transaction whose receipt is flagged
    reimbursable in Zoho Expense."""
    tx = Transaction(
        transaction_id="t1", legal_entity_id="le1", account_id="amex-9001",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("180"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="HOTEL",
    )
    rec = Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Hotel",
        reimbursable=True,
        line_items=(
            LineItem(
                description="room", line_total=Decimal("180"),
                categorization=Categorization(
                    category="Travel & Transport", zoho_account=None,
                    confidence=0.9, source=ClassificationSource.LINE, reasoning="t",
                ),
            ),
        ),
    )
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)]
    )
    snapshot = snapshot_to_dict([tx], [rec], outcome, [])
    return RunRow(
        run_id="run1", created_at="2026-07-20T00:00:00", label="test",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )


def test_effective_disposition_seeds_reimbursable_from_receipt():
    rec = Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Hotel", reimbursable=True,
        line_items=(),
    )
    eff, default = effective_disposition(rec, None)
    assert default == "reimbursable_personal"
    assert eff == "reimbursable_personal"
    # An explicit verdict overrides the seed; the default still reflects it.
    eff2, default2 = effective_disposition(
        rec, Decision(status="pending", chosen_document_id=None, disposition="business")
    )
    assert eff2 == "business"
    assert default2 == "reimbursable_personal"


def test_effective_disposition_defaults_business_without_reimbursable():
    eff, default = effective_disposition(None, None)
    assert (eff, default) == ("business", "business")


def test_build_view_row_seeds_reimbursable_disposition(tmp_path):
    view = build_view(_reimbursable_run(tmp_path), {}, {})
    row = next(r for r in view["rows"] if r["transaction_id"] == "t1")
    assert row["disposition_default"] == "reimbursable_personal"
    assert row["disposition"] == "reimbursable_personal"
