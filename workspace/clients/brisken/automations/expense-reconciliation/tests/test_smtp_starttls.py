"""The intake mailbox offers STARTTLS (backlog item 125).

Two layers under test. The certificate helper `ensure_cert` (pure, no
socket): it makes a self-signed pair on the data volume, reuses it, renews
it before expiry, and fails open to plaintext when openssl is absent. And
the listener itself, driven over a real loopback socket with `smtplib`:
STARTTLS is advertised and completes, and every arrival records whether its
session was encrypted (`transport_tls`) on the archive meta and on the
receipt's `submitted_by` provenance that `GET /api/expense-batches/{id}`
serves.

The differential case is the one that matters: a sender that never issues
STARTTLS still delivers, and its receipt reads `transport_tls: False`, not
absent. A one-sided test that only exercised the TLS path would pass even
if the field were hard-wired to True; the plaintext row is what makes the
field mean something. See `test_plaintext_session_lands_false` (differential
probe) below.
"""
from __future__ import annotations

import calendar
import logging
import smtplib
import socket
import ssl
import threading
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("aiosmtpd")

from aiosmtpd.controller import Controller  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import smtp_server as ss  # noqa: E402
from expense_recon.web import smtp_tls  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import _read_meta, inbound_root, read_log, route_archived  # noqa: E402
from expense_recon.web.smtp_server import IntakeHandler  # noqa: E402
from expense_recon.web.smtp_tls import cert_not_after, ensure_cert  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000  # big enough not to read as a logo
DOMAIN = "expenses.brisken.com"
RECEIPT_DAY = date.today().replace(day=1) - timedelta(days=20)
MONTH_LABEL = f"{calendar.month_name[RECEIPT_DAY.month]} {RECEIPT_DAY.year}"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _clear_tls_env(monkeypatch) -> None:
    monkeypatch.delenv(smtp_tls.ENV_CERT, raising=False)
    monkeypatch.delenv(smtp_tls.ENV_KEY, raising=False)


# ------------------------------------------------------------ ensure_cert --

def test_ensure_cert_creates_pair(tmp_path, monkeypatch):
    _clear_tls_env(monkeypatch)
    pair = ensure_cert(tmp_path)
    assert pair is not None
    cert, key = pair
    assert cert.is_file() and key.is_file()
    assert cert == tmp_path / "tls" / "cert.pem"
    assert cert.read_text().startswith("-----BEGIN CERTIFICATE-----")
    # An expiry ~825 days out (the CERT_DAYS default), well beyond the window.
    not_after = cert_not_after(cert)
    assert not_after is not None
    assert not_after - datetime.now(timezone.utc) > timedelta(days=700)


def test_ensure_cert_reuses_pair(tmp_path, monkeypatch):
    _clear_tls_env(monkeypatch)
    cert, _ = ensure_cert(tmp_path)
    first_bytes = cert.read_bytes()
    first_mtime = cert.stat().st_mtime_ns
    cert2, _ = ensure_cert(tmp_path)
    # A healthy, in-date pair is returned untouched: same file, same bytes.
    assert cert2 == cert
    assert cert.read_bytes() == first_bytes
    assert cert.stat().st_mtime_ns == first_mtime


def test_ensure_cert_renews_before_expiry(tmp_path, monkeypatch):
    _clear_tls_env(monkeypatch)
    # A pair that expires tomorrow is inside the 30-day renew window.
    cert, _ = ensure_cert(tmp_path, days=1)
    near = cert_not_after(cert)
    assert near is not None
    assert near - datetime.now(timezone.utc) < timedelta(days=2)
    # The next call sees it is about to expire and regenerates a full-life one.
    cert2, _ = ensure_cert(tmp_path)
    far = cert_not_after(cert2)
    assert far is not None
    assert far - near > timedelta(days=700)


def test_ensure_cert_returns_none_without_openssl(tmp_path, monkeypatch, caplog):
    _clear_tls_env(monkeypatch)
    monkeypatch.setattr(smtp_tls.shutil, "which", lambda name: None)
    with caplog.at_level(logging.WARNING, logger="expense_recon.intake"):
        assert ensure_cert(tmp_path) is None
    assert "openssl" in caplog.text.lower()
    assert not (tmp_path / "tls" / "cert.pem").exists()


def test_ensure_cert_uses_env_pair_and_skips_generation(tmp_path, monkeypatch):
    # A CA-issued pair dropped in via the env overrides is used verbatim, and
    # no generation happens (proven by pointing openssl at nothing).
    cert, key = ensure_cert(tmp_path / "seed")  # borrow the generator for a real pair
    monkeypatch.setenv(smtp_tls.ENV_CERT, str(cert))
    monkeypatch.setenv(smtp_tls.ENV_KEY, str(key))
    monkeypatch.setattr(smtp_tls.shutil, "which", lambda name: None)
    data_root = tmp_path / "data"
    pair = ensure_cert(data_root)
    assert pair == (cert, key)
    assert not (data_root / "tls").exists()  # nothing generated on the volume


