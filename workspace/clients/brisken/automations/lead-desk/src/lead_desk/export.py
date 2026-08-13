"""Export the Lead Desk to CSV / XLSX.

The spreadsheet becomes a DERIVED artifact regenerated from the database, so
it is never hand-edited (that was the old drift source). Stage and status are
computed, not stored.

    lead-desk-export --data ./lead-desk-data --out lead-desk.xlsx
"""
from __future__ import annotations

import argparse
import csv
import io
import os
from pathlib import Path

from .web.service import build_board
from .web.store import ContactStore

EXPORT_COLUMNS = [
    "contact_id", "tier", "lead_type", "stage", "status", "suppressed", "suppress_reason",
    "first_name", "last_name", "company", "job_title", "email", "alt_email", "phone",
    "country", "linkedin_url", "crm_owner", "next_step", "next_step_due",
    "last_out", "last_in", "demo_date", "dirk_verdict",
    "bant_need", "bant_authority", "bant_timeline", "bant_budget",
    "source", "tier_reason", "dirk_notes",
    # Appended only, never inserted (downstream consumers key on column
    # order): the contact's campaign and the master sheet's display-only
    # status column, so the export covers the /sheet view's column set.
    "campaign", "outreach_status",
]


def _rows(store: ContactStore) -> list[dict]:
    # show_suppressed => every contact, with derived stage/status attached.
    return build_board(store, {"show_suppressed": "1"})["rows"]


def _cell(row: dict, col: str):
    v = row.get(col)
    return "" if v is None else v


def to_csv_bytes(store: ContactStore) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(EXPORT_COLUMNS)
    for r in _rows(store):
        w.writerow([_cell(r, c) for c in EXPORT_COLUMNS])
    return buf.getvalue().encode("utf-8")


def to_xlsx_bytes(store: ContactStore) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Lead Desk"
    ws.append(EXPORT_COLUMNS)
    for r in _rows(store):
        ws.append([_cell(r, c) for c in EXPORT_COLUMNS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lead-desk-export")
    p.add_argument("--data", default=os.environ.get("LEAD_DESK_DATA", "lead-desk-data"))
    p.add_argument("--out", default="lead-desk-rome-2026.xlsx")
    args = p.parse_args(argv)
    db = Path(args.data).resolve() / "lead-desk.sqlite"
    out = Path(args.out)
    with ContactStore(db) as store:
        if out.suffix.lower() == ".csv":
            out.write_bytes(to_csv_bytes(store))
        else:
            out.write_bytes(to_xlsx_bytes(store))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
