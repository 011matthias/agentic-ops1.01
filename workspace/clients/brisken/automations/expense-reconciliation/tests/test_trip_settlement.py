"""The trip-spanning match pool + the trip report (R4b, backlog item 38).

Item 38 ruling 3: both functions reconcile. A month's statement charges
must be matchable against receipts sitting in TRIPS, so the candidate pool
spans batch types — every trip whose date range overlaps the month's charge
span contributes its receipts — and the `receipt_claims` registry (R4a)
arbitrates so one receipt never settles two charges across two batches.

The trip report is the existing listing + receipt-evidence document with
the LISTING sectioned per person (item 40's field, through the card
chain): roster order first, other named persons after, unowned rows last,
numbering continuous.
"""
from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdf")

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import (  # noqa: E402
    ExtractedReceipt,
    FxJudgmentResult,
    MockLLMClient,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _extraction(vendor="Staples", total="42.50", date="2026-04-15",
                payment_hint=None):
    return ExtractedReceipt(
        date=date, total=total, currency="USD", vendor=vendor,
        reference="", line_items=(), confidence=0.9, notes="",
        payment_hint=payment_hint,
    )


def _wire(monkeypatch, *extractions, n_fx=12):
    mock = MockLLMClient(
        extraction_responses=list(extractions),
        fx_responses=[
            FxJudgmentResult(
                is_match=True, same_purchase_confidence=0.9,
                implied_rate=1.0, converted_amount=Decimal("42.50"),
                reasoning="same purchase",
            )
        ] * n_fx,
    )
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )
    return mock


