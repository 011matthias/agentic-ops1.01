"""Item 47 step 2c/2e: the cost-center chain RESOLVED onto expense rows.

test_cost_centers.py proves the registry decides correctly; this file
proves `build_expense_view` actually calls it and puts the answer on the
row (B2 fix-bites-the-caller). Every test here goes through
`GET /api/expense-batches/{id}` or the field-override PUT, never through
`CostCenterRegistry.resolve` directly.

The first test is the one that matters most and the only one that would
fail SILENTLY if the contract broke: with no cost centers defined, every
row must resolve to nothing AND flag nothing. Without it, the day this
ships every row in every month reads `needs_cost_center`, and a review
state firing at 100% is noise rather than signal.
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
    "corp-1672": {
        "label": "Corporate card (Chase)",
        "digits": ["1672"],
        "entity": "Corporate Services",
        "person": "Nicolas",
        "default_cost_center": "Lidar",
    },
    "plain-9999": {
        "label": "Plain card",
        "digits": ["9999"],
        "entity": "Corporate Services",
        "person": "Nicolas",
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
        # Trip batches keep their create-with-receipt shape.
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


def _grid(client, batch_id) -> dict:
    resp = client.get(f"/api/expense-batches/{batch_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _row(client, batch_id, index=0) -> dict:
    return _grid(client, batch_id)["expenses"][index]


# --- the empty-registry contract ---------------------------------------


def test_an_empty_registry_resolves_nothing_and_flags_nothing(
    client, monkeypatch
):
    """THE contract. The card below carries a `default_cost_center`, so
    something COULD resolve; nothing may, because the owner has defined no
    cost centers and a name nobody defined is not a cost center.

    This is the test that fails silently: break it and the feature still
    "works", it just shouts `needs_cost_center` on every row of every month
    from the day it ships.
    """
    client.put("/api/settings", json={"cards": CARDS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    grid = _grid(client, batch)

    row = grid["expenses"][0]
    assert row["cost_center"] is None
    assert row["cost_center_source"] == ""
    assert row["cost_center_source_label"] == ""
    assert row["needs_cost_center"] is False
    assert grid["summary"]["n_needs_cost_center"] == 0
    assert grid["cost_center_options"] == []
    # And no row is pushed into review by it.
    assert row["review"]["reason_code"] != "needs_cost_center"


# --- the chain, one link at a time -------------------------------------


def test_the_card_default_resolves_once_the_centre_is_defined(
    client, monkeypatch
):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    row = _row(client, batch)

    assert row["cost_center"] == "Lidar"
    assert row["cost_center_source"] == "card"
    # Rule 5: the enum ships WITH a parallel label, so an un-updated SPA
    # degrades to correct text instead of somebody else's copy.
    assert row["cost_center_source_label"] == "default for this card"
    assert row["needs_cost_center"] is False


def test_the_merchant_registry_outranks_the_card(client, monkeypatch):
    client.put("/api/settings", json={
        "cards": CARDS,
        "cost_centers": CENTERS,
        "merchants": {"Staples": {"aliases": [], "cost_center": "Marketing"}},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    row = _row(client, batch)

    assert row["cost_center"] == "Marketing"
    assert row["cost_center_source"] == "merchant"
    assert row["cost_center_source_label"] == "learned for this merchant"


def test_the_trip_outranks_the_merchant(client, monkeypatch):
    client.put("/api/settings", json={
        "cards": CARDS,
        "cost_centers": CENTERS,
        "merchants": {"Staples": {"aliases": [], "cost_center": "Marketing"}},
    })
    trip = client.post("/api/trips", json={
        "name": "Brazil", "start": "2026-07-25", "end": "2026-08-10",
        "travelers": ["Nicolas"], "cost_center": "Brazil",
    })
    assert trip.status_code == 200, trip.text
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client, label="TEST - Brazil", extra={
        "batch_type": "trip", "trip_id": trip.json()["trip_id"],
    })
    row = _row(client, batch)

    # A human DECLARED the trip's cost center at creation; that outranks
    # anything the tool inferred from a merchant or a card.
    assert row["cost_center"] == "Brazil"
    assert row["cost_center_source"] == "trip"
    assert row["cost_center_source_label"] == "from the trip"


def test_the_row_override_beats_everything(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    assert _row(client, batch)["cost_center"] == "Lidar"  # from the card

    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": "Marketing"})
    assert r.status_code == 200, r.text

    row = _row(client, batch)
    assert row["cost_center"] == "Marketing"
    assert row["cost_center_source"] == "override"
    assert row["cost_center_source_label"] == "set by reviewer"
    # It rides the EXISTING override mechanism, so it lands in edited_fields
    # like any other field edit; no second path through the export.
    assert "cost_center" in row["edited_fields"]


def test_clearing_the_override_falls_back_down_the_chain(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    client.put(f"/api/runs/{batch}/expenses/{doc}",
               json={"field": "cost_center", "value": "Marketing"})

    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": ""})
    assert r.status_code == 200, r.text
    row = _row(client, batch)
    assert row["cost_center"] == "Lidar"
    assert row["cost_center_source"] == "card"


# --- the review state ---------------------------------------------------


def test_needs_cost_center_fires_only_after_needs_person(client, monkeypatch):
    """Registry work of the same class as needs_person, ranked below it: a
    row with no owner is the more actionable gap, and the cost-center flag
    must never hide it."""
    client.put("/api/settings", json={
        "cost_centers": CENTERS,
        # entity known, NO person, NO cost center
        "cards": {"corp-1672": {
            "digits": ["1672"], "entity": "Corporate Services",
        }},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]
    r = client.post(f"/api/runs/{batch}/categories", json={
        "document_id": doc, "line_index": 0,
        "category": "Software & Subscriptions",
    })
    assert r.status_code == 200, r.text

    # person is missing too, and it wins.
    row = _row(client, batch)
    assert row["review"]["reason_code"] == "needs_person"
    assert row["needs_cost_center"] is True  # the FIELD is honest meanwhile

    # give the card a person; now the cost-center gap is what is left.
    client.put("/api/settings", json={"cards": {"corp-1672": {
        "digits": ["1672"], "entity": "Corporate Services",
        "person": "Nicolas",
    }}})
    r = client.post(f"/api/expense-batches/{batch}/refresh-master-data")
    assert r.status_code == 200, r.text

    row = _row(client, batch)
    assert row["review"]["state"] == "check"
    assert row["review"]["reason_code"] == "needs_cost_center"
    assert row["review"]["reason"]  # rule 5: the prose rides beside the code
    assert _grid(client, batch)["summary"]["n_needs_cost_center"] == 1


def test_a_more_actionable_row_exception_still_wins(client, monkeypatch):
    """An uncategorized row is row work; the cost-center gap is registry
    work. The row exception wins."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...9999"))
    batch = _create_batch(client)
    row = _row(client, batch)
    assert row["needs_cost_center"] is True
    assert row["review"]["reason_code"] in (
        "uncategorized", "partial_uncategorized",
    )


