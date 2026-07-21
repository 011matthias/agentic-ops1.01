# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: pessimistic-case floor on the pricing menu's contribution surplus (anti-overfit).

RECIPES constructed-metric rule 3 ("held-out score floor, mandatory"). The scorer
(tools/scorers/pricing-tiers.py) rewards CENTRAL-case surplus; a hill-climb drifts
toward whatever the central WTP assumptions reward. This guard is an INDEPENDENT
reimplementation of the same self-selection model under a PESSIMISTIC parameter
set, and it fails the round if the menu's pessimistic surplus drops below the floor.

Floor = 0.0: even in the bad case, the tier menu must clear the owner's opportunity
cost (the contribution from clients who buy must beat grinding hourly). A menu that
only wins under optimistic willingness-to-pay is discarded even when it beats the
current best central score.

Pessimistic haircuts vs central: segment sizes x0.7 (fewer prospects reach the buy
decision), per-month value x0.8 (tighter budgets discount what they will pay),
delivery cost x1.25 (subcontractors cost more), owner oversight x1.25, delivery
capacity x0.8 (tighter). A pessimistic buyer also has a stricter outside option:
it only buys if its surplus clears a positive threshold, not merely > 0.

Deliberately separate code from the scorer: a shared bug cannot hide in both, and
drift between them is a signal to re-review. Kept economically in lockstep at pin time.

Exit 0 = pessimistic surplus >= floor. Exit 1 = below. Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

STRESS_FLOOR = 0.0

LIFETIME_MONTHS = 14.0
OPP_RATE_EUR_HR = 33.0
OH_BASE, OH_SLOPE = 1.0, 1.6
OH_PENALTY = 1.25
D_BASE, D_SLOPE, D_QUAD = 120.0, 450.0, 350.0
D_PENALTY = 1.25
VALUE_HAIRCUT = 0.8
SIZE_HAIRCUT = 0.7
CAP_CLIENT_EQUIV = 150.0 * 0.8
MIN_LOAD = 0.15
BUY_THRESHOLD = 150.0     # a squeezed prospect needs > EUR150/mo of surplus to bother switching

TIERS = ("good", "better", "best")

# Independent copy of the segments (mirror of the scorer), value haircut applied inline.
SEGMENTS = {
    "micro": {"size": 150.0, "LIN": 0.0,    "SAT": 1500.0, "K": 3.0},
    "core":  {"size": 95.0,  "LIN": 1600.0, "SAT": 1900.0, "K": 2.2},
    "scale": {"size": 30.0,  "LIN": 9000.0, "SAT": 2200.0, "K": 2.0},
}


def value(seg: str, q: float) -> float:
    s = SEGMENTS[seg]
    return (s["LIN"] * q + s["SAT"] * (1.0 - math.exp(-s["K"] * q))) * VALUE_HAIRCUT


def deliv(q: float) -> float:
    return (D_BASE + D_SLOPE * q + D_QUAD * q * q) * D_PENALTY


def oversight_h(q: float) -> float:
    return (OH_BASE + OH_SLOPE * q) * OH_PENALTY


def _tiers(plan: dict) -> dict:
    t = plan["tiers"]
    if not isinstance(t, dict):
        raise TypeError("tiers must be an object")
    return {name: {"price": float(t[name]["price"]), "scope": float(t[name]["scope"])} for name in TIERS}


def pessimistic_surplus(plan: dict) -> float:
    menu = _tiers(plan)

    picks = {}
    for s in SEGMENTS:
        best_t, best_surplus = None, BUY_THRESHOLD
        for t in TIERS:
            surplus = value(s, menu[t]["scope"]) - menu[t]["price"]
            if surplus > best_surplus + 1e-9:
                best_surplus, best_t = surplus, t
        picks[s] = best_t

    rows = {}
    load = 0.0
    for s in SEGMENTS:
        t = picks[s]
        if t is None:
            rows[s] = {"tier": None, "buyers": 0.0, "scope": 0.0, "margin_mo": 0.0}
            continue
        q = menu[t]["scope"]
        size = SEGMENTS[s]["size"] * SIZE_HAIRCUT
        rows[s] = {"tier": t, "buyers": size, "scope": q, "margin_mo": menu[t]["price"] - deliv(q)}
        load += size * max(q, MIN_LOAD)

    if load > CAP_CLIENT_EQUIV:
        active = [s for s in SEGMENTS if rows[s]["tier"]]
        order = sorted(active, key=lambda s: -(rows[s]["margin_mo"] / max(rows[s]["scope"], MIN_LOAD)))
        remaining = CAP_CLIENT_EQUIV
        for s in active:
            rows[s]["buyers"] = 0.0
        for s in order:
            per = max(rows[s]["scope"], MIN_LOAD)
            take = min(SEGMENTS[s]["size"] * SIZE_HAIRCUT, remaining / per)
            rows[s]["buyers"] = take
            remaining = max(0.0, remaining - take * per)

    total = 0.0
    for s in SEGMENTS:
        r = rows[s]
        if not r["tier"] or r["buyers"] <= 0:
            continue
        contribution = r["margin_mo"] * LIFETIME_MONTHS * r["buyers"]
        owner_cost = oversight_h(r["scope"]) * LIFETIME_MONTHS * OPP_RATE_EUR_HR * r["buyers"]
        total += contribution - owner_cost
    return total


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: pricing-tiers-stress-guard.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        net = pessimistic_surplus(plan)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot evaluate stress floor ({type(e).__name__}): {e}", file=sys.stderr)
        return 2
    ok = net >= STRESS_FLOOR
    print(f"pessimistic contribution surplus = EUR {net:,.0f} ({net / 1000.0:.2f} kEUR)  "
          f"(floor {STRESS_FLOOR:.2f})")
    print("STRESS FLOOR PASS" if ok else "STRESS FLOOR FAIL: menu only wins under optimistic WTP")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
