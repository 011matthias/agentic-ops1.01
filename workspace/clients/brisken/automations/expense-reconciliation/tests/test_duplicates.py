"""Duplicate / double-charge detection (Tier-1 #4)."""
from datetime import date
from decimal import Decimal

from expense_recon.duplicates import (
    find_duplicate_charges,
    find_duplicate_receipts,
)
from expense_recon.matching.types import Receipt, Transaction

LE = "le"


def tx(tid, amount, d, vendor="ACME", currency="USD"):
    return Transaction(
        transaction_id=tid,
        legal_entity_id=LE,
        account_id="card",
        transaction_date=d,
        posting_date=None,
        amount=Decimal(amount),
        transaction_currency=currency,
        account_card_currency="USD",
        vendor_from_statement=vendor,
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


def test_duplicate_charges_same_merchant_amount_within_window():
    txs = [tx("a", "20.00", date(2026, 4, 10)), tx("b", "20.00", date(2026, 4, 11))]
    assert find_duplicate_charges(txs, window_days=3) == [["a", "b"]]


def test_duplicate_charges_ignores_far_apart_recurring():
    # Same vendor + amount a month apart is a subscription, not a double-charge.
    txs = [tx("a", "9.99", date(2026, 4, 1)), tx("b", "9.99", date(2026, 5, 1))]
    assert find_duplicate_charges(txs, window_days=3) == []


def test_duplicate_charges_distinguish_amount_and_merchant():
    txs = [
        tx("a", "20.00", date(2026, 4, 10)),
        tx("b", "21.00", date(2026, 4, 10)),               # different amount
        tx("c", "20.00", date(2026, 4, 10), vendor="OTHER"),  # different vendor
    ]
    assert find_duplicate_charges(txs) == []


def test_duplicate_charges_skips_dateless_amountless():
    txs = [
        Transaction(
            transaction_id="a", legal_entity_id=LE, account_id="card",
            transaction_date=date(2026, 4, 10), posting_date=None,
            amount=None, transaction_currency="USD",
            account_card_currency="USD", vendor_from_statement="ACME",
        ),
        tx("b", "20.00", date(2026, 4, 10)),
    ]
    # The amountless one is skipped; a single remaining charge is not a dup.
    assert find_duplicate_charges(txs) == []


def test_duplicate_receipts_same_fields_distinct_ids():
    rs = [rc("r1", "30.00", date(2026, 4, 5)), rc("r2", "30.00", date(2026, 4, 5))]
    assert find_duplicate_receipts(rs) == [["r1", "r2"]]


def test_duplicate_receipts_single_not_flagged():
    rs = [rc("r1", "30.00", date(2026, 4, 5)), rc("r2", "31.00", date(2026, 4, 5))]
    assert find_duplicate_receipts(rs) == []
