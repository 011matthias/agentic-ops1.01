"""Chart-of-accounts ingest tests (slice 4.1).

Synthetic accounts only — Brisken's real chart is sensitive client
data and never lands in this repo. The shape (parent + leaf accounts,
a DO-NOT-USE marker, mixed account types) mirrors the real Zoho export
structure so the filters are exercised the way production data hits
them.
"""
from __future__ import annotations

import pytest

from expense_recon.ingest._common import StatementParseError
from expense_recon.ingest.chart_of_accounts import Account, ChartOfAccounts

# A small synthetic chart: one expense parent with two leaves, a
# retired leaf, an inactive leaf, a COGS leaf, and a non-expense bank
# account — every filter branch represented.
_API_RECORDS = [
    {"account_id": "1", "account_name": "Travel Expense", "account_code": "E100",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "2", "account_name": "Travel: Flights", "account_code": "E100-21",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "3", "account_name": "Travel: Hotels", "account_code": "E100-26",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "4", "account_name": "Lodging (DO NOT USE)", "account_code": "E100Z",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "5", "account_name": "Old Software", "account_code": "E200",
     "account_type": "expense", "parent_account_name": None, "is_active": False},
    {"account_id": "6", "account_name": "COGS Core", "account_code": "E700",
     "account_type": "cost_of_goods_sold", "parent_account_name": None, "is_active": True},
    {"account_id": "7", "account_name": "Business Checking", "account_code": "A100",
     "account_type": "bank", "parent_account_name": None, "is_active": True},
]


def _coa() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_API_RECORDS)


def test_from_api_loads_all_named_accounts():
    coa = _coa()
    assert len(coa) == 7
    assert coa.by_code("E100-21").name == "Travel: Flights"
    assert coa.by_code("E100-21").account_id == "2"


def test_from_api_skips_nameless_rows():
    coa = ChartOfAccounts.from_api(_API_RECORDS + [{"account_id": "9", "account_name": ""}])
    assert len(coa) == 7


def test_leaf_accounts_excludes_parents():
    coa = _coa()
    leaf_names = {a.name for a in coa.leaf_accounts()}
    assert "Travel Expense" not in leaf_names  # it is a parent
    assert {"Travel: Flights", "Travel: Hotels"} <= leaf_names


def test_postable_expense_accounts_applies_every_filter():
    coa = _coa()
    postable = {a.code for a in coa.postable_expense_accounts()}
    # Kept: the two travel leaves + the COGS leaf.
    assert postable == {"E100-21", "E100-26", "E700"}
    # Dropped: parent (E100), DO-NOT-USE (E100Z), inactive (E200),
    # and the bank account (A100, wrong type).


def test_postable_can_narrow_types_to_drop_cogs():
    coa = _coa()
    postable = {a.code for a in coa.postable_expense_accounts(types=["expense"])}
    assert postable == {"E100-21", "E100-26"}  # COGS now excluded


def test_resolve_by_code_then_name():
    coa = _coa()
    assert coa.resolve("E100-26").name == "Travel: Hotels"
    assert coa.resolve("Travel: Flights").code == "E100-21"
    assert coa.resolve("nonexistent") is None


def test_llm_labels_default_to_postable_set():
    coa = _coa()
    labels = coa.llm_account_labels()
    assert "E100-21 Travel: Flights" in labels
    assert all("DO NOT USE" not in label for label in labels)


def test_do_not_use_property():
    a = Account(name="Lodging (DO NOT USE)", code="X", account_type="expense")
    assert a.is_do_not_use is True


def test_from_csv_parses_export(tmp_path):
    csv_path = tmp_path / "coa.csv"
    csv_path.write_text(
        "Account Name,Account Code,Account Type,Parent Account,Status\n"
        "Travel Expense,E100,Expense,,Active\n"
        "Travel: Flights,E100-21,Expense,Travel Expense,Active\n"
        ",E999,Expense,,Active\n",  # nameless row skipped
        encoding="utf-8",
    )
    coa = ChartOfAccounts.from_csv(csv_path)
    assert len(coa) == 2
    assert coa.by_code("E100-21").parent_name == "Travel Expense"


def test_from_csv_missing_name_column_raises(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("Code,Type\nE100,Expense\n", encoding="utf-8")
    with pytest.raises(StatementParseError):
        ChartOfAccounts.from_csv(csv_path)
