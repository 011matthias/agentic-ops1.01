"""The two tabular statement readers agree, field by field (backlog item 128).

The September 2026 sign defect was `statement_csv` and `statement_xlsx`
drifting apart on charge sign: the CSV reader canonicalized (purchase =
positive, credit = negative) and the Excel reader kept the printed sign, so
Criss's Chase workbooks reached the matcher as `-15.00` against a `15.00`
receipt and two months reconciled 0 of 111. Each reader had its own tests
and each passed; nothing compared them to each other.

This file does. ONE synthetic statement is written as CSV and as XLSX from
the SAME row list, parsed through both readers (and through the CLI's
`_load_statement` dispatch with a run.json for each), and the Transaction
lists are compared field by field. Every row class where a drift could hide
is present, because a class that is absent is a class the guard is blind to:

* a purchase, a refund (credit), a card payment, a fee, an interest line and
  a reversal, so every recognised Type label is read by both;
* an amount printed with a thousands separator as TEXT in the CSV
  (`-2,500.00`) beside a NUMERIC cell in the workbook;
* dates typed as datetime cells in the workbook and as `MM/DD/YYYY` text in
  the CSV, and a row with no posting date;
* a vendor with leading/trailing whitespace and a non-ASCII character;
* a lowercase currency code, a card typed as an integer cell, a row that
  prints no card;
* a foreign-currency purchase carrying `original_amount` /
  `original_currency` / `fx_rate`;
* a byte-identical repeat of an earlier row (the occurrence suffix on the
  content id);
* a blank row in the middle of the file and a blank trailing row.

Two variants of the same rows: with the Type column mapped (the label decides
the sign per row) and without it (the whole-statement sign inference,
`infer_sign_flip`, must fire in both readers and land on the same answer).

Identity: `transaction_id` is content-derived (`assign_content_ids`) from
account, card, date, canonical amount, currency and vendor, none of which is
format-specific, so the ids MUST be equal across formats and are compared
like every other field. The one field excluded is `raw_text`, which is
`str(dict)` of the source row and differs by construction (the CSV row holds
strings, the workbook row holds datetime and float objects). Amounts compare
numerically: the CSV spells `2500.00` and the float cell `2500.0`, the same
money, and the id canonicalizes the trailing zeros away.
"""
from __future__ import annotations

import csv
import json
from dataclasses import fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from expense_recon.cli import _load_statement
from expense_recon.ingest.statement_csv import parse_statement_csv_tolerant
from expense_recon.ingest.statement_xlsx import parse_statement_xlsx_tolerant
from expense_recon.matching.types import Transaction

HEADERS = (
    "Transaction Date", "Post Date", "Description", "Type", "Amount",
    "Currency", "Original Amount", "Original Currency", "Exchange Rate", "Card",
)

# Every logical key both readers accept (`_common.REQUIRED_KEYS` +
# `OPTIONAL_KEYS`), so no column is left out of the comparison.
COLUMN_MAP = {
    "transaction_date": "Transaction Date",
    "posting_date": "Post Date",
    "vendor": "Description",
    "type": "Type",
    "amount": "Amount",
    "transaction_currency": "Currency",
    "original_amount": "Original Amount",
    "original_currency": "Original Currency",
    "fx_rate": "Exchange Rate",
    "card": "Card",
}

ACCOUNT = dict(
    account_id="card-family-1111",
    legal_entity_id="example-corp",
    account_card_currency="USD",
)

# The rows as PRINTED by a Chase-style export: purchases negative, credits
# positive. Values are typed; the two writers below spell them per format.
# None in a cell means the export left it empty. A row of all-None is blank.
BLANK = (None,) * len(HEADERS)
ROWS: list[tuple] = [
    # date, post date, description, type, amount, currency, orig amount, orig currency, fx rate, card
    (date(2026, 4, 1), date(2026, 4, 2), "COFFEE CORNER", "Sale", Decimal("-4.50"), "USD", None, None, None, 1111),
    (date(2026, 4, 3), date(2026, 4, 4), "  CAFÉ MÜNCHEN  ", "Sale", Decimal("-31.73"), "USD", Decimal("27.00"), "EUR", Decimal("1.175185185"), 1111),
    (date(2026, 4, 5), date(2026, 4, 5), "RAIL TICKETS", "Sale", Decimal("-2500.00"), "USD", None, None, None, 2222),
    (date(2026, 4, 7), date(2026, 4, 8), "OFFICE DEPOT RETURN", "Return", Decimal("15.00"), "USD", None, None, None, 1111),
    (date(2026, 4, 10), date(2026, 4, 10), "Payment Thank You", "Payment", Decimal("1234.56"), "USD", None, None, None, None),
    (date(2026, 4, 11), None, "TAXI 4711", "Sale", Decimal("-12.00"), "usd", None, None, None, 2222),
    (date(2026, 4, 12), date(2026, 4, 13), "ANNUAL FEE", "Fee", Decimal("-95.00"), "USD", None, None, None, 1111),
    BLANK,
    (date(2026, 4, 1), date(2026, 4, 2), "COFFEE CORNER", "Sale", Decimal("-4.50"), "USD", None, None, None, 1111),
    (date(2026, 4, 18), date(2026, 4, 19), "HOTEL LISBOA", "Sale", Decimal("-210.40"), "USD", Decimal("190.00"), "EUR", Decimal("1.107368421"), 2222),
    (date(2026, 4, 20), date(2026, 4, 21), "INTEREST CHARGE", "Interest", Decimal("-3.10"), "USD", None, None, None, None),
    (date(2026, 4, 22), date(2026, 4, 22), "REVERSAL SUBSCRIPTION", "Reversal", Decimal("9.99"), "USD", None, None, None, 1111),
    BLANK,
]
N_CHARGES = sum(1 for r in ROWS if r != BLANK)


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%m/%d/%Y")
    if isinstance(value, Decimal):
        # The export's own spelling: thousands separator, two decimals for
        # money, the rate as printed.
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent >= -2:
            return f"{value:,.2f}"
        return format(value, "f")
    return str(value)


