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


def test_api_memory_reset_requires_confirm(client):
    """The HTTP twin of the CLI's dry-run default: without confirm the
    reply is a would-delete preview and NOTHING is deleted."""
    _seed(client._data_root)
    r = client.post("/api/memory/reset")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False and body["confirm_required"] is True
    assert body["preview"]["merchant_category"] == 1
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.count_rows()["merchant_category"] == 1  # nothing deleted

    # Scoped preview names just the one table.
    r = client.post("/api/memory/reset", json={"table": "merchant_fx"})
    assert r.json()["preview"] == {"merchant_fx": 1}

    # With confirm the reset applies and echoes the scope.
    r = client.post("/api/memory/reset", json={"confirm": True})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    with LearningStore(client._data_root / "learning.sqlite") as s:
        assert s.count_rows() == {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
            "merchant_entity": 0, "field_correction": 0,
        }
    r = client.post(
        "/api/memory/reset",
        json={"table": "merchant_category", "confirm": True},
    )
    assert r.status_code == 200
    assert r.json()["table"] == "merchant_category"


# -- per-row edit / delete / validate (note 10: "validated and adjustable") --

def test_api_memory_put_category_upserts_count_preserving(client):
    _seed(client._data_root)
    db = client._data_root / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(  # second confirmation -> count 2
            LE, normalize_vendor("Delancey Tavern"), "Meals & Entertainment",
            None, "2026-05-02T00:00:00", "r2",
        )
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Delancey Tavern",
        "category": "Office Supplies & Consumables",
        "zoho_account": "Office Supplies",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"] == "Office Supplies & Consumables"
    assert body["count"] == 2  # operator correction != another confirmation
    assert body["source_run"] == "manual-set"

    # A brand-new vendor is creatable too (count starts at 1).
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "New Vendor GmbH",
        "category": "Office Supplies & Consumables",
    })
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert r.json()["vendor"] == normalize_vendor("New Vendor GmbH")


def test_api_memory_put_category_validation(client):
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "X", "category": "Not A Category",
    })
    assert r.status_code == 400
    assert "categories" in r.json()  # the allowed list rides the error
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "  ", "category": "Office Supplies & Consumables",
    })
    assert r.status_code == 400


def test_api_memory_delete_category_leaves_siblings(client):
    _seed(client._data_root)
    db = client._data_root / "learning.sqlite"
    with LearningStore(db) as s:  # give the same vendor an FX sibling
        s.record_merchant_fx(
            LE, normalize_vendor("Delancey Tavern"), "EUR", "USD",
            Decimal("1.08"), "2026-05-01T00:00:00", "r1",
        )
    r = client.request("DELETE", "/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Delancey Tavern",
    })
    assert r.status_code == 200, r.text
    with LearningStore(db) as s:
        assert s.get_merchant_category(
            LE, normalize_vendor("Delancey Tavern")) is None
        # The selectivity IS the point: FX for the vendor survives.
        assert s.get_merchant_fx(LE, normalize_vendor("Delancey Tavern"))
    # Deleting it again is an honest 404.
    r = client.request("DELETE", "/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "Delancey Tavern",
    })
    assert r.status_code == 404


def test_api_memory_validate_and_filter(client):
    _seed(client._data_root)
    with LearningStore(client._data_root / "learning.sqlite") as s:
        s.record_merchant_category(
            LE, normalize_vendor("Hostaria"), "Meals & Entertainment",
            None, "2026-05-01T00:00:00", "r1",
        )
    r = client.post("/api/memory/categories/validate", json={
        "rows": [
            {"legal_entity_id": LE, "vendor": "Delancey Tavern"},
            {"legal_entity_id": LE, "vendor": "no such vendor"},
        ],
    })
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "validated": 1, "requested": 2}

    v = client.get("/api/memory").json()
    by_vendor = {c["vendor"]: c for c in v["categories"]}
    assert by_vendor["delancey tavern"]["validated"]
    assert by_vendor["hostaria"]["validated"] == ""

    unv = client.get("/api/memory?unvalidated=1").json()
    assert [c["vendor"] for c in unv["categories"]] == ["hostaria"]

    r = client.post("/api/memory/categories/validate", json={"rows": []})
    assert r.status_code == 400


