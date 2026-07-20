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

`Personal / business / reimbursement` (§17, 2026-07-20): the reviewer's
per-transaction ``dispositions`` map controls how each entry posts.
``business`` (and any transaction absent from the map) posts normally;
``personal_on_business_card`` and ``do_not_export`` are withheld from the
journal (still fully present in the report / reconciled CSV — nothing
silently dropped); ``reimbursable_personal`` posts with its balancing
credit redirected to the reimbursement clearing account
(``reimbursable_account``, from config ``zoho.reimbursable_account``) —
only the credit ACCOUNT changes, never the amount, so double-entry
holds. ``dispositions=None`` (the default) treats every line as a
straight business expense, byte-for-byte the pre-§17 output.

Double-entry shape: one Debit row per categorized line item (to its
expense account) plus one balancing Credit row per transaction (to the
card / bank account), linked by `Reference#` = transaction_id. A
multi-line Amazon receipt becomes N debit rows + 1 credit row, all
sharing the transaction_id.

Posting policy: MATCHED transactions are exported. FX / ambiguous /
review items are withheld until confirmed (call-outcomes D2 — review
everything for the first months). Receiptless charges (Slice 10,
2026-07-20): an unmatched charge whose side-map categorization is
Tier-1 LEARNED (a confirmed merchant->account recalled from memory or
seeded from Zoho posting history) is posting-ELIGIBLE, but only behind
the opt-in `include_receiptless_learned` flag (config
`zoho.export_receiptless_learned`) — withheld-until-confirmed default.
VENDOR / REVIEW charges never export. The COA gate runs on the charge
pseudo-receipts the same way it runs on matched receipts, so a bad
account diverts to review instead of reaching the file. Journal
POSTING to Zoho (slice 4b) is irreversible and stays gated behind
explicit confirmation; this module only writes the import file.

