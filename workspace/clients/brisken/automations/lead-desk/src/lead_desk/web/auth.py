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

Env vars:
    LEAD_DESK_ACCESS_CODES    "matthias:code1,dirk:code2,chris:code3"; gate on iff set
    LEAD_DESK_AUTH_SECRET     HMAC key for cookies; set in prod so sessions survive restart
    LEAD_DESK_INGEST_SECRET   bearer secret required on POST /events
    LEAD_DESK_INSECURE_COOKIE set to "1" to drop the cookie Secure flag for local http
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

COOKIE_NAME = "lead_desk_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours

# Reachable without a session cookie: the login flow, the health probe, the
# favicon, and the ingest sink (which guards itself with its own secret).
OPEN_PATHS = frozenset({"/login", "/logout", "/healthz", "/favicon.ico", "/events"})

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


def issue_token(user: str) -> str:
    mac = hmac.new(_secret(), user.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{user}.{mac}"


def read_user(token: str | None) -> str | None:
    """Validate a session cookie and return its user, or None."""
    if not token or "." not in token:
        return None
    user, _, mac = token.partition(".")
    expected = hmac.new(_secret(), user.encode("utf-8"), hashlib.sha256).hexdigest()
    return user if hmac.compare_digest(mac, expected) else None


def cookie_is_secure() -> bool:
    return os.environ.get("LEAD_DESK_INSECURE_COOKIE") != "1"


def path_is_open(path: str) -> bool:
    return path in OPEN_PATHS


def ingest_secret() -> str | None:
    s = os.environ.get("LEAD_DESK_INGEST_SECRET", "").strip()
    return s or None


def ingest_authorized(header_value: str | None) -> bool:
    """Check the bearer secret on ``POST /events``. Closed unless a secret is set."""
    secret = ingest_secret()
    if secret is None or not header_value:
        return False
    token = header_value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return hmac.compare_digest(token, secret)
