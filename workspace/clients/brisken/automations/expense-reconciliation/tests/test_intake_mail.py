"""Mail intake (the app's own mailbox): parse -> archive -> route BY MONTH
into the matching expense batch, with per-file submitter provenance.

Since 2026-08-24 the routing decision is the receipt's own PRINTED month,
not "whichever batch happens to be open": mail whose month has no batch
RESTS in the pool (status ``pooled``) and is claimed automatically when
that month is created or renamed into. Most of the end-to-end tests here
therefore label their batch with a month, and budget TWO mock extractions
per mailed file: one for the arrival read that decides the month, one for
the batch ingest. (In production those two are one paid call, because the
extraction cache is content-addressed and the arrival read warms it; the
mock has no cache, so tests pay the queue twice. See
`test_arrival_extraction_warms_the_batch_cache` for the real path.)

Submission is open to any sender (owner directive 2026-08-23); the
boundaries that remain are the recipient domain (no relaying) and the spend
guards. Who we RECOGNISE is a narrower question than who may submit
(2026-08-24): a known sender (inside @brisken.com, or listed in
``intake.known_senders``) gets the acceptance ack even at a private
address, and their body-only mail is rendered on arrival instead of
waiting for a click. A stranger's still waits, and still alerts. Decision logic is pure/sync; the SMTP transport is exercised
through its decision functions and its handler, never a real socket. See
web/intake_mail.py + web/smtp_server.py."""
from __future__ import annotations

import asyncio
import calendar
import hashlib
import json
import time
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    HELD_BODY_ONLY,
    HELD_FAILED,
    STATUS_INGESTED,
    STATUS_POOLED,
    DayBudget,
    IntakeConfig,
    claim_pooled,
    is_known_sender,
    normalize_intake_setting,
    parse_inbound,
    process_message,
    read_log,
    replay_held,
    resolve_person,
    resolve_receipt_month,
)
from expense_recon.web.smtp_server import IntakeHandler, rcpt_decision  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000  # big enough to not read as a logo
DOMAIN = "expenses.brisken.com"
# A submitter we do not recognise. Since 2026-08-24 a KNOWN sender's
# body-only mail renders itself on arrival, so every fixture that wants a
# mail sitting in held_body_only has to come from outside: that is now the
# only way body-only mail waits for a click. Tests of the auto-render path
# use an @brisken.com sender or a listed address instead.
OUTSIDE = "guest@example.org"

# Fixture dates are relative to today, not literals, so the plausibility
# clamp (a printed date more than ~12 months before arrival reads as
# unreadable) can never expire this file. RECEIPT_DAY always lands in the
# month BEFORE today's — which is the whole point under test: the mail
# arrives in one month and belongs to another.
RECEIPT_DAY = date.today().replace(day=1) - timedelta(days=20)
RECEIPT_MONTH = f"{RECEIPT_DAY.year:04d}-{RECEIPT_DAY.month:02d}"
MONTH_LABEL = f"{calendar.month_name[RECEIPT_DAY.month]} {RECEIPT_DAY.year}"
ARRIVAL_MONTH = date.today().strftime("%Y-%m")
# Old enough to count as a never-routed straggler (the threshold is 10
# minutes) while still being a believable arrival for RECEIPT_DAY: the
# plausibility clamp measures the printed date AGAINST the arrival, so a
# forged year here would clamp every fixture receipt.
STALE_ARRIVAL = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()


def _label_for(day: date) -> str:
    return f"{calendar.month_name[day.month]} {day.year}"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(
        date=RECEIPT_DAY.isoformat(), total="42.50", currency="USD",
        vendor="Staples", reference="", line_items=(), confidence=0.9,
        notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    """One mock client for the whole turn: the arrival read and the batch
    ingest pop from the SAME queue, in that order. An empty queue answers
    with a dateless extraction, which routes the mail to its ARRIVAL
    month — so an under-budgeted test fails loudly rather than silently."""
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(
    client, monkeypatch, label: str | None = None,
    *extra: ExtractedReceipt,
) -> str:
    """Create an expense batch and wait for its OCR job.

    `label` names the batch's month; without one the batch carries the
    default full-date label, which names no month and can never claim
    mail. `extra` extends the mock queue past the seed receipt, for the
    pool claim that a month-labelled batch triggers on creation."""
    _patch_ocr(monkeypatch, _extraction(), *extra)
    data = {"legal_entity": "Corporate Services"}
    if label:
        data["label"] = label
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
        data=data,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "done", job
    return body["batch_id"]


def _mail(
    from_addr: str,
    to_addr: str = f"receipts@{DOMAIN}",
    attachments: list[tuple[str, bytes]] | None = None,
    body: str = "receipt attached",
    subject: str = "July taxi",
) -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = "<test@brisken.com>"
    msg.set_content(body)
    for name, data in attachments or []:
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf") else ("image", "jpeg")
        )
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=name
        )
    return msg.as_bytes()


# ---------------------------------------------------------------- parsing --

def test_parse_extracts_attachments_and_plus_alias():
    raw = _mail(
        "Dirk Neumann <dirk.neumann@brisken.com>",
        to_addr=f"receipts+dirk@{DOMAIN}",
        attachments=[("taxi.pdf", b"%PDF-1.4 fake"), ("photo.jpg", JPG)],
    )
    parsed = parse_inbound(raw, DOMAIN)
    assert parsed.from_addr == "dirk.neumann@brisken.com"
    assert parsed.to_locals == ["dirk"]  # plus-tag is the alias signal
    assert [n for n, _ in parsed.attachments] == ["taxi.pdf", "photo.jpg"]
    assert parsed.body_only is False


def test_parse_skips_signature_pixels_and_unsupported_types():
    raw = _mail(
        "a@brisken.com",
        attachments=[("logo.jpg", b"\xff\xd8tiny"), ("notes.docx", b"PK\x03\x04")],
    )
    parsed = parse_inbound(raw, DOMAIN)
    assert parsed.attachments == []
    assert "logo.jpg" in parsed.skipped
    # a docx is not receipt media and not a receipt suffix
    assert parsed.body_only is True  # nothing usable, but there IS a body


def test_parse_body_only_mail():
    parsed = parse_inbound(_mail("a@brisken.com", attachments=[]), DOMAIN)
    assert parsed.body_only is True
    assert parsed.attachments == []


def test_resolve_person_alias_beats_sender():
    cfg = IntakeConfig(aliases={"dirk": "Dirk Neumann"})
    by_alias = resolve_person(["dirk"], "criss@brisken.com", cfg)
    assert by_alias["person"] == "Dirk Neumann"
    assert by_alias["source"] == "alias"
    by_sender = resolve_person(["unknown"], "criss@brisken.com", cfg)
    assert by_sender["person"] == "criss@brisken.com"
    assert by_sender["source"] == "sender"


# ------------------------------------------------------- SMTP decisions --

def test_rcpt_decision_relay_denied():
    assert rcpt_decision(f"receipts@{DOMAIN}", DOMAIN, 0) is None
    assert rcpt_decision("victim@gmail.com", DOMAIN, 0).startswith("550")
    assert rcpt_decision(f"receipts@{DOMAIN}", DOMAIN, 10).startswith("452")


def _deliver(client, monkeypatch, raw: bytes, mail_from: str,
             rcpt: str = f"receipts@{DOMAIN}") -> str:
    """Drive the SMTP handler's acceptance path and return its reply line.

    Routing is stubbed: everything under test here happens BEFORE the 250
    (custody + the guards), and the real router would race the assertions.
    """
    from expense_recon.web import smtp_server as ss

    def fake_route(self, arch, parsed):  # noqa: ARG001 - signature match
        ss.end_route()

    monkeypatch.setattr(IntakeHandler, "_route", fake_route)
    monkeypatch.setattr(ss, "DAY_BUDGET", DayBudget())  # hermetic budget
    state = client.app.state
    handler = IntakeHandler(state.db_path, state.learning_db_path,
                            state.data_root)
    envelope = SimpleNamespace(content=raw, rcpt_tos=[rcpt],
                               mail_from=mail_from)
    session = SimpleNamespace(peer=("203.0.113.9", 51000))
    return asyncio.run(handler.handle_DATA(None, session, envelope))


def test_an_outside_sender_may_submit(client, monkeypatch):
    """The allowlist is gone (owner directive 2026-08-23). A hotel mailing
    an invoice, or a faculty member mailing from a private address, used to
    get a 550 at this exact point; now the mail is taken into custody."""
    raw = _mail("guest@gmail.com", attachments=[("hotel.pdf", b"%PDF-1.4 x")])
    reply = _deliver(client, monkeypatch, raw, "guest@gmail.com")
    assert reply.startswith("250")
    log = read_log(client.app.state.data_root)
    assert log[-1]["from"] == "guest@gmail.com"


def test_a_forged_header_sender_is_no_longer_a_refusal(client, monkeypatch):
    """Envelope and header sender used to have to agree, which is what
    refused forwarded and relayed mail. Attribution still records both."""
    raw = _mail("someone.else@example.org", attachments=[("r.jpg", JPG)])
    reply = _deliver(client, monkeypatch, raw, "bounces@mailer.example")
    assert reply.startswith("250")


def test_the_listener_is_still_not_an_open_relay(client, monkeypatch):
    """Opening the SENDER must not open the RECIPIENT: mail addressed
    anywhere but our own domain is still refused, or the app becomes a
    spam relay wearing Brisken's IP."""
    assert rcpt_decision("victim@gmail.com", DOMAIN, 0).startswith("550")
    raw = _mail("guest@gmail.com", attachments=[("r.jpg", JPG)])
    reply = _deliver(client, monkeypatch, raw, "guest@gmail.com",
                     rcpt=f"receipts@{DOMAIN}")
    assert reply.startswith("250")


