"""§16 export-approved gate: the settings store + the regenerate_zoho filter.

The gate ships advisory/OFF. With `export_approved_only` on, only reviewer-
CONFIRMED matches reach the Zoho journal; a still-pending auto-match is
withheld (but stays in the report / reconciled CSV). The policy is read
from the run's snapshotted `config["policy"]`, not the live setting, so a
run reproduces under the policy that was in effect when it ran.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from expense_recon.web.serialize import snapshot_to_dict
from expense_recon.web.service import regenerate_zoho
from expense_recon.web.store import Decision, RunRow, RunStore


# ── settings store ───────────────────────────────────────────────────


def test_settings_default_is_off(tmp_path):
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        assert store.get_settings() == {"export_approved_only": False}


def test_settings_roundtrip(tmp_path):
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        out = store.set_settings({"export_approved_only": True}, "2026-07-20T00:00:00")
        assert out["export_approved_only"] is True
        assert store.get_settings()["export_approved_only"] is True
        # A patch that omits the key leaves it intact (shallow merge).
        store.set_settings({"something_else": 1}, "2026-07-20T01:00:00")
        got = store.get_settings()
        assert got["export_approved_only"] is True
        assert got["something_else"] == 1


# ── regenerate_zoho gate ─────────────────────────────────────────────


def _line(desc, amount, category) -> LineItem:
    return LineItem(
        description=desc, line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.9,
            source=ClassificationSource.LINE, reasoning="t",
        ),
    )


def _tx(tid) -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id="amex-usd",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("180"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=f"VENDOR-{tid}",
    )


def _rec(doc) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Vendor",
        line_items=(_line("item", "180", "Equipment & Hardware"),),
    )


def _two_matched_run(work_dir, *, policy) -> RunRow:
    tx1, tx2 = _tx("t1"), _tx("t2")
    rec1, rec2 = _rec("r1"), _rec("r2")
    outcome = MatchOutcome(matches=[
        Match("t1", "r1", MatchType.EXACT, 0.99, "x", False),
        Match("t2", "r2", MatchType.EXACT, 0.99, "x", False),
    ])
    snapshot = snapshot_to_dict([tx1, tx2], [rec1, rec2], outcome, [])
    return RunRow(
        run_id="run1", created_at="2026-07-20T00:00:00", label="test",
        operator=None, summary={}, snapshot=snapshot,
        config={"policy": {"export_approved_only": policy}},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )


def test_gate_off_exports_all_matched(tmp_path):
    """Default (policy off): every matched charge exports, no decision
    needed — unchanged prior behaviour."""
    path = regenerate_zoho(_two_matched_run(tmp_path, policy=False), {}, {})
    body = path.read_text(encoding="utf-8")
    assert "t1" in body and "t2" in body


def test_gate_on_withholds_pending_exports_confirmed(tmp_path):
    """Policy on: only the CONFIRMED match exports; the pending one is
    withheld from the journal."""
    decisions = {
        "t1": Decision(status="confirmed", chosen_document_id=None,
                       updated_at="2026-07-20T00:00:00"),
    }
    path = regenerate_zoho(_two_matched_run(tmp_path, policy=True), decisions, {})
    body = path.read_text(encoding="utf-8")
    assert "t1" in body        # confirmed -> exported
    assert "t2" not in body    # pending -> withheld


def test_gate_on_with_nothing_confirmed_exports_nothing(tmp_path):
    path = regenerate_zoho(_two_matched_run(tmp_path, policy=True), {}, {})
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1  # header only, no data rows


def test_gate_reads_snapshotted_policy_not_live_settings(tmp_path):
    """Reproducibility: the run carries policy=on in its config; flipping a
    live setting elsewhere cannot change what THIS run exports (regenerate
    reads run.config, never the settings table)."""
    with RunStore(tmp_path / "recon-web.sqlite") as store:
        store.set_settings({"export_approved_only": False}, "2026-07-20T00:00:00")
    # The run was created under policy=on and keeps it, despite the live
    # setting now being off.
    path = regenerate_zoho(_two_matched_run(tmp_path, policy=True), {}, {})
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1  # still gated: nothing confirmed
