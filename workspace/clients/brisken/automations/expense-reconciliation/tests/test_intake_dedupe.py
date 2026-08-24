"""Arrival-time duplicate detection (owner directive 2026-08-25).

"We need to be able to sort duplicates out before they are ingested into
the tool's workflow."

Before this, the only dedupe was the receipt pool's own content check at
ADD time. That was correct as far as it went (a repeat file created no
second expense) but it had two holes: the intake row still said "Added"
about a mail that added nothing, and a repeat that routed to a DIFFERENT
month landed in a batch the first copy was not in, where the pool check
had nothing to compare it against.

Detection is byte-identical content only. A near-miss MISSES, which is
the old behavior; a false match would hide a real receipt, which is worse
than anything it prevents.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from email.message import EmailMessage

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    STATUS_DUPLICATE,
    STATUS_INGESTED,
    content_fingerprints,
    process_message,
)

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000
DOMAIN = "expenses.brisken.com"
OUTSIDE = "guest@example.org"
RECEIPT_DAY = date.today().replace(day=1) - timedelta(days=20)
MONTH_LABEL = f"{calendar.month_name[RECEIPT_DAY.month]} {RECEIPT_DAY.year}"


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
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _create_batch(client, monkeypatch, label=None, *extra) -> str:
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
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _mail(from_addr, attachments=None, body="receipt attached", subject="r"):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = subject
    msg["Message-ID"] = f"<{subject}@brisken.com>"
    msg.set_content(body)
    for name, data in attachments or []:
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf") else ("image", "jpeg")
        )
        msg.add_attachment(
            data, maintype=maintype, subtype=subtype, filename=name
        )
    return msg.as_bytes()


def _send(client, monkeypatch, *, subject, attachments=None, body="hello",
          sender="criss@brisken.com", extractions=1):
    _patch_ocr(monkeypatch, *[_extraction() for _ in range(extractions)])
    state = client.app.state
    return process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(sender, attachments=attachments, body=body, subject=subject),
        synchronous=True,
    )


def _rows(client):
    return client.get("/api/inbound/log").json()


def _row(client, subject):
    return [
        e for e in _rows(client)["entries"] if e.get("subject") == subject
    ][-1]


# ── the fingerprint ────────────────────────────────────────────────


def test_attachment_digests_match_the_receipt_pools_own_shape():
    """The two dedupe layers must agree about what "the same file" is,
    or a mail could pass here and still add a row there. Both use
    sha1(bytes)[:16]."""
    import hashlib

    data = b"receipt-bytes"
    assert content_fingerprints([("a.pdf", data)]) == [
        hashlib.sha1(data).hexdigest()[:16]
    ]


def test_a_body_only_mail_fingerprints_its_body():
    """It has no attachment to hash at arrival: the PDF does not exist
    until something renders it."""
    fps = content_fingerprints([], "Your receipt from OpenAI, $20.00")
    assert len(fps) == 1 and fps[0].startswith("body:")


def test_body_fingerprints_ignore_rewrapping_and_case():
    """A forward re-wraps lines and clients disagree about case."""
    a = content_fingerprints([], "Your receipt\nfrom OpenAI")
    b = content_fingerprints([], "your   receipt from openai")
    assert a == b


def test_different_bodies_do_not_collide():
    a = content_fingerprints([], "Receipt for 20.00")
    b = content_fingerprints([], "Receipt for 30.00")
    assert a != b


def test_a_mail_with_nothing_in_it_fingerprints_to_nothing():
    """No content means no claim; such a mail must never make the NEXT
    empty mail look like a duplicate of it."""
    assert content_fingerprints([], "   ") == []


# ── detection, through the intake ──────────────────────────────────


def test_an_identical_resend_is_parked_before_ingestion(client, monkeypatch):
    _create_batch(client, monkeypatch, MONTH_LABEL)
    payload = JPG + b"same"
    first = _send(
        client, monkeypatch, subject="first",
        attachments=[("t.jpg", payload)], extractions=2,
    )
    assert first["status"] == STATUS_INGESTED

    second = _send(
        client, monkeypatch, subject="second",
        attachments=[("t.jpg", payload)], extractions=2,
    )
    assert second["status"] == STATUS_DUPLICATE
    assert second["duplicate_of"] == first["archive"]

    row = _row(client, "second")
    assert row["status_kind"] == "resting"
    assert "first" in row["status_label"]
    assert _rows(client)["n_duplicates"] == 1
    # It never reached a batch, so it created nothing to join.
    assert not row.get("expenses")


def test_a_different_filename_does_not_disguise_a_duplicate(client, monkeypatch):
    """Content decides, not the name the sender's mail client chose."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    payload = JPG + b"same"
    _send(client, monkeypatch, subject="first",
          attachments=[("invoice.jpg", payload)], extractions=2)
    second = _send(client, monkeypatch, subject="second",
                   attachments=[("IMG_0042.jpg", payload)], extractions=2)
    assert second["status"] == STATUS_DUPLICATE


