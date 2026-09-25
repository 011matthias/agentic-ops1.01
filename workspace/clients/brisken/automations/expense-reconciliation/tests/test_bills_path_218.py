"""Build 4 / backlog item 218 (owner decisions 2026-09-25): invoices paid by
bank transfer leave the card queue for a Bills section.

July 2026 held four invoices no card paid, each waiting in the card queue for
a statement that will never cover it. The owner decided:

1. Destination: a Bills section inside the month. A bill row stays visible,
   leaves the card counts, the "waits for statement" count, `expenses.csv`
   and the Zoho journal, and is exported as its own `bills.csv`.
2. Trigger: a row moves by itself only when the document's stated payment
   method reads as a bank payment and names no card, or when the reviewer's
   item-62 disposition says bank transfer. Printed bank details alone earn a
   suggestion, never a move. A person can move any row either way.

Route-level through the real routes: the receipts drop, the mail intake,
the Expenses and Matching payloads, the field PUT, the settled-outside
route and the three downloads. Every value is synthetic TEST data (no real
account number, IBAN, SWIFT/ABA code or supplier text). Fixtures are copied
from test_receipts_drop / test_case9_status_c9 / test_settled_outside, never
imported (a shared fixture import is an F811 in CI).
"""
from __future__ import annotations

import calendar
import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from email.message import EmailMessage

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon import payment_path as pp  # noqa: E402
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.output.bills_csv import BILL_COLUMNS  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0" + b"x" * 5000
# The drop and the mail both clamp a printed date against today, so the
# fixture month is last month, never a literal.
DAY = date.today().replace(day=1) - timedelta(days=20)
MONTH = f"{DAY.year:04d}-{DAY.month:02d}"
LABEL = f"{calendar.month_name[DAY.month]} {DAY.year}"
DOMAIN = "expenses.brisken.com"

WIRE_VENDOR = "TEST Consultoria Ltda"
IBAN_TEXT = "Remit to TEST Bank\nIBAN LU00 TEST 0000 0000 0000\nThank you"
# The remittance line alone. The real reminder's "our records show ...
# remains unpaid" sets it aside as correspondence before any of this runs
# (`correspondence.py`), so the route test keeps only the line that reaches
# the grid; the unit test holds the full wording.
REMINDER_TEXT = "Please send payment remittance to TEST Cloud Inc., PO Box 0000."

FAMILY = {
    "card-2838": {"label": "Credit Card - 2838", "digits": ["2838"],
                  "entity": "Corporate Services"},
    "3645": {"label": "Credit Card Chase Visa - 3645", "digits": ["3645"],
             "entity": "Corporate Services", "parent": "card-2838"},
}
CYCLE = {"card-9693": {"label": "BCS Chase Visa - 9693", "digits": ["9693"],
                       "entity": "Consulting"}}


def _extraction(day, total, currency, vendor, hint=None, notes=""):
    return ExtractedReceipt(
        date=str(day), total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes=notes,
        payment_hint=hint,
    )


def _wire_bill(day=DAY):
    return _extraction(day, "27203.34", "BRL", WIRE_VENDOR, hint="Wire Transfer")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_INTAKE_SMTP", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    with TestClient(create_app(tmp_path)) as c:
        c._data_root = tmp_path
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1,
                implied_rate=1.0, converted_amount=Decimal("0"),
                reasoning="mock",
            )
        ] * 40,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _patch_ocr_by_name(monkeypatch, mapping):
    """Answer each read by the FILE being read (the drop reads on a pool)."""
    class _ByName(MockLLMClient):
        def extract_receipt(self, *, file_name, images=None, text=None):
            for name, extraction in mapping.items():
                if str(file_name).endswith(name):
                    return extraction
            raise AssertionError(f"unbudgeted read of {file_name!r}")

    mock = _ByName()
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, label, files) -> str:
    """A company month holding `files` (name, bytes), added through the add
    route in one call, extraction order = file order."""
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    if files:
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/receipts",
            files=[("files", (n, b, "application/octet-stream")) for n, b in files],
        ))
    return batch_id


