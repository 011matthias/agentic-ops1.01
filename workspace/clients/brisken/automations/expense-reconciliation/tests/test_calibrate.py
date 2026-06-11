"""Tests for the `expense-recon calibrate` subcommand (E8 / slice 3b)."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from expense_recon.calibrate import _metrics, main
from expense_recon.matching.types import Match, MatchOutcome, MatchType, Receipt, Transaction


def _tx(tid, amount, ccy="USD", account="card-a"):
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id=account,
        transaction_date=date(2026, 4, 1), posting_date=None,
        amount=Decimal(amount), transaction_currency=ccy,
        account_card_currency="USD", vendor_from_statement="V",
    )


def _rec(did, ccy="USD"):
    return Receipt(
        document_id=did, legal_entity_id="le1", detected_date=date(2026, 4, 1),
        detected_total=Decimal("10"), detected_currency=ccy, detected_vendor="V",
    )


def test_metrics_clean_run():
    txs = [_tx("t1", "10"), _tx("t2", "20")]
    recs = [_rec("r1"), _rec("r-brl", ccy="BRL")]
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "ok", False)],
        judgment_required=[Match("t2", "r-brl", MatchType.FX_JUDGMENT, 0.5, "fx", True)],
    )
    m = _metrics(outcome, txs, recs, "USD")
    assert m["invariant_ok"] is True
    assert m["double_bound_receipts"] == []
    assert m["matched"] == 1
    assert m["needs_review"] == 1
    assert m["foreign_receipts"] == 1
    assert m["fx_pairs"] == 1
    assert m["fx_multiplicity"] == 1.0
    assert m["by_card_spend"]["card-a"] == 30.0


def test_metrics_flags_double_binding():
    """A receipt bound to two transactions is the failure calibrate exists
    to catch — it must surface in double_bound_receipts (gate -> exit 1)."""
    txs = [_tx("t1", "10"), _tx("t2", "10")]
    recs = [_rec("r1")]
    outcome = MatchOutcome(
        matches=[
            Match("t1", "r1", MatchType.EXACT, 0.99, "ok", False),
            Match("t2", "r1", MatchType.EXACT, 0.99, "ok", False),  # same receipt
        ],
    )
    m = _metrics(outcome, txs, recs, "USD")
    assert m["double_bound_receipts"] == ["r1"]


def test_metrics_flags_fx_multiplicity_over_target():
    txs = [_tx("t1", "10"), _tx("t2", "10"), _tx("t3", "10")]
    recs = [_rec("r-brl", ccy="BRL")]  # 1 foreign receipt
    outcome = MatchOutcome(
        judgment_required=[
            Match("t1", "r-brl", MatchType.FX_JUDGMENT, 0.5, "fx", True),
            Match("t2", "r-brl", MatchType.FX_JUDGMENT, 0.5, "fx", True),
            Match("t3", "r-brl", MatchType.FX_JUDGMENT, 0.5, "fx", True),
        ],
        unmatched_transactions=[],
    )
    m = _metrics(outcome, txs, recs, "USD")
    assert m["fx_multiplicity"] == 3.0
    assert m["fx_multiplicity_ok"] is False


_STATEMENT = (
    "Date,Description,Amount\n"
    "04/01/2026,COFFEE,5.75\n"
    "04/03/2026,MYSTERY,42.00\n"
)
_RECEIPTS = (
    "document_id,detected_date,detected_total,detected_vendor,detected_currency\n"
    "r1,2026-04-01,5.75,Coffee,USD\n"
)


def _write_config(tmp_path: Path) -> Path:
    (tmp_path / "s.csv").write_text(_STATEMENT, encoding="utf-8")
    (tmp_path / "r.csv").write_text(_RECEIPTS, encoding="utf-8")
    cfg = {
        "statement": {
            "path": "s.csv", "account_id": "card-a",
            "legal_entity_id": "le1", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "r.csv", "source": "csv"},
    }
    p = tmp_path / "run.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def test_calibrate_main_clean_exits_zero(tmp_path, capsys):
    rc = main(["--config", str(_write_config(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CALIBRATION METRICS" in out
    assert "Reconciliation invariant: OK" in out


def test_calibrate_main_json(tmp_path, capsys):
    rc = main(["--config", str(_write_config(tmp_path)), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    data = json.loads(out)
    assert data["transactions"] == 2
    assert data["matched"] == 1
    assert data["invariant_ok"] is True


def test_calibrate_missing_config_exits_two(tmp_path, capsys):
    rc = main(["--config", str(tmp_path / "nope.json")])
    assert rc == 2
