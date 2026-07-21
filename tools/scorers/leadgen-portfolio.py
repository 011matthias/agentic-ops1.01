# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
# direction: maximize
"""Scorer: net won-client VALUE of an Upwork-independence client-acquisition
portfolio, over a 30-MONTH horizon, in kEUR (client contribution won, minus the
acquisition cost of winning them).

THE QUESTION: "how are we going to win clients?" The GTM-v2 run
(tools/scorers/gtm-roi-v2.py) optimized DELIVERY + PRICING and found the winner
capped by MARKET REACH (Route-2 ~25 clients/yr). That reach ceiling is the
lead-generation problem: no single channel wins enough clients. So the decision
here is HOW TO SPLIT a fixed acquisition budget (your hours + cash) across the
OWNED acquisition channels. Delivery/pricing economics are LOCKED inputs taken
from the GTM-v2 result (per-client value, net of delivery). The free decision is
the channel allocation.

WHY THESE FIVE CHANNELS, AND WHY NOT UPWORK
-------------------------------------------
The channels are the OWNED acquisition routes the owner controls: demo-first
local SMB (the DE-legal wedge), cold-email B2B (UK/US), LinkedIn outbound,
referral/partnership, and AEO/content inbound. Upwork is the STATUS QUO being
replaced (rented lead flow, no compounding, platform + fee + policy risk); it is
NOT an optimizable channel here. The scorer prints an all-Upwork baseline for
contrast so the independence upside is visible, but the loop cannot invest in it.

THE MODEL (per channel c, over the horizon)
-------------------------------------------
The asset gives channel_effort[c] = the fraction of the fixed acquisition-HOURS
budget directed to c (sum <= 1; leftover reinvests at the opportunity rate ->
zero surplus, neutral). From c's hours it wins clients:
  hours_c      = effort_c * H_ACQ
  producing    = max(0, (horizon - ramp_c)/horizon)   # a slow-ramp channel produces for less of a finite horizon
  clients_c    = min( (hours_c - fixed_c)/hpc_c * producing , pool_c )   # 0 if hours_c <= fixed_c
where hpc_c = YOUR hours to win one client, fixed_c = one-time setup hours before
any lead flows, pool_c = reachable clients over the horizon (a hard per-channel
ceiling; the reason a portfolio must diversify -- no one channel reaches enough).

Two shared constraints bind the portfolio:
  CASH:        if sum(clients_c * cpc_c) > M_ACQ, scale the cash-consuming
               channels down proportionally.
  SERVICEABLE: you cannot bank clients you cannot deliver. If total won >
               SERV_CAP (the delivery ceiling from GTM-v2, subcontracted), keep
               the HIGHEST-VALUE clients (value-greedy truncation) and drop the
               rest. This makes value-per-CLIENT, not just value-per-hour, the
               priority when delivery is the binding constraint -- which is the
               honest reconciliation with GTM-v2.

SCORE = net won-client value = sum(clients_c * value_c) - (hours_used * opp_rate
+ cash_used), in kEUR. Maximize. value_c is the per-client lifetime contribution
NET of delivery, carried over from GTM-v2 (B2B retainer clients dwarf local
build+care clients). Because idle hours reinvest at the opportunity rate, their
surplus is zero and they do not drag the score (same freed-hour-reinvestment
principle as gtm-roi-v2.py).

NOT comparable to the GTM scorers' numbers -- different asset, different metric.
This one answers "which acquisition mix wins the most client-value per budget",
holding delivery/pricing fixed.

Parameter provenance is tagged inline: SOURCED = traced to a repo memory /
GTM-v2 locked economics / verified datum; ASSUMPTION = a defensible planning
estimate reviewed at pin time (the PR review is the honesty gate).

Deterministic: pure arithmetic over the plan file, no network, no timing, no RNG.

Contract (tools/scorers/README.md): last stdout line is `SCORE: <number>`,
exit 0 only on a successful measurement.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# --- LOCKED budgets + delivery ceiling (central case) ------------------------
HORIZON_MONTHS = 30.0             # owner directive 2026-07-21 (24-36mo); midpoint, matches GTM v2
OPP_RATE_EUR_HR = 33.0           # SOURCED user_rates_unpauseai ($36/hr low end -> ~EUR33)
H_ACQ_HOURS = 1800.0             # ASSUMPTION acquisition hours over horizon (~15 h/wk of the GTM-v2 32 h/wk winner on winning clients; rest is delivery/oversight)
M_ACQ_CASH_EUR = 12000.0         # ASSUMPTION acquisition cash over horizon (~EUR400/mo lists + tools + light ads)
SERVICEABLE_CAP_CLIENTS = 110.0  # SOURCED-adjacent: GTM-v2 winner delivered ~103 clients (62.5 B2B + 41 local) subcontracted; ~110 delivery ceiling

# --- LOCKED per-channel economics --------------------------------------------
#  hpc   = YOUR hours to WIN one client (hours_per_lead / conversion)
#  cpc   = cash to win one client (EUR)
#  pool  = reachable clients over the horizon (hard per-channel ceiling)
#  ramp  = months before the channel produces (finite-horizon haircut)
#  fixed = one-time setup hours before any lead flows
#  value = per-client lifetime contribution EUR, NET of delivery (from GTM v2)
#  geos  = markets where the channel is legal/applicable
CHANNELS = {
    "demo_first_local": {        # DE-legal wedge: build the bespoke site, then approach
        "hpc": 27.3,             # SOURCED GTM v2: 6h customize / 0.22 demo->client conv
        "cpc": 0.0,              # ASSUMPTION no per-client cash (your hours are the cost)
        "pool": 33.0,            # SOURCED GTM v2: handwerk 150 reachable prospects * 0.22
        "ramp": 1.0, "fixed": 20.0,  # SOURCED GTM v2 template setup
        "value": 4080.0,         # SOURCED GTM v2: build 1200 + care 200*18mo*0.8 factor
        "geos": ("DE", "UK", "US"),
    },
    "cold_email_b2b": {          # UK/US only (DE cold email illegal, UWG Sec.7)
        "hpc": 12.4,             # SOURCED GTM v2: (1/35 h/prospect) / 0.00231 funnel conv
        "cpc": 170.0,            # ASSUMPTION list + tool ~EUR0.4/prospect / 0.00231 conv
        "pool": 50.0,            # ASSUMPTION UK/US cold-reachable B2B clients (~ GTM v2 market cap)
        "ramp": 1.0, "fixed": 40.0,  # ASSUMPTION domain warmup + infra
        "value": 30000.0,        # SOURCED GTM v2: retainer 2500*14mo, net of subcontracted delivery
        "geos": ("UK", "US"),
    },
    "linkedin_outbound": {       # personal 1:1 outreach, legal any geo
        "hpc": 20.0,             # ASSUMPTION 0.4 h/lead / 0.02 conv
        "cpc": 25.0,             # ASSUMPTION Sales Navigator seat amortized per client
        "pool": 30.0,            # ASSUMPTION reachable B2B via personal outreach
        "ramp": 2.0, "fixed": 20.0,
        "value": 30000.0,        # B2B retainer client (GTM v2)
        "geos": ("DE", "UK", "US"),
    },
    "referral_partnership": {    # warm, network-limited, any geo
        "hpc": 16.7,             # ASSUMPTION 2 h/lead / 0.12 conv (SOURCED GTM v2 referral conv 0.12)
        "cpc": 0.0,
        "pool": 15.0,            # ASSUMPTION network/partner reach is small
        "ramp": 3.0, "fixed": 0.0,   # relationships take time to produce, no infra
        "value": 30000.0,        # B2B retainer client
        "geos": ("DE", "UK", "US"),
    },
    "content_aeo_inbound": {     # AEO/GEO content, compounding, high fixed, any geo
        "hpc": 4.0,              # ASSUMPTION low MARGINAL hours once the corpus exists (incl. sales convo)
        "cpc": 17.0,             # ASSUMPTION hosting/tooling per inbound client
        "pool": 25.0,            # ASSUMPTION inbound clients the corpus can attract over horizon
        "ramp": 5.0, "fixed": 200.0, # ASSUMPTION slow to rank; heavy one-time corpus build
        "value": 20000.0,        # ASSUMPTION mixed inbound (some local, some B2B), net of delivery
        "geos": ("DE", "UK", "US"),
    },
}
# Status-quo baseline for contrast only (NOT optimizable):
UPWORK_BASELINE = {"hpc": 2.5, "cpc": 0.0, "pool": 40.0, "ramp": 0.0, "fixed": 0.0,
                   "value": 21250.0}  # 25000 gross, less the ~15% platform fee


def _channel_clients(effort: float, ch: dict) -> float:
    hours = effort * H_ACQ_HOURS
    if hours <= ch["fixed"]:
        return 0.0
    producing = max(0.0, (HORIZON_MONTHS - ch["ramp"]) / HORIZON_MONTHS)
    from_hours = (hours - ch["fixed"]) / ch["hpc"] * producing
    return min(from_hours, ch["pool"])


def compute(plan: dict) -> dict:
    """Pure function of the plan. Returns a breakdown incl. 'net_value_eur'."""
    target = set(plan.get("target_geos") or [])
    effort = plan["channel_effort"]
    if not isinstance(effort, dict):
        raise TypeError("channel_effort must be an object")

    clients: dict[str, float] = {}
    for name, ch in CHANNELS.items():
        e = float(effort.get(name, 0.0))
        # a channel unusable in the target markets wins nothing (validate guard
        # rejects spending effort on it; here we simply score it as inapplicable)
        if not (set(ch["geos"]) & target):
            clients[name] = 0.0
            continue
        clients[name] = _channel_clients(e, ch)

    # CASH constraint: scale cash-consuming channels down if over budget.
    cash_need = sum(clients[n] * CHANNELS[n]["cpc"] for n in clients)
    if cash_need > M_ACQ_CASH_EUR and cash_need > 0:
        f = M_ACQ_CASH_EUR / cash_need
        for n in clients:
            if CHANNELS[n]["cpc"] > 0:
                clients[n] *= f

    # SERVICEABLE cap: keep the highest-VALUE clients you can actually deliver.
    total = sum(clients.values())
    capped = total > SERVICEABLE_CAP_CLIENTS
    if capped:
        remaining = SERVICEABLE_CAP_CLIENTS
        for n in sorted(clients, key=lambda x: -CHANNELS[x]["value"]):
            take = min(clients[n], remaining)
            clients[n] = take
            remaining -= take

    value = sum(clients[n] * CHANNELS[n]["value"] for n in clients)
    cash_used = min(sum(clients[n] * CHANNELS[n]["cpc"] for n in clients), M_ACQ_CASH_EUR)
    hours_used = min(sum(float(effort.get(n, 0.0)) for n in CHANNELS) * H_ACQ_HOURS, H_ACQ_HOURS)
    net = value - (hours_used * OPP_RATE_EUR_HR + cash_used)
    return {
        "clients": clients, "total_clients": sum(clients.values()),
        "value": value, "cash_used": cash_used, "hours_used": hours_used,
        "serviceable_capped": capped, "net_value_eur": net,
    }


def _upwork_baseline_net() -> float:
    u = UPWORK_BASELINE
    clients = min(H_ACQ_HOURS / u["hpc"], u["pool"])
    clients = min(clients, SERVICEABLE_CAP_CLIENTS)
    hours = min(clients * u["hpc"], H_ACQ_HOURS)
    return clients * u["value"] - hours * OPP_RATE_EUR_HR


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: leadgen-portfolio.py PLAN.json", file=sys.stderr)
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

    print(f"plan: {path}  (horizon {HORIZON_MONTHS:.0f} months, markets {plan.get('target_geos')})")
    print(f"  budgets: {H_ACQ_HOURS:.0f} acq-hours ({r['hours_used']:.0f} used), "
          f"EUR {M_ACQ_CASH_EUR:.0f} cash ({r['cash_used']:.0f} used), "
          f"serviceable cap {SERVICEABLE_CAP_CLIENTS:.0f}{' (BINDING)' if r['serviceable_capped'] else ''}")
    for name in CHANNELS:
        c = r["clients"].get(name, 0.0)
        if c > 0.05:
            print(f"  {name:22} {float(plan['channel_effort'].get(name, 0)):.2f} effort -> "
                  f"{c:5.1f} clients  (EUR {c * CHANNELS[name]['value']:,.0f})")
    print(f"  total {r['total_clients']:.1f} clients -> value EUR {r['value']:,.0f}; "
          f"net of acquisition cost = EUR {r['net_value_eur']:,.0f}")
    print(f"  contrast: all-Upwork status quo nets EUR {_upwork_baseline_net():,.0f} "
          f"({_upwork_baseline_net() / 1000.0:.0f} kEUR)")
    print("  SCORE = net won-client value over the 30-month horizon, in kEUR (maximize):")
    print(f"SCORE: {r['net_value_eur'] / 1000.0:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
