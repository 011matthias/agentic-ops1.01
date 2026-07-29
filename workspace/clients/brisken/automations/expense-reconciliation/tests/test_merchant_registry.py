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
