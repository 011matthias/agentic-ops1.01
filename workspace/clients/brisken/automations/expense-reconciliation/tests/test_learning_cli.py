"""Escape-hatch tests (PR 2d): store-level forget/reset primitives and the
`expense-recon memory` CLI (list / forget / reset preview+apply)."""
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
    assert counts == {"merchant_category": 1, "vendor_alias": 1, "merchant_fx": 0}


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
        assert s.count_rows() == {"merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0}


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
        assert s.count_rows() == {"merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0}


def test_cli_reset_invalid_table_rejected(tmp_path):
    db = tmp_path / "learning.sqlite"
    _seed(db)
    with pytest.raises(SystemExit):  # argparse choices guard
        memory_main(["reset", "--db", str(db), "--table", "bogus"])
