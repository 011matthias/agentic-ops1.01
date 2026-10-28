"""What the document calls itself (item 223 step 4, front 4, 2026-09-27).

Item 217 keeps a purchase's payment receipt over its invoice, and it told the
two apart by the printed numbers or else by the file NAME (Stripe's
``Invoice-...`` / ``Receipt-...``). A vendor that names its files anything
else left the choice to upload order. The extraction now also returns
``document_kind`` (invoice / receipt / reminder / statement / other), asked in
the response schema only, and the ladder reads it before the file name.

A reminder is a notice chasing another invoice (July's Redis 0070). It is
never kept over the document it chases, and on its own it asks a person
(``reads_as_reminder``); a reading alone never removes a row.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    _EXTRACT_INSTRUCTIONS,
    _EXTRACT_SCHEMA,
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
    _extraction_from_payload,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import receipt_from_dict, receipt_to_dict  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _x(vendor, day, total, currency, reference, kind):
    return ExtractedReceipt(
        date=day, total=total, currency=currency, vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=None, document_kind=kind,
    )


def _month(client, monkeypatch, files, extractions, label="July 2026"):
    """A month with no statement: the kept copy is chosen as the page is read."""
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("50.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    batch_id = resp.json()["batch_id"]
    resp = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + bytes([i]), "application/octet-stream"))
            for i, name in enumerate(files)
        ],
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_name(grid, needle):
    return next(e for e in grid["expenses"] if needle in e["document_id"])


# ── the reading ──────────────────────────────────────────────────────────


def test_the_kind_is_read_whitelisted_and_absent_when_unrecognised():
    assert _extraction_from_payload({"document_kind": " Reminder "}).document_kind == "reminder"
    assert _extraction_from_payload({"document_kind": "invoice"}).document_kind == "invoice"
    # junk, a missing key (every cached payload read before the field) -> None
    assert _extraction_from_payload({"document_kind": "bill"}).document_kind is None
    assert _extraction_from_payload({}).document_kind is None


def test_the_question_rides_in_the_schema_and_the_instructions_do_not_change():
    """The item 77 shape: last, carried by `description`. Naming a field in the
    instructions moved 39 stable readings on 2026-09-16; this shape did not
    touch a date, total, currency, type or card."""
    assert "document_kind" not in _EXTRACT_INSTRUCTIONS
    assert list(_EXTRACT_SCHEMA["properties"])[-1] == "document_kind"
    assert _EXTRACT_SCHEMA["required"][-1] == "document_kind"
    assert _EXTRACT_SCHEMA["properties"]["document_kind"]["enum"] == [
        "invoice", "receipt", "reminder", "statement", "other"]


def test_the_kind_survives_the_snapshot_and_an_older_snapshot_still_loads():
    from expense_recon.matching.types import Receipt

    r = Receipt(
        document_id="a.jpg", legal_entity_id="", detected_date=None,
        detected_total=None, detected_currency=None, detected_vendor=None,
        detected_reference=None, document_kind="receipt",
    )
    d = receipt_to_dict(r)
    assert receipt_from_dict(d).document_kind == "receipt"
    d.pop("document_kind")
    assert receipt_from_dict(d).document_kind is None


# ── which copy counts ────────────────────────────────────────────────────


def test_the_payment_receipt_counts_over_its_invoice_when_only_the_document_says_so(
    client, monkeypatch
):
    """Neither file name nor any printed number says which is which, and the
    invoice arrived first: before step 4 upload order kept the invoice."""
    batch_id = _month(client, monkeypatch, ["acme-a.jpg", "acme-b.jpg"], [
        _x("ACME CLOUD", "2026-07-10", "50.00", "USD", "AC-778812", "invoice"),
        _x("ACME CLOUD", "2026-07-10", "50.00", "USD", "AC-778812", "receipt"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["verdict"] == "copy", group
    assert _by_name(grid, "acme-b").get("counts_in_total", True) is True
    assert _by_name(grid, "acme-a").get("counts_in_total", True) is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "50.00"}


def test_a_reminder_is_never_the_copy_that_counts(client, monkeypatch):
    """July's Redis shape: the past-due notice quotes the invoice's number,
    date and amount, so the two group; the notice arrived first."""
    batch_id = _month(client, monkeypatch, ["notice.jpg", "bill.jpg"], [
        _x("REDIS INC", "2026-07-22", "13200.00", "USD", "IUS25300", "reminder"),
        _x("REDIS INC", "2026-07-22", "13200.00", "USD", "IUS25300", "invoice"),
    ])
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["verdict"] == "copy", group
    assert _by_name(grid, "bill").get("counts_in_total", True) is True
    assert _by_name(grid, "notice").get("counts_in_total", True) is False


def test_a_reminder_alone_asks_a_person_and_still_counts(client, monkeypatch):
    """No invoice beside it: the row stays in the month (never a deletion)
    and reads `reads_as_reminder` until the reviewer makes a category hers."""
    batch_id = _month(client, monkeypatch, ["notice.jpg"], [
        _x("REDIS INC", "2026-07-22", "13200.00", "USD", "IUS25300", "reminder"),
    ])
    row = _by_name(_grid(client, batch_id), "notice")
    assert row.get("counts_in_total", True) is True
    assert row["review"]["reason_code"] == "reads_as_reminder", row["review"]

    resp = client.put(
        f"/api/runs/{batch_id}/expenses/{row['document_id']}",
        json={"field": "category", "value": "Software & Subscriptions"},
    )
    assert resp.status_code == 200, resp.text
    row = _by_name(_grid(client, batch_id), "notice")
    assert row["review"]["reason_code"] != "reads_as_reminder", row["review"]


def test_a_receipt_read_before_the_field_existed_asks_nothing_new(client, monkeypatch):
    """Every stored reading has no kind: the file-name rule and the review
    ladder behave exactly as before."""
    batch_id = _month(client, monkeypatch, ["Invoice-ABCD1234-0001.jpg", "Receipt-2231-0001.jpg"], [
        _x("LOVABLE LABS", "2026-07-03", "25.00", "USD", "ABCD1234-0001", None),
        _x("LOVABLE LABS", "2026-07-03", "25.00", "USD", "ABCD1234-0001", None),
    ])
    grid = _grid(client, batch_id)
    assert _by_name(grid, "Receipt-2231").get("counts_in_total", True) is True
    assert _by_name(grid, "Invoice-ABCD1234").get("counts_in_total", True) is False
    assert all(
        (e.get("review") or {}).get("reason_code") != "reads_as_reminder"
        for e in grid["expenses"]
    )


def test_a_receipt_that_also_reads_its_invoice_number_still_counts_over_the_invoice(
    client, monkeypatch
):
    """Measured in the A/B: with the kind in the schema, a Stripe receipt also
    reads the invoice number it prints (``HMVWDWIL0029`` on both copies), so
    the numbers alone would call both copies invoices and keep the first."""
    def read(kind):
        return ExtractedReceipt(
            date="2026-08-05", total="15.00", currency="USD", vendor="LOVABLE LABS",
            reference="HMVWDWIL-0029", line_items=(), confidence=0.9, notes="",
            payment_hint=None, invoice_number="HMVWDWIL0029", document_kind=kind,
        )

    batch_id = _month(client, monkeypatch, ["stripe-a.jpg", "stripe-b.jpg"],
                      [read("invoice"), read("receipt")], label="August 2026")
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["verdict"] == "copy", group
    assert _by_name(grid, "stripe-b").get("counts_in_total", True) is True
    assert _by_name(grid, "stripe-a").get("counts_in_total", True) is False
