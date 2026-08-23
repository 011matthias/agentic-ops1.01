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
from expense_recon.web.store import RunStore  # noqa: E402

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


def test_inbound_log_detail_joins_created_expenses(client, monkeypatch):
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia", total="89.00"))
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
    _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(
        monkeypatch,
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
        _mail("criss@brisken.com", attachments=[("t.jpg", JPG + b"t1")],
              subject="held one"),
        synchronous=True,
    )
    assert held["status"] == HELD_NO_BATCH

    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
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
    held_row = [e for e in entries if e.get("subject") == "held one"][0]
    assert held_row["status"] == HELD_NO_BATCH
    assert "batch_label" not in held_row
    assert "batch_deleted" not in held_row


def test_delete_month_stamps_inbound_and_reports_routing(client, monkeypatch):
    """Note 2 (delete month): the cascade stamps the mail metas (archives
    NEVER deleted - custody holds), the log says "month deleted" instead
    of misreporting rows as operator-removed, and the response carries
    the new routing target + the learned-memory statement."""
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
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
    assert body["inbound_marked"] >= 1
    assert body["next_open_batch"] is None  # no batch left: mail will hold
    assert body["learned_memory"] == "kept"

    # The mail archive survives with its stamp; the log tells the truth.
    entries = client.get("/api/inbound/log?detail=1").json()["entries"]
    row = [e for e in entries if e.get("subject") == "into the month"][0]
    arch = state.data_root / "inbound" / row["archive"]
    assert (arch / "message.eml").exists()
    assert row["batch_deleted"] is True
    assert "batch_label" not in row
    # Pre-fix shape was [{document_id, deleted: True}] - operator-removed
    # misattribution. The month is gone; batch_deleted carries the story.
    assert row["expenses"] == []


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


def test_replay_into_new_batch_clears_delete_stamp(client, monkeypatch):
    """A mail whose original month was deleted, replayed into a live
    month, must not keep saying "month deleted" (stale batch_deleted
    stamp; adversarial review 2026-08-21 finding 2)."""
    import expense_recon.web.intake_mail as im

    first_id = _create_batch(client, monkeypatch)
    state = client.app.state

    # The ingest fails AFTER routing stamped batch_id -> held_failed.
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
    entries = client.get("/api/inbound/log").json()["entries"]
    row = [e for e in entries if e.get("subject") == "stamped mail"][0]
    assert row["batch_deleted"] is True  # stamped while its month is gone

    second_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="Taxi"))
    replay = client.post("/api/inbound/replay-held").json()
    assert replay["replayed"] == 1
    entries = client.get("/api/inbound/log").json()["entries"]
    row = [e for e in entries if e.get("subject") == "stamped mail"][0]
    assert row["batch_id"] == second_id
    assert not row.get("batch_deleted")  # the stamp is cleared
    assert row.get("batch_label")


def test_done_stamp_guard_flips_job_when_batch_vanishes(client, monkeypatch):
    """The delete/ingest ordering where the ingest wins the lock: the DONE
    stamp lands after the cascade purged jobs (run_id was NULL until
    then). The guard re-checks and flips the job to error + the mail to
    held_failed instead of leaving a done-job pointing at a gone run
    (adversarial review 2026-08-21 finding 4)."""
    import expense_recon.web.intake_mail as im
    from expense_recon.web.store import JOB_ERROR

    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state

    def _add_then_batch_vanishes(store, run, *a, **k):
        # Simulate the delete cascade landing right after our locked
        # write: by the time the DONE stamp runs, the run row is gone.
        store.delete_run(run.run_id)
        return {"documents": []}
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
        _html_mail("criss@brisken.com"), synchronous=True,
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
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("criss@brisken.com", subject="render me"),
        synchronous=True,
    )
    assert res["status"] == HELD_BODY_ONLY
    entries = client.get("/api/inbound/log").json()["entries"]
    archive = [e for e in entries if e.get("subject") == "render me"][0]["archive"]

    _patch_ocr(monkeypatch, _extraction(vendor="Uber", total="27.90",
                                        currency="EUR"))
    resp = client.post(f"/api/inbound/{archive}/render-ingest")
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["status"] == STATUS_INGESTED
    assert out["batch_id"] == batch_id
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
    assert mailed[0]["submitted_by"]["address"] == "criss@brisken.com"

    # Now ingested: a second render is refused (no double-charge path).
    again = client.post(f"/api/inbound/{archive}/render-ingest")
    assert again.status_code == 409


