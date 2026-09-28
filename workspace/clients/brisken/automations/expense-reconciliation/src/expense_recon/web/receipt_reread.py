"""Re-read a month's stored receipts with the reader new ones get (backlog
item 240, owner decision 2026-09-28: "Preview, then apply").

Item 239 switched receipt reading to Gemini 3.8 Flash for every document
that ARRIVES from 2026-09-28 on. The receipts already stored keep the reading
OpenAI gave them, because nothing reads a stored receipt again: a re-match
reuses the stored readings, `statements/reread` covers statements and the
inbound `re-ingest` covers held mail. `POST /api/runs/{run_id}/receipts/reread`
is the operator's way to read one month's stored receipts again, after
previewing what that changes.

Each stored file goes through the path an arrival takes (`parse_receipt_file`
with the month's own card list and reader, then the arrival's own rules:
`keep_invoice_read_as_statement`, `quarantine_correspondence`, remembered
corrections, the card gate, card entity stamping). The new reading is then
merged into the stored one field by field, and only where the item-239 A/B
says the new reader is the better witness:

- TAKEN: date, total, currency, tax, document type, the card, and the
  merchant when it names a DIFFERENT merchant (one name containing the other,
  alphanumerics only, is the same merchant written two ways; the A/B's four
  "Brisken named as the supplier" invoices are exactly the other case). A
  blank reading never blanks a stored date, total, currency, merchant or
  tax; a blank card does replace one, because the reader is told "null is
  always better than a guess" and the A/B's card wins were nulls in place of
  invented digits.
- NOT TAKEN, compared and counted only: `document_kind` (OpenAI was right 5
  to 2), `reference` / `invoice_number` / `receipt_number` (never
  adjudicated, and they are the duplicate ladder's keys: rewriting 59 of 251
  receipts' numbers unseen would regroup copies nobody checked), and the line
  items, which carry the categories (a receipt whose merchant or company
  moves is categorized again, as an arrival would be).

A reading is written where extraction readings live: the snapshot's
`extracted_receipts` baseline and its `receipts` pool, never the reviewer's
tables. Criss's field edits, category picks, set-aside restores, duplicate
rulings and match decisions are separate rows applied on top, so they stay on
top, and nothing a re-read writes is a correction a Publish could learn from.

- A pool receipt the new reader calls a statement or report page is listed
  (`reads_as_non_receipt`) and left exactly as it is: removing an expense
  from a working month is Criss's call.
- A set-aside page the new reader calls a purchase joins the month (the
  AWS and AT&T bills OpenAI set aside as statements), categorized like a
  restore and marked `restored_by: "reread"`. A page a reviewer restored is
  already in the pool; one still set aside after the re-read is untouched.

The dry run is a job too (reading a month takes minutes): it reads every
file (warming the extraction cache, which is what makes the real run read
the same answers), commits the plan to a throwaway copy of the database,
re-matches the copy, and diffs the Expenses view and the match before and
after. The real run commits the same plan to the month and re-matches it
(trigger `receipts_reread`); its result carries the readings and the same
diff read back from the month.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..batch_period import month_from_label
from ..cli import NON_RECEIPT_LABELS
from ..matching.types import Receipt
from .duplicate_reapply import duplicate_layer, layer_diff, rematch_running
from .serialize import (
    outcome_to_dict,
    receipt_from_dict,
    receipt_to_dict,
    snapshot_from_dict,
)
from .service import (
    EXTRACTED_RECEIPTS_KEY,
    GL_ENTITY_ORGS_KEY,
    MODE_EXPENSE_GENERATION,
    REMATCH_PENDING_KEY,
    ExpenseMemory,
    MerchantCategoryLookup,
    MerchantRegistry,
    RunInputError,
    _BATCH_ADD_LOCK,
    _batch_card_hints,
    _batch_cards,
    _batch_llm_client,
    _display_name,
    apply_expense_edits,
    baseline_receipts,
    categorized_counts,
    cross_month_duplicate_evidence,
    drop_unvouched_remembered_cards,
    has_statement,
    receipt_image_file,
    rematch_after_change,
    rematch_pending_mark,
    run_mode,
    set_aside_entries,
    store_cross_month_evidence,
)
from .store import JOB_DONE, JOB_ERROR, STATUS_CONFIRMED, RunStore

log = logging.getLogger(__name__)

ViewOf = Callable[[RunStore, object], dict]

TRIGGER = "receipts_reread"
SNAPSHOT_KEY = "receipts_reread"
TAKEN_FIELDS = ("date", "total", "currency", "vendor", "card_last4", "tax", "document_type")
NOT_TAKEN_FIELDS = ("document_kind", "reference", "invoice_number", "receipt_number")
# Parallel reads: Gemini answers a receipt in about 5 s, so a 100-receipt
# month read one at a time would hold the job for 8 minutes.
READ_WORKERS = 6


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Refusals ────────────────────────────────────────────────────────────


def _rereadable(snapshot: dict) -> bool:
    pool = snapshot.get("receipts") or []
    waiting = [e for e in set_aside_entries(snapshot) if not e.get("restored")]
    return bool(pool or waiting)


def reread_refusal(run) -> RunInputError | None:
    """Why this run's receipts cannot be read again, or None. Checked by the
    route and again when the job starts and when it commits."""
    if run is None:
        return RunInputError("run not found", code="run_not_found")
    if run_mode(run) != MODE_EXPENSE_GENERATION:
        return RunInputError("not an expense batch", code="not_an_expense_batch")
    if run.published:
        return RunInputError(
            "this month is published; unpublish it before reading its "
            "receipts again", code="month_published")
    if rematch_running(run):
        return RunInputError(
            "a re-match of this month is running or owed; wait for it to "
            "finish", code="rematch_running")
    if not _rereadable(run.snapshot or {}):
        return RunInputError("this month holds no receipts", code="reread_no_receipts")
    return None


def confirm_refusal(run, confirm: str) -> RunInputError | None:
    """The typed confirm: the month's label or its run id, for a dry run as
    for a real one, so a mistyped id never reads another month quietly."""
    if not confirm:
        return RunInputError(
            "confirm is required: repeat the month label (or run id) to read "
            "its receipts again", code="reread_confirm_required")
    if confirm not in {(run.label or "").strip(), run.run_id}:
        return RunInputError("confirm label mismatch", code="reread_confirm_mismatch")
    return None


def reader_of(llm_client) -> dict:
    """Which reader answers: the second reader when one is switched on for
    receipts (item 239), else the client's own models."""
    reader = getattr(llm_client, "receipt_reader", None)
    if reader is not None:
        return {"provider": "gemini", "model": getattr(reader, "model", None),
                "reads": getattr(reader, "reads", None)}
    return {"provider": "openai", "model": getattr(llm_client, "model", None),
            "vision_model": getattr(llm_client, "vision_model", None)}


