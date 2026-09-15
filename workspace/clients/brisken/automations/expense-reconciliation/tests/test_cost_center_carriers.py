"""The three carriers of a cost center, tested THROUGH their callers.

Item 47 step 2a/2b/2d. A cost center reaches an expense row from one of
four places; the override is the row's own edit, and the other three are
carried by a card, a merchant registry entry, and a trip. This file proves
each carrier round-trips through the surface that actually writes it (the
settings PUT, the trips POST/PUT), not just through its normalize helper.

The shared contract across all three (B2 fix-bites-the-caller): the name is
stored as typed and is NOT validated against the cost-center registry at
the settings edge. Cards, merchants, trips and cost centers are edited
independently, so requiring the centre to exist first would make the edit
ORDER matter -- define a card's project before the project exists and the
save would fail for a reason the operator cannot see from that screen.
Validation happens at RESOLUTION time instead, where an unknown name simply
fails to resolve.
"""
from __future__ import annotations

import pytest

from expense_recon.cards import (
    Card,
    card_to_dict,
    cards_from_setting,
    cards_to_setting,
    effective_cards,
    normalize_cards_setting,
)
from expense_recon.merchant_registry import (
    MerchantRegistry,
    normalize_merchants_setting,
)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


# --- 2a: the card ------------------------------------------------------


def test_card_default_cost_center_survives_the_settings_put(client):
    r = client.put("/api/settings", json={"cards": {
        "corp-2838": {"label": "Corporate", "default_cost_center": "Lidar"},
    }})
    assert r.status_code == 200, r.text
    stored = client.get("/api/settings").json()["cards"]["corp-2838"]
    assert stored["default_cost_center"] == "Lidar"

    cards = client.get("/api/cards").json()["cards"]
    corp = next(c for c in cards if c["key"] == "corp-2838")
    assert corp["default_cost_center"] == "Lidar"


def test_a_card_with_no_cost_center_reads_blank_never_absent(client):
    client.put("/api/settings", json={"cards": {"plain": {"label": "Plain"}}})
    cards = client.get("/api/cards").json()["cards"]
    plain = next(c for c in cards if c["key"] == "plain")
    # Parallel field, always present: a stale SPA reading `.default_cost_center`
    # gets "" rather than undefined.
    assert plain["default_cost_center"] == ""


def test_the_settings_edge_does_not_require_the_centre_to_exist(client):
    """The edit-order contract. `cards` is saved before `cost_centers`
    exists at all, and the save stands."""
    r = client.put("/api/settings", json={"cards": {
        "corp": {"label": "Corp", "default_cost_center": "NotDefinedYet"},
    }})
    assert r.status_code == 200, r.text
    assert client.get("/api/settings").json()["cards"]["corp"][
        "default_cost_center"] == "NotDefinedYet"


def test_card_normalize_trims_and_drops_the_blank():
    out = normalize_cards_setting({
        "a": {"default_cost_center": "  Lidar  "},
        "b": {"default_cost_center": "   "},
    })
    assert out["a"]["default_cost_center"] == "Lidar"
    # Empty fields are omitted entirely, keeping the settings blob small.
    assert "default_cost_center" not in out["b"]


def test_card_snapshot_round_trip_carries_the_cost_center():
    """`cards_to_setting` snapshots the composed registry into a batch's
    run config; a field it drops never reaches an existing batch."""
    card = Card(key="corp", label="Corp", default_cost_center="Lidar")
    snap = cards_to_setting({"corp": card})
    assert snap["corp"]["default_cost_center"] == "Lidar"
    assert cards_from_setting(snap)["corp"].default_cost_center == "Lidar"


def test_legacy_composition_leaves_the_cost_center_blank():
    """Read-time composition is the migration: a tenant whose cards exist
    only as legacy maps gets "" here, not a crash and not a guess."""
    composed = effective_cards({"card_entities": {"2838": "Corporate"}})
    assert [c.default_cost_center for c in composed.values()] == [""]
    assert card_to_dict(next(iter(composed.values())))[
        "default_cost_center"] == ""


# --- 2b: the merchant registry entry -----------------------------------


def test_merchant_cost_center_survives_the_settings_put(client):
    r = client.put("/api/settings", json={"merchants": {
        "Velodyne": {"aliases": ["VELODYNE LIDAR"], "cost_center": "Lidar"},
    }})
    assert r.status_code == 200, r.text
    stored = client.get("/api/settings").json()["merchants"]["Velodyne"]
    assert stored["cost_center"] == "Lidar"


