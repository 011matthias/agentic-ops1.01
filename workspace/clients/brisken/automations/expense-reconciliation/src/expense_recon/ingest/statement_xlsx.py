"""Excel statement parser — v2 spec §7.1 (sibling to `statement_csv.py`).

Reads an .xlsx statement Brisken downloads today and produces a list
of `Transaction` objects. Same interface, same `StatementParseError`
posture, same column-map shape as the CSV parser; the only behavioral
differences are the Excel-native cell type handling described below.

Cell-type handling
------------------
openpyxl returns native Python objects from cells:

* `datetime.datetime` / `datetime.date` for real date cells → used
  directly via `.date()` (no string parsing).
* `int` / `float` for numeric cells → routed through
  ``Decimal(str(value))`` so the IEEE-754 binary noise that bites
  ``Decimal(5.75)`` is avoided.
* `str` for text cells → routed through the shared `parse_date` /
  `parse_amount` helpers so the same date formats and
  ``$ / , / (50.00)`` tolerances apply as in CSV.
* `None` / empty string → empty.

Row-numbering convention matches CSV: header is row 1, first data row
is row 2. ``StatementParseError.line_number`` is consistent across
formats.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

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
    "parse_statement_xlsx",
]


def _is_cell_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _coerce_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_date(_coerce_str(value))


def _coerce_amount(value: object) -> Decimal:
    # bool is a subclass of int in Python — reject explicitly so a stray
    # TRUE/FALSE cell never becomes Decimal(1) / Decimal(0).
    if isinstance(value, bool):
        raise ValueError(f"Not a number: {value!r}")
    if isinstance(value, (int, float)):
        # Decimal(str(5.75)) == Decimal("5.75"); Decimal(5.75) doesn't.
        return Decimal(str(value))
    return parse_amount(_coerce_str(value))


def parse_statement_xlsx(
    path: str | Path,
    column_map: Mapping[str, str],
    account_id: str,
    legal_entity_id: str,
    account_card_currency: str,
    sheet_name: str | None = None,
) -> list[Transaction]:
    """Parse an Excel statement into a list of `Transaction` objects.

    Sibling to :func:`parse_statement_csv`; arguments and behavior are
    identical except for `sheet_name`.

    Parameters
    ----------
    path
        Path to the .xlsx file.
    column_map
        Logical field name -> source column header (text in row 1).
        Required keys: ``transaction_date``, ``amount``, ``vendor``.
        Optional keys: ``posting_date``, ``transaction_currency``.
    account_id, legal_entity_id, account_card_currency
        Same meaning as in :func:`parse_statement_csv`.
    sheet_name
        Worksheet to read. Default reads the active sheet (typical
        when banks export a single-sheet file).

    Returns
    -------
    list[Transaction]

    Raises
    ------
    StatementParseError
        On a missing required column-map key, an .xlsx missing a
        mapped source column, or a malformed row. Carries
        ``.line_number`` for row-specific errors.
    """
    validate_required_map(column_map)

    path = Path(path)
    wb = load_workbook(filename=path, read_only=True, data_only=True)
    try:
        ws = wb[sheet_name] if sheet_name is not None else wb.active

        rows = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows)
        except StopIteration:
            raise StatementParseError("Excel sheet has no rows") from None

        headers: list[str] = []
        for cell in header_row:
            if cell is None:
                headers.append("")
            elif isinstance(cell, str):
                headers.append(cell.strip())
            else:
                headers.append(str(cell))

        if not any(headers):
            raise StatementParseError("Excel sheet has no header row")

        header_index: dict[str, int] = {}
        for i, h in enumerate(headers):
            if h:
                # First occurrence wins on duplicate headers; same as csv.DictReader.
                header_index.setdefault(h, i)

        for logical_key, source_col in column_map.items():
            if source_col not in header_index:
                raise StatementParseError(
                    f"Excel missing column {source_col!r} "
                    f"(mapped from logical key {logical_key!r}). "
                    f"Available columns: {[h for h in headers if h]}"
                )

        transactions: list[Transaction] = []
        for row_index, row_values in enumerate(rows, start=2):
            mapped: dict[str, object] = {}
            for logical, source_col in column_map.items():
                idx = header_index[source_col]
                mapped[logical] = row_values[idx] if idx < len(row_values) else None

            if all(_is_cell_empty(v) for v in mapped.values()):
                continue  # blank row, common at EOF

            try:
                txdate = _coerce_date(mapped["transaction_date"])
                amount = _coerce_amount(mapped["amount"])
                vendor = _coerce_str(mapped["vendor"])

                posting: date | None = None
                if "posting_date" in column_map and not _is_cell_empty(
                    mapped.get("posting_date")
                ):
                    posting = _coerce_date(mapped["posting_date"])

                tx_currency = account_card_currency.upper()
                if "transaction_currency" in column_map:
                    raw_cur = _coerce_str(mapped.get("transaction_currency"))
                    if raw_cur:
                        tx_currency = raw_cur.upper()
            except (KeyError, ValueError) as exc:
                raise StatementParseError(
                    f"Row {row_index}: {exc}", line_number=row_index
                ) from exc

            raw_row = dict(
                zip(
                    [h for h in headers],
                    list(row_values) + [None] * max(0, len(headers) - len(row_values)),
                )
            )
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
                    raw_text=str(raw_row),
                )
            )
    finally:
        wb.close()

    return transactions