# ── Field comparison ────────────────────────────────────────────────────


def _alnum(value) -> str:
    return re.sub(r"[^0-9a-z]", "", str(value or "").casefold())


def same_merchant(a: Receipt, b: Receipt) -> bool:
    """One merchant written two ways ("SendGrid" / "SendGrid Inc.",
    "Caspari" / "Restaurant Caspari"): some name of one contains some name of
    the other, alphanumerics only. A side with no name at all is a different
    answer, so a reading can fill a merchant the stored one lacked."""
    names_a = {n for n in (_alnum(a.detected_vendor), _alnum(a.vendor_clean)) if n}
    names_b = {n for n in (_alnum(b.detected_vendor), _alnum(b.vendor_clean)) if n}
    if not names_a or not names_b:
        return not names_a and not names_b
    return any(x in y or y in x for x in names_a for y in names_b)


_CARD_RE = re.compile(r"\.\.\.(\d{4})$")


def card_digits(payment_mode: str | None) -> str | None:
    """The confirmed card the reading picked: `_payment_mode` writes it as a
    trailing `...NNNN`. A free-text hint with no confirmed pick is None."""
    m = _CARD_RE.search((payment_mode or "").strip())
    return m.group(1) if m else None


def _show(value) -> str | None:
    if value is None:
        return None
    return str(value)


def _vendor_shown(r: Receipt) -> str | None:
    return r.detected_vendor or r.vendor_clean