def test_an_outside_submitter_gets_no_acknowledgement(monkeypatch):
    """The ack now has an untrusted recipient, so the Graph guard is the
    only thing between us and mailing confirmations to strangers as
    Brisken. Pin it with the sender ENABLED, or the test passes for the
    wrong reason (no creds in CI => every send is already False)."""
    from expense_recon.web import graph_notify

    for key in ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
                "BRISKEN_GRAPH_CLIENT_SECRET"):
        monkeypatch.setenv(key, "test")
    # Token minting stands in for "reached the network"; returning None
    # stops the send there, so no test ever talks to Graph.
    reached_network: list[str] = []
    monkeypatch.setattr(
        graph_notify, "_get_token", lambda: reached_network.append("token")
    )

    assert graph_notify.send_mail("guest@gmail.com", "s", "b") is False
    assert reached_network == []  # refused BEFORE any Graph call
    # ...and an internal recipient does get past the guard, so the line
    # above is the recipient rule and not some other early return.
    graph_notify.send_mail("criss@brisken.com", "s", "b")
    assert reached_network == ["token"]
    # The one exception is explicit and per call: an outside address the
    # operator LISTED. The same recipient is refused without the list and
    # passes with it, so the widening is the list and nothing else.
    private = "dirk_.neumann@icloud.com"
    assert graph_notify.send_mail(private, "s", "b") is False
    assert reached_network == ["token"]
    graph_notify.send_mail(private, "s", "b", allow_external=(private,))
    assert reached_network == ["token", "token"]


def test_day_budget_reserves_at_accept_and_charges_zero_file_mail(tmp_path):
    cfg = IntakeConfig(sender_daily_cap=3, global_daily_cap=4)
    budget = DayBudget()
    a = "a@brisken.com"
    # 2 files reserve 2 units; a zero-file mail still costs 1 unit
    assert budget.reserve(tmp_path, a, 2, cfg)
    assert budget.reserve(tmp_path, a, 0, cfg)
    # sender cap (3) is now exhausted
    assert not budget.reserve(tmp_path, a, 1, cfg)
    # a different sender still fits under the global cap (4): 1 unit left
    assert budget.reserve(tmp_path, "b@brisken.com", 1, cfg)
    assert not budget.reserve(tmp_path, "c@brisken.com", 1, cfg)


def test_day_budget_seeds_from_acceptance_log(tmp_path):
    from expense_recon.web.intake_mail import _append_log, _now_iso

    _append_log(tmp_path, {
        "at": _now_iso(), "from": "a@brisken.com", "n_files": 2,
        "status": "received", "archive": "x",
    })
    cfg = IntakeConfig(sender_daily_cap=3, global_daily_cap=10)
    budget = DayBudget()
    # 2 units already spent today by the log -> only 1 left for this sender
    assert budget.reserve(tmp_path, "a@brisken.com", 1, cfg)
    assert not budget.reserve(tmp_path, "a@brisken.com", 1, cfg)


def test_zip_attachments_are_refused_at_the_mail_boundary():
    msg = EmailMessage()
    msg["From"] = "a@brisken.com"
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = "zipped"
    msg.set_content("here")
    msg.add_attachment(
        b"PK\x03\x04zipbytes", maintype="application", subtype="zip",
        filename="receipts.zip",
    )
    parsed = parse_inbound(msg.as_bytes(), DOMAIN)
    assert parsed.attachments == []
    assert "receipts.zip" in parsed.skipped


def test_envelope_rcpts_feed_alias_resolution():
    # Bcc'd alias: headers show nothing, the envelope knows the recipient.
    raw = _mail("a@brisken.com", to_addr="someone@else.example",
                attachments=[("r.jpg", JPG)])
    parsed = parse_inbound(raw, DOMAIN, [f"receipts+dirk@{DOMAIN}"])
    assert parsed.to_locals == ["dirk"]


def test_intake_settings_drop_the_retired_senders_key():
    """A stored blob or an older client may still send `senders`. It is
    dropped, not rejected: a 400 on a dead key would block edits to the
    live ones sitting beside it."""
    ok = normalize_intake_setting(
        {"senders": ["@brisken.com"], "aliases": {"dirk": "Dirk Neumann"}}
    )
    assert "senders" not in ok
    assert ok["aliases"] == {"dirk": "Dirk Neumann"}


def test_a_stored_senders_list_no_longer_gates_anything():
    cfg = IntakeConfig.from_settings({"intake": {"senders": ["@brisken.com"]}})
    assert not hasattr(cfg, "sender_allowlist")


# ---------------------------------------------------------- end to end --

def test_mail_lands_in_open_batch_with_provenance(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    # alias map: mail to receipts+dirk@ books to Dirk by name
    with_settings = client.put(
        "/api/settings",
        json={"intake": {"aliases": {"dirk": "Dirk Neumann"}}},
    )
    assert with_settings.status_code == 200, with_settings.text

    # Two: the arrival read that decides the month, then the batch ingest.
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.63"),
        _extraction(vendor="Uber", total="27.63"),
    )
    raw = _mail(
        "Criss <cristiane.cavalcanti@brisken.com>",
        to_addr=f"receipts+dirk@{DOMAIN}",
        attachments=[("uber.jpg", JPG + b"uber")],
    )
    result = process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    assert result["status"] == STATUS_INGESTED
    assert result["batch_id"] == batch_id
    assert result["pool_month"] == RECEIPT_MONTH

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [
        e for e in grid["expenses"] if e.get("submitted_by") is not None
    ]
    assert len(mailed) == 1
    sub = mailed[0]["submitted_by"]
    assert sub["person"] == "Dirk Neumann"
    assert sub["source"] == "alias"
    assert sub["address"] == "cristiane.cavalcanti@brisken.com"
    # the seed receipt has no provenance (uploaded, not mailed)
    assert any(e["submitted_by"] is None for e in grid["expenses"])

    log = read_log(state.data_root)
    assert log[-1]["status"] == STATUS_INGESTED
    assert log[-1]["person"] == "Dirk Neumann"


def test_duplicate_mail_is_noop_and_keeps_first_provenance(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    payload = JPG + b"same-bytes"
    _patch_ocr(monkeypatch, _extraction(vendor="DB"), _extraction(vendor="DB"))
    first = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("a@brisken.com", attachments=[("db.jpg", payload)]),
        synchronous=True,
    )
    assert first["status"] == STATUS_INGESTED
    # One only: the resend still pays the arrival read (it decides the
    # month before anything knows the bytes are a duplicate), then the
    # content dedupe skips the ingest extraction entirely.
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("b@brisken.com", attachments=[("db-again.jpg", payload)]),
        synchronous=True,
    )
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1  # identical bytes ingested once
    assert mailed[0]["submitted_by"]["address"] == "a@brisken.com"


def test_mail_pools_until_its_month_opens_then_is_claimed(client, monkeypatch):
    """The pool lifecycle end to end: a receipt whose month has no batch
    rests in the pool with its month on it, and OPENING that month claims
    it — no replay click, no operator step."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())  # arrival read only; nothing to ingest into
    raw = _mail(
        "criss@brisken.com", attachments=[("taxi.jpg", JPG + b"taxi")]
    )
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED
    assert pooled["pool_month"] == RECEIPT_MONTH
    assert pooled["receipt_month_source"] == "receipt"

    log = client.get("/api/inbound/log").json()
    assert log["n_pooled"] == 1
    assert log["n_held"] == 0  # pooled is a resting state, not a held one
    row = [e for e in log["entries"] if e["archive"] == pooled["archive"]][0]
    assert row["pool_month"] == RECEIPT_MONTH
    assert row["pool_month_state"] == "no_batch"

    # Creating the month is the whole trigger.
    batch_id = _create_batch(
        client, monkeypatch, MONTH_LABEL, _extraction(vendor="Taxi Roma"),
    )
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1
    assert mailed[0]["submitted_by"]["address"] == "criss@brisken.com"

    log = client.get("/api/inbound/log").json()
    assert log["n_pooled"] == 0
    claimed = [e for e in log["entries"] if e["archive"] == pooled["archive"]]
    assert all(e["status"] == STATUS_INGESTED for e in claimed)
    assert claimed[-1]["batch_id"] == batch_id
    # Nothing left to drain, and a second pass does not re-add.
    again = client.post("/api/inbound/replay-held").json()
    assert (again["replayed"], again["claimed"]) == (0, 0)
    assert len(client.get(f"/api/expense-batches/{batch_id}").json()
               ["expenses"]) == len(grid["expenses"])


def test_body_only_mail_is_held_not_dropped(client):
    state = client.app.state
    result = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[], body="Uber receipt inline"),
        synchronous=True,
    )
    assert result["status"] == HELD_BODY_ONLY
    log_resp = client.get("/api/inbound/log").json()
    assert log_resp["n_held"] == 1
    assert log_resp["entries"][-1]["status"] == HELD_BODY_ONLY
    # body-only is NOT replayable (needs the round-2 body renderer)
    replay = replay_held(state.db_path, state.learning_db_path, state.data_root)
    assert replay["replayed"] == 0


def test_archive_preserves_raw_message(client):
    state = client.app.state
    raw = _mail(OUTSIDE, attachments=[], body="hello")
    process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    inbound = state.data_root / "inbound"
    arch_dirs = [p for p in inbound.iterdir() if p.is_dir()]
    assert len(arch_dirs) == 1
    assert (arch_dirs[0] / "message.eml").read_bytes() == raw
    meta = json.loads((arch_dirs[0] / "meta.json").read_text(encoding="utf-8"))
    assert meta["from"] == OUTSIDE
    assert meta["status"] == HELD_BODY_ONLY


# ---------------------------------------------------------- notifications --
# Acks + held alerts (graph_notify) are hard-disabled in tests (no Graph
# creds in the env); these tests patch the module seam and assert the
# decision logic + idempotency, never a real send.

def _patch_notify(monkeypatch):
    """Record (recipient, subject, body, allow_external) per send.

    The stub deliberately does NOT re-implement the recipient guard, so a
    test that cares whether an address may be mailed AT ALL has to assert
    against the real `graph_notify.send_mail` (see
    `test_an_outside_submitter_gets_no_acknowledgement`). What it does
    capture is the allowlist the caller passed, which is the other half of
    that decision.
    """
    from expense_recon.web import graph_notify
    calls: list[tuple[str, str, str, tuple]] = []
    monkeypatch.setattr(graph_notify, "enabled", lambda: True)
    monkeypatch.setattr(
        graph_notify, "send_mail",
        lambda r, s, b, **kw: calls.append(
            (r, s, b, tuple(kw.get("allow_external") or ()))
        ) or True,
    )
    return calls


def test_ingest_ack_goes_to_real_sender_once(client, monkeypatch):
    calls = _patch_notify(monkeypatch)
    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Uber"),
               _extraction(vendor="Uber"))
    raw = _mail(
        "dirk.neumann@brisken.com",
        to_addr=f"receipts+criss@{DOMAIN}",  # alias claims criss
        attachments=[("r.jpg", JPG + b"ack")],
    )
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED
    # The ack goes to the SENDER address, never the alias person.
    assert [c[0] for c in calls] == ["dirk.neumann@brisken.com"]
    assert calls[0][1].startswith("Receipt received")
    # ...and it NAMES where the receipt landed, so "received" can never be
    # read as "someone still has to file this".
    assert MONTH_LABEL in calls[0][2]
    # Idempotent per archive: the meta stamp blocks a second ack.
    from expense_recon.web.intake_mail import _maybe_ack, inbound_root
    _maybe_ack(state.db_path, inbound_root(state.data_root) / res["archive"])
    assert len(calls) == 1


def test_no_ack_for_auto_generated_or_disabled(client, monkeypatch):
    calls = _patch_notify(monkeypatch)
    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    # (a) an auto-generated inbound (OOF-style) ingests but is never acked
    _patch_ocr(monkeypatch, _extraction(vendor="OOF"),
               _extraction(vendor="OOF"))
    msg = EmailMessage()
    msg["From"] = "dirk.neumann@brisken.com"
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = "auto"
    msg["Auto-Submitted"] = "auto-replied"
    msg.set_content("x")
    msg.add_attachment(JPG + b"oof", maintype="image", subtype="jpeg",
                       filename="a.jpg")
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        msg.as_bytes(), synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED
    assert calls == []
    # (b) intake.auto_ack=false switches acks off for normal mail too
    resp = client.put("/api/settings", json={"intake": {"auto_ack": False}})
    assert resp.status_code == 200, resp.text
    _patch_ocr(monkeypatch, _extraction(vendor="DB"), _extraction(vendor="DB"))
    res2 = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("b.jpg", JPG + b"db")]),
        synchronous=True,
    )
    assert res2["status"] == STATUS_INGESTED
    assert calls == []


def test_held_mail_alerts_operator_once(client, monkeypatch):
    """Body-only mail from a STRANGER, deliberately: an attachment mail
    with no month open now pools, and pooling is not a problem to alert
    anyone about; a known sender's body-only mail renders itself. What is
    left needing a human is unrecognised mail we cannot read as a
    receipt."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[], body="Uber receipt inline"),
        synchronous=True,
    )
    assert res["status"] == HELD_BODY_ONLY
    assert [c[0] for c in calls] == ["matthias.silva@brisken.com"]
    assert HELD_BODY_ONLY in calls[0][1]
    # Idempotent per archive.
    from expense_recon.web.intake_mail import _maybe_alert, inbound_root
    _maybe_alert(
        state.db_path, inbound_root(state.data_root) / res["archive"],
        HELD_BODY_ONLY,
    )
    assert len(calls) == 1
    # Recipients follow settings intake.alert_recipients.
    resp = client.put("/api/settings", json={
        "intake": {"alert_recipients": ["dirk.neumann@brisken.com"]}
    })
    assert resp.status_code == 200, resp.text
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[], body="another one",
              subject="second"),
        synchronous=True,
    )
    assert calls[-1][0] == "dirk.neumann@brisken.com"


