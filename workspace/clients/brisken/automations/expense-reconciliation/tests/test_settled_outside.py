"""Receipts that never post to a card get a disposition (backlog item 62).

July 2026 holds a Redis invoice for 13,200.00 USD, a Konsultancy Finance one
for 15,972.00 EUR and a 360Crossmedia one for 900.00 EUR. All three were paid
by bank transfer, so no card statement will ever settle them; they sat in
`unmatched_receipts`, in the pool counts and in month health's exact-pair scan
with no disposition that could ever retire them.

"Settled outside the card" is that disposition, and it is bookkeeping rather
than matching. The run payload lets the receipt go; the expense grid and the
month report keep it, because it is real company spend whose evidence is the
invoice (owner ruling 2026-09-15).

The live months are the reason the SUGGESTION is only ever a suggestion:
read on 2026-09-15, all three named invoices carry an EMPTY `payment_mode`,
and the one live receipt whose mode reads "Pay $15.00 with a bank transfer"
(August, Lovable, 15.00 USD) is MATCHED to a card charge. So the chip fires on
nothing in July today, and the one string that would fire it sat on a receipt
that did post. Nothing is ever auto-applied.

Route-level through both payloads and the disposition route.
"""
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
HEADERS = ("Date", "Description", "Type", "Amount")

# LOVABLE settles its receipt. TRANSFERCO is the same amount on the same day
# as the EUR invoice, which makes the two an exact pair for month health's
# scan while the currency blocker keeps the matcher off it -- the shape that
# lets us prove the pair scan lets a settled-outside receipt go.
ROWS = [
    (datetime(2026, 8, 5), "LOVABLE", "Sale", -25.00),
    (datetime(2026, 8, 10), "TRANSFERCO", "Sale", -900.00),
]

# Upload order fixes extraction order. The modes are the live vocabulary:
# a card tail, nothing at all (what the three named invoices really carry),
# an invoice's bank-transfer line, and a transfer that names its card.
RECEIPTS = [
    ("lovable.jpg", "Lovable Labs", "25.00", "USD", "2026-08-05",
     "Visa ...3645"),
    ("konsultancy.jpg", "Konsultancy Finance", "900.00", "EUR", "2026-08-10",
     None),
    ("redis.jpg", "Redis Inc.", "13200.00", "USD", "2026-08-22",
     "Pay $13,200.00 with a bank transfer"),
    ("microsoft.jpg", "Microsoft", "718.20", "USD", "2026-08-24",
     "Electronic Funds Transfer ...2838"),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor, total, currency, date, hint):
    return ExtractedReceipt(
        date=date, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=hint,
    )


def _wire(monkeypatch):
    mock = MockLLMClient(
        extraction_responses=[_extraction(*r[1:]) for r in RECEIPTS],
        fx_responses=[
            FxJudgmentResult(
                is_match=False, same_purchase_confidence=0.1,
                implied_rate=1.0, converted_amount=Decimal("900.00"),
                reasoning="mock",
            )
        ] * 24,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _xlsx_bytes(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _month(client, monkeypatch, *, with_statement=True):
    """A company month holding the four receipts, optionally reconciling."""
    _wire(monkeypatch)
    resp = client.post(
        "/api/expense-batches",
        data={"legal_entity": "", "label": "August 2026"},
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            # Distinct bytes per file: identical bytes are ONE document to
            # the duplicate collapse, so four copies of one JPEG arrive as a
            # single receipt.
            ("files", (name, JPG + name.encode(), "application/octet-stream"))
            for name, *_ in RECEIPTS
        ],
    ))
    if with_statement:
        _done(client, client.post(
            f"/api/expense-batches/{batch_id}/statement",
            files={"statement": (
                "August2026.xlsx", _xlsx_bytes(ROWS),
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet",
            )},
            data={
                "account_id": "card-2838",
                "account_legal_entities": '{"card-2838": "Corporate Services"}',
                "account_card_currency": "USD",
            },
        ))
    return batch_id


def _view(client, batch_id):
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _unmatched(view, vendor):
    return next(
        (r for r in view["unmatched_receipts"] if r["vendor"] == vendor), None
    )


def _doc_id(view, vendor):
    hit = _unmatched(view, vendor)
    assert hit is not None, f"{vendor} is not in the pool"
    return hit["document_id"]


def _mark(client, batch_id, document_id, how="bank_transfer", note=""):
    return client.post(
        f"/api/runs/{batch_id}/receipts/{document_id}/settled-outside",
        json={"how": how, "note": note},
    )


def _unmark(client, batch_id, document_id):
    return client.delete(
        f"/api/runs/{batch_id}/receipts/{document_id}/settled-outside"
    )


# ── the disposition ─────────────────────────────────────────────────────

