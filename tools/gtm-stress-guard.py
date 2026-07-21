# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: pessimistic-case floor on GTM plan margin (the anti-overfit lock).

RECIPES constructed-metric rule 3 ("held-out score floor, mandatory") and rule 2
("dual-score when the instrument is unreliable"). The scorer (tools/scorers/
gtm-roi.py) rewards CENTRAL-case margin/hr over a 30-month horizon; a hill-climb
will drift toward whatever the central assumptions reward. This guard is an
INDEPENDENT reimplementation of the same 30-month model under a PESSIMISTIC
parameter set, and it fails the round if the plan's pessimistic margin/hr drops
below STRESS_FLOOR.

Floor = 0.0 EUR/hr: even in the bad case, the plan must earn AT LEAST the hourly-work
fallback (opportunity cost is already netted out, so >= 0 means "no worse than
grinding hourly"). A plan that only wins under optimism fails here and is discarded
even when it beats the current best central score.

Deliberately separate code from the scorer: a shared bug cannot hide in both, and
drift between them is a signal to re-review. Kept economically in lockstep with
gtm-roi.py at pin time.

Exit 0 = pessimistic margin/hr >= floor. Exit 1 = below floor. Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STRESS_FLOOR_EUR_HR = 0.0

# Pessimistic reality parameters: central case with adverse haircuts.
#   conversion x0.5, realized price/retainer x0.85, client lifetimes x0.7, caps x0.7.
PESSIMISTIC = {
    "horizon_months": 30.0,
    "eur_usd": 0.92,
    "opportunity_rate_eur_hr": 33.0,
    "weeks_per_year": 48.0,
    "tool_cost_eur_mo": 200.0,
    "r1_template_hours": 20.0,
    "r1_customize_hours": 6.0,
    "r1_ref_price_build": 2000.0,
    "r1_conv_base": 0.22 * 0.5,          # conversion halved
    "r1_price_elasticity": 0.6,
    "r1_care_lifetime_months": 18.0 * 0.7,  # worse retention
    "r1_segment_pool_yr": {                 # tighter saturation
        "handwerk": 60.0 * 0.7, "physio": 35.0 * 0.7, "beauty": 45.0 * 0.7,
        "medical": 25.0 * 0.7, "food": 40.0 * 0.7,
    },
    "r2_prospects_per_hr_cold": 35.0,
    "r2_prospects_per_hr_referral": 3.0,
    "r2_acq_fraction": 0.55,
    "r2_reply_rate": 0.03 * 0.5,         # cold funnel halved
    "r2_meeting_from_reply": 0.35,
    "r2_close_from_meeting": 0.22,
    "r2_referral_conv": 0.12 * 0.5,      # referral conv halved
    "r2_bounce_verified": 0.02,
    "r2_ref_retainer": 1200.0,
    "r2_retainer_elasticity": 0.4,
    "r2_retainer_lifetime_months": 14.0 * 0.7,  # worse churn
    "r2_service_hours_client_mo": 6.0,
    "r2_market_cap_yr": 25.0 * 0.7,             # tighter market
    "price_realized_factor": 0.85,              # discounting under pressure
}


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def pessimistic_margin_per_hour(plan: dict, p: dict) -> float:
    horizon = p["horizon_months"]
    years = horizon / 12.0
    cap_total = float(plan["capacity_hours_per_week"]) * p["weeks_per_year"] * years
    alloc = plan["route_allocation"]
    h_local = cap_total * float(alloc["local_smb"])
    h_b2b = cap_total * float(alloc["b2b_lead_gen"])
    disc = p["price_realized_factor"]

    l = plan["local_smb"]
    pb_list = float(l["price_build_eur"])
    pb = pb_list * disc
    pc = float(l["price_care_eur_mo"]) * disc
    care_months = min(p["r1_care_lifetime_months"], horizon)
    rev1 = 0.0
    if h_local > p["r1_template_hours"]:
        demos = (h_local - p["r1_template_hours"]) / p["r1_customize_hours"]
        demos_eff = min(demos, p["r1_segment_pool_yr"][l["segment"]] * years)
        conv1 = _clamp(
            p["r1_conv_base"] * (1.0 - p["r1_price_elasticity"] * (pb_list - p["r1_ref_price_build"]) / p["r1_ref_price_build"]),
            0.02, 1.3 * p["r1_conv_base"])
        rev1 = demos_eff * conv1 * (pb + pc * care_months)

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
    prospects = h_b2b * p["r2_acq_fraction"] * pph
    clients2 = min(prospects * base_conv * ret_factor * (1.0 - p["r2_bounce_verified"]), p["r2_market_cap_yr"] * years)
    ret_months = min(p["r2_retainer_lifetime_months"], horizon)
    per_client_service_h = p["r2_service_hours_client_mo"] * ret_months
    serviceable = (h_b2b * (1.0 - p["r2_acq_fraction"])) / per_client_service_h if per_client_service_h > 0 else clients2
    clients2 = min(clients2, serviceable)
    rev2 = clients2 * ret_realized * ret_months

    hours = h_local + h_b2b
    if hours <= 0:
        raise ValueError("plan allocates zero hours")
    margin = (rev1 + rev2) - p["tool_cost_eur_mo"] * horizon - hours * p["opportunity_rate_eur_hr"]
    return margin / hours


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: gtm-stress-guard.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        mph = pessimistic_margin_per_hour(plan, PESSIMISTIC)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot evaluate stress floor ({type(e).__name__}): {e}", file=sys.stderr)
        return 2
    ok = mph >= STRESS_FLOOR_EUR_HR
    print(f"pessimistic margin/hr = EUR {mph:.2f}  (floor {STRESS_FLOOR_EUR_HR:.2f})")
    print("STRESS FLOOR PASS" if ok else "STRESS FLOOR FAIL: plan only wins under optimism")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
