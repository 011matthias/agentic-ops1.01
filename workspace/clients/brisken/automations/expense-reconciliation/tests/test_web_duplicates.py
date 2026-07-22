"""§18 duplicate surfacing + resolve.

`build_view` exposes the duplicate groups with a stable `group_id` and the
reviewer's advisory resolution; the resolve endpoint records `ignore` /
`confirmed`. Advisory only: a resolution never changes a bucket, never
deletes, never touches the reconciliation invariant.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.duplicates import duplicate_group_id  # noqa: E402
from expense_recon.matching.types import (  # noqa: E402
    MatchOutcome,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import build_view  # noqa: E402
from expense_recon.web.store import RunRow, RunStore  # noqa: E402


def _dup_tx(tid, day) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, day), posting_date=None,
        amount=Decimal("180"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )


def _dup_snapshot() -> dict:
    # Two same-merchant / same-amount charges one day apart -> one duplicate
    # charge group (find_duplicate_charges clusters within 3 days).
    t1, t2 = _dup_tx("t1", 7), _dup_tx("t2", 8)
    outcome = MatchOutcome(unmatched_transactions=["t1", "t2"])
    return snapshot_to_dict([t1, t2], [], outcome, [])


_GROUP_ID = duplicate_group_id("charge", ["t1", "t2"])


def _run(work_dir) -> RunRow:
    return RunRow(
        run_id="run1", created_at="2026-07-21T00:00:00", label="test",
        operator=None, summary={}, snapshot=_dup_snapshot(), config={},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )


# ── build_view ───────────────────────────────────────────────────────


def test_build_view_surfaces_unresolved_group(tmp_path):
    view = build_view(_run(tmp_path), {}, {})
    groups = view["duplicate_groups"]
    grp = next(g for g in groups if g["kind"] == "charge")
    assert grp["group_id"] == _GROUP_ID
    assert sorted(grp["members"]) == ["t1", "t2"]
    assert grp["resolution"] is None
    # The legacy list-of-lists view is preserved for the Jinja workbench.
    assert view["duplicate_charges"]


def test_build_view_attaches_resolution(tmp_path):
    view = build_view(_run(tmp_path), {}, {}, {_GROUP_ID: "ignore"})
    grp = next(g for g in view["duplicate_groups"] if g["kind"] == "charge")
    assert grp["resolution"] == "ignore"


# ── endpoint ─────────────────────────────────────────────────────────


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _seed(client) -> str:
    db = RunStore(client._data_root / "recon-web.sqlite")
    db.create_run(
        run_id="run1", created_at="2026-07-21T00:00:00", label="test",
        operator=None, summary={}, snapshot=_dup_snapshot(), config={},
        work_dir=str(client._data_root), llm_enabled=False, has_coa=False,
    )
    db.close()
    return "run1"


def test_resolve_endpoint_records_resolution(client):
    run_id = _seed(client)
    # Unresolved to start.
    view = client.get(f"/api/runs/{run_id}").json()
    grp = next(g for g in view["duplicate_groups"] if g["kind"] == "charge")
    assert grp["resolution"] is None

    r = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": grp["group_id"], "resolution": "ignore"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    view2 = client.get(f"/api/runs/{run_id}").json()
    grp2 = next(g for g in view2["duplicate_groups"] if g["kind"] == "charge")
    assert grp2["resolution"] == "ignore"


def test_resolve_accepts_action_alias(client):
    run_id = _seed(client)
    r = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": _GROUP_ID, "action": "confirmed"},
    )
    assert r.status_code == 200, r.text
    view = client.get(f"/api/runs/{run_id}").json()
    grp = next(g for g in view["duplicate_groups"] if g["kind"] == "charge")
    assert grp["resolution"] == "confirmed"


def test_resolve_rejects_invalid_resolution(client):
    run_id = _seed(client)
    r = client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": _GROUP_ID, "resolution": "delete-it"},
    )
    assert r.status_code == 400


def test_resolve_is_advisory_only(client):
    """Resolving a duplicate group must not change any bucket or the
    reconciliation invariant."""
    run_id = _seed(client)
    before = client.get(f"/api/runs/{run_id}").json()["summary"]
    client.post(
        f"/api/runs/{run_id}/duplicates/resolve",
        json={"group_id": _GROUP_ID, "resolution": "confirmed"},
    )
    after = client.get(f"/api/runs/{run_id}").json()["summary"]
    assert before["invariant_ok"] == after["invariant_ok"]
    assert before["n_reconciled"] == after["n_reconciled"]
    assert before["n_unmatched_tx"] == after["n_unmatched_tx"]
