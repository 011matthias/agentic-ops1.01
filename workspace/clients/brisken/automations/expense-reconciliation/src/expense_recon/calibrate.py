"""Calibration metrics — BLUEPRINT slice 3b / ANNEALING E8.

`expense-recon calibrate --config run.json` runs the matching engine and
prints the calibration metrics that matter when tuning the matcher
against a real reconciled month: the distinct-transaction outcome split,
the reconciliation invariant, the receipt double-binding check, the
FX-pair-vs-foreign-receipt multiplicity (the BLUEPRINT "<= 2x" target),
and per-card spend reconciliation against the statement.

This promotes what was a throwaway %TEMP% driver (re-run by hand on every
calibration, the E8 trigger) into a first-class, repeatable subcommand.
It writes NO report; it is the measurement view of a run. Receipts come
from the run config's CSV source (the slice-1 bridge), so calibration is
deterministic and needs no LLM.

Exit code is 0 when the two hard guarantees hold (reconciliation
invariant intact AND no receipt double-bound), 1 otherwise — so it
doubles as a regression gate on a known-good month. The multiplicity and
match-rate numbers are reported, never gated (they are tuning signals,
not correctness guarantees).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .matching.deterministic import match_month
from .matching.types import MatchOutcome, Receipt, Transaction

FX_MULTIPLICITY_TARGET = 2.0  # BLUEPRINT slice-3 acceptance criterion


def _metrics(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    card_currency: str,
) -> dict:
    all_tx_ids = {tx.transaction_id for tx in transactions}
    matched_tx = {m.transaction_id for m in outcome.matches}
    review_tx = {m.transaction_id for m in outcome.judgment_required} | {
        m.transaction_id for m in outcome.ambiguous
    }
    unmatched_tx = set(outcome.unmatched_transactions)

    bucketed = matched_tx | review_tx | unmatched_tx
    invariant_ok = (
        bucketed == all_tx_ids
        and len(matched_tx) + len(review_tx) + len(unmatched_tx) == len(all_tx_ids)
    )

    # Double-binding: a receipt assigned to more than one transaction
    # (ambiguous ties legitimately share a receipt, so exclude them).
    assigned_docs = [m.document_id for m in outcome.matches] + [
        m.document_id for m in outcome.judgment_required
    ]
    doc_counts: dict[str, int] = defaultdict(int)
    for d in assigned_docs:
        doc_counts[d] += 1
    double_bound = sorted(d for d, n in doc_counts.items() if n > 1)

    # FX multiplicity: FX pairs emitted vs the foreign receipts that
    # could legitimately produce them. Target <= 2x.
    foreign_receipts = [
        r for r in receipts
        if r.detected_currency and r.detected_currency != card_currency
    ]
    n_foreign = len(foreign_receipts)
    n_fx_pairs = len(outcome.judgment_required)
    fx_multiplicity = (n_fx_pairs / n_foreign) if n_foreign else 0.0

    by_card_spend: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for tx in transactions:
        by_card_spend[tx.account_id] += tx.amount

    return {
        "transactions": len(all_tx_ids),
        "receipts": len(receipts),
        "matched": len(matched_tx),
        "needs_review": len(review_tx),
        "unmatched_tx": len(unmatched_tx),
        "unmatched_receipts": len(outcome.unmatched_receipts),
        "match_rate_pct": round(len(matched_tx) / len(all_tx_ids) * 100, 1)
        if all_tx_ids else 0.0,
        "invariant_ok": invariant_ok,
        "double_bound_receipts": double_bound,
        "foreign_receipts": n_foreign,
        "fx_pairs": n_fx_pairs,
        "fx_multiplicity": round(fx_multiplicity, 2),
        "fx_multiplicity_ok": fx_multiplicity <= FX_MULTIPLICITY_TARGET,
        "by_card_spend": {k: float(v) for k, v in sorted(by_card_spend.items())},
    }


def _print_report(m: dict) -> None:
    print("CALIBRATION METRICS")
    print(f"  Transactions:        {m['transactions']}")
    print(f"  Receipts:            {m['receipts']}")
    print(
        f"  Matched:             {m['matched']}  ({m['match_rate_pct']}%)"
    )
    print(f"  Needs review (tx):   {m['needs_review']}")
    print(f"  Unmatched tx:        {m['unmatched_tx']}")
    print(f"  Unmatched receipts:  {m['unmatched_receipts']}")
    print()
    inv = "OK" if m["invariant_ok"] else "BROKEN"
    print(f"  Reconciliation invariant: {inv}")
    if m["double_bound_receipts"]:
        print(
            f"  Double-bound receipts:    FAIL "
            f"({len(m['double_bound_receipts'])}: "
            f"{', '.join(m['double_bound_receipts'][:5])})"
        )
    else:
        print("  Double-bound receipts:    none")
    print()
    mult_flag = "OK" if m["fx_multiplicity_ok"] else f"OVER {FX_MULTIPLICITY_TARGET}x"
    print(
        f"  FX pairs / foreign receipts: {m['fx_pairs']} / "
        f"{m['foreign_receipts']} = {m['fx_multiplicity']}x  ({mult_flag})"
    )
    print()
    print("  By-card spend (statement charge sum):")
    for card, spend in m["by_card_spend"].items():
        print(f"    {card}: {spend:.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon calibrate",
        description="Run the matcher and print calibration metrics (no report written).",
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--json", action="store_true", help="Emit metrics as JSON instead of a report."
    )
    args = parser.parse_args(argv)

    # Reuse the CLI's loaders. Imported lazily to avoid a module-load
    # cycle (cli imports this module only inside its own main()).
    from .cli import ConfigError, _load_receipts, _load_statement

    config_path = args.config.resolve()
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        return 2
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    config_dir = config_path.parent

    try:
        transactions, _ = _load_statement(cfg, config_dir)
        receipts, _ = _load_receipts(
            cfg, config_dir,
            legal_entity_id=cfg["statement"]["legal_entity_id"],
            llm_client=None,  # CSV receipts only; calibration is deterministic
        )
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    card_currency = cfg["statement"]["account_card_currency"]
    outcome = match_month(transactions, receipts)
    m = _metrics(outcome, transactions, receipts, card_currency)

    if args.json:
        print(json.dumps(m, indent=2))
    else:
        _print_report(m)

    # Gate on the two hard guarantees only.
    return 0 if (m["invariant_ok"] and not m["double_bound_receipts"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
