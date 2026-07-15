"""Sort-pass memory consult (PR 2b): a learned merchant->category upgrades
the weak vendor-fallback path to Tier-1 LEARNED, but never preempts a
confident line read. Plus the override audit-trail confirmation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.categorize import categorize_receipts
from expense_recon.learning import (
    LearningStore,
    MerchantCategory,
    MerchantCategoryLookup,
    normalize_vendor,
)
from expense_recon.matching.types import (
    ClassificationSource,
    LineItem,
    Receipt,
)

LE = "brisken-llc"


def _lookup(vendor, category, *, when="2026-05-01T00:00:00"):
    return MerchantCategoryLookup([
        MerchantCategory(LE, normalize_vendor(vendor), category, None, 1, when, "r1")
    ])


def _rcpt(vendor, line_items=()):
    return Receipt(
        document_id="d1", legal_entity_id=LE, detected_date=date(2026, 4, 1),
        detected_total=Decimal("10.00"), detected_currency="USD",
        detected_vendor=vendor, line_items=line_items,
    )


def _cat(receipt):
    return receipt.line_items[0].categorization


def test_thin_line_learned_merchant_promotes_to_tier1_learned():
    # "Bluebottle Consulting" is not in the keyword vendor map -> baseline
    # would be REVIEW. Memory upgrades it to a LEARNED Tier-1 category.
    r = _rcpt("Bluebottle Consulting")  # no line items
    out = categorize_receipts([r], client=None,
                              learned=_lookup("Bluebottle Consulting", "Professional Services"))
    cat = _cat(out[0])
    assert cat.category == "Professional Services"
    assert cat.source is ClassificationSource.LEARNED
    assert cat.confidence == 1.0
    assert "2026-05" in cat.reasoning  # provenance carries the month


def test_no_memory_leaves_thin_line_unchanged():
    r = _rcpt("Bluebottle Consulting")
    out = categorize_receipts([r], client=None, learned=None)
    # Unknown vendor, no memory -> REVIEW (today's behaviour).
    assert _cat(out[0]).source is ClassificationSource.REVIEW


def test_good_line_read_wins_over_conflicting_memory():
    # Receipt has a confident line ("Office chair" -> chair -> Equipment).
    # A conflicting learned mapping must NOT preempt it.
    r = _rcpt("Contoso Hardware", (LineItem(description="Office chair", line_total=Decimal("10.00")),))
    out = categorize_receipts([r], client=None,
                              learned=_lookup("Contoso Hardware", "Office Supplies & Consumables"))
    cat = _cat(out[0])
    assert cat.category == "Equipment & Hardware"
    assert cat.source is ClassificationSource.LINE


def test_empty_lookup_is_a_noop():
    r = _rcpt("Bluebottle Consulting")
    out = categorize_receipts([r], client=None, learned=MerchantCategoryLookup([]))
    assert _cat(out[0]).source is ClassificationSource.REVIEW


def test_zoho_seeded_hit_carries_books_history_provenance():
    # An L2-seeded row (source_run "zoho-seed:{org}") is a LEARNED Tier-1
    # hit whose reasoning names the Zoho Books posting history, not a
    # reviewer decision.
    lookup = MerchantCategoryLookup([
        MerchantCategory(
            LE, normalize_vendor("Anthropic"), "Software & Subscriptions",
            "Other Infra and IT Costs for Cloud Business", 1,
            "2026-07-15T00:00:00", "zoho-seed:822741658",
        )
    ])
    r = _rcpt("Anthropic")  # no line items -> weak path -> memory consult
    out = categorize_receipts([r], client=None, learned=lookup)
    cat = _cat(out[0])
    assert cat.source is ClassificationSource.LEARNED
    assert cat.category == "Software & Subscriptions"
    assert cat.zoho_account == "Other Infra and IT Costs for Cloud Business"
    assert cat.confidence == 1.0
    assert cat.reasoning == "from your Zoho Books posting history"


def test_override_recommit_updates_audit_trail(tmp_path):
    # The retrains loop: a reviewer override re-committed to memory is a
    # latest-wins upsert that bumps decision_count and moves last_confirmed.
    db = tmp_path / "learning.sqlite"
    with LearningStore(db) as s:
        s.record_merchant_category(LE, normalize_vendor("Acme"), "Meals & Entertainment",
                                   None, "2026-04-01T00:00:00", "run-apr")
        s.record_merchant_category(LE, normalize_vendor("Acme"), "Professional Services",
                                   None, "2026-05-01T00:00:00", "run-may")
        got = s.get_merchant_category(LE, normalize_vendor("Acme"))
    assert got.category == "Professional Services"   # latest wins
    assert got.decision_count == 2                    # audit trail accrues
    assert got.last_confirmed_at == "2026-05-01T00:00:00"
    assert got.source_run == "run-may"
