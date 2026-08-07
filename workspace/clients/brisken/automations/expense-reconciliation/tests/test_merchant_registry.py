"""Canonical merchant registry (2026-07-29): the deterministic resolver, the
vendor-name cleaner, the settings validator, and the seed clustering. Pure
units — no web, no model, no network."""
from __future__ import annotations

import pytest

from expense_recon.matching.types import Receipt
from expense_recon.merchant_registry import (
    MerchantRegistry,
    normalize_merchants_setting,
)
from expense_recon.seed_registry import (
    build_merchants,
    cluster_receipts,
    label_to_bucket,
)
from expense_recon.vendor_names import clean_vendor_name


# ── vendor_names.clean_vendor_name ──────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MEGA CENTE CONSTR LTDA", "MEGA CENTE CONSTR"),
        ("Padaria Estrela Comercio de Alimentos Ltda", "Padaria Estrela"),
        ("X Industria e Comercio Ltda", "X"),
        ("Acme GmbH", "Acme"),
        ("Uber B.V.", "Uber"),
        ("OpenAI, Inc.", "OpenAI"),
        ("Ltda", "Ltda"),          # only-a-legal-form never vanishes
        ("   ", None),
        (None, None),
    ],
)
def test_clean_vendor_name(raw, expected):
    assert clean_vendor_name(raw) == expected


# ── MerchantRegistry.resolve ────────────────────────────────────────


@pytest.fixture
def registry():
    return MerchantRegistry({
        "Uber": {
            "aliases": ["UBER *EATS", "UBER BV"],
            "category": "Travel & Transport",
            "zoho_account": "E100010 - Travel Expense",
        },
        "Padaria Estrela": {
            "aliases": ["PADARIA ESTRELA COMERCIO DE ALIMENTOS LTDA"],
            "category": "Meals & Entertainment",
            "zoho_account": None,
        },
        "OpenAI": {
            "aliases": ["OPENAI INC", "OPENAI, INC."],
            "category": "Software & Subscriptions",
            "zoho_account": None,
        },
    })


def test_resolve_exact_alias(registry):
    m = registry.resolve("Uber Eats", "UBER   *EATS")
    assert m is not None
    assert m.canonical_name == "Uber" and m.kind == "exact" and m.score == 100.0
    assert m.category == "Travel & Transport"
    assert m.zoho_account == "E100010 - Travel Expense"
    assert m.source == "registry"


def test_resolve_exact_canonical(registry):
    m = registry.resolve(None, "OpenAI")
    assert m is not None and m.canonical_name == "OpenAI" and m.kind == "exact"


def test_resolve_via_deterministic_clean_probe(registry):
    # No vendor_clean; the raw carries the full legal name -> the resolver's
    # own clean_vendor_name probe recovers "Padaria Estrela".
    m = registry.resolve(None, "PADARIA ESTRELA COMERCIO DE ALIMENTOS LTDA")
    assert m is not None and m.canonical_name == "Padaria Estrela"


def test_resolve_fuzzy_ocr_variant(registry):
    m = registry.resolve("OpenAl Inc", None)  # lowercase-L OCR slip
    assert m is not None and m.canonical_name == "OpenAI" and m.kind == "fuzzy"
    assert m.score >= registry.threshold


def test_resolve_unrelated_is_unmatched(registry):
    assert registry.resolve("Deutsche Bahn", "DB VERTRIEB GMBH") is None


def test_empty_registry_is_a_noop():
    empty = MerchantRegistry({})
    assert not empty and len(empty) == 0
    assert empty.resolve("Uber", "Uber") is None
    assert MerchantRegistry(None).resolve("x", "y") is None


def test_threshold_is_configurable():
    strict = MerchantRegistry(
        {"OpenAI": {"aliases": ["OPENAI INC"]}}, threshold=99.5
    )
    # A fuzzy variant that clears the default 88 no longer clears 99.5.
    assert strict.resolve("0PENAI 1NC", None) is None


def test_resolve_is_deterministic(registry):
    a = registry.resolve("OpenAl Inc", None)
    b = registry.resolve("OpenAl Inc", None)
    assert (a.canonical_name, a.score) == (b.canonical_name, b.score)


def test_from_settings():
    reg = MerchantRegistry.from_settings({"merchants": {"Uber": {"aliases": []}}})
    assert reg.resolve(None, "Uber").canonical_name == "Uber"
    assert not MerchantRegistry.from_settings({})
    assert not MerchantRegistry.from_settings(None)


# ── normalize_merchants_setting ─────────────────────────────────────


