"""Zoho journal-entry export skeleton tests (slice 4.6)."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.output.zoho_export import (
    ZOHO_COLUMNS,
    build_journal_rows,
    write_zoho_export,
)


def _line(desc, amount, category, source=ClassificationSource.LINE) -> LineItem:
    return LineItem(
        description=desc,
        line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.9,
            source=source, reasoning="t",
        ),
    )


def _tx(tid="t1", amount="180", account="amex-usd") -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id=account,
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )


def _receipt(items) -> Receipt:
    return Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        line_items=tuple(items),
    )


def test_multi_line_receipt_becomes_n_debits_plus_one_credit():
    tx = _tx()
    rec = _receipt([
        _line("chair", "150", "Equipment & Hardware"),
        _line("coffee beans", "30", "Office Supplies & Consumables"),
    ])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])

    rows = build_journal_rows(outcome, {"t1": tx}, {"r1": rec})

    # 2 debit rows + 1 balancing credit row.
    assert len(rows) == 3
    debits = [r for r in rows if r[5]]   # Debit column non-empty
    credits = [r for r in rows if r[6]]  # Credit column non-empty
    assert len(debits) == 2
    assert len(credits) == 1
    # Balanced: debits sum == credit.
    assert sum(Decimal(r[5]) for r in debits) == Decimal(credits[0][6]) == Decimal("180.00")
    # All linked by the same Reference#.
    assert {r[3] for r in rows} == {"t1"}


def test_only_matched_transactions_exported():
    tx1 = _tx("t1")
    tx2 = _tx("t2")  # unmatched
    rec = _receipt([_line("chair", "180", "Equipment & Hardware")])
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    rows = build_journal_rows(outcome, {"t1": tx1, "t2": tx2}, {"r1": rec})
    assert {r[3] for r in rows} == {"t1"}  # t2 withheld


def test_review_line_marked_uncategorized():
    tx = _tx()
    rec = _receipt([_line("???", "180", None, source=ClassificationSource.REVIEW)])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])
    rows = build_journal_rows(outcome, {"t1": tx}, {"r1": rec})
    debit_row = next(r for r in rows if r[5])
    assert debit_row[1] == "(uncategorized - assign)"


def test_write_zoho_export_has_header(tmp_path):
    tx = _tx()
    rec = _receipt([_line("chair", "180", "Equipment & Hardware")])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])

    out = write_zoho_export(outcome, [tx], [rec], tmp_path / "zoho.csv")
    with out.open(encoding="utf-8") as fh:
        reader = list(csv.reader(fh))
    assert tuple(reader[0]) == ZOHO_COLUMNS
    assert len(reader) == 3  # header + 1 debit + 1 credit
