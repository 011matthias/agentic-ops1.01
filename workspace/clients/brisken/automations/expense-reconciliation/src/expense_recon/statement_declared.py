"""The period a statement upload DECLARES for itself (item 220 step 3).

A loaded statement's span used to be read only off the charges it printed
(`statements[].period_start..period_end`), so a file said nothing about the
days after its last charge or about a subcard that did not spend. Two kinds
of upload do declare their own period, and this module reads it:

* **A Chase cycle PDF** prints `Opening/Closing Date MM/DD/YY - MM/DD/YY`.
  `ingest/statement_pdf._parse_period` already read that line, but only to
  resolve the year of a MM/DD charge; the days were dropped.
* **A Chase activity export pulled from SharePoint** carries the POSTED range
  it was requested for in its name:
  `Chase9693_2026-09_posted_0906-0915_from-SharePoint.xlsx` asked for the
  charges posted 09-06 to 09-15. Its own rows run 09-04 to 09-14 (a charge
  posts a day or two after the purchase), so the name reaches a day further
  than the rows do.

A declared period is recorded on new attaches and re-reads as
`statements[].period_declared_start/period_end` (absent when the upload
declares none). An entry stored before that has no field; for a workbook the
same range is read off its `upload_name` at read time, while a stored PDF gains
it only when it is attached or re-read again (reading the file back is a
write to the month, which is Criss's).

What the declaration changes is coverage (`card_suggestion.statement_evidence`):
the span a card is covered for is the union of the printed span and the
declared one, and a family's subcards (`Card.parent`) count as covered by an
upload only when it printed one of their charges or declared its period. A
workbook that names no period and printed no charge of a subcard says nothing
about that subcard: the April 2026 activity CSV of the 2838 account carried
no 3876 charge at all and 0340 only to April 22.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

DECLARED_START = "period_declared_start"
DECLARED_END = "period_declared_end"

_CHASE_POSTED = re.compile(
    r"chase\d{4}_(\d{4})-(\d{2})_posted_(\d{2})(\d{2})-(\d{2})(\d{2})", re.IGNORECASE
)
_PDF = ".pdf"


def from_pdf_text(text: str) -> tuple[date, date] | None:
    """The Opening/Closing Date line of a Chase statement, as two dates, or
    None when the line is absent or does not read as a forward range."""
    from .ingest.statement_pdf import _PERIOD

    m = _PERIOD.search(text or "")
    if not m:
        return None
    m1, d1, y1, m2, d2, y2 = (int(g) for g in m.groups())
    try:
        start, end = date(2000 + y1, m1, d1), date(2000 + y2, m2, d2)
    except ValueError:
        return None
    return (start, end) if start <= end else None


def from_upload_name(name: str) -> tuple[date, date] | None:
    """The posted range a SharePoint-pulled Chase export names, or None.

    `ChaseNNNN_YYYY-MM_posted_MMDD-MMDD`: the year is the file's; a range
    that crosses New Year (`2026-12_posted_1215-0105`) ends in the next year,
    and one filed under January that starts in December
    (`2027-01_posted_1230-0105`) starts in the previous one."""
    m = _CHASE_POSTED.search(Path(str(name or "")).name)
    if not m:
        return None
    year, file_month, sm, sd, em, ed = (int(g) for g in m.groups())
    try:
        start, end = date(year, sm, sd), date(year, em, ed)
    except ValueError:
        return None
    if end < start:
        try:
            if sm > file_month:
                start = start.replace(year=year - 1)
            else:
                end = end.replace(year=year + 1)
        except ValueError:
            return None
    return (start, end) if start <= end else None


def for_upload(path: Path, upload_name: str) -> tuple[date, date] | None:
    """The declared period of one stored upload: a PDF's printed
    Opening/Closing Date, a workbook's posted range from the name the
    operator sent (or the stored name). None when it declares none or the
    PDF cannot be read."""
    path = Path(path)
    if path.suffix.lower() == _PDF:
        from .ingest.statement_pdf import _extract_pages

        try:
            return from_pdf_text("\n".join(_extract_pages(path)))
        except Exception:  # noqa: BLE001 - an unreadable file declares nothing
            return None
    return from_upload_name(upload_name) or from_upload_name(path.name)


def entry_fields(declared: tuple[date, date] | None) -> dict:
    """The `statements[]` keys for a declared period, {} when there is none
    (absent, never null)."""
    if declared is None:
        return {}
    return {DECLARED_START: declared[0].isoformat(), DECLARED_END: declared[1].isoformat()}


def of_entry(entry: dict) -> tuple[date, date] | None:
    """The declared period of one `statements[]` entry: the recorded fields
    when present, else (a workbook stored before they existed) its posted
    range read off `upload_name` / `file`. A PDF with no recorded fields
    declares nothing here."""
    try:
        a = date.fromisoformat(str(entry.get(DECLARED_START) or ""))
        b = date.fromisoformat(str(entry.get(DECLARED_END) or ""))
        if a <= b:
            return a, b
    except ValueError:
        pass
    names = [str(entry.get("upload_name") or ""), str(entry.get("file") or "")]
    if any(Path(n).suffix.lower() == _PDF for n in names if n):
        return None
    for name in names:
        found = from_upload_name(name)
        if found is not None:
            return found
    return None
