"""Zoho Books "Expenses" import CSV — one row per expense (receipt-first).

The statement-free sibling of `zoho_export.py`. Where the journal export
posts a double-entry journal keyed to a bank-statement transaction, this
writes one Zoho Expense per receipt (Dirk's note #1, "the flow is
backwards"): the receipt IS the expense, no statement required.

Account resolution, the COA validation gate, per-line posting-amount
allocation, and the §17 disposition rules are REUSED from `zoho_export.py`
so the two exports resolve accounts identically and a bad account can never
reach either file.

The column set is Zoho Books' standard Expenses import shape. Header
spellings were validated 2026-07-29 against this tenant's own downloaded
import template (`sample_expense.xls`): `Expense Amount`, `Vendor`, and
`Reference#` match Zoho's exact headers, so the import's field-mapping step
auto-maps them (a mismatched header drops a column to "unmapped" and has to
be hand-mapped on every import). `Tax Name`, `Tax Amount`, `Legal Entity`,
and `Receipt URL` are NOT in Zoho's expense import template; they carry
extracted or reference data, and Zoho silently ignores any column it cannot
map, so they stay as human-reference helpers (Zoho scopes the org per
import and attaches receipts in-app, not via CSV).
"""
from __future__ import annotations

import csv
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from .zoho_export import (
    _DISPOSITION_REIMBURSABLE,
    _DISPOSITION_WITHHELD,
    _REIMBURSABLE_PLACEHOLDER,
    _UNCATEGORIZED,
    _amount,
    _debit_account_and_note,
    _posting_amounts,
    _resolve_account,
    _str,
)

if TYPE_CHECKING:
    from ..coa_gate import CoaGate
    from ..ingest.chart_of_accounts import ChartOfAccounts
    from ..matching.types import Receipt

EXPENSE_COLUMNS = (
    "Expense Date",
    "Expense Account",
    "Expense Amount",
    "Currency Code",
    "Exchange Rate",
    "Paid Through",
    "Vendor",
    "Reference#",
    "Expense Description",
    "Tax Name",
    "Tax Amount",
    "Customer Name",
    "Legal Entity",
    "Receipt URL",
)

_PAID_THROUGH_PLACEHOLDER = "(paid-through - assign)"


def _card_last4(payment_mode: str | None) -> str | None:
    """The paying card's last 4 digits from the receipt's OCR payment
    hint. The vision extractor writes it as "Visa ...1234" / "1234" / a
    tender word ("Cash", "Amex"), so this pulls the trailing 4-digit
    group, or None when none is printed (cash, tender-only, unreadable).
    """
    if not payment_mode:
        return None
    groups = re.findall(r"\d{4}", payment_mode)
    return groups[-1] if groups else None


def _card_account(
    payment_mode: str | None, card_accounts: "Mapping[str, str] | None"
) -> str | None:
    """The Zoho "Paid Through" account for the card a receipt was paid on,
    via the `card_accounts` digit -> account map (the same map the journal
    export credits against). None when the receipt names no card, or names
    a card the map does not know: an unknown card falls through to the
    default rather than posting to a wrong account (B4).

    The trailing digit group keeps its historic fuzzy comparison; the
    EARLIER runs are also tried (Cards R2, 2026-08-21) because a Zoho
    payment-mode label prints BOTH of a card's digit identities
    ("1 - CorpServ 2838/1672 (Chase)": statement marker 2838, plastic
    last-4 1672) and the map may know the card under either — but an
    earlier run matches EXACTLY only, and two distinct account hits deny.
    A masked-PAN BIN fragment ("5412 75** **** 3456") must never
    endswith-wildcard its way onto an unrelated card: this is a money
    path, so a visible gap beats a guessed account (R2 adversarial
    review).
    """
    if not payment_mode or not card_accounts:
        return None
    runs = re.findall(r"\d{4}", payment_mode)
    if not runs:
        return None
    last4 = runs[-1]
    for key, account in card_accounts.items():
        k = str(key).strip()
        if k and account and (
            k == last4 or last4.endswith(k) or k.endswith(last4)
        ):
            return str(account)
    hits: list[str] = []
    for run in runs[:-1]:
        norm = run.lstrip("0") or "0"
        for key, account in card_accounts.items():
            k = str(key).strip()
            if k and account and (k.lstrip("0") or "0") == norm:
                hits.append(str(account))
    return hits[0] if len(set(hits)) == 1 else None


