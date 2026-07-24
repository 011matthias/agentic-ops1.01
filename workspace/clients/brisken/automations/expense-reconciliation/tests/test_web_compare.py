"""PR G — compare two runs in the browser (mirror of the CLI `diff`).

Covers the framework-free compare_runs (count deltas + per-charge bucket
changes, unioned ids) and the /compare page (picker renders; two runs
render the deltas).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from expense_recon.matching.types import (  # noqa: E402
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.app import create_app  # noqa: E402
from expense_recon.web.serialize import snapshot_to_dict  # noqa: E402
from expense_recon.web.service import compare_runs  # noqa: E402
from expense_recon.web.store import RunRow  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _run(run_id: str, summary: dict, snapshot: dict) -> RunRow:
    return RunRow(
        run_id=run_id,
        created_at="2026-06-01",
        label=run_id,
        operator=None,
        summary=summary,
        snapshot=snapshot,
        config={},
        work_dir=".",
        llm_enabled=False,
        has_coa=False,
    )


def _snap(matched_tx: list[str], unmatched_tx: list[str]) -> dict:
    txs = [
        Transaction(t, "ent", "card", date(2026, 5, 1), None, Decimal("10"), "USD", "USD", t)
        for t in matched_tx + unmatched_tx
    ]
    recs = [Receipt(f"d-{t}", "ent", date(2026, 5, 1), Decimal("10"), "USD", t) for t in matched_tx]
    outcome = MatchOutcome(
        matches=[Match(t, f"d-{t}", MatchType.EXACT, 0.99, "x") for t in matched_tx],
        unmatched_transactions=list(unmatched_tx),
    )
    return snapshot_to_dict(txs, recs, outcome, [])


def test_compare_runs_counts_and_bucket_changes():
    # Run A: t1 matched, t2 unmatched. Run B: both matched (t2 fixed).
    a = _run("A", {"n_transactions": 2, "n_matched": 1, "n_unmatched_tx": 1, "match_rate": 50.0}, _snap(["t1"], ["t2"]))
    b = _run("B", {"n_transactions": 2, "n_matched": 2, "n_unmatched_tx": 0, "match_rate": 100.0}, _snap(["t1", "t2"], []))

    cmp = compare_runs(a, b)
    matched_delta = next(d for d in cmp["deltas"] if d["label"] == "Matched")
    assert matched_delta == {"label": "Matched", "a": 1, "b": 2, "delta": 1}
    assert cmp["rate"]["delta"] == 50.0
    # only t2 changed bucket: unmatched -> matched
    assert cmp["n_changed"] == 1
    assert cmp["changes"][0] == {"transaction_id": "t2", "from": "unmatched", "to": "matched"}


def test_compare_runs_absent_charge_marked():
    # Different months: B has a charge A never had.
    a = _run("A", {"n_transactions": 1, "n_matched": 1}, _snap(["t1"], []))
    b = _run("B", {"n_transactions": 1, "n_matched": 1}, _snap(["zz"], []))
    cmp = compare_runs(a, b)
    changes = {c["transaction_id"]: (c["from"], c["to"]) for c in cmp["changes"]}
    assert changes["t1"] == ("matched", "(absent)")
    assert changes["zz"] == ("(absent)", "matched")


def _api_run(c, files, data) -> str:
    resp = c.post("/api/runs", files=files, data=data)
    assert resp.status_code == 200, resp.text
    job = c.get(f"/jobs/{resp.json()['job_id']}").json()
    assert job["status"] == "done", job
    return job["run_id"]


def test_api_compare_returns_server_computed_diff(tmp_path):
    """The SPA compare endpoint returns the diff computed by compare_runs, so
    the front end never derives it."""
    app = create_app(tmp_path)
    with TestClient(app) as c:
        files = {
            "statement": ("statement.example.csv", (EXAMPLES / "statement.example.csv").read_bytes(), "text/csv"),
            "receipts": ("receipts.example.csv", (EXAMPLES / "receipts.example.csv").read_bytes(), "text/csv"),
        }
        data = {"account_id": "amex-9001", "legal_entity_id": "brisken-llc", "receipts_source": "csv"}
        r1 = _api_run(c, files, data)
        r2 = _api_run(c, files, data)

        # No selection yet: the run list is present, comparison is null.
        empty = c.get("/api/compare").json()
        assert {"runs", "a", "b", "comparison"} <= empty.keys()
        assert empty["comparison"] is None
        assert len(empty["runs"]) == 2
        assert {"run_id", "label", "created_at"} <= empty["runs"][0].keys()

        # Both selected: the server-computed diff comes back whole.
        body = c.get(f"/api/compare?a={r1}&b={r2}").json()
        cmp = body["comparison"]
        assert cmp is not None
        assert {"deltas", "rate", "n_changed", "changes"} <= cmp.keys()
        # identical re-runs of the same data -> nothing changed bucket
        assert cmp["n_changed"] == 0
        assert any(d["label"] == "Matched" for d in cmp["deltas"])
