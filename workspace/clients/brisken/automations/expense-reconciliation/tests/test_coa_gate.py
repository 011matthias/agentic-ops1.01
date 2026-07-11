"""Pre-write chart-of-accounts (COA) validation gate tests.

Synthetic charts only. Brisken's real Books COA JSON is sensitive client
data and never lands in this repo (per coa_gate.py / BLUEPRINT 5.3). The
two-entity synthetic JSON here mirrors the real shape
(`{ "<org_id>": { "org": {...}, "accounts": [...] }, ... }`) so the
loader + gate are exercised the way live data hits them.
"""
from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal

import pytest

from expense_recon.coa_gate import (
    CoaGate,
    CoaVerdict,
    apply_gate,
    chart_for_org,
    classify_account,
    load_entity_chart,
    validate_postings,
)
from expense_recon.ingest.chart_of_accounts import ChartOfAccounts
from expense_recon.matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
)
from expense_recon.output.zoho_export import build_journal_rows


# ── synthetic chart (one entity) ────────────────────────────────────
#
# A parent expense group with two leaves, a retired ("DO NOT USE") leaf,
# an inactive leaf, a parent/header account, and a non-expense card —
# every verdict branch represented.
_API_RECORDS = [
    {"account_id": "1", "account_name": "Travel Expense", "account_code": "E100",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "2", "account_name": "Travel: Flights", "account_code": "E100-21",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "3", "account_name": "Travel: Hotels", "account_code": "E100-26",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "4", "account_name": "Office Pantry", "account_code": "E400-10",
     "account_type": "expense", "parent_account_name": "Office Infra", "is_active": True},
    {"account_id": "5", "account_name": "Office Infra", "account_code": "E400",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "6", "account_name": "Lodging (DO NOT USE)", "account_code": "E100Z",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "7", "account_name": "Old Software", "account_code": "E200",
     "account_type": "expense", "parent_account_name": None, "is_active": False},
    {"account_id": "9", "account_name": "Amex Card USD", "account_code": "A200",
     "account_type": "credit_card", "parent_account_name": None, "is_active": True},
]


def _coa() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_API_RECORDS)


def _line(zoho_account, *, category="Travel & Transport",
          source=ClassificationSource.LINE) -> LineItem:
    return LineItem(
        description="x",
        line_total=Decimal("10.00"),
        categorization=Categorization(
            category=category, zoho_account=zoho_account, confidence=0.9,
            source=source, reasoning="orig",
        ),
    )


def _receipt(items, doc="r1") -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id="le1",
        detected_date=date(2026, 4, 7), detected_total=Decimal("10.00"),
        detected_currency="USD", detected_vendor="Vendor",
        line_items=tuple(items),
    )


# ── classify_account: one verdict per branch ────────────────────────


def test_verdict_ok_for_active_leaf_in_scope():
    verdict, account = classify_account("E100-21 Travel: Flights", _coa())
    assert verdict is CoaVerdict.OK
    assert account.name == "Travel: Flights"


def test_verdict_missing_account_for_blank():
    assert classify_account(None, _coa())[0] is CoaVerdict.MISSING_ACCOUNT
    assert classify_account("", _coa())[0] is CoaVerdict.MISSING_ACCOUNT
    assert classify_account("   ", _coa())[0] is CoaVerdict.MISSING_ACCOUNT


def test_verdict_unknown_for_unresolvable():
    assert classify_account("Z999 Bogus", _coa())[0] is CoaVerdict.UNKNOWN


def test_verdict_inactive():
    verdict, account = classify_account("E200", _coa())
    assert verdict is CoaVerdict.INACTIVE
    assert account.name == "Old Software"


def test_verdict_do_not_use():
    assert classify_account("E100Z", _coa())[0] is CoaVerdict.DO_NOT_USE


