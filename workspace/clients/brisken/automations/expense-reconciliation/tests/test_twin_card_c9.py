"""An invoice takes the card its own payment receipt prints (backlog item 204,
step 2; case 9, owner plan approved 2026-09-25).

A Stripe vendor mails two documents for one purchase: the INVOICE, which
prints no card, and the RECEIPT, which prints "Visa - 9693". The two carry
different numbers (`890D70BF-0034` / `2642-9215-3921`), so no reference group
holds them and `inherit_card_from_copies` lent nothing, although the grid
already marked the pair one document (rung 3: the receipt prints the
invoice's number). On September 2026 three invoices read "No legal entity
yet" beside a twin printing their card.

The lending now walks the groups the app SHOWS (`duplicates.lending_groups`:
the groups behind `expenses[].duplicate`), under the guards it always had:
every card-bearing copy names ONE card, a group ruled `ignore` lends nothing,
an operator-assigned hint on a member keeps it, entity lends only when exactly
one is named. Standing rulings: "a blank prompts Criss to look; a wrong card
silently books the receipt to the wrong entity and the wrong person" (item
173); every expense's company and person come through its card (item 40).

Route-level through `GET /api/expense-batches/{id}`, plus one re-match (the
bake) and one unit test for the guard a second group adds.
"""
from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import inherit_card_from_copies  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

