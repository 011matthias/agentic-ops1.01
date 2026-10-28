"""The mail path: a payment reminder must not become an expense (2026-09-24).

This is the path the live defect took. Brisken July 2026 holds a Redis
past-due notice booked as a second USD 13,200.00 expense beside the real
invoice, because the notice arrived as a body-only mail, rendered to a PDF
and read as a receipt.

The helper tests in `test_correspondence.py` prove the rule. These prove the
WIRING, which is the half that was missing: disable the call in
`add_receipts_to_expense_batch` and a test here goes red.

One trap is pinned deliberately. A rendered mail body is an IMAGE pdf with no
text layer, so the extractor keeps the model's `notes` as `ocr_text` and the
body's own words never reach the rule unless the intake carries them in. A
version of this change that read only `ocr_text` looked complete, passed its
helper tests, and would have missed the exact document it was written for.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.intake_mail import body_text_by_digest  # noqa: E402
from expense_recon.web.service import (  # noqa: E402
    add_receipts_to_expense_batch,
    set_aside_entries,
)
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

REDIS_PAST_DUE = """
From: Sagar Pardeshi <sagar.pardeshi@redis.com>
Subject: Redis Invoice Past Due IUS25300

Dear Customer,

Our records show that the following invoice remains unpaid and is now 7 days
past due.

Invoice #  Invoice Date  Due Date  Invoice Amount  Invoice Balance
IUS25300  July 22, 2026  Sept. 5, 2026  $13,200.00  $13,200.00
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(total: str = "13200.00") -> ExtractedReceipt:
    """What the vision reader returns for the rendered notice: it reads the
    vendor, the amount and the number off the quoted table, and no line
    items, because a notice itemizes nothing."""
    return ExtractedReceipt(
        date="2026-07-22", total=total, currency="USD", vendor="Redis",
        reference="IUS25300", line_items=(), confidence=0.9,
        notes="rendered email body", payment_hint=None,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _batch(client) -> str:
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": "July 2026"},
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _stage(tmp_path: Path, name: str, data: bytes) -> tuple[Path, str]:
    staging = tmp_path / "staging"
    staging.mkdir(exist_ok=True)
    (staging / name).write_bytes(data)
    return staging, hashlib.sha1(data).hexdigest()[:16]


def _add(client, tmp_path, staging, **kw) -> dict:
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(_BATCH["id"])
        return add_receipts_to_expense_batch(
            store, run, staging, "2026-09-24T00:00:00+00:00", **kw
        )


_BATCH: dict = {}


def test_a_mailed_reminder_never_becomes_an_expense(client, tmp_path, monkeypatch):
    _wire(monkeypatch, _extraction())
    _BATCH["id"] = _batch(client)
    staging, digest = _stage(tmp_path, "0000__rendered-body.pdf", JPG)

    summary = _add(client, tmp_path, staging, text_by_digest={digest: REDIS_PAST_DUE})

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(_BATCH["id"])
    aside = set_aside_entries(run.snapshot or {})
    assert [e.get("reason") for e in aside] == ["correspondence"], summary
    assert not (run.snapshot or {}).get("receipts"), "the notice became an expense"


def test_the_same_document_without_the_carried_text_is_kept(
    client, tmp_path, monkeypatch
):
    """The differential probe: one input moves, the answer moves. Without the
    body text the reader sees only its own notes, so the row stays — which is
    exactly the live defect, and exactly what the carry fixes."""
    _wire(monkeypatch, _extraction())
    _BATCH["id"] = _batch(client)
    staging, _ = _stage(tmp_path, "0000__rendered-body.pdf", JPG)

    _add(client, tmp_path, staging)

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(_BATCH["id"])
    assert not set_aside_entries(run.snapshot or {})
    assert (run.snapshot or {}).get("receipts")


def test_an_invoice_attached_to_a_reminder_keeps_its_row(
    client, tmp_path, monkeypatch
):
    """"FW: Reminder Invoice from Redis" attaches the genuine invoice. The
    carry maps the body text to the RENDERED BODY only, so an attachment is
    judged on its own text and survives."""
    _wire(monkeypatch, ExtractedReceipt(
        date="2026-07-22", total="13200.00", currency="USD", vendor="Redis Inc.",
        reference="IUS25300", line_items=(), confidence=0.9,
        notes="invoice", payment_hint=None,
    ))
    _BATCH["id"] = _batch(client)
    staging, digest = _stage(tmp_path, "0000__invoice-IUS25300.pdf", JPG)

    # The mail carried a reminder body, but this digest is the ATTACHMENT's.
    _add(client, tmp_path, staging, text_by_digest={"0" * 16: REDIS_PAST_DUE})

    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        run = store.get_run(_BATCH["id"])
    assert not set_aside_entries(run.snapshot or {})
    assert (run.snapshot or {}).get("receipts")


# --- the staging-prefix trap ------------------------------------------------

def test_body_text_maps_the_position_prefixed_rendered_body(tmp_path):
    """Staging writes `0000__rendered-body.pdf`, so an exact-name lookup
    silently never matches and the whole carry goes dead with every test
    still green. Caught by reading the staging writer, not by a failure."""
    arch = tmp_path / "arch"
    arch.mkdir()
    (arch / "message.eml").write_bytes(
        b"From: ar@redis.com\r\nSubject: Past Due\r\n"
        b"Content-Type: text/plain\r\n\r\n" + REDIS_PAST_DUE.encode()
    )
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "0000__rendered-body.pdf").write_bytes(JPG)

    out = body_text_by_digest(arch, staging)
    assert list(out) == [hashlib.sha1(JPG).hexdigest()[:16]]
    assert "past due" in next(iter(out.values())).lower()


def test_body_text_never_maps_an_attachment(tmp_path):
    arch = tmp_path / "arch"
    arch.mkdir()
    (arch / "message.eml").write_bytes(
        b"From: ar@redis.com\r\nSubject: Reminder\r\n"
        b"Content-Type: text/plain\r\n\r\n" + REDIS_PAST_DUE.encode()
    )
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "0000__invoice-IUS25300.pdf").write_bytes(JPG)

    assert body_text_by_digest(arch, staging) == {}


def test_body_text_is_fail_open(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    assert body_text_by_digest(None, staging) == {}
    assert body_text_by_digest(tmp_path / "missing", staging) == {}