def test_verdict_non_leaf_for_parent_account():
    # E100 (Travel Expense) and E400 (Office Infra) are parents.
    assert classify_account("E100", _coa())[0] is CoaVerdict.NON_LEAF
    assert classify_account("Office Infra", _coa())[0] is CoaVerdict.NON_LEAF


def test_verdict_out_of_scope_when_scope_groups_set():
    # Office Pantry is a postable leaf, but its root group (Office Infra)
    # is outside the Travel scope.
    verdict, _ = classify_account(
        "E400-10 Office Pantry", _coa(), scope_groups=["Travel Expense"]
    )
    assert verdict is CoaVerdict.OUT_OF_SCOPE
    # In-scope leaf passes.
    assert classify_account(
        "E100-21", _coa(), scope_groups=["Travel Expense"]
    )[0] is CoaVerdict.OK


# ── validate_postings: report + counts ──────────────────────────────


def test_validate_postings_counts_each_verdict():
    receipts = [
        _receipt([
            _line("E100-21 Travel: Flights"),   # OK
            _line("Z999 Bogus"),                # UNKNOWN
            _line("E100Z"),                     # DO_NOT_USE
            _line(None),                        # MISSING_ACCOUNT
        ]),
    ]
    report = validate_postings(receipts, _coa(), entity="822741658")
    assert report.n_lines == 4
    assert report.n_ok == 1
    assert report.n_diverted == 3
    assert report.counts[CoaVerdict.OK.value] == 1
    assert report.counts[CoaVerdict.UNKNOWN.value] == 1
    assert report.counts[CoaVerdict.DO_NOT_USE.value] == 1
    assert report.counts[CoaVerdict.MISSING_ACCOUNT.value] == 1
    assert not report.all_ok


def test_validate_skips_lines_without_categorization():
    rec = _receipt([LineItem(description="no cat", line_total=Decimal("10.00"))])
    report = validate_postings([rec], _coa())
    assert report.n_lines == 0


# ── apply_gate: divert non-OK, leave OK untouched ───────────────────


def test_apply_gate_diverts_non_ok_to_review():
    rec = _receipt([
        _line("E100-21 Travel: Flights"),   # OK, untouched
        _line("Z999 Bogus", category="Equipment & Hardware"),  # diverted
    ])
    report = validate_postings([rec], _coa(), entity="Corporate Services")
    gated = apply_gate([rec], report)

    ok_cat = gated[0].line_items[0].categorization
    bad_cat = gated[0].line_items[1].categorization

    # OK line: account + source preserved.
    assert ok_cat.zoho_account == "E100-21 Travel: Flights"
    assert ok_cat.source is ClassificationSource.LINE

    # Diverted line: account cleared, source REVIEW, note appended.
    assert bad_cat.zoho_account is None
    assert bad_cat.source is ClassificationSource.REVIEW
    assert "not postable in Corporate Services" in bad_cat.reasoning
    assert "UNKNOWN" in bad_cat.reasoning
    # Original reasoning preserved alongside the note.
    assert "orig" in bad_cat.reasoning


def test_apply_gate_does_not_mutate_inputs():
    rec = _receipt([_line("Z999 Bogus")])
    report = validate_postings([rec], _coa())
    apply_gate([rec], report)
    # The original receipt's categorization is unchanged (frozen + replace).
    assert rec.line_items[0].categorization.zoho_account == "Z999 Bogus"
    assert rec.line_items[0].categorization.source is ClassificationSource.LINE


def test_apply_gate_all_ok_returns_receipts_unchanged():
    rec = _receipt([_line("E100-21 Travel: Flights")])
    report = validate_postings([rec], _coa())
    gated = apply_gate([rec], report)
    assert report.all_ok
    assert gated[0] is rec  # same object, no rebuild


# ── CoaGate.run: validate + divert in one call ──────────────────────


