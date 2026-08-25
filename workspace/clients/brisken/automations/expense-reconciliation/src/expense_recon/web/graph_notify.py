"""Guarded Microsoft Graph sender for intake notifications.

Two message kinds, both INTERNAL-ONLY: acceptance acks to the Brisken
person who mailed a receipt in, and held-mail alerts to the operator.
Send discipline follows the Brisken send-by-id standard: every call is a
per-recipient ``sendMail`` whose recipient is explicitly enumerated and
asserted against hard guards before the request fires. Deny-by-default:
any failed guard or transport error means "no send", never an exception
into the ingest path (callers treat False as "notification skipped").

Guards, all asserted per call:
  - creds present (Fly secrets BRISKEN_TENANT_ID / _GRAPH_CLIENT_ID /
    _GRAPH_CLIENT_SECRET); absent => disabled, silently
  - the sending mailbox is in the sanctioned set (matthias.silva)
  - the recipient is EXACTLY ONE well-formed address, and either inside
    @brisken.com or on the caller's explicit ``allow_external`` list (the
    operator-curated ``intake.known_senders``). Alerts never pass a list,
    so they never leave the tenant; an ack does, for the few private
    addresses our own people mail their receipts from
  - an in-process daily cap (resets per UTC day and per boot; the intake
    day budget already caps how many acks CAN be triggered)

Loop safety: outbound mail carries ``X-Auto-Response-Suppress: All``
(honored inside the Exchange org, which is the only place these go), and
the ack caller additionally refuses to ack inbound mail that is itself
auto-generated (Auto-Submitted / Precedence / no-reply senders).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

log = logging.getLogger("expense_recon.intake.notify")

GRAPH = "https://graph.microsoft.com/v1.0"
SEND_MAILBOX = "matthias.silva@brisken.com"
# The client-wide sanctioned mailboxes; a code change is required to send
# as anyone else, mirroring the hard allowlist in the Graph-first rule.
SANCTIONED_MAILBOXES = frozenset(
    {"dirk.neumann@brisken.com", "matthias.silva@brisken.com"}
)
RECIPIENT_SUFFIX = "@brisken.com"
DAILY_SEND_CAP = 50

_lock = threading.Lock()
_token: str | None = None
_token_expires = 0.0
_sent_day = ""
_sent_count = 0


def enabled() -> bool:
    return all(
        os.environ.get(k)
        for k in (
            "BRISKEN_TENANT_ID",
            "BRISKEN_GRAPH_CLIENT_ID",
            "BRISKEN_GRAPH_CLIENT_SECRET",
        )
    )


def _get_token() -> str | None:
    """App-only client-credentials token, cached until ~5 min before
    expiry. Returns None on any failure (caller skips the send)."""
    global _token, _token_expires
    with _lock:
        if _token and time.time() < _token_expires - 300:
            return _token
    tenant = os.environ.get("BRISKEN_TENANT_ID", "")
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": os.environ.get("BRISKEN_GRAPH_CLIENT_ID", ""),
        "client_secret": os.environ.get("BRISKEN_GRAPH_CLIENT_SECRET", ""),
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=body, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.warning("graph token mint failed: %s", exc)
        return None
    tok = data.get("access_token")
    if not tok:
        return None
    with _lock:
        _token = tok
        _token_expires = time.time() + float(data.get("expires_in", 3600))
    return tok


def _cap_exhausted() -> bool:
    global _sent_day, _sent_count
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _lock:
        if _sent_day != today:
            _sent_day, _sent_count = today, 0
        if _sent_count >= DAILY_SEND_CAP:
            return True
        _sent_count += 1
        return False


def send_mail(
    recipient: str, subject: str, body: str,
    *, allow_external: tuple[str, ...] | frozenset[str] = (),
) -> bool:
    """One guarded notification. True only when Graph accepted the send;
    every refused guard and transport error returns False.

    ``allow_external`` is an EXPLICIT enumeration of outside addresses THIS
    call may reach: the operator-curated ``intake.known_senders``, nothing
    else. It widens the recipient rule by exactly those addresses and
    relaxes none of the structural checks, so a stranger who mails us —
    or forges a From we have never heard of — still gets nothing back.
    That is the send-by-id standard applied to an automated reply: we mail
    an address a human listed on purpose, never one that merely turned up
    in a header."""
    if not enabled():
        return False
    recipient = (recipient or "").strip().lower()
    # Structural guard, asserted for every recipient before the allowlist
    # is consulted: exactly one address, with nothing in it that could
    # smuggle a second one past the single-recipient rule.
    if (
        recipient.count("@") != 1
        or any(c in recipient for c in " \t,;<>\r\n")
        or recipient.startswith("@")
        or recipient.endswith("@")
    ):
        log.warning("notify refused: recipient %r malformed", recipient)
        return False
    listed = recipient in {
        str(a).strip().lower() for a in (allow_external or ())
    }
    if not (recipient.endswith(RECIPIENT_SUFFIX) or listed):
        log.warning(
            "notify refused: recipient %r is neither internal nor listed",
            recipient,
        )
        return False
    if SEND_MAILBOX not in SANCTIONED_MAILBOXES:
        log.error("notify refused: send mailbox not sanctioned")
        return False
    if _cap_exhausted():
        log.warning("notify refused: daily send cap reached")
        return False
    token = _get_token()
    if not token:
        return False
    payload = {
        "message": {
            "subject": subject[:200],
            "body": {"contentType": "Text", "content": body[:4000]},
            "toRecipients": [{"emailAddress": {"address": recipient}}],
            "internetMessageHeaders": [
                # Graph custom headers must be X-*; this one is honored
                # org-internally by Exchange and stops OOF/auto-replies.
                {"name": "X-Auto-Response-Suppress", "value": "All"},
            ],
        },
        "saveToSentItems": True,
    }
    req = urllib.request.Request(
        f"{GRAPH}/users/{SEND_MAILBOX}/sendMail",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ok = resp.status in (200, 202)
    except (urllib.error.URLError, OSError) as exc:
        log.warning("notify send to %s failed: %s", recipient, exc)
        return False
    if not ok:
        log.warning("notify send to %s: unexpected status", recipient)
    return ok
