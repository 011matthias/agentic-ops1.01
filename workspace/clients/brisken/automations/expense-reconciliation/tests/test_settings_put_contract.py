"""What `PUT /api/settings` wrote, and what it refuses to pretend it wrote.

The settings screen saves ONE group per request. Under the tabbed page that
request is the only feedback the group gets, so two things have to hold: a
key the handler does not write is refused by name, and the response says
which keys actually landed. Both run THROUGH the API here (B2
fix-bites-the-caller): unplug either branch in `api_put_settings` and
something in this file goes red.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.store import (  # noqa: E402
    SETTINGS_DERIVED_KEYS,
    SETTINGS_WRITABLE_KEYS,
    RunStore,
)

# One minimal VALID payload per writable key. The meta-test below walks this
# map, so a key added to `SETTINGS_WRITABLE_KEYS` without a handler branch
# (or without a sample here) fails instead of silently doing nothing.
VALID_SAMPLE: dict[str, object] = {
    "export_approved_only": True,
    "card_entities": {"2838": "Corporate Services"},
    "card_accounts": {"2838": "Chase 2838"},
    "entities": {"Corporate Services": {"org_id": "60021234567"}},
    "entity_order": ["Corporate Services"],
    "merchants": {"Uber": {"aliases": ["UBER *TRIP"]}},
    "cards": {"corp-2838": {"label": "Corporate Services", "digits": ["2838"]}},
    "cost_centers": {"Lidar": {"kind": "project"}},
    "intake": {"aliases": {"dirk": "Dirk Neumann"}},
    "receipt_requests": {
        "enabled": False,
        "holders": {"Dirk Neumann": "dirk.neumann@brisken.com"},
    },
    "private_cards": {"3281": {"person": "Dirk Neumann"}},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_RECON_RECEIPT_FIRST", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as c:
        yield c


def test_saving_one_group_names_that_group_and_nothing_else(client):
    r = client.put("/api/settings", json={"cards": VALID_SAMPLE["cards"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["applied"] == ["cards"]
    assert body["ignored"] == []
    # the other groups are untouched by a one-group save
    assert body["merchants"] == {}
    assert body["cost_centers"] == {}


def test_every_writable_key_actually_lands(client):
    """The tuple and the handler agree, key by key."""
    missing = sorted(set(SETTINGS_WRITABLE_KEYS) - set(VALID_SAMPLE))
    assert not missing, f"no sample payload for {missing}"
    for key in SETTINGS_WRITABLE_KEYS:
        r = client.put("/api/settings", json={key: VALID_SAMPLE[key]})
        assert r.status_code == 200, f"{key}: {r.text}"
        assert r.json()["applied"] == [key], key
    stored = client.get("/api/settings").json()
    assert stored["export_approved_only"] is True
    assert stored["cost_centers"]["Lidar"]["kind"] == "project"
    assert stored["intake"]["aliases"] == {"dirk": "Dirk Neumann"}


def test_a_retired_key_is_accepted_and_ignored_never_refused(client):
    """`fx_reference_rates` was retired on 2026-09-23. The published SPA
    keeps sending it on every FX-tab save until its removal prompt is
    applied, so refusing it would break that tab with a 400 over a key that
    no longer means anything. It is reported in `ignored`, like a derived
    key, and nothing is stored under it."""
    r = client.put("/api/settings", json={"fx_reference_rates": {"EUR:USD": "1.1"}})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] == []
    assert r.json()["ignored"] == ["fx_reference_rates"]
    assert "fx_reference_rates" not in client.get("/api/settings").json()


def test_the_typed_rates_are_deleted_from_the_stored_row_not_merely_hidden(
    tmp_path,
):
    """The estate really carried two typed rates (EUR:USD 1.162275,
    BRL:USD 0.192448). Dropping them from the GET would hide them while
    leaving them in the database, where a rollback of the read side would
    bring them straight back; the migration on open deletes them.

    `RunStore.get_settings` is the instrument because it reads the row as
    stored. The route's GET strips the key either way, so a test driven
    through the API reports success on an unwired migration, which is
    exactly what it did before this test existed."""
    db = tmp_path / "recon-web.sqlite"
    store = RunStore(db)
    try:
        store.conn.execute(
            "INSERT INTO settings (id, data, updated_at) VALUES (1, ?, ?)",
            (json.dumps({
                "fx_reference_rates": {
                    "EUR:USD": "1.162275", "BRL:USD": "0.192448",
                },
                "card_accounts": {"2838": "Chase 2838"},
            }), "2026-09-22T10:00:00+00:00"),
        )
        store.conn.commit()
    finally:
        store.close()

    store = RunStore(db)
    try:
        stored = store.get_settings()
        assert "fx_reference_rates" not in stored
        # Everything beside it survives: the migration drops keys, not rows.
        assert stored["card_accounts"] == {"2838": "Chase 2838"}
        raw = store.conn.execute(
            "SELECT data FROM settings WHERE id = 1"
        ).fetchone()["data"]
        assert "1.162275" not in raw
    finally:
        store.close()


def test_an_unknown_key_is_refused_by_name_and_writes_nothing(client):
    r = client.put("/api/settings", json={"cost_centres": {"Lidar": {}}})
    assert r.status_code == 400
    assert "cost_centres" in r.json()["error"]
    assert client.get("/api/settings").json()["cost_centers"] == {}


def test_a_good_key_beside_an_unknown_one_writes_nothing(client):
    """All or nothing: a typo next to a real group must not half-save."""
    r = client.put(
        "/api/settings",
        json={"merchants": VALID_SAMPLE["merchants"], "merchant": {}},
    )
    assert r.status_code == 400
    assert r.json()["error"].endswith("merchant")  # only the typo is named
    assert client.get("/api/settings").json()["merchants"] == {}


def test_the_whole_get_payload_can_be_sent_back(client):
    """Read, edit one group, send the object back: derived keys ride along
    and are reported as ignored rather than refused."""
    payload = client.get("/api/settings").json()
    for key in SETTINGS_DERIVED_KEYS:
        if key in ("applied", "ignored"):
            continue
        assert key in payload, f"{key} is not derived by GET any more"
    payload["merchants"] = VALID_SAMPLE["merchants"]
    r = client.put("/api/settings", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "merchants" in body["applied"]
    assert "categories" in body["ignored"]
    assert body["merchants"]["Uber"]["aliases"] == ["UBER *TRIP"]
    # ignored means ignored: the derived lists are served, never stored
    assert client.get("/api/settings").json()["cards"] == {}


def test_a_body_that_is_not_an_object_is_refused(client):
    r = client.put("/api/settings", json=["cards"])
    assert r.status_code == 400
    assert "object" in r.json()["error"]


def test_an_empty_body_applies_nothing(client):
    r = client.put("/api/settings", json={})
    assert r.status_code == 200, r.text
    assert r.json()["applied"] == []
