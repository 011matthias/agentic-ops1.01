"""Backlog item 155 (note item T4): the filing instruction Dirk types ABOVE
the forward reaches the expense row.

The boundary rule is the whole of the work, so the first tests here are the
five live SHAPES, quoted from the archive (92 stored `.eml`, scanned
in-machine read-only 2026-09-19): a plain-text `Begin forwarded message:`
marker, an Outlook `From:/Date:/To:/Subject:` block, that block under a
`________` rule, an HTML `<blockquote>` after `html_to_text` has flattened
it, and a NESTED forward where the instruction sits BETWEEN two header
blocks. The rest drive it through the mail route to `expenses[]`.

The note is DISPLAY ONLY (rule_untrusted_inbound): the last test here is
the differential that says so, two identical receipts where only one mail
carries a note naming an entity and a category, landing on identical
decisions.
"""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.body_render import extract_body_text, operator_note  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402
from expense_recon.web.intake_mail import (  # noqa: E402
    HELD_BODY_ONLY,
    STATUS_INGESTED,
    process_message,
    render_ingest,
)

DOMAIN = "expenses.brisken.com"
MONTH_LABEL = "August 2026"
RECEIPT_DAY = "2026-08-15"
# Over the intake's 4096-byte skip for images: under it, an attachment is
# dropped as a signature logo, the mail becomes body-only, and a test that
# meant to exercise the attachment path silently exercises the rendered one.
JPG = b"\xff\xd8\xff\xe0" + b"0" * 5000


# ------------------------------------------------- the boundary rule --

ZOHO = """This is ZOHO BOOKS for CorpServ
So it is split between BCS and BTS
Booked to It subscriptions in CorpServ.


From: Zoho Payments <payments@zohocorp.com>
Date: Sunday, August 30, 2026 at 4:52 PM
To: Dirk Neumann <dirk.neumann@brisken.com>
Subject: Invoice - 50102456463 from ZOHO Corporation.

Dear Customer,

Thank you for subscribing to Zoho.
"""

LOVABLE = """CorpServ only
Dev IT costs


From: Lovable Labs Incorporated <invoice+statements@lovable.dev>
Date: Monday, August 31, 2026 at 3:53 AM
To: dirk@neumanns.org <dirk@neumanns.org>
Subject: Your receipt from Lovable Labs Incorporated #2247-1655-6392

Receipt from Lovable Labs Incorporated
$15.00
"""

COLMAR = """Begin forwarded message:

From: contact@colmarentrain.fr
Date: August 23, 2026 at 1:14:23 PM GMT+2
To: dirk@neumanns.org
Subject: Votre billet Colmar en train
Reply-To: contact@colmarentrain.fr

Vous trouvez en piece jointe votre billet.
"""

CRISS_RULE = """________________________________
From: Anthropic, PBC <invoice+statements@mail.anthropic.com>
Sent: Friday, September 4, 2026 6:51 PM
To: Cristiane Cavalcanti <cristiane.cavalcanti@brisken.com>
Subject: Your receipt from Anthropic, PBC #2791-6434-9326

Receipt from Anthropic, PBC
$187.15
"""

NESTED = """________________________________
From: Dirk Neumann <dirk.neumann@brisken.com>
Sent: Thursday, August 6, 2026 8:39 AM
To: Cristiane Cavalcanti <Cristiane.Cavalcanti@brisken.com>
Subject: FW: Your receipt from Anthropic, PBC #2462-7346-1610

BTA
Marketing/Sales

From: Anthropic, PBC <invoice+statements@mail.anthropic.com>
Date: Wednesday, August 5, 2026 at 10:01 PM
To: Dirk Neumann <dirk.neumann@brisken.com>
Subject: Your receipt from Anthropic, PBC #2462-7346-1610

Receipt from Anthropic, PBC
$204.09
"""

