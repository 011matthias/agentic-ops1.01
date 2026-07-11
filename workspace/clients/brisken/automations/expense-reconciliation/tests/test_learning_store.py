"""LearningStore unit tests (PR 2a) — schema, upserts, scoping, FX samples,
and the normalization-alignment invariant with the matcher."""
from __future__ import annotations

from decimal import Decimal

from expense_recon.learning import LearningStore, normalize_vendor
from expense_recon.matching.deterministic import _normalize


def _store(tmp_path) -> LearningStore:
    return LearningStore(tmp_path / "learning.sqlite")


def test_merchant_category_record_and_get(tmp_path):
    with _store(tmp_path) as s:
        s.record_merchant_category(
            "brisken-llc", "amazon", "Equipment & Hardware",
            "6420 - Office Equipment", "2026-04-01T00:00:00", "run-1",
        )
        got = s.get_merchant_category("brisken-llc", "amazon")
    assert got is not None
    assert got.category == "Equipment & Hardware"
    assert got.zoho_account == "6420 - Office Equipment"
    assert got.decision_count == 1
    assert got.source_run == "run-1"


def test_merchant_category_latest_wins_and_counts(tmp_path):
    with _store(tmp_path) as s:
        s.record_merchant_category(
            "brisken-llc", "amazon", "Equipment & Hardware", None, "t1", "run-1"
        )
        s.record_merchant_category(
            "brisken-llc", "amazon", "Office Supplies & Consumables", None, "t2", "run-2"
        )
        got = s.get_merchant_category("brisken-llc", "amazon")
    # Latest write wins on the category; the count is the audit trail.
    assert got.category == "Office Supplies & Consumables"
    assert got.decision_count == 2
    assert got.source_run == "run-2"


def test_merchant_category_scoped_by_legal_entity(tmp_path):
    with _store(tmp_path) as s:
        s.record_merchant_category("ent-a", "uber", "Travel & Transport", None, "t", "r")
        s.record_merchant_category("ent-b", "uber", "Professional Services", None, "t", "r")
        a = s.get_merchant_category("ent-a", "uber")
        b = s.get_merchant_category("ent-b", "uber")
        assert s.get_merchant_category("ent-c", "uber") is None
    assert a.category == "Travel & Transport"
    assert b.category == "Professional Services"


def test_vendor_alias_upsert_increments(tmp_path):
    with _store(tmp_path) as s:
        s.record_vendor_alias("brisken-llc", "mega cente constr", "mega center comercio", "t1", "r1")
        s.record_vendor_alias("brisken-llc", "mega cente constr", "mega center comercio", "t2", "r2")
        aliases = s.get_vendor_aliases("brisken-llc")
    assert len(aliases) == 1
    assert aliases[0].confirmed_count == 2
    assert aliases[0].receipt_vendor_norm == "mega center comercio"


def test_merchant_fx_samples_and_stats(tmp_path):
    with _store(tmp_path) as s:
        s.record_merchant_fx("brisken-llc", "hostaria", "EUR", "USD", Decimal("1.10"), "t1", "r1")
        s.record_merchant_fx("brisken-llc", "hostaria", "EUR", "USD", Decimal("1.20"), "t2", "r2")
        fx = s.get_merchant_fx("brisken-llc", "hostaria")
    assert len(fx) == 1
    row = fx[0]
    assert row.count == 2
    assert row.min == Decimal("1.10")
    assert row.max == Decimal("1.20")
    assert row.mean == Decimal("1.15")


def test_empty_store_returns_empty(tmp_path):
    with _store(tmp_path) as s:
        assert s.get_merchant_category("brisken-llc", "nope") is None
        assert s.all_merchant_categories() == []
        assert s.get_vendor_aliases() == []
        assert s.all_merchant_fx() == []


def test_normalize_vendor_matches_matcher(tmp_path):
    # The learned key MUST be computed the same way the matcher computes a
    # consult-time key, or 2c's lookups silently miss. Guard the invariant.
    for raw in ("MEGA CENTE CONSTR", "Coffee Shop NYC", "UBER * TRIP", "AMAZON.COM"):
        assert normalize_vendor(raw) == _normalize(raw)