def merge_reading(
    stored: Receipt, new: Receipt, *, label_year: int | None = None,
    held: list | None = None,
) -> tuple[Receipt, dict, bool]:
    """(merged receipt, {field: {before, after}}, recategorize?).

    `stored` is the extraction baseline (the reading before any reviewer
    edit), `new` the arrival-shaped re-read. Only TAKEN_FIELDS move; every
    other field is the stored one. A new date in a year that is neither the
    stored reading's nor the batch's is not taken (April's San Paolo slip
    prints 21/04/2026 and was read as 2024); it is appended to `held`."""
    kw: dict = {}
    changes: dict[str, dict] = {}

    def moved(name: str, before, after) -> None:
        changes[name] = {"before": _show(before), "after": _show(after)}

    years = {y for y in (label_year, stored.detected_date and stored.detected_date.year) if y}
    if (new.detected_date is not None and new.detected_date != stored.detected_date
            and years and new.detected_date.year not in years):
        if held is not None:
            held.append({"field": "date", "why": "other_year",
                         "before": _show(stored.detected_date and stored.detected_date.isoformat()),
                         "after": new.detected_date.isoformat()})
    elif new.detected_date is not None and new.detected_date != stored.detected_date:
        kw["detected_date"] = new.detected_date
        moved("date", stored.detected_date and stored.detected_date.isoformat(),
              new.detected_date.isoformat())
    if new.detected_total is not None and new.detected_total != stored.detected_total:
        kw["detected_total"] = new.detected_total
        moved("total", stored.detected_total, new.detected_total)
    new_ccy = (new.detected_currency or "").strip().upper()
    if new_ccy and new_ccy != (stored.detected_currency or "").strip().upper():
        kw["detected_currency"] = new_ccy
        moved("currency", stored.detected_currency, new_ccy)
    vendor_moved = bool(new.detected_vendor or new.vendor_clean) and not same_merchant(stored, new)
    if vendor_moved:
        kw.update(
            detected_vendor=new.detected_vendor,
            vendor_clean=new.vendor_clean,
            vendor_source=new.vendor_source,
            # The registry names the merchant again when it is categorized.
            canonical_vendor=None,
            # A remembered card is keyed on the merchant it was learned for.
            card_key=new.card_key,
        )
        moved("vendor", _vendor_shown(stored), _vendor_shown(new))
    old4, new4 = card_digits(stored.payment_mode), card_digits(new.payment_mode)
    if old4 != new4:
        kw["payment_mode"] = new.payment_mode
        moved("card_last4", old4, new4)
    if new.detected_tax is not None and new.detected_tax != stored.detected_tax:
        kw["detected_tax"] = new.detected_tax
        kw["tax_label"] = new.tax_label or stored.tax_label
        moved("tax", stored.detected_tax, new.detected_tax)
    if (new.document_type or "receipt") != (stored.document_type or "receipt"):
        kw["document_type"] = new.document_type
        moved("document_type", stored.document_type, new.document_type)
    if vendor_moved or "payment_mode" in kw:
        # The company follows the card and the merchant memory, as at arrival.
        kw["legal_entity_id"] = new.legal_entity_id
    recategorize = vendor_moved or (
        kw.get("legal_entity_id", stored.legal_entity_id) != stored.legal_entity_id
    )
    if not changes:
        return stored, {}, False
    return replace(stored, **kw), changes, recategorize


def not_taken_differences(stored: Receipt, new: Receipt) -> list[str]:
    """The compared-only fields this reading answers differently (alphanumerics
    only, so `HMVWDWIL 0029` and `HMVWDWIL0029` are one number)."""
    out = []
    pairs = {
        "document_kind": (stored.document_kind, new.document_kind),
        "reference": (stored.detected_reference, new.detected_reference),
        "invoice_number": (stored.invoice_number, new.invoice_number),
        "receipt_number": (stored.receipt_number, new.receipt_number),
    }
    for name, (a, b) in pairs.items():
        if name == "document_kind" and not a:
            continue  # read before item 223 step 4 added the field
        if _alnum(a) != _alnum(b):
            out.append(name)
    return out


# ── Reading ─────────────────────────────────────────────────────────────


@dataclass
class ReadPlan:
    """What a re-read of one month found. `merged` / `restores` are what a
    commit writes; the rest is the report."""
    reader: dict
    n_read: int = 0
    merged: dict[str, Receipt] = field(default_factory=dict)
    restores: dict[str, Receipt] = field(default_factory=dict)
    recategorize: set[str] = field(default_factory=set)
    changes: list[dict] = field(default_factory=list)
    reads_as_non_receipt: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    held: list[dict] = field(default_factory=list)
    not_taken: dict[str, int] = field(default_factory=dict)
    unchanged: int = 0
    # document id -> the stored reading the plan was made against, so a
    # commit can refuse a document someone replaced in the meantime.
    seen: dict[str, str] = field(default_factory=dict)

    def report(self) -> dict:
        return {
            "reader": self.reader,
            "n_read": self.n_read,
            "n_changed": len(self.changes),
            "n_unchanged": self.unchanged,
            "changes": self.changes,
            "reads_as_non_receipt": self.reads_as_non_receipt,
            "skipped": self.skipped,
            "held": self.held,
            "not_taken": {k: self.not_taken.get(k, 0) for k in NOT_TAKEN_FIELDS},
        }


