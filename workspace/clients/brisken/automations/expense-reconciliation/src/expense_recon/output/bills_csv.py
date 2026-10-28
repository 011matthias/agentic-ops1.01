"""`bills.csv`: the month's bills paid by bank transfer (Build 4 / backlog
item 218, owner decisions 2026-09-25).

A bill is an expense of the month that no company card paid, so it is in
neither `expenses.csv` (the card-side Zoho Expenses import) nor the Zoho
journal. Criss books each one by hand in Zoho from this file; nothing posts
anywhere. One row per bill, in the month's order, with what the row was
decided on so a reader can check it against the document.

The rows arrive composed (`service.regenerate_bills_export`); this module
only fixes the columns and writes them, the same split as the other CSVs.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from pathlib import Path

BILL_COLUMNS = (
    "Date",
    "Supplier",
    "Invoice number",
    "Amount",
    "Currency",
    "Company",
    "How decided",
    "Evidence",
    "Document",
)


def write_bills_csv(rows: Iterable[Mapping[str, str]], out_path: Path) -> Path:
    """Write `rows` (one mapping per bill, keyed by `BILL_COLUMNS`) under the
    header. A month with no bills writes the header alone, so the download is
    never an error."""
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(BILL_COLUMNS)
        for row in rows:
            writer.writerow([str(row.get(col) or "") for col in BILL_COLUMNS])
    return out_path
