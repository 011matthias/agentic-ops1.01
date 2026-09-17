"""Item 102: a yellow (booked) charge with no receipt is counted apart.

Criss colours a statement row yellow once she has keyed it into her books.
The review view folds those rows away as settled, so they never counted as
unreconciled money, and nothing said how many of them carry no receipt at
all (July 2026: 47 rows, USD 3,385.47 behind a USD 1,054.48 headline).
These tests go through `GET /api/runs/{id}`, the route the month page reads.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from expense_recon.matching.types import Match, MatchOutcome, MatchType, Receipt, Transaction
from expense_recon.web.app import create_app
from expense_recon.web.serialize import snapshot_to_dict
from expense_recon.web.store import RunStore


def _tx(tid, d, vendor, amount, currency="USD", **kw) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="chase",
        transaction_date=d, posting_date=None, amount=Decimal(amount),
        transaction_currency=currency, account_card_currency=currency,
        vendor_from_statement=vendor, card_last4="2838", **kw,
    )


def _rc(doc, vendor, total, d) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1", detected_date=d,
        detected_total=Decimal(total), detected_currency="USD",
        detected_vendor=vendor,
    )


CHARGES = [
    _tx("t_open", date(2026, 4, 1), "AMAZON", "180.00"),
    _tx("t_booked", date(2026, 4, 10), "YELLOW ROW", "50.00", entry_status="posted"),
    _tx("t_booked_eur", date(2026, 4, 11), "YELLOW EUR", "12.30", currency="EUR", entry_status="posted"),
    _tx("t_booked_ok", date(2026, 4, 15), "CAFE", "20.00", entry_status="posted"),
]
RECEIPTS = [_rc("m1", "Cafe", "20.00", date(2026, 4, 15))]


def _snapshot() -> dict:
    outcome = MatchOutcome(
        matches=[Match(
            transaction_id="t_booked_ok", document_id="m1", match_type=MatchType.EXACT,
            confidence=0.99, reason="exact", score=95,
            amount_score=1.0, date_score=1.0, vendor_score=1.0,
        )],
        unmatched_transactions=["t_open", "t_booked", "t_booked_eur"],
        unmatched_receipts=[],
    )
    return snapshot_to_dict(CHARGES, RECEIPTS, outcome, [])


@pytest.fixture
def summary(tmp_path) -> dict:
    with TestClient(create_app(tmp_path)) as client:
        db = RunStore(tmp_path / "recon-web.sqlite")
        db.create_run(
            run_id="run1", created_at="2026-05-02T00:00:00", label="April 2026",
            operator=None, summary={}, snapshot=_snapshot(), config={},
            work_dir=str(tmp_path), llm_enabled=False, has_coa=False,
        )
        db.close()
        resp = client.get("/api/runs/run1")
        assert resp.status_code == 200, resp.text
        return resp.json()["summary"]


def test_booked_charges_without_a_receipt_are_counted_per_currency(summary):
    assert summary["n_booked_no_receipt"] == 2
    assert summary["booked_no_receipt_by_ccy"] == {"EUR": "12.30", "USD": "50.00"}


def test_a_booked_charge_with_its_receipt_is_not_counted(summary):
    # t_booked_ok is yellow AND settled by m1: evidenced, so not in the count.
    assert summary["n_already_posted"] == 3
    assert summary["n_booked_no_receipt"] == 2


def test_the_unreconciled_figure_keeps_its_meaning(summary):
    # Booked rows stay out of unreconciled; the new figure sits beside it.
    assert summary["unreconciled_by_ccy"] == {"USD": "180.00"}
