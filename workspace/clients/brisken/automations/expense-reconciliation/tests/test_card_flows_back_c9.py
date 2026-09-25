"""The card flows back to a receipt a neighbour month settled (item 204, case 9
build 3).

A receipt printed on July 31 is paid by a charge that posts on August 1, so
August's statement borrows it from July (`adjacent_pool_for_month`), pairs
it and writes a `receipt_claims` row. Until this build July's own grid showed
only `settled_by` on that receipt: no card, no company, no person, while
August's statement named all three. The settled-cards map now also carries
the claim another month holds, resolved through that month's charge.

Pinned through the routes (`GET /api/expense-batches/{july}` and the July
CSV, month report and sign-off learner):

1. After August's statement pairs July's receipt, July's row shows the
   charge's card, company and person (`card_source: "settled_charge"`) and
   `settled_by` names August. Before the statement it showed none of them.
2. The documents and the learner say what the screen says.
3. What lends nothing: a pair left in August's review bucket, a pair the
   reviewer rejected, a receipt confirmed private before the borrow, and a
   deleted August.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdf")

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0c9-3-bytes"

CARDS = {
    "corp-2838": {
        "label": "Corporate card (Chase)",
        "digits": ["2838", "1672"],
        "entity": "Corporate Services",
        "person": "Dirk",
        "zoho_account": "Chase 2838",
    },
    "cloud-3645": {
        "label": "Cloud card",
        "digits": ["3645"],
        "entity": "Cloud Services",
        "person": "Nicolas",
        "zoho_account": "Chase 3645",
    },
}

CARD_HEADERS = ("Card", "Date", "Description", "Type", "Amount")
# August as Chase cuts it live: the cycle opens on 07-31, so July's last-day
# receipt is inside August's period, and the Google charge posts on 08-01
# on the Cloud card.
AUGUST_ROWS = [
    ("2838", datetime(2026, 7, 31), "OPENAI", "Sale", -80.28),
    ("3645", datetime(2026, 8, 1), "GOOGLE WORKSPACE", "Sale", -71.64),
    ("2838", datetime(2026, 8, 15), "LOVABLE", "Sale", -25.00),
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _extraction(vendor, total, day) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch, *, tie: bool = False):
    """July's Google receipt is read first, then August's Lovable one and,
    with `tie`, an August copy of the same Google receipt."""
    mock = MockLLMClient(
        extraction_responses=[
            _extraction("Google", "71.64", "2026-07-31"),
            _extraction("Lovable Labs", "25.00", "2026-08-15"),
            *([_extraction("Google", "71.64", "2026-07-31")] if tie else []),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("71.64"),
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


def _xlsx_bytes(rows, headers) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _month(client, label: str, *fnames: str) -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[
            ("files", (f, JPG + f.encode(), "application/octet-stream"))
            for f in fnames
        ],
    ))
    return batch_id


def _attach_august(client, august: str) -> None:
    _done(client, client.post(
        f"/api/expense-batches/{august}/statement",
        files={"statement": (
            "August2026.xlsx", _xlsx_bytes(AUGUST_ROWS, CARD_HEADERS),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
        data={
            "account_id": "card-2838",
            "account_legal_entities": '{"card-2838": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    ))


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _google(client, july) -> dict:
    return next(
        e for e in _grid(client, july)["expenses"]
        if e["receipt_name"] == "google.jpg"
    )


def _charge(client, batch_id, vendor) -> dict:
    resp = client.get(f"/api/runs/{batch_id}")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json()["rows"] if r["vendor"] == vendor)


def _decide(client, batch_id, tx_id, status, doc=None):
    resp = client.post(
        f"/api/runs/{batch_id}/decisions",
        json={"transaction_id": tx_id, "status": status, "chosen_document_id": doc},
    )
    assert resp.status_code == 200, resp.text


def _months(client, monkeypatch, *, tie: bool = False) -> tuple[str, str]:
    """July with its one Google receipt, August with its Lovable one; no
    statement yet. Both months take the card registry at creation."""
    assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
    _wire(monkeypatch, tie=tie)
    july = _month(client, "July 2026", "google.jpg")
    august = _month(
        client, "August 2026", "lovable.jpg", *(["google-aug.jpg"] if tie else [])
    )
    return july, august


def _assert_no_card(row: dict) -> None:
    assert row["card"] is None and row["card_source"] == "none", row
    assert row["legal_entity_id"] == "" and row["person"] == "", row
    assert "needs_company_or_person" in row["boxes"], row


# ── the card flows back ──────────────────────────────────────────────


def test_julys_receipt_takes_the_card_of_the_august_charge_that_settled_it(
    client, monkeypatch
):
    july, august = _months(client, monkeypatch)
    before = _google(client, july)
    _assert_no_card(before)
    assert "settled_by" not in before

    _attach_august(client, august)

    charge = _charge(client, august, "GOOGLE WORKSPACE")
    assert charge["effective_bucket"] == "reconciled", charge
    assert charge["chosen_document_id"] == before["document_id"], charge

    row = _google(client, july)
    assert row["card_source"] == "settled_charge", row
    assert row["card"]["key"] == "cloud-3645"
    assert row["legal_entity_id"] == "Cloud Services"
    assert row["entity_source"] == "card"
    assert row["person"] == "Nicolas" and row["person_source"] == "card"
    assert "needs_company_or_person" not in row["boxes"]
    # The company paid, so the private-card option is gone, exactly as for a
    # receipt a charge of its own month settles.
    assert row["can_mark_private"] is False
    # The borrowing month is named, and it is the one that lent the card.
    assert row["settled_by"]["run_id"] == august
    assert row["settled_by"]["label"] == "August 2026"
    assert row["settled_by"]["transaction_id"] == charge["transaction_id"]
    assert _grid(client, july)["summary"]["n_needs_company_or_person"] == 0


def test_a_confirmed_pick_in_august_lends_its_card_too(client, monkeypatch):
    """A reviewer's confirm writes the same claim a deterministic match
    does, so the card follows it."""
    july, august = _months(client, monkeypatch)
    _attach_august(client, august)
    charge = _charge(client, august, "GOOGLE WORKSPACE")
    _decide(
        client, august, charge["transaction_id"], "confirmed",
        charge["chosen_document_id"],
    )
    row = _google(client, july)
    assert row["card_source"] == "settled_charge"
    assert row["card"]["key"] == "cloud-3645"


# ── the documents and the learner say what the screen says ───────────


def test_the_csv_and_the_month_report_print_the_flowed_back_company(
    client, monkeypatch
):
    july, august = _months(client, monkeypatch)
    _attach_august(client, august)

    resp = client.get(f"/runs/{july}/expenses.csv")
    assert resp.status_code == 200, resp.text
    rows = {
        r["Vendor"]: r for r in csv.DictReader(io.StringIO(resp.text))
        if r.get("Vendor")
    }
    assert rows["Google"]["Legal Entity"] == "Cloud Services"
    assert rows["Google"]["Paid Through"] == "Chase 3645"

    resp = client.get(f"/runs/{july}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    text = " ".join(
        " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(resp.content)).pages)
        .split()
    )
    assert "Cloud Services" in text and "Chase 3645" in text
    assert "(entity - assign)" not in text


def test_publishing_july_teaches_the_card_augusts_statement_named(
    client, monkeypatch
):
    """Item 171's learner reads the same map: July's sign-off records the
    card the bank named for the merchant."""
    july, august = _months(client, monkeypatch)
    resp = client.put("/api/settings", json={"merchants": {
        "Google": {"aliases": [], "category": None, "zoho_account": None},
    }})
    assert resp.status_code == 200, resp.text
    _attach_august(client, august)

    resp = client.post(f"/api/runs/{july}/publish", json={"override": True})
    assert resp.status_code == 200, resp.text
    merchants = client.get("/api/settings").json()["merchants"]
    assert merchants["Google"]["cards_seen"] == ["cloud-3645"]


# ── what lends nothing ───────────────────────────────────────────────


def test_a_pair_left_in_augusts_review_bucket_lends_nothing(client, monkeypatch):
    """A proposal waiting for the reviewer writes no claim: the receipt is
    offered to the charge, not settled by it. Here August holds an identical
    Google receipt of its own, so the charge has two equal candidates and the
    matcher settles neither (live July 2026 holds June's SUPERMERCADO FENIX
    receipt in review the same way, with no claim)."""
    july, august = _months(client, monkeypatch, tie=True)
    _attach_august(client, august)

    charge = _charge(client, august, "GOOGLE WORKSPACE")
    doc = _google(client, july)["document_id"]
    assert charge["effective_bucket"] == "review", charge
    assert any(c["document_id"] == doc for c in charge["candidates"]), charge

    row = _google(client, july)
    _assert_no_card(row)
    assert "settled_by" not in row


def test_a_rejected_pair_lends_nothing(client, monkeypatch):
    july, august = _months(client, monkeypatch)
    _attach_august(client, august)
    assert _google(client, july)["card_source"] == "settled_charge"

    charge = _charge(client, august, "GOOGLE WORKSPACE")
    _decide(client, august, charge["transaction_id"], "rejected")

    row = _google(client, july)
    _assert_no_card(row)
    assert "settled_by" not in row


def test_a_receipt_confirmed_private_is_never_borrowed(client, monkeypatch):
    july, august = _months(client, monkeypatch)
    doc = _google(client, july)["document_id"]
    resp = client.post(
        f"/api/runs/{july}/expenses/{doc}/private",
        json={"private": True, "reimburse_to": "Dirk"},
    )
    assert resp.status_code == 200, resp.text

    _attach_august(client, august)

    assert _charge(client, august, "GOOGLE WORKSPACE")["chosen_document_id"] != doc
    row = _google(client, july)
    assert "settled_by" not in row
    assert row["card_source"] != "settled_charge"
    assert row["card"] is None


def test_deleting_august_takes_the_card_away_again(client, monkeypatch):
    july, august = _months(client, monkeypatch)
    _attach_august(client, august)
    assert _google(client, july)["card_source"] == "settled_charge"

    resp = client.post(
        f"/api/runs/{august}/delete", json={"confirm": "August 2026"}
    )
    assert resp.status_code == 200, resp.text

    row = _google(client, july)
    _assert_no_card(row)
    assert "settled_by" not in row