def _fingerprint(r: Receipt) -> str:
    return json.dumps(receipt_to_dict(r), sort_keys=True, default=str)


def _read_one(work_dir: Path, stored: Receipt, *, client, entity: str, default_ccy):
    """(document id, arrival-shaped Receipt or None, skip reason or None)."""
    from ..ingest.receipts_folder import parse_receipt_file

    doc = stored.document_id
    path = receipt_image_file(work_dir, doc, expense_mode=True)
    if path is None:
        return doc, None, "no_file"
    try:
        parsed = parse_receipt_file(
            path, legal_entity_id=entity, client=client, default_currency=default_ccy,
        )
    except Exception as exc:  # noqa: BLE001 - one unreadable file never stops a month
        log.warning("item 240: could not read %s again (%s)", doc, exc)
        return doc, None, "unreadable"
    return doc, parsed, None


def _arrival_shape(parsed: Receipt, stored: Receipt) -> Receipt:
    """The per-file rules an arrival applies after reading. The stored text
    is kept where there is one: a mail body is read as a picture, and the
    body's own words were carried onto the receipt when it arrived."""
    from ..cli import keep_invoice_read_as_statement
    from ..correspondence import quarantine_correspondence

    text = stored.ocr_text if (stored.ocr_text or "").strip() else parsed.ocr_text
    r = replace(
        parsed,
        document_id=stored.document_id,
        receipt_name=stored.receipt_name,
        ocr_text=text,
    )
    r = keep_invoice_read_as_statement(r) or r
    return quarantine_correspondence(r) or r


