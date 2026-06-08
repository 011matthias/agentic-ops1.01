"""Zoho Books journal-entry export — BLUEPRINT slice 4.6.

Builds a Zoho Books journal-entry import CSV from the matched
transactions. The CSV column shape is the stable Zoho Books
journal-entry import format.

Account resolution (slice 4.6 — de-placeholdered):

* **Expense (debit) side.** The categorizer attaches an LLM-picked
  `zoho_account` label (`"CODE name"`) to each line item's
  `Categorization`. When a `ChartOfAccounts` is supplied, that label is
  resolved to a real Zoho account via `ChartOfAccounts.resolve()` (the
  code is parsed from the leading token), and the resolved account name
  goes in the `Account` column. A line whose source is REVIEW, whose
  category is blank, or whose `zoho_account` does not resolve against
  the chart is left flagged (`(uncategorized - assign)` /
  `(account unmapped - assign)`) and never guessed.
* **Balancing (credit) side.** The card / bank account is resolved
  from the run config's `card_accounts` map (statement `account_id` →
  Zoho bank/card account reference), again via the chart of accounts.
  When no mapping exists for an account, the `Card: {account_id}`
  placeholder is kept so the gap is visible rather than guessed.

Without a `ChartOfAccounts` (legacy / no-Zoho runs), the export falls
back to the pre-4.6 behaviour: category name on the debit side, the
`Card: {account_id}` placeholder on the credit side.

`Personal / business / reimbursement` mapping (v2 spec §31) is still
unresolved; every line is treated as a straight business expense.

Double-entry shape: one Debit row per categorized line item (to its
expense account) plus one balancing Credit row per transaction (to the
card / bank account), linked by `Reference#` = transaction_id. A
multi-line Amazon receipt becomes N debit rows + 1 credit row, all
sharing the transaction_id.

Posting policy: only MATCHED transactions are exported. FX / ambiguous
/ review / unmatched items are withheld until confirmed
(call-outcomes D2 — review everything for the first months). Journal
POSTING to Zoho (slice 4b) is irreversible and stays gated behind
explicit confirmation; this module only writes the import file.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from ..matching.types import (
    Categorization,
    ClassificationSource,
    MatchOutcome,
    Receipt,
    Transaction,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ..ingest.chart_of_accounts import ChartOfAccounts

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
_UNMAPPED = "(account unmapped - assign)"


def _amount(value: Decimal | None) -> str:
    """Format a Decimal for the CSV; blank for the unused debit/credit side."""
    if value is None:
        return ""
    return f"{value:.2f}"


def _resolve_account(ref: str | None, coa: "ChartOfAccounts") -> str | None:
    """Resolve an account reference to its canonical Zoho account name.

    `ref` is what the categorizer / config carries: a `"CODE name"`
    label, a bare code, or a bare name. Resolution order: exact
    code-or-name (`ChartOfAccounts.resolve`), then the leading token as
    a code, then the remainder as a name. Returns the account name, or
    None when nothing in the chart matches (caller flags it, never
    guesses).
    """
    ref = (ref or "").strip()
    if not ref:
        return None
    acct = coa.resolve(ref)
    if acct is None:
        head, _, tail = ref.partition(" ")
        acct = coa.by_code(head.strip())
        if acct is None and tail.strip():
            acct = coa.by_name(tail.strip())
    return acct.name if acct else None


def _debit_account_and_note(
    cat: Categorization | None, coa: "ChartOfAccounts | None"
) -> tuple[str, str]:
    """Account + Notes for one line item's debit row.

    REVIEW / no-category lines stay flagged. With a chart, the picked
    `zoho_account` is resolved to a real account; an unresolvable pick
    is flagged `(account unmapped - assign)` rather than guessed.
    """
    if cat is None or cat.source is ClassificationSource.REVIEW or not cat.category:
        return _UNCATEGORIZED, "needs category"
    note = f"{cat.source.value} conf={cat.confidence:.2f}"
    if coa is None:
        # Legacy: no chart to resolve against — pass the label through.
        return (cat.zoho_account or cat.category), note
    resolved = _resolve_account(cat.zoho_account, coa)
    if resolved is None:
        return _UNMAPPED, f"{cat.category} (no Zoho account match) — assign"
    return resolved, note


def _credit_account_and_note(
    tx: Transaction,
    card_accounts: "Mapping[str, str] | None",
    coa: "ChartOfAccounts | None",
) -> tuple[str, str]:
    """Account + Notes for the balancing credit row.

    Maps the statement `account_id` to a real Zoho bank/card account via
    the `card_accounts` config map + chart of accounts. Falls back to
    the `Card: {account_id}` placeholder when no mapping exists, so the
    gap is visible.
    """
    ref = (card_accounts or {}).get(tx.account_id)
    if not ref:
        return (
            _CARD_ACCOUNT.format(account_id=tx.account_id),
            "balancing entry (card account unmapped)",
        )
    if coa is None:
        return ref, "balancing entry"
    resolved = _resolve_account(ref, coa)
    if resolved is None:
        return ref, "balancing entry (card account not in chart) — verify"
    return resolved, "balancing entry"


def build_journal_rows(
    outcome: MatchOutcome,
    tx_by_id: dict[str, Transaction],
    rec_by_id: dict[str, Receipt],
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
) -> list[list[str]]:
    """Build the Zoho journal rows for the matched transactions.

    Returns a list of rows in `ZOHO_COLUMNS` order (no header). One
    debit row per categorized line item + one balancing credit row per
    transaction.

    `chart_of_accounts` resolves LLM-picked account labels (debit) and
    `card_accounts` references (credit) to real Zoho accounts. Both
    optional: without them the legacy category-name / placeholder
    behaviour applies.
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
                account, notes = _debit_account_and_note(
                    item.categorization, chart_of_accounts
                )
                rows.append([
                    date_str, account, item.description, ref,
                    notes, _amount(item.line_total), "",
                ])
                line_total_sum += item.line_total

        # Balancing credit to the card / bank account.
        credit_account, credit_note = _credit_account_and_note(
            tx, card_accounts, chart_of_accounts
        )
        rows.append([
            date_str,
            credit_account,
            f"Payment to {tx.vendor_from_statement}",
            ref,
            credit_note,
            "",
            _amount(line_total_sum),
        ])

    return rows


def write_zoho_export(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    out_path: str | Path,
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
) -> Path:
    """Write the Zoho Books journal-entry CSV. Returns the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    rows = build_journal_rows(
        outcome, tx_by_id, rec_by_id,
        chart_of_accounts=chart_of_accounts,
        card_accounts=card_accounts,
    )

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(ZOHO_COLUMNS)
        writer.writerows(rows)

    return out_path