def test_render_ingest_guards(client, monkeypatch):
    state = client.app.state
    # No open batch -> 409, mail stays held (deny-by-default).
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("criss@brisken.com", subject="no batch yet"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "no batch yet"
    ][0]["archive"]
    resp = client.post(f"/api/inbound/{archive}/render-ingest")
    assert resp.status_code == 409
    assert "open month" in resp.json()["error"]

    # A mail with attachments (ingested) is never renderable.
    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
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
        _html_mail("criss@brisken.com", subject="junk forward"),
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

    # Only held mail can be dismissed.
    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="DB"))
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

    _create_batch(client, monkeypatch)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("criss@brisken.com", subject="retry me"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "retry me"
    ][0]["archive"]

    def _boom(*a, **k):
        raise RuntimeError("vision transient")
    with monkeypatch.context() as mp:
        mp.setattr(im, "add_receipts_to_expense_batch", _boom)
        first = client.post(f"/api/inbound/{archive}/render-ingest")
    assert first.status_code == 200  # render ran; the INGEST failed
    assert first.json()["status"] == "held_failed"

    # Replay drains held_failed but finds no parts/ -> held_no_valid_files.
    replay_held(state.db_path, state.learning_db_path, state.data_root)

    _patch_ocr(monkeypatch, _extraction(vendor="Uber", total="27.90"))
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

    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("criss@brisken.com", subject="commit then fail"),
        synchronous=True,
    )
    archive = [
        e for e in client.get("/api/inbound/log").json()["entries"]
        if e.get("subject") == "commit then fail"
    ][0]["archive"]

    def _ack_boom(*a, **k):
        raise RuntimeError("tail failure after commit")
    _patch_ocr(monkeypatch, _extraction(vendor="Uber", total="27.90"))
    with monkeypatch.context() as mp:
        mp.setattr(im, "_maybe_ack", _ack_boom)
        first = client.post(f"/api/inbound/{archive}/render-ingest")
    assert first.status_code == 200
    assert first.json()["status"] == "held_failed"  # but the row committed

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

    _create_batch(client, monkeypatch)
    state = client.app.state
    process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _html_mail("criss@brisken.com", subject="race me"),
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
    _patch_ocr(monkeypatch, _extraction(vendor="Uber"))
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

    _create_batch(client, monkeypatch)
    state = client.app.state
    raw = _html_mail("criss@brisken.com", subject="stranded")
    parsed = parse_inbound(raw, DOMAIN)
    arch = archive_incoming(state.data_root, raw, parsed)
    meta_path = arch / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["at"] = "2026-08-21T00:00:00+00:00"  # stale-received threshold
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    replay_held(state.db_path, state.learning_db_path, state.data_root)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["status"] == HELD_BODY_ONLY

    _patch_ocr(monkeypatch, _extraction(vendor="Uber"))
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
    raw = _html_mail("criss@brisken.com", subject="killed mid-render")
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
    """A mail whose attachments were INGESTED into a month that is then
    deleted. Its bytes survive in the custody archive; its expenses do not.
    Replay will not touch it (status `ingested` is not replayable), which is
    exactly the stranding item 19 is about."""
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
    res = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail("criss@brisken.com", attachments=[("tren.jpg", JPG + b"i19")],
              subject=subject),
        synchronous=True,
    )
    assert res["status"] == STATUS_INGESTED
    resp = client.post(f"/api/runs/{batch_id}/delete", json={"confirm": batch_id})
    assert resp.status_code == 200, resp.text
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
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch, _extraction(vendor="Trenitalia"))
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
        _mail("criss@brisken.com", attachments=[], subject="body only",
              body="just text"),
        synchronous=True,
    )
    archive = [e for e in client.get("/api/inbound/log").json()["entries"]
               if e.get("subject") == "body only"][0]["archive"]
    resp = client.post(f"/api/inbound/{archive}/re-ingest")
    assert resp.status_code == 409, resp.text
    assert "attachment" in resp.json()["error"].lower()
