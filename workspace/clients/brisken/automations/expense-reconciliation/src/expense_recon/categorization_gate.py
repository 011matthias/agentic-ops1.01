"""Categorization-accuracy regression gate for `calibrate` (PR 2b).

`calibrate` already gates the reconciliation invariant + matcher scoring;
it does NOT measure categorization. The moment memory auto-applies a
learned merchant->category (the Sort consult), a subtly-wrong learned
mapping could degrade Sort while the reconciliation gate sails through
green. This gate closes that hole.

It measures categorization accuracy on a bundled labeled fixture (keyword
stub, deterministic, no LLM — same posture as the rest of `calibrate`) and
SEGMENTS it:

* **overall** — coarse floor at today's baseline; catches a broad
  regression.
* **changed subset** — only the receipts whose merchant carries a learned
  mapping (`MEMORY_FIXTURE`), i.e. the population whose behavior actually
  changes once consult lands. Its floor RATCHETS UP in the consult commit,
  so a drop in the auto-applied population trips the gate on its own even
  when overall holds flat (the exact "coarse metric sails through" failure
  the segmentation exists to prevent).

The fixture is built to guard BOTH consult invariants:
  - thin-line receipts for learned merchants (baseline keyword stub gets
    them wrong; memory should upgrade them) — proves the win.
  - a good-LINE receipt whose merchant has a CONFLICTING learned mapping
    (`Contoso Hardware`): the line read is correct and must win; if memory
    ever preempts the line, this receipt flips wrong and the subset score
    drops below floor. This guards "memory is a fallback, not an override".

This commit (the gate) lands BEFORE the consult path: with no consult,
memory has no effect, so the numbers are the empty-store baseline and the
floors are set to it. The consult commit raises `SUBSET_FLOOR`.
"""
from __future__ import annotations

from decimal import Decimal

from .categorize import categorize_receipts
from .learning import normalize_vendor
from .matching.types import LineItem, Receipt

LE = "brisken-llc"
_EPS = 1e-9


def _li(desc: str, total: str) -> LineItem:
    return LineItem(description=desc, line_total=Decimal(total))


def _rcpt(doc: str, vendor: str, line_items: tuple[LineItem, ...] = ()) -> Receipt:
    return Receipt(
        document_id=doc, legal_entity_id=LE, detected_date=None,
        detected_total=Decimal("10.00"), detected_currency="USD",
        detected_vendor=vendor, line_items=line_items,
    )


# (receipt, correct category). Single line item each, so the predicted
# category is unambiguous: receipt.line_items[0] after categorization.
LABELED: tuple[tuple[Receipt, str], ...] = (
    # Good-line receipts (line keyword wins; merchant NOT in memory).
    (_rcpt("lat", "Cafe Grumpy", (_li("Latte", "10.00"),)), "Meals & Entertainment"),
    (_rcpt("desk", "Office Outlet", (_li("Standing desk", "10.00"),)), "Equipment & Hardware"),
    # Good-line receipt whose merchant HAS a conflicting learned mapping:
    # the line ("chair" -> Equipment) must win over the learned Office
    # Supplies mapping. Guards "fallback, not override".
    (_rcpt("guard", "Contoso Hardware", (_li("Office chair", "10.00"),)), "Equipment & Hardware"),
    # Thin-line receipts for learned merchants (baseline stub -> REVIEW;
    # memory should upgrade them to the correct category).
    (_rcpt("blue", "Bluebottle Consulting"), "Professional Services"),
    (_rcpt("vrtx", "Vertex Audit Group"), "Professional Services"),
    (_rcpt("nrth", "Northwind Premises"), "Utilities & Premises"),
    # Thin-line control: vendor the keyword stub already knows; NOT in
    # memory, so it is unchanged by consult.
    (_rcpt("uber", "Uber"), "Travel & Transport"),
)

# Learned merchant->category mappings seeded for the with-memory
# measurement (consult commit). The Contoso entry is deliberately WRONG for
# the guard receipt, to prove the line read wins.
MEMORY_FIXTURE: tuple[tuple[str, str, str], ...] = (
    (LE, "Contoso Hardware", "Office Supplies & Consumables"),
    (LE, "Bluebottle Consulting", "Professional Services"),
    (LE, "Vertex Audit Group", "Professional Services"),
    (LE, "Northwind Premises", "Utilities & Premises"),
)

_MEMORY_VENDORS = {normalize_vendor(v) for (_le, v, _c) in MEMORY_FIXTURE}

# Floors. Baseline = empty-store accuracy (keyword stub, no consult).
# overall: 4/7 correct (the three thin learned merchants miss). subset:
# 1/4 (only the Contoso guard is right at baseline). SUBSET_FLOOR ratchets
# to 1.0 in the consult commit.
OVERALL_FLOOR = 4 / 7
SUBSET_FLOOR = 1 / 4


def _predicted_category(receipt: Receipt) -> str | None:
    cat = receipt.line_items[0].categorization if receipt.line_items else None
    return cat.category if cat else None


def measure() -> dict:
    """Run the keyword categorizer over the labeled fixture and report
    overall + changed-subset accuracy. Deterministic; no LLM, no store."""
    receipts = [r for r, _label in LABELED]
    labels = [label for _r, label in LABELED]
    out = categorize_receipts(receipts, client=None)

    n = n_ok = 0
    n_sub = n_sub_ok = 0
    for receipt, label in zip(out, labels):
        ok = _predicted_category(receipt) == label
        n += 1
        n_ok += int(ok)
        if normalize_vendor(receipt.detected_vendor or "") in _MEMORY_VENDORS:
            n_sub += 1
            n_sub_ok += int(ok)

    overall = n_ok / n if n else 0.0
    subset = n_sub_ok / n_sub if n_sub else 0.0
    return {
        "n": n, "n_ok": n_ok, "overall": overall, "overall_floor": OVERALL_FLOOR,
        "n_subset": n_sub, "n_subset_ok": n_sub_ok,
        "subset": subset, "subset_floor": SUBSET_FLOOR,
    }


def run_gate() -> dict:
    m = measure()
    m["ok"] = (
        m["overall"] >= OVERALL_FLOOR - _EPS
        and m["subset"] >= SUBSET_FLOOR - _EPS
    )
    return m


def print_report(m: dict) -> None:
    print("CATEGORIZATION ACCURACY (labeled fixture)")
    print(
        f"  Overall:        {m['n_ok']}/{m['n']} = {m['overall'] * 100:.1f}%  "
        f"(floor {m['overall_floor'] * 100:.1f}%)"
    )
    print(
        f"  Changed subset: {m['n_subset_ok']}/{m['n_subset']} = {m['subset'] * 100:.1f}%  "
        f"(floor {m['subset_floor'] * 100:.1f}%)"
    )
    print(f"  Gate: {'OK' if m['ok'] else 'FAIL'}")
