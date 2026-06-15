"""PR D — match transparency: amount/date/vendor sub-scores + near-miss.

The matcher already blends three sub-scores into the triage score; these
persist them on Match (round-trip safe) and surface them on the workbench
candidate, plus a nearest-free-receipt hint for unmatched charges.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import MatchingConfig, match_one
from expense_recon.matching.types import (
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.serialize import match_from_dict, match_to_dict, snapshot_to_dict
from expense_recon.web.service import build_view
from expense_recon.web.store import RunRow


def test_match_one_populates_and_serializes_subscores():
    tx = Transaction("t1", "ent", "card", date(2026, 5, 1), None, Decimal("10.00"), "USD", "USD", "UBER")
    rec = Receipt("d1", "ent", date(2026, 5, 1), Decimal("10.00"), "USD", "Uber")
    m = match_one(tx, rec, MatchingConfig())
    assert m.match_type is MatchType.EXACT
    assert m.amount_score == 1.0
    assert m.date_score > 0.0
    # Round-trip through the snapshot serialization preserves them.
    m2 = match_from_dict(match_to_dict(m))
    assert (m2.amount_score, m2.date_score, m2.vendor_score) == (
        m.amount_score,
        m.date_score,
        m.vendor_score,
    )


def test_build_view_exposes_subscores_and_near_miss():
    tx_match = Transaction("t1", "ent", "card", date(2026, 5, 1), None, Decimal("10.00"), "USD", "USD", "UBER")
    rec_match = Receipt("d1", "ent", date(2026, 5, 1), Decimal("10.00"), "USD", "Uber")
    tx_un = Transaction("t2", "ent", "card", date(2026, 5, 2), None, Decimal("58.00"), "USD", "USD", "TAVERN")
    rec_free = Receipt("d2", "ent", date(2026, 5, 6), Decimal("58.40"), "USD", "Delancey Tavern")
    outcome = MatchOutcome(
        matches=[
            Match("t1", "d1", MatchType.EXACT, 0.99, "x", amount_score=1.0, date_score=1.0, vendor_score=0.5)
        ],
        unmatched_transactions=["t2"],
        unmatched_receipts=["d2"],
    )
    snapshot = snapshot_to_dict([tx_match, tx_un], [rec_match, rec_free], outcome, [])
    run = RunRow("r", "2026-05-01", "x", None, {}, snapshot, {}, ".", False, False)
    view = build_view(run, {}, {})

    cand = next(r for r in view["rows"] if r["transaction_id"] == "t1")["candidates"][0]
    assert cand["amount_pct"] == 100
    assert cand["vendor_pct"] == 50

    un_row = next(r for r in view["rows"] if r["transaction_id"] == "t2")
    assert un_row["effective_bucket"] == "unmatched"
    assert un_row["near_miss"] is not None
    assert un_row["near_miss"]["total"] == "58.40"
    assert un_row["near_miss"]["amount_diff"] == "0.40"
    assert un_row["near_miss"]["date_diff_days"] == 4
