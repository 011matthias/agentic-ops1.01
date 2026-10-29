"""A charge in "Charges with no receipt, to chase" can be matched by hand (item 258).

Notes #133 and #135 (2026-10-29): the chase list had no way to pair a charge
with a receipt the matcher left alone, and the hand-match picker that exists
elsewhere read `date` and `reference` off `assignable_receipts`, which did not
carry them, so every picker row showed "-" for its date and a reviewer could
not tell two same-vendor receipts apart.

Route-level over a hand-built snapshot (the `test_receipt_held_by_review`
pattern): the picker fields are read from the payload, and the pairing goes
through the real `POST .../manual-match` and out of `receipt_chase`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    MatchOutcome,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _store_run(client, run_id: str) -> dict:
    tx = Transaction(
        transaction_id="gh1", legal_entity_id="le1", account_id="card-2838",
        transaction_date=date(2026, 8, 5), posting_date=None,
        amount=Decimal("21.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="GITHUB INC.",
    )
    rec = Receipt(
        document_id="0001__github.pdf", legal_entity_id="le1",
        detected_date=date(2026, 8, 4), detected_total=Decimal("21.00"),
        detected_currency="USD", detected_vendor="GitHub, Inc.",
        detected_reference="GH-4471",
    )
    outcome = MatchOutcome(
        matches=[], unmatched_transactions=["gh1"],
        unmatched_receipts=[rec.document_id],
    )
    snapshot = snapshot_to_dict([tx], [rec], outcome, [])
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        store.create_run(
            run_id=run_id, created_at="2026-09-01T00:00:00+00:00",
            label="August 2026", operator=None, summary={}, snapshot=snapshot,
            config={}, work_dir=str(client._data_root), llm_enabled=False,
            has_coa=False,
        )
    finally:
        store.close()
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _chase_ids(view: dict) -> set[str]:
    return {
        c["transaction_id"]
        for g in view.get("receipt_chase") or []
        for c in g.get("charges") or []
    }


def test_the_run_summary_carries_the_open_remainder(client):
    """Item 260: the counter reaches the payload the SPA reads (0 here: the
    one receiptless charge is a purchase, so it is chased, not remainder)."""
    view = _store_run(client, "chase-remainder")
    assert view["summary"]["n_charges_open_no_receipt_due"] == 0
    assert view["summary"]["n_charges_need_receipt"] == 1


def test_the_picker_carries_date_and_reference(client):
    view = _store_run(client, "chase-picker")
    picker = next(
        a for a in view["assignable_receipts"]
        if a["document_id"] == "0001__github.pdf"
    )
    assert picker["date"] == "2026-08-04"
    assert picker["reference"] == "GH-4471"


def test_a_hand_match_takes_the_charge_off_the_chase_list(client):
    before = _store_run(client, "chase-match")
    assert "gh1" in _chase_ids(before)
    assert before["summary"]["n_charges_need_receipt"] == 1

    resp = client.post(
        "/api/runs/chase-match/manual-match",
        json={"transaction_id": "gh1", "document_id": "0001__github.pdf"},
    )
    assert resp.status_code == 200, resp.text

    after = client.get("/api/runs/chase-match").json()
    assert "gh1" not in _chase_ids(after)
    assert after["summary"]["n_charges_need_receipt"] == 0