def _xlsx_cell(value):
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, Decimal):
        return float(value)
    return value  # str, int, None


def write_csv(path: Path, rows: list[tuple]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow([_csv_cell(v) for v in row])
    return path


def write_xlsx(path: Path, rows: list[tuple]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(list(HEADERS))
    for row in rows:
        ws.append([_xlsx_cell(v) for v in row])
    wb.save(path)
    return path


COMPARED_FIELDS = tuple(f.name for f in fields(Transaction) if f.name != "raw_text")


def field_diff(csv_txs: list[Transaction], xlsx_txs: list[Transaction]) -> list[tuple]:
    """Every (source_row, field, csv value, xlsx value) that disagrees."""
    out: list[tuple] = []
    if len(csv_txs) != len(xlsx_txs):
        out.append(("*", "len", len(csv_txs), len(xlsx_txs)))
    for c, x in zip(csv_txs, xlsx_txs):
        for name in COMPARED_FIELDS:
            cv, xv = getattr(c, name), getattr(x, name)
            if cv != xv:
                out.append((c.source_row, name, cv, xv))
    return out


def _parse_both(tmp_path: Path, column_map: dict):
    csv_path = write_csv(tmp_path / "statement.csv", ROWS)
    xlsx_path = write_xlsx(tmp_path / "statement.xlsx", ROWS)
    csv_txs, csv_issues = parse_statement_csv_tolerant(csv_path, column_map, **ACCOUNT)
    xlsx_txs, xlsx_issues = parse_statement_xlsx_tolerant(xlsx_path, column_map, **ACCOUNT)
    return csv_txs, csv_issues, xlsx_txs, xlsx_issues


@pytest.fixture
def typed(tmp_path):
    return _parse_both(tmp_path, COLUMN_MAP)


@pytest.fixture
def inferred(tmp_path):
    """The same files with the Type column unmapped: sign by inference."""
    no_type = {k: v for k, v in COLUMN_MAP.items() if k != "type"}
    return _parse_both(tmp_path, no_type)


def test_the_fixture_exercises_every_row_class(typed):
    """A guard over a fixture that quietly exercises nothing guards nothing.
    Pin what the rows are supposed to be, on the CSV side (the XLSX side is
    then held to it by the parity test)."""
    txs, issues, _, _ = typed
    assert len(txs) == N_CHARGES, [t.vendor_from_statement for t in txs]
    assert not [i for i in issues if i.severity == "error"], issues
    by_vendor = {t.vendor_from_statement: t for t in txs}
    assert by_vendor["COFFEE CORNER"].amount == Decimal("4.50")  # purchase: positive
    assert by_vendor["COFFEE CORNER"].row_type == "purchase"
    assert by_vendor["OFFICE DEPOT RETURN"].amount == Decimal("-15.00")  # refund: negative
    assert by_vendor["OFFICE DEPOT RETURN"].is_credit is True
    assert by_vendor["OFFICE DEPOT RETURN"].row_type == "refund"
    assert by_vendor["Payment Thank You"].amount == Decimal("-1234.56")  # thousands, credit
    assert by_vendor["Payment Thank You"].row_type == "payment"
    assert by_vendor["Payment Thank You"].card_last4 is None
    assert by_vendor["RAIL TICKETS"].amount == Decimal("2500")  # thousands, purchase
    assert by_vendor["ANNUAL FEE"].row_type == "fee"
    assert by_vendor["INTEREST CHARGE"].row_type == "interest"
    assert by_vendor["REVERSAL SUBSCRIPTION"].row_type == "reversal"
    assert by_vendor["REVERSAL SUBSCRIPTION"].is_credit is True
    assert by_vendor["TAXI 4711"].posting_date is None
    assert by_vendor["TAXI 4711"].transaction_currency == "USD"  # upper-cased
    assert by_vendor["TAXI 4711"].card_last4 == "2222"
    assert "CAFÉ MÜNCHEN" in by_vendor  # stripped, non-ASCII kept
    cafe = by_vendor["CAFÉ MÜNCHEN"]
    assert (cafe.original_amount, cafe.original_currency, cafe.fx_rate) == (
        Decimal("27.00"), "EUR", Decimal("1.175185185"))
    # the repeat of row 1 keeps its own identity through the occurrence suffix
    coffees = [t for t in txs if t.vendor_from_statement == "COFFEE CORNER"]
    assert [t.transaction_id for t in coffees] == [
        coffees[0].transaction_id, coffees[0].transaction_id + "-1"]
    # blank rows are skipped, and numbering still counts them (header = 1)
    assert [t.source_row for t in txs] == [2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13]


def test_csv_and_xlsx_agree_on_every_field_with_a_type_column(typed):
    """The Type-column path: the export's own label decides each row's sign
    in BOTH readers, and every other field reads the same."""
    csv_txs, _, xlsx_txs, _ = typed
    assert field_diff(csv_txs, xlsx_txs) == []


def test_csv_and_xlsx_agree_on_every_field_under_sign_inference(inferred):
    """The no-Type path: both readers infer the file's convention from the
    sign majority, both flip, both warn, and the result is the same set of
    canonical charges. This is the exact path September's defect lived on."""
    csv_txs, csv_issues, xlsx_txs, xlsx_issues = inferred
    assert field_diff(csv_txs, xlsx_txs) == []
    assert len(csv_txs) == N_CHARGES
    flip_csv = [i for i in csv_issues if "sign convention inferred" in i.message]
    flip_xlsx = [i for i in xlsx_issues if "sign convention inferred" in i.message]
    assert len(flip_csv) == 1 and len(flip_xlsx) == 1, (csv_issues, xlsx_issues)
    assert flip_csv[0].severity == flip_xlsx[0].severity == "warning"
    # the inference lands on the same canonical signs the Type label gives
    purchases = [t for t in csv_txs if t.row_type is None and not t.is_credit]
    assert len(purchases) == 8
    assert all(t.amount > 0 for t in purchases)
    credits = [t for t in csv_txs if t.is_credit]
    assert sorted(t.amount for t in credits) == [
        Decimal("-1234.56"), Decimal("-15.00"), Decimal("-9.99")]


def test_the_two_sign_paths_agree_on_amount_and_credit(typed, inferred):
    """Mapping the Type column or not must not change which way the money
    went; only `row_type` (display) may differ, since the label is the only
    thing that can name a payment as a payment."""
    with_type = typed[0]
    without = inferred[0]
    assert [(t.amount, t.is_credit) for t in with_type] == [
        (t.amount, t.is_credit) for t in without]
    assert all(t.row_type is None for t in without)
    assert [t.transaction_id for t in with_type] == [t.transaction_id for t in without]


def test_the_cli_dispatch_reads_both_formats_to_the_same_charges(tmp_path):
    """Through `cli._load_statement` with a run.json for each file, the way a
    real run reaches the readers: same dispatch, same ids, same fields."""
    write_csv(tmp_path / "statement.csv", ROWS)
    write_xlsx(tmp_path / "statement.xlsx", ROWS)
    results = {}
    for name in ("statement.csv", "statement.xlsx"):
        cfg = {"statement": {"path": name, "column_map": COLUMN_MAP, **ACCOUNT}}
        (tmp_path / f"run-{name}.json").write_text(json.dumps(cfg), encoding="utf-8")
        loaded = json.loads((tmp_path / f"run-{name}.json").read_text(encoding="utf-8"))
        results[name] = _load_statement(loaded, tmp_path)
    csv_txs, csv_issues = results["statement.csv"]
    xlsx_txs, xlsx_issues = results["statement.xlsx"]
    assert field_diff(csv_txs, xlsx_txs) == []
    assert len(csv_txs) == N_CHARGES
    assert not [i for i in csv_issues + xlsx_issues if i.severity == "error"]


def test_field_diff_names_the_field_that_moved(typed):
    """The comparator itself: a one-field drift is reported by row and field,
    not swallowed. Without this the parity tests could pass on a comparator
    that compares nothing."""
    from dataclasses import replace

    csv_txs, _, xlsx_txs, _ = typed
    flipped = list(xlsx_txs)
    flipped[3] = replace(flipped[3], amount=-flipped[3].amount)
    diff = field_diff(csv_txs, flipped)
    assert [(row, name) for row, name, _, _ in diff] == [(5, "amount")], diff
