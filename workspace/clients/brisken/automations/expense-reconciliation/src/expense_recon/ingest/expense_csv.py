"""Zoho Expense CSV ingest adapter — BLUEPRINT 8.1 (Path A).

Path A makes the Zoho Expense export the primary receipt source in
place of the generic slice-1 receipts CSV. Zoho Expense already holds
Chris's hand-entered expense lines (date, amount, currency, merchant,
the GL category, the report they belong to, the attached receipt). This
adapter reads that export and produces the same `Receipt` objects the
matcher already consumes; nothing downstream changes.

It is a config-driven **column map** over the receipts path, exactly
like `statement_csv.py` is for the bank side: the run config maps each
logical field to whatever the real export calls its column, so the tool
hardcodes no Zoho header names. The exact Zoho Expense export headers
are not pinned in code because no live export header has been shared
(owner-clarified 2026-06-12: the samples in hand are the full extent);
the map settles them per-run. `examples/run.with-expense-csv.example.json`
carries a documented-format template to confirm against a real header.

Logical column-map keys:

  Required: expense_date, amount, vendor
  Optional: currency, document_id, reference, report_number,
            receipt_url, receipt_name

Field mapping into `Receipt`:

  expense_date  -> detected_date
  amount        -> detected_total
  vendor        -> detected_vendor        (the merchant column)
  currency      -> detected_currency      (else `default_currency`)
  reference     -> detected_reference
  report_number -> report_number          (8.3 cross-ref, 8.5 export)
  document_id   -> document_id             (else synthesized, see below)
  receipt_url   -> receipt_url             ┐ the receipt-URL design fork
  receipt_name  -> receipt_name            ┘ (BLUEPRINT 8.1): carry the
                                             URL if the export has one,
                                             else the filename so 8.4
                                             hosting resolves it later.

`document_id` must be unique per file (the matcher keys receipts by it).
When the export carries a stable per-expense id, map it; otherwise this
adapter synthesizes `"<report_number-or-EXP>:<row>"` from the report
number and the 1-indexed row, which is stable for a given file.

`legal_entity_id` is taken from the run config, not the export — one
legal entity per run, same as the slice-1 receipts CSV. Categorization
runs downstream from `line_items`; a Zoho Expense line is one receipt
with a total and no itemization, so `line_items` is empty here and the
Tier-2 vendor-fallback categorization path triggers (BLUEPRINT LD-2).
Zoho's own GL category is intentionally NOT carried in 8.1 (the tool
re-derives the category); that is a later extension, not this slice.

Error model mirrors the statement parsers (`_common.py`): header-level
problems (missing required map key, a mapped source column absent from
the CSV, no header) raise `StatementParseError`; row-level problems
(bad date, bad amount, duplicate id) land in the tolerant issues list
and parsing continues. Empty rows are skipped.
"""
from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from ..matching.types import Receipt
from ._common import (
    ParseIssue,
    StatementParseError,
    parse_amount,
    parse_date,
)

__all__ = [
    "EXPENSE_REQUIRED_KEYS",
    "EXPENSE_OPTIONAL_KEYS",
    "parse_expense_csv",
    "parse_expense_csv_tolerant",
]


EXPENSE_REQUIRED_KEYS: tuple[str, ...] = ("expense_date", "amount", "vendor")
EXPENSE_OPTIONAL_KEYS: tuple[str, ...] = (
    "currency",
    "document_id",
    "reference",
    "report_number",
    "receipt_url",
    "receipt_name",
)


def parse_expense_csv(
    path: str | Path,
    legal_entity_id: str,
    column_map: Mapping[str, str],
    default_currency: str | None = None,
) -> list[Receipt]:
    """Strict mode: raise on the first row-level error.

    Backward-compatible wrapper around the tolerant variant; the CLI
    uses the tolerant form and surfaces issues on the Errors sheet.
    """
    receipts, issues = parse_expense_csv_tolerant(
        path, legal_entity_id, column_map, default_currency
    )
    if issues:
        raise issues[0].to_error()
    return receipts


def parse_expense_csv_tolerant(
    path: str | Path,
    legal_entity_id: str,
    column_map: Mapping[str, str],
    default_currency: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Tolerant mode (ANNEALING B1): collect row-level errors, continue.

    Header-level errors (missing required map key, a mapped source
    column absent, no header) still raise `StatementParseError`.
    Row-level errors land in the returned issues list with the source
    file basename + 1-indexed line number; surrounding rows continue.
    """
    _validate_expense_map(column_map)

    path = Path(path)
    file_name = path.name
    receipts: list[Receipt] = []
    issues: list[ParseIssue] = []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise StatementParseError("Expense CSV has no header row")

        fieldnames = list(reader.fieldnames)
        for logical_key, source_col in column_map.items():
            if source_col not in fieldnames:
                raise StatementParseError(
                    f"Expense CSV missing column {source_col!r} "
                    f"(mapped from logical key {logical_key!r}). "
                    f"Available columns: {fieldnames}"
                )

        seen_ids: dict[str, int] = {}

        for row_index, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # blank row, common at EOF

            try:
                detected_date = parse_date(row[column_map["expense_date"]] or "")
                detected_total = parse_amount(row[column_map["amount"]] or "")
                detected_vendor = (
                    (row[column_map["vendor"]] or "").strip() or None
                )

                detected_currency = default_currency
                raw_cur = _opt(row, column_map, "currency")
                if raw_cur:
                    detected_currency = raw_cur.upper()

                detected_reference = _opt(row, column_map, "reference") or None
                report_number = _opt(row, column_map, "report_number") or None
                receipt_url = _opt(row, column_map, "receipt_url") or None
                receipt_name = _opt(row, column_map, "receipt_name") or None

                document_id = _opt(row, column_map, "document_id")
                if not document_id:
                    document_id = f"{report_number or 'EXP'}:{row_index}"
                if document_id in seen_ids:
                    raise ValueError(
                        f"duplicate document_id {document_id!r} "
                        f"(also on row {seen_ids[document_id]})"
                    )
            except (KeyError, ValueError) as exc:
                issues.append(
                    ParseIssue(
                        file_name=file_name,
                        line_number=row_index,
                        message=str(exc),
                    )
                )
                continue

            # Register the id only after every field parsed cleanly — a
            # row that fails late must not preempt a clean later dup.
            seen_ids[document_id] = row_index

            receipts.append(
                Receipt(
                    document_id=document_id,
                    legal_entity_id=legal_entity_id,
                    detected_date=detected_date,
                    detected_total=detected_total,
                    detected_currency=detected_currency,
                    detected_vendor=detected_vendor,
                    detected_reference=detected_reference,
                    report_number=report_number,
                    receipt_url=receipt_url,
                    receipt_name=receipt_name,
                )
            )

    return receipts, issues


def _validate_expense_map(column_map: Mapping[str, str]) -> None:
    """Raise `StatementParseError` if required column-map keys are missing."""
    missing = [k for k in EXPENSE_REQUIRED_KEYS if k not in column_map]
    if missing:
        raise StatementParseError(
            f"column_map missing required keys: {', '.join(missing)}"
        )


def _opt(row: Mapping[str, str], column_map: Mapping[str, str], key: str) -> str:
    """Read an optional mapped column's trimmed value, or '' when the
    logical key is not mapped."""
    if key not in column_map:
        return ""
    return (row.get(column_map[key]) or "").strip()
