# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Guard: structural + legal + in-bounds validation of an acquisition portfolio.

A pass/fail argv guard for /comd_optimize (RECIPES: guards discard an experiment
that fails, even on a score win). This is the realism fence around the decision
space. Every rule here is duplicated INDEPENDENTLY of the scorer on purpose (an
independent instrument catches a scorer bug).

Hard rules enforced:
  - schema: channel_effort is an object over the KNOWN owned channels only
    (no unknown channel; Upwork is not an allowed channel here)
  - each effort in [0, 1]; sum(effort) <= 1.0 (leftover = reinvested slack)
  - target_geos is a non-empty subset of {DE, UK, US}
  - LEGAL/applicability: a channel with effort > 0 must be usable in at least
    one target geo. cold_email_b2b is UK/US only (German UWG Sec.7 makes DE B2B
    cold email an Abmahnung risk), so allocating to it with a target set that
    excludes UK and US is rejected -- the same legal fence as the GTM guard,
    expressed through channel geos.

Exit 0 = valid. Exit 1 = at least one violation (printed). Exit 2 = usage/parse.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Independent copy of the owned-channel geo-applicability (mirror of the scorer).
CHANNEL_GEOS = {
    "demo_first_local": {"DE", "UK", "US"},
    "cold_email_b2b": {"UK", "US"},        # NOT DE (UWG Sec.7)
    "linkedin_outbound": {"DE", "UK", "US"},
    "referral_partnership": {"DE", "UK", "US"},
    "content_aeo_inbound": {"DE", "UK", "US"},
}
KNOWN = set(CHANNEL_GEOS)
GEOS = {"DE", "UK", "US"}


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"expected number, got {v!r}")
    return float(v)


def validate(plan: dict) -> list[str]:
    errs: list[str] = []
    try:
        target = plan["target_geos"]
        if not isinstance(target, list) or not target:
            errs.append("target_geos must be a non-empty list")
            target = []
        for g in target:
            if g not in GEOS:
                errs.append(f"target_geos entry {g!r} not in {sorted(GEOS)}")
        target_set = set(target)

        effort = plan["channel_effort"]
        if not isinstance(effort, dict):
            errs.append("channel_effort must be an object")
            return errs
        total = 0.0
        for name, val in effort.items():
            if name not in KNOWN:
                errs.append(f"unknown channel {name!r} (allowed: {sorted(KNOWN)}; "
                            "Upwork is the status quo, not an allocatable channel)")
                continue
            v = _num(val)
            if not (0.0 <= v <= 1.0):
                errs.append(f"channel_effort.{name}={v} out of [0,1]")
            total += v
            if v > 0.0 and not (CHANNEL_GEOS[name] & target_set):
                errs.append(f"LEGAL/applicability: {name} (geos {sorted(CHANNEL_GEOS[name])}) "
                            f"has effort {v} but no overlap with target_geos {sorted(target_set)}. "
                            "cold_email_b2b needs UK or US in the target (DE B2B cold email "
                            "violates UWG Sec.7).")
        if total > 1.0 + 1e-9:
            errs.append(f"channel_effort sums to {total:.3f} > 1.0 (over the hours budget)")
    except (KeyError, TypeError) as e:
        errs.append(f"schema error: {type(e).__name__}: {e}")
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: leadgen-portfolio-validate.py PLAN.json", file=sys.stderr)
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
    print("plan valid: schema, effort bounds, budget sum, and geo-legality all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
