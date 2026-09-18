"""The mail path end to end, through the real SMTP listener (backlog item 128).

`tests/test_intake_mail.py` drives the handler's decision functions and
`process_message(synchronous=True)` directly, and stubs routing. Nothing in
the suite started the aiosmtpd `Controller` the app runs in production, so a
break anywhere between the socket and the month (the app's startup hook, the
port, the envelope the library hands the handler, the routing thread, the
job that ingests) was invisible until a real mail failed to appear.

Here the app is created with `EXPENSE_RECON_INTAKE_SMTP=1`, its own startup
starts the listener through `smtp_server.start_intake_smtp` on a free port,
and a real client (`smtplib`) talks SMTP to it:

* a receipt mailed to the intake domain lands in the open month for its
  printed date, with mail provenance, read back from
  `GET /api/expense-batches/{id}`;
* RCPT to a foreign domain is answered 550 (no relaying), and written down;
* a message above the unrecognised-sender size cap is answered 552, written
  down, and never archived.

One test-side shim, on the library not the app: aiosmtpd's readiness probe
opens a TCP connection to the BIND address to be sure the server is up. The
listener binds `0.0.0.0`; Linux routes a connect to that address to loopback,
Windows refuses it (WinError 10049), so on a Windows box the unmodified
`start()` raises and `start_intake_smtp` fails open to None. The shim points
the probe at 127.0.0.1 and changes nothing else: the listener still binds
`0.0.0.0` and serves the real protocol.

Nothing here asserts the EHLO capability list: a `250-STARTTLS` line is due
to appear when the STARTTLS round lands, and this file must not care.
"""
from __future__ import annotations

import calendar
import smtplib
import socket
import time
from contextlib import ExitStack
from datetime import date, timedelta
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import make_msgid

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("aiosmtpd")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web import smtp_server  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    STATUS_INGESTED,
    DayBudget,
    read_log,
    read_refusals,
)

DOMAIN = "receipts.example.test"
SENDER = "bookkeeper@example.test"
STRANGER = "someone@elsewhere.test"
JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000  # big enough to not read as a logo
# Relative to today so the plausibility clamp never expires the fixture:
# the receipt is dated in the month BEFORE the arrival month.
RECEIPT_DAY = date.today().replace(day=1) - timedelta(days=20)
MONTH_LABEL = f"{calendar.month_name[RECEIPT_DAY.month]} {RECEIPT_DAY.year}"
LANDING_DEADLINE_S = 60.0


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _probe_via_loopback(self):
    """aiosmtpd's `InetMixin._trigger_server`, with the bind-all address
    mapped to loopback (see the module docstring)."""
    hostname = self.hostname or self._localhost
    if hostname == "0.0.0.0":
        hostname = "127.0.0.1"
    with ExitStack() as stk:
        s = stk.enter_context(socket.create_connection((hostname, self.port), 1.0))
        s.recv(1024)


@pytest.fixture
def listener(tmp_path, monkeypatch):
    """The app with its listener up on a free port. Yields the TestClient,
    with `_port` and `_data_root` on it."""
    from aiosmtpd.controller import InetMixin

    port = _free_port()
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP", "1")
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_SMTP_PORT", str(port))
    monkeypatch.setenv("EXPENSE_RECON_INTAKE_DOMAIN", DOMAIN)
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    for var in ("OPENAI_API_KEY", "BRISKEN_TENANT_ID",
                "BRISKEN_GRAPH_CLIENT_ID", "BRISKEN_GRAPH_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)  # no model, no acks
    monkeypatch.setattr(InetMixin, "_trigger_server", _probe_via_loopback)
    monkeypatch.setattr(smtp_server, "DAY_BUDGET", DayBudget())  # hermetic
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.app.state.intake_smtp is not None, (
            "the app's startup did not bring the listener up"
        )
        client._port = port
        client._data_root = tmp_path
        yield client
    assert app.state.intake_smtp is None, "shutdown did not stop the listener"


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date=RECEIPT_DAY.isoformat(), total="42.50", currency="USD",
        vendor="Stationer", reference="", line_items=(), confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    """One mock reader for the whole turn: the arrival read that decides the
    month and the batch ingest pop from the same queue, in that order."""
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, monkeypatch, label: str) -> str:
    """An open month labelled `label` holding one uploaded seed receipt."""
    _patch_ocr(monkeypatch)
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": label},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    batch_id = body["batch_id"]
    _patch_ocr(monkeypatch, _extraction())
    added = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
    )
    assert added.status_code == 200, added.text
    assert client.get(f"/jobs/{added.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _mail(from_addr: str, to_addr: str, attachments: list[tuple[str, bytes]],
          subject: str = "taxi receipt") -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="example.test")
    msg.set_content("receipt attached")
    for name, data in attachments:
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf") else ("image", "jpeg")
        )
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
    # On the wire lines end in CRLF (RFC 5321). `smtplib` fixes the line
    # endings of a `str` payload and sends `bytes` untouched, and the default
    # policy serializes with bare LF, which aiosmtpd reads as one line of the
    # whole message and refuses (500 Line too long). The SMTP policy is what
    # a real sender's MTA produces.
    return msg.as_bytes(policy=SMTP_POLICY)


