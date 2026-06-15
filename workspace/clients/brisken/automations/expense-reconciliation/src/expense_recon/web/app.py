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
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .service import (
    DEFAULT_EXPENSE_COLUMN_MAP,
    STATEMENT_MAP_FIELDS,
    RunForm,
    RunInputError,
    build_memory_view,
    build_view,
    commit_to_memory,
    create_run,
    forget_memory_vendor,
    regenerate_report,
    reset_memory,
)
from .store import VALID_STATUSES, RunStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _operator() -> str | None:
    return (
        os.environ.get("EXPENSE_RECON_OPERATOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
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

        try:
            with open_store() as store:
                run_id = create_run(
                    store,
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
            return _render_form_error(
                templates, request, exc.message, headers=exc.headers
            )

        return RedirectResponse(url=f"/runs/{run_id}", status_code=303)

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
