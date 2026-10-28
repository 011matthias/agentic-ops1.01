"""Correspondence quarantine: a document ABOUT an obligation is not an expense.

Every fixture text below is lifted from the real Brisken July 2026 documents
read on 2026-09-24, because the whole point of this rung is that synthetic
"reminder-looking" text is easy and the real shapes are what defeated it.

The negative cases are the contract. A rung that only proves it catches the
Redis notice would happily quarantine the Redis INVOICE, the Hostinger
confirmation, and every taxi slip in the estate.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from expense_recon.cli import NON_RECEIPT_LABELS, split_non_receipt_documents
from expense_recon.correspondence import (
    CORRESPONDENCE,
    correspondence_marker,
    quarantine_correspondence,
)
from expense_recon.matching.types import LineItem, Receipt

# --- real document text -----------------------------------------------------

# The past-due notice that became a second USD 13,200.00 July expense.
REDIS_PAST_DUE = """
From: dirk.neumann@brisken.com
Subject: FW: Redis Invoice Past Due IUS25300
Received: 2026-09-12T09:24:20+00:00
Rendered from e-mail body (no attachment was delivered)

From: Sagar Pardeshi <sagar.pardeshi@redis.com>
Subject: Redis Invoice Past Due IUS25300

Dear Customer,

Our records show that the following invoice remains unpaid and is now 7 days
past due. If payment has already been completed, kindly provide the
remittance details so we can update our records.

Invoice #  Invoice Date  Due Date  Invoice Amount  Invoice Balance  Invoice PDF
IUS25300  July 22, 2026  Sept. 5, 2026  $13,200.00  $13,200.00  View PDF
"""

# The genuine invoice the notice is about. Note "due date" and "Remit Payment
# to" -- close to the markers on purpose, and it must survive.
REDIS_INVOICE = """
Redis Inc.  Invoice
Invoice #: IUS25300   Date: 07/22/2026   Due Date: 09/05/2026   Currency: USD
Bill To: BRISKEN. LLC

P/N 20210201001004  [Redis Enterprise - Cloud] Annual Commit  12,000.00
P/N 20210201004006  Customer Support - Business                1,200.00
Total  $13,200.00

