"""Inbound SMTP listener: the app IS the mailbox for expenses.brisken.com.

Fly terminates raw TCP on public port 25 (dedicated IPv4) and forwards to
this listener on the internal port (default 2525) inside the same machine
as the web app, so the intake shares the /data volume and the run store.
Scale-to-zero: the Fly proxy starts the machine on an incoming connection;
senders that raced the cold start retry per SMTP semantics.

Custody contract (adversarial review 2026-08-20): the 250 is answered only
AFTER the raw message + acceptance log row are on the /data volume, so an
acknowledged mail can never vanish in a crash/stop window. Refusals are
in-protocol (550 permanent / 452-451 temporary) — the sender's own mail
system generates the bounce; this app sends nothing, keeping the
no-autonomous-send rule intact. Abuse guards fire BEFORE acceptance: the
in-memory day budget (reserved under its lock, raceproof in-process), an
in-flight route ceiling, and a free-disk floor.

Who may submit: anyone (owner directive 2026-08-23). The two boundaries
that remain are the recipient — mail must be addressed to our own domain,
so the listener is not an open relay — and the spend guards above. There
is deliberately no sender check: From is forgeable, so an allowlist bought
tidiness rather than security, and it cost every receipt that reached us
by any route other than a Brisken mailbox.

Every refusal is also WRITTEN DOWN (backlog item 30 b, 2026-08-24).
Answering in-protocol is correct and silent; until the ledger existed,
"is anything being turned away?" had no answer anywhere in the system,
which is precisely the question an owner asked about receipts that never
appeared. Recording never blocks the refusal itself.

Transport (backlog item 125, 2026-09-18): the listener offers STARTTLS
(opportunistic, TLS 1.2+, a self-signed pair from smtp_tls.py until a CA
certificate is dropped in through its env overrides). It is never
required: a sender without TLS still delivers, and every arrival records
whether its session was encrypted (`transport_tls` on the archive meta,
the acceptance log row and the receipt's provenance), so who still
delivers in the clear is readable from the data, not guessed.
EXPENSE_RECON_SMTP_TLS=0 turns the offer off.

Enabled only when EXPENSE_RECON_INTAKE_SMTP=1 (fly.toml); test_intake_mail
exercises the decision functions and handler directly, never a real
socket; test_smtp_starttls runs the real listener on a loopback port.
"""
from __future__ import annotations

import logging
import os
import ssl
import threading
from pathlib import Path

from .intake_mail import (
    DAY_BUDGET,
    IntakeConfig,
    archive_incoming,
    disk_low,
    end_route,
    is_known_sender,
    parse_inbound,
    record_refusal,
    route_archived,
    try_begin_route,
)
from .smtp_tls import describe, ensure_cert, server_context
from .store import RunStore

log = logging.getLogger("expense_recon.intake")

# The listener's protocol ceiling, for everyone. An unrecognised sender is
# held to a much smaller per-message size and a shared daily byte budget
# (item 122, enforced in handle_DATA): anyone may submit, so a stranger
# mailing 25 MB two hundred times a day used to be enough to fill the
# volume in an afternoon and stop Brisken's own receipts.
DATA_SIZE_LIMIT = 25 * 1024 * 1024  # bytes per message (attachments incl.)
MAX_RCPTS = 10


def rcpt_decision(address: str, domain: str, n_rcpts: int) -> str | None:
    """None = accept; else the SMTP error line."""
    addr = (address or "").strip().lower()
    if n_rcpts >= MAX_RCPTS:
        return "452 4.5.3 too many recipients"
    if not addr.endswith("@" + domain):
        return "550 5.7.1 relay not permitted"
    return None


def _peer(session) -> str:
    """Best-effort connecting IP; never raises into the SMTP path."""
    try:
        return session.peer[0] if session and session.peer else ""
    except Exception:  # noqa: BLE001 - peer is best-effort metadata
        return ""


def transport_tls(session) -> bool:
    """Whether this SMTP session completed STARTTLS before now.

    aiosmtpd 1.4.6 keeps `session.ssl` at None and sets it to the TLS
    transport's extra-info dict once the handshake succeeds (smtp.py,
    `connection_made`: `self.session.ssl = self._tls_protocol._extra`); a
    session that never issued STARTTLS keeps None. getattr-tolerant: the
    handler tests drive `handle_DATA` with a bare namespace, and an
    unreadable session reads as plaintext, never as a crash."""
    try:
        return getattr(session, "ssl", None) is not None
    except Exception:  # noqa: BLE001 - a transport flag is never worth a 4xx
        return False


