"""Shared helpers for statement parsers (CSV, Excel, ...).

Lifted from `statement_csv.py` when the Excel sibling parser landed;
both parsers share the same column-map shape, the same error type,
and the same date/amount tolerance rules (v2 spec §7.1).

Row-number convention is identical across formats: header row is
line 1, the first data row is line 2. `StatementParseError.line_number`
points the caller at the offending row regardless of file format.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


REQUIRED_KEYS: tuple[str, ...] = ("transaction_date", "amount", "vendor")
OPTIONAL_KEYS: tuple[str, ...] = ("posting_date", "transaction_currency")


class StatementParseError(ValueError):
    """Raised when a statement file cannot be parsed.

    `line_number` is the 1-indexed row number (the header row is
    line 1; the first data row is line 2). Use it to point the user
    at the exact problematic row.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number


_DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")


def parse_date(s: str) -> date:
    s = s.strip()
    if not s:
        raise ValueError("empty date")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {s!r}")


def parse_amount(s: str) -> Decimal:
    """Parse an amount string. Tolerates `$`, commas, surrounding
    whitespace, and accounting-style negatives like `(50.00)`."""
    raw = s.strip()
    if not raw:
        raise ValueError("empty amount")
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative = True
        raw = raw[1:-1]
    raw = raw.replace("$", "").replace(",", "").strip()
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"Not a number: {s!r}") from exc
    return -value if negative else value


def validate_required_map(column_map: Mapping[str, str]) -> None:
    """Raise `StatementParseError` if required column-map keys are missing."""
    missing = [k for k in REQUIRED_KEYS if k not in column_map]
    if missing:
        raise StatementParseError(
            f"column_map missing required keys: {', '.join(missing)}"
        )