def test_coa_gate_run_returns_gated_receipts_and_report():
    rec = _receipt([_line("E400-10 Office Pantry")])  # out of Travel scope
    gate = CoaGate(chart=_coa(), scope_groups=("Travel Expense",), entity="822741658")
    gated, report = gate.run([rec])
    assert report.counts[CoaVerdict.OUT_OF_SCOPE.value] == 1
    assert gated[0].line_items[0].categorization.zoho_account is None
    assert gated[0].line_items[0].categorization.source is ClassificationSource.REVIEW


# ── org-id chart loader: two-entity synthetic JSON ──────────────────


_CORP_ORG = "822741658"   # Corporate Services
_CLOUD_ORG = "697686691"  # Cloud Services


def _two_entity_json() -> dict:
    return {
        _CORP_ORG: {
            "org": {"name": "Corporate Services"},
            "accounts": [
                {"account_id": "c1", "account_name": "Corp Travel", "account_code": "C100",
                 "account_type": "expense", "parent_account_name": None, "is_active": True},
            ],
        },
        _CLOUD_ORG: {
            "org": {"name": "Cloud Services"},
            "accounts": [
                {"account_id": "k1", "account_name": "Cloud Hosting", "account_code": "K100",
                 "account_type": "expense", "parent_account_name": None, "is_active": True},
            ],
        },
    }


def test_chart_for_org_selects_the_right_entity():
    data = _two_entity_json()
    corp = chart_for_org(data, _CORP_ORG)
    cloud = chart_for_org(data, _CLOUD_ORG)
    # Each entity's chart holds only its own accounts.
    assert corp.by_code("C100").name == "Corp Travel"
    assert corp.by_code("K100") is None
    assert cloud.by_code("K100").name == "Cloud Hosting"
    assert cloud.by_code("C100") is None


def test_chart_for_org_accepts_int_org_id():
    data = _two_entity_json()
    corp = chart_for_org(data, int(_CORP_ORG))
    assert corp.by_code("C100").name == "Corp Travel"


def test_chart_for_org_unknown_entity_raises():
    with pytest.raises(KeyError, match="not in COA JSON"):
        chart_for_org(_two_entity_json(), "000000000")


def test_load_entity_chart_from_file(tmp_path):
    path = tmp_path / "books-coa.json"
    path.write_text(json.dumps(_two_entity_json()), encoding="utf-8")
    cloud = load_entity_chart(path, _CLOUD_ORG)
    assert cloud.by_code("K100").name == "Cloud Hosting"
    # And the gate built on that chart validates against it.
    verdict, _ = classify_account("K100 Cloud Hosting", cloud)
    assert verdict is CoaVerdict.OK


# ── end-to-end: gated build_journal_rows never posts a bad account ──


def _tx(tid="t1", amount="10", account="amex-usd"):
    from expense_recon.matching.types import Transaction

    return Transaction(
        transaction_id=tid, legal_entity_id="le1", account_id=account,
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="VENDOR",
    )


def _matched():
    return MatchOutcome(matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)])


def test_end_to_end_bad_account_never_reaches_journal_rows():
    """A receipt whose Zoho category does not exist in the target chart
    does NOT appear with that account in the export; it is flagged
    '(uncategorized - assign)' instead (the gate diverted it to REVIEW
    before resolution)."""
    tx = _tx()
    rec = _receipt([_line("Z999 Nonexistent Account", category="Travel & Transport")])
    gate = CoaGate(chart=_coa(), entity="822741658")

    rows = build_journal_rows(
        _matched(), {"t1": tx}, {"r1": rec},
        chart_of_accounts=_coa(),
        coa_gate=gate,
    )
    debit = next(r for r in rows if r[5])
    # The bad account string is nowhere in the export.
    assert "Z999" not in debit[1]
    assert "Nonexistent" not in debit[1]
    # And it's flagged for the reviewer.
    assert debit[1] == "(uncategorized - assign)"