def _resolve_or(
    ref: str | None, coa: "ChartOfAccounts | None", placeholder: str
) -> str:
    """A reference resolved against the chart, or the placeholder when the
    reference is empty. Mirrors the export's account resolution exactly."""
    if not ref:
        return placeholder
    if coa is None:
        return ref
    return _resolve_account(ref, coa) or ref


def resolve_paid_through(
    receipt: "Receipt",
    override: str | None,
    default: str | None,
    disposition: str | None,
    reimbursable_account: str | None,
    coa: "ChartOfAccounts | None",
    card_accounts: "Mapping[str, str] | None" = None,
) -> tuple[str, str]:
    """Resolve the "Paid Through" account AND how it was chosen, so the
    review grid can show the same account the export will post plus its
    provenance.

    Order: a reimbursable_personal expense (§17) redirects to the
    reimbursement clearing account; otherwise per-expense override ->
    the receipt's own Zoho "Paid Through" (ER path) -> the card the
    receipt was paid on (its OCR'd last4 mapped through `card_accounts`)
    -> the run-level default -> a visible placeholder (never guessed, B4).
    The card step reads the last4 the receipt prints and translates it to
    a real Zoho account via `card_accounts`; a card the map does not know
    falls through rather than posting to a wrong account.

    Returns (account, source) where source is one of: reimbursable,
    override, receipt, card, default, unassigned.
    """
    if disposition == _DISPOSITION_REIMBURSABLE:
        return (
            _resolve_or(reimbursable_account, coa, _REIMBURSABLE_PLACEHOLDER),
            "reimbursable",
        )
    if override:
        return _resolve_or(override, coa, _PAID_THROUGH_PLACEHOLDER), "override"
    if receipt.paid_through:
        return _resolve_or(receipt.paid_through, coa, _PAID_THROUGH_PLACEHOLDER), "receipt"
    card = _card_account(receipt.payment_mode, card_accounts)
    if card:
        return _resolve_or(card, coa, _PAID_THROUGH_PLACEHOLDER), "card"
    if default:
        return _resolve_or(default, coa, _PAID_THROUGH_PLACEHOLDER), "default"
    return _PAID_THROUGH_PLACEHOLDER, "unassigned"


def _paid_through(
    receipt: "Receipt",
    override: str | None,
    default: str | None,
    disposition: str | None,
    reimbursable_account: str | None,
    coa: "ChartOfAccounts | None",
    card_accounts: "Mapping[str, str] | None" = None,
) -> str:
    """The exported Paid Through account (the account half of
    `resolve_paid_through`)."""
    return resolve_paid_through(
        receipt, override, default, disposition, reimbursable_account, coa,
        card_accounts,
    )[0]


def build_expense_rows(
    receipts: "Sequence[Receipt]",
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    coa_gate: "CoaGate | None" = None,
    default_paid_through: str | None = None,
    paid_through_by_doc: "Mapping[str, str] | None" = None,
    entity_by_doc: "Mapping[str, str] | None" = None,
    dispositions: "Mapping[str, str] | None" = None,
    reimbursable_account: str | None = None,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    customer_by_doc: "Mapping[str, str] | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
) -> list[list[str]]:
    """Build the Zoho Expenses rows (no header), one row per expense.

    Each receipt becomes one expense row. A receipt whose line items
    resolve to more than one Zoho account splits into one row per account
    (the amount allocated across accounts via `_posting_amounts`, sharing
    the Reference#), because a single Zoho expense posts to one account.
    Tax lands on the FIRST row of an expense only, so a split never
    double-counts tax.

    `coa_gate` diverts any non-postable account to review before a row is
    built (the same guarantee as the journal export). `dispositions`
    (document_id -> §17 disposition) withholds personal / do-not-export
    expenses and redirects a reimbursable expense's Paid Through. Every
    map is keyed by `document_id`.
    """
    if coa_gate is not None:
        gated, _report = coa_gate.run(list(receipts))
        receipts = gated

    rows: list[list[str]] = []
    for r in receipts:
        disposition = (dispositions or {}).get(r.document_id)
        if disposition in _DISPOSITION_WITHHELD:
            continue

        date_str = r.detected_date.isoformat() if r.detected_date else ""
        ref = r.detected_reference or r.document_id
        # Same display rule as the web grid: the registry's canonical merchant
        # name wins over the raw OCR reading, so the Zoho import carries ONE
        # spelling per merchant instead of whatever the extractor saw today.
        vendor = r.canonical_vendor or r.detected_vendor or ""
        ccy = (r.detected_currency or "").upper()
        rate = _amount(r.exchange_rate) if r.exchange_rate is not None else ""
        tax_amt = _amount(r.detected_tax) if r.detected_tax is not None else ""
        tax_label = r.tax_label or ""
        entity = (entity_by_doc or {}).get(r.document_id) or r.legal_entity_id or ""
        customer = (customer_by_doc or {}).get(r.document_id, "")
        url = (
            receipt_urls.get(r.document_id)
            if receipt_urls is not None
            else r.receipt_url
        ) or ""
        paid_through = _paid_through(
            r,
            (paid_through_by_doc or {}).get(r.document_id),
            default_paid_through,
            disposition,
            reimbursable_account,
            chart_of_accounts,
            card_accounts,
        )

        first = True
        for account, amt, part_descs in expense_posting_parts(
            r, chart_of_accounts=chart_of_accounts, fallback_desc=vendor
        ):
            description = "; ".join(part_descs) or vendor
            rows.append([
                date_str,
                account,
                _amount(amt),
                ccy,
                rate,
                paid_through,
                vendor,
                ref,
                description,
                tax_label if first else "",
                tax_amt if first else "",
                customer,
                entity,
                _str(url),
            ])
            first = False
    return rows


