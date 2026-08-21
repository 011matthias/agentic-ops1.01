"""The card registry (2026-08-21, Cards R1).

Owner directive: cards get their own identity, independent of Zoho. R1 is
the registry + read-time composition with ZERO behavior change: with
``settings["cards"]`` empty, every consumer (resolve_entity,
apply_master_data, the batch snapshot, available_entities) must produce
exactly what the legacy ``card_entities`` / ``card_accounts`` maps
produced — the seeded 2026-08-06 master data keeps working untouched.
The legacy-shaped pins live in test_master_data_settings.py and must stay
green; these tests cover the new module and the composition itself.

The one production fact that drove the model: the SAME physical card has
multiple digit identities (Chase cycle-marker "2838", plastic last-4
"1672"; Zoho labels print both, "1 - CorpServ 2838/1672 (Chase)"). A
last4-keyed map can never resolve "Visa ...1672"; a card with
digits=["2838","1672"] can.
"""
from __future__ import annotations

import pytest

from expense_recon.cards import (
    Card,
    card_to_dict,
    effective_cards,
    entity_for,
    legacy_card_accounts,
    normalize_cards_setting,
    resolve_card,
    zoho_account_for,
)
from expense_recon.cards_provision import CardPreset


# ── normalize_cards_setting (the PUT /api/settings edge) ───────────────


def test_normalize_full_entry_roundtrip():
    cleaned = normalize_cards_setting({
        "corp-2838": {
            "label": " Corporate card (Chase) ",
            "digits": ["2838", "1672"],
            "aliases": ["CorpServ"],
            "entity": "Corporate Services",
            "zoho_account": "1010 Chase Corporate",
            "currency": "usd",
        }
    })
    entry = cleaned["corp-2838"]
    assert entry["label"] == "Corporate card (Chase)"
    assert entry["digits"] == ["2838", "1672"]
    assert entry["aliases"] == ["CorpServ"]
    assert entry["entity"] == "Corporate Services"
    assert entry["zoho_account"] == "1010 Chase Corporate"
    assert entry["currency"] == "USD"
    assert "active" not in entry, "active stored only when False"


def test_normalize_blank_slug_dropped_and_shape_errors():
    assert normalize_cards_setting({"  ": {"entity": "X"}}) == {}
    with pytest.raises(ValueError):
        normalize_cards_setting("not a dict")
    with pytest.raises(ValueError):
        normalize_cards_setting({"a": "not a dict"})
    with pytest.raises(ValueError):
        normalize_cards_setting({"a": {"digits": "2838"}})  # not a list
    with pytest.raises(ValueError):
        normalize_cards_setting({"a": {"digits": ["28x8"]}})  # not digits
    with pytest.raises(ValueError):
        normalize_cards_setting({"a": {"digits": ["123456789"]}})  # too long
    with pytest.raises(ValueError):
        # A sub-3-digit token would be inert for resolution but become an
        # endswith wildcard in the snapshot map — rejected at the edge.
        normalize_cards_setting({"a": {"digits": ["28"]}})


def test_normalize_dedupes_and_stores_inactive():
    cleaned = normalize_cards_setting({
        "c": {
            "digits": ["2838", "2838"],
            "aliases": ["CorpServ", "corpserv", " "],
            "active": False,
        }
    })
    assert cleaned["c"]["digits"] == ["2838"]
    assert cleaned["c"]["aliases"] == ["CorpServ"]
    assert cleaned["c"]["active"] is False


# ── effective_cards: read-time composition IS the migration ────────────


def test_legacy_maps_compose_into_one_card():
    """The seeded shape: both legacy maps keyed "2838" become ONE card
    carrying entity AND zoho account, digit identity intact."""
    cards = effective_cards({
        "card_entities": {"2838": "Corporate Services"},
        "card_accounts": {"2838": "1010 Chase Corporate"},
    })
    assert list(cards) == ["card-2838"]
    card = cards["card-2838"]
    assert card.entity == "Corporate Services"
    assert card.zoho_account == "1010 Chase Corporate"
    assert card.digits == ("2838",)
    assert card.source == "legacy"


def test_legacy_nondigit_key_keeps_digit_identity():
    """A legacy key "card-2838" digit-matches exactly like "2838" did in
    the old `_card_key_matches` token path."""
    cards = effective_cards({"card_entities": {"card-2838": "Corporate Services"}})
    card = cards["card-2838"]
    assert card.digits == ("2838",)
    assert "card-2838" in card.aliases
    assert entity_for("2838 - May 2026", cards) == "Corporate Services"


