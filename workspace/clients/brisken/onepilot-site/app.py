"""Brisken OnePilot prototype: name-gated static host + feedback collector.

Serves the single-file marketing prototype behind a name gate: each reviewer
enters their name before the prototype is shown, and that name is carried in a
signed cookie. Every feedback note is attributed to the cookie's name server
side, so reviewers never retype it. There is no shared password; the gate is
identification, not access control (this is a pre-Dirk internal review). Notes
are appended to a JSONL file on the Fly volume.

The name cookie is `<b64(name)>.<hmac>`: the HMAC (keyed by the auth secret)
makes it tamper-evident, so a forged cookie fails to validate and the visitor
is sent back to the name page.

Env vars:
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

import base64
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

COOKIE_NAME = "brisken_reviewer"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours
OPEN_PATHS = frozenset({"/welcome", "/logout", "/healthz", "/favicon.ico"})
NAME_MAX_LEN = 80
_PROCESS_SECRET = secrets.token_hex(32)


# ---- name-gate helpers ---------------------------------------------------
def _secret() -> bytes:
    return (os.environ.get("BRISKEN_SITE_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def _sig(raw: str) -> str:
    return hmac.new(_secret(), raw.encode("ascii"), hashlib.sha256).hexdigest()[:32]


def sign_name(name: str) -> str:
    """Cookie value `<b64(name)>.<hmac>` carrying the reviewer's name."""
    raw = base64.urlsafe_b64encode(name.encode("utf-8")).decode("ascii")
    return raw + "." + _sig(raw)


def read_name(cookie: "str | None") -> "str | None":
    """Return the reviewer's name from a valid signed cookie, else None."""
    if not cookie or "." not in cookie:
        return None
    raw, sig = cookie.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sig(raw)):
        return None
    try:
        name = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8").strip()
    except Exception:
        return None
    return name or None


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
    if request.url.path not in OPEN_PATHS:
        if read_name(request.cookies.get(COOKIE_NAME)) is None:
            if request.url.path == "/feedback":
                return JSONResponse({"ok": False, "error": "no reviewer name"}, status_code=401)
            return RedirectResponse("/welcome?next=" + request.url.path, status_code=303)
    return await call_next(request)


@app.get("/healthz")
async def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok")


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(status_code=204)


def render_welcome(error: str, nxt: str) -> str:
    err_block = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return (
        WELCOME_TEMPLATE
        .replace("%%ERROR%%", err_block)
        .replace("%%NEXT%%", html.escape(nxt, quote=True))
    )


@app.get("/welcome", response_class=HTMLResponse)
async def welcome_form(request: Request, next: str = "/") -> HTMLResponse:
    if read_name(request.cookies.get(COOKIE_NAME)) is not None:
        return RedirectResponse(safe_next(next), status_code=303)
    return HTMLResponse(render_welcome("", safe_next(next)))


@app.post("/welcome")
async def welcome_submit(request: Request):
    form = await request.form()
    name = str(form.get("name", "")).strip()[:NAME_MAX_LEN]
    nxt = safe_next(str(form.get("next", "/")))
    if not name:
        return HTMLResponse(render_welcome("Please enter your name to continue.", nxt), status_code=400)
    resp = RedirectResponse(nxt, status_code=303)
    resp.set_cookie(
        COOKIE_NAME,
        sign_name(name),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=cookie_is_secure(),
        samesite="lax",
    )
    return resp