def _create_trip(client, name="TEST - Rome", start="2026-04-01",
                 end="2026-04-20", travelers=("Dirk",)):
    resp = client.post("/api/trips", json={
        "name": name, "start": start, "end": end,
        "travelers": list(travelers),
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["trip_id"]


def _create_batch(client, label="April 2026", *, files=None, extra=None,
                  fname="a.jpg", body=b""):
    resp = client.post(
        "/api/expense-batches",
        files=files or [
            ("files", (fname, JPG + body, "application/octet-stream"))
        ],
        data={
            "legal_entity": "Corporate Services", "label": label,
            **(extra or {}),
        },
    )
    assert resp.status_code == 200, resp.text
    assert client.get(f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    return resp.json()["batch_id"]


def _create_trip_batch(client, trip_id, *, files=None):
    return _create_batch(
        client, label="TEST - trip receipts", files=files,
        extra={"batch_type": "trip", "trip_id": trip_id},
    )


def _attach(client, batch_id):
    resp = client.post(
        f"/api/expense-batches/{batch_id}/statement",
        files={"statement": (
            "statement.example.csv",
            (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv",
        )},
        data={
            "account_id": "amex-9001",
            "account_legal_entities": '{"amex-9001": "Corporate Services"}',
            "account_card_currency": "USD",
        },
    )
    job_id = resp.json().get("job_id") if resp.status_code == 200 else None
    if job_id:
        assert client.get(f"/jobs/{job_id}").json()["status"] == "done"
    return resp


def _store(client) -> RunStore:
    return RunStore(Path(client._data_root) / "recon-web.sqlite")


def _snapshot(client, batch_id) -> dict:
    with _store(client) as store:
        return store.get_run(batch_id).snapshot or {}


def _matches(client, batch_id) -> list[dict]:
    return (_snapshot(client, batch_id).get("outcome") or {}).get(
        "matches"
    ) or []


# ── the spanning pool ────────────────────────────────────────────────


def test_a_month_statement_settles_from_an_overlapping_trip(
    client, monkeypatch
):
    """Ruling 3 end to end: the trip's Staples receipt settles the month
    statement's STAPLES charge, the claim is on file keyed to the TRIP,
    and both payloads name each other."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)  # consumes the Staples read
    month = _create_batch(client, fname="m.jpg", body=b"9")  # its own receipt

    _attach(client, month)

    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    settled = [m for m in _matches(client, month) if m["document_id"] == doc]
    assert settled, "the trip's receipt never reached the month's matcher"
    tx_id = settled[0]["transaction_id"]
    with _store(client) as store:
        claims = store.get_claims_by_run(month)
    assert [(c["receipt_run_id"], c["document_id"], c["transaction_id"])
            for c in claims] == [(trip_batch, doc, tx_id)], (
        "the claim must be keyed to the receipt's HOME run (the trip)"
    )
    # The month names the trip on the settled row; its own pool stays its
    # own (the borrowed receipt is not one of the month's receipts).
    view = client.get(f"/api/runs/{month}").json()
    row = next(r for r in view["rows"] if r["transaction_id"] == tx_id)
    assert row["settled_by"]["run_id"] == trip_batch
    assert row["settled_by"]["trip_id"] == trip_id
    assert row["settled_by"]["label"] == "TEST - Rome"
    assert all(
        "settled_by" not in r for r in view["rows"]
        if r["transaction_id"] != tx_id
    )
    assert view["summary"]["n_receipts"] == 1
    assert all(
        r.get("document_id") != doc for r in view["unmatched_receipts"]
    )
    # The trip names the month on the settled receipt.
    grid = client.get(f"/api/expense-batches/{trip_batch}").json()
    exp = next(e for e in grid["expenses"] if e["document_id"] == doc)
    assert exp["settled_by"]["run_id"] == month
    assert exp["settled_by"]["label"] == "April 2026"
    assert exp["settled_by"]["transaction_id"] == tx_id


def test_one_trip_receipt_never_settles_two_months(client, monkeypatch):
    """The global claim, cross-batch: two months whose statements both
    print the Staples charge overlap the same trip; only the first settles
    the trip's receipt, the second's charge stays unmatched. Disable the
    claims exclusion in `trip_pool_for_month` and both match — one
    receipt settling two charges across two batches."""
    _wire(
        monkeypatch,
        _extraction(),
        _extraction("Late Vendor", "17.00"),
        _extraction("Other Vendor", "9.99"),
    )
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)
    month_a = _create_batch(client, label="April 2026", fname="m.jpg", body=b"9")
    month_b = _create_batch(client, label="April 2026 again", fname="n.jpg", body=b"8")

    _attach(client, month_a)
    _attach(client, month_b)

    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    assert any(m["document_id"] == doc for m in _matches(client, month_a))
    assert not any(
        m["document_id"] == doc for m in _matches(client, month_b)
    ), "one receipt settled two charges across two batches"
    with _store(client) as store:
        assert store.get_claims_on_receipts(trip_batch)[doc][
            "claimed_by_run_id"] == month_a
        assert store.get_claims_by_run(month_b) == []


def test_a_disjoint_trip_stays_out_of_the_pool(client, monkeypatch):
    """Only trips whose date range overlaps the month's charge span
    contribute; a June trip has no business in an April statement."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    trip_id = _create_trip(client, start="2026-06-01", end="2026-06-10")
    trip_batch = _create_trip_batch(client, trip_id)
    month = _create_batch(client, fname="m.jpg", body=b"9")

    _attach(client, month)

    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    assert not any(m["document_id"] == doc for m in _matches(client, month))
    snap = _snapshot(client, month)
    assert "borrowed_receipts" not in snap
    assert "receipt_sources" not in snap
    with _store(client) as store:
        assert store.get_claims_by_run(month) == []


def test_a_confirmed_private_trip_receipt_never_meets_the_statement(
    client, monkeypatch
):
    """A confirmed private expense is somebody's own money (item 41), not
    company-card spend; it cannot settle a company statement charge."""
    _wire(monkeypatch, _extraction(), _extraction("Late Vendor", "17.00"))
    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)
    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    with _store(client) as store:
        store.set_expense_field_override(
            trip_batch, doc, "private", "1", "2026-09-07T00:00:00"
        )
        store.set_expense_field_override(
            trip_batch, doc, "reimburse_to", "Dirk", "2026-09-07T00:00:00"
        )
    month = _create_batch(client, fname="m.jpg", body=b"9")

    _attach(client, month)

    assert not any(m["document_id"] == doc for m in _matches(client, month))
    with _store(client) as store:
        assert store.get_claims_by_run(month) == []


def test_a_receipt_joining_a_trip_rematches_the_overlapping_month(
    client, monkeypatch
):
    """The trigger, creation-side: the month reconciled BEFORE the trip
    existed, its Staples charge unmatched. The trip batch materializing
    with that receipt re-matches the month without anyone touching it."""
    _wire(monkeypatch, _extraction("Late Vendor", "17.00"), _extraction())
    month = _create_batch(client, fname="m.jpg", body=b"9")
    _attach(client, month)
    staples_before = [
        m for m in _matches(client, month)
        if m["document_id"] != ""  # any match at all
    ]
    assert staples_before == [], "harness: the month matched something early"

    trip_id = _create_trip(client)
    trip_batch = _create_trip_batch(client, trip_id)  # consumes the Staples read

    doc = _snapshot(client, trip_batch)["receipts"][0]["document_id"]
    settled = [m for m in _matches(client, month) if m["document_id"] == doc]
    assert settled, (
        "the trip batch materialized but the overlapping month never "
        "re-matched"
    )
    with _store(client) as store:
        assert store.get_claims_on_receipts(trip_batch)[doc][
            "claimed_by_run_id"] == month


# ── the trip report ──────────────────────────────────────────────────


def test_trip_report_sections_per_person(client, monkeypatch):
    """Item 40 through the card chain, on paper: roster persons first in
    roster order, an off-roster person flagged, per-person sums, the trip
    named in the title with its range and roster beneath."""
    _wire(
        monkeypatch,
        _extraction("Hotel Roma", "100.00", payment_hint="VISA 1111"),
        _extraction("Trattoria", "50.00", date="2026-04-16",
                    payment_hint="VISA 2222"),
        _extraction("Taxi Zed", "20.00", date="2026-04-17",
                    payment_hint="VISA 3333"),
    )
    resp = client.put("/api/settings", json={"cards": {
        "card-dirk": {"label": "Dirk's card", "digits": ["1111"],
                      "entity": "Corporate Services", "person": "Dirk",
                      "currency": "USD", "active": True},
        "card-ana": {"label": "Ana's card", "digits": ["2222"],
                     "entity": "Corporate Services", "person": "Ana",
                     "currency": "USD", "active": True},
        "card-zed": {"label": "Zed's card", "digits": ["3333"],
                     "entity": "Corporate Services", "person": "Zed",
                     "currency": "USD", "active": True},
    }})
    assert resp.status_code == 200, resp.text
    trip_id = _create_trip(client, travelers=("Dirk", "Ana"))
    trip_batch = _create_trip_batch(client, trip_id, files=[
        ("files", ("h.jpg", JPG + b"1", "application/octet-stream")),
        ("files", ("t.jpg", JPG + b"2", "application/octet-stream")),
        ("files", ("z.jpg", JPG + b"3", "application/octet-stream")),
    ])

    resp = client.get(f"/runs/{trip_batch}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    text = PdfReader(io.BytesIO(resp.content)).pages[0].extract_text() or ""
    assert "Trip report" in text and "TEST - Rome" in text
    assert "2026-04-01 to 2026-04-20" in text
    assert "travelers: Dirk, Ana" in text
    assert "Dirk: 1 expense" in text
    assert "Ana: 1 expense" in text
    assert "Zed: 1 expense" in text
    assert "not on the trip roster" in text
    # Roster order first, the off-roster person after.
    assert text.index("Dirk: 1") < text.index("Ana: 1") < text.index(
        "Zed: 1"
    )


def test_a_company_month_report_is_not_sectioned(client, monkeypatch):
    """The flat listing is untouched for company months — the trip report
    is a trip-batch behavior, not a new default."""
    _wire(monkeypatch, _extraction())
    month = _create_batch(client, fname="m.jpg", body=b"9")
    resp = client.get(f"/runs/{month}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    text = PdfReader(io.BytesIO(resp.content)).pages[0].extract_text() or ""
    assert "Expense report" in text
    assert "not on the trip roster" not in text
    assert "Trip report" not in text