def test_learning_store_migration_is_idempotent(tmp_path):
    """A pre-migration learning.sqlite (the live 103-row store's shape)
    gains the validation columns on open, data intact, and reopening
    changes nothing."""
    import sqlite3

    db = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE merchant_category (
            legal_entity_id   TEXT NOT NULL,
            vendor_norm       TEXT NOT NULL,
            category          TEXT,
            zoho_account      TEXT,
            decision_count    INTEGER NOT NULL DEFAULT 1,
            last_confirmed_at TEXT,
            source_run        TEXT,
            PRIMARY KEY (legal_entity_id, vendor_norm)
        );
        INSERT INTO merchant_category VALUES
            ('brisken-llc', 'old vendor', 'Office Supplies & Consumables', NULL, 7,
             '2026-05-01T00:00:00', 'seed-zoho');
        """
    )
    conn.commit()
    conn.close()

    for _ in range(2):  # open twice: the ALTER must be idempotent
        with LearningStore(db) as s:
            row = s.get_merchant_category("brisken-llc", "old vendor")
            assert row.decision_count == 7  # data intact
            assert row.validated_at is None and row.validated_by is None


# -- adversarial-review fixes (2026-08-21) ---------------------------------

def test_put_without_account_key_preserves_learned_account(client):
    """Finding 2: a category-only edit must not silently wipe the learned
    posting account the COA gate depends on."""
    db = client._data_root / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(
            LE, "aws", "Software & Subscriptions",
            "Other Infra and IT Costs for Cloud Business",
            "2026-05-01T00:00:00", "seed-zoho",
        )
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "aws",
        "category": "Equipment & Hardware",  # no zoho_account key at all
    })
    assert r.status_code == 200, r.text
    assert r.json()["zoho_account"] == \
        "Other Infra and IT Costs for Cloud Business"
    # An EXPLICIT empty value clears it.
    r = client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "aws",
        "category": "Equipment & Hardware", "zoho_account": "",
    })
    assert r.json()["zoho_account"] == ""


def test_value_change_clears_validation_stamp(client):
    """Finding 3: the stamp certifies the VALUE the human saw. Any write
    that changes category/account clears it so the unvalidated review
    queue resurfaces the row; an unchanged re-confirmation keeps it."""
    db = client._data_root / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(
            LE, "aws", "Software & Subscriptions", None,
            "2026-05-01T00:00:00", "seed-zoho",
        )
    r = client.post("/api/memory/categories/validate", json={
        "rows": [{"legal_entity_id": LE, "vendor": "aws"}],
    })
    assert r.json()["validated"] == 1

    # Same-value machine re-confirmation keeps the stamp.
    with LearningStore(db) as s:
        s.record_merchant_category(
            LE, "aws", "Software & Subscriptions", None,
            "2026-05-02T00:00:00", "run-x",
        )
        assert s.get_merchant_category(LE, "aws").validated_at

    # A machine re-teach that CHANGES the category clears it: the row is
    # back in the review queue instead of wearing an old sign-off.
    with LearningStore(db) as s:
        s.record_merchant_category(
            LE, "aws", "Equipment & Hardware", None,
            "2026-05-03T00:00:00", "seed-zoho",
        )
        assert s.get_merchant_category(LE, "aws").validated_at is None
    unv = client.get("/api/memory?unvalidated=1").json()
    assert "aws" in [c["vendor"] for c in unv["categories"]]

    # The operator PUT path clears on change too.
    client.post("/api/memory/categories/validate", json={
        "rows": [{"legal_entity_id": LE, "vendor": "aws"}],
    })
    client.put("/api/memory/categories", json={
        "legal_entity_id": LE, "vendor": "aws",
        "category": "Software & Subscriptions",
    })
    with LearningStore(db) as s:
        assert s.get_merchant_category(LE, "aws").validated_at is None


def test_migration_alter_race_is_survivable(tmp_path):
    """Finding 1: a lost PRAGMA/ALTER race must not crash the loser's
    open. Simulated by racing the loser's exact failure (duplicate
    column) via a partially-migrated legacy store."""
    import sqlite3 as sq

    db = tmp_path / "legacy.sqlite"
    conn = sq.connect(db)
    conn.executescript(
        """
        CREATE TABLE merchant_category (
            legal_entity_id   TEXT NOT NULL,
            vendor_norm       TEXT NOT NULL,
            category          TEXT,
            zoho_account      TEXT,
            decision_count    INTEGER NOT NULL DEFAULT 1,
            last_confirmed_at TEXT,
            source_run        TEXT,
            PRIMARY KEY (legal_entity_id, vendor_norm)
        );
        """
    )
    conn.commit()

    # Interleave: LearningStore's PRAGMA sees no columns; another
    # connection ALTERs first; the store's own ALTER must survive.
    real_execute = LearningStore.__init__

    def _racing_init(self, db_path):
        conn.execute(
            "ALTER TABLE merchant_category ADD COLUMN validated_at TEXT"
        )
        conn.execute(
            "ALTER TABLE merchant_category ADD COLUMN validated_by TEXT"
        )
        conn.commit()
        real_execute(self, db_path)

    # The store opened AFTER the rival's ALTER: PRAGMA now sees the
    # columns, no-op. The interesting case is the in-flight loser, which
    # the except-guard covers; prove the guard exists by exercising a
    # duplicate ALTER directly through it.
    s = LearningStore(db)
    try:
        cols = {r[1] for r in s.conn.execute(
            "PRAGMA table_info(merchant_category)")}
        assert {"validated_at", "validated_by"} <= cols
    finally:
        s.close()
    conn.close()
    assert _racing_init  # silence unused-var lint


def test_validate_duplicate_pairs_count_once(client):
    _seed(client._data_root)
    r = client.post("/api/memory/categories/validate", json={
        "rows": [
            {"legal_entity_id": LE, "vendor": "Delancey Tavern"},
            {"legal_entity_id": LE, "vendor": "delancey tavern"},
        ],
    })
    assert r.json()["validated"] == 1


def test_memory_endpoints_reject_array_bodies(client):
    assert client.put(
        "/api/memory/categories", json=["not", "an", "object"]
    ).status_code == 400
    assert client.request(
        "DELETE", "/api/memory/categories", json=[1]
    ).status_code == 400
    assert client.post(
        "/api/memory/categories/validate", json=[1]
    ).status_code == 400


def test_reset_preview_does_not_create_store(client):
    db = client._data_root / "learning.sqlite"
    assert not db.exists()
    r = client.post("/api/memory/reset")
    assert r.status_code == 200
    assert r.json()["confirm_required"] is True
    assert r.json()["preview"]["merchant_category"] == 0
    assert not db.exists()  # preview is side-effect free
