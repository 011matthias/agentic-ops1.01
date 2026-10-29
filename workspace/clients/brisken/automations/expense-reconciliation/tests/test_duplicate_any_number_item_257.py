"""Copies share an important number, in whichever field it sits (backlog item
257, owner 2026-10-29, on October's Anthropic pair).

The Compare copies view showed the shape: the receipt's reference is its OWN
receipt number (``2709 9940``), the invoice's reference is the invoice number
(``EF742DD0 0062``), and BOTH carry ``EF742DD0 0062`` as their invoice number.
Comparing references alone, the ladder's rung 4 called that pair two
purchases; October got it right only because one mail delivered both (rung 0).
Uploaded separately, or re-mailed, it was two expenses again.

Now a number shared in any number field (reference, invoice number, receipt
number) makes documents of one amount one purchase, the receipt is kept
(item 256), and the set-aside invoice asks nothing.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    BASIS_REFERENCE,
    VERDICT_COPY,
    number_keys,
)
from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _x(*, vendor, day, total, reference, invoice_number, receipt_number=None,
       kind, payment_hint=None):
    return ExtractedReceipt(
        date=f"2026-10-{day:02d}", total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint, invoice_number=invoice_number,
        receipt_number=receipt_number, document_kind=kind,
    )


def _invoice(**kw):
    base = dict(vendor="Anthropic, PBC", day=1, total="66.00",
                reference="EF742DD0 0062", invoice_number="EF742DD0 0062",
                kind="invoice")
    return _x(**{**base, **kw})


def _receipt(**kw):
    base = dict(vendor="Anthropic, PBC", day=1, total="66.00",
                reference="2709 9940", invoice_number="EF742DD0 0062",
                receipt_number="2709-9940", kind="receipt")
    return _x(**{**base, **kw})


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, *extractions):
    """A month with no statement, the documents uploaded by hand: no mail
    delivered them together, so no intake record pairs them."""
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": "October 2026"})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    names = ["Invoice-EF742DD0-0062.jpg", "Receipt-2709-9940.jpg", "Other-3.jpg"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (names[i], JPG + bytes([i]), "application/octet-stream"))
            for i in range(len(extractions))
        ],
    ))
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(grid, stem):
    return next(e for e in grid["expenses"] if stem in e["document_id"])


def test_the_screenshot_pair_is_one_purchase_and_the_receipt_counts(client, monkeypatch):
    grid = _month(client, monkeypatch, _invoice(), _receipt())
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_REFERENCE, VERDICT_COPY)
    inv, rec = _row(grid, "Invoice-"), _row(grid, "Receipt-")
    assert rec["duplicate"]["is_extra"] is False, "the receipt is the real expense"
    assert inv["duplicate"]["is_extra"] is True
    assert inv["counts_in_total"] is False
    assert inv["review"]["state"] == "none", "the copy asks nothing (item 256)"
    assert grid["summary"]["totals_by_ccy"] == {"USD": "66.00"}


def test_found_by_the_number_alone_whatever_the_vendor_spelling_or_date(client, monkeypatch):
    """Stripe prints the vendor two ways on the two PDFs and a re-mailed copy
    carries the mail's date, so no older key nominates the pair."""
    grid = _month(
        client, monkeypatch,
        _invoice(vendor="Anthropic, PBC", day=1),
        _receipt(vendor="Anthropic, PBC (@anthropic)", day=4),
    )
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == (BASIS_REFERENCE, VERDICT_COPY)
    assert _row(grid, "Receipt-")["duplicate"]["is_extra"] is False
    assert grid["summary"]["totals_by_ccy"] == {"USD": "66.00"}


def test_a_number_carried_at_two_amounts_is_an_account_not_a_document(client, monkeypatch):
    """Two top-ups under one account code: the code is printed on three
    documents at two different totals, so it twins nothing and the two
    66.00 top-ups stay two purchases."""
    grid = _month(
        client, monkeypatch,
        _invoice(reference="A-1001", invoice_number="NQTJA4FE"),
        _receipt(reference="R-2002", invoice_number="NQTJA4FE", receipt_number=None),
        _invoice(reference="A-1003", invoice_number="NQTJA4FE", total="45.44"),
    )
    assert not any(g.get("verdict") == VERDICT_COPY for g in grid["duplicate_groups"])
    assert grid["summary"]["n_copies_set_aside"] == 0


def test_two_cards_on_the_documents_keep_them_apart(client, monkeypatch):
    grid = _month(
        client, monkeypatch,
        _invoice(payment_hint="Visa ending 2838"),
        _receipt(payment_hint="Visa ending 1672"),
    )
    assert not any(g.get("verdict") == VERDICT_COPY for g in grid["duplicate_groups"])
    assert grid["summary"]["n_copies_set_aside"] == 0


def _r(doc, **kw):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=date(2026, 10, 1),
        detected_total=Decimal(kw.pop("total", "66.00")), detected_currency="USD",
        detected_vendor="Anthropic", **kw,
    )


def test_number_keys_read_every_number_field():
    keys = number_keys([
        _r("a", detected_reference="2709 9940", invoice_number="EF742DD0 0062",
           receipt_number="2709-9940"),
        _r("b", detected_reference="EF742DD0-0062", invoice_number="EF742DD0 0062"),
        # a till counter and the receipt's own date are no numbers
        _r("c", detected_reference="4563", invoice_number="20261001"),
    ])
    assert keys == {
        "a": frozenset({"27099940", "EF742DD00062"}),
        "b": frozenset({"EF742DD00062"}),
    }
