"""A receipt a neighbour month settled converts at that charge (backlog item 212).

Item 204 step 3 made the card, company and person of a receipt follow the
claim a neighbour month's charge holds on it. The money did not follow:
`settled_charge_amounts` read only the month's own charges, so July's EUR
receipt that August's USD charge settled printed August's card in the CSV
and converted at the ECB reference rate anyway. Card and rate described two
different things. Both now come from one reader
(`charges_settled_elsewhere`).

Pinned through the routes a reviewer downloads (`GET /runs/{july}/expenses.csv`
and `GET /runs/{july}/expense-report.pdf`). The fixture sets the two rungs
apart on purpose: the charge is USD 66.60 for a EUR 60.00 receipt (1.11),
the ECB table says 1.10, so a test on the wrong rung fails instead of
agreeing by coincidence.
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

JPG = b"\xff\xd8\xff\xe0item-212-bytes"

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

# Units per ONE EUR, the ECB table's shape: EUR:USD is 1.10.
ECB_PER_EUR = {"USD": "1.10"}

CARD_HEADERS = ("Card", "Date", "Description", "Type", "Amount")
# August's cycle opens on 07-31, so July's last-day receipt is inside it, and
# the Google charge posts on 08-01 on the Cloud card, in USD.
AUGUST_ROWS = [
    ("2838", datetime(2026, 7, 31), "OPENAI", "Sale", -80.28),
    ("3645", datetime(2026, 8, 1), "GOOGLE WORKSPACE", "Sale", -66.60),
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


def _extraction(vendor, total, day, currency) -> ExtractedReceipt:
    return ExtractedReceipt(
        date=day, total=total, currency=currency, vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=None,
    )


def _wire(monkeypatch):
    """July's EUR Google receipt is read first, then August's USD Lovable
    one; the ECB table every month fetches at creation is the fixture's."""
    from expense_recon.web import ecb_rates

    monkeypatch.setattr(
        ecb_rates, "fetch_monthly",
        lambda start, end, **kw: {
            m: dict(ECB_PER_EUR)
            for m in ("2026-%02d" % i for i in range(1, 13))
            if start <= m <= end
        },
    )
    mock = MockLLMClient(
        extraction_responses=[
            _extraction("Google", "60.00", "2026-07-31", "EUR"),
            _extraction("Lovable Labs", "25.00", "2026-08-15", "USD"),
        ],
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.11, converted_amount=Decimal("66.60"),
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


def _month(client, label: str, fname: str) -> str:
    resp = client.post(
        "/api/expense-batches", data={"legal_entity": "", "label": label}
    )
    _done(client, resp)
    batch_id = resp.json()["batch_id"]
    _done(client, client.post(
        f"/api/expense-batches/{batch_id}/receipts",
        files=[("files", (fname, JPG + fname.encode(), "application/octet-stream"))],
    ))
    return batch_id


def _months(client, monkeypatch) -> tuple[str, str]:
    assert client.put("/api/settings", json={"cards": CARDS}).status_code == 200
    _wire(monkeypatch)
    return _month(client, "July 2026", "google.jpg"), _month(
        client, "August 2026", "lovable.jpg"
    )


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


def _google_charge(client, august) -> dict:
    resp = client.get(f"/api/runs/{august}")
    assert resp.status_code == 200, resp.text
    return next(r for r in resp.json()["rows"] if r["vendor"] == "GOOGLE WORKSPACE")


def _google_doc(client, july) -> str:
    resp = client.get(f"/api/expense-batches/{july}")
    assert resp.status_code == 200, resp.text
    return next(
        e["document_id"] for e in resp.json()["expenses"]
        if e["receipt_name"] == "google.jpg"
    )


def _decide(client, august, tx_id, status, doc) -> None:
    resp = client.post(
        f"/api/runs/{august}/decisions",
        json={"transaction_id": tx_id, "status": status, "chosen_document_id": doc},
    )
    assert resp.status_code == 200, resp.text


def _settle(client, july, august) -> dict:
    """August's statement pairs July's receipt. A cross-currency pair can
    land as a proposal, which writes no claim, so the reviewer confirms it
    the way Criss would; a deterministic pair is confirmed all the same."""
    _attach_august(client, august)
    charge = _google_charge(client, august)
    _decide(client, august, charge["transaction_id"], "confirmed", _google_doc(client, july))
    charge = _google_charge(client, august)
    assert charge["effective_bucket"] == "reconciled", charge
    return charge


def _google_csv_row(client, july) -> dict:
    resp = client.get(f"/runs/{july}/expenses.csv")
    assert resp.status_code == 200, resp.text
    return next(
        r for r in csv.DictReader(io.StringIO(resp.text))
        if r.get("Vendor") == "Google"
    )


def _pdf_text(client, july) -> str:
    resp = client.get(f"/runs/{july}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    raw = "\n".join(
        p.extract_text() or "" for p in PdfReader(io.BytesIO(resp.content)).pages
    )
    return " ".join(raw.split())


# ── the rate follows the charge the card came from ───────────────────


def test_the_csv_converts_at_the_neighbour_charge_that_named_the_card(
    client, monkeypatch
):
    july, august = _months(client, monkeypatch)
    before = _google_csv_row(client, july)
    # No charge yet: the reference rate is the only rung.
    assert before["Exchange Rate"] == "1.100000", before

    _settle(client, july, august)

    row = _google_csv_row(client, july)
    # The card came from August's USD 66.60 charge ...
    assert row["Paid Through"] == "Chase 3645", row
    # ... and so does the rate: 66.60 / 60.00, not the ECB 1.10.
    assert row["Exchange Rate"] == "1.110000", row


def test_the_month_report_prints_the_charges_figure(client, monkeypatch):
    july, august = _months(client, monkeypatch)
    _settle(client, july, august)

    text = _pdf_text(client, july)
    assert "= USD 66.60 at 1.11, the charge" in text, text
    assert "= USD 66.00 at 1.1, ECB" not in text
    assert "Total in USD: 66.60" in text


def test_a_rejected_neighbour_pair_lends_no_rate(client, monkeypatch):
    """Item 111's rule on the money side, across months: a pair August's
    reviewer threw out is not evidence of what the card charged, so July's
    row falls back to the reference rate, and loses the card with it."""
    july, august = _months(client, monkeypatch)
    charge = _settle(client, july, august)
    _decide(client, august, charge["transaction_id"], "rejected", _google_doc(client, july))

    row = _google_csv_row(client, july)
    assert row["Exchange Rate"] == "1.100000", row
    assert row["Paid Through"] != "Chase 3645", row
