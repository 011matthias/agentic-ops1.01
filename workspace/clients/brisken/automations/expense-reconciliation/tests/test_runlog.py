"""Slice 5b — run-log persistence + history/diff. All offline."""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.matching.types import Match, MatchOutcome, MatchType
from expense_recon.runlog import RunLog, TxDecision, decisions_from_outcome


def _outcome() -> MatchOutcome:
    o = MatchOutcome()
    o.matches.append(Match("t1", "r1", MatchType.EXACT, 1.0, "exact"))
    o.matches.append(Match("t2", "r2", MatchType.PROBABLE, 0.8, "tolerance", requires_review=True))
    o.judgment_required.append(Match("t3", "r3", MatchType.FX_JUDGMENT, 0.5, "fx", requires_review=True))
    o.ambiguous.append(Match("t4", "r4", MatchType.AMBIGUOUS, 0.4, "tie", requires_review=True))
    o.ambiguous.append(Match("t4", "r5", MatchType.AMBIGUOUS, 0.4, "tie", requires_review=True))
    o.unmatched_transactions.append("t5")
    o.unmatched_receipts.append("r9")
    return o


def _summary() -> dict:
    return {
        "config_path": "run.json",
        "statement_path": "stmt.csv",
        "account_id": "amex-9001",
        "legal_entity_id": "brisken-llc",
        "report_path": "report.xlsx",
        "n_transactions": 5,
        "n_receipts": 6,
        "n_matched": 2,
        "n_review": 2,
        "n_unmatched": 1,
        "n_parse_errors": 0,
        "llm_calls": 3,
        "llm_cost_usd": Decimal("0.0042"),
    }


def test_decisions_from_outcome_covers_every_transaction():
    decisions = decisions_from_outcome(_outcome())
    tx_ids = {d.transaction_id for d in decisions}
    # t4 appears twice in ambiguous but is recorded once; every tx present
    assert tx_ids == {"t1", "t2", "t3", "t4", "t5"}
    by_id = {d.transaction_id: d for d in decisions}
    assert by_id["t1"].match_type == "exact"
    assert by_id["t5"].match_type == "unmatched"
    assert by_id["t5"].requires_review is True


def test_record_and_list_roundtrip(tmp_path):
    db = tmp_path / "h.sqlite"
    with RunLog(db) as rl:
        rl.record_run(
            run_id="aaaa1111", created_at="2026-06-10T10:00:00+00:00",
            summary=_summary(), decisions=decisions_from_outcome(_outcome()),
            operator="chris",
        )
    with RunLog(db) as rl:
        runs = rl.list_runs()
        assert len(runs) == 1
        s = runs[0]
        assert s.run_id == "aaaa1111"
        assert s.operator == "chris"
        assert s.account_id == "amex-9001"
        assert s.llm_cost_usd == Decimal("0.0042")
        assert s.n_matched == 2
        decisions = rl.get_decisions("aaaa1111")
        assert len(decisions) == 5


def test_get_run_by_unique_prefix(tmp_path):
    db = tmp_path / "h.sqlite"
    with RunLog(db) as rl:
        rl.record_run(run_id="abcd0001", created_at="2026-06-10T10:00:00+00:00",
                      summary=_summary(), decisions=[])
        rl.record_run(run_id="ef990002", created_at="2026-06-10T11:00:00+00:00",
                      summary=_summary(), decisions=[])
        assert rl.get_run("abcd").run_id == "abcd0001"
        assert rl.get_run("zzzz") is None


def test_get_run_ambiguous_prefix_returns_none(tmp_path):
    db = tmp_path / "h.sqlite"
    with RunLog(db) as rl:
        rl.record_run(run_id="ab110001", created_at="2026-06-10T10:00:00+00:00",
                      summary=_summary(), decisions=[])
        rl.record_run(run_id="ab220002", created_at="2026-06-10T11:00:00+00:00",
                      summary=_summary(), decisions=[])
        assert rl.get_run("ab") is None  # ambiguous


