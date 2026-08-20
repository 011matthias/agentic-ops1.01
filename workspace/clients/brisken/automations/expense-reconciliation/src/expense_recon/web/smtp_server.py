"""Inbound SMTP listener: the app IS the mailbox for expenses.brisken.com.

Fly terminates raw TCP on public port 25 (dedicated IPv4) and forwards to
this listener on the internal port (default 2525) inside the same machine
as the web app, so the intake shares the /data volume and the run store.
Scale-to-zero: the Fly proxy starts the machine on an incoming connection;
senders that raced the cold start retry per SMTP semantics.

Policy (decisions delegated to intake_mail, kept pure for tests):
  - RCPT must be at the intake domain (else 550; we relay nothing).
  - MAIL FROM + the From header must pass the sender allowlist (else 550:
    the sender's own system generates the bounce — the app sends nothing,
    which keeps the no-autonomous-send rule intact).
  - Daily per-sender/global file caps => 452 (temporary; sender retries).
  - Accepted mail is archived + routed by intake_mail.process_message in a
    worker thread; DATA answers fast.

Enabled only when EXPENSE_RECON_INTAKE_SMTP=1 (fly.toml); tests exercise
the decision functions and handler directly, never a real socket.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from .intake_mail import (
    IntakeConfig,
    parse_inbound,
    process_message,
    sender_allowed,
    today_counts,
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


def data_decision(
    mail_from: str,
    header_from: str,
    cfg: IntakeConfig,
    per_sender_today: dict[str, int],
    global_today: int,
) -> str | None:
    """None = accept; else the SMTP error line. Envelope AND header sender
    must both pass: the envelope is what bounced mail routes to, the header
    is what attribution reads — a mismatch on either side is refused."""
    for candidate in (mail_from, header_from):
        if not sender_allowed(candidate, cfg.sender_allowlist):
            return "550 5.7.1 sender not permitted"
    sender = (header_from or mail_from).strip().lower()
    if per_sender_today.get(sender, 0) >= cfg.sender_daily_cap:
        return "452 4.5.3 daily submission limit reached, try again tomorrow"
    if global_today >= cfg.global_daily_cap:
        return "452 4.5.3 intake busy, try again tomorrow"
    return None


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
            return err
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        raw = envelope.content or b""
        cfg = self._config()
        parsed = parse_inbound(raw, cfg.domain)
        per_sender, global_today = today_counts(self.data_root)
        err = data_decision(
            envelope.mail_from or "", parsed.from_addr, cfg,
            per_sender, global_today,
        )
        if err is not None:
            log.info(
                "intake refused mail from %s (%s): %s",
                envelope.mail_from, parsed.from_addr, err,
            )
            return err
        peer = ""
        try:
            peer = session.peer[0] if session.peer else ""
        except Exception:  # noqa: BLE001 - peer is best-effort metadata
            peer = ""
        # Archive + route off the SMTP transaction; DATA answers immediately.
        threading.Thread(
            target=self._process, args=(raw, peer), daemon=True
        ).start()
        return "250 Message accepted for processing"

    def _process(self, raw: bytes, peer: str) -> None:
        try:
            result = process_message(
                self.db_path, self.learning_db_path, self.data_root, raw,
                peer=peer,
            )
            log.info("intake processed mail: %s", result.get("status"))
        except Exception:  # noqa: BLE001 - a processing crash must not kill
            log.exception("intake processing failed")


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