def plan_reread(
    store: RunStore, run, *, llm_client, learning_db_path: "Path | None",
    workers: int = READ_WORKERS, skip: frozenset[str] = frozenset(),
) -> ReadPlan:
    """Read every stored receipt of the month again and decide, per field,
    what a commit would write. Writes nothing (the extraction cache warms)."""
    from ..cards import stamp_card_entities

    cfg = run.config or {}
    work_dir = Path(run.work_dir)
    entity = (cfg.get("expense") or {}).get("legal_entity_id", "")
    default_ccy = (cfg.get("receipts") or {}).get("default_currency")
    snapshot = run.snapshot or {}
    plan = ReadPlan(reader=reader_of(llm_client))

    # An expense the reviewer deleted (or moved to another month) is gone
    # from her month, so it is neither read nor listed.
    deleted = {
        e["document_id"] for e in store.get_expense_edits(run.run_id)
        if e.get("op") == "delete"
    }
    pool = [
        r for r in baseline_receipts(run)
        if "~" not in r.document_id and r.document_id not in deleted
    ]
    waiting: list[tuple[dict, Receipt]] = []
    for e in set_aside_entries(snapshot):
        if e.get("restored"):
            continue
        stored = (
            receipt_from_dict(e["receipt"]) if isinstance(e.get("receipt"), dict)
            else Receipt(
                document_id=e["file"], legal_entity_id=entity, detected_date=None,
                detected_total=None, detected_currency=None,
                detected_vendor=_display_name(e["file"]),
                receipt_name=e.get("display") or _display_name(e["file"]),
                document_type=e.get("reason") or "other",
            )
        )
        waiting.append((e, stored))
    targets = pool + [s for _e, s in waiting]
    for r in [t for t in targets if t.document_id in skip]:
        # The operator left this one out (a faded slip she reads better).
        plan.skipped.append({"document_id": r.document_id,
                             "display": r.receipt_name or _display_name(r.document_id),
                             "why": "operator_skip"})
    targets = [t for t in targets if t.document_id not in skip]
    for r in targets:
        plan.seen[r.document_id] = _fingerprint(r)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        results = list(ex.map(
            lambda s: _read_one(work_dir, s, client=llm_client, entity=entity,
                                default_ccy=default_ccy),
            targets,
        ))
    by_doc = {r.document_id: r for r in targets}
    read: dict[str, Receipt] = {}
    for doc, parsed, why in results:
        stored = by_doc[doc]
        if parsed is None:
            plan.skipped.append({
                "document_id": doc,
                "display": stored.receipt_name or _display_name(doc),
                "why": why,
            })
            continue
        read[doc] = _arrival_shape(parsed, stored)
    plan.n_read = len(read)

    # The arrival's batch rules, in its order: remembered corrections, the
    # card gate, then the card's company.
    registry = MerchantRegistry.from_settings(store.get_settings())
    memory = ExpenseMemory.from_db_path(learning_db_path)
    order = [d for d in by_doc if d in read]
    batch = memory.apply([read[d] for d in order])
    batch = drop_unvouched_remembered_cards(batch, registry)
    batch = stamp_card_entities(batch, _batch_cards(cfg), _batch_card_hints(cfg))
    read = dict(zip(order, batch))

    waiting_docs = {s.document_id: (e, s) for e, s in waiting}
    label_month = month_from_label(run.label)

    def elsewhere(change: dict, receipt: Receipt) -> dict:
        # A re-read never moves a receipt to another month; one whose new
        # date lies outside this batch's month says so (January 2026 exists
        # only because a July slip was read as 2026-01-04).
        d = receipt.detected_date
        if ("date" in change["changes"] and d is not None and label_month
                and (d.year, d.month) != label_month):
            change["new_date_outside_month"] = True
        return change

    for doc in order:
        stored, new = by_doc[doc], read[doc]
        display = stored.receipt_name or _display_name(doc)
        held: list = []
        for name in not_taken_differences(stored, new):
            plan.not_taken[name] = plan.not_taken.get(name, 0) + 1
        new_is_purchase = new.document_type not in NON_RECEIPT_LABELS
        if doc in waiting_docs:
            entry, _s = waiting_docs[doc]
            if not new_is_purchase:
                plan.unchanged += 1
                continue
            merged, changes, _recat = merge_reading(
                stored, new, label_year=label_month and label_month[0], held=held)
            plan.held += [{"document_id": doc, "display": display, **h} for h in held]
            merged = replace(merged, document_type=new.document_type or "receipt")
            plan.restores[doc] = merged
            plan.changes.append(elsewhere({
                "document_id": doc, "display": display, "where": "set_aside",
                "set_aside_reason": entry.get("reason") or "other",
                "joins_month": True, "changes": changes,
            }, merged))
            continue
        if not new_is_purchase and stored.document_type not in NON_RECEIPT_LABELS:
            plan.reads_as_non_receipt.append({
                "document_id": doc, "display": display,
                "reads_as": new.document_type,
            })
            continue
        merged, changes, recat = merge_reading(
            stored, new, label_year=label_month and label_month[0], held=held)
        plan.held += [{"document_id": doc, "display": display, **h} for h in held]
        if not changes:
            plan.unchanged += 1
            continue
        plan.merged[doc] = merged
        if recat:
            plan.recategorize.add(doc)
        plan.changes.append(elsewhere({
            "document_id": doc, "display": display, "where": "expense",
            "changes": changes,
        }, merged))
    return plan


# ── Commit ──────────────────────────────────────────────────────────────


