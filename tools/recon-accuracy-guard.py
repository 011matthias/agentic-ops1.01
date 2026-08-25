# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "openpyxl==3.1.5",
#     "openai==2.38.0",
#     "pypdf==6.13.2",
#     "pypdfium2==5.9.0",
#     "pillow==12.2.0",
# ]
# ///
"""Guard for the brisken-recon-tuning optimize runs (anti-overfit floor).

Four checks against ASSET (the match-tuning file) and BASELINE (the
holdout baseline JSON captured at lock-on):

  1. invariant      — reconciliation invariant + no double-bound receipts
                      on ALL six labelled bundles under the asset. Lives
                      here (not only in `expense-recon calibrate`) because
                      the bundles' run.json files carry no tuning_path, so
                      calibrate alone never sees the asset under test.
  2. holdout-floor  — held-out composite (two 2024 months) >= baseline.
  3. holdout-wrongs — held-out (determ_wrong + nc_determ_matched) <=
                      baseline. Strict no-new-wrongs on unseen months:
                      this is exactly where a train-fit global FX rate
                      shows its overfit.
  4. wrong-ceiling  — total wrong deterministic matches across all six
                      bundles <= the ceiling written into the baseline
                      file (baseline + slack, owner-reviewed at lock-on).

Prints only PASS / FAIL per check — never the holdout NUMBERS. Guard
output lands in round logs the optimizing agent reads; pass/fail leakage
is the design, numeric leakage would let the hill-climb fit the holdout
by proxy.

Scoring math is not duplicated: this guard imports the pinned scorer
(tools/scorers/recon-match-accuracy.py) by path and calls its
evaluate/totals, so scorer and guard cannot drift apart. Both files are
hash-pinned; the engine re-verifies both every round.

Usage:
    uv run tools/recon-accuracy-guard.py ASSET.json BASELINE.json
Exit 0 = all checks pass; exit 1 = discard the round; exit 2 = cannot
measure (missing files — never treated as a verdict either way).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCORER = REPO / "tools" / "scorers" / "recon-match-accuracy.py"


def _load_scorer():
    spec = importlib.util.spec_from_file_location(
        "recon_match_accuracy", SCORER
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: recon-accuracy-guard.py ASSET.json BASELINE.json",
            file=sys.stderr,
        )
        return 2
    asset, baseline_path = Path(argv[0]), Path(argv[1])
    if not asset.is_file():
        print(f"ERROR: asset not found: {asset}", file=sys.stderr)
        return 2
    if not baseline_path.is_file():
        print(f"ERROR: baseline not found: {baseline_path}", file=sys.stderr)
        return 2
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        floor = float(baseline["holdout_composite"])
        wrong_floor = int(baseline["holdout_wrongs"])
        ceiling = int(baseline["determ_wrong_ceiling"])
    except (ValueError, KeyError) as exc:
        print(f"ERROR: baseline unreadable: {exc}", file=sys.stderr)
        return 2

    scorer = _load_scorer()
    if not scorer.MODULE_SRC.is_dir():
        print("ERROR: module src not found", file=sys.stderr)
        return 2
    sys.path.insert(0, str(scorer.MODULE_SRC))

    all_stats = scorer.evaluate(
        asset, scorer.TRAIN_BUNDLES + scorer.HOLDOUT_BUNDLES
    )
    holdout_stats = [
        s for s in all_stats if s["bundle"] in scorer.HOLDOUT_BUNDLES
    ]
    tot_all = scorer.totals(all_stats)
    tot_holdout = scorer.totals(holdout_stats)

    failed = False

    ok = tot_all["invariant_ok"] and tot_all["double_bound_receipts"] == 0
    print(f"{'PASS' if ok else 'FAIL'}: invariant")
    failed |= not ok

    ok = tot_holdout["composite"] >= floor
    print(f"{'PASS' if ok else 'FAIL'}: holdout-floor")
    failed |= not ok

    holdout_wrongs = (
        tot_holdout["determ_wrong"] + tot_holdout["nc_determ_matched"]
    )
    ok = holdout_wrongs <= wrong_floor
    print(f"{'PASS' if ok else 'FAIL'}: holdout-wrongs")
    failed |= not ok

    total_wrong = tot_all["determ_wrong"] + tot_all["nc_determ_matched"]
    ok = total_wrong <= ceiling
    print(f"{'PASS' if ok else 'FAIL'}: wrong-ceiling")
    failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
