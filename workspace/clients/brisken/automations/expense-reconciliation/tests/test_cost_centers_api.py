"""Cost centers THROUGH the settings API, not through the helper.

B2 fix-bites-the-caller: test_cost_centers.py proves the registry works;
this file proves it is WIRED. Unplug the PUT branch or the GET derive and
something here goes red.
"""
from __future__ import annotations

import pytest

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


def test_default_is_an_empty_registry_and_no_options(client):
    body = client.get("/api/settings").json()
    assert body["cost_centers"] == {}
    assert body["cost_center_options"] == []


def test_put_stores_and_get_derives_the_picker(client):
    r = client.put("/api/settings", json={"cost_centers": {
        "Lidar": {"kind": "project", "note": "laser"},
        "Marketing": {"kind": "function"},
        "Retired": {"kind": "project", "active": False},
    }})
    assert r.status_code == 200, r.text
    assert r.json()["cost_centers"]["Lidar"] == {"kind": "project", "note": "laser"}

    body = client.get("/api/settings").json()
    # active only, name-sorted, kind carried for the roll-up grouping
    assert body["cost_center_options"] == [
        {"name": "Lidar", "kind": "project", "note": "laser"},
        {"name": "Marketing", "kind": "function", "note": ""},
    ]


def test_a_malformed_payload_is_a_400_at_the_edge(client):
    r = client.put("/api/settings", json={"cost_centers": {"X": {"kind": "department"}}})
    assert r.status_code == 400
    assert "kind" in r.json()["error"]
    assert client.get("/api/settings").json()["cost_centers"] == {}


def test_case_collision_is_refused_rather_than_silently_dropping_one(client):
    r = client.put("/api/settings", json={"cost_centers": {"Lidar": {}, "lidar": {}}})
    assert r.status_code == 400
    assert "case" in r.json()["error"]


def test_whole_map_replace_like_the_sibling_registries(client):
    client.put("/api/settings", json={"cost_centers": {"A": {}, "B": {}}})
    client.put("/api/settings", json={"cost_centers": {"B": {}}})
    assert set(client.get("/api/settings").json()["cost_centers"]) == {"B"}


def test_options_are_read_only_and_a_put_of_them_is_ignored(client):
    client.put("/api/settings", json={"cost_center_options": [{"name": "Sneaky"}]})
    body = client.get("/api/settings").json()
    assert body["cost_centers"] == {}
    assert body["cost_center_options"] == []


def test_other_settings_survive_a_cost_center_write(client):
    client.put("/api/settings", json={"merchants": {"Acme": {"aliases": ["ACME INC"]}}})
    client.put("/api/settings", json={"cost_centers": {"Lidar": {}}})
    body = client.get("/api/settings").json()
    assert "Acme" in body["merchants"]
    assert "Lidar" in body["cost_centers"]