def test_a_genuinely_different_receipt_is_not_a_duplicate(client, monkeypatch):
    _create_batch(client, monkeypatch, MONTH_LABEL)
    _send(client, monkeypatch, subject="first",
          attachments=[("a.jpg", JPG + b"aaa")], extractions=2)
    second = _send(client, monkeypatch, subject="second",
                   attachments=[("b.jpg", JPG + b"bbb")], extractions=2)
    assert second["status"] != STATUS_DUPLICATE


def test_a_partly_new_mail_is_not_a_duplicate(client, monkeypatch):
    """Two attachments where one is already held still carries a receipt
    the tool does not have. The pool's content dedupe drops the repeat at
    add time; parking the whole mail would lose the new one."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    old = JPG + b"aaa"
    _send(client, monkeypatch, subject="first",
          attachments=[("a.jpg", old)], extractions=2)
    second = _send(
        client, monkeypatch, subject="second",
        attachments=[("a.jpg", old), ("b.jpg", JPG + b"bbb")], extractions=4,
    )
    assert second["status"] != STATUS_DUPLICATE


def test_a_dismissed_mail_does_not_own_its_content(client, monkeypatch):
    """A dismissed first copy means the tool does NOT hold that receipt.
    Calling the next copy a duplicate would hide a receipt nobody ever
    ingested, which is the opposite of what dedupe is for."""
    # No batch for the receipt's month, so the mail rests in the pool —
    # which is a state the operator can dismiss from (an ingested mail is
    # not, by design).
    payload = JPG + b"junked"
    first = _send(client, monkeypatch, subject="first",
                  attachments=[("t.jpg", payload)], extractions=1)
    assert first["status"] == "pooled"
    assert client.post(
        f"/api/inbound/{first['archive']}/dismiss"
    ).status_code == 200

    second = _send(client, monkeypatch, subject="second",
                   attachments=[("t.jpg", payload)], extractions=1)
    assert second["status"] != STATUS_DUPLICATE


def test_a_held_mail_does_not_own_its_content(client, monkeypatch):
    """Held body-only mail from a stranger never entered the workflow
    either. Its content is not held, so a resend is not a duplicate."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    first = _send(client, monkeypatch, subject="body one",
                  body="Your OpenAI receipt 20.00", sender=OUTSIDE)
    assert str(first["status"]).startswith("held_")
    second = _send(client, monkeypatch, subject="body two",
                   body="Your OpenAI receipt 20.00", sender=OUTSIDE)
    assert second["status"] != STATUS_DUPLICATE


# ── the escape hatch ───────────────────────────────────────────────


def test_not_a_duplicate_routes_the_mail_after_all(client, monkeypatch):
    """Byte-identical content CAN be two real purchases (a fixed-price
    subscription receipt carrying no invoice number, mailed two months
    running), so a parked mail must never be trapped."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    payload = JPG + b"sub"
    _send(client, monkeypatch, subject="first",
          attachments=[("s.jpg", payload)], extractions=2)
    second = _send(client, monkeypatch, subject="second",
                   attachments=[("s.jpg", payload)], extractions=2)
    assert second["status"] == STATUS_DUPLICATE

    _patch_ocr(monkeypatch, _extraction(), _extraction())
    resp = client.post(
        f"/api/inbound/{second['archive']}/not-a-duplicate"
    )
    assert resp.status_code == 200, resp.text
    assert _row(client, "second")["status"] != STATUS_DUPLICATE


def test_an_override_survives_the_detector_on_the_way_back_in(
    client, monkeypatch
):
    """Without honouring the override, routing would re-park the mail and
    the escape hatch would be a no-op."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    payload = JPG + b"again"
    _send(client, monkeypatch, subject="first",
          attachments=[("s.jpg", payload)], extractions=2)
    second = _send(client, monkeypatch, subject="second",
                   attachments=[("s.jpg", payload)], extractions=2)

    _patch_ocr(monkeypatch, _extraction(), _extraction())
    client.post(f"/api/inbound/{second['archive']}/not-a-duplicate")
    assert _rows(client)["n_duplicates"] == 0


def test_not_a_duplicate_refuses_a_mail_that_is_not_parked(client, monkeypatch):
    """Deny-by-default: this must never become a second, unguarded ingest
    path for arbitrary mail."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    held = _send(client, monkeypatch, subject="body one",
                 body="a body", sender=OUTSIDE)
    resp = client.post(f"/api/inbound/{held['archive']}/not-a-duplicate")
    assert resp.status_code == 409


def test_a_duplicate_can_be_dismissed(client, monkeypatch):
    """Otherwise it rests forever with no way to finish with it."""
    _create_batch(client, monkeypatch, MONTH_LABEL)
    payload = JPG + b"dd"
    _send(client, monkeypatch, subject="first",
          attachments=[("d.jpg", payload)], extractions=2)
    second = _send(client, monkeypatch, subject="second",
                   attachments=[("d.jpg", payload)], extractions=2)
    assert second["status"] == STATUS_DUPLICATE
    assert client.post(
        f"/api/inbound/{second['archive']}/dismiss"
    ).status_code == 200
    assert _rows(client)["n_duplicates"] == 0