def _statement(client, batch_id, rows):
    body = "Date,Amount,Vendor,Card\n" + "".join(
        f"{d},{a},{v},{c}\n" for d, a, v, c in rows
    )
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": ("export.csv", body.encode(), "application/octet-stream")},
        data={
            "account_id": "chase-2838",
            "account_legal_entities": '{"chase-2838": "Corporate Services"}',
            "account_card_currency": "USD",
            "map_transaction_date": "Date",
            "map_amount": "Amount",
            "map_vendor": "Vendor",
            "map_card": "Card",
        },
    )
    _done(client, resp)


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _run(client, batch_id) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _rows(view) -> dict[str, dict]:
    return {str((e["vendor"] or {}).get("display")): e for e in view["expenses"]}


def _put_path(client, batch_id, doc, value):
    return client.put(
        f"/api/runs/{batch_id}/expenses/{doc}",
        json={"field": "payment_path", "value": value},
    )


def _csv(client, path) -> list[list[str]]:
    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    return list(csv.reader(io.StringIO(resp.text)))


def _assert_bill(row, source):
    """Everything a bill row says, in one place."""
    assert row["payment_path"] == "bill"
    assert row["payment_path_source"] == source
    assert row["counts_in_total"] is False
    assert row["boxes"] == [], "a bill is in no box"
    assert "waits_for_statements" not in row
    assert "card_suggestion" not in row
    assert "bill_suggestion" not in row
    assert row["can_mark_private"] is False
    assert row["review"]["state"] == "none"
    assert row["review"]["reason_code"] == "bill"
    assert row["review"]["reason"], "rule 5: the English label rides beside the code"


def _assert_invariant(summary):
    assert summary["n_receipts"] == (
        summary["n_expenses"] + summary["n_copies_set_aside"] + summary["n_bills"]
    )


# ── 1. the drop ─────────────────────────────────────────────────────────


def test_a_dropped_wire_invoice_lands_in_its_month_as_a_bill(client, monkeypatch):
    _patch_ocr_by_name(monkeypatch, {
        "wire-invoice.jpg": _wire_bill(),
        "staples.jpg": _extraction(DAY, "42.50", "USD", "Staples TEST", hint="Visa ...3645"),
    })
    resp = client.post(
        "/api/receipts",
        files=[
            ("files", ("wire-invoice.jpg", JPG + b"w", "application/octet-stream")),
            ("files", ("staples.jpg", JPG + b"s", "application/octet-stream")),
        ],
    )
    result = _done(client, resp)["result"]
    assert result["n_filed"] == 2, result
    (entry,) = result["months"]
    assert entry["month"] == MONTH
    batch_id = entry["batch_id"]

    grid = _grid(client, batch_id)
    rows = _rows(grid)
    _assert_bill(rows[WIRE_VENDOR], "stated")
    card = rows["Staples TEST"]
    assert card["payment_path"] == "card" and card["payment_path_source"] == ""
    assert "counts_in_total" not in card

    summary = grid["summary"]
    assert summary["n_bills"] == 1
    assert summary["bills_by_ccy"] == {"BRL": "27,203.34"}
    assert summary["totals_by_ccy"] == {"USD": "42.50"}, "the bill is out of the total"
    assert summary["n_expenses"] == 1
    _assert_invariant(summary)
    assert summary["n_review"] == sum(
        1 for e in grid["expenses"]
        if e["payment_path"] == "card" and e["review"]["state"] in ("check", "pick")
    )
    strip_docs = {
        d for g in grid["card_review"]["unresolved_hints"] for d in g["documents"]
    }
    assert rows[WIRE_VENDOR]["document_id"] not in strip_docs, (
        "the strip asks which card paid; a bill has none"
    )

    expenses_csv = _csv(client, f"/runs/{batch_id}/expenses.csv")
    assert not any(WIRE_VENDOR in cell for line in expenses_csv for cell in line)
    assert any("Staples TEST" in cell for line in expenses_csv for cell in line)

    bills = _csv(client, f"/runs/{batch_id}/bills.csv")
    assert tuple(bills[0]) == BILL_COLUMNS
    (bill,) = [dict(zip(BILL_COLUMNS, line)) for line in bills[1:]]
    assert bill["Supplier"] == WIRE_VENDOR
    assert bill["Amount"] == "27203.34"
    assert bill["Currency"] == "BRL"
    assert bill["Date"] == DAY.isoformat()
    assert bill["How decided"] == pp.HOW_DECIDED["stated"]
    assert bill["Evidence"] == "Wire Transfer"
    assert bill["Document"].endswith("wire-invoice.jpg")
    # The /api spelling serves the same file.
    assert _csv(client, f"/api/runs/{batch_id}/bills.csv") == bills

    # The months list counts what the page counts.
    listed = next(
        b for b in client.get("/api/expense-batches").json()["batches"]
        if b.get("run_id", b.get("id")) == batch_id
    )
    assert listed["summary"]["n_bills"] == 1
    assert listed["summary"]["n_expenses"] == 1