CARDS = {
    "corp-2838": {
        "label": "Credit Card - 2838", "digits": ["2838"],
        "entity": "Corporate Services", "person": "Dirk Neumann - Corp Services",
        "currency": "USD",
    },
    "corp-3645": {
        "label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
        "entity": "Corporate Services", "person": "Dirk Neumann - Corp Services",
        "currency": "USD",
    },
    "corp-3876": {
        "label": "Credit Card Chase Visa - 3876", "digits": ["3876"],
        "entity": "Corporate Services", "person": "Nicolas Neumann",
        "currency": "USD",
    },
    "cons-1176": {
        "label": "Credit Card Chase Visa - 1176", "digits": ["1176"],
        "entity": "Consulting", "person": "Brisken Consulting", "currency": "USD",
    },
    "cloud-9693": {
        "label": "Credit Card Chase Visa - 9693", "digits": ["9693"],
        "entity": "Cloud Services", "person": "Brisken Cloud Services",
        "currency": "USD",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.put("/api/settings", json={
            "entities": {"Corporate Services": {}, "Consulting": {}, "Cloud Services": {}},
            "cards": CARDS,
        })
        assert resp.status_code == 200, resp.text
        yield c


def _extraction(vendor, total, day, reference, payment_hint=None):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
    )


def _wire(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("15.00"),
                reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _text_pdf(*lines: str) -> bytes:
    """A receipt PDF with a real text layer, so the ladder's rung 3 reads it."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 720
    for line in lines:
        c.drawString(60, y, line)
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


def _batch(client, files, legal_entity="", label="September 2026"):
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": legal_entity, "label": label},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (name, data, "application/octet-stream")) for name, data in files],
    ))
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _expense(grid, needle):
    return next(e for e in grid["expenses"] if needle in e["document_id"])


def _card_key(expense):
    return (expense.get("card") or {}).get("key")


# The two September 2026 shapes, as the live month holds them (read
# 2026-09-25): `0029`/`0030` Anthropic 184.35 on 9693, `0033`/`0034` Lovable
# 50.00 on 3645. The extractor read the receipt's own number, not the
# invoice's, so the pair twins only through the receipt's printed text.
STRIPE_PAIRS = [
    pytest.param(
        "Anthropic, PBC (@anthropic)", "184.35", "2026-09-11",
        "890D70BF-0034", "2642-9215-3921", "9693",
        "cloud-9693", "Cloud Services", "Brisken Cloud Services",
        id="anthropic-184.35-on-9693",
    ),
    pytest.param(
        "Lovable Labs Incorporated", "50.00", "2026-09-15",
        "HMVWDWIL-0032", "2811-8284-7349", "3645",
        "corp-3645", "Corporate Services", "Dirk Neumann - Corp Services",
        id="lovable-50-on-3645",
    ),
]


def _stripe_pair(monkeypatch, client, vendor, total, day, inv_ref, rcpt_ref,
                 digits, invoice_hint=None):
    _wire(
        monkeypatch,
        _extraction(vendor, total, day, inv_ref, payment_hint=invoice_hint),
        _extraction(vendor, total, day, rcpt_ref, payment_hint=f"Visa ...{digits}"),
    )
    return _batch(client, [
        (f"Invoice-{inv_ref}.pdf", _text_pdf(
            vendor, f"Invoice number {inv_ref}", f"Date of issue {day}",
            f"Amount due ${total} USD",
        )),
        (f"Receipt-{rcpt_ref}.pdf", _text_pdf(
            vendor, f"Receipt number {rcpt_ref}", f"Invoice number {inv_ref}",
            f"Date paid {day}", f"Amount paid ${total}", f"Visa - {digits}",
        )),
    ])


@pytest.mark.parametrize(
    "vendor,total,day,inv_ref,rcpt_ref,digits,card,entity,person", STRIPE_PAIRS,
)
def test_an_invoice_reads_the_card_entity_and_person_its_receipt_prints(
    client, monkeypatch, vendor, total, day, inv_ref, rcpt_ref, digits,
    card, entity, person,
):
    pytest.importorskip("reportlab")
    batch_id = _stripe_pair(
        monkeypatch, client, vendor, total, day, inv_ref, rcpt_ref, digits,
    )
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert group["basis"] == "printed_reference", "no reference group holds them"
    assert group["verdict"] == "copy"

    invoice = _expense(grid, "Invoice-")
    assert invoice["payment_hint"] == f"Visa ...{digits}"
    assert _card_key(invoice) == card
    assert invoice["legal_entity_id"] == entity
    assert invoice["entity_source"] == "card"
    assert invoice["person"] == person
    assert invoice["person_source"] == "card"
    assert invoice["duplicate"]["copy"] == 1, "the kept copy is the one that moved"
    assert grid["summary"]["n_needs_entity"] == 0

    # The export builds from `_expense_export_inputs`: the invoice row ships
    # under the twin's entity, not the placeholder.
    import csv

    resp = client.get(f"/runs/{batch_id}/expenses.csv")
    assert resp.status_code == 200, resp.text
    by_ref = {r["Reference#"]: r for r in csv.DictReader(io.StringIO(resp.text))}
    assert by_ref[inv_ref]["Legal Entity"] == entity


def test_a_vendor_date_twin_lends_its_card_too(client, monkeypatch):
    """Two scans of one till slip, neither with a usable number (July's
    Supermercado Fenix shape): the ladder decides them one copy on vendor,
    date, total and currency (rung 6), so the slip that printed the card
    lends it to the one that did not."""
    _wire(
        monkeypatch,
        _extraction("Supermercado Fenix", "325.88", "2026-07-11", "", payment_hint=None),
        _extraction("Supermercado Fenix", "325.88", "2026-07-11", "",
                    payment_hint="VISA x3876"),
    )
    batch_id = _batch(client, [
        ("0059__Receipt_Groceries_Fenix.jpg", JPG + b"0"),
        ("0072__CARD-127_Groceries_Fenix.jpg", JPG + b"1"),
    ], label="July 2026")
    grid = _grid(client, batch_id)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("vendor_date", "copy")
    slip = _expense(grid, "0059__")
    assert _card_key(slip) == "corp-3876"
    assert slip["person"] == "Nicolas Neumann"
    assert slip["legal_entity_id"] == "Corporate Services"


# ── negatives ──────────────────────────────────────────────────────────


def test_a_group_ruled_not_a_duplicate_lends_nothing(client, monkeypatch):
    pytest.importorskip("reportlab")
    batch_id = _stripe_pair(
        monkeypatch, client, "Anthropic, PBC (@anthropic)", "184.35",
        "2026-09-11", "890D70BF-0034", "2642-9215-3921", "9693",
    )
    (group,) = _grid(client, batch_id)["duplicate_groups"]
    resp = client.post(
        f"/api/runs/{batch_id}/duplicates/resolve",
        json={"group_id": group["group_id"], "resolution": "ignore"},
    )
    assert resp.status_code == 200, resp.text

    grid = _grid(client, batch_id)
    invoice = _expense(grid, "Invoice-")
    assert invoice["duplicate"] is None
    assert _card_key(invoice) is None
    assert invoice["legal_entity_id"] == ""
    assert invoice["person"] == ""
    assert grid["summary"]["n_needs_entity"] == 1


def test_copies_naming_different_cards_lend_nothing(client, monkeypatch):
    """One document number on three copies: the grid shows them one
    document (rung 2), but two copies print different cards, so the
    document does not say which card paid and the invoice stays blank."""
    _wire(
        monkeypatch,
        _extraction("Lovable Labs Incorporated", "50.00", "2026-09-15", "HMVWDWIL-0032"),
        _extraction("Lovable Labs Incorporated", "50.00", "2026-09-15", "HMVWDWIL0032",
                    payment_hint="Visa ...3645"),
        _extraction("Lovable Labs Incorporated", "50.00", "2026-09-15", "HMVWDWIL 0032",
                    payment_hint="Visa ...1176"),
    )
    batch_id = _batch(client, [
        ("Invoice-HMVWDWIL-0032.jpg", JPG + b"0"),
        ("Receipt-2811-8284-7349.jpg", JPG + b"1"),
        ("Receipt-2811-8284-7349-resent.jpg", JPG + b"2"),
    ])
    grid = _grid(client, batch_id)
    invoice = _expense(grid, "Invoice-")
    assert invoice["duplicate"] is not None, "the group IS shown"
    assert _card_key(invoice) is None
    assert invoice["legal_entity_id"] == ""
    assert invoice["person"] == ""


def test_three_invoices_the_ladder_keeps_apart_lend_nothing(client, monkeypatch):
    """The three OpenAI 80.12 invoices of 16 September 2026: one vendor, one
    day, one amount, three document numbers. The ladder decides them three
    purchases (rung 4), no row is marked a copy, and the card one of them
    prints (added here to make the negative bite) reaches neither other."""
    _wire(
        monkeypatch,
        _extraction("OpenAI", "80.12", "2026-09-16", "58596F4C-0059"),
        _extraction("OpenAI", "80.12", "2026-09-16", "58596F4C-0060",
                    payment_hint="credit card ending in ...9693"),
        _extraction("OpenAI", "80.12", "2026-09-16", "58596F4C-0061"),
    )
    batch_id = _batch(client, [
        ("0036__rendered-body.jpg", JPG + b"0"),
        ("0038__rendered-body.jpg", JPG + b"1"),
        ("0039__rendered-body.jpg", JPG + b"2"),
    ])
    grid = _grid(client, batch_id)
    assert all(e["duplicate"] is None for e in grid["expenses"])
    assert _card_key(_expense(grid, "0038__")) == "cloud-9693"
    for needle in ("0036__", "0039__"):
        row = _expense(grid, needle)
        assert _card_key(row) is None, needle
        assert row["legal_entity_id"] == "", needle


def test_an_operator_assigned_hint_on_a_member_survives(client, monkeypatch):
    """The invoice reads "Link". Unassigned, it borrows its receipt's 3645
    through the printed-reference group; once the operator assigns "Link" to
    card 1176 for this batch, the invoice keeps "Link" and resolves through
    the assignment, because the assignment is keyed on that stored string."""
    pytest.importorskip("reportlab")
    batch_id = _stripe_pair(
        monkeypatch, client, "Lovable Labs Incorporated", "50.00", "2026-09-15",
        "HMVWDWIL-0032", "2811-8284-7349", "3645", invoice_hint="Link",
    )
    invoice = _expense(_grid(client, batch_id), "Invoice-")
    assert _card_key(invoice) == "corp-3645", "borrowed while unassigned"

    resp = client.post(
        f"/api/expense-batches/{batch_id}/cards",
        json={"assignments": [{"hint": "Link", "card": "cons-1176"}]},
    )
    assert resp.status_code == 200, resp.text
    invoice = _expense(_grid(client, batch_id), "Invoice-")
    assert invoice["payment_hint"] == "Link"
    assert _card_key(invoice) == "cons-1176"
    assert invoice["legal_entity_id"] == "Consulting"
    assert invoice["person"] == "Brisken Consulting"


# ── the re-match: the kept invoice leaves a stranger card's scope ─────────


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_the_re_match_keeps_the_invoice_off_another_cards_charge(client, monkeypatch):
    """The matcher pool: item 56 keeps the INVOICE copy and sets the receipt
    aside, so before this build the pool's only copy named no card and took
    the first same-amount charge on the batch's statement. It now carries
    9693 (Cloud Services), and a 2838 charge of 184.35 is no candidate."""
    pytest.importorskip("reportlab")
    batch_id = _stripe_pair(
        monkeypatch, client, "Anthropic, PBC (@anthropic)", "184.35",
        "2026-09-11", "890D70BF-0034", "2642-9215-3921", "9693",
    )
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("September2026.xlsx", _xlsx([
            (datetime(2026, 9, 12), "ANTHROPIC", "Sale", -184.35),
        ]), XLSX)},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    _done(client, resp)
    view = client.get(f"/api/runs/{batch_id}").json()
    assert view["summary"]["n_reconciled"] == 0
    (row,) = [r for r in view["rows"] if r["vendor"] == "ANTHROPIC"]
    assert row["chosen_document_id"] is None
    assert row["candidates"] == [], "a Cloud Services invoice is no candidate here"


# ── unit: a document two shown groups would lend two cards gets none ─────


def _receipt(doc, ref, vendor="Lovable", day=date(2026, 9, 15), payment_mode=None,
             entity=""):
    return Receipt(
        document_id=doc, legal_entity_id=entity, detected_date=day,
        detected_total=Decimal("50.00"), detected_currency="USD",
        detected_vendor=vendor, detected_reference=ref, payment_mode=payment_mode,
    )


def test_a_document_two_groups_would_lend_two_cards_receives_neither():
    """`x` is the vendor/date twin of `a` (9693, Cloud Services) and the
    reference twin of `b` (1176, Consulting). Either card could be right;
    a blank prompts Criss to look, a guess books the wrong entity."""
    x = _receipt("x", "AAAA1111-2222")
    a = _receipt("a", "", payment_mode="Visa ...9693", entity="Cloud Services")
    b = _receipt("b", "AAAA11112222", vendor="Lovable (@lovable)",
                 day=date(2026, 9, 16), payment_mode="Visa ...1176",
                 entity="Consulting")
    torn = {r.document_id: r for r in inherit_card_from_copies([x, a, b])}
    assert torn["x"].payment_mode is None
    assert torn["x"].legal_entity_id == ""
    # Each group alone lends.
    alone = {r.document_id: r for r in inherit_card_from_copies([x, a])}
    assert alone["x"].payment_mode == "Visa ...9693"
    assert alone["x"].legal_entity_id == "Cloud Services"
    alone = {r.document_id: r for r in inherit_card_from_copies([x, b])}
    assert alone["x"].payment_mode == "Visa ...1176"
