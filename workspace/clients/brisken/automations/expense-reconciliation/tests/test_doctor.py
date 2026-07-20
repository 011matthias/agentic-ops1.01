"""Pre-flight `doctor` command (BLUEPRINT 5.14). All offline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from expense_recon.doctor import run_doctor


def _write(p: Path, obj) -> Path:
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def _statement_csv(folder: Path) -> Path:
    f = folder / "stmt.csv"
    f.write_text("Date,Amount,Description\n2026-05-01,12.00,Coffee\n", encoding="utf-8")
    return f


def _base_cfg(folder: Path) -> dict:
    _statement_csv(folder)
    (folder / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor\n", encoding="utf-8"
    )
    return {
        "statement": {
            "path": "stmt.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {
                "transaction_date": "Date",
                "amount": "Amount",
                "vendor": "Description",
            },
        },
        "receipts": {"path": "receipts.csv", "source": "csv"},
        "output": {"path": "report.xlsx"},
    }


def test_clean_config_passes(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "all checks passed" in out
    assert "FAIL" not in out.replace("0 FAIL", "")


def test_missing_config_file(tmp_path, capsys):
    rc = run_doctor(tmp_path / "nope.json")
    assert rc == 1


def test_invalid_json(tmp_path, capsys):
    p = tmp_path / "run.json"
    p.write_text("{ not json", encoding="utf-8")
    rc = run_doctor(p)
    assert rc == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_missing_statement_file_fails(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    cfg["statement"]["path"] = "ghost.csv"
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    assert rc == 1
    assert "file not found" in capsys.readouterr().out


def test_column_map_missing_required_key_fails(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    del cfg["statement"]["column_map"]["amount"]
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    assert rc == 1
    assert "missing required keys" in capsys.readouterr().out


def test_mapped_column_absent_from_header_fails(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    cfg["statement"]["column_map"]["vendor"] = "Merchant"  # not in header
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 1
    assert "'Merchant'" in out and "not in header" in out


def test_folder_source_without_llm_fails(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "r.jpg").write_bytes(b"x")
    cfg["receipts"] = {"path": "receipts", "source": "folder"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 1
    assert "needs an `llm:` block" in out


def test_folder_source_with_llm_but_unset_key_fails(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = _base_cfg(tmp_path)
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "r.jpg").write_bytes(b"x")
    (folder / "notes.txt").write_text("skip me")
    cfg["receipts"] = {"path": "receipts", "source": "folder"}
    cfg["llm"] = {"provider": "openai", "api_key_env": "OPENAI_API_KEY"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 1
    assert "is not set" in out
    # the non-receipt file is surfaced as a WARN, not a silent drop
    assert "non-receipt file" in out
    assert "1 receipt file(s) ready" in out


def test_folder_source_with_key_set_passes(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cfg = _base_cfg(tmp_path)
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "r.jpg").write_bytes(b"x")
    cfg["receipts"] = {"path": "receipts", "source": "folder"}
    cfg["llm"] = {"provider": "openai", "api_key_env": "OPENAI_API_KEY"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    assert rc == 0
    assert "is set" in capsys.readouterr().out


def test_inferred_folder_mode_from_directory_path(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    cfg = _base_cfg(tmp_path)
    folder = tmp_path / "rcpts"
    folder.mkdir()
    (folder / "a.png").write_bytes(b"x")
    cfg["receipts"] = {"path": "rcpts"}  # no explicit source
    cfg["llm"] = {"provider": "openai"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "folder mode" in out


def test_zoho_csv_source_missing_file_fails(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    cfg["zoho"] = {"coa_source": "csv", "coa_csv_path": "chart.csv"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    assert rc == 1
    assert "chart-of-accounts CSV not found" in capsys.readouterr().out


def test_zoho_api_source_missing_creds_fails(tmp_path, capsys, monkeypatch):
    for v in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN", "ZOHO_ORG_ID"):
        monkeypatch.delenv(v, raising=False)
    cfg = _base_cfg(tmp_path)
    cfg["zoho"] = {"coa_source": "api"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 1
    assert "env vars unset" in out


def test_zoho_export_card_account_uncovered_warns(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("ZOHO_CLIENT_ID", "x")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "x")
    monkeypatch.setenv("ZOHO_REFRESH_TOKEN", "x")
    monkeypatch.setenv("ZOHO_ORG_ID", "x")
    cfg = _base_cfg(tmp_path)
    cfg["zoho"] = {
        "coa_source": "api",
        "export_path": "journal.csv",
        "card_accounts": {"some-other-card": "A200"},
    }
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    # WARN does not change exit code
    assert rc == 0
    assert "not in card_accounts" in out


def test_doctor_routes_through_cli_main(tmp_path, capsys):
    from expense_recon.cli import main as cli_main

    cfg = _base_cfg(tmp_path)
    config_path = _write(tmp_path / "run.json", cfg)
    rc = cli_main(["doctor", "--config", str(config_path)])
    assert rc == 0
    assert "all checks passed" in capsys.readouterr().out


# ── 3.15 PDF statement support + statement-source advisory ───────────


def test_pdf_statement_accepted_without_column_map(tmp_path, capsys):
    """A Chase statement PDF needs only path + legal_entity_id (account
    ids come from the per-card markers); doctor must not demand a
    column map for it."""
    cfg = _base_cfg(tmp_path)
    (tmp_path / "stmt.pdf").write_bytes(b"%PDF-1.4 stub")
    cfg["statement"] = {"path": "stmt.pdf", "legal_entity_id": "brisken-llc"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "statement PDF present" in out


def test_foreign_heavy_receipts_with_csv_statement_warns(tmp_path, capsys):
    """3.15 advisory: a foreign-heavy receipt set against a tabular
    statement WARNs to prefer the statement PDF (which carries the
    per-charge original-currency FX detail). Never changes exit code."""
    cfg = _base_cfg(tmp_path)
    rows = "\n".join(
        f"r{i},2026-05-0{i % 9 + 1},10.00,LOJA {i},BRL" for i in range(1, 7)
    )
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor,detected_currency\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "foreign-currency" in out and "statement PDF" in out


def test_domestic_receipts_no_advisory(tmp_path, capsys):
    cfg = _base_cfg(tmp_path)
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor,detected_currency\n"
        "r1,2026-05-01,10.00,STAPLES,USD\n"
        "r2,2026-05-02,20.00,UBER,USD\n",
        encoding="utf-8",
    )
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "foreign-currency" not in out


def test_expense_report_pdf_receipts_source_accepted(tmp_path, capsys):
    """The consolidated Zoho ER PDF is a first-class receipts source in
    the CLI (2026-07-16); doctor must accept it (no LLM needed)."""
    cfg = _base_cfg(tmp_path)
    (tmp_path / "ER-00215.pdf").write_bytes(b"%PDF-1.4 stub")
    cfg["receipts"] = {"path": "ER-00215.pdf", "source": "expense_report_pdf"}
    rc = run_doctor(_write(tmp_path / "run.json", cfg))
    out = capsys.readouterr().out
    assert rc == 0
    assert "expense report PDF present" in out
