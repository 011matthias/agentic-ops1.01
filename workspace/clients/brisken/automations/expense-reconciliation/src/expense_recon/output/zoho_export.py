"""Zoho Books journal-entry export — BLUEPRINT slice 4.6 (skeleton).

SKELETON STATUS. The CSV column shape is the Zoho Books journal-entry
import format and is stable, but two things are deliberately
placeholder until Chris's data lands:

* **Account names.** Until chart-of-accounts ingest (slice 4.1) maps
  our 8 categories to Brisken's real Zoho GL accounts, the `Account`
  column carries the category name on the expense side, a
  `Card: {account_id}` placeholder on the balancing side, and
  `(uncategorized - assign)` where no category was assigned. None of
  these are real Zoho account names yet.
* **Personal / business / reimbursement mapping** (v2 spec §31) is
  unresolved, so every line is treated as a straight business expense
  for now.

Double-entry shape: one Debit row per categorized line item (to its
expense account) plus one balancing Credit row per transaction (to the
card / bank account), linked by `Reference#` = transaction_id. A
multi-line Amazon receipt becomes N debit rows + 1 credit row, all
sharing the transaction_id.

Posting policy: only MATCHED transactions are exported. FX / ambiguous
/ review / unmatched items are withheld until confirmed
(call-outcomes D2 — review everything for the first months). Which
items become post-ready is a policy decision to settle with Chris;
this skeleton takes the conservative default.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ..matching.types import (
    ClassificationSource,
    MatchOutcome,
    Receipt,
    Transaction,
)

ZOHO_COLUMNS = (
    "Date",
    "Account",
    "Description",
    "Reference#",
    "Notes",
    "Debit",
    "Credit",
)

_CARD_ACCOUNT = "Card: {account_id}"
_UNCATEGORIZED = "(uncategorized - assign)"


def _amount(value: Decimal | None) -> str:
    """Format a Decimal for the CSV; blank for the unused debit/credit side."""
    if value is None:
        return ""
    return f"{value:.2f}"


def build_journal_rows(
    outcome: MatchOutcome,
    tx_by_id: dict[str, Transaction],
    rec_by_id: dict[str, Receipt],
) -> list[list[str]]:
    """Build the Zoho journal rows for the matched transactions.

    Returns a list of rows in `ZOHO_COLUMNS` order (no header). One
    debit row per categorized line item + one balancing credit row per
    transaction.
    """
    rows: list[list[str]] = []

    for match in outcome.matches:
        tx = tx_by_id.get(match.transaction_id)
        rec = rec_by_id.get(match.document_id)
        if tx is None or rec is None:
            continue

        date_str = tx.transaction_date.isoformat() if tx.transaction_date else ""
        ref = tx.transaction_id
        line_total_sum = Decimal("0")

        items = rec.line_items or ()
        if not items:
            # Defensive: categorizer normally synthesizes one line item.
            rows.append([
                date_str, _UNCATEGORIZED, tx.vendor_from_statement, ref,
                "no line items", _amount(tx.amount), "",
            ])
            line_total_sum += tx.amount
        else:
            for item in items:
                cat = item.categorization
                if cat and cat.source is not ClassificationSource.REVIEW and cat.category:
                    account = cat.zoho_account or cat.category
                    notes = f"{cat.source.value} conf={cat.confidence:.2f}"
                else:
                    account = _UNCATEGORIZED
                    notes = "needs category"
                rows.append([
                    date_str, account, item.description, ref,
                    notes, _amount(item.line_total), "",
                ])
                line_total_sum += item.line_total

        # Balancing credit to the card / bank account.
        rows.append([
            date_str,
            _CARD_ACCOUNT.format(account_id=tx.account_id),
            f"Payment to {tx.vendor_from_statement}",
            ref,
            "balancing entry",
            "",
            _amount(line_total_sum),
        ])

    return rows


def write_zoho_export(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    out_path: str | Path,
) -> Path:
    """Write the Zoho Books journal-entry CSV. Returns the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    rows = build_journal_rows(outcome, tx_by_id, rec_by_id)

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(ZOHO_COLUMNS)
        writer.writerows(rows)

    return out_path
