"""Tests for the inspect subcommand (ANNEALING B2)."""
from __future__ import annotations

from pathlib import Path

import pytest

from expense_recon.inspect import (
    format_output,
    guess_column_map,
    inspect,
    read_csv_headers,
)


def test_guess_amex_us_headers():
    headers = ["Date", "Description", "Amount", "Card Member"]
    mapping, missing = guess_column_map(headers)
    assert mapping == {
        "transaction_date": "Date",
        "amount": "Amount",
        "vendor": "Description",
    }
    assert missing == []


def test_guess_chase_style_headers():
    headers = ["Transaction Date", "Posting Date", "Description", "Category", "Type", "Amount"]
    mapping, missing = guess_column_map(headers)
    assert mapping["transaction_date"] == "Transaction Date"
    assert mapping["posting_date"] == "Posting Date"
    assert mapping["amount"] == "Amount"
    assert mapping["vendor"] == "Description"
    assert missing == []


def test_posting_date_does_not_steal_transaction_date():
    """`Posting Date` matches the date regex too — must not be claimed
    by transaction_date when a dedicated Transaction Date exists.
    """
    headers = ["Posting Date", "Transaction Date", "Amount", "Description"]
    mapping, _ = guess_column_map(headers)
    assert mapping["posting_date"] == "Posting Date"
    assert mapping["transaction_date"] == "Transaction Date"


def test_de_amex_headers_recognized():
    """German Amex export headers."""
    headers = ["Buchungsdatum", "Beschreibung", "Betrag", "Währung"]
    mapping, missing = guess_column_map(headers)
    assert mapping["transaction_date"] == "Buchungsdatum"
    assert mapping["vendor"] == "Beschreibung"
    assert mapping["amount"] == "Betrag"
    assert mapping["transaction_currency"] == "Währung"
    assert missing == []


def test_unknown_headers_produce_missing_list():
    headers = ["Foo", "Bar", "Baz"]
    mapping, missing = guess_column_map(headers)
    assert mapping == {}
    assert sorted(missing) == ["amount", "transaction_date", "vendor"]


def test_partial_match_reports_only_missing():
    headers = ["Date", "Foo", "Bar"]
    mapping, missing = guess_column_map(headers)
    assert mapping == {"transaction_date": "Date"}
    assert sorted(missing) == ["amount", "vendor"]


def test_inspect_csv_end_to_end(tmp_path: Path):
    csv_path = tmp_path / "stmt.csv"
    csv_path.write_text(
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE,5.75,M\n",
        encoding="utf-8",
    )
    mapping, missing, headers = inspect(csv_path)
    assert mapping == {
        "transaction_date": "Date",
        "amount": "Amount",
        "vendor": "Description",
    }
    assert missing == []
    assert headers == ["Date", "Description", "Amount", "Card Member"]


def test_inspect_xlsx_end_to_end(tmp_path: Path):
    import openpyxl
    xlsx_path = tmp_path / "stmt.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date", "Description", "Amount"])
    ws.append(["2026-04-01", "Coffee", 5.75])
    wb.save(xlsx_path)

    mapping, missing, _ = inspect(xlsx_path)
    assert mapping["transaction_date"] == "Date"
    assert mapping["vendor"] == "Description"
    assert mapping["amount"] == "Amount"
    assert missing == []


def test_inspect_unsupported_extension_raises(tmp_path: Path):
    bad = tmp_path / "stmt.txt"
    bad.write_text("Date\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unsupported file extension"):
        inspect(bad)


def test_format_output_includes_tbd_block_when_missing():
    mapping = {"transaction_date": "Date"}
    missing = ["amount", "vendor"]
    headers = ["Date", "Foo", "Bar"]
    output = format_output(mapping, missing, headers)

    assert '"column_map"' in output
    assert '"transaction_date": "Date"' in output
    assert "MISSING required field(s)" in output
    assert "amount: TBD" in output
    assert "vendor: TBD" in output
    assert "'Foo'" in output  # available header listed


def test_format_output_clean_when_all_mapped():
    mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "vendor": "Description",
    }
    output = format_output(mapping, [], ["Date", "Amount", "Description"])
    assert "MISSING" not in output
    assert "TBD" not in output


def test_read_csv_headers_handles_bom(tmp_path: Path):
    """Windows-exported CSVs often ship a UTF-8 BOM. The CSV header
    reader must strip it so the column_map matches the visible header.
    """
    csv_path = tmp_path / "bom.csv"
    csv_path.write_bytes(b"\xef\xbb\xbfDate,Amount,Description\n")
    headers = read_csv_headers(csv_path)
    assert headers == ["Date", "Amount", "Description"]