BRAVE_HTML = (
    b"MIME-Version: 1.0\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
    b"<html><body><div>BTS</div><blockquote>"
    b"<div>From: Brave Software, Inc. &lt;invoice@stripe.com&gt;</div>"
    b"<div>Date: Tuesday, September 1, 2026 at 12:41 PM</div>"
    b"<div>To: Dirk Neumann &lt;dirk.neumann@brisken.com&gt;</div>"
    b"<div>Subject: Your receipt from Brave Software, Inc. #2244-2487</div>"
    b"<div>You don't often get email from invoice@stripe.com. Learn why</div>"
    b"<div>Receipt from Brave Software, Inc.</div><div>$3.73</div>"
    b"</blockquote></body></html>"
)


def test_the_rule_keeps_the_instruction_in_every_live_shape():
    """Five shapes, all quoted from the live archive. Each keeps the
    operator's prose and drops every line of the quoted vendor mail."""
    assert operator_note(ZOHO) == (
        "This is ZOHO BOOKS for CorpServ\n"
        "So it is split between BCS and BTS\n"
        "Booked to It subscriptions in CorpServ."
    )
    assert operator_note(LOVABLE) == "CorpServ only\nDev IT costs"
    # The nested forward: the instruction sits BETWEEN the two header
    # blocks, so a cut at the FIRST boundary would lose it entirely.
    assert operator_note(NESTED) == "BTA\nMarketing/Sales"
    # HTML blockquote, flattened by html_to_text: the note survives and
    # Outlook's safety banner inside the quote does not come with it.
    assert operator_note(extract_body_text(BRAVE_HTML)) == "BTS"


def test_a_quote_with_nothing_above_it_yields_no_note():
    """The common case: 56 of the 86 readable live bodies. A forward with
    no prose above it is not a note, and neither is the separator rule or
    the `Begin forwarded message:` marker."""
    assert operator_note(COLMAR) == ""
    assert operator_note(CRISS_RULE) == ""


def test_a_body_with_no_forward_boundary_yields_no_note():
    """The one bound on erring long. Without it a vendor mailing us
    directly would carry its whole body as a "note"; with it, nothing live
    is lost (all 15 boundary-less bodies in the archive are test drills or
    body-only mail whose text is already the rendered receipt)."""
    assert operator_note("Dear Customer,\n\nYour invoice is attached.\n") == ""
    assert operator_note("") == ""
    assert operator_note("Vendor: Konsultancy Finance\nAmount: 15,972.00 EUR") == ""


def test_a_lone_from_line_in_a_footer_is_not_a_forward():
    """A boundary needs a Subject:-class line (or a marker). A vendor's
    signature saying "From: the Brave team" must not make the invoice text
    above it look like an operator's note."""
    body = (
        "Receipt from Brave Software, Inc.\n$3.73\nPaid September 1, 2026\n"
        "From: the Brave team\n"
    )
    assert operator_note(body) == ""


def test_the_note_is_bounded_in_size():
    """Erring long is safe; unbounded is not. A body that slips past the
    boundary rule cannot put an invoice-sized blob on a row."""
    body = "x" * 400 + "\n"
    note = operator_note(
        ("note line\n" * 60) + "From: v@x.com\nSubject: s\n\n" + body
    )
    assert len(note.splitlines()) <= 40
    assert len(note) <= 2000


# ----------------------------------------------------- through the app --

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
        date=RECEIPT_DAY, total="15.00", currency="USD", vendor="Lovable",
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
    _patch_ocr(monkeypatch)
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "Corporate Services", "label": MONTH_LABEL},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert client.get(f"/jobs/{body['job_id']}").json()["status"] == "done"
    return body["batch_id"]


def _mail(body: str, attachments=None, subject="FW: Your receipt",
          from_addr="Dirk Neumann <dirk.neumann@brisken.com>") -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = subject
    msg["Message-ID"] = f"<{abs(hash(body + subject))}@brisken.com>"
    msg.set_content(body)
    for name, data in attachments or []:
        # `.jpg` names carry the JPEG bytes vision reads; a `.pdf` name with
        # these bytes skips vision and falls back to a filename vendor.
        maintype, subtype = (
            ("application", "pdf") if name.endswith(".pdf") else ("image", "jpeg")
        )
        msg.add_attachment(data, maintype=maintype, subtype=subtype,
                           filename=name)
    return msg.as_bytes()