Path-A reference columns (BLUEPRINT 8.5): two trailing columns carry the
receipt link and the Zoho Expense report each entry traces to, so Chris
can click through to the receipt image and see its ER report straight
from the journal. ``Receipt URL`` comes from the 8.4
``resolve_receipt_urls`` mapping when wired, else the receipt's own
passthrough ``receipt_url``; ``Report Reference`` comes from the 8.3
``ReportStore.report_for`` lookup when wired, else the receipt's own
``report_number`` (the 8.1 adapter populates both). They repeat per row
of an entry, the same way ``Date`` and ``Reference#`` already do, and are
blank when unknown (never fabricated, B4). Appended after ``Credit`` so
the existing seven-column shape and its column positions are unchanged.
"""
from __future__ import annotations

import csv
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from ..matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    MatchOutcome,
    Receipt,
    Transaction,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ..coa_gate import CoaGate
    from ..ingest.chart_of_accounts import ChartOfAccounts

ZOHO_COLUMNS = (
    "Date",
    "Account",
    "Description",
    "Reference#",
    "Notes",
    "Debit",
    "Credit",
    "Receipt URL",
    "Report Reference",
)

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


def _str(value: str | None) -> str:
    """A reference cell: the value, or blank when unknown (never guessed)."""
    return value or ""


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


def _reimbursable_credit_and_note(
    reimbursable_account: str | None, coa: "ChartOfAccounts | None"
) -> tuple[str, str]:
    """Account + Notes for a `reimbursable_personal` entry's credit row (§17).

    The credit is redirected from the card account to the reimbursement
    clearing account — only the ACCOUNT changes, never the amount, so the
    entry still balances. Unconfigured => a visible placeholder, never a
    guess (B4); an account that does not resolve against the chart passes
    through flagged, mirroring `_credit_account_and_note`.
    """
    if not reimbursable_account:
        return (
            _REIMBURSABLE_PLACEHOLDER,
            "balancing entry (reimbursable - assign clearing account)",
        )
    if coa is None:
        return reimbursable_account, "balancing entry (reimbursable)"
    resolved = _resolve_account(reimbursable_account, coa)
    if resolved is None:
        return (
            reimbursable_account,
            "balancing entry (reimbursable account not in chart) — verify",
        )
    return resolved, "balancing entry (reimbursable)"


def build_journal_rows(
    outcome: MatchOutcome,
    tx_by_id: dict[str, Transaction],
    rec_by_id: dict[str, Receipt],
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    report_for: "Callable[[str], str | None] | None" = None,
    coa_gate: "CoaGate | None" = None,
    charge_categorizations: "Mapping[str, Categorization] | None" = None,
    include_receiptless_learned: bool = False,
    dispositions: "Mapping[str, str] | None" = None,
    reimbursable_account: str | None = None,
) -> list[list[str]]:
    """Build the Zoho journal rows for the matched transactions.

    Returns a list of rows in `ZOHO_COLUMNS` order (no header). One
    debit row per categorized line item + one balancing credit row per
    transaction.

    `chart_of_accounts` resolves LLM-picked account labels (debit) and
    `card_accounts` references (credit) to real Zoho accounts. Both
    optional: without them the legacy category-name / placeholder
    behaviour applies.

    `coa_gate` (opt-in; None = no change) is the pre-write
    chart-of-accounts validation gate. When present, every categorized
    line's posting account is validated against the target legal entity's
    chart BEFORE rows are built; any line whose account is missing /
    unknown / inactive / DO-NOT-USE / non-leaf / out-of-scope is diverted
    to review (account blanked, source set REVIEW), so a bad account can
    never resolve into the export. See `coa_gate.CoaGate`.

    `receipt_urls` (8.4 `resolve_receipt_urls` output, document_id → URL)
    and `report_for` (8.3 `ReportStore.report_for`, document_id →
    report_number) fill the two trailing reference columns. Both
    optional: without them each receipt's own `receipt_url` /
    `report_number` (8.1) is used, so the existing CLI path carries the
    references with no extra wiring. Unknown → blank, never fabricated.

    `charge_categorizations` (Slice 10 side-map, transaction_id →
    Categorization) + `include_receiptless_learned` add the receiptless-
    charge rows: with the flag on, each unmatched charge whose (COA-
    gated) categorization is still Tier-1 LEARNED gets one debit row to
    its learned account + one balancing credit row. VENDOR / REVIEW
    charges, gate-diverted charges, and `entry_status == "posted"`
    charges are never written. Flag off (the default) => byte-for-byte
    prior behaviour.

    `dispositions` (§17, transaction_id → disposition) withholds
    `personal_on_business_card` / `do_not_export` entries and redirects
    the balancing credit of `reimbursable_personal` entries to
    `reimbursable_account` (placeholder when unset — visible, never
    guessed). Applies to matched AND receiptless-charge entries. None
    (the default) => byte-for-byte prior behaviour.
    """
    # Pre-write COA validation: divert any line with a non-postable
    # account to review before it can resolve into a debit row. Rebuilds
    # rec_by_id from the gated receipts so the loop below sees the diverted
    # categorizations.
    if coa_gate is not None:
        gated, _report = coa_gate.run(list(rec_by_id.values()))
        rec_by_id = {r.document_id: r for r in gated}

    rows: list[list[str]] = []

    for match in outcome.matches:
        tx = tx_by_id.get(match.transaction_id)
        rec = rec_by_id.get(match.document_id)
        if tx is None or rec is None:
            continue
        # L1 posting policy: a yellow row in Chris's workbook is ALREADY
        # entered in Zoho — exporting it again would double-post the
        # journal. The row stays fully visible in the report and the
        # reconciled CSV (nothing silently dropped); only the Books
        # import skips it. The skip count is surfaced by the callers.
        if tx.entry_status == "posted":
            continue
        # §17 posting policy: personal spend on the business card, and an
        # explicit do-not-export, never reach the journal. The row stays
        # fully visible in the report / reconciled CSV (nothing silently
        # dropped) — only the Books import withholds it.
        disposition = (dispositions or {}).get(tx.transaction_id)
        if disposition in _DISPOSITION_WITHHELD:
            continue

        date_str = tx.transaction_date.isoformat() if tx.transaction_date else ""
        ref = tx.transaction_id
        line_total_sum = Decimal("0")

        # Entry-level reference columns: the wired 8.4 / 8.3 lookups take
        # precedence; the receipt's own 8.1 fields are the fallback. These
        # repeat on every row of the entry, like Date and Reference#.
        receipt_url = (
            receipt_urls.get(rec.document_id)
            if receipt_urls is not None
            else rec.receipt_url
        )
        report_ref = (
            report_for(rec.document_id)
            if report_for is not None
            else rec.report_number
        )
        provenance = [_str(receipt_url), _str(report_ref)]

        items = rec.line_items or ()
        if not items:
            # Defensive: categorizer normally synthesizes one line item.
            rows.append([
                date_str, _UNCATEGORIZED, tx.vendor_from_statement, ref,
                "no line items", _amount(tx.amount), "",
            ] + provenance)
            line_total_sum += tx.amount
        else:
            for item in items:
                account, notes = _debit_account_and_note(
                    item.categorization, chart_of_accounts
                )
                rows.append([
                    date_str, account, item.description, ref,
                    notes, _amount(item.line_total), "",
                ] + provenance)
                line_total_sum += item.line_total

        # Balancing credit to the card / bank account — or, for a
        # reimbursable_personal entry (§17), to the reimbursement clearing
        # account (same amount, different account; double-entry holds).
        if disposition == _DISPOSITION_REIMBURSABLE:
            credit_account, credit_note = _reimbursable_credit_and_note(
                reimbursable_account, chart_of_accounts
            )
        else:
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
        ] + provenance)

    # Slice 10: postable receiptless-LEARNED charges (opt-in flag).
    if include_receiptless_learned and charge_categorizations:
        rows.extend(
            _receiptless_charge_rows(
                outcome,
                tx_by_id,
                charge_categorizations,
                chart_of_accounts=chart_of_accounts,
                card_accounts=card_accounts,
                coa_gate=coa_gate,
                dispositions=dispositions,
                reimbursable_account=reimbursable_account,
            )
        )

    return rows


def _receiptless_charge_rows(
    outcome: MatchOutcome,
    tx_by_id: dict[str, Transaction],
    charge_categorizations: "Mapping[str, Categorization]",
    *,
    chart_of_accounts: "ChartOfAccounts | None",
    card_accounts: "Mapping[str, str] | None",
    coa_gate: "CoaGate | None",
    dispositions: "Mapping[str, str] | None" = None,
    reimbursable_account: str | None = None,
) -> list[list[str]]:
    """Journal rows for the unmatched charges whose categorization is
    Tier-1 LEARNED. Each becomes one debit row (the learned account) +
    one balancing credit row (the card account), Reference# = the
    transaction id. The receipt-URL / report-reference columns stay
    blank — there IS no receipt, and B4 says blank over fabricated.

    The COA gate runs on charge pseudo-receipts exactly as it runs on
    matched receipts; a diverted line (source flipped to REVIEW) drops
    out of the file entirely — a receiptless charge is either cleanly
    postable or review-only, never exported flagged.
    """
    from ..categorize_charges import CHARGE_DOC_PREFIX, build_charge_pseudo_receipt

    pseudo: list[Receipt] = []
    for tx_id in outcome.unmatched_transactions:
        tx = tx_by_id.get(tx_id)
        cat = charge_categorizations.get(tx_id)
        if tx is None or cat is None:
            continue
        if cat.source is not ClassificationSource.LEARNED or not cat.category:
            continue  # VENDOR / REVIEW charges stay review-only
        # L1 posting policy, same as the matched loop: an already-in-Zoho
        # row never reaches the journal again.
        if tx.entry_status == "posted":
            continue
        # §17: personal / do-not-export receiptless charges are withheld too.
        if (dispositions or {}).get(tx_id) in _DISPOSITION_WITHHELD:
            continue
        line = LineItem(
            description=tx.vendor_from_statement,
            line_total=tx.amount,
            categorization=cat,
        )
        pseudo.append(
            replace(build_charge_pseudo_receipt(tx), line_items=(line,))
        )

    if not pseudo:
        return []
    if coa_gate is not None:
        pseudo, _report = coa_gate.run(pseudo)

    rows: list[list[str]] = []
    for rec in pseudo:
        item = rec.line_items[0]
        cat = item.categorization
        if (
            cat is None
            or cat.source is not ClassificationSource.LEARNED
            or not cat.category
        ):
            continue  # gate-diverted -> review, not the journal
        tx = tx_by_id[rec.document_id[len(CHARGE_DOC_PREFIX):]]
        account, note = _debit_account_and_note(cat, chart_of_accounts)
        note = f"{note} · receiptless charge"
        if cat.reasoning:
            note = f"{note} ({cat.reasoning})"
        date_str = tx.transaction_date.isoformat() if tx.transaction_date else ""
        ref = tx.transaction_id
        provenance = ["", ""]
        rows.append([
            date_str, account, tx.vendor_from_statement, ref,
            note, _amount(tx.amount), "",
        ] + provenance)
        if (dispositions or {}).get(tx.transaction_id) == _DISPOSITION_REIMBURSABLE:
            credit_account, credit_note = _reimbursable_credit_and_note(
                reimbursable_account, chart_of_accounts
            )
        else:
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
            _amount(tx.amount),
        ] + provenance)
    return rows


def write_zoho_export(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    out_path: str | Path,
    *,
    chart_of_accounts: "ChartOfAccounts | None" = None,
    card_accounts: "Mapping[str, str] | None" = None,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    report_for: "Callable[[str], str | None] | None" = None,
    coa_gate: "CoaGate | None" = None,
    charge_categorizations: "Mapping[str, Categorization] | None" = None,
    include_receiptless_learned: bool = False,
    dispositions: "Mapping[str, str] | None" = None,
    reimbursable_account: str | None = None,
) -> Path:
    """Write the Zoho Books journal-entry CSV. Returns the path.

    `coa_gate` (opt-in; None = no change) validates each posting account
    against the target legal entity's chart and diverts any non-postable
    line to review before it can reach the file. See
    `build_journal_rows` / `coa_gate.CoaGate`.

    `charge_categorizations` + `include_receiptless_learned` (Slice 10,
    both opt-in) add the receiptless-LEARNED charge entries; see
    `build_journal_rows`.

    `dispositions` + `reimbursable_account` (§17, opt-in) withhold personal
    / do-not-export entries and redirect reimbursable credits; see
    `build_journal_rows`.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    rows = build_journal_rows(
        outcome, tx_by_id, rec_by_id,
        chart_of_accounts=chart_of_accounts,
        card_accounts=card_accounts,
        receipt_urls=receipt_urls,
        report_for=report_for,
        coa_gate=coa_gate,
        charge_categorizations=charge_categorizations,
        include_receiptless_learned=include_receiptless_learned,
        dispositions=dispositions,
        reimbursable_account=reimbursable_account,
    )

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(ZOHO_COLUMNS)
        writer.writerows(rows)

    return out_path
