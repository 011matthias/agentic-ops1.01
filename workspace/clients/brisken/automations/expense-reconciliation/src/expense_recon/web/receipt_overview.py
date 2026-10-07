"""Every receipt the tool holds, one row each: the Receipt overview page.

Dirk, 2026-10-07: users should be able to see and filter ALL receipts in one
place, by source, file type, file name, status, subject, received date, the
date and vendor printed on the receipt and its sum. The Email intake page
listed MAILS (one row per message, the newest 100), so a receipt that came in
through an upload never appeared there, and a receipt inside a mail was a
line in an expander.

This module turns what already exists into that one list. It decides nothing
new: every verdict is read off the month page's own payload, so a receipt
reads "matched" here exactly when its month says a charge holds it.

Three inputs, all read-only:

* each expense batch's Expenses page payload (months and trips): its
  `expenses[]` are the receipts in the tool, its `set_aside[]` the files the
  tool kept but judged not to be receipts;
* the mail intake log (`intake_mail.read_log`, status-overlaid): subject,
  sender and arrival for mailed receipts, plus the mail that never became an
  expense (held, waiting for its month, parked as a duplicate, dismissed, or
  removed again after it arrived);
* when the stored receipt file was written, for uploads. No upload records
  who or when per file, so the stored file's write time is the only honest
  arrival time an upload has (`received_from: "stored_file"`).

`status` is one code per row. For a receipt in a month, in this order:

* ``duplicate``             a copy of another receipt, out of the totals
* ``private``               marked a private expense
* ``bill``                  paid by bank transfer, not by a card
* ``settled_outside``       settled outside the card
* ``matched``               a card charge holds it
* ``waiting_for_statement`` no charge yet, and the month (or the card) has no
                            statement to find one in
* ``no_charge``             the month has its statements and no charge holds it

and for a file that is not (or no longer) an expense: ``set_aside`` (the tool
judged it not a receipt), ``waiting_for_month`` (mail pooled until its month
exists), ``held`` (arrived, could not be turned into an expense), ``processing``
(being read right now), ``removed`` (became an expense and was deleted, or its
month was), ``dismissed`` (an operator dismissed the mail).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable

# The mail statuses that mean "being worked on right now".
_WORKING = frozenset({"rendering", "re_ingesting", "routing", "claiming", "received"})
_PROCESSED = frozenset({"ingested", "replayed"})

# The stored name of a mail body the intake rendered to a PDF.
BODY_FILE = "rendered-body.pdf"

STATUS_ORDER = (
    "matched", "waiting_for_statement", "no_charge", "duplicate", "private",
    "bill", "settled_outside", "set_aside", "waiting_for_month", "held",
    "processing", "removed", "dismissed",
)


@dataclass(frozen=True)
class BatchPage:
    """One expense batch as the Expenses page shows it."""

    batch_id: str
    label: str
    batch_type: str
    view: dict = field(default_factory=dict)


def file_name_of(document_id: str) -> str:
    """`0003__0021__receipt_22_p28.png` -> `receipt_22_p28.png`: every
    `NNNN__` prefix a store or a month move added, removed."""
    return re.sub(r"^(\d{4}__)+", "", str(document_id or ""))


def file_type_of(name: str) -> str:
    """A filter-friendly type: the lower-case extension (`jpeg` -> `jpg`),
    `email_body` for a mail text the intake rendered, `other` without one."""
    base = file_name_of(name)
    if base == BODY_FILE:
        return "email_body"
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", base)
    if not m:
        return "other"
    ext = m.group(1).lower()
    return "jpg" if ext == "jpeg" else ext


def _amount(total) -> float | None:
    text = str(total or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _display(value) -> str | None:
    if isinstance(value, dict):
        value = value.get("display")
    text = str(value or "").strip()
    return text or None


def _second(ts) -> str:
    """An ISO timestamp cut to the second, the key mail and provenance share."""
    return str(ts or "")[:19]


def _receipt_status(expense: dict, has_statement: bool) -> str:
    duplicate = expense.get("duplicate") or {}
    if expense.get("counts_in_total") is False or duplicate.get("is_extra"):
        return "duplicate"
    if expense.get("private"):
        return "private"
    if expense.get("payment_path") == "bill":
        return "bill"
    if expense.get("settled_outside"):
        return "settled_outside"
    if not expense.get("without_charge"):
        return "matched"
    if not has_statement or expense.get("waits_for_statements"):
        return "waiting_for_statement"
    return "no_charge"


def _category(expense: dict) -> str | None:
    accounts = [
        str(b.get("account") or "").strip()
        for b in expense.get("books_as") or []
        if isinstance(b, dict) and not b.get("unassigned")
    ]
    accounts = [a for a in dict.fromkeys(accounts) if a]
    if accounts:
        return ", ".join(accounts)
    posting = expense.get("posting_category") or {}
    if isinstance(posting, dict):
        return _display(posting.get("zoho_account")) or _display(posting.get("category"))
    return _display(expense.get("zoho_category"))


def _merge_mail(rows: Iterable[dict]) -> dict[str, dict]:
    """The log keeps one row per acceptance plus one per replay or claim;
    the overview needs one per MAIL. Later rows win on scalars (the overlay
    already carries the current status), lists are unioned in order."""
    merged: dict[str, dict] = {}
    for row in rows:
        archive = str(row.get("archive") or "")
        if not archive:
            continue
        cur = merged.setdefault(archive, {})
        for key, value in row.items():
            if key in ("documents", "files", "not_added"):
                seen = list(cur.get(key) or [])
                for item in value or []:
                    if item not in seen:
                        seen.append(item)
                cur[key] = seen
            elif value not in (None, "", [], {}) or key not in cur:
                cur[key] = value
    return merged


def build_receipt_overview(
    batches: Iterable[BatchPage],
    mail_rows: Iterable[dict],
    *,
    stored_at: Callable[[str, str], str | None] = lambda _b, _d: None,
    generated_at: str | None = None,
) -> dict:
    """The overview payload: `receipts[]` (one row per receipt or held-back
    file, newest arrival first) plus counts per status and per source."""
    batches = list(batches)
    labels = {b.batch_id: b for b in batches}
    mails = _merge_mail(mail_rows)

    # Three ways a stored document finds the mail it came in: the archive id
    # newer provenance carries, the (batch, document) pairs the log stamped
    # at ingest, and the arrival second older provenance shares with the log.
    by_doc: dict[tuple[str, str], str] = {}
    by_second: dict[str, str] = {}
    for archive, m in mails.items():
        bid = str(m.get("batch_id") or "")
        for doc in m.get("documents") or []:
            by_doc[(bid, str(doc))] = archive
        for na in m.get("not_added") or []:
            if isinstance(na, dict) and na.get("document_id"):
                by_doc[(bid, str(na["document_id"]))] = archive
        if m.get("at"):
            by_second.setdefault(_second(m["at"]), archive)

    rows: list[dict] = []
    joined_names: dict[str, set[str]] = {}
    accounted: set[tuple[str, str]] = set()

    def _mail_fields(archive: str | None) -> dict:
        m = mails.get(archive or "") or {}
        return {
            "archive": archive or None,
            "subject": _display(m.get("subject")),
            "from_address": _display(m.get("from")),
        }

    for b in batches:
        view = b.view or {}
        has_statement = bool(view.get("has_statement"))
        for e in view.get("expenses") or []:
            doc = str(e.get("document_id") or "")
            prov = e.get("submitted_by") if isinstance(e.get("submitted_by"), dict) else {}
            archive = (
                str(prov.get("archive") or "")
                or by_doc.get((b.batch_id, doc))
                or (by_second.get(_second(prov.get("received_at"))) if prov else None)
            )
            if archive and archive not in mails:
                archive = None
            if archive:
                joined_names.setdefault(archive, set()).add(file_name_of(doc))
            accounted.add((b.batch_id, doc))
            mail = mails.get(archive or "") or {}
            received = mail.get("at") or prov.get("received_at")
            received_from = "mail" if received else None
            if not received:
                received = stored_at(b.batch_id, doc)
                received_from = "stored_file" if received else None
            name = str(e.get("receipt_name") or "").strip() or file_name_of(doc)
            review = (e.get("review") or {}).get("state")
            duplicate = e.get("duplicate") or {}
            card = e.get("card") or {}
            rows.append({
                "id": f"{b.batch_id}/{doc}",
                "source": "email" if (prov or archive) else "upload",
                "status": _receipt_status(e, has_statement),
                "review": review if review in ("ready", "check", "pick") else None,
                "review_reason": (e.get("review") or {}).get("reason_code"),
                "file_name": file_name_of(name),
                "file_type": file_type_of(name if name else doc),
                "document_id": doc,
                "can_view": bool(e.get("receipt_image_available")),
                "batch_id": b.batch_id,
                "batch_label": b.label,
                "batch_type": b.batch_type,
                **_mail_fields(archive),
                "submitted_by": _display(prov.get("person")) or _display(mail.get("person")),
                "received_at": received or None,
                "received_from": received_from,
                "receipt_date": _display(e.get("date")),
                "vendor": _display(e.get("vendor")),
                "total": _display(e.get("total")),
                "amount": _amount(_display(e.get("total"))),
                "currency": _display(e.get("currency")),
                "card": _display(card.get("label")) if isinstance(card, dict) else None,
                "person": _display(e.get("person")),
                "category": _category(e),
                "reference": _display(e.get("invoice_number"))
                or _display(e.get("receipt_number"))
                or _display(e.get("reference")),
                "note": _display(e.get("operator_note") or prov.get("operator_note")),
                "duplicate_of": file_name_of(duplicate.get("of") or "") or None
                if duplicate.get("is_extra") else None,
                "pool_month": None,
                "set_aside_reason": None,
            })
        for s in view.get("set_aside") or []:
            if s.get("restored"):
                continue
            doc = str(s.get("document_id") or s.get("file") or "")
            archive = by_doc.get((b.batch_id, doc))
            if archive:
                joined_names.setdefault(archive, set()).add(file_name_of(doc))
            accounted.add((b.batch_id, doc))
            mail = mails.get(archive or "") or {}
            name = str(s.get("display") or "") or file_name_of(doc)
            received = mail.get("at") or s.get("at")
            rows.append({
                **_empty_row(),
                "id": f"{b.batch_id}/{doc}",
                "source": "email" if archive else "upload",
                "status": "set_aside",
                "file_name": file_name_of(name),
                "file_type": file_type_of(name),
                "document_id": doc,
                "can_view": bool(s.get("receipt_image_available")),
                "batch_id": b.batch_id,
                "batch_label": b.label,
                "batch_type": b.batch_type,
                **_mail_fields(archive),
                "submitted_by": _display(mail.get("person")),
                "received_at": received or None,
                "received_from": "mail" if mail.get("at") else ("stored_file" if received else None),
                "set_aside_reason": _display(s.get("reason")),
            })

    # Mail that is not, or no longer, an expense.
    for archive, m in mails.items():
        status = str(m.get("status") or "")
        bid = str(m.get("batch_id") or "")
        batch = labels.get(bid)
        docs = [str(d) for d in m.get("documents") or []]
        files = [str(f) for f in m.get("files") or [] if str(f).strip()]
        base = {
            **_empty_row(),
            **_mail_fields(archive),
            "source": "email",
            "submitted_by": _display(m.get("person")),
            "received_at": m.get("at") or None,
            "received_from": "mail" if m.get("at") else None,
            "pool_month": _display(m.get("pool_month")),
        }

        def _file_rows(status_code: str, note: str | None = None) -> None:
            names = files or [BODY_FILE]
            for i, name in enumerate(names):
                rows.append({
                    **base,
                    "id": f"mail/{archive}/{i}",
                    "status": status_code,
                    "file_name": file_name_of(name),
                    "file_type": file_type_of(name),
                    "note": note,
                    "duplicate_of": _display(m.get("duplicate_of_subject"))
                    if status_code == "duplicate" else None,
                })

        if status in _PROCESSED:
            # A document is gone when the month it was filed in no longer
            # shows it (or the month itself was deleted), unless a row joined
            # to this mail carries its file name: a month move keeps the
            # provenance, so a moved receipt is still found, under a new id.
            in_batch = batch is not None
            found = joined_names.get(archive, set())
            stray = [
                d for d in docs
                if (bid, d) not in accounted and file_name_of(d) not in found
            ]
            for d in stray:
                rows.append({
                    **base,
                    "id": f"mail/{archive}/{d}",
                    "status": "removed",
                    "file_name": file_name_of(d),
                    "file_type": file_type_of(d),
                    "document_id": d if in_batch else None,
                    "can_view": in_batch,
                    "batch_id": bid if in_batch else None,
                    "batch_label": batch.label if batch else None,
                    "batch_type": batch.batch_type if batch else None,
                })
        elif status == "pooled":
            _file_rows("waiting_for_month")
        elif status == "duplicate":
            _file_rows("duplicate")
        elif status == "dismissed":
            if not any((bid, d) in accounted for d in docs):
                _file_rows("dismissed")
        elif status.startswith("held_"):
            _file_rows("held", status)
        elif status in _WORKING:
            _file_rows("processing")
        elif status:
            _file_rows("held", status)

    rows.sort(key=lambda r: str(r.get("received_at") or ""), reverse=True)
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    return {
        "receipts": rows,
        "n_receipts": len(rows),
        "by_status": by_status,
        "by_source": by_source,
        "statuses": list(STATUS_ORDER),
        "batches": [
            {"batch_id": b.batch_id, "label": b.label, "batch_type": b.batch_type}
            for b in batches
        ],
        "generated_at": generated_at,
    }


def _empty_row() -> dict:
    """Every key a row carries, so the SPA never meets a missing one."""
    return {
        "id": "", "source": "", "status": "", "review": None,
        "review_reason": None, "file_name": "", "file_type": "other",
        "document_id": None, "can_view": False, "batch_id": None,
        "batch_label": None, "batch_type": None, "archive": None,
        "subject": None, "from_address": None, "submitted_by": None,
        "received_at": None, "received_from": None, "receipt_date": None,
        "vendor": None, "total": None, "amount": None, "currency": None,
        "card": None, "person": None, "category": None, "reference": None,
        "note": None, "duplicate_of": None, "pool_month": None,
        "set_aside_reason": None,
    }