# ------------------------------------------------- the live listener --

def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date=RECEIPT_DAY.isoformat(), total="42.50", currency="USD",
        vendor="Staples", reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


@pytest.fixture
def mailbox(tmp_path, monkeypatch):
    """A running app with one month-labelled batch open, plus a real SMTP
    listener wired to it. Yields (client, batch_id, start_listener)."""
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    _clear_tls_env(monkeypatch)
    app = create_app(tmp_path)
    with TestClient(app) as client:
        client._data_root = tmp_path
        # A month-labelled batch, so a receipt printed in RECEIPT_MONTH claims it.
        _patch_ocr(monkeypatch)
        resp = client.post(
            "/api/expense-batches",
            data={"legal_entity": "Corporate Services", "label": MONTH_LABEL},
        )
        assert resp.status_code == 200, resp.text
        batch_id = resp.json()["batch_id"]
        assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
        # Alias so a mailed receipt books to a named person (submitted_by).
        client.put("/api/settings", json={"intake": {"aliases": {"dirk": "Dirk Neumann"}}})

        state = client.app.state

        def start_listener(monkeypatch_, tls_context) -> tuple[Controller, int, threading.Event]:
            """A listener bound to this app's store, routing synchronously and
            signalling an Event so the test can read the grid without polling."""
            done = threading.Event()

            def sync_route(self, arch, parsed):
                try:
                    route_archived(
                        self.db_path, self.learning_db_path, self.data_root,
                        arch, parsed, synchronous=True,
                    )
                finally:
                    ss.end_route()
                    done.set()

            monkeypatch_.setattr(IntakeHandler, "_route", sync_route)
            handler = IntakeHandler(state.db_path, state.learning_db_path, state.data_root)
            port = _free_port()
            controller = Controller(
                handler, hostname="127.0.0.1", port=port,
                tls_context=tls_context, require_starttls=False,
            )
            controller.start()
            return controller, port, done

        yield client, batch_id, start_listener


def _send(port: int, *, starttls: bool, from_addr: str) -> None:
    smtp = smtplib.SMTP("127.0.0.1", port, timeout=15)
    try:
        smtp.ehlo()
        advertised = "starttls" in smtp.esmtp_features
        if starttls:
            assert advertised, "STARTTLS not advertised on a TLS-enabled listener"
            smtp.starttls(context=ssl._create_unverified_context())
            smtp.ehlo()
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = f"receipts+dirk@{DOMAIN}"
        msg["Subject"] = "July taxi"
        msg.set_content("receipt attached")
        msg.add_attachment(
            JPG + b"uber", maintype="image", subtype="jpeg", filename="uber.jpg"
        )
        smtp.send_message(msg)
    finally:
        smtp.quit()


def _newest_meta(data_root: Path) -> dict:
    archives = sorted(inbound_root(data_root).glob("2*-*"))
    assert archives, "no archive written"
    return _read_meta(archives[-1])


def test_starttls_delivery_lands_true(mailbox, monkeypatch):
    """A real STARTTLS session: the offer is advertised, the handshake
    completes, and the mailed receipt carries transport_tls True on both the
    archive meta and the grid's submitted_by."""
    client, batch_id, start_listener = mailbox
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.63"),
        _extraction(vendor="Uber", total="27.63"),
    )
    ctx = smtp_tls.server_context(*ensure_cert(client._data_root))
    controller, port, done = start_listener(monkeypatch, ctx)
    try:
        _send(port, starttls=True, from_addr="Criss <cristiane.cavalcanti@brisken.com>")
        assert done.wait(25), "routing did not finish"
    finally:
        controller.stop()

    assert _newest_meta(client._data_root)["transport_tls"] is True
    assert read_log(client._data_root)[-1]["transport_tls"] is True

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1
    assert mailed[0]["submitted_by"]["transport_tls"] is True


def test_plaintext_session_lands_false(mailbox, monkeypatch):
    """Differential probe. The row class a one-sided test would miss: a
    sender that never issues STARTTLS. It still delivers on the SAME
    TLS-enabled listener, and its receipt reads transport_tls False (present,
    not absent), so the field distinguishes cleartext from encrypted rather
    than merely echoing that TLS was offered."""
    client, batch_id, start_listener = mailbox
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.63"),
        _extraction(vendor="Uber", total="27.63"),
    )
    ctx = smtp_tls.server_context(*ensure_cert(client._data_root))
    controller, port, done = start_listener(monkeypatch, ctx)
    try:
        _send(port, starttls=False, from_addr="Criss <cristiane.cavalcanti@brisken.com>")
        assert done.wait(25), "routing did not finish"
    finally:
        controller.stop()

    meta = _newest_meta(client._data_root)
    assert "transport_tls" in meta and meta["transport_tls"] is False

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1
    sub = mailed[0]["submitted_by"]
    assert "transport_tls" in sub and sub["transport_tls"] is False


