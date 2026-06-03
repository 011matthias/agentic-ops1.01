"""Receipts CSV ingest — slice-1 bridge.

The matcher needs `Receipt` objects with already-extracted fields
(date, total, currency, vendor). The real source of those fields is
the OCR / Claude-vision layer that runs over receipt images and PDFs
(v2 spec §24). That layer lands in slice 2, when Anthropic API access
is provisioned.

For slice 1, the tool accepts a CSV of already-extracted receipt rows.
This lets us run the full pipeline end-to-end against Chris's data the
moment OCR lands — the receipt-source swap is a single function call
in `cli.py`, nothing else changes.

CSV columns (header row, exact names):

  Required: document_id, detected_date, detected_total, detected_vendor
  Optional: detected_currency, detected_reference, line_items

`line_items` is a JSON array string per row (slice-1 carrier for the
LD-2 line-item data). Each item: `{"description": str, "line_total":
str|number, "quantity"?: number, "unit_price"?: number}`. Empty list,
missing column, or empty string = receipt has no itemization (the
Tier-2 vendor-fallback path will trigger in slice 4 categorization).

`legal_entity_id` is taken from the run config, not the CSV — same
legal entity per run. `ocr_text` is omitted; not used by the
deterministic matcher.
"""
from __future__ import annotations

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..matching.types import LineItem, Receipt
from ._common import ParseIssue, StatementParseError, parse_amount, parse_date


REQUIRED_RECEIPT_COLUMNS: tuple[str, ...] = (
    "document_id",
    "detected_date",
    "detected_total",
    "detected_vendor",
)


def parse_receipts_csv(
    path: str | Path,
    legal_entity_id: str,
    default_currency: str | None = None,
) -> list[Receipt]:
    """Strict mode: raise on the first row-level error.

    See module docstring for header-vs-row error distinction.
    """
    receipts, issues = parse_receipts_csv_tolerant(
        path, legal_entity_id, default_currency
    )
    if issues:
        raise issues[0].to_error()
    return receipts


def parse_receipts_csv_tolerant(
    path: str | Path,
    legal_entity_id: str,
    default_currency: str | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Tolerant mode (ANNEALING B1): collect row-level errors, continue.

    Header-level errors (no header, missing required column) still
    raise `StatementParseError`. Row-level errors land in the
    returned issues list with the source file basename + 1-indexed
    line number; the surrounding rows continue parsing.
    """
    path = Path(path)
    file_name = path.name
    receipts: list[Receipt] = []
    issues: list[ParseIssue] = []

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise StatementParseError("Receipts CSV has no header row")

        fieldnames = list(reader.fieldnames)
        missing = [c for c in REQUIRED_RECEIPT_COLUMNS if c not in fieldnames]
        if missing:
            raise StatementParseError(
                f"Receipts CSV missing required columns: {', '.join(missing)}. "
                f"Available: {fieldnames}"
            )

        seen_ids: dict[str, int] = {}

        for row_index, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # blank row

            try:
                document_id = (row["document_id"] or "").strip()
                if not document_id:
                    raise ValueError("document_id is required")
                if document_id in seen_ids:
                    raise ValueError(
                        f"duplicate document_id {document_id!r} "
                        f"(also on row {seen_ids[document_id]})"
                    )

                detected_date = parse_date(row["detected_date"] or "")
                detected_total = parse_amount(row["detected_total"] or "")
                detected_vendor = (row["detected_vendor"] or "").strip() or None

                detected_currency = default_currency
                raw_cur = (row.get("detected_currency") or "").strip()
                if raw_cur:
                    detected_currency = raw_cur.upper()

                detected_reference = (
                    (row.get("detected_reference") or "").strip() or None
                )

                line_items = _parse_line_items(row.get("line_items") or "")
            except (KeyError, ValueError) as exc:
                issues.append(
                    ParseIssue(
                        file_name=file_name,
                        line_number=row_index,
                        message=str(exc),
                    )
                )
                continue

            # Only register the id AFTER all field parsing succeeds — a
            # row that fails on a later field should not preempt a clean
            # duplicate of the same id later in the file.
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
                    line_items=line_items,
                )
            )

    return receipts, issues


def _parse_line_items(raw: str) -> tuple[LineItem, ...]:
    """Parse the JSON-in-CSV line_items column into LineItem objects.

    Empty / missing → empty tuple (no itemization; vendor-fallback path
    will trigger in slice 4 categorization). Malformed JSON raises
    ValueError carrying the offending text so the caller can surface
    with row number.
    """
    raw = raw.strip()
    if not raw:
        return ()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"line_items is not valid JSON: {exc.msg}") from exc

    if not isinstance(items, list):
        raise ValueError("line_items must be a JSON array")

    out: list[LineItem] = []
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"line_items[{i}] must be an object")
        if "description" not in item:
            raise ValueError(f"line_items[{i}] missing 'description'")
        if "line_total" not in item:
            raise ValueError(f"line_items[{i}] missing 'line_total'")

        try:
            line_total = Decimal(str(item["line_total"]))
        except (InvalidOperation, TypeError) as exc:
            raise ValueError(
                f"line_items[{i}].line_total not a number: {item['line_total']!r}"
            ) from exc

        quantity = _opt_decimal(item.get("quantity"), f"line_items[{i}].quantity")
        unit_price = _opt_decimal(
            item.get("unit_price"), f"line_items[{i}].unit_price"
        )

        out.append(
            LineItem(
                description=str(item["description"]).strip(),
                line_total=line_total,
                quantity=quantity,
                unit_price=unit_price,
            )
        )

    return tuple(out)


def _opt_decimal(value: object, label: str) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{label} not a number: {value!r}") from exc