def test_pooled_mail_is_acked_with_its_month_and_not_acked_again(
    client, monkeypatch,
):
    """A sender whose receipt lands in the pool gets told so, in the same
    breath as which month it is waiting for and that nothing is expected
    of them. The claim must not ack a second time."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("dirk.neumann@brisken.com",
              attachments=[("r.jpg", JPG + b"pool-ack")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert [c[0] for c in calls] == ["dirk.neumann@brisken.com"]
    body = calls[0][2]
    assert MONTH_LABEL in body
    assert "automatically" in body

    _create_batch(client, monkeypatch, MONTH_LABEL, _extraction(vendor="X"))
    assert len(calls) == 1  # claimed, not re-acked


def test_send_mail_guards_refuse_external_and_malformed(monkeypatch):
    from expense_recon.web import graph_notify
    for k in ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
              "BRISKEN_GRAPH_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    # No creds -> disabled, even for an internal recipient.
    assert graph_notify.send_mail(
        "matthias.silva@brisken.com", "s", "b") is False
    # Creds present: every non-internal/malformed recipient is refused
    # BEFORE any network traffic (urlopen patched to explode).
    for k in ("BRISKEN_TENANT_ID", "BRISKEN_GRAPH_CLIENT_ID",
              "BRISKEN_GRAPH_CLIENT_SECRET"):
        monkeypatch.setenv(k, "test-cred")
    def _no_network(*a, **kw):
        raise AssertionError("guard let a refused recipient reach the network")
    monkeypatch.setattr(
        "expense_recon.web.graph_notify.urllib.request.urlopen", _no_network
    )
    for bad in (
        "victim@gmail.com",
        "victim@gmail.com,x@brisken.com",
        "a@b@brisken.com",
        "@brisken.com",
        "two words@brisken.com",
        "",
    ):
        assert graph_notify.send_mail(bad, "s", "b") is False
    # Listing an address does not buy it past the STRUCTURAL guard: a
    # smuggled second recipient stays refused even when the allowlist
    # matches it byte for byte.
    for bad in (
        "victim@gmail.com,x@brisken.com",
        "a@b@brisken.com",
        "listed@example.org\nbcc: victim@gmail.com",
        "",
    ):
        assert graph_notify.send_mail(
            bad, "s", "b", allow_external=(bad,)
        ) is False


def test_retention_sweep_deletes_only_expired(client):
    from datetime import datetime, timezone
    from expense_recon.web.intake_mail import inbound_root, sweep_retention
    state = client.app.state
    root = inbound_root(state.data_root)
    root.mkdir(parents=True, exist_ok=True)
    old = root / "20100101T000000-deadbeef"
    old.mkdir()
    (old / "meta.json").write_text("{}", encoding="utf-8")
    keep = root / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-cafecafe"
    )
    keep.mkdir()
    odd = root / "not-an-archive"
    odd.mkdir()
    removed = sweep_retention(state.db_path, state.data_root)
    assert removed == 1
    assert not old.exists() and keep.exists() and odd.exists()


def test_intake_settings_validate_ack_alerts_retention():
    ok = normalize_intake_setting({
        "auto_ack": False,
        "alert_recipients": ["Dirk.Neumann@brisken.com"],
        "retention_years": 10,
    })
    assert ok["auto_ack"] is False
    assert ok["alert_recipients"] == ["dirk.neumann@brisken.com"]
    assert ok["retention_years"] == 10
    with pytest.raises(ValueError):
        normalize_intake_setting({"auto_ack": "yes"})
    with pytest.raises(ValueError):
        normalize_intake_setting({"alert_recipients": ["x@gmail.com"]})
    with pytest.raises(ValueError):
        normalize_intake_setting({"retention_years": 0})


def test_inbound_log_detail_joins_created_expenses(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Trenitalia", total="89.00"),
        _extraction(vendor="Trenitalia", total="89.00"),
    )
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("train.jpg", JPG + b"tren")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED

    entries = client.get("/api/inbound/log?detail=1").json()["entries"]
    mine = [e for e in entries if e.get("subject") == "July taxi"]
    assert len(mine) == 1
    row = mine[0]
    assert row["batch_id"] == batch_id
    assert row.get("batch_label")
    assert len(row["expenses"]) == 1
    exp = row["expenses"][0]
    assert exp["vendor"] == "Trenitalia"
    assert exp["total"] == "89.00"
    doc_id = exp["document_id"]

    # A resend of the same bytes dedupes: ingested, zero rows created.
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("train.jpg", JPG + b"tren")],
              subject="resend"),
        synchronous=True,
    )
    entries = client.get("/api/inbound/log?detail=1").json()["entries"]
    resend = [e for e in entries if e.get("subject") == "resend"][0]
    assert resend["status"] == STATUS_INGESTED
    assert resend["expenses"] == []

    # Deleting the row keeps the mail's story honest: deleted flag, not
    # a vanished document.
    del_resp = client.delete(f"/api/runs/{batch_id}/expenses/{doc_id}")
    assert del_resp.status_code == 200, del_resp.text
    entries = client.get("/api/inbound/log?detail=1").json()["entries"]
    row = [e for e in entries if e.get("subject") == "July taxi"][0]
    assert row["expenses"] == [{"document_id": doc_id, "deleted": True}]


# ------------------------------------------- intake quick-wins (C1 + B) --

def test_inbound_log_lists_delivered_files(client, monkeypatch):
    """Note 3: the operator needs to see WHICH files a mail delivered.
    New mail records the sender's original names in meta; a legacy
    archive (no files key) derives sanitized names from parts/."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    # Two files: the arrival read extracts both, then the ingest does.
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber"), _extraction(vendor="Hotel"),
        _extraction(vendor="Uber"), _extraction(vendor="Hotel"),
    )
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[
            ("uber trip.jpg", JPG + b"u1"),
            ("hotel münchen.pdf", b"%PDF-1.4 " + JPG + b"h1"),
        ]),
        synchronous=True,
    )
    entries = client.get("/api/inbound/log").json()["entries"]
    row = entries[-1]
    assert row["files"] == ["uber trip.jpg", "hotel münchen.pdf"]

    # Legacy archive: strip the files key from meta -> derived from the
    # parts/ listing, NNN__ prefix stripped, sanitized names remain.
    arch = state.data_root / "inbound" / row["archive"]
    meta = json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    del meta["files"]
    (arch / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    entries = client.get("/api/inbound/log").json()["entries"]
    assert entries[-1]["files"] == ["uber_trip.jpg", "hotel_m_nchen.pdf"]


def test_inbound_log_month_column_everywhere(client, monkeypatch):
    """Note 13 ("month says no date"): the PLAIN log resolves batch_label
    for every routed row; held rows carry their held status instead."""
    state = client.app.state
    held = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[], body="inline receipt",
              subject="held one"),
        synchronous=True,
    )
    assert held["status"] == HELD_BODY_ONLY

    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    _patch_ocr(monkeypatch, _extraction(vendor="DB"), _extraction(vendor="DB"))
    ok = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("db.jpg", JPG + b"d1")],
              subject="routed one"),
        synchronous=True,
    )
    assert ok["status"] == STATUS_INGESTED

    entries = client.get("/api/inbound/log").json()["entries"]
    routed = [e for e in entries if e.get("subject") == "routed one"][0]
    assert routed["batch_id"] == batch_id
    assert routed.get("batch_label")  # pre-fix: absent outside ?detail=1
    assert routed["pool_month"] == RECEIPT_MONTH
    held_row = [e for e in entries if e.get("subject") == "held one"][0]
    assert held_row["status"] == HELD_BODY_ONLY
    assert "batch_label" not in held_row
    assert "batch_deleted" not in held_row