Remit Payment to: HSBC Bank USA National Association
Payments received after due date shall be subject to a late charge of 1.5%
per month.
"""

# A forwarded payment confirmation. One purchase, forwarded twice; both copies
# must stay expenses.
HOSTINGER_CONFIRMATION = """
Subject: FW: Hostinger Invoice H_46243348 - KVM 2 Server (2 Years)
Invoice: H_46243348
Product: KVM 2 (2 years)
Price: 172.61 USD
Taxes: 0.00 USD
Total paid: 172.61 USD
"""

# No itemization at all, and no dunning language. The commonest real shape.
TAXI_SLIP = """
TAXI PARIS
22/07/2026  18:42
TOTAL  34,50 EUR
CB ****2838  MERCI
"""


def _receipt(doc_id: str, text: str, *, lines=(), doc_type="receipt") -> Receipt:
    return Receipt(
        document_id=doc_id,
        legal_entity_id="Consulting",
        detected_date=None,
        detected_total=Decimal("13200.00"),
        detected_currency="USD",
        detected_vendor="Redis",
        ocr_text=text,
        line_items=tuple(lines),
        document_type=doc_type,
    )


def _line(desc: str, total: str) -> LineItem:
    return LineItem(description=desc, quantity=None, unit_price=None,
                    line_total=Decimal(total))


# --- the defect this rung exists for ---------------------------------------

def test_past_due_notice_is_quarantined():
    r = _receipt("0070__rendered-body.pdf", REDIS_PAST_DUE)
    out = quarantine_correspondence(r)
    assert out is not None
    assert out.document_type == CORRESPONDENCE
    assert "payment reminder" in (out.data_quality_note or "")


def test_quarantined_type_is_excluded_by_the_partition():
    """Through the caller, not just the helper: the rung is only worth
    anything if `split_non_receipt_documents` actually drops the row."""
    notice = _receipt("0070__rendered-body.pdf", REDIS_PAST_DUE)
    kept, excluded, issues = split_non_receipt_documents([notice])
    assert [r.document_id for r in kept] == []
    assert [r.document_id for r in excluded] == ["0070__rendered-body.pdf"]
    assert len(issues) == 1
    assert "payment reminder or account notice" in issues[0].message


def test_correspondence_has_a_reviewer_facing_label():
    assert CORRESPONDENCE in NON_RECEIPT_LABELS


# --- the negatives: what must NOT be quarantined ---------------------------

def test_the_real_invoice_survives_its_own_due_date_language():
    """The Redis INVOICE prints "Due Date" and "Remit Payment to" and has real
    line items. Quarantining it would delete the expense and keep nothing."""
    r = _receipt("0004__invoice-IUS25300.pdf", REDIS_INVOICE,
                 lines=[_line("[Redis Enterprise - Cloud] Annual Commit", "12000.00"),
                        _line("Customer Support - Business", "1200.00")])
    assert quarantine_correspondence(r) is None
    kept, excluded, _ = split_non_receipt_documents([r])
    assert [x.document_id for x in kept] == ["0004__invoice-IUS25300.pdf"]
    assert excluded == []


def test_a_forwarded_payment_confirmation_survives():
    r = _receipt("0000__rendered-body.pdf", HOSTINGER_CONFIRMATION,
                 lines=[_line("KVM 2 (2 years)", "172.61")])
    assert quarantine_correspondence(r) is None


def test_no_itemization_alone_never_quarantines():
    """Taxi slips, card slips and tickets legitimately print a total and
    nothing else; the extractor is told to return an empty list for them."""
    r = _receipt("0031__taxi.pdf", TAXI_SLIP)
    assert not r.line_items
    assert quarantine_correspondence(r) is None


def test_a_marker_alone_never_quarantines():
    """An invoice carrying a past-due footer keeps its row, because it prints
    its own purchased lines. Both signals are required."""
    text = REDIS_INVOICE + "\nThis account is past due.\n"
    r = _receipt("0004__invoice-IUS25300.pdf", text,
                 lines=[_line("Annual Commit", "12000.00")])
    assert quarantine_correspondence(r) is None


def test_an_already_quarantined_document_keeps_its_own_reason():
    r = _receipt("0001__statement.pdf", REDIS_PAST_DUE, doc_type="statement")
    assert quarantine_correspondence(r) is None


def test_a_source_with_no_text_layer_is_untouched():
    """CSV and consolidated-report sources keep `ocr_text` empty; the rung
    must be silent for them rather than guessing from the other fields."""
    r = _receipt("row-14", "")
    assert quarantine_correspondence(r) is None
    assert quarantine_correspondence(replace(r, ocr_text="   \n ")) is None


# --- the markers themselves -------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    (REDIS_PAST_DUE, "past_due"),
    ("This is a friendly reminder that the attached invoice is due in 10 days.",
     "reminder"),
    ("Invoice Amount Invoice Balance Invoice PDF", "invoice_balance"),
    ("Zahlungserinnerung: Ihre Rechnung ist offen.", "de_mahnung"),
    ("Sua fatura esta em atraso.", "pt_atraso"),
])
def test_markers_fire(text, expected):
    assert correspondence_marker(text) == expected


@pytest.mark.parametrize("text", [
    # Measured near-misses, deliberately NOT markers.
    "Remit Payment to: HSBC Bank USA National Association",
    "kindly provide the remittance details",
    "Balance due: 0.00",
    "We will automatically charge the total amount due shown above",
    # Ordinary receipt language.
    "Payments received after due date shall be subject to a late charge",
    "Thank you for your Business!",
    "Total paid: 172.61 USD",
    "",
    None,
])
def test_markers_stay_quiet(text):
    assert correspondence_marker(text) is None
