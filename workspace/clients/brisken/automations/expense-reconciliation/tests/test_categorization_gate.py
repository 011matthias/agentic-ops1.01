"""Categorization-accuracy gate (PR 2b). Documents the empty-store baseline,
the with-memory lift on the changed subset, and that the gate's segmented
subset floor protects the auto-applied population."""
from __future__ import annotations

from expense_recon import categorization_gate as g
from expense_recon.learning import normalize_vendor


def test_baseline_measure_no_memory():
    m = g.measure(None)
    assert m["n"] == 7
    # Three thin-line learned merchants miss at baseline; 4 right.
    assert m["n_ok"] == 4
    # Changed subset = the 4 merchants carrying a learned mapping; only the
    # Contoso guard (good line read) is right at baseline.
    assert m["n_subset"] == 4
    assert m["n_subset_ok"] == 1


def test_memory_lifts_changed_subset_to_full():
    m = g.measure(g.memory_lookup())
    # The three thin learned merchants now categorize via memory; the guard
    # stays right via its line read -> whole fixture correct.
    assert m["n_ok"] == 7
    assert m["n_subset_ok"] == 4
    assert m["subset"] == 1.0


def test_gate_green_with_memory():
    assert g.run_gate()["ok"] is True


def test_floors():
    assert abs(g.OVERALL_FLOOR - 4 / 7) < 1e-9
    assert g.SUBSET_FLOOR == 1.0  # ratcheted up once consult is live


def test_guard_line_wins_over_conflicting_memory():
    # The guard receipt's merchant has a learned Office-Supplies mapping, but
    # the receipt has a good line ("Office chair" -> Equipment). With memory
    # applied, the LINE read must still win — fallback, not override.
    receipts = [r for r, _ in g.LABELED]
    out = g.categorize_receipts(receipts, client=None, learned=g.memory_lookup())
    guard = next(r for r in out if r.document_id == "guard")
    assert guard.line_items[0].categorization.category == "Equipment & Hardware"
    assert guard.line_items[0].categorization.source.value == "LINE"


def test_guard_fixture_mapping_actually_conflicts():
    guard = next(r for r, _ in g.LABELED if r.document_id == "guard")
    learned = {normalize_vendor(v): c for _le, v, c in g.MEMORY_FIXTURE}
    assert learned[normalize_vendor(guard.detected_vendor)] != "Equipment & Hardware"
