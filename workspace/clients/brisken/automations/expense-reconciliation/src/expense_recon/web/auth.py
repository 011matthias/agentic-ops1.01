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

All configured codes grant the same operator role; what a NAMED code adds
is attribution and per-person revocability (remove one person's code
without rotating everyone else's). The label rides inside the signed
token as ``operator.<label>:<mac>``.

Env vars:
    EXPENSE_RECON_OPERATOR_CODE    legacy single shared code (label
                                   "operator"); still honored
    EXPENSE_RECON_OPERATOR_CODES   comma-separated ``code:label`` pairs
                                   (labels lowercase [a-z0-9_-]); codes
                                   must not contain ':' or ','
    EXPENSE_RECON_AUTH_SECRET      HMAC key for the token; set in prod so
                                   sessions survive restarts (falls back to
                                   a per-process random key when unset)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

COOKIE_NAME = "erc_session"

ROLE_OPERATOR = "operator"
ROLES = (ROLE_OPERATOR,)
DEFAULT_LABEL = "operator"
_LABEL_RE = re.compile(r"^[a-z0-9_-]{1,32}$")

# Paths reachable without a session: the login handler and the health
# probe. Everything else is gated.
OPEN_PATHS = frozenset({"/api/login", "/healthz"})

# Stable for the life of the process; used only when AUTH_SECRET is unset.
_PROCESS_SECRET = secrets.token_hex(32)


def operator_code() -> str | None:
    code = os.environ.get("EXPENSE_RECON_OPERATOR_CODE", "").strip()
    return code or None


def operator_codes() -> dict[str, str]:
    """label -> code, from EXPENSE_RECON_OPERATOR_CODES plus the legacy
    single code (label "operator"). Malformed pairs are skipped rather
    than bricking the login."""
    out: dict[str, str] = {}
    raw = os.environ.get("EXPENSE_RECON_OPERATOR_CODES", "")
    for pair in raw.split(","):
        code, _, label = pair.strip().partition(":")
        code, label = code.strip(), label.strip().lower()
        if code and _LABEL_RE.match(label):
            out[label] = code
    legacy = operator_code()
    if legacy and DEFAULT_LABEL not in out:
        out[DEFAULT_LABEL] = legacy
    return out


def gate_enabled() -> bool:
    """True when at least one code is configured (i.e. the hosted case)."""
    return bool(operator_codes())


def _secret() -> bytes:
    return (os.environ.get("EXPENSE_RECON_AUTH_SECRET") or _PROCESS_SECRET).encode("utf-8")


def _role_mac(role: str, label: str) -> str:
    payload = f"role:{role}:{label}".encode("utf-8")
    return hmac.new(_secret(), payload, hashlib.sha256).hexdigest()


def issue_token(role: str, label: str = DEFAULT_LABEL) -> str:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    if not _LABEL_RE.match(label):
        label = DEFAULT_LABEL
    return f"{role}.{label}:{_role_mac(role, label)}"


def _parse_token(token: str | None) -> tuple[str, str] | None:
    """(role, label) for a valid token, else None. Pre-label tokens fail
    the mac and simply require one re-login."""
    if not token or ":" not in token:
        return None
    head, _, mac = token.partition(":")
    role, _, label = head.partition(".")
    label = label or DEFAULT_LABEL
    if role not in ROLES or not _LABEL_RE.match(label):
        return None
    if not hmac.compare_digest(mac, _role_mac(role, label)):
        return None
    return role, label


def token_role(token: str | None) -> str | None:
    parsed = _parse_token(token)
    return parsed[0] if parsed else None


def token_label(token: str | None) -> str | None:
    """The operator label a session token carries (who logged in)."""
    parsed = _parse_token(token)
    return parsed[1] if parsed else None


def code_identity(submitted: str) -> str | None:
    """The label of the matching configured code, else None. Every
    configured code is compared (constant-time each) so timing does not
    reveal which code family matched."""
    submitted = submitted.strip()
    matched: str | None = None
    for label, code in operator_codes().items():
        if hmac.compare_digest(submitted, code):
            matched = label
    return matched


def code_role(submitted: str) -> str | None:
    """ROLE_OPERATOR when the submitted code matches any configured code,
    else None. Kept for callers that only need the role."""
    return ROLE_OPERATOR if code_identity(submitted) is not None else None


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
