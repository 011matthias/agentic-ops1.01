"""FastAPI app: the JSON API behind the Lovable SPA front end.

`create_app(data_root)` builds the application; `serve.py` launches it
with uvicorn. Every route opens a short-lived `RunStore` against the
SQLite db under `data_root`; uploads and generated exports live under
`data_root/runs/<run_id>/`.

The browser UI is the SPA (repo `brisken-expense-review`, Lovable-hosted);
the server-rendered Jinja workbench was retired 2026-07-22 once the SPA
reached parity. This app serves JSON plus file downloads only:

    POST /api/login                bearer-token login
    GET  /healthz                  health probe
    POST /api/intakes              upload a document set (queue, run nothing)
    POST /api/intakes/{id}/files   replace files on a queued intake
    POST /api/intakes/{id}/run     run the pipeline on a stored intake
    POST /api/runs                 run a reconciliation from an upload
    GET  /api/runs/{id}            the review render model
    POST /api/runs/{id}/...        review mutations: decisions,
                                   decisions/confirm-matched, categories,
                                   manual-match, disposition,
                                   duplicates/resolve, publish, unpublish,
                                   forget, commit-memory
    PUT  /api/runs/{id}/charges/{tx}/category   a category on a CHARGE row
                                   (no receipt needed; item 109)
    GET/PUT /api/settings          §16 export policy
    POST /api/fx/poll              poll the daily FX rates now (note #79)
    GET  /api/compare              across-runs bucket deltas
    GET  /api/memory               learned facts; POST /api/memory/forget,
                                   POST /api/memory/reset to correct them
    GET  /api/operator/state       polled by the dev-side notifier
    POST /api/feedback             anchored reviewer note
    GET  /feedback.jsonl           raw notes download
    GET  /jobs/{job_id}            background-run poll
    GET  /runs/{id}/report.xlsx / zoho.csv / reconciled.csv /
         statement-categorized.xlsx    file downloads with edits applied

Receipt-first expense mode (behind EXPENSE_RECON_RECEIPT_FIRST; every
route 404s while the flag is unset):

    POST /api/expense-batches      upload receipts -> statement-less batch
    GET  /api/expense-batches      list batches; /{id} the expense grid
    POST /api/expense-batches/{id}/receipts   add receipts mid-month
    POST /api/expense-batches/{id}/statement  month-end: attach statement,
         reconcile the batch (the run then serves the workbench)
    PUT  /api/runs/{id}/expenses/{doc}           one field edit {field,value}
    PUT  /api/runs/{id}/expenses/{doc}/entity    per-expense legal entity
    POST /api/runs/{id}/expenses                 manual expense add
    DELETE /api/runs/{id}/expenses/{doc}         soft-remove an expense
    GET  /runs/{id}/expenses.csv   Zoho Expenses import CSV, edits applied
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Body,
    FastAPI,
    Form,
    Query,
    Request,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..batch_period import month_from_label
from ..cards import card_to_dict, effective_cards, normalize_cards_setting
from ..cards_provision import card_by_key, load_cards
from ..error_codes import Refusal, code_of, fields_of  # Refusal: item 104
from ..ingest.expense_report_images import render_receipt_page
from ..learning import CATEGORY_SOURCE_HUMAN, CATEGORY_SOURCE_INHERITED
from ..receipt_render import (
    ReceiptRenderError,
    guess_media_type,
    is_pdf,
    page_count,
    render_page_png,
)
from .serialize import receipt_from_dict
from . import fx_daily_rates
from .service import (
    BATCH_TYPE_COMPANY,
    BATCH_TYPE_TRIP,
    DEFAULT_EXPENSE_COLUMN_MAP,
    EXPENSE_CATEGORY_FIELDS,
    EXPENSE_HEADER_FIELDS,
    MODE_EXPENSE_GENERATION,
    PreparedExpenseBatch,
    PreparedRun,
    cards_seen_but_undefined,
    prepare_row_card_fix,
    RunForm,
    RunInputError,
    add_receipts_to_expense_batch,
    apply_expense_edits,
    assign_batch_cards,
    attach_emailed_receipt,
    available_entities,
    baseline_receipts,
    batch_list_summary,
    build_card_status,
    build_cost_center_totals,
    build_expense_report,
    build_reconciliation_report,
    build_expense_view,
    build_memory_view,
    build_view,
    bulk_decisions,
    compare_runs,
    batch_type,
    claim_trip_batch_slot,
    create_expense_batch,
    create_intake,
    delete_trip_entity,
    execute_expense_batch,
    execute_run,
    execute_statement_attach,
    find_trip_batch,
    has_statement,
    REMATCH_LOG_KEY,
    rematch_pending,
    is_trip_batch,
    release_trip_batch_slot,
    prepare_statement_attach,
    reread_statements,
    forget_memory_vendor,
    ingest_receipts_folder_into_run,
    matched_autopick_decisions,
    move_expense_to_month,
    ready_confirm_pairs,
    prepare_intake_run,
    prepare_run,
    rematch_after_change,
    owe_trip_month_rematches,
    rematch_trip_months,
    relabel_borrowed_sources,
    refresh_batch_master_data,
    regenerate_expense_export,
    regenerate_reconciled,
    regenerate_report,
    regenerate_writeback,
    regenerate_zoho,
    replace_intake_files,
    reset_memory,
    restore_set_aside_file,
    run_mode,
    sync_claim_for_decision,
    trip_view,
    validate_expense_field,
    validate_manual_match,
    validate_trip_fields,
    clear_receipt_settled_outside,
    set_receipt_settled_outside,
)
from .service import (  # item 70
    EXPENSE_MATCH_FIELDS,
    category_edit_account,
    category_edit_receipt,
    recategorize_after_entity_change,
)
from .service import (  # item 88
    MEMORY_TRIGGER_BUTTON,
    MEMORY_TRIGGER_PUBLISH,
    commit_month_memory,
)
from .service import (  # item 163
    MEMORY_TABLE_SURFACE,
    plan_month_memory,
    undo_memory_commit,
)
from .service import confirm_expense_category  # note #62
from .service import set_charge_category  # item 109
from .service import attach_expense_card_tabs, attach_run_card_tabs  # item 138
from .service import TURN_DECIDE, confirm_matched_pairs  # item 101
from .month_readiness import (  # items 99 + 100
    PUBLISH_MONTH_NOT_COMPLETE,
    PUBLISH_NO_STATEMENT,
    PUBLISH_NOT_A_MONTH,
    not_complete_detail,
    readiness_of,
)
from ..category_vocabulary import (
    gl_account_options,
    gl_revision,
    recognize as recognize_category,
)
from ..matching.types import EXPENSE_CATEGORIES
from ..cost_centers import (
    CostCenterRegistry,
    normalize_cost_centers_setting,
)
from ..merchant_registry import normalize_merchants_setting
from .store import (
    INTAKE_PROCESSING,
    INTAKE_READY,
    INTAKE_RECEIVED,
    JOB_DONE,
    JOB_ERROR,
    RETIRED_SETTINGS_KEYS,
    SETTINGS_DERIVED_KEYS,
    SETTINGS_MAP_KEYS,
    SETTINGS_WRITABLE_KEYS,
    STATUS_CONFIRMED,
    STATUS_PENDING,  # item 104: the undo target of a first verdict
    VALID_DISPOSITIONS,
    VALID_DUP_RESOLUTIONS,
    VALID_STATUSES,
    RunStore,
    without_retired_entity_keys,
    without_retired_settings_keys,
)
from . import auth, machine, ratelimit
from . import decision_history as dh  # item 104
from .service import charge_category_key  # item 104

log = logging.getLogger("expense_recon.web")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# A value no comparison can match by accident: `_current_history_value`
# returns it when the row's present value cannot be read, and the undo
# route turns that into a refusal. A plain None would have compared equal
# to "this row has no value", which is a real state and must stay undoable.
_HISTORY_UNREADABLE = object()


def _history_who(request) -> str:
    """Which named person is making this change.

    `request.state.operator` is the label inside the signed session token,
    set by the gate middleware: "criss", "matthias", or "operator" for the
    legacy shared code and the gate-off local case. This is deliberately NOT
    `_operator()`, which reads the SERVER's environment and therefore answers
    the same name whoever is logged in; that is the confusion item 104 names
    (Criss's feedback notes read "operator" while the developer's read
    "matthias"). A request that somehow carries no state falls back to the
    unnamed label rather than failing the write.
    """
    return getattr(getattr(request, "state", None), "operator", None) or dh.UNNAMED


def _decision_entry(run_id, tx_id, before, status, chosen, *, who, at, trigger):
    """One history line for a decision write, or None when nothing moved.

    `before` is the row's `Decision` as it stood before the write (None when
    the charge had no row at all). Reading it BEFORE calling `set_decision`
    is the whole trick: the upsert destroys the old value, so a caller that
    records afterwards can only ever say what the new value is.
    """
    old = None
    if before is not None:
        old = dh.decision_value(before.status, before.chosen_document_id)
    return dh.make_entry(
        run_id=run_id, row_key=tx_id, row_kind=dh.ROW_CHARGE,
        field=dh.FIELD_DECISION,
        old=old, new=dh.decision_value(status, chosen),
        who=who, at=at, trigger=trigger,
    )


def _append_history(store, entries) -> None:
    """Append the lines that carry a change; silence otherwise.

    Wrapped so a history failure can never take down the verdict that was
    already written and already answered for. A month whose ledger lost a
    line is a smaller harm than a confirm that 500s after the decision
    landed, and the miss is visible in the log.
    """
    real = [e for e in entries if e]
    if not real:
        return
    try:
        store.append_history(real)
    except Exception:  # pragma: no cover - defensive
        log.exception("decision history append failed for %s", real[0]["run_id"])


def _current_history_value(store, run, entry_row):
    """What the row holds RIGHT NOW, in the same shape the line recorded.

    Used by the undo guard: a line may only be put back while the row still
    holds exactly what that line left there. Returns `_HISTORY_UNREADABLE`
    when the current value cannot be established, which the caller treats as
    a conflict rather than as agreement.
    """
    run_id = entry_row["run_id"]
    field = entry_row["field"]
    row_key = entry_row["row_key"]
    if field == dh.FIELD_DECISION:
        current = store.get_decisions(run_id).get(row_key)
        if current is None:
            return None
        return dh.decision_value(current.status, current.chosen_document_id)
    if field == dh.FIELD_DISPOSITION:
        current = store.get_decisions(run_id).get(row_key)
        return getattr(current, "disposition", None) if current else None
    if field in (dh.FIELD_CHARGE_CATEGORY, dh.FIELD_RECEIPT_CATEGORY):
        detail = dh.decode(entry_row.get("detail")) or {}
        document_id = detail.get("document_id")
        line_index = detail.get("line_index")
        if document_id is None or line_index is None:
            return _HISTORY_UNREADABLE
        override = store.get_category_overrides(run_id).get(
            (document_id, int(line_index))
        )
        return _category_value(override)
    if field == dh.FIELD_DUPLICATE:
        return store.get_duplicate_resolutions(run_id).get(row_key)
    return _HISTORY_UNREADABLE


def _receipt_category_entries(
    run_id, document_id, before_map, after_map, *, who, at, trigger
):
    """One line per LINE of this receipt whose category actually moved.

    Used where the write happens inside a service call that this route does
    not want to reach into: snapshot the override map before, call it, read
    the map after, and let `make_entry` drop every line that did not move.
    A confirm that ratifies eight lines the reviewer already agreed with
    records nothing, which is correct.
    """
    keys = {
        key for key in set(before_map) | set(after_map)
        if key[0] == document_id
    }
    return [
        dh.make_entry(
            run_id=run_id, row_key=document_id, row_kind=dh.ROW_RECEIPT,
            field=dh.FIELD_RECEIPT_CATEGORY,
            old=_category_value(before_map.get(key)),
            new=_category_value(after_map.get(key)),
            who=who, at=at, trigger=trigger,
            detail={
                "document_id": key[0], "line_index": key[1],
                "old_category_source": _old_category_source(before_map.get(key)),
            },
        )
        for key in sorted(keys, key=lambda k: k[1])
    ]


def _old_category_source(override) -> str:
    """Whose category an override row held before an edit replaced it.

    Recorded in a history line's `detail` so an undo puts the provenance back
    with the value. It cannot live in `_category_value`: the undo guard
    compares that value for equality, and a row differing only in provenance
    would read as superseded. A row with no provenance, and an absent row,
    both read human, the same back-compat rule the column itself uses."""
    return (override or {}).get("category_source") or CATEGORY_SOURCE_HUMAN


def _category_value(override) -> dict | None:
    """A category override as a comparable value.

    An absent row and a row holding nothing are both `None`. A row holding
    EITHER half is its own value: an account with no category is a real
    stored state and a real reviewer decision.

    That distinction is load-bearing twice over, and collapsing it cost both.
    An account-only pick recorded no line at all (nothing seemed to have
    moved), and, worse, the undo guard compares this value, so a row that had
    since moved to "account, no category" compared EQUAL to a stale line's
    recorded `None` -- the undo was allowed and overwrote the account pick,
    which is exactly the harm `history_superseded` exists to prevent.
    """
    if not override:
        return None
    category = override.get("category") or None
    account = override.get("zoho_account") or None
    if category is None and account is None:
        return None
    return {"category": category, "zoho_account": account}


_HISTORY_UNDO_REFUSALS = {
    "history_already_undone": "this change has already been put back",
    "history_not_undoable": (
        "this change is recorded but cannot be put back here: reverse a "
        "duplicate ruling by making the opposite ruling on the group, which "
        "re-matches the month, and a first disposition has no earlier value "
        "to restore"
    ),
    "history_superseded": (
        "this row has changed since; putting this back would throw away the "
        "later change"
    ),
    "history_no_previous_value": "there was no earlier value to put back",
}

# Refusals from the write itself that mean "someone else got there": the same
# condition the original confirm answers 409 for, so the undo answers 409 too.
_HISTORY_UNDO_CONFLICT_CODES = frozenset({
    "receipt_settled_elsewhere",
    "receipt_just_settled",
    "receipt_claimed_elsewhere",
})


def _apply_history_undo(store, run, entry_row, old, now):
    """Write the old value back. Returns (error, restored_value).

    `restored_value` is what the row actually holds afterwards, which is not
    always `old`: a decision line whose `old` is None recorded the very first
    verdict on a charge that had no row, and the nearest thing to "no row" a
    route can write is `pending` with no receipt. That is exactly what the
    app already calls undoing a confirm (re-POST the row pending), so the
    undo line records `pending`, not a `None` it did not restore.
    """
    run_id = entry_row["run_id"]
    field = entry_row["field"]
    row_key = entry_row["row_key"]
    if field == dh.FIELD_DECISION:
        status = (old or {}).get("status") or STATUS_PENDING
        chosen = (old or {}).get("chosen_document_id")
        # R4 again: putting a confirmed pair back has to pass the same
        # cross-run claim check the original confirm passed, or an undo
        # could settle a receipt another month now holds.
        conflict = sync_claim_for_decision(store, run, row_key, status, chosen, now)
        if conflict is not None:
            return conflict, None
        store.set_decision(run_id, row_key, status, chosen, now)
        return None, dh.decision_value(status, chosen)
    if field == dh.FIELD_DISPOSITION:
        # `dh.undoable` already refused a first disposition, so `old` is a
        # real verdict here; there is no "no previous value" case left.
        store.set_disposition(run_id, row_key, old, now)
        return None, old
    if field == dh.FIELD_CHARGE_CATEGORY:
        err = set_charge_category(
            store, run, row_key,
            (old or {}).get("category"), (old or {}).get("zoho_account"), now,
        )
        if err is not None:
            return err, None
        return None, old
    if field == dh.FIELD_RECEIPT_CATEGORY:
        detail = dh.decode(entry_row.get("detail")) or {}
        document_id = detail.get("document_id")
        line_index = detail.get("line_index")
        if document_id is None or line_index is None:
            # Unreachable in practice: `_current_history_value` returns the
            # unreadable sentinel on the same condition and the route 409s
            # first. Kept as a refusal rather than an exception because a
            # ledger read must never 500.
            return Refusal(
                "this line does not say which receipt line it changed",
                code="history_no_previous_value",
            ), None
        store.set_category_override(
            run_id, document_id, int(line_index),
            (old or {}).get("category"), (old or {}).get("zoho_account"), now,
            # Restore the provenance the row had, not the provenance of the
            # edit being undone. A line that was carrying the model's guess
            # before an edit goes back to carrying it, and an undo can
            # therefore never promote a guess to her statement.
            category_source=(
                detail.get("old_category_source") or CATEGORY_SOURCE_HUMAN
            ),
        )
        return None, old
    return _HISTORY_UNDO_REFUSALS["history_not_undoable"], None


def _trip_range(start: object, end: object):
    """One inclusive `(start, end)` date pair, or None when either side is
    unreadable. A trip whose stored dates cannot be parsed selects no
    months rather than raising inside a route."""
    try:
        return (
            date.fromisoformat(str(start)[:10]),
            date.fromisoformat(str(end)[:10]),
        )
    except ValueError:
        return None


def _sync_trip_batch_label(store, batch, old_name: str, new_name: str) -> None:
    """Carry a trip rename onto its batch label (R4.1).

    The batch is labelled from the trip's name at CREATION and nothing
    updated it afterwards, so a rename left three surfaces naming a trip
    that no longer went by that name: the batch's own header, the delete
    confirm (which is keyed on the label), and the `settled_by` badge on
    every month borrowing from it. Only the leading occurrence of the old
    name is replaced, so an operator's own suffix (" receipts") survives;
    a label that does not start with the old name is left alone rather
    than guessed at."""
    old, new = str(old_name).strip(), str(new_name).strip()
    label = str(batch.label or "")
    if not old or not new or not label.startswith(old):
        return
    store.set_run_label(batch.run_id, new + label[len(old):])
    # A borrowing month renders its own stored copy of the lender's label,
    # so the badge stays on the old name until those copies move too. The
    # stored label is the TRIP's name, not the batch's, which is what the
    # badge reads ("Settled by trip {name}").
    relabel_borrowed_sources(store, batch.run_id, new)


def _not_found(message: str, code: str) -> JSONResponse:
    return JSONResponse({"error": message.lower(), "code": code}, status_code=404)


def _refused(message, status: int = 400, **extra) -> JSONResponse:
    """A refusal whose English sentence carries its own code and named
    values (a `Refusal` from the service layer), answered with both
    (item 130). A plain string still answers, under a generic code."""
    return JSONResponse(
        {"error": str(message), "code": code_of(message, "request_refused"),
         **fields_of(message), **extra},
        status_code=status,
    )


def _input_refused(exc: RunInputError) -> JSONResponse:
    """A user-fixable input problem on the wire (item 130): the English
    sentence, its stable code, and the named values the sentence used."""
    return JSONResponse(
        {"error": exc.message, "code": exc.code, **exc.fields}, status_code=400
    )


def _refusal_response(result: dict, default_status: int = 400) -> JSONResponse:
    """A service-layer refusal dict on the wire (item 130). The service keeps
    the HTTP status under an int `code`, which never leaves the server; its
    `error_code` becomes the body's `code`, beside the unchanged English
    `error` and whatever named values the refusal carries."""
    body = dict(result)
    status = body.pop("code", default_status)
    body["code"] = body.pop("error_code", None) or "request_refused"
    return JSONResponse(body, status_code=status)


def _operator() -> str | None:
    return (
        os.environ.get("EXPENSE_RECON_OPERATOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
    )


def _receipt_first_on() -> bool:
    """Receipt-first expense mode (Dirk's note #1). Off by default so a
    deploy changes nothing for Criss until the flag flips (Phase 8). Read
    per request, never cached, so a restartless env change takes effect."""
    return os.environ.get("EXPENSE_RECON_RECEIPT_FIRST") == "1"


def _run_id_from_path(page: str) -> str | None:
    """The run id when a feedback note was left on a run page, else None.

    The SPA routes statement runs as /runs/{id} and expense batches as
    /expenses/{id} (an expense batch IS a run row); both attribute. The
    /expenses/new create form carries no id.
    """
    parts = page.strip("/").split("/")
    if len(parts) >= 2 and parts[0] in ("runs", "expenses") and parts[1] and parts[1] != "new":
        return parts[1][:64]
    return None


def _run_job(db_path: Path, job_id: str, prepared: PreparedRun) -> None:
    """Run a prepared reconciliation off the request (PR F).

    Starlette runs this sync function in a worker thread, so the event loop
    stays free to serve the polling page. It opens its own RunStore (a
    SQLite connection is per-thread) and records the outcome in the durable
    `jobs` table the poller reads -- durable because a Fly scale-to-zero
    stop can kill this thread; the startup sweep then marks the job
    interrupted instead of leaving an eternal spinner.
    """
    try:
        with RunStore(db_path) as store:
            run_id = execute_run(
                store,
                prepared,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
            if prepared.intake_id is not None:
                store.set_intake_status(
                    prepared.intake_id, INTAKE_RECEIVED, updated_at=_now_iso()
                )


def _run_folder_job(
    db_path: Path, job_id: str, run_id: str, staging_dir: Path
) -> None:
    """Ingest + re-match a bulk receipts-folder upload against an existing run
    (2026-07-27), off the request in a worker thread like `_run_job`. Vision
    OCR over a folder is minutes of work, so it never runs synchronously; the
    SPA polls GET /jobs/{id} and reloads the run when it flips to done. The
    staging dir (raw uploads spooled by the endpoint) is removed either way."""
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                return
            ingest_receipts_folder_into_run(
                store, run, staging_dir, _now_iso(),
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _claim_pooled_quietly(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
) -> None:
    """Drain the month pool, never raising at the caller. Claiming is a
    convenience on top of whatever just happened (a batch created, a month
    renamed, a boot); a failure there must not fail that."""
    try:
        from .intake_mail import claim_pooled

        result = claim_pooled(db_path, learning_db_path, data_root)
        if result["claimed"] or result["failed"]:
            log.info(
                "pool claim: %d claimed, %d failed, %d still pooled",
                result["claimed"], result["failed"], result["still_pooled"],
            )
    except Exception:  # noqa: BLE001 - a claim never breaks its trigger
        log.warning("pool claim failed", exc_info=True)


def _resume_rematches_quietly(
    db_path: Path, learning_db_path: Path | None,
) -> None:
    """Item 113: re-pair every month still owing a re-match, never raising.
    A failure stays recorded on the month's mark for the next attempt."""
    try:
        from .service import resume_pending_rematches

        done = resume_pending_rematches(db_path, learning_db_path)
        if done:
            log.info("boot re-pair: %d month(s) re-matched", len(done))
    except Exception:  # noqa: BLE001 - boot re-pair is best-effort
        log.warning("boot re-pair failed", exc_info=True)


def _run_expense_job(
    db_path: Path, job_id: str, prepared: PreparedExpenseBatch,
    learning_db_path: Path | None = None, data_root: Path | None = None,
) -> None:
    """Run a prepared expense batch (OCR + categorization) off the request,
    the receipt-first twin of `_run_job`. Same durable jobs-table contract:
    the SPA polls GET /jobs/{id} until done/error.

    When the batch's label names a month, the pool is drained into it once
    the rows are committed: creating "July 2026" is what makes July's
    waiting mail arrive, with no second click."""
    pending_trip = str((prepared.cfg or {}).get("trip_id") or "")
    try:
        with RunStore(db_path) as store:
            run_id = execute_expense_batch(
                store,
                prepared,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
                learning_db_path=learning_db_path,
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
        return
    finally:
        # The trip's creation slot opens once the outcome is durable:
        # committed => find_trip_batch sees the row; failed => no row and
        # the next create may try again.
        if pending_trip:
            release_trip_batch_slot(pending_trip)
    # Inline, not threaded: this already runs off the request, and the
    # claim must not start before the batch rows are committed.
    if data_root is not None and month_from_label(prepared.label) is not None:
        _claim_pooled_quietly(db_path, learning_db_path, data_root)


def _run_batch_receipts_job(
    db_path: Path, job_id: str, run_id: str, staging_dir: Path,
    learning_db_path: Path,
) -> None:
    """Incremental receipt-add on an expense batch, off the request (OCR is
    slow). Staging dir is consumed and removed either way."""
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                return
            add_receipts_to_expense_batch(
                store, run, staging_dir, _now_iso(),
                learning_db_path=learning_db_path,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
            )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
            if store.get_run(run_id) is None:
                # The month was deleted between our locked write and this
                # stamp (the delete cascade purges jobs by run_id, which
                # was NULL until now). Don't leave a done-job pointing at
                # a gone run; if the delete lands after this check instead,
                # its cascade removes the row we just stamped.
                store.set_job_status(
                    job_id, JOB_ERROR, error="batch deleted",
                    updated_at=_now_iso(),
                )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _run_receipts_drop_job(
    db_path: Path, job_id: str, staging: Path, month_override: str,
    learning_db_path: Path | None, data_root: Path,
) -> None:
    """Route a dropped pile of receipts to their months, off the request
    (per-file vision). The per-file ledger lands in the job row's
    ``result``, so GET /jobs/{id} is where the page reads what filed
    where, what needs a month picked, and what was rejected."""
    from .intake_mail import route_dropped_receipts

    def _stage(name: str) -> None:
        # A fresh short-lived connection per stage write: the routing runs
        # for minutes and opens its own stores, so nothing long-lived may
        # sit beside them.
        with RunStore(db_path) as store:
            store.set_job_stage(job_id, name, _now_iso())

    try:
        outcome = route_dropped_receipts(
            db_path, learning_db_path, data_root, staging,
            month_override, on_stage=_stage,
        )
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_DONE, result=json.dumps(outcome),
                updated_at=_now_iso(),
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )
    finally:
        _discard_drop(staging)  # item 114: the folder and its sidecar


def _resolve_duplicate_rematch(
    db_path: Path, learning_db_path: Path, run_id: str
) -> dict | None:
    """Re-match a reconciling month after a duplicate resolution (item 56).

    The resolution decides the matcher's pool: an unresolved or confirmed
    group is collapsed to one candidate, an `ignore` group is not. Without
    this the ruling would be recorded and inert until the month's next
    change, which is exactly the "allowed but inert" failure
    `rematch_after_change` exists to prevent. Its own error contract
    applies: a failure rides back in the reply, it never fails the
    resolution that is already written.
    """
    with RunStore(db_path) as store:
        return rematch_after_change(
            store, run_id,
            learning_db_path=learning_db_path, trigger="duplicates",
        )


def _expense_edit_rematch(
    db_path: Path, learning_db_path: Path, run_id: str
) -> dict | None:
    """Re-match a reconciling month after an expense edit that can change
    what pairs with what (item 70).

    The five expense-edit routes stayed closed on a statement month because
    a re-match bakes the overlay into the pool, so an edit surface was only
    worth reopening together with the re-match the edit has to trigger.
    This is that re-match. Same contract as every other living-month
    caller: it runs AFTER the edit is committed and outside any batch-lock
    span, and a failure rides back in the reply instead of failing an edit
    that is already written. Returns None on a month with no statement.
    """
    with RunStore(db_path) as store:
        return rematch_after_change(
            store, run_id,
            learning_db_path=learning_db_path, trigger="expense_edit",
        )


def _run_reread_statements_job(
    db_path: Path, job_id: str, run_id: str, learning_db_path: Path,
) -> None:
    """Rebuild a month's charges from its stored statement files and
    re-match, off the request (the match can take minutes with the LLM).
    Same job shape as the attach so the SPA's poller reads it unchanged."""
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                return
            settings = store.get_settings()
            result = reread_statements(
                store, run,
                settings=settings, now_iso=_now_iso(),
                learning_db_path=learning_db_path,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
            )
            warnings = [
                result[k] for k in ("entity_mismatch", "statement_advisory")
                if result.get(k)
            ]
            if warnings:
                store.set_job_stage(
                    job_id, f"warning: {'; '.join(warnings)}", _now_iso()
                )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )


