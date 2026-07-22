"""Shared helpers for statement parsers (CSV, Excel, ...).

Lifted from `statement_csv.py` when the Excel sibling parser landed;
both parsers share the same column-map shape, the same error type,
and the same date/amount tolerance rules (v2 spec §7.1).

Row-number convention is identical across formats: header row is
line 1, the first data row is line 2. `StatementParseError.line_number`
points the caller at the offending row regardless of file format.

Two parse modes per ANNEALING B1:

* **Strict** — `parse_X(path, ...)` raises `StatementParseError` on
  the first bad row. Backward-compatible with the slice-1 behavior;
  used by tests that pin parser semantics.
* **Tolerant** — `parse_X_tolerant(path, ...)` returns
  `tuple[list[Obj], list[ParseIssue]]`. Header-level errors (missing
  column, no header) still raise (nothing to recover). Row-level
  errors (bad date, bad amount, dup id) land in the issues list and
  the parser continues. The CLI uses tolerant mode and surfaces
  issues on the Errors sheet — first real Brisken month is expected
  to have at least one malformed row, and stack-tracing on row 5 of
  500 would lose all the good data.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


REQUIRED_KEYS: tuple[str, ...] = ("transaction_date", "amount", "vendor")
# L5 (2026-07-15): original_amount / original_currency / fx_rate let a
# tabular statement carry per-charge foreign-currency detail (BRL on the
# USD card), the same fields the Chase PDF parser populates. The matcher
# already consumes them (deterministic.py FX-detail path).
# 3.15 (2026-07-20): "type" maps the export's debit/credit column (Chase
# activity CSV "Type": Sale / Payment / Return / ...) so the row's sign
# can be canonicalized per source instead of trusted blindly.
# WS3 (2026-07-21): "card" maps the per-row card column a tabular export
# prints beside every charge (Chase activity CSV "Card": 2838 / 3645 /
# 3876 / 0340) into `Transaction.card_last4`. The statement PDF has always
# carried this identity in `account_id` via its per-card cycle markers; on
# the CSV / xlsx path `account_id` names the whole account, so without this
# key a multi-card export looks like one card and card-scoped matching
# silently does nothing.
OPTIONAL_KEYS: tuple[str, ...] = (
    "posting_date",
    "transaction_currency",
    "original_amount",
    "original_currency",
    "fx_rate",
    "type",
    "card",
)

# Type-column values that mark a CREDIT (money back to the card): the
# canonical sign is negative and the transaction is partitioned into the
# refunds bucket, never pair-matched to a purchase receipt (LD-5 A5).
# Anything else (Sale, Fee, an unknown label) is treated as a purchase;
# an ambiguous label like "Adjustment" deliberately stays a purchase so
# it surfaces for review rather than silently landing in refunds.
CREDIT_TYPE_VALUES: frozenset[str] = frozenset(
    {"payment", "return", "refund", "credit", "reversal"}
)


def is_credit_type(type_value: str) -> bool:
    """True when a statement Type-column value marks a credit/refund."""
    return type_value.strip().lower() in CREDIT_TYPE_VALUES


def infer_sign_flip(amounts: "list[Decimal]") -> bool:
    """True when a statement's sign convention is inverted (purchases
    printed negative), detected by strict majority of nonzero amounts
    being negative. A normal month is dominated by purchases, so a
    majority-negative export (the Chase activity CSV: Type=Sale prints
    -10.32) is printing debits as negatives and every sign must flip to
    reach the canonical convention (purchase = positive, credit =
    negative). At least 3 negatives are required before inferring: a
    tiny export that happens to hold only a refund or two is kept
    verbatim rather than wrongly flipped. Used only when no Type column
    is mapped; the caller emits a warning ParseIssue so the inference
    is never silent."""
    nonzero = [a for a in amounts if a != 0]
    if not nonzero:
        return False
    negatives = sum(1 for a in nonzero if a < 0)
    return negatives >= 3 and negatives * 2 > len(nonzero)


class StatementParseError(ValueError):
    """Raised when a statement file cannot be parsed.

    `line_number` is the 1-indexed row number (the header row is
    line 1; the first data row is line 2). Use it to point the user
    at the exact problematic row.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        super().__init__(message)
        self.line_number = line_number


@dataclass(frozen=True)
class ParseIssue:
    """One row-level parse failure collected in tolerant mode.

    `file_name` is the source-file basename (e.g., "receipts.csv");
    the Errors sheet shows this so the user knows which file the
    issue came from when a run ingests multiple files. `line_number`
    follows the same convention as `StatementParseError.line_number`
    (header is row 1, data starts at row 2).

    `severity`: "error" (a row failed to parse) or "warning" (advisory,
    e.g. a mapped column is formula-derived, L6). Strict mode raises
    only on errors; warnings never abort a run.
    """

    file_name: str
    line_number: int
    message: str
    severity: str = "error"

    def to_error(self) -> StatementParseError:
        return StatementParseError(
            f"{self.file_name} row {self.line_number}: {self.message}",
            line_number=self.line_number,
        )


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