def test_the_transfer_invoice_leaves_the_pool_and_the_counts(
    client, monkeypatch
):
    """The item itself: a receipt no card will ever carry stops sitting in
    `unmatched_receipts` and in the pool counts, without leaving the
    month."""
    batch_id = _month(client, monkeypatch)
    before = _view(client, batch_id)
    doc = _doc_id(before, "Konsultancy Finance")
    n_receipts = before["summary"]["n_receipts"]
    n_unmatched = before["summary"]["n_unmatched_rec"]
    assert before["summary"]["n_settled_outside"] == 0

    resp = _mark(client, batch_id, doc, note="wire sent 2026-08-11")
    assert resp.status_code == 200, resp.text

    after = _view(client, batch_id)
    assert _unmatched(after, "Konsultancy Finance") is None
    assert after["summary"]["n_unmatched_rec"] == n_unmatched - 1
    assert after["summary"]["n_settled_outside"] == 1
    # Still in the month: `n_receipts` answers "how many receipts are in the
    # month" and that has not changed.
    assert after["summary"]["n_receipts"] == n_receipts


def test_the_rate_is_read_over_the_receipts_a_card_could_settle(
    client, monkeypatch
):
    """A receipt settled by transfer is not a receipt the statement failed
    to explain, so it leaves the denominator rather than counting against
    the month forever."""
    batch_id = _month(client, monkeypatch)
    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    before = _view(client, batch_id)["summary"]["receipt_match_rate"]
    assert _mark(client, batch_id, doc).status_code == 200
    after = _view(client, batch_id)["summary"]
    assert after["receipt_match_rate"] > before
    assert after["n_receipts_matched"] == (
        after["n_receipts"] - after["n_settled_outside"]
        - after["n_unmatched_rec"]
    )


def test_month_health_stops_counting_it_as_an_exact_pair(client, monkeypatch):
    """TRANSFERCO 900.00 USD and the 900.00 EUR invoice are the same amount
    on the same day, so the pair scan sees them. Once the invoice is settled
    outside the card it is not a pair the matcher missed, and a receipt no
    card can carry must never make a healthy month read broken."""
    batch_id = _month(client, monkeypatch)
    before = _view(client, batch_id)["summary"]["month_health"]
    assert before["n_exact_pairs"] >= 1

    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    assert _mark(client, batch_id, doc).status_code == 200

    after = _view(client, batch_id)["summary"]["month_health"]
    assert after["n_exact_pairs"] == before["n_exact_pairs"] - 1


def test_the_expense_grid_keeps_the_row_and_says_how_it_was_settled(
    client, monkeypatch
):
    """Owner ruling: the EXPENSE view removes nothing. The row carries the
    disposition so the grid can caption it.

    Build 4 / item 218 (owner decisions 2026-09-25): a bank transfer is now a
    BILL. The row stays on screen (`n_receipts` does not move) and leaves the
    card-side count `n_expenses` for `n_bills` (test_bills_path_218)."""
    batch_id = _month(client, monkeypatch)
    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    before = _grid(client, batch_id)["summary"]
    assert _mark(
        client, batch_id, doc, how="bank_transfer", note="wire 2026-08-11"
    ).status_code == 200

    grid = _grid(client, batch_id)
    assert grid["summary"]["n_receipts"] == before["n_receipts"]
    assert grid["summary"]["n_expenses"] == before["n_expenses"] - 1
    assert grid["summary"]["n_bills"] == before["n_bills"] + 1
    assert grid["summary"]["n_settled_outside"] == 1
    row = next(e for e in grid["expenses"] if e["document_id"] == doc)
    assert row["settled_outside"]["how"] == "bank_transfer"
    assert row["settled_outside"]["note"] == "wire 2026-08-11"
    assert row["settled_outside"]["at"]


def test_it_is_absent_on_every_row_nobody_settled(client, monkeypatch):
    """Parallel field, rule 1: absent rather than null, so a month with no
    dispositions renders exactly as it did before the field existed."""
    batch_id = _month(client, monkeypatch)
    grid = _grid(client, batch_id)
    assert all("settled_outside" not in e for e in grid["expenses"])
    assert grid["summary"]["n_settled_outside"] == 0


def test_undo_puts_it_back_in_the_pool(client, monkeypatch):
    """The duplicates `ignore` shape: nothing about the receipt changed, so
    releasing it restores the pool, the counts and the pair scan."""
    batch_id = _month(client, monkeypatch)
    before = _view(client, batch_id)["summary"]
    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    assert _mark(client, batch_id, doc).status_code == 200
    assert _view(client, batch_id)["summary"]["n_settled_outside"] == 1

    resp = _unmark(client, batch_id, doc)
    assert resp.status_code == 200, resp.text
    assert resp.json()["removed"] is True

    after = _view(client, batch_id)
    assert _unmatched(after, "Konsultancy Finance") is not None
    assert after["summary"]["n_settled_outside"] == 0
    assert after["summary"]["n_unmatched_rec"] == before["n_unmatched_rec"]
    assert after["summary"]["month_health"]["n_exact_pairs"] == (
        before["month_health"]["n_exact_pairs"]
    )
    assert all(
        "settled_outside" not in e for e in _grid(client, batch_id)["expenses"]
    )