def _run_attach_statement_job(
    db_path: Path, job_id: str, run_id: str, stmt_name: str,
    column_map: dict | None, form: RunForm, learning_db_path: Path,
    upload_name: str = "",
) -> None:
    """Graduate an expense batch into a reconciliation, off the request
    (statement load + match + judgment can take minutes with the LLM)."""
    try:
        with RunStore(db_path) as store:
            run = store.get_run(run_id)
            if run is None:
                store.set_job_status(
                    job_id, JOB_ERROR, error="run not found",
                    updated_at=_now_iso(),
                )
                return
            settings = store.get_settings()
            result = execute_statement_attach(
                store, run,
                stmt_name=stmt_name, column_map=column_map, form=form,
                settings=settings, now_iso=_now_iso(),
                learning_db_path=learning_db_path,
                on_stage=lambda s: store.set_job_stage(job_id, s, _now_iso()),
                upload_name=upload_name,
            )
            # Warnings must survive the job round-trip: park them on the
            # job's stage-free error-less row via the stage field. Both are
            # about a month that reconciled successfully and still needs a
            # human look, so they ride the same channel; `statement_advisory`
            # is the append-specific one (PR 2b-2b-2).
            warnings = [
                result[k] for k in ("entity_mismatch", "statement_advisory")
                if result.get(k)
            ]
            if warnings:
                store.set_job_stage(
                    job_id, f"warning: {'; '.join(warnings)}", _now_iso()
                )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
            )


# Item 114: a drop's files are on the volume (/data/drops/<job>) before its
# job starts, so a restart mid-drop need not cost the operator a second
# drop. The request writes a sidecar beside the folder carrying what the
# folder alone cannot say (the operator's month pick) and how often the drop
# was resumed. The boot pass re-runs an interrupted drop ONCE under its own
# job id (content dedupe skips files that landed before the kill), and
# deletes drop folders whose job is already over. (A month folder a kill
# leaves mid-create, before its row commits, is older than this and not
# swept here.)
_DROP_RESUME_LIMIT = 1
_DROP_INTERRUPTED = "interrupted by a server restart"


def _drop_sidecar(staging: Path) -> Path:
    return staging.with_name(staging.name + ".json")


def _write_drop_sidecar(staging: Path, meta: dict) -> None:
    side = _drop_sidecar(staging)
    tmp = side.with_name(side.name + ".tmp")
    tmp.write_text(json.dumps(meta), encoding="utf-8")
    os.replace(tmp, side)


def _discard_drop(staging: Path) -> None:
    shutil.rmtree(staging, ignore_errors=True)
    for leftover in (_drop_sidecar(staging),
                     staging.with_name(staging.name + ".json.tmp")):
        try:
            leftover.unlink()
        except OSError:
            pass