def test_list_runs_newest_first(tmp_path):
    db = tmp_path / "h.sqlite"
    with RunLog(db) as rl:
        rl.record_run(run_id="old00001", created_at="2026-06-09T10:00:00+00:00",
                      summary=_summary(), decisions=[])
        rl.record_run(run_id="new00002", created_at="2026-06-10T10:00:00+00:00",
                      summary=_summary(), decisions=[])
    with RunLog(db) as rl:
        runs = rl.list_runs()
        assert [r.run_id for r in runs] == ["new00002", "old00001"]


def test_record_run_is_atomic_on_duplicate_id(tmp_path):
    db = tmp_path / "h.sqlite"
    with RunLog(db) as rl:
        rl.record_run(run_id="dup00001", created_at="2026-06-10T10:00:00+00:00",
                      summary=_summary(), decisions=decisions_from_outcome(_outcome()))
        with pytest.raises(Exception):
            rl.record_run(run_id="dup00001", created_at="2026-06-10T11:00:00+00:00",
                          summary=_summary(), decisions=decisions_from_outcome(_outcome()))
        # the failed second insert did not leave half its decisions behind
        assert len(rl.get_decisions("dup00001")) == 5


# ── CLI integration: run() writes the log when configured ────────────


def _base_run_cfg(tmp_path):
    import json

    stmt = tmp_path / "stmt.csv"
    stmt.write_text("Date,Amount,Description\n2026-05-01,12.00,Coffee Bar\n", encoding="utf-8")
    receipts = tmp_path / "receipts.csv"
    receipts.write_text(
        "document_id,detected_date,detected_total,detected_vendor\n"
        "r1,2026-05-01,12.00,Coffee Bar\n",
        encoding="utf-8",
    )
    cfg = {
        "statement": {
            "path": "stmt.csv", "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "source": "csv"},
        "output": {"path": "report.xlsx"},
        "run_log": {"path": "history.sqlite", "operator": "tester"},
    }
    p = tmp_path / "run.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p


def test_cli_run_writes_run_log(tmp_path, capsys):
    from expense_recon.cli import run

    config_path = _base_run_cfg(tmp_path)
    run(config_path)
    out = capsys.readouterr().out
    assert "Run logged:" in out

    db = tmp_path / "history.sqlite"
    assert db.exists()
    with RunLog(db) as rl:
        runs = rl.list_runs()
        assert len(runs) == 1
        assert runs[0].operator == "tester"
        assert runs[0].n_transactions == 1
        assert runs[0].statement_path == "stmt.csv"


def test_cli_run_without_run_log_block_writes_nothing(tmp_path):
    import json

    config_path = _base_run_cfg(tmp_path)
    cfg = json.loads(config_path.read_text())
    del cfg["run_log"]
    config_path.write_text(json.dumps(cfg), encoding="utf-8")

    from expense_recon.cli import run

    run(config_path)
    assert not (tmp_path / "history.sqlite").exists()


def test_history_and_diff_subcommands(tmp_path, capsys):
    from expense_recon.cli import main as cli_main, run

    config_path = _base_run_cfg(tmp_path)
    run(config_path)
    run(config_path)  # second run, same month

    with RunLog(tmp_path / "history.sqlite") as rl:
        ids = [r.run_id for r in rl.list_runs()]
    assert len(ids) == 2

    rc = cli_main(["history", "--config", str(config_path)])
    assert rc == 0
    assert "run " in capsys.readouterr().out

    rc = cli_main(["history", "--config", str(config_path), "--run", ids[0]])
    assert rc == 0
    assert "bucket" in capsys.readouterr().out

    rc = cli_main(["diff", "--config", str(config_path), ids[1], ids[0]])
    out = capsys.readouterr().out
    assert rc == 0
    assert "diff" in out
    # identical re-run of the same month: no bucket changes
    assert "no transaction changed bucket" in out


def test_history_no_runlog_block_errors(tmp_path, capsys):
    import json

    from expense_recon.cli import main as cli_main

    cfg = {"statement": {}, "receipts": {}}
    p = tmp_path / "run.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    rc = cli_main(["history", "--config", str(p)])
    assert rc == 2
    assert "no run_log" in capsys.readouterr().err
