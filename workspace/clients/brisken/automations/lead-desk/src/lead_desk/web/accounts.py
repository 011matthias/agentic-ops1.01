"""Passwordless (magic-link) login + admin-approval account flow.

The browser gate in ``auth.py`` stays the crypto/session primitive; this module
is the policy layer on top of it and the ``users`` / ``login_tokens`` store:

* ``request_magic_link`` - an email is submitted at /login. An APPROVED user
  gets a single-use link mailed to them; an unknown email becomes a PENDING
  access request (admins notified); pending/disabled get a plain message. No
  branch ever reveals a password, and a token is created ONLY when there is a
  live mailer to deliver it (no orphan links).
* ``verify_and_login`` - the link lands at /auth/verify; the token is redeemed
  single-use and the session is issued. Fails closed if approval was revoked
  between issue and click.
* ``approve_user`` / ``is_admin`` - the admin-approval half.

Email goes out via the existing app-only Graph sender (``graph_mail.GraphMailer``,
matthias.silva only). It is INERT until ``LEAD_DESK_AUTH_EMAILS=1`` AND the
Graph creds are present, so the very first live auth-email is a deliberate,
owner-gated flip - not a side effect of deploying this code. Access-code login
(``auth.resolve_user``) remains as an admin break-glass so no one is locked out
while auth-email is still off.

Mailer is dependency-injected (``mailer=`` param) so tests never touch Graph.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from . import auth

_UNSET = object()

# Legacy access-code identities (short names, no '@') that are admins by
# break-glass: the two known operators. A code login as anyone else is a member.
_LEGACY_ADMIN_NAMES = ("matthias", "dirk")


# -- mailer resolution --------------------------------------------------------

def auth_emails_enabled() -> bool:
    """The deliberate on-switch for live auth email. Off by default so a deploy
    of this code sends nothing until an owner flips it (and runs the drill)."""
    return os.environ.get("LEAD_DESK_AUTH_EMAILS") == "1"


def _resolve_mailer():
    """The live Graph mailer, or None when auth-email is off / creds absent /
    unavailable. None => the flow still records state but sends nothing."""
    if not auth_emails_enabled():
        return None
    try:
        from ..sync import have_creds
        if not have_creds():
            return None
        from ..graph_mail import GraphMailer
        return GraphMailer()
    except Exception:  # noqa: BLE001 - a mail-path failure must never 500 login
        return None


def base_url_from(request) -> str:
    """Origin used to build the emailed link. Prefer the pinned env so the link
    never trusts a spoofable Host header; fall back to the request origin
    (honoring the Fly proxy's x-forwarded-proto so the link is https)."""
    env = os.environ.get("LEAD_DESK_BASE_URL", "").strip().rstrip("/")
    if env:
        return env
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


# -- email bodies -------------------------------------------------------------

def _send(mailer, to: str, subject: str, body: str) -> bool:
    if mailer is None:
        return False
    try:
        mailer.send_auto({"to": to, "subject": subject, "body": body})
        return True
    except Exception:  # noqa: BLE001 - delivery failure is surfaced, not raised
        return False


def _send_login_email(mailer, to: str, link: str) -> bool:
    body = (
        "Hi,\n\n"
        "Here is your one-time sign-in link for the Brisken Lead Desk:\n\n"
        f"{link}\n\n"
        "The link works once and expires in 15 minutes. If you did not ask to "
        "sign in, you can ignore this email.\n\n"
        "Lead Desk"
    )
    return _send(mailer, to, "Sign in to Lead Desk", body)


def _notify_admins(store, requester: str, base_url: str, mailer) -> None:
    if mailer is None:
        return
    body = (
        f"{requester} requested access to the Lead Desk.\n\n"
        f"Approve or decline here:\n{base_url}/admin/users\n\n"
        "Lead Desk"
    )
    for u in store.list_users():
        if u["role"] == "admin" and u["status"] == "approved":
            _send(mailer, u["email"], "Lead Desk: new access request", body)


def _send_approval_email(mailer, to: str, base_url: str) -> bool:
    body = (
        "Hi,\n\n"
        "Your access to the Brisken Lead Desk has been approved. To sign in, "
        f"open {base_url}/login and enter this email address; we'll send you a "
        "one-time link.\n\n"
        "Lead Desk"
    )
    return _send(mailer, to, "Lead Desk access approved", body)


# -- login-token TTL ----------------------------------------------------------

def _expiry(now_str: str, ttl: int = auth.MAGIC_TOKEN_TTL) -> str:
    """now (an ISO ``+00:00`` string from now_iso) + ttl, same format so the
    store's lexicographic expiry comparison holds."""
    return (datetime.fromisoformat(now_str) + timedelta(seconds=ttl)) \
        .isoformat(timespec="seconds")


# -- the flow -----------------------------------------------------------------

def request_magic_link(store, email: str, *, base_url: str, ip: str | None,
                       now: str, mailer=_UNSET) -> dict:
    """Handle an email submitted at /login. Returns a status dict; the route
    maps status -> a user-facing banner. ``link`` is present only on 'sent' and
    is for tests / server-side use, never rendered to the browser."""
    if mailer is _UNSET:
        mailer = _resolve_mailer()
    email = auth.normalize_email(email)
    if not auth.valid_email(email):
        return {"status": "invalid"}

    user = store.get_user(email)
    if user is None:
        # First time we've seen this address: record an access request and ping
        # the admins. Never issue a link to an unapproved address.
        store.create_pending_user(email, "", now)
        _notify_admins(store, email, base_url, mailer)
        return {"status": "pending_new"}

    status = user["status"]
    if status == "approved":
        if mailer is None:
            # Approved but auth-email is off / creds absent: don't mint an
            # orphan token. Admins fall back to the access code.
            return {"status": "no_mailer"}
        raw, token_hash = auth.new_magic_token()
        store.create_login_token(token_hash, email, now, _expiry(now), ip)
        link = f"{base_url}/auth/verify?token={raw}"
        if not _send_login_email(mailer, email, link):
            return {"status": "send_failed"}
        return {"status": "sent", "link": link}
    if status == "pending":
        return {"status": "pending"}
    return {"status": "disabled"}


def verify_and_login(store, raw_token: str, now: str) -> str | None:
    """Redeem a magic-link token (single-use) and return the email to seat in
    the session, or None. Re-checks approval so a token cannot outlive a
    revocation."""
    if not raw_token:
        return None
    email = store.consume_login_token(auth.hash_magic_token(raw_token), now)
    if email is None:
        return None
    user = store.get_user(email)
    if user is None or user["status"] != "approved":
        return None
    store.touch_user_login(email, now)
    return email


# -- admin half ---------------------------------------------------------------

def is_admin(store, identity: str | None) -> bool:
    """True when the session identity may use the admin surface. Email
    identities resolve against the users table; legacy short-name access-code
    identities map the two known operators to admin; the ungated-local 'local'
    identity is trusted (the gate is off there anyway)."""
    ident = auth.normalize_email(identity)
    if not ident or ident == "local":
        return True
    if "@" in ident:
        u = store.get_user(ident)
        return bool(u and u["role"] == "admin" and u["status"] == "approved")
    return ident in _LEGACY_ADMIN_NAMES


def approve_user(store, email: str, *, by: str, now: str, base_url: str,
                 mailer=_UNSET) -> None:
    if mailer is _UNSET:
        mailer = _resolve_mailer()
    email = auth.normalize_email(email)
    store.set_user_status(email, "approved", by, now)
    _send_approval_email(mailer, email, base_url)


def invite_user(store, email: str, *, name: str, role: str, by: str, now: str,
                base_url: str, mailer=_UNSET) -> dict:
    """Admin proactively adds + approves a user (Dirk onboards a colleague
    directly). Approved on creation, so they can request a link at once."""
    if mailer is _UNSET:
        mailer = _resolve_mailer()
    email = auth.normalize_email(email)
    if not auth.valid_email(email):
        return {"status": "invalid"}
    store.upsert_user(email, name, role, "approved", by, now)
    _send_approval_email(mailer, email, base_url)
    return {"status": "ok"}