def test_delete_month_pools_its_mail_and_recreating_reclaims(
    client, monkeypatch,
):
    """Deleting a month returns its month-stamped mail to the POOL, and
    re-creating that month claims it back — the receipts are never
    stranded and never need the manual re-ingest path (which supersedes
    the item-19 ruling for month-stamped mail). Custody is untouched
    throughout: archives are never deleted."""
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"),
               _extraction(vendor="Trenitalia"))
    ok = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("tren.jpg", JPG + b"tr")],
              subject="into the month"),
        synchronous=True,
    )
    assert ok["status"] == STATUS_INGESTED

    with RunStore(state.db_path) as store:
        label = store.get_run(batch_id).label

    resp = client.post(
        f"/api/runs/{batch_id}/delete", json={"confirm": label}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted"] is True
    assert body["pooled_back"] == 1
    assert body["inbound_marked"] == 0  # nothing legacy to stamp
    assert body["learned_memory"] == "kept"

    # The mail is waiting again, not "month deleted".
    log = client.get("/api/inbound/log?detail=1").json()
    assert log["n_pooled"] == 1
    row = [e for e in log["entries"]
           if e.get("subject") == "into the month"][0]
    arch = state.data_root / "inbound" / row["archive"]
    assert (arch / "message.eml").exists()
    assert row["status"] == STATUS_POOLED
    assert not row.get("batch_deleted")
    assert row["pool_month"] == RECEIPT_MONTH
    assert row["pool_month_state"] == "no_batch"
    # The rows went with the month, and the row points at no batch — so
    # the detail join has nothing to attribute, which is the truth. The
    # pre-pool shape said "month deleted" about mail that is simply
    # waiting again.
    assert row["documents"] == []
    assert "expenses" not in row

    # Re-creating the month claims it back, with no operator action.
    second = _create_batch(
        client, monkeypatch, MONTH_LABEL, _extraction(vendor="Trenitalia"),
    )
    assert client.get("/api/inbound/log").json()["n_pooled"] == 0
    grid = client.get(f"/api/expense-batches/{second}").json()
    assert "Trenitalia" in [e["vendor"]["display"] for e in grid["expenses"]]


def test_delete_month_reports_next_open_batch(client, monkeypatch):
    first_id = _create_batch(client, monkeypatch)
    second_id = _create_batch(client, monkeypatch)
    resp = client.post(
        f"/api/runs/{second_id}/delete", json={"confirm": second_id}
    )
    assert resp.status_code == 200, resp.text
    with RunStore(client.app.state.db_path) as store:
        first_label = store.get_run(first_id).label or first_id
    assert resp.json()["next_open_batch"] == first_label


def test_failed_ingest_pools_back_when_its_month_is_deleted(
    client, monkeypatch,
):
    """A mail whose ingest failed carries a batch_id and a held_failed
    status. Deleting that month must return it to the pool like any other
    month-stamped mail, so re-creating the month retries it — rather than
    leaving it stamped "month deleted" forever (the stale-stamp bug of
    adversarial review 2026-08-21 finding 2, in its pool-era shape)."""
    import expense_recon.web.intake_mail as im

    first_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state

    # One extraction: the arrival read runs, then the INGEST blows up.
    _patch_ocr(monkeypatch, _extraction(vendor="Taxi"))

    def _boom(*a, **k):
        raise RuntimeError("simulated ingest failure")
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch", _boom)
        res = process_message(
            state.db_path, state.learning_db_path, state.data_root,
            _mail("criss@brisken.com", attachments=[("t.jpg", JPG + b"rp")],
                  subject="stamped mail"),
            synchronous=True,
        )
    assert res["status"] == "held_failed"

    resp = client.post(
        f"/api/runs/{first_id}/delete", json={"confirm": first_id}
    )
    assert resp.status_code == 200
    assert resp.json()["pooled_back"] == 1
    row = [e for e in client.get("/api/inbound/log").json()["entries"]
           if e.get("subject") == "stamped mail"][0]
    assert row["status"] == STATUS_POOLED
    assert not row.get("batch_deleted")

    second_id = _create_batch(
        client, monkeypatch, MONTH_LABEL, _extraction(vendor="Taxi"),
    )
    rows = [e for e in client.get("/api/inbound/log").json()["entries"]
            if e.get("subject") == "stamped mail"]
    assert rows[-1]["status"] == STATUS_INGESTED
    assert rows[-1]["batch_id"] == second_id
    assert not rows[-1].get("batch_deleted")
    assert rows[-1].get("batch_label") == MONTH_LABEL


def test_done_stamp_guard_flips_job_when_batch_vanishes(client, monkeypatch):
    """The delete/ingest ordering where the ingest wins the lock: the DONE
    stamp lands after the cascade purged jobs (run_id was NULL until
    then). The guard re-checks and flips the job to error + the mail to
    held_failed instead of leaving a done-job pointing at a gone run
    (adversarial review 2026-08-21 finding 4)."""
    import expense_recon.web.intake_mail as im
    from expense_recon.web.store import JOB_ERROR

    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state

    def _add_then_batch_vanishes(store, run, *a, **k):
        # Simulate the delete cascade landing right after our locked
        # write: by the time the DONE stamp runs, the run row is gone.
        store.delete_run(run.run_id)
        return {"documents": []}
    _patch_ocr(monkeypatch, _extraction(vendor="Taxi"))  # arrival read only
    monkeypatch.setattr(
        im, "add_receipts_to_expense_batch", _add_then_batch_vanishes
    )
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("t.jpg", JPG + b"gv")],
              subject="raced mail"),
        synchronous=True,
    )
    assert res["batch_id"] == batch_id
    with RunStore(state.db_path) as store:
        job = store.get_job(res["job_id"])
    assert job["status"] == JOB_ERROR
    assert job["error"] == "batch deleted"
    entries = client.get("/api/inbound/log").json()["entries"]
    row = [e for e in entries if e.get("subject") == "raced mail"][0]
    assert row["status"] == "held_failed"  # replayable into the next month


def test_ingest_refuses_deleted_batch(client, monkeypatch, tmp_path):
    """The delete/ingest race, resolved deny-by-default: a writer whose
    batch vanished while it waited on the lock refuses (the mail then
    goes held_failed and stays replayable) instead of reporting receipts
    ingested into a batch that no longer exists."""
    from expense_recon.web.service import (
        RunInputError,
        add_receipts_to_expense_batch,
    )

    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    with RunStore(state.db_path) as store:
        stale = store.get_run(batch_id)
        store.delete_run(batch_id)
        staging = tmp_path / "staging"
        staging.mkdir()
        with pytest.raises(RunInputError, match="no longer exists"):
            add_receipts_to_expense_batch(
                store, stale, staging, "2026-08-21T12:00:00+00:00"
            )


# --------------------------------------------- body-only handling (C2) --

def _html_mail(from_addr: str, subject: str = "Uber forward") -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = subject
    msg["Message-ID"] = "<html-test@brisken.com>"
    msg.set_content("Total: 27,90 € — Uber trip")
    msg.add_alternative(
        "<html><head><style>p{color:red}</style>"
        "<script>alert('x')</script></head><body>"
        "<p>Your Uber trip</p><table><tr><td>Total</td>"
        "<td>27,90&nbsp;&euro;</td></tr></table></body></html>",
        subtype="html",
    )
    return msg.as_bytes()


def test_body_view_returns_sanitized_text(client):
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE), synchronous=True,
    )
    assert res["status"] == HELD_BODY_ONLY
    entries = client.get("/api/inbound/log").json()["entries"]
    archive = entries[-1]["archive"]

    resp = client.get(f"/api/inbound/{archive}/body")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["subject"] == "Uber forward"
    assert "27,90" in body["text"]
    assert "<" not in body["text"] and "script" not in body["text"].lower()

    assert client.get("/api/inbound/nope/body").status_code == 404


def test_render_ingest_creates_expense_via_normal_path(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="render me"),
        synchronous=True,
    )
    assert res["status"] == HELD_BODY_ONLY
    entries = client.get("/api/inbound/log").json()["entries"]
    archive = [e for e in entries if e.get("subject") == "render me"][0]["archive"]

    # Two: the rendered PDF is read for its month, then ingested.
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.90", currency="EUR"),
        _extraction(vendor="Uber", total="27.90", currency="EUR"),
    )
    resp = client.post(f"/api/inbound/{archive}/render-ingest")
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["status"] == STATUS_INGESTED
    assert out["batch_id"] == batch_id
    assert out["pool_month"] == RECEIPT_MONTH
    assert len(out["documents"]) == 1

    # The rendered PDF lives at the archive ROOT (custody: parts/ stays
    # exactly what was delivered; the Files column never lists it).
    arch = state.data_root / "inbound" / archive
    assert (arch / "rendered-body.pdf").exists()
    assert not (arch / "parts").exists()
    meta = json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    assert meta["rendered"] is True
    assert meta["files"] == []

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1
    assert mailed[0]["submitted_by"]["address"] == OUTSIDE

    # Now ingested: a second render is refused (no double-charge path).
    again = client.post(f"/api/inbound/{archive}/render-ingest")
    assert again.status_code == 409