@app.get("/logout")
async def logout() -> RedirectResponse:
    resp = RedirectResponse("/welcome", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    reviewer = read_name(request.cookies.get(COOKIE_NAME)) or ""
    try:
        text = SITE_HTML.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse("<h1>Prototype HTML not found.</h1>", status_code=500)
    # Expose the reviewer's name to the page so the feedback popover can show
    # "leaving feedback as ...". The authoritative name for storage is the
    # cookie, read server-side in /feedback. Escape "<" so a crafted name can
    # not break out of the <script>.
    inject = "<script>window.__fbReviewer=" + json.dumps(reviewer).replace("<", "\\u003c") + ";</script>"
    return HTMLResponse(text.replace("</head>", inject + "</head>", 1))


@app.post("/feedback")
async def feedback(request: Request) -> JSONResponse:
    # The reviewer's name is taken from the signed cookie, never the body, so
    # every note is attributed to the name entered at the gate.
    name = read_name(request.cookies.get(COOKIE_NAME))
    if not name:
        return JSONResponse({"ok": False, "error": "no reviewer name"}, status_code=401)
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    comment = str(data.get("comment", "")).strip()
    if not comment:
        return JSONResponse({"ok": False, "error": "comment is required"}, status_code=400)
    # Sanitize the position payload to numeric fields only, so a note can be
    # located exactly later: document/viewport coordinates, scroll, and how far
    # down the page (%) the reviewer clicked.
    raw_pos = data.get("pos")
    pos = {}
    if isinstance(raw_pos, dict):
        for k in ("pageX", "pageY", "clientX", "clientY", "scrollY", "vw", "vh", "docH", "pct"):
            v = raw_pos.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                pos[k] = int(v)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "name": name[:200],
        "section": str(data.get("section", "")).strip()[:200],
        "section_id": str(data.get("sectionId", "")).strip()[:120],
        "selector": str(data.get("selector", "")).strip()[:480],
        "anchor": str(data.get("anchor", "")).strip()[:300],
        "pos": pos or None,
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


def _where_cell(r: dict) -> str:
    """Render the full location of a note: section (deep-linked), the clicked
    text, where on the page (% down + coordinates + viewport), and a CSS
    selector path to the exact element."""
    parts = []
    section = r.get("section", "") or "This page"
    sid = r.get("section_id", "") or ""
    if sid:
        parts.append(f"<a class=where-sec href='/#{html.escape(sid, quote=True)}'>{html.escape(section)}</a>")
    else:
        parts.append(f"<span class=where-sec>{html.escape(section)}</span>")
    anchor = r.get("anchor", "")
    if anchor:
        parts.append(f"<span class=anchor>&#8220;{html.escape(anchor)}&#8221;</span>")
    pos = r.get("pos") or {}
    bits = []
    if isinstance(pos, dict):
        if pos.get("pct") is not None:
            bits.append(f"{int(pos['pct'])}% down")
        if pos.get("pageY") is not None:
            bits.append(f"x={int(pos.get('pageX', 0))} y={int(pos['pageY'])}px")
        if pos.get("vw"):
            bits.append(f"{int(pos['vw'])}&#215;{int(pos.get('vh', 0))} vp")
    if bits:
        parts.append("<span class=pos>" + " &middot; ".join(bits) + "</span>")
    selector = r.get("selector", "")
    if selector:
        parts.append(f"<code class=sel>{html.escape(selector)}</code>")
    return "<br>".join(parts)


@app.get("/feedback-log", response_class=HTMLResponse)
async def feedback_log() -> HTMLResponse:
    rows = _read_feedback()
    rows.reverse()  # newest first
    if rows:
        body = "".join(
            "<tr>"
            f"<td class=ts>{html.escape(r.get('ts',''))}</td>"
            f"<td class=where>{_where_cell(r)}</td>"
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

WELCOME_TEMPLATE = (
    "<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>"
    "<meta name=viewport content='width=device-width, initial-scale=1'>"
    "<title>Brisken OnePilot, prototype review</title>"
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
    "<form class=card method=post action=/welcome>"
    "<div class=brand>" + _BRAND_CUBE + "<span class=wm>brisken</span><span class=pr>OnePilot</span></div>"
    "<h1>Review the OnePilot prototype</h1>"
    "<p class=sub>Enter your name to start. We attach it to any feedback you leave, so the team knows who said what.</p>"
    "%%ERROR%%"
    "<input type=hidden name=next value='%%NEXT%%'>"
    "<label for=name>Your name</label>"
    "<input id=name name=name type=text autocomplete=name maxlength=80 autofocus required placeholder='e.g. Dirk Brisken'>"
    "<button type=submit>Start reviewing</button>"
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
    "td.where{max-width:330px}"
    "a.where-sec{color:var(--navy);font-weight:600;text-decoration:none;border-bottom:1px dotted var(--border)}"
    "a.where-sec:hover{color:var(--teal)}"
    "span.where-sec{font-weight:600;color:var(--navy)}"
    "span.anchor{color:var(--muted);font-size:12.5px}"
    "span.pos{display:inline-block;margin-top:2px;color:var(--muted);font-family:'IBM Plex Mono',monospace;font-size:11px}"
    "code.sel{display:inline-block;margin-top:3px;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--teal);"
    "background:#eef3fa;padding:2px 6px;border-radius:2px;word-break:break-all;line-height:1.4}"
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
