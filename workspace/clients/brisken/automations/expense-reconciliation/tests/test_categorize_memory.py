"""Sort-pass memory consult (PR 2b): a learned merchant->category upgrades
the weak vendor-fallback path to Tier-1 LEARNED. Since item 115 it also
applies to a receipt WITH line items when a person taught the rule, and
says so when the line read disagreed; a Zoho-seeded row nobody validated
still stays below a confident line read. Plus the override audit-trail
confirmation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from expense_recon.categorize import (
    DECISION_LEARNED_OVER_LINE,
    categorize_receipts,
)
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


def _lookup(vendor, category, *, when="2026-05-01T00:00:00", source="r1",
            entity=LE, validated=None):
    return MerchantCategoryLookup([
        MerchantCategory(
            entity, normalize_vendor(vendor), category, None, 1, when, source,
            validated_at=validated,
        )
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


def test_a_correction_beats_a_line_read_and_the_row_says_so():
    # Item 115. The receipt has a confident line ("Office chair" -> chair ->
    # Equipment) and a person taught this merchant a different category. Her
    # correction wins -- that is the whole promise of saving it -- and the
    # row carries the flag that asks for a glance, with what the items read.
    r = _rcpt("Contoso Hardware", (LineItem(description="Office chair", line_total=Decimal("10.00")),))
    out = categorize_receipts([r], client=None,
                              learned=_lookup("Contoso Hardware", "Office Supplies & Consumables"))
    cat = _cat(out[0])
    assert cat.category == "Office Supplies & Consumables"
    assert cat.source is ClassificationSource.LEARNED
    assert cat.decision == DECISION_LEARNED_OVER_LINE
    assert "Equipment & Hardware" in cat.reasoning


def test_an_agreeing_line_read_leaves_no_flag():
    r = _rcpt("Contoso Hardware", (LineItem(description="Office chair", line_total=Decimal("10.00")),))
    out = categorize_receipts([r], client=None,
                              learned=_lookup("Contoso Hardware", "Equipment & Hardware"))
    cat = _cat(out[0])
    assert cat.source is ClassificationSource.LEARNED
    assert cat.decision is None


def test_a_validated_rule_needs_no_line_read_at_all():
    # A person certified this answer on the Memory page, so the line read is
    # not bought and the row asks for no glance.
    r = _rcpt("Contoso Hardware", (LineItem(description="Office chair", line_total=Decimal("10.00")),))
    lookup = _lookup(
        "Contoso Hardware", "Office Supplies & Consumables",
        validated="2026-06-01T00:00:00",
    )
    out = categorize_receipts([r], client=None, learned=lookup)
    cat = _cat(out[0])
    assert cat.category == "Office Supplies & Consumables"
    assert cat.decision is None


def test_a_zoho_seeded_row_still_stays_below_a_line_read():
    # The Zoho seed is how the books posted, not what a person said about
    # this merchant, and no live row has been validated. Left as it was,
    # pending the owner's ruling (item 115).
    r = _rcpt("Contoso Hardware", (LineItem(description="Office chair", line_total=Decimal("10.00")),))
    lookup = _lookup(
        "Contoso Hardware", "Office Supplies & Consumables",
        source="zoho-seed:822741658",
    )
    out = categorize_receipts([r], client=None, learned=lookup)
    cat = _cat(out[0])
    assert cat.category == "Equipment & Hardware"
    assert cat.source is ClassificationSource.LINE


def test_a_rule_saved_with_no_company_reaches_a_receipt_that_has_one():
    # Item 115 hole 2: a month's corrections are saved under the company the
    # expense carried, and most carry none. Without this the 11 rules a live
    # sign-off writes would reach no row whose card names a company.
    r = _rcpt("Contoso Hardware")  # no line items
    out = categorize_receipts([r], client=None,
                              learned=_lookup("Contoso Hardware", "Professional Services", entity=""))
    cat = _cat(out[0])
    assert cat.source is ClassificationSource.LEARNED
    assert cat.category == "Professional Services"
    assert "no company" in cat.reasoning


def test_a_company_less_receipt_takes_the_vendors_rules_when_they_agree():
    rows = [
        MerchantCategory("Cloud Services", normalize_vendor("Contoso"),
                         "Software & Subscriptions", "COGS - Infra", 1,
                         "2026-05-01T00:00:00", "r1"),
        MerchantCategory("Corporate Services", normalize_vendor("Contoso"),
                         "Software & Subscriptions", "IT: Cloud Subs", 1,
                         "2026-05-01T00:00:00", "r2"),
    ]
    r = Receipt(
        document_id="d1", legal_entity_id="", detected_date=date(2026, 4, 1),
        detected_total=Decimal("10.00"), detected_currency="USD",
        detected_vendor="Contoso", line_items=(),
    )
    cat = _cat(categorize_receipts([r], client=None,
                                   learned=MerchantCategoryLookup(rows))[0])
    assert cat.category == "Software & Subscriptions"
    assert cat.source is ClassificationSource.LEARNED
    # Two companies' charts, two account names: no account is carried.
    assert cat.zoho_account is None
    assert "Cloud Services" in cat.reasoning and "Corporate Services" in cat.reasoning


def test_rules_that_disagree_decide_nothing_for_a_company_less_receipt():
    rows = [
        MerchantCategory("Cloud Services", normalize_vendor("Contoso"),
                         "Software & Subscriptions", None, 1, "t", "r1"),
        MerchantCategory("Corporate Services", normalize_vendor("Contoso"),
                         "Marketing & Advertising", None, 1, "t", "r2"),
    ]
    r = Receipt(
        document_id="d1", legal_entity_id="", detected_date=date(2026, 4, 1),
        detected_total=Decimal("10.00"), detected_currency="USD",
        detected_vendor="Contoso", line_items=(),
    )
    cat = _cat(categorize_receipts([r], client=None,
                                   learned=MerchantCategoryLookup(rows))[0])
    assert cat.source is ClassificationSource.REVIEW


def test_empty_lookup_is_a_noop():
    r = _rcpt("Bluebottle Consulting")
    out = categorize_receipts([r], client=None, learned=MerchantCategoryLookup([]))
    assert _cat(out[0]).source is ClassificationSource.REVIEW


def test_zoho_seeded_hit_carries_books_history_provenance():
    # An L2-seeded row (source_run "zoho-seed:{org}") is a LEARNED Tier-1
    # hit whose reasoning names the earlier posting history, not a
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
    assert cat.reasoning == "from your earlier posting history"


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