def test_end_to_end_good_account_still_resolves_without_gate_change():
    """An in-chart, postable account resolves to its real name when the
    gate is present and passes it (gate is a no-op for OK lines)."""
    tx = _tx()
    rec = _receipt([_line("E100-21 Travel: Flights")])
    gate = CoaGate(chart=_coa(), entity="822741658")
    rows = build_journal_rows(
        _matched(), {"t1": tx}, {"r1": rec},
        chart_of_accounts=_coa(),
        coa_gate=gate,
    )
    debit = next(r for r in rows if r[5])
    assert debit[1] == "Travel: Flights"


def test_no_gate_is_byte_for_byte_identical():
    """Absent gate (coa_gate=None) leaves the export identical to the
    pre-gate behaviour — a bad account still resolves (or flags) exactly
    as before, proving the gate is opt-in."""
    tx = _tx()
    rec = _receipt([_line("E100-21 Travel: Flights")])
    without = build_journal_rows(
        _matched(), {"t1": tx}, {"r1": rec}, chart_of_accounts=_coa()
    )
    with_none = build_journal_rows(
        _matched(), {"t1": tx}, {"r1": rec}, chart_of_accounts=_coa(), coa_gate=None
    )
    assert without == with_none


# ── CLI config wiring: coa_validation block end-to-end ──────────────


def test_cli_coa_validation_diverts_bad_account(tmp_path):
    """End-to-end through the CLI: a `coa_validation:` block loads the
    target entity's chart from the Books COA JSON and diverts a posting
    account that does not exist in that chart, so it never lands in the
    Zoho export.

    Path-A `expense_csv` source: the Zoho Expense `category` becomes the
    receipt's `zoho_category`, which `_carry_zoho_account` puts on each
    line's posting account (Dirk 2026-06-16). The vendor "Uber" makes the
    keyword stub classify the line VENDOR (non-REVIEW), so the bad account
    ("E900 Phantom") is genuinely categorized and the gate is what catches
    it; without the gate it would resolve / flag as before. E900 is not in
    the entity's chart, so the gate diverts it to review.
    """
    from expense_recon.cli import run

    statement_csv = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,UBER TRIP,5.75,M\n"
    )
    # Zoho Expense export columns (Path A). `Category` -> Receipt.zoho_category
    # -> the posting account on the line. Set it to an account NOT in the
    # validation chart.
    receipts_csv = (
        "Expense ID,Expense Date,Amount,Currency,Merchant,Report Number,Category\n"
        "rcpt-001,2026-04-01,5.75,USD,Uber,ER-00220,E900 Phantom\n"
    )
    # The Zoho-export chart (resolves debits) has E900 so that, WITHOUT the
    # gate, the bad account would resolve to a real name — proving the gate
    # is what stops it, not a coincidental unmapped flag.
    coa_csv = (
        "Account Name,Account Code,Account Type,Parent Account,Status\n"
        "Phantom Expense,E900,Expense,,Active\n"
        "Amex Card USD,A200,Other Current Liability,,Active\n"
    )
    # The validation chart (Books COA JSON) for the target entity does NOT
    # contain E900, so E900 is UNKNOWN there and gets diverted.
    books_json = {
        _CORP_ORG: {
            "org": {"name": "Corporate Services"},
            "accounts": [
                {"account_id": "1", "account_name": "Travel: Flights",
                 "account_code": "E100-21", "account_type": "expense",
                 "parent_account_name": None, "is_active": True},
            ],
        },
    }
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    (tmp_path / "coa.csv").write_text(coa_csv, encoding="utf-8")
    (tmp_path / "books-coa.json").write_text(json.dumps(books_json), encoding="utf-8")

    expense_column_map = {
        "document_id": "Expense ID",
        "expense_date": "Expense Date",
        "amount": "Amount",
        "currency": "Currency",
        "vendor": "Merchant",
        "report_number": "Report Number",
        "category": "Category",
    }
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "amex-usd",
            "legal_entity_id": "brisken-llc", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount",
                           "vendor": "Description"},
        },
        "receipts": {
            "path": "receipts.csv", "source": "expense_csv",
            "default_currency": "USD", "column_map": expense_column_map,
        },
        "output": {"path": "report.xlsx"},
        "zoho": {
            "coa_source": "csv", "coa_csv_path": "coa.csv",
            "export_path": "zoho-journal.csv",
            "card_accounts": {"amex-usd": "A200 Amex Card USD"},
        },
        "coa_validation": {
            "chart_path": "books-coa.json",
            "org_id": _CORP_ORG,
            "entity_label": "Corporate Services",
        },
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    run(config_path)

    export = tmp_path / "zoho-journal.csv"
    assert export.exists()
    with export.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    debit = next(r for r in rows[1:] if r[5])
    # E900 / its resolved name "Phantom Expense" was diverted by the gate ->
    # flagged, never posted.
    assert "E900" not in debit[1]
    assert "Phantom" not in debit[1]
    assert debit[1] == "(uncategorized - assign)"


