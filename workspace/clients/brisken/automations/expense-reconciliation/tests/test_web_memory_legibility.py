"""PR C — memory legibility on the workbench.

The view surfaces how many line items the cross-run memory auto-filled
(LEARNED), flags which rows carry them, and the /forget route lets the
reviewer retrain a wrong merchant in place. A reviewer reclassification
(override) removes a line from the learned count.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import build_view  # noqa: E402
from expense_recon.web.store import RunRow  # noqa: E402


def _learned_run() -> RunRow:
    li = LineItem(
        description="Uber ride",
        line_total=Decimal("22.30"),
        categorization=Categorization(
            category="Travel & Transport",
            zoho_account=None,
            confidence=1.0,
            source=ClassificationSource.LEARNED,
            reasoning="learned from your 2026-05 decision",
        ),
    )
    rec = Receipt("d1", "ent", date(2026, 6, 1), Decimal("22.30"), "USD", "Uber", line_items=(li,))
    tx = Transaction("t1", "ent", "card", date(2026, 6, 1), None, Decimal("22.30"), "USD", "USD", "UBER")
    outcome = MatchOutcome(matches=[Match("t1", "d1", MatchType.EXACT, 0.99, "x")])
    snapshot = snapshot_to_dict([tx], [rec], outcome, [])
    return RunRow(
        run_id="r1",
        created_at="2026-06-01",
        label="x",
        operator=None,
        summary={},
        snapshot=snapshot,
        config={},
        work_dir=".",
        llm_enabled=False,
        has_coa=False,
    )


def test_build_view_counts_and_flags_learned_lines():
    view = build_view(_learned_run(), {}, {})
    assert view["summary"]["n_learned_lines"] == 1
    row = view["rows"][0]
    assert row["has_learned"] is True
    line = row["candidates"][0]["receipt"]["line_items"][0]
    assert line["is_learned"] is True
    assert "learned from" in line["provenance"]


def test_reclassification_removes_line_from_learned_count():
    overrides = {("d1", 0): {"category": "Meals & Entertainment", "zoho_account": None}}
    view = build_view(_learned_run(), {}, overrides)
    assert view["summary"]["n_learned_lines"] == 0
    row = view["rows"][0]
    assert row["has_learned"] is False
    assert row["candidates"][0]["receipt"]["line_items"][0]["source"] == "EDITED"


def test_forget_route_ok_and_validation(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        ok = c.post("/api/runs/r1/forget", json={"legal_entity_id": "ent", "vendor": "Uber"})
        assert ok.status_code == 200
        assert ok.json()["ok"] is True
        # missing vendor -> bad request
        bad = c.post("/api/runs/r1/forget", json={"legal_entity_id": "ent"})
        assert bad.status_code == 400
