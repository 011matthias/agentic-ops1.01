"""Subprocess CLI test (E2).

Exercises the real entry point via `python -m expense_recon.cli`, so a
broken console-script wiring or import-time error is caught — the
in-process `run()` tests can't see those.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_STATEMENT = (
    "Date,Description,Amount,Card Member\n"
    "04/01/2026,COFFEE,5.75,M\n"
)
_RECEIPTS = (
    'document_id,detected_date,detected_total,detected_currency,'
    'detected_vendor,detected_reference,line_items\n'
    'rcpt-001,2026-04-01,5.75,USD,Coffee,,'
    '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
)


def _write_fixture(tmp_path: Path, extra: dict | None = None) -> Path:
    (tmp_path / "statement.csv").write_text(_STATEMENT, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(_RECEIPTS, encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "report.xlsx"},
    }
    if extra:
        config.update(extra)
    cfg = tmp_path / "run.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    return cfg


def _run(*args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "expense_recon.cli", *args],
        cwd=cwd, capture_output=True, text=True,
    )


def test_cli_entrypoint_writes_report(tmp_path):
    cfg = _write_fixture(tmp_path)
    result = _run("--config", str(cfg), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Wrote report" in result.stdout
    assert (tmp_path / "report.xlsx").exists()


def test_cli_entrypoint_dry_run_writes_no_file(tmp_path):
    cfg = _write_fixture(tmp_path)
    result = _run("--config", str(cfg), "--dry-run", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "DRY RUN" in result.stdout
    assert not (tmp_path / "report.xlsx").exists()


def test_cli_entrypoint_bad_config_exits_2(tmp_path):
    missing = tmp_path / "nope.json"
    result = _run("--config", str(missing), cwd=tmp_path)
    assert result.returncode == 2
    assert "ERROR" in result.stderr