def test_render_ingest_guards(client, monkeypatch):
    state = client.app.state
    # No batch for the rendered receipt's month: the render still happens
    # and the result RESTS in the pool. It used to 409 and leave the
    # operator with nothing to show for the click.
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="no batch yet"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "no batch yet"
    ][0]["archive"]
    _patch_ocr(monkeypatch, _extraction())  # the rendered PDF's month
    resp = client.post(f"/api/inbound/{archive}/render-ingest")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == STATUS_POOLED
    assert resp.json()["pool_month"] == RECEIPT_MONTH
    assert client.get("/api/inbound/log").json()["n_pooled"] == 1

    # A mail with attachments (ingested) is never renderable.
    batch_id = _create_batch(
        client, monkeypatch, MONTH_LABEL, _extraction(vendor="Uber"),
    )
    _patch_ocr(monkeypatch, _extraction(vendor="DB"), _extraction(vendor="DB"))
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("db.jpg", JPG + b"c2")],
              subject="normal ingest"),
        synchronous=True,
    )
    ing = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "normal ingest"
    ][0]["archive"]
    assert client.post(f"/api/inbound/{ing}/render-ingest").status_code == 409
    assert client.post("/api/inbound/nope/render-ingest").status_code == 404
    assert batch_id  # silence unused warning


def test_dismiss_held_mail(client, monkeypatch):
    from expense_recon.web.intake_mail import STATUS_DISMISSED as DISMISSED

    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="junk forward"),
        synchronous=True,
    )
    log1 = client.get("/api/inbound/log").json()
    archive = [
        e for e in log1["entries"] if e.get("subject") == "junk forward"
    ][0]["archive"]
    assert log1["n_held"] == 1

    resp = client.post(f"/api/inbound/{archive}/dismiss")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == DISMISSED

    log2 = client.get("/api/inbound/log").json()
    assert log2["n_held"] == 0  # the held strip can reach zero now
    row = [e for e in log2["entries"] if e.get("subject") == "junk forward"][0]
    assert row["status"] == DISMISSED
    # Custody untouched; terminal: not replayable, not renderable.
    arch = state.data_root / "inbound" / archive
    assert (arch / "message.eml").exists()
    assert replay_held(
        state.db_path, state.learning_db_path, state.data_root
    )["replayed"] == 0
    assert client.post(f"/api/inbound/{archive}/render-ingest").status_code == 409

    # Only held or pooled mail can be dismissed; landed mail cannot.
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    _patch_ocr(monkeypatch, _extraction(vendor="DB"), _extraction(vendor="DB"))
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("db.jpg", JPG + b"dm")],
              subject="landed"),
        synchronous=True,
    )
    ing = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "landed"
    ][0]["archive"]
    assert client.post(f"/api/inbound/{ing}/dismiss").status_code == 409
    assert batch_id


def test_pooled_junk_can_be_dismissed(client, monkeypatch):
    """Junk that carries an attachment now RESTS in the pool rather than
    being held, so without widening the dismiss guard it would wait there
    forever with no way to clear it."""
    from expense_recon.web.intake_mail import STATUS_DISMISSED as DISMISSED

    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("spam@example.com", attachments=[("ad.jpg", JPG + b"junk")],
              subject="junk with a picture"),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert client.get("/api/inbound/log").json()["n_pooled"] == 1

    resp = client.post(f"/api/inbound/{res['archive']}/dismiss")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == DISMISSED
    assert client.get("/api/inbound/log").json()["n_pooled"] == 0

    # Terminal: opening its month must not resurrect it.
    _create_batch(client, monkeypatch, MONTH_LABEL)
    row = [e for e in client.get("/api/inbound/log").json()["entries"]
           if e["archive"] == res["archive"]][0]
    assert row["status"] == DISMISSED


def test_body_render_pdf_is_valid_pdf():
    pytest.importorskip("PIL")
    pypdf = pytest.importorskip("pypdf")
    from expense_recon.web.body_render import html_to_text, render_body_pdf

    text = html_to_text(
        "<div>Fare<script>x()</script></div><p>Total 12,50&nbsp;&euro;</p>"
        "<p>" + "verylongtokenwithoutspaces" * 20 + "</p>"
    )
    assert "x()" not in text and "Total 12,50" in text
    pdf = render_body_pdf(["From: a@b.com", "Subject: t"], text)
    reader = pypdf.PdfReader(__import__("io").BytesIO(pdf))
    assert len(reader.pages) >= 1


def test_render_ingest_retry_after_failure(client, monkeypatch):
    """A failed render ingest (held_failed) stays renderable: without the
    retry rule the mail would be stuck (replay flips a partless archive
    to held_no_valid_files, and the render guard would 409 forever)."""
    import expense_recon.web.intake_mail as im

    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="retry me"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "retry me"
    ][0]["archive"]

    def _boom(*a, **k):
        raise RuntimeError("vision transient")
    _patch_ocr(monkeypatch, _extraction())  # the rendered PDF's month
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch", _boom)
        first = client.post(f"/api/inbound/{archive}/render-ingest")
    assert first.status_code == 200  # render ran; the INGEST failed
    assert first.json()["status"] == "held_failed"

    # Replay drains held_failed but finds no parts/ -> held_no_valid_files.
    replay_held(state.db_path, state.learning_db_path, state.data_root)

    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.90"),
        _extraction(vendor="Uber", total="27.90"),
    )
    second = client.post(f"/api/inbound/{archive}/render-ingest")
    assert second.status_code == 200, second.text
    assert second.json()["status"] == STATUS_INGESTED


def test_render_pdf_bytes_deterministic():
    pytest.importorskip("PIL")
    import time as _time

    from expense_recon.web.body_render import render_body_pdf

    a = render_body_pdf(["From: x"], "Gebühr 27,90 €")
    _time.sleep(1.1)  # Pillow default stamps wall-clock into the PDF
    b = render_body_pdf(["From: x"], "Gebühr 27,90 €")
    assert a == b  # digest dedupe depends on byte-stable re-renders
    stamp = _time.gmtime(1_000_000)
    assert render_body_pdf(["h"], "t", created=stamp) == \
        render_body_pdf(["h"], "t", created=stamp)


def test_render_retry_after_commit_failure_does_not_duplicate(
    client, monkeypatch,
):
    """Finding 1: rows commit, then the job's tail fails -> held_failed.
    The retry re-renders the SAME bytes, dedupe eats them, and the month
    keeps exactly one row for the mail."""
    import expense_recon.web.intake_mail as im

    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="commit then fail"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "commit then fail"
    ][0]["archive"]

    def _ack_boom(*a, **k):
        raise RuntimeError("tail failure after commit")
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Uber", total="27.90"),
        _extraction(vendor="Uber", total="27.90"),
    )
    with monkeypatch.context() as mp:
        mp.setattr(im, "_maybe_ack", _ack_boom)
        first = client.post(f"/api/inbound/{archive}/render-ingest")
    assert first.status_code == 200
    assert first.json()["status"] == "held_failed"  # but the row committed

    # One: the re-render is read for its month again, and the ingest then
    # dedupes the identical bytes without extracting.
    _patch_ocr(monkeypatch, _extraction(vendor="Uber", total="27.90"))
    second = client.post(f"/api/inbound/{archive}/render-ingest")
    assert second.status_code == 200, second.text
    assert second.json()["status"] == STATUS_INGESTED
    assert second.json()["documents"] == []  # dedupe: no second row

    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1  # exactly one row for the mail, not two


def test_dismiss_refused_while_render_in_flight(client, monkeypatch):
    """Finding 2: the transient rendering status makes dismiss/render
    mutually exclusive — an acknowledged dismissal can no longer be
    silently reversed by a completing ingest."""
    import expense_recon.web.intake_mail as im
    from expense_recon.web.intake_mail import dismiss_archive

    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="race me"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "race me"
    ][0]["archive"]

    seen: dict = {}
    real_add = im.add_receipts_to_expense_batch

    def _add_with_midflight_dismiss(store, run, *a, **k):
        seen["dismiss"] = dismiss_archive(state.data_root, archive)
        return real_add(store, run, *a, **k)
    _patch_ocr(monkeypatch, _extraction(vendor="Uber"),
               _extraction(vendor="Uber"))
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch",
                   _add_with_midflight_dismiss)
        resp = client.post(f"/api/inbound/{archive}/render-ingest")
    assert resp.status_code == 200
    assert resp.json()["status"] == STATUS_INGESTED
    assert seen["dismiss"]["code"] == 409  # refused mid-flight, not queued


def test_replay_rescues_stranded_body_only(client, monkeypatch):
    """Finding 3: a body-only mail whose router died before classifying
    it (stale 'received', no parts/) replays into the RENDERABLE state,
    not the terminal held_no_valid_files."""
    from expense_recon.web.intake_mail import (
        archive_incoming,
        parse_inbound,
    )

    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    raw = _html_mail(OUTSIDE, subject="stranded")
    parsed = parse_inbound(raw, DOMAIN)
    arch = archive_incoming(state.data_root, raw, parsed)
    meta_path = arch / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["at"] = STALE_ARRIVAL  # past the stale threshold
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    replay_held(state.db_path, state.learning_db_path, state.data_root)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == HELD_BODY_ONLY

    _patch_ocr(monkeypatch, _extraction(vendor="Uber"),
               _extraction(vendor="Uber"))
    resp = client.post(f"/api/inbound/{arch.name}/render-ingest")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == STATUS_INGESTED


def test_reconcile_flips_interrupted_render(client):
    from expense_recon.web.intake_mail import (
        STATUS_RENDERING,
        archive_incoming,
        parse_inbound,
        reconcile_interrupted,
    )

    state = client.app.state
    raw = _html_mail(OUTSIDE, subject="killed mid-render")
    parsed = parse_inbound(raw, DOMAIN)
    arch = archive_incoming(state.data_root, raw, parsed)
    meta_path = arch / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({"status": STATUS_RENDERING, "rendered": True})
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    flipped = reconcile_interrupted(state.db_path, state.data_root)
    assert flipped == 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == "held_failed"
    assert meta["rendered"] is True  # stays retryable


