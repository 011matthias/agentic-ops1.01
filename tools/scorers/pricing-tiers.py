# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# direction: maximize
"""Scorer: total contribution surplus of a good/better/best PRICING MENU for the
Upwork-independence B2B lead-generation service, over a 30-MONTH horizon, in kEUR
(above the owner's opportunity cost).

THE QUESTION: "what exactly do we sell, and at what price?" GTM-v2 fixed a single
B2B retainer (~EUR2500/mo) and leadgen-portfolio fixed how clients are won. Neither
priced the OFFER itself. This run designs the packaging: a three-tier menu
(good / better / best), where each tier is a {price, scope} pair, sold to a
heterogeneous population of prospects who SELF-SELECT the tier that maximizes their
own surplus (or buy nothing). This is second-degree price discrimination
(versioning): the whole reason to offer tiers instead of one flat price is that a
flat price forces a bad trade-off between excluding low-value prospects and leaving
money on the table with high-value ones.

THE MODEL
---------
Decision (the asset): tiers.{good,better,best} = {price EUR/mo, scope in [0,1]},
where scope is normalized service intensity (lead volume / channels / reporting
depth; 1.0 = the fullest package offered). Locked: three prospect segments, each
self-selecting; the scope->value and scope->cost curves; delivery capacity.

Per-month value a segment s gets from scope q:
  value(s,q) = LIN[s]*q + SAT[s]*(1 - exp(-K[s]*q))
LIN is value that scales with service volume (a bigger client absorbs more leads ->
proportionally more revenue); SAT is a saturating base that caps out. micro is
pure-saturating (caps fast, low ceiling); scale is linear-dominated (value keeps
climbing with scope). That single-crossing structure is what makes tiering pay.

Delivery cost per month at scope q (subcontracted, from GTM-v2 economics):
  deliv(q) = DBASE + DSLOPE*q + DQUAD*q^2      (CONVEX: coordinating a high-volume
                                                engagement is disproportionately harder)
Owner oversight hours per client-month rise with scope too:
  oversight(q) = OH_BASE + OH_SLOPE*q          (a high-touch engagement needs more
                                                of the solo's attention than a thin one)

Each segment picks the tier maximizing monthly surplus value(s,q_t) - price_t if
that surplus is positive, else buys nothing. A buyer yields, over its lifetime:
  (price_t - deliv(q_t)) * LIFETIME             contribution
  - oversight(q_t) * LIFETIME * OPP_RATE        the owner's own time, at opportunity cost
Delivery capacity binds as a scope-weighted client-equivalent cap over the horizon;
when it binds, the highest-margin-per-delivery-load segments are kept (you cannot
bank clients you cannot service, and scarce delivery goes to the efficient ones).

SCORE = sum over buyers of that net contribution, in kEUR, over 30 months. Maximize.
The scorer also prints the best SINGLE FLAT price for contrast: the tiering lift
(3-tier surplus minus best-flat surplus) is the headline result -- it is the money
that versioning captures over one-size-fits-all pricing.

NOT comparable to the GTM scorers' numbers -- different asset, different metric.
gtm-roi-v2 optimized delivery+pricing of ONE retainer; leadgen-portfolio optimized
acquisition; this optimizes the tier MENU.

Parameter provenance is tagged inline: SOURCED = traced to GTM-v2 locked economics /
a repo memory / verified datum; ASSUMPTION = a defensible planning estimate reviewed
at pin time (the PR review is the honesty gate). The segment WTP distribution is the
load-bearing assumption; the stress guard haircuts it and the RANKING of menus is
more stable than the absolute EUR.

Deterministic: pure arithmetic over the plan file, no network, no timing, no RNG.

Contract (tools/scorers/README.md): last stdout line is `SCORE: <number>`, exit 0
only on a successful measurement.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# --- LOCKED horizon + owner economics (central case) -------------------------
HORIZON_MONTHS = 30.0          # owner directive 2026-07-21 (24-36mo); matches GTM v2 + leadgen
LIFETIME_MONTHS = 14.0         # SOURCED GTM v2 retainer lifetime
OPP_RATE_EUR_HR = 33.0         # SOURCED user_rates_unpauseai ($36/hr low end -> ~EUR33)
OH_BASE = 1.0                  # SOURCED-adjacent GTM v2 (~1.5 h/client/mo oversight at mid scope)
OH_SLOPE = 1.6                 # ASSUMPTION extra oversight h/client/mo per unit scope (high-touch costs more attention)

# --- LOCKED delivery-cost model (subcontracted, EUR/client-month) ------------
D_BASE = 120.0                 # ASSUMPTION min subcontractor + tooling at scope 0
D_SLOPE = 450.0                # ASSUMPTION linear marginal delivery cost per unit scope
D_QUAD = 350.0                 # ASSUMPTION convex coordination overhead (full scope ~EUR920/mo)

# --- LOCKED delivery capacity ------------------------------------------------
CAP_CLIENT_EQUIV = 150.0       # SOURCED-adjacent: leadgen serviceable ~110 + subcontract headroom;
                               # scope-weighted client-equivalents over the horizon
MIN_LOAD = 0.15                # a thin client still consumes some delivery capacity

# --- LOCKED prospect segments (reaching the buy decision over the horizon) ---
#  size = # prospects; value(q) = LIN*q + SAT*(1 - exp(-K*q)) EUR/month
#  micro: numerous, low WTP, saturates early -> a cheap thin entry tier
#  core:  the workhorse (~the GTM v2 EUR2500 retainer client)
#  scale: few, absorbs volume, value climbs with scope -> pays for a premium tier
SEGMENTS = {
    "micro": {"size": 150.0, "LIN": 0.0,    "SAT": 1500.0, "K": 3.0},   # ASSUMPTION
    "core":  {"size": 95.0,  "LIN": 1600.0, "SAT": 1900.0, "K": 2.2},   # ASSUMPTION (anchored to GTM v2)
    "scale": {"size": 30.0,  "LIN": 9000.0, "SAT": 2200.0, "K": 2.0},   # ASSUMPTION
}
TIERS = ("good", "better", "best")


def value(seg: str, q: float) -> float:
    s = SEGMENTS[seg]
    return s["LIN"] * q + s["SAT"] * (1.0 - math.exp(-s["K"] * q))


def deliv(q: float) -> float:
    return D_BASE + D_SLOPE * q + D_QUAD * q * q


def oversight_h(q: float) -> float:
    return OH_BASE + OH_SLOPE * q


def _tiers(plan: dict) -> dict:
    t = plan["tiers"]
    if not isinstance(t, dict):
        raise TypeError("tiers must be an object")
    out = {}
    for name in TIERS:
        row = t[name]
        out[name] = {"price": float(row["price"]), "scope": float(row["scope"])}
    return out


def choose_tier(seg: str, menu: dict) -> str | None:
    """Segment picks the offered tier maximizing monthly surplus (>0), else None."""
    best_t, best_surplus = None, 0.0     # 0 = the outside option (buy nothing)
    for t in TIERS:
        surplus = value(seg, menu[t]["scope"]) - menu[t]["price"]
        if surplus > best_surplus + 1e-9:
            best_surplus, best_t = surplus, t
    return best_t


def compute(plan: dict) -> dict:
    """Pure function of the plan. Returns a breakdown incl. 'surplus_eur'."""
    menu = _tiers(plan)
    picks = {s: choose_tier(s, menu) for s in SEGMENTS}

    rows: dict[str, dict] = {}
    load = 0.0
    for s in SEGMENTS:
        t = picks[s]
        if t is None:
            rows[s] = {"tier": None, "buyers": 0.0, "scope": 0.0, "margin_mo": 0.0}
            continue
        q = menu[t]["scope"]
        rows[s] = {"tier": t, "buyers": SEGMENTS[s]["size"], "scope": q,
                   "margin_mo": menu[t]["price"] - deliv(q)}
        load += SEGMENTS[s]["size"] * max(q, MIN_LOAD)

    # Capacity: when scope-weighted load exceeds the cap, fill it with the highest
    # margin-per-delivery-load segments first (scarce delivery goes to the efficient
    # ones; you cannot bank clients you cannot service).
    capped = load > CAP_CLIENT_EQUIV
    if capped:
        active = [s for s in SEGMENTS if rows[s]["tier"]]
        order = sorted(active, key=lambda s: -(rows[s]["margin_mo"] / max(rows[s]["scope"], MIN_LOAD)))
        remaining = CAP_CLIENT_EQUIV
        for s in active:
            rows[s]["buyers"] = 0.0
        for s in order:
            per = max(rows[s]["scope"], MIN_LOAD)
            take = min(SEGMENTS[s]["size"], remaining / per)
            rows[s]["buyers"] = take
            remaining = max(0.0, remaining - take * per)

    surplus = 0.0
    for s in SEGMENTS:
        r = rows[s]
        if not r["tier"] or r["buyers"] <= 0:
            continue
        contribution = r["margin_mo"] * LIFETIME_MONTHS * r["buyers"]
        owner_cost = oversight_h(r["scope"]) * LIFETIME_MONTHS * OPP_RATE_EUR_HR * r["buyers"]
        surplus += contribution - owner_cost

    return {"menu": menu, "picks": picks, "rows": rows,
            "load": load, "capped": capped, "surplus_eur": surplus}


def _best_flat_surplus() -> tuple[float, float, float]:
    """Best single flat (one price, one scope) plan, for the tiering-lift contrast."""
    best = (-1e18, 0.0, 0.0)
    q = 0.05
    while q <= 1.0 + 1e-9:
        pr = 400.0
        while pr <= 12000.0 + 1e-9:
            flat = {"tiers": {t: {"price": pr, "scope": q} for t in TIERS}}
            sc = compute(flat)["surplus_eur"]
            if sc > best[0]:
                best = (sc, pr, q)
            pr += 200.0
        q += 0.05
    return best


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: pricing-tiers.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        r = compute(plan)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot score plan ({type(e).__name__}): {e}", file=sys.stderr)
        return 2

    print(f"plan: {path}  (horizon {HORIZON_MONTHS:.0f} months, lifetime {LIFETIME_MONTHS:.0f} months)")
    for t in TIERS:
        m = r["menu"][t]
        print(f"  {t:6} EUR{m['price']:>6,.0f}/mo  scope {m['scope']:.2f}  "
              f"deliv EUR{deliv(m['scope']):.0f}/mo  margin EUR{m['price'] - deliv(m['scope']):.0f}/mo")
    for s in SEGMENTS:
        row = r["rows"][s]
        pick = row["tier"] or "(none)"
        print(f"  segment {s:6} ({SEGMENTS[s]['size']:.0f} prospects) -> {pick:7}  "
              f"buyers {row['buyers']:5.1f}")
    print(f"  delivery load {r['load']:.0f}/{CAP_CLIENT_EQUIV:.0f} client-equiv"
          f"{' (BINDING)' if r['capped'] else ''}")
    flat_sc, flat_pr, flat_q = _best_flat_surplus()
    lift = r["surplus_eur"] - flat_sc
    print(f"  contrast: best SINGLE FLAT price EUR{flat_pr:,.0f}/mo scope {flat_q:.2f} "
          f"-> {flat_sc / 1000.0:,.1f} kEUR; tiering lift {lift / 1000.0:+,.1f} kEUR")
    print("  SCORE = total contribution surplus over the 30-month horizon, in kEUR (maximize):")
    print(f"SCORE: {r['surplus_eur'] / 1000.0:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