# ── 2. the mail intake ──────────────────────────────────────────────────


def test_a_mailed_wire_invoice_is_a_bill_too(client, monkeypatch):
    from expense_recon.web.intake_mail import STATUS_INGESTED, process_message

    _patch_ocr(monkeypatch)
    batch_id = _month(client, LABEL, [])
    # Two reads: the arrival read that decides the month, then the ingest.
    _patch_ocr(monkeypatch, _wire_bill(), _wire_bill())
    msg = EmailMessage()
    msg["From"] = "TEST Sender <test.sender@brisken.com>"
    msg["To"] = f"receipts@{DOMAIN}"
    msg["Subject"] = "TEST invoice"
    msg["Message-ID"] = "<bills-218@brisken.com>"
    msg.set_content("invoice attached")
    msg.add_attachment(JPG + b"mail", maintype="image", subtype="jpeg",
                       filename="mailed-invoice.jpg")
    state = client.app.state
    result = process_message(
        state.db_path, state.learning_db_path, state.data_root, msg.as_bytes(),
        synchronous=True,
    )
    assert result["status"] == STATUS_INGESTED, result
    assert result["batch_id"] == batch_id

    grid = _grid(client, batch_id)
    (row,) = grid["expenses"]
    _assert_bill(row, "stated")
    assert grid["summary"]["n_bills"] == 1
    assert grid["summary"]["n_expenses"] == 0
    assert grid["summary"]["totals_by_ccy"] == {}
    _assert_invariant(grid["summary"])


# ── 3. after the statement: the Matching payload lets it go ─────────────


def _july_with_statement(client, monkeypatch, *, cards, extra=(), rows=None):
    """July 2026: Staples (settles the STAPLES charge), the wire bill, and
    `extra` receipts after them."""
    readings = [
        _extraction("2026-07-01", "42.50", "USD", "Staples TEST"),
        _wire_bill("2026-07-20"),
        *[e for _n, e in extra],
    ]
    _patch_ocr(monkeypatch, *readings)
    assert client.put("/api/settings", json={"cards": cards}).status_code == 200
    batch_id = _month(client, "July 2026", [
        ("staples.jpg", JPG + b"s"), ("wire.jpg", JPG + b"w"),
        *[(n, JPG + n.encode()) for n, _e in extra],
    ])
    _statement(client, batch_id, rows or (("2026-07-01", "42.50", "STAPLES", "2838"),))
    return batch_id


def test_the_matching_payload_drops_the_bill_from_every_open_list(client, monkeypatch):
    batch_id = _july_with_statement(
        client, monkeypatch, cards={**FAMILY, **CYCLE},
        extra=[
            ("acme.jpg", _extraction("2026-07-15", "88.00", "USD", "Acme TEST")),
            ("uber.jpg", _extraction("2026-07-31", "15.00", "USD", "Uber TEST",
                                     hint="Visa ...3645")),
        ],
        rows=(
            ("2026-07-01", "42.50", "STAPLES", "2838"),
            ("2026-07-31", "15.00", "UBER", "3645"),
        ),
    )
    grid = _grid(client, batch_id)
    grid_rows = _rows(grid)
    bill = grid_rows[WIRE_VENDOR]
    _assert_bill(bill, "stated")
    # The control: a card-less row with no bill signal still waits.
    assert "BCS Chase Visa - 9693" in grid_rows["Acme TEST"]["waits_for_statements"]
    # The card tabs: two cards, so they render, and no tab lists the bill.
    assert bill["card_section"] == "" and bill["without_charge"] is False
    no_card = next(s for s in grid["card_sections"] if s["key"] == "")
    assert no_card["n_receipts"] == 1 and no_card["n_expenses"] == 1, (
        "Acme only, never the bill"
    )

    run = _run(client, batch_id)
    unmatched = {r["document_id"] for r in run["unmatched_receipts"]}
    assert bill["document_id"] not in unmatched
    assert grid_rows["Acme TEST"]["document_id"] in unmatched
    summary = run["summary"]
    assert summary["n_receipts_need_charge"] == 1, "Acme only, never the bill"
    assert summary["n_bills"] == 1
    assert summary["bills_by_ccy"] == {"BRL": "27,203.34"}
    assert summary["n_settled_outside"] == 0, "stored dispositions only"

    # The journal and the reconciled CSV are per statement line; a bill holds
    # none, so neither can carry it.
    for path in (f"/runs/{batch_id}/zoho.csv", f"/runs/{batch_id}/reconciled.csv"):
        lines = _csv(client, path)
        assert not any(WIRE_VENDOR in cell for line in lines for cell in line), path