def test_merchant_registry_resolve_carries_the_cost_center():
    reg = MerchantRegistry({
        "Velodyne": {"aliases": ["VELODYNE LIDAR INC"], "cost_center": "Lidar"},
    })
    match = reg.resolve("VELODYNE LIDAR INC", None)
    assert match is not None
    assert match.canonical_name == "Velodyne"
    assert match.cost_center == "Lidar"


def test_a_merchant_with_no_cost_center_resolves_none():
    reg = MerchantRegistry({"Uber": {"aliases": [], "category": None}})
    match = reg.resolve("Uber", None)
    assert match is not None and match.cost_center is None


def test_multi_category_merchant_still_carries_its_cost_center():
    """`multi_category` decouples the registry's CATEGORY fact, because the
    vendor books to different categories. The cost center is a different
    dimension -- Amazon buying for one project is still that project -- so
    the flag does not suppress it."""
    reg = MerchantRegistry({
        "Amazon": {"aliases": [], "multi_category": True, "cost_center": "Lidar"},
    })
    match = reg.resolve("Amazon", None)
    assert match is not None
    assert match.category is None
    assert match.cost_center == "Lidar"


def test_merchant_normalize_keeps_the_shape_stable():
    out = normalize_merchants_setting({
        "A": {"cost_center": "  Lidar "},
        "B": {"aliases": ["b"]},
    })
    assert out["A"]["cost_center"] == "Lidar"
    # Stored only when set, so an existing entry's diff stays honest.
    assert "cost_center" not in out["B"]


# --- 2d: the trip ------------------------------------------------------


def _make_trip(client, **extra):
    payload = {
        "name": "Brazil", "start": "2026-03-01", "end": "2026-03-10",
        "travelers": ["Nicolas"],
    }
    payload.update(extra)
    return client.post("/api/trips", json=payload)


def test_trip_carries_a_cost_center_through_post(client):
    r = _make_trip(client, cost_center="Brazil")
    assert r.status_code == 200, r.text
    assert r.json()["cost_center"] == "Brazil"

    listed = client.get("/api/trips").json()["trips"]
    assert [t["cost_center"] for t in listed] == ["Brazil"]


def test_trip_without_a_cost_center_reads_blank(client):
    r = _make_trip(client)
    assert r.status_code == 200, r.text
    assert r.json()["cost_center"] == ""


def test_put_trip_sets_and_clears_the_cost_center(client):
    trip_id = _make_trip(client).json()["trip_id"]

    r = client.put(f"/api/trips/{trip_id}", json={"cost_center": "Brazil"})
    assert r.status_code == 200, r.text
    assert r.json()["cost_center"] == "Brazil"
    # The roster must survive a save that did not mention it (the whole-map
    # -replace trap that already bit `person` on cards).
    assert r.json()["travelers"] == ["Nicolas"]

    r = client.put(f"/api/trips/{trip_id}", json={"cost_center": ""})
    assert r.status_code == 200, r.text
    assert r.json()["cost_center"] == ""


def test_put_trip_that_omits_cost_center_keeps_it(client):
    trip_id = _make_trip(client, cost_center="Brazil").json()["trip_id"]
    r = client.put(f"/api/trips/{trip_id}", json={"name": "Brazil 2026"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Brazil 2026"
    assert r.json()["cost_center"] == "Brazil"


def test_a_pre_cost_center_trips_table_migrates(tmp_path):
    """The column is added to an existing database, so a deployed tenant's
    trips survive the upgrade instead of erroring on SELECT *."""
    import sqlite3

    from expense_recon.web.store import RunStore

    db = tmp_path / "runs.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE trips (trip_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,"
        " name TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,"
        " travelers TEXT NOT NULL, updated_at TEXT)"
    )
    conn.execute(
        "INSERT INTO trips VALUES ('t1', 'x', 'Old', '2026-01-01',"
        " '2026-01-02', '[]', NULL)"
    )
    conn.commit()
    conn.close()

    with RunStore(db) as store:
        trip = store.get_trip("t1")
        assert trip is not None
        assert trip.name == "Old"
        assert trip.cost_center == ""