def _read_drop_sidecar(staging: Path) -> dict | None:
    """The sidecar, or None when it is missing or cannot be trusted (then
    the month pick is unknown and re-running could file into the wrong
    month)."""
    from .intake_mail import valid_month_key

    try:
        meta = json.loads(_drop_sidecar(staging).read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            return None
        meta["resumed"] = int(meta.get("resumed") or 0)
        month = str(meta.get("month") or "")
        if month and not valid_month_key(month):
            return None
        meta["month"] = month
        return meta
    except (OSError, TypeError, ValueError):
        return None


def _give_up_drop(db_path: Path, staging: Path, error: str) -> None:
    try:
        with RunStore(db_path) as store:
            store.set_job_status(
                staging.name, JOB_ERROR, error=error, updated_at=_now_iso()
            )
    except Exception:  # noqa: BLE001 - the folder still goes
        log.warning("could not record drop %s as given up", staging.name,
                    exc_info=True)
    _discard_drop(staging)


def resume_interrupted_drops(db_path: Path, data_root: Path) -> list[tuple]:
    """Boot pass for item 114; runs after the stale-job sweep and before the
    app serves. Returns ``(job_id, staging, month_override)`` for each drop
    to re-run, marked running (stage "waiting to resume after a server
    restart") so the page polling it never reads the sweep's "run it
    again". The resume COUNT is not touched here: `_resume_drops_quietly`
    bumps it just before a drop actually runs, so a restart that lands
    while drops still wait in the queue gives up only the one that ran.
    A drop that ran once after a restart and was cut off again is given up
    (a drop that kills the machine must not kill it every boot). A folder
    with no interrupted job, or no trustworthy sidecar, is deleted; its job
    keeps what it already says. A ``drop-add-*`` copy left inside a month by
    a killed add is deleted too: its source is the drop folder, and nothing
    is mid-add at boot. Each folder is handled on its own, so one that
    fails never strands the others."""
    from .store import JOB_RUNNING

    drops = Path(data_root) / "drops"
    resume: list[tuple] = []
    try:
        with RunStore(db_path) as store:
            runs = store.list_runs()
        for run in runs:
            work = Path(run.work_dir) if run.work_dir else None
            if work is not None and work.is_dir():
                for stale in work.glob("drop-add-*"):
                    shutil.rmtree(stale, ignore_errors=True)
    except Exception:  # noqa: BLE001 - a copy left behind costs disk only
        log.warning("drop-add cleanup at boot failed", exc_info=True)
    if not drops.is_dir():
        return resume
    for staging in sorted(p for p in drops.iterdir() if p.is_dir()):
        try:
            with RunStore(db_path) as store:
                job = store.get_job(staging.name)
                interrupted = (
                    job is not None
                    and job.get("status") == JOB_ERROR
                    and not job.get("result")
                    and _DROP_INTERRUPTED in str(job.get("error") or "")
                )
                meta = _read_drop_sidecar(staging)
                if not interrupted or meta is None:
                    _discard_drop(staging)
                    continue
                if meta["resumed"] >= _DROP_RESUME_LIMIT:
                    store.set_job_status(
                        staging.name, JOB_ERROR,
                        error=(
                            "interrupted by a server restart again after it "
                            "was resumed; drop the files again"
                        ),
                        updated_at=_now_iso(),
                    )
                    _discard_drop(staging)
                    continue
                store.set_job_status(
                    staging.name, JOB_RUNNING,
                    stage="waiting to resume after a server restart",
                    updated_at=_now_iso(),
                )
            resume.append((staging.name, staging, meta["month"]))
        except Exception:  # noqa: BLE001 - one folder never strands the rest
            log.warning("drop %s could not be resumed", staging.name,
                        exc_info=True)
            _give_up_drop(
                db_path, staging,
                "could not be resumed after a server restart; "
                "drop the files again",
            )
    for side in drops.glob("*.json"):
        if not side.with_name(side.name[: -len(".json")]).is_dir():
            side.unlink(missing_ok=True)
    return resume


def _resume_drops_quietly(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
    resumed: list[tuple],
) -> None:
    """Re-run the drops `resume_interrupted_drops` marked, one after the
    other, through the same job runner a fresh drop uses. The resume count
    is written right before each run starts (the crash-loop guard), and a
    drop that raises is given up without stopping the next."""
    for job_id, staging, month in resumed:
        try:
            meta = _read_drop_sidecar(staging)
            if meta is None or not staging.is_dir():
                continue
            meta["resumed"] += 1
            _write_drop_sidecar(staging, meta)
            with RunStore(db_path) as store:
                store.set_job_stage(
                    job_id, "resuming after a server restart", _now_iso()
                )
            log.info("resuming drop %s after a restart", job_id)
            _run_receipts_drop_job(
                db_path, job_id, staging, month, learning_db_path, data_root,
            )
        except Exception:  # noqa: BLE001 - the next drop still runs
            log.warning("resumed drop %s failed", job_id, exc_info=True)
            _give_up_drop(
                db_path, staging,
                "could not be resumed after a server restart; "
                "drop the files again",
            )


# Upper bound on one bulk-decision call. A month is ~100 charges, so this
# is far above any real batch; it exists so a malformed client cannot
# open a huge write transaction.
_BULK_DECISION_LIMIT = 1000


def create_app(data_root: str | Path | None = None) -> FastAPI:
    data_root_path = Path(
        data_root or os.environ.get("EXPENSE_RECON_WEB_DATA", "recon-web-data")
    ).resolve()
    data_root_path.mkdir(parents=True, exist_ok=True)
    db_path = data_root_path / "recon-web.sqlite"

    app = FastAPI(title="Brisken Expense Reconciliation")
    app.state.data_root = data_root_path
    app.state.db_path = db_path
    # Durable cross-run memory (Phase 2). Separate db from the per-run web
    # state: runs come and go, learned facts persist across months.
    app.state.learning_db_path = data_root_path / "learning.sqlite"

    # Item 130: the framework's own refusals carry a code like every other
    # refusal. A request the route signature cannot bind (422) and a path or
    # method no route serves (404 / 405) keep FastAPI's `detail` for any
    # reader of it, and gain the `error` sentence and the `code` the SPA
    # translates.
    @app.exception_handler(RequestValidationError)
    async def _validation_refused(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {"error": "the request is missing a field, or one has the wrong "
                      "type",
             "code": "validation_failed",
             "detail": jsonable_encoder(exc.errors())},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_refused(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            {"error": str(exc.detail).lower(), "code": code,
             "detail": exc.detail},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    # Startup sweep: a job still `running` in the durable table was killed
    # by a restart (Fly scale-to-zero). Mark it interrupted and put its
    # intake back in the queue so the operator sees the truth, not a
    # spinner.
    with RunStore(db_path) as _store:
        for _intake_id in _store.sweep_stale_jobs(_now_iso()):
            if _intake_id is not None:
                _store.set_intake_status(
                    _intake_id, INTAKE_RECEIVED, updated_at=_now_iso()
                )
    # Mail-intake companion sweep: an inbound archive whose ingest job the
    # sweep above just marked interrupted flips back to a replayable held
    # status, so a Fly stop mid-OCR never leaves mail stranded as pending.
    try:
        from .intake_mail import (
            reconcile_interrupted,
            sweep_dismissed,
            sweep_retention,
        )

        reconcile_interrupted(db_path, data_root_path)
        # Retention floor (settings intake.retention_years, default 10y per
        # AO paragraph 147): expired inbound archives are deleted at boot,
        # which scale-to-zero makes a near-daily event.
        sweep_retention(db_path, data_root_path)
        # Item 122: archives the operator dismissed as junk, once they
        # have sat dismissed for intake.dismissed_purge_days. Inert by
        # default (0 = never); one settings write turns it on.
        sweep_dismissed(db_path, data_root_path)
    except Exception:  # noqa: BLE001 - reconcile must never block startup
        pass
    # Pool sweep: a month may have been created while this machine was
    # stopped (scale-to-zero), so mail can be waiting for a month that is
    # already open. Pre-scan for pooled mail first and start the thread
    # only when there is any — claiming does vision, and a boot with an
    # empty pool must cost nothing and start nothing.
    try:
        from .intake_mail import has_pooled_mail

        if has_pooled_mail(data_root_path):
            log.info("mail is waiting in the pool; claiming at boot")
            threading.Thread(
                target=_claim_pooled_quietly,
                args=(db_path, app.state.learning_db_path, data_root_path),
                daemon=True,
            ).start()
    except Exception:  # noqa: BLE001 - a claim never blocks startup
        pass
    # Item 113: a month whose re-match raised or was cut off by the last
    # restart still carries its owed-re-match mark; re-pair it now, off the
    # boot path (a re-match can call the model). Nothing owed starts nothing.
    try:
        with RunStore(db_path) as _store:
            _owed = any(
                rematch_pending(r) is not None for r in _store.list_runs()
            )
        if _owed:
            log.info("a month owes a re-match; re-pairing at boot")
            threading.Thread(
                target=_resume_rematches_quietly,
                args=(db_path, app.state.learning_db_path),
                daemon=True,
            ).start()
    except Exception:  # noqa: BLE001 - a re-pair never blocks startup
        pass
    # Item 114: a drop cut off by the last restart runs again from the files
    # already on the volume; leftovers of finished drops are deleted.
    try:
        _resumed_drops = resume_interrupted_drops(db_path, data_root_path)
        if _resumed_drops:
            threading.Thread(
                target=_resume_drops_quietly,
                args=(db_path, app.state.learning_db_path, data_root_path,
                      _resumed_drops),
                daemon=True,
            ).start()
    except Exception:  # noqa: BLE001 - a resume never blocks startup
        log.warning("drop resume at boot failed", exc_info=True)

    # Item 119: the nightly copy of the data folder to Brisken's own
    # SharePoint. OFF unless EXPENSE_RECON_BACKUP=1, so this deploy
    # changes nothing until the owner turns it on; `start_backup_thread`
    # answers None in that case and the attribute says so.
    try:
        from .backup import start_backup_thread

        app.state.backup = start_backup_thread(data_root_path)
    except Exception:  # noqa: BLE001 - a backup never blocks startup
        app.state.backup = None
        log.warning("backup scheduler could not start", exc_info=True)

    # Feedback note #79 (owner 2026-09-23): the daily FX reference rates,
    # polled from OpenTickers at boot and every 24 h. OFF unless
    # OPENTICKERS_API_KEY is set (a Fly secret); `start_poll_thread` answers
    # None in that case and the attribute says so. The first round also
    # backfills the days the live months span (once; the plan allows it).
    try:
        app.state.fx_poll = fx_daily_rates.start_poll_thread(db_path)
    except Exception:  # noqa: BLE001 - a rate poll never blocks startup
        app.state.fx_poll = None
        log.warning("fx poll could not start", exc_info=True)

    def open_store() -> RunStore:
        return RunStore(db_path)

    # --- Mail intake (the app's own mailbox) -----------------------------
    # Enabled only when EXPENSE_RECON_INTAKE_SMTP=1 (fly.toml). The SMTP
    # listener runs in this same machine so it shares /data and the store;
    # start/stop ride the app lifecycle. Fail-open: a listener that cannot
    # start never blocks the web app (senders' mail systems retry).
    app.state.intake_smtp = None

    @app.on_event("startup")
    async def _start_intake() -> None:
        from .smtp_server import start_intake_smtp

        app.state.intake_smtp = start_intake_smtp(
            db_path, app.state.learning_db_path, data_root_path
        )

    @app.on_event("shutdown")
    async def _stop_intake() -> None:
        controller = app.state.intake_smtp
        if controller is not None:
            try:
                controller.stop()
            except Exception:  # noqa: BLE001 - shutdown is best-effort
                pass
            app.state.intake_smtp = None

    # --- Password gate (hosted only) -------------------------------------
    # Active iff the operator code is set. Loopback/local use leaves it
    # unset and stays open; a public host MUST set it (this tool serves
    # financial data). Operator is the only role (owner 2026-07-22): an
    # authenticated session has the full surface. See auth.py.
    @app.middleware("http")
    async def require_login(request: Request, call_next):
        label = auth.DEFAULT_LABEL
        if auth.gate_enabled() and not auth.path_is_open(request.url.path):
            token = request.cookies.get(auth.COOKIE_NAME)
            role = auth.token_role(token)
            # The SPA has no cookie; it authenticates with the same signed
            # token in an Authorization: Bearer header. A 401 tells it to
            # clear the token and show its own login screen.
            if role is None:
                token = auth.bearer_token(request.headers.get("authorization"))
                role = auth.token_role(token)
            if role is None:
                return JSONResponse(
                    {"error": "authentication required",
                     "code": "unauthenticated"},
                    status_code=401,
                )
            label = auth.token_label(token) or auth.DEFAULT_LABEL
        request.state.role = auth.ROLE_OPERATOR
        # Which named operator code this session logged in with; "operator"
        # for the legacy shared code and the gate-off local case.
        request.state.operator = label
        return await call_next(request)

    # Cross-origin access for the SPA front end (Lovable-built React app)
    # and local dev. Auth is a Bearer token in the Authorization header,
    # never a cookie, so no ambient credentials cross the origin and a
    # scoped allow-list is safe. Added after the gate middleware so it
    # wraps it and answers the CORS preflight before the gate runs.
    # `expenses.brisken.com` is the SPA's own Brisken domain (2026-09-08),
    # listed literally rather than as a brisken.com wildcard: the domain
    # carries many unrelated hosts and only this one serves the front end.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"https://([a-z0-9-]+\.)*(lovable\.app|lovableproject\.com|lovable\.dev)"
            r"|https://expenses\.brisken\.com"
            r"|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?"
        ),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.post("/api/login")
    async def api_login(request: Request):
        """Token login for the SPA front end. Returns the same signed
        session token the cookie carries, for the client to send back as
        `Authorization: Bearer`. When the gate is disabled (local dev) every
        caller is the operator, mirroring the cookie login flow."""
        if not auth.gate_enabled():
            return JSONResponse({
                "token": auth.issue_token(auth.ROLE_OPERATOR),
                "role": auth.ROLE_OPERATOR,
                "operator": auth.DEFAULT_LABEL,
            })
        # One shared code is this app's entire security boundary, so an
        # attempt is throttled BEFORE the code is checked: per-caller with
        # a doubling lockout (bucketed by IPv6 /64, so one end site cannot
        # rotate addresses for fresh buckets), plus a global budget for the
        # distributed case. See web/ratelimit.py.
        caller = ratelimit.client_ip(request)
        now = time.time()
        with open_store() as store:
            verdict = ratelimit.evaluate(store, caller, now)
        if not verdict.allowed:
            return JSONResponse(
                ratelimit.denial_body(verdict),
                status_code=429,
                headers={"Retry-After": str(verdict.retry_after)},
            )
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - a malformed body is a client error
            body = {}
        code = str((body or {}).get("code", ""))
        label = auth.code_identity(code)
        with open_store() as store:
            if label is None:
                ratelimit.register_failure(store, caller, now)
            else:
                ratelimit.register_success(store, caller)
        if label is None:
            return JSONResponse(
                {"error": "invalid code", "code": "invalid_login_code"},
                status_code=401,
            )
        return JSONResponse({
            "token": auth.issue_token(auth.ROLE_OPERATOR, label),
            "role": auth.ROLE_OPERATOR,
            "operator": label,
        })

    @app.get("/healthz")
    def healthz():
        """Liveness, plus what this process IS (item 50) and how full its
        disk is (item 122).

        `status` is unchanged and still the only field a caller needs.
        The parallel `server` block answers the question the September
        "Failed to fetch" could not: whether the machine answering now is
        the one that was answering a moment ago. A `uptime_s` of a few
        seconds means this process has just replaced another.

        The `disk` block makes a filling volume visible BEFORE the
        mailbox starts turning receipts away: free space in bytes and
        percent, the floor the intake refuses below, and whether it is
        refusing right now. Until this existed the only sign of a full
        disk was Dirk's receipts bouncing mid-close.
        """
        from .intake_mail import disk_snapshot

        return JSONResponse({
            "status": "ok",
            "server": machine.snapshot(),
            "disk": disk_snapshot(data_root_path),
        })

    # ── The client-failure probe (backlog item 50) ──────────────────────
    # A fetch that rejects in the browser never reached this app, so no
    # amount of server logging can ever contain it; the only instrument
    # that can see it is the client itself. These two routes are where the
    # browser's account lands, stamped with this process's identity and
    # age so the decisive question is answerable from the row alone: if
    # the failure was N seconds ago and this process has been up for less
    # than N, it did not exist when the request was made and the machine
    # was replaced underneath it. Fly's machine event log corroborates and
    # outlives the machine, so the timestamp is enough to look it up.
    #
    # The probe must never become a second failure the operator sees: it
    # answers 200 to anything, saying whether it recorded and why not.

    _CLIENT_ERROR_BURST = 20  # per caller per minute; beyond that, drop

    def _capped(value: object, limit: int) -> str:
        return str(value if value is not None else "")[:limit]

    @app.post("/api/client-errors")
    async def post_client_error(request: Request):
        """Record one client-side failure (the SPA calls this when a fetch
        rejects). Authenticated like every other API route: the failures
        worth catching happen inside a live session, so the gate costs no
        coverage and keeps an unauthenticated write off a public host.

        `seconds_ago` drives the machine comparison rather than
        `occurred_at`, deliberately: the client's wall clock can be skewed
        by minutes against the server's, and a skewed clock would fabricate
        or hide a restart. Elapsed time measured inside the one browser is
        immune to that.
        """
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - a broken client is the point here
            body = {}
        if not isinstance(body, dict):
            body = {}

        seconds_ago: float | None
        try:
            raw_ago = body.get("seconds_ago")
            seconds_ago = None if raw_ago is None else float(raw_ago)
            if seconds_ago is not None and (
                seconds_ago < 0 or seconds_ago != seconds_ago  # NaN
            ):
                seconds_ago = None
        except (TypeError, ValueError):
            seconds_ago = None

        def _int_or_none(value: object) -> int | None:
            try:
                return None if value is None else int(value)
            except (TypeError, ValueError):
                return None

        online = body.get("online")
        snap = machine.snapshot()
        now = time.time()
        caller = ratelimit.client_ip(request)
        detail = body.get("detail")
        try:
            detail_text = json.dumps(detail)[:2000] if detail is not None else ""
        except (TypeError, ValueError):
            detail_text = ""

        row = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "received_ts": now,
            "operator": getattr(request.state, "operator", "") or "",
            "caller": caller,
            "kind": _capped(body.get("kind") or "fetch-failed", 40),
            "url": _capped(body.get("url"), 500),
            "method": _capped(body.get("method"), 10).upper(),
            "message": _capped(body.get("message"), 500),
            "occurred_at": _capped(body.get("occurred_at"), 40),
            "seconds_ago": seconds_ago,
            "duration_ms": _int_or_none(body.get("duration_ms")),
            "online": None if online is None else int(bool(online)),
            "detail": detail_text,
            "machine": snap["machine"],
            "region": snap["region"],
            # Which BUILD served this failure (item 120). Stamped from the
            # same snapshot as the machine id, and stamped HERE rather than
            # read back later: this is the process that took the report, and
            # after a restart nothing can reconstruct which build it was.
            "server_commit": snap["commit"],
            "server_image": snap["image"],
            "process_started_at": snap["started_at"],
            "uptime_s": snap["uptime_s"],
            "process_predates_failure": (
                None if (pp := machine.process_predates(seconds_ago)) is None
                else int(pp)
            ),
        }

        with open_store() as store:
            # A broken client can retry in a loop, and an unbounded loop
            # would push the interesting older rows out of a bounded
            # table. Dropping the overflow protects the signal.
            recent = store.count_client_errors_since(now - 60.0, caller)
            if recent >= _CLIENT_ERROR_BURST:
                return JSONResponse({
                    "ok": True, "recorded": False, "reason": "rate-limited",
                    "server": snap,
                })
            row_id = store.record_client_error(row)
        return JSONResponse({
            "ok": True, "recorded": True, "id": row_id, "server": snap,
            "process_predates_failure": row["process_predates_failure"],
        })

    @app.get("/api/client-errors")
    def list_client_errors(limit: int = 50):
        """The reports, newest first, with what this process is right now.

        The stated limit, which every reader has to carry: a row exists
        only when the browser could reach us AFTER the failure. An empty
        list is not evidence that nothing failed.
        """
        with open_store() as store:
            rows = store.list_client_errors(limit)
        return JSONResponse({
            "client_errors": rows,
            "server": machine.snapshot(),
            "note": (
                "A client-side failure is recorded only if the browser "
                "could reach this app afterwards. An empty list is not "
                "proof that nothing failed."
            ),
        })

    # ── Intake (testing mode): saves the documents, runs nothing. The
    # operator runs the pipeline from the queue; the dev-side notifier
    # polls /api/operator/state and mails us about new uploads.
    @app.post("/api/intakes")
    async def post_intake(
        request: Request,
        statement: UploadFile,
        receipts: UploadFile | None = None,
        card_key: str = Form(""),
        card_name: str = Form(""),
        month: str = Form(""),
    ):
        cards = load_cards()
        card = card_by_key(card_key, cards)
        card_label = card.label if card else card_name.strip()
        month_clean = month.strip()
        # The card is the one required identifier; a month alone must not
        # slip through as the label.
        label = f"{card_label} {month_clean}".strip() if card_label else ""

        statement_bytes = await statement.read()
        receipts_bytes = await receipts.read() if receipts is not None else None
        try:
            with open_store() as store:
                intake_row = create_intake(
                    store,
                    app.state.data_root,
                    statement_bytes=statement_bytes,
                    statement_filename=statement.filename or "statement.csv",
                    receipts_bytes=receipts_bytes,
                    receipts_filename=(
                        receipts.filename if receipts is not None else None
                    ),
                    label=label,
                    card_key=card.key if card else None,
                    now_iso=_now_iso(),
                    uploaded_by=request.state.role,
                )
        except RunInputError as exc:
            return _input_refused(exc)
        return JSONResponse(
            {"ok": True, "intake_id": intake_row.intake_id,
             "label": intake_row.label, "status": intake_row.status}
        )

    # Replace (or late-add) files on a queued intake (2026-07-16 user
    # feedback: a wrongly-attached file needs a way out). `received` only;
    # the service layer enforces that and validates extensions.
    @app.post("/api/intakes/{intake_id}/files")
    async def post_intake_files(
        intake_id: str,
        statement: UploadFile | None = None,
        receipts: UploadFile | None = None,
    ):
        with open_store() as store:
            intake = store.get_intake(intake_id)
        if intake is None:
            return _not_found("Upload not found", "upload_not_found")

        statement_bytes = await statement.read() if statement is not None else None
        receipts_bytes = await receipts.read() if receipts is not None else None
        try:
            with open_store() as store:
                replace_intake_files(
                    store,
                    intake,
                    statement_bytes=statement_bytes,
                    statement_filename=(
                        statement.filename if statement is not None else None
                    ),
                    receipts_bytes=receipts_bytes,
                    receipts_filename=(
                        receipts.filename if receipts is not None else None
                    ),
                    now_iso=_now_iso(),
                )
        except RunInputError as exc:
            return _input_refused(exc)
        return JSONResponse({"ok": True, "intake_id": intake_id})

    def _parse_run_form(
        *,
        account_id: str,
        account_legal_entities: str,
        account_card_currency: str,
        sheet_name: str,
        receipts_source: str,
        receipts_default_currency: str,
        use_llm: str,
        expense_column_map: str,
        map_transaction_date: str,
        map_amount: str,
        map_vendor: str,
        map_posting_date: str,
        map_transaction_currency: str,
        card_key: str = "",
        map_card: str = "",
    ) -> RunForm:
        """Shared form parsing for POST /api/runs and POST /api/intakes/{id}/run.
        Raises RunInputError for a user-fixable problem. A provisioned card
        preset fills account/entity/currency; explicit fields still win.

        `map_card` (WS3) is not `card_key`: the former names the statement
        COLUMN holding each row's card, the latter picks a provisioned card
        preset for the whole run."""
        overrides = {
            "transaction_date": map_transaction_date.strip(),
            "amount": map_amount.strip(),
            "vendor": map_vendor.strip(),
            "posting_date": map_posting_date.strip(),
            "transaction_currency": map_transaction_currency.strip(),
            "card": map_card.strip(),
        }
        try:
            expense_map = (
                json.loads(expense_column_map)
                if expense_column_map.strip()
                else dict(DEFAULT_EXPENSE_COLUMN_MAP)
            )
        except json.JSONDecodeError as exc:
            raise RunInputError(
                f"Receipt column map is not valid JSON: {exc}",
                code="receipt_column_map_invalid",
            )

        # Account -> legal entity map (Dirk 2026-06-16): the legal entity is
        # derived from the paying account, not typed each run. Blank => no
        # map, the account name becomes the entity.
        try:
            entity_map_raw = (
                json.loads(account_legal_entities)
                if account_legal_entities.strip()
                else {}
            )
            if not isinstance(entity_map_raw, dict):
                raise ValueError("expected a JSON object of account -> legal entity")
            entity_map = {str(k): str(v) for k, v in entity_map_raw.items()}
        except (json.JSONDecodeError, ValueError) as exc:
            raise RunInputError(
                f"Account to legal-entity map is not valid JSON: {exc}",
                code="entity_map_invalid",
            )

        card = card_by_key(card_key, load_cards())
        resolved_account = account_id.strip() or (card.account_id if card else "")
        resolved_currency = account_card_currency.strip() or (
            card.currency if card else ""
        )
        if card and card.account_id not in entity_map:
            entity_map[card.account_id] = card.legal_entity

        return RunForm(
            account_id=resolved_account,
            account_legal_entities=entity_map,
            account_card_currency=resolved_currency or "USD",
            sheet_name=sheet_name.strip() or None,
            column_map_overrides={k: v for k, v in overrides.items() if v},
            receipts_source=receipts_source.strip() or "csv",
            expense_column_map=expense_map,
            receipts_default_currency=receipts_default_currency.strip(),
            use_llm=bool(use_llm.strip()),
            card_key=card_key.strip(),
        )

    def _start_background_run(
        background: BackgroundTasks, prepared: PreparedRun, label: str
    ) -> JSONResponse:
        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, prepared.intake_id, _now_iso())
        background.add_task(_run_job, app.state.db_path, job_id, prepared)
        # The SPA gets the job id and polls GET /jobs/{id} itself.
        return JSONResponse({"ok": True, "job_id": job_id, "label": label})

    @app.post("/api/runs")
    async def api_post_run(
        request: Request,
        background: BackgroundTasks,
        statement: UploadFile,
        receipts: UploadFile,
        account_id: str = Form(""),
        account_legal_entities: str = Form(""),
        account_card_currency: str = Form("USD"),
        sheet_name: str = Form(""),
        receipts_source: str = Form("csv"),
        receipts_default_currency: str = Form(""),
        use_llm: str = Form(""),
        expense_column_map: str = Form(""),
        map_transaction_date: str = Form(""),
        map_amount: str = Form(""),
        map_vendor: str = Form(""),
        map_posting_date: str = Form(""),
        map_transaction_currency: str = Form(""),
        map_card: str = Form(""),
        card_key: str = Form(""),
    ):
        """Run a reconciliation from an upload: statement + receipts in,
        validate synchronously, kick the pipeline in the background, return
        {job_id}. The SPA polls GET /jobs/{job_id} until status flips to
        "done" (then loads GET /api/runs/{run_id}) or "error". A
        user-fixable input problem is a JSON 400. Always async (no sync
        seam): the SPA is built to poll."""
        try:
            form = _parse_run_form(
                account_id=account_id,
                account_legal_entities=account_legal_entities,
                account_card_currency=account_card_currency,
                sheet_name=sheet_name,
                receipts_source=receipts_source,
                receipts_default_currency=receipts_default_currency,
                use_llm=use_llm,
                expense_column_map=expense_column_map,
                map_transaction_date=map_transaction_date,
                map_amount=map_amount,
                map_vendor=map_vendor,
                map_posting_date=map_posting_date,
                map_transaction_currency=map_transaction_currency,
                map_card=map_card,
                card_key=card_key,
            )
        except RunInputError as exc:
            return _input_refused(exc)

        statement_bytes = await statement.read()
        receipts_bytes = await receipts.read()
        if not statement_bytes:
            return JSONResponse(
                {"error": "No statement file uploaded.", "code": "no_statement_file"},
                status_code=400
            )
        if not receipts_bytes:
            return JSONResponse(
                {"error": "No receipts file uploaded.", "code": "no_receipts_file"},
                status_code=400
            )

        with open_store() as store:
            settings = store.get_settings()
        try:
            prepared = prepare_run(
                app.state.data_root,
                statement_bytes=statement_bytes,
                statement_filename=statement.filename or "statement.csv",
                receipts_bytes=receipts_bytes,
                receipts_filename=receipts.filename or "receipts.csv",
                form=form,
                now_iso=_now_iso(),
                operator=_operator(),
                learning_db_path=app.state.learning_db_path,
                settings=settings,
            )
        except RunInputError as exc:
            return _input_refused(exc)

        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, prepared.intake_id, _now_iso())
        background.add_task(_run_job, app.state.db_path, job_id, prepared)
        return JSONResponse(
            {"job_id": job_id, "label": form.account_id or "this month"}
        )

    # ── Operator: run the pipeline on a stored intake ──────────────────

    @app.post("/api/intakes/{intake_id}/run")
    async def intake_run(
        background: BackgroundTasks,
        intake_id: str,
        account_id: str = Form(""),
        account_legal_entities: str = Form(""),
        account_card_currency: str = Form(""),
        sheet_name: str = Form(""),
        receipts_source: str = Form("csv"),
        receipts_default_currency: str = Form(""),
        use_llm: str = Form(""),
        expense_column_map: str = Form(""),
        map_transaction_date: str = Form(""),
        map_amount: str = Form(""),
        map_vendor: str = Form(""),
        map_posting_date: str = Form(""),
        map_transaction_currency: str = Form(""),
        map_card: str = Form(""),
        card_key: str = Form(""),
    ):
        with open_store() as store:
            intake = store.get_intake(intake_id)
            settings = store.get_settings()
        if intake is None:
            return _not_found("Upload not found", "upload_not_found")

        def _error_page(exc: RunInputError, status_code: int = 400):
            return JSONResponse(
                {"error": exc.message, "code": exc.code, **exc.fields,
                 "headers": exc.headers},
                status_code=status_code,
            )

        try:
            form = _parse_run_form(
                account_id=account_id,
                account_legal_entities=account_legal_entities,
                account_card_currency=account_card_currency,
                sheet_name=sheet_name,
                receipts_source=receipts_source,
                receipts_default_currency=receipts_default_currency,
                use_llm=use_llm,
                expense_column_map=expense_column_map,
                map_transaction_date=map_transaction_date,
                map_amount=map_amount,
                map_vendor=map_vendor,
                map_posting_date=map_posting_date,
                map_transaction_currency=map_transaction_currency,
                map_card=map_card,
                card_key=card_key or intake.card_key or "",
            )
            prepared = prepare_intake_run(
                app.state.data_root,
                intake,
                form,
                now_iso=_now_iso(),
                operator=_operator(),
                learning_db_path=app.state.learning_db_path,
                settings=settings,
            )
        except RunInputError as exc:
            return _error_page(exc)

        with open_store() as store:
            store.set_intake_status(
                intake_id, INTAKE_PROCESSING, updated_at=_now_iso()
            )

        # Sync seam (tests): run inline and answer with the run id directly,
        # no background job to poll.
        if os.environ.get("EXPENSE_RECON_WEB_SYNC") == "1":
            try:
                with open_store() as store:
                    run_id = execute_run(store, prepared)
            except RunInputError as exc:
                with open_store() as store:
                    store.set_intake_status(
                        intake_id, INTAKE_RECEIVED, updated_at=_now_iso()
                    )
                return _error_page(exc)
            return JSONResponse({"ok": True, "run_id": run_id})

        return _start_background_run(background, prepared, intake.label)

    # ── Publish / unpublish a reviewed run (drives the intake status the
    # dashboard and the dev-side notifier read).
    @app.post("/api/runs/{run_id}/publish")
    def publish_run(
        run_id: str, request: Request, payload: dict | None = Body(None)
    ):
        # Items 99 + 100 (owner rulings 2026-09-17): publishing is the month's
        # sign-off, so the route itself refuses a month that is not complete
        # unless the caller overrides, and never publishes a classic run.
        override = isinstance(payload, dict) and payload.get("override") is True
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            if run_mode(run) != MODE_EXPENSE_GENERATION:
                # A statement-first run from the classic page (the live ones
                # are test uploads). It is not a month and teaches nothing;
                # an override does not change that.
                return JSONResponse({
                    "error": "Only a month can be published. This run was made "
                             "on the classic page, so it is not a month.",
                    "code": PUBLISH_NOT_A_MONTH,
                }, status_code=400)
            if has_statement(run):
                summary = _workbench_view(store, run)["summary"]
                complete = bool(summary.get("month_complete"))
                if not complete and not override:
                    return JSONResponse({
                        "error": not_complete_detail(summary),
                        "code": PUBLISH_MONTH_NOT_COMPLETE,
                        "readiness": readiness_of(summary),
                    }, status_code=400)
            else:
                complete = False
                if not override:
                    return JSONResponse({
                        "error": "This month has no statement yet, so no charge "
                                 "is reconciled. Attach the statement, or "
                                 "publish with override.",
                        "code": PUBLISH_NO_STATEMENT,
                    }, status_code=400)
            published_at = _now_iso()
            published_by = getattr(request.state, "operator", auth.DEFAULT_LABEL)
            store.set_run_published(
                run_id, True, published_at,
                published_by=published_by, override=not complete,
            )
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_READY,
                    run_id=run_id, updated_at=_now_iso(),
                )
            # Item 88 (owner ruling 2026-09-16): publishing is the month's
            # sign-off, and it saves the month's corrections to memory. The
            # month is published either way; a failed save is logged and
            # named in the reply, never swallowed and never a failed publish.
            try:
                memory = commit_month_memory(
                    store, run, app.state.learning_db_path, _now_iso(),
                    trigger=MEMORY_TRIGGER_PUBLISH, only_if_changed=True,
                )
            except Exception as exc:  # noqa: BLE001 - publish must not fail on memory
                log.exception("publish %s: saving corrections to memory failed", run_id)
                memory = {"saved": False, "error": str(exc)[:200]}
        return JSONResponse({
            "ok": True, "run_id": run_id, "published": True, "memory": memory,
            "published_at": published_at,
            "published_by": published_by,
            "published_override": not complete,
        })

    @app.post("/api/runs/{run_id}/unpublish")
    def unpublish_run(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            store.set_run_published(run_id, False, None)
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_PROCESSING, updated_at=_now_iso()
                )
            last_save = store.get_memory_commit(run_id)
        # Item 100: say truthfully what unpublishing does to memory. It
        # removes nothing: whatever a save (by Publish or by the button)
        # taught stays until someone forgets it on the Memory page.
        memory: dict = {"unlearned": False, "kept": last_save is not None}
        if last_save is not None:
            memory["saved_at"] = last_save["committed_at"]
            memory["trigger"] = last_save["trigger"]
        return JSONResponse({
            "ok": True, "run_id": run_id, "published": False, "memory": memory,
        })

    # ── Rename / delete a run (F9). The operator accumulates test runs and
    # needs to relabel or clear them; deleting also removes the on-disk
    # upload/export tree so the volume does not grow without bound.
    runs_root = (data_root_path / "runs").resolve()

    @app.post("/api/runs/{run_id}/rename")
    async def rename_run(run_id: str, request: Request):
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        label = str((data or {}).get("label", "")).strip()[:200] if isinstance(data, dict) else ""
        if not label:
            return JSONResponse({"error": "label is required", "code": "label_required"}, status_code=400)
        with open_store() as store:
            if not store.set_run_label(run_id, label):
                return _not_found("Run not found", "run_not_found")
        # Renaming a batch INTO a month is how a mis-labelled month claims
        # the mail that has been waiting for it — the fix path for the
        # default full-date label, which names no month and never claims.
        # A daemon thread because claiming does vision: an async handler
        # must never park the event loop on it.
        month = month_from_label(label)
        if month is not None:
            threading.Thread(
                target=_claim_pooled_quietly,
                args=(app.state.db_path, app.state.learning_db_path,
                      app.state.data_root),
                daemon=True,
            ).start()
        return JSONResponse({
            "ok": True, "run_id": run_id, "label": label,
            "month": f"{month[0]:04d}-{month[1]:02d}" if month else None,
        })

    @app.post("/api/runs/{run_id}/delete")
    def delete_run(run_id: str, payload: dict | None = Body(None)):
        # Sync on purpose: this handler blocks on the batch writer lock,
        # which an OCR ingest can hold for minutes. A sync def runs in the
        # threadpool; an async def would park the EVENT LOOP on the lock
        # and freeze every endpoint including /healthz (adversarial review
        # 2026-08-21, delete-during-ingest is the designed contention).
        from .intake_mail import open_batch, pool_deleted_batch
        from .service import _owe_trip_month_rematches_locked, batch_write_lock

        with open_store() as store:
            if store.get_run(run_id) is None:
                return _not_found("Run not found", "run_not_found")
        # Destructive-action gate: the caller repeats the month's label
        # (or the run id) in the body. A bare POST deletes nothing.
        confirm = (
            str(payload.get("confirm", "")).strip()
            if isinstance(payload, dict) else ""
        )
        if not confirm:
            return JSONResponse(
                {"error": "confirm is required: repeat the month label "
                          "(or run id) to delete",
                 "code": "delete_confirm_required"},
                status_code=400,
            )
        owed_trip_months: list[str] = []
        # Serialize with the batch writers: rows must not vanish under an
        # in-flight ingest RMW, and a writer entering after us re-fetches
        # None and refuses (mail goes held_failed, stays replayable).
        with batch_write_lock():
            with open_store() as store:
                run = store.get_run(run_id)
                if run is None:
                    return _not_found("Run not found", "run_not_found")
                if confirm not in {(run.label or "").strip(), run.run_id}:
                    return JSONResponse(
                        {"error": "confirm label mismatch",
                         "code": "delete_confirm_mismatch"},
                        status_code=409
                    )
                # R4.1: a TRIP batch going away is a pool change for every
                # month borrowing from it. Chosen BEFORE the delete, while
                # the trip and its batch still exist, and stamped in this
                # same lock span so a restart before the paying loop leaves
                # the debt on the month instead of leaving it reporting
                # charges as settled by a run that no longer exists
                # (measured 2026-09-21: July read 33 reconciled, not 31).
                if is_trip_batch(run):
                    try:
                        owed_trip_months = _owe_trip_month_rematches_locked(
                            store, run
                        )
                    except Exception:  # noqa: BLE001 - never block a delete
                        owed_trip_months = []
                store.delete_run(run_id)
                # A deleted run must not leave its intake pointing at a gone
                # run; put the intake back in the queue so it can be re-run.
                if run.intake_id is not None:
                    store.set_intake_status(
                        run.intake_id, INTAKE_RECEIVED, run_id=None,
                        updated_at=_now_iso(),
                    )
                # Where would UPLOADED work land now? Label of the newest
                # remaining open batch, or null. Mailed receipts no longer
                # follow this: they go to the month they print, and
                # `pooled_back` below is their side of the story.
                next_open = open_batch(store)
        # Mail custody holds: archives are NEVER deleted. Month-stamped
        # mail goes back to the POOL, so re-creating the month re-claims
        # it; legacy mail keeps the "month deleted" stamp and its manual
        # re-ingest path.
        n_pooled_back, n_inbound = pool_deleted_batch(
            app.state.data_root, run_id
        )
        # Remove the on-disk work tree, but only inside data_root/runs — never
        # follow a stored path outside the volume.
        try:
            work_dir = Path(run.work_dir).resolve()
            if runs_root in work_dir.parents and work_dir.is_dir():
                shutil.rmtree(work_dir, ignore_errors=True)
        except (OSError, ValueError):
            pass
        # R4.1: pay the trip debt outside the lock (`rematch_month` takes
        # the same non-reentrant lock to commit). Parallel field: absent
        # unless a trip batch was deleted and some month owed a re-match.
        months_rematched = []
        if owed_trip_months:
            with open_store() as store:
                months_rematched = rematch_trip_months(
                    store, owed_trip_months,
                    learning_db_path=app.state.learning_db_path,
                )
        return JSONResponse({
            "ok": True, "run_id": run_id, "deleted": True,
            **({"months_rematched": months_rematched}
               if months_rematched else {}),
            # inbound_marked keeps its old meaning (legacy mail stamped
            # "month deleted"); pooled_back is the parallel field for the
            # mail that simply went back to waiting for this month.
            "inbound_marked": n_inbound,
            "pooled_back": n_pooled_back,
            "next_open_batch": (
                (next_open.label or next_open.run_id)
                if next_open is not None else None
            ),
            # Learned memory (categories/aliases/fx) is deliberately NOT
            # part of the cascade: months come and go, learned facts stay.
            "learned_memory": "kept",
        })

    # ── Operator state API: polled by the dev-side notifier (server stays
    # API-free per the One Assessment precedent; mail is sent from a dev
    # machine, never from this box).
    @app.get("/api/operator/state")
    def operator_state():
        with open_store() as store:
            intakes = store.list_intakes()
            all_runs = store.list_runs()
            active_jobs = store.list_active_jobs()
        published = [r for r in all_runs if r.published]
        return JSONResponse(
            {
                "intakes": [
                    {
                        "intake_id": i.intake_id,
                        "created_at": i.created_at,
                        "label": i.label,
                        "status": i.status,
                        "statement_name": i.statement_name,
                        "receipts_name": i.receipts_name,
                        "detect_note": i.detect_note,
                        "run_id": i.run_id,
                    }
                    for i in intakes
                ],
                # Every run in the store, so the dev-side notifier can ping
                # on a new operator "run now" upload. Since 2026-07-20 the
                # user page is gone and Criss uploads via the operator form,
                # which creates an (initially unpublished) run, not an intake;
                # published_runs alone left those uploads invisible, so no
                # mail ever fired. A run row exists only once its pipeline
                # finished, so `summary` is always populated here.
                "operator_runs": [
                    {
                        "run_id": r.run_id,
                        "created_at": r.created_at,
                        "label": r.label,
                        "published": r.published,
                        "n_transactions": r.summary.get("n_transactions"),
                        "n_matched": r.summary.get("n_matched"),
                        "match_rate": r.summary.get("match_rate"),
                    }
                    for r in all_runs
                ],
                "published_runs": [
                    {
                        "run_id": r.run_id,
                        "label": r.label,
                        "published_at": r.published_at,
                    }
                    for r in published
                ],
                # In-flight pipeline work (F3): a run row appears only once
                # its pipeline finished, so a mid-flight upload is otherwise
                # invisible. The dashboard shows these as "processing".
                "processing": active_jobs,
                "feedback": {
                    "count": len(_read_feedback()),
                },
                # Item 58: every commit of `rematch_month` (attach, re-read,
                # receipts, cards, master data, set-aside, trip) left one
                # event in the month's `rematch_log`; the notifier diffs on
                # `event_id` and mails one line per event. Oldest first;
                # the sort is stable, so two events in one second keep the
                # order their month appended them in.
                "rematches": sorted(
                    (
                        {"run_id": r.run_id, "label": r.label, **ev}
                        for r in all_runs
                        for ev in ((r.snapshot or {}).get(REMATCH_LOG_KEY) or [])
                        if isinstance(ev, dict) and ev.get("event_id")
                    ),
                    key=lambda ev: str(ev.get("at") or ""),
                ),
                # Item 113: months owing a re-match that has not committed
                # (raised, or cut off by a restart), with the last error.
                "rematch_pending": sorted(
                    (
                        {"run_id": r.run_id, "label": r.label, **mark}
                        for r in all_runs
                        for mark in [rematch_pending(r)]
                        if mark is not None
                    ),
                    key=lambda m: str(m.get("since") or ""),
                ),
            }
        )

    # ── Reviewer feedback: the SPA's note widget posts here. Attribution
    # comes from the SESSION (the role), never from the body; the page path
    # and the run id (when the note was left on a run page) locate the
    # note. Storage is an append-only jsonl on the data volume.
    feedback_file = data_root_path / "feedback.jsonl"

    @app.post("/api/feedback")
    async def leave_feedback(request: Request) -> JSONResponse:
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"ok": False, "error": "invalid json", "code": "invalid_json"}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"ok": False, "error": "invalid payload", "code": "invalid_body"}, status_code=400)
        comment = str(data.get("comment", "")).strip()
        if not comment:
            return JSONResponse(
                {"ok": False, "error": "comment is required", "code": "comment_required"}, status_code=400
            )
        # Position sanitized to the known numeric fields, so a note can be
        # located exactly later (coordinates, scroll, % down the page).
        raw_pos = data.get("pos")
        pos = {}
        if isinstance(raw_pos, dict):
            for key in ("pageX", "pageY", "clientX", "clientY", "scrollY", "vw", "vh", "docH", "pct"):
                value = raw_pos.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                pos[key] = int(value)
        page = str(data.get("path", ""))[:300]
        # The SPA sends the run/batch id explicitly when its current view has
        # one; the path parse stays as the fallback so old widget builds (and
        # /runs/{id} routes) keep attributing without it.
        explicit_run_id = str(data.get("run_id", "")).strip()[:64]
        entry = {
            "ts": _now_iso(),
            "role": request.state.role,
            "operator": getattr(request.state, "operator", auth.DEFAULT_LABEL),
            "page": page,
            "run_id": explicit_run_id or _run_id_from_path(page),
            "title": str(data.get("title", ""))[:300],
            "section": str(data.get("section", "")).strip()[:200],
            "selector": str(data.get("selector", "")).strip()[:480],
            "anchor": str(data.get("anchor", "")).strip()[:300],
            "pos": pos or None,
            "comment": comment[:8000],
            "ip": request.headers.get("fly-client-ip")
            or (request.client.host if request.client else ""),
            "ua": request.headers.get("user-agent", "")[:400],
        }
        with feedback_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return JSONResponse({"ok": True})

    def _read_feedback() -> list[dict]:
        rows: list[dict] = []
        if feedback_file.exists():
            for line in feedback_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
        return rows

    # ── Mail intake triage: what arrived, what was held, and the one-click
    # drain for mail that arrived before a month batch existed.
    @app.get("/api/inbound/log")
    def inbound_log(limit: int = 100, detail: int = 0) -> JSONResponse:
        from .intake_mail import (
            annotate_pool_state,
            annotate_status_view,
            annotate_travel_pool,
            count_archives,
            read_log,
            refusal_view,
        )

        rows = read_log(app.state.data_root, limit=max(1, min(limit, 500)))
        # Distinct MAILS, not log rows: an archive that has been replayed
        # or claimed carries a second row, and a badge saying "2 held"
        # about one held mail sends the operator looking for a mail that
        # is not there.
        n_held = count_archives(
            rows, lambda r: str(r.get("status", "")).startswith("held_")
        )
        # Same distinct-MAILS rule: a duplicate parked at arrival is one
        # mail however many log rows it accumulates.
        n_duplicates = count_archives(
            rows, lambda r: str(r.get("status", "")) == "duplicate"
        )
        # Month column truth: resolve the label for EVERY referenced batch
        # (one get_run per distinct id, plain and detail alike). A batch
        # that no longer resolves marks its rows batch_deleted — the UI
        # says "month deleted" — instead of the pre-fix detail join
        # misreporting every document as operator-removed. Held rows have
        # no batch_id; their held_* status IS the Month cell.
        need_view: set[str] = set()
        if detail:
            # Intake overview: each ingested entry gains the expense rows
            # its mail created. One view build per distinct referenced
            # batch (entries cluster on the open month, so this is 1-2
            # builds, not one per entry); a build failure degrades that
            # batch's entries to ids-only rather than sinking the log.
            need_view = {
                str(r["batch_id"]) for r in rows
                if r.get("batch_id") and r.get("documents")
            }
        views: dict[str, dict] = {}
        labels: dict[str, str | None] = {}
        with open_store() as store:
            # Pooled rows say WHY they are waiting: no batch for that
            # month, one open (a claim is imminent), or one already
            # reconciled.
            n_pooled = annotate_pool_state(store, rows)
            for r in rows:
                bid = str(r.get("batch_id") or "")
                if not bid or bid in labels:
                    continue
                run = store.get_run(bid)
                if run is None:
                    labels[bid] = None
                    continue
                labels[bid] = run.label or bid
                # Item 106: a set-aside file restored since is this mail's
                # expense; then the row needs the expenses join too.
                from .intake_mail import apply_restored_set_aside

                apply_restored_set_aside(rows, run)
                if detail and any(
                    str(x.get("batch_id") or "") == bid and x.get("documents")
                    for x in rows
                ):
                    need_view.add(bid)
                if bid in need_view:
                    try:
                        views[bid] = {
                            e["document_id"]: e
                            for e in _expense_view(store, run).get("expenses", [])
                        }
                    except Exception:  # noqa: BLE001 - degrade, don't 500
                        views[bid] = {}
        for r in rows:
            bid = str(r.get("batch_id") or "")
            if not bid:
                continue
            label = labels.get(bid)
            if label is None:
                r["batch_deleted"] = True
            else:
                r["batch_label"] = label
            if not detail:
                continue
            docs = r.get("documents")
            if docs is None:
                continue
            if label is None:
                # The whole month is gone — batch_deleted carries the
                # story; per-document "deleted" rows would misattribute.
                r["expenses"] = []
                continue
            idx = views.get(bid, {})
            out = []
            for doc in docs:
                e = idx.get(doc)
                if e is None:
                    # Created by this mail but no longer in the batch
                    # (operator deleted it) — still part of the story.
                    out.append({"document_id": doc, "deleted": True})
                    continue
                def _disp(v):
                    return v.get("display") if isinstance(v, dict) else v
                out.append({
                    "document_id": doc,
                    "vendor": _disp(e.get("vendor")),
                    "date": _disp(e.get("date")),
                    "total": _disp(e.get("total")),
                    "currency": e.get("currency"),
                })
            r["expenses"] = out
        refused_counts, refusals = refusal_view(app.state.data_root)
        # Travel rows (item 38): stamp the trip suggestion, count the
        # travel share of the pool. Before the status view, whose travel
        # label names the suggestion.
        n_pooled_travel = annotate_travel_pool(
            app.state.db_path, app.state.data_root, rows
        )
        # LAST: the label needs the pool state and the resolved batch
        # labels that the loops above just stamped.
        annotate_status_view(rows)
        # Item 106: finished mails that created no expense, as MAILS (after
        # the batch_deleted stamps above; a deleted month keeps its story).
        from .intake_mail import mail_added_nothing

        n_no_expense = count_archives(rows, mail_added_nothing)
        return JSONResponse({
            "entries": rows,
            "n_held": n_held,
            "n_pooled": n_pooled,
            # The travel share of n_pooled (item 38). Parallel count with
            # its own name, never a second meaning on n_pooled.
            "n_pooled_travel": n_pooled_travel,
            "n_duplicates": n_duplicates,
            # Mail we turned away. Deliberately NOT rows in `entries`: a
            # refusal has no archive, and a row there carrying a status no
            # consumer knows is the exact shape of the "Arriving" bug.
            "n_refused": refused_counts["total"],
            # Parallel split (item 42): a permanent relay-probe floor made
            # the single number blind to a real refused submission.
            # `n_refused` keeps its meaning; these answer the two questions
            # it conflated.
            "n_refused_ours": refused_counts["ours"],
            "n_probes": refused_counts["probes"],
            "refusals": refusals,
            # Item 106: finished mails that created no expense.
            "n_no_expense": n_no_expense,
        })

    @app.post("/api/inbound/replay-held")
    def inbound_replay_held(payload: dict | None = Body(None)) -> JSONResponse:
        """Drain both halves in one click: held mail re-routes by month
        (pooling what has no month open), then every pooled mail whose
        month IS open is claimed.

        `{"materialize": true}` (item 39) is the explicit operator
        backfill: month batches are CREATED for confidently-stamped pooled
        mail, then the normal claim drains them, and LAST the stranded
        `batch_deleted` archives are re-pooled — last on purpose, so a
        freshly re-pooled archive always rests one full round-trip before
        any later call may act on its just-guessed stamps. Requires the
        EXPENSE_RECON_AUTO_MATERIALIZE flag — with it off (or on a plain
        call), the pool only ever waits and the stranded archives are not
        touched, exactly as before the flag existed."""
        from .intake_mail import (
            auto_materialize_enabled,
            claim_pooled,
            materialize_pooled,
            re_pool_stranded,
            replay_held,
        )

        materialize = bool((payload or {}).get("materialize"))
        if materialize and not auto_materialize_enabled():
            return JSONResponse({
                "error": "auto-materialization is off "
                         "(EXPENSE_RECON_AUTO_MATERIALIZE); the pool keeps "
                         "waiting. Flip the flag before backfilling.",
                "code": "auto_materialize_off",
            }, status_code=409)
        result = replay_held(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root,
        )
        mat: dict = {}
        if materialize:
            mat = materialize_pooled(
                app.state.db_path, app.state.learning_db_path,
                app.state.data_root,
            )
        claim = claim_pooled(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root,
        )
        body = {
            "ok": True, **result,
            "claimed": claim["claimed"],
            # replay_held's own `pooled` counts what it just parked; the
            # claim's still_pooled is the pool's size after both halves.
            "still_pooled": claim["still_pooled"],
            "failed": result["failed"] + claim["failed"],
        }
        if materialize:
            # Parallel fields (item 39): which months the backfill created
            # (their first mail is already ingested into each), and how
            # many creations were refused or errored back to the pool.
            body["materialized_months"] = mat.get("materialized_months", [])
            body["materialize_failed"] = mat.get("failed", 0)
            # The stranded re-pool sweep, AFTER the claim: what it just
            # re-pooled rests until the operator's next explicit call.
            sweep = re_pool_stranded(
                app.state.db_path, app.state.learning_db_path,
                app.state.data_root,
            )
            body["re_pooled"] = sweep["re_pooled"]
        return JSONResponse(body)

    # ── Body-only mail actions (C2): view the body, render+ingest it as a
    # PDF through the normal pipeline, or dismiss it as junk. All sync:
    # render-ingest does vision work and must run in the threadpool.
    @app.get("/api/inbound/{archive}/body")
    def inbound_body(archive: str) -> JSONResponse:
        from .intake_mail import read_body_view

        view = read_body_view(app.state.data_root, archive)
        if view is None:
            return _not_found("Archive not found", "mail_not_found")
        return JSONResponse(view)

    @app.post("/api/inbound/{archive}/render-ingest")
    def inbound_render_ingest(archive: str) -> JSONResponse:
        from .intake_mail import render_ingest

        result = render_ingest(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root, archive, operator=_operator(),
        )
        if "error" in result:
            return _refusal_response(result)
        return JSONResponse({"ok": True, **result})

    @app.post("/api/inbound/{archive}/re-ingest")
    def inbound_re_ingest(archive: str) -> JSONResponse:
        """Item 19: put a stranded mail's attachments back into the open
        month. Sync like render-ingest — the ingest does vision work, so the
        threadpool the sync handler already runs in is where it belongs."""
        from .intake_mail import re_ingest

        result = re_ingest(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root, archive, operator=_operator(),
        )
        if "error" in result:
            return _refusal_response(result)
        return JSONResponse({"ok": True, **result})

    @app.post("/api/inbound/{archive}/join-trip")
    async def inbound_join_trip(archive: str, request: Request) -> JSONResponse:
        """Item 38: the operator's click that puts a travel-pooled mail on
        a trip — the ONLY way travel mail becomes expenses. Body:
        {"trip_id": ...}. Runs the ingest synchronously in the threadpool
        like the other inbound actions (vision work)."""
        from .intake_mail import join_trip

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        trip_id = str((body or {}).get("trip_id") or "").strip() \
            if isinstance(body, dict) else ""
        if not trip_id:
            return JSONResponse(
                {"error": "trip_id is required", "code": "trip_id_required"},
                status_code=400
            )
        result = await run_in_threadpool(
            join_trip,
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root, archive, trip_id, _operator(),
        )
        if "error" in result:
            return _refusal_response(result)
        return JSONResponse({"ok": True, **result})

    @app.post("/api/inbound/{archive}/not-a-duplicate")
    def inbound_not_a_duplicate(archive: str) -> JSONResponse:
        """Route a mail the detector parked as a duplicate after all.

        Sync for the same reason re-ingest is: routing reads the receipts,
        which is vision work, and belongs on the threadpool this handler
        already runs in."""
        from .intake_mail import unmark_duplicate

        result = unmark_duplicate(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root, archive,
        )
        if "error" in result:
            return _refusal_response(result)
        return JSONResponse({"ok": True, **result})

    @app.post("/api/inbound/{archive}/dismiss")
    def inbound_dismiss(archive: str) -> JSONResponse:
        from .intake_mail import dismiss_archive

        result = dismiss_archive(
            app.state.data_root, archive, operator=_operator(),
        )
        if "error" in result:
            return _refusal_response(result)
        return JSONResponse({"ok": True, **result})

    @app.get("/feedback.jsonl")
    def feedback_raw() -> PlainTextResponse:
        text = feedback_file.read_text(encoding="utf-8") if feedback_file.exists() else ""
        return PlainTextResponse(text, media_type="application/x-ndjson")

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str):
        # PR F — the SPA polls this until status flips to done (then it
        # loads the run) or error. Durable read: the row survives a
        # restart, so an interrupted job reports honestly.
        with open_store() as store:
            job = store.get_job(job_id)
        if job is None:
            return JSONResponse({"error": "unknown job", "code": "job_not_found"}, status_code=404)
        return JSONResponse(job)

    def _expense_view(store: RunStore, run) -> dict:
        """The receipt-spine render model for an expense batch, with every
        stored edit overlay loaded. Shared by the run dispatch, the batch
        GET, and the edit endpoints' summary replies."""
        overrides = store.get_category_overrides(run.run_id)
        field_overrides = store.get_expense_field_overrides(run.run_id)
        edits = store.get_expense_edits(run.run_id)
        resolutions = store.get_duplicate_resolutions(run.run_id)
        settings = store.get_settings()
        # PR 3: the per-card coverage roll-up is decision-aware, so the grid
        # reports the same stage of done the workbench does. Read here
        # because the store is open here; a month with no statement holds no
        # charges and the read costs nothing.
        decisions = store.get_decisions(run.run_id)
        # Item 38: a trip batch renders its trip entity (name, range,
        # travelers roster) beside the grid; null on company months and
        # on a trip batch whose entity was deleted out from under it
        # (the null is the honest answer, never a fabricated object).
        trip = None
        trip_id = str((run.config or {}).get("trip_id") or "")
        if trip_id:
            trip_row = store.get_trip(trip_id)
            if trip_row is not None:
                trip = {
                    "trip_id": trip_row.trip_id,
                    "name": trip_row.name,
                    "start": trip_row.start_date,
                    "end": trip_row.end_date,
                    "travelers": list(trip_row.travelers),
                    # Item 47: the trip is the strongest AUTOMATIC
                    # cost-center signal for every row in its batch.
                    "cost_center": trip_row.cost_center,
                }
        return build_expense_view(
            run, overrides, field_overrides, edits, resolutions,
            settings=settings, decisions=decisions, trip=trip,
            # R4: name the month that settled each of this batch's
            # receipts (a trip receipt matched by a statement). Empty on
            # every batch with no cross-batch settlements.
            settled_elsewhere=_settled_elsewhere(store, run.run_id),
            # 2026-09-16: the payload's `updated_at` has to see edits the
            # snapshot never records (a field edit on a month with no
            # statement), and the edit tables are where they live.
            edited_at=store.latest_edit_at(run.run_id),
            # Item 77: which batch a move offer would join. Called only for
            # rows that carry an offer, so a month with none pays nothing.
            month_batch=lambda month: _month_batch_id(store, month),
            # Item 169: the remembered card, read live rather than off the
            # stamp ingest left, so a correction taught after this month was
            # ingested still names its card.
            learning_db_path=app.state.learning_db_path,
        )

    def _expense_page_view(store: RunStore, run) -> dict:
        """The Expenses page's payload: `_expense_view` plus its card tabs
        (item 138). Only the page GETs build the tabs; the edit routes that
        reply with `_expense_view`'s summary skip the extra view build."""
        return attach_expense_card_tabs(
            _expense_view(store, run), run,
            overrides=store.get_category_overrides(run.run_id),
            field_overrides=store.get_expense_field_overrides(run.run_id),
            edits=store.get_expense_edits(run.run_id),
            resolutions=store.get_duplicate_resolutions(run.run_id),
            decisions=store.get_decisions(run.run_id),
        )

    def _month_batch_id(store: RunStore, month: str) -> str | None:
        """The batch month routing picks for "YYYY-MM", or None."""
        from .intake_mail import _open_batch_for_month, _ym

        target = _open_batch_for_month(store, _ym(month))
        return target.run_id if target is not None else None

    def _settled_elsewhere(store: RunStore, run_id: str) -> dict[str, dict]:
        """R4 (item 38): document_id -> {run_id, label, transaction_id} for
        receipts in this run's pool that another run's charge settled.
        Empty for every month with no cross-batch settlements, and
        `build_view` then adds nothing."""
        out: dict[str, dict] = {}
        label_cache: dict[str, str] = {}
        for doc, c in store.get_claims_on_receipts(run_id).items():
            holder = c["claimed_by_run_id"]
            if holder == run_id:
                continue
            if holder not in label_cache:
                other = store.get_run(holder)
                label_cache[holder] = (
                    (other.label or other.run_id) if other else holder
                )
            out[doc] = {
                "run_id": holder,
                "label": label_cache[holder],
                "transaction_id": c["transaction_id"],
            }
        return out

    def _workbench_view(store: RunStore, run) -> dict:
        """The statement workbench payload exactly as `GET /api/runs/{id}`
        serves it, so the publish gate reads the counts the page shows."""
        run_id = run.run_id
        decisions = store.get_decisions(run_id)
        overrides = store.get_category_overrides(run_id)
        resolutions = store.get_duplicate_resolutions(run_id)
        settled_elsewhere = _settled_elsewhere(store, run_id)
        # 2026-09-16: `updated_at` over the edit tables too; a category
        # override or a duplicate ruling moves the month without
        # touching its snapshot or its decisions.
        edited_at = store.latest_edit_at(run_id)
        return build_view(
            run, decisions, overrides, resolutions,
            settled_elsewhere=settled_elsewhere,
            edited_at=edited_at,
            field_overrides=store.get_expense_field_overrides(run_id),
            # Item 107: the holders' addresses and the merchant registry's
            # portal hints, for `receipt_chase[]`. The list itself, and
            # every count, come off the rows and do not depend on this.
            settings=store.get_settings(),
        )

    def _run_view(store: RunStore, run) -> dict:
        """The payload `GET /api/runs/{id}` serves for this run, dispatched
        the way that route dispatches it.

        Every mutating route that answers with a `summary` answers with THIS
        one (residual R2), so the counts the SPA holds after a write are the
        counts a refetch gives it. `build_view(run, decisions, overrides)`
        was missing the month's own overlays — the header edits above all,
        so a receipt marked private still read as needing a charge in the
        reply (`n_receipts_need_charge`, `month_complete`) and corrected
        itself only on the next run refetch."""
        if run_mode(run) == MODE_EXPENSE_GENERATION and not has_statement(run):
            return _expense_view(store, run)
        return _workbench_view(store, run)

    @app.get("/api/runs/{run_id}")
    def api_workbench(run_id: str):
        """The review render model for the SPA: `build_view` (transaction
        spine) for a statement run, `build_expense_view` (receipt spine)
        for an expense batch — dispatched on the run's stored mode marker.
        jsonable_encoder handles the view's Decimal / date values for the
        display-only client."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            # A batch WITH a statement attached graduates to the workbench:
            # build_view over the baked snapshot, every statement-mode
            # surface (decisions / confirm-ready / exports) unchanged. The
            # expense grid stays reachable via GET /api/expense-batches/{id}.
            if run_mode(run) == MODE_EXPENSE_GENERATION and not has_statement(run):
                return JSONResponse(jsonable_encoder(_expense_page_view(store, run)))
            # Item 138: the Matching page's card tabs ride this GET only,
            # on top of `_run_view`, which is the dispatch the mutating
            # routes reply with (residual R2). The tabs are additive and
            # never touch the summary, which is why the reply can skip them.
            view = attach_run_card_tabs(
                _run_view(store, run), run,
                store.get_expense_field_overrides(run_id),
            )
        # build_view already carries run_id, label, summary, rows,
        # unmatched_*, duplicate_groups, category_options: return it as the
        # SPA render model.
        return JSONResponse(jsonable_encoder(view))

    @app.post("/api/runs/{run_id}/decisions")
    async def post_decision(run_id: str, request: Request):
        body = await request.json()
        tx_id = body.get("transaction_id")
        status = body.get("status")
        chosen = body.get("chosen_document_id")
        if not tx_id or status not in VALID_STATUSES:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            # R4 (item 38): the claim sync runs FIRST -- a verdict that
            # would let this receipt settle a second charge in another
            # batch is refused whole, decision unwritten.
            # Item 104: read the old verdict BEFORE the upsert destroys it.
            before = store.get_decisions(run_id).get(tx_id)
            conflict = sync_claim_for_decision(
                store, run, tx_id, status, chosen, _now_iso()
            )
            if conflict is not None:
                return _refused(conflict, status=409)
            store.set_decision(run_id, tx_id, status, chosen, _now_iso())
            _append_history(store, [_decision_entry(
                run_id, tx_id, before, status, chosen,
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
            )])
            view = _run_view(store, run)
        return JSONResponse(jsonable_encoder({"ok": True, "summary": view["summary"]}))

    # §17 disposition. The upsert is status-preserving in the store (never
    # clobbers the row's triage verdict).
    @app.post("/api/runs/{run_id}/disposition")
    async def post_disposition(run_id: str, request: Request):
        body = await request.json()
        tx_id = body.get("transaction_id")
        disposition = body.get("disposition")
        if not tx_id or disposition not in VALID_DISPOSITIONS:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            before = store.get_decisions(run_id).get(tx_id)
            store.set_disposition(run_id, tx_id, disposition, _now_iso())
            _append_history(store, [dh.make_entry(
                run_id=run_id, row_key=tx_id, row_kind=dh.ROW_CHARGE,
                field=dh.FIELD_DISPOSITION,
                old=getattr(before, "disposition", None),
                new=disposition,
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
            )])
            view = _run_view(store, run)
        return JSONResponse(jsonable_encoder({"ok": True, "summary": view["summary"]}))

    # Item 107, the chase states. Both are per-charge, both are written by
    # the same status-preserving upsert family as the disposition above, and
    # both live on the charge's `decisions` row, which is what carries them
    # through a re-match. Asking closes nothing; "no receipt expected"
    # closes the charge and takes its money out of the unreconciled total.
    @app.post("/api/runs/{run_id}/receipt-requested")
    async def post_receipt_requested(run_id: str, request: Request):
        """Record that this charge's receipt was asked for (or clear it).

        Body: `{transaction_id, to?}` marks it asked NOW, optionally naming
        the address it was asked from; `{transaction_id, clear: true}`
        removes the record. Writing the mark is all this does: no mail is
        composed and none is sent (see receipt_chase.py)."""
        body = await request.json()
        tx_id = str((body or {}).get("transaction_id") or "").strip()
        if not tx_id:
            return JSONResponse(
                {"error": "bad request", "code": "invalid_body",
                 "missing": "transaction_id"},
                status_code=400,
            )
        clear = bool((body or {}).get("clear"))
        to = str((body or {}).get("to") or "").strip() or None
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse(
                    {"error": "run not found", "code": "run_not_found"},
                    status_code=404,
                )
            store.set_receipt_requested(
                run_id, tx_id,
                None if clear else _now_iso(),
                None if clear else to,
                _now_iso(),
            )
            view = _workbench_view(store, run)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    @app.post("/api/runs/{run_id}/no-receipt-expected")
    async def post_no_receipt_expected(run_id: str, request: Request):
        """Rule that no receipt will ever exist for this charge, and say why.

        Body: `{transaction_id, reason}` marks it; `{transaction_id, clear:
        true}` removes the mark. The reason is refused blank: a verdict
        nobody can read next month is worse than no verdict, and this one
        both closes the charge for the month gate and takes its money out of
        `unreconciled_by_ccy`."""
        body = await request.json()
        tx_id = str((body or {}).get("transaction_id") or "").strip()
        clear = bool((body or {}).get("clear"))
        reason = str((body or {}).get("reason") or "").strip()
        if not tx_id or (not clear and not reason):
            return JSONResponse(
                {"error": "transaction_id and a reason are required",
                 "code": "reason_required"},
                status_code=400,
            )
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse(
                    {"error": "run not found", "code": "run_not_found"},
                    status_code=404,
                )
            store.set_no_receipt_expected(
                run_id, tx_id, None if clear else reason[:200], _now_iso()
            )
            view = _workbench_view(store, run)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    @app.get("/api/runs/{run_id}/receipt-requests")
    def get_receipt_requests(run_id: str):
        """The chase mail this month WOULD send, per card holder: the dry
        run. Read-only, composes and returns; nothing is sent, and no send
        path exists for it to reach (item 107).

        `enabled` is the owner's switch (`settings.receipt_requests.
        enabled`, off by default). `can_send` is false in this build
        whatever the switch says, and `send_blocked_reason` names which gate
        is refusing."""
        from .intake_mail import IntakeConfig
        from .receipt_chase import (
            SEND_DISABLED,
            SEND_NOT_WIRED,
            compose_requests,
            requests_enabled,
        )

        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            settings = store.get_settings()
            view = _workbench_view(store, run)
        cfg = IntakeConfig.from_settings(settings)
        intake_address = f"receipts@{cfg.domain}"
        groups = view.get("receipt_chase") or []
        enabled = requests_enabled(settings)
        return JSONResponse(jsonable_encoder({
            "run_id": run_id,
            "label": run.label,
            "enabled": enabled,
            "can_send": False,
            "send_blocked_reason": SEND_NOT_WIRED if enabled else SEND_DISABLED,
            "intake_address": intake_address,
            "n_charges_need_receipt": view["summary"]["n_charges_need_receipt"],
            "groups": groups,
            "mails": compose_requests(
                groups, month_label=run.label, intake_address=intake_address
            ),
        }))

    @app.post("/api/runs/{run_id}/receipt-requests/send")
    def post_receipt_requests_send(run_id: str):
        """Refuses, always, in this build.

        The owner approves real sends separately (Brisken send-by-id
        standard). Until then there is no sender to reach: `receipt_chase`
        imports no mail transport, so this route cannot deliver a message
        even with the switch on. It answers 403 and names which gate."""
        from .receipt_chase import (
            SEND_DISABLED,
            SEND_NOT_WIRED,
            requests_enabled,
        )

        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            enabled = requests_enabled(store.get_settings())
        if not enabled:
            return JSONResponse({
                "error": "Receipt requests are switched off. Turn on "
                         "Settings > receipt requests first; the owner "
                         "approves the first real send separately.",
                "code": SEND_DISABLED,
            }, status_code=403)
        return JSONResponse({
            "error": "Receipt requests are switched on, but no sender is "
                     "wired yet: this build composes the mail and never "
                     "sends it. Use the preview and send it by hand until "
                     "the owner approves the automated send.",
            "code": SEND_NOT_WIRED,
        }, status_code=403)

    # §18 duplicate resolve. Advisory: records the reviewer's verdict on a
    # flagged duplicate group (ignore / confirmed); never touches buckets or
    # the invariant, never deletes. Accepts either the backend-native
    # {group_id, resolution} or the SPA contract's {group_id, action}.
    @app.post("/api/runs/{run_id}/duplicates/resolve")
    async def post_duplicate_resolve(run_id: str, request: Request):
        body = await request.json()
        group_id = body.get("group_id") or body.get("group_key")
        resolution = body.get("resolution") or body.get("action")
        if not group_id or resolution not in VALID_DUP_RESOLUTIONS:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            before_dup = store.get_duplicate_resolutions(run_id).get(group_id)
            store.set_duplicate_resolution(run_id, group_id, resolution, _now_iso())
            _append_history(store, [dh.make_entry(
                run_id=run_id, row_key=group_id, row_kind=dh.ROW_GROUP,
                field=dh.FIELD_DUPLICATE,
                old=before_dup, new=resolution,
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
            )])
            reconciling = has_statement(run)
        # Item 56: the resolution decides what the matcher's pool holds (an
        # `ignore` group is NOT collapsed), so a reconciling month has to
        # re-match or the ruling is allowed but inert -- the same reasoning
        # as every other living-month change. Off the event loop, because
        # rematch takes the batch lock and can call the model.
        rematch = None
        if reconciling:
            rematch = await run_in_threadpool(
                _resolve_duplicate_rematch,
                app.state.db_path, app.state.learning_db_path, run_id,
            )
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            # Dispatch on the run's mode, exactly as GET /api/runs/{id}
            # does. Duplicate groups are flagged in BOTH payloads, so an
            # expense batch can be resolved from the grid; replying with
            # `build_view`'s summary there handed the grid the workbench's
            # counts, and every one of the fields it renders (n_expenses,
            # n_ready, n_duplicate_rows) is absent from that shape.
            view = _run_view(store, run)
        out = {"ok": True, "summary": view["summary"]}
        if rematch is not None:
            out["rematch"] = rematch
        return JSONResponse(jsonable_encoder(out))

    # §16 export policy. The policy is snapshotted into each new run's
    # config at creation, so changing it affects future runs, never
    # re-writes a run already produced.
    @app.get("/api/settings")
    def api_get_settings():
        # `categories` is the fixed 8, surfaced read-only (Phase 5) so the
        # settings screen can show them; PUT ignores the key entirely.
        # `entity_options` is the real legal-entity list (CoA provisioning +
        # card->entity targets + registry) so the create form and the entity
        # editor can offer a dropdown instead of a free-text field; also
        # read-only (derived), PUT ignores it.
        # `cards_effective` is the composed card registry (settings cards +
        # legacy maps + /data presets, `cards.effective_cards`) so the
        # Settings screen can render the one merged view; read-only
        # (derived), PUT ignores it — edits go to the `cards` key.
        # `merchants_inert` (Cards R2) names the merchants whose
        # zoho_account can never fire because no category is set
        # (apply_registry_category is a no-op without one) — the Settings
        # screen shows the hint instead of a silently dead field.
        with open_store() as store:
            settings = store.get_settings()
            return JSONResponse({
                **without_retired_settings_keys(
                    without_retired_entity_keys(settings)
                ),
                "categories": list(EXPENSE_CATEGORIES),
                # The new vocabulary, served BESIDE the eight rather than
                # instead of them: the published SPA keeps rendering
                # `categories` until the owner publishes a bundle that
                # reads these. `gl_revision` makes a stale one diagnosable.
                "gl_accounts": gl_account_options(settings),
                "gl_revision": gl_revision(),
                "entity_options": available_entities(settings),
                "cards_effective": [
                    card_to_dict(c)
                    for c in effective_cards(settings, load_cards()).values()
                ],
                "merchants_inert": sorted(
                    name
                    for name, entry in (settings.get("merchants") or {}).items()
                    if isinstance(entry, dict)
                    and str(entry.get("zoho_account") or "").strip()
                    and not str(entry.get("category") or "").strip()
                ),
                # The picker's list: ACTIVE cost centers, name-sorted, each
                # with its display-only kind. Derived and read-only; PUT
                # ignores it, edits go to the `cost_centers` key. Empty
                # until the owner defines one, and that is the whole
                # contract (cost_centers.py).
                "cost_center_options": CostCenterRegistry.from_settings(
                    settings
                ).options(),
                # Note #79: the poll's state and the newest polled day's
                # rates (units per EUR + every pair), so the FX tab can
                # show what the app fetched. Derived and read-only; PUT
                # ignores it. Since the typed rates were retired (item
                # 168) these and the ECB monthly average are the only
                # reference rates the matcher has, besides the ones a run
                # derives from its own statement and receipts.
                "fx_daily_rates": fx_daily_rates.settings_view(store),
            })

    @app.post("/api/fx/poll")
    def api_fx_poll():
        """Poll the daily FX rates now (note #79): the same round the
        24-hour thread runs, synchronously, so the screen's "Poll now" and
        a deploy check see the result. 409 `fx_poll_disabled` when no
        provider key is configured; otherwise 200 with the round's summary,
        `ok: false` + `errors[]` when the provider failed (nothing is lost:
        the table keeps what it had)."""
        with open_store() as store:
            result = fx_daily_rates.poll_once(store)
        if result.get("code") == "fx_poll_disabled":
            return JSONResponse(
                {"error": result.get("reason"), "code": "fx_poll_disabled"},
                status_code=409,
            )
        return JSONResponse(result)

    @app.get("/api/cards")
    def api_get_cards():
        # The composed card enumeration (owner ask 2026-08-21: "laying out
        # all card identities"). Same payload family as cards_effective,
        # plus the entity options the assignment UI needs.
        with open_store() as store:
            settings = store.get_settings()
            runs = store.list_runs()
        composed = effective_cards(settings, load_cards())
        return JSONResponse({
            "cards": [card_to_dict(c) for c in composed.values()],
            "entity_options": available_entities(settings),
            # Cards the months actually charge that the registry cannot
            # name (2026-08-28). Without this the definition screen listed
            # only cards somebody had already defined, so on the live April
            # month it showed 2838 plus four cards with no charges, while
            # 0340, 3645 and 4700 carried 53 of the 94 charges and appeared
            # nowhere. Parallel field: empty when every card is known.
            "seen_undefined": cards_seen_but_undefined(runs, composed),
        })

    @app.put("/api/settings")
    async def api_put_settings(request: Request):
        body = await request.json()
        # One settings GROUP per request is the settings screen's contract
        # (the tabbed page saves the tab you are in, `{"cards": {...}}`),
        # so this request is the only feedback that group gets. A key the
        # handler does not write is refused by name rather than dropped in
        # silence under a 200 that means "saved" everywhere else. The
        # derived keys `GET` composes stay accepted-and-ignored: reading
        # the payload, editing one group and sending the whole object back
        # is legal, and `applied` says what actually landed.
        if not isinstance(body, dict):
            return JSONResponse(
                {"error": "settings body must be an object", "code": "invalid_body"}, status_code=400
            )
        unknown = sorted(
            k
            for k in body
            if k not in SETTINGS_WRITABLE_KEYS
            and k not in SETTINGS_DERIVED_KEYS
            and k not in RETIRED_SETTINGS_KEYS
        )
        if unknown:
            return JSONResponse(
                {"error": f"unknown settings key(s): {', '.join(unknown)}",
                 "code": "unknown_settings_keys", "keys": unknown},
                status_code=400,
            )
        patch: dict = {}
        # Per-merchant categories the save carried that the server no longer
        # knows. Collected rather than refused (see `category_vocabulary`)
        # and reported as dotted paths in `ignored` below, so the caller is
        # told exactly which merchant lost its category.
        dropped_categories: list[tuple[str, str]] = []
        if "export_approved_only" in body:
            patch["export_approved_only"] = bool(body["export_approved_only"])
        # Master-data maps (FX reference rates, card -> legal entity, card
        # -> Zoho bank account). Values normalize to trimmed strings; a
        # blank value drops the key, which is how the UI deletes a row. An
        # FX rate must parse as a positive number: a typo here would
        # silently mis-match a whole month, so it is rejected at the edge
        # instead of being swallowed at match time.
        for key in SETTINGS_MAP_KEYS:
            if key not in body:
                continue
            raw = body[key]
            if not isinstance(raw, dict):
                return JSONResponse(
                    {"error": f"{key} must be an object",
                     "code": "invalid_body", "setting": key},
                    status_code=400
                )
            cleaned: dict[str, str] = {}
            for k, v in raw.items():
                name = str(k).strip()
                value = str(v).strip()
                if not name or not value:
                    continue
                cleaned[name] = value
            patch[key] = cleaned
        # Legal-entity registry (Phase 5): {label: {org_id, chart_path,
        # default_paid_through, scope_groups}}. String fields trim; list
        # fields must be lists of strings. The whole map replaces the stored
        # one (same contract as the other map keys), so deleting an entity is
        # omitting it. `categories` is read-only and never persisted.
        # A retired field (`RETIRED_ENTITY_KEYS`) is dropped whatever its
        # shape, never a 400: the published SPA sends `account_picks` on
        # every entities save until its removal prompt is applied.
        if "entities" in body:
            raw = body["entities"]
            if not isinstance(raw, dict):
                return JSONResponse(
                    {"error": "entities must be an object",
                     "code": "invalid_body", "setting": "entities"},
                    status_code=400
                )
            cleaned_entities: dict[str, dict] = {}
            for label, ent in raw.items():
                name = str(label).strip()
                if not name:
                    continue
                if not isinstance(ent, dict):
                    return JSONResponse(
                        {"error": f"entities[{name!r}] must be an object",
                         "code": "invalid_body", "setting": "entities"},
                        status_code=400,
                    )
                entry: dict = {}
                for skey in ("org_id", "chart_path", "default_paid_through"):
                    if str(ent.get(skey) or "").strip():
                        entry[skey] = str(ent[skey]).strip()
                for lkey in ("scope_groups",):
                    if ent.get(lkey) is None:
                        continue
                    if not isinstance(ent[lkey], list):
                        return JSONResponse(
                            {"error": f"entities[{name!r}].{lkey} must be a list",
                             "code": "invalid_body", "setting": "entities"},
                            status_code=400,
                        )
                    values = [str(v).strip() for v in ent[lkey] if str(v).strip()]
                    if values:
                        entry[lkey] = values
                cleaned_entities[name] = entry
            patch["entities"] = cleaned_entities
        # The operator's own order for the entity list (item 92): a list of
        # entity names, best first. Whole-list replace, trimmed, blanks
        # dropped, first occurrence wins on a repeat. Nothing here checks
        # that a name still exists: an entity can leave the /data
        # provisioning or the card map at any time, and a save that 400'd
        # because the list remembered a name the tool no longer knows would
        # refuse the operator's own ordering for a reason they cannot see.
        # `available_entities` ignores stale names at read time instead.
        if "entity_order" in body:
            raw_order = body["entity_order"]
            if not isinstance(raw_order, list):
                return JSONResponse(
                    {"error": "entity_order must be a list",
                     "code": "invalid_body", "setting": "entity_order"},
                    status_code=400
                )
            order: list[str] = []
            for item in raw_order:
                name = str(item).strip()
                if name and name not in order:
                    order.append(name)
            patch["entity_order"] = order
        # Merchant registry (2026-07-29): {canonical_name: {aliases, category,
        # zoho_account}}. Whole-map replace, same contract as `entities`;
        # validated + cleaned by the registry module (blank canonical dropped,
        # aliases de-duped on their normalized key, category constrained to
        # the fixed 8). A malformed payload is rejected at the edge.
        if "merchants" in body:
            # Item 117: the stored map lets the registry refuse a NEW
            # generic-word alias while accepting what is already saved.
            with open_store() as store:
                stored_merchants = (
                    (store.get_settings() or {}).get("merchants") or {}
                )
            try:
                patch["merchants"] = normalize_merchants_setting(
                    body["merchants"], stored=stored_merchants,
                    dropped=dropped_categories,
                )
            except ValueError as exc:
                return JSONResponse({
                    "error": str(exc), "code": code_of(exc, "invalid_body"),
                    "setting": "merchants", **fields_of(exc),
                }, status_code=400)
        # Card registry (2026-08-21): {slug: {label, digits, aliases,
        # entity, zoho_account?, currency, active}}. Whole-map replace,
        # validated + cleaned by the cards module (blank slug dropped,
        # digits constrained to digit strings, aliases de-duped on their
        # normalized key). The legacy card_entities/card_accounts maps
        # stay writable unchanged; composition happens at read time.
        if "cards" in body:
            try:
                patch["cards"] = normalize_cards_setting(body["cards"])
            except ValueError as exc:
                return JSONResponse({
                    "error": str(exc), "code": code_of(exc, "invalid_body"),
                    "setting": "cards", **fields_of(exc),
                }, status_code=400)
        # Cost centers (item 47): {name: {kind, note, active}}. Whole-map
        # replace, same contract family as merchants / cards / entities.
        # Owner-authored ONLY — nothing else in the tool ever writes this
        # key, because the tool must never invent a cost center.
        if "cost_centers" in body:
            try:
                patch["cost_centers"] = normalize_cost_centers_setting(
                    body["cost_centers"]
                )
            except ValueError as exc:
                return JSONResponse({
                    "error": str(exc), "code": code_of(exc, "invalid_body"),
                    "setting": "cost_centers", **fields_of(exc),
                }, status_code=400)
        # Mail-intake config (aliases -> person names, sender allowlist,
        # daily caps). Validated at the edge like merchants.
        if "intake" in body:
            from .intake_mail import normalize_intake_setting

            try:
                patch["intake"] = normalize_intake_setting(body["intake"])
            except ValueError as exc:
                return JSONResponse({
                    "error": str(exc), "code": code_of(exc, "invalid_body"),
                    "setting": "intake", **fields_of(exc),
                }, status_code=400)
        # Receipt chasing (item 107): {enabled, holders: {person: address}}.
        # Whole-object replace, same contract as `intake`. `enabled` must be
        # a real boolean and an address must be a single plain one: the key
        # decides who an outbound chase would reach, so a tolerant parse
        # here is the wrong kind of kindness.
        if "receipt_requests" in body:
            from .receipt_chase import normalize_receipt_requests_setting

            try:
                patch["receipt_requests"] = normalize_receipt_requests_setting(
                    body["receipt_requests"]
                )
            except ValueError as exc:
                return JSONResponse({
                    "error": str(exc), "code": code_of(exc, "invalid_body"),
                    "setting": "receipt_requests", **fields_of(exc),
                }, status_code=400)
        with open_store() as store:
            settings = store.set_settings(patch, _now_iso())
        return JSONResponse({
            **without_retired_entity_keys(settings),
            "categories": list(EXPENSE_CATEGORIES),
            # Both vocabularies on the save reply too, so an editor that
            # just added an entity sees its leaves without a second GET.
            "gl_accounts": gl_account_options(settings),
            "gl_revision": gl_revision(),
            # What this request wrote, and what it carried that the server
            # derives. A caller shows "saved" on its own key appearing in
            # `applied`, never on the 200 alone.
            "applied": sorted(patch),
            # A derived key is read-only; a RETIRED key no longer exists
            # at all. Both are accepted and reported rather than refused,
            # so the published SPA can keep sending `fx_reference_rates`
            # until its removal prompt is applied.
            # A dropped merchant category joins this list as the dotted path
            # `merchants.<name>.category`. Still a list of strings, so a
            # caller testing for a key it sent is unaffected; the path says
            # which merchant to re-pick rather than just that something went.
            "ignored": sorted(
                [
                    k for k in body
                    if k in SETTINGS_DERIVED_KEYS or k in RETIRED_SETTINGS_KEYS
                ]
                + [f"merchants.{name}.category" for name, _ in dropped_categories]
            ),
        })

    @app.get("/api/compare")
    def api_compare(a: str = "", b: str = ""):
        """Across-runs compare: the SPA picks two runs and shows the bucket
        deltas. The diff is computed server-side by `compare_runs`, so the
        front end never derives it. Returns the run list for the two
        selectors plus the comparison (null until both a and b resolve to
        real runs)."""
        with open_store() as store:
            runs = store.list_runs()
            run_a = store.get_run(a.strip()) if a.strip() else None
            run_b = store.get_run(b.strip()) if b.strip() else None
        comparison = (
            compare_runs(run_a, run_b)
            if run_a is not None and run_b is not None
            else None
        )
        return JSONResponse({
            "runs": [
                {"run_id": r.run_id, "label": r.label, "created_at": r.created_at}
                for r in runs
            ],
            "a": a.strip(),
            "b": b.strip(),
            "comparison": comparison,
        })

    @app.get("/api/memory")
    def api_memory(unvalidated: int = 0):
        """Everything the tool has learned (merchant categories, vendor
        aliases, FX means) grouped by table, for the SPA memory screen.
        ?unvalidated=1 filters the categories table to rows no human has
        validated yet. build_memory_view is already a JSON-safe dict;
        jsonable_encoder is kept for symmetry with the other routes.
        Note item M1: the merchant registry rides along so `by_vendor[]`
        can say which category a vendor's receipts will actually read."""
        with open_store() as store:
            merchants = (store.get_settings() or {}).get("merchants")
        return JSONResponse(
            jsonable_encoder(build_memory_view(
                app.state.learning_db_path,
                unvalidated_only=bool(unvalidated),
                merchants=merchants,
            ))
        )

    def _memory_row_key(body: dict) -> tuple[str, str]:
        """(entity, vendor_norm) for the per-row memory endpoints; an
        empty vendor_norm means the input failed normalization."""
        from ..learning import normalize_vendor

        legal_entity_id = str((body or {}).get("legal_entity_id") or "").strip()
        vendor_norm = normalize_vendor(str((body or {}).get("vendor") or ""))
        return legal_entity_id, vendor_norm

    @app.put("/api/memory/categories")
    async def api_memory_set_category(request: Request):
        """Single-row upsert — the HTTP twin of CLI `memory set` (note 10:
        "this must be validated and adjustable"). Same validation, and the
        write is count-preserving (an operator correction is not another
        independent confirmation)."""
        from ..learning import LearningStore

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object", "code": "invalid_body"},
                                status_code=400)
        legal_entity_id, vendor_norm = _memory_row_key(body)
        category = str(body.get("category") or "").strip()
        # Absent key = leave the stored posting account alone (a category-
        # only edit must not silently wipe what the COA gate depends on);
        # an explicit empty value clears it.
        keep_account = "zoho_account" not in body
        zoho_account = str(body.get("zoho_account") or "").strip() or None
        if not legal_entity_id or not vendor_norm:
            return JSONResponse(
                {"error": "legal_entity_id and a non-empty vendor are "
                          "required", "code": "memory_row_key_required"},
                status_code=400)
        if not category:
            return JSONResponse(
                {"error": "category is required",
                 "code": "category_required"},
                status_code=400)
        # Two vocabularies are live at once, so this accepts both and
        # refuses neither (`category_vocabulary`). A value from neither is
        # DROPPED and named under `ignored`, never written: this row is
        # durable memory consulted ahead of the model on every later run,
        # and a string the tool cannot match would sit in it looking like a
        # decision somebody made. The stored row is left exactly as it was.
        stored_category = recognize_category(category)
        with LearningStore(app.state.learning_db_path) as s:
            if stored_category is not None:
                s.set_merchant_category_manual(
                    legal_entity_id, vendor_norm, stored_category,
                    zoho_account, _now_iso(), keep_account=keep_account,
                )
            row = s.get_merchant_category(legal_entity_id, vendor_norm)
        reply = {
            "ok": True, "entity": legal_entity_id, "vendor": vendor_norm,
            "category": row.category if row else "",
            "zoho_account": (row.zoho_account or "") if row else "",
            "count": row.decision_count if row else 0,
            "source_run": row.source_run if row else "",
        }
        if stored_category is None:
            reply["ignored"] = {"category": category}
        return JSONResponse(reply)

    @app.delete("/api/memory/categories")
    async def api_memory_delete_category(request: Request):
        """Drop ONE learned category row; the vendor's aliases / FX rows
        stay (forget is the sweep-everything sibling)."""
        from ..learning import LearningStore

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object", "code": "invalid_body"},
                                status_code=400)
        legal_entity_id, vendor_norm = _memory_row_key(body)
        if not legal_entity_id or not vendor_norm:
            return JSONResponse(
                {"error": "legal_entity_id and a non-empty vendor are "
                          "required", "code": "memory_row_key_required"},
                status_code=400)
        with LearningStore(app.state.learning_db_path) as s:
            existed = s.delete_merchant_category(legal_entity_id, vendor_norm)
        if not existed:
            return JSONResponse(
                {"error": "no learned category for that entity + vendor",
                 "code": "memory_category_not_found"},
                status_code=404)
        return JSONResponse({
            "ok": True, "entity": legal_entity_id, "vendor": vendor_norm,
            "deleted": True,
        })

    @app.post("/api/memory/categories/validate")
    async def api_memory_validate_categories(request: Request):
        """Bulk human sign-off: stamp validated_at/validated_by on the
        given {legal_entity_id, vendor} rows."""
        from ..learning import LearningStore, normalize_vendor

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object", "code": "invalid_body"},
                                status_code=400)
        rows = body.get("rows")
        if not isinstance(rows, list) or not rows:
            return JSONResponse(
                {"error": "rows must be a non-empty list of "
                          "{legal_entity_id, vendor}",
                 "code": "memory_rows_required"}, status_code=400)
        pairs: list[tuple[str, str]] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            entity = str(r.get("legal_entity_id") or "").strip()
            vendor = normalize_vendor(str(r.get("vendor") or ""))
            if entity and vendor:
                pairs.append((entity, vendor))
        if not pairs:
            return JSONResponse(
                {"error": "no valid rows in the list",
                 "code": "memory_rows_invalid"}, status_code=400)
        with LearningStore(app.state.learning_db_path) as s:
            n = s.validate_merchant_categories(
                pairs, _now_iso(), _operator()
            )
        return JSONResponse({"ok": True, "validated": n,
                             "requested": len(pairs)})

    @app.post("/api/memory/forget")
    async def api_memory_forget(request: Request):
        """Drop everything learned for one merchant in one entity so next
        month stops auto-filling it. Same {legal_entity_id, vendor} body
        and {ok, forgotten: <per-table delete counts>} reply as the
        workbench's /api/runs/{id}/forget."""
        body = await request.json()
        legal_entity_id = (body.get("legal_entity_id") or "").strip()
        vendor = (body.get("vendor") or "").strip()
        if not legal_entity_id or not vendor:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        forgotten = forget_memory_vendor(
            app.state.learning_db_path, legal_entity_id, vendor
        )
        return JSONResponse({"ok": True, "forgotten": forgotten})

    @app.post("/api/runs/{run_id}/decisions/confirm-matched")
    def post_confirm_matched(run_id: str, request: Request):
        # PR A — one click confirms matched pairs with their auto-picked
        # receipt. Item 101 (2026-09-17): only the pairs the owner's rule
        # lets through without a closer look (`confirmable_pair`: exact,
        # one candidate, vendor 75+, not borrowed / held / rejected, the
        # reviewer's turn), never a booked row, whatever the category says.
        # The raw matched list confirmed 27 booked July rows and August's
        # vendor-40 BASE44 pair. Read off the payload GET serves, so
        # `summary.n_confirm_matched` is exactly what this writes. Ordinary
        # reviewer confirms; never stomps an explicit verdict.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            view = _workbench_view(store, run)
            autopick = dict(matched_autopick_decisions(run, decisions))
            pairs = confirm_matched_pairs(view["rows"], autopick)
            # The reviewer's-turn rows the rule left for a person.
            n_decide = sum(1 for r in view["rows"] if r.get("turn") == TURN_DECIDE)
            skipped_rule = max(n_decide - len(pairs), 0)
            remaining = 0
            if len(pairs) > _BULK_DECISION_LIMIT:
                remaining = len(pairs) - _BULK_DECISION_LIMIT
                pairs = pairs[:_BULK_DECISION_LIMIT]
            confirmed = 0
            # Item 104: `decisions` above is the pre-write snapshot, so it
            # is what each line's "old" comes from.
            history = []
            who, at = _history_who(request), _now_iso()
            for tx_id, doc_id in pairs:
                # R4: a pair whose receipt another run settled meanwhile is
                # skipped, not confirmed onto a receipt this month no
                # longer holds; the next re-match re-sorts the row.
                if sync_claim_for_decision(
                    store, run, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                ) is not None:
                    continue
                store.set_decision(
                    run_id, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                )
                history.append(_decision_entry(
                    run_id, tx_id, decisions.get(tx_id), STATUS_CONFIRMED,
                    doc_id, who=who, at=at, trigger=dh.TRIGGER_BULK,
                ))
                confirmed += 1
            _append_history(store, history)
            view = _workbench_view(store, run)
        return JSONResponse(jsonable_encoder({
            "ok": True,
            "confirmed": confirmed,
            "remaining": remaining,
            "skipped_rule": skipped_rule,
            "summary": view["summary"],
        }))

    @app.post("/api/runs/{run_id}/decisions/confirm-ready")
    def post_confirm_ready(run_id: str, request: Request):
        # Safe "Confirm all Ready" (2026-07-27): confirms ONLY the rows the
        # server classifies review.state == "ready" (reconciled, categorized
        # from a trusted tier, no category/account disagreement), each with the
        # matcher's own auto-picked receipt. Check / pick / none rows and any
        # already-decided row are never touched, so a bulk confirm can only
        # ratify rows that need no further work. Reversible in-app (re-POST the
        # row pending) until the run is exported. When more than the per-call
        # cap are eligible, confirm the cap and report the remainder rather
        # than silently truncating.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            pairs = ready_confirm_pairs(run, decisions, overrides)
            remaining = 0
            if len(pairs) > _BULK_DECISION_LIMIT:
                remaining = len(pairs) - _BULK_DECISION_LIMIT
                pairs = pairs[:_BULK_DECISION_LIMIT]
            confirmed = 0
            history = []
            who, at = _history_who(request), _now_iso()
            for tx_id, doc_id in pairs:
                # R4: skip a pair whose receipt another run settled
                # meanwhile (see confirm-matched).
                if sync_claim_for_decision(
                    store, run, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                ) is not None:
                    continue
                store.set_decision(
                    run_id, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                )
                history.append(_decision_entry(
                    run_id, tx_id, decisions.get(tx_id), STATUS_CONFIRMED,
                    doc_id, who=who, at=at, trigger=dh.TRIGGER_BULK,
                ))
                confirmed += 1
            _append_history(store, history)
            view = _run_view(store, run)
        return JSONResponse(jsonable_encoder({
            "ok": True,
            "confirmed": confirmed,
            "remaining": remaining,
            "summary": view["summary"],
        }))

    @app.post("/api/runs/{run_id}/decisions/bulk")
    async def post_bulk_decisions(run_id: str, request: Request):
        """Confirm or reject a named set of charges in one call (2026-07-22).

        The review bucket held 34 rows on the real April run and could only
        be cleared one row at a time. The client sends the ids it is acting
        on, so the scope is explicit and auditable rather than the server
        guessing "everything that looks like this". Confirming uses each
        charge's own top candidate and skips any charge without one, and
        (item 101) any charge booked in the workbook, which never offers
        Confirm. Rejecting is unchanged.
        """
        body = await request.json()
        tx_ids = body.get("transaction_ids")
        status = body.get("status")
        if not isinstance(tx_ids, list) or not tx_ids:
            return JSONResponse(
                {"error": "transaction_ids must be a non-empty list",
                 "code": "transaction_ids_required"},
                status_code=400,
            )
        if status not in VALID_STATUSES:
            return JSONResponse(
                {"error": f"status must be one of {sorted(VALID_STATUSES)}",
                 "code": "invalid_decision_status",
                 "allowed": sorted(VALID_STATUSES)},
                status_code=400,
            )
        tx_ids = [str(t) for t in tx_ids]
        if len(tx_ids) > _BULK_DECISION_LIMIT:
            return JSONResponse(
                {"error": f"at most {_BULK_DECISION_LIMIT} rows per call",
                 "code": "too_many_rows", "limit": _BULK_DECISION_LIMIT},
                status_code=400,
            )
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            writes = bulk_decisions(run, decisions, tx_ids, status)
            updated = 0
            history = []
            who, at = _history_who(request), _now_iso()
            for tx_id, doc_id in writes:
                # R4: a write whose receipt another run settled meanwhile
                # is skipped, and lands in `skipped` below.
                if sync_claim_for_decision(
                    store, run, tx_id, status, doc_id, _now_iso()
                ) is not None:
                    continue
                store.set_decision(run_id, tx_id, status, doc_id, _now_iso())
                history.append(_decision_entry(
                    run_id, tx_id, decisions.get(tx_id), status, doc_id,
                    who=who, at=at, trigger=dh.TRIGGER_BULK,
                ))
                updated += 1
            _append_history(store, history)
            view = _run_view(store, run)
        # `skipped` is the honest half of the count: rows already decided,
        # (when confirming) rows with no candidate to confirm against, or
        # rows whose receipt another batch settled first.
        return JSONResponse(jsonable_encoder({
            "ok": True,
            "updated": updated,
            "skipped": len(tx_ids) - updated,
            "summary": view["summary"],
        }))

    # -- decision history (item 104) ---------------------------------------
    #
    # Read the month's ledger, and put one line back. Both are scoped to a
    # run: the history is a month's story, and that is the page it is read
    # on. A month with no recorded change answers `entries: []`, which is
    # the honest answer for every month that existed before this shipped --
    # nothing was recorded then, and nothing is invented now.

    @app.get("/api/runs/{run_id}/history")
    def api_run_history(
        run_id: str,
        limit: int = 200,
        before_id: int | None = None,
        row_key: str | None = None,
    ):
        """Newest first. `row_key` narrows to one charge's own story (the
        per-row fold); `before_id` pages further back."""
        limit = max(1, min(int(limit or 200), 500))
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            # One more than asked for, then trimmed: that is the only way
            # `has_more` can be a fact rather than a guess. Comparing the
            # page size to the limit says "maybe" and reads as "yes",
            # which hands the reader a next page that is empty.
            rows = store.list_history(
                run_id, limit=limit + 1, before_id=before_id, row_key=row_key
            )
            has_more = len(rows) > limit
            rows = rows[:limit]
            total = store.count_history(run_id, row_key=row_key)
        entries = [dh.view_entry(r) for r in rows]
        return JSONResponse(jsonable_encoder({
            "run_id": run_id,
            "entries": entries,
            "n_entries": total,
            "has_more": has_more,
        }))

    @app.post("/api/runs/{run_id}/history/{entry_id}/undo")
    async def api_run_history_undo(run_id: str, entry_id: int, request: Request):
        """Put one recorded change back.

        Refused (409) unless the row still holds exactly what this line left
        there. A history line says "A became B"; undoing it writes A, and if
        something has moved the row to C since, writing A would throw that
        later work away without telling anyone. The reader gets
        `history_superseded` and can look at what happened after instead.

        The undo is itself a change, so it appends its own line (trigger
        `undo`) and stamps the original as undone. Nothing is ever erased.
        """
        who = _history_who(request)
        now = _now_iso()
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            entry_row = store.get_history_entry(entry_id)
            if entry_row is None or entry_row["run_id"] != run_id:
                return JSONResponse(
                    {"error": "history entry not found", "code": "history_entry_not_found"},
                    status_code=404,
                )
            # The sentinel needs no separate arm: it compares unequal to
            # every recorded value, so `undo_conflict` already answers
            # `history_superseded` for it.
            current = _current_history_value(store, run, entry_row)
            conflict = dh.undo_conflict(entry_row, current)
            if conflict is not None:
                return JSONResponse(
                    {"error": _HISTORY_UNDO_REFUSALS[conflict], "code": conflict,
                     "entry_id": entry_id},
                    status_code=409,
                )
            old = dh.decode(entry_row["old_value"])
            err, restored = _apply_history_undo(store, run, entry_row, old, now)
            if err is not None:
                # Every refusal on this path is a `Refusal`, which IS a str,
                # so the type cannot tell them apart; the CODE can. A
                # cross-run claim conflict answers 409, the same status the
                # original confirm answers for the same condition, which is
                # what the contract and the SPA prompt both promise.
                code = code_of(err, "request_refused")
                return JSONResponse(
                    {"error": str(err), "code": code, "entry_id": entry_id,
                     **fields_of(err)},
                    status_code=409 if code in _HISTORY_UNDO_CONFLICT_CODES else 400,
                )
            # Stamped AFTER the write landed, so a line can never read
            # "undone" over a value that was not put back. Writing the same
            # old value twice is the same state, so the losing side of a
            # double click costs one no-op write and records nothing (the
            # append below sees no change and makes no line).
            store.mark_history_undone(entry_id, undone_at=now, undone_by=who)
            _append_history(store, [dh.make_entry(
                run_id=run_id, row_key=entry_row["row_key"],
                row_kind=entry_row["row_kind"], field=entry_row["field"],
                old=dh.decode(entry_row["new_value"]), new=restored,
                who=who, at=now, trigger=dh.TRIGGER_UNDO,
                detail=dh.decode(entry_row.get("detail")),
            )])
            view = _run_view(store, run)
        return JSONResponse(jsonable_encoder({
            "ok": True, "entry_id": entry_id, "summary": view["summary"],
        }))

    @app.post("/api/runs/{run_id}/categories")
    async def post_category(run_id: str, request: Request):
        body = await request.json()
        document_id = body.get("document_id")
        line_index = body.get("line_index")
        category = body.get("category")
        zoho_account = body.get("zoho_account")
        # Item 70: `line_index` absent or null reclassifies the WHOLE receipt
        # (the SPA sent 0 and a 33-line receipt came out reading two
        # categories). An explicit int keeps the per-line edit it always was.
        if (
            not document_id
            or isinstance(line_index, bool)
            or (line_index is not None and not isinstance(line_index, int))
        ):
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        # The same three-way reading the charge and expense-field routes
        # use. An explicit clear ("" or null) clears BOTH stored values, so
        # the tool's own answer shows again; it is still her act, so it is
        # written as human. A value from neither vocabulary is dropped and
        # named under `ignored`, and the stored pick is left alone: this
        # route used to store any string it was sent, which a later run's
        # learning would then read as a category somebody chose.
        category_text = "" if category is None else str(category).strip()
        if category_text:
            category = recognize_category(category_text)
            if category is None:
                return JSONResponse(
                    {"ok": True, "ignored": {"category": category_text}})
        else:
            category = None
            zoho_account = None
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            rec = category_edit_receipt(store, run, document_id)
            if line_index is None:
                if rec is None:
                    return JSONResponse(
                        {"error": "unknown expense", "code": "expense_not_found"}, status_code=404
                    )
                indices = list(range(len(rec.line_items))) or [0]  # every line
            else:
                indices = [line_index]
            overrides = store.get_category_overrides(run_id)
            now = _now_iso()
            # Item 104. One line per LINE that actually moves: a whole-
            # receipt reclassify to the category it already had records
            # nothing, and one that changes 33 lines records 33, which is
            # what happened. `bulk` when the edit covered the receipt.
            history = []
            who = _history_who(request)
            trigger = dh.TRIGGER_CLICK if line_index is not None else dh.TRIGGER_BULK
            for i in indices:
                base = (
                    rec.line_items[i].categorization
                    if rec is not None and 0 <= i < len(rec.line_items)
                    else None
                )
                # A changed category drops the account chosen for the old
                # one; an explicit account, or an unchanged category, keeps.
                account = category_edit_account(
                    category, zoho_account, overrides.get((document_id, i)), base
                )
                store.set_category_override(
                    run_id, document_id, i, category, account, now,
                    # This route IS the category picker: the category in the
                    # body is the one she chose.
                    category_source=CATEGORY_SOURCE_HUMAN,
                )
                history.append(dh.make_entry(
                    run_id=run_id, row_key=document_id,
                    row_kind=dh.ROW_RECEIPT, field=dh.FIELD_RECEIPT_CATEGORY,
                    old=_category_value(overrides.get((document_id, i))),
                    new=_category_value(
                        {"category": category, "zoho_account": account}
                    ),
                    who=who, at=now, trigger=trigger,
                    detail={
                        "document_id": document_id, "line_index": i,
                        # Whose category the row held BEFORE this edit, so an
                        # undo restores the provenance along with the value
                        # instead of promoting a model guess to her word.
                        # `_category_value` deliberately holds two keys only
                        # (the undo guard compares it), so provenance travels
                        # in `detail`.
                        "old_category_source": _old_category_source(
                            overrides.get((document_id, i))
                        ),
                    },
                ))
            _append_history(store, history)
        return JSONResponse({"ok": True})

    @app.put("/api/runs/{run_id}/charges/{transaction_id}/category")
    async def put_charge_category(
        run_id: str, transaction_id: str, request: Request
    ):
        """Item 109: the category on a charge that has no receipt.

        {"category": "<one of the eight>", "zoho_account": "<optional>"};
        category null / "" clears the pick and the tool's guess shows again.
        The sibling of the per-receipt category routes, writing the same
        `category_overrides` table under the charge's own pseudo-receipt id,
        so the CSV, the journal and the report carry it and sign-off teaches
        it under the bank's description."""
        body = await request.json()
        raw = (body or {}).get("category")
        category = "" if raw is None else str(raw).strip()
        zoho_account = str((body or {}).get("zoho_account") or "").strip()
        # Both vocabularies are accepted; a value from neither is dropped and
        # named under `ignored` rather than refused. Dropped means the stored
        # pick is LEFT ALONE, not cleared: clearing on an unrecognised string
        # would destroy a reviewer's earlier choice to honour a client bug.
        stored_category = recognize_category(category) if category else ""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            if stored_category is None:
                view = build_view(
                    run, store.get_decisions(run_id),
                    store.get_category_overrides(run_id),
                    store.get_duplicate_resolutions(run_id),
                )
                return JSONResponse({
                    "ok": True, "summary": view["summary"],
                    "ignored": {"category": category},
                })
            category = stored_category
            # Item 104: the override this write replaces, read first.
            charge_key = charge_category_key(transaction_id)
            before_cat = _category_value(
                store.get_category_overrides(run_id).get(charge_key)
            )
            err = set_charge_category(
                store, run, transaction_id, category or None,
                zoho_account or None, _now_iso(),
            )
            if err is not None:
                code = 404 if err == "unknown charge" else 400
                return JSONResponse(
                    {"error": err, "code": code_of(err, "request_refused"),
                     **fields_of(err)},
                    status_code=code,
                )
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
            _append_history(store, [dh.make_entry(
                run_id=run_id, row_key=transaction_id,
                row_kind=dh.ROW_CHARGE, field=dh.FIELD_CHARGE_CATEGORY,
                old=before_cat,
                new=_category_value(overrides.get(charge_key)),
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
                detail={"document_id": charge_key[0],
                        "line_index": charge_key[1]},
            )])
        view = build_view(run, decisions, overrides, resolutions)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    @app.post("/api/runs/{run_id}/manual-match")
    async def post_manual_match(run_id: str, request: Request):
        # PR B — assign a receipt to a charge by hand. Recorded as a
        # confirmed decision with the chosen document; the chosen receipt
        # may currently be auto-matched elsewhere (stealing it frees that
        # charge via apply_decisions' two-pass resolution).
        body = await request.json()
        tx_id = body.get("transaction_id")
        document_id = body.get("document_id")
        if not tx_id or not document_id:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            err = validate_manual_match(run, tx_id, document_id)
            if err:
                return _refused(err)
            # R4: an in-run steal is fine (apply_decisions frees the other
            # charge); a CROSS-run steal is refused -- the receipt already
            # settles a charge in another batch.
            before = store.get_decisions(run_id).get(tx_id)
            conflict = sync_claim_for_decision(
                store, run, tx_id, STATUS_CONFIRMED, document_id, _now_iso()
            )
            if conflict is not None:
                return _refused(conflict, status=409)
            store.set_decision(
                run_id, tx_id, STATUS_CONFIRMED, document_id, _now_iso()
            )
            _append_history(store, [_decision_entry(
                run_id, tx_id, before, STATUS_CONFIRMED, document_id,
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
            )])
            view = _run_view(store, run)
        return JSONResponse(jsonable_encoder({"ok": True, "summary": view["summary"]}))

    @app.post("/api/runs/{run_id}/transactions/{transaction_id}/receipt")
    async def post_manual_receipt(
        run_id: str, transaction_id: str, request: Request
    ):
        # Owner directive 2026-07-24: some receipts reach Criss by email,
        # not through the Zoho ER export, so their charges sit in
        # unmatched with nothing to pair. Upload one against a specific
        # charge; it joins the run's receipt pool and the pair is
        # recorded as a confirmed decision (same path as manual match).
        form = await request.form()
        upload = form.get("file")
        if upload is None or not getattr(upload, "filename", None):
            return JSONResponse({"error": "file required", "code": "file_required"}, status_code=400)
        data = await upload.read()
        filename = upload.filename
        # Read off the request before the work hands itself to the threadpool.
        attach_who = _history_who(request)

        # Off the event loop: since item 66 attach_emailed_receipt takes the
        # batch writer lock to commit against a fresh re-read, and an OCR
        # ingest can hold that lock for MINUTES. Blocking on it here would park
        # the loop and stop every endpoint including /healthz, so Fly's health
        # check fails and the restart kills that same ingest. The form read
        # above has to be awaited, so the handler stays async and hands the
        # locked span to the threadpool, exactly as post_restore_set_aside and
        # post_batch_cards do. See tests/test_web_batch_lock_threadpool.py.
        def _work():
            with open_store() as store:
                run = store.get_run(run_id)
                if run is None:
                    return JSONResponse(
                        {"error": "run not found", "code": "run_not_found"}, status_code=404
                    )
                before = store.get_decisions(run_id).get(transaction_id)
                err, document_id = attach_emailed_receipt(
                    store, run, transaction_id, filename, data, _now_iso()
                )
                if err:
                    return _refused(err)
                # Item 104: the attach records a confirmed decision against
                # the new document (service.attach_emailed_receipt), so the
                # charge changed verdict and owner without a trace until now.
                _append_history(store, [_decision_entry(
                    run_id, transaction_id, before, STATUS_CONFIRMED,
                    document_id, who=attach_who, at=_now_iso(),
                    trigger=dh.TRIGGER_CLICK,
                )])
                run = store.get_run(run_id)  # snapshot changed above
                view = _run_view(store, run)
            return JSONResponse(jsonable_encoder(
                {"ok": True, "document_id": document_id,
                 "summary": view["summary"]}
            ))

        return await run_in_threadpool(_work)

    @app.post("/api/runs/{run_id}/receipts/folder")
    async def post_receipts_folder(
        run_id: str, background: BackgroundTasks, request: Request
    ):
        # Bulk digital-receipt folder upload (2026-07-27). Criss drops a whole
        # folder (or a .zip) of receipts she only has digitally; each is OCR'd
        # and the matcher proposes pairings against the run's not-yet-decided
        # charges, WITHOUT disturbing confirmed / rejected / posted work. Heavy
        # (vision per file), so it runs in the background: returns {job_id}, the
        # SPA polls GET /jobs/{id} and reloads the run on done. Raw uploads are
        # spooled to a staging dir the job consumes and deletes.
        with open_store() as store:
            run = store.get_run(run_id)
        if run is None:
            return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)

        form = await request.form()
        uploads = [
            u for u in form.getlist("files") if getattr(u, "filename", None)
        ]
        one = form.get("file")  # tolerate the singular field name too
        if one is not None and getattr(one, "filename", None):
            uploads.append(one)
        if not uploads:
            return JSONResponse({"error": "no files uploaded", "code": "no_files_uploaded"}, status_code=400)

        job_id = uuid.uuid4().hex[:12]
        staging = Path(run.work_dir) / f"folder-staging-{job_id}"
        staging.mkdir(parents=True, exist_ok=True)
        saved = 0
        for i, up in enumerate(uploads):
            data = await up.read()
            if not data:
                continue
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(up.filename).name) or "file"
            (staging / f"{i:04d}__{safe}").write_bytes(data)
            saved += 1
        if saved == 0:
            shutil.rmtree(staging, ignore_errors=True)
            return JSONResponse(
                {"error": "all uploaded files were empty", "code": "all_files_empty"}, status_code=400
            )

        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_folder_job, app.state.db_path, job_id, run_id, staging
        )
        return JSONResponse({"ok": True, "job_id": job_id, "n_files": saved})

    @app.get("/api/runs/{run_id}/receipts/{document_id:path}/image")
    def receipt_image(
        run_id: str,
        document_id: str,
        as_: str | None = Query(default=None, alias="as"),
        page: int = Query(default=0, ge=0),
    ):
        # Receipt preview (owner directive 2026-07-25): a reviewer working
        # the needs-review queue gets a quick look at the actual receipt.
        # Serves the vision-mapped page of the uploaded ER PDF (rendered to
        # PNG) or an operator-uploaded manual receipt file, straight from
        # the run's work dir. 404 whenever no image is attributable — the
        # SPA keys its preview control off `receipt_image_available`.
        #
        # `?as=png` (backlog item 178) renders the stored file to a raster
        # instead of handing back its own bytes, because 70 of September's
        # 75 receipts are PDFs and a PDF cannot go in an <img>. Without it
        # the only thing a viewer can do with a receipt is download it,
        # which is feedback note #3 word for word. `?page=N` picks the page
        # and `X-Receipt-Pages` says how many there are. No param means the
        # old behaviour exactly, so nothing that works today changes.
        with open_store() as store:
            run = store.get_run(run_id)
        if run is None:
            return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
        work_dir = Path(run.work_dir)

        want_png = (as_ or "").lower() == "png"

        def serve(target: Path) -> Response:
            """The one place a receipt file becomes an HTTP response."""
            pages = page_count(target) if want_png else 1
            headers = {"X-Receipt-Pages": str(pages)}
            if want_png and is_pdf(target):
                try:
                    png = render_page_png(target, page)
                except ReceiptRenderError as exc:
                    log.warning(
                        "receipt render failed for %s page %s: %s",
                        target.name, page, exc,
                    )
                    # Fall back to the stored bytes rather than 404: a
                    # reviewer who can download the receipt is better off
                    # than one told it does not exist.
                    return FileResponse(
                        target,
                        media_type=guess_media_type(target),
                        headers={"X-Receipt-Render": "failed"},
                    )
                return Response(
                    png,
                    media_type="image/png",
                    headers={
                        **headers,
                        "Cache-Control": "private, max-age=86400",
                    },
                )
            return FileResponse(
                target, media_type=guess_media_type(target), headers=headers
            )

        if document_id.startswith("manual:"):
            tx_part = document_id[len("manual:"):]
            fs_tx = re.sub(r"[^A-Za-z0-9._-]", "_", tx_part)
            folder = work_dir / "manual-receipts"
            hits = sorted(folder.glob(f"{fs_tx}__*")) if folder.is_dir() else []
            if not hits:
                return JSONResponse(
                    {"error": "no receipt image", "code": "receipt_image_not_found"}, status_code=404
                )
            return serve(hits[0])

        if document_id.startswith("folder:"):
            # Bulk folder receipt (2026-07-27): the file is stored under
            # folder-receipts/ named by its content hash (the id after the
            # prefix), so glob it back the same way the manual branch does.
            digest = document_id[len("folder:"):]
            fs_digest = re.sub(r"[^A-Za-z0-9._-]", "_", digest)
            folder = work_dir / "folder-receipts"
            hits = sorted(folder.glob(f"{fs_digest}__*")) if folder.is_dir() else []
            if not hits:
                return JSONResponse(
                    {"error": "no receipt image", "code": "receipt_image_not_found"}, status_code=404
                )
            return serve(hits[0])

        if run_mode(run) == MODE_EXPENSE_GENERATION:
            # Expense batch (receipt-first): document ids ARE filenames
            # under the batch's receipts dir. Resolve inside it only —
            # never follow a crafted id out of the run's tree.
            exp_dir = (work_dir / "receipts").resolve()
            try:
                target = (exp_dir / document_id).resolve()
                if exp_dir in target.parents and target.is_file():
                    return serve(target)
            except (OSError, ValueError):
                pass
            return JSONResponse({"error": "no receipt image", "code": "receipt_image_not_found"}, status_code=404)

        receipts = [
            receipt_from_dict(x) for x in run.snapshot.get("receipts", [])
        ]
        rec = next(
            (r for r in receipts if r.document_id == document_id), None
        )
        if rec is None or rec.receipt_image_page is None:
            return JSONResponse({"error": "no receipt image", "code": "receipt_image_not_found"}, status_code=404)
        rcpt_rel = ((run.config or {}).get("receipts") or {}).get("path") or ""
        pdf_path = work_dir / rcpt_rel
        if not rcpt_rel or not pdf_path.is_file():
            return JSONResponse(
                {"error": "report file missing", "code": "report_file_missing"}, status_code=404
            )
        png = render_receipt_page(pdf_path, rec.receipt_image_page)
        if png is None:
            return JSONResponse({"error": "no receipt image", "code": "receipt_image_not_found"}, status_code=404)
        # Immutable per run: the snapshot never re-maps pages after creation.
        return Response(
            png,
            media_type="image/png",
            headers={"Cache-Control": "private, max-age=86400"},
        )

    # ── Receipt-first expense batches (Phase 4, behind the env flag) ────
    # The decoupled upload step (Dirk's note #1): receipts are their own
    # top-level object, not an attachment to a statement run. Every route
    # below 404s while EXPENSE_RECON_RECEIPT_FIRST is unset, so a deploy
    # changes nothing until the flag flips.

    def _flag_off() -> JSONResponse:
        return JSONResponse({"error": "not found", "code": "not_found"}, status_code=404)

    def _expense_run_or_error(store: RunStore, run_id: str):
        """(run, None) for an expense batch; (None, response) otherwise."""
        run = store.get_run(run_id)
        if run is None:
            return None, JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
        if run_mode(run) != MODE_EXPENSE_GENERATION:
            return None, JSONResponse(
                {"error": "not an expense batch", "code": "not_an_expense_batch"}, status_code=400
            )
        return run, None

    def _paid_by_conflict(
        store: RunStore, run, document_id: str, *, marking_private: bool,
    ) -> JSONResponse | None:
        """Owner 2026-09-17: an expense is paid by a company card OR a
        private card, never both, so nobody is reimbursed for money a company
        card already paid. Marking private is refused on a row a defined
        company card paid; a company-card pick is refused on a confirmed
        private row. A row that is ALREADY private is not refused (item
        176): since `can_mark_private` went false on it, this check would
        otherwise answer a correction of who gets reimbursed with the
        company-card wording, about a row no company card paid.
        Reads the row from the grid's own view, so the refusal
        and `expenses[].can_mark_private` cannot disagree. A document the
        view does not list keeps the old behavior (no check)."""
        view = _expense_view(store, run)
        row = next(
            (e for e in view["expenses"] if e.get("document_id") == document_id),
            None,
        )
        if row is None:
            return None
        if (
            marking_private
            and not row.get("private")
            and not row.get("can_mark_private", True)
        ):
            card = row.get("card") or {}
            label = card.get("label") or card.get("key") or "a company card"
            return JSONResponse(
                {"error": f"This expense was paid with the company card "
                          f"{label}, so there is nothing to reimburse. If "
                          "someone paid with their own card, correct the "
                          "card first.",
                 "code": "company_card",
                 "card": {"key": card.get("key"), "label": card.get("label")}},
                status_code=400,
            )
        if not marking_private and row.get("private"):
            return JSONResponse(
                {"error": "This expense is marked as paid with a private card "
                          f"(reimburse {row.get('reimburse_to') or 'someone'}). "
                          "Undo that first if a company card paid.",
                 "code": "private_card"},
                status_code=400,
            )
        return None

    async def _expense_edit_reply(
        run_id: str, rematch_needed: bool, extra: dict | None = None,
        *, recategorize: str | None = None,
    ) -> JSONResponse:
        """The reply every expense-edit route gives (item 70).

        The five edit routes used to refuse a month with a statement
        (`_mutable_expense_run_or_error`, retired here): a re-match BAKES the
        overlay into the pool, so the surface stayed closed until its edits
        were reversible (PR #628's extraction baseline) and each edit that
        can move a pairing triggered the re-match it needs. This is that
        re-match. Off the event loop, because `rematch_after_change` takes
        the batch lock and can call the model; after the edit is committed;
        its result or error under `rematch`, absent when nothing re-matched.
        The summary is read AFTER it, so it describes the re-matched month.

        `recategorize` names a receipt whose company just changed: on a GL
        batch it is categorized again against the new company's leaves
        (owner decision 2026-09-24), BEFORE the re-match reads the pool. A
        failure rides back under `recategorized` like the re-match's does."""
        recategorized = None
        if recategorize:
            try:
                recategorized = await run_in_threadpool(
                    recategorize_after_entity_change,
                    app.state.db_path, app.state.learning_db_path, run_id,
                    recategorize,
                )
            except Exception as exc:  # noqa: BLE001 - the edit is already written
                recategorized = {"error": str(exc)}
        rematch = None
        if rematch_needed:
            rematch = await run_in_threadpool(
                _expense_edit_rematch,
                app.state.db_path, app.state.learning_db_path, run_id,
            )
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            view = _expense_view(store, run)
        out = {"ok": True, **(extra or {}), "summary": view["summary"]}
        if rematch is not None:
            out["rematch"] = rematch
        if recategorized is not None:
            out["recategorized"] = recategorized
        return JSONResponse(jsonable_encoder(out))

    @app.post("/api/expense-batches")
    async def post_expense_batch(
        background: BackgroundTasks,
        request: Request,
        legal_entity: str = Form(""),
        default_currency: str = Form(""),
        label: str = Form(""),
    ):
        """Upload a batch of receipts -> statement-less run + background OCR
        job. Multipart `files` (repeatable; a .zip expands); returns
        {batch_id, job_id}, the SPA polls GET /jobs/{job_id} then loads
        GET /api/expense-batches/{batch_id}."""
        if not _receipt_first_on():
            return _flag_off()
        form = await request.form()
        uploads = [
            u for u in form.getlist("files") if getattr(u, "filename", None)
        ]
        one = form.get("file")  # tolerate the singular field name too
        if one is not None and getattr(one, "filename", None):
            uploads.append(one)
        files = []
        for up in uploads:
            files.append((up.filename, await up.read()))
        # Item 38: the DECLARED batch type. Absent / "" / "company-month"
        # is a company month (the pre-split shape, byte-identical config);
        # "trip" requires an existing trip and at most one batch per trip
        # (further receipts join through POST .../receipts or the pool).
        declared = str(form.get("batch_type") or "").strip()
        trip_id = str(form.get("trip_id") or "").strip()
        if declared and declared not in (BATCH_TYPE_COMPANY, BATCH_TYPE_TRIP):
            return JSONResponse(
                {"error": "batch_type must be 'company-month' or 'trip'",
                 "code": "invalid_batch_type"},
                status_code=400,
            )
        if declared != BATCH_TYPE_TRIP and files:
            # 2026-09-08 owner directive: receipt entry is decoupled from
            # month creation. A company month is created EMPTY (the
            # container a statement lands in); receipts enter through the
            # Receipts drop page (POST /api/receipts) or by mail, and each
            # files into the month printed on it. Trip creates keep their
            # create-with-receipt shape (a trip batch exists only once a
            # receipt joins), and the mail materializer builds months
            # through the service layer, not this route.
            return JSONResponse(
                {"error": (
                    "Receipts no longer attach at month creation. Create "
                    "the month empty, then add receipts on the Receipts "
                    "page — each files into its month automatically."
                ), "code": "receipts_not_at_month_creation"},
                status_code=400,
            )
        if declared == BATCH_TYPE_TRIP:
            if not trip_id:
                return JSONResponse(
                    {"error": "trip_id is required for a trip batch",
                     "code": "trip_id_required"},
                    status_code=400,
                )
            # Single-winner batch creation: the run row only commits when
            # the OCR job does, so a store scan alone is blind for the
            # whole job. The slot is released by `_run_expense_job` (or
            # below, when the create fails before a job exists).
            with open_store() as store:
                refused = claim_trip_batch_slot(store, trip_id)
                trip_row = (
                    store.get_trip(trip_id) if refused is None else None
                )
            if refused is not None:
                return _refusal_response(refused, 409)
            if not label.strip() and trip_row is not None:
                label = trip_row.name
        elif trip_id:
            return JSONResponse(
                {"error": "trip_id only applies to batch_type 'trip'",
                 "code": "trip_id_not_allowed"},
                status_code=400,
            )
        # R4.1: the slot is claimed above and handed to `_run_expense_job`
        # below, so everything between the two has to release it on ANY
        # failure. It used to release only on `RunInputError`, and any
        # other exception (an OSError spooling the upload, a store error
        # creating the job) left the slot held for the life of the
        # process: every later create and every `DELETE /api/trips`
        # answering 409 `trip_batch_being_created` until a restart.
        # `join_trip` has had this `finally` since it was written.
        handed_off = False
        try:
            with open_store() as store:
                settings = store.get_settings()
            try:
                prepared = create_expense_batch(
                    app.state.data_root,
                    files=files,
                    legal_entity=legal_entity,
                    default_currency=default_currency,
                    label=label,
                    now_iso=_now_iso(),
                    operator=_operator(),
                    learning_db_path=app.state.learning_db_path,
                    settings=settings,
                    batch_type=declared,
                    trip_id=trip_id,
                    # A company month is a legal empty container since
                    # 2026-09-08; a trip batch still requires its first
                    # receipt (create-with-receipt or first join).
                    allow_empty=declared != BATCH_TYPE_TRIP,
                )
            except RunInputError as exc:
                return _input_refused(exc)

            job_id = uuid.uuid4().hex[:12]
            with open_store() as store:
                store.create_job(job_id, None, _now_iso())
            background.add_task(
                _run_expense_job, app.state.db_path, job_id, prepared,
                app.state.learning_db_path, app.state.data_root,
            )
            handed_off = True
        finally:
            if declared == BATCH_TYPE_TRIP and not handed_off:
                release_trip_batch_slot(trip_id)
        month = month_from_label(prepared.label)
        body = {
            "ok": True,
            "batch_id": prepared.run_id,
            "job_id": job_id,
            "label": prepared.label,
            "batch_type": declared or BATCH_TYPE_COMPANY,
            "upload_issues": prepared.upload_issues,
            "month": f"{month[0]:04d}-{month[1]:02d}" if month else None,
        }
        if declared == BATCH_TYPE_TRIP:
            # A trip is not addressed by month: no month advisory, and the
            # month field is null even when the trip NAME happens to parse
            # as one (month routing skips trip batches structurally).
            body["month"] = None
            body["trip_id"] = trip_id
        elif month is None:
            # Mailed receipts are addressed by MONTH, and this label names
            # none — the default label is a full date, which is a timestamp,
            # not a month. Say so at creation time; renaming claims.
            body["advisory"] = (
                "This batch's label does not name a month, so receipts "
                "mailed in cannot join it. Rename it to a month "
                '(for example "July 2026") and its waiting mail is '
                "added automatically."
            )
        return JSONResponse(body)

    @app.get("/api/expense-batches")
    def list_expense_batches():
        """Expense batches only (mode-filtered runs), newest first — the
        SPA's batch landing screen."""
        if not _receipt_first_on():
            return _flag_off()
        # The rows are composed INSIDE the store context: the summary is
        # derived from each batch's live overlay, which needs a live store.
        # Trip batches live on the trips list (GET /api/trips), not here:
        # the months screen stays months (item 38).
        with open_store() as store:
            batches = [
                {
                    "batch_id": r.run_id,
                    "run_id": r.run_id,
                    "label": r.label,
                    "created_at": r.created_at,
                    # Item 38, parallel scalar: constant here (trips are
                    # filtered out) but the SPA gets one vocabulary for
                    # both lists.
                    "batch_type": batch_type(r),
                    # Derived, not the frozen ingest summary: the list and
                    # the batch page must show one number (2026-08-22).
                    "summary": batch_list_summary(store, r),
                    # Lifecycle: False = still collecting receipts; True =
                    # statement attached, review lives in the workbench.
                    "has_statement": has_statement(r),
                    # Item 39 origin marker: "intake" when mail created
                    # this month itself; null otherwise (parallel field).
                    "created_by": (r.summary or {}).get("created_by"),
                }
                for r in store.list_runs()
                if (r.config or {}).get("mode") == MODE_EXPENSE_GENERATION
                and not is_trip_batch(r)
            ]
        return JSONResponse({"batches": batches})

    @app.get("/api/cards/status")
    def api_card_status():
        """The cross-month card roll-up (item 185): one line per card over
        every expense batch, each with the months it is on. The per-card
        filter the month page already has, outside the months."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            return JSONResponse(build_card_status(store))

    @app.get("/api/cost-centers/totals")
    def cost_center_totals(
        date_from: str | None = Query(default=None, alias="from"),
        date_to: str | None = Query(default=None, alias="to"),
    ):
        """The cross-month cost-center roll-up (item 47, step 5): per
        cost center, per currency, with a row count and an explicit
        unassigned bucket, over every expense batch, months and trips.
        `from` / `to` are inclusive ISO dates on the row's expense date;
        either may be omitted. The payload's `note` carries the stated
        limit: card and receipt spend only, not total project cost."""
        if not _receipt_first_on():
            return _flag_off()
        bounds: dict[str, date | None] = {}
        for key, raw in (("from", date_from), ("to", date_to)):
            text = str(raw or "").strip()
            if not text:
                bounds[key] = None
                continue
            try:
                bounds[key] = date.fromisoformat(text)
            except ValueError:
                return JSONResponse(
                    {"error": f"{key} must be a date like 2026-01-31, "
                              f"got {text!r}",
                     "code": "invalid_date", "param": key, "value": text},
                    status_code=400,
                )
        if bounds["from"] and bounds["to"] and bounds["from"] > bounds["to"]:
            return JSONResponse(
                {"error": f"from ({bounds['from']}) is after to "
                          f"({bounds['to']})",
                 "code": "date_range_reversed",
                 "from": bounds["from"].isoformat(),
                 "to": bounds["to"].isoformat()},
                status_code=400,
            )
        with open_store() as store:
            payload = build_cost_center_totals(
                store, date_from=bounds["from"], date_to=bounds["to"],
            )
        return JSONResponse(payload)

    # ── Trips (item 38): the travel half of the expense split. A trip is
    # an entity of its own — named, date-ranged, variable roster — because
    # only a human knows those, so it can never be auto-created. Its
    # expense BATCH materializes when the first receipt joins (a click on
    # a travel-pooled mail, or an upload declared batch_type=trip).

    @app.get("/api/trips")
    def list_trips():
        """Every trip, newest range first, each joined to its batch when
        one exists (`batch_id` / `summary` null until then)."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            trips = store.list_trips()
            out = [
                trip_view(store, t, find_trip_batch(store, t.trip_id))
                for t in trips
            ]
        return JSONResponse({"trips": out})

    @app.post("/api/trips")
    async def post_trip(request: Request):
        if not _receipt_first_on():
            return _flag_off()
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        cleaned, err = validate_trip_fields(payload)
        if err is not None:
            return _refused(err)
        trip_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_trip(
                trip_id=trip_id, created_at=_now_iso(), **cleaned
            )
            trip = store.get_trip(trip_id)
            view = trip_view(store, trip, None)
        return JSONResponse({"ok": True, **view})

    @app.put("/api/trips/{trip_id}")
    async def put_trip(trip_id: str, request: Request):
        """Update name / range / roster. Whole-object semantics on the
        fields it takes: `travelers` replaces the whole roster.

        R4.1: a DATE change moves which months may borrow this trip's
        receipts, so the months that overlapped the OLD range and those
        that overlap the NEW one are both owed a re-match (the union: a
        month the trip has just moved off has to let go of receipts it
        can no longer see, and a month it has just moved onto has to pick
        them up). The reply carries `months_rematched` when any ran.
        Roster and cost-center changes owe nothing, because the grid
        resolves both from the live trip on every read.

        A RENAME also re-labels the batch, so the months screen, the
        delete confirm and the `settled_by` badge on a borrowing month
        stop naming the trip's creation-time name."""
        if not _receipt_first_on():
            return _flag_off()
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json", "code": "invalid_json"}, status_code=400)
        with open_store() as store:
            current = store.get_trip(trip_id)
            if current is None:
                return _not_found("Trip not found", "trip_not_found")
            merged = {
                "name": payload.get("name", current.name),
                "start": payload.get("start", current.start_date),
                "end": payload.get("end", current.end_date),
                "travelers": payload.get("travelers", current.travelers),
                # Item 47: omitted keeps the stored value, "" clears it
                # -- the same merge semantics as every field above.
                "cost_center": payload.get(
                    "cost_center", current.cost_center
                ),
            } if isinstance(payload, dict) else None
            cleaned, err = validate_trip_fields(merged)
            if err is not None:
                return _refused(err)

        # Item 18: the rename and the owe both take the batch writer lock,
        # so the whole span runs in the threadpool. An `async def` handler
        # blocking on that lock parks the EVENT LOOP for as long as an OCR
        # ingest holds it, which stops /healthz and gets the machine
        # restarted mid-ingest.
        def _apply() -> tuple[dict, list[str]]:
            with open_store() as store:
                before = store.get_trip(trip_id)
                if before is None:
                    return {}, []
                old_name = before.name
                old_range = _trip_range(before.start_date, before.end_date)
                store.update_trip(trip_id, updated_at=_now_iso(), **cleaned)
                trip = store.get_trip(trip_id)
                batch = find_trip_batch(store, trip_id)
                owed: list[str] = []
                if batch is not None:
                    if str(trip.name) != str(old_name):
                        _sync_trip_batch_label(
                            store, batch, old_name, trip.name
                        )
                        batch = store.get_run(batch.run_id) or batch
                    if (
                        cleaned["start_date"] != before.start_date
                        or cleaned["end_date"] != before.end_date
                    ):
                        new_range = _trip_range(
                            cleaned["start_date"], cleaned["end_date"]
                        )
                        owed = owe_trip_month_rematches(
                            store, batch,
                            ranges=[
                                r for r in (old_range, new_range) if r
                            ],
                        )
                return trip_view(store, trip, batch), owed

        view, owed = await run_in_threadpool(_apply)
        if not view:
            return _not_found("Trip not found", "trip_not_found")
        if owed:
            def _pay() -> list[dict]:
                with open_store() as store:
                    return rematch_trip_months(
                        store, owed,
                        learning_db_path=app.state.learning_db_path,
                    )

            paid = await run_in_threadpool(_pay)
            if paid:
                view = {**view, "months_rematched": paid}
        return JSONResponse({"ok": True, **view})

    @app.delete("/api/trips/{trip_id}")
    def delete_trip(trip_id: str):
        """Remove a trip ENTITY. Refused while a batch references it (the
        batch holds real expenses and goes first: POST /api/runs/{id}/
        delete, then the entity) — or while one is mid-creation, which is
        the window `delete_trip_entity` serializes shut."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            refused = delete_trip_entity(store, trip_id)
        if refused is not None:
            return _refusal_response(refused, 409)
        return JSONResponse({"ok": True, "trip_id": trip_id, "deleted": True})

    @app.get("/api/expense-batches/{run_id}")
    def get_expense_batch(run_id: str):
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            return JSONResponse(jsonable_encoder(_expense_page_view(store, run)))

    @app.post("/api/expense-batches/{run_id}/receipts")
    async def post_batch_receipts(
        run_id: str, background: BackgroundTasks, request: Request
    ):
        """Add receipts to an existing batch — they arrive gradually all
        month. Multipart `files` (a .zip expands); identical bytes already
        in the pool are skipped. Background OCR job -> {job_id}, the SPA
        polls GET /jobs/{id}. Refused once a statement is attached."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
        if err is not None:
            return err

        form = await request.form()
        uploads = [
            u for u in form.getlist("files") if getattr(u, "filename", None)
        ]
        one = form.get("file")
        if one is not None and getattr(one, "filename", None):
            uploads.append(one)
        if not uploads:
            return JSONResponse({"error": "no files uploaded", "code": "no_files_uploaded"}, status_code=400)

        job_id = uuid.uuid4().hex[:12]
        staging = Path(run.work_dir) / f"add-staging-{job_id}"
        staging.mkdir(parents=True, exist_ok=True)
        saved = 0
        for i, up in enumerate(uploads):
            data = await up.read()
            if not data:
                continue
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(up.filename).name) or "file"
            (staging / f"{i:04d}__{safe}").write_bytes(data)
            saved += 1
        if saved == 0:
            shutil.rmtree(staging, ignore_errors=True)
            return JSONResponse(
                {"error": "all uploaded files were empty", "code": "all_files_empty"}, status_code=400
            )

        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_batch_receipts_job, app.state.db_path, job_id, run_id,
            staging, app.state.learning_db_path,
        )
        return JSONResponse({"ok": True, "job_id": job_id, "n_files": saved})

    @app.post("/api/receipts")
    async def post_receipts_drop(
        background: BackgroundTasks, request: Request
    ):
        """The Receipts page (2026-09-08): drop any receipts, any time —
        the ONE manual entrance for expense creation. Each file routes to
        the month printed on it (months materialize when absent,
        `created_by: "drop"`); a file with no readable date is reported
        `needs_month` and the page re-submits it with an explicit
        `month` ("YYYY-MM") override. Multipart `files` (repeatable);
        background job -> {job_id}; the SPA polls GET /jobs/{id} and
        reads the per-file ledger from the job's `result`."""
        if not _receipt_first_on():
            return _flag_off()
        from .intake_mail import valid_month_key

        form = await request.form()
        uploads = [
            u for u in form.getlist("files") if getattr(u, "filename", None)
        ]
        one = form.get("file")
        if one is not None and getattr(one, "filename", None):
            uploads.append(one)
        if not uploads:
            return JSONResponse({"error": "no files uploaded", "code": "no_files_uploaded"}, status_code=400)
        month_override = str(form.get("month") or "").strip()
        if month_override and not valid_month_key(month_override):
            return JSONResponse(
                {"error": 'month must be "YYYY-MM"', "code": "invalid_month"},
                status_code=400
            )

        job_id = uuid.uuid4().hex[:12]
        staging = Path(app.state.data_root) / "drops" / job_id
        staging.mkdir(parents=True, exist_ok=True)
        saved = 0
        for i, up in enumerate(uploads):
            data = await up.read()
            if not data:
                continue
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(up.filename).name) or "file"
            (staging / f"{i:04d}__{safe}").write_bytes(data)
            saved += 1
        if saved == 0:
            shutil.rmtree(staging, ignore_errors=True)
            return JSONResponse(
                {"error": "all uploaded files were empty", "code": "all_files_empty"}, status_code=400
            )

        # Item 114: what a restart would otherwise lose (the month pick).
        _write_drop_sidecar(
            staging, {"month": month_override, "resumed": 0,
                      "created_at": _now_iso()},
        )
        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_receipts_drop_job, app.state.db_path, job_id, staging,
            month_override, app.state.learning_db_path,
            Path(app.state.data_root),
        )
        return JSONResponse({"ok": True, "job_id": job_id, "n_files": saved})

    @app.post("/api/expense-batches/{run_id}/set-aside/restore")
    async def post_restore_set_aside(run_id: str, request: Request):
        """The set-aside strip's one-click override ("this really is a
        receipt"): body {"file": <stored name>} moves that file from the
        set-aside list into the expense pool. The stored extraction is
        reused (no fresh vision call), then the usual memory + registry +
        categorize pass runs — fast enough to answer synchronously with
        the refreshed batch view."""
        if not _receipt_first_on():
            return _flag_off()
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a plain 400
            body = None
        file = str(((body or {}).get("file")) or "").strip()
        if not file:
            return JSONResponse({"error": "file is required", "code": "file_name_required"}, status_code=400)

        # Off the event loop: restore_set_aside_file takes the batch writer
        # lock, which an OCR ingest can hold for MINUTES. Blocking on it here
        # would park the loop and stop every endpoint including /healthz, so
        # Fly's health check fails and the restart kills that same ingest.
        # The body read above has to be awaited, so the handler stays async
        # and hands the locked span to the threadpool instead of going sync
        # like delete_run. See tests/test_web_batch_lock_threadpool.py.
        def _work():
            with open_store() as store:
                run, err = _expense_run_or_error(store, run_id)
                if err is not None:
                    return err
                try:
                    result = restore_set_aside_file(
                        store, run, file, _now_iso(),
                        learning_db_path=app.state.learning_db_path,
                    )
                except RunInputError as exc:
                    return _input_refused(exc)
                run = store.get_run(run_id)
                view = _expense_view(store, run)
            return JSONResponse(jsonable_encoder({**result, "batch": view}))

        return await run_in_threadpool(_work)

    @app.post("/api/expense-batches/{run_id}/cards")
    async def post_batch_cards(run_id: str, request: Request):
        """Cards R3: operator hint -> card assignments for a batch. Body
        {"assignments": [{"hint", "card"}], "new_cards": {slug: {...}}?,
        "learn": bool} — assignments apply to THIS batch (exact hint
        strings, recorded in the batch config); `learn` additionally
        persists the hint's identifying tokens into settings["cards"] so
        the next batch resolves on its own. Generic tender words assign
        batch-only and are never learned (they identify a network, not a
        card). Answers with the refreshed batch view."""
        if not _receipt_first_on():
            return _flag_off()
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a plain 400
            body = None
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object", "code": "invalid_body"}, status_code=400)
        assignments = body.get("assignments") or []
        if not isinstance(assignments, list):
            return JSONResponse(
                {"error": "assignments must be a list",
                 "code": "invalid_body", "field": "assignments"},
                status_code=400
            )
        new_cards = body.get("new_cards")
        if new_cards is not None and not isinstance(new_cards, dict):
            return JSONResponse(
                {"error": "new_cards must be an object",
                 "code": "invalid_body", "field": "new_cards"},
                status_code=400
            )
        # Off the event loop, same reason as set-aside/restore above:
        # assign_batch_cards takes the batch writer lock.
        def _work():
            with open_store() as store:
                run, err = _expense_run_or_error(store, run_id)
                if err is not None:
                    return err
                try:
                    result = assign_batch_cards(
                        store, run,
                        assignments=assignments,
                        new_cards=new_cards,
                        learn=bool(body.get("learn")),
                        now_iso=_now_iso(),
                    )
                except RunInputError as exc:
                    return _input_refused(exc)
                run = store.get_run(run_id)
                view = _expense_view(store, run)
            return JSONResponse(jsonable_encoder({**result, "batch": view}))

        return await run_in_threadpool(_work)

    @app.post("/api/expense-batches/{run_id}/refresh-master-data")
    def post_batch_refresh_master_data(run_id: str):
        """Cards R3: re-derive this batch's snapshotted master data (cards,
        card -> account map, entity default, CoA block) from the CURRENT
        stored settings — the explicit, audited fix for the snapshot trap.
        Answers with the changes made and the refreshed batch view."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            try:
                result = refresh_batch_master_data(
                    store, run, now_iso=_now_iso(), operator=_operator()
                )
            except RunInputError as exc:
                return _input_refused(exc)
            run = store.get_run(run_id)
            view = _expense_view(store, run)
        return JSONResponse(jsonable_encoder({**result, "batch": view}))

    @app.post("/api/expense-batches/{run_id}/statement")
    async def post_batch_statement(
        run_id: str,
        background: BackgroundTasks,
        statement: UploadFile,
        account_id: str = Form(""),
        account_legal_entities: str = Form(""),
        account_card_currency: str = Form("USD"),
        sheet_name: str = Form(""),
        card_key: str = Form(""),
        map_transaction_date: str = Form(""),
        map_amount: str = Form(""),
        map_vendor: str = Form(""),
        map_posting_date: str = Form(""),
        map_transaction_currency: str = Form(""),
        map_card: str = Form(""),
        # Aliases the deployed SPA actually sends on its column-mapping
        # retry (backlog item 37: the SPA appends map_date /
        # map_description / map_currency, which this route silently
        # dropped, so the operator's column picks never reached the
        # parser). Accepted alongside the canonical names so both an
        # updated and an un-updated SPA work; canonical wins on conflict.
        map_date: str = Form(""),
        map_description: str = Form(""),
        map_currency: str = Form(""),
    ):
        """Month-end: attach the bank statement to a batch and reconcile
        it. THIS is where the card / account id is asked (never at batch
        creation). Fail-fast half (file save + column-map resolve) runs
        synchronously so a mapping problem is a form 400 with the file's
        headers; the match runs in the background -> {job_id}. On done the
        run serves the reconciliation workbench at GET /api/runs/{id}.

        Repeatable since PR 2b-2b-2: a statement arrives per card and often
        twice (a mid-month partial, then the full cycle), so this appends by
        identity rather than refusing. That is why the gate below is the
        plain expense-run check (the statement-refusing variant is retired
        since item 70) — the lift is deliberate, and pinned by
        `tests/test_living_month.py` so it cannot be reverted by accident
        either."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
        if err is not None:
            return err
        if is_trip_batch(run):
            # Item 38 ruling 3: trips DO reconcile, but through the
            # company month's statement. A statement never attaches to a
            # trip; opening that here would give one charge two competing
            # settlement homes. The cross-batch design HAS landed (R4,
            # PR #685, 2026-09-07): `trip_pool_for_month` lends this
            # trip's receipts to every overlapping month and
            # `receipt_claims` arbitrates, so the refusal below is the
            # permanent rule, not a placeholder.
            return JSONResponse(
                {"error": "statements attach to company months; a trip's "
                          "receipts reconcile against the month statement "
                          "covering the charge",
                 "code": "statement_on_trip"},
                status_code=400,
            )

        try:
            form = _parse_run_form(
                account_id=account_id,
                account_legal_entities=account_legal_entities,
                account_card_currency=account_card_currency,
                sheet_name=sheet_name,
                receipts_source="csv",
                receipts_default_currency="",
                use_llm="",
                expense_column_map="",
                map_transaction_date=map_transaction_date or map_date,
                map_amount=map_amount,
                map_vendor=map_vendor or map_description,
                map_posting_date=map_posting_date,
                map_transaction_currency=(
                    map_transaction_currency or map_currency
                ),
                map_card=map_card,
                card_key=card_key,
            )
        except RunInputError as exc:
            return _input_refused(exc)

        statement_bytes = await statement.read()
        try:
            stmt_name, column_map = prepare_statement_attach(
                run,
                statement_bytes=statement_bytes,
                statement_filename=statement.filename or "statement.csv",
                form=form,
            )
        except RunInputError as exc:
            return JSONResponse(
                {"error": exc.message, "code": exc.code, **exc.fields,
                 "headers": exc.headers},
                status_code=400,
            )

        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_attach_statement_job, app.state.db_path, job_id, run_id,
            stmt_name, column_map, form, app.state.learning_db_path,
            statement.filename or "",
        )
        return JSONResponse({"ok": True, "job_id": job_id})

    @app.post("/api/expense-batches/{run_id}/statements/reread")
    async def post_batch_statements_reread(
        run_id: str, background: BackgroundTasks,
    ):
        """Rebuild the month's charges from the statement files it already
        holds and re-match (2026-09-11). The repair for a month whose stored
        charges were parsed wrong: re-uploading the same file cannot fix it,
        because content-derived ids would fold the corrected rows in beside
        the wrong ones and double the month. Runs in the background ->
        {job_id}; poll GET /jobs/{id}. Refuses (job error, nothing written)
        when a statement file is missing, a column map no longer resolves,
        or a reviewer decision cannot be carried over by sheet row."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is None and not has_statement(run):
                err = JSONResponse(
                    {"error": "this month has no statement to re-read",
                     "code": "no_statement_to_reread"},
                    status_code=400,
                )
        if err is not None:
            return err
        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_reread_statements_job, app.state.db_path, job_id, run_id,
            app.state.learning_db_path,
        )
        return JSONResponse({"ok": True, "job_id": job_id})

    @app.put("/api/runs/{run_id}/expenses/{document_id:path}/entity")
    async def put_expense_entity(run_id: str, document_id: str, request: Request):
        """Per-expense legal-entity override — sugar over the generic field
        edit, kept as its own route per the SPA contract. Registered BEFORE
        the generic {document_id:path} PUT so `/x/entity` resolves here."""
        if not _receipt_first_on():
            return _flag_off()
        body = await request.json()
        entity = str((body or {}).get("legal_entity") or "").strip()
        if not entity:
            return JSONResponse(
                {"error": "legal_entity is required", "code": "legal_entity_required"},
                status_code=400
            )
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            before = (
                store.get_expense_field_overrides(run_id).get(document_id) or {}
            ).get("legal_entity") or ""
            store.set_expense_field_override(
                run_id, document_id, "legal_entity", entity, _now_iso()
            )
            # Matching is entity-scoped, so a changed entity can move a pair.
            rematch_needed = has_statement(run) and before != entity
        return await _expense_edit_reply(
            run_id, rematch_needed,
            recategorize=document_id if before != entity else None,
        )

    @app.post("/api/runs/{run_id}/expenses/{document_id:path}/private")
    async def post_expense_private(run_id: str, document_id: str, request: Request):
        """Item 41: confirm or clear a private expense. Body
        {"private": bool, "reimburse_to": str}. Confirming requires
        `reimburse_to` — a reimbursement owed to nobody is not a decision
        — and turns the row into a reimbursement row (person =
        reimburse_to, entity not required). `private: false` clears both
        and the suggestion returns if the payment method still resolves
        no card. Assigning a real card clears the SUGGESTION through the
        existing flow; a confirmed row stays confirmed until cleared
        here. Same mutability rule as every other expense edit."""
        if not _receipt_first_on():
            return _flag_off()
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse({"error": "invalid payload", "code": "invalid_body"}, status_code=400)
        private = bool(body.get("private"))
        reimburse_to = str(body.get("reimburse_to") or "").strip()
        if private and not reimburse_to:
            return JSONResponse(
                {"error": "reimburse_to is required to confirm a private "
                          "expense: name who gets reimbursed",
                 "code": "reimburse_to_required"},
                status_code=400,
            )
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            if private:
                conflict = _paid_by_conflict(
                    store, run, document_id, marking_private=True
                )
                if conflict is not None:
                    return conflict
            now = _now_iso()
            store.set_expense_field_override(
                run_id, document_id, "private", "1" if private else None, now
            )
            store.set_expense_field_override(
                run_id, document_id, "reimburse_to",
                reimburse_to if private else None, now
            )
        # No re-match (item 70): the private flag and who is reimbursed never
        # reach the matcher; the card chain derives a row's entity without it.
        return await _expense_edit_reply(run_id, False)

    @app.post("/api/runs/{run_id}/expenses/{document_id:path}/confirm-category")
    async def post_expense_confirm_category(
        run_id: str, document_id: str, request: Request
    ):
        """Note #62: keep the category the tool guessed from the vendor name
        (or could not explain) as the reviewer's own. Before this a right
        guess read "needs a look" until a DIFFERENT category was picked. No
        body. 400 when the category is not a guess to confirm, 404 for an
        unknown expense. Undone by the category PUT with `""`."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            # Item 104: accepting the tool's guess IS a reviewer verdict --
            # it writes an override where there was none -- so it earns a
            # line like any other category change.
            before_map = store.get_category_overrides(run_id)
            msg = confirm_expense_category(store, run, document_id, _now_iso())
            if msg == "unknown expense":
                return _refused(msg, status=404)
            if msg:
                return _refused(msg)
            _append_history(store, _receipt_category_entries(
                run_id, document_id, before_map,
                store.get_category_overrides(run_id),
                who=_history_who(request), at=_now_iso(),
                trigger=dh.TRIGGER_CLICK,
            ))
        # No re-match (item 70): a category never reaches the matcher.
        return await _expense_edit_reply(run_id, False)

    @app.put("/api/runs/{run_id}/expenses/{document_id:path}")
    async def put_expense_field(run_id: str, document_id: str, request: Request):
        """One field edit on one expense: {field, value}. Header fields land
        in expense_field_overrides; category / zoho_account fold into the
        existing line-level category_overrides (every line of the expense),
        so the export path needs no second override mechanism. value null /
        "" clears the edit."""
        if not _receipt_first_on():
            return _flag_off()
        body = await request.json()
        field = str((body or {}).get("field") or "").strip()
        raw_value = (body or {}).get("value")
        value = "" if raw_value is None else str(raw_value).strip()
        if field not in EXPENSE_HEADER_FIELDS | EXPENSE_CATEGORY_FIELDS:
            return JSONResponse(
                {"error": f"unknown field {field!r}",
                 "code": "unknown_field", "field": field},
                status_code=400
            )
        if value:
            if field == "category":
                # Both vocabularies accepted; neither refused. A value from
                # neither is dropped and named under `ignored`, leaving the
                # stored pick untouched (an empty value is the clear).
                stored_category = recognize_category(value)
                if stored_category is None:
                    return await _expense_edit_reply(
                        run_id, False, {"ignored": {"category": value}}
                    )
                value = stored_category
            err_msg = validate_expense_field(field, value)
            if err_msg:
                return _refused(err_msg)

        if field == "card_key" and value:
            # Item 87: a per-row card fix names an active registry card, which
            # may be copied into the batch's card snapshot. That write takes
            # the batch writer lock, so it runs off the event loop (item 18).
            def _prep_card():
                with open_store() as store:
                    _run, err = _expense_run_or_error(store, run_id)
                    if err is not None:
                        return err
                    conflict = _paid_by_conflict(
                        store, _run, document_id, marking_private=False
                    )
                    if conflict is not None:
                        return conflict
                    msg = prepare_row_card_fix(store, run_id, value)
                    return (
                        _refused(msg)
                        if msg else None
                    )

            card_err = await run_in_threadpool(_prep_card)
            if card_err is not None:
                return card_err

        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            rematch_needed = False
            recategorize = None
            # Item 41: a private confirmation is the PAIR (flag + who
            # gets reimbursed). This one-field-at-a-time route cannot
            # set both, so the flag alone is refused unless reimburse_to
            # is already stored — otherwise "owed to nobody" would read
            # as decided (adversarial review, 2026-09-06).
            # Item 47: an override may only name a cost center the owner
            # has DEFINED. This is the one place the name is checked,
            # because it is the one place a human is picking from a list
            # the tool showed her; the carriers (card / merchant / trip)
            # stay unvalidated so edit order cannot matter. An inactive
            # centre is accepted here on purpose: correcting history
            # onto a retired project is a legitimate edit, and only
            # DEFAULTS are barred from resurrecting one.
            if field == "cost_center" and value:
                registry = CostCenterRegistry.from_settings(
                    store.get_settings()
                )
                canon = registry.canonical(value)
                if canon is None:
                    return JSONResponse(
                        {"error": f"cost_center {value!r} is not a defined "
                                  "cost center; define it in Settings first",
                         "code": "cost_center_not_defined",
                         "cost_center": value},
                        status_code=400,
                    )
                # Store the registry's own spelling, so a picked name and
                # a typed one cannot read as two different centres.
                value = canon
            if field == "private" and value == "1":
                stored = store.get_expense_field_overrides(run_id).get(
                    document_id, {}
                )
                if not str(stored.get("reimburse_to") or "").strip():
                    return JSONResponse(
                        {"error": "confirming a private expense needs "
                                  "reimburse_to; set it first, or use "
                                  "POST .../expenses/{id}/private which "
                                  "takes both together",
                         "code": "reimburse_to_required"},
                        status_code=400,
                    )
                conflict = _paid_by_conflict(
                    store, run, document_id, marking_private=True
                )
                if conflict is not None:
                    return conflict
            if field in EXPENSE_CATEGORY_FIELDS:
                # Whole-expense category/account edit -> a category_override
                # per line. Find the expense in the EFFECTIVE receipt set so
                # a manual add is editable too; merge with any existing
                # override so setting the account never clears the category.
                receipts = baseline_receipts(run)
                field_overrides = store.get_expense_field_overrides(run_id)
                edits = store.get_expense_edits(run_id)
                overrides = store.get_category_overrides(run_id)
                default_entity = (
                    ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
                )
                effective = apply_expense_edits(
                    receipts, field_overrides, edits,
                    category_overrides=overrides, default_entity=default_entity,
                )
                rec = next(
                    (r for r in effective if r.document_id == document_id), None
                )
                if rec is None:
                    return JSONResponse(
                        {"error": "unknown expense", "code": "expense_not_found"}, status_code=404
                    )
                indices = list(range(len(rec.line_items))) or [0]
                for i in indices:
                    ov = overrides.get((document_id, i)) or {}
                    base = (
                        rec.line_items[i].categorization
                        if i < len(rec.line_items) else None
                    )
                    if field == "category":
                        category = value or None
                        # Item 70: a changed category drops the account
                        # chosen for the old one instead of keeping it.
                        account = category_edit_account(category, None, ov, base)
                        source = CATEGORY_SOURCE_HUMAN
                    else:
                        account = value or None
                        # apply_overrides only fires on an override WITH a
                        # category; carry the line's own when none is set.
                        category = ov.get("category") or (
                            base.category if base else None
                        )
                        # She fixed the ACCOUNT. The category above is only
                        # carried so `apply_overrides` fires at all, and the
                        # 2026-09-24 ruling is that it must not be taught as
                        # hers; a category she had already picked keeps its
                        # own provenance.
                        source = (
                            (ov.get("category_source") or CATEGORY_SOURCE_HUMAN)
                            if ov.get("category")
                            else CATEGORY_SOURCE_INHERITED
                        )
                    store.set_category_override(
                        run_id, document_id, i, category, account, _now_iso(),
                        category_source=source,
                    )
                # Item 104: the same differ the confirm above uses. `bulk`
                # because one PUT rewrites every line of the expense.
                _append_history(store, _receipt_category_entries(
                    run_id, document_id, overrides,
                    store.get_category_overrides(run_id),
                    who=_history_who(request), at=_now_iso(),
                    trigger=dh.TRIGGER_BULK,
                ))
            else:
                before = (
                    store.get_expense_field_overrides(run_id).get(document_id)
                    or {}
                ).get(field) or ""
                store.set_expense_field_override(
                    run_id, document_id, field, value or None, _now_iso()
                )
                # Item 70: only a field the matcher reads, and only when it
                # actually changed, pays for a re-match.
                rematch_needed = (
                    has_statement(run)
                    and field in EXPENSE_MATCH_FIELDS
                    and before != value
                )
                # Owner decision 2026-09-24: a company set (or changed) here
                # re-categorizes the receipt against that company's leaves.
                if field == "legal_entity" and before != value:
                    recategorize = document_id
        return await _expense_edit_reply(
            run_id, rematch_needed, recategorize=recategorize)

    @app.post("/api/runs/{run_id}/expenses")
    async def post_expense_add(run_id: str, request: Request):
        """Add a manual expense (Note 3: some expenses have no receipt
        file). Vendor + total required; date / currency / tax / category /
        paid_through / legal_entity optional, validated like field edits."""
        if not _receipt_first_on():
            return _flag_off()
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse({"error": "invalid payload", "code": "invalid_body"}, status_code=400)
        payload = {
            k: str(body.get(k) or "").strip()
            for k in (
                "vendor", "date", "total", "currency", "tax", "tax_label",
                "category", "zoho_account", "paid_through", "legal_entity",
                "reference", "description",
            )
            if str(body.get(k) or "").strip()
        }
        if not payload.get("vendor") or not payload.get("total"):
            return JSONResponse(
                {"error": "vendor and total are required",
                 "code": "vendor_and_total_required"},
                status_code=400
            )
        # Both vocabularies accepted; neither refused. A category from
        # neither is dropped from the payload and named under `ignored`, and
        # the expense is still added: the vendor and total are what the add
        # is for, and refusing the whole row over one field would lose them.
        dropped_category = ""
        if payload.get("category"):
            stored_category = recognize_category(payload["category"])
            if stored_category is None:
                dropped_category = payload.pop("category")
            else:
                payload["category"] = stored_category
        for f in ("date", "total", "currency", "tax"):
            if payload.get(f):
                err_msg = validate_expense_field(f, payload[f])
                if err_msg:
                    return _refused(err_msg)

        document_id = f"manual:{uuid.uuid4().hex[:12]}"
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            store.set_expense_edit(run_id, document_id, "add", payload, _now_iso())
            # Item 70: the add joins the matcher's pool on a reconciling month.
            rematch_needed = has_statement(run)
        extra: dict = {"document_id": document_id}
        if dropped_category:
            extra["ignored"] = {"category": dropped_category}
        return await _expense_edit_reply(run_id, rematch_needed, extra)

    @app.delete("/api/runs/{run_id}/expenses/{document_id:path}")
    async def delete_expense(run_id: str, document_id: str):
        """Remove one expense from the batch (soft: an edit-table row, the
        snapshot is never rewritten by the delete itself; on a reconciling
        month the re-match that follows bakes the pool without it).
        Deleting a manual add overwrites its add row, so it simply
        disappears."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            prior_edits = store.get_expense_edits(run_id)
            known = {
                r["document_id"] for r in run.snapshot.get("receipts", [])
            } | {
                e["document_id"] for e in prior_edits
            }
            if document_id not in known:
                return JSONResponse({"error": "unknown expense", "code": "expense_not_found"}, status_code=404)
            already = any(
                e["document_id"] == document_id and e["op"] == "delete"
                for e in prior_edits
            )
            store.set_expense_edit(run_id, document_id, "delete", None, _now_iso())
            # R4: a deleted expense settles nothing any more -- whichever
            # run's charge claimed this receipt releases it.
            store.delete_claims_for_receipt(run_id, document_id)
            # Item 70: the receipt leaves the matcher's pool, so its charge
            # has to be re-matched or it keeps pairing with nothing real.
            rematch_needed = has_statement(run) and not already
            # R4.1: on a TRIP that condition is never true (a trip has no
            # statement of its own), so deleting a trip receipt used to
            # tell nobody, and the month that had borrowed it kept the
            # settlement and the count. The months that borrow from this
            # trip are the ones owed the re-match, not the trip.
            owes_trip_months = is_trip_batch(run) and not already
        if owes_trip_months:
            # Item 18: this handler is `async def`, so the locked span goes
            # to the threadpool. Blocking here would park the EVENT LOOP on
            # a lock an OCR ingest can hold for minutes, stopping /healthz
            # and getting the machine restarted mid-ingest.
            def _pay_trip_debt() -> None:
                with open_store() as store:
                    fresh = store.get_run(run_id)
                    if fresh is None:
                        return
                    try:
                        owed = owe_trip_month_rematches(store, fresh)
                    except Exception:  # noqa: BLE001 - never block a delete
                        return
                    if owed:
                        rematch_trip_months(
                            store, owed,
                            learning_db_path=app.state.learning_db_path,
                        )

            await run_in_threadpool(_pay_trip_debt)
        return await _expense_edit_reply(run_id, rematch_needed)

    @app.post("/api/runs/{run_id}/expenses/{document_id:path}/move")
    def post_expense_move(
        run_id: str, document_id: str, background: BackgroundTasks,
        body: dict | None = Body(None),
    ):
        """Item 77: move one expense into the month its date names.
        Body `{month: "YYYY-MM"}`, optional: the default is the month the
        row's `month_move` offer names. Sync on purpose (the batch lock and
        the re-match of both months run here, off the event loop). A month
        created by the move claims its pooled mail afterwards, the way a
        created month always does."""
        if not _receipt_first_on():
            return _flag_off()
        month = str((body or {}).get("month") or "").strip()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            if not month:
                row = next(
                    (e for e in _expense_view(store, run)["expenses"]
                     if e.get("document_id") == document_id),
                    None,
                )
                if row is None:
                    return JSONResponse(
                        {"error": "unknown expense", "code": "expense_not_found"}, status_code=404
                    )
                month = (row.get("month_move") or {}).get("month") or ""
                if not month:
                    return JSONResponse(
                        {"error": "this expense's date is inside this month; "
                                  "name a month to move it anyway",
                         "code": "month_move_not_needed"},
                        status_code=400,
                    )
            try:
                out = move_expense_to_month(
                    store, run, document_id, month, _now_iso(),
                    data_root=Path(app.state.data_root),
                    learning_db_path=app.state.learning_db_path,
                )
            except RunInputError as exc:
                status = 404 if str(exc) == "unknown expense" else 400
                return JSONResponse(
                    {"error": str(exc), "code": exc.code, **exc.fields},
                    status_code=status,
                )
            source = store.get_run(run_id)
            if source is not None:
                out["summary"] = _expense_view(store, source)["summary"]
        if out.get("created_batch"):
            background.add_task(
                _claim_pooled_quietly, app.state.db_path,
                app.state.learning_db_path, Path(app.state.data_root),
            )
        return JSONResponse(jsonable_encoder(out))

    @app.get("/runs/{run_id}/expenses.csv")
    def download_expenses_csv(run_id: str):
        """The Zoho Books Expenses import CSV for an expense batch, with
        every reviewer edit applied — the receipt-first sibling of
        /runs/{id}/zoho.csv."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            overrides = store.get_category_overrides(run_id)
            field_overrides = store.get_expense_field_overrides(run_id)
            edits = store.get_expense_edits(run_id)
            dup_resolutions = store.get_duplicate_resolutions(run_id)
            # Item 94: a copy a reviewer hand-matched holds a charge and
            # stays listed, so the verdicts are part of the question.
            charge_decisions = store.get_decisions(run_id)
            # Note item M2: the CSV resolves a row's card through the same
            # chain the grid does, merchant card included, so the two cannot
            # name different cards for one receipt. Read inside the store
            # block, like every other input on this route.
            csv_merchants = (store.get_settings() or {}).get("merchants")
        path = regenerate_expense_export(
            run, overrides, field_overrides, edits, dup_resolutions,
            charge_decisions=charge_decisions,
            merchants=csv_merchants,
            learning_db_path=app.state.learning_db_path,
        )
        return FileResponse(
            path,
            filename=f"expenses-{run_id}.csv",
            media_type="text/csv",
        )

    @app.get("/runs/{run_id}/reconciliation-report.pdf")
    def download_reconciliation_report(run_id: str):
        """The statement reconciliation as a document: what needs attention
        first, then every charge with its receipt, then the receipts
        themselves (owner directive 2026-08-23)."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
            # Item 68: the reviewer's live overlay, the same pair the
            # expense report and the grid are built from. Without it this
            # document showed an expense the reviewer had already deleted.
            field_overrides = store.get_expense_field_overrides(run_id)
            edits = store.get_expense_edits(run_id)
            label = run.label or run_id
        pdf = build_reconciliation_report(
            run, decisions, overrides, resolutions,
            field_overrides=field_overrides, edits=edits,
        )
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or run_id
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="reconciliation-{safe}.pdf"'
            },
        )

    @app.get("/runs/{run_id}/expense-report.pdf")
    def download_expense_report(run_id: str):
        """The month's report: the organized listing, then every receipt
        (owner directive 2026-08-23 — the output is a document now, not an
        import file). Sync: it reads every receipt off the volume and
        stitches a PDF, so it belongs in the threadpool."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            overrides = store.get_category_overrides(run_id)
            field_overrides = store.get_expense_field_overrides(run_id)
            edits = store.get_expense_edits(run_id)
            label = run.label or run_id
            # R4b: a trip batch's report is the trip report -- sectioned
            # per person, titled by the trip. Null for company months and
            # for a trip whose entity was deleted (it still sections).
            trip = store.get_trip(
                str((run.config or {}).get("trip_id") or "")
            ) if batch_type(run) == BATCH_TYPE_TRIP else None
            # Item 47: the cost-center registry is read LIVE from
            # settings, the same way the grid reads it, so the report
            # and the screen partition on the same names.
            settings = store.get_settings()
            dup_resolutions = store.get_duplicate_resolutions(run_id)
            # Item 94: which copies the report sets aside (see the CSV).
            charge_decisions = store.get_decisions(run_id)
        outcomes: dict = {}
        pdf = build_expense_report(
            run, overrides, field_overrides, edits, trip=trip,
            settings=settings,
            render_outcomes=outcomes,
            dup_resolutions=dup_resolutions,
            charge_decisions=charge_decisions,
            learning_db_path=app.state.learning_db_path,
        )
        # Item 67: building the report is the only moment renderability is
        # known, so it is the moment the answer gets recorded. The grid reads
        # it back off the run summary; the run is re-read here rather than
        # reusing the row from before the build, which took seconds and may
        # have raced another writer.
        with open_store() as store:
            fresh = store.get_run(run_id)
            if fresh is not None and (fresh.summary or {}).get(
                "receipt_render"
            ) != outcomes:
                summary = dict(fresh.summary or {})
                summary["receipt_render"] = outcomes
                store.update_run_summary(run_id, summary)
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") or run_id
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="expense-report-{safe}.pdf"'
            },
        )

    @app.post("/api/runs/{run_id}/forget")
    async def post_forget(run_id: str, request: Request):
        # PR C — "this was wrong": drop everything the tool learned for one
        # merchant so next month stops auto-filling it. Sibling of
        # /api/memory/forget, so the workbench can forget in place and then
        # reopen the reclassify dropdown without a page nav.
        body = await request.json()
        legal_entity_id = (body.get("legal_entity_id") or "").strip()
        vendor = (body.get("vendor") or "").strip()
        if not legal_entity_id or not vendor:
            return JSONResponse({"error": "bad request", "code": "invalid_body"}, status_code=400)
        forgotten = forget_memory_vendor(
            app.state.learning_db_path, legal_entity_id, vendor
        )
        return JSONResponse({"ok": True, "forgotten": forgotten})

    @app.get("/api/runs/{run_id}/memory-plan")
    def get_memory_plan(run_id: str):
        """Item 163 (note #81): what "Save corrections to memory" would
        write, before it is pressed. Read-only: every row is computed by
        running the real learners against a recording stand-in, so the
        preview and the save cannot disagree. `writes[]` names the table,
        the key, the value and the surface that manages it; `registry` is
        the per-merchant before/after of the same save."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            plan = plan_month_memory(
                store, run, app.state.learning_db_path, now_iso=_now_iso()
            )
        return JSONResponse(jsonable_encoder(plan))

    @app.get("/api/memory/commits")
    def get_memory_commits(limit: int = 50):
        """Item 163: the saves themselves, newest first — which month, when,
        by which trigger, what it taught, and whether it has been undone.
        This is the "where are these saved" answer: each entry lists the
        keys it wrote and the surface each one is managed on."""
        with open_store() as store:
            entries = store.list_memory_journal(limit=limit)
        out = []
        for e in entries:
            out.append({
                "id": e["id"],
                "run_id": e["run_id"],
                "label": e["label"],
                "committed_at": e["committed_at"],
                "trigger": e["trigger"],
                "learned": e["learned"],
                "reverted_at": e["reverted_at"],
                "n_rows": len(e["rows"]),
                "rows": [
                    {"table": r["table"], "key": r["key"],
                     "surface": MEMORY_TABLE_SURFACE.get(r["table"], ""),
                     "existed": r["row"] is not None}
                    for r in e["rows"]
                ],
                "n_merchants_changed": sum(
                    1 for name in set(e["merchants_before"]) | set(e["merchants_after"])
                    if e["merchants_before"].get(name) != e["merchants_after"].get(name)
                ),
            })
        return JSONResponse(jsonable_encoder({"commits": out}))

    @app.post("/api/memory/commits/{journal_id}/undo")
    def post_memory_commit_undo(journal_id: int):
        """Item 163: put one save back. Every learning row it touched
        returns to its pre-image (a row it created is deleted), the merchant
        registry returns to the map that preceded it, and the month's saved
        digest is cleared so the next publish teaches the corrections
        again. Only the most recent un-undone save can be undone."""
        with open_store() as store:
            result = undo_memory_commit(
                store, journal_id, app.state.learning_db_path, _now_iso()
            )
        if isinstance(result, Refusal):
            status = 404 if code_of(result, "") == "memory_journal_not_found" else 409
            return _refused(result, status=status)
        return JSONResponse(jsonable_encoder(result))

    @app.post("/api/runs/{run_id}/commit-memory")
    def post_commit_memory(run_id: str):
        # Explicit finalize: fold THIS run's confirmed decisions into the
        # durable learning store so next month consults them (Phase 2).
        # Expense batches (Phase 6) branch inside commit_to_memory: the
        # field/edit overlays teach entity mappings + field corrections.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
            # Passing the open store lets the expense branch upsert the same
            # vendor / category edits into settings["merchants"] (2026-07-29,
            # self-improving registry) in the same transaction context. Item
            # 88: the same helper Publish uses, which records the save so a
            # Publish right after it does not teach the same corrections twice.
            saved = commit_month_memory(
                store, run, app.state.learning_db_path, _now_iso(),
                trigger=MEMORY_TRIGGER_BUTTON, only_if_changed=False,
            )
        # Item 163: the id of the journal entry this save wrote, so the
        # caller can undo exactly this save rather than "the last one".
        return JSONResponse({
            "ok": True, "learned": saved["learned"],
            "journal_id": saved.get("journal_id"),
        })

    @app.get("/runs/{run_id}/report.xlsx")
    def download_report(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_report(run, decisions, overrides)
        return FileResponse(
            path,
            filename=f"report-{run_id}.xlsx",
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    @app.get("/runs/{run_id}/zoho.csv")
    def download_zoho(run_id: str):
        # PR E — the Zoho Books journal-entry import CSV, with the reviewer's
        # decisions + category overrides applied. Only effective matched
        # transactions are exported (the writer's posting policy).
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_zoho(run, decisions, overrides)
        return FileResponse(
            path,
            filename=f"zoho-journal-{run_id}.csv",
            media_type="text/csv",
        )

    @app.get("/runs/{run_id}/reconciled.csv")
    def download_reconciled(run_id: str):
        # The flat reconciled CSV — the CSV twin of the .xlsx report, with
        # the reviewer's decisions + category overrides applied. Every
        # statement line with its match status + matched-expense enrichment.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_reconciled(run, decisions, overrides)
        return FileResponse(
            path,
            filename=f"reconciled-{run_id}.csv",
            media_type="text/csv",
        )

    @app.get("/runs/{run_id}/statement-categorized.xlsx")
    def download_writeback(run_id: str, file: str = "", statement_id: str = ""):
        # L3 — her own uploaded workbook with one new "Zoho Account (tool)"
        # column; only for xlsx/xlsm statements.
        #
        # `?file=` picks WHICH statement, for a month that has taken several
        # (PR 2b-2b-2); it is resolved against the run's own `statements[]`
        # and 404s otherwise, so the query string cannot address a file the
        # month never loaded. No parameter keeps the existing behavior: the
        # run's current statement, which is the only one a single-statement
        # month ever had. `?statement_id=` (note item T2) addresses the
        # upload by its content id instead, resolved against
        # `statements[].statement_id`; it wins over `?file=` when both are
        # given, and an unknown id is the same 404.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found", "run_not_found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_writeback(
            run, decisions, overrides, file, statement_id=statement_id,
        )
        if path is None:
            return JSONResponse(
                {"error": "This run's statement is not an Excel workbook",
                 "code": "statement_not_workbook"},
                status_code=404,
            )
        return FileResponse(
            path,
            filename=f"statement-categorized-{run_id}{path.suffix}",
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    # Memory reset: the destructive counterpart of /api/memory/forget
    # (whole tables / whole entities instead of one merchant). Confirm
    # gate mirrors the CLI's dry-run default: without {"confirm": true}
    # the reply is a would-delete preview and NOTHING is deleted.
    @app.post("/api/memory/reset")
    async def api_memory_reset(request: Request):
        from ..learning import LearningStore

        body = await request.json() if await request.body() else {}
        table = (body.get("table") or "").strip() or None
        legal_entity_id = (body.get("legal_entity_id") or "").strip() or None
        if body.get("confirm") is not True:
            # Preview must not create the store as a side effect.
            if Path(app.state.learning_db_path).exists():
                with LearningStore(app.state.learning_db_path) as s:
                    counts = s.count_rows(legal_entity_id)
            else:
                counts = {
                    "merchant_category": 0, "vendor_alias": 0,
                    "merchant_fx": 0, "merchant_entity": 0,
                    "field_correction": 0,
                }
            preview = (
                {table: counts.get(table, 0)} if table else counts
            )
            return JSONResponse({
                "ok": False, "confirm_required": True, "preview": preview,
                "table": table, "legal_entity_id": legal_entity_id,
            })
        reset_memory(app.state.learning_db_path, table, legal_entity_id)
        return JSONResponse(
            {"ok": True, "table": table, "legal_entity_id": legal_entity_id}
        )

    # ── Settled outside the card (backlog item 62) ──────────────────────
    # A receipt paid by bank transfer, cash or PayPal never posts to a card,
    # so no statement line will ever settle it and it sat in the unmatched
    # pool forever (July 2026: Redis 13,200.00 USD, Konsultancy 15,972.00
    # EUR, 360Crossmedia 900.00 EUR). This retires it from the
    # reconciliation side while it stays an expense of the month.

    @app.post("/api/runs/{run_id}/receipts/{document_id:path}/settled-outside")
    async def post_receipt_settled_outside(
        run_id: str, document_id: str, request: Request
    ):
        """Mark one receipt settled outside the card.

        Body `{"how": "bank_transfer"|"cash"|"paypal"|"other", "note": ""}`.
        Threadpool: the write takes the batch lock, and an `async def`
        blocking on that lock parks the event loop (see the lock's own
        note in service.py)."""
        body = await request.json() if await request.body() else {}
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
        try:
            result = await run_in_threadpool(
                _settled_outside_write,
                run_id, document_id, body.get("how"), body.get("note"),
            )
        except RunInputError as exc:
            return _input_refused(exc)
        return JSONResponse(result)

    @app.delete(
        "/api/runs/{run_id}/receipts/{document_id:path}/settled-outside"
    )
    async def delete_receipt_settled_outside(run_id: str, document_id: str):
        """Undo it: the receipt rejoins the pool, the counts and the pair
        scan exactly as it was."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found", "code": "run_not_found"}, status_code=404)
        try:
            result = await run_in_threadpool(
                _settled_outside_write, run_id, document_id, None, None,
                True,
            )
        except RunInputError as exc:
            return _input_refused(exc)
        return JSONResponse(result)

    def _settled_outside_write(
        run_id: str,
        document_id: str,
        how: str | None,
        note: str | None,
        clear: bool = False,
    ) -> dict:
        """One locked write, then the caller's own payload rebuilt from it.

        Replies with the summary of whichever view this batch renders, the
        way duplicates/resolve does, so the SPA never has to guess which
        counts moved."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                raise RunInputError("This batch no longer exists.", code="batch_deleted")
            if clear:
                out = clear_receipt_settled_outside(store, run, document_id)
            else:
                out = set_receipt_settled_outside(
                    store, run, document_id, how or "", note or "", _now_iso()
                )
            run = store.get_run(run_id)
            if run is None:
                raise RunInputError("This batch no longer exists.", code="batch_deleted")
            view = _run_view(store, run)
        return {**out, "summary": jsonable_encoder(view["summary"])}

    return app
