"""Bulk confirm / reject over the review bucket (2026-07-22).

The real April run left 34 charges in "needs review" and the only way to
clear them was one row at a time. `bulk_decisions` resolves a named set in
one call, reusing the per-row decision write so the outcome is identical to
doing them by hand.
"""
from __future__ import annotations

from expense_recon.web.service import bulk_decisions
from expense_recon.web.store import (
    STATUS_CONFIRMED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Decision,
    RunRow,
)


def _run(snapshot: dict) -> RunRow:
    return RunRow(
        run_id="r1",
        created_at="2026-07-22T00:00:00",
        label="2838 2026-07-22",
        operator="operator",
        summary={},
        snapshot=snapshot,
        config={},
        work_dir="",
        llm_enabled=False,
        has_coa=False,
        published=False,
        intake_id=None,
    )


def _snapshot() -> dict:
    """Two review charges with a candidate, one with none."""
    return {
        "transactions": [],
        "receipts": [],
        "parse_errors": [],
        "outcome": {
            "matches": [],
            "judgment_required": [
                {
                    "transaction_id": "t1",
                    "document_id": "d1",
                    "match_type": "fx_judgment",
                    "confidence": 0.5,
                    "score": 0.5,
                    "reason": "fx",
                },
                {
                    "transaction_id": "t2",
                    "document_id": "d2",
                    "match_type": "fx_judgment",
                    "confidence": 0.5,
                    "score": 0.5,
                    "reason": "fx",
                },
            ],
            "ambiguous": [],
            "refunds": [],
            "unmatched_transactions": ["t3"],
            "unmatched_receipts": [],
        },
    }


def _decision(status: str) -> Decision:
    return Decision(
        status=status, chosen_document_id=None, updated_at="2026-07-22T00:00:00"
    )


def test_bulk_confirm_uses_each_charges_own_candidate():
    writes = bulk_decisions(_run(_snapshot()), {}, ["t1", "t2"], STATUS_CONFIRMED)
    assert writes == [("t1", "d1"), ("t2", "d2")]


def test_bulk_confirm_skips_a_charge_with_no_candidate():
    """A receiptless charge cannot be confirmed: never invent a pairing."""
    writes = bulk_decisions(_run(_snapshot()), {}, ["t1", "t3"], STATUS_CONFIRMED)
    assert writes == [("t1", "d1")]


def test_bulk_reject_clears_the_document_and_needs_no_candidate():
    writes = bulk_decisions(_run(_snapshot()), {}, ["t1", "t3"], STATUS_REJECTED)
    assert writes == [("t1", None), ("t3", None)]


def test_an_explicit_earlier_verdict_is_never_stomped():
    decisions = {"t1": _decision(STATUS_REJECTED)}
    writes = bulk_decisions(
        _run(_snapshot()), decisions, ["t1", "t2"], STATUS_CONFIRMED
    )
    assert writes == [("t2", "d2")]


def test_pending_rows_are_still_written():
    decisions = {"t1": _decision(STATUS_PENDING)}
    writes = bulk_decisions(
        _run(_snapshot()), decisions, ["t1"], STATUS_CONFIRMED
    )
    assert writes == [("t1", "d1")]


def test_duplicate_ids_are_written_once():
    writes = bulk_decisions(
        _run(_snapshot()), {}, ["t1", "t1", "t1"], STATUS_CONFIRMED
    )
    assert writes == [("t1", "d1")]