# ── item 19: re-ingest mail stranded by a deleted month ─────────────


def _stranded_mail(client, monkeypatch, subject="stranded mail"):
    """A LEGACY mail whose attachments were INGESTED into a month that is
    then deleted. Its bytes survive in the custody archive; its expenses
    do not. Replay will not touch it (status `ingested` is not
    replayable), which is exactly the stranding item 19 is about.

    "Legacy" is load-bearing here: the month stamps are stripped from the
    meta before the delete, because month-stamped mail goes back to the
    POOL instead of stranding (2026-08-24). Only mail routed before the
    stamps existed still needs the manual re-ingest path this fixture
    feeds."""
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"),
               _extraction(vendor="Trenitalia"))
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("tren.jpg", JPG + b"i19")],
              subject=subject),
        synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED
    arch = state.data_root / "inbound" / res["archive"]
    meta = json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    for key in ("receipt_month", "receipt_month_source", "receipt_dates",
                "mixed_months"):
        meta.pop(key, None)
    (arch / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    resp = client.post(f"/api/runs/{batch_id}/delete", json={"confirm": batch_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["pooled_back"] == 0  # legacy: stamped, not pooled
    row = [e for e in client.get("/api/inbound/log").json()["entries"]
           if e.get("subject") == subject][0]
    assert row["batch_deleted"] is True
    return row["archive"]


def test_re_ingest_puts_stranded_attachments_into_the_open_month(client, monkeypatch):
    """The owner-approved fix: an explicit per-archive action that re-ingests
    the delivered attachments into the month that is open now. Replay cannot
    do it (it skips `ingested`), so before this the receipts were unreachable
    from the app even though the bytes were never deleted."""
    archive = _stranded_mail(client, monkeypatch)
    # Nothing to replay: this is the gap.
    assert client.post("/api/inbound/replay-held").json()["replayed"] == 0

    new_batch = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
    resp = client.post(f"/api/inbound/{archive}/re-ingest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["batch_id"] == new_batch
    assert body["documents"], body

    row = [e for e in client.get("/api/inbound/log").json()["entries"]
           if e["archive"] == archive][0]
    assert row["batch_id"] == new_batch
    assert not row.get("batch_deleted")  # the stamp is cleared
    # _create_batch seeds a receipt of its own, so the arrival is what
    # matters, not the batch being empty beforehand.
    grid = client.get(f"/api/expense-batches/{new_batch}").json()
    assert "Trenitalia" in [e["vendor"]["display"] for e in grid["expenses"]]


def test_re_ingest_refuses_mail_whose_month_still_exists(client, monkeypatch):
    """Deny-by-default: this action exists for stranding, not for copying a
    month's receipts into another month. A live batch keeps its mail."""
    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"),
               _extraction(vendor="Trenitalia"))
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("t.jpg", JPG + b"live")],
              subject="live mail"),
        synchronous=True,
    )
    archive = [e for e in client.get("/api/inbound/log").json()["entries"]
               if e.get("subject") == "live mail"][0]["archive"]

    resp = client.post(f"/api/inbound/{archive}/re-ingest")
    assert resp.status_code == 409, resp.text
    assert "still" in resp.json()["error"].lower()
    # And the batch it belongs to is untouched (its own seeded receipt
    # plus the mailed one, unchanged by the refusal).
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert len(grid["expenses"]) == 2


def test_re_ingest_without_an_open_month_says_so(client, monkeypatch):
    archive = _stranded_mail(client, monkeypatch, subject="no target")
    resp = client.post(f"/api/inbound/{archive}/re-ingest")
    assert resp.status_code == 409, resp.text
    assert "no open month" in resp.json()["error"].lower()


def test_re_ingest_twice_does_not_duplicate_the_receipts(client, monkeypatch):
    """A second click cannot double-add. The first call cleared the
    `batch_deleted` stamp, so the mail now belongs to a live month and the
    second hits the same refusal any live mail gets — a firmer guarantee than
    relying on byte-dedupe to absorb it."""
    archive = _stranded_mail(client, monkeypatch, subject="double click")
    new_batch = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
    assert client.post(f"/api/inbound/{archive}/re-ingest").status_code == 200
    before = len(client.get(f"/api/expense-batches/{new_batch}").json()["expenses"])

    second = client.post(f"/api/inbound/{archive}/re-ingest")
    assert second.status_code == 409, second.text
    assert "live month" in second.json()["error"]

    after = client.get(f"/api/expense-batches/{new_batch}").json()["expenses"]
    assert len(after) == before


def test_re_ingest_refuses_a_body_only_archive(client, monkeypatch):
    """Body-only mail has no delivered attachment to re-ingest; its path is
    render-ingest, and the error says so rather than silently doing nothing."""
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[], subject="body only",
              body="just text"),
        synchronous=True,
    )
    archive = [e for e in client.get("/api/inbound/log").json()["entries"]
               if e.get("subject") == "body only"][0]["archive"]
    resp = client.post(f"/api/inbound/{archive}/re-ingest")
    assert resp.status_code == 409, resp.text
    assert "attachment" in resp.json()["error"].lower()


# ── the month pool (owner directive 2026-08-24) ──────────────────────
# Mail is addressed by the receipt's PRINTED month, not by whichever
# batch happens to be open. These tests pin that decision, the resting
# place when the month is not open, and the pull that empties it.


def _wait_for(predicate, timeout: float = 5.0) -> bool:
    """Poll a claim that runs on a daemon thread. Claiming does vision, so
    the handlers that trigger it never block on it; the tests must."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_printed_date_beats_the_open_month(client, monkeypatch):
    """The regression this whole feature exists for. An open batch for a
    DIFFERENT month must not swallow the mail: Dirk's August receipts
    landed in the April 2026 batch exactly this way, because the router
    picked the newest statement-less batch and never read the receipt."""
    other = _create_batch(client, monkeypatch, _label_for(date.today()))
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())  # prints RECEIPT_MONTH
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"printed")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["pool_month"] == RECEIPT_MONTH
    assert res["receipt_month_source"] == "receipt"
    # The other month is untouched: only its own seed receipt.
    grid = client.get(f"/api/expense-batches/{other}").json()
    assert [e for e in grid["expenses"] if e.get("submitted_by")] == []


def test_an_unreadable_date_falls_back_to_the_arrival_month(
    client, monkeypatch,
):
    """No printed date is readable (a blurred photo, no LLM key): the mail
    files under the month it ARRIVED in, and says so."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(date=None))
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"blurred")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["pool_month"] == ARRIVAL_MONTH
    assert res["receipt_month_source"] == "arrival"


def test_an_implausible_printed_date_clamps_to_the_arrival_month(
    client, monkeypatch,
):
    """A date years before arrival is a misread, not a receipt from 2019
    (backlog item 25's YY-MM-DD slips read `26-04-22` as 2022-04-26). It
    counts as unreadable, and the source records that it was clamped
    rather than simply absent."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(date="2019-04-02"))
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"old")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["pool_month"] == ARRIVAL_MONTH
    assert res["receipt_month_source"] == "implausible-receipt"


def test_a_multi_month_mail_routes_by_its_earliest_date_and_says_so(
    client, monkeypatch,
):
    """One mail routes as ONE unit, so a mail spanning two months goes to
    the earlier of them. That is a real limitation, not a silent one: the
    row carries mixed_months so the operator can move what does not
    belong."""
    state = client.app.state
    older = RECEIPT_DAY.replace(day=1) - timedelta(days=5)
    _patch_ocr(
        monkeypatch,
        _extraction(date=RECEIPT_DAY.isoformat()),
        _extraction(date=older.isoformat()),
    )
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[
            ("a.jpg", JPG + b"m1"), ("b.jpg", JPG + b"m2"),
        ]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["pool_month"] == f"{older.year:04d}-{older.month:02d}"
    row = [e for e in client.get("/api/inbound/log").json()["entries"]
           if e["archive"] == res["archive"]][0]
    assert row["mixed_months"] is True


def test_resolve_receipt_month_boundaries():
    """The clamp's own edges, without the cost of a round trip: one day
    into the future is timezone skew and stays readable; two days is a
    wrong year. A receipt just under a year old is still readable."""
    arrival = "2026-08-24T09:00:00+00:00"
    assert resolve_receipt_month(["2026-08-25"], arrival)[:2] == \
        ("2026-08", "receipt")
    assert resolve_receipt_month(["2026-08-26"], arrival)[1] == \
        "implausible-receipt"
    assert resolve_receipt_month(["2025-08-23"], arrival)[:2] == \
        ("2025-08", "receipt")
    assert resolve_receipt_month(["2025-08-22"], arrival)[1] == \
        "implausible-receipt"
    # Junk parses as no date at all, which is "arrival", not a crash.
    assert resolve_receipt_month(["not-a-date"], arrival)[1] == "arrival"
    # The earliest PLAUSIBLE date wins, and an unreadable sibling neither
    # wins nor makes the mail count as mixed.
    assert resolve_receipt_month(
        ["2026-08-10", "2026-07-30", "2019-01-01"], arrival
    ) == ("2026-07", "receipt", True)


def test_a_month_less_label_never_claims_and_the_response_says_so(
    client, monkeypatch,
):
    """The DEFAULT batch label is a full date, which is a timestamp and
    not a month. Such a batch can never receive mailed receipts, so
    creation says so, and renaming into a month is the fix path."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"nolabel")]),
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED

    _patch_ocr(monkeypatch, _extraction())
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["month"] is None
    assert "does not name a month" in body["advisory"]
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    # Still waiting: an unnamed month is not a claim target.
    assert client.get("/api/inbound/log").json()["n_pooled"] == 1


