"""CLI `store:` / `hosting:` opt-in wiring — BLUEPRINT Path A integration.

End-to-end through `run()`: a real run persists its statement (8.2) and
reports (8.3), content-addresses filename-only receipts (8.4), and carries
the receipt URL + report reference into the Zoho export (8.5). All offline
(keyword-stub categorizer, no LLM, synthetic chart of accounts)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from expense_recon.cli import run
from expense_recon.hosting import ReceiptStore
from expense_recon.store import ReportStore, StatementStore

_STATEMENT = (
    "Date,Description,Amount\n"
    "04/01/2026,COFFEE SHOP NYC,5.75\n"
    "04/03/2026,DELANCEY TAVERN,57.50\n"
)
# Two expenses on one report: one carries a Zoho URL (passthrough side of
# the 8.1 fork), one only a filename (8.4 hosting side).
_EXPENSES = (
    "Expense Date,Amount,Merchant,Currency,Report Number,Expense ID,Receipt URL,Receipt Name\n"
    "2026-04-01,5.75,Coffee Shop NYC,USD,ER-00220,EXP-1,https://expense.zoho.example/r/1,\n"
    "2026-04-03,57.50,Delancey Tavern,USD,ER-00220,EXP-2,,delancey.jpg\n"
)
_COA = (
    "Account Name,Account Code,Account Type,Parent Account,Status\n"
    "Travel Expense,E100,Expense,,Active\n"
    "Amex Card USD,A200,Other Current Liability,,Active\n"
)


def _write_run(tmp_path: Path, *, store=True, hosting=True, zoho=True) -> Path:
    (tmp_path / "statement.csv").write_text(_STATEMENT, encoding="utf-8")
    (tmp_path / "expense.csv").write_text(_EXPENSES, encoding="utf-8")
    (tmp_path / "coa.csv").write_text(_COA, encoding="utf-8")
    folder = tmp_path / "receipts"
    folder.mkdir()
    (folder / "delancey.jpg").write_bytes(b"delancey-image-bytes")

    config: dict = {
        "statement": {
            "path": "statement.csv", "account_id": "chase-2838",
            "legal_entity_id": "brisken-us", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {
            "path": "expense.csv", "source": "expense_csv", "default_currency": "USD",
            "column_map": {
                "expense_date": "Expense Date", "amount": "Amount", "vendor": "Merchant",
                "currency": "Currency", "report_number": "Report Number",
                "document_id": "Expense ID", "receipt_url": "Receipt URL",
                "receipt_name": "Receipt Name",
            },
        },
        "output": {"path": "report.xlsx"},
    }
    if store:
        config["store"] = {"statements_path": "statements.sqlite", "reports_path": "reports.sqlite"}
    if hosting:
        config["hosting"] = {"root": "receipt-store", "receipts_dir": "receipts"}
    if zoho:
        config["zoho"] = {
            "coa_source": "csv", "coa_csv_path": "coa.csv",
            "scope_groups": ["Travel Expense"], "export_path": "zoho-journal.csv",
            "card_accounts": {"chase-2838": "A200 Amex Card USD"},
        }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_run_persists_statement_table(tmp_path):
    run(_write_run(tmp_path))
    db = tmp_path / "statements.sqlite"
    assert db.exists()
    with StatementStore(db) as store:
        assert store.count() == 2  # both statement transactions persisted


def test_run_persists_reports_and_crossreference(tmp_path):
    run(_write_run(tmp_path))
    db = tmp_path / "reports.sqlite"
    assert db.exists()
    with ReportStore(db) as store:
        assert store.count() == 1
        assert store.report_for("EXP-1") == "ER-00220"
        assert store.report_for("EXP-2") == "ER-00220"
        assert store.expense_count("ER-00220") == 2


def test_run_hosts_filename_only_receipt(tmp_path):
    run(_write_run(tmp_path))
    root = tmp_path / "receipt-store"
    assert root.exists()
    # delancey.jpg (filename-only) is content-addressed under the store.
    import hashlib
    h = hashlib.sha256(b"delancey-image-bytes").hexdigest()
    assert ReceiptStore(root).get_path(h, ".jpg") is not None


def test_export_carries_receipt_url_and_report_reference(tmp_path):
    run(_write_run(tmp_path))
    export = tmp_path / "zoho-journal.csv"
    assert export.exists()
    with export.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    hdr = rows[0]
    iu, ir = hdr.index("Receipt URL"), hdr.index("Report Reference")
    body = rows[1:]
    assert body, "expected at least one matched journal entry"
    # Every exported row traces to the one report.
    assert {r[ir] for r in body} == {"ER-00220"}
    urls = {r[iu] for r in body}
    assert "https://expense.zoho.example/r/1" in urls          # passthrough (8.1 URL side)
    assert any(u.startswith("/receipts/") for u in urls)        # hosted (8.4 filename side)


def test_dry_run_persists_and_hosts_nothing(tmp_path):
    run(_write_run(tmp_path), dry_run=True)
    assert not (tmp_path / "statements.sqlite").exists()
    assert not (tmp_path / "reports.sqlite").exists()
    assert not (tmp_path / "receipt-store").exists()
    assert not (tmp_path / "zoho-journal.csv").exists()


def test_no_store_or_hosting_blocks_writes_no_extra_files(tmp_path):
    # Absent blocks = no behaviour change beyond the export, which falls
    # back to each receipt's own 8.1 fields for the reference columns.
    run(_write_run(tmp_path, store=False, hosting=False))
    assert not (tmp_path / "statements.sqlite").exists()
    assert not (tmp_path / "reports.sqlite").exists()
    assert not (tmp_path / "receipt-store").exists()

    export = tmp_path / "zoho-journal.csv"
    with export.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    hdr = rows[0]
    iu, ir = hdr.index("Receipt URL"), hdr.index("Report Reference")
    body = rows[1:]
    # Report reference still present (from rec.report_number fallback);
    # the passthrough URL still present (rec.receipt_url); the filename-only
    # receipt has no URL without hosting, so it is blank, not fabricated.
    assert {r[ir] for r in body} == {"ER-00220"}
    urls = {r[iu] for r in body}
    assert "https://expense.zoho.example/r/1" in urls
    assert not any(u.startswith("/receipts/") for u in urls)  # nothing hosted
