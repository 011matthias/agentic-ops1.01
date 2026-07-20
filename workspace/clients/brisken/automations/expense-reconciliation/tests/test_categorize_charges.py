"""Slice 10: receiptless-charge categorization + Slice 11 subscription
derivation. The charge path is a side-map ANNOTATION: buckets never
change, pseudo-receipts never reach the matcher, and LEARNED beats the
vendor keyword table (never LINE — a statement Description is not a
line item)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.categorize_charges import (
    build_charge_pseudo_receipt,
    categorize_charges,
    derive_subscription_status,
)
from expense_recon.learning import (
    MerchantCategory,
    MerchantCategoryLookup,
    normalize_vendor,
)
from expense_recon.matching.types import (
    ClassificationSource,
    Match,
    MatchOutcome,
    MatchType,
    Transaction,
)
from expense_recon.store import StatementStore

LE = "brisken-llc"


def _tx(tid, vendor, *, amount="20.00", day=7, month=4, entry_status=None):
    return Transaction(
        transaction_id=tid, legal_entity_id=LE, account_id="chase-2838",
        transaction_date=date(2026, month, day), posting_date=None,
        amount=Decimal(amount), transaction_currency="USD",
        account_card_currency="USD", vendor_from_statement=vendor,
        entry_status=entry_status,
    )


def _lookup(vendor, category, account=None):
    return MerchantCategoryLookup([
        MerchantCategory(
            LE, normalize_vendor(vendor), category, account, 1,
            "2026-05-01T00:00:00", "manual-set",
        )
    ])


def test_pseudo_receipt_shape_forces_vendor_fallback():
    rec = build_charge_pseudo_receipt(_tx("t1", "ANTHROPIC"))
    assert rec.document_id == "charge:t1"
    assert rec.line_items == ()          # empty => never the LINE tier
    assert rec.detected_vendor == "ANTHROPIC"
    assert rec.detected_total == Decimal("20.00")
    assert rec.detected_currency == "USD"
    assert rec.legal_entity_id == LE


def test_learned_rule_wins_and_carries_the_books_account():
    outcome = MatchOutcome(unmatched_transactions=["t1"])
    cats = categorize_charges(
        outcome, [_tx("t1", "ANTHROPIC")],
        learned=_lookup(
            "ANTHROPIC", "Software & Subscriptions",
            "Other Infra and IT Costs for Cloud Business",
        ),
    )
    cat = cats["t1"]
    assert cat.source is ClassificationSource.LEARNED
    assert cat.category == "Software & Subscriptions"
    assert cat.zoho_account == "Other Infra and IT Costs for Cloud Business"
    assert cat.confidence == 1.0


def test_vendor_keyword_fallback_without_memory():
    outcome = MatchOutcome(unmatched_transactions=["t1"])
    cats = categorize_charges(outcome, [_tx("t1", "ANTHROPIC")])
    cat = cats["t1"]
    assert cat.source is ClassificationSource.VENDOR
    assert cat.category == "Software & Subscriptions"
    assert cat.zoho_account is None      # a guess carries no posting account


def test_unknown_vendor_stays_review_with_no_invented_category():
    outcome = MatchOutcome(unmatched_transactions=["t1"])
    cats = categorize_charges(outcome, [_tx("t1", "ZZQXW LLC")])
    assert cats["t1"].source is ClassificationSource.REVIEW
    assert cats["t1"].category is None


def test_only_unmatched_transactions_are_categorized_and_buckets_untouched():
    outcome = MatchOutcome(
        matches=[Match("t1", "r1", MatchType.EXACT, 0.99, "x", False)],
        unmatched_transactions=["t2"],
    )
    txs = [_tx("t1", "UBER"), _tx("t2", "ADOBE")]
    cats = categorize_charges(outcome, txs)
    assert set(cats) == {"t2"}
    # Annotation only: the outcome's buckets are exactly what they were.
    assert [m.transaction_id for m in outcome.matches] == ["t1"]
    assert outcome.unmatched_transactions == ["t2"]
    assert outcome.unmatched_receipts == []
    assert outcome.judgment_required == []
    assert outcome.ambiguous == []


def test_unknown_tx_id_is_skipped_defensively():
    outcome = MatchOutcome(unmatched_transactions=["ghost"])
    assert categorize_charges(outcome, [_tx("t1", "ADOBE")]) == {}


# ── Slice 11: subscription derivation from statement history ─────────


def _seed_store(db_path, months, vendor="ANTHROPIC"):
    """One charge per given month in the store (prior history)."""
    txs = [
        _tx(f"h{i}", vendor, month=m, day=5) for i, m in enumerate(months)
    ]
    with StatementStore(db_path) as store:
        store.ingest_transactions(txs, statement_id=f"hist:{vendor}")


def test_vendor_recurring_two_prior_months_derives_subscription(tmp_path):
    db = tmp_path / "statements.sqlite"
    _seed_store(db, months=[2, 3])
    current = _tx("t1", "ANTHROPIC", month=4)
    with StatementStore(db) as store:
        out = derive_subscription_status([current], store)
    assert out[0].entry_status == "subscription"
    assert out[0].transaction_id == "t1"    # same tx, annotated copy


def test_one_prior_month_is_not_enough(tmp_path):
    db = tmp_path / "statements.sqlite"
    _seed_store(db, months=[3])
    with StatementStore(db) as store:
        out = derive_subscription_status([_tx("t1", "ANTHROPIC", month=4)], store)
    assert out[0].entry_status is None


def test_same_month_rows_never_count_as_prior(tmp_path):
    # A prior identical run put THIS month's rows in the store; they must
    # not self-derive a subscription on the re-run.
    db = tmp_path / "statements.sqlite"
    _seed_store(db, months=[4, 4])
    with StatementStore(db) as store:
        out = derive_subscription_status([_tx("t1", "ANTHROPIC", month=4)], store)
    assert out[0].entry_status is None


def test_fill_and_operator_precedence_over_derived(tmp_path):
    db = tmp_path / "statements.sqlite"
    _seed_store(db, months=[2, 3])
    posted = _tx("t1", "ANTHROPIC", month=4, entry_status="posted")
    with StatementStore(db) as store:
        out = derive_subscription_status([posted], store)
    assert out[0].entry_status == "posted"  # her yellow fill wins
