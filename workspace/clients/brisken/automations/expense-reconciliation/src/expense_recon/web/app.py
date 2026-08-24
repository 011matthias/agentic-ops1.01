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
    GET/PUT /api/settings          §16 export policy
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
import mimetypes
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import BackgroundTasks, Body, FastAPI, Form, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from starlette.concurrency import run_in_threadpool

from ..batch_period import month_from_label
from ..cards import card_to_dict, effective_cards, normalize_cards_setting
from ..cards_provision import card_by_key, load_cards
from ..ingest.expense_report_images import render_receipt_page
from .serialize import receipt_from_dict
from .service import (
    DEFAULT_EXPENSE_COLUMN_MAP,
    EXPENSE_CATEGORY_FIELDS,
    EXPENSE_HEADER_FIELDS,
    MODE_EXPENSE_GENERATION,
    PreparedExpenseBatch,
    PreparedRun,
    RunForm,
    RunInputError,
    add_receipts_to_expense_batch,
    apply_expense_edits,
    assign_batch_cards,
    attach_emailed_receipt,
    available_entities,
    batch_list_summary,
    build_expense_report,
    build_reconciliation_report,
    build_expense_view,
    build_memory_view,
    build_view,
    bulk_decisions,
    commit_to_memory,
    compare_runs,
    create_expense_batch,
    create_intake,
    execute_expense_batch,
    execute_run,
    execute_statement_attach,
    has_statement,
    prepare_statement_attach,
    forget_memory_vendor,
    ingest_receipts_folder_into_run,
    matched_autopick_decisions,
    ready_confirm_pairs,
    prepare_intake_run,
    prepare_run,
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
    validate_expense_field,
    validate_manual_match,
)
from ..matching.types import EXPENSE_CATEGORIES
from ..merchant_registry import normalize_merchants_setting
from .serialize import snapshot_from_dict
from .store import (
    INTAKE_PROCESSING,
    INTAKE_READY,
    INTAKE_RECEIVED,
    JOB_DONE,
    JOB_ERROR,
    SETTINGS_MAP_KEYS,
    STATUS_CONFIRMED,
    VALID_DISPOSITIONS,
    VALID_DUP_RESOLUTIONS,
    VALID_STATUSES,
    RunStore,
)
from . import auth, ratelimit

