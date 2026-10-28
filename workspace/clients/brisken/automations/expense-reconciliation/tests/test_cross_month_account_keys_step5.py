"""Billing-account keys across months (backlog item 223 step 5, 2026-09-27).

Duplicate detection saw one month's receipts only. `reference_keys` and
`document_number_cores` drop a reference as an account id only when the SAME
list carries it at DIFFERENT totals, and some vendors print the customer's
billing-account code where the document number goes: Railway `77H7ITO0` 5.00
in July and September, Rize `5ZK1BCDG` 12.99 in July and August. Each is
alone in its month, so nothing is wrong yet; two real monthly bills of one
amount under such a code in one month (a late bill filed with the next) would
twin as copies and one would leave the total.

A number another month shows on the same money a billing cycle (20 days or
more) away is now an account key: computed where neighbour months are read
(a re-match, a receipt added to a month with no statement), stored on the
snapshot, and read by every surface. A re-filed copy prints the same date, so
it never becomes a key; it is listed in `cross_month_copies[]` instead.

Route-level through `create_app` + `TestClient`, one caller-level test per
wiring point.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from expense_recon.duplicates import (  # noqa: E402
    collapsed_duplicate_copies,
    cross_month_evidence,
)
from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.matching.types import Receipt  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CODE = "77H7ITO0"

CARDS = {
    "corp-2838": {
        "label": "Credit Card - 2838", "digits": ["2838"],
        "entity": "Corporate Services", "person": "Dirk Neumann - Corp Services",
        "currency": "USD",
    },
    "cons-1176": {
        "label": "Credit Card Chase Visa - 1176", "digits": ["1176"],
        "entity": "Consulting", "person": "Brisken Consulting", "currency": "USD",
    },
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        resp = c.put("/api/settings", json={
            "entities": {"Corporate Services": {}, "Consulting": {}},
            "cards": CARDS,
        })
        assert resp.status_code == 200, resp.text
        yield c


def _x(vendor, day, total, reference, payment_hint=None, invoice_number=None):
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference=reference, line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint, invoice_number=invoice_number,
    )


def _done(client, resp):
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job


def _month(client, monkeypatch, label, receipts):
    """A month created empty, its receipts added through the add route (the
    commit that computes the keys on a month with no statement)."""
    mock = MockLLMClient(
        extraction_responses=[x for _name, x in receipts],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9, implied_rate=1.0,
                converted_amount=Decimal("5.00"), reasoning="same purchase",
            )
        ] * 12,
    )
    monkeypatch.setattr("expense_recon.cli._build_llm_client", lambda cfg: (mock, None))
    resp = client.post("/api/expense-batches", data={"legal_entity": "", "label": label})
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (name, JPG + label.encode() + name.encode(), "application/octet-stream"))
            for name, _x_ in receipts
        ],
    ))
    return batch_id


def _grid(client, batch_id):
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(grid, needle):
    return next(e for e in grid["expenses"] if needle in e["document_id"])


def _card_key(expense):
    return (expense.get("card") or {}).get("key")


def _snapshot(tmp_path, batch_id) -> dict:
    store = RunStore(tmp_path / "recon-web.sqlite")
    try:
        return dict(store.get_run(batch_id).snapshot or {})
    finally:
        store.close()


def _n_expenses(client, batch_id) -> int:
    batches = client.get("/api/expense-batches").json()["batches"]
    return next(b for b in batches if b["batch_id"] == batch_id)["summary"]["n_expenses"]


def _september(client, monkeypatch, day="2026-09-01", reference=CODE):
    return _month(client, monkeypatch, "September 2026", [
        ("railway-sep.jpg", _x("Railway", day, "5.00", reference)),
    ])


JULY_PAIR = [
    ("railway-0701.jpg", _x("Railway", "2026-07-01", "5.00", CODE, payment_hint="Visa ...2838")),
    ("railway-0730.jpg", _x("Railway", "2026-07-30", "5.00", CODE)),
]


# ── (a) another month shows the code is an account ───────────────────────


def test_two_bills_under_an_account_code_both_count_when_another_month_shows_it(
    client, monkeypatch, tmp_path,
):
    """September holds `77H7ITO0` 5.00 dated 09-01; July's two bills of 5.00
    under it, 07-01 and 07-30, are two bills. The keys are computed by the
    add commit (July has no statement) and every surface reads them: the
    grid (no group, both count, the 07-30 bill borrows no card), the months
    list, the export."""
    _september(client, monkeypatch)
    july = _month(client, monkeypatch, "July 2026", JULY_PAIR)

    assert _snapshot(tmp_path, july)["duplicate_account_keys"] == [CODE]
    grid = _grid(client, july)
    assert grid["duplicate_groups"] == []
    assert all(e.get("counts_in_total") is not False for e in grid["expenses"])
    assert grid["summary"]["totals_by_ccy"] == {"USD": "10.00"}
    assert "cross_month_copies" not in grid
    # Not a copy, so the 07-01 bill's card is not lent to the 07-30 bill.
    assert _card_key(_row(grid, "railway-0701")) == "corp-2838"
    assert _card_key(_row(grid, "railway-0730")) is None

    assert _n_expenses(client, july) == 2
    resp = client.get(f"/runs/{july}/expenses.csv")
    assert resp.status_code == 200, resp.text
    entities = [
        r["Legal Entity"] for r in csv.DictReader(io.StringIO(resp.text))
        if r["Reference#"] == CODE
    ]
    assert len(entities) == 2, entities
    assert entities.count("Corporate Services") == 1, entities


# ── (b) the control: no other month holds the code ───────────────────────


def test_the_same_pair_with_no_other_month_still_twins(client, monkeypatch, tmp_path):
    """Today's behaviour, unchanged: one number + one total in one month is
    one document, and nothing is stored."""
    july = _month(client, monkeypatch, "July 2026", JULY_PAIR)

    snapshot = _snapshot(tmp_path, july)
    assert "duplicate_account_keys" not in snapshot
    assert "cross_month_copies" not in snapshot
    grid = _grid(client, july)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("reference", "copy")
    assert grid["summary"]["totals_by_ccy"] == {"USD": "5.00"}
    assert _n_expenses(client, july) == 1


# ── (c) a re-filed copy is a copy, never an account ──────────────────────


def test_a_re_filed_copy_in_another_month_is_listed_and_makes_no_key(
    client, monkeypatch, tmp_path,
):
    """September holds a re-filed copy of July's 07-30 bill (same date).
    It makes no account key, so July's own twin (a reference pair the
    vendor/date key misses) stays one document, and the Expenses payload
    lists the cross-month copy."""
    sept = _month(client, monkeypatch, "September 2026", [
        ("railway-refiled.jpg", _x("Railway", "2026-07-30", "5.00", CODE)),
    ])
    july = _month(client, monkeypatch, "July 2026", [
        ("railway-0730.jpg", _x("Railway", "2026-07-30", "5.00", CODE)),
        ("railway-0730-receipt.jpg", _x("Railway Corporation", "2026-07-30", "5.00", CODE)),
    ])

    assert "duplicate_account_keys" not in _snapshot(tmp_path, july)
    grid = _grid(client, july)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("reference", "copy")
    assert grid["summary"]["totals_by_ccy"] == {"USD": "5.00"}
    sept_doc = _grid(client, sept)["expenses"][0]["document_id"]
    assert grid["cross_month_copies"] == [{
        "document_id": _row(grid, "railway-0730.jpg")["document_id"],
        "batch_id": sept,
        "other_document_id": sept_doc,
    }]


# ── (d) a page view never loads another month ────────────────────────────


def test_reading_the_page_loads_no_neighbour_month(client, monkeypatch, tmp_path):
    from expense_recon.web import service

    calls = []
    real = service.other_month_receipts

    def counting(store, run):
        calls.append(run.run_id)
        return real(store, run)

    monkeypatch.setattr(service, "other_month_receipts", counting)
    _september(client, monkeypatch)
    july = _month(client, monkeypatch, "July 2026", JULY_PAIR)
    assert july in calls, "the counter sees the write that computes the keys"

    seen = len(calls)
    for _ in range(2):
        assert _grid(client, july)["duplicate_groups"] == []
    assert client.get(f"/api/runs/{july}").status_code == 200
    assert client.get("/api/expense-batches").status_code == 200
    assert client.get(f"/runs/{july}/expenses.csv").status_code == 200
    assert len(calls) == seen, calls[seen:]


# ── (e) the re-match computes, bakes, pools and stores them ──────────────


def _xlsx(rows) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Type", "Amount"])
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_the_re_match_computes_the_keys_and_matches_both_bills_as_bills(
    client, monkeypatch, tmp_path,
):
    """July is filled BEFORE September exists, so its add stored no key and
    the pair twins. September arrives; July's statement attach re-matches,
    reads September, and the 07-30 bill (no card of its own, so no 2838 lent
    by the 07-01 bill) takes the 1176 charge of 07-30."""
    july = _month(client, monkeypatch, "July 2026", JULY_PAIR)
    assert len(_grid(client, july)["duplicate_groups"]) == 1
    _september(client, monkeypatch)

    _done(client, client.post(
        f"/api/expense-batches/{july}/statement",
        files={"statement": ("July2026.xlsx", _xlsx([
            (datetime(2026, 7, 30), "RAILWAY", "Sale", -5.00),
        ]), XLSX)},
        data={
            "account_id": "card-1176",
            "account_legal_entities": '{"card-1176": "Consulting"}',
            "account_card_currency": "USD",
        },
    ))
    assert _snapshot(tmp_path, july)["duplicate_account_keys"] == [CODE]
    assert _grid(client, july)["duplicate_groups"] == []
    view = client.get(f"/api/runs/{july}").json()
    (row,) = [r for r in view["rows"] if r["vendor"] == "RAILWAY"]
    assert "railway-0730" in (row["chosen_document_id"] or ""), row


# ── (f) an invoice printing the code beside its receipt ──────────────────


def test_an_invoice_printing_the_code_is_still_its_receipts_copy(client, monkeypatch):
    """07-30: an invoice printing only the account code, and its receipt
    printing the invoice number and card 1176 (vendor, date, total agree).
    With the code an account, the pair is not "two different numbers"
    (rung 4): it is one document on vendor + date (rung 6), the receipt lends
    the invoice its card, and the month counts two expenses, on the page and
    on the months list alike."""
    _september(client, monkeypatch)
    july = _month(client, monkeypatch, "July 2026", [
        ("railway-0701.jpg", _x("Railway", "2026-07-01", "5.00", CODE, payment_hint="Visa ...2838")),
        ("Invoice-railway-0730.jpg", _x("Railway", "2026-07-30", "5.00", CODE)),
        ("Receipt-railway-0730.jpg", _x("Railway", "2026-07-30", "5.00", "RW-2026-0730",
                                        payment_hint="Visa ...1176")),
    ])
    grid = _grid(client, july)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("vendor_date", "copy")
    assert grid["summary"]["totals_by_ccy"] == {"USD": "10.00"}
    assert _card_key(_row(grid, "Invoice-railway")) == "cons-1176"
    assert _n_expenses(client, july) == 2


# ── (g) the digit core: a late bill filed with the next ───────────────────


def test_a_late_bill_filed_with_the_next_keeps_both_under_a_numeric_account(
    client, monkeypatch,
):
    """June's bill (06-30) filed in July beside July's own (07-01), one day
    apart, both printing customer number 7788990011 in different words; a
    September bill prints the bare number. The number key would have called
    them one slip read two ways (`reference_digits`)."""
    _september(client, monkeypatch, reference="7788990011")
    july = _month(client, monkeypatch, "July 2026", [
        ("railway-0630.jpg", _x("Railway", "2026-06-30", "5.00", "Customer 7788990011")),
        ("railway-0701.jpg", _x("Railway", "2026-07-01", "5.00", "Cust no 7788990011")),
    ])
    grid = _grid(client, july)
    assert grid["duplicate_groups"] == []
    assert grid["summary"]["totals_by_ccy"] == {"USD": "10.00"}


# ── (h) the billing-account index reads the same keys ────────────────────


def test_the_billing_account_index_takes_no_lent_card_from_a_false_twin(
    client, monkeypatch,
):
    """The Stripe-shaped account `RAILACCT` has one purchase on 2838 (07-01).
    The 07-30 bill shares the code `77H7ITO0` with it; lent 2838 through a
    false twin it would be a second purchase on 2838, and the index would
    then decide 2838 for the card-less 07-15 bill. It stays blank."""
    _september(client, monkeypatch)
    july = _month(client, monkeypatch, "July 2026", [
        ("railway-0701.jpg", _x("Railway", "2026-07-01", "5.00", CODE,
                                payment_hint="Visa ...2838", invoice_number="RAILACCT-0006")),
        ("railway-0730.jpg", _x("Railway", "2026-07-30", "5.00", CODE,
                                invoice_number="RAILACCT-0007")),
        ("railway-0715.jpg", _x("Railway", "2026-07-15", "7.00", "",
                                invoice_number="RAILACCT-0008")),
    ])
    grid = _grid(client, july)
    assert grid["duplicate_groups"] == []
    assert _card_key(_row(grid, "railway-0730")) is None
    assert _card_key(_row(grid, "railway-0715")) is None


# ── (i) two invoice numbers on one numeric account, one day ──────────────


def test_two_invoices_on_one_numeric_account_the_same_day_stay_two(client, monkeypatch):
    """Vendor, date and total agree, so the vendor/date key nominates the
    pair; the only thing the two numbers share is the account number, which
    September shows is an account. Two invoice numbers are two purchases
    (rung 4), not one slip read two ways (`reference_digits`)."""
    _september(client, monkeypatch, reference="7788990011")
    july = _month(client, monkeypatch, "July 2026", [
        ("railway-a1.jpg", _x("Railway", "2026-07-30", "5.00", "INV-A1 CUST 7788990011")),
        ("railway-b2.jpg", _x("Railway", "2026-07-30", "5.00", "INV-B2 CUST 7788990011")),
    ])
    grid = _grid(client, july)
    (group,) = grid["duplicate_groups"]
    assert (group["basis"], group["verdict"]) == ("distinct_reference", "distinct")
    assert grid["summary"]["totals_by_ccy"] == {"USD": "10.00"}


# ── (j) a fixture batch is no evidence ───────────────────────────────────


def test_a_test_fixture_batch_holding_the_code_makes_no_key(client, monkeypatch, tmp_path):
    _month(client, monkeypatch, "TEST - September 2026", [
        ("railway-sep.jpg", _x("Railway", "2026-09-01", "5.00", CODE)),
    ])
    july = _month(client, monkeypatch, "July 2026", JULY_PAIR)
    assert "duplicate_account_keys" not in _snapshot(tmp_path, july)
    assert len(_grid(client, july)["duplicate_groups"]) == 1


# ── the rule itself ──────────────────────────────────────────────────────


def _r(doc, day, total="5.00", reference=CODE, vendor="Railway", currency="USD"):
    return Receipt(
        document_id=doc, legal_entity_id="", detected_date=day,
        detected_total=Decimal(total), detected_currency=currency,
        detected_vendor=vendor, detected_reference=reference,
    )


def test_a_billing_cycle_is_twenty_days_on_the_same_money():
    july = [_r("j", date(2026, 7, 30))]
    assert cross_month_evidence(july, {"s": [_r("s", date(2026, 8, 19))]})[0] == {CODE}
    assert cross_month_evidence(july, {"s": [_r("s", date(2026, 8, 18))]})[0] == frozenset()
    assert cross_month_evidence(july, {"s": [_r("s", date(2026, 9, 1), total="6.00")]})[0] == frozenset()
    assert cross_month_evidence(july, {"s": [_r("s", date(2026, 9, 1), currency="EUR")]})[0] == frozenset()
    keys, copies = cross_month_evidence(july, {"s": [_r("s", date(2026, 7, 30))]})
    assert keys == frozenset()
    assert copies == [{"document_id": "j", "batch_id": "s", "other_document_id": "s"}]


def test_the_collapse_helper_takes_the_keys_too():
    """`collapsed_duplicate_copies` (the attribution tool's entry) keeps a
    pair under an account key in the pool, and collapses it without."""
    pair = [_r("a", date(2026, 7, 1)), _r("b", date(2026, 7, 30))]
    assert collapsed_duplicate_copies(pair) == {"b"}
    assert collapsed_duplicate_copies(pair, account_keys={CODE}) == set()