def _categorize(store: RunStore, run, receipts: list[Receipt], *, llm_client,
                learning_db_path) -> list[Receipt]:
    """The categorization an arrival (and a restore) gives a receipt."""
    from ..categorize import categorize_receipts_with_registry
    from ..cli import _resolve_categorizer_chart

    if not receipts:
        return receipts
    cfg = run.config or {}
    registry = MerchantRegistry.from_settings(store.get_settings())
    learned = (
        MerchantCategoryLookup.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    try:
        _, account_labels, _scope = _resolve_categorizer_chart(
            cfg, Path(run.work_dir), None, {}
        )
    except Exception:  # noqa: BLE001 - labels degrade, a re-read never breaks
        account_labels = None
    out, _ = categorize_receipts_with_registry(
        receipts, registry=registry, client=llm_client,
        chart_of_accounts=account_labels, learned=learned,
        entity_orgs=cfg.get(GL_ENTITY_ORGS_KEY),
    )
    return out


def commit_plan(
    store: RunStore, run_id: str, plan: ReadPlan, now_iso: str, *,
    llm_client, learning_db_path: "Path | None",
) -> dict:
    """Write the plan's readings into the month and re-match it. Returns
    what was written, and the re-match's own answer."""
    run = store.get_run(run_id)
    refused = reread_refusal(run)
    if refused is not None:
        raise refused
    # Categorize outside the lock: it calls the model.
    recat = [plan.merged[d] for d in sorted(plan.recategorize) if d in plan.merged]
    recat_done = {r.document_id: r for r in _categorize(
        store, run, recat, llm_client=llm_client, learning_db_path=learning_db_path)}
    restores = {r.document_id: r for r in _categorize(
        store, run, list(plan.restores.values()), llm_client=llm_client,
        learning_db_path=learning_db_path)}

    written: list[str] = []
    joined: list[str] = []
    gone: list[dict] = []
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run_id)
        refused = reread_refusal(fresh)
        if refused is not None:
            raise refused
        snapshot = dict(fresh.snapshot or {})
        current = {r.document_id: r for r in baseline_receipts(fresh)}
        pool_dicts = list(snapshot.get("receipts") or [])
        baseline = snapshot.get(EXTRACTED_RECEIPTS_KEY)
        baseline = list(baseline) if isinstance(baseline, list) else None
        fields_of = {c["document_id"]: sorted(c["changes"]) for c in plan.changes}
        for doc, merged in plan.merged.items():
            now = current.get(doc)
            if now is None or _fingerprint(now) != plan.seen.get(doc):
                gone.append({"document_id": doc, "why": "changed_since_read"})
                continue
            merged = recat_done.get(doc, merged)
            # Never silent: the row says what the second reading changed.
            note = f"read again {now_iso[:10]}: {', '.join(fields_of.get(doc, []))} changed"
            merged = replace(merged, data_quality_note=(
                f"{merged.data_quality_note}; {note}" if merged.data_quality_note else note))
            row = receipt_to_dict(merged)
            pool_dicts = [row if d.get("document_id") == doc else d for d in pool_dicts]
            if baseline is not None:
                baseline = [row if isinstance(d, dict) and d.get("document_id") == doc else d
                            for d in baseline]
            written.append(doc)
        snapshot["receipts"] = pool_dicts
        if baseline is not None:
            snapshot[EXTRACTED_RECEIPTS_KEY] = baseline

        entries = set_aside_entries(snapshot)
        _, _receipts, outcome, _ = snapshot_from_dict(snapshot)
        pool_ids = {d.get("document_id") for d in pool_dicts}
        for doc, receipt in restores.items():
            entry = next((e for e in entries if e["file"] == doc), None)
            if entry is None or entry.get("restored") or doc in pool_ids:
                gone.append({"document_id": doc, "why": "changed_since_read"})
                continue
            entry["restored"] = True
            entry["restored_at"] = now_iso
            entry["restored_by"] = "reread"
            note = (f"set aside as {entry.get('reason') or 'other'}; read again "
                    f"{now_iso[:10]} as a {receipt.document_type or 'receipt'}")
            receipt = replace(receipt, data_quality_note=(
                f"{receipt.data_quality_note}; {note}" if receipt.data_quality_note else note))
            pool_dicts.append(receipt_to_dict(receipt))
            outcome.unmatched_receipts.append(doc)
            joined.append(doc)
        if joined:
            snapshot["receipts"] = pool_dicts
            snapshot["set_aside"] = entries
            snapshot["outcome"] = outcome_to_dict(outcome)

        record = {
            "at": now_iso,
            "reader": plan.reader,
            "n_read": plan.n_read,
            "documents": [c for c in plan.changes
                          if c["document_id"] in set(written) | set(joined)],
        }
        snapshot[SNAPSHOT_KEY] = list(snapshot.get(SNAPSHOT_KEY) or []) + [record]
        wrote = bool(written or joined)
        if wrote and has_statement(fresh):
            # Item 113: the readings and the debt to re-pair them are one write.
            snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(fresh.snapshot, TRIGGER)
        elif wrote:
            # A month with no statement is never re-matched: its account keys
            # are computed here, as a receipt add computes them.
            receipts_now = [receipt_from_dict(d) for d in pool_dicts]
            edited = apply_expense_edits(
                receipts_now, store.get_expense_field_overrides(run_id),
                store.get_expense_edits(run_id),
                default_entity=(fresh.config or {}).get("expense", {}).get("legal_entity_id", ""),
            )
            keys, copies = cross_month_duplicate_evidence(store, fresh, edited)
            store_cross_month_evidence(snapshot, keys, copies)
        store.update_run_snapshot(run_id, snapshot)
        if joined:
            pool_receipts = [receipt_from_dict(d) for d in pool_dicts]
            n_cat, n_uncat = categorized_counts(pool_receipts)
            store.update_run_summary(run_id, {
                **fresh.summary,
                "n_expenses": len(pool_receipts),
                "n_receipts": len(pool_receipts),
                "n_categorized": n_cat,
                "n_uncategorized": n_uncat,
                "n_set_aside": sum(1 for e in entries if not e.get("restored")),
            })
    rematch = None
    if (written or joined) and has_statement(store.get_run(run_id)):
        rematch = rematch_after_change(
            store, run_id, learning_db_path=learning_db_path, trigger=TRIGGER,
        )
    return {"written": written, "joined": joined, "gone": gone, "rematch": rematch}


