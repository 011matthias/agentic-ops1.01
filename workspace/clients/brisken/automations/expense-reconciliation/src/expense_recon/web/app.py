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
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .service import (
    DEFAULT_EXPENSE_COLUMN_MAP,
    STATEMENT_MAP_FIELDS,
    PreparedRun,
    RunForm,
    RunInputError,
    build_memory_view,
    build_view,
    commit_to_memory,
    create_run,
    execute_run,
    forget_memory_vendor,
    matched_autopick_decisions,
    prepare_run,
    regenerate_report,
    regenerate_zoho,
    reset_memory,
    validate_manual_match,
)
from .store import STATUS_CONFIRMED, VALID_STATUSES, RunStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _operator() -> str | None:
    return (
        os.environ.get("EXPENSE_RECON_OPERATOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
    )


def _run_job(
    db_path: Path, jobs: dict, job_id: str, prepared: PreparedRun
) -> None:
    """Run a prepared reconciliation off the request (PR F).

    Starlette runs this sync function in a worker thread, so the event loop
    stays free to serve the polling page. It opens its own RunStore (a
    SQLite connection is per-thread) and records the outcome in the
    in-memory job map the poller reads.
    """
    try:
        with RunStore(db_path) as store:
            run_id = execute_run(store, prepared)
        jobs[job_id] = {"status": "done", "run_id": run_id, "error": None}
    except Exception as exc:  # noqa: BLE001 - surface any failure to the poller
        jobs[job_id] = {"status": "error", "run_id": None, "error": str(exc)}


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
    # In-memory background-job map (PR F). A single-user local tool runs one
    # process, so an in-memory map is enough; a job lost to a server restart
    # just means re-uploading the file.
    app.state.jobs = {}
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    def open_store() -> RunStore:
        return RunStore(db_path)

    @app.get("/favicon.ico")
    def favicon():
        # No icon asset; answer cleanly so the browser stops logging a 404.
        from fastapi.responses import Response

        return Response(status_code=204)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        with open_store() as store:
            runs = store.list_runs()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "runs": runs,
                "statement_fields": STATEMENT_MAP_FIELDS,
                "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
                "error": None,
                "headers": None,
            },
        )

    @app.post("/runs")
    async def post_run(
        request: Request,
        background: BackgroundTasks,
        statement: UploadFile,
        receipts: UploadFile,
        account_id: str = Form(""),
        legal_entity_id: str = Form(""),
        account_card_currency: str = Form("USD"),
        sheet_name: str = Form(""),
        receipts_source: str = Form("csv"),
        receipts_default_currency: str = Form("USD"),
        use_llm: str = Form(""),
        expense_column_map: str = Form(""),
        map_transaction_date: str = Form(""),
        map_amount: str = Form(""),
        map_vendor: str = Form(""),
        map_posting_date: str = Form(""),
        map_transaction_currency: str = Form(""),
    ):
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
            return _render_form_error(
                templates, request, f"Receipt column map is not valid JSON: {exc}"
            )

        form = RunForm(
            account_id=account_id.strip(),
            legal_entity_id=legal_entity_id.strip(),
            account_card_currency=account_card_currency.strip() or "USD",
            sheet_name=sheet_name.strip() or None,
            column_map_overrides={k: v for k, v in overrides.items() if v},
            receipts_source=receipts_source.strip() or "csv",
            expense_column_map=expense_map,
            receipts_default_currency=receipts_default_currency.strip() or "USD",
            use_llm=bool(use_llm.strip()),
        )

        statement_bytes = await statement.read()
        receipts_bytes = await receipts.read()
        if not statement_bytes:
            return _render_form_error(templates, request, "No statement file uploaded.")
        if not receipts_bytes:
            return _render_form_error(templates, request, "No receipts file uploaded.")

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
                    templates, request, exc.message, headers=exc.headers
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
                templates, request, exc.message, headers=exc.headers
            )

        job_id = uuid.uuid4().hex[:12]
        app.state.jobs[job_id] = {"status": "running", "run_id": None, "error": None}
        background.add_task(
            _run_job, app.state.db_path, app.state.jobs, job_id, prepared
        )
        return templates.TemplateResponse(
            request,
            "running.html",
            {"job_id": job_id, "label": form.account_id or "this month"},
        )

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str):
        # PR F — the running page polls this until status flips to done (then
        # it navigates to the workbench) or error.
        job = app.state.jobs.get(job_id)
        if job is None:
            return JSONResponse({"error": "unknown job"}, status_code=404)
        return JSONResponse(job)

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def workbench(request: Request, run_id: str):
        with open_store() as store:
            run = store.get_run(run_id)
            if run is None:
                return HTMLResponse("Run not found", status_code=404)
            decisions = store.get_decisions(run_id)
            overrides = store.get_category_overrides(run_id)
        view = build_view(run, decisions, overrides)
        return templates.TemplateResponse(request, "workbench.html", {"view": view})

    @app.post("/runs/{run_id}/decisions")
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

    @app.post("/runs/{run_id}/decisions/confirm-matched")
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
            if store.get_run(run_id) is None:
                return JSONResponse({"error": "run not found"}, status_code=404)
            store.set_category_override(
                run_id, document_id, line_index, category, zoho_account, _now_iso()
            )
        return JSONResponse({"ok": True})

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
    message: str,
    headers: list[str] | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "runs": [],
            "statement_fields": STATEMENT_MAP_FIELDS,
            "expense_map": DEFAULT_EXPENSE_COLUMN_MAP,
            "error": message,
            "headers": headers,
        },
        status_code=400,
    )