def test_normalize_drops_blank_and_dedupes_aliases():
    out = normalize_merchants_setting({
        "  ": {"aliases": ["x"]},                       # blank canonical dropped
        "Uber": {"aliases": ["a", "a", "A", "", " UBER "],
                 "category": "Travel & Transport", "zoho_account": " E1 "},
    })
    assert "  " not in out and set(out) == {"Uber"}
    # 'a'/'A' collapse on the normalized key; ' UBER ' trims to 'UBER'.
    assert out["Uber"]["aliases"] == ["a", "UBER"]
    assert out["Uber"]["zoho_account"] == "E1"


def test_normalize_rejects_bad_category():
    with pytest.raises(ValueError):
        normalize_merchants_setting({"X": {"category": "Not A Category"}})


def test_normalize_rejects_non_dict_entry():
    with pytest.raises(ValueError):
        normalize_merchants_setting({"X": "nope"})


def test_normalize_none_and_empty():
    assert normalize_merchants_setting(None) == {}
    assert normalize_merchants_setting({}) == {}


# ── seed_registry ───────────────────────────────────────────────────


def _r(vendor, zoho=None):
    return Receipt(
        document_id="d", legal_entity_id="e", detected_date=None,
        detected_total=None, detected_currency=None,
        detected_vendor=vendor, zoho_category=zoho,
    )


@pytest.mark.parametrize(
    "label,bucket",
    [
        ("E100010 - Travel Expense", "Travel & Transport"),
        ("E100020 - Meals & Ent", "Meals & Entertainment"),
        ("Software Subscriptions", "Software & Subscriptions"),
        ("E999 - Mystery", None),
        (None, None),
    ],
)
def test_label_to_bucket(label, bucket):
    assert label_to_bucket(label) == bucket


def test_cluster_merges_variants_but_not_distinct_brands():
    recs = [
        _r("OPENAI, INC.", "Software Subscriptions"),
        _r("OPENAI INC", "Software Subscriptions"),
        _r("UBER EATS", "Meals"),   # different brand from OpenAI, stays apart
    ]
    clusters = cluster_receipts(recs)
    canon = {c["canonical"] for c in clusters}
    # Canonical keeps the source casing (no risky auto-title-casing that would
    # turn "OpenAI" into "Openai"); the owner refines display in the editor.
    assert "OPENAI" in canon
    openai = next(c for c in clusters if c["canonical"] == "OPENAI")
    assert openai["count"] == 2 and "OPENAI INC" in openai["aliases"]
    assert openai["category"] == "Software & Subscriptions"


def test_build_merchants_shape_and_determinism():
    recs = [
        _r("PADARIA ESTRELA COMERCIO DE ALIMENTOS LTDA", "E100020 - Meals"),
        _r("", None), _r(None, None),  # empty vendors ignored
    ]
    m = build_merchants(recs)
    assert "PADARIA ESTRELA" in m       # source casing kept
    entry = m["PADARIA ESTRELA"]
    assert entry["category"] == "Meals & Entertainment"
    assert "PADARIA ESTRELA COMERCIO DE ALIMENTOS LTDA" in entry["aliases"]
    assert build_merchants(recs) == m  # deterministic


def test_seed_min_count_drops_singletons():
    recs = [_r("Acme", "Software Subscriptions"), _r("OneOff", "Meals")]
    m = build_merchants(recs, min_count=2)
    assert m == {}  # both seen once, both dropped


def test_label_to_bucket_reads_the_leaf_of_a_nested_chart():
    # Brisken's chart nests the real category under a "Travel Expense" parent;
    # the leaf carries the signal, not the parent.
    assert label_to_bucket("E100010-31 - Travel Expense | Food") == "Meals & Entertainment"
    assert label_to_bucket("E100010-01 - Travel Expense | Transportation") == "Travel & Transport"
    assert label_to_bucket("E100010 - Travel Expense") == "Travel & Transport"  # no leaf


def test_seed_drops_noise_vendors():
    recs = [
        _r("BRL94.00", "E100010 - Travel Expense | Food"),                 # amount fragment
        _r("Expense Location : Lisbon, Portugal", "E100010 | Food"),       # location tail
        _r("cielo", "E100010 | Food"),                                     # payment processor
        _r("AB", "E100010 | Food"),                                        # too short
        _r("MARTINO SUPERMERCADO", "E100010 - Travel Expense | Food"),     # the real merchant
    ]
    m = build_merchants(recs)
    assert set(m) == {"MARTINO SUPERMERCADO"}
    assert m["MARTINO SUPERMERCADO"]["category"] == "Meals & Entertainment"


# ── registry vs per-entity memory precedence (2026-08-07) ───────────
#
# Owner call on reviewer feedback r1c: the same merchant legitimately posts
# to different accounts per legal entity, so a per-entity LEARNED row
# outranks the registry's single canonical answer. Modeled on Brisken's real
# Zoho history, where `anthropic` posts to two different accounts across the
# two entities.

