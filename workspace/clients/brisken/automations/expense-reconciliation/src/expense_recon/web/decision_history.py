"""Item 104: a decision history, one line per change that actually moved.

Every verdict in this tool is an upsert: `set_decision` replaces the row's
status and chosen receipt in place, `set_disposition` replaces the §17
verdict, the category routes replace the override, `set_duplicate_resolution`
replaces the ruling. The previous value is gone the moment the next one
lands, so "who confirmed this, and when" has no answer, and a bulk action or
a re-match that moved forty rows leaves nothing behind that says so.

This module is the pure half: what a history line IS, whether a write
changed anything worth a line, how a line reads in English, and what putting
one back would mean. It touches no database and no request. The store owns
the append-only table; `app.py` owns the wiring and the two routes.

Three rules decide the shape:

1. **Only real changes.** A write whose value equals what was already there
   makes no line. A re-match writes every charge on the month; recording all
   of them would bury the four that moved under a hundred that did not.
2. **Values that must move together ride one line.** A confirm sets a
   status AND a chosen receipt together, and an undo has to put both back
   together, so they ride one line with a JSON value rather than two lines
   that can be undone apart and leave the row half-reverted. Values that are
   genuinely independent do not: reclassifying a 33-line receipt writes 33
   lines, because each line's category is its own decision and undoing one
   leaves the other 32 standing, which is right.
3. **Undo is a new line, never an erasure.** Putting a value back appends
   its own line (trigger `undo`) and stamps the original as undone. The
   ledger only ever grows, which is the whole point of having one.
"""
from __future__ import annotations

import json

# The kinds of change that get a line. Each names one write path in app.py.
FIELD_DECISION = "decision"                    # status + chosen receipt
FIELD_DISPOSITION = "disposition"              # §17 business/private/...
FIELD_CHARGE_CATEGORY = "charge_category"      # item 109, charge with no receipt
FIELD_RECEIPT_CATEGORY = "receipt_category"    # a line on a receipt
FIELD_DUPLICATE = "duplicate"                  # a duplicate-group ruling

FIELDS = frozenset({
    FIELD_DECISION,
    FIELD_DISPOSITION,
    FIELD_CHARGE_CATEGORY,
    FIELD_RECEIPT_CATEGORY,
    FIELD_DUPLICATE,
})

# What caused the write. `click` is one row acted on by hand; `bulk` is one
# of the confirm-all / reject-all family; `rematch` and `tool` are the
# machine's own writes; `undo` is this module putting a value back.
TRIGGER_CLICK = "click"
TRIGGER_BULK = "bulk"
TRIGGER_REMATCH = "rematch"
TRIGGER_TOOL = "tool"
TRIGGER_UNDO = "undo"

TRIGGERS = frozenset({
    TRIGGER_CLICK, TRIGGER_BULK, TRIGGER_REMATCH, TRIGGER_TOOL, TRIGGER_UNDO,
})

# Which side of the month the row lives on.
ROW_CHARGE = "charge"
ROW_RECEIPT = "receipt"
ROW_GROUP = "group"
ROW_KINDS = frozenset({ROW_CHARGE, ROW_RECEIPT, ROW_GROUP})

# Which fields the one-click undo is offered on. Four of the five are plain
# upserts whose old value is a value the same route already accepts, so
# writing it back leaves the month exactly as it was.
#
# FIELD_DUPLICATE is deliberately NOT here. A duplicate ruling decides what
# the matcher's pool holds, so the resolve route re-matches the month after
# writing it (item 56); an undo that wrote the old ruling back without that
# re-match would leave a month whose ruling says one thing and whose pairs
# still reflect the other. The change is still RECORDED -- the ledger is the
# point -- and it is reversed by making the opposite ruling on the duplicate
# group, which re-matches properly.
UNDOABLE_FIELDS = frozenset({
    FIELD_DECISION,
    FIELD_DISPOSITION,
    FIELD_CHARGE_CATEGORY,
    FIELD_RECEIPT_CATEGORY,
})

# The label a session carries when nobody named themselves: the legacy
# shared code, and the gate-off local case. Mirrors auth.DEFAULT_LABEL;
# duplicated rather than imported so this module stays free of the web layer.
UNNAMED = "operator"


def encode(value) -> str | None:
    """A history value as stored text. `None` means "there was nothing"."""
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def decode(raw: str | None):
    """The stored text back as a value; corrupt text reads as absent rather
    than 500ing a page whose whole job is to show what happened."""
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def decision_value(status: str | None, chosen_document_id: str | None) -> dict | None:
    """The decision half of a row as one comparable value.

    A row nobody has ruled on is `None`, not `{"status": None}`: "no verdict"
    and "a verdict of nothing" have to compare equal to each other and
    different from a real status, or the first write on every charge would
    record a line from nothing to pending.
    """
    if status is None:
        return None
    return {"status": status, "chosen_document_id": chosen_document_id or None}


def changed(old, new) -> bool:
    """Whether this write moved the value at all.

    Compared on the decoded values, so `{"a": 1, "b": 2}` and
    `{"b": 2, "a": 1}` are the same change (they are the same verdict) even
    though their JSON text differs.
    """
    return old != new


