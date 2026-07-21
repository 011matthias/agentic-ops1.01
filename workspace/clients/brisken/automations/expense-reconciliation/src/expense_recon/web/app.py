"""FastAPI app: the browser front end for the reconciliation tool.

`create_app(data_root)` builds the application; `serve.py` launches it
with uvicorn. Every route opens a short-lived `RunStore` against the
SQLite db under `data_root`; uploads and generated exports live under
`data_root/runs/<run_id>/`.

Routes:

    GET  /                      upload + recent runs
    POST /runs                  run a reconciliation from the upload
    GET  /runs/{id}             the review workbench
    POST /runs/{id}/decisions   confirm / reject / pick a match (JSON)
    POST /runs/{id}/categories  reclassify one receipt line (JSON)
    GET  /runs/{id}/report.xlsx download the report with edits applied
    GET  /runs/{id}/zoho.csv    download the Zoho journal import (matched)
    GET  /runs/{id}/reconciled.csv  download the flat reconciled CSV
    GET  /guide / /how-it-works  embedded docs
    POST /feedback              anchored reviewer note (any logged-in role)
    GET  /feedback-log          the collected notes (operator only)
    GET  /feedback.jsonl        raw notes download (operator only)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.templating import Jinja2Templates

from ..cards_provision import card_by_key, load_cards
from .service import (
    DEFAULT_EXPENSE_COLUMN_MAP,
    STATEMENT_MAP_FIELDS,
    PreparedRun,
    RunForm,
    RunInputError,
    build_memory_view,
    build_view,
    commit_to_memory,
    compare_runs,
    create_intake,
    create_run,
    execute_run,
    forget_memory_vendor,
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
    STATUS_CONFIRMED,
    VALID_DISPOSITIONS,
    VALID_DUP_RESOLUTIONS,
    VALID_STATUSES,
    RunStore,
)
from . import auth

_TEMPLATES_DIR = Path(__file__).parent / "templates"
# Packaged brand assets (design tokens, Brisken logos, favicon). Served
# ungated so the login page can style itself; nothing here is client data.
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_TYPES = {".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wants_json(request: Request) -> bool:
    """True when this request came in on the /api surface.

    The browser-facing mutations answer with a 303 back to the page they
    were posted from; the SPA needs a JSON body it can read a result and
    an error out of. Rather than fork the handlers (two implementations
    of publish that drift), each is mounted on both paths and branches
    here. Keyed on the path, not on the Accept header, so the contract is
    a property of the URL the caller chose and cannot be changed by a
    header the browser happens to send.
    """
    return request.url.path.startswith("/api/")


def _not_found(request: Request, message: str):
    """404 in the shape the caller's surface expects."""
    if _wants_json(request):
        return JSONResponse({"error": message.lower()}, status_code=404)
    return HTMLResponse(message, status_code=404)


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

    def _template_globals(request: Request) -> dict:
        # Every template can branch on the session role (user surface vs
        # operator surface) without each handler threading it through.
        return {"role": getattr(request.state, "role", auth.ROLE_OPERATOR)}

    templates = Jinja2Templates(
        directory=str(_TEMPLATES_DIR), context_processors=[_template_globals]
    )

    def open_store() -> RunStore:
        return RunStore(db_path)

    # --- Password gate (hosted only) -------------------------------------
    # Active iff an access code is set. Loopback/local use leaves the codes
    # unset, stays open, and resolves to the operator role (full surface);
    # a public host MUST set them (this tool serves financial data). See
    # auth.py for the role model.
    @app.middleware("http")
    async def require_login(request: Request, call_next):
        role = auth.ROLE_OPERATOR
        if auth.gate_enabled():
            role = auth.token_role(request.cookies.get(auth.COOKIE_NAME))
            # The SPA front end (Lovable) has no cookie; it authenticates
            # with the same signed token in an Authorization: Bearer header.
            if role is None:
                role = auth.token_role(
                    auth.bearer_token(request.headers.get("authorization"))
                )
            if role is None and not auth.path_is_open(request.url.path):
                # HTML pages redirect a signed-out browser to the login
                # form; API paths return a JSON 401 the SPA can act on
                # (clear the token, show its own login screen).
                if request.method == "GET" and not request.url.path.startswith("/api/"):
                    return RedirectResponse(url="/login", status_code=303)
                return JSONResponse({"error": "authentication required"}, status_code=401)
        request.state.role = role or auth.ROLE_USER
        if request.state.role != auth.ROLE_OPERATOR and auth.path_requires_operator(
            request.url.path, request.method
        ):
            if request.method == "GET" and not request.url.path.startswith("/api/"):
                return RedirectResponse(url="/", status_code=303)
            return JSONResponse({"error": "operator access required"}, status_code=403)
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

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request) -> HTMLResponse:
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login")
    def login_submit(request: Request, code: str = Form("")):
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        role = auth.code_role(code)
        if role is None:
            return templates.TemplateResponse(
                request, "login.html", {"error": "Wrong access code."}, status_code=401
            )
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(
            auth.COOKIE_NAME, auth.issue_token(role),
            max_age=auth.SESSION_MAX_AGE, httponly=True,
            secure=auth.cookie_is_secure(), samesite="lax",
        )
        return resp

    @app.post("/logout")
    def logout():
        resp = RedirectResponse(url="/login", status_code=303)
        resp.delete_cookie(auth.COOKIE_NAME)
        return resp

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
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - a malformed body is a client error
            body = {}
        code = str((body or {}).get("code", ""))
        role = auth.code_role(code)
        if role is None:
            return JSONResponse({"error": "invalid code"}, status_code=401)
        return JSONResponse({"token": auth.issue_token(role), "role": role})

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"status": "ok"})

    @app.get("/favicon.ico")
    def favicon():
        return FileResponse(_STATIC_DIR / "favicon.png", media_type="image/png")

    @app.get("/static/{name}")
    def static_asset(name: str):
        # Basename-only lookup in the packaged static dir; unknown names 404.
        target = _STATIC_DIR / Path(name).name
        media_type = _STATIC_TYPES.get(target.suffix.lower())
        if media_type is None or not target.is_file():
            return HTMLResponse("Not found", status_code=404)
        return FileResponse(
            target, media_type=media_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    def _operator_home_ctx(store: RunStore, *, error=None, headers=None) -> dict:
        return {
            "runs": store.list_runs(),
            "intakes": store.list_intakes(),
            "cards": load_cards(),
            "statement_fields": STATEMENT_MAP_FIELDS,
            "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
            "error": error,
            "headers": headers,
        }

    def _user_home_ctx(store: RunStore, *, error=None) -> dict:
        return {
            "intakes": store.list_intakes(),
            "published_runs": store.list_runs(published_only=True),
            "cards": load_cards(),
            "error": error,
        }

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        with open_store() as store:
            if request.state.role == auth.ROLE_OPERATOR:
                return templates.TemplateResponse(
                    request, "home_operator.html", _operator_home_ctx(store)
                )
            return templates.TemplateResponse(
                request, "home_user.html", _user_home_ctx(store)
            )

    # ── Intake (testing mode): the USER path. Saves the documents, runs
    # nothing. Operators run the pipeline from the queue; the dev-side
    # notifier polls /api/operator/state and mails us about new uploads.
    # Upload a document set. Mounted twice; the multipart body is the
    # same on both, only the response shape differs (see `_wants_json`).
    @app.post("/api/intakes")
    @app.post("/intakes")
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
            if _wants_json(request):
                return JSONResponse({"error": exc.message}, status_code=400)
            with open_store() as store:
                if request.state.role == auth.ROLE_OPERATOR:
                    return templates.TemplateResponse(
                        request,
                        "home_operator.html",
                        _operator_home_ctx(store, error=exc.message),
                        status_code=400,
                    )
                return templates.TemplateResponse(
                    request,
                    "home_user.html",
                    _user_home_ctx(store, error=exc.message),
                    status_code=400,
                )
        if _wants_json(request):
            return JSONResponse(
                {"ok": True, "intake_id": intake_row.intake_id,
                 "label": intake_row.label, "status": intake_row.status}
            )
        return RedirectResponse(url="/", status_code=303)

    # Replace (or late-add) files on a queued intake (2026-07-16 user
    # feedback: a wrongly-attached file needs a way out). `received` only;
    # the service layer enforces that and validates extensions.
    @app.post("/api/intakes/{intake_id}/files")
    @app.post("/intakes/{intake_id}/files")
    async def post_intake_files(
        request: Request,
        intake_id: str,
        statement: UploadFile | None = None,
        receipts: UploadFile | None = None,
    ):
        with open_store() as store:
            intake = store.get_intake(intake_id)
        if intake is None:
            return _not_found(request, "Upload not found")

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
            if _wants_json(request):
                return JSONResponse({"error": exc.message}, status_code=400)
            with open_store() as store:
                if request.state.role == auth.ROLE_OPERATOR:
                    return templates.TemplateResponse(
                        request,
                        "home_operator.html",
                        _operator_home_ctx(store, error=exc.message),
                        status_code=400,
                    )
                return templates.TemplateResponse(
                    request,
                    "home_user.html",
                    _user_home_ctx(store, error=exc.message),
                    status_code=400,
                )
        if _wants_json(request):
            return JSONResponse({"ok": True, "intake_id": intake_id})
        return RedirectResponse(url="/", status_code=303)

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
    ) -> RunForm:
        """Shared form parsing for POST /runs and POST /intakes/{id}/run.
        Raises RunInputError for a user-fixable problem. A provisioned card
        preset fills account/entity/currency; explicit fields still win."""
        overrides = {
            "transaction_date": map_transaction_date.strip(),
            "amount": map_amount.strip(),
            "vendor": map_vendor.strip(),
            "posting_date": map_posting_date.strip(),
            "transaction_currency": map_transaction_currency.strip(),
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

    def _start_background_run(request: Request, background: BackgroundTasks, prepared: PreparedRun, label: str):
        job_id = uuid.uuid4().hex[:12]
        with open_store() as store:
            store.create_job(job_id, prepared.intake_id, _now_iso())
        background.add_task(_run_job, app.state.db_path, job_id, prepared)
        # The page renders a poller; the SPA gets the job id and polls
        # GET /jobs/{id} itself.
        if _wants_json(request):
            return JSONResponse({"ok": True, "job_id": job_id, "label": label})
        return templates.TemplateResponse(
            request, "running.html", {"job_id": job_id, "label": label}
        )

    @app.post("/runs")
    async def post_run(
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
        card_key: str = Form(""),
    ):
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
                card_key=card_key,
            )
        except RunInputError as exc:
            return _render_form_error(templates, request, open_store, exc.message)

        statement_bytes = await statement.read()
        receipts_bytes = await receipts.read()
        if not statement_bytes:
            return _render_form_error(
                templates, request, open_store, "No statement file uploaded."
            )
        if not receipts_bytes:
            return _render_form_error(
                templates, request, open_store, "No receipts file uploaded."
            )

        statement_name = statement.filename or "statement.csv"
        receipts_name = receipts.filename or "receipts.csv"

        # Sync seam (tests): run inline and 303 to the workbench, the
        # original contract. Default (production): background the slow
        # pipeline and hand back a polling page so an LLM run never blocks.
        if os.environ.get("EXPENSE_RECON_WEB_SYNC") == "1":
            try:
                with open_store() as store:
                    run_id = create_run(
                        store,
                        app.state.data_root,
                        statement_bytes=statement_bytes,
                        statement_filename=statement_name,
                        receipts_bytes=receipts_bytes,
                        receipts_filename=receipts_name,
                        form=form,
                        now_iso=_now_iso(),
                        operator=_operator(),
                        learning_db_path=app.state.learning_db_path,
                    )
            except RunInputError as exc:
                return _render_form_error(
                    templates, request, open_store, exc.message, headers=exc.headers
                )
            return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

        # Async: validate synchronously (a bad column map is still a form
        # error), then run the pipeline in the background.
        try:
            prepared = prepare_run(
                app.state.data_root,
                statement_bytes=statement_bytes,
                statement_filename=statement_name,
                receipts_bytes=receipts_bytes,
                receipts_filename=receipts_name,
                form=form,
                now_iso=_now_iso(),
                operator=_operator(),
                learning_db_path=app.state.learning_db_path,
            )
        except RunInputError as exc:
            return _render_form_error(
                templates, request, open_store, exc.message, headers=exc.headers
            )
        return _start_background_run(
            request, background, prepared, form.account_id or "this month"
        )

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
        card_key: str = Form(""),
    ):
        """JSON twin of POST /runs for the SPA front end: upload statement +
        receipts, validate synchronously, kick the pipeline in the
        background, return {job_id}. The SPA polls GET /jobs/{job_id} until
        status flips to "done" (then navigates to /runs/{run_id}) or
        "error". A user-fixable input problem is a JSON 400, not an HTML
        form re-render. Always async (no sync seam): the SPA is built to
        poll."""
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
    @app.get("/intakes/{intake_id}/prepare", response_class=HTMLResponse)
    def intake_prepare(request: Request, intake_id: str):
        with open_store() as store:
            intake = store.get_intake(intake_id)
        if intake is None:
            return _not_found(request, "Upload not found")
        card = card_by_key(intake.card_key, load_cards())
        return templates.TemplateResponse(
            request,
            "operator_run.html",
            {
                "intake": intake,
                "card": card,
                "cards": load_cards(),
                "statement_fields": STATEMENT_MAP_FIELDS,
                "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
                "error": None,
                "headers": None,
            },
        )

    @app.post("/api/intakes/{intake_id}/run")
    @app.post("/intakes/{intake_id}/run")
    async def intake_run(
        request: Request,
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
        card_key: str = Form(""),
    ):
        with open_store() as store:
            intake = store.get_intake(intake_id)
        if intake is None:
            return _not_found(request, "Upload not found")

        def _error_page(message: str, headers=None, status_code: int = 400):
            if _wants_json(request):
                return JSONResponse(
                    {"error": message, "headers": headers},
                    status_code=status_code,
                )
            card = card_by_key(intake.card_key, load_cards())
            return templates.TemplateResponse(
                request,
                "operator_run.html",
                {
                    "intake": intake,
                    "card": card,
                    "cards": load_cards(),
                    "statement_fields": STATEMENT_MAP_FIELDS,
                    "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
                    "error": message,
                    "headers": headers,
                },
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
                card_key=card_key or intake.card_key or "",
            )
            prepared = prepare_intake_run(
                app.state.data_root,
                intake,
                form,
                now_iso=_now_iso(),
                operator=_operator(),
                learning_db_path=app.state.learning_db_path,
            )
        except RunInputError as exc:
            return _error_page(exc.message, headers=exc.headers)

        with open_store() as store:
            store.set_intake_status(
                intake_id, INTAKE_PROCESSING, updated_at=_now_iso()
            )

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
            return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

        return _start_background_run(request, background, prepared, intake.label)

    # ── Operator: publish a reviewed run back to the user ───────────────
    # Publish / unpublish. Mounted twice: the bare path answers the
    # server-rendered page with a redirect back to the run, the /api path
    # answers the SPA with JSON. `_wants_json` keys off the request path,
    # so one handler serves both contracts and they can never drift.
    # Operator-only on either path (auth.path_requires_operator
    # canonicalizes the /api prefix before matching its rules).
    @app.post("/api/runs/{run_id}/publish")
    @app.post("/runs/{run_id}/publish")
    def publish_run(run_id: str, request: Request):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found(request, "Run not found")
            store.set_run_published(run_id, True, _now_iso())
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_READY,
                    run_id=run_id, updated_at=_now_iso(),
                )
        if _wants_json(request):
            return JSONResponse({"ok": True, "run_id": run_id, "published": True})
        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

    @app.post("/api/runs/{run_id}/unpublish")
    @app.post("/runs/{run_id}/unpublish")
    def unpublish_run(run_id: str, request: Request):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return _not_found(request, "Run not found")
            store.set_run_published(run_id, False, None)
            if run.intake_id is not None:
                store.set_intake_status(
                    run.intake_id, INTAKE_PROCESSING, updated_at=_now_iso()
                )
        if _wants_json(request):
            return JSONResponse({"ok": True, "run_id": run_id, "published": False})
        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

    # ── Operator state API: polled by the dev-side notifier (server stays
    # API-free per the One Assessment precedent; mail is sent from a dev
    # machine, never from this box).
    @app.get("/api/operator/state")
    def operator_state():
        with open_store() as store:
            intakes = store.list_intakes()
            all_runs = store.list_runs()
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
                "feedback": {
                    "count": len(_read_feedback()),
                },
            }
        )

    # ── Reviewer feedback: the double-click widget in base.html posts here
    # from every logged-in page. Attribution comes from the SESSION (the
    # role), never from the body; the page path and the run id (when the
    # note was left on a run page) locate the note. Storage is an
    # append-only jsonl on the data volume; reading it is operator-only
    # (auth._OPERATOR_RULES).
    feedback_file = data_root_path / "feedback.jsonl"

    @app.post("/api/feedback")
    @app.post("/feedback")
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

    @app.get("/feedback-log", response_class=HTMLResponse)
    def feedback_log(request: Request) -> HTMLResponse:
        rows = _read_feedback()
        rows.reverse()  # newest first
        return templates.TemplateResponse(request, "feedback_log.html", {"rows": rows})

    @app.get("/feedback.jsonl")
    def feedback_raw() -> PlainTextResponse:
        text = feedback_file.read_text(encoding="utf-8") if feedback_file.exists() else ""
        return PlainTextResponse(text, media_type="application/x-ndjson")

    @app.get("/compare", response_class=HTMLResponse)
    def compare(request: Request, a: str = "", b: str = ""):
        # PR G — pick two runs, show the bucket deltas in the browser
        # (mirror of the CLI `diff`). The index already re-opens a run; this
        # adds the across-runs view.
        with open_store() as store:
            runs = store.list_runs()
            run_a = store.get_run(a.strip()) if a.strip() else None
            run_b = store.get_run(b.strip()) if b.strip() else None
        comparison = (
            compare_runs(run_a, run_b) if run_a is not None and run_b is not None else None
        )
        return templates.TemplateResponse(
            request,
            "compare.html",
            {
                "runs": runs,
                "a": a.strip(),
                "b": b.strip(),
                "run_a": run_a,
                "run_b": run_b,
                "comparison": comparison,
            },
        )

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str):
        # PR F — the running page polls this until status flips to done (then
        # it navigates to the workbench) or error. Durable read: the row
        # survives a restart, so an interrupted job reports honestly.
        with open_store() as store:
            job = store.get_job(job_id)
        if job is None:
            return JSONResponse({"error": "unknown job"}, status_code=404)
        return JSONResponse(job)

    def _visible_run(store: RunStore, request: Request, run_id: str):
        """The run, or None when it does not exist OR the session is a user
        and the run is unpublished (404 either way, so unpublished run ids
        are not confirmable from the user role)."""
        run = store.get_run(run_id)
        if run is None:
            return None
        if request.state.role != auth.ROLE_OPERATOR and not run.published:
            return None
        return run

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def workbench(request: Request, run_id: str):
        with open_store() as store:
            run = _visible_run(store, request, run_id)
            if run is None:
                return HTMLResponse("Run not found", status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
        view = build_view(run, decisions, overrides, resolutions)
        return templates.TemplateResponse(
            request, "workbench.html", {"view": view, "run": run}
        )

    @app.get("/api/runs/{run_id}")
    def api_workbench(request: Request, run_id: str):
        """JSON twin of the workbench: the same build_view render model the
        Jinja page uses, for the SPA front end to render the review screen.
        The mutation endpoints (/runs/{id}/decisions, /categories,
        /manual-match, /confirm-matched, /forget, /commit-memory) already
        speak JSON and are reused as-is. jsonable_encoder handles the view's
        Decimal / date values for the display-only client."""
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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
    @app.post("/runs/{run_id}/decisions")
    async def post_decision(run_id: str, request: Request):
        body = await request.json()
        tx_id = body.get("transaction_id")
        status = body.get("status")
        chosen = body.get("chosen_document_id")
        if not tx_id or status not in VALID_STATUSES:
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = _visible_run(store, request, run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_decision(run_id, tx_id, status, chosen, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    # §17 disposition. Registered on both the /api surface (the SPA's
    # merged JSON API) and the bare /runs/{id}/... family the other JSON
    # mutation handlers live on, so either client contract resolves. One
    # shared handler; the disposition upsert is status-preserving in the
    # store (never clobbers the row's triage verdict).
    @app.post("/api/runs/{run_id}/disposition")
    @app.post("/runs/{run_id}/disposition")
    async def post_disposition(run_id: str, request: Request):
        body = await request.json()
        tx_id = body.get("transaction_id")
        disposition = body.get("disposition")
        if not tx_id or disposition not in VALID_DISPOSITIONS:
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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
    # Registered on both the /api surface and the bare /runs family.
    @app.post("/api/runs/{run_id}/duplicates/resolve")
    @app.post("/runs/{run_id}/duplicates/resolve")
    async def post_duplicate_resolve(run_id: str, request: Request):
        body = await request.json()
        group_id = body.get("group_id") or body.get("group_key")
        resolution = body.get("resolution") or body.get("action")
        if not group_id or resolution not in VALID_DUP_RESOLUTIONS:
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            run = _visible_run(store, request, run_id)
            if run is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_duplicate_resolution(run_id, group_id, resolution, _now_iso())
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
            resolutions = store.get_duplicate_resolutions(run_id)
        view = build_view(run, decisions, overrides, resolutions)
        return JSONResponse({"ok": True, "summary": view["summary"]})

    # §16 export policy. GET is readable by any logged-in role (reference);
    # PUT is operator-only (enforced in auth._OPERATOR_RULES). The policy is
    # snapshotted into each new run's config at creation, so changing it
    # affects future runs, never re-writes a run already produced.
    @app.get("/api/settings")
    def api_get_settings(request: Request):
        with open_store() as store:
            return JSONResponse(store.get_settings())

    @app.put("/api/settings")
    async def api_put_settings(request: Request):
        body = await request.json()
        patch: dict = {}
        if "export_approved_only" in body:
            patch["export_approved_only"] = bool(body["export_approved_only"])
        with open_store() as store:
            settings = store.set_settings(patch, _now_iso())
        return JSONResponse(settings)

    @app.get("/api/compare")
    def api_compare(request: Request, a: str = "", b: str = ""):
        """JSON twin of the HTML /compare: the SPA picks two runs and shows
        the bucket deltas. The diff is computed server-side by
        `compare_runs` (the same function the Jinja page uses), so the front
        end never derives it. Returns the run list for the two selectors plus
        the comparison (null until both a and b resolve to real runs).
        Operator-only, mirroring the HTML compare rule."""
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
    def api_memory(request: Request):
        """JSON twin of the HTML /memory page: everything the tool has
        learned (merchant categories, vendor aliases, FX means) grouped by
        table, for the SPA memory screen. build_memory_view is already a
        JSON-safe dict; jsonable_encoder is kept for symmetry with the
        other /api render-model routes. Operator-only, mirroring the HTML
        /memory rule."""
        return JSONResponse(
            jsonable_encoder(build_memory_view(app.state.learning_db_path))
        )

    @app.post("/api/memory/forget")
    async def api_memory_forget(request: Request):
        """JSON twin of the /memory/forget form post: drop everything
        learned for one merchant in one entity so next month stops
        auto-filling it. Same {legal_entity_id, vendor} body and
        {ok, forgotten: <per-table delete counts>} reply as the workbench's
        /runs/{id}/forget. Operator-only."""
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
    @app.post("/runs/{run_id}/decisions/confirm-matched")
    def post_confirm_matched(run_id: str, request: Request):
        # PR A — one click confirms every matched-bucket transaction with
        # its auto-picked receipt, so only review + unmatched need hand
        # work. Reuses the per-row decision write; never stomps an
        # explicit confirm/reject.
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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

    @app.post("/api/runs/{run_id}/categories")
    @app.post("/runs/{run_id}/categories")
    async def post_category(run_id: str, request: Request):
        body = await request.json()
        document_id = body.get("document_id")
        line_index = body.get("line_index")
        category = body.get("category")
        zoho_account = body.get("zoho_account")
        if not document_id or not isinstance(line_index, int):
            return JSONResponse({"error": "bad request"}, status_code=400)
        with open_store() as store:
            if _visible_run(store, request, run_id) is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_category_override(
                run_id, document_id, line_index, category, zoho_account, _now_iso()
            )
        return JSONResponse({"ok": True})

    @app.post("/api/runs/{run_id}/manual-match")
    @app.post("/runs/{run_id}/manual-match")
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
            run = _visible_run(store, request, run_id)
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

    @app.post("/api/runs/{run_id}/forget")
    @app.post("/runs/{run_id}/forget")
    async def post_forget(run_id: str, request: Request):
        # PR C — "this was wrong": drop everything the tool learned for one
        # merchant so next month stops auto-filling it. JSON sibling of the
        # /memory/forget form post, so the workbench can forget in place and
        # then reopen the reclassify dropdown without a page nav.
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
    @app.post("/runs/{run_id}/commit-memory")
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
    def download_report(run_id: str, request: Request):
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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
    def download_zoho(run_id: str, request: Request):
        # PR E — the Zoho Books journal-entry import CSV, with the reviewer's
        # decisions + category overrides applied. Only effective matched
        # transactions are exported (the writer's posting policy).
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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
    def download_reconciled(run_id: str, request: Request):
        # The flat reconciled CSV — the CSV twin of the .xlsx report, with
        # the reviewer's decisions + category overrides applied. Every
        # statement line with its match status + matched-expense enrichment.
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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
    def download_writeback(run_id: str, request: Request):
        # L3 — her own uploaded workbook with one new "Zoho Account (tool)"
        # column; only for xlsx/xlsm statements.
        with open_store() as store:
            run = _visible_run(store, request, run_id)
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

    # ── Help: one merged trilingual page (replaces the old /guide +
    # /how-it-works standalone docs, which had drifted). Rendered inside
    # the app chrome so it inherits the brand tokens, theme, and role nav.
    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "help.html", {})

    @app.get("/guide")
    def guide_redirect():
        return RedirectResponse(url="/help", status_code=301)

    @app.get("/how-it-works")
    def how_it_works_redirect():
        return RedirectResponse(url="/help", status_code=301)

    # ── Memory (PR 2e): see and correct what the tool has learned ──────
    @app.get("/memory", response_class=HTMLResponse)
    def memory(request: Request):
        view = build_memory_view(app.state.learning_db_path)
        return templates.TemplateResponse(request, "memory.html", {"view": view})

    @app.post("/memory/forget")
    def memory_forget(
        legal_entity_id: str = Form(...), vendor: str = Form(...)
    ):
        forget_memory_vendor(app.state.learning_db_path, legal_entity_id, vendor)
        return RedirectResponse(url="/memory", status_code=303)

    # The SPA twin of the page's forget form. `/api/memory/forget` already
    # existed with a JSON body; this is the reset counterpart, which had no
    # JSON surface at all. Operator-only via the ^/memory($|/) rule, which
    # the /api canonicalization now also applies to /api/memory/reset.
    @app.post("/api/memory/reset")
    async def api_memory_reset(request: Request):
        body = await request.json() if await request.body() else {}
        table = (body.get("table") or "").strip() or None
        legal_entity_id = (body.get("legal_entity_id") or "").strip() or None
        reset_memory(app.state.learning_db_path, table, legal_entity_id)
        return JSONResponse(
            {"ok": True, "table": table, "legal_entity_id": legal_entity_id}
        )

    @app.post("/memory/reset")
    def memory_reset(
        table: str = Form(""), legal_entity_id: str = Form("")
    ):
        reset_memory(
            app.state.learning_db_path, table.strip() or None,
            legal_entity_id.strip() or None,
        )
        return RedirectResponse(url="/memory", status_code=303)

    return app


def _render_form_error(
    templates: Jinja2Templates,
    request: Request,
    open_store,
    message: str,
    headers: list[str] | None = None,
) -> HTMLResponse:
    # Operator-only surface (POST /runs is operator-gated), so the error
    # re-render is the operator home WITH its real context: losing the
    # recent-runs table on a form error was a long-standing paper cut.
    with open_store() as store:
        return templates.TemplateResponse(
            request,
            "home_operator.html",
            {
                "runs": store.list_runs(),
                "intakes": store.list_intakes(),
                "cards": load_cards(),
                "statement_fields": STATEMENT_MAP_FIELDS,
                "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
                "error": message,
                "headers": headers,
            },
            status_code=400,
        )
