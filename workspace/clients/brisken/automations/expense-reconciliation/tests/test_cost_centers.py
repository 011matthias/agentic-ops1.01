"""Cost-center registry + resolution chain (backlog item 47).

The load-bearing test in this file is `test_empty_registry_flags_nothing`.
Everything else can regress noisily; that one regresses SILENTLY, by turning
every row in every month into `needs_cost_center` on the day the field ships.
"""
import pytest

from expense_recon.cost_centers import (
    COST_CENTER_KINDS,
    SOURCE_CARD,
    SOURCE_MERCHANT,
    SOURCE_NONE,
    SOURCE_OVERRIDE,
    SOURCE_TRIP,
    CostCenterRegistry,
    normalize_cost_centers_setting,
)

REGISTRY = {
    "Lidar": {"kind": "project"},
    "Marketing": {"kind": "function"},
    "Brazil 2026": {"kind": "trip"},
    "Expense tool": {"kind": "project", "note": "Matthias"},
    "Retired thing": {"kind": "project", "active": False},
}


# ── the empty-registry contract ───────────────────────────────────────────

def test_empty_registry_flags_nothing():
    """An empty registry resolves nothing AND flags nothing.

    Without this, every row everywhere reads needs_cost_center the moment
    the field ships, and a review state at 100% is noise rather than signal.
    """
    reg = CostCenterRegistry({})
    r = reg.resolve(override="Lidar", trip="Brazil 2026", card="Marketing")
    assert r.name is None
    assert r.needs is False
    assert r.source == SOURCE_NONE
    assert r.as_fields()["needs_cost_center"] is False


def test_missing_key_behaves_exactly_as_empty():
    assert CostCenterRegistry.from_settings({}).resolve(override="x").needs is False
    assert CostCenterRegistry.from_settings(None).resolve(override="x").needs is False
    assert not CostCenterRegistry.from_settings({"cost_centers": {}})


def test_flag_starts_firing_once_one_centre_exists():
    """The other half of the contract: with a registry, an unattributed row
    IS worth flagging."""
    reg = CostCenterRegistry({"Lidar": {"kind": "project"}})
    r = reg.resolve()
    assert r.name is None
    assert r.needs is True


# ── resolution order ──────────────────────────────────────────────────────

def test_resolution_order_is_override_trip_merchant_card():
    reg = CostCenterRegistry(REGISTRY)
    assert reg.resolve(override="Lidar", trip="Brazil 2026", merchant="Marketing",
                       card="Expense tool").source == SOURCE_OVERRIDE
    assert reg.resolve(trip="Brazil 2026", merchant="Marketing",
                       card="Expense tool").source == SOURCE_TRIP
    assert reg.resolve(merchant="Marketing", card="Expense tool").source == SOURCE_MERCHANT
    assert reg.resolve(card="Expense tool").source == SOURCE_CARD


def test_unknown_name_is_ignored_never_invented():
    """The tool never invents a cost center; a name the owner has not
    defined resolves nothing and falls through to the next source."""
    reg = CostCenterRegistry(REGISTRY)
    r = reg.resolve(override="Not A Real Centre", card="Lidar")
    assert r.name == "Lidar"
    assert r.source == SOURCE_CARD


def test_case_insensitive_but_registry_spelling_wins():
    reg = CostCenterRegistry(REGISTRY)
    r = reg.resolve(override="lIdAr")
    assert r.name == "Lidar"


def test_person_and_category_are_not_resolvers():
    """Guarded by construction: resolve() takes no person/category argument.
    If someone adds one, this test is the place the decision gets re-argued."""
    import inspect
    params = set(inspect.signature(CostCenterRegistry.resolve).parameters)
    assert "person" not in params
    assert "category" not in params
    assert params == {"self", "override", "trip", "merchant", "card"}


# ── active / inactive ─────────────────────────────────────────────────────

def test_inactive_centre_is_not_applied_by_a_default():
    reg = CostCenterRegistry(REGISTRY)
    assert reg.resolve(card="Retired thing").name is None
    assert reg.resolve(card="Retired thing").needs is True


def test_inactive_centre_is_still_settable_by_a_reviewer():
    """Deactivating must not stop a human correcting history into it."""
    reg = CostCenterRegistry(REGISTRY)
    r = reg.resolve(override="Retired thing")
    assert r.name == "Retired thing"
    assert r.source == SOURCE_OVERRIDE


def test_options_lists_active_only_sorted():
    reg = CostCenterRegistry(REGISTRY)
    names = [o["name"] for o in reg.options()]
    assert names == ["Brazil 2026", "Expense tool", "Lidar", "Marketing"]
    assert {o["kind"] for o in reg.options()} == {"project", "function", "trip"}


# ── API field shape ───────────────────────────────────────────────────────

def test_fields_are_parallel_and_carry_a_source_label():
    reg = CostCenterRegistry(REGISTRY)
    f = reg.resolve(card="Lidar").as_fields()
    assert f == {
        "cost_center": "Lidar",
        "cost_center_source": SOURCE_CARD,
        "cost_center_source_label": "default for this card",
        "needs_cost_center": False,
    }


# ── normalization at the settings edge ────────────────────────────────────

def test_normalize_keeps_the_smallest_honest_shape():
    out = normalize_cost_centers_setting({
        "  Lidar  ": {"kind": "PROJECT", "note": "  laser  "},
        "Plain": {},
        "Off": {"kind": "function", "active": False},
        "": {"kind": "project"},
    })
    assert out == {
        "Lidar": {"kind": "project", "note": "laser"},
        "Plain": {},
        "Off": {"kind": "function", "active": False},
    }


def test_normalize_rejects_a_bad_kind():
    with pytest.raises(ValueError, match="kind"):
        normalize_cost_centers_setting({"X": {"kind": "department"}})


def test_normalize_rejects_case_collisions_rather_than_silently_dropping_one():
    with pytest.raises(ValueError, match="differing only in case"):
        normalize_cost_centers_setting({"Lidar": {}, "lidar": {}})


def test_normalize_rejects_non_objects():
    with pytest.raises(ValueError):
        normalize_cost_centers_setting([1, 2])
    with pytest.raises(ValueError):
        normalize_cost_centers_setting({"X": "project"})


def test_normalize_none_is_empty_not_an_error():
    assert normalize_cost_centers_setting(None) == {}


def test_blank_kind_is_allowed():
    assert "" in COST_CENTER_KINDS
    assert normalize_cost_centers_setting({"X": {"kind": ""}}) == {"X": {}}
