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


# -- routes ---------------------------------------------------------------

def test_memory_page_empty(client):
    r = client.get("/memory")
    assert r.status_code == 200
    assert "Nothing learned yet" in r.text


def test_memory_page_lists_learned(client):
    _seed(client._data_root)
    r = client.get("/memory")
    assert r.status_code == 200
    assert "delancey tavern" in r.text
    assert "Meals" in r.text                 # category (& is html-escaped)
    assert "mega cente constr" in r.text     # alias statement side
    assert "hostaria" in r.text and "1.1000" in r.text  # fx mean


def test_forget_removes_the_merchant(client):
    _seed(client._data_root)
    r = client.post(
        "/memory/forget",
        data={"legal_entity_id": LE, "vendor": "delancey tavern"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.get_merchant_category(LE, normalize_vendor("Delancey Tavern")) is None
        # other merchants untouched
        assert s.get_merchant_fx(LE, normalize_vendor("Hostaria"))


def test_reset_clears_everything(client):
    _seed(client._data_root)
    r = client.post("/memory/reset", data={}, follow_redirects=False)
    assert r.status_code == 303
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.count_rows() == {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
        }
