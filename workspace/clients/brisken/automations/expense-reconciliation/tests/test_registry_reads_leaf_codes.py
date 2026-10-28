"""A curated leaf code stored in the registry reaches a row.

#1236 taught the WRITE path both vocabularies: `normalize_merchants_setting`
runs `category_vocabulary.recognize`, so a leaf code saved through
`PUT /api/settings` is stored. The two READ paths kept filtering against the
eight buckets (`merchant_registry._match`, `categorize.apply_registry_category`),
so the same value came back None, the rule went inert, and the receipt fell
through to the LLM at full cost with no error and no log line. It looked
exactly like working software, which is why every assertion here runs THROUGH
a caller rather than through either filter.

The negative half is the point and is asserted too. A string from neither
vocabulary must still come back None, because that tolerance gate is what
keeps an invented category off a row; widening it to "anything truthy" would
trade a silent drop for a silent acceptance, which is the worse of the two.
"""
from __future__ import annotations

from decimal import Decimal

from expense_recon.categorize import (
    apply_registry_category,
    categorize_receipts_with_registry,
)
from expense_recon.matching.types import ClassificationSource, Receipt
from expense_recon.merchant_registry import MerchantRegistry
from expense_recon.zoho import curated_leaves

BCS = "697686691"
_ENTITY = "Cloud Services"


def _a_curated_code() -> str:
    """A real postable code, read from the compiled asset rather than typed.

    A hard-coded one would keep passing against a taxonomy that no longer
    contains it, which is the failure this whole change set is about.
    """
    return sorted(curated_leaves.postable_codes(BCS))[0]


def _registry(category):
    return MerchantRegistry(
        {"Anthropic": {"aliases": ["ANTHROPIC"], "category": category}}
    )


def _charge_receipt(doc_id="d1"):
    """No line items, so categorization takes the vendor-fallback path."""
    return Receipt(
        document_id=doc_id,
        legal_entity_id=_ENTITY,
        detected_date=None,
        detected_total=Decimal("20.00"),
        detected_currency="USD",
        detected_vendor="ANTHROPIC",
        line_items=(),
    )


# ── through MerchantRegistry.resolve, the caller of the filter ────────────


def test_resolve_returns_a_stored_leaf_code():
    code = _a_curated_code()

    match = _registry(code).resolve("ANTHROPIC", "ANTHROPIC")

    assert match is not None
    assert match.category == code


def test_resolve_still_returns_a_stored_bucket():
    match = _registry("Software & Subscriptions").resolve("ANTHROPIC", "ANTHROPIC")

    assert match is not None
    assert match.category == "Software & Subscriptions"


def test_resolve_drops_a_string_from_neither_vocabulary():
    match = _registry("Bogus Made Up Category").resolve("ANTHROPIC", "ANTHROPIC")

    assert match is not None
    assert match.category is None


def test_resolve_reduces_a_code_name_label_to_the_bare_code():
    """`"CODE name"` is the shape `llm_leaf_labels` emits and a client may
    echo back. Storing the label would make one account read as several."""
    code = _a_curated_code()
    name = curated_leaves.binding(code, BCS).name

    match = _registry(f"{code} {name}").resolve("ANTHROPIC", "ANTHROPIC")

    assert match is not None
    assert match.category == code


def test_resolve_never_recognises_a_bare_account_name():
    """Org-blind by design: the same name is a different account in a
    different entity, so a name must not resolve without one."""
    code = _a_curated_code()
    name = curated_leaves.binding(code, BCS).name

    match = _registry(name).resolve("ANTHROPIC", "ANTHROPIC")

    assert match is not None
    assert match.category is None


# ── through apply_registry_category, which stamps the row ─────────────────


def test_a_leaf_code_is_stamped_onto_the_row():
    code = _a_curated_code()

    stamped = apply_registry_category(
        _charge_receipt(), category=code, zoho_account=None, reasoning="registry"
    )

    assert stamped.line_items
    assert stamped.line_items[0].categorization.category == code


# ── through categorize_receipts_with_registry, the production entrance ────


def test_a_leaf_coded_merchant_is_decided_by_the_registry_not_the_model():
    """The measurable cost of the bug: `cat_docs` reads `m.category`, so a
    dropped leaf code put the receipt back in the batch the model classifies.
    `client=None` means any fall-through is visibly not a REGISTRY decision."""
    code = _a_curated_code()

    out, _ = categorize_receipts_with_registry(
        [_charge_receipt()], registry=_registry(code), client=None
    )

    cat = out[0].line_items[0].categorization
    assert cat.source is ClassificationSource.REGISTRY
    assert cat.category == code


def test_a_bucket_coded_merchant_still_is():
    out, _ = categorize_receipts_with_registry(
        [_charge_receipt()],
        registry=_registry("Software & Subscriptions"),
        client=None,
    )

    cat = out[0].line_items[0].categorization
    assert cat.source is ClassificationSource.REGISTRY
    assert cat.category == "Software & Subscriptions"


def test_an_unrecognised_category_is_not_stamped_as_a_registry_decision():
    out, _ = categorize_receipts_with_registry(
        [_charge_receipt()],
        registry=_registry("Bogus Made Up Category"),
        client=None,
    )

    cat = out[0].line_items[0].categorization if out[0].line_items else None
    assert cat is None or cat.category != "Bogus Made Up Category"