def test_a_bill_never_blocks_month_complete(client, monkeypatch):
    batch_id = _july_with_statement(client, monkeypatch, cards=FAMILY)
    run = _run(client, batch_id)
    (row,) = [r for r in run["rows"] if r["effective_bucket"] != "unmatched"]
    resp = client.post(f"/api/runs/{batch_id}/decisions", json={
        "transaction_id": row["transaction_id"], "status": "confirmed",
        "chosen_document_id": row["chosen_document_id"],
    })
    assert resp.status_code == 200, resp.text
    summary = _run(client, batch_id)["summary"]
    assert summary["n_receipts_need_charge"] == 0
    assert summary["n_bills"] == 1
    assert summary["month_complete"] is True, summary


def _pdf_text(client, path) -> str:
    from pypdf import PdfReader

    resp = client.get(path)
    assert resp.status_code == 200, resp.text
    return "\n".join(
        p.extract_text() or "" for p in PdfReader(io.BytesIO(resp.content)).pages
    )


def test_the_reports_list_the_bill_in_its_own_section(client, monkeypatch):
    batch_id = _july_with_statement(client, monkeypatch, cards=FAMILY)

    report = _pdf_text(client, f"/runs/{batch_id}/expense-report.pdf")
    listing, _sep, rest = report.partition("Bills (paid by bank transfer)")
    assert rest, "the month report has a Bills section"
    assert "1 expenses · USD 42.50" in listing, "the month's total leaves it out"
    assert WIRE_VENDOR not in listing and "BRL" not in listing
    assert WIRE_VENDOR in rest
    assert "Bills total: BRL 27,203.34" in rest
    assert "bill, paid by bank transfer" in rest, "its receipt page stays in"

    recon = _pdf_text(client, f"/runs/{batch_id}/reconciliation-report.pdf")
    assert f"Paid by bank transfer · {WIRE_VENDOR}" in recon


# ── 4. a person moves a row, either way ─────────────────────────────────


def test_a_person_moves_a_card_less_row_to_bills_and_back(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction("2026-07-15", "15972.00", "EUR", "TEST Finance"),
        _wire_bill("2026-07-20"),
    )
    batch_id = _month(client, "July 2026", [("fin.jpg", JPG + b"f"), ("wire.jpg", JPG + b"w")])
    rows = _rows(_grid(client, batch_id))
    fin, wire = rows["TEST Finance"], rows[WIRE_VENDOR]
    assert fin["payment_path"] == "card"

    resp = _put_path(client, batch_id, fin["document_id"], "bill")
    assert resp.status_code == 200, resp.text
    grid = _grid(client, batch_id)
    fin = _rows(grid)["TEST Finance"]
    _assert_bill(fin, "person")
    assert "payment_path" in fin["edited_fields"]
    assert grid["summary"]["n_bills"] == 2
    assert grid["summary"]["bills_by_ccy"] == {"BRL": "27,203.34", "EUR": "15,972.00"}

    # The stated-wire row moved to the card queue by hand.
    assert _put_path(client, batch_id, wire["document_id"], "card").status_code == 200
    grid = _grid(client, batch_id)
    wire = _rows(grid)[WIRE_VENDOR]
    assert wire["payment_path"] == "card" and wire["payment_path_source"] == "person"
    assert "counts_in_total" not in wire and wire["boxes"]
    assert grid["summary"]["totals_by_ccy"] == {"BRL": "27,203.34"}
    assert grid["summary"]["n_bills"] == 1
    _assert_invariant(grid["summary"])

    # A clear hands the row back to what the document says.
    assert _put_path(client, batch_id, wire["document_id"], None).status_code == 200
    _assert_bill(_rows(_grid(client, batch_id))[WIRE_VENDOR], "stated")


