"""Categorization-accuracy gate (PR 2b). Documents the empty-store baseline,
the with-memory lift on the changed subset, and that the gate's segmented
subset floor protects the auto-applied population. Item 115 split the
conflicting-mapping guard in two: a Zoho-seeded row still loses to a line
read, a correction a person taught wins it."""
from __future__ import annotations

from expense_recon import categorization_gate as g
from expense_recon.learning import normalize_vendor


def test_baseline_measure_no_memory():
    m = g.measure(None)
    assert m["n"] == 8
    # Three thin-line learned merchants and the taught-category receipt miss
    # at baseline; 4 right.
    assert m["n_ok"] == 4
    # Changed subset = the 5 merchants carrying a learned mapping; only the
    # Contoso guard (good line read) is right at baseline.
    assert m["n_subset"] == 5
    assert m["n_subset_ok"] == 1


def test_memory_lifts_changed_subset_to_full():
    m = g.measure(g.memory_lookup())
    # The three thin learned merchants categorize via memory, the taught
    # receipt takes its person's category, and the seeded guard stays right
    # via its line read -> whole fixture correct.
    assert m["n_ok"] == 8
    assert m["n_subset_ok"] == 5
    assert m["subset"] == 1.0


def test_gate_green_with_memory():
    assert g.run_gate()["ok"] is True


def test_floors():
    assert abs(g.OVERALL_FLOOR - 4 / 8) < 1e-9
    assert g.SUBSET_FLOOR == 1.0  # ratcheted up once consult is live


def test_guard_line_wins_over_a_conflicting_seeded_row():
    # The guard receipt's merchant has a Zoho-seeded Office-Supplies row, but
    # the receipt has a good line ("Office chair" -> Equipment). With memory
    # applied, the LINE read must still win — the seed is posting history,
    # not a decision about this merchant.
    receipts = [r for r, _ in g.LABELED]
    out = g.categorize_receipts(receipts, client=None, learned=g.memory_lookup())
    guard = next(r for r in out if r.document_id == "guard")
    assert guard.line_items[0].categorization.category == "Equipment & Hardware"
    assert guard.line_items[0].categorization.source.value == "LINE"


def test_a_taught_row_wins_the_same_line_read_and_says_so():
    receipts = [r for r, _ in g.LABELED]
    out = g.categorize_receipts(receipts, client=None, learned=g.memory_lookup())
    taught = next(r for r in out if r.document_id == "taught")
    cat = taught.line_items[0].categorization
    assert cat.category == "Office Supplies & Consumables"
    assert cat.source.value == "LEARNED"
    assert cat.decision == "learned_over_line"


def test_guard_fixture_mappings_actually_conflict():
    learned = {normalize_vendor(v): c for _le, v, c, _s in g.MEMORY_FIXTURE}
    for doc in ("guard", "taught"):
        r = next(r for r, _ in g.LABELED if r.document_id == doc)
        assert learned[normalize_vendor(r.detected_vendor)] != "Equipment & Hardware"
