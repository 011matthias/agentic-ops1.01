# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: structural + realism validation of a good/better/best pricing menu.

A pass/fail argv guard for /comd_optimize (RECIPES: guards discard an experiment
that fails, even on a score win). This is the realism fence around the decision
space. Every rule here is duplicated INDEPENDENTLY of the scorer on purpose (an
independent instrument catches a scorer bug).

Hard rules enforced:
  - schema: tiers is an object with exactly good/better/best; each has numeric
    price >= 0 and scope in [0, 1]
  - a VALID good/better/best LADDER: price and scope both non-decreasing across
    good -> better -> best (a "best" that is cheaper or thinner than "good" is not
    a real premium tier; the optimizer cannot invent one)
  - no structurally loss-making tier: each tier's price >= its own delivery cost,
    so no tier bleeds margin every month (a recurring retainer priced below
    subcontracted delivery cost loses money forever, unlike a one-time loss-leader)

Exit 0 = valid. Exit 1 = at least one violation (printed). Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TIERS = ("good", "better", "best")

# Independent copy of the delivery-cost model (mirror of the scorer).
D_BASE, D_SLOPE, D_QUAD = 120.0, 450.0, 350.0


def deliv(q: float) -> float:
    return D_BASE + D_SLOPE * q + D_QUAD * q * q


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"expected number, got {v!r}")
    return float(v)


def validate(plan: dict) -> list[str]:
    errs: list[str] = []
    try:
        tiers = plan["tiers"]
        if not isinstance(tiers, dict):
            errs.append("tiers must be an object")
            return errs
        extra = set(tiers) - set(TIERS)
        if extra:
            errs.append(f"unknown tier(s) {sorted(extra)} (allowed: {list(TIERS)})")
        parsed = {}
        for name in TIERS:
            if name not in tiers:
                errs.append(f"missing tier {name!r}")
                continue
            row = tiers[name]
            if not isinstance(row, dict) or "price" not in row or "scope" not in row:
                errs.append(f"tier {name!r} must have price and scope")
                continue
            price, scope = _num(row["price"]), _num(row["scope"])
            if price < 0:
                errs.append(f"{name}.price={price} must be >= 0")
            if not (0.0 <= scope <= 1.0):
                errs.append(f"{name}.scope={scope} out of [0,1]")
            if price < deliv(scope) - 1e-6:
                errs.append(f"{name} priced EUR{price:.0f}/mo below its delivery cost "
                            f"EUR{deliv(scope):.0f}/mo (a loss-making recurring tier)")
            parsed[name] = (price, scope)
        if len(parsed) == len(TIERS):
            if not (parsed["good"][0] <= parsed["better"][0] <= parsed["best"][0]):
                errs.append(f"prices not non-decreasing good<=better<=best: "
                            f"{parsed['good'][0]:.0f}/{parsed['better'][0]:.0f}/{parsed['best'][0]:.0f}")
            if not (parsed["good"][1] <= parsed["better"][1] <= parsed["best"][1]):
                errs.append(f"scopes not non-decreasing good<=better<=best: "
                            f"{parsed['good'][1]:.2f}/{parsed['better'][1]:.2f}/{parsed['best'][1]:.2f}")
    except (KeyError, TypeError) as e:
        errs.append(f"schema error: {type(e).__name__}: {e}")
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: pricing-tiers-validate.py PLAN.json", file=sys.stderr)
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
        print("MENU INVALID:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print("menu valid: schema, monotone good/better/best ladder, and per-tier margin all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
