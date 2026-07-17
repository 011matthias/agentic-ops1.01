"""PR B — manual match: assign / steal a receipt by hand.

Covers the base case (a freed receipt -> an unmatched charge), the steal
case (taking a receipt already auto-matched to another charge frees that
charge), input validation, and the conflict-safety of apply_decisions'
two-pass resolution (latest confirm wins a contested receipt).
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
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import apply_decisions, build_view  # noqa: E402
from expense_recon.web.store import Decision, RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
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


def _create_run(client) -> str:
    resp = client.post(
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
    assert resp.status_code == 303, resp.text
    return resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]


def _view(client, run_id) -> dict:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    decisions = db.get_decisions(run_id)
    overrides = db.get_category_overrides(run_id)
    db.close()
    return build_view(run, decisions, overrides)


def _snapshot(client, run_id) -> dict:
    db = RunStore(client._data_root / "recon-web.sqlite")
    run = db.get_run(run_id)
    db.close()
    return run.snapshot


def test_manual_match_freed_receipt_to_unmatched_charge(client):
    run_id = _create_run(client)
    snap = _snapshot(client, run_id)
    matches = snap["outcome"]["matches"]
    unmatched_tx = snap["outcome"]["unmatched_transactions"]
    assert matches and unmatched_tx, "example month needs a matched + an unmatched tx"
    holder_tx = matches[0]["transaction_id"]
    freed_doc = matches[0]["document_id"]
    target_tx = unmatched_tx[0]

    # Free the receipt by rejecting its current charge; it must reappear in
    # the unmatched-receipt list so it can be re-assigned.
    client.post(
        f"/runs/{run_id}/decisions",
        json={"transaction_id": holder_tx, "status": "rejected"},
    )
    view = _view(client, run_id)
    assert any(r["document_id"] == freed_doc for r in view["unmatched_receipts"])

    # Hand-match the freed receipt to the unmatched charge.
    resp = client.post(
        f"/runs/{run_id}/manual-match",
        json={"transaction_id": target_tx, "document_id": freed_doc},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["summary"]["invariant_ok"] is True

    view = _view(client, run_id)
    target_row = next(r for r in view["rows"] if r["transaction_id"] == target_tx)
    assert target_row["effective_bucket"] == "reconciled"
    assert target_row["chosen_document_id"] == freed_doc
    # No longer free, and not double-bound.
    assert all(r["document_id"] != freed_doc for r in view["unmatched_receipts"])


def test_manual_match_steals_auto_matched_receipt(client):
    run_id = _create_run(client)
    snap = _snapshot(client, run_id)
    matches = snap["outcome"]["matches"]
    unmatched_tx = snap["outcome"]["unmatched_transactions"]
    holder_tx = matches[0]["transaction_id"]
    stolen_doc = matches[0]["document_id"]
    thief_tx = unmatched_tx[0]

    resp = client.post(
        f"/runs/{run_id}/manual-match",
        json={"transaction_id": thief_tx, "document_id": stolen_doc},
    )
    assert resp.status_code == 200, resp.text

    view = _view(client, run_id)
    thief = next(r for r in view["rows"] if r["transaction_id"] == thief_tx)
    holder = next(r for r in view["rows"] if r["transaction_id"] == holder_tx)
    assert thief["effective_bucket"] == "reconciled"
    assert thief["chosen_document_id"] == stolen_doc
    # The former holder lost the receipt -> unmatched.
    assert holder["effective_bucket"] == "unmatched"
    # Exactly one row holds the receipt (no double-binding).
    holders = [
        r["transaction_id"]
        for r in view["rows"]
        if any(c["is_chosen"] and c["document_id"] == stolen_doc for c in r["candidates"])
    ]
    assert holders == [thief_tx]
    assert view["summary"]["invariant_ok"] is True


def test_manual_match_unknown_receipt_rejected(client):
    run_id = _create_run(client)
    tx_id = _snapshot(client, run_id)["transactions"][0]["transaction_id"]
    resp = client.post(
        f"/runs/{run_id}/manual-match",
        json={"transaction_id": tx_id, "document_id": "does-not-exist"},
    )
    assert resp.status_code == 400
    assert "receipt" in resp.json()["error"].lower()


def test_apply_decisions_latest_confirm_wins_contested_receipt():
    # Two confirmed charges both claim the same receipt; the more recent
    # confirm keeps it, the older one falls to unmatched, receipt once.
    txs = [
        Transaction("t1", "ent", "card", date(2026, 5, 1), None, Decimal("10"), "USD", "USD", "A"),
        Transaction("t2", "ent", "card", date(2026, 5, 1), None, Decimal("10"), "USD", "USD", "B"),
    ]
    recs = [Receipt("r1", "ent", date(2026, 5, 1), Decimal("10"), "USD", "A")]
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x")],
        unmatched_transactions=["t2"],
    )
    decisions = {
        "t1": Decision("confirmed", "r1", "2026-05-01T00:00:00+00:00"),
        "t2": Decision("confirmed", "r1", "2026-05-02T00:00:00+00:00"),  # newer
    }
    eff = apply_decisions(outcome, txs, recs, decisions)
    assert [m.transaction_id for m in eff.matches if m.document_id == "r1"] == ["t2"]
    assert "t1" in eff.unmatched_transactions
    assert "r1" not in eff.unmatched_receipts
