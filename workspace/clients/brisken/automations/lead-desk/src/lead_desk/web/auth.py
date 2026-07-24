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
import re
import secrets
import time

COOKIE_NAME = "lead_desk_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours

# /login brute-force throttle: block after this many fails within the window.
LOGIN_MAX_FAILS = 8
LOGIN_WINDOW = 300  # seconds

# Magic-link (passwordless) login. A raw url-safe token (256 bits) is emailed;
# only its sha256 is stored (store.login_tokens), and each is single-use with a
# short TTL so a leaked or intercepted link has a small, one-shot window.
MAGIC_TOKEN_TTL = 15 * 60  # seconds

# Deliberately permissive shape check (not full RFC 5322): reject the obviously
# malformed before we ever create a pending row or a token. No length blow-ups.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str | None) -> str:
    return (raw or "").strip().lower()


def valid_email(raw: str | None) -> bool:
    e = normalize_email(raw)
    return bool(e) and len(e) <= 254 and _EMAIL_RE.match(e) is not None


# Seeded approved admins - the two known operators (also the hard mail
# allowlist in graph_mail). New DBs seed these via the v6 migration so an
# admin-approval gate is never left with zero approvers. Overridable at deploy
# time via LEAD_DESK_ADMIN_EMAILS (comma-separated) for future operators.
_DEFAULT_ADMIN_EMAILS = ("matthias.silva@brisken.com", "dirk.neumann@brisken.com")


def _env_admin_emails() -> tuple[str, ...]:
    raw = os.environ.get("LEAD_DESK_ADMIN_EMAILS", "").strip()
    extra = tuple(normalize_email(e) for e in raw.split(",") if normalize_email(e))
    # Dedupe, preserve order, defaults first.
    seen: dict[str, None] = {}
    for e in _DEFAULT_ADMIN_EMAILS + extra:
        seen.setdefault(e, None)
    return tuple(seen)


# Concrete tuple the store migration seeds from (evaluated at import).
SEED_ADMIN_EMAILS = _env_admin_emails()


def is_seed_admin(email: str | None) -> bool:
    return normalize_email(email) in SEED_ADMIN_EMAILS


# -- magic-link tokens --------------------------------------------------------

def new_magic_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token goes in the emailed link;
    only the hash is persisted, so a DB read never yields a usable link."""
    raw = secrets.token_urlsafe(32)  # 256 bits of entropy
    return raw, hash_magic_token(raw)


def hash_magic_token(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()

# Reachable without a session cookie: the login flow, the health probe, the
# favicon, the ingest sink, and the worker outbox API (each API guards itself
# with its own secret).
OPEN_PATHS = frozenset({
    "/login", "/logout", "/healthz", "/favicon.ico", "/events",
    # Passwordless login: the email-a-link submit and the link-verify landing
    # are reached BEFORE a session exists, so they sit outside the cookie gate
    # (each self-throttles / validates a single-use token). /admin/* stays
    # gated + admin-only, so it is intentionally NOT here.
    "/login/magic", "/auth/verify",
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


# -- magic-link request throttle (separate from the code-login fail counter so
#    legit link requests never lock out the access-code break-glass) ----------

MAGIC_MAX_REQS = 5
MAGIC_WINDOW = 300  # seconds
_MAGIC_REQS: dict[str, list[float]] = {}


def magic_blocked(ip: str, now: float | None = None) -> bool:
    now = now if now is not None else time.time()
    fresh = [t for t in _MAGIC_REQS.get(ip, []) if now - t < MAGIC_WINDOW]
    _MAGIC_REQS[ip] = fresh
    return len(fresh) >= MAGIC_MAX_REQS


def record_magic_request(ip: str, now: float | None = None) -> None:
    now = now if now is not None else time.time()
    _MAGIC_REQS.setdefault(ip, []).append(now)


def cookie_is_secure() -> bool:
    return os.environ.get("LEAD_DESK_INSECURE_COOKIE") != "1"


def path_is_open(path: str) -> bool:
    # /static/* serves packaged brand assets (tokens, logos, favicon) so the
    # login page can style itself pre-auth; nothing under it is client data.
    return path in OPEN_PATHS or path.startswith("/static/")


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
