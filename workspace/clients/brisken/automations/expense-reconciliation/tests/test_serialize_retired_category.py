"""A stored snapshot must still load once the category key stops being written.

The eight-bucket vocabulary (`EXPENSE_CATEGORIES`) is being retired in favour of
classifying a receipt directly into a Zoho GL leaf. Before any writer may stop
emitting `category`, the READ has to tolerate its absence, or the first month
snapshot written by the new version becomes an unopenable month.

These assertions run through `lineitem_from_dict`, the caller that actually
loads a persisted line item, rather than through `categorization_from_dict`
alone. A helper proven in isolation says nothing about whether it is wired:
regressing `d.get("category")` back to `d["category"]` has to turn one of these
RED, and that is the test this module exists to be.
"""
from __future__ import annotations

import pytest

from expense_recon.web.serialize import (
    categorization_to_dict,
    lineitem_from_dict,
    lineitem_to_dict,
)


def _line(categorization: dict | None) -> dict:
    """A persisted line-item dict, shaped exactly as `lineitem_to_dict` writes one."""
    return {
        "description": "Claude Pro subscription",
        "line_total": "20.00",
        "quantity": "1",
        "unit_price": "20.00",
        "categorization": categorization,
    }


def _cat(**overrides) -> dict:
    base = {
        "category": "Software & Subscriptions",
        "zoho_account": "E500010-30",
        "confidence": 1.0,
        "source": "REGISTRY",
        "reasoning": "registry default",
        "decision": None,
    }
    base.update(overrides)
    return base


def test_line_item_loads_when_the_snapshot_omits_category():
    """The forward-compatible case: a leaf-only classification, no bucket.

    This is the one that bites. With a bare `d["category"]` subscript it raises
    KeyError and the month will not open.
    """
    stored = _cat()
    del stored["category"]

    li = lineitem_from_dict(_line(stored))

    assert li.categorization is not None
    assert li.categorization.category is None
    # The half that now carries the meaning must survive intact.
    assert li.categorization.zoho_account == "E500010-30"


def test_line_item_loads_when_the_snapshot_omits_zoho_account():
    """The mirror case, so the tolerance is not one-sided."""
    stored = _cat()
    del stored["zoho_account"]

    li = lineitem_from_dict(_line(stored))

    assert li.categorization is not None
    assert li.categorization.zoho_account is None
    assert li.categorization.category == "Software & Subscriptions"


def test_line_item_loads_when_the_snapshot_omits_both():
    stored = _cat()
    del stored["category"]
    del stored["zoho_account"]

    li = lineitem_from_dict(_line(stored))

    assert li.categorization is not None
    assert li.categorization.category is None
    assert li.categorization.zoho_account is None


def test_an_existing_eight_bucket_snapshot_still_loads_unchanged():
    """The negative case, and the reason the tolerance is safe to ship alone.

    Every month frozen under the old vocabulary must keep opening and keep
    reading exactly as before. If tolerance ever starts dropping real values,
    this is what goes red.
    """
    li = lineitem_from_dict(_line(_cat()))

    assert li.categorization is not None
    assert li.categorization.category == "Software & Subscriptions"
    assert li.categorization.zoho_account == "E500010-30"
    assert li.categorization.confidence == pytest.approx(1.0)
    assert li.categorization.source.value == "REGISTRY"


def test_round_trip_through_the_writer_is_unchanged():
    """A line written by today's writer reloads identically.

    Guards the other direction: the tolerant read must not quietly change what
    a normal save/load cycle produces.
    """
    original = lineitem_from_dict(_line(_cat()))

    reloaded = lineitem_from_dict(lineitem_to_dict(original))

    assert reloaded.categorization is not None
    assert original.categorization is not None
    assert reloaded.categorization.category == original.categorization.category
    assert reloaded.categorization.zoho_account == original.categorization.zoho_account
    assert categorization_to_dict(reloaded.categorization) == categorization_to_dict(
        original.categorization
    )


def test_a_line_with_no_categorization_at_all_still_loads():
    """Pre-categorization snapshots carry an explicit null; unchanged behaviour."""
    li = lineitem_from_dict(_line(None))

    assert li.categorization is None