def test_undo_twice_is_not_an_error(client, monkeypatch):
    """An undo button clicked twice must not raise at the reviewer."""
    batch_id = _month(client, monkeypatch)
    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    assert _mark(client, batch_id, doc).status_code == 200
    assert _unmark(client, batch_id, doc).json()["removed"] is True
    second = _unmark(client, batch_id, doc)
    assert second.status_code == 200, second.text
    assert second.json()["removed"] is False


# ── the suggestion, never the disposition ───────────────────────────────

def test_a_bank_transfer_line_is_suggested_and_nothing_is_applied(
    client, monkeypatch
):
    """The chip names the tender it read and pre-selects `how`. The receipt
    is STILL in the pool and still in the counts: a suggestion the reviewer
    has not acted on changes nothing."""
    batch_id = _month(client, monkeypatch)
    view = _view(client, batch_id)
    redis = _unmatched(view, "Redis Inc.")
    assert redis is not None, "the suggestion never removes a receipt"
    assert redis["suggested_settled_outside"] == {
        "how": "bank_transfer",
        "evidence": "Pay $13,200.00 with a bank transfer",
    }
    assert view["summary"]["n_settled_outside"] == 0


def test_a_mode_that_names_a_card_suggests_nothing(client, monkeypatch):
    """"Electronic Funds Transfer ...2838" is a transfer that names the card
    it posted to. The card wins; suggesting otherwise would nudge a reviewer
    to retire a real card charge from the pool."""
    batch_id = _month(client, monkeypatch)
    microsoft = _unmatched(_view(client, batch_id), "Microsoft")
    assert microsoft is not None
    assert "suggested_settled_outside" not in microsoft


def test_an_empty_payment_mode_suggests_nothing(client, monkeypatch):
    """What July's three named invoices actually carry. There is no signal
    to read, so the field is absent and the reviewer decides unaided."""
    batch_id = _month(client, monkeypatch)
    konsultancy = _unmatched(_view(client, batch_id), "Konsultancy Finance")
    assert konsultancy is not None
    assert konsultancy["payment_mode"] == ""
    assert "suggested_settled_outside" not in konsultancy


def test_the_suggestion_goes_when_the_receipt_is_settled(client, monkeypatch):
    """Acting on the chip removes the row it sat on, so the suggestion and
    the disposition can never both be on screen for one receipt."""
    batch_id = _month(client, monkeypatch)
    doc = _doc_id(_view(client, batch_id), "Redis Inc.")
    assert _mark(client, batch_id, doc).status_code == 200
    assert _unmatched(_view(client, batch_id), "Redis Inc.") is None


# ── refusals ────────────────────────────────────────────────────────────

def test_a_receipt_that_settles_a_charge_is_refused(client, monkeypatch):
    """LOVABLE's receipt is on a charge. Marking it here would leave the
    month claiming both that a card paid it and that none did."""
    batch_id = _month(client, monkeypatch)
    grid = _grid(client, batch_id)
    doc = next(
        e["document_id"] for e in grid["expenses"]
        if e["vendor"]["display"].startswith("Lovable")
    )
    resp = _mark(client, batch_id, doc)
    assert resp.status_code == 400, resp.text
    assert "settled against a charge" in resp.json()["error"]
    assert _view(client, batch_id)["summary"]["n_settled_outside"] == 0


def test_an_unknown_tender_is_refused(client, monkeypatch):
    batch_id = _month(client, monkeypatch)
    doc = _doc_id(_view(client, batch_id), "Konsultancy Finance")
    resp = _mark(client, batch_id, doc, how="crypto")
    assert resp.status_code == 400, resp.text
    assert "bank_transfer" in resp.json()["error"]


def test_a_receipt_from_another_month_is_refused(client, monkeypatch):
    batch_id = _month(client, monkeypatch)
    resp = _mark(client, batch_id, "0099__not-here.pdf")
    assert resp.status_code == 400, resp.text
    assert "not in this month" in resp.json()["error"]


# ── the month report keeps it, behind a caption ─────────────────────────

def test_the_month_report_still_prints_the_row_with_its_tender(
    client, monkeypatch
):
    """Owner ruling 2026-09-15: a bank transfer is real company spend whose
    evidence is the invoice, so dropping it would hide the spend from the
    accountant. It prints, captioned with how it was settled."""
    from expense_recon.output import month_report_pdf

    batch_id = _month(client, monkeypatch, with_statement=False)
    doc = next(
        e["document_id"] for e in _grid(client, batch_id)["expenses"]
        if e["vendor"]["display"].startswith("Konsultancy")
    )
    assert _mark(client, batch_id, doc).status_code == 200

    # `service.build_expense_report` imports this at CALL time, so the spy
    # has to sit on the source module, not on a name bound in service.
    captured = {}
    real = month_report_pdf.build_expense_report_pdf

    def spy(*args, **kwargs):
        captured["evidence"] = kwargs.get("evidence")
        return real(*args, **kwargs)

    monkeypatch.setattr(month_report_pdf, "build_expense_report_pdf", spy)
    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text

    details = [str(i.get("detail") or "") for i in captured["evidence"]]
    assert any("paid by bank transfer" in d for d in details), details
    # Every other receipt is untouched by the caption.
    assert sum("paid by bank transfer" in d for d in details) == 1
