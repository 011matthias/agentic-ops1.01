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
    STATUS_INGESTED,
    IntakeConfig,
    parse_inbound,
    process_message,
    read_log,
    replay_held,
    resolve_person,
    sender_allowed,
)
from expense_recon.web.smtp_server import data_decision, rcpt_decision  # noqa: E402

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


def test_data_decision_sender_and_caps():
    cfg = IntakeConfig(sender_daily_cap=2, global_daily_cap=5)
    ok = data_decision(
        "dirk.neumann@brisken.com", "dirk.neumann@brisken.com", cfg, {}, 0
    )
    assert ok is None
    # envelope passes but header sender does not -> refused
    spoofed = data_decision(
        "dirk.neumann@brisken.com", "evil@gmail.com", cfg, {}, 0
    )
    assert spoofed.startswith("550")
    capped = data_decision(
        "dirk.neumann@brisken.com", "dirk.neumann@brisken.com", cfg,
        {"dirk.neumann@brisken.com": 2}, 2,
    )
    assert capped.startswith("452")
    global_capped = data_decision(
        "dirk.neumann@brisken.com", "dirk.neumann@brisken.com", cfg, {}, 5
    )
    assert global_capped.startswith("452")


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
