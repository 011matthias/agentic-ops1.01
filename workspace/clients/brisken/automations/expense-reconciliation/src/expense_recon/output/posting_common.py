"""Posting helpers shared by the expense export and the sheet writeback.

Lifted out of `zoho_export.py` unchanged (backlog item 23, layer 4) so the
journal export can be deleted without taking its callers with it. Nothing
here is Zoho-specific: the amounts rule, the account resolution and the
disposition sentinels are the app's own posting vocabulary.

`_UNCATEGORIZED` is byte-stable on purpose: `web/service.py` compares
against that exact literal to set `expenses[].books_as[].unassigned`, which
is contract-pinned in `tests/test_view_contract.py`.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from ..matching.types import Categorization, ClassificationSource

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import Account, ChartOfAccounts


_CARD_ACCOUNT = "Card: {account_id}"
_UNCATEGORIZED = "(uncategorized - assign)"
_UNMAPPED = "(account unmapped - assign)"

# §17 disposition values (string-typed copies of web.store's
# VALID_DISPOSITIONS members; the output layer stays import-free of the
# web layer). Absent / "business" posts normally.
_DISPOSITION_WITHHELD = frozenset({"personal_on_business_card", "do_not_export"})
_DISPOSITION_REIMBURSABLE = "reimbursable_personal"
_REIMBURSABLE_PLACEHOLDER = "(reimbursable clearing - assign)"


def _amount(value: Decimal | None) -> str:
    """Format a Decimal for the CSV; blank for the unused debit/credit side."""
    if value is None:
        return ""
    return f"{value:.2f}"


_CENT = Decimal("0.01")


def _posting_amounts(
    line_totals: "list[Decimal]", charged: Decimal
) -> list[Decimal]:
    """Allocate the CHARGED amount across a receipt's line items.

    The journal posts in the statement currency, because the bank
    statement is the source of truth for what the company actually paid
    (Chris's process, 2026-07-15). A receipt's line items are in the
    receipt's own currency: a BRL meal on a USD card lists BRL line
    totals while the card was charged USD. Writing those line totals
    into the journal posts the wrong number in the wrong currency — on
    the real April run a 9.18 USD charge exported as 46.00 of BRL
    debits, roughly 5x the true amount.

    Each line keeps its share of the charge, proportional to its own
    total, with the rounding residual applied to the largest line so the
    debits sum EXACTLY to `charged` and double-entry holds to the cent.
    This also absorbs the common case where the parsed lines do not sum
    to the receipt's printed total (April: lines 46.00 vs printed
    47.50) — the bank's number wins, rather than the journal disagreeing
    with the statement.

    Same-currency receipts whose lines already sum to the charge are
    unaffected: the allocation is the identity.
    """
    total = sum(line_totals, Decimal("0"))
    if total <= 0:
        # No usable split (all-zero or negative lines): put the whole
        # charge on the first line rather than emitting zero debits.
        return [charged] + [Decimal("0")] * (len(line_totals) - 1)
    out = [
        (charged * lt / total).quantize(_CENT) for lt in line_totals
    ]
    residual = charged - sum(out, Decimal("0"))
    if residual:
        biggest = max(range(len(out)), key=lambda i: out[i])
        out[biggest] += residual
    return out


def _str(value: str | None) -> str:
    """A reference cell: the value, or blank when unknown (never guessed)."""
    return value or ""


def resolve_ref(ref: str | None, coa: "ChartOfAccounts") -> "Account | None":
    """Resolve an account reference to its chart Account, or None.

    `ref` is what the categorizer / config carries: a `"CODE name"`
    label, a bare code, or a bare name. Resolution order: exact
    code-or-name (`ChartOfAccounts.resolve`), then the leading token as
    a code, then the remainder as a name. None when nothing in the chart
    matches; the caller flags it and never guesses.

    The single resolution order for the whole posting surface. The file
    exports want the account's NAME (`_resolve_account` below) and the
    API poster wants its numeric `account_id` (`zoho.accounts`), and the
    two must never disagree about WHICH account a reference means.
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
    return acct


def _resolve_account(ref: str | None, coa: "ChartOfAccounts") -> str | None:
    """The canonical posting account NAME for a reference, or None when
    nothing in the chart matches. Thin wrapper over `resolve_ref`."""
    acct = resolve_ref(ref, coa)
    return acct.name if acct else None


def _debit_account_and_note(
    cat: Categorization | None, coa: "ChartOfAccounts | None"
) -> tuple[str, str]:
    """Account + Notes for one line item's debit row.

    REVIEW / no-category lines stay flagged. With a chart, the picked
    `zoho_account` is resolved to a real account; an unresolvable pick
    is flagged `(account unmapped - assign)` rather than guessed.

    A line with no account is flagged the same way with or without a
    chart. The account column never carries the CATEGORY: a bucket label
    is no account in any org, and under the GL engine a category is a leaf
    code, so either one there reads as an account nobody picked. It used
    to, whenever no chart loaded, which is every entity-less batch (its
    multi-entity gate has no single chart) and every uncharted CLI run.
    """
    if cat is None or cat.source is ClassificationSource.REVIEW or not cat.category:
        return _UNCATEGORIZED, "needs category"
    note = f"{cat.source.value} conf={cat.confidence:.2f}"
    if not cat.zoho_account:
        return _UNMAPPED, f"{cat.category} (no account match), assign"
    if coa is None:
        # No chart to resolve against: the pick passes through as written.
        return cat.zoho_account, note
    resolved = _resolve_account(cat.zoho_account, coa)
    if resolved is None:
        return _UNMAPPED, f"{cat.category} (no account match), assign"
    return resolved, note
