"""Where a charge came from: which statement upload printed it, and where.

Note item T3 (2026-09-18), "the receipt-to-line link survives as a record".
Item 150 gave the UPLOAD an identity (`statements[].statement_id`, the
sha256 of its bytes). This module is the other half: which upload printed
each CHARGE, so a booked expense can be traced back to the line on the
statement it settles, and a stored verdict still names that line after the
month has been re-read.

It lives in its own module, not in `service.py`, because `store.py` needs
the same answer when it stamps a decision and must not import the service
layer (the service imports the store). The snapshot key literals are
therefore defined here; `service.py` keeps its own `STATEMENTS_KEY` /
`STATEMENT_ANCHORS_KEY` for its own reads, and `STATEMENT_ORIGINS_KEY` has
its single home here.

Two records, deliberately kept apart:

* `statement_anchors` (item 2a / T2) is the WRITEBACK's map: id -> sheet
  row, per upload, and EMPTY for a PDF statement, which has no tabular row.
  Its emptiness is load-bearing there and must not be given a meaning.
* `statement_origins` (this module) records every charge an upload printed,
  workbook and PDF alike, with wherever it was printed: `{"row": n}` for a
  workbook line, `{"page": n}` for a PDF one, `{}` when the parser recorded
  neither. An id present with an empty location still answers "this upload
  printed this charge", which is what the anchors cannot say for a PDF.

A month recorded before `statement_origins` existed (every live month on
2026-09-18) has no entry here, so `origins_from_snapshot` falls back to the
anchors: a workbook charge still resolves to its upload and its sheet row
today, and gains its `statement_id` at the month's next re-read, exactly as
item 150's ids do.
"""

from __future__ import annotations

# The three snapshot keys this module reads. The first two are also spelled
# in `service.py` (its own readers); the third is only ever written and read
# through here.
STATEMENTS_KEY = "statements"
STATEMENT_ANCHORS_KEY = "statement_anchors"
STATEMENT_ORIGINS_KEY = "statement_origins"


def upload_origins(transactions: list) -> dict[str, dict]:
    """One upload's charge-id to printed-location map.

    Every parsed charge gets a key, including one whose location the parser
    did not record: the KEY is the record that this upload printed it, and
    the value is the finer answer when there is one. That is the difference
    from `_upload_anchors`, which keeps only the rows it can write back to.
    """
    out: dict[str, dict] = {}
    for t in transactions:
        where: dict[str, int] = {}
        row = getattr(t, "source_row", None)
        if row is not None:
            where["row"] = int(row)
        page = getattr(t, "source_page", None)
        if page is not None:
            where["page"] = int(page)
        out[str(t.transaction_id)] = where
    return out


def origins_from_snapshot(snapshot: dict | None) -> dict[str, dict]:
    """`transaction_id -> {statement_file, statement_id, source_row,
    source_page}` for every charge the month's uploads printed.

    The FIRST upload that printed a charge wins. A charge occupies a place
    in every file that prints it (a mid-month partial and the closing cycle
    both carry it), and the question this answers is where the month got it
    from, which is the upload that put it there.

    Values are None where nothing is recorded, never invented. The caller
    turns them into parallel payload fields with `origin_fields`, which
    leaves an unknown one out rather than serialising a null.
    """
    snap = snapshot or {}
    per_upload = snap.get(STATEMENT_ORIGINS_KEY) or {}
    anchors = snap.get(STATEMENT_ANCHORS_KEY) or {}
    index: dict[str, dict] = {}
    for entry in snap.get(STATEMENTS_KEY) or []:
        if not isinstance(entry, dict):
            continue
        file = str(entry.get("file") or "")
        statement_id = str(entry.get("statement_id") or "") or None
        printed = per_upload.get(file)
        if printed is None:
            # Recorded before this key existed: the anchors are the only
            # record of which upload printed which charge, and they hold a
            # row for every charge a WORKBOOK printed. A PDF upload of that
            # vintage has an empty map and stays unresolved, which is the
            # truth about it.
            printed = {
                str(k): {"row": v} for k, v in (anchors.get(file) or {}).items()
            }
        if not isinstance(printed, dict):
            continue
        for tx_id, where in printed.items():
            key = str(tx_id)
            if key in index:
                continue
            place = where if isinstance(where, dict) else {}
            index[key] = {
                "statement_file": file,
                "statement_id": statement_id,
                "source_row": _as_int(place.get("row")),
                "source_page": _as_int(place.get("page")),
            }
    return index


def origin_fields(origin: dict | None) -> dict:
    """The parallel payload fields for one charge's origin.

    Absent, never null: a reader tells "not recorded" from "recorded as
    nothing", which is the same rule `statement_id` itself follows. A month
    whose uploads predate this record therefore renders byte-identically to
    before the fields existed.
    """
    if not origin:
        return {}
    out: dict = {}
    if origin.get("statement_file"):
        out["statement_file"] = origin["statement_file"]
    if origin.get("statement_id"):
        out["statement_id"] = origin["statement_id"]
    if origin.get("source_row") is not None:
        out["source_row"] = int(origin["source_row"])
    if origin.get("source_page") is not None:
        out["source_page"] = int(origin["source_page"])
    return out


def statement_id_of(origin: dict | None) -> str | None:
    """The upload id a charge's origin names, or None when unrecorded."""
    return (origin or {}).get("statement_id") or None


def _as_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
