"""FastAPI app: the gated browser front end for the Lead Desk.

``create_app(data_root)`` builds the application; ``serve.py`` launches it with
uvicorn. Every route opens a short-lived ``ContactStore`` against the SQLite db
under ``data_root``.

Routes:

    GET  /                        pipeline board (filters ?tier=&stage=&owner=&bucket=&q=)
    GET  /contacts/{id}           per-contact timeline + judgment + log-a-touch
    POST /contacts/{id}/touch     append one hand-logged outreach event
    POST /contacts/{id}/suppress  do-not-contact toggle
    POST /contacts/{id}/fields    BANT / demo / verdict / next-step update
    GET  /export.csv /export.xlsx regenerate the master sheet from the db
    POST /events                  event sink for the cloud capture worker (shared secret)
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse, Response,
)
from fastapi.templating import Jinja2Templates

from . import auth
from .service import (
    EDITABLE_FLAGS, EDITABLE_TEXT, apply_fields, build_board,
    build_contact_view, create_contact, ingest_event, log_touch, toggle_suppress,
)
from ..sync import have_creds, run_all, run_sync
from .store import CHANNELS, DIRECTIONS, EVENT_TYPES, ContactStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(data_root: str | Path | None = None) -> FastAPI:
    data_root_path = Path(
        data_root or os.environ.get("LEAD_DESK_DATA", "lead-desk-data")
    ).resolve()
    data_root_path.mkdir(parents=True, exist_ok=True)
    db_path = data_root_path / "lead-desk.sqlite"

    app = FastAPI(title="Brisken Lead Desk")
    app.state.db_path = db_path
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    def open_store() -> ContactStore:
        return ContactStore(db_path)

    def current_user(request: Request) -> str:
        return auth.read_user(request.cookies.get(auth.COOKIE_NAME)) or "local"

    # --- gate (hosted only) ---------------------------------------------
    @app.middleware("http")
    async def require_login(request: Request, call_next):
        if auth.gate_enabled() and not auth.path_is_open(request.url.path):
            if not auth.read_user(request.cookies.get(auth.COOKIE_NAME)):
                if request.method == "GET":
                    return RedirectResponse(url="/login", status_code=303)
                return JSONResponse({"error": "authentication required"}, status_code=401)
        return await call_next(request)

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request):
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {"error": None})

    @app.post("/login")
    def login_submit(request: Request, code: str = Form("")):
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        user = auth.resolve_user(code)
        if not user:
            return templates.TemplateResponse(
                request, "login.html", {"error": "Wrong access code."}, status_code=401
            )
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(
            auth.COOKIE_NAME, auth.issue_token(user),
            max_age=auth.SESSION_MAX_AGE, httponly=True,
            secure=auth.cookie_is_secure(), samesite="lax",
        )
        return resp

    @app.post("/logout")
    def logout():
        resp = RedirectResponse(url="/login", status_code=303)
        resp.delete_cookie(auth.COOKIE_NAME)
        return resp

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"status": "ok"})

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    # --- board ----------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def board(request: Request, tier: str = "", stage: str = "", owner: str = "",
              bucket: str = "", q: str = "", show_suppressed: str = ""):
        filters = {"tier": tier, "stage": stage, "owner": owner,
                   "bucket": bucket, "q": q, "show_suppressed": show_suppressed}
        with open_store() as store:
            view = build_board(store, filters)
        return templates.TemplateResponse(
            request, "board.html", {"view": view, "user": current_user(request)}
        )

    @app.get("/contacts/{contact_id}", response_class=HTMLResponse)
    def contact(request: Request, contact_id: str):
        with open_store() as store:
            view = build_contact_view(store, contact_id)
        if view is None:
            return HTMLResponse("Contact not found", status_code=404)
        return templates.TemplateResponse(
            request, "contact.html",
            {"view": view, "user": current_user(request),
             "channels": CHANNELS, "directions": DIRECTIONS, "event_types": EVENT_TYPES},
        )

    @app.post("/contacts/{contact_id}/touch")
    def post_touch(request: Request, contact_id: str, channel: str = Form("email"),
                   direction: str = Form("outbound"), type: str = Form("sent"),
                   ts: str = Form(""), subject: str = Form(""), detail: str = Form("")):
        with open_store() as store:
            try:
                log_touch(store, contact_id, channel=channel, direction=direction,
                          type=type, ts=ts, subject=subject or None, detail=detail or None,
                          user=current_user(request))
            except ValueError:
                return HTMLResponse("Contact not found", status_code=404)
        return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)

    @app.post("/contacts/{contact_id}/suppress")
    def post_suppress(request: Request, contact_id: str,
                      suppressed: str = Form(""), reason: str = Form("")):
        on = suppressed.strip() in ("1", "true", "on")
        with open_store() as store:
            if store.get_contact(contact_id) is None:
                return HTMLResponse("Contact not found", status_code=404)
            toggle_suppress(store, contact_id, on, reason.strip() or None,
                            current_user(request))
        return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)

    @app.post("/contacts/{contact_id}/fields")
    async def post_fields(request: Request, contact_id: str):
        """Accept every editable field (identity / classification / provenance /
        qualification). Only keys present in the form are updated; checkboxes
        absent from the form resolve to 0."""
        form = await request.form()
        fields: dict = {}
        for k in EDITABLE_TEXT:
            if k in form:
                fields[k] = str(form[k]).strip()
        # A checkbox absent from the POST means "unchecked" ONLY for the flags the
        # submitting form declares it manages (via _managed_flags). This lets a
        # partial form (e.g. inline board edit) touch text fields without zeroing
        # every BANT/provenance flag.
        managed = set(str(form.get("_managed_flags", "")).split())
        for k in EDITABLE_FLAGS:
            if k in managed:
                fields[k] = 1 if str(form.get(k, "")).strip() in ("1", "true", "on") else 0
        with open_store() as store:
            try:
                apply_fields(store, contact_id, fields, current_user(request))
            except ValueError:
                return HTMLResponse("Contact not found", status_code=404)
        return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)

    @app.post("/contacts")
    async def create_contact_route(request: Request):
        """Add a new lead. Dedupes by email (redirects to the existing contact if
        the address is already on file)."""
        form = await request.form()
        data = {k: str(form.get(k, "")).strip() for k in
                ("first_name", "last_name", "company", "job_title",
                 "email", "tier", "lead_type")}
        if not any(data[k] for k in ("first_name", "last_name", "company", "email")):
            return HTMLResponse("Need at least a name, company, or email.", status_code=400)
        with open_store() as store:
            contact_id, _created = create_contact(store, data, current_user(request))
        return RedirectResponse(url=f"/contacts/{contact_id}", status_code=303)

    # --- exports --------------------------------------------------------
    @app.get("/export.csv")
    def export_csv():
        from ..export import to_csv_bytes
        with open_store() as store:
            data = to_csv_bytes(store)
        return Response(content=data, media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=lead-desk-rome-2026.csv"})

    @app.get("/export.xlsx")
    def export_xlsx():
        from ..export import to_xlsx_bytes
        with open_store() as store:
            data = to_xlsx_bytes(store)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=lead-desk-rome-2026.xlsx"},
        )

    # --- event sink (cloud capture worker) ------------------------------
    @app.post("/events")
    async def post_events(request: Request):
        if not auth.ingest_authorized(request.headers.get("authorization")):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        events = body if isinstance(body, list) else [body]
        results = []
        with open_store() as store:
            for ev in events:
                if not isinstance(ev, dict):
                    results.append({"ok": False, "reason": "not an object"})
                    continue
                results.append(ingest_event(store, ev))
        inserted = sum(1 for r in results if r.get("inserted"))
        return JSONResponse({"ok": True, "inserted": inserted, "results": results})

    # --- sheet sync (Graph app-only) ------------------------------------
    @app.post("/sync")
    async def post_sync(request: Request, campaign: str = ""):
        """Pull the campaign master sheet(s) into the DB now. Allowed for a
        logged-in user (the board button) or the ingest secret (external cron)."""
        import asyncio
        authed = bool(auth.read_user(request.cookies.get(auth.COOKIE_NAME))) \
            or auth.ingest_authorized(request.headers.get("authorization"))
        if auth.gate_enabled() and not authed:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        if not have_creds():
            return JSONResponse({"error": "graph credentials not configured"}, status_code=503)
        try:
            if campaign:
                reps = [await asyncio.to_thread(run_sync, data_root_path, campaign=campaign)]
            else:
                reps = await asyncio.to_thread(run_all, data_root_path)
        except Exception as exc:  # noqa: BLE001 - surface sync failures to the caller
            return JSONResponse({"error": str(exc)}, status_code=500)
        if "text/html" in (request.headers.get("accept") or ""):
            return RedirectResponse(url="/", status_code=303)  # browser form submit
        return JSONResponse({"ok": True, "synced": [
            {"campaign": r.get("campaign"), "contacts": r.get("total_contacts"),
             "source_modified": (r.get("source") or {}).get("last_modified")}
            for r in reps]})

    # --- daily sheet -> DB scheduler ------------------------------------
    @app.on_event("startup")
    async def _start_sync_scheduler():
        import asyncio
        if os.environ.get("LEAD_DESK_SYNC_DISABLED"):
            return
        if not have_creds():
            print("[sync] Graph credentials absent; daily scheduler disabled")
            return
        interval = int(os.environ.get("LEAD_DESK_SYNC_INTERVAL", "86400"))  # daily

        async def _loop():
            while True:
                try:
                    reps = await asyncio.to_thread(run_all, data_root_path)
                    tot = sum(r.get("total_contacts", 0) for r in reps)
                    print(f"[sync] pass ok: {len(reps)} campaign(s), {tot} contacts")
                except Exception as exc:  # noqa: BLE001
                    print(f"[sync] pass failed: {exc}")
                await asyncio.sleep(interval)

        asyncio.create_task(_loop())

    return app