def test_settings_card_wins_field_by_field():
    """An explicit card entry absorbs the legacy maps by digit identity:
    legacy fills only fields the entry left empty."""
    cards = effective_cards({
        "cards": {
            "corp-2838": {
                "digits": ["2838", "1672"],
                "entity": "Explicit Entity",
            }
        },
        "card_entities": {"2838": "Legacy Entity"},
        "card_accounts": {"2838": "1010 Chase Corporate"},
    })
    assert list(cards) == ["corp-2838"], "no duplicate legacy card synthesized"
    card = cards["corp-2838"]
    assert card.entity == "Explicit Entity", "settings wins over legacy"
    assert card.zoho_account == "1010 Chase Corporate", "legacy fills the gap"
    assert card.source == "settings"


def test_preset_file_folds_in_after_legacy():
    """The /data presets file merges by digit identity too; its entity
    fills only when neither settings nor legacy set one."""
    presets = [
        CardPreset(
            key="corp-2838",
            label="Corporate card ending 2838",
            label_pt="Cartao corporativo final 2838",
            account_id="card-2838",
            legal_entity="Preset Entity",
            currency="USD",
        )
    ]
    merged = effective_cards(
        {"card_entities": {"2838": "Legacy Entity"}}, presets
    )
    assert list(merged) == ["card-2838"]
    assert merged["card-2838"].entity == "Legacy Entity"
    assert merged["card-2838"].label == "Corporate card ending 2838"
    assert merged["card-2838"].currency == "USD"

    alone = effective_cards({}, presets)
    assert list(alone) == ["corp-2838"]
    assert alone["corp-2838"].entity == "Preset Entity"
    assert alone["corp-2838"].digits == ("2838",)
    assert alone["corp-2838"].source == "preset"


def test_empty_settings_compose_to_nothing():
    assert effective_cards(None) == {}
    assert effective_cards({}) == {}
    assert effective_cards({"card_entities": {}, "card_accounts": {}}) == {}


def test_fold_merge_keeps_composite_key_digits():
    """Adversarial-review find (Cards R1): a composite accounts key
    "2838/1672" that token-merges into the card the entities map created
    as "2838" must keep BOTH digit identities — dropping "1672" would
    shrink the batch snapshot and silently unresolve "Visa ...1672"."""
    cards = effective_cards({
        "card_entities": {"2838": "Corporate Services"},
        "card_accounts": {"2838/1672": "1010 Chase Corporate"},
    })
    assert list(cards) == ["card-2838"]
    card = cards["card-2838"]
    assert set(card.digits) == {"2838", "1672"}
    assert legacy_card_accounts(cards) == {
        "2838": "1010 Chase Corporate",
        "1672": "1010 Chase Corporate",
    }
    assert zoho_account_for("Visa ...1672", cards) == "1010 Chase Corporate"


def test_cross_map_shadowing_resolves_both_fields():
    """Adversarial-review find (Cards R1): the old per-map scans were
    independent — an entity lookup consulted only entity-bearing keys. A
    digit hit on an accounts-only card must not shadow an alias hit on
    the entity-bearing card (the has_coa:false silent-disarm class)."""
    cards = effective_cards({
        "card_entities": {"CorpServ": "EntA"},
        "card_accounts": {"2838": "1010 Chase Corporate"},
    })
    assert entity_for("2838 - CorpServ", cards) == "EntA"
    assert zoho_account_for("2838 - CorpServ", cards) == "1010 Chase Corporate"


def test_inactive_settings_card_suppresses_its_legacy_fold():
    """Deactivating a card means "stop resolving this card" — the legacy
    entry that folds into it is suppressed too, by design."""
    cards = effective_cards({
        "cards": {"corp-2838": {"digits": ["2838"], "active": False}},
        "card_accounts": {"2838": "1010 Chase Corporate"},
    })
    assert list(cards) == ["corp-2838"]
    assert legacy_card_accounts(cards) == {}
    assert zoho_account_for("2838", cards) is None


# ── resolve_card: one resolver for every observed card string ──────────


_CARDS = {
    "corp-2838": Card(
        key="corp-2838",
        digits=("2838", "1672"),
        aliases=("CorpServ",),
        entity="Corporate Services",
        zoho_account="1010 Chase Corporate",
    ),
    "cloud-9693": Card(
        key="cloud-9693", digits=("9693",), entity="Cloud Services"
    ),
}


