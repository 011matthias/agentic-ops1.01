"""Item 47 step 5: `GET /api/cost-centers/totals`, the cross-month roll-up.

The only surface that aggregates ACROSS batches. Every test goes through
the route, never through `build_cost_center_totals`, so what is pinned is
the wiring: the route parses and passes the range, the service scans every
expense batch (months and trips), resolves each row through the same chain
the grid runs, leaves confirmed private rows out, and never hides the
unassigned bucket.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.llm.client import ExtractedReceipt, MockLLMClient  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402

JPG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"

CARDS = {
    "lidar-1111": {
        "label": "Lidar card", "digits": ["1111"],
        "entity": "Corporate Services", "person": "Nicolas",
        "default_cost_center": "Lidar",
    },
    "plain-9999": {
        "label": "Plain card", "digits": ["9999"],
        "entity": "Corporate Services", "person": "Dirk",
    },
}

CENTERS = {
    "Lidar": {"kind": "project"},
    "Marketing": {"kind": "function"},
    "Brazil": {"kind": "trip"},
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


def _totals(client, **params) -> dict:
    resp = client.get("/api/cost-centers/totals", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _center(payload: dict, name: str) -> dict:
    hits = [c for c in payload["cost_centers"] if c["name"] == name]
    assert len(hits) == 1, payload["cost_centers"]
    return hits[0]


def _two_months(client, monkeypatch):
    """August: 100 USD on the Lidar card + 5 USD on the plain card.
    September: 25 USD on the Lidar card. Distinct file bytes per batch so
    nothing is filed as a duplicate."""
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Lidar Parts Co", total="100.00",
                    payment_hint="Visa ...1111"),
        _extraction(vendor="Coffee Bar", total="5.00", date="2026-08-03",
                    payment_hint="Visa ...9999"),
    )
    august = _create_batch(client, n_files=2, label="August 2026")
    _patch_ocr(
        monkeypatch,
        _extraction(vendor="Lidar Optics", total="25.00", date="2026-09-03",
                    payment_hint="Visa ...1111"),
    )
    resp = client.post("/api/expense-batches",
                       data={"legal_entity": "", "label": "September 2026"})
    assert resp.status_code == 200, resp.text
    september = resp.json()["batch_id"]
    assert client.get(
        f"/jobs/{resp.json()['job_id']}").json()["status"] == "done"
    added = client.post(f"/api/expense-batches/{september}/receipts", files=[
        ("files", ("sep.jpg", JPG + b"\x09\x09", "application/octet-stream")),
    ])
    assert added.status_code == 200, added.text
    assert client.get(
        f"/jobs/{added.json()['job_id']}").json()["status"] == "done"
    return august, september


def test_totals_roll_up_every_batch_per_centre_and_currency(
    client, monkeypatch,
):
    """Two months, one project: the roll-up crosses the batch boundary,
    lists every active centre (at zero when nothing reached it), keeps
    the unassigned bucket explicit, and carries the stated limit."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _two_months(client, monkeypatch)

    payload = _totals(client)
    assert payload["from"] is None and payload["to"] is None
    assert "not a total project cost" in payload["note"]
    assert payload["n_batches"] == 2
    assert payload["n_rows"] == 3
    assert payload["n_undated"] == 0

    lidar = _center(payload, "Lidar")
    assert lidar == {"name": "Lidar", "kind": "project", "active": True,
                     "n_rows": 2, "n_batches": 2, "totals": {"USD": "125.00"}}
    assert _center(payload, "Marketing")["n_rows"] == 0
    assert _center(payload, "Marketing")["totals"] == {}
    assert [c["name"] for c in payload["cost_centers"]] == [
        "Brazil", "Lidar", "Marketing",
    ]
    assert payload["unassigned"] == {
        "n_rows": 1, "n_batches": 1, "totals": {"USD": "5.00"},
    }