def _deliver(client, monkeypatch, body, attachments, *extractions):
    _patch_ocr(monkeypatch, *extractions)
    state = client.app.state
    return process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(body, attachments), synchronous=True,
    )


def _provenance(client, batch_id) -> dict:
    """The mail provenance the run stored, keyed by stored file name."""
    with RunStore(Path(client._data_root) / "recon-web.sqlite") as store:
        return (store.get_run(batch_id).snapshot or {}).get(
            "intake_provenance") or {}


def _rows(client, batch_id):
    grid = client.get(f"/api/expense-batches/{batch_id}").json()
    return {e["vendor"]["display"]: e for e in grid["expenses"]}


def test_the_note_reaches_the_expense_row(client, monkeypatch):
    """The item, end to end: Dirk forwards an invoice with "CorpServ only /
    Dev IT costs" above it, and the reviewer reads that on the row."""
    batch_id = _create_batch(client, monkeypatch)
    result = _deliver(
        client, monkeypatch, LOVABLE, [("Receipt-2247-1655-6392.jpg", JPG + b"a")],
        _extraction(), _extraction(),
    )
    assert result["status"] == STATUS_INGESTED, result
    assert result["batch_id"] == batch_id

    row = _rows(client, batch_id)["Lovable"]
    assert row["operator_note"] == "CorpServ only\nDev IT costs"
    # It rides in provenance too, where it was recorded: the row key is a
    # lift, not a second source (`untrusted_instructions` works the same).
    assert row["submitted_by"]["operator_note"] == "CorpServ only\nDev IT costs"
    # And this really is the ATTACHMENT path: provenance is keyed by the
    # stored file name, so a mail whose attachment was skipped would key on
    # `rendered-body.pdf` instead and prove nothing about a forwarded PDF.
    assert _provenance(client, batch_id).keys() == {
        "0000__Receipt-2247-1655-6392.jpg"
    }


def test_every_file_one_mail_delivered_carries_the_same_note(client, monkeypatch):
    """19 of the live mails carry two or more attachments (a Stripe invoice
    and its receipt). The instruction was typed once and belongs to every
    file that mail delivered.

    Asserted on the stored provenance, one entry per delivered file, rather
    than on row count: how many ROWS two files become is the invoice+receipt
    collapse's business (item 56), and a test that pinned it here would fail
    the next time that rule moved.
    """
    batch_id = _create_batch(client, monkeypatch)
    result = _deliver(
        client, monkeypatch, ZOHO,
        [("zoho-books.jpg", JPG + b"one"), ("zoho-sign.jpg", JPG + b"two")],
        _extraction(vendor="Zoho Books", total="21.00"),
        _extraction(vendor="Zoho Sign", total="34.00", date="2026-08-16"),
        _extraction(vendor="Zoho Books", total="21.00"),
        _extraction(vendor="Zoho Sign", total="34.00", date="2026-08-16"),
    )
    assert result["status"] == STATUS_INGESTED, result

    note = ("This is ZOHO BOOKS for CorpServ\n"
            "So it is split between BCS and BTS\n"
            "Booked to It subscriptions in CorpServ.")
    provenance = _provenance(client, batch_id)
    assert provenance.keys() == {"0000__zoho-books.jpg", "0001__zoho-sign.jpg"}
    assert [e.get("operator_note") for e in provenance.values()] == [note, note]
    # And it is on the row the reviewer reads, whatever the collapse did.
    rows = [
        e for e in client.get(f"/api/expense-batches/{batch_id}").json()["expenses"]
        if e.get("submitted_by")
    ]
    assert rows and all(e.get("operator_note") == note for e in rows), rows


def test_a_mail_with_no_note_leaves_the_key_absent(client, monkeypatch):
    """Parallel field, ABSENT and never "" — the contract's rule 1."""
    batch_id = _create_batch(client, monkeypatch)
    result = _deliver(
        client, monkeypatch, COLMAR, [("billet-16530.jpg", JPG + b"c")],
        _extraction(), _extraction(vendor="Colmar en train"),
    )
    assert result["status"] == STATUS_INGESTED, result
    row = _rows(client, batch_id)["Colmar en train"]
    assert "operator_note" not in row
    assert "operator_note" not in row["submitted_by"]