def make_entry(
    *,
    run_id: str,
    row_key: str,
    row_kind: str,
    field: str,
    old,
    new,
    who: str | None,
    at: str,
    trigger: str,
    detail: dict | None = None,
) -> dict | None:
    """One history line, or `None` when nothing moved.

    Returning `None` rather than raising is deliberate: every caller is a
    write path that has already succeeded, and a history line is never worth
    failing a verdict the reviewer already made.
    """
    if field not in FIELDS:
        raise ValueError(f"unknown history field {field!r}; expected {sorted(FIELDS)}")
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown history trigger {trigger!r}; expected {sorted(TRIGGERS)}")
    if row_kind not in ROW_KINDS:
        raise ValueError(f"unknown history row kind {row_kind!r}; expected {sorted(ROW_KINDS)}")
    if not changed(old, new):
        return None
    return {
        "run_id": run_id,
        "row_key": str(row_key),
        "row_kind": row_kind,
        "field": field,
        "old_value": encode(old),
        "new_value": encode(new),
        "who": (who or UNNAMED),
        "at": at,
        "trigger": trigger,
        "detail": encode(detail) if detail else None,
    }


def _receipt_name(document_id: str | None) -> str:
    """A receipt id as a reader sees it: the stored name without the
    numeric prefix the pipeline puts on every file."""
    if not document_id:
        return ""
    name = str(document_id)
    head, sep, tail = name.partition("__")
    return tail if sep and head.isdigit() else name


def _describe_decision(old: dict | None, new: dict | None) -> str:
    old_status = (old or {}).get("status")
    new_status = (new or {}).get("status")
    old_doc = (old or {}).get("chosen_document_id")
    new_doc = (new or {}).get("chosen_document_id")
    if old_status != new_status:
        head = f"{old_status or 'no verdict'} to {new_status or 'no verdict'}"
    else:
        head = str(new_status or "no verdict")
    if old_doc != new_doc:
        if new_doc and old_doc:
            return f"{head}, receipt changed from {_receipt_name(old_doc)} to {_receipt_name(new_doc)}"
        if new_doc:
            return f"{head}, receipt {_receipt_name(new_doc)}"
        return f"{head}, receipt removed"
    return head


def _describe_plain(label: str, old, new) -> str:
    def show(value):
        if value is None or value == "":
            return "none"
        if isinstance(value, dict):
            # The key is dropped for `category` because the label already
            # said it: without this the line read "category category
            # Professional Services to none".
            parts = [
                str(v) if k == "category" else f"{k} {v}"
                for k, v in sorted(value.items()) if v not in (None, "")
            ]
            return ", ".join(parts) or "none"
        return str(value)
    return f"{label} {show(old)} to {show(new)}"


def describe(entry: dict) -> str:
    """The line in English, for a reader scanning what happened.

    English on purpose: the SPA gets the structured `old` / `new` beside
    this and renders its own Portuguese from those, the same division every
    other reason code in this app uses.
    """
    field = entry.get("field")
    old = decode(entry.get("old_value"))
    new = decode(entry.get("new_value"))
    if field == FIELD_DECISION:
        return _describe_decision(old, new)
    if field == FIELD_DISPOSITION:
        return _describe_plain("disposition", old, new)
    if field == FIELD_CHARGE_CATEGORY:
        return _describe_plain("category", old, new)
    if field == FIELD_RECEIPT_CATEGORY:
        return _describe_plain("category", old, new)
    if field == FIELD_DUPLICATE:
        return _describe_plain("duplicate ruling", old, new)
    return _describe_plain(str(field), old, new)


def view_entry(row: dict) -> dict:
    """One stored row as the API serves it: the structured values decoded,
    the English summary computed, and whether putting it back is offered."""
    old = decode(row.get("old_value"))
    new = decode(row.get("new_value"))
    undone_at = row.get("undone_at") or None
    out = {
        "id": row["id"],
        "row_key": row["row_key"],
        "row_kind": row["row_kind"],
        "field": row["field"],
        "old": old,
        "new": new,
        "who": row.get("who") or UNNAMED,
        "at": row["at"],
        "trigger": row["trigger"],
        "summary": describe(row),
        "undoable": undoable(row),
    }
    detail = decode(row.get("detail"))
    if detail:
        out["detail"] = detail
    if undone_at:
        out["undone_at"] = undone_at
        out["undone_by"] = row.get("undone_by") or UNNAMED
    return out


def undoable(entry_row: dict) -> bool:
    """Whether putting this line back is offered at all.

    Three reasons it is not. The field is one the undo does not serve (a
    duplicate ruling). The line has already been put back. Or it is the FIRST
    disposition on a row: `set_disposition` takes only a real verdict, there
    is no "no disposition" to write, so the button would fail every single
    time it was pressed. Offering a control that cannot work is worse than
    not offering it, because the reader tries it and learns the ledger lies.
    """
    if entry_row["field"] not in UNDOABLE_FIELDS:
        return False
    if entry_row.get("undone_at"):
        return False
    if entry_row["field"] == FIELD_DISPOSITION:
        return decode(entry_row.get("old_value")) is not None
    return True


def undo_conflict(entry_row: dict, current) -> str | None:
    """Why this line cannot be put back, or `None` when it can.

    The last check is the one that matters. A history line records a move
    from A to B; putting it back means writing A. If something has happened
    since and the row now holds C, writing A would silently throw that later
    change away, and the reader who clicked undo on a line from Tuesday
    would have reverted Thursday's work without being told. So an undo is
    refused unless the row still holds exactly what this line left there.
    """
    if entry_row.get("undone_at"):
        return "history_already_undone"
    if not undoable(entry_row):
        return "history_not_undoable"
    if changed(decode(entry_row.get("new_value")), current):
        return "history_superseded"
    return None
