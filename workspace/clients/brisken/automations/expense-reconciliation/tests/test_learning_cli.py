"""Escape-hatch tests (PR 2d): store-level forget/reset primitives and the
`expense-recon memory` CLI (list / forget / reset preview+apply), plus the
`set` command that authors a standing vendor rule.

The `seed-zoho` importer and its tests were removed 2026-08-22 with the rest
of the accounting-API connection.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from expense_recon.learning import LearningStore, normalize_vendor
from expense_recon.learning_cli import main as memory_main

LE = "brisken-llc"


def _seed(db):
    with LearningStore(db) as s:
        s.record_merchant_category(LE, normalize_vendor("Coffee Shop NYC"),
                                   "Meals & Entertainment", None, "t", "r1")
        s.record_vendor_alias(LE, normalize_vendor("COFFEE SHOP NYC"),
                              normalize_vendor("Coffee Shop NYC"), "t", "r1")
        s.record_merchant_fx(LE, normalize_vendor("Hostaria"), "EUR", "USD",
                             Decimal("1.16"), "t", "r1")
        s.record_merchant_category("other-ent", normalize_vendor("Amazon"),
                                   "Equipment & Hardware", None, "t", "r1")


# -- store primitives -----------------------------------------------------

def test_forget_vendor_clears_all_three_tables(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with LearningStore(db) as s:
        counts = s.forget_vendor(LE, normalize_vendor("Coffee Shop NYC"))
        assert s.get_merchant_category(LE, normalize_vendor("Coffee Shop NYC")) is None
        assert s.get_vendor_aliases(LE) == []  # matched on either side
    assert counts == {
        "merchant_category": 1, "vendor_alias": 1, "merchant_fx": 0,
        "merchant_entity": 0, "field_correction": 0,
    }


def test_reset_scoped_by_entity_and_table(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with LearningStore(db) as s:
        s.reset(table="merchant_category", legal_entity_id=LE)
        # only brisken-llc's category went; the other entity's stays.
        assert s.get_merchant_category(LE, normalize_vendor("Coffee Shop NYC")) is None
        assert s.get_merchant_category("other-ent", normalize_vendor("Amazon")) is not None
        assert s.get_vendor_aliases(LE)  # untouched table


def test_reset_all_clears_everything(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with LearningStore(db) as s:
        s.reset()
        assert s.count_rows() == {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
            "merchant_entity": 0, "field_correction": 0,
        }


def test_reset_rejects_unknown_table(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with LearningStore(db) as s:
        with pytest.raises(ValueError):
            s.reset(table="bogus")


# -- CLI surface ----------------------------------------------------------

def test_cli_list_empty(tmp_path, capsys):
    rc = memory_main(["list", "--db", str(tmp_path / "nope.sqlite")])
    assert rc == 0
    assert "no learned memory yet" in capsys.readouterr().out


def test_cli_list_shows_rows(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    rc = memory_main(["list", "--db", str(db), "--entity", LE])
    assert rc == 0
    out = capsys.readouterr().out
    assert "coffee shop nyc" in out
    assert "Meals & Entertainment" in out
    assert "EUR->USD" in out


def test_cli_forget_removes_vendor(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    rc = memory_main(["forget", "Coffee Shop NYC", "--db", str(db), "--entity", LE])
    assert rc == 0
    assert "forgot 'coffee shop nyc'" in capsys.readouterr().out
    with LearningStore(db) as s:
        assert s.get_merchant_category(LE, normalize_vendor("Coffee Shop NYC")) is None


def test_cli_forget_requires_entity(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    rc = memory_main(["forget", "Coffee Shop NYC", "--db", str(db)])
    assert rc == 2
    assert "needs --entity" in capsys.readouterr().err


def test_cli_reset_preview_then_apply(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    # Preview: reports counts, deletes nothing.
    rc = memory_main(["reset", "--db", str(db)])
    assert rc == 0
    assert "re-run with --yes" in capsys.readouterr().out
    with LearningStore(db) as s:
        assert s.count_rows()["merchant_category"] == 2
    # Apply.
    rc = memory_main(["reset", "--db", str(db), "--yes"])
    assert rc == 0
    with LearningStore(db) as s:
        assert s.count_rows() == {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
            "merchant_entity": 0, "field_correction": 0,
        }


def test_cli_reset_invalid_table_rejected(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with pytest.raises(SystemExit):  # argparse choices guard
        memory_main(["reset", "--db", str(db), "--table", "bogus"])


# -- set (Slice 10): author a standing vendor -> category/account rule ----

def test_cli_set_authors_standing_rule(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    rc = memory_main([
        "set", "Anthropic",
        "--entity", LE,
        "--category", "Software & Subscriptions",
        "--account", "Other Infra and IT Costs for Cloud Business",
        "--db", str(db),
    ])
    assert rc == 0
    with LearningStore(db) as s:
        row = s.get_merchant_category(LE, normalize_vendor("Anthropic"))
    assert row is not None
    assert row.category == "Software & Subscriptions"
    assert row.zoho_account == "Other Infra and IT Costs for Cloud Business"
    assert row.source_run == "manual-set"
    out = capsys.readouterr().out
    assert "Software & Subscriptions" in out


def test_cli_set_rejects_unknown_category(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    rc = memory_main([
        "set", "Anthropic", "--entity", LE,
        "--category", "Not A Real Category", "--db", str(db),
    ])
    assert rc == 2
    assert not db.exists()  # nothing written on a rejected rule
    err = capsys.readouterr().err
    assert "Software & Subscriptions" in err  # the valid list is shown


def test_cli_set_without_account_warns_but_writes(tmp_path, capsys):
    db = tmp_path / "learning.sqlite"
    rc = memory_main([
        "set", "Anthropic", "--entity", LE,
        "--category", "Software & Subscriptions", "--db", str(db),
    ])
    assert rc == 0
    with LearningStore(db) as s:
        row = s.get_merchant_category(LE, normalize_vendor("Anthropic"))
    assert row is not None and row.zoho_account is None
    assert "no --account" in capsys.readouterr().out


def test_cli_set_then_charge_categorizer_recalls_it(tmp_path):
    """The end-to-end loop the command exists for: a manual rule set today
    is recalled as Tier-1 LEARNED by the receiptless-charge path."""
    from datetime import date

    from expense_recon.categorize_charges import categorize_charges
    from expense_recon.learning import MerchantCategoryLookup
    from expense_recon.matching.types import (
        ClassificationSource,
        MatchOutcome,
        Transaction,
    )

    db = tmp_path / "learning.sqlite"
    assert memory_main([
        "set", "Anthropic", "--entity", LE,
        "--category", "Software & Subscriptions",
        "--account", "Other Infra and IT Costs for Cloud Business",
        "--db", str(db),
    ]) == 0

    tx = Transaction(
        transaction_id="t1", legal_entity_id=LE, account_id="chase-2838",
        transaction_date=date(2026, 4, 7), posting_date=None,
        amount=Decimal("20.00"), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement="ANTHROPIC",
    )
    cats = categorize_charges(
        MatchOutcome(unmatched_transactions=["t1"]), [tx],
        learned=MerchantCategoryLookup.from_db_path(db),
    )
    cat = cats["t1"]
    assert cat.source is ClassificationSource.LEARNED
    assert cat.zoho_account == "Other Infra and IT Costs for Cloud Business"