_CORP = "Corporate Services"
_CLOUD = "Cloud Services"
_LEARNED_ACCOUNT = "Other Infra and IT Costs for Cloud Business"
_REGISTRY_ACCOUNT = "COGS - DEV Infrastructure (SAP Apps & others)"


def _anthropic_registry():
    return MerchantRegistry({
        "Anthropic": {
            "aliases": ["ANTHROPIC"],
            "category": "Software & Subscriptions",
            "zoho_account": _REGISTRY_ACCOUNT,
        },
    })


def _charge_receipt(doc_id: str, entity: str) -> Receipt:
    """A receipt with NO line items, so categorization takes the
    vendor-fallback path where memory is consulted."""
    from decimal import Decimal
    return Receipt(
        document_id=doc_id,
        legal_entity_id=entity,
        detected_date=None,
        detected_total=Decimal("20.00"),
        detected_currency="USD",
        detected_vendor="ANTHROPIC",
        line_items=(),
    )


def _lookup_with_corp_row():
    from expense_recon.learning.consult import MerchantCategoryLookup
    from expense_recon.learning.store import MerchantCategory
    return MerchantCategoryLookup([
        MerchantCategory(
            legal_entity_id=_CORP,
            vendor_norm="anthropic",
            category="Software & Subscriptions",
            zoho_account=_LEARNED_ACCOUNT,
            decision_count=1,
            last_confirmed_at="2026-08-06T00:00:00",
            source_run="manual-set",
        ),
    ])


def _categorization(receipt):
    return receipt.line_items[0].categorization


def test_learned_entity_row_outranks_registry_default():
    """The entity WITH a learned row gets its own account, not the
    registry's."""
    from expense_recon.categorize import categorize_receipts_with_registry
    from expense_recon.matching.types import ClassificationSource

    out, matches = categorize_receipts_with_registry(
        [_charge_receipt("d-corp", _CORP)],
        registry=_anthropic_registry(),
        client=None,
        learned=_lookup_with_corp_row(),
    )
    cat = _categorization(out[0])
    assert cat.source is ClassificationSource.LEARNED
    assert cat.zoho_account == _LEARNED_ACCOUNT
    # naming is independent of categorization: the registry still supplies
    # the canonical display vendor even though memory won the category.
    assert "d-corp" in matches
    assert out[0].canonical_vendor == "Anthropic"


def test_registry_still_wins_for_entity_without_a_learned_row():
    """The other entity has nothing learned, so the registry default stands
    — this is what keeps the change additive rather than a regression."""
    from expense_recon.categorize import categorize_receipts_with_registry
    from expense_recon.matching.types import ClassificationSource

    out, _ = categorize_receipts_with_registry(
        [_charge_receipt("d-cloud", _CLOUD)],
        registry=_anthropic_registry(),
        client=None,
        learned=_lookup_with_corp_row(),
    )
    cat = _categorization(out[0])
    assert cat.source is ClassificationSource.REGISTRY
    assert cat.zoho_account == _REGISTRY_ACCOUNT


def test_same_vendor_two_entities_diverge_in_one_batch():
    """Both receipts in ONE batch: the whole point of the owner's call."""
    from expense_recon.categorize import categorize_receipts_with_registry
    from expense_recon.matching.types import ClassificationSource

    out, _ = categorize_receipts_with_registry(
        [_charge_receipt("d-corp", _CORP), _charge_receipt("d-cloud", _CLOUD)],
        registry=_anthropic_registry(),
        client=None,
        learned=_lookup_with_corp_row(),
    )
    by_doc = {r.document_id: _categorization(r) for r in out}
    assert by_doc["d-corp"].source is ClassificationSource.LEARNED
    assert by_doc["d-corp"].zoho_account == _LEARNED_ACCOUNT
    assert by_doc["d-cloud"].source is ClassificationSource.REGISTRY
    assert by_doc["d-cloud"].zoho_account == _REGISTRY_ACCOUNT
    assert [r.document_id for r in out] == ["d-corp", "d-cloud"]


def test_no_learned_store_leaves_registry_behavior_unchanged():
    """learned=None must reduce to the pre-2026-08-07 behavior exactly."""
    from expense_recon.categorize import categorize_receipts_with_registry
    from expense_recon.matching.types import ClassificationSource

    out, _ = categorize_receipts_with_registry(
        [_charge_receipt("d-corp", _CORP)],
        registry=_anthropic_registry(),
        client=None,
        learned=None,
    )
    cat = _categorization(out[0])
    assert cat.source is ClassificationSource.REGISTRY
    assert cat.zoho_account == _REGISTRY_ACCOUNT
