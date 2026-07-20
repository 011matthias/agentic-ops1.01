"""Flat reconciled CSV — the CSV twin of the `report_xlsx` review report.

Dirk's target output (2026-06-16): "output is CSV + Excel of the
reconciled data." `report_xlsx` is the Excel; this is the CSV. One flat
row per statement line (Transaction), in statement order, enriched with
the matched expense it reconciled against.

Grain is one row per statement transaction, NOT per receipt line item
(that is the journal-export grain in `zoho_export`). The whole bank line
is preserved verbatim — amount, currency, the original foreign detail,
the raw statement text, the dates — because Dirk's constraint is "all
data from the bank statement must stay as it was." The expense columns
to the right are the enrichment found during recon (report number, Zoho
GL category, receipt URL, paying card, the receipt's own amounts), blank
when the line did not match.

Match status is explicit per line so the file is a full reconciliation
view, not a posting file: every statement line shows MATCHED,
NEEDS_REVIEW (FX / ambiguous), or UNMATCHED. Unlike the Zoho journal
export, nothing is withheld — an unmatched charge is a row with blank
expense columns, never a silent drop (the reconciliation guarantee, v2
spec §25.5).

The two enrichment lookups mirror `zoho_export.build_journal_rows`:
``receipt_urls`` (8.4 `resolve_receipt_urls`, document_id → URL) and
``report_for`` (8.3 `ReportStore.report_for`, document_id →
report_number) take precedence over the receipt's own 8.1 fields when
wired; without them the receipt's own `receipt_url` / `report_number`
carry through, so the CLI path needs no extra wiring. Unknown values are
blank, never fabricated (B4).
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from ..matching.types import Categorization, Match, MatchOutcome, Receipt, Transaction

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


RECONCILED_COLUMNS = (
    # ── statement side (preserved verbatim — Dirk: bank data stays as it was) ──
    "Account",
    "Transaction Date",
    "Posting Date",
    "Description",
    "Statement Amount",
    "Currency",
    "Original Amount",
    "Original Currency",
    "FX Rate",
    "Statement Text",
    "Entry Status",
    # ── match status ──
    "Match Status",
    "Match Type",
    "Confidence",
    "Match Score",
    "Match Reason",
    # ── expense enrichment (blank when unmatched) ──
    "Expense ID",
    "Report Number",
    "Zoho Category",
    "Payment Mode",
    "Receipt URL",
    "Receipt Image",
    "Receipt Vendor",
    "Receipt Date",
    "Receipt Total",
    "Receipt Currency",
    "Base Amount",
    "Exchange Rate",
    "Reimbursable",
    # ── receiptless-charge categorization (Slice 10; blank unless the
    #    line is an unmatched charge the side-map categorized) ──
    "Charge Category",
    "Charge Zoho Account",
    "Charge Category Source",
)

# Statement-line dispositions. Mirrors the report_xlsx Explain sheet's
# first-write-wins ordering so a transaction keeps its primary bucket.
_STATUS_MATCHED = "MATCHED"
_STATUS_FX = "NEEDS_REVIEW (FX)"
_STATUS_AMBIGUOUS = "NEEDS_REVIEW (ambiguous)"
_STATUS_UNMATCHED = "UNMATCHED"


def _money(value: Decimal | None) -> str:
    """A currency amount at 2 dp; blank when absent."""
    return f"{value:.2f}" if value is not None else ""


def _rate(value: Decimal | None) -> str:
    """An FX rate, preserved at its captured precision (no rounding —
    the bank's printed rate stays verbatim); blank when absent."""
    return f"{value:f}" if value is not None else ""


def _date(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


def _str(value: str | None) -> str:
    """A reference cell: the value, or blank when unknown (never guessed)."""
    return value or ""


def _reimbursable(value: bool | None) -> str:
    if value is None:
        return ""
    return "Yes" if value else "No"


def _disposition(outcome: MatchOutcome) -> dict[str, tuple[str, Match | None]]:
    """transaction_id -> (status label, the disposing Match | None).

    First write wins, in priority order matched > FX > ambiguous >
    unmatched, so a transaction that somehow appears in two buckets keeps
    its strongest disposition (the report_xlsx Explain convention).
    """
    disp: dict[str, tuple[str, Match | None]] = {}
    for m in outcome.matches:
        disp.setdefault(m.transaction_id, (_STATUS_MATCHED, m))
    for m in outcome.judgment_required:
        disp.setdefault(m.transaction_id, (_STATUS_FX, m))
    for m in outcome.ambiguous:
        disp.setdefault(m.transaction_id, (_STATUS_AMBIGUOUS, m))
    for tx_id in outcome.unmatched_transactions:
        disp.setdefault(tx_id, (_STATUS_UNMATCHED, None))
    return disp


def build_reconciled_rows(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    *,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    report_for: "Callable[[str], str | None] | None" = None,
    charge_categorizations: "Mapping[str, Categorization] | None" = None,
) -> list[list[str]]:
    """Build the flat reconciled rows: one per statement line, in input
    (statement) order, in `RECONCILED_COLUMNS` order (no header row).

    Every transaction surfaces exactly once regardless of outcome; the
    expense columns carry the matched receipt's enrichment, or are blank
    for an unmatched / review-with-no-receipt line. For an ambiguous
    transaction the row carries the top candidate (the matcher / LLM
    tie-break promotes it to the front of its group).

    `charge_categorizations` (Slice 10 side-map) fills the three trailing
    charge-categorization columns on unmatched lines; blank elsewhere.
    """
    rec_by_id = {r.document_id: r for r in receipts}
    charge_cats = charge_categorizations or {}
    disp = _disposition(outcome)
    # L4 noise guard: only flag missing receipt images when the run's
    # source carries image info at all (the slice-1 receipts CSV never
    # populates receipt_url/receipt_name; flagging every row would be
    # noise, not signal).
    run_has_image_info = any(r.has_receipt_image for r in receipts)

    rows: list[list[str]] = []
    for tx in transactions:
        status, match = disp.get(tx.transaction_id, ("UNKNOWN", None))
        rec = rec_by_id.get(match.document_id) if match is not None else None

        # Entry-level reference columns: the wired 8.4 / 8.3 lookups take
        # precedence; the receipt's own 8.1 fields are the fallback.
        if rec is not None:
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
        else:
            receipt_url = None
            report_ref = None

        # Slice 10: the side-map only ever holds unmatched charges, so a
        # matched line's lookup is a no-op by construction.
        charge_cat = charge_cats.get(tx.transaction_id)
        if charge_cat is not None and not charge_cat.category:
            charge_cat = None  # REVIEW with no signal: stay blank, not noise

        rows.append([
            # statement side
            tx.account_id,
            _date(tx.transaction_date),
            _date(tx.posting_date),
            tx.vendor_from_statement,
            _money(tx.amount),
            tx.transaction_currency,
            _money(tx.original_amount),
            _str(tx.original_currency),
            _rate(tx.fx_rate),
            tx.raw_text,
            (
                "ALREADY_POSTED"
                if tx.entry_status == "posted"
                else ("SUBSCRIPTION" if tx.entry_status == "subscription" else "")
            ),
            # match status
            status,
            match.match_type.value if match is not None else "",
            f"{match.confidence:.2f}" if match is not None else "",
            str(match.score) if (match is not None and match.score) else "",
            match.reason if match is not None else "",
            # expense enrichment
            rec.document_id if rec is not None else "",
            _str(report_ref),
            _str(rec.zoho_category) if rec is not None else "",
            _str(rec.payment_mode) if rec is not None else "",
            _str(receipt_url),
            (
                ("Yes" if rec.has_receipt_image else "MISSING")
                if (rec is not None and run_has_image_info)
                else ""
            ),
            _str(rec.detected_vendor) if rec is not None else "",
            _date(rec.detected_date) if rec is not None else "",
            _money(rec.detected_total) if rec is not None else "",
            _str(rec.detected_currency) if rec is not None else "",
            _money(rec.base_amount) if rec is not None else "",
            _rate(rec.exchange_rate) if rec is not None else "",
            _reimbursable(rec.reimbursable) if rec is not None else "",
            # receiptless-charge categorization (Slice 10)
            _str(charge_cat.category) if charge_cat is not None else "",
            _str(charge_cat.zoho_account) if charge_cat is not None else "",
            charge_cat.source.value if charge_cat is not None else "",
        ])

    return rows


def write_reconciled_csv(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    out_path: str | Path,
    *,
    receipt_urls: "Mapping[str, str | None] | None" = None,
    report_for: "Callable[[str], str | None] | None" = None,
    charge_categorizations: "Mapping[str, Categorization] | None" = None,
) -> Path:
    """Write the flat reconciled CSV. Returns the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = build_reconciled_rows(
        outcome,
        transactions,
        receipts,
        receipt_urls=receipt_urls,
        report_for=report_for,
        charge_categorizations=charge_categorizations,
    )

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(RECONCILED_COLUMNS)
        writer.writerows(rows)

    return out_path
