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
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)

from ..cards_provision import card_by_key, load_cards
from ..ingest.expense_report_images import render_receipt_page
from .serialize import receipt_from_dict
from .service import (
    DEFAULT_EXPENSE_COLUMN_MAP,
    PreparedRun,
    RunForm,
    RunInputError,
    attach_emailed_receipt,
    build_memory_view,
    build_view,
    bulk_decisions,
    commit_to_memory,
    compare_runs,
    create_intake,
    execute_run,
    forget_memory_vendor,
    ingest_receipts_folder_into_run,
    matched_autopick_decisions,
    prepare_intake_run,
    prepare_run,
    regenerate_reconciled,
    regenerate_report,
    regenerate_writeback,
    regenerate_zoho,
    replace_intake_files,
    reset_memory,
    validate_manual_match,
)
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


def _run_id_from_path(page: str) -> str | None:
    """The run id when a feedback note was left on a run page, else None."""
    parts = page.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "runs" and parts[1]:
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

    def open_store() -> RunStore:
        return RunStore(db_path)

    # --- Password gate (hosted only) -------------------------------------
    # Active iff the operator code is set. Loopback/local use leaves it
    # unset and stays open; a public host MUST set it (this tool serves
    # financial data). Operator is the only role (owner 2026-07-22): an
    # authenticated session has the full surface. See auth.py.
    @app.middleware("http")
    async def require_login(request: Request, call_next):
        if auth.gate_enabled() and not auth.path_is_open(request.url.path):
            role = auth.token_role(request.cookies.get(auth.COOKIE_NAME))
            # The SPA has no cookie; it authenticates with the same signed
            # token in an Authorization: Bearer header. A 401 tells it to
            # clear the token and show its own login screen.
            if role is None:
                role = auth.token_role(
                    auth.bearer_token(request.headers.get("authorization"))
                )
            if role is None:
                return JSONResponse(
                    {"error": "authentication required"}, status_code=401
                )
        request.state.role = auth.ROLE_OPERATOR
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
            return JSONResponse(
                {"token": auth.issue_token(auth.ROLE_OPERATOR), "role": auth.ROLE_OPERATOR}
            )
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
        role = auth.code_role(code)
        with open_store() as store:
            if role is None:
                ratelimit.register_failure(store, caller, now)
            else:
                ratelimit.register_success(store, caller)
        if role is None:
            return JSONResponse({"error": "invalid code"}, status_code=401)
        return JSONResponse({"token": auth.issue_token(role), "role": role})

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
        return JSONResponse({"ok": True, "run_id": run_id, "label": label})

    @app.post("/api/runs/{run_id}/delete")
    def delete_run(run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found("Run not found")
            store.delete_run(run_id)
            # A deleted run must not leave its intake pointing at a gone run;
            # put the intake back in the queue so it can be re-run.
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_RECEIVED, run_id=None,
                    updated_at=_now_iso(),
                )
        # Remove the on-disk work tree, but only inside data_root/runs — never
        # follow a stored path outside the volume.
        try:
            work_dir = Path(run.work_dir).resolve()
            if runs_root in work_dir.parents and work_dir.is_dir():
                shutil.rmtree(work_dir, ignore_errors=True)
        except (OSError, ValueError):
            pass
        return JSONResponse({"ok": True, "run_id": run_id, "deleted": True})

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
        entry = {
            "ts": _now_iso(),
            "role": request.state.role,
            "page": page,
            "run_id": _run_id_from_path(page),
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

    @app.get("/api/runs/{run_id}")
    def api_workbench(run_id: str):
        """The review render model (build_view) for the SPA's workbench
        screen. jsonable_encoder handles the view's Decimal / date values
        for the display-only client."""
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
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
        with open_store() as store:
            return JSONResponse(store.get_settings())

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
        with open_store() as store:
            settings = store.set_settings(patch, _now_iso())
        return JSONResponse(settings)

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
    def api_memory():
        """Everything the tool has learned (merchant categories, vendor
        aliases, FX means) grouped by table, for the SPA memory screen.
        build_memory_view is already a JSON-safe dict; jsonable_encoder is
        kept for symmetry with the other render-model routes."""
        return JSONResponse(
            jsonable_encoder(build_memory_view(app.state.learning_db_path))
        )

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
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        learned = commit_to_memory(
            run, decisions, overrides, app.state.learning_db_path, _now_iso()
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
    # (whole tables / whole entities instead of one merchant).
    @app.post("/api/memory/reset")
    async def api_memory_reset(request: Request):
        body = await request.json() if await request.body() else {}
        table = (body.get("table") or "").strip() or None
        legal_entity_id = (body.get("legal_entity_id") or "").strip() or None
        reset_memory(app.state.learning_db_path, table, legal_entity_id)
        return JSONResponse(
            {"ok": True, "table": table, "legal_entity_id": legal_entity_id}
        )

    return app
