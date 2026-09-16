"""Duplicate receipt detection (Tier-1 #4). Charge-side detection was deleted
in item 74 (owner ruling 2026-09-15: two charges to one vendor are two
charges); `tests/test_web_duplicates.py` pins that at the route."""
from datetime import date
from decimal import Decimal

from expense_recon import duplicates
from expense_recon.duplicates import (
    duplicate_group_id,
    find_duplicate_receipts,
)
from expense_recon.matching.types import Receipt

LE = "le"


# ── §18 stable group id ──────────────────────────────────────────────


def test_group_id_is_member_order_independent():
    assert duplicate_group_id("receipt", ["t2", "t1"]) == duplicate_group_id(
        "receipt", ["t1", "t2"]
    )


def test_group_id_is_kind_scoped():
    """A charge-kind id and a receipt-kind id with the same member ids
    differ, so a resolution saved before item 74 on a charge group can never
    land on a receipt group."""
    assert duplicate_group_id("charge", ["a", "b"]) != duplicate_group_id(
        "receipt", ["a", "b"]
    )


def test_group_id_distinguishes_membership():
    assert duplicate_group_id("receipt", ["a", "b"]) != duplicate_group_id(
        "receipt", ["a", "c"]
    )


def rc(rid, amount, d, vendor="ACME", currency="USD"):
    return Receipt(
        document_id=rid,
        legal_entity_id=LE,
        detected_date=d,
        detected_total=Decimal(amount) if amount else None,
        detected_currency=currency,
        detected_vendor=vendor,
    )


def test_the_charge_detector_is_gone():
    assert not hasattr(duplicates, "find_duplicate_charges")


def test_duplicate_receipts_same_fields_distinct_ids():
    rs = [rc("r1", "30.00", date(2026, 4, 5)), rc("r2", "30.00", date(2026, 4, 5))]
    assert find_duplicate_receipts(rs) == [["r1", "r2"]]


def test_duplicate_receipts_single_not_flagged():
    rs = [rc("r1", "30.00", date(2026, 4, 5)), rc("r2", "31.00", date(2026, 4, 5))]
    assert find_duplicate_receipts(rs) == []
