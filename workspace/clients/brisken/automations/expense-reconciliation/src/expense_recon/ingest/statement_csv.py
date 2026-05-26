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
from pathlib import Path

from ..matching.types import Transaction
from ._common import (
    OPTIONAL_KEYS,
    REQUIRED_KEYS,
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
]


def parse_statement_csv(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
) -> list[Transaction]:
    """Parse a CSV statement into a list of `Transaction` objects.

    Parameters
    ----------
    path
        Path to the CSV file.
    column_map
        Logical field name -> source CSV column name. Required keys:
        ``transaction_date``, ``amount``, ``vendor``. Optional keys:
        ``posting_date``, ``transaction_currency``.
    account_id
        The bank/card account identifier this statement belongs to.
    legal_entity_id
        The legal entity that owns the account (v2 spec §4.2).
    account_card_currency
        Currency of the account/card per v2 spec §20 layer 2. Used as
        the default `transaction_currency` when no per-row currency
        column is mapped.

    Returns
    -------
    list[Transaction]

    Raises
    ------
    StatementParseError
        On a missing required column-map key, a CSV missing a mapped
        source column, or a malformed row. Carries ``.line_number``
        for row-specific errors.
    """
    validate_required_map(column_map)

    path = Path(path)
    transactions: list[Transaction] = []

    # utf-8-sig handles Windows-exported CSVs that ship a BOM.
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

        # csv.DictReader starts at line 2 (after the header).
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
            except (KeyError, ValueError) as exc:
                raise StatementParseError(
                    f"Row {row_index}: {exc}", line_number=row_index
                ) from exc

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
                )
            )

    return transactions