def test_the_range_filters_on_the_row_date_inclusively(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _two_months(client, monkeypatch)

    since_sep = _totals(client, **{"from": "2026-09-01"})
    assert since_sep["from"] == "2026-09-01"
    assert _center(since_sep, "Lidar")["totals"] == {"USD": "25.00"}
    assert _center(since_sep, "Lidar")["n_batches"] == 1
    assert since_sep["unassigned"]["n_rows"] == 0
    assert since_sep["n_rows"] == 1
    # The batch count is what was SCANNED, not what fell in range.
    assert since_sep["n_batches"] == 2

    # Inclusive on both ends: the 2026-08-03 coffee is inside [08-03, 08-03].
    one_day = _totals(client, **{"from": "2026-08-03", "to": "2026-08-03"})
    assert one_day["unassigned"]["totals"] == {"USD": "5.00"}
    assert _center(one_day, "Lidar")["n_rows"] == 0


def test_a_bad_range_is_refused_with_a_reason(client):
    r = client.get("/api/cost-centers/totals", params={"from": "2026-13-40"})
    assert r.status_code == 400, r.text
    assert "from" in r.json()["error"] and "2026-13-40" in r.json()["error"]
    r = client.get("/api/cost-centers/totals",
                   params={"from": "2026-09-01", "to": "2026-08-01"})
    assert r.status_code == 400, r.text
    assert "after" in r.json()["error"]


def test_a_confirmed_private_row_is_not_company_spend(client, monkeypatch):
    """A reimbursement owed is somebody's money, not the project's: the
    row leaves the roll-up the moment the reviewer confirms it private."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(vendor="Lidar Parts Co",
                                        total="100.00",
                                        payment_hint="Visa ...1111"))
    batch = _create_batch(client)
    assert _center(_totals(client), "Lidar")["n_rows"] == 1

    doc = _row(client, batch)["document_id"]
    r = client.post(f"/api/runs/{batch}/expenses/{doc}/private",
                    json={"private": True, "reimburse_to": "Nicolas"})
    assert r.status_code == 200, r.text

    payload = _totals(client)
    assert _center(payload, "Lidar")["n_rows"] == 0
    assert payload["unassigned"]["n_rows"] == 0
    assert payload["n_rows"] == 0


def test_the_trip_cost_center_reaches_the_roll_up(client, monkeypatch):
    """A trip batch counts like a month, and its rows land on the cost
    center a human declared on the trip (the strongest automatic link)."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    resp = client.post("/api/trips", json={
        "name": "TEST - Brazil", "start": "2026-08-01", "end": "2026-08-10",
        "travelers": ["Nicolas"], "cost_center": "Brazil",
    })
    assert resp.status_code == 200, resp.text
    _patch_ocr(monkeypatch, _extraction(vendor="Hotel Rio", total="300.00",
                                        currency="BRL",
                                        payment_hint="Visa ...1111"))
    _create_batch(client, extra={
        "batch_type": "trip", "trip_id": resp.json()["trip_id"],
    })

    payload = _totals(client)
    assert payload["n_batches"] == 1
    assert _center(payload, "Brazil") == {
        "name": "Brazil", "kind": "trip", "active": True,
        "n_rows": 1, "n_batches": 1, "totals": {"BRL": "300.00"},
    }
    # The card default (Lidar) lost to the trip, as on the row itself.
    assert _center(payload, "Lidar")["n_rows"] == 0


def test_with_no_cost_center_defined_everything_is_unassigned(
    client, monkeypatch,
):
    """The roll-up states the fact rather than hiding it: an empty
    registry lists no centres and puts every row in the unassigned
    bucket. That is not a review state; the review flag stays silent."""
    client.put("/api/settings", json={"cards": CARDS})
    _two_months(client, monkeypatch)

    payload = _totals(client)
    assert payload["cost_centers"] == []
    assert payload["unassigned"] == {
        "n_rows": 3, "n_batches": 2, "totals": {"USD": "130.00"},
    }


def test_an_inactive_centre_is_listed_only_while_history_sits_on_it(
    client, monkeypatch,
):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": {
        **CENTERS, "Retired": {"kind": "project", "active": False},
    }})
    _patch_ocr(monkeypatch, _extraction(vendor="Lidar Parts Co",
                                        payment_hint="Visa ...1111"))
    batch = _create_batch(client)
    assert [c["name"] for c in _totals(client)["cost_centers"]] == [
        "Brazil", "Lidar", "Marketing",
    ]

    doc = _row(client, batch)["document_id"]
    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": "Retired"})
    assert r.status_code == 200, r.text

    payload = _totals(client)
    retired = _center(payload, "Retired")
    assert retired["active"] is False and retired["n_rows"] == 1
    assert _center(payload, "Lidar")["n_rows"] == 0
