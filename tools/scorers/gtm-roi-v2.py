# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# direction: maximize
"""Scorer v2: total blended contribution SURPLUS of an Upwork-independence GTM
plan, over a 30-MONTH horizon, in kEUR ABOVE the hourly-work opportunity cost.

WHAT CHANGED FROM v1 (tools/scorers/gtm-roi.py) AND WHY
-------------------------------------------------------
v1 pegged levers to their bounds because the model had no resistance there
(see docs/optimize/upwork-independence-gtm-v1/SUMMARY.md): care price hit its
ceiling (no care-price elasticity), and capacity collapsed toward the low end
(freed hours were charged full opportunity cost and could not be reinvested, so
a per-hour metric punished every hour past channel saturation). v2 adds the two
terms that give those levers resistance, and re-frames the objective so
"reinvest freed hours" means what it means for THIS owner's goal.

(a) CARE-PRICE ELASTICITY. Care revenue per client is scaled by a demand
    multiplier `clamp(1 - r1_care_elasticity*(pc-r1_ref_care)/r1_ref_care)`,
    structurally identical to the build-price and retainer elasticities v1
    already had. Higher care price lifts revenue but sheds uptake/retention;
    pc*care_factor(pc) has an interior maximum (~EUR200/mo at the pinned
    params), so care stops pegging to the ceiling.

(b) SUBCONTRACTING + FREED-HOUR REINVESTMENT. Two coupled changes:
    - Subcontracting: Route-2 delivery can be run by a subcontractor at
      `subcontractor_rate_eur_hr` while you spend only
      `r2_oversight_hours_client_mo` of YOUR time per client on QA/coordination
      (vs the full `r2_service_hours_client_mo` of solo delivery). This ~4x
      leverage means Route-2 client count is bounded by the MARKET and by your
      OVERSIGHT capacity, not by solo delivery hours as in v1 — so added
      capacity produces more served clients up to the caps.
    - Freed-hour reinvestment: hours a plan cannot use productively (local
      demos past pool saturation, acquisition past the market cap, service
      hours past what the served clients need) are treated as reinvested at
      the opportunity rate. They earn exactly the fallback, so their SURPLUS
      (contribution ABOVE the fallback) is zero. Idle capacity is therefore
      NEUTRAL, not a drag: capacity settles at the knee that saturates the
      productive channels, instead of the v1 floor artifact.

WHY TOTAL SURPLUS, NOT EUR-PER-HOUR (a deliberate metric change; flag for review)
--------------------------------------------------------------------------------
v1 scored EUR margin per working hour. Combined with reinvestment, a per-hour
metric develops a pathology that fights the owner's actual goal: it rewards
concentrating on the single highest-premium activity and reinvesting everything
else, because adding a second still-profitable (above-opportunity) channel
lowers the per-hour AVERAGE. Under the v2 model that produces a mono-channel
corner (allocation pegged to b2b=1.0) — the exact "bound artifact" this v2 set
out to remove — and "reinvest the rest at the hourly rate" is literally the
Upwork hourly grind the owner is trying to escape. The owner's goal is durable
TOTAL independence income. So v2 maximizes TOTAL contribution surplus over the
horizon: every above-opportunity productive use is filled (mixed allocation up
to each channel's cap), idle hours are neutral (reinvested), and the number IS
the independence prize in EUR. The per-productive-hour figure is still printed
as a secondary readout. NOT comparable to v1's number — different metric;
compare each run's baseline->final internally, and the two WINNERS by their
DECISIONS, not their scores.

Everything else is carried over from v1 unchanged: the decision asset is a plan
of DECISIONS ONLY; every reality parameter that turns a decision into money is
LOCKED here and hash-pinned (tools/scorers/PINS.json), so the agent cannot win
by inflating conversion, price, or horizon past reality. The legal fence (no DE
cold email) and the schema/bounds guard are the UNCHANGED
tools/gtm-plan-validate.py; the anti-optimism floor is the v2 reimplementation
tools/gtm-stress-guard-v2.py.

Parameter provenance is tagged inline: SOURCED = traced to a repo memory /
verified market datum; ASSUMPTION = a defensible planning estimate reviewed at
pin time (the PR review is the honesty gate).

Deterministic: pure arithmetic over the plan file, no network, no timing, no RNG.

Contract (tools/scorers/README.md): last stdout line is `SCORE: <number>`,
exit 0 only on a successful measurement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# --- LOCKED reality parameters (central case) --------------------------------
CENTRAL = {
    # Global
    "horizon_months": 30.0,          # owner directive 2026-07-21 (24-36mo); midpoint
    "eur_usd": 0.92,                 # ASSUMPTION market FX
    "opportunity_rate_eur_hr": 33.0, # SOURCED user_rates_unpauseai: $36/hr low end -> ~EUR33 (conservative)
    "weeks_per_year": 48.0,          # ASSUMPTION 48 working weeks/yr (4 off)
    "tool_cost_eur_mo": 200.0,       # ASSUMPTION Apollo+Instantly+hosting bundle

    # Route 1 - local SMB, demo-first (legal in DE; cold email is NOT, see validate guard)
    "r1_template_hours": 20.0,       # ASSUMPTION one-time per segment to a 13-gate site template
    "r1_customize_hours": 6.0,       # ASSUMPTION per-prospect bespoke demo off the template
    "r1_ref_price_build": 2000.0,    # ASSUMPTION reference build price for the conversion baseline
    "r1_conv_base": 0.22,            # ASSUMPTION demo->client at ref price (memory: demo-first = high-conversion wedge)
    "r1_price_elasticity": 0.6,      # ASSUMPTION conv multiplier drop per +100% over ref build price
    "r1_ref_care": 150.0,            # ASSUMPTION v2-NEW: reference care retainer (market EUR50-300/mo website-care; midpoint)
    "r1_care_elasticity": 0.6,       # ASSUMPTION v2-NEW: care uptake/retention multiplier drop per +100% over ref care
                                     #   (magnitude mirrors the build 0.6 / retainer 0.4 elasticities);
                                     #   yields an interior care optimum ~EUR200/mo (see docstring)
    "r1_care_lifetime_months": 18.0, # ASSUMPTION expected care-retainer lifetime (capped at horizon)
    "r1_segment_pool_yr": {          # ASSUMPTION reachable prospects/YEAR per niche before saturation
        "handwerk": 60.0, "physio": 35.0, "beauty": 45.0, "medical": 25.0, "food": 40.0,
    },

    # Route 2 - B2B lead-gen (cold email UK/US only; DE must use referral, see validate guard)
    "r2_prospects_per_hr_cold": 35.0,   # ASSUMPTION list-build + sequence setup amortized
    "r2_prospects_per_hr_referral": 3.0,# ASSUMPTION referral is low-volume by nature
    "r2_acq_fraction": 0.55,            # ASSUMPTION share of route hours on acquisition vs service/oversight
    "r2_reply_rate": 0.03,              # ASSUMPTION cold-email positive reply
    "r2_meeting_from_reply": 0.35,      # ASSUMPTION
    "r2_close_from_meeting": 0.22,      # ASSUMPTION -> cold prospect->client ~= 0.0023 at ref retainer
    "r2_referral_conv": 0.12,           # ASSUMPTION referral prospect->client (warm, higher)
    "r2_bounce_verified": 0.02,         # SOURCED OSINT memo: verified-list bounce < 2%
    "r2_ref_retainer": 1200.0,          # ASSUMPTION reference monthly retainer for the elasticity baseline
    "r2_retainer_elasticity": 0.4,      # ASSUMPTION close-rate drop per +100% over ref retainer
    "r2_retainer_lifetime_months": 14.0,# ASSUMPTION expected retainer lifetime (capped at horizon)
    "r2_service_hours_client_mo": 6.0,  # ASSUMPTION full ongoing delivery per retained client per month
    "r2_oversight_hours_client_mo": 1.5,# ASSUMPTION v2-NEW: YOUR QA/coordination hours per SUBCONTRACTED client/mo
                                        #   (vs 6h full solo delivery -> ~4x service leverage)
    "subcontractor_rate_eur_hr": 20.0,  # ASSUMPTION v2-NEW: blended near-shore/EU delivery-subcontractor cost;
                                        #   below the EUR33/hr opportunity rate, far below billable value
    "r2_market_cap_yr": 25.0,           # ASSUMPTION reachable UK/US clients/YEAR for a solo operator (+ subcontract bench)
}

BOUNDS = {
    "capacity_hours_per_week": (5.0, 45.0),
    "price_build_eur": (1200.0, 4000.0),
    "price_care_eur_mo": (0.0, 300.0),   # care optimum ~200 is interior -> ceiling stays non-binding (validate guard reused)
    "retainer_eur_mo": (500.0, 2500.0),
}
SEGMENTS = ("handwerk", "physio", "beauty", "medical", "food")
GEOS = ("DE", "UK", "US")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute(plan: dict, p: dict) -> dict:
    """Return a breakdown dict incl. 'margin' (total surplus) and
    'margin_per_productive_hour'. Pure function of (plan, params)."""
    horizon = p["horizon_months"]
    years = horizon / 12.0
    cap_wk = float(plan["capacity_hours_per_week"])
    cap_total = cap_wk * p["weeks_per_year"] * years  # total working hours available over the horizon

    alloc = plan["route_allocation"]
    h_local = cap_total * float(alloc["local_smb"])
    h_b2b = cap_total * float(alloc["b2b_lead_gen"])

    # ---- Route 1: local SMB, demo-first (care now price-elastic) ----
    l = plan["local_smb"]
    pb = float(l["price_build_eur"])
    pc = float(l["price_care_eur_mo"])
    seg = l["segment"]
    pool = p["r1_segment_pool_yr"][seg] * years  # prospects replenish over the horizon
    care_months = min(p["r1_care_lifetime_months"], horizon)
    rev1 = clients1 = demos1 = 0.0
    h_local_productive = 0.0
    if h_local > p["r1_template_hours"]:
        demos1 = (h_local - p["r1_template_hours"]) / p["r1_customize_hours"]
        demos_eff = min(demos1, pool)   # demos beyond the reachable pool produce nothing (reinvested)
        conv1 = _clamp(
            p["r1_conv_base"] * (1.0 - p["r1_price_elasticity"] * (pb - p["r1_ref_price_build"]) / p["r1_ref_price_build"]),
            0.02, 1.3 * p["r1_conv_base"],
        )
        # v2-NEW: care revenue scaled by a price-elastic demand factor -> interior care optimum.
        care_factor = _clamp(
            1.0 - p["r1_care_elasticity"] * (pc - p["r1_ref_care"]) / p["r1_ref_care"],
            0.05, 1.3,
        )
        clients1 = demos_eff * conv1
        rev1 = clients1 * (pb + pc * care_months * care_factor)
        # productive local hours = template + only the demos that fell within the pool
        h_local_productive = p["r1_template_hours"] + demos_eff * p["r1_customize_hours"]

    # ---- Route 2: B2B lead-gen (subcontracted delivery, oversight-limited) ----
    b = plan["b2b_lead_gen"]
    ret = float(b["retainer_eur_mo"])
    if b["acquisition"] == "cold_email":
        pph = p["r2_prospects_per_hr_cold"]
        base_conv = p["r2_reply_rate"] * p["r2_meeting_from_reply"] * p["r2_close_from_meeting"]
    else:  # referral
        pph = p["r2_prospects_per_hr_referral"]
        base_conv = p["r2_referral_conv"]
    ret_factor = _clamp(1.0 - p["r2_retainer_elasticity"] * (ret - p["r2_ref_retainer"]) / p["r2_ref_retainer"], 0.1, 1.5)
    conv2 = base_conv * ret_factor
    per_prospect_client = conv2 * (1.0 - p["r2_bounce_verified"])  # clients per acquired prospect

    acq_hours = h_b2b * p["r2_acq_fraction"]
    service_hours = h_b2b * (1.0 - p["r2_acq_fraction"])
    ret_months = min(p["r2_retainer_lifetime_months"], horizon)

    # Three independent ceilings on served clients; the binding one wins.
    acq_output = acq_hours * pph * per_prospect_client                    # what the funnel can generate
    market_cap_clients = p["r2_market_cap_yr"] * years                    # what the market holds
    oversight_per_client_h = p["r2_oversight_hours_client_mo"] * ret_months
    oversight_cap = service_hours / oversight_per_client_h if oversight_per_client_h > 0 else acq_output
    clients2 = min(acq_output, market_cap_clients, oversight_cap)

    # Productive Route-2 hours = acquisition actually needed for clients2 + your oversight of clients2.
    # (Acquisition hours past the point that saturates the served demand are reinvested.)
    denom = pph * per_prospect_client
    acq_hours_needed = clients2 / denom if denom > 0 else acq_hours
    acq_hours_productive = min(acq_hours, acq_hours_needed)
    oversight_hours_productive = clients2 * oversight_per_client_h
    h_b2b_productive = acq_hours_productive + oversight_hours_productive

    # Subcontractors run the full delivery (6h/client/mo) at the subcontractor rate.
    subcontractor_hours = clients2 * p["r2_service_hours_client_mo"] * ret_months
    subcontractor_cost = subcontractor_hours * p["subcontractor_rate_eur_hr"]
    rev2 = clients2 * ret * ret_months

    # ---- Blend: total contribution surplus with freed-hour reinvestment ----
    # Idle capacity reinvests at the opportunity rate, so its surplus (contribution
    # ABOVE the fallback) is zero: only productive hours bear the opportunity cost.
    total_rev = rev1 + rev2
    productive_hours = h_local_productive + h_b2b_productive
    idle_hours = max(0.0, cap_total - productive_hours)
    if productive_hours <= 0:
        raise ValueError("plan produces no productive hours; nothing to score")
    tool_cost = p["tool_cost_eur_mo"] * horizon
    opp_cost = productive_hours * p["opportunity_rate_eur_hr"]
    margin = total_rev - tool_cost - subcontractor_cost - opp_cost  # total surplus over the horizon (EUR)
    return {
        "horizon": horizon, "cap_total": cap_total, "h_local": h_local, "h_b2b": h_b2b,
        "demos1": demos1, "clients1": clients1, "rev1": rev1,
        "clients2": clients2, "rev2": rev2, "subcontractor_cost": subcontractor_cost,
        "acq_output": acq_output, "market_cap_clients": market_cap_clients, "oversight_cap": oversight_cap,
        "total_rev": total_rev, "productive_hours": productive_hours, "idle_hours": idle_hours,
        "tool_cost": tool_cost, "opp_cost": opp_cost, "margin": margin,
        "margin_per_productive_hour": margin / productive_hours,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: gtm-roi-v2.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        r = compute(plan, CENTRAL)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot score plan ({type(e).__name__}): {e}", file=sys.stderr)
        return 2

    b = plan["b2b_lead_gen"]
    opp = CENTRAL["opportunity_rate_eur_hr"]
    which_cap = min(("acq", r["acq_output"]), ("market", r["market_cap_clients"]),
                    ("oversight", r["oversight_cap"]), key=lambda t: t[1])[0]
    print(f"plan: {path}  (horizon {r['horizon']:.0f} months)")
    print(f"  capacity: {plan['capacity_hours_per_week']} h/wk -> {r['cap_total']:.0f} h available "
          f"({r['productive_hours']:.0f}h productive, {r['idle_hours']:.0f}h reinvested)")
    print(f"  route 1 (local/{plan['local_smb']['segment']}): {r['clients1']:.2f} clients from "
          f"{r['demos1']:.1f} demos -> EUR {r['rev1']:,.0f}")
    print(f"  route 2 ({b['geo']}/{b['acquisition']}): {r['clients2']:.2f} clients "
          f"(binding cap: {which_cap}) -> EUR {r['rev2']:,.0f}; subcontractor cost EUR {r['subcontractor_cost']:,.0f}")
    print(f"  revenue EUR {r['total_rev']:,.0f} - tools EUR {r['tool_cost']:,.0f} "
          f"- subcontract EUR {r['subcontractor_cost']:,.0f} - opportunity EUR {r['opp_cost']:,.0f} "
          f"= surplus EUR {r['margin']:,.0f}")
    print(f"  secondary readout: EUR {r['margin_per_productive_hour']:.2f} surplus per PRODUCTIVE hour "
          f"(above the EUR {opp:.0f}/hr fallback)")
    print("  SCORE = total contribution surplus over the 30-month horizon, in kEUR (maximize):")
    print(f"SCORE: {r['margin'] / 1000.0:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