# ── What changes around the readings ───────────────────────────────────


def month_state(store: RunStore, run) -> dict:
    """The match and the decisions, as the consequences diff reads them."""
    _tx, _r, outcome, _ = snapshot_from_dict(run.snapshot or {})
    pairs = {m.transaction_id: m.document_id for m in outcome.matches}
    decisions = {
        tx: {"status": d.status, "document_id": d.chosen_document_id,
             "decided_by": d.decided_by}
        for tx, d in store.get_decisions(run.run_id).items()
    }
    return {"pairs": pairs, "decisions": decisions}


def _row_facts(view: dict) -> dict[str, dict]:
    keys = ("vendor", "date", "total", "currency", "category", "zoho_account", "entity")
    return {
        e["document_id"]: {k: e.get(k) for k in keys}
        for e in view.get("expenses") or [] if e.get("document_id")
    }


def consequences(before_view: dict, before: dict, after_view: dict, after: dict,
                 plan: ReadPlan) -> dict:
    """What moved around the readings: pairs, confirmed matches, copies,
    and each expense's category, account and company."""
    pairs_changed = []
    for tx in sorted(set(before["pairs"]) | set(after["pairs"])):
        b, a = before["pairs"].get(tx), after["pairs"].get(tx)
        if b != a:
            pairs_changed.append({"transaction_id": tx, "before": b, "after": a})
    moving_money = {
        c["document_id"] for c in plan.changes
        if {"date", "total", "currency"} & set(c["changes"])
    }
    confirmed = []
    for tx, d in sorted(before["decisions"].items()):
        if d["status"] != STATUS_CONFIRMED:
            continue
        now = after["decisions"].get(tx) or {}
        lost = now.get("status") != STATUS_CONFIRMED or now.get("document_id") != d["document_id"]
        reading_moves = d["document_id"] in moving_money
        if lost or reading_moves:
            confirmed.append({
                "transaction_id": tx, "document_id": d["document_id"],
                "decided_by": d.get("decided_by"),
                "reading_moves": reading_moves,
                "after": {"status": now.get("status"), "document_id": now.get("document_id")},
            })
    rows_b, rows_a = _row_facts(before_view), _row_facts(after_view)
    rows = []
    for doc in sorted(set(rows_b) | set(rows_a)):
        b, a = rows_b.get(doc), rows_a.get(doc)
        if b == a:
            continue
        moved = sorted(k for k in set(b or {}) | set(a or {})
                       if (b or {}).get(k) != (a or {}).get(k))
        rows.append({"document_id": doc, "fields": moved, "before": b, "after": a})
    return {
        "pairs": {
            "n_before": len(before["pairs"]), "n_after": len(after["pairs"]),
            "changed": pairs_changed,
        },
        "confirmed": confirmed,
        "expenses": rows,
        "duplicates": layer_diff(duplicate_layer(before_view), duplicate_layer(after_view)),
    }


