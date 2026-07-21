# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# direction: maximize
"""Scorer: blended contribution-margin-per-working-hour of an Upwork-independence
GTM plan, over a 30-MONTH horizon, in EUR/hr ABOVE the hourly-work opportunity cost.

The honest-number design (rule_optimize_loop / RECIPES constructed-metric):
the ASSET the agent edits is a plan of DECISIONS ONLY (route mix, prices,
capacity, geo, segment). Every reality parameter that turns a decision into money
(conversion funnels, build hours, saturation caps, deliverability, price
elasticity, client lifetimes, the horizon itself) is LOCKED in CENTRAL below and
cannot be edited during a run (this file is scorer-locked + hash-pinned). The agent
cannot "win" by inflating conversion, price, or horizon past reality; it can only
search the decision space against a fixed model.

Horizon = 30 months (owner directive 2026-07-21, "24-36 months"). This lets the
recurring routes (Route-1 care retainers, Route-2 lead-gen retainers) accrue their
durable value: a client won early is an annuity, which is the whole reason to build
a business instead of grinding hourly. Hours, opportunity cost, tool cost, prospect
pools, and market caps all scale to the 30-month period; each client is credited its
expected recurring lifetime, capped at the horizon, and must be serviceable over that
lifetime within the service-hour budget.

SCORE semantics: EUR of contribution created per working hour ABOVE the hourly-work
fallback (OPPORTUNITY_RATE), across the 30-month build-out. SCORE = 0 ties grinding
hourly; SCORE > 0 is the per-hour premium the GTM buys. Maximize it. The stress-floor
guard (tools/gtm-stress-guard.py) independently re-checks this stays >= 0 under
pessimistic parameters, so an optimism-only plan is discarded even on a score win.

Parameter provenance is tagged inline: SOURCED = traced to a repo memory / verified
market datum; ASSUMPTION = a defensible planning estimate reviewed at pin time.

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
    "r1_price_elasticity": 0.6,      # ASSUMPTION conv multiplier drop per +100% over ref price
    "r1_care_lifetime_months": 18.0, # ASSUMPTION expected care-retainer lifetime (capped at horizon)
    "r1_segment_pool_yr": {          # ASSUMPTION reachable prospects/YEAR per niche before saturation
        "handwerk": 60.0, "physio": 35.0, "beauty": 45.0, "medical": 25.0, "food": 40.0,
    },

    # Route 2 - B2B lead-gen (cold email UK/US only; DE must use referral, see validate guard)
    "r2_prospects_per_hr_cold": 35.0,   # ASSUMPTION list-build + sequence setup amortized
    "r2_prospects_per_hr_referral": 3.0,# ASSUMPTION referral is low-volume by nature
    "r2_acq_fraction": 0.55,            # ASSUMPTION share of route hours on acquisition vs service
    "r2_reply_rate": 0.03,              # ASSUMPTION cold-email positive reply
    "r2_meeting_from_reply": 0.35,      # ASSUMPTION
    "r2_close_from_meeting": 0.22,      # ASSUMPTION -> cold prospect->client ~= 0.0023 at ref retainer
    "r2_referral_conv": 0.12,           # ASSUMPTION referral prospect->client (warm, higher)
    "r2_bounce_verified": 0.02,         # SOURCED OSINT memo: verified-list bounce < 2%
    "r2_ref_retainer": 1200.0,          # ASSUMPTION reference monthly retainer for the elasticity baseline
    "r2_retainer_elasticity": 0.4,      # ASSUMPTION close-rate drop per +100% over ref retainer
    "r2_retainer_lifetime_months": 14.0,# ASSUMPTION expected retainer lifetime (capped at horizon)
    "r2_service_hours_client_mo": 6.0,  # ASSUMPTION ongoing delivery per retained client per month
    "r2_market_cap_yr": 25.0,           # ASSUMPTION reachable UK/US clients/YEAR for a solo operator
}

BOUNDS = {
    "capacity_hours_per_week": (5.0, 45.0),
    "price_build_eur": (1200.0, 4000.0),
    "price_care_eur_mo": (0.0, 300.0),
    "retainer_eur_mo": (500.0, 2500.0),
}
SEGMENTS = ("handwerk", "physio", "beauty", "medical", "food")
GEOS = ("DE", "UK", "US")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute(plan: dict, p: dict) -> dict:
    """Return a breakdown dict incl. 'margin_per_hour'. Pure function of (plan, params)."""
    horizon = p["horizon_months"]
    years = horizon / 12.0
    cap_wk = float(plan["capacity_hours_per_week"])
    cap_total = cap_wk * p["weeks_per_year"] * years  # total working hours over the horizon

    alloc = plan["route_allocation"]
    h_local = cap_total * float(alloc["local_smb"])
    h_b2b = cap_total * float(alloc["b2b_lead_gen"])

    # ---- Route 1: local SMB, demo-first ----
    l = plan["local_smb"]
    pb = float(l["price_build_eur"])
    pc = float(l["price_care_eur_mo"])
    seg = l["segment"]
    pool = p["r1_segment_pool_yr"][seg] * years  # prospects replenish over the horizon
    care_months = min(p["r1_care_lifetime_months"], horizon)
    rev1 = clients1 = demos1 = 0.0
    if h_local > p["r1_template_hours"]:
        demos1 = (h_local - p["r1_template_hours"]) / p["r1_customize_hours"]
        demos_eff = min(demos1, pool)
        conv1 = _clamp(
            p["r1_conv_base"] * (1.0 - p["r1_price_elasticity"] * (pb - p["r1_ref_price_build"]) / p["r1_ref_price_build"]),
            0.02, 1.3 * p["r1_conv_base"],
        )
        clients1 = demos_eff * conv1
        rev1 = clients1 * (pb + pc * care_months)

    # ---- Route 2: B2B lead-gen ----
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
    prospects = h_b2b * p["r2_acq_fraction"] * pph
    clients2 = prospects * conv2 * (1.0 - p["r2_bounce_verified"])
    clients2 = min(clients2, p["r2_market_cap_yr"] * years)
    # A won client must be serviceable over its whole lifetime within the service-hour budget.
    ret_months = min(p["r2_retainer_lifetime_months"], horizon)
    service_budget_h = h_b2b * (1.0 - p["r2_acq_fraction"])
    per_client_service_h = p["r2_service_hours_client_mo"] * ret_months
    max_serviceable = service_budget_h / per_client_service_h if per_client_service_h > 0 else clients2
    clients2 = min(clients2, max_serviceable)
    rev2 = clients2 * ret * ret_months

    # ---- Blend ----
    total_rev = rev1 + rev2
    hours_spent = h_local + h_b2b
    if hours_spent <= 0:
        raise ValueError("plan allocates zero hours; nothing to score")
    tool_cost = p["tool_cost_eur_mo"] * horizon
    opp_cost = hours_spent * p["opportunity_rate_eur_hr"]
    margin = total_rev - tool_cost - opp_cost
    return {
        "horizon": horizon, "cap_total": cap_total, "h_local": h_local, "h_b2b": h_b2b,
        "demos1": demos1, "clients1": clients1, "rev1": rev1,
        "clients2": clients2, "rev2": rev2,
        "total_rev": total_rev, "hours_spent": hours_spent,
        "tool_cost": tool_cost, "opp_cost": opp_cost, "margin": margin,
        "margin_per_hour": margin / hours_spent,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: gtm-roi.py PLAN.json", file=sys.stderr)
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

    print(f"plan: {path}  (horizon {r['horizon']:.0f} months)")
    print(f"  capacity: {plan['capacity_hours_per_week']} h/wk -> {r['cap_total']:.0f} h over horizon "
          f"(local {r['h_local']:.0f}h, b2b {r['h_b2b']:.0f}h)")
    print(f"  route 1 (local/{plan['local_smb']['segment']}): {r['clients1']:.2f} clients from "
          f"{r['demos1']:.1f} demos -> EUR {r['rev1']:,.0f}")
    print(f"  route 2 ({plan['b2b_lead_gen']['geo']}/{plan['b2b_lead_gen']['acquisition']}): "
          f"{r['clients2']:.2f} clients -> EUR {r['rev2']:,.0f}")
    print(f"  revenue EUR {r['total_rev']:,.0f} - tools EUR {r['tool_cost']:,.0f} "
          f"- opportunity EUR {r['opp_cost']:,.0f} = margin EUR {r['margin']:,.0f}")
    print(f"  margin per working hour (above EUR {CENTRAL['opportunity_rate_eur_hr']:.0f}/hr fallback):")
    print(f"SCORE: {r['margin_per_hour']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