log = logging.getLogger("expense_recon.web")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _not_found(message: str) -> JSONResponse:
    return JSONResponse({"error": message.lower()}, status_code=404)


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
    try:
        with RunStore(db_path) as store:
            run_id = execute_expense_batch(
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
        return
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


def _run_attach_statement_job(
    db_path: Path, job_id: str, run_id: str, stmt_name: str,
    column_map: dict | None, form: RunForm, learning_db_path: Path,
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
            )
            # The mismatch warning must survive the job round-trip: park it
            # on the job's stage-free error-less row via the stage field.
            if result.get("entity_mismatch"):
                store.set_job_stage(
                    job_id, f"warning: {result['entity_mismatch']}", _now_iso()
                )
            store.set_job_status(
                job_id, JOB_DONE, run_id=run_id, updated_at=_now_iso()
            )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        with RunStore(db_path) as store:
            store.set_job_status(
                job_id, JOB_ERROR, error=str(exc), updated_at=_now_iso()
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
        from .intake_mail import reconcile_interrupted, sweep_retention

        reconcile_interrupted(db_path, data_root_path)
        # Retention floor (settings intake.retention_years, default 10y per
        # AO paragraph 147): expired inbound archives are deleted at boot,
        # which scale-to-zero makes a near-daily event.
        sweep_retention(db_path, data_root_path)
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
                    {"error": "authentication required"}, status_code=401
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
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"https://([a-z0-9-]+\.)*(lovable\.app|lovableproject\.com|lovable\.dev)"
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
            return JSONResponse({"error": "invalid code"}, status_code=401)
        return JSONResponse({
            "token": auth.issue_token(auth.ROLE_OPERATOR, label),
            "role": auth.ROLE_OPERATOR,
            "operator": label,
        })

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"status": "ok"})

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
            return JSONResponse({"error": exc.message}, status_code=400)
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
            return _not_found("Upload not found")

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
            return JSONResponse({"error": exc.message}, status_code=400)
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
            raise RunInputError(f"Receipt column map is not valid JSON: {exc}")

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
                f"Account to legal-entity map is not valid JSON: {exc}"
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
            return JSONResponse({"error": exc.message}, status_code=400)

        statement_bytes = await statement.read()
        receipts_bytes = await receipts.read()
        if not statement_bytes:
            return JSONResponse(
                {"error": "No statement file uploaded."}, status_code=400
            )
        if not receipts_bytes:
            return JSONResponse(
                {"error": "No receipts file uploaded."}, status_code=400
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
            return JSONResponse({"error": exc.message}, status_code=400)

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
            return _not_found("Upload not found")

        def _error_page(message: str, headers=None, status_code: int = 400):
            return JSONResponse(
                {"error": message, "headers": headers},
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
            return _error_page(exc.message, headers=exc.headers)

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
                return _error_page(exc.message, headers=exc.headers)
            return JSONResponse({"ok": True, "run_id": run_id})

        return _start_background_run(background, prepared, intake.label)

    # ── Publish / unpublish a reviewed run (drives the intake status the
    # dashboard and the dev-side notifier read).
    @app.post("/api/runs/{run_id}/publish")
    def publish_run(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found")
            store.set_run_published(run_id, True, _now_iso())
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_READY,
                    run_id=run_id, updated_at=_now_iso(),
                )
        return JSONResponse({"ok": True, "run_id": run_id, "published": True})

    @app.post("/api/runs/{run_id}/unpublish")
    def unpublish_run(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found")
            store.set_run_published(run_id, False, None)
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_PROCESSING, updated_at=_now_iso()
                )
        return JSONResponse({"ok": True, "run_id": run_id, "published": False})

    # ── Rename / delete a run (F9). The operator accumulates test runs and
    # needs to relabel or clear them; deleting also removes the on-disk
    # upload/export tree so the volume does not grow without bound.
    runs_root = (data_root_path / "runs").resolve()

    @app.post("/api/runs/{run_id}/rename")
    async def rename_run(run_id: str, request: Request):
        try:
            data = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json"}, status_code=400)
        label = str((data or {}).get("label", "")).strip()[:200] if isinstance(data, dict) else ""
        if not label:
            return JSONResponse({"error": "label is required"}, status_code=400)
        with open_store() as store:
            if not store.set_run_label(run_id, label):
                return _not_found("Run not found")
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
        from .service import batch_write_lock

        with open_store() as store:
            if store.get_run(run_id) is None:
                return _not_found("Run not found")
        # Destructive-action gate: the caller repeats the month's label
        # (or the run id) in the body. A bare POST deletes nothing.
        confirm = (
            str(payload.get("confirm", "")).strip()
            if isinstance(payload, dict) else ""
        )
        if not confirm:
            return JSONResponse(
                {"error": "confirm is required: repeat the month label "
                          "(or run id) to delete"},
                status_code=400,
            )
        # Serialize with the batch writers: rows must not vanish under an
        # in-flight ingest RMW, and a writer entering after us re-fetches
        # None and refuses (mail goes held_failed, stays replayable).
        with batch_write_lock():
            with open_store() as store:
                run = store.get_run(run_id)
                if run is None:
                    return _not_found("Run not found")
                if confirm not in {(run.label or "").strip(), run.run_id}:
                    return JSONResponse(
                        {"error": "confirm label mismatch"}, status_code=409
                    )
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
        return JSONResponse({
            "ok": True, "run_id": run_id, "deleted": True,
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
            return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
        if not isinstance(data, dict):
            return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
        comment = str(data.get("comment", "")).strip()
        if not comment:
            return JSONResponse(
                {"ok": False, "error": "comment is required"}, status_code=400
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
            count_archives,
            count_refusals,
            read_log,
            read_refusals,
        )

        rows = read_log(app.state.data_root, limit=max(1, min(limit, 500)))
        # Distinct MAILS, not log rows: an archive that has been replayed
        # or claimed carries a second row, and a badge saying "2 held"
        # about one held mail sends the operator looking for a mail that
        # is not there.
        n_held = count_archives(
            rows, lambda r: str(r.get("status", "")).startswith("held_")
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
        # LAST: the label needs the pool state and the resolved batch
        # labels that the loops above just stamped.
        annotate_status_view(rows)
        return JSONResponse({
            "entries": rows,
            "n_held": n_held,
            "n_pooled": n_pooled,
            # Mail we turned away. Deliberately NOT rows in `entries`: a
            # refusal has no archive, and a row there carrying a status no
            # consumer knows is the exact shape of the "Arriving" bug.
            "n_refused": count_refusals(app.state.data_root),
            "refusals": read_refusals(app.state.data_root),
        })

    @app.post("/api/inbound/replay-held")
    def inbound_replay_held() -> JSONResponse:
        """Drain both halves in one click: held mail re-routes by month
        (pooling what has no month open), then every pooled mail whose
        month IS open is claimed."""
        from .intake_mail import claim_pooled, replay_held

        result = replay_held(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root,
        )
        claim = claim_pooled(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root,
        )
        return JSONResponse({
            "ok": True, **result,
            "claimed": claim["claimed"],
            # replay_held's own `pooled` counts what it just parked; the
            # claim's still_pooled is the pool's size after both halves.
            "still_pooled": claim["still_pooled"],
            "failed": result["failed"] + claim["failed"],
        })

    # ── Body-only mail actions (C2): view the body, render+ingest it as a
    # PDF through the normal pipeline, or dismiss it as junk. All sync:
    # render-ingest does vision work and must run in the threadpool.
    @app.get("/api/inbound/{archive}/body")
    def inbound_body(archive: str) -> JSONResponse:
        from .intake_mail import read_body_view

        view = read_body_view(app.state.data_root, archive)
        if view is None:
            return _not_found("Archive not found")
        return JSONResponse(view)

    @app.post("/api/inbound/{archive}/render-ingest")
    def inbound_render_ingest(archive: str) -> JSONResponse:
        from .intake_mail import render_ingest

        result = render_ingest(
            app.state.db_path, app.state.learning_db_path,
            app.state.data_root, archive, operator=_operator(),
        )
        if "error" in result:
            code = result.pop("code", 400)
            return JSONResponse(result, status_code=code)
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
            code = result.pop("code", 400)
            return JSONResponse(result, status_code=code)
        return JSONResponse({"ok": True, **result})

    @app.post("/api/inbound/{archive}/dismiss")
    def inbound_dismiss(archive: str) -> JSONResponse:
        from .intake_mail import dismiss_archive

        result = dismiss_archive(
            app.state.data_root, archive, operator=_operator(),
        )
        if "error" in result:
            code = result.pop("code", 400)
            return JSONResponse(result, status_code=code)
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
            return JSONResponse({"error": "unknown job"}, status_code=404)
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
        return build_expense_view(
            run, overrides, field_overrides, edits, resolutions,
            settings=settings,
        )

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
                return JSONResponse({"error": "run not found"}, status_code=404)
            # A batch WITH a statement attached graduates to the workbench:
            # build_view over the baked snapshot, every statement-mode
            # surface (decisions / confirm-ready / exports) unchanged. The
            # expense grid stays reachable via GET /api/expense-batches/{id}.
            if run_mode(run) == MODE_EXPENSE_GENERATION and not has_statement(run):
                return JSONResponse(jsonable_encoder(_expense_view(store, run)))
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
        view = build_view(run, decisions, overrides, resolutions)
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
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_decision(run_id, tx_id, status, chosen, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    # §17 disposition. The upsert is status-preserving in the store (never
    # clobbers the row's triage verdict).
    @app.post("/api/runs/{run_id}/disposition")
    async def post_disposition(run_id: str, request: Request):
        body = await request.json()
        tx_id = body.get("transaction_id")
        disposition = body.get("disposition")
        if not tx_id or disposition not in VALID_DISPOSITIONS:
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_disposition(run_id, tx_id, disposition, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse({"ok": True, "summary": view["summary"]})

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
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_duplicate_resolution(run_id, group_id, resolution, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
        view = build_view(run, decisions, overrides, resolutions)
        return JSONResponse({"ok": True, "summary": view["summary"]})

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
                **settings,
                "categories": list(EXPENSE_CATEGORIES),
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
            })

    @app.get("/api/cards")
    def api_get_cards():
        # The composed card enumeration (owner ask 2026-08-21: "laying out
        # all card identities"). Same payload family as cards_effective,
        # plus the entity options the assignment UI needs.
        with open_store() as store:
            settings = store.get_settings()
        composed = effective_cards(settings, load_cards())
        return JSONResponse({
            "cards": [card_to_dict(c) for c in composed.values()],
            "entity_options": available_entities(settings),
        })

    @app.put("/api/settings")
    async def api_put_settings(request: Request):
        body = await request.json()
        patch: dict = {}
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
                    {"error": f"{key} must be an object"}, status_code=400
                )
            cleaned: dict[str, str] = {}
            for k, v in raw.items():
                name = str(k).strip()
                value = str(v).strip()
                if not name or not value:
                    continue
                if key == "fx_reference_rates":
                    from_ccy, _, to_ccy = name.partition(":")
                    if not from_ccy.strip() or not to_ccy.strip():
                        return JSONResponse(
                            {"error": f"rate key {name!r} must be 'FROM:TO'"},
                            status_code=400,
                        )
                    try:
                        if Decimal(value) <= 0:
                            raise ValueError(value)
                    except (ArithmeticError, ValueError):
                        return JSONResponse(
                            {"error": f"rate {name} must be a positive number"},
                            status_code=400,
                        )
                cleaned[name] = value
            patch[key] = cleaned
        # Legal-entity registry (Phase 5): {label: {org_id, chart_path,
        # default_paid_through, scope_groups, account_picks}}. String
        # fields trim; list fields must be lists of strings. The whole map
        # replaces the stored one (same contract as the other map keys), so
        # deleting an entity is omitting it. `categories` is read-only and
        # never persisted.
        if "entities" in body:
            raw = body["entities"]
            if not isinstance(raw, dict):
                return JSONResponse(
                    {"error": "entities must be an object"}, status_code=400
                )
            cleaned_entities: dict[str, dict] = {}
            for label, ent in raw.items():
                name = str(label).strip()
                if not name:
                    continue
                if not isinstance(ent, dict):
                    return JSONResponse(
                        {"error": f"entities[{name!r}] must be an object"},
                        status_code=400,
                    )
                entry: dict = {}
                for skey in ("org_id", "chart_path", "default_paid_through"):
                    if str(ent.get(skey) or "").strip():
                        entry[skey] = str(ent[skey]).strip()
                for lkey in ("scope_groups", "account_picks"):
                    if ent.get(lkey) is None:
                        continue
                    if not isinstance(ent[lkey], list):
                        return JSONResponse(
                            {"error": f"entities[{name!r}].{lkey} must be a list"},
                            status_code=400,
                        )
                    values = [str(v).strip() for v in ent[lkey] if str(v).strip()]
                    if values:
                        entry[lkey] = values
                cleaned_entities[name] = entry
            patch["entities"] = cleaned_entities
        # Merchant registry (2026-07-29): {canonical_name: {aliases, category,
        # zoho_account}}. Whole-map replace, same contract as `entities`;
        # validated + cleaned by the registry module (blank canonical dropped,
        # aliases de-duped on their normalized key, category constrained to
        # the fixed 8). A malformed payload is rejected at the edge.
        if "merchants" in body:
            try:
                patch["merchants"] = normalize_merchants_setting(body["merchants"])
            except ValueError as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
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
                return JSONResponse({"error": str(exc)}, status_code=400)
        # Mail-intake config (aliases -> person names, sender allowlist,
        # daily caps). Validated at the edge like merchants.
        if "intake" in body:
            from .intake_mail import normalize_intake_setting

            try:
                patch["intake"] = normalize_intake_setting(body["intake"])
            except ValueError as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
        with open_store() as store:
            settings = store.set_settings(patch, _now_iso())
        return JSONResponse({
            **settings, "categories": list(EXPENSE_CATEGORIES),
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
        jsonable_encoder is kept for symmetry with the other routes."""
        return JSONResponse(
            jsonable_encoder(build_memory_view(
                app.state.learning_db_path,
                unvalidated_only=bool(unvalidated),
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
        from ..matching.types import EXPENSE_CATEGORIES

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - malformed body is a client error
            return JSONResponse({"error": "invalid json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object"},
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
                          "required"}, status_code=400)
        if category not in EXPENSE_CATEGORIES:
            return JSONResponse(
                {"error": f"category must be one of the tool's "
                          f"{len(EXPENSE_CATEGORIES)} categories",
                 "categories": sorted(EXPENSE_CATEGORIES)},
                status_code=400)
        with LearningStore(app.state.learning_db_path) as s:
            s.set_merchant_category_manual(
                legal_entity_id, vendor_norm, category, zoho_account,
                _now_iso(), keep_account=keep_account,
            )
            row = s.get_merchant_category(legal_entity_id, vendor_norm)
        return JSONResponse({
            "ok": True, "entity": legal_entity_id, "vendor": vendor_norm,
            "category": row.category, "zoho_account": row.zoho_account or "",
            "count": row.decision_count, "source_run": row.source_run,
        })

    @app.delete("/api/memory/categories")
    async def api_memory_delete_category(request: Request):
        """Drop ONE learned category row; the vendor's aliases / FX rows
        stay (forget is the sweep-everything sibling)."""
        from ..learning import LearningStore

        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object"},
                                status_code=400)
        legal_entity_id, vendor_norm = _memory_row_key(body)
        if not legal_entity_id or not vendor_norm:
            return JSONResponse(
                {"error": "legal_entity_id and a non-empty vendor are "
                          "required"}, status_code=400)
        with LearningStore(app.state.learning_db_path) as s:
            existed = s.delete_merchant_category(legal_entity_id, vendor_norm)
        if not existed:
            return JSONResponse(
                {"error": "no learned category for that entity + vendor"},
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
            return JSONResponse({"error": "invalid json"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "body must be an object"},
                                status_code=400)
        rows = body.get("rows")
        if not isinstance(rows, list) or not rows:
            return JSONResponse(
                {"error": "rows must be a non-empty list of "
                          "{legal_entity_id, vendor}"}, status_code=400)
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
                {"error": "no valid rows in the list"}, status_code=400)
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
            return JSONResponse({"error": "bad request"}, status_code=400)
        forgotten = forget_memory_vendor(
            app.state.learning_db_path, legal_entity_id, vendor
        )
        return JSONResponse({"ok": True, "forgotten": forgotten})

    @app.post("/api/runs/{run_id}/decisions/confirm-matched")
    def post_confirm_matched(run_id: str):
        # PR A — one click confirms every matched-bucket transaction with
        # its auto-picked receipt, so only review + unmatched need hand
        # work. Reuses the per-row decision write; never stomps an
        # explicit confirm/reject.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            pairs = matched_autopick_decisions(run, decisions)
            for tx_id, doc_id in pairs:
                store.set_decision(
                    run_id, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                )
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse(
            {"ok": True, "confirmed": len(pairs), "summary": view["summary"]}
        )

    @app.post("/api/runs/{run_id}/decisions/confirm-ready")
    def post_confirm_ready(run_id: str):
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
                return JSONResponse({"error": "run not found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            pairs = ready_confirm_pairs(run, decisions, overrides)
            remaining = 0
            if len(pairs) > _BULK_DECISION_LIMIT:
                remaining = len(pairs) - _BULK_DECISION_LIMIT
                pairs = pairs[:_BULK_DECISION_LIMIT]
            for tx_id, doc_id in pairs:
                store.set_decision(
                    run_id, tx_id, STATUS_CONFIRMED, doc_id, _now_iso()
                )
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse({
            "ok": True,
            "confirmed": len(pairs),
            "remaining": remaining,
            "summary": view["summary"],
        })

    @app.post("/api/runs/{run_id}/decisions/bulk")
    async def post_bulk_decisions(run_id: str, request: Request):
        """Confirm or reject a named set of charges in one call (2026-07-22).

        The review bucket held 34 rows on the real April run and could only
        be cleared one row at a time. The client sends the ids it is acting
        on, so the scope is explicit and auditable rather than the server
        guessing "everything that looks like this". Confirming uses each
        charge's own top candidate and skips any charge without one.
        """
        body = await request.json()
        tx_ids = body.get("transaction_ids")
        status = body.get("status")
        if not isinstance(tx_ids, list) or not tx_ids:
            return JSONResponse(
                {"error": "transaction_ids must be a non-empty list"},
                status_code=400,
            )
        if status not in VALID_STATUSES:
            return JSONResponse(
                {"error": f"status must be one of {sorted(VALID_STATUSES)}"},
                status_code=400,
            )
        tx_ids = [str(t) for t in tx_ids]
        if len(tx_ids) > _BULK_DECISION_LIMIT:
            return JSONResponse(
                {"error": f"at most {_BULK_DECISION_LIMIT} rows per call"},
                status_code=400,
            )
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            writes = bulk_decisions(run, decisions, tx_ids, status)
            for tx_id, doc_id in writes:
                store.set_decision(run_id, tx_id, status, doc_id, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
        view = build_view(run, decisions, overrides, resolutions)
        # `skipped` is the honest half of the count: rows already decided,
        # or (when confirming) rows with no candidate to confirm against.
        return JSONResponse({
            "ok": True,
            "updated": len(writes),
            "skipped": len(tx_ids) - len(writes),
            "summary": view["summary"],
        })

    @app.post("/api/runs/{run_id}/categories")
    async def post_category(run_id: str, request: Request):
        body = await request.json()
        document_id = body.get("document_id")
        line_index = body.get("line_index")
        category = body.get("category")
        zoho_account = body.get("zoho_account")
        if not document_id or not isinstance(line_index, int):
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            if store.get_run(run_id) is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_category_override(
                run_id, document_id, line_index, category, zoho_account, _now_iso()
            )
        return JSONResponse({"ok": True})

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
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            err = validate_manual_match(run, tx_id, document_id)
            if err:
                return JSONResponse({"error": err}, status_code=400)
            store.set_decision(
                run_id, tx_id, STATUS_CONFIRMED, document_id, _now_iso()
            )
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse({"ok": True, "summary": view["summary"]})

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
            return JSONResponse({"error": "file required"}, status_code=400)
        data = await upload.read()
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            err, document_id = attach_emailed_receipt(
                store, run, transaction_id, upload.filename, data, _now_iso()
            )
            if err:
                return JSONResponse({"error": err}, status_code=400)
            run = store.get_run(run_id)  # snapshot changed above
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse(
            {"ok": True, "document_id": document_id, "summary": view["summary"]}
        )

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
            return JSONResponse({"error": "run not found"}, status_code=404)

        form = await request.form()
        uploads = [
            u for u in form.getlist("files") if getattr(u, "filename", None)
        ]
        one = form.get("file")  # tolerate the singular field name too
        if one is not None and getattr(one, "filename", None):
            uploads.append(one)
        if not uploads:
            return JSONResponse({"error": "no files uploaded"}, status_code=400)

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
                {"error": "all uploaded files were empty"}, status_code=400
            )

        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_folder_job, app.state.db_path, job_id, run_id, staging
        )
        return JSONResponse({"ok": True, "job_id": job_id, "n_files": saved})

    @app.get("/api/runs/{run_id}/receipts/{document_id:path}/image")
    def receipt_image(run_id: str, document_id: str):
        # Receipt preview (owner directive 2026-07-25): a reviewer working
        # the needs-review queue gets a quick look at the actual receipt.
        # Serves the vision-mapped page of the uploaded ER PDF (rendered to
        # PNG) or an operator-uploaded manual receipt file, straight from
        # the run's work dir. 404 whenever no image is attributable — the
        # SPA keys its preview control off `receipt_image_available`.
        with open_store() as store:
            run = store.get_run(run_id)
        if run is None:
            return JSONResponse({"error": "run not found"}, status_code=404)
        work_dir = Path(run.work_dir)

        if document_id.startswith("manual:"):
            tx_part = document_id[len("manual:"):]
            fs_tx = re.sub(r"[^A-Za-z0-9._-]", "_", tx_part)
            folder = work_dir / "manual-receipts"
            hits = sorted(folder.glob(f"{fs_tx}__*")) if folder.is_dir() else []
            if not hits:
                return JSONResponse(
                    {"error": "no receipt image"}, status_code=404
                )
            media = (
                mimetypes.guess_type(hits[0].name)[0]
                or "application/octet-stream"
            )
            return FileResponse(hits[0], media_type=media)

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
                    {"error": "no receipt image"}, status_code=404
                )
            media = (
                mimetypes.guess_type(hits[0].name)[0]
                or "application/octet-stream"
            )
            return FileResponse(hits[0], media_type=media)

        if run_mode(run) == MODE_EXPENSE_GENERATION:
            # Expense batch (receipt-first): document ids ARE filenames
            # under the batch's receipts dir. Resolve inside it only —
            # never follow a crafted id out of the run's tree.
            exp_dir = (work_dir / "receipts").resolve()
            try:
                target = (exp_dir / document_id).resolve()
                if exp_dir in target.parents and target.is_file():
                    media = (
                        mimetypes.guess_type(target.name)[0]
                        or "application/octet-stream"
                    )
                    return FileResponse(target, media_type=media)
            except (OSError, ValueError):
                pass
            return JSONResponse({"error": "no receipt image"}, status_code=404)

        receipts = [
            receipt_from_dict(x) for x in run.snapshot.get("receipts", [])
        ]
        rec = next(
            (r for r in receipts if r.document_id == document_id), None
        )
        if rec is None or rec.receipt_image_page is None:
            return JSONResponse({"error": "no receipt image"}, status_code=404)
        rcpt_rel = ((run.config or {}).get("receipts") or {}).get("path") or ""
        pdf_path = work_dir / rcpt_rel
        if not rcpt_rel or not pdf_path.is_file():
            return JSONResponse(
                {"error": "report file missing"}, status_code=404
            )
        png = render_receipt_page(pdf_path, rec.receipt_image_page)
        if png is None:
            return JSONResponse({"error": "no receipt image"}, status_code=404)
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
        return JSONResponse({"error": "not found"}, status_code=404)

    def _expense_run_or_error(store: RunStore, run_id: str):
        """(run, None) for an expense batch; (None, response) otherwise."""
        run = store.get_run(run_id)
        if run is None:
            return None, JSONResponse({"error": "run not found"}, status_code=404)
        if run_mode(run) != MODE_EXPENSE_GENERATION:
            return None, JSONResponse(
                {"error": "not an expense batch"}, status_code=400
            )
        return run, None

    def _mutable_expense_run_or_error(store: RunStore, run_id: str):
        """Like `_expense_run_or_error`, but additionally refuses a batch
        whose statement is attached: from that point the receipt pool is
        the reconciliation's provenance and review continues in the
        workbench (decisions / categories / manual match), never through
        the expense-edit overlay."""
        run, err = _expense_run_or_error(store, run_id)
        if err is not None:
            return None, err
        if has_statement(run):
            return None, JSONResponse(
                {"error": "a statement is attached; review this month in "
                          "the reconciliation workbench"},
                status_code=400,
            )
        return run, None

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
            )
        except RunInputError as exc:
            return JSONResponse({"error": exc.message}, status_code=400)

        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_expense_job, app.state.db_path, job_id, prepared,
            app.state.learning_db_path, app.state.data_root,
        )
        month = month_from_label(prepared.label)
        body = {
            "ok": True,
            "batch_id": prepared.run_id,
            "job_id": job_id,
            "label": prepared.label,
            "upload_issues": prepared.upload_issues,
            "month": f"{month[0]:04d}-{month[1]:02d}" if month else None,
        }
        if month is None:
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
        with open_store() as store:
            batches = [
                {
                    "batch_id": r.run_id,
                    "run_id": r.run_id,
                    "label": r.label,
                    "created_at": r.created_at,
                    # Derived, not the frozen ingest summary: the list and
                    # the batch page must show one number (2026-08-22).
                    "summary": batch_list_summary(store, r),
                    # Lifecycle: False = still collecting receipts; True =
                    # statement attached, review lives in the workbench.
                    "has_statement": has_statement(r),
                }
                for r in store.list_runs()
                if (r.config or {}).get("mode") == MODE_EXPENSE_GENERATION
            ]
        return JSONResponse({"batches": batches})

    @app.get("/api/expense-batches/{run_id}")
    def get_expense_batch(run_id: str):
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _expense_run_or_error(store, run_id)
            if err is not None:
                return err
            return JSONResponse(jsonable_encoder(_expense_view(store, run)))

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
            run, err = _mutable_expense_run_or_error(store, run_id)
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
            return JSONResponse({"error": "no files uploaded"}, status_code=400)

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
                {"error": "all uploaded files were empty"}, status_code=400
            )

        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_batch_receipts_job, app.state.db_path, job_id, run_id,
            staging, app.state.learning_db_path,
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
            return JSONResponse({"error": "file is required"}, status_code=400)

        # Off the event loop: restore_set_aside_file takes the batch writer
        # lock, which an OCR ingest can hold for MINUTES. Blocking on it here
        # would park the loop and stop every endpoint including /healthz, so
        # Fly's health check fails and the restart kills that same ingest.
        # The body read above has to be awaited, so the handler stays async
        # and hands the locked span to the threadpool instead of going sync
        # like delete_run. See tests/test_web_batch_lock_threadpool.py.
        def _work():
            with open_store() as store:
                run, err = _mutable_expense_run_or_error(store, run_id)
                if err is not None:
                    return err
                try:
                    result = restore_set_aside_file(
                        store, run, file, _now_iso(),
                        learning_db_path=app.state.learning_db_path,
                    )
                except RunInputError as exc:
                    return JSONResponse({"error": exc.message}, status_code=400)
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
            return JSONResponse({"error": "body must be an object"}, status_code=400)
        assignments = body.get("assignments") or []
        if not isinstance(assignments, list):
            return JSONResponse(
                {"error": "assignments must be a list"}, status_code=400
            )
        new_cards = body.get("new_cards")
        if new_cards is not None and not isinstance(new_cards, dict):
            return JSONResponse(
                {"error": "new_cards must be an object"}, status_code=400
            )
        # Off the event loop, same reason as set-aside/restore above:
        # assign_batch_cards takes the batch writer lock.
        def _work():
            with open_store() as store:
                run, err = _mutable_expense_run_or_error(store, run_id)
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
                    return JSONResponse({"error": exc.message}, status_code=400)
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
            run, err = _mutable_expense_run_or_error(store, run_id)
            if err is not None:
                return err
            try:
                result = refresh_batch_master_data(
                    store, run, now_iso=_now_iso(), operator=_operator()
                )
            except RunInputError as exc:
                return JSONResponse({"error": exc.message}, status_code=400)
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
    ):
        """Month-end: attach the bank statement to a batch and reconcile
        it. THIS is where the card / account id is asked (never at batch
        creation). Fail-fast half (file save + column-map resolve) runs
        synchronously so a mapping problem is a form 400 with the file's
        headers; the match runs in the background -> {job_id}. On done the
        run serves the reconciliation workbench at GET /api/runs/{id}."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _mutable_expense_run_or_error(store, run_id)
        if err is not None:
            return err

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
                map_transaction_date=map_transaction_date,
                map_amount=map_amount,
                map_vendor=map_vendor,
                map_posting_date=map_posting_date,
                map_transaction_currency=map_transaction_currency,
                map_card=map_card,
                card_key=card_key,
            )
        except RunInputError as exc:
            return JSONResponse({"error": exc.message}, status_code=400)

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
                {"error": exc.message, "headers": exc.headers},
                status_code=400,
            )

        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, None, _now_iso())
        background.add_task(
            _run_attach_statement_job, app.state.db_path, job_id, run_id,
            stmt_name, column_map, form, app.state.learning_db_path,
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
                {"error": "legal_entity is required"}, status_code=400
            )
        with open_store() as store:
            run, err = _mutable_expense_run_or_error(store, run_id)
            if err is not None:
                return err
            store.set_expense_field_override(
                run_id, document_id, "legal_entity", entity, _now_iso()
            )
            view = _expense_view(store, run)
        return JSONResponse({"ok": True, "summary": view["summary"]})

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
                {"error": f"unknown field {field!r}"}, status_code=400
            )
        if value:
            if field == "category" and value not in EXPENSE_CATEGORIES:
                return JSONResponse(
                    {"error": f"category must be one of {sorted(EXPENSE_CATEGORIES)}"},
                    status_code=400,
                )
            err_msg = validate_expense_field(field, value)
            if err_msg:
                return JSONResponse({"error": err_msg}, status_code=400)

        with open_store() as store:
            run, err = _mutable_expense_run_or_error(store, run_id)
            if err is not None:
                return err
            if field in EXPENSE_CATEGORY_FIELDS:
                # Whole-expense category/account edit -> a category_override
                # per line. Find the expense in the EFFECTIVE receipt set so
                # a manual add is editable too; merge with any existing
                # override so setting the account never clears the category.
                _, receipts, _, _ = snapshot_from_dict(run.snapshot)
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
                        {"error": "unknown expense"}, status_code=404
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
                        account = ov.get("zoho_account")
                    else:
                        account = value or None
                        # apply_overrides only fires on an override WITH a
                        # category; carry the line's own when none is set.
                        category = ov.get("category") or (
                            base.category if base else None
                        )
                    store.set_category_override(
                        run_id, document_id, i, category, account, _now_iso()
                    )
            else:
                store.set_expense_field_override(
                    run_id, document_id, field, value or None, _now_iso()
                )
            view = _expense_view(store, run)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    @app.post("/api/runs/{run_id}/expenses")
    async def post_expense_add(run_id: str, request: Request):
        """Add a manual expense (Note 3: some expenses have no receipt
        file). Vendor + total required; date / currency / tax / category /
        paid_through / legal_entity optional, validated like field edits."""
        if not _receipt_first_on():
            return _flag_off()
        body = await request.json()
        if not isinstance(body, dict):
            return JSONResponse({"error": "invalid payload"}, status_code=400)
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
                {"error": "vendor and total are required"}, status_code=400
            )
        if payload.get("category") and payload["category"] not in EXPENSE_CATEGORIES:
            return JSONResponse(
                {"error": f"category must be one of {sorted(EXPENSE_CATEGORIES)}"},
                status_code=400,
            )
        for f in ("date", "total", "currency", "tax"):
            if payload.get(f):
                err_msg = validate_expense_field(f, payload[f])
                if err_msg:
                    return JSONResponse({"error": err_msg}, status_code=400)

        document_id = f"manual:{uuid.uuid4().hex[:12]}"
        with open_store() as store:
            run, err = _mutable_expense_run_or_error(store, run_id)
            if err is not None:
                return err
            store.set_expense_edit(run_id, document_id, "add", payload, _now_iso())
            view = _expense_view(store, run)
        return JSONResponse({
            "ok": True, "document_id": document_id, "summary": view["summary"],
        })

    @app.delete("/api/runs/{run_id}/expenses/{document_id:path}")
    async def delete_expense(run_id: str, document_id: str):
        """Remove one expense from the batch (soft: an edit-table row, the
        snapshot is never rewritten). Deleting a manual add overwrites its
        add row, so it simply disappears."""
        if not _receipt_first_on():
            return _flag_off()
        with open_store() as store:
            run, err = _mutable_expense_run_or_error(store, run_id)
            if err is not None:
                return err
            known = {
                r["document_id"] for r in run.snapshot.get("receipts", [])
            } | {
                e["document_id"] for e in store.get_expense_edits(run_id)
            }
            if document_id not in known:
                return JSONResponse({"error": "unknown expense"}, status_code=404)
            store.set_expense_edit(run_id, document_id, "delete", None, _now_iso())
            view = _expense_view(store, run)
        return JSONResponse({"ok": True, "summary": view["summary"]})

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
        path = regenerate_expense_export(run, overrides, field_overrides, edits)
        return FileResponse(
            path,
            filename=f"zoho-expenses-{run_id}.csv",
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
                return _not_found("Run not found")
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
            label = run.label or run_id
        pdf = build_reconciliation_report(run, decisions, overrides, resolutions)
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
        pdf = build_expense_report(run, overrides, field_overrides, edits)
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
            return JSONResponse({"error": "bad request"}, status_code=400)
        forgotten = forget_memory_vendor(
            app.state.learning_db_path, legal_entity_id, vendor
        )
        return JSONResponse({"ok": True, "forgotten": forgotten})

    @app.post("/api/runs/{run_id}/commit-memory")
    def post_commit_memory(run_id: str):
        # Explicit finalize: fold THIS run's confirmed decisions into the
        # durable learning store so next month consults them (Phase 2).
        # Expense batches (Phase 6) branch inside commit_to_memory: the
        # field/edit overlays teach entity mappings + field corrections.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            field_overrides = store.get_expense_field_overrides(run_id)
            edits = store.get_expense_edits(run_id)
            # Passing the open store lets the expense branch upsert the same
            # vendor / category edits into settings["merchants"] (2026-07-29,
            # self-improving registry) in the same transaction context.
            learned = commit_to_memory(
                run, decisions, overrides, app.state.learning_db_path, _now_iso(),
                field_overrides=field_overrides, edits=edits, settings_store=store,
            )
        return JSONResponse({"ok": True, "learned": learned})

    @app.get("/runs/{run_id}/report.xlsx")
    def download_report(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return HTMLResponse("Run not found", status_code=404)
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
                return HTMLResponse("Run not found", status_code=404)
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
                return HTMLResponse("Run not found", status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_reconciled(run, decisions, overrides)
        return FileResponse(
            path,
            filename=f"reconciled-{run_id}.csv",
            media_type="text/csv",
        )

    @app.get("/runs/{run_id}/statement-categorized.xlsx")
    def download_writeback(run_id: str):
        # L3 — her own uploaded workbook with one new "Zoho Account (tool)"
        # column; only for xlsx/xlsm statements.
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return HTMLResponse("Run not found", status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        path = regenerate_writeback(run, decisions, overrides)
        if path is None:
            return HTMLResponse(
                "This run's statement is not an Excel workbook", status_code=404
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

    return app