def expense_posting_parts(
    receipt: "Receipt",
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    fallback_desc: str = "",
) -> list[tuple[str, Decimal, list[str]]]:
    """The per-account fan-out for ONE expense: `[(account, amount,
    descriptions)]` in first-appearance order, zero-amount groups dropped.

    Resolve each line to its Zoho account + posted amount, then aggregate
    by account so a single-account expense is one part and a genuinely
    multi-account receipt splits cleanly. The receipt's own currency is
    the expense currency (no statement to convert against), so line totals
    and detected_total share a currency and the allocation only absorbs
    rounding / line-sum mismatch.

    This is the exact split `build_expense_rows` writes; the web grid's
    `books_as` depiction (backlog item 2) calls the same function so the
    grid and the export agree by construction.
    """
    charged = receipt.detected_total or Decimal("0")
    items = receipt.line_items or ()
    if not items:
        pairs = [(_UNCATEGORIZED, charged, fallback_desc)]
    else:
        posting = _posting_amounts([i.line_total for i in items], charged)
        pairs = [
            (
                _debit_account_and_note(item.categorization, chart_of_accounts)[0],
                posted,
                item.description,
            )
            for item, posted in zip(items, posting)
        ]

    amounts: dict[str, Decimal] = {}
    descs: dict[str, list[str]] = {}
    order: list[str] = []
    for account, amount, desc in pairs:
        if account not in amounts:
            amounts[account] = Decimal("0")
            descs[account] = []
            order.append(account)
        amounts[account] += amount
        if desc:
            descs[account].append(desc)
    return [
        (account, amounts[account], descs[account])
        for account in order
        if amounts[account] != 0
    ]


def write_zoho_expense_export(
    receipts: "Sequence[Receipt]",
    out_path: str | Path,
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    coa_gate: "CoaGate | None" = None,
    default_paid_through: str | None = None,
    paid_through_by_doc: "Mapping[str, str] | None" = None,
    entity_by_doc: "Mapping[str, str] | None" = None,
    dispositions: "Mapping[str, str] | None" = None,
    reimbursable_account: str | None = None,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    customer_by_doc: "Mapping[str, str] | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
) -> Path:
    """Write the Zoho Books Expenses import CSV (one row per expense).
    Returns the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_expense_rows(
        receipts,
        chart_of_accounts=chart_of_accounts,
        coa_gate=coa_gate,
        default_paid_through=default_paid_through,
        paid_through_by_doc=paid_through_by_doc,
        entity_by_doc=entity_by_doc,
        dispositions=dispositions,
        reimbursable_account=reimbursable_account,
        receipt_urls=receipt_urls,
        customer_by_doc=customer_by_doc,
        card_accounts=card_accounts,
    )
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(EXPENSE_COLUMNS)
        writer.writerows(rows)
    return out_path
