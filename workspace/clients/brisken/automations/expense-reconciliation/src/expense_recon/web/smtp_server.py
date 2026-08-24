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

Enabled only when EXPENSE_RECON_INTAKE_SMTP=1 (fly.toml); tests exercise
the decision functions and handler directly, never a real socket.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from .intake_mail import (
    DAY_BUDGET,
    IntakeConfig,
    archive_incoming,
    disk_low,
    end_route,
    parse_inbound,
    record_refusal,
    route_archived,
    try_begin_route,
)
from .store import RunStore

log = logging.getLogger("expense_recon.intake")

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
        if not try_begin_route():
            return _refuse("452 4.5.3 intake busy, try again later")
        # Reserve spend at acceptance time, BEFORE the 250, so concurrent
        # connections cannot race past the caps (units: files, min 1 so
        # zero-file spam consumes budget too).
        sender = parsed.from_addr or (envelope.mail_from or "").lower()
        if not DAY_BUDGET.reserve(
            self.data_root, sender, len(parsed.attachments), cfg
        ):
            end_route()
            return _refuse(
                "452 4.5.3 daily submission limit reached, try again tomorrow"
            )
        # Custody BEFORE the ack: archive inline; only routing/OCR moves to
        # the worker thread. An archive failure answers 451 (sender retries).
        try:
            arch = archive_incoming(self.data_root, raw, parsed, peer=peer)
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
    controller = Controller(
        handler,
        hostname="0.0.0.0",  # noqa: S104 - Fly-internal; public edge is the Fly proxy
        port=port,
        data_size_limit=DATA_SIZE_LIMIT,
        ident="brisken-expense-intake",
    )
    try:
        controller.start()
    except Exception:  # noqa: BLE001 - the web app must come up regardless
        log.exception("intake SMTP listener failed to start (port %s)", port)
        return None
    log.info("intake SMTP listener on :%s", port)
    return controller
