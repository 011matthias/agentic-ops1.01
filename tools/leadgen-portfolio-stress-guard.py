# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: pessimistic-case floor on acquisition-portfolio net value (anti-overfit).

RECIPES constructed-metric rule 3 ("held-out score floor, mandatory"). The scorer
(tools/scorers/leadgen-portfolio.py) rewards CENTRAL-case net won-client value; a
hill-climb drifts toward whatever the central assumptions reward. This guard is an
INDEPENDENT reimplementation of the same model under a PESSIMISTIC parameter set,
and it fails the round if the plan's pessimistic net value drops below the floor.

Floor = 0.0: even in the bad case, the portfolio's net won-client value must be
non-negative (acquisition hours are charged at the opportunity rate, so >= 0
means "the clients you win are worth more than the hours+cash spent winning them,
vs grinding hourly"). A portfolio that only wins under optimism is discarded even
when it beats the current best central score.

Pessimistic haircuts vs central: per-client value x0.85 (discounting under
pressure), reachable pools x0.6 (channels harder to tap), conversion effectively
worse via hours-per-client x1.25, ramp +2 months (slower to produce), cash-per-
client x1.3, and the delivery serviceable cap x0.8 (tighter capacity).

Deliberately separate code from the scorer: a shared bug cannot hide in both, and
drift between them is a signal to re-review. Kept economically in lockstep at pin
time.

Exit 0 = pessimistic net value >= floor. Exit 1 = below. Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

STRESS_FLOOR = 0.0

HORIZON_MONTHS = 30.0
OPP_RATE_EUR_HR = 33.0
H_ACQ_HOURS = 1800.0
M_ACQ_CASH_EUR = 12000.0
SERVICEABLE_CAP_CLIENTS = 110.0 * 0.8          # tighter delivery capacity

VALUE_HAIRCUT = 0.85
POOL_HAIRCUT = 0.6
HPC_PENALTY = 1.25
RAMP_ADD_MONTHS = 2.0
CPC_PENALTY = 1.3

# Independent copy of the owned-channel economics (mirror of the scorer),
# with pessimistic haircuts applied inline.
CHANNELS = {
    "demo_first_local":    {"hpc": 27.3, "cpc": 0.0,   "pool": 33.0, "ramp": 1.0, "fixed": 20.0,  "value": 4080.0,  "geos": {"DE", "UK", "US"}},
    "cold_email_b2b":      {"hpc": 12.4, "cpc": 170.0, "pool": 50.0, "ramp": 1.0, "fixed": 40.0,  "value": 30000.0, "geos": {"UK", "US"}},
    "linkedin_outbound":   {"hpc": 20.0, "cpc": 25.0,  "pool": 30.0, "ramp": 2.0, "fixed": 20.0,  "value": 30000.0, "geos": {"DE", "UK", "US"}},
    "referral_partnership":{"hpc": 16.7, "cpc": 0.0,   "pool": 15.0, "ramp": 3.0, "fixed": 0.0,   "value": 30000.0, "geos": {"DE", "UK", "US"}},
    "content_aeo_inbound": {"hpc": 4.0,  "cpc": 17.0,  "pool": 25.0, "ramp": 5.0, "fixed": 200.0, "value": 20000.0, "geos": {"DE", "UK", "US"}},
}


def pessimistic_net_value(plan: dict) -> float:
    target = set(plan.get("target_geos") or [])
    effort = plan["channel_effort"]
    if not isinstance(effort, dict):
        raise TypeError("channel_effort must be an object")

    clients: dict[str, float] = {}
    for name, ch in CHANNELS.items():
        e = float(effort.get(name, 0.0))
        if not (ch["geos"] & target):
            clients[name] = 0.0
            continue
        hours = e * H_ACQ_HOURS
        if hours <= ch["fixed"]:
            clients[name] = 0.0
            continue
        ramp = ch["ramp"] + RAMP_ADD_MONTHS
        producing = max(0.0, (HORIZON_MONTHS - ramp) / HORIZON_MONTHS)
        from_hours = (hours - ch["fixed"]) / (ch["hpc"] * HPC_PENALTY) * producing
        clients[name] = min(from_hours, ch["pool"] * POOL_HAIRCUT)

    cash_need = sum(clients[n] * CHANNELS[n]["cpc"] * CPC_PENALTY for n in clients)
    if cash_need > M_ACQ_CASH_EUR and cash_need > 0:
        f = M_ACQ_CASH_EUR / cash_need
        for n in clients:
            if CHANNELS[n]["cpc"] > 0:
                clients[n] *= f

    total = sum(clients.values())
    if total > SERVICEABLE_CAP_CLIENTS:
        remaining = SERVICEABLE_CAP_CLIENTS
        for n in sorted(clients, key=lambda x: -CHANNELS[x]["value"]):
            take = min(clients[n], remaining)
            clients[n] = take
            remaining -= take

    value = sum(clients[n] * CHANNELS[n]["value"] * VALUE_HAIRCUT for n in clients)
    cash_used = min(sum(clients[n] * CHANNELS[n]["cpc"] * CPC_PENALTY for n in clients), M_ACQ_CASH_EUR)
    hours_used = min(sum(float(effort.get(n, 0.0)) for n in CHANNELS) * H_ACQ_HOURS, H_ACQ_HOURS)
    return value - (hours_used * OPP_RATE_EUR_HR + cash_used)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: leadgen-portfolio-stress-guard.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
        net = pessimistic_net_value(plan)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"cannot evaluate stress floor ({type(e).__name__}): {e}", file=sys.stderr)
        return 2
    ok = net >= STRESS_FLOOR
    print(f"pessimistic net won-client value = EUR {net:,.0f} ({net / 1000.0:.2f} kEUR)  "
          f"(floor {STRESS_FLOOR:.2f})")
    print("STRESS FLOOR PASS" if ok else "STRESS FLOOR FAIL: portfolio only wins under optimism")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
