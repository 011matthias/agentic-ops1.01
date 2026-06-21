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
SITE_PLATFORM_HTML = Path(os.environ.get("BRISKEN_SITE_PLATFORM_HTML", str(APP_DIR / "site" / "brisken-onepilot-platform.html")))
# Which page the root path "/" serves. Default is the TreasuryCentral prototype
# (index.html); set BRISKEN_SITE_ROOT=platform to land "/" on the OnePilot
# platform page (the standalone platform container that becomes onepilot.brisken.com).
SITE_ROOT_HTML = SITE_PLATFORM_HTML if os.environ.get("BRISKEN_SITE_ROOT") == "platform" else SITE_HTML
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


# Real Brisken cube favicon (the brisken.com PNG asset, base64-embedded so the
# app stays self-contained), served so every page (gate, prototype, feedback
# log) shows the real mark in the browser tab, not a drawn approximation.
_FAVICON_PNG = base64.b64decode(
    "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"
)


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(
        _FAVICON_PNG,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


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


def _render_page(html_path: Path, request: Request) -> HTMLResponse:
    """Read a gated page and inject the reviewer name for the feedback popover.

    Expose the reviewer's name to the page so the feedback popover can show
    "leaving feedback as ...". The authoritative name for storage is the
    cookie, read server-side in /feedback. Escape "<" so a crafted name can
    not break out of the <script>.
    """
    reviewer = read_name(request.cookies.get(COOKIE_NAME)) or ""
    try:
        text = html_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse("<h1>Page HTML not found.</h1>", status_code=500)
    inject = "<script>window.__fbReviewer=" + json.dumps(reviewer).replace("<", "\\u003c") + ";</script>"
    return HTMLResponse(text.replace("</head>", inject + "</head>", 1))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return _render_page(SITE_ROOT_HTML, request)


# Both pages are also served by their file name so the absolute cross-links in
# the HTML (TreasuryCentral <-> the OnePilot platform page) resolve on Fly.
@app.get("/brisken-onepilot-website-prototype.html", response_class=HTMLResponse)
async def prototype_page(request: Request) -> HTMLResponse:
    return _render_page(SITE_HTML, request)


@app.get("/brisken-onepilot-platform.html", response_class=HTMLResponse)
async def platform_page(request: Request) -> HTMLResponse:
    return _render_page(SITE_PLATFORM_HTML, request)


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
