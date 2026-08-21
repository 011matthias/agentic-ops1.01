"""Mail intake (the app's own mailbox): parse -> allowlist -> archive ->
route into the open expense batch with per-file submitter provenance.
Decision logic is pure/sync; the SMTP transport is exercised through its
decision functions, never a real socket. See web/intake_mail.py +
web/smtp_server.py."""
from __future__ import annotations

import json
from email.message import EmailMessage

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    HELD_BODY_ONLY,
    HELD_NO_BATCH,
    HELD_NO_VALID_FILES,
    STATUS_INGESTED,
    DayBudget,
    IntakeConfig,
    normalize_intake_setting,
    parse_inbound,
    process_message,
    read_log,
    replay_held,
    resolve_person,
    sender_allowed,
)
from expense_recon.web.smtp_server import rcpt_decision, sender_decision  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000  # big enough to not read as a logo
DOMAIN = "expenses.brisken.com"


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
        date="2026-07-01", total="42.50", currency="USD", vendor="Staples",
        reference="", line_items=(), confidence=0.9, notes="",
    )
    base.update(overrides)
    return ExtractedReceipt(**base)


def _patch_ocr(monkeypatch, *extractions: ExtractedReceipt) -> None:
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, monkeypatch) -> str:
    _patch_ocr(monkeypatch, _extraction())
    resp = client.post(
        "/api/expense-batches",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
        data={"legal_entity": "Corporate Services"},
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


# ------------------------------------------------------------- allowlist --

def test_sender_allowlist_domain_and_exact():
    allow = ("@brisken.com", "assistant@gmail.com")
    assert sender_allowed("dirk.neumann@brisken.com", allow)
    assert sender_allowed("ASSISTANT@GMAIL.COM".lower(), allow)
    assert not sender_allowed("evil@gmail.com", allow)
    assert not sender_allowed("", allow)
    assert not sender_allowed("brisken.com", allow)


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


def test_sender_decision_envelope_and_header_must_both_pass():
    cfg = IntakeConfig()
    ok = sender_decision(
        "dirk.neumann@brisken.com", "dirk.neumann@brisken.com", cfg
    )
    assert ok is None
    # envelope passes but header sender does not -> refused
    spoofed = sender_decision(
        "dirk.neumann@brisken.com", "evil@gmail.com", cfg
    )
    assert spoofed.startswith("550")


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


def test_intake_settings_reject_matchless_sender_entry():
    with pytest.raises(ValueError):
        normalize_intake_setting({"senders": ["brisken.com"]})
    ok = normalize_intake_setting(
        {"senders": ["@brisken.com", "helper@gmail.com"]}
    )
    assert ok["senders"] == ["@brisken.com", "helper@gmail.com"]


# ---------------------------------------------------------- end to end --

def test_mail_lands_in_open_batch_with_provenance(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    # alias map: mail to receipts+dirk@ books to Dirk by name
    with_settings = client.put(
        "/api/settings",
        json={"intake": {"aliases": {"dirk": "Dirk Neumann"}}},
    )
    assert with_settings.status_code == 200, with_settings.text

    _patch_ocr(monkeypatch, _extraction(vendor="Uber", total="27.63"))
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
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    payload = JPG + b"same-bytes"
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
    first = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("a@brisken.com", attachments=[("db.jpg", payload)]),
        synchronous=True,
    )
    assert first["status"] == STATUS_INGESTED
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


def test_no_open_batch_holds_then_replays(client, monkeypatch):
    state = client.app.state
    raw = _mail(
        "criss@brisken.com", attachments=[("taxi.jpg", JPG + b"taxi")]
    )
    held = process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    assert held["status"] == HELD_NO_BATCH

    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="Taxi Roma"))
    resp = client.post("/api/inbound/replay-held")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["replayed"] == 1
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    mailed = [e for e in grid["expenses"] if e.get("submitted_by")]
    assert len(mailed) == 1
    assert mailed[0]["submitted_by"]["address"] == "criss@brisken.com"
    # a second replay finds nothing held
    again = client.post("/api/inbound/replay-held").json()
    assert again["replayed"] == 0


def test_body_only_mail_is_held_not_dropped(client):
    state = client.app.state
    result = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[], body="Uber receipt inline"),
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
    raw = _mail("criss@brisken.com", attachments=[], body="hello")
    process_message(
        state.db_path, state.learning_db_path, state.data_root, raw,
        synchronous=True,
    )
    inbound = state.data_root / "inbound"
    arch_dirs = [p for p in inbound.iterdir() if p.is_dir()]
    assert len(arch_dirs) == 1
    assert (arch_dirs[0] / "message.eml").read_bytes() == raw
    meta = json.loads((arch_dirs[0] / "meta.json").read_text(encoding="utf-8"))
    assert meta["from"] == "criss@brisken.com"
    assert meta["status"] == HELD_BODY_ONLY


# ---------------------------------------------------------- notifications --
# Acks + held alerts (graph_notify) are hard-disabled in tests (no Graph
# creds in the env); these tests patch the module seam and assert the
# decision logic + idempotency, never a real send.

def _patch_notify(monkeypatch):
    from expense_recon.web import graph_notify
    calls: list[tuple[str, str, str]] = []
    monkeypatch.setattr(graph_notify, "enabled", lambda: True)
    monkeypatch.setattr(
        graph_notify, "send_mail",
        lambda r, s, b: calls.append((r, s, b)) or True,
    )
    return calls


def test_ingest_ack_goes_to_real_sender_once(client, monkeypatch):
    calls = _patch_notify(monkeypatch)
    _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Uber"))
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
    # Idempotent per archive: the meta stamp blocks a second ack.
    from expense_recon.web.intake_mail import _maybe_ack, inbound_root
    _maybe_ack(state.db_path, inbound_root(state.data_root) / res["archive"])
    assert len(calls) == 1


def test_no_ack_for_auto_generated_or_disabled(client, monkeypatch):
    calls = _patch_notify(monkeypatch)
    _create_batch(client, monkeypatch)
    state = client.app.state
    # (a) an auto-generated inbound (OOF-style) ingests but is never acked
    _patch_ocr(monkeypatch, _extraction(vendor="OOF"))
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
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
    res2 = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("b.jpg", JPG + b"db")]),
        synchronous=True,
    )
    assert res2["status"] == STATUS_INGESTED
    assert calls == []


def test_held_mail_alerts_operator_once(client, monkeypatch):
    calls = _patch_notify(monkeypatch)
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("t.jpg", JPG + b"t")]),
        synchronous=True,
    )
    assert res["status"] == HELD_NO_BATCH
    assert [c[0] for c in calls] == ["matthias.silva@brisken.com"]
    assert "held_no_batch" in calls[0][1]
    # Idempotent per archive.
    from expense_recon.web.intake_mail import _maybe_alert, inbound_root
    _maybe_alert(
        state.db_path, inbound_root(state.data_root) / res["archive"],
        HELD_NO_BATCH,
    )
    assert len(calls) == 1
    # Recipients follow settings intake.alert_recipients.
    resp = client.put("/api/settings", json={
        "intake": {"alert_recipients": ["dirk.neumann@brisken.com"]}
    })
    assert resp.status_code == 200, resp.text
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("u.jpg", JPG + b"u")],
              subject="second"),
        synchronous=True,
    )
    assert calls[-1][0] == "dirk.neumann@brisken.com"


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