def shadow_preview(
    db_path: Path, learning_db_path: "Path | None", run_id: str, plan: ReadPlan,
    view_of: ViewOf, *, llm_client,
) -> dict:
    """The consequences of committing `plan`, measured on throwaway copies of
    the database (then deleted; the month itself is only read).

    Two copies, because a re-match on its own already moves things: a rule
    that changed since the month's last re-match (item 223's kept copy, a
    confirmation it no longer reaches) lands at ANY next re-match. Copy A is
    only re-matched; copy B gets the readings and is re-matched. `A -> B` is
    what the re-read itself changes (the top-level keys); `now -> A` is what
    any re-match of this month would change today (`rematch_alone`)."""
    with RunStore(db_path) as store:
        run = store.get_run(run_id)
        before_view = view_of(store, run)
        before = month_state(store, run)

    def alone(shadow: RunStore):
        rematch = None
        if has_statement(shadow.get_run(run_id)):
            rematch = rematch_after_change(
                shadow, run_id, learning_db_path=learning_db_path, trigger=TRIGGER)
        return rematch

    def reread(shadow: RunStore):
        return commit_plan(
            shadow, run_id, plan, _now(), llm_client=llm_client,
            learning_db_path=learning_db_path,
        ).get("rematch")

    a_view, a_state, _a = _on_copy(db_path, run_id, view_of, alone)
    b_view, b_state, b_rematch = _on_copy(db_path, run_id, view_of, reread)
    out = consequences(a_view, a_state, b_view, b_state, plan)
    out["rematch_error"] = (b_rematch or {}).get("error")
    out["rematch_alone"] = consequences(
        before_view, before, a_view, a_state, ReadPlan(reader={}))
    return out


def _on_copy(db_path: Path, run_id: str, view_of: ViewOf, fn):
    """(view, state, fn's answer) after running `fn` on a throwaway copy."""
    tmp = Path(tempfile.mkdtemp(prefix="reread240-"))
    try:
        shadow_path = tmp / "shadow.sqlite"
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(shadow_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        with RunStore(shadow_path) as shadow:
            answer = fn(shadow)
            run = shadow.get_run(run_id)
            return view_of(shadow, run), month_state(shadow, run), answer
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── The job ─────────────────────────────────────────────────────────────


def run_reread_job(
    db_path: Path, learning_db_path: "Path | None", job_id: str, run_id: str,
    view_of: ViewOf, *, dry_run: bool, skip: list[str] | None = None,
) -> None:
    """Read the month again, then either measure the plan on a copy (dry
    run) or commit it to the month (real run). A refusal lands as the job's
    error, its code first."""
    def _stage(name: str) -> None:
        try:
            with RunStore(db_path) as s:
                s.set_job_stage(job_id, name, _now())
        except Exception:  # noqa: BLE001 - progress is best-effort
            pass

    readings = None
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            refused = reread_refusal(run)
            if refused is not None:
                raise refused
            llm_client, tracker, _source = _batch_llm_client(run.config or {})
            if llm_client is None:
                raise RunInputError("no receipt reader is configured",
                                    code="reread_no_reader")
        _stage("reading")
        with RunStore(db_path) as store:
            plan = plan_reread(store, run, llm_client=llm_client,
                               learning_db_path=learning_db_path,
                               skip=frozenset(skip or ()))
        readings = plan.report()
        if dry_run:
            _stage("previewing")
            effects = shadow_preview(
                db_path, learning_db_path, run_id, plan, view_of, llm_client=llm_client,
            )
            result = {"dry_run": True, "run_id": run_id, "label": run.label,
                      "readings": readings, "consequences": effects}
        else:
            _stage("applying")
            with RunStore(db_path) as store:
                before_run = store.get_run(run_id)
                before_view = view_of(store, before_run)
                before = month_state(store, before_run)
                commit = commit_plan(
                    store, run_id, plan, _now(), llm_client=llm_client,
                    learning_db_path=learning_db_path,
                )
                after_run = store.get_run(run_id)
                applied = consequences(before_view, before, view_of(store, after_run),
                                       month_state(store, after_run), plan)
            result = {"dry_run": False, "run_id": run_id, "label": run.label,
                      "readings": readings, "applied": applied,
                      "written": commit["written"], "joined": commit["joined"],
                      "gone": commit["gone"], "rematch": commit["rematch"]}
        if tracker is not None:
            result["cost_usd"] = float(round(tracker.total_cost_usd, 4))
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id,
                result=json.dumps(result, default=str), updated_at=_now(),
            )
    except RunInputError as exc:
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=f"{exc.code}: {exc.message}",
                result=json.dumps({"readings": readings}, default=str) if readings else None,
                updated_at=_now(),
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        log.exception("item 240: re-read failed on %s", run_id)
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc),
                result=json.dumps({"readings": readings}, default=str) if readings else None,
                updated_at=_now(),
            )
