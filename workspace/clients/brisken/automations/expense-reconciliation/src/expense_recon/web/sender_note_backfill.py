"""Apply our senders' notes to the receipts already in a month (backlog item
252, owner 2026-10-07: "change existing rows, reread if need be").

Item 250 reads the note one of our senders typed above a forwarded receipt
when the receipt ARRIVES, so a receipt already in a month carries no note
fields and nothing changed for it. `POST /api/runs/{run_id}/sender-notes/apply`
is the operator's way to apply the same rulings to one month's stored
receipts, after previewing what that changes.

For every receipt in the month's pool that came by mail:

1. **The note.** The provenance entry's own `operator_note` when it recorded
   one. Receipts ingested before 2026-09-20 never recorded it, so the note is
   read again from the mail it came in: the archive the entry names
   (`archive`, item 106), else the one archive whose log row lists this
   document for this month. No confident mapping means no note; an archive is
   never guessed. A note read again also carries the mail's agent-directed
   text flags: the ones the archive recorded, else a fresh scan of its
   subject and body (`untrusted.scan`, the arrival's own scan), because a mail
   from before that scan existed was never checked.
2. **The trust boundary** is item 250's, unchanged:
   `intake_mail.trusted_sender_notes` over those entries.
3. **The stamp** is item 250's too (`stamp_sender_notes`), on both stored
   lists that hold the receipt: the `receipts` pool and the `extracted_receipts`
   baseline the views and every re-match read. A pool row the reviewer gave a
   company of her own keeps the company it was baked with on a baked month.
   A receipt already carrying identical note fields is unchanged, so a second
   run changes nothing.
4. **The display half.** A note read again from the archive is also written
   into the month's `intake_provenance`, as arrival records it, so the row
   shows it.
5. **Categories**, only where the note can change them and only on a month on
   the GL engine: a row whose shown company moves is categorized again for
   that company (its chart changed); a row whose company stays but whose note
   asks an account question (`account_hint`) is categorized again and keeps
   the old answer unless the new one is the note's (`NOTE`), so a model
   suggestion never churns. Every other row is stamped only.

What it never touches: the reviewer's tables. Her company pick, category
picks and edits are separate rows applied on read, so they stay on top, and
nothing here is written where the Publish learners read: a note is not a
correction (owner 2026-09-24).

A month with a statement re-matches when a row's company moved, because the
company scopes the match (`EXPENSE_MATCH_FIELDS`): a person's company edit
re-matches for the same reason. The dry run measures that on throwaway copies
of the database, exactly as item 240's re-read does; on a month with no
statement, or where no company moves, it builds the Expenses view on the run
with the new snapshot in memory. Neither writes to the month.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..matching.types import ClassificationSource, Receipt
from ..sender_note import account_hint, stamp_sender_notes
from .duplicate_reapply import rematch_running
from .receipt_reread import (
    ReadPlan,
    _categorize,
    _on_copy,
    consequences,
    month_state,
)
from .serialize import receipt_from_dict, receipt_to_dict
from .service import (
    EXTRACTED_RECEIPTS_KEY,
    GL_ENTITY_ORGS_KEY,
    MODE_EXPENSE_GENERATION,
    REMATCH_PENDING_KEY,
    RunInputError,
    _BATCH_ADD_LOCK,
    _batch_llm_client,
    baseline_receipts,
    has_statement,
    rematch_after_change,
    rematch_pending_mark,
    run_mode,
)
from .store import JOB_DONE, JOB_ERROR, RunStore

log = logging.getLogger(__name__)

ViewOf = Callable[[RunStore, object], dict]

TRIGGER = "sender_notes"
SNAPSHOT_KEY = "sender_notes_applied"
POOL_KEYS = ("receipts", EXTRACTED_RECEIPTS_KEY)
# Every row of the mail log: the mapping from a document to its mail must
# see the whole history, not the last page.
LOG_ROWS = 10_000_000
# The note fields a stamp writes; a receipt whose fields read the same after
# the stamp is unchanged.
NOTE_FIELDS = ("sender_note", "sender_note_entity", "sender_note_split", "legal_entity_id")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Refusals ────────────────────────────────────────────────────────────


def mailed_documents(snapshot: dict) -> list[str]:
    """The pool's receipts that came by mail (a provenance entry), in pool
    order."""
    prov = snapshot.get("intake_provenance") or {}
    return [
        str(d.get("document_id")) for d in snapshot.get("receipts") or []
        if isinstance(d, dict) and isinstance(prov.get(d.get("document_id")), dict)
    ]


def backfill_refusal(run) -> RunInputError | None:
    """Why the senders' notes cannot be applied to this run, or None. Checked
    by the route, again when the job starts and again when it commits."""
    if run is None:
        return RunInputError("run not found", code="run_not_found")
    if run_mode(run) != MODE_EXPENSE_GENERATION:
        return RunInputError("not an expense batch", code="not_an_expense_batch")
    if run.published:
        return RunInputError(
            "this month is published; unpublish it before applying the "
            "senders' notes", code="month_published")
    if rematch_running(run):
        return RunInputError(
            "a re-match of this month is running or owed; wait for it to "
            "finish", code="rematch_running")
    if not mailed_documents(run.snapshot or {}):
        return RunInputError(
            "this month holds no receipts that came by mail",
            code="sender_notes_no_receipts")
    return None


def confirm_refusal(run, confirm: str) -> RunInputError | None:
    """The typed confirm: the month's label or its run id, for a dry run as
    for a real one, so a mistyped id never touches another month quietly."""
    if not confirm:
        return RunInputError(
            "confirm is required: repeat the month label (or run id) to apply "
            "the senders' notes to it", code="sender_notes_confirm_required")
    if confirm not in {(run.label or "").strip(), run.run_id}:
        return RunInputError("confirm label mismatch",
                             code="sender_notes_confirm_mismatch")
    return None


# ── Finding each receipt's note ─────────────────────────────────────────


def archives_by_document(data_root: Path, run_id: str) -> dict[str, list[str]]:
    """document id -> every archive whose mail lists it among the expenses it
    created in THIS month (the log row, overlaid with the archive's meta)."""
    from .intake_mail import read_log

    out: dict[str, list[str]] = {}
    seen: set[str] = set()
    for row in read_log(data_root, limit=LOG_ROWS):
        name = str(row.get("archive") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        if str(row.get("batch_id") or "") != run_id or row.get("batch_deleted"):
            continue
        for doc in row.get("documents") or []:
            out.setdefault(str(doc), []).append(name)
    return out


def _mail_flags(arch: Path) -> tuple[list[dict], bool]:
    """(the agent-directed text this mail carried, whether it could be
    checked): what its archive recorded, else the arrival's own scan of its
    subject and body, run now. A mail that could not be checked is never
    trusted, and no flag is invented for the row."""
    from .. import untrusted
    from .intake_mail import _archive_body_text, _read_meta, _untrusted_flags

    flags = _untrusted_flags(arch)
    if flags:
        return flags, True
    try:
        return [dict(f) for f in untrusted.scan(
            str(_read_meta(arch).get("subject") or ""), _archive_body_text(arch))], True
    except Exception:  # noqa: BLE001 - an unscannable mail is never trusted
        return [], False


@dataclass
class NoteFinding:
    """Every mailed receipt's note, as the trust filter will read it."""
    provenance: dict[str, dict] = field(default_factory=dict)
    reread: dict[str, str] = field(default_factory=dict)
    restore: dict[str, dict] = field(default_factory=dict)
    skipped: list[dict] = field(default_factory=list)
    n_scanned: int = 0
    n_mailed: int = 0
    n_recorded: int = 0


def find_notes(run, data_root: Path, *, skip_docs: frozenset[str] = frozenset()) -> NoteFinding:
    """The provenance entries of the month's mailed receipts, each carrying
    its note: recorded, or read again from the one mail it came in."""
    from .intake_mail import _archive_dir, _archive_operator_note

    snapshot = run.snapshot or {}
    prov = snapshot.get("intake_provenance") or {}
    out = NoteFinding()
    index: dict[str, list[str]] | None = None
    for d in snapshot.get("receipts") or []:
        if not isinstance(d, dict):
            continue
        doc = str(d.get("document_id") or "")
        if not doc or doc in skip_docs:
            continue
        out.n_scanned += 1
        entry = prov.get(doc)
        if not isinstance(entry, dict):
            continue
        out.n_mailed += 1
        if str(entry.get("operator_note") or "").strip():
            out.n_recorded += 1
            out.provenance[doc] = dict(entry)
            continue
        name = str(entry.get("archive") or "")
        if not name:
            if index is None:
                index = archives_by_document(data_root, run.run_id)
            names = index.get(doc) or []
            if len(names) != 1:
                out.skipped.append({
                    "document_id": doc,
                    "why": "archive_ambiguous" if names else "no_archive",
                })
                continue
            name = names[0]
        arch = _archive_dir(data_root, name)
        if arch is None:
            out.skipped.append({"document_id": doc, "why": "archive_missing"})
            continue
        note = _archive_operator_note(arch)  # item 252: the note, read again
        if not note:
            continue
        patch: dict = {"operator_note": note}
        checked = True
        if not entry.get("untrusted_instructions"):
            flags, checked = _mail_flags(arch)
            if flags:
                patch["untrusted_instructions"] = flags
        out.reread[doc] = note
        out.restore[doc] = patch
        out.provenance[doc] = {**entry, **patch}
        if not checked:
            out.provenance[doc]["untrusted_instructions"] = [{"kind": "unchecked"}]
    return out


# ── The plan ────────────────────────────────────────────────────────────


def _note_fields(r: Receipt) -> tuple:
    return tuple(getattr(r, f) for f in NOTE_FIELDS)


def _stamp(r: Receipt, note: str) -> Receipt:
    """One receipt through item 250's own stamp."""
    (new,) = stamp_sender_notes([r], {r.document_id: note})
    return new


def _has_note_answer(r: Receipt) -> bool:
    return any(
        li.categorization is not None
        and li.categorization.source is ClassificationSource.NOTE
        for li in r.line_items
    )


def _with_categorizations(old: Receipt, new: Receipt) -> Receipt:
    """`old` carrying `new`'s line categorizations, line by line where the
    lines agree (`recategorize_for_companies`' swap)."""
    if len(old.line_items) == len(new.line_items):
        items = tuple(
            replace(li, categorization=n.categorization)
            for li, n in zip(old.line_items, new.line_items)
        )
    else:
        items = new.line_items
    return replace(old, line_items=items)


def _cat_view(cat) -> dict | None:
    if not cat:
        return None
    return {k: cat.get(k) for k in ("category", "zoho_account", "source")}


def row_facts(view: dict) -> dict[str, dict]:
    """What the note can move on each Expenses row."""
    out: dict[str, dict] = {}
    for e in view.get("expenses") or []:
        doc = e.get("document_id")
        if not doc:
            continue
        vendor = e.get("vendor")
        out[doc] = {
            "vendor": vendor.get("display") if isinstance(vendor, dict) else vendor,
            "legal_entity_id": e.get("legal_entity_id"),
            "entity_source": e.get("entity_source"),
            "posting_category": _cat_view(e.get("posting_category")),
            "suggested_category": _cat_view(e.get("suggested_category")),
            "review_reason_code": (e.get("review") or {}).get("reason_code"),
            "operator_note": e.get("operator_note"),
        }
    return out


@dataclass
class NotePlan:
    """What applying the notes to one month would write. `rows` / `seen` are
    per snapshot list (`receipts`, `extracted_receipts`): the new row and the
    row it was planned against, so a commit can refuse a row someone changed
    in the meantime."""
    finding: NoteFinding
    trusted: dict[str, str] = field(default_factory=dict)
    stamped: list[str] = field(default_factory=list)
    rows: dict[str, dict[str, dict]] = field(default_factory=dict)
    seen: dict[str, dict[str, dict]] = field(default_factory=dict)
    company_changed: set[str] = field(default_factory=set)
    recategorized: dict[str, str] = field(default_factory=dict)
    account_by_note: set[str] = field(default_factory=set)
    snapshot: dict = field(default_factory=dict)
    cost_usd: float | None = None

    def counts(self) -> dict:
        f = self.finding
        return {
            "receipts": f.n_scanned,
            "mailed": f.n_mailed,
            "notes_found": f.n_recorded + len(f.reread),
            "notes_recorded": f.n_recorded,
            "notes_reread": len(f.reread),
            "trusted": len(self.trusted),
            "stamped": len(self.stamped),
            "company_changed": len(self.company_changed),
            "account_by_note": len(self.account_by_note),
            "unchanged": len(self.trusted) - len(self.stamped),
            "display_restored": len(f.restore),
        }

    def rematch_owed(self, run) -> bool:
        return bool(self.company_changed) and has_statement(run)


def plan_backfill(
    store: RunStore, run, *, data_root: Path, learning_db_path: "Path | None",
    view_of: ViewOf,
) -> NotePlan:
    """Find, filter and stamp every mailed receipt's note, and categorize again
    what the note can change. Writes nothing; the model is called only for
    rows whose category the note can move."""
    from .intake_mail import IntakeConfig, trusted_sender_notes

    cfg = run.config or {}
    snapshot = run.snapshot or {}
    deleted = frozenset(
        e["document_id"] for e in store.get_expense_edits(run.run_id)
        if e.get("op") == "delete"
    )
    finding = find_notes(run, data_root, skip_docs=deleted)
    plan = NotePlan(finding=finding)
    plan.trusted = trusted_sender_notes(
        finding.provenance, IntakeConfig.from_settings(store.get_settings()))

    base = {r.document_id: r for r in baseline_receipts(run)}
    for doc in [d for d in mailed_documents(snapshot) if d in plan.trusted]:
        old = base.get(doc)
        if old is None:
            continue
        new = _stamp(old, plan.trusted[doc])
        if _note_fields(new) != _note_fields(old):
            plan.stamped.append(doc)

    # The stamped snapshot: each list's own row stamped, and the display half.
    baked = isinstance(snapshot.get(EXTRACTED_RECEIPTS_KEY), list)
    picked = {
        doc for doc, f in store.get_expense_field_overrides(run.run_id).items()
        if str((f or {}).get("legal_entity") or "").strip()
    }
    stamped = set(plan.stamped)
    s1 = dict(snapshot)
    for key in POOL_KEYS:
        rows = snapshot.get(key)
        if not isinstance(rows, list):
            continue
        plan.rows[key], plan.seen[key] = {}, {}
        for d in rows:
            doc = d.get("document_id") if isinstance(d, dict) else None
            if doc not in stamped:
                continue
            old = receipt_from_dict(d)
            new = _stamp(old, plan.trusted[doc])
            if key == "receipts" and baked and doc in picked:
                # The baked pool holds the company she picked; the next bake
                # puts it there again, and the matcher reads it till then.
                new = replace(new, legal_entity_id=old.legal_entity_id)
            plan.seen[key][doc] = d
            plan.rows[key][doc] = receipt_to_dict(new)
        s1[key] = [
            plan.rows[key].get(d.get("document_id"), d) if isinstance(d, dict) else d
            for d in rows
        ]
    if finding.restore:
        prov = dict(s1.get("intake_provenance") or {})
        for doc, patch in finding.restore.items():
            prov[doc] = {**prov[doc], **patch}
        s1["intake_provenance"] = prov

    plan.snapshot = s1
    if not plan.stamped:
        return plan
    before = row_facts(view_of(store, run))
    mid = row_facts(view_of(store, replace(run, snapshot=s1)))
    for doc in plan.stamped:
        if (before.get(doc) or {}).get("legal_entity_id") != (mid.get(doc) or {}).get("legal_entity_id"):
            plan.company_changed.add(doc)

    entity_orgs = cfg.get(GL_ENTITY_ORGS_KEY)
    todo: dict[str, str] = {}
    if entity_orgs is not None:
        stamped_base = {
            r.document_id: r for r in baseline_receipts(replace(run, snapshot=s1))
        }
        for doc in plan.stamped:
            if doc in plan.company_changed:
                todo[doc] = "company"
            elif account_hint(stamped_base[doc].sender_note):
                todo[doc] = "account"
    answers: dict[str, Receipt] = {}
    if todo:
        llm_client, tracker, _source = _batch_llm_client(cfg)
        shown = {doc: (mid.get(doc) or {}).get("legal_entity_id") or "" for doc in todo}
        recat = _categorize(
            store, run,
            [replace(stamped_base[doc], legal_entity_id=shown[doc]) for doc in todo],
            llm_client=llm_client, learning_db_path=learning_db_path,
        )
        for r in recat:
            why = todo[r.document_id]
            if why == "account" and not _has_note_answer(r):
                continue  # the note named no account: the old answer stays
            answers[r.document_id] = r
            plan.recategorized[r.document_id] = why
            if _has_note_answer(r):
                plan.account_by_note.add(r.document_id)
        if tracker is not None:
            plan.cost_usd = float(round(tracker.total_cost_usd, 4))

    for key in plan.rows:
        for doc, d in list(plan.rows[key].items()):
            if doc in answers:
                plan.rows[key][doc] = receipt_to_dict(
                    _with_categorizations(receipt_from_dict(d), answers[doc]))
        if key in s1:
            s1[key] = [
                plan.rows[key].get(d.get("document_id"), d) if isinstance(d, dict) else d
                for d in s1[key]
            ]
    plan.snapshot = s1
    return plan


# ── Commit ──────────────────────────────────────────────────────────────


def commit_plan(
    store: RunStore, run_id: str, plan: NotePlan, now_iso: str, *,
    learning_db_path: "Path | None",
) -> dict:
    """Write the plan into the month under the batch lock, against a fresh
    read of it, and re-match the month when a company moved on a month with
    a statement. Returns what was written and the re-match's own answer."""
    written: list[str] = []
    restored: list[str] = []
    gone: list[dict] = []
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run_id)
        refused = backfill_refusal(fresh)
        if refused is not None:
            raise refused
        snapshot = dict(fresh.snapshot or {})
        moved = set()
        for key, planned in plan.seen.items():
            now = {
                d.get("document_id"): d for d in snapshot.get(key) or []
                if isinstance(d, dict)
            }
            moved |= {doc for doc, d in planned.items() if now.get(doc) != d}
        for doc in sorted(moved):
            gone.append({"document_id": doc, "why": "changed_since_read"})
        for key, rows in plan.rows.items():
            current = snapshot.get(key)
            if not isinstance(current, list):
                continue
            snapshot[key] = [
                rows[d["document_id"]]
                if isinstance(d, dict) and d.get("document_id") in rows
                and d.get("document_id") not in moved else d
                for d in current
            ]
        written = [doc for doc in plan.stamped if doc not in moved]
        prov = dict(snapshot.get("intake_provenance") or {})
        for doc, patch in plan.finding.restore.items():
            entry = prov.get(doc)
            if isinstance(entry, dict) and not str(entry.get("operator_note") or "").strip():
                prov[doc] = {**entry, **patch}
                restored.append(doc)
        if restored:
            snapshot["intake_provenance"] = prov
        if not written and not restored:
            return {"written": [], "restored": [], "gone": gone, "rematch": None}
        snapshot[SNAPSHOT_KEY] = list(snapshot.get(SNAPSHOT_KEY) or []) + [{
            "at": now_iso,
            "documents": written,
            "restored": restored,
            "company_changed": sorted(set(written) & plan.company_changed),
            "account_by_note": sorted(set(written) & plan.account_by_note),
        }]
        owed = bool(set(written) & plan.company_changed) and has_statement(fresh)
        if owed:
            # Item 113: the new companies and the debt to re-pair them are
            # one write, so no restart can store the one without the other.
            snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(fresh.snapshot, TRIGGER)
        store.update_run_snapshot(run_id, snapshot)
    rematch = None
    if owed:
        rematch = rematch_after_change(
            store, run_id, learning_db_path=learning_db_path, trigger=TRIGGER,
        )
    return {"written": written, "restored": restored, "gone": gone, "rematch": rematch}


# ── The report ──────────────────────────────────────────────────────────


def document_report(plan: NotePlan, docs: list[str], before_view: dict,
                    after_view: dict) -> list[dict]:
    """Per changed receipt: what the row showed and what it shows after."""
    before, after = row_facts(before_view), row_facts(after_view)
    out = []
    for doc in docs:
        b, a = before.get(doc), after.get(doc)
        keys = [k for k in (b or a or {}) if k != "vendor"]
        out.append({
            "document_id": doc,
            "vendor": (a or b or {}).get("vendor"),
            "note": plan.trusted.get(doc),
            "note_reread": doc in plan.finding.reread,
            "company_changed": doc in plan.company_changed,
            "recategorized": plan.recategorized.get(doc),
            "account_by_note": doc in plan.account_by_note,
            "fields": [k for k in keys if (b or {}).get(k) != (a or {}).get(k)],
            "before": b,
            "after": a,
        })
    return out


def preview(
    db_path: Path, learning_db_path: "Path | None", run_id: str, plan: NotePlan,
    view_of: ViewOf,
) -> dict:
    """The dry run's report. Where a re-match is owed it is measured on two
    throwaway copies, as item 240's dry run does: copy A is only re-matched,
    copy B gets the notes and is re-matched, so `consequences` is the notes'
    own effect and `rematch_alone` what any re-match would change today.
    Otherwise the Expenses view is built on the run with the new snapshot in
    memory."""
    with RunStore(db_path) as store:
        run = store.get_run(run_id)
        before_view = view_of(store, run)
        before = month_state(store, run)
        owed = plan.rematch_owed(run)
        if not owed:
            planned = replace(run, snapshot=plan.snapshot)
            after_view = view_of(store, planned)
            effects = consequences(
                before_view, before, after_view, month_state(store, planned),
                ReadPlan(reader={}))
            effects["rematch_error"] = None
            effects["rematch_alone"] = None
            return {"documents": document_report(plan, plan.stamped, before_view, after_view),
                    "consequences": effects, "rematch_owed": False}

    def alone(shadow: RunStore):
        return rematch_after_change(
            shadow, run_id, learning_db_path=learning_db_path, trigger=TRIGGER)

    def apply(shadow: RunStore):
        return commit_plan(shadow, run_id, plan, _now(),
                           learning_db_path=learning_db_path).get("rematch")

    a_view, a_state, _a = _on_copy(db_path, run_id, view_of, alone)
    b_view, b_state, b_rematch = _on_copy(db_path, run_id, view_of, apply)
    effects = consequences(a_view, a_state, b_view, b_state, ReadPlan(reader={}))
    effects["rematch_error"] = (b_rematch or {}).get("error")
    effects["rematch_alone"] = consequences(
        before_view, before, a_view, a_state, ReadPlan(reader={}))
    return {"documents": document_report(plan, plan.stamped, before_view, b_view),
            "consequences": effects, "rematch_owed": True}


# ── The job ─────────────────────────────────────────────────────────────


def run_backfill_job(
    db_path: Path, learning_db_path: "Path | None", job_id: str, run_id: str,
    view_of: ViewOf, *, dry_run: bool, data_root: Path,
) -> None:
    """Plan the month's notes, then either measure the plan (dry run) or
    commit it (real run). A refusal lands as the job's error, its code
    first."""
    def _stage(name: str) -> None:
        try:
            with RunStore(db_path) as s:
                s.set_job_stage(job_id, name, _now())
        except Exception:  # noqa: BLE001 - progress is best-effort
            pass

    try:
        _stage("reading")
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            refused = backfill_refusal(run)
            if refused is not None:
                raise refused
            plan = plan_backfill(store, run, data_root=data_root,
                                 learning_db_path=learning_db_path, view_of=view_of)
        result = {"dry_run": dry_run, "run_id": run_id, "label": run.label,
                  "counts": plan.counts(), "skipped": plan.finding.skipped}
        if dry_run:
            _stage("previewing")
            result.update(preview(db_path, learning_db_path, run_id, plan, view_of))
            result["display_restored"] = sorted(plan.finding.restore)
        else:
            _stage("applying")
            with RunStore(db_path) as store:
                before_run = store.get_run(run_id)
                before_view = view_of(store, before_run)
                before = month_state(store, before_run)
                commit = commit_plan(store, run_id, plan, _now(),
                                     learning_db_path=learning_db_path)
                after_run = store.get_run(run_id)
                after_view = view_of(store, after_run)
                applied = consequences(before_view, before, after_view,
                                       month_state(store, after_run), ReadPlan(reader={}))
            result.update({
                "documents": document_report(plan, commit["written"], before_view, after_view),
                "applied": applied,
                "written": commit["written"],
                "display_restored": commit["restored"],
                "gone": commit["gone"],
                "rematch": commit["rematch"],
            })
        if plan.cost_usd is not None:
            result["cost_usd"] = plan.cost_usd
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id,
                result=json.dumps(result, default=str), updated_at=_now(),
            )
    except RunInputError as exc:
        with RunStore(db_path) as store:
            store.set_job_status(job_id, JOB_ERROR, error=f"{exc.code}: {exc.message}",
                                 updated_at=_now())
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        log.exception("item 252: applying the senders' notes failed on %s", run_id)
        with RunStore(db_path) as store:
            store.set_job_status(job_id, JOB_ERROR, error=str(exc), updated_at=_now())
