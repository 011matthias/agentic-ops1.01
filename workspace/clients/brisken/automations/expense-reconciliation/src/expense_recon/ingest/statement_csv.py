"""CSV statement parser — v2 spec §7.1.

Reads the CSV format Brisken downloads today and produces a list of
`Transaction` objects ready for the matching engine. Per the
2026-05-20 call (call-outcomes "C1 statements"): statements are
read as structured columns with no interpretation — this is a
tabular ingest, not a parsing problem.

Reconciliation-guarantee posture (v2 spec §25.5): malformed rows are
never silently dropped. A malformed row raises `StatementParseError`
with the offending line number so the caller can surface it to the
user. Empty rows (all fields blank) are skipped — trailing blank
lines are common in CSV exports and carry no information.

Column auto-detection is deliberately out of scope; the caller
provides a column map. Auto-detection belongs in a settings UI
(v2 spec §27 Settings screens), not in this module.

The Excel sibling lives in `statement_xlsx.py`. Shared helpers
(error type, column-map validation, date/amount parsing) are in
`_common.py`.
"""
from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..matching.types import Transaction
from ._common import (
    OPTIONAL_KEYS,
    REQUIRED_KEYS,
    ParseIssue,
    StatementParseError,
    parse_amount,
    parse_date,
    validate_required_map,
)

__all__ = [
    "OPTIONAL_KEYS",
    "REQUIRED_KEYS",
    "StatementParseError",
    "parse_statement_csv",
    "parse_statement_csv_tolerant",
]


def parse_statement_csv(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
) -> list[Transaction]:
    """Strict mode: raise on first row-level error.

    See `_common.py` module docstring for the header-vs-row error
    distinction. This wrapper exists for backward compatibility;
    new callers should use the tolerant variant.
    """
    transactions, issues = parse_statement_csv_tolerant(
        path, column_map, account_id, legal_entity_id, account_card_currency
    )
    hard = [i for i in issues if i.severity == "error"]
    if hard:
        raise hard[0].to_error()
    return transactions


def parse_statement_csv_tolerant(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
) -> tuple[list[Transaction], list[ParseIssue]]:
    """Tolerant mode (ANNEALING B1): collect row-level errors, continue.

    Header-level errors (missing required column-map key, CSV missing
    a mapped source column, no header) still raise
    `StatementParseError`. Row-level errors land in the returned
    issues list with the source file basename + 1-indexed line number.
    """
    validate_required_map(column_map)

    path = Path(path)
    file_name = path.name
    transactions: list[Transaction] = []
    issues: list[ParseIssue] = []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise StatementParseError("CSV has no header row")

        fieldnames = list(reader.fieldnames)
        for logical_key, source_col in column_map.items():
            if source_col not in fieldnames:
                raise StatementParseError(
                    f"CSV missing column {source_col!r} "
                    f"(mapped from logical key {logical_key!r}). "
                    f"Available columns: {fieldnames}"
                )

        for row_index, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # blank row, common at EOF

            try:
                txdate = parse_date(row[column_map["transaction_date"]] or "")
                amount = parse_amount(row[column_map["amount"]] or "")
                vendor = (row[column_map["vendor"]] or "").strip()

                posting: date | None = None
                if "posting_date" in column_map:
                    raw_posting = (row.get(column_map["posting_date"]) or "").strip()
                    if raw_posting:
                        posting = parse_date(raw_posting)

                tx_currency = account_card_currency.upper()
                if "transaction_currency" in column_map:
                    raw_cur = (row.get(column_map["transaction_currency"]) or "").strip()
                    if raw_cur:
                        tx_currency = raw_cur.upper()

                # L5: optional per-charge FX detail (BRL on the USD card),
                # symmetric with the xlsx sibling and the Chase PDF fields.
                original_amount: Decimal | None = None
                if "original_amount" in column_map:
                    raw_orig_amt = (row.get(column_map["original_amount"]) or "").strip()
                    if raw_orig_amt:
                        original_amount = parse_amount(raw_orig_amt)
                original_currency: str | None = None
                if "original_currency" in column_map:
                    raw_orig_cur = (row.get(column_map["original_currency"]) or "").strip()
                    if raw_orig_cur:
                        original_currency = raw_orig_cur.upper()
                fx_rate: Decimal | None = None
                if "fx_rate" in column_map:
                    raw_rate = (row.get(column_map["fx_rate"]) or "").strip()
                    if raw_rate:
                        fx_rate = parse_amount(raw_rate)
            except (KeyError, ValueError) as exc:
                issues.append(
                    ParseIssue(
                        file_name=file_name,
                        line_number=row_index,
                        message=str(exc),
                    )
                )
                continue

            transactions.append(
                Transaction(
                    transaction_id=f"{account_id}:{row_index}",
                    legal_entity_id=legal_entity_id,
                    account_id=account_id,
                    transaction_date=txdate,
                    posting_date=posting,
                    amount=amount,
                    transaction_currency=tx_currency,
                    account_card_currency=account_card_currency.upper(),
                    vendor_from_statement=vendor,
                    raw_text=str(row),
                    original_amount=original_amount,
                    original_currency=original_currency,
                    fx_rate=fx_rate,
                )
            )

    return transactions, issues
