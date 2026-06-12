"""Zoho journal-entry export skeleton tests (slice 4.6)."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

import pytest

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
from expense_recon.output.zoho_export import (
    ZOHO_COLUMNS,
    build_journal_rows,
    write_zoho_export,
)


def _line(desc, amount, category, source=ClassificationSource.LINE) -> LineItem:
    return LineItem(
        description=desc,
        line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=None, confidence=0.9,
            source=source, reasoning="t",
        ),
    )


def _tx(tid="t1", amount="180", account="amex-usd") -> Transaction:
    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id=account,
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="AMAZON",
    )


def _receipt(items) -> Receipt:
    return Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        line_items=tuple(items),
    )


def test_multi_line_receipt_becomes_n_debits_plus_one_credit():
    tx = _tx()
    rec = _receipt([
        _line("chair", "150", "Equipment & Hardware"),
        _line("coffee beans", "30", "Office Supplies & Consumables"),
    ])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])

    rows = build_journal_rows(outcome, {"t1": tx}, {"r1": rec})

    # 2 debit rows + 1 balancing credit row.
    assert len(rows) == 3
    debits = [r for r in rows if r[5]]   # Debit column non-empty
    credits = [r for r in rows if r[6]]  # Credit column non-empty
    assert len(debits) == 2
    assert len(credits) == 1
    # Balanced: debits sum == credit.
    assert sum(Decimal(r[5]) for r in debits) == Decimal(credits[0][6]) == Decimal("180.00")
    # All linked by the same Reference#.
    assert {r[3] for r in rows} == {"t1"}


def test_only_matched_transactions_exported():
    tx1 = _tx("t1")
    tx2 = _tx("t2")  # unmatched
    rec = _receipt([_line("chair", "180", "Equipment & Hardware")])
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    rows = build_journal_rows(outcome, {"t1": tx1, "t2": tx2}, {"r1": rec})
    assert {r[3] for r in rows} == {"t1"}  # t2 withheld


def test_review_line_marked_uncategorized():
    tx = _tx()
    rec = _receipt([_line("???", "180", None, source=ClassificationSource.REVIEW)])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])
    rows = build_journal_rows(outcome, {"t1": tx}, {"r1": rec})
    debit_row = next(r for r in rows if r[5])
    assert debit_row[1] == "(uncategorized - assign)"


def test_write_zoho_export_has_header(tmp_path):
    tx = _tx()
    rec = _receipt([_line("chair", "180", "Equipment & Hardware")])
    outcome = MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])

    out = write_zoho_export(outcome, [tx], [rec], tmp_path / "zoho.csv")
    with out.open(encoding="utf-8") as fh:
        reader = list(csv.reader(fh))
    assert tuple(reader[0]) == ZOHO_COLUMNS
    assert len(reader) == 3  # header + 1 debit + 1 credit


# ── slice 4.6: account resolution against a (synthetic) chart ────────
#
# Synthetic accounts only. Brisken's real chart of accounts is sensitive
# client data and never lands in this repo (BLUEPRINT 4.1 / 5.3). The
# shape here (parent + leaf, an expense subtree, a card account) mirrors
# the real Zoho export so the resolver is exercised the way live data
# hits it.

from expense_recon.ingest.chart_of_accounts import ChartOfAccounts  # noqa: E402

_COA_RECORDS = [
    {"account_id": "1", "account_name": "Travel Expense", "account_code": "E100",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "2", "account_name": "Travel: Flights", "account_code": "E100-21",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "3", "account_name": "Office Pantry", "account_code": "E400-10",
     "account_type": "expense", "parent_account_name": "Office Infra and Admin", "is_active": True},
    {"account_id": "9", "account_name": "Amex Card USD", "account_code": "A200",
     "account_type": "credit_card", "parent_account_name": None, "is_active": True},
]


def _coa() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_COA_RECORDS)


def _line_acct(desc, amount, category, zoho_account, source=ClassificationSource.LINE) -> LineItem:
    return LineItem(
        description=desc,
        line_total=Decimal(amount),
        categorization=Categorization(
            category=category, zoho_account=zoho_account, confidence=0.9,
            source=source, reasoning="t",
        ),
    )


def _matched_outcome() -> MatchOutcome:
    return MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])


def test_debit_label_resolved_to_real_account_name():
    """The LLM-picked 'CODE name' label resolves to the real Zoho account
    name (code parsed from the leading token), not left as the label."""
    tx = _tx()
    rec = _receipt([_line_acct("flight to BER", "180", "Travel & Transport",
                               "E100-21 Travel: Flights")])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa())
    debit = next(r for r in rows if r[5])
    assert debit[1] == "Travel: Flights"


def test_unresolvable_account_flagged_never_guessed():
    """A picked account that isn't in the chart is flagged unmapped, not
    silently coerced to the category name."""
    tx = _tx()
    rec = _receipt([_line_acct("widget", "180", "Equipment & Hardware",
                               "Z999 Hallucinated Account")])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa())
    debit = next(r for r in rows if r[5])
    assert debit[1] == "(account unmapped - assign)"


def test_missing_zoho_account_flagged_when_chart_present():
    """Category present but no zoho_account picked (e.g. keyword stub) →
    unmapped flag under a chart, rather than a guessed account."""
    tx = _tx()
    rec = _receipt([_line_acct("flight", "180", "Travel & Transport", None)])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa())
    debit = next(r for r in rows if r[5])
    assert debit[1] == "(account unmapped - assign)"


def test_review_line_still_uncategorized_under_chart():
    tx = _tx()
    rec = _receipt([_line_acct("???", "180", None, None,
                               source=ClassificationSource.REVIEW)])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa())
    debit = next(r for r in rows if r[5])
    assert debit[1] == "(uncategorized - assign)"


def test_credit_resolved_from_card_map_by_label():
    tx = _tx(account="amex-usd")
    rec = _receipt([_line_acct("flight", "180", "Travel & Transport",
                               "E100-21 Travel: Flights")])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa(),
                              card_accounts={"amex-usd": "A200 Amex Card USD"})
    credit = next(r for r in rows if r[6])
    assert credit[1] == "Amex Card USD"


def test_credit_resolved_from_card_map_by_code():
    tx = _tx(account="amex-usd")
    rec = _receipt([_line_acct("flight", "180", "Travel & Transport",
                               "E100-21 Travel: Flights")])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa(),
                              card_accounts={"amex-usd": "A200"})
    credit = next(r for r in rows if r[6])
    assert credit[1] == "Amex Card USD"


def test_credit_placeholder_kept_when_card_unmapped():
    """No card_accounts entry → the visible placeholder stays, so the gap
    is obvious rather than guessed."""
    tx = _tx(account="amex-usd")
    rec = _receipt([_line_acct("flight", "180", "Travel & Transport",
                               "E100-21 Travel: Flights")])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa())
    credit = next(r for r in rows if r[6])
    assert credit[1] == "Card: amex-usd"


def test_resolution_keeps_books_balanced():
    """De-placeholdering must not disturb the double-entry invariant."""
    tx = _tx(account="amex-usd")
    rec = _receipt([
        _line_acct("flight", "150", "Travel & Transport", "E100-21 Travel: Flights"),
        _line_acct("snacks", "30", "Office Supplies & Consumables", "E400-10 Office Pantry"),
    ])
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec},
                              chart_of_accounts=_coa(),
                              card_accounts={"amex-usd": "A200"})
    debits = sum(Decimal(r[5]) for r in rows if r[5])
    credits = sum(Decimal(r[6]) for r in rows if r[6])
    assert debits == credits == Decimal("180.00")


# ── slice 4.9: CLI wires the zoho: block end-to-end ─────────────────


def test_cli_writes_zoho_export_with_csv_chart(tmp_path):
    """End-to-end: a `zoho:` block with a CSV chart source loads the
    chart, narrows to the approved scope groups, and writes the Zoho
    journal CSV with the balancing credit resolved to the real card
    account. No LLM (keyword stub) → the debit is left unmapped, which
    is the correct 'never guess' behaviour."""
    import json
    from expense_recon.cli import run

    statement_csv = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE SHOP NYC,5.75,M\n"
    )
    receipts_csv = (
        'document_id,detected_date,detected_total,detected_currency,'
        'detected_vendor,detected_reference,line_items\n'
        'rcpt-001,2026-04-01,5.75,USD,Coffee Shop NYC,,'
        '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    )
    coa_csv = (
        "Account Name,Account Code,Account Type,Parent Account,Status\n"
        "Travel Expense,E100,Expense,,Active\n"
        "Travel: Flights,E100-21,Expense,Travel Expense,Active\n"
        "Amex Card USD,A200,Other Current Liability,,Active\n"
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    (tmp_path / "coa.csv").write_text(coa_csv, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-usd",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "report.xlsx"},
        "zoho": {
            "coa_source": "csv",
            "coa_csv_path": "coa.csv",
            "scope_groups": ["Travel Expense"],
            "export_path": "zoho-journal.csv",
            "card_accounts": {"amex-usd": "A200 Amex Card USD"},
        },
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    run(config_path)

    export = tmp_path / "zoho-journal.csv"
    assert export.exists()
    with export.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == ZOHO_COLUMNS
    credit = next(r for r in rows[1:] if r[6])
    assert credit[1] == "Amex Card USD"  # balancing credit resolved


def test_cli_csv_source_missing_path_raises(tmp_path):
    import json
    from expense_recon.cli import ConfigError, run

    (tmp_path / "statement.csv").write_text(
        "Date,Description,Amount,Card Member\n04/01/2026,X,1.0,M\n", encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor\n", encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "a", "legal_entity_id": "b",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv"},
        "zoho": {"coa_source": "csv"},  # no coa_csv_path
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"coa_csv_path"):
        run(config_path)


def test_cli_disabled_zoho_block_writes_no_export(tmp_path):
    """`enabled: false` short-circuits the chart load and export."""
    import json
    from expense_recon.cli import run

    statement_csv = "Date,Description,Amount,Card Member\n04/01/2026,COFFEE,5.75,M\n"
    receipts_csv = (
        'document_id,detected_date,detected_total,detected_currency,'
        'detected_vendor,detected_reference,line_items\n'
        'rcpt-001,2026-04-01,5.75,USD,Coffee,,'
        '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "amex-usd", "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "report.xlsx"},
        "zoho": {"enabled": False, "export_path": "zoho-journal.csv"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = run(config_path)
    assert result is not None
    assert not (tmp_path / "zoho-journal.csv").exists()


# ── slice 8.5: receipt-URL + report-reference columns ───────────────
#
# Two trailing columns (index 7 = Receipt URL, 8 = Report Reference)
# carry the receipt link + the Zoho Expense report each entry traces to.

_RECEIPT_URL_COL = 7
_REPORT_REF_COL = 8


def _receipt_prov(items, *, report_number=None, receipt_url=None, receipt_name=None) -> Receipt:
    return Receipt(
        document_id="r1", legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("180"),
        detected_currency="USD", detected_vendor="Amazon",
        report_number=report_number, receipt_url=receipt_url, receipt_name=receipt_name,
        line_items=tuple(items),
    )


def test_header_carries_the_two_reference_columns(tmp_path):
    assert ZOHO_COLUMNS[_RECEIPT_URL_COL] == "Receipt URL"
    assert ZOHO_COLUMNS[_REPORT_REF_COL] == "Report Reference"
    tx = _tx()
    rec = _receipt_prov([_line("chair", "180", "Equipment & Hardware")],
                        report_number="ER-00220", receipt_url="https://z/r/1")
    out = write_zoho_export(_matched_outcome(), [tx], [rec], tmp_path / "z.csv")
    with out.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert tuple(rows[0]) == ZOHO_COLUMNS
    assert all(len(r) == len(ZOHO_COLUMNS) for r in rows)


def test_reference_columns_fall_back_to_receipt_fields():
    """With no wired lookups, the receipt's own 8.1 fields populate the
    columns — so the existing CLI path carries the references for free."""
    tx = _tx()
    rec = _receipt_prov(
        [_line("chair", "150", "Equipment & Hardware"),
         _line("beans", "30", "Office Supplies & Consumables")],
        report_number="ER-00220", receipt_url="https://expense.zoho.example/r/1001",
    )
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec})
    # 2 debits + 1 credit; the reference columns repeat on every row.
    assert len(rows) == 3
    for r in rows:
        assert r[_RECEIPT_URL_COL] == "https://expense.zoho.example/r/1001"
        assert r[_REPORT_REF_COL] == "ER-00220"


def test_wired_lookups_override_receipt_fields():
    """receipt_urls (8.4) + report_for (8.3) take precedence over the
    receipt's own fields (e.g. a filename-only receipt hosted by 8.4)."""
    tx = _tx()
    rec = _receipt_prov([_line("chair", "180", "Equipment & Hardware")],
                        report_number="ER-OLD", receipt_url=None, receipt_name="chair.jpg")
    rows = build_journal_rows(
        _matched_outcome(), {"t1": tx}, {"r1": rec},
        receipt_urls={"r1": "/receipts/ab/abcd.jpg"},
        report_for={"r1": "ER-00220"}.get,
    )
    debit = next(r for r in rows if r[5])
    assert debit[_RECEIPT_URL_COL] == "/receipts/ab/abcd.jpg"
    assert debit[_REPORT_REF_COL] == "ER-00220"


def test_reference_columns_blank_when_unknown():
    """No receipt fields and no wired lookups → blank, never fabricated."""
    tx = _tx()
    rec = _receipt([_line("chair", "180", "Equipment & Hardware")])  # no prov fields
    rows = build_journal_rows(_matched_outcome(), {"t1": tx}, {"r1": rec})
    for r in rows:
        assert r[_RECEIPT_URL_COL] == ""
        assert r[_REPORT_REF_COL] == ""


def test_wired_lookup_miss_is_blank_not_error():
    """A document_id absent from the wired mapping resolves to blank, and
    a report_for returning None is blank — surfaced, not fabricated."""
    tx = _tx()
    rec = _receipt_prov([_line("chair", "180", "Equipment & Hardware")],
                        report_number="ER-FALLBACK", receipt_url="https://fallback")
    rows = build_journal_rows(
        _matched_outcome(), {"t1": tx}, {"r1": rec},
        receipt_urls={},                 # r1 not present
        report_for=lambda doc: None,     # always unknown
    )
    debit = next(r for r in rows if r[5])
    assert debit[_RECEIPT_URL_COL] == ""   # wired mapping wins, miss → blank
    assert debit[_REPORT_REF_COL] == ""