def test_a_row_a_charge_holds_cannot_move_to_bills(client, monkeypatch):
    batch_id = _july_with_statement(client, monkeypatch, cards=FAMILY)
    staples = _rows(_grid(client, batch_id))["Staples TEST"]
    resp = _put_path(client, batch_id, staples["document_id"], "bill")
    assert resp.status_code == 400
    assert resp.json()["code"] == "bill_held_by_charge"
    staples = _rows(_grid(client, batch_id))["Staples TEST"]
    assert "payment_path" not in staples["edited_fields"]
    assert staples["payment_path"] == "card"

    resp = _put_path(client, batch_id, staples["document_id"], "sometimes")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_payment_path"


# ── 5. the item-62 disposition ──────────────────────────────────────────


def test_a_bank_transfer_disposition_makes_a_bill_and_cash_does_not(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction("2026-07-15", "15972.00", "EUR", "TEST Finance"),
        _extraction("2026-07-16", "30.00", "EUR", "TEST Kiosk"),
    )
    batch_id = _month(client, "July 2026", [("fin.jpg", JPG + b"f"), ("kiosk.jpg", JPG + b"k")])
    rows = _rows(_grid(client, batch_id))
    fin, kiosk = rows["TEST Finance"]["document_id"], rows["TEST Kiosk"]["document_id"]

    def mark(doc, how):
        resp = client.post(
            f"/api/runs/{batch_id}/receipts/{doc}/settled-outside",
            json={"how": how, "note": f"TEST {how}"},
        )
        assert resp.status_code == 200, resp.text

    mark(fin, "bank_transfer")
    mark(kiosk, "cash")
    grid = _grid(client, batch_id)
    rows = _rows(grid)
    _assert_bill(rows["TEST Finance"], "settled_outside")
    assert rows["TEST Finance"]["settled_outside"]["note"] == "TEST bank_transfer"
    assert rows["TEST Kiosk"]["payment_path"] == "card"
    assert rows["TEST Kiosk"]["settled_outside"]["how"] == "cash"
    assert grid["summary"]["n_bills"] == 1
    assert grid["summary"]["n_settled_outside"] == 2
    (bill,) = [
        dict(zip(BILL_COLUMNS, line))
        for line in _csv(client, f"/runs/{batch_id}/bills.csv")[1:]
    ]
    assert bill["How decided"] == pp.HOW_DECIDED["settled_outside"]
    assert bill["Evidence"] == "TEST bank_transfer"

    # A person's move back to the card overrules the disposition, which then
    # neither displays nor counts; nothing is deleted.
    assert _put_path(client, batch_id, fin, "card").status_code == 200
    grid = _grid(client, batch_id)
    row = _rows(grid)["TEST Finance"]
    assert row["payment_path"] == "card" and row["payment_path_source"] == "person"
    assert "settled_outside" not in row
    assert grid["summary"]["n_settled_outside"] == 1

    # And the later explicit decision wins the other way too.
    mark(fin, "bank_transfer")
    row = _rows(_grid(client, batch_id))["TEST Finance"]
    _assert_bill(row, "settled_outside")
    assert "payment_path" not in row["edited_fields"]


# ── 6. the suggestion ───────────────────────────────────────────────────


