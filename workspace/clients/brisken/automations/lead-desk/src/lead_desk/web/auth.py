"""Server-side access gate for the hosted Lead Desk.

Local (loopback) use needs no auth, so the gate is active ONLY when access
codes are configured via ``LEAD_DESK_ACCESS_CODES``. When set (the hosted
case), every page requires a signed session cookie obtained by entering a code
at ``/login``. Codes are compared in constant time and never leave the server;
the cookie carries only ``<user>.<hmac(user)>``, never the code. Each user gets
their own code so every logged event is attributed to a real person.

The event-ingest endpoint (``POST /events``) sits outside the cookie gate but
carries its own shared-secret check (``LEAD_DESK_INGEST_SECRET``) so the cloud
capture worker can post events without a browser session.

The outbox/worker API (``/api/outbox/*``, ``/api/worker/*``) also sits outside
the cookie gate with its own bearer (``LEAD_DESK_WORKER_SECRET``) - separate
from the ingest secret because claim responses carry lead PII and mutate queue
state, so the two rotate independently.

Env vars:
    LEAD_DESK_ACCESS_CODES    "matthias:code1,dirk:code2,chris:code3"; gate on iff set
    LEAD_DESK_AUTH_SECRET     HMAC key for cookies; set in prod so sessions survive restart
    LEAD_DESK_INGEST_SECRET   bearer secret required on POST /events
    LEAD_DESK_WORKER_SECRET   bearer secret for the local send worker's outbox API
    LEAD_DESK_INSECURE_COOKIE set to "1" to drop the cookie Secure flag for local http
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

COOKIE_NAME = "lead_desk_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours

# /login brute-force throttle: block after this many fails within the window.
LOGIN_MAX_FAILS = 8
LOGIN_WINDOW = 300  # seconds

# Reachable without a session cookie: the login flow, the health probe, the
# favicon, the ingest sink, and the worker outbox API (each API guards itself
# with its own secret).
OPEN_PATHS = frozenset({
    "/login", "/logout", "/healthz", "/favicon.ico", "/events",
    # /sync self-guards: its handler checks cookie OR ingest bearer. Without
    # this the cookie gate rejected the documented external-cron ingest path.
    "/sync",
    "/api/outbox/claim", "/api/outbox/result", "/api/outbox/draft-sent",
    "/api/worker/status", "/api/worker/watchlist", "/api/worker/heartbeat",
})

# Stable for the life of the process; used only when AUTH_SECRET is unset.
_PROCESS_SECRET = secrets.token_hex(32)


def _codes() -> dict[str, str]:
    """Parse ``LEAD_DESK_ACCESS_CODES`` into {user: code}. Empty => gate off."""
    raw = os.environ.get("LEAD_DESK_ACCESS_CODES", "").strip()
    out: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        user, code = pair.split(":", 1)
        user, code = user.strip().lower(), code.strip()
        if user and code:
            out[user] = code
    return out


def gate_enabled() -> bool:
    """True when at least one access code is configured (the hosted case)."""
    return bool(_codes())


def _secret() -> bytes:
    return (os.environ.get("LEAD_DESK_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def resolve_user(submitted: str) -> str | None:
    """Return the user whose code matches (constant time), else None.

    Compares against every configured code without early return so timing does
    not reveal which user (if any) matched.
    """
    submitted = (submitted or "").strip()
    match: str | None = None
    for user, code in _codes().items():
        if hmac.compare_digest(submitted, code):
            match = user
    return match


def issue_token(user: str, now: float | None = None) -> str:
    """Signed cookie binding user + issued-at + a random nonce, so a token is
    unique per login and expires server-side (see read_user)."""
    iat = int(now if now is not None else time.time())
    payload = f"{user}|{iat}|{secrets.token_hex(8)}"
    b = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    mac = hmac.new(_secret(), b.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{b}.{mac}"


def read_user(token: str | None, now: float | None = None) -> str | None:
    """Validate a session cookie and return its user, or None. Enforces the
    12h window server-side. Old-format (user.mac) tokens no longer parse, so
    they are rejected -> a one-time forced re-login after this ships."""
    if not token or "." not in token:
        return None
    b, _, mac = token.rpartition(".")
    expected = hmac.new(_secret(), b.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return None
    try:
        payload = base64.urlsafe_b64decode(b.encode("ascii")).decode("utf-8")
        user, iat_s, _nonce = payload.split("|", 2)
        iat = int(iat_s)
    except Exception:  # noqa: BLE001 - any malformed/old-format token -> re-login
        return None
    if (now if now is not None else time.time()) - iat > SESSION_MAX_AGE:
        return None
    return user or None


# -- CSRF (double-submit token bound to the session) --------------------------

def csrf_token(user: str) -> str:
    return hmac.new(_secret(), (user + "|csrf").encode("utf-8"), hashlib.sha256).hexdigest()


def csrf_for_cookie(token: str | None) -> str:
    """The CSRF token to embed in forms for the current session ('' if none)."""
    user = read_user(token)
    return csrf_token(user) if user else ""


def csrf_valid(cookie_token: str | None, submitted: str | None) -> bool:
    user = read_user(cookie_token)
    if not user or not submitted:
        return False
    return hmac.compare_digest(submitted, csrf_token(user))


# -- /login brute-force throttle (in-process, per client IP) ------------------

_LOGIN_FAILS: dict[str, list[float]] = {}


def _prune(ip: str, now: float) -> list[float]:
    fails = [t for t in _LOGIN_FAILS.get(ip, []) if now - t < LOGIN_WINDOW]
    _LOGIN_FAILS[ip] = fails
    return fails


def login_blocked(ip: str, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    return len(_prune(ip, now)) >= LOGIN_MAX_FAILS


def record_login_fail(ip: str, now: float | None = None) -> None:
    now = now if now is not None else time.time()
    _prune(ip, now).append(now)


def record_login_success(ip: str) -> None:
    _LOGIN_FAILS.pop(ip, None)


def cookie_is_secure() -> bool:
    return os.environ.get("LEAD_DESK_INSECURE_COOKIE") != "1"


def path_is_open(path: str) -> bool:
    return path in OPEN_PATHS


def ingest_secret() -> str | None:
    s = os.environ.get("LEAD_DESK_INGEST_SECRET", "").strip()
    return s or None


def _bearer_matches(header_value: str | None, secret: str | None) -> bool:
    if secret is None or not header_value:
        return False
    token = header_value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return hmac.compare_digest(token, secret)


def ingest_authorized(header_value: str | None) -> bool:
    """Check the bearer secret on ``POST /events``. Closed unless a secret is set."""
    return _bearer_matches(header_value, ingest_secret())


def worker_secret() -> str | None:
    s = os.environ.get("LEAD_DESK_WORKER_SECRET", "").strip()
    return s or None


def worker_authorized(header_value: str | None) -> bool:
    """Check the bearer on the outbox/worker API. Closed unless a secret is set."""
    return _bearer_matches(header_value, worker_secret())
