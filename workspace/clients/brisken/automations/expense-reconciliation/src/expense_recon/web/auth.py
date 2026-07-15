"""Optional password gate for the hosted web app.

Local (loopback) use needs no auth, so the gate is active ONLY when an
access code is configured via ``EXPENSE_RECON_ACCESS_CODE``. When it is set
(the hosted case), every page requires a signed session cookie obtained by
entering the code at ``/login``. The submitted code is compared in constant
time and never leaves the server; the cookie carries only an HMAC of a
fixed marker, never the code itself.

Env vars:
    EXPENSE_RECON_ACCESS_CODE     the shared password; gate is on iff set
    EXPENSE_RECON_AUTH_SECRET     HMAC key for the cookie; set in prod so
                                  sessions survive restarts (falls back to a
                                  per-process random key when unset)
    EXPENSE_RECON_INSECURE_COOKIE set to "1" to drop the cookie Secure flag
                                  for local http testing (never in prod)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

COOKIE_NAME = "erc_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours

# Paths reachable without a session: the login form/handler, the health
# probe, the favicon, and the packaged static assets (brand CSS/logos the
# login page itself needs; no client data lives there). Everything else is
# gated.
OPEN_PATHS = frozenset({"/login", "/logout", "/healthz", "/favicon.ico"})
OPEN_PREFIXES = ("/static/",)

# Stable for the life of the process; used only when AUTH_SECRET is unset.
_PROCESS_SECRET = secrets.token_hex(32)


def access_code() -> str | None:
    code = os.environ.get("EXPENSE_RECON_ACCESS_CODE", "").strip()
    return code or None


def gate_enabled() -> bool:
    """True when an access code is configured (i.e. the hosted case)."""
    return access_code() is not None


def _secret() -> bytes:
    return (os.environ.get("EXPENSE_RECON_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def issue_token() -> str:
    return hmac.new(_secret(), b"authenticated", hashlib.sha256).hexdigest()


def token_valid(token: str | None) -> bool:
    if not token:
        return False
    return hmac.compare_digest(token, issue_token())


def code_matches(submitted: str) -> bool:
    code = access_code()
    if code is None:
        return False
    return hmac.compare_digest(submitted.strip(), code)


def cookie_is_secure() -> bool:
    return os.environ.get("EXPENSE_RECON_INSECURE_COOKIE") != "1"


def path_is_open(path: str) -> bool:
    return path in OPEN_PATHS or path.startswith(OPEN_PREFIXES)