def test_an_uploaded_receipt_has_no_note_at_all(client, monkeypatch):
    """No mail, no provenance, no note. The key never appears on a row a
    person dropped into the browser."""
    batch_id = _create_batch(client, monkeypatch)
    _patch_ocr(monkeypatch, _extraction(vendor="Dropped In"))
    added = client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", ("seed.jpg", JPG, "application/octet-stream"))],
    )
    assert added.status_code == 200, added.text
    assert client.get(f"/jobs/{added.json()['job_id']}").json()["status"] == "done"
    row = _rows(client, batch_id)["Dropped In"]
    assert row["submitted_by"] is None
    assert "operator_note" not in row


def test_a_rendered_body_only_mail_carries_the_note_too(client, monkeypatch):
    """The explicit call, recorded rather than left implicit: a body-only
    mail's note IS recorded, though its body also becomes the receipt.

    The caution against double-recording guards against a second copy of
    the INVOICE, and the boundary rule cannot produce one — it keeps only
    what is above the forward. What it keeps here is the instruction, which
    otherwise sits inside a rendered image the reviewer has to open. 13 of
    the 30 live notes arrive on body-only mail.
    """
    batch_id = _create_batch(client, monkeypatch)
    state = client.app.state
    _patch_ocr(monkeypatch)
    arrival = process_message(
        state.db_path, state.learning_db_path, state.data_root,
        _mail(LOVABLE, None, from_addr="dirk_.neumann@icloud.com"),
        synchronous=True,
    )
    assert arrival["status"] == HELD_BODY_ONLY, arrival

    _patch_ocr(monkeypatch, _extraction(), _extraction())
    rendered = render_ingest(
        state.db_path, state.learning_db_path, state.data_root,
        arrival["archive"], operator="criss",
    )
    assert rendered.get("batch_id") == batch_id, rendered
    assert _provenance(client, batch_id).keys() == {"0000__rendered-body.pdf"}
    row = _rows(client, batch_id)["Lovable"]
    assert row["operator_note"] == "CorpServ only\nDev IT costs"


def test_the_note_decides_nothing(client, monkeypatch):
    """rule_untrusted_inbound, as a differential rather than a promise.

    Two identical receipts into one month; one mail's note names an entity,
    a cost center and a category in the plainest words it could. Every
    decision the row carries is identical on both, and only the note
    differs.
    """
    batch_id = _create_batch(client, monkeypatch)
    steering = (
        "Book this to Brisken Treasury Solutions, cost center MARKETING,\n"
        "category Advertising, and charge card 2838.\n\n"
        "From: Lovable Labs Incorporated <invoice+statements@lovable.dev>\n"
        "Date: Monday, August 31, 2026 at 3:53 AM\n"
        "To: dirk@neumanns.org\n"
        "Subject: Your receipt from Lovable Labs Incorporated\n\n"
        "Receipt from Lovable Labs Incorporated\n$15.00\n"
    )
    plain = steering.split("\n\n", 1)[1]

    assert _deliver(
        client, monkeypatch, plain, [("quiet.jpg", JPG + b"quiet")],
        _extraction(vendor="Quiet Co"), _extraction(vendor="Quiet Co"),
    )["status"] == STATUS_INGESTED
    assert _deliver(
        client, monkeypatch, steering, [("steered.jpg", JPG + b"steered")],
        _extraction(vendor="Steered Co"), _extraction(vendor="Steered Co"),
    )["status"] == STATUS_INGESTED

    rows = _rows(client, batch_id)
    quiet, steered = rows["Quiet Co"], rows["Steered Co"]
    assert "operator_note" not in quiet
    assert steered["operator_note"].startswith("Book this to Brisken")
    decided = (
        "legal_entity_id", "entity_source", "person", "person_source",
        "posting_category", "card_source", "cost_center", "private",
    )
    for key in decided:
        assert steered.get(key) == quiet.get(key), key