def test_cli_without_gate_bad_account_would_resolve(tmp_path):
    """Control for the gate test above: with NO `coa_validation:` block,
    the SAME bad account ("E900 Phantom") resolves to its real name in the
    export (because the Zoho-export chart contains E900). This proves the
    diversion in the gate test is caused by the gate, not by E900 being
    unmappable on its own."""
    from expense_recon.cli import run

    statement_csv = "Date,Description,Amount,Card Member\n04/01/2026,UBER TRIP,5.75,M\n"
    receipts_csv = (
        "Expense ID,Expense Date,Amount,Currency,Merchant,Report Number,Category\n"
        "rcpt-001,2026-04-01,5.75,USD,Uber,ER-00220,E900 Phantom\n"
    )
    coa_csv = (
        "Account Name,Account Code,Account Type,Parent Account,Status\n"
        "Phantom Expense,E900,Expense,,Active\n"
        "Amex Card USD,A200,Other Current Liability,,Active\n"
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    (tmp_path / "coa.csv").write_text(coa_csv, encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "amex-usd",
            "legal_entity_id": "brisken-llc", "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount",
                           "vendor": "Description"},
        },
        "receipts": {
            "path": "receipts.csv", "source": "expense_csv",
            "default_currency": "USD",
            "column_map": {
                "document_id": "Expense ID", "expense_date": "Expense Date",
                "amount": "Amount", "currency": "Currency", "vendor": "Merchant",
                "report_number": "Report Number", "category": "Category",
            },
        },
        "output": {"path": "report.xlsx"},
        "zoho": {
            "coa_source": "csv", "coa_csv_path": "coa.csv",
            "export_path": "zoho-journal.csv",
            "card_accounts": {"amex-usd": "A200 Amex Card USD"},
        },
        # No coa_validation block.
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    run(config_path)
    export = tmp_path / "zoho-journal.csv"
    with export.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    debit = next(r for r in rows[1:] if r[5])
    # Unguarded: E900 resolves to its real chart name.
    assert debit[1] == "Phantom Expense"


def test_cli_coa_validation_missing_chart_path_raises(tmp_path):
    from expense_recon.cli import ConfigError, run

    (tmp_path / "statement.csv").write_text(
        "Date,Description,Amount,Card Member\n04/01/2026,X,1.0,M\n", encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor,line_items\n"
        'r1,2026-04-01,1.0,X,"[{""description"":""x"",""line_total"":""1.0""}]"\n',
        encoding="utf-8")
    (tmp_path / "coa.csv").write_text(
        "Account Name,Account Code,Account Type,Parent Account,Status\n"
        "Travel: Flights,E100-21,Expense,,Active\n", encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv", "account_id": "amex-usd", "legal_entity_id": "b",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount",
                           "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "zoho": {"coa_source": "csv", "coa_csv_path": "coa.csv",
                 "export_path": "zoho-journal.csv"},
        "coa_validation": {"org_id": _CORP_ORG},  # no chart_path
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"chart_path"):
        run(config_path)
