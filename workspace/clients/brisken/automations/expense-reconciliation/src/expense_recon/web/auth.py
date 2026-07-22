"""Optional password gate for the hosted web app.

Local (loopback) use needs no auth, so the gate is active ONLY when the
operator code is configured. When it is set (the hosted case), every
request outside the open set requires the signed session token, sent by
the SPA as ``Authorization: Bearer`` (a legacy cookie session is also
accepted). Operator is the only role (owner decision 2026-07-22): an
authenticated session has the full surface.

The submitted code is compared in constant time and never leaves the
server; the token carries only ``{role}:{HMAC(secret, "role:"+role)}``,
never the code itself. When the gate is disabled (no code set, the local
dev case) every request resolves to the operator role.

Env vars:
    EXPENSE_RECON_OPERATOR_CODE   the operator code; gate is on iff set
    EXPENSE_RECON_AUTH_SECRET     HMAC key for the token; set in prod so
                                  sessions survive restarts (falls back to a
                                  per-process random key when unset)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

COOKIE_NAME = "erc_session"

ROLE_OPERATOR = "operator"
ROLES = (ROLE_OPERATOR,)

# Paths reachable without a session: the login handler and the health
# probe. Everything else is gated.
OPEN_PATHS = frozenset({"/api/login", "/healthz"})

# Stable for the life of the process; used only when AUTH_SECRET is unset.
_PROCESS_SECRET = secrets.token_hex(32)


def operator_code() -> str | None:
    code = os.environ.get("EXPENSE_RECON_OPERATOR_CODE", "").strip()
    return code or None


def gate_enabled() -> bool:
    """True when the operator code is configured (i.e. the hosted case)."""
    return operator_code() is not None


def _secret() -> bytes:
    return (os.environ.get("EXPENSE_RECON_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def _role_mac(role: str) -> str:
    return hmac.new(_secret(), b"role:" + role.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_token(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    return f"{role}:{_role_mac(role)}"


def token_role(token: str | None) -> str | None:
    """The role a session token carries, or None for a missing/invalid/
    legacy token (legacy tokens, including old user-role ones, simply
    require one re-login)."""
    if not token or ":" not in token:
        return None
    role, _, mac = token.partition(":")
    if role not in ROLES:
        return None
    if not hmac.compare_digest(mac, _role_mac(role)):
        return None
    return role


def code_role(submitted: str) -> str | None:
    """ROLE_OPERATOR when the submitted code matches, else None.
    Constant-time comparison."""
    op = operator_code()
    if op is not None and hmac.compare_digest(submitted.strip(), op):
        return ROLE_OPERATOR
    return None


def bearer_token(authorization: str | None) -> str | None:
    """The token from an ``Authorization: Bearer <token>`` header, or None.
    The token carried is the same one ``issue_token`` mints."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def path_is_open(path: str) -> bool:
    return path in OPEN_PATHS