def test_renaming_a_batch_into_a_month_claims_its_pool(client, monkeypatch):
    """The fix path for the advisory above, and for a mis-typed month."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"rename")]),
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED
    batch_id = _create_batch(client, monkeypatch)  # month-less label
    assert client.get("/api/inbound/log").json()["n_pooled"] == 1

    _patch_ocr(monkeypatch, _extraction(vendor="Renamed"))
    resp = client.post(f"/api/runs/{batch_id}/rename",
                       json={"label": MONTH_LABEL})
    assert resp.status_code == 200, resp.text
    assert resp.json()["month"] == RECEIPT_MONTH
    assert _wait_for(
        lambda: client.get("/api/inbound/log").json()["n_pooled"] == 0
    ), client.get("/api/inbound/log").json()
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert [e for e in grid["expenses"] if e.get("submitted_by")]


def test_startup_sweep_claims_mail_pooled_while_the_machine_slept(
    client, monkeypatch,
):
    """Scale-to-zero: a month can be created, and mail can arrive, in
    different lifetimes of the process. Boot reconciles them."""
    from expense_recon.web.intake_mail import _update_meta, inbound_root

    state = client.app.state
    data_root = state.data_root
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"boot")]),
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED
    _create_batch(client, monkeypatch, MONTH_LABEL, _extraction(vendor="Boot"))
    # Put it back in the pool: the mail arrived while the machine was
    # down, so nothing claimed it at create time.
    arch = inbound_root(data_root) / pooled["archive"]
    _update_meta(arch, {"status": STATUS_POOLED, "batch_id": "",
                        "documents": []})

    _patch_ocr(monkeypatch, _extraction(vendor="Boot"))
    with TestClient(create_app(data_root)) as booted:
        assert _wait_for(
            lambda: booted.get("/api/inbound/log").json()["n_pooled"] == 0
        ), booted.get("/api/inbound/log").json()


def test_startup_sweep_starts_nothing_when_the_pool_is_empty(tmp_path):
    """The pre-scan, so a boot with no waiting mail neither reads the
    store nor spins up a vision-capable thread."""
    from expense_recon.web.intake_mail import has_pooled_mail

    assert has_pooled_mail(tmp_path) is False


def test_a_batch_created_mid_arrival_ingests_exactly_once(
    client, monkeypatch,
):
    """The race the pool lock exists for: the month opens between "is
    there a batch for this month?" and the status write. The receipt must
    land once, and never both land AND wait."""
    import expense_recon.web.intake_mail as im
    from expense_recon.web.service import (
        create_expense_batch,
        execute_expense_batch,
    )

    state = client.app.state
    real_resolve = im._open_batch_for_month
    made: dict = {}

    def _create_month_then_resolve(store, ym):
        # Fires INSIDE the pool lock, standing in for another request
        # creating the month at the worst possible instant. Service-level
        # on purpose: a nested TestClient call here would deadlock on the
        # very lock under test.
        if not made:
            with RunStore(state.db_path) as s2:
                prepared = create_expense_batch(
                    state.data_root, files=[("seed.jpg", JPG)],
                    legal_entity="Corporate Services", default_currency="",
                    label=MONTH_LABEL, now_iso="2026-08-24T00:00:00+00:00",
                    operator="test",
                    learning_db_path=state.learning_db_path,
                    settings=s2.get_settings(),
                )
                made["id"] = execute_expense_batch(s2, prepared)
        return real_resolve(store, ym)

    _patch_ocr(
        monkeypatch,
        _extraction(),                    # the arrival read
        _extraction(vendor="Seed"),       # the mid-flight batch's seed
        _extraction(vendor="Raced"),      # the ingest
    )
    monkeypatch.setattr(im, "_open_batch_for_month", _create_month_then_resolve)
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"raced")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED
    assert res["batch_id"] == made["id"]
    assert client.get("/api/inbound/log").json()["n_pooled"] == 0
    grid = client.get(f"/api/expense-batches/{made['id']}").json()
    assert len([e for e in grid["expenses"] if e.get("submitted_by")]) == 1


def test_a_second_router_stands_down(client, monkeypatch):
    """Status is the arbiter: only one router can move an archive out of
    `received`, so a redelivery or a replay racing the router cannot
    double-ingest the same mail."""
    from expense_recon.web.intake_mail import (
        STATUS_ROUTING,
        _update_meta,
        archive_incoming,
        parse_inbound,
        route_archived,
    )

    _create_batch(client, monkeypatch, MONTH_LABEL)
    state = client.app.state
    raw = _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"cas")])
    parsed = parse_inbound(raw, DOMAIN)
    arch = archive_incoming(state.data_root, raw, parsed)
    _update_meta(arch, {"status": STATUS_ROUTING})  # a router already has it

    _patch_ocr(monkeypatch, _extraction(), _extraction())
    res = route_archived(
        state.db_path, state.learning_db_path, state.data_root, arch,
        parsed, synchronous=True,
    )
    assert res["skipped"] == "already routed"
    assert res["status"] == STATUS_ROUTING
    # Nothing ingested, nothing pooled: the second router did nothing.
    assert client.get("/api/inbound/log").json()["n_pooled"] == 0


def test_a_failed_claim_returns_to_the_pool_and_retries(client, monkeypatch):
    """The pool is the truthful resting place for a receipt whose month
    exists: a claim that blows up must leave it waiting (with the error
    recorded), not held, so the next trigger simply tries again."""
    import expense_recon.web.intake_mail as im

    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com",
              attachments=[("r.jpg", JPG + b"claimfail")]),
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED

    def _boom(*a, **k):
        raise RuntimeError("transient vision failure")
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch", _boom)
        batch_id = _create_batch(client, monkeypatch, MONTH_LABEL)
    log = client.get("/api/inbound/log").json()
    assert log["n_pooled"] == 1  # back to waiting, not held
    row = [e for e in log["entries"] if e["archive"] == pooled["archive"]][0]
    assert row["status"] == STATUS_POOLED
    assert row["pool_month_state"] == "open"  # month IS open; retry pending
    assert "transient" in row["error"]

    # The next trigger drains it.
    _patch_ocr(monkeypatch, _extraction(vendor="Retried"))
    drain = client.post("/api/inbound/replay-held").json()
    assert drain["claimed"] == 1
    assert client.get("/api/inbound/log").json()["n_pooled"] == 0
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    assert [e for e in grid["expenses"] if e.get("submitted_by")]


def test_reconcile_flips_interrupted_routing_and_claiming(client):
    """A kill mid-route and a kill mid-claim end up in different places,
    because they mean different things: a half-routed mail never reached
    a resting place (hold it, alert), a half-claimed one already had one
    (put it back in the pool, quietly)."""
    from expense_recon.web.intake_mail import (
        STATUS_CLAIMING,
        STATUS_ROUTING,
        _update_meta,
        archive_incoming,
        parse_inbound,
        reconcile_interrupted,
    )

    state = client.app.state
    made = {}
    for status in (STATUS_ROUTING, STATUS_CLAIMING):
        raw = _mail("criss@brisken.com",
                    attachments=[("r.jpg", JPG + status.encode())],
                    subject=status)
        arch = archive_incoming(state.data_root, raw,
                                parse_inbound(raw, DOMAIN))
        _update_meta(arch, {"status": status, "receipt_month": RECEIPT_MONTH,
                            "batch_id": "gone-run"})
        made[status] = arch

    assert reconcile_interrupted(state.db_path, state.data_root) == 2
    routing = json.loads(
        (made[STATUS_ROUTING] / "meta.json").read_text(encoding="utf-8")
    )
    assert routing["status"] == "held_failed"
    assert routing["error"] == "routing interrupted"
    claiming = json.loads(
        (made[STATUS_CLAIMING] / "meta.json").read_text(encoding="utf-8")
    )
    assert claiming["status"] == STATUS_POOLED
    assert claiming["batch_id"] == ""


def test_inbound_log_reports_the_pool_state_per_month(client, monkeypatch):
    """The Month column's three answers for waiting mail: no batch yet, a
    batch is open (a claim is imminent), and the month is already
    reconciled."""
    from expense_recon.web.intake_mail import _update_meta, inbound_root

    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"state")]),
        synchronous=True,
    )
    arch = inbound_root(state.data_root) / pooled["archive"]

    def _state() -> str:
        rows = client.get("/api/inbound/log").json()["entries"]
        return [r for r in rows
                if r["archive"] == pooled["archive"]][0]["pool_month_state"]

    assert _state() == "no_batch"

    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL,
                             _extraction(vendor="Claimed"))
    _update_meta(arch, {"status": STATUS_POOLED, "batch_id": ""})
    assert _state() == "open"

    # A statement makes the month closed to new mail (PR 2 lifts this),
    # and a claim into it correctly declines.
    with RunStore(state.db_path) as store:
        snapshot = dict(store.get_run(batch_id).snapshot or {})
        snapshot["transactions"] = [{"transaction_id": "x"}]
        assert store.update_run_snapshot(batch_id, snapshot)
    assert _state() == "closed"
    assert claim_pooled(
        state.db_path, state.learning_db_path, state.data_root
    )["still_pooled"] == 1


def test_arrival_extraction_warms_the_batch_cache(tmp_path, monkeypatch):
    """The economics of reading every receipt at arrival: it must cost
    NOTHING extra. The extraction cache is content-addressed and salted
    with the run's card list, and the arrival client composes that list
    the same way a batch config does; so the batch ingest of the same
    bytes is a cache hit. One model call for one mailed receipt, total.

    Unlike the rest of this file this drives the REAL client build path
    (`cli._build_llm_client`) over a real on-disk cache, with only the
    OpenAI transport faked."""
    import openai

    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv(
        "EXPENSE_RECON_EXTRACTION_CACHE", str(tmp_path / "cache.sqlite")
    )
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)

    # Each entry fingerprints the WHOLE request (model + messages), so the
    # assertion below can say the exact call the arrival read made was
    # never made a second time — rather than counting calls and hoping.
    calls: list[tuple[str, str]] = []
    payload = json.dumps({
        "date": RECEIPT_DAY.isoformat(), "total": "42.50", "currency": "USD",
        "vendor": "Staples", "reference": None, "line_items": [],
        "confidence": 0.9, "notes": "",
    })

    class _Completions:
        def create(self, **kwargs):
            body = json.dumps(kwargs.get("messages"), default=str,
                              sort_keys=True)
            calls.append((
                str(kwargs.get("model", "")),
                hashlib.sha1(body.encode()).hexdigest(),
            ))
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content=payload)
                )],
                usage=SimpleNamespace(
                    prompt_tokens=10, completion_tokens=5, total_tokens=15,
                ),
            )

    class _FakeOpenAI:
        def __init__(self, *a, **k):
            self.chat = SimpleNamespace(completions=_Completions())

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)

    with TestClient(create_app(tmp_path / "data")) as c:
        state = c.app.state
        res = process_message(
            state.db_path, state.learning_db_path, state.data_root,
            _mail("criss@brisken.com",
                  attachments=[("cached.jpg", JPG + b"cache-me")]),
            synchronous=True,
        )
        assert res["status"] == STATUS_POOLED
        assert res["pool_month"] == RECEIPT_MONTH
        assert len(calls) == 1, calls
        arrival_call = calls[0]

        resp = c.post(
            "/api/expense-batches",
            files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
            data={"legal_entity": "Corporate Services",
                  "label": MONTH_LABEL},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert c.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
        assert c.get("/api/inbound/log").json()["n_pooled"] == 0

        # THE assertion: the mailed image was read exactly once, ever.
        # The ingest asked the cache the identical question and was
        # answered from disk. (The batch's own seed is a different image
        # and pays its own vision call; the categorizer pays more still.
        # Neither is what this test is about.)
        assert calls.count(arrival_call) == 1, calls
        grid = c.get(f"/api/expense-batches/{body['batch_id']}").json()
        assert len([e for e in grid["expenses"] if e.get("submitted_by")]) == 1


def test_a_rendered_body_ack_does_not_claim_zero_files(client, monkeypatch):
    """A body-only mail delivers no attachment, so `n_files` is 0. The ack
    for it has to name the email rather than count files, or it reads
    "0 file(s) from your email ... is stored for July 2026" about work
    that really did happen.

    The sender is known, so the render is the arrival path's own and this
    ack is the FIRST thing they hear about the mail; there is no operator
    alert beside it any more."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())  # the rendered PDF's month
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("dirk.neumann@brisken.com", subject="inline receipt"),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED

    assert [c[0] for c in calls] == ["dirk.neumann@brisken.com"]
    body = calls[0][2]
    assert "0 file(s)" not in body
    assert body.startswith("Your email")
    assert MONTH_LABEL in body


