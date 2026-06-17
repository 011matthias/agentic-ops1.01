"""Brisken OnePilot prototype: gated static host + feedback collector.

Serves the single-file marketing prototype behind a shared access code and
records reviewer feedback to a JSONL file on the Fly volume. The gate mirrors
the expense-reconciliation web gate (signed-cookie, env-activated): it is on
ONLY when ``BRISKEN_SITE_ACCESS_CODE`` is set, so local loopback runs stay
open. The cookie carries only an HMAC of a fixed marker, never the code.

Env vars:
    BRISKEN_SITE_ACCESS_CODE   shared password; gate is on iff set
    BRISKEN_SITE_AUTH_SECRET   HMAC key for the cookie (set in prod so
                               sessions survive restarts; random per-process
                               when unset)
    BRISKEN_SITE_DATA          dir for the feedback log (default ./data;
                               /data on Fly, the mounted volume)
    BRISKEN_SITE_HTML          path to the prototype HTML (default ./site/index.html)
    BRISKEN_SITE_INSECURE_COOKIE  set "1" to drop the cookie Secure flag for
                               local http testing (never in prod)
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)

# ---- configuration -------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
SITE_HTML = Path(os.environ.get("BRISKEN_SITE_HTML", str(APP_DIR / "site" / "index.html")))
DATA_DIR = Path(os.environ.get("BRISKEN_SITE_DATA", str(APP_DIR / "data")))
FEEDBACK_FILE = DATA_DIR / "feedback.jsonl"

COOKIE_NAME = "brisken_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours
OPEN_PATHS = frozenset({"/login", "/logout", "/healthz", "/favicon.ico"})
_PROCESS_SECRET = secrets.token_hex(32)


# ---- gate helpers --------------------------------------------------------
def access_code() -> "str | None":
    code = os.environ.get("BRISKEN_SITE_ACCESS_CODE", "").strip()
    return code or None


def gate_enabled() -> bool:
    return access_code() is not None


def _secret() -> bytes:
    return (os.environ.get("BRISKEN_SITE_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def issue_token() -> str:
    return hmac.new(_secret(), b"authenticated", hashlib.sha256).hexdigest()


def token_valid(token: "str | None") -> bool:
    return bool(token) and hmac.compare_digest(token, issue_token())


def code_matches(submitted: str) -> bool:
    code = access_code()
    return code is not None and hmac.compare_digest(submitted.strip(), code)


def cookie_is_secure() -> bool:
    return os.environ.get("BRISKEN_SITE_INSECURE_COOKIE") != "1"


def safe_next(value: str) -> str:
    """Only allow same-origin absolute paths as redirect targets."""
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"


# ---- app -----------------------------------------------------------------
app = FastAPI(title="Brisken OnePilot prototype", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def gate(request: Request, call_next):
    if gate_enabled() and request.url.path not in OPEN_PATHS:
        if not token_valid(request.cookies.get(COOKIE_NAME)):
            if request.url.path == "/feedback":
                return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
            return RedirectResponse("/login?next=" + request.url.path, status_code=303)
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(status_code=204)


def render_login(error: str, nxt: str) -> str:
    err_block = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return (
        LOGIN_TEMPLATE
        .replace("%%ERROR%%", err_block)
        .replace("%%NEXT%%", html.escape(nxt, quote=True))
    )


@app.get("/login", response_class=HTMLResponse)
async def login_form(next: str = "/") -> HTMLResponse:
    if not gate_enabled():
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_login("", safe_next(next)))


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    code = str(form.get("code", ""))
    nxt = safe_next(str(form.get("next", "/")))
    if code_matches(code):
        resp = RedirectResponse(nxt, status_code=303)
        resp.set_cookie(
            COOKIE_NAME,
            issue_token(),
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=cookie_is_secure(),
            samesite="lax",
        )
        return resp
    return HTMLResponse(render_login("That access code was not recognized.", nxt), status_code=401)


@app.get("/logout")
async def logout() -> RedirectResponse:
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    try:
        return HTMLResponse(SITE_HTML.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HTMLResponse("<h1>Prototype HTML not found.</h1>", status_code=500)


@app.post("/feedback")
async def feedback(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    name = str(data.get("name", "")).strip()
    comment = str(data.get("comment", "")).strip()
    if not name or not comment:
        return JSONResponse({"ok": False, "error": "name and comment are required"}, status_code=400)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "name": name[:200],
        "section": str(data.get("section", "")).strip()[:200],
        "anchor": str(data.get("anchor", "")).strip()[:300],
        "comment": comment[:8000],
        "path": str(data.get("path", ""))[:300],
        "title": str(data.get("title", ""))[:300],
        "ip": request.headers.get("fly-client-ip") or (request.client.host if request.client else ""),
        "ua": request.headers.get("user-agent", "")[:400],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return JSONResponse({"ok": True})


def _read_feedback() -> list:
    rows = []
    if FEEDBACK_FILE.exists():
        for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


@app.get("/feedback-log", response_class=HTMLResponse)
async def feedback_log() -> HTMLResponse:
    rows = _read_feedback()
    rows.reverse()  # newest first
    if rows:
        body = "".join(
            "<tr>"
            f"<td class=ts>{html.escape(r.get('ts',''))}</td>"
            f"<td>{html.escape(r.get('section','') or 'This page')}"
            f"{('<br><span class=role>&#8220;'+html.escape(r.get('anchor',''))+'&#8221;</span>') if r.get('anchor') else ''}</td>"
            f"<td class=comment>{html.escape(r.get('comment',''))}</td>"
            f"<td><b>{html.escape(r.get('name',''))}</b></td>"
            "</tr>"
            for r in rows
        )
    else:
        body = '<tr><td colspan="4" class="empty">No feedback submitted yet.</td></tr>'
    return HTMLResponse(
        LOG_TEMPLATE.replace("%%COUNT%%", str(len(rows))).replace("%%ROWS%%", body)
    )


@app.get("/feedback.jsonl", response_class=PlainTextResponse)
async def feedback_raw() -> PlainTextResponse:
    if FEEDBACK_FILE.exists():
        return PlainTextResponse(FEEDBACK_FILE.read_text(encoding="utf-8"), media_type="application/x-ndjson")
    return PlainTextResponse("", media_type="application/x-ndjson")


# ---- inline templates ----------------------------------------------------
_BRAND_CUBE = (
    '<svg viewBox="0 0 32 32" width="30" height="30" role="img" aria-label="Brisken">'
    '<polygon points="16,3 28,10 16,17 4,10" fill="#5fd3df"/>'
    '<polygon points="4,10 16,17 16,31 4,24" fill="#00b8ce"/>'
    '<polygon points="28,10 16,17 16,31 28,24" fill="#0b6f7a"/></svg>'
)

LOGIN_TEMPLATE = (
    "<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>"
    "<meta name=viewport content='width=device-width, initial-scale=1'>"
    "<title>Brisken OnePilot, access</title>"
    "<style>"
    ":root{--navy:#00396f;--navy-deep:#042a52;--teal:#0e7c86;--teal-strong:#0b626a;"
    "--paper:#f4f7fb;--surface:#fff;--text:#0a1a2f;--muted:#56657c;--border:#c8d5e5;}"
    "*{box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:'IBM Plex Sans',system-ui,-apple-system,Segoe UI,sans-serif;"
    "background:linear-gradient(140deg,#eef3fa,#f4f7fb);color:var(--text);min-height:100vh;"
    "display:flex;align-items:center;justify-content:center;padding:24px}"
    ".card{background:var(--surface);border:1px solid var(--border);border-radius:2px;"
    "box-shadow:0 18px 44px rgba(10,26,47,.12);padding:40px 36px;width:100%;max-width:400px}"
    ".brand{display:flex;align-items:center;gap:10px;margin-bottom:22px}"
    ".brand .wm{font-weight:700;font-size:22px;letter-spacing:-.02em;color:var(--navy)}"
    ".brand .pr{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:10.5px;letter-spacing:.16em;"
    "text-transform:uppercase;color:var(--muted);padding-left:9px;border-left:1px solid var(--border)}"
    "h1{font-size:19px;color:var(--navy);margin-bottom:6px}"
    "p.sub{color:var(--muted);font-size:14px;margin-bottom:22px;line-height:1.5}"
    "label{display:block;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.1em;"
    "text-transform:uppercase;color:var(--muted);margin-bottom:7px}"
    "input{width:100%;font-size:15px;padding:12px 13px;border:1px solid var(--border);border-radius:2px;"
    "background:var(--paper);color:var(--text)}"
    "input:focus{outline:none;border-color:var(--teal);box-shadow:0 0 0 3px rgba(14,124,134,.18)}"
    "button{width:100%;margin-top:16px;background:var(--teal);color:#fff;border:none;border-radius:2px;"
    "padding:13px;font-size:15px;font-weight:600;cursor:pointer}"
    "button:hover{background:var(--teal-strong)}"
    "p.err{background:#fdecea;color:#b3261e;border-radius:2px;padding:9px 12px;font-size:13px;margin-bottom:16px}"
    "p.foot{margin-top:20px;font-size:12px;color:var(--muted);text-align:center}"
    "</style></head><body>"
    "<form class=card method=post action=/login>"
    "<div class=brand>" + _BRAND_CUBE + "<span class=wm>brisken</span><span class=pr>OnePilot</span></div>"
    "<h1>Prototype review access</h1>"
    "<p class=sub>This site is a working prototype shared for review. Enter the access code to continue.</p>"
    "%%ERROR%%"
    "<input type=hidden name=next value='%%NEXT%%'>"
    "<label for=code>Access code</label>"
    "<input id=code name=code type=password autocomplete=current-password autofocus required>"
    "<button type=submit>Enter</button>"
    "<p class=foot>Brisken OnePilot &middot; internal review</p>"
    "</form></body></html>"
)

LOG_TEMPLATE = (
    "<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>"
    "<meta name=viewport content='width=device-width, initial-scale=1'>"
    "<title>Feedback log, Brisken OnePilot</title>"
    "<style>"
    ":root{--navy:#00396f;--teal:#0e7c86;--paper:#f4f7fb;--surface:#fff;--text:#0a1a2f;"
    "--muted:#56657c;--border:#dfe7f1;}"
    "*{box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:'IBM Plex Sans',system-ui,-apple-system,Segoe UI,sans-serif;background:var(--paper);"
    "color:var(--text);padding:32px 24px}"
    ".wrap{max-width:1000px;margin:0 auto}"
    ".head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px;flex-wrap:wrap}"
    ".brand{display:flex;align-items:center;gap:10px}"
    ".brand .wm{font-weight:700;font-size:21px;letter-spacing:-.02em;color:var(--navy)}"
    ".brand .pr{font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.16em;"
    "text-transform:uppercase;color:var(--muted);padding-left:9px;border-left:1px solid var(--border)}"
    "h1{font-size:16px;color:var(--navy);font-weight:600;margin:18px 0 4px}"
    "p.meta{color:var(--muted);font-size:13px;margin-bottom:18px}"
    "p.meta a{color:var(--teal)}"
    "table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);"
    "border-radius:2px;overflow:hidden;font-size:14px}"
    "th{text-align:left;padding:11px 13px;background:#eef3fa;border-bottom:2px solid var(--border);"
    "font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}"
    "td{padding:11px 13px;border-bottom:1px solid var(--border);vertical-align:top}"
    "td.ts{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--muted);white-space:nowrap}"
    "td.comment{line-height:1.5}"
    "span.role{color:var(--muted);font-size:12.5px}"
    "td.empty{text-align:center;color:var(--muted);padding:28px}"
    "</style></head><body><div class=wrap>"
    "<div class=head><div class=brand>" + _BRAND_CUBE + "<span class=wm>brisken</span><span class=pr>OnePilot</span></div>"
    "<a href='/' style='color:var(--teal);font-size:13px;text-decoration:none'>&larr; Back to the prototype</a></div>"
    "<h1>Reviewer feedback</h1>"
    "<p class=meta>%%COUNT%% entr&#105;es &middot; newest first &middot; <a href='/feedback.jsonl'>download JSONL</a></p>"
    "<table><thead><tr><th>When (UTC)</th><th>Where</th><th>Comment</th><th>Who</th></tr></thead>"
    "<tbody>%%ROWS%%</tbody></table>"
    "</div></body></html>"
)
