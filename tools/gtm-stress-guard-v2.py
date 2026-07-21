# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard v2: pessimistic-case floor on GTM-v2 plan margin (the anti-overfit lock).

RECIPES constructed-metric rule 3 ("held-out score floor, mandatory") and rule 2
("dual-score when the instrument is unreliable"). The scorer (tools/scorers/
gtm-roi-v2.py) rewards CENTRAL-case TOTAL contribution surplus over a 30-month
horizon; a hill-climb drifts toward whatever the central assumptions reward.
This guard is an INDEPENDENT reimplementation of the same v2 model (care-price
elasticity + subcontracted delivery + freed-hour reinvestment) under a
PESSIMISTIC parameter set, and it fails the round if the plan's pessimistic
TOTAL surplus drops below STRESS_FLOOR.

Floor = 0.0: even in the bad case, the plan's total contribution surplus above
the hourly-work fallback must be non-negative (opportunity cost is already
netted out, so >= 0 means "no worse than grinding hourly"). A plan that only
wins under optimism fails here and is discarded even when it beats the current
best central score. (Sign-equivalent to a per-hour floor since productive
hours > 0; reported as total surplus to match the v2 scorer's unit.)

Pessimistic haircuts vs central (adverse but not absurd):
  conversion x0.5, realized price/retainer x0.85, client lifetimes x0.7,
  caps x0.7, AND the v2-specific adverse moves: subcontractor rate x1.3
  (worse delivery-cost spread) and oversight hours x1.5 (worse leverage /
  more coordination drag). If subcontracting only pays under optimism, this
  is where it shows.

Deliberately separate code from the scorer: a shared bug cannot hide in both,
and drift between them is a signal to re-review. Kept economically in lockstep
with gtm-roi-v2.py at pin time.

Exit 0 = pessimistic margin/productive-hr >= floor. Exit 1 = below. Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STRESS_FLOOR = 0.0

PESSIMISTIC = {
    "horizon_months": 30.0,
    "eur_usd": 0.92,
    "opportunity_rate_eur_hr": 33.0,
    "weeks_per_year": 48.0,
    "tool_cost_eur_mo": 200.0,
    "r1_template_hours": 20.0,
    "r1_customize_hours": 6.0,
    "r1_ref_price_build": 2000.0,
    "r1_conv_base": 0.22 * 0.5,             # conversion halved
    "r1_price_elasticity": 0.6,
    "r1_ref_care": 150.0,
    "r1_care_elasticity": 0.6,
    "r1_care_lifetime_months": 18.0 * 0.7,  # worse retention
    "r1_segment_pool_yr": {                 # tighter saturation
        "handwerk": 60.0 * 0.7, "physio": 35.0 * 0.7, "beauty": 45.0 * 0.7,
        "medical": 25.0 * 0.7, "food": 40.0 * 0.7,
    },
    "r2_prospects_per_hr_cold": 35.0,
    "r2_prospects_per_hr_referral": 3.0,
    "r2_acq_fraction": 0.55,
    "r2_reply_rate": 0.03 * 0.5,            # cold funnel halved
    "r2_meeting_from_reply": 0.35,
    "r2_close_from_meeting": 0.22,
    "r2_referral_conv": 0.12 * 0.5,         # referral conv halved
    "r2_bounce_verified": 0.02,
    "r2_ref_retainer": 1200.0,
    "r2_retainer_elasticity": 0.4,
    "r2_retainer_lifetime_months": 14.0 * 0.7,   # worse churn
    "r2_service_hours_client_mo": 6.0,
    "r2_oversight_hours_client_mo": 1.5 * 1.5,   # worse oversight leverage / more coordination drag
    "subcontractor_rate_eur_hr": 20.0 * 1.3,     # worse delivery-cost spread
    "r2_market_cap_yr": 25.0 * 0.7,              # tighter market
    "price_realized_factor": 0.85,               # discounting under pressure
}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def pessimistic_total_surplus(plan: dict, p: dict) -> float:
    horizon = p["horizon_months"]
    years = horizon / 12.0
    cap_total = float(plan["capacity_hours_per_week"]) * p["weeks_per_year"] * years
    alloc = plan["route_allocation"]
    h_local = cap_total * float(alloc["local_smb"])
    h_b2b = cap_total * float(alloc["b2b_lead_gen"])
    disc = p["price_realized_factor"]

    # Route 1 (care price-elastic; realized prices discounted)
    l = plan["local_smb"]
    pb_list = float(l["price_build_eur"])
    pb = pb_list * disc
    pc_list = float(l["price_care_eur_mo"])
    pc = pc_list * disc
    care_months = min(p["r1_care_lifetime_months"], horizon)
    rev1 = 0.0
    h_local_productive = 0.0
    if h_local > p["r1_template_hours"]:
        demos = (h_local - p["r1_template_hours"]) / p["r1_customize_hours"]
        demos_eff = min(demos, p["r1_segment_pool_yr"][l["segment"]] * years)
        conv1 = _clamp(
            p["r1_conv_base"] * (1.0 - p["r1_price_elasticity"] * (pb_list - p["r1_ref_price_build"]) / p["r1_ref_price_build"]),
            0.02, 1.3 * p["r1_conv_base"])
        care_factor = _clamp(
            1.0 - p["r1_care_elasticity"] * (pc_list - p["r1_ref_care"]) / p["r1_ref_care"],
            0.05, 1.3)
        rev1 = demos_eff * conv1 * (pb + pc * care_months * care_factor)
        h_local_productive = p["r1_template_hours"] + demos_eff * p["r1_customize_hours"]

    # Route 2 (subcontracted delivery, oversight-limited)
    b = plan["b2b_lead_gen"]
    ret_list = float(b["retainer_eur_mo"])
    ret_realized = ret_list * disc
    if b["acquisition"] == "cold_email":
        pph = p["r2_prospects_per_hr_cold"]
        base_conv = p["r2_reply_rate"] * p["r2_meeting_from_reply"] * p["r2_close_from_meeting"]
    else:
        pph = p["r2_prospects_per_hr_referral"]
        base_conv = p["r2_referral_conv"]
    ret_factor = _clamp(1.0 - p["r2_retainer_elasticity"] * (ret_list - p["r2_ref_retainer"]) / p["r2_ref_retainer"], 0.1, 1.5)
    per_prospect_client = base_conv * ret_factor * (1.0 - p["r2_bounce_verified"])

    acq_hours = h_b2b * p["r2_acq_fraction"]
    service_hours = h_b2b * (1.0 - p["r2_acq_fraction"])
    ret_months = min(p["r2_retainer_lifetime_months"], horizon)
    acq_output = acq_hours * pph * per_prospect_client
    market_cap_clients = p["r2_market_cap_yr"] * years
    oversight_per_client_h = p["r2_oversight_hours_client_mo"] * ret_months
    oversight_cap = service_hours / oversight_per_client_h if oversight_per_client_h > 0 else acq_output
    clients2 = min(acq_output, market_cap_clients, oversight_cap)

    denom = pph * per_prospect_client
    acq_hours_needed = clients2 / denom if denom > 0 else acq_hours
    acq_hours_productive = min(acq_hours, acq_hours_needed)
    oversight_hours_productive = clients2 * oversight_per_client_h
    h_b2b_productive = acq_hours_productive + oversight_hours_productive

    subcontractor_cost = clients2 * p["r2_service_hours_client_mo"] * ret_months * p["subcontractor_rate_eur_hr"]
    rev2 = clients2 * ret_realized * ret_months

    productive_hours = h_local_productive + h_b2b_productive
    if productive_hours <= 0:
        raise ValueError("plan produces no productive hours")
    margin = (rev1 + rev2) - p["tool_cost_eur_mo"] * horizon - subcontractor_cost - productive_hours * p["opportunity_rate_eur_hr"]
    return margin  # total surplus over the horizon (EUR)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: gtm-stress-guard-v2.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        surplus = pessimistic_total_surplus(plan, PESSIMISTIC)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot evaluate stress floor ({type(e).__name__}): {e}", file=sys.stderr)
        return 2
    ok = surplus >= STRESS_FLOOR
    print(f"pessimistic total surplus = EUR {surplus:,.0f} ({surplus / 1000.0:.2f} kEUR)  "
          f"(floor {STRESS_FLOOR:.2f})")
    print("STRESS FLOOR PASS" if ok else "STRESS FLOOR FAIL: plan only wins under optimism")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