@pytest.mark.parametrize(
    "observed",
    [
        "2838",
        "2838 - May 2026",
        "1 - CorpServ 2838/1672 (Chase)",
        "Visa ...1672",
        "corpserv monthly",
    ],
)
def test_resolve_card_hits(observed):
    card = resolve_card(observed, _CARDS)
    assert card is not None and card.key == "corp-2838"


@pytest.mark.parametrize(
    "observed",
    ["Visa", "Cartão de crédito", "brisken", "cash", "", None, "9999"],
)
def test_resolve_card_generic_tenders_stay_unresolved(observed):
    """Generic tender words carry no card identity: review, not guess."""
    assert resolve_card(observed, _CARDS) is None


def test_resolve_card_inactive_never_resolves():
    cards = {
        "old": Card(key="old", digits=("2838",), active=False, entity="X")
    }
    assert resolve_card("2838", cards) is None
    assert legacy_card_accounts(
        {"old": Card(key="old", digits=("2838",), zoho_account="A", active=False)}
    ) == {}


def test_resolve_card_ambiguity_modes():
    cards = {
        "a": Card(key="a", digits=("2838",), entity="First"),
        "b": Card(key="b", digits=("2838",), entity="Second"),
    }
    first = resolve_card("2838", cards, on_ambiguity="first")
    assert first is not None and first.key == "a", "legacy first-match order"
    assert resolve_card("2838", cards, on_ambiguity="none") is None, (
        "review-flow contract: ambiguity surfaces instead of guessing"
    )


def test_entity_and_account_helpers():
    assert entity_for("Visa ...1672", _CARDS) == "Corporate Services"
    assert zoho_account_for("Visa ...1672", _CARDS) == "1010 Chase Corporate"
    assert entity_for("9693", _CARDS) == "Cloud Services"
    assert zoho_account_for("9693", _CARDS) is None, "no Zoho account is fine"
    assert entity_for("unknown", _CARDS) is None


# ── resolve_account_map: the conservative money-path resolver ──────────


def test_resolve_account_map_semantics():
    """Exact key first; bare-digit keys match a label printing their
    number; label-shaped keys are exact-only; ambiguity denies (R2
    adversarial review: a money path never guesses)."""
    from expense_recon.cards import resolve_account_map

    assert resolve_account_map("amex-usd", {"amex-usd": "A200"}) == "A200"
    assert resolve_account_map("2838 - May 2026", {"2838": "A200"}) == "A200"
    assert resolve_account_map("0340 - June", {"340": "A300"}) == "A300"
    # Label-shaped key: exact only — no token bleed across labels.
    assert resolve_account_map(
        "0340 - June 2026", {"2838 - May 2026": "A200"}
    ) is None
    # Two bare-digit hits on one label: deny.
    assert resolve_account_map(
        "2838 - May 2026", {"2838": "A200", "2026": "A300"}
    ) is None
    # Same account under both hits is not ambiguous.
    assert resolve_account_map(
        "2838 - May 2026", {"2838": "A200", "2026": "A200"}
    ) == "A200"
    # Word keys never wildcard; empties resolve nothing.
    assert resolve_account_map("0340 - Chase", {"chase": "A200"}) is None
    assert resolve_account_map("", {"2838": "A200"}) is None
    assert resolve_account_map("2838", None) is None


# ── legacy_card_accounts: the snapshot flatten (cfg compat) ────────────


def test_flatten_reproduces_legacy_map_exactly():
    """With settings cards empty the batch snapshot must be byte-identical
    to the legacy map (run reproducibility)."""
    settings = {"card_accounts": {"2838": "1010 Chase Corporate",
                                  "9693": "1020 Chase Cloud"}}
    flat = legacy_card_accounts(effective_cards(settings))
    assert flat == settings["card_accounts"]


def test_flatten_carries_every_digit_of_a_settings_card():
    """The dual-identity fix: a card with both digit identities makes the
    exports resolve "Visa ...1672" too."""
    cards = effective_cards({
        "cards": {
            "corp-2838": {
                "digits": ["2838", "1672"],
                "zoho_account": "1010 Chase Corporate",
            }
        }
    })
    assert legacy_card_accounts(cards) == {
        "2838": "1010 Chase Corporate",
        "1672": "1010 Chase Corporate",
    }


# ── card_to_dict: the API shape ────────────────────────────────────────


def test_card_to_dict_shape():
    d = card_to_dict(_CARDS["corp-2838"])
    assert d["key"] == "corp-2838"
    assert d["label"] == "corp-2838", "display label falls back to key"
    assert d["digits"] == ["2838", "1672"]
    assert d["entity"] == "Corporate Services"
    assert d["active"] is True
    assert d["source"] == "settings"
