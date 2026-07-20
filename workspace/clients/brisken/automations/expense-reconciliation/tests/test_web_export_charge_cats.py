"""Regression: the receiptless-charge categorization side-map (Slice 10)
must reach the WEB downloads.

Before this fix the web `regenerate_report/zoho/reconciled/writeback`
functions never passed `charge_categorizations` to their writers (only the
CLI did), so a web-downloaded reconciled CSV or Zoho journal silently
dropped the receiptless-charge categories the workbench displayed. Each
`regenerate_*` now rebuilds the side-map from the run snapshot (via
`service._charge_cats`) and threads it to its writer; the Zoho export also
honors the opt-in `zoho.export_receiptless_learned` config flag.
"""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    MatchOutcome,
    Transaction,
)
from expense_recon.web.serialize import categorization_to_dict, snapshot_to_dict
from expense_recon.web.service import regenerate_reconciled, regenerate_zoho
from expense_recon.web.store import RunRow

_ACCOUNT = "Other Infra and IT Costs for Cloud Business"


def _run(work_dir, *, config=None) -> RunRow:
    """A run with ONE receiptless charge (ANTHROPIC, no receipt) carrying a
    LEARNED categorization in the snapshot side-map."""
    tx = Transaction(
        transaction_id="t1", legal_entity_id="le1", account_id="amex-9001",
        transaction_date=date(2026, 4, 29), posting_date=None,
        amount=Decimal("10.32"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="ANTHROPIC",
    )
    snapshot = snapshot_to_dict(
        [tx], [], MatchOutcome(unmatched_transactions=["t1"]), []
    )
    snapshot["charge_categorizations"] = {
        "t1": categorization_to_dict(
            Categorization(
                category="Software & Subscriptions",
                zoho_account=_ACCOUNT,
                confidence=1.0,
                source=ClassificationSource.LEARNED,
                reasoning="from your Zoho Books posting history",
            )
        )
    }
    return RunRow(
        run_id="run1", created_at="2026-07-20T00:00:00", label="test",
        operator=None, summary={}, snapshot=snapshot, config=config or {},
        work_dir=str(work_dir), llm_enabled=False, has_coa=False,
    )


def test_reconciled_csv_carries_receiptless_charge_category(tmp_path):
    path = regenerate_reconciled(_run(tmp_path), {}, {})
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    row = next(r for r in rows if r["Description"] == "ANTHROPIC")
    assert row["Charge Category"] == "Software & Subscriptions"
    assert row["Charge Zoho Account"] == _ACCOUNT
    assert row["Charge Category Source"] == "LEARNED"


def test_zoho_journal_includes_receiptless_learned_only_when_flagged(tmp_path):
    # Default (flag off): the receiptless charge stays OUT of the journal,
    # preserving the prior web behaviour byte-for-byte.
    off_dir = tmp_path / "off"
    off_dir.mkdir()
    off = regenerate_zoho(_run(off_dir), {}, {}).read_text(encoding="utf-8")
    assert _ACCOUNT not in off

    # Flag on: the receiptless LEARNED charge becomes posting-eligible and
    # its learned account reaches the journal.
    on_dir = tmp_path / "on"
    on_dir.mkdir()
    on = regenerate_zoho(
        _run(on_dir, config={"zoho": {"export_receiptless_learned": True}}),
        {}, {},
    ).read_text(encoding="utf-8")
    assert _ACCOUNT in on
