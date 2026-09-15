"""Item 47 step 3: the month report grouped by cost center, on paper.

test_cost_center_resolution.py proves the chain lands on the row; this
file proves `build_expense_report` partitions the LISTING on it and that
the route hands the report the live settings it resolves against (B2
fix-bites-the-caller). Every test goes through
`GET /runs/{id}/expense-report.pdf`, never through the PDF builder.

The flat-listing test is the one that would fail SILENTLY: with no cost
center defined the report must stay exactly as it was. The report does
not re-check the registry; it partitions only when the chain resolves or
flags a row, so that test rides the empty-registry contract's single home
in `CostCenterRegistry.resolve` and reddens if that home is unwired.
"""
from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("pypdf")

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CARDS = {
    "lidar-1111": {
        "label": "Lidar card", "digits": ["1111"],
        "entity": "Corporate Services", "person": "Nicolas",
        "default_cost_center": "Lidar",
    },
    "mkt-2222": {
        "label": "Marketing card", "digits": ["2222"],
        "entity": "Corporate Services", "person": "Dirk",
        "default_cost_center": "Marketing",
    },
    "plain-9999": {
        "label": "Plain card", "digits": ["9999"],
        "entity": "Corporate Services", "person": "Dirk",
    },
}

CENTERS = {
    "Lidar": {"kind": "project"},
    "Marketing": {"kind": "function"},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EXPENSE_RECON_CARDS", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def _patch_ocr(monkeypatch, *extractions):
    mock = MockLLMClient(extraction_responses=list(extractions))
    monkeypatch.setattr(
        "expense_recon.cli._build_llm_client", lambda cfg: (mock, None)
    )


def _extraction(**overrides) -> ExtractedReceipt:
    base = dict(date="2026-08-01", total="42.50", currency="USD",
                vendor="Staples", reference="", line_items=(),
                confidence=0.9, notes="")
    base.update(overrides)
    return ExtractedReceipt(**base)


def _create_batch(client, n_files=1, label="August 2026", extra=None):
    data = {"legal_entity": "", "label": label}
    files = [
        ("files", (f"r{i}.jpg", JPG + bytes([i]), "application/octet-stream"))
        for i in range(n_files)
    ]
    if (extra or {}).get("batch_type") == "trip":
        data.update(extra)
        resp = client.post("/api/expense-batches", files=files, data=data)
        assert resp.status_code == 200, resp.text
        assert client.get(
            f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
        return resp.json()["batch_id"]
    resp = client.post("/api/expense-batches", data=data)
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["batch_id"]
    assert client.get(
        f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    added = client.post(f"/api/expense-batches/{batch_id}/receipts", files=files)
    assert added.status_code == 200, added.text
    assert client.get(
        f"/jobs/{added.json()['job_id']}").json()["status"] == "done"
    return batch_id


def _row(client, batch_id, index=0) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()["expenses"][index]


def _report_text(client, batch_id) -> str:
    """The whole report's text, whitespace-normalized so a phrase that
    wraps across a line break still matches."""
    resp = client.get(f"/runs/{batch_id}/expense-report.pdf")
    assert resp.status_code == 200, resp.text
    pages = PdfReader(io.BytesIO(resp.content)).pages
    return " ".join(" ".join(p.extract_text() or "" for p in pages).split())


THREE_CARDS = (
    _extraction(vendor="Lidar Parts Co", total="100.00",
                payment_hint="Visa ...1111"),
    _extraction(vendor="Ad Agency", total="50.00", date="2026-08-02",
                payment_hint="Visa ...2222"),
    _extraction(vendor="Coffee Bar", total="5.00", date="2026-08-03",
                payment_hint="Visa ...9999"),
)


def test_the_month_report_groups_by_cost_center_once_one_is_defined(
    client, monkeypatch,
):
    """Named centres in name order with their kind, each with its own
    sums line, the unassigned slice LAST, and the stated limit above the
    partition."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, *THREE_CARDS)
    batch = _create_batch(client, n_files=3)

    text = _report_text(client, batch)
    assert "Expense report" in text
    assert "Listing by cost center" in text
    assert "Card and receipt spend only" in text
    assert "not a total project cost" in text
    assert "Lidar (project)" in text
    assert "Marketing (function)" in text
    assert "Unassigned (no cost center)" in text
    assert "Lidar: 1 expense" in text
    assert "Marketing: 1 expense" in text
    assert "Unassigned: 1 expense" in text
    assert "USD 100.00" in text and "USD 50.00" in text and "USD 5.00" in text
    assert text.index("Lidar: 1") < text.index("Marketing: 1") < text.index(
        "Unassigned: 1"
    )


def test_the_month_report_stays_flat_while_no_cost_center_is_defined(
    client, monkeypatch,
):
    """THE contract, on paper. The cards below carry defaults, so the
    only thing keeping this report flat is the empty registry resolving
    nothing and flagging nothing. Without that, the listing would
    partition into one all-unassigned section on every month in the
    tool, the day the field ships."""
    client.put("/api/settings", json={"cards": CARDS})
    _patch_ocr(monkeypatch, *THREE_CARDS)
    batch = _create_batch(client, n_files=3)

    text = _report_text(client, batch)
    assert "Expense report" in text
    assert "3 expenses" in text
    assert "Listing by cost center" not in text
    assert "Unassigned" not in text
    assert "total project cost" not in text


def test_unassigned_is_its_own_final_section_even_when_nothing_resolves(
    client, monkeypatch,
):
    """A centre exists but no row reaches it: the report still partitions,
    and what it shows is an honest all-unassigned section rather than the
    flat listing pretending nothing is defined."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(vendor="Coffee Bar", total="5.00",
                                        payment_hint="Visa ...9999"))
    batch = _create_batch(client)

    text = _report_text(client, batch)
    assert "Listing by cost center" in text
    assert "Unassigned (no cost center)" in text
    assert "Unassigned: 1 expense" in text
    assert "Lidar" not in text and "Marketing" not in text


def test_a_row_override_moves_the_row_between_sections(client, monkeypatch):
    """The report partitions on the RESOLVED name, so a reviewer's
    override lands the row in the section they chose."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(vendor="Lidar Parts Co",
                                        payment_hint="Visa ...1111"))
    batch = _create_batch(client)
    assert "Lidar: 1 expense" in _report_text(client, batch)

    doc = _row(client, batch)["document_id"]
    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": "Marketing"})
    assert r.status_code == 200, r.text

    text = _report_text(client, batch)
    assert "Marketing: 1 expense" in text
    assert "Lidar: 1 expense" not in text
    assert "Unassigned" not in text


def test_a_trip_report_keeps_its_per_person_sections(client, monkeypatch):
    """Item 38 owns the trip report. A defined registry and a trip that
    carries a cost center change nothing on paper: the trip still
    sections per person and never grows the cost-center partition."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    resp = client.post("/api/trips", json={
        "name": "TEST - Brazil", "start": "2026-08-01", "end": "2026-08-10",
        "travelers": ["Nicolas"], "cost_center": "Lidar",
    })
    assert resp.status_code == 200, resp.text
    trip_id = resp.json()["trip_id"]
    _patch_ocr(monkeypatch, _extraction(vendor="Hotel Rio", total="100.00",
                                        payment_hint="Visa ...1111"))
    batch = _create_batch(client, extra={
        "batch_type": "trip", "trip_id": trip_id,
    })

    text = _report_text(client, batch)
    assert "Trip report" in text
    assert "Nicolas: 1 expense" in text
    assert "Listing by cost center" not in text