class IntakeHandler:
    """aiosmtpd handler. Thin: parse envelope, delegate every decision."""

    def __init__(
        self, db_path: Path, learning_db_path: Path | None, data_root: Path,
    ) -> None:
        self.db_path = Path(db_path)
        self.learning_db_path = learning_db_path
        self.data_root = Path(data_root)

    def _config(self) -> IntakeConfig:
        with RunStore(self.db_path) as store:
            return IntakeConfig.from_settings(store.get_settings())

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        err = rcpt_decision(
            address, self._config().domain, len(envelope.rcpt_tos)
        )
        if err is not None:
            record_refusal(
                self.data_root, stage="rcpt", reason=err,
                sender=getattr(envelope, "mail_from", "") or "",
                recipient=address, peer=_peer(session),
            )
            return err
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        raw = envelope.content or b""
        cfg = self._config()
        parsed = parse_inbound(raw, cfg.domain, envelope.rcpt_tos)
        peer = _peer(session)
        rcpt = (envelope.rcpt_tos or [""])[0]

        def _refuse(reason: str) -> str:
            # DATA-stage refusals matter MORE than a bad RCPT: each one is
            # a real submission we accepted the envelope for and then
            # turned away, so it is exactly the mail somebody will later
            # swear they sent.
            record_refusal(
                self.data_root, stage="data", reason=reason,
                sender=parsed.from_addr or (envelope.mail_from or ""),
                recipient=rcpt, peer=peer,
            )
            return reason

        if disk_low(self.data_root):
            log.warning("intake refusing mail: low disk on data volume")
            return _refuse("452 4.3.1 storage low, try again later")
        # Who we RECOGNISE decides how much disk this message may spend
        # (item 122). Our own people keep the full 25 MB and skip the
        # per-sender file cap a month-end backfill exceeds; a stranger is
        # capped per message and against a shared daily byte budget.
        sender = parsed.from_addr or (envelope.mail_from or "").lower()
        known = is_known_sender(sender, cfg)
        if not known and len(raw) > cfg.unknown_max_message_bytes:
            # 552 is permanent on purpose: retrying the same 25 MB message
            # would fail identically, and the sender's own MTA should say
            # so rather than queue it for days.
            return _refuse(
                "552 5.3.4 message too large from an unrecognised sender"
            )
        if not try_begin_route():
            return _refuse("452 4.5.3 intake busy, try again later")
        # Reserve spend at acceptance time, BEFORE the 250, so concurrent
        # connections cannot race past the caps (units: files, min 1 so
        # zero-file spam consumes budget too; bytes, for strangers).
        if not DAY_BUDGET.reserve(
            self.data_root, sender, len(parsed.attachments), cfg,
            known=known, n_bytes=len(raw),
        ):
            end_route()
            return _refuse(
                "452 4.5.3 daily submission limit reached, try again tomorrow"
            )
        # Custody BEFORE the ack: archive inline; only routing/OCR moves to
        # the worker thread. An archive failure answers 451 (sender retries).
        try:
            arch = archive_incoming(
                self.data_root, raw, parsed, peer=peer, known_sender=known,
                transport_tls=transport_tls(session),
            )
        except Exception:  # noqa: BLE001 - no custody, no ack
            end_route()
            log.exception("intake archive failed")
            return _refuse("451 4.3.0 temporary storage failure, try again")
        threading.Thread(
            target=self._route, args=(arch, parsed), daemon=True
        ).start()
        return "250 Message accepted for processing"

    def _route(self, arch, parsed) -> None:
        try:
            result = route_archived(
                self.db_path, self.learning_db_path, self.data_root,
                arch, parsed,
            )
            log.info("intake routed mail: %s", result.get("status"))
        except Exception:  # noqa: BLE001 - a routing crash must not kill
            log.exception("intake routing failed")
        finally:
            end_route()


def start_intake_smtp(
    db_path: Path, learning_db_path: Path | None, data_root: Path,
):
    """Start the listener (aiosmtpd Controller: own thread + loop). Returns
    the controller, or None when disabled/unavailable — the web app must
    come up either way (fail-open: mail queues at the sender on failure,
    receipts are never silently lost by a dead web app)."""
    if os.environ.get("EXPENSE_RECON_INTAKE_SMTP") != "1":
        return None
    try:
        from aiosmtpd.controller import Controller
    except ImportError:
        log.error("EXPENSE_RECON_INTAKE_SMTP=1 but aiosmtpd is not installed")
        return None
    port = int(os.environ.get("EXPENSE_RECON_INTAKE_SMTP_PORT", "2525"))
    handler = IntakeHandler(db_path, learning_db_path, data_root)
    tls_ctx, tls_state = _tls_context(Path(data_root))
    controller = Controller(
        handler,
        hostname="0.0.0.0",  # noqa: S104 - Fly-internal; public edge is the Fly proxy
        port=port,
        data_size_limit=DATA_SIZE_LIMIT,
        ident="brisken-expense-intake",
        # Item 125: the STARTTLS offer (aiosmtpd forwards both kwargs to
        # SMTP.__init__; None = plaintext only, the pre-item-125 listener).
        tls_context=tls_ctx,
        # Opportunistic, never required: a sender without TLS still delivers.
        require_starttls=False,
    )
    try:
        controller.start()
    except Exception:  # noqa: BLE001 - the web app must come up regardless
        log.exception("intake SMTP listener failed to start (port %s)", port)
        return None
    log.info("intake SMTP listener on :%s", port)
    log.info("intake SMTP STARTTLS %s", tls_state)
    return controller


def _tls_context(data_root: Path) -> tuple[ssl.SSLContext | None, str]:
    """(context, state line) for the listener. The state line reads
    `on (self-signed, CN=..., expires ...)` or `off: <reason>`; every
    failure path returns (None, reason) so the listener stays plaintext,
    which is today's behaviour, never a crash."""
    if os.environ.get("EXPENSE_RECON_SMTP_TLS", "1").strip() == "0":
        return None, "off: EXPENSE_RECON_SMTP_TLS=0"
    try:
        pair = ensure_cert(data_root)
    except Exception:  # noqa: BLE001 - certificate trouble never blocks mail
        log.exception("intake SMTP STARTTLS: certificate step raised")
        return None, "off: certificate step raised (see traceback above)"
    if pair is None:
        return None, "off: no usable certificate (see warning above)"
    cert, key = pair
    try:
        ctx = server_context(cert, key)
    except (OSError, ssl.SSLError) as exc:
        log.warning("intake SMTP STARTTLS: certificate pair rejected: %s", exc)
        return None, f"off: certificate pair rejected ({exc})"
    return ctx, f"on ({describe(cert)})"
