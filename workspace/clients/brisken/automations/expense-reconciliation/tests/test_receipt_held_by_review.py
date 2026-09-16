"""`held_by` also names a receipt held by a PENDING review row (2026-09-16).

Item 60 taught a candidate to name the charge that holds its receipt. The
holder map it reads was filled from the reconciled matches and from each
charge's `held_doc`, and a review row's `held_doc` is the reviewer's pick:
None until somebody picks. But `apply_decisions` pass 2 has already CONSUMED
every receipt a pending judgment / ambiguous row keeps, so a later charge the
matcher paired with the same receipt falls to `unmatched` holding a candidate
that names nobody.

Live, August 2026 (run 074a7b8905d7, read 2026-09-16): charge
`6d474e9e8e964bd4` (ANTHROPIC 52.46) was raw-matched to
`0023__Invoice-DZ9BH3VA-0034.pdf`, bucketed unmatched, and its candidate
carried no `held_by`, while `assignable_receipts` on the same payload said
0023 was held by review row `c632cb75a5098253`. So
`summary.n_charges_receipt_taken` read 0 on the one month that had exactly
the case it counts.

Route-level over a hand-built snapshot (the `test_view_contract` synthetic
pattern): the matcher's own output is the precondition here, and pinning the
view against it directly is what makes the ORDER explicit. The review charge
comes first in the transaction list, so pass 2 hands it the receipt before
the matched charge asks.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

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


def _tx(tx_id: str, day: int, vendor: str = "ANTHROPIC",
        amount: str = "52.46") -> Transaction:
    return Transaction(
        transaction_id=tx_id, legal_entity_id="le1", account_id="card-2838",
        transaction_date=date(2026, 8, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
    )


def _rec(doc_id: str, day: int, vendor: str = "Anthropic, PBC",
         amount: str = "52.46") -> Receipt:
    return Receipt(
        document_id=doc_id, legal_entity_id="le1",
        detected_date=date(2026, 8, day), detected_total=Decimal(amount),
        detected_currency="USD", detected_vendor=vendor,
        detected_reference="R" + doc_id,
    )


def _pair(tx_id: str, doc_id: str, match_type: MatchType) -> Match:
    review = match_type is not MatchType.EXACT
    return Match(
        transaction_id=tx_id, document_id=doc_id, match_type=match_type,
        confidence=0.6 if review else 0.99, reason="seeded",
        requires_review=review, score=60 if review else 95,
        amount_score=1.0, date_score=0.9, vendor_score=0.8,
    )


def _store_run(client, run_id: str, transactions, receipts, outcome) -> dict:
    snapshot = snapshot_to_dict(transactions, receipts, outcome, [])
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


def _row(view: dict, tx_id: str) -> dict:
    return next(r for r in view["rows"] if r["transaction_id"] == tx_id)


def _candidate(row: dict, doc_id: str) -> dict:
    return next(c for c in row["candidates"] if c["document_id"] == doc_id)


@pytest.mark.parametrize("bucket", ["judgment_required", "ambiguous"])
def test_a_pending_review_row_is_named_as_the_holder(client, bucket):
    """The August shape: the review row takes the receipt in pass 2, the
    charge the matcher settled with the same receipt falls to unmatched, and
    its candidate now says which row has it."""
    review_type = (
        MatchType.FX_JUDGMENT if bucket == "judgment_required"
        else MatchType.AMBIGUOUS
    )
    review, taken = _tx("c632cb75a5098253", 3), _tx("6d474e9e8e964bd4", 4)
    doc = "0023__Invoice-DZ9BH3VA-0034.pdf"
    outcome = MatchOutcome(
        matches=[_pair(taken.transaction_id, doc, MatchType.EXACT)],
        unmatched_transactions=[], unmatched_receipts=[],
        **{bucket: [_pair(review.transaction_id, doc, review_type)]},
    )
    # ORDER: the review charge before the one it dispossesses.
    view = _store_run(client, f"held-{bucket}", [review, taken],
                      [_rec(doc, 3)], outcome)

    review_row = _row(view, review.transaction_id)
    taken_row = _row(view, taken.transaction_id)
    assert review_row["effective_bucket"] == "review"
    assert review_row["chosen_document_id"] is None, "pending: nobody picked"
    assert taken_row["effective_bucket"] == "unmatched"

    held = _candidate(taken_row, doc)["held_by"]
    assert held == {
        "transaction_id": review.transaction_id,
        "vendor": "ANTHROPIC",
        "amount": "52.46",
        "currency": "USD",
        "date": "2026-08-03",
    }
    # The holder's own candidate is not "taken": it is the holder.
    assert "held_by" not in _candidate(review_row, doc)
    assert view["summary"]["n_charges_receipt_taken"] == 1
    # The hand-match picker already said so; the row now agrees with it.
    picker = next(
        a for a in view["assignable_receipts"] if a["document_id"] == doc
    )
    assert picker["held_by"] == review.transaction_id


def test_a_reconciled_holder_still_wins_over_a_review_row(client):
    """Precedence, as the effective outcome can reach it. The reconciled
    charge settles D1 first; the review row that also scored D1 keeps only
    D2; a third charge matched to D2 loses it to the review row.

    `apply_decisions` never lets a reconciled match and a pending review row
    keep the same receipt, so the setdefault order is not observable through
    this route on its own; what IS observable, and what this pins, is that
    the review row's own D1 candidate names the RECONCILED charge (not
    itself, not nobody) while D2 on the third charge names the review row."""
    settled = _tx("settled", 2)
    review = _tx("review", 3)
    loser = _tx("loser", 4, amount="18.00", vendor="SUPABASE")
    d1, d2 = "d1-invoice.pdf", "d2-invoice.pdf"
    outcome = MatchOutcome(
        matches=[
            _pair(settled.transaction_id, d1, MatchType.EXACT),
            _pair(loser.transaction_id, d2, MatchType.EXACT),
        ],
        unmatched_transactions=[], unmatched_receipts=[],
        judgment_required=[
            _pair(review.transaction_id, d1, MatchType.FX_JUDGMENT),
            _pair(review.transaction_id, d2, MatchType.FX_JUDGMENT),
        ],
    )
    view = _store_run(client, "held-precedence", [settled, review, loser],
                      [_rec(d1, 2), _rec(d2, 3, amount="18.00")], outcome)

    settled_row = _row(view, "settled")
    review_row = _row(view, "review")
    loser_row = _row(view, "loser")
    assert settled_row["effective_bucket"] == "reconciled"
    assert review_row["effective_bucket"] == "review"
    assert loser_row["effective_bucket"] == "unmatched"

    assert _candidate(review_row, d1)["held_by"]["transaction_id"] == "settled"
    assert "held_by" not in _candidate(review_row, d2)
    assert "held_by" not in _candidate(settled_row, d1)
    assert _candidate(loser_row, d2)["held_by"]["transaction_id"] == "review"
    # Only the unmatched row counts; a review row is waiting on a pick of
    # its own, not dispossessed.
    assert view["summary"]["n_charges_receipt_taken"] == 1


def test_a_reviewer_pick_keeps_precedence_over_a_pending_review_row(client):
    """The overlap the effective outcome CAN reach, and the reason the new
    loop is a setdefault: a pending decision that names a document is the
    reviewer's pick, recorded as that charge's `held_doc`, while
    `apply_decisions` (which ignores `chosen_document_id` on a pending row)
    still lets another review row keep the same receipt. The pick names the
    holder; the review row does not overwrite it."""
    picker, other = _tx("picker", 3), _tx("other", 5)
    d1, d2 = "d1-invoice.pdf", "d2-invoice.pdf"
    outcome = MatchOutcome(
        matches=[], unmatched_transactions=[], unmatched_receipts=[],
        judgment_required=[
            _pair(picker.transaction_id, d1, MatchType.FX_JUDGMENT),
            _pair(other.transaction_id, d2, MatchType.FX_JUDGMENT),
        ],
    )
    snapshot = snapshot_to_dict([picker, other], [_rec(d1, 3), _rec(d2, 5)],
                                outcome, [])
    store = RunStore(client._data_root / "recon-web.sqlite")
    try:
        store.create_run(
            run_id="held-pick", created_at="2026-09-01T00:00:00+00:00",
            label="August 2026", operator=None, summary={}, snapshot=snapshot,
            config={}, work_dir=str(client._data_root), llm_enabled=False,
            has_coa=False,
        )
        store.set_decision("held-pick", "picker", "pending", d2,
                           "2026-09-16T08:00:00+00:00")
    finally:
        store.close()
    view = client.get("/api/runs/held-pick").json()

    other_row = _row(view, "other")
    assert _row(view, "picker")["chosen_document_id"] == d2
    assert other_row["effective_bucket"] == "review"
    assert _candidate(other_row, d2)["held_by"]["transaction_id"] == "picker"


def test_a_month_with_no_contest_still_carries_no_held_by(client):
    """Absent, not null, when the review row's receipt is nobody else's."""
    review, other = _tx("review", 3), _tx("other", 9, vendor="LOVABLE",
                                          amount="25.00")
    outcome = MatchOutcome(
        matches=[_pair(other.transaction_id, "d-other", MatchType.EXACT)],
        unmatched_transactions=[], unmatched_receipts=[],
        judgment_required=[
            _pair(review.transaction_id, "d-review", MatchType.FX_JUDGMENT),
        ],
    )
    view = _store_run(
        client, "held-none", [review, other],
        [_rec("d-review", 3), _rec("d-other", 9, "Lovable", "25.00")], outcome,
    )
    for row in view["rows"]:
        assert all("held_by" not in c for c in row["candidates"]), row
    assert view["summary"]["n_charges_receipt_taken"] == 0
