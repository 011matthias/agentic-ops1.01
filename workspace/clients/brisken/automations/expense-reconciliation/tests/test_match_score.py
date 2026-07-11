"""Graded 0-100 triage score (Tier-1 #1).

The score blends amount agreement, date proximity, and fuzzy vendor
similarity. It orders the review workbench (weakest first) and never
changes which bucket a pair lands in; the bucket assertions live in
test_deterministic_matching.py and stay green.
"""
from datetime import date
from decimal import Decimal

from expense_recon.matching.deterministic import match_month
from expense_recon.matching.types import MatchType, Receipt, Transaction

LE = "brisken-us"


def tx(tid, amount, d, vendor="VENDOR", currency="USD"):
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


def receipt(rid, amount, d, vendor="VENDOR", currency="USD"):
    return Receipt(
        document_id=rid,
        legal_entity_id=LE,
        detected_date=d,
        detected_total=Decimal(amount) if amount else None,
        detected_currency=currency,
        detected_vendor=vendor,
    )


def test_exact_match_with_matching_vendor_scores_high():
    out = match_month(
        [tx("t1", "42.50", date(2026, 4, 12), vendor="STARBUCKS 412")],
        [receipt("r1", "42.50", date(2026, 4, 12), vendor="Starbucks")],
    )
    m = out.matches[0]
    assert m.match_type == MatchType.EXACT
    assert m.score >= 90


def test_score_is_bounded_0_100():
    out = match_month(
        [tx("t1", "57.50", date(2026, 4, 22), vendor="A")],
        [receipt("r1", "50.00", date(2026, 4, 26), vendor="Z")],
    )
    m = out.matches[0]
    assert 0 <= m.score <= 100


def test_strong_match_outscores_weak_match():
    strong = match_month(
        [tx("s", "50.00", date(2026, 4, 12), vendor="HILTON HOTELS")],
        [receipt("rs", "50.00", date(2026, 4, 12), vendor="Hilton")],
    ).matches[0]
    weak = match_month(
        [tx("w", "50.00", date(2026, 4, 12), vendor="UNKNOWN CO")],
        [receipt("rw", "57.00", date(2026, 4, 16), vendor="totally different")],
    ).matches[0]
    assert strong.score > weak.score


def test_fx_candidate_carries_a_score():
    out = match_month(
        [tx("t1", "112.30", date(2026, 4, 15), vendor="HOTEL ROMA")],
        [receipt("r1", "100.00", date(2026, 4, 15), currency="EUR", vendor="Hotel Roma")],
    )
    assert out.judgment_required
    assert 0 < out.judgment_required[0].score <= 100