def test_the_picker_options_reach_the_batch_payload(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": {
        **CENTERS, "Retired": {"kind": "project", "active": False},
    }})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    options = _grid(client, batch)["cost_center_options"]
    # active only, name-sorted, kind carried for the roll-up grouping
    assert [o["name"] for o in options] == ["Brazil", "Lidar", "Marketing"]


# --- the override's validation -----------------------------------------


def test_an_undefined_name_is_refused_at_the_route(client, monkeypatch):
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]

    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": "Invented"})
    assert r.status_code == 400
    assert "not a defined" in r.json()["error"]
    # and nothing was stored
    assert _row(client, batch)["cost_center"] == "Lidar"


def test_the_override_stores_the_registrys_own_spelling(client, monkeypatch):
    """A picked name and a typed one must not read as two centres."""
    client.put("/api/settings", json={"cards": CARDS, "cost_centers": CENTERS})
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    doc = _row(client, batch)["document_id"]

    r = client.put(f"/api/runs/{batch}/expenses/{doc}",
                   json={"field": "cost_center", "value": "  marketing  "})
    assert r.status_code == 200, r.text
    assert _row(client, batch)["cost_center"] == "Marketing"


def test_a_default_never_resurrects_an_inactive_centre(client, monkeypatch):
    """Deactivating a cost center stops it being STAMPED, without unlabelling
    the history already attributed to it (an override still names it)."""
    client.put("/api/settings", json={
        "cards": CARDS,
        "cost_centers": {**CENTERS, "Lidar": {"kind": "project",
                                              "active": False}},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    row = _row(client, batch)
    assert row["cost_center"] is None
    assert row["needs_cost_center"] is True

    # but a deliberate override onto the retired project is accepted
    r = client.put(f"/api/runs/{batch}/expenses/{row['document_id']}",
                   json={"field": "cost_center", "value": "Lidar"})
    assert r.status_code == 200, r.text
    assert _row(client, batch)["cost_center"] == "Lidar"


def test_an_undefined_card_default_leaves_the_row_unresolved(
    client, monkeypatch
):
    """The edit-order contract seen from the resolution end: a card naming a
    centre nobody defined resolves to nothing rather than inventing it."""
    client.put("/api/settings", json={
        "cost_centers": CENTERS,
        "cards": {"corp-1672": {
            "digits": ["1672"], "entity": "Corporate Services",
            "person": "Nicolas", "default_cost_center": "NotDefinedYet",
        }},
    })
    _patch_ocr(monkeypatch, _extraction(payment_hint="Visa ...1672"))
    batch = _create_batch(client)
    row = _row(client, batch)
    assert row["cost_center"] is None
    assert row["needs_cost_center"] is True