def _smtp(client) -> smtplib.SMTP:
    smtp = smtplib.SMTP("127.0.0.1", client._port, timeout=10)
    code, _ = smtp.ehlo()
    assert code == 250
    return smtp


def _wait_for_mailed_expense(client, batch_id: str) -> dict:
    """Poll the month until an expense carrying mail provenance appears.
    The listener acks before routing, so the landing is asynchronous by
    design; the deadline is the failure, not a sleep."""
    deadline = time.monotonic() + LANDING_DEADLINE_S
    grid: dict = {}
    while time.monotonic() < deadline:
        grid = client.get(f"/api/expense-batches/{batch_id}").json()
        mailed = [e for e in grid.get("expenses", []) if e.get("submitted_by")]
        if mailed:
            assert len(mailed) == 1, mailed
            return mailed[0]
        time.sleep(0.2)
    pytest.fail(
        "the mailed receipt never landed in its month: expenses="
        f"{[(e.get('vendor'), e.get('submitted_by')) for e in grid.get('expenses', [])]} "
        f"log={read_log(client._data_root)}"
    )


# ------------------------------------------------------------ landing --

def test_a_mailed_receipt_lands_in_its_month_with_provenance(listener, monkeypatch):
    """Socket to month: a real SMTP session delivers a JPEG receipt to the
    intake address; the listener acks 250 after custody, routes it to the
    open month whose label names the receipt's printed month, and the month
    payload shows it with the sender as its provenance."""
    client = listener
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    # Two reads: the arrival read that decides the month, then the ingest.
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Taxi Lisboa", total="27.63"),
        _extraction(vendor="Taxi Lisboa", total="27.63"),
    )
    raw = _mail(SENDER, f"receipts@{DOMAIN}", [("taxi.jpg", JPG + b"taxi")])

    with _smtp(client) as smtp:
        smtp.mail(SENDER)
        code, _ = smtp.rcpt(f"receipts@{DOMAIN}")
        assert code == 250
        code, reply = smtp.data(raw)
    assert code == 250, reply
    assert b"accepted" in reply.lower(), reply

    mailed = _wait_for_mailed_expense(client, batch_id)
    assert mailed["submitted_by"]["address"] == SENDER
    assert mailed["submitted_by"]["source"] == "sender"
    assert mailed["vendor"]["display"] == "Taxi Lisboa"

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert any(e["submitted_by"] is None for e in grid["expenses"])  # the seed

    log = read_log(client._data_root)
    assert log and log[-1]["status"] == STATUS_INGESTED, log
    assert log[-1]["from"] == SENDER
    assert log[-1]["batch_id"] == batch_id
    assert read_refusals(client._data_root) == []


# ----------------------------------------------------------- refusals --

def test_the_listener_refuses_to_relay_to_a_foreign_domain(listener):
    """RCPT outside the intake domain is 550 at the envelope (the listener
    is not an open relay), and the refusal is written down."""
    client = listener
    with _smtp(client) as smtp:
        smtp.mail(STRANGER)
        code, reply = smtp.rcpt("victim@elsewhere.test")
        assert code == 550, reply
        assert b"relay" in reply.lower(), reply
        # the intake's own address is still fine in the same session
        code, _ = smtp.rcpt(f"receipts@{DOMAIN}")
        assert code == 250
    refusals = read_refusals(client._data_root)
    hit = [r for r in refusals if r["to"] == "victim@elsewhere.test"]
    assert len(hit) == 1, refusals
    assert hit[0]["stage"] == "rcpt"
    assert hit[0]["reason"].startswith("550")
    assert read_log(client._data_root) == []


def test_the_listener_refuses_an_oversized_message_from_a_stranger(listener):
    """A message over `intake.unknown_max_message_bytes` from an address we
    do not recognise is 552 at DATA (permanent: a retry would fail the same
    way), written down, and never archived."""
    client = listener
    resp = client.put(
        "/api/settings", json={"intake": {"unknown_max_message_bytes": 4096}},
    )
    assert resp.status_code == 200, resp.text
    raw = _mail(STRANGER, f"receipts@{DOMAIN}", [("big.jpg", JPG + b"x" * 20000)])
    assert len(raw) > 4096

    with _smtp(client) as smtp:
        smtp.mail(STRANGER)
        code, _ = smtp.rcpt(f"receipts@{DOMAIN}")
        assert code == 250
        code, reply = smtp.data(raw)
    assert code == 552, reply
    assert b"too large" in reply.lower(), reply

    refusals = read_refusals(client._data_root)
    hit = [r for r in refusals if r["stage"] == "data"]
    assert len(hit) == 1, refusals
    assert hit[0]["reason"].startswith("552")
    assert hit[0]["from"] == STRANGER
    assert read_log(client._data_root) == []