def test_the_pool_count_counts_mails_not_log_rows(client, monkeypatch):
    """A claimed mail gets a SECOND log row (acceptance, then the claim).
    When its month is later deleted it goes back to the pool as ONE
    waiting mail, and the badge has to say 1. The live drill on 2026-08-24
    read 2 for one receipt, which sends the operator hunting for a mail
    that does not exist."""
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    pooled = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("r.jpg", JPG + b"count")]),
        synchronous=True,
    )
    assert pooled["status"] == STATUS_POOLED
    assert client.get("/api/inbound/log").json()["n_pooled"] == 1

    batch_id = _create_batch(client, monkeypatch, MONTH_LABEL,
                             _extraction(vendor="Counted"))
    entries = client.get("/api/inbound/log").json()["entries"]
    mine = [e for e in entries if e["archive"] == pooled["archive"]]
    assert len(mine) == 2, "the claim appends its own row"

    with RunStore(state.db_path) as store:
        label = store.get_run(batch_id).label
    resp = client.post(f"/api/runs/{batch_id}/delete", json={"confirm": label})
    assert resp.status_code == 200, resp.text
    assert resp.json()["pooled_back"] == 1

    log = client.get("/api/inbound/log").json()
    assert len([e for e in log["entries"]
                if e["archive"] == pooled["archive"]]) == 2
    assert log["n_pooled"] == 1  # one mail, two rows


# ------------------------------------------- who we recognise (item 30) --
# Anyone may submit; who we RECOGNISE is the narrower question, and two
# things hang off it: the acceptance ack reaches a listed outside address,
# and a known sender's body-only mail is read on arrival instead of
# waiting for a click.

def test_a_listed_private_address_gets_the_ack(client, monkeypatch):
    """Dirk mails receipts from a private iCloud address as well as his
    work one. Until an operator could list it, that send produced no ack
    and no bounce either, so a delivered receipt and a lost one looked
    identical from his chair. That is the question that took a whole
    session to answer on 2026-08-24."""
    calls = _patch_notify(monkeypatch)
    private = "dirk_.neumann@icloud.com"
    resp = client.put("/api/settings", json={
        "intake": {"known_senders": [private.upper()]}
    })
    assert resp.status_code == 200, resp.text
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(private, attachments=[("r.jpg", JPG + b"listed")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert [c[0] for c in calls] == [private]
    # The allowlist reached the sender, which is the only thing that lets
    # the real guard mail an address outside the tenant.
    assert private in calls[0][3]


def test_an_unlisted_outside_submitter_is_not_acked(client, monkeypatch):
    """The list is narrow on purpose. A stranger's mail is still taken
    into custody and still routed; what they do not get is a reply from
    Brisken to an address nobody vouched for."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(OUTSIDE, attachments=[("r.jpg", JPG + b"unlisted")]),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    # _maybe_ack still runs; the empty allowlist is what stops it, and the
    # real send_mail refuses the recipient (pinned in the guard test).
    assert [c[3] for c in calls] == [()]


def test_known_senders_settings_validation():
    from expense_recon.web.intake_mail import MAX_KNOWN_SENDERS

    ok = normalize_intake_setting({"known_senders": [
        "Dirk_.Neumann@icloud.com", "dirk_.neumann@icloud.com",
    ]})
    assert ok["known_senders"] == ["dirk_.neumann@icloud.com"]
    for bad in (
        {"known_senders": "dirk@icloud.com"},          # not a list
        {"known_senders": ["not-an-address"]},
        {"known_senders": ["a@b.com,c@d.com"]},        # two smuggled as one
        {"known_senders": ["a@b.com\nbcc: x@y.com"]},  # header injection
        {"known_senders": ["a@nodot"]},
        {"known_senders": [f"a{i}@b.com"
                           for i in range(MAX_KNOWN_SENDERS + 1)]},
    ):
        with pytest.raises(ValueError):
            normalize_intake_setting(bad)


def test_a_malformed_known_sender_in_stored_settings_is_ignored():
    """The PUT edge refuses a bad list. A settings blob edited around it
    has to degrade to "not known", never take the mailbox down."""
    cfg = IntakeConfig.from_settings({"intake": {"known_senders": [
        "dirk_.neumann@icloud.com", "oops", "x@y.com,z@q.com", 7,
    ]}})
    assert cfg.known_senders == ("dirk_.neumann@icloud.com",)
    assert is_known_sender("Dirk_.Neumann@icloud.com", cfg)
    assert is_known_sender("anyone@brisken.com", cfg)
    assert not is_known_sender("oops", cfg)
    assert not is_known_sender("stranger@example.org", cfg)
    # A look-alike domain must not read as internal.
    assert not is_known_sender("attacker@evil-brisken.com", cfg)


def test_a_known_senders_body_only_mail_renders_itself(client, monkeypatch):
    """A forwarded vendor receipt IS the email body far more often than it
    is an attachment: all six mails held on 2026-08-24 (AWS, OpenAI twice,
    OpenAI credits, the CIC ticket, Hostinger) delivered no file at all.
    Holding each of them for a click is what made a receipt that HAD
    arrived read as an error."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())  # the rendered PDF's month
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("dirk.neumann@brisken.com", subject="forwarded receipt"),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["auto_rendered"] is True
    assert res["pool_month"] == RECEIPT_MONTH
    arch = state.data_root / "inbound" / res["archive"]
    assert (arch / "rendered-body.pdf").exists()
    meta = json.loads((arch / "meta.json").read_text(encoding="utf-8"))
    assert meta["rendered"] is True and meta["rendered_by"] == "auto"
    # Nobody is asked to click anything, and the sender is told where it
    # went rather than nothing at all.
    assert client.get("/api/inbound/log").json()["n_held"] == 0
    assert [c[0] for c in calls] == ["dirk.neumann@brisken.com"]


def test_a_listed_senders_body_only_mail_renders_itself(client, monkeypatch):
    """One list, both halves: an address an operator listed is known for
    the render decision too, so Dirk forwarding from his private mailbox
    behaves exactly like Dirk forwarding from his work one."""
    private = "dirk_.neumann@icloud.com"
    assert client.put("/api/settings", json={
        "intake": {"known_senders": [private]}
    }).status_code == 200
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction())
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(private, subject="private forward"),
        synchronous=True,
    )
    assert res["status"] == STATUS_POOLED
    assert res["auto_rendered"] is True


def test_a_strangers_body_only_mail_still_waits_for_a_click(
    client, monkeypatch,
):
    """The gate is on the RENDER, not on the submission: anyone may still
    mail us, but we do not pay a vision call to read every stranger's
    newsletter. An unrecognised body-only mail stays held, and alerts."""
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail(OUTSIDE, subject="stranger forward"),
        synchronous=True,
    )
    assert res["status"] == HELD_BODY_ONLY
    assert "auto_rendered" not in res
    arch = state.data_root / "inbound" / res["archive"]
    assert not (arch / "rendered-body.pdf").exists()
    assert [c[0] for c in calls] == ["matthias.silva@brisken.com"]


def test_a_failed_auto_render_alerts_the_operator(client, monkeypatch):
    """Nobody is watching an automatic render. Without this alert an
    arrival that rendered and then failed to ingest would sit in
    held_failed with the sender told nothing and the operator told
    nothing, which is the exact silence this round exists to remove."""
    import expense_recon.web.intake_mail as im

    _create_batch(client, monkeypatch, MONTH_LABEL)
    calls = _patch_notify(monkeypatch)
    state = client.app.state

    def _boom(*a, **k):
        raise RuntimeError("vision transient")

    _patch_ocr(monkeypatch, _extraction())  # the rendered PDF's month
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch", _boom)
        res = process_message(
            state.db_path, state.learning_db_path, state.data_root,
            _html_mail("dirk.neumann@brisken.com", subject="fails to ingest"),
            synchronous=True,
        )
    assert res["status"] == HELD_FAILED
    assert [c[0] for c in calls] == ["matthias.silva@brisken.com"]
    assert HELD_FAILED in calls[0][1]