def test_printed_bank_details_suggest_and_never_move(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction("2026-07-10", "900.00", "EUR", "TEST Media", notes=IBAN_TEXT),
        _extraction("2026-07-11", "13200.00", "USD", "TEST Cloud", notes=REMINDER_TEXT),
        _extraction("2026-07-12", "718.20", "USD", "TEST Software",
                    hint="Electronic Funds Transfer ...2838"),
    )
    batch_id = _month(client, "July 2026", [
        ("media.jpg", JPG + b"m"), ("cloud.jpg", JPG + b"c"), ("soft.jpg", JPG + b"s"),
    ])
    grid = _grid(client, batch_id)
    rows = _rows(grid)
    media = rows["TEST Media"]
    assert media["payment_path"] == "card", "a suggestion never moves the row"
    assert media["bill_suggestion"] == {"evidence": "IBAN LU00 TEST 0000 0000 0000"}
    assert "bill_suggestion" not in rows["TEST Cloud"], "remittance alone is no bill"
    assert rows["TEST Software"]["payment_path"] == "card", "a transfer naming its card"
    assert "bill_suggestion" not in rows["TEST Software"]
    assert grid["summary"]["n_bills"] == 0


def test_a_row_a_charge_holds_is_offered_nothing(client, monkeypatch):
    _patch_ocr(
        monkeypatch,
        _extraction("2026-07-01", "42.50", "USD", "Staples TEST", notes=IBAN_TEXT),
    )
    assert client.put("/api/settings", json={"cards": FAMILY}).status_code == 200
    batch_id = _month(client, "July 2026", [("staples.jpg", JPG + b"s")])
    assert "bill_suggestion" in _rows(_grid(client, batch_id))["Staples TEST"], (
        "precondition: open and card-less, the details suggest"
    )
    _statement(client, batch_id, (("2026-07-01", "42.50", "STAPLES", "2838"),))
    row = _rows(_grid(client, batch_id))["Staples TEST"]
    assert row.get("transaction_id"), "precondition: a charge holds it"
    assert "bill_suggestion" not in row


# ── 7. the negative contract: a month with no bill signal is unchanged ──


def test_a_month_with_no_bill_signal_renders_as_before(client, monkeypatch):
    """Both payloads built twice over the same month: once as shipped, once
    with the bill path unwired (the pre-218 reading: every row a card, the
    stored dispositions as the only settled-outside map). Every old key must
    agree. The month is test_settled_outside's four live-vocabulary
    receipts, one of them the invoice payment OFFER, which suggests and
    does not move."""
    from expense_recon.web import service

    _patch_ocr(
        monkeypatch,
        _extraction("2026-08-05", "25.00", "USD", "Lovable TEST", hint="Visa ...3645"),
        _extraction("2026-08-10", "900.00", "EUR", "TEST Finance"),
        _extraction("2026-08-22", "13200.00", "USD", "TEST Cloud",
                    hint="Pay $13,200.00 with a bank transfer"),
        _extraction("2026-08-24", "718.20", "USD", "TEST Software",
                    hint="Electronic Funds Transfer ...2838"),
    )
    batch_id = _month(client, "August 2026", [
        (f"r{i}.jpg", JPG + bytes([i])) for i in range(4)
    ])
    _statement(client, batch_id, (
        ("2026-08-05", "25.00", "LOVABLE", "3645"),
        ("2026-08-10", "900.00", "TRANSFERCO", "2838"),
    ))
    shipped = (_grid(client, batch_id), _run(client, batch_id))
    assert shipped[0]["summary"]["n_bills"] == 0
    assert "bill_suggestion" in _rows(shipped[0])["TEST Cloud"]

    def unwired(run, receipts, field_overrides, decisions, *, held=None):
        stored = service.settled_outside_map(run.snapshot or {})
        return pp.MonthPaths(
            paths={r.document_id: ("card", "") for r in receipts}, bills={},
            effective_settled=stored, displayed_settled=stored,
            held=pp.LazyDocs(()),
        )

    monkeypatch.setattr(service, "month_payment_paths", unwired)
    before = (_grid(client, batch_id), _run(client, batch_id))

    new_summary = {"n_bills", "bills_by_ccy"}
    new_row = {"payment_path", "payment_path_source", "bill_suggestion"}
    for now, then in zip(shipped, before):
        assert {k: v for k, v in now["summary"].items() if k not in new_summary} == {
            k: v for k, v in then["summary"].items() if k not in new_summary
        }
    for now, then in zip(shipped[0]["expenses"], before[0]["expenses"]):
        assert {k: v for k, v in now.items() if k not in new_row} == {
            k: v for k, v in then.items() if k not in new_row
        }
    assert shipped[1]["unmatched_receipts"] == before[1]["unmatched_receipts"]
