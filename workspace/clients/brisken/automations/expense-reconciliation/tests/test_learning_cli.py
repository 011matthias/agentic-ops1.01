"""Escape-hatch tests (PR 2d): store-level forget/reset primitives and the
`expense-recon memory` CLI (list / forget / reset preview+apply), plus the
L2 `seed-zoho` command (seed merchant memory from Zoho Books posting
history)."""
from __future__ import annotations

from decimal import Decimal

import pytest

import expense_recon.learning_cli as learning_cli
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


# -- seed-zoho (L2) --------------------------------------------------------

ORG = "822741658"
ENTITY = "Corporate Services"

# The pinned ground truth: this record must seed zoho_account EXACTLY as
# posted and category "Software & Subscriptions" (keyword map on the
# account name).
_ANTHROPIC = {
    "vendor_name": "Anthropic",
    "account_name": "Other Infra and IT Costs for Cloud Business",
    "date": "2026-06-03",
}


class _FakeZohoClient:
    def __init__(self, expenses):
        self._expenses = expenses
        self.calls: list[tuple] = []

    def list_expenses(self, *, date_start=None, date_end=None):
        self.calls.append((date_start, date_end))
        return self._expenses


def _wire_zoho(monkeypatch, expenses):
    """Fake creds in env + a fake client behind the factory seam. Returns
    (fake client, list capturing the ZohoConfig the CLI built)."""
    monkeypatch.setenv("ZOHO_CLIENT_ID", "cid")
    monkeypatch.setenv("ZOHO_CLIENT_SECRET", "sec")
    monkeypatch.setenv("ZOHO_BOOKS_REFRESH_TOKEN", "books-tok")
    for var in ("ZOHO_REFRESH_TOKEN", "ZOHO_API_DOMAIN", "ZOHO_ACCOUNTS_DOMAIN", "ZOHO_DC"):
        monkeypatch.delenv(var, raising=False)
    fake = _FakeZohoClient(expenses)
    configs = []

    def factory(config):
        configs.append(config)
        return fake

    monkeypatch.setattr(learning_cli, "_make_zoho_client", factory)
    return fake, configs


def test_cli_seed_zoho_dry_run_writes_nothing(tmp_path, capsys, monkeypatch):
    db = tmp_path / "learning.sqlite"
    _wire_zoho(monkeypatch, [_ANTHROPIC])
    rc = memory_main(["seed-zoho", "--entity", ENTITY, "--org", ORG,
                      "--dry-run", "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "anthropic" in out
    assert "Software & Subscriptions" in out
    assert "nothing written" in out
    assert not db.exists()  # dry run never even opens the store


def test_cli_seed_zoho_seeds_unanimous_vendor(tmp_path, capsys, monkeypatch):
    db = tmp_path / "learning.sqlite"
    fake, configs = _wire_zoho(
        monkeypatch, [_ANTHROPIC, dict(_ANTHROPIC, date="2026-06-20")]
    )
    rc = memory_main(["seed-zoho", "--entity", ENTITY, "--org", ORG,
                      "--since", "2026-06-01", "--until", "2026-06-30",
                      "--db", str(db)])
    assert rc == 0
    assert "seeded 1" in capsys.readouterr().out
    with LearningStore(db) as s:
        got = s.get_merchant_category(ENTITY, normalize_vendor("Anthropic"))
    assert got is not None
    assert got.category == "Software & Subscriptions"
    assert got.zoho_account == "Other Infra and IT Costs for Cloud Business"
    assert got.source_run == f"zoho-seed:{ORG}"
    # the date window is handed to the client (which filters client-side)
    assert fake.calls == [("2026-06-01", "2026-06-30")]
    # env adaptation: --org wins, Books token preferred, EU domains derived
    cfg = configs[0]
    assert cfg.org_id == ORG
    assert cfg.refresh_token == "books-tok"
    assert cfg.api_domain == "https://www.zohoapis.eu"
    assert cfg.accounts_domain == "https://accounts.zoho.eu"


def test_cli_seed_zoho_skips_mixed_vendor(tmp_path, capsys, monkeypatch):
    db = tmp_path / "learning.sqlite"
    _wire_zoho(monkeypatch, [
        _ANTHROPIC,
        {"vendor_name": "Amazon", "account_name": "Office Supplies", "date": "2026-06-01"},
        {"vendor_name": "Amazon", "account_name": "Travel Expenses", "date": "2026-06-05"},
    ])
    rc = memory_main(["seed-zoho", "--entity", ENTITY, "--org", ORG, "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "skipped_mixed 1" in out
    assert "amazon" in out  # named so the operator sees what was ambiguous
    with LearningStore(db) as s:
        assert s.get_merchant_category(ENTITY, normalize_vendor("Amazon")) is None
        assert s.get_merchant_category(ENTITY, normalize_vendor("Anthropic")) is not None


def test_cli_seed_zoho_skips_unmapped_account_and_reports_it(tmp_path, capsys, monkeypatch):
    db = tmp_path / "learning.sqlite"
    _wire_zoho(monkeypatch, [
        {"vendor_name": "Some Vendor", "account_name": "Depreciation and Amortisation",
         "date": "2026-06-01"},
        {"account_name": "Travel Expenses", "date": "2026-06-02"},  # no vendor_name
    ])
    rc = memory_main(["seed-zoho", "--entity", ENTITY, "--org", ORG, "--db", str(db)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "seeded 0" in out
    assert "skipped_unmapped 1" in out
    assert "skipped_no_vendor 1" in out
    assert "Depreciation and Amortisation" in out  # operator extends the map
    with LearningStore(db) as s:
        assert s.get_merchant_category(ENTITY, normalize_vendor("Some Vendor")) is None


def test_seed_zoho_config_env_adaptation():
    # Generic token accepted when no Books token; ZOHO_DC drives the domains.
    cfg = learning_cli._zoho_config_from_env("111", env={
        "ZOHO_CLIENT_ID": "cid", "ZOHO_CLIENT_SECRET": "sec",
        "ZOHO_REFRESH_TOKEN": "generic-tok", "ZOHO_DC": "us",
    })
    assert cfg.refresh_token == "generic-tok"
    assert cfg.org_id == "111"
    assert cfg.api_domain == "https://www.zohoapis.com"
    assert cfg.accounts_domain == "https://accounts.zoho.com"
    # Explicit domains beat the DC derivation.
    cfg = learning_cli._zoho_config_from_env("111", env={
        "ZOHO_CLIENT_ID": "cid", "ZOHO_CLIENT_SECRET": "sec",
        "ZOHO_BOOKS_REFRESH_TOKEN": "b", "ZOHO_API_DOMAIN": "https://x.example",
        "ZOHO_ACCOUNTS_DOMAIN": "https://y.example",
    })
    assert cfg.api_domain == "https://x.example"
    assert cfg.accounts_domain == "https://y.example"
    # Missing creds named all at once.
    with pytest.raises(ValueError) as exc:
        learning_cli._zoho_config_from_env("111", env={})
    assert "ZOHO_CLIENT_ID" in str(exc.value)
    assert "ZOHO_BOOKS_REFRESH_TOKEN" in str(exc.value)


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
