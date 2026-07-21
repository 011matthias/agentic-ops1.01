# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: structural + legal + in-bounds validation of a GTM plan.

A pass/fail argv guard for /comd_optimize (RECIPES: guards discard an experiment
that fails, even on a score win). This is the realism fence around the decision
space: it stops the loop from "winning" with an illegal channel, an out-of-market
price, or an over-capacity plan. Every bound here is duplicated INDEPENDENTLY of
the scorer on purpose (an independent instrument catches a scorer bug).

Hard rules enforced:
  - schema: all required decision keys present and well-typed
  - route_allocation fractions in [0,1] and sum <= 1.0 (leftover = slack)
  - prices/capacity within the sourced market/realism bounds
  - LEGAL: geo == 'DE' with acquisition == 'cold_email' is REJECTED
    (German UWG Sec.7 makes B2B cold email an Abmahnung risk without consent;
    SOURCED project_upwork_independence_two_routes). DE B2B must use referral.

Exit 0 = plan is valid. Exit 1 = at least one violation (printed). Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOUNDS = {
    "capacity_hours_per_week": (5.0, 45.0),   # 45 = you + realistic overflow
    "price_build_eur": (1200.0, 4000.0),      # DE local-SMB one-time build band
    "price_care_eur_mo": (0.0, 300.0),
    "retainer_eur_mo": (500.0, 2500.0),
}
SEGMENTS = ("handwerk", "physio", "beauty", "medical", "food")
GEOS = ("DE", "UK", "US")
ACQ_LOCAL = ("demo_first", "referral")
ACQ_B2B = ("cold_email", "referral")


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"expected number, got {v!r}")
    return float(v)


def validate(plan: dict) -> list[str]:
    errs: list[str] = []

    def bound(key, val):
        lo, hi = BOUNDS[key]
        if not (lo <= val <= hi):
            errs.append(f"{key}={val} out of bounds [{lo}, {hi}]")

    try:
        bound("capacity_hours_per_week", _num(plan["capacity_hours_per_week"]))

        alloc = plan["route_allocation"]
        a_local = _num(alloc["local_smb"])
        a_b2b = _num(alloc["b2b_lead_gen"])
        for name, v in (("local_smb", a_local), ("b2b_lead_gen", a_b2b)):
            if not (0.0 <= v <= 1.0):
                errs.append(f"route_allocation.{name}={v} out of [0,1]")
        if a_local + a_b2b > 1.0 + 1e-9:
            errs.append(f"route_allocation sums to {a_local + a_b2b:.3f} > 1.0")
        if a_local + a_b2b <= 0.0:
            errs.append("route_allocation sums to 0 (plan spends no hours)")

        l = plan["local_smb"]
        bound("price_build_eur", _num(l["price_build_eur"]))
        bound("price_care_eur_mo", _num(l["price_care_eur_mo"]))
        if l["segment"] not in SEGMENTS:
            errs.append(f"local_smb.segment={l['segment']!r} not in {SEGMENTS}")
        if l["geo"] not in GEOS:
            errs.append(f"local_smb.geo={l['geo']!r} not in {GEOS}")
        if l["acquisition"] not in ACQ_LOCAL:
            errs.append(f"local_smb.acquisition={l['acquisition']!r} not in {ACQ_LOCAL}")

        b = plan["b2b_lead_gen"]
        bound("retainer_eur_mo", _num(b["retainer_eur_mo"]))
        if b["geo"] not in GEOS:
            errs.append(f"b2b_lead_gen.geo={b['geo']!r} not in {GEOS}")
        if b["acquisition"] not in ACQ_B2B:
            errs.append(f"b2b_lead_gen.acquisition={b['acquisition']!r} not in {ACQ_B2B}")
        # LEGAL fence (UWG Sec.7): no DE B2B cold email.
        if b["geo"] == "DE" and b["acquisition"] == "cold_email":
            errs.append("LEGAL: b2b_lead_gen geo=DE + acquisition=cold_email violates German UWG Sec.7 "
                        "(B2B cold email without consent = Abmahnung risk). Use acquisition=referral for DE.")
    except (KeyError, TypeError) as e:
        errs.append(f"schema error: {type(e).__name__}: {e}")
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: gtm-plan-validate.py PLAN.json", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 2
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"invalid JSON: {e}", file=sys.stderr)
        return 2
    errs = validate(plan)
    if errs:
        print("PLAN INVALID:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("plan valid: schema, bounds, and UWG Sec.7 legal fence all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
