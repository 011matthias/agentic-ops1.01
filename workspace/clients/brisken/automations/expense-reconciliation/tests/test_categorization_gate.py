"""Categorization-accuracy gate (PR 2b, gate commit). Locks the empty-store
baseline so the consult commit's improvement on the changed subset is
visible, and proves the gate is green at baseline."""
from __future__ import annotations

from expense_recon import categorization_gate as g
from expense_recon.learning import normalize_vendor


def test_baseline_measure_matches_floors():
    m = g.measure()
    assert m["n"] == 7
    # Three thin-line learned merchants miss at baseline; 4 right.
    assert m["n_ok"] == 4
    # Changed subset = the 4 merchants carrying a learned mapping; only the
    # Contoso guard (good line read) is right at baseline.
    assert m["n_subset"] == 4
    assert m["n_subset_ok"] == 1


def test_gate_green_at_baseline():
    assert g.run_gate()["ok"] is True


def test_floors_are_the_baseline():
    # The floors ARE today's numbers — the gate is exact at baseline, so any
    # regression (or, in the consult commit, the raised subset floor) bites.
    assert abs(g.OVERALL_FLOOR - 4 / 7) < 1e-9
    assert abs(g.SUBSET_FLOOR - 1 / 4) < 1e-9


def test_guard_receipt_has_conflicting_learned_mapping():
    # The good-line guard receipt's merchant must carry a learned mapping
    # that DISAGREES with its correct line-based category, or it cannot
    # guard "fallback, not override".
    guard = next(r for r, _ in g.LABELED if r.document_id == "guard")
    assert guard.line_items  # has a real line read
    learned = {normalize_vendor(v): c for _le, v, c in g.MEMORY_FIXTURE}
    vn = normalize_vendor(guard.detected_vendor)
    assert vn in learned
    assert learned[vn] != "Equipment & Hardware"  # conflicts with the line read
