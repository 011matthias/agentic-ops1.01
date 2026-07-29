"""FastAPI app: the gated browser front end for the Lead Desk.

``create_app(data_root)`` builds the application; ``serve.py`` launches it with
uvicorn. Every route opens a short-lived ``ContactStore`` against the SQLite db
under ``data_root``.

Routes (cookie gate):

    GET  /                        pipeline board (?campaign=&tier=&stage=&owner=&degree=&bucket=&q=)
    GET  /contacts/{id}           per-contact timeline + judgment + cadence card
    POST /contacts/{id}/touch     append one hand-logged outreach event
    POST /contacts/{id}/suppress  do-not-contact toggle
    POST /contacts/{id}/fields    BANT / demo / verdict / next-step update
    GET  /export.csv /export.xlsx regenerate the master sheet from the db
    GET  /campaigns               campaign list + create
    GET  /campaigns/{cid}         campaign admin (upload, rules, sequences, approval)
    POST /campaigns/{cid}/...     upload / rules / reclassify / sequences / approve / pause / resume
    POST /templates               save a template (new version)
    POST /enrollments/{eid}/...   degree override / remove / manual step done
    POST /attempts/retry          re-queue a stalled/parked send (human decision)
    POST /worker/kill             global kill switch toggle

Machine APIs (own bearer secrets, outside the cookie gate):

    POST /events                  event sink for capture workers (ingest secret)
    GET  /api/worker/status       kill switch + per-campaign window/cap state (worker secret)
    POST /api/outbox/claim        lease due sends, rendered with pinned copy
    POST /api/outbox/result       ack/nack a leased send (emits the 'sent' event)
    POST /api/outbox/draft-sent   a Dirk-draft observed actually sent
    GET  /api/worker/watchlist    enrolled emails + drafted attempts to correlate
    POST /api/worker/heartbeat    worker liveness (staleness alerting)
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import (
    FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response,
)
from fastapi.templating import Jinja2Templates

from . import accounts, auth, cadence, uploads
from .service import (
    EDITABLE_FLAGS, EDITABLE_TEXT, StaleWriteError, apply_fields, build_board,
    build_contact_view, create_contact, ingest_event, log_touch, now_iso,
    toggle_suppress,
)
from .store import (
    CHANNELS, DEGREES, DIRECTIONS, EVENT_TYPES, SEND_MODES, USER_ROLES,
    ContactStore,
)
from ..sync import have_creds, run_all, run_sync

# Login-page banners, keyed by ?notice= / ?err= so a POST can 303-redirect
# (no form re-submit on refresh) and the GET renders the message.
_LOGIN_NOTICES = {
    "sent": "Check your email. We just sent you a one-time sign-in link.",
    "pending": "Your access request is with an admin. We'll email you once it's approved.",
}
_LOGIN_ERRORS = {
    "throttled": "Too many attempts. Wait a few minutes and try again.",
    "badlink": "That sign-in link is invalid, expired, or already used. Request a new one below.",
    "invalidemail": "Enter a valid email address.",
    "nomailer": "Email sign-in is temporarily unavailable. Please contact an admin.",
    "sendfail": "We couldn't send the email just now. Please try again in a moment.",
}

_TEMPLATES_DIR = Path(__file__).parent / "templates"
# Packaged brand assets (design tokens, Brisken logos, favicon). Served
# ungated so the login page can style itself; nothing here is client data.
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_TYPES = {".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}


def _cookie_value(cookie_header: str, name: str) -> str | None:
    for part in (cookie_header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == name:
            return v
    return None


class _CSRFMiddleware:
    """Double-submit CSRF check on cookie-authed, url-encoded mutating forms.
    Bearer machine APIs (Authorization header), the ingest/open paths, and
    multipart uploads are exempt (the latter keep SameSite=Lax protection).
    Defense-in-depth on top of the SameSite=Lax session cookie."""

    _EXEMPT = ("/events", "/api/", "/sync", "/login", "/logout")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH", "DELETE"):
            return await self.app(scope, receive, send)
        path = scope["path"]
        headers = {k.decode("latin1").lower(): v.decode("latin1")
                   for k, v in scope.get("headers", [])}
        if (any(path == p or path.startswith(p) for p in self._EXEMPT)
                or "authorization" in headers
                or not headers.get("content-type", "").startswith(
                    "application/x-www-form-urlencoded")):
            return await self.app(scope, receive, send)
        cookie = _cookie_value(headers.get("cookie", ""), auth.COOKIE_NAME)
        if not auth.gate_enabled() or not cookie:
            return await self.app(scope, receive, send)  # local/dev: no gate, no CSRF
        body = b""
        while True:
            msg = await receive()
            body += msg.get("body", b"")
            if not msg.get("more_body"):
                break
        from urllib.parse import parse_qs
        submitted = parse_qs(body.decode("utf-8", "replace")).get("csrf", [""])[0]
        if not auth.csrf_valid(cookie, submitted):
            resp = JSONResponse(
                {"error": "CSRF check failed; reload the page and try again."},
                status_code=403)
            return await resp(scope, receive, send)
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        return await self.app(scope, replay, send)


def create_app(data_root: str | Path | None = None) -> FastAPI:
    data_root_path = Path(
        data_root or os.environ.get("LEAD_DESK_DATA", "lead-desk-data")
    ).resolve()
    data_root_path.mkdir(parents=True, exist_ok=True)
    db_path = data_root_path / "lead-desk.sqlite"

    app = FastAPI(title="Brisken Lead Desk")
    app.state.db_path = db_path

    def _csrf_context(request: Request) -> dict:
        # Auto-inject the session CSRF token into every template render.
        return {"csrf_token": auth.csrf_for_cookie(request.cookies.get(auth.COOKIE_NAME))}

    def _nav_context(request: Request) -> dict:
        # Expose is_admin so base.html can show the admin nav link only to
        # admins. Fail-closed: any lookup error hides the link, never 500s.
        ident = auth.read_user(request.cookies.get(auth.COOKIE_NAME))
        if not ident and not auth.gate_enabled():
            ident = "local"
        admin = False
        if ident:
            try:
                with ContactStore(db_path) as store:
                    admin = accounts.is_admin(store, ident)
            except Exception:  # noqa: BLE001 - a nav flag must never break a render
                admin = False
        return {"is_admin": admin}

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR),
                                context_processors=[_csrf_context, _nav_context])
    app.add_middleware(_CSRFMiddleware)

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

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        # Templates use inline styles/scripts + onclick handlers, so 'unsafe-inline'
        # is required for now (plan: start permissive, tighten later).
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "base-uri 'self'; frame-ancestors 'none'")
        return resp

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, notice: str = "", err: str = ""):
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {
            "error": _LOGIN_ERRORS.get(err),
            "notice": _LOGIN_NOTICES.get(notice),
            "auth_email_on": accounts.auth_emails_enabled(),
        })

    def _client_ip(request: Request) -> str:
        # Fly puts the real client IP in Fly-Client-IP; request.client.host is
        # the fly-proxy, so keying a throttle on it would rate-limit everyone.
        return request.headers.get("fly-client-ip") or (
            request.client.host if request.client else "unknown")

    @app.post("/login/magic")
    def login_magic(request: Request, email: str = Form("")):
        """Passwordless: email in -> single-use link out (approved), or an
        access request recorded (new). Never reveals a password; rate-limited
        per client IP so it cannot be used to spam an inbox."""
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        ip = _client_ip(request)
        if auth.magic_blocked(ip):
            return RedirectResponse(url="/login?err=throttled", status_code=303)
        auth.record_magic_request(ip)
        with open_store() as store:
            result = accounts.request_magic_link(
                store, email, base_url=accounts.base_url_from(request),
                ip=ip, now=now_iso())
        # Map the outcome to a neutral banner. pending / disabled / new all read
        # as "with an admin" so the page never discloses account state.
        target = {
            "sent": "/login?notice=sent",
            "pending_new": "/login?notice=pending",
            "pending": "/login?notice=pending",
            "disabled": "/login?notice=pending",
            "invalid": "/login?err=invalidemail",
            "no_mailer": "/login?err=nomailer",
            "send_failed": "/login?err=sendfail",
        }.get(result["status"], "/login?notice=sent")
        return RedirectResponse(url=target, status_code=303)

    @app.get("/auth/verify")
    def auth_verify(request: Request, token: str = ""):
        if not auth.gate_enabled():
            return RedirectResponse(url="/", status_code=303)
        with open_store() as store:
            email = accounts.verify_and_login(store, token, now_iso())
        if not email:
            return RedirectResponse(url="/login?err=badlink", status_code=303)
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(
            auth.COOKIE_NAME, auth.issue_token(email),
            max_age=auth.SESSION_MAX_AGE, httponly=True,
            secure=auth.cookie_is_secure(), samesite="lax",
        )
        return resp

    @app.post("/logout")
    def logout():
        resp = RedirectResponse(url="/login", status_code=303)
        resp.delete_cookie(auth.COOKIE_NAME)
        return resp

    # --- admin: user management (gated + admin-only) --------------------
    # These paths are NOT in OPEN_PATHS, so require_login already blocks the
    # unauthenticated; every handler then re-checks admin (deny by default).

    @app.get("/admin/users", response_class=HTMLResponse)
    def admin_users(request: Request):
        with open_store() as store:
            if not accounts.is_admin(store, current_user(request)):
                return HTMLResponse("Forbidden", status_code=403)
            users = [dict(u) for u in store.list_users()]
        return templates.TemplateResponse(request, "admin_users.html", {
            "users": users, "user": current_user(request),
            "roles": USER_ROLES,
            "auth_email_on": accounts.auth_emails_enabled(),
        })

    @app.post("/admin/users/approve")
    def admin_user_approve(request: Request, email: str = Form(...)):
        with open_store() as store:
            if not accounts.is_admin(store, current_user(request)):
                return HTMLResponse("Forbidden", status_code=403)
            accounts.approve_user(store, email, by=current_user(request),
                                  now=now_iso(),
                                  base_url=accounts.base_url_from(request))
        return RedirectResponse(url="/admin/users", status_code=303)

    @app.post("/admin/users/disable")
    def admin_user_disable(request: Request, email: str = Form(...)):
        with open_store() as store:
            if not accounts.is_admin(store, current_user(request)):
                return HTMLResponse("Forbidden", status_code=403)
            u = store.get_user(email)
            # Never disable the last approved admin - that would lock everyone
            # out of the admin surface.
            if (u and u["role"] == "admin" and u["status"] == "approved"
                    and store.count_admins() <= 1):
                return HTMLResponse("Cannot disable the last admin.", status_code=400)
            store.set_user_status(auth.normalize_email(email), "disabled",
                                  current_user(request), now_iso())
        return RedirectResponse(url="/admin/users", status_code=303)

    @app.post("/admin/users/role")
    def admin_user_role(request: Request, email: str = Form(...),
                        role: str = Form(...)):
        role = role.strip().lower()
        if role not in USER_ROLES:
            return HTMLResponse("bad role", status_code=400)
        with open_store() as store:
            if not accounts.is_admin(store, current_user(request)):
                return HTMLResponse("Forbidden", status_code=403)
            email_n = auth.normalize_email(email)
            u = store.get_user(email_n)
            if (u and u["role"] == "admin" and role == "member"
                    and store.count_admins() <= 1):
                return HTMLResponse("Cannot demote the last admin.", status_code=400)
            store.set_user_role(email_n, role)
        return RedirectResponse(url="/admin/users", status_code=303)

    @app.post("/admin/users/invite")
    def admin_user_invite(request: Request, email: str = Form(...),
                          name: str = Form(""), role: str = Form("member")):
        with open_store() as store:
            if not accounts.is_admin(store, current_user(request)):
                return HTMLResponse("Forbidden", status_code=403)
            accounts.invite_user(store, email, name=name,
                                 role=role.strip().lower(), by=current_user(request),
                                 now=now_iso(),
                                 base_url=accounts.base_url_from(request))
        return RedirectResponse(url="/admin/users", status_code=303)

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

    # --- board ----------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def board(request: Request, campaign: str = "", tier: str = "", stage: str = "",
              owner: str = "", degree: str = "", bucket: str = "", q: str = "",
              show_suppressed: str = ""):
        filters = {"tier": tier, "stage": stage, "owner": owner, "degree": degree,
                   "bucket": bucket, "q": q, "show_suppressed": show_suppressed}
        with open_store() as store:
            cid = campaign.strip()
            if not cid:
                first = store.list_campaigns()
                cid = first[0]["campaign_id"] if first else "rome-2026"
            view = build_board(store, filters, campaign=cid)
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

    @app.post("/contacts/{contact_id}/mark-replied")
    def post_mark_replied(request: Request, contact_id: str, back: str = Form("")):
        """One-click 'I replied to them': logs an outbound email so our last_out
        is now newer than their inbound, clearing the row from the action set.
        No email is sent - this only records that the operator handled it."""
        with open_store() as store:
            try:
                log_touch(store, contact_id, channel="email", direction="outbound",
                          type="sent", ts=None, subject="Replied",
                          detail="Marked replied from the board", user=current_user(request))
            except ValueError:
                return HTMLResponse("Contact not found", status_code=404)
        target = back if back.startswith("/") else f"/contacts/{contact_id}"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/contacts/{contact_id}/merge")
    def post_merge(request: Request, contact_id: str, survivor: str = Form("")):
        """Merge this contact (the loser) into ``survivor`` (a contact_id). The
        loser becomes a suppressed 'duplicate' tombstone pointing at survivor;
        events + enrollments move over. Redirects to the survivor."""
        survivor = survivor.strip()
        if not survivor or survivor == contact_id:
            return HTMLResponse("Pick a different survivor contact", status_code=400)
        with open_store() as store:
            if store.get_contact(contact_id) is None or store.get_contact(survivor) is None:
                return HTMLResponse("Contact not found", status_code=404)
            store.merge_contacts(survivor, contact_id, now_iso())
        return RedirectResponse(url=f"/contacts/{survivor}", status_code=303)

    @app.post("/contacts/{contact_id}/suppress")
    def post_suppress(request: Request, contact_id: str,
                      suppressed: str = Form(""), reason: str = Form(""),
                      back: str = Form("")):
        on = suppressed.strip() in ("1", "true", "on")
        with open_store() as store:
            if store.get_contact(contact_id) is None:
                return HTMLResponse("Contact not found", status_code=404)
            toggle_suppress(store, contact_id, on, reason.strip() or None,
                            current_user(request))
        target = back.strip() if back.strip().startswith("/") else f"/contacts/{contact_id}"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/contacts/{contact_id}/fields")
    async def post_fields(request: Request, contact_id: str):
        """Accept every editable field (identity / classification / provenance /
        qualification). Only keys present in the form are updated; a checkbox
        flag resolves to 0 only when its form declares it manages that flag
        (via _managed_flags), so a partial edit never zeroes untouched flags."""
        form = await request.form()
        fields: dict = {}
        for k in EDITABLE_TEXT:
            if k in form:
                fields[k] = str(form[k]).strip()
        managed = set(str(form.get("_managed_flags", "")).split())
        for k in EDITABLE_FLAGS:
            if k in managed:
                fields[k] = 1 if str(form.get(k, "")).strip() in ("1", "true", "on") else 0
        expected = str(form.get("updated_at", "")).strip() or None
        back = str(form.get("back", "")).strip()
        with open_store() as store:
            try:
                apply_fields(store, contact_id, fields, current_user(request),
                             expected_updated_at=expected)
            except StaleWriteError:
                # Someone (a sync or another editor) changed the row since this
                # form loaded: reject and reload rather than clobber the newer data.
                sep = "&" if (back and "?" in back) else "?"
                target = f"{back}{sep}stale=1" if back.startswith("/") \
                    else f"/contacts/{contact_id}?stale=1"
                return RedirectResponse(url=target, status_code=303)
            except ValueError:
                return HTMLResponse("Contact not found", status_code=404)
        # Board inline edits pass back=/?... so the operator stays on the board.
        target = back if back.startswith("/") else f"/contacts/{contact_id}"
        return RedirectResponse(url=target, status_code=303)

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

    # --- campaigns --------------------------------------------------------
    def _campaign_or_404(store: ContactStore, cid: str):
        row = store.get_campaign(cid)
        if row is None:
            return None
        return dict(row)

    @app.get("/campaigns", response_class=HTMLResponse)
    def campaigns_list(request: Request):
        with open_store() as store:
            rows = [dict(c) for c in store.list_campaigns()]
            for c in rows:
                c["enrolled"] = store.conn.execute(
                    "SELECT COUNT(*) FROM enrollments WHERE campaign_id = ?",
                    (c["campaign_id"],),
                ).fetchone()[0]
            kill = (store.get_state("kill_switch") or "0") == "1"
            mailbox_cap = int(store.get_state("mailbox_daily_cap") or 0)
        return templates.TemplateResponse(
            request, "campaigns.html",
            {"campaigns": rows, "kill_switch": kill, "mailbox_cap": mailbox_cap,
             "user": current_user(request)},
        )

    @app.post("/campaigns")
    def campaigns_create(request: Request, campaign_id: str = Form(...),
                         name: str = Form(""), daily_cap: str = Form("40")):
        cid = campaign_id.strip().lower().replace(" ", "-")
        if not cid:
            return HTMLResponse("campaign id required", status_code=400)
        with open_store() as store:
            store.create_campaign(cid, name.strip() or cid, now_iso(),
                                  daily_cap=int(daily_cap or 40))
            if not store.get_rules(cid):
                store.replace_rules(cid, cadence.DEFAULT_RULES)
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.get("/campaigns/{cid}", response_class=HTMLResponse)
    def campaign_admin(request: Request, cid: str):
        with open_store() as store:
            campaign = _campaign_or_404(store, cid)
            if campaign is None:
                return HTMLResponse("Campaign not found", status_code=404)
            report = cadence.approval_report(store, cid)
            rules = [dict(r) for r in store.get_rules(cid)]
            sequences = store.sequences_for_campaign(cid)
            all_templates = [dict(t) for t in store.list_templates()]
            enrollments = [dict(r) for r in store.enrollments_for_campaign(cid)]
            attempts = [dict(a) for a in store.attempts_for_campaign(cid)]
            pins = store.get_pins(cid)
            kill_switch = (store.get_state("kill_switch") or "0") == "1"
        return templates.TemplateResponse(
            request, "campaign.html",
            {"campaign": campaign, "report": report, "rules": rules,
             "sequences": sequences, "templates_": all_templates,
             "enrollments": enrollments, "attempts": attempts, "pins": pins,
             "degrees": DEGREES, "send_modes": SEND_MODES,
             "kill_switch": kill_switch,
             "user": current_user(request)},
        )

    @app.post("/campaigns/{cid}/upload")
    async def campaign_upload(request: Request, cid: str,
                              file: UploadFile = File(...)):
        data = await file.read()
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            result = uploads.import_upload(store, cid, file.filename or "upload.csv",
                                           data, current_user(request))
            store.set_state(f"upload-report:{cid}", json.dumps(result), now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}?uploaded=1", status_code=303)

    @app.post("/campaigns/{cid}/rules")
    def campaign_rules(request: Request, cid: str, rules_json: str = Form("")):
        try:
            rules = json.loads(rules_json)
            assert isinstance(rules, list)
            for r in rules:
                json.loads(r["predicate"]) if isinstance(r["predicate"], str) else r["predicate"]
                r["priority"], r["degree"], r["label"]
        except Exception:
            return HTMLResponse("invalid rules JSON", status_code=400)
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            for r in rules:
                if not isinstance(r["predicate"], str):
                    r["predicate"] = json.dumps(r["predicate"])
            store.replace_rules(cid, rules)
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/reclassify")
    def campaign_reclassify(request: Request, cid: str):
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            cadence.classify_enrollments(store, cid, current_user(request), now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/sequences")
    def campaign_sequences(request: Request, cid: str, degree: str = Form(...),
                           name: str = Form(""), send_mode: str = Form("auto-matthias"),
                           steps: str = Form("")):
        """Steps: one per line, 'channel template_key day_offset'."""
        parsed = []
        for i, raw in enumerate(s for s in steps.splitlines() if s.strip()):
            parts = raw.split()
            if len(parts) != 3 or parts[0] not in ("email", "linkedin"):
                return HTMLResponse(
                    f"bad step line {i + 1!r}: want 'channel template_key day_offset'",
                    status_code=400)
            try:
                off = int(parts[2])
            except ValueError:
                return HTMLResponse(f"bad day_offset on line {i + 1}", status_code=400)
            parsed.append({"step_no": i + 1, "channel": parts[0],
                           "template_key": parts[1], "day_offset": off})
        if send_mode not in SEND_MODES:
            return HTMLResponse("bad send_mode", status_code=400)
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            if parsed:
                store.upsert_sequence(cid, degree.strip(), name.strip() or degree,
                                      send_mode, parsed)
            else:
                store.delete_sequence(cid, degree.strip())
            # Structure changed: a frozen approval no longer matches reality.
            cadence.supersede_approval(store, cid, f"sequence '{degree}' edited")
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/sequences/{degree}/delta")
    def campaign_sequence_delta(request: Request, cid: str, degree: str,
                                steps: str = Form("")):
        """Live sequence edit: append / insert / swap FUTURE steps on an
        approved-or-sending campaign WITHOUT demoting it to draft. Already-sent
        steps are immutable; the delta refuses any change to them (the operator
        pauses and re-approves for that). Steps: one per line,
        'channel template_key day_offset'."""
        parsed = []
        for i, raw in enumerate(s for s in steps.splitlines() if s.strip()):
            parts = raw.split()
            if len(parts) != 3 or parts[0] not in ("email", "linkedin"):
                return HTMLResponse(
                    f"bad step line {i + 1!r}: want 'channel template_key day_offset'",
                    status_code=400)
            try:
                off = int(parts[2])
            except ValueError:
                return HTMLResponse(f"bad day_offset on line {i + 1}", status_code=400)
            parsed.append({"channel": parts[0], "template_key": parts[1],
                           "day_offset": off})
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            result = cadence.apply_sequence_delta(store, cid, degree.strip(),
                                                  parsed, current_user(request))
            store.set_state(f"delta-result:{cid}", json.dumps(result), now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/schedule")
    def campaign_schedule(request: Request, cid: str,
                          start_not_before: str = Form(""),
                          ramp_per_day: str = Form("")):
        """Set (or clear) the 'no earlier than' start date and the per-day new
        contact ramp. A pacing change alters neither copy nor recipient list, so
        it does NOT supersede an approval; it only shifts when steps become due."""
        raw = start_not_before.strip()
        if raw:
            try:
                date.fromisoformat(raw)
            except ValueError:
                return HTMLResponse("start_not_before must be YYYY-MM-DD",
                                    status_code=400)
        ramp_raw = ramp_per_day.strip()
        ramp_val = None
        if ramp_raw:
            try:
                ramp_val = int(ramp_raw)
            except ValueError:
                return HTMLResponse("ramp_per_day must be a whole number",
                                    status_code=400)
            if ramp_val < 0:
                return HTMLResponse("ramp_per_day must be >= 0", status_code=400)
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            store.update_campaign(cid, {"start_not_before": raw or None,
                                        "ramp_per_day": ramp_val}, now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}?scheduled=1", status_code=303)

    @app.post("/settings/mailbox-cap")
    def settings_mailbox_cap(request: Request, mailbox_daily_cap: str = Form("")):
        """Global per-mailbox daily send cap across ALL campaigns from one warm
        mailbox (0 or blank = off)."""
        raw = mailbox_daily_cap.strip()
        val = 0
        if raw:
            try:
                val = int(raw)
            except ValueError:
                return HTMLResponse("mailbox_daily_cap must be a whole number",
                                    status_code=400)
            if val < 0:
                return HTMLResponse("mailbox_daily_cap must be >= 0", status_code=400)
        with open_store() as store:
            store.set_state("mailbox_daily_cap", str(val), now_iso())
        return RedirectResponse(url="/campaigns?mbxcap=1", status_code=303)

    @app.post("/templates")
    def template_save(request: Request, template_key: str = Form(...),
                      channel: str = Form("email"), subject: str = Form(""),
                      body: str = Form(...), campaign: str = Form("")):
        key = template_key.strip()
        if not key or channel not in ("email", "linkedin"):
            return HTMLResponse("bad template", status_code=400)
        with open_store() as store:
            store.save_template(key, channel, subject.strip() or None, body,
                                current_user(request), now_iso())
        target = f"/campaigns/{campaign}" if campaign.strip() else "/campaigns"
        return RedirectResponse(url=target, status_code=303)

    @app.get("/templates/{key}/preview")
    def template_preview(request: Request, key: str, contact_id: str = ""):
        with open_store() as store:
            tpl = store.get_template(key)
            if tpl is None:
                return JSONResponse({"error": "unknown template"}, status_code=404)
            contact = dict(store.get_contact(contact_id) or {}) if contact_id else {}
        return JSONResponse({
            "template_key": key, "version": tpl["version"],
            "subject": cadence.render(tpl["subject"] or "", contact),
            "body": cadence.render(tpl["body"], contact),
            "missing": cadence.missing_vars(
                (tpl["subject"] or "") + " " + tpl["body"], contact) if contact else [],
        })

    @app.post("/enrollments/{eid}/degree")
    def enrollment_degree(request: Request, eid: int, degree: str = Form(...),
                          campaign: str = Form("")):
        with open_store() as store:
            enr = store.get_enrollment(eid)
            if enr is None:
                return HTMLResponse("Enrollment not found", status_code=404)
            store.set_degree(eid, degree.strip() or None, "manual",
                             f"set by {current_user(request)}")
            store.add_event(
                contact_id=enr["contact_id"], ts=now_iso(), channel="email",
                direction="outbound", type="note", subject="degree override",
                detail=f"{enr['campaign_id']}: degree={degree.strip()}",
                source="manual", created_by=current_user(request),
                campaign=enr["campaign_id"], now=now_iso(),
            )
        target = f"/campaigns/{campaign}" if campaign.strip() else "/"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/enrollments/{eid}/remove")
    def enrollment_remove(request: Request, eid: int, campaign: str = Form("")):
        with open_store() as store:
            enr = store.get_enrollment(eid)
            if enr is None:
                return HTMLResponse("Enrollment not found", status_code=404)
            if enr["approved_at"]:
                return HTMLResponse(
                    "Enrollment already approved; suppress the contact instead.",
                    status_code=400)
            store.remove_enrollment(eid)
        target = f"/campaigns/{campaign}" if campaign.strip() else "/"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/enrollments/{eid}/steps/{step_no}/done")
    def enrollment_step_done(request: Request, eid: int, step_no: int):
        with open_store() as store:
            result = cadence.mark_manual_done(store, eid, step_no,
                                              current_user(request))
        if not result.get("ok"):
            return HTMLResponse(result.get("error", "error"), status_code=400)
        return RedirectResponse(url=request.headers.get("referer") or "/",
                                status_code=303)

    @app.post("/campaigns/{cid}/approve")
    def campaign_approve(request: Request, cid: str, confirm: str = Form("")):
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            result = cadence.approve_campaign(store, cid, current_user(request),
                                              confirm)
            store.set_state(f"approve-result:{cid}", json.dumps(result), now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/start-sending")
    def campaign_start_sending(request: Request, cid: str, confirm: str = Form("")):
        """The second gate: an approved (frozen) campaign starts sending only
        when a human presses this and re-types the id."""
        with open_store() as store:
            if store.get_campaign(cid) is None:
                return HTMLResponse("Campaign not found", status_code=404)
            result = cadence.start_sending(store, cid, current_user(request),
                                           confirm)
            store.set_state(f"start-result:{cid}", json.dumps(result), now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/pause")
    def campaign_pause(request: Request, cid: str):
        with open_store() as store:
            campaign = store.get_campaign(cid)
            if campaign is None:
                return HTMLResponse("Campaign not found", status_code=404)
            # Pausing only makes sense for a live 'sending' campaign; an
            # 'approved' (not yet sending) one is already not sending.
            if campaign["status"] == "sending":
                store.update_campaign(cid, {"status": "paused"}, now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/campaigns/{cid}/resume")
    def campaign_resume(request: Request, cid: str):
        with open_store() as store:
            campaign = store.get_campaign(cid)
            if campaign is None:
                return HTMLResponse("Campaign not found", status_code=404)
            if campaign["status"] != "paused":
                return HTMLResponse("Only a paused campaign can resume.", status_code=400)
            if not campaign["approved_at"]:
                return HTMLResponse("Never approved; run the approval.", status_code=400)
            # A paused campaign was sending before the pause, so resume goes
            # straight back to 'sending'.
            store.update_campaign(cid, {"status": "sending"}, now_iso())
        return RedirectResponse(url=f"/campaigns/{cid}", status_code=303)

    @app.post("/attempts/retry")
    def attempt_retry(request: Request, attempt_key: str = Form(...),
                      campaign: str = Form("")):
        """Human decision on a stalled/parked send: re-queue it for the worker."""
        with open_store() as store:
            attempt = store.get_attempt(attempt_key.strip())
            if attempt is None:
                return HTMLResponse("Attempt not found", status_code=404)
            if attempt["status"] not in ("stalled", "parked", "failed"):
                return HTMLResponse("Not retryable", status_code=400)
            # Reset attempt_count too: try_lease re-leases a 'queued' row only
            # while attempt_count < max_attempts, so an operator retry of a
            # send that exhausted the transient-retry cap was a silent no-op
            # without this. An operator-initiated retry is a fresh start.
            store.update_attempt(attempt_key.strip(), {
                "status": "queued", "failure_reason": None, "attempt_count": 0,
            })
        target = f"/campaigns/{campaign}" if campaign.strip() else "/"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/attempts/mark-sent")
    def attempt_mark_sent(request: Request, attempt_key: str = Form(...),
                          campaign: str = Form("")):
        """Human resolution of an ambiguous stall: assert the mail DID go out."""
        with open_store() as store:
            attempt = store.get_attempt(attempt_key.strip())
            if attempt is None:
                return HTMLResponse("Attempt not found", status_code=404)
            enr = store.get_enrollment(int(attempt["enrollment_id"]))
            now = now_iso()
            store.update_attempt(attempt_key.strip(),
                                 {"status": "sent", "resolved_at": now})
            if enr is not None:
                store.add_event(
                    contact_id=enr["contact_id"], ts=now, channel="email",
                    direction="outbound", type="sent",
                    subject=attempt["rendered_subject"],
                    detail=f"cadence step {attempt['step_no']} (marked sent by "
                           f"{current_user(request)})",
                    source="manual", created_by=current_user(request),
                    ext_key=attempt["attempt_key"], campaign=enr["campaign_id"],
                    now=now,
                )
        target = f"/campaigns/{campaign}" if campaign.strip() else "/"
        return RedirectResponse(url=target, status_code=303)

    @app.post("/worker/kill")
    def worker_kill(request: Request, on: str = Form("")):
        with open_store() as store:
            store.set_state("kill_switch",
                            "1" if on.strip() in ("1", "true", "on") else "0",
                            now_iso())
        return RedirectResponse(url="/campaigns", status_code=303)

    # --- worker API (bearer-gated, outside the cookie gate) ----------------
    def _worker_auth(request: Request) -> bool:
        return auth.worker_authorized(request.headers.get("authorization"))

    @app.get("/api/worker/status")
    def worker_status(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        at = cadence.now_utc()
        with open_store() as store:
            kill = (store.get_state("kill_switch") or "0") == "1"
            campaigns = []
            for row in store.list_campaigns():
                c = dict(row)
                window = cadence.parse_window(c.get("send_window"))
                today = cadence._campaign_today(c, at).isoformat()
                sent_today = store.cadence_sends_today(c["campaign_id"], today)
                campaigns.append({
                    "campaign": c["campaign_id"], "status": c["status"],
                    "window": window, "in_window": cadence.in_window(window, at),
                    "daily_cap": c["daily_cap"], "daily_sent": sent_today,
                    "daily_remaining": max(0, int(c["daily_cap"]) - sent_today),
                    "throttle_seconds": c["throttle_seconds"],
                    "jitter_seconds": c["jitter_seconds"],
                })
        return JSONResponse({"server_time": cadence._iso(at),
                             "kill_switch": kill, "campaigns": campaigns})

    @app.post("/api/outbox/claim")
    async def outbox_claim(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            body = {}
        worker_id = str(body.get("worker_id") or "worker")
        max_items = min(int(body.get("max_items") or 10), 50)
        peek = bool(body.get("peek"))
        with open_store() as store:
            result = cadence.claim_sends(store, worker_id, max_items, peek=peek)
        return JSONResponse(result)

    @app.post("/api/outbox/result")
    async def outbox_result(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        with open_store() as store:
            result = cadence.resolve_result(store, body)
        status = result.pop("http", 200 if result.get("ok") else 400)
        return JSONResponse(result, status_code=status)

    @app.post("/api/outbox/draft-sent")
    async def outbox_draft_sent(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        with open_store() as store:
            result = cadence.confirm_draft_sent(store, body)
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    @app.get("/api/worker/watchlist")
    def worker_watchlist(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        with open_store() as store:
            contacts = store.conn.execute(
                """
                SELECT DISTINCT c.contact_id, c.email, c.alt_email
                FROM enrollments en JOIN contacts c ON c.contact_id = en.contact_id
                JOIN campaigns cp ON cp.campaign_id = en.campaign_id
                WHERE cp.status IN ('approved', 'sending', 'paused')
                """
            ).fetchall()
            drafted = store.conn.execute(
                "SELECT attempt_key, to_addr, rendered_subject "
                "FROM send_attempts WHERE status = 'drafted'"
            ).fetchall()
        return JSONResponse({
            "contacts": [{"contact_id": r["contact_id"], "email": r["email"],
                          "alt_email": r["alt_email"]} for r in contacts],
            "drafted": [{"attempt_key": r["attempt_key"], "to": r["to_addr"],
                         "subject": r["rendered_subject"]} for r in drafted],
        })

    @app.post("/api/worker/heartbeat")
    async def worker_heartbeat(request: Request):
        if not _worker_auth(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            body = {}
        with open_store() as store:
            store.set_state("worker_heartbeat", json.dumps({
                "worker_id": body.get("worker_id"), "ts": now_iso(),
                "counters": body.get("counters") or {},
            }), now_iso())
        return JSONResponse({"ok": True})

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

    # --- sheet sync (Graph app-only, sheet -> DB) -----------------------
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
        is_browser = "text/html" in (request.headers.get("accept") or "")
        try:
            if campaign:
                reps = [await asyncio.to_thread(run_sync, data_root_path, campaign=campaign)]
            else:
                reps = await asyncio.to_thread(run_all, data_root_path)
        except Exception as exc:  # noqa: BLE001 - surface sync failures to the caller
            with open_store() as st:
                st.set_state("last_sync_error", f"{now_iso()}: {exc}", now_iso())
            if is_browser:  # readable banner, not a raw JSON dump in the browser
                return RedirectResponse(url="/?sync_error=1", status_code=303)
            return JSONResponse({"error": str(exc)}, status_code=500)
        total = sum(r.get("total_contacts", 0) or 0 for r in reps)
        diffs = sum(r.get("sheet_diff_count", 0) or 0 for r in reps)
        if is_browser:  # confirmation banner instead of a silent reload
            return RedirectResponse(url=f"/?synced={total}&sdiffs={diffs}", status_code=303)
        return JSONResponse({"ok": True, "synced": [
            {"campaign": r.get("campaign"), "contacts": r.get("total_contacts"),
             "sheet_diffs": r.get("sheet_diff_count"),
             "source_modified": (r.get("source") or {}).get("last_modified")}
            for r in reps]})

    # --- cloud worker tick loop (4d; OPT-IN via LEAD_DESK_CLOUD_WORKER=1) --
    @app.on_event("startup")
    async def _start_cloud_worker():
        import asyncio
        from ..cloud_worker import cloud_worker_enabled, run_tick
        enabled, reason = cloud_worker_enabled()
        if not enabled:
            print(f"[cloud-worker] disabled: {reason}")
            return
        interval = int(os.environ.get("LEAD_DESK_TICK_INTERVAL", "900"))

        async def _loop():
            backoff = 60
            while True:
                try:
                    rep = await asyncio.to_thread(run_tick, data_root_path)
                    print(f"[cloud-worker] tick ok: kill={rep.get('kill_switch')} "
                          f"paused={rep.get('paused')} claimed={rep.get('claimed')} "
                          f"capture={rep.get('capture') or rep.get('capture_error')}")
                    sleep_for, backoff = interval, 60
                except Exception as exc:  # noqa: BLE001 - the loop must survive a bad tick
                    print(f"[cloud-worker] tick failed: {exc}")
                    sleep_for = min(backoff, interval)
                    backoff = min(backoff * 2, 3600)
                await asyncio.sleep(sleep_for)

        asyncio.create_task(_loop())

    # --- daily sheet -> DB scheduler (guarded; inert without Graph creds) --
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
            backoff = 60
            while True:
                try:
                    reps = await asyncio.to_thread(run_all, data_root_path)
                    tot = sum(r.get("total_contacts", 0) for r in reps)
                    print(f"[sync] pass ok: {len(reps)} campaign(s), {tot} contacts")
                    sleep_for, backoff = interval, 60
                except Exception as exc:  # noqa: BLE001
                    print(f"[sync] pass failed: {exc}")
                    try:
                        with open_store() as st:
                            st.set_state("last_sync_error", f"{now_iso()}: {exc}", now_iso())
                    except Exception:  # noqa: BLE001 - never let error-recording kill the loop
                        pass
                    # Retry in MINUTES (exponential, capped at 1h), not after the
                    # full daily interval, so a transient Graph 503 recovers fast.
                    sleep_for = min(backoff, interval)
                    backoff = min(backoff * 2, 3600)
                await asyncio.sleep(sleep_for)

        asyncio.create_task(_loop())

    return app
