"""Optional password gate for the hosted web app, with two roles.

Local (loopback) use needs no auth, so the gate is active ONLY when an
access code is configured. When it is set (the hosted case), every page
requires a signed session cookie obtained by entering a code at ``/login``.
Two codes exist while the tool is in testing mode:

* ``EXPENSE_RECON_ACCESS_CODE``   the USER code (Chris). Uploads documents
  and reviews published runs; never triggers the pipeline.
* ``EXPENSE_RECON_OPERATOR_CODE`` the OPERATOR code (devs). Full surface:
  intake queue, pipeline runs, publish, memory, compare.

The submitted code is compared in constant time and never leaves the
server; the cookie carries only ``{role}:{HMAC(secret, "role:"+role)}``,
never the code itself. When the gate is disabled (no codes set, the local
dev case) every request resolves to the operator role so local workflows
keep the full surface.

Env vars:
    EXPENSE_RECON_ACCESS_CODE     the user code; gate is on iff a code is set
    EXPENSE_RECON_OPERATOR_CODE   the operator code (must differ from the
                                  user code; operator is checked first)
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
import re
import secrets

COOKIE_NAME = "erc_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours

ROLE_USER = "user"
ROLE_OPERATOR = "operator"
ROLES = (ROLE_USER, ROLE_OPERATOR)

# Paths reachable without a session: the login form/handler, the health
# probe, the favicon, and the packaged static assets (brand CSS/logos the
# login page itself needs; no client data lives there). Everything else is
# gated.
OPEN_PATHS = frozenset({"/login", "/logout", "/api/login", "/healthz", "/favicon.ico"})
OPEN_PREFIXES = ("/static/",)

# Operator-only surface (testing mode): the pipeline trigger, job polling,
# the intake run flow, publish, memory teaching, compare, the state
# API the dev-side notifier polls, and the reviewer-feedback log (leaving
# feedback via POST /feedback is open to every logged-in role; reading it
# is not). `None` methods = every method. The published-run visibility
# check for users is per-run (needs the DB row) and lives in the route
# handlers, not here.
_OPERATOR_RULES: tuple[tuple[re.Pattern, frozenset | None], ...] = (
    (re.compile(r"^/runs$"), frozenset({"POST"})),
    (re.compile(r"^/api/runs$"), frozenset({"POST"})),  # SPA run kickoff
    (re.compile(r"^/jobs/"), None),
    (re.compile(r"^/compare$"), None),
    (re.compile(r"^/api/compare$"), None),  # SPA compare (operator-only)
    (re.compile(r"^/memory($|/)"), None),
    (re.compile(r"^/api/memory($|/)"), None),  # SPA memory (operator-only)
    (re.compile(r"^/intakes/[^/]+($|/)"), None),  # POST /intakes itself is for users
    (re.compile(r"^/runs/[^/]+/(publish|unpublish|commit-memory|forget)$"), None),
    (re.compile(r"^/api/operator($|/)"), None),
    (re.compile(r"^/api/settings$"), frozenset({"PUT"})),  # §16 policy write
    (re.compile(r"^/feedback-log$"), None),
    (re.compile(r"^/feedback\.jsonl$"), None),
)

# Stable for the life of the process; used only when AUTH_SECRET is unset.
_PROCESS_SECRET = secrets.token_hex(32)


def access_code() -> str | None:
    code = os.environ.get("EXPENSE_RECON_ACCESS_CODE", "").strip()
    return code or None


def operator_code() -> str | None:
    code = os.environ.get("EXPENSE_RECON_OPERATOR_CODE", "").strip()
    return code or None


def gate_enabled() -> bool:
    """True when any access code is configured (i.e. the hosted case)."""
    return access_code() is not None or operator_code() is not None


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
    legacy token (legacy tokens simply require one re-login)."""
    if not token or ":" not in token:
        return None
    role, _, mac = token.partition(":")
    if role not in ROLES:
        return None
    if not hmac.compare_digest(mac, _role_mac(role)):
        return None
    return role


def token_valid(token: str | None) -> bool:
    return token_role(token) is not None


def code_role(submitted: str) -> str | None:
    """The role a submitted code grants, or None. The operator code wins
    when both are set to the same value (they should differ; deploy sets
    two distinct secrets). Both comparisons run constant-time."""
    sub = submitted.strip()
    op = operator_code()
    usr = access_code()
    if op is not None and hmac.compare_digest(sub, op):
        return ROLE_OPERATOR
    if usr is not None and hmac.compare_digest(sub, usr):
        return ROLE_USER
    return None


def code_matches(submitted: str) -> bool:
    """Back-compat boolean check (any valid code)."""
    return code_role(submitted) is not None


def cookie_is_secure() -> bool:
    return os.environ.get("EXPENSE_RECON_INSECURE_COOKIE") != "1"


def bearer_token(authorization: str | None) -> str | None:
    """The token from an ``Authorization: Bearer <token>`` header, or None.
    Lets the SPA front end authenticate cross-origin (no cookie) while the
    server-rendered pages keep using the session cookie. The token carried
    is the same one ``issue_token`` mints."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def path_is_open(path: str) -> bool:
    return path in OPEN_PATHS or path.startswith(OPEN_PREFIXES)


def path_requires_operator(path: str, method: str) -> bool:
    """True when this path+method is operator-only.

    Every rule is matched against BOTH the raw path and the same path with
    a leading ``/api`` removed, because most mutations are mounted twice:
    once bare for the server-rendered pages and once under ``/api`` for the
    SPA. The rules are ``^``-anchored, so without the second match a twin
    would silently escape its rule; ``^/runs/[^/]+/publish$`` does not match
    ``/api/runs/x/publish``, and the user role could publish through the
    SPA surface. Checking the canonical form means a new twin inherits its
    rule automatically instead of needing a duplicate regex nobody
    remembers to add.

    Union, not replacement: the explicitly ``/api``-prefixed rules (e.g.
    ``^/api/operator($|/)``, whose bare form has no rule) keep matching.
    """
    candidates = [path]
    if path.startswith("/api/"):
        candidates.append(path[len("/api"):])
    for pattern, methods in _OPERATOR_RULES:
        if methods is not None and method.upper() not in methods:
            continue
        if any(pattern.match(candidate) for candidate in candidates):
            return True
    return False
