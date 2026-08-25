"""Slice 10 on the web workbench: the receiptless-charge side-map rides
in the snapshot under its own key, and build_view puts the suggestion on
the no-receipt rows (None on matched rows and pre-Slice-10 snapshots)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

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
from expense_recon.web.serialize import (  # noqa: E402
    categorization_to_dict,
    snapshot_to_dict,
)
from expense_recon.web.service import build_view  # noqa: E402
from expense_recon.web.store import RunRow, RunStore  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as c:
        c._data_root = tmp_path
        yield c


def _create_run(client) -> str:
    resp = client.post(
        "/api/runs",
        files={
            "statement": (
                "statement.example.csv",
                (EXAMPLES / "statement.example.csv").read_bytes(),
                "text/csv",
            ),
            "receipts": (
                "receipts.example.csv",
                (EXAMPLES / "receipts.example.csv").read_bytes(),
                "text/csv",
            ),
        },
        data={"account_id": "amex-9001", "account_card_currency": "USD"},
    )
    assert resp.status_code == 200, resp.text
    job = client.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def test_snapshot_carries_charge_categorizations_for_unmatched(client):
    run_id = _create_run(client)
    with RunStore(client._data_root / "recon-web.sqlite") as store:
        run = store.get_run(run_id)
    unmatched = run.snapshot["outcome"]["unmatched_transactions"]
    assert unmatched, "example fixtures should leave at least one charge"
    cats = run.snapshot.get("charge_categorizations")
    assert cats is not None
    assert set(cats) == set(unmatched)
    for d in cats.values():
        assert {"category", "zoho_account", "confidence", "source"} <= set(d)


def _tx(tid, vendor):
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="amex-9001",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("20.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
    )


def _run_row(snapshot) -> RunRow:
    return RunRow(
        run_id="run1", created_at="2026-07-20T00:00:00", label="test",
        operator=None, summary={}, snapshot=snapshot, config={},
        work_dir="", llm_enabled=False, has_coa=False,
    )


def test_build_view_surfaces_suggestion_on_noreceipt_row():
    tx = _tx("t1", "ANTHROPIC")
    snapshot = snapshot_to_dict(
        [tx], [], MatchOutcome(unmatched_transactions=["t1"]), []
    )
    snapshot["charge_categorizations"] = {
        "t1": categorization_to_dict(
            Categorization(
                category="Software & Subscriptions",
                zoho_account="Other Infra and IT Costs for Cloud Business",
                confidence=1.0, source=ClassificationSource.LEARNED,
                reasoning="from your Zoho Books posting history",
            )
        )
    }
    view = build_view(_run_row(snapshot), {}, {})
    row = next(r for r in view["rows"] if r["transaction_id"] == "t1")
    assert row["section"] == "noreceipt"
    cc = row["charge_category"]
    assert cc is not None
    assert cc["category"] == "Software & Subscriptions"
    assert cc["zoho_account"] == "Other Infra and IT Costs for Cloud Business"
    assert cc["source"] == "LEARNED"
    assert cc["is_learned"] is True
    assert "Zoho Books posting history" in cc["provenance"]


def test_build_view_pre_slice10_snapshot_renders_none():
    tx = _tx("t1", "MYSTERY LLC")
    snapshot = snapshot_to_dict(
        [tx], [], MatchOutcome(unmatched_transactions=["t1"]), []
    )
    view = build_view(_run_row(snapshot), {}, {})
    row = next(r for r in view["rows"] if r["transaction_id"] == "t1")
    assert row["charge_category"] is None


def test_render_model_serves_no_suggestion_rows(client):
    """The no-receipt STAPLES charge in the example fixtures has no
    keyword hit (REVIEW, no category) — the render model must serve its
    plain no-receipt row with a null charge_category, and stay 200."""
    run_id = _create_run(client)
    resp = client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    assert any(r["charge_category"] is None for r in resp.json()["rows"])


# ── posting_category: category + account resolved onto EVERY row ──────


def _matched_snapshot(cat):
    """One charge auto-matched to one receipt whose single line carries
    `cat` (None => an uncategorized receipt, e.g. a folder upload)."""
    tx = _tx("t1", "ADOBE")
    rec = Receipt(
        document_id="r1",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 7),
        detected_total=Decimal("20.00"),
        detected_currency="USD",
        detected_vendor="Adobe",
        line_items=(
            LineItem(
                description="Creative Cloud",
                line_total=Decimal("20.00"),
                categorization=cat,
            ),
        ),
    )
    outcome = MatchOutcome(
        matches=[
            Match(
                transaction_id="t1",
                document_id="r1",
                match_type=MatchType.EXACT,
                confidence=1.0,
                reason="exact",
            )
        ]
    )
    return snapshot_to_dict([tx], [rec], outcome, [])


def _row(view):
    return next(r for r in view["rows"] if r["transaction_id"] == "t1")


def test_posting_category_resolved_on_a_matched_row():
    cat = Categorization(
        category="Software & Subscriptions",
        zoho_account="Cloud Services Payable",
        confidence=1.0,
        source=ClassificationSource.LINE,
    )
    view = build_view(_run_row(_matched_snapshot(cat)), {}, {})
    pc = _row(view)["posting_category"]
    assert pc is not None
    assert pc["category"] == "Software & Subscriptions"
    assert pc["zoho_account"] == "Cloud Services Payable"
    assert pc["source"] == "LINE"


def test_posting_category_reviewer_override_wins():
    cat = Categorization(
        category="Software & Subscriptions",
        zoho_account="Cloud Services Payable",
        confidence=1.0,
        source=ClassificationSource.LINE,
    )
    overrides = {("r1", 0): {"category": "Travel", "zoho_account": "Travel Payable"}}
    view = build_view(_run_row(_matched_snapshot(cat)), {}, overrides)
    pc = _row(view)["posting_category"]
    assert pc["category"] == "Travel"
    assert pc["zoho_account"] == "Travel Payable"
    assert pc["source"] == "EDITED"


def test_posting_category_none_for_uncategorized_matched_receipt():
    # A folder-uploaded receipt is matched but never categorized -> no
    # posting category (the UI shows a plain "assign", not a wrong guess).
    view = build_view(_run_row(_matched_snapshot(None)), {}, {})
    assert _row(view)["posting_category"] is None


def test_posting_category_falls_back_to_receiptless_charge_category():
    tx = _tx("t1", "ANTHROPIC")
    snapshot = snapshot_to_dict(
        [tx], [], MatchOutcome(unmatched_transactions=["t1"]), []
    )
    snapshot["charge_categorizations"] = {
        "t1": categorization_to_dict(
            Categorization(
                category="Software & Subscriptions",
                zoho_account="Cloud Services Payable",
                confidence=1.0,
                source=ClassificationSource.LEARNED,
            )
        )
    }
    pc = _row(build_view(_run_row(snapshot), {}, {}))["posting_category"]
    assert pc is not None
    assert pc["category"] == "Software & Subscriptions"
    assert pc["zoho_account"] == "Cloud Services Payable"


def test_posting_category_present_on_every_api_row(client):
    run_id = _create_run(client)
    rows = client.get(f"/api/runs/{run_id}").json()["rows"]
    assert rows and all("posting_category" in r for r in rows)
