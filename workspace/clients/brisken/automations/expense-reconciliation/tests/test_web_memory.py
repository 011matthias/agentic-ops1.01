"""The in-browser memory view (PR 2e): list learned data, forget one
merchant, reset all — the escape hatch where Chris actually works."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.learning import LearningStore, normalize_vendor  # noqa: E402
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.service import build_memory_view  # noqa: E402

LE = "brisken-llc"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(data_root: Path):
    with LearningStore(data_root / "learning.sqlite") as s:
        s.record_merchant_category(
            LE, normalize_vendor("Delancey Tavern"), "Meals & Entertainment",
            None, "2026-05-01T00:00:00", "r1",
        )
        s.record_vendor_alias(
            LE, normalize_vendor("MEGA CENTE CONSTR"), normalize_vendor("Mega Center"),
            "2026-05-01T00:00:00", "r1",
        )
        s.record_merchant_fx(
            LE, normalize_vendor("Hostaria"), "EUR", "USD", Decimal("1.10"),
            "2026-05-01T00:00:00", "r1",
        )


# -- service --------------------------------------------------------------

def test_build_memory_view_empty(tmp_path):
    v = build_memory_view(tmp_path / "none.sqlite")
    assert v["total"] == 0
    assert v["categories"] == [] and v["aliases"] == [] and v["fx"] == []


def test_build_memory_view_seeded(tmp_path):
    _seed(tmp_path)
    v = build_memory_view(tmp_path / "learning.sqlite")
    assert v["total"] == 3
    assert v["categories"][0]["category"] == "Meals & Entertainment"
    assert v["fx"][0]["mean"] == "1.1000"


# -- SPA JSON API (the memory screen the Lovable front end renders) --------

def test_api_memory_empty(client):
    r = client.get("/api/memory")
    assert r.status_code == 200
    v = r.json()
    assert v["total"] == 0
    assert v["categories"] == [] and v["aliases"] == [] and v["fx"] == []


def test_api_memory_lists_learned(client):
    _seed(client._data_root)
    r = client.get("/api/memory")
    assert r.status_code == 200
    v = r.json()
    assert v["total"] == 3
    assert v["categories"][0]["category"] == "Meals & Entertainment"
    assert v["aliases"][0]["stmt"] == "mega cente constr"
    assert v["fx"][0]["mean"] == "1.1000"


def test_api_memory_forget_removes_the_merchant(client):
    _seed(client._data_root)
    r = client.post(
        "/api/memory/forget",
        json={"legal_entity_id": LE, "vendor": "delancey tavern"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["forgotten"]["merchant_category"] == 1
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.get_merchant_category(LE, normalize_vendor("Delancey Tavern")) is None
        # other merchants untouched
        assert s.get_merchant_fx(LE, normalize_vendor("Hostaria"))


def test_api_memory_forget_bad_request(client):
    r = client.post("/api/memory/forget", json={"legal_entity_id": LE})
    assert r.status_code == 400
    assert r.json()["error"]


def test_api_memory_reset_clears_everything(client):
    _seed(client._data_root)
    # An empty body is accepted (reset everything)...
    r = client.post("/api/memory/reset")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.count_rows() == {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
            "merchant_entity": 0, "field_correction": 0,
        }
    # ...and a scoped body echoes the scope back.
    r = client.post("/api/memory/reset", json={"table": "merchant_category"})
    assert r.status_code == 200
    assert r.json()["table"] == "merchant_category"
