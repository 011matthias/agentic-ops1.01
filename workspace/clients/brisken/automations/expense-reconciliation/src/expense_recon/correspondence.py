"""Correspondence quarantine: a document ABOUT an obligation is not evidence OF one.

A dunning notice or a payment reminder quotes the invoice's number, its date
and its amount. That triple is exactly what every duplicate key matches on, so
correspondence is a FLAWLESS duplicate of the invoice it chases and no key can
tell the two apart. It is also not a purchase, so the right answer is not
"copy" but "not an expense".

The live instance this was built from (measured 2026-09-24, Brisken July 2026):
Redis AR mailed "Redis Invoice Past Due IUS25300" on 2026-09-12 about invoice
IUS25300 of 2026-07-22. No attachment, so the body rendered to a PDF, read as a
receipt, and became a SECOND USD 13,200.00 expense beside the real invoice --
about 42% of July's USD total. The tool grouped the two as copies; the reviewer
correctly said "not a copy". Neither verdict was the right one.

Two cases from the same month must keep working, and they are why this module
is narrow:

* **A reminder can carry the real invoice.** "FW: Reminder Invoice from Redis
  IUS25300" says *"the attached invoice is due in 10 days"* -- and its
  attachment is the genuine invoice PDF, which SHOULD become the expense. So
  the text tested here is the STORED DOCUMENT's own text, never the mail's.
  Judging the mail would have thrown away the invoice.
* **A forwarded receipt is still a receipt.** Hostinger invoice H_46243348
  ("KVM 2 (2 years), Total paid: 172.61 USD") was forwarded on Jul 3 and again
  on Jul 28. Two renderings of one purchase; a payment confirmation carries no
  dunning language and prints its own line item, so nothing here touches it.

Deterministic, text-only, no model call. The extractor's prompt is left alone
on purpose, following item 105: a prompt edit moves unrelated readings across
the estate and invalidates every cached one.
"""
from __future__ import annotations

import re
from dataclasses import replace

from .matching.types import Receipt

#: What this module writes into ``Receipt.document_type``. Deliberately NOT a
#: member of the extractor's ``document_type`` enum: only this module produces
#: it, so the extraction-cache fingerprint is untouched.
CORRESPONDENCE = "correspondence"

CORRESPONDENCE_NOTE = (
    "reads as a payment reminder or account notice about another document, "
    "not as evidence of a purchase, so no expense was created"
)

#: Phrases only correspondence ABOUT a document prints.
#:
#: Calibrated 2026-09-24 over every archived mail body the live app holds (103
#: of 143 archives carry readable body text; the rest are attachment-only).
#: The set below fires on 2 of 103 -- the two Redis mails -- and on nothing
#: else. Three near-misses were measured and are deliberately NOT markers:
#:
#: * ``remittance`` -- the real Redis INVOICE prints "Remit Payment to:".
#: * ``balance due`` / ``amount due`` -- ``amount due`` fires on the AWS
#:   "Billing Statement Available" mail, which the statement rung already sets
#:   aside, so it would add risk and catch nothing new.
#:
#: The German and Portuguese phrases have zero hits either way in today's
#: estate; they are carried because the estate is multilingual and a
#: Zahlungserinnerung is the same document as a past-due notice.
_MARKERS: tuple[tuple[str, str], ...] = (
    ("past_due", r"past\s+due"),
    ("unpaid", r"remains?\s+unpaid|still\s+unpaid"),
    ("invoice_balance", r"invoice\s+balance"),
    ("our_records", r"our\s+records\s+show"),
    ("reminder", r"payment\s+reminder|friendly\s+reminder|gentle\s+reminder"),
    ("de_mahnung", r"zahlungserinnerung|\bmahnung\b"),
    ("pt_atraso", r"em\s+atraso|aviso\s+de\s+vencimento"),
)
_COMPILED = tuple((name, re.compile(rx, re.I)) for name, rx in _MARKERS)


def correspondence_marker(text: str | None) -> str | None:
    """The name of the first marker this text prints, or None.

    Pure, so a caller can say WHY a document was set aside instead of
    announcing a verdict with no evidence behind it.
    """
    if not text or not text.strip():
        return None
    for name, rx in _COMPILED:
        if rx.search(text):
            return name
    return None


def _has_itemization(r: Receipt) -> bool:
    """Whether the reader found real purchased lines on this document.

    The same discriminator item 105 measured from the other side: real
    invoices print their own line items, while statements and billing-notice
    mails print none. An unreadable line amount is stored as 0, so "has a
    line" means "has a line with a non-zero amount".
    """
    return any(li.line_total for li in r.line_items)


def quarantine_correspondence(r: Receipt) -> Receipt | None:
    """The receipt re-typed as correspondence, or None to leave it alone.

    Reads ``Receipt.ocr_text``, which the folder ingest already fills with the
    stored file's own text layer. That is deliberately the DOCUMENT's text and
    never the mail's: "FW: Reminder Invoice from Redis IUS25300" attaches the
    genuine invoice, so judging the mail would set the invoice aside with it.
    Sources that read no text (a Zoho CSV, a consolidated report PDF) leave
    ``ocr_text`` empty and are untouched.

    Mirrors ``keep_invoice_read_as_statement`` (item 105) in the opposite
    direction: that one rescues a real invoice the reader called a statement;
    this one quarantines a notice the reader called a receipt.

    Both signals are required, and each covers the other's blind spot. The
    MARKER alone would quarantine a genuine invoice that prints a past-due
    warning in its footer -- a shape the mail-body corpus could not rule out,
    since it holds no vendor PDFs. NO ITEMIZATION alone is ordinary: taxi
    slips, card slips and tickets legitimately print a total and nothing else,
    and the extractor is told to return an empty list for them.

    Only a document the reader called a ``receipt`` is second-guessed. A file
    already set aside as a statement / summary / other keeps the reason it has:
    re-labelling it would make the reviewer's set-aside strip less truthful,
    and it is out of the expense pool either way.
    """
    if r.document_type != "receipt":
        return None
    if _has_itemization(r):
        return None
    marker = correspondence_marker(r.ocr_text)
    if marker is None:
        return None
    note = CORRESPONDENCE_NOTE
    return replace(
        r,
        document_type=CORRESPONDENCE,
        data_quality_note=(
            f"{r.data_quality_note}; {note}" if r.data_quality_note else note
        ),
    )