def test_tls_disabled_offers_no_starttls(mailbox, monkeypatch):
    """EXPENSE_RECON_SMTP_TLS=0 is the documented escape hatch: the listener
    comes up plaintext (start_intake_smtp builds no context) and never
    advertises STARTTLS."""
    client, _batch_id, start_listener = mailbox
    # The listener with a None context is exactly what _tls_context returns
    # under EXPENSE_RECON_SMTP_TLS=0; assert the switch maps to None first.
    monkeypatch.setenv("EXPENSE_RECON_SMTP_TLS", "0")
    ctx, state = ss._tls_context(Path(client._data_root))
    assert ctx is None
    assert state.startswith("off: EXPENSE_RECON_SMTP_TLS=0")

    controller, port, _done = start_listener(monkeypatch, ctx)
    try:
        smtp = smtplib.SMTP("127.0.0.1", port, timeout=15)
        smtp.ehlo()
        assert "starttls" not in smtp.esmtp_features
        smtp.quit()
    finally:
        controller.stop()


# ------------------------------------------ start_intake_smtp (the caller) --
# The tests above build a Controller directly; these drive the real
# assembly, start_intake_smtp, so they bite the wiring that feeds the TLS
# context into the listener. Removing `tls_context=` from that call fails
# `test_start_intake_smtp_offers_starttls`; the hand-built tests above,
# which pass their own context, would not notice, which is why this one
# exists.
#
# start_intake_smtp binds `hostname="0.0.0.0"`; aiosmtpd's start-readiness
# probe then connects to (0.0.0.0, port), which Windows rejects (WinError
# 10049) though Linux (the Fly target) accepts it. To run the real caller
# on either OS we bind the probe to loopback, changing only where it
# listens, never the tls_context / require_starttls it is under test for.

def _patch_loopback_controller(monkeypatch) -> None:
    import aiosmtpd.controller as aiocontroller

    class _LoopbackController(aiocontroller.Controller):
        def __init__(self, handler, **kw):
            kw["hostname"] = "127.0.0.1"
            super().__init__(handler, **kw)

    # start_intake_smtp does `from aiosmtpd.controller import Controller`
    # at call time, so patching the module attribute is enough.
    monkeypatch.setattr(aiocontroller, "Controller", _LoopbackController)


def test_start_intake_smtp_offers_starttls(tmp_path, monkeypatch):
    """start_intake_smtp builds the context from the data volume and hands it
    to the Controller: a fresh EHLO advertises STARTTLS."""
    _clear_tls_env(monkeypatch)
    monkeypatch.delenv("EXPENSE_RECON_SMTP_TLS", raising=False)
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP", "1")
    _patch_loopback_controller(monkeypatch)
    port = _free_port()
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP_PORT", str(port))
    controller = ss.start_intake_smtp(tmp_path / "recon-web.sqlite", None, tmp_path)
    assert controller is not None, "listener did not start"
    try:
        smtp = smtplib.SMTP("127.0.0.1", port, timeout=15)
        smtp.ehlo()
        assert "starttls" in smtp.esmtp_features
        smtp.quit()
    finally:
        controller.stop()
    # And the pair really landed on the volume where a CA cert would replace it.
    assert (tmp_path / "tls" / "cert.pem").is_file()


def test_start_intake_smtp_honours_disable_switch(tmp_path, monkeypatch):
    """EXPENSE_RECON_SMTP_TLS=0 end to end: start_intake_smtp comes up
    plaintext and advertises no STARTTLS, and writes no certificate."""
    _clear_tls_env(monkeypatch)
    monkeypatch.setenv("EXPENSE_RECON_SMTP_TLS", "0")
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP", "1")
    _patch_loopback_controller(monkeypatch)
    port = _free_port()
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP_PORT", str(port))
    controller = ss.start_intake_smtp(tmp_path / "recon-web.sqlite", None, tmp_path)
    assert controller is not None
    try:
        smtp = smtplib.SMTP("127.0.0.1", port, timeout=15)
        smtp.ehlo()
        assert "starttls" not in smtp.esmtp_features
        smtp.quit()
    finally:
        controller.stop()
    assert not (tmp_path / "tls").exists()
