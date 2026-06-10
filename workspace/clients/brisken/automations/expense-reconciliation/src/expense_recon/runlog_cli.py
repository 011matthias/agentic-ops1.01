"""`expense-recon history` and `expense-recon diff` (BLUEPRINT 5.8/5.9).

Read-only views over the run-log (`runlog.py`). Both resolve the SQLite
path from either `--db PATH` or `--config PATH` (reading the config's
`run_log.path`).

    expense-recon history --config run.json
    expense-recon history --config run.json --run 4f2a
    expense-recon diff --config run.json 4f2a 9b71

`diff` compares two runs of (usually) the same month: count deltas plus
which transactions changed bucket (matched / review / unmatched) between
the two runs. Useful after fixing a receipt and re-running.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runlog import RunLog, RunSummary, TxDecision


def _resolve_db(args) -> Path | None:
    if args.db:
        return Path(args.db).resolve()
    if args.config:
        config_path = Path(args.config).resolve()
        if not config_path.exists():
            print(f"config file not found: {config_path}", file=sys.stderr)
            return None
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        rl = cfg.get("run_log")
        if not isinstance(rl, dict) or not rl.get("path"):
            print("config has no run_log.path block", file=sys.stderr)
            return None
        return (config_path.parent / rl["path"]).resolve()
    print("need --db or --config", file=sys.stderr)
    return None


def _bucket(d: TxDecision) -> str:
    if d.match_type == "unmatched":
        return "unmatched"
    if d.requires_review:
        return "review"
    return "matched"


def _print_run_header(s: RunSummary) -> None:
    rate = (s.n_matched / s.n_transactions * 100) if s.n_transactions else 0.0
    print(f"run {s.run_id}  {s.created_at}  {s.operator or '-'}")
    print(f"  account {s.account_id or '-'} / {s.legal_entity_id or '-'}")
    print(
        f"  tx {s.n_transactions}  receipts {s.n_receipts}  "
        f"matched {s.n_matched} ({rate:.0f}%)  review {s.n_review}  "
        f"unmatched {s.n_unmatched}  errors {s.n_parse_errors}"
    )
    print(f"  LLM {s.llm_calls} call(s), ${s.llm_cost_usd}")
    if s.report_path:
        print(f"  report: {s.report_path}")


def cmd_history(args) -> int:
    db = _resolve_db(args)
    if db is None:
        return 2
    if not db.exists():
        print(f"run-log not found: {db} (no runs recorded yet)", file=sys.stderr)
        return 1

    with RunLog(db) as rl:
        if args.run:
            s = rl.get_run(args.run)
            if s is None:
                print(f"no unique run matching {args.run!r}", file=sys.stderr)
                return 1
            _print_run_header(s)
            print()
            decisions = rl.get_decisions(s.run_id)
            print(f"  {'transaction':24} {'bucket':9} {'type':12} {'receipt'}")
            for d in decisions:
                print(
                    f"  {d.transaction_id[:24]:24} {_bucket(d):9} "
                    f"{d.match_type:12} {d.document_id or '-'}"
                )
            return 0

        runs = rl.list_runs(limit=args.limit)
        if not runs:
            print("no runs recorded yet")
            return 0
        for s in runs:
            _print_run_header(s)
            print()
    return 0


def cmd_diff(args) -> int:
    db = _resolve_db(args)
    if db is None:
        return 2
    if not db.exists():
        print(f"run-log not found: {db}", file=sys.stderr)
        return 1

    with RunLog(db) as rl:
        a = rl.get_run(args.run_a)
        b = rl.get_run(args.run_b)
        if a is None or b is None:
            missing = args.run_a if a is None else args.run_b
            print(f"no unique run matching {missing!r}", file=sys.stderr)
            return 1

        print(f"diff {a.run_id} -> {b.run_id}")
        for label, va, vb in (
            ("transactions", a.n_transactions, b.n_transactions),
            ("matched", a.n_matched, b.n_matched),
            ("review", a.n_review, b.n_review),
            ("unmatched", a.n_unmatched, b.n_unmatched),
            ("parse errors", a.n_parse_errors, b.n_parse_errors),
            ("LLM calls", a.llm_calls, b.llm_calls),
        ):
            delta = vb - va
            sign = f"+{delta}" if delta > 0 else str(delta)
            mark = "" if delta == 0 else f"  ({sign})"
            print(f"  {label:14} {va:>5} -> {vb:>5}{mark}")

        da = {d.transaction_id: _bucket(d) for d in rl.get_decisions(a.run_id)}
        dbk = {d.transaction_id: _bucket(d) for d in rl.get_decisions(b.run_id)}
        changed = sorted(
            tx for tx in (set(da) | set(dbk))
            if da.get(tx) != dbk.get(tx)
        )
        if changed:
            print(f"\n  {len(changed)} transaction(s) changed bucket:")
            for tx in changed:
                print(f"    {tx[:30]:30} {da.get(tx, '(absent)')} -> {dbk.get(tx, '(absent)')}")
        else:
            print("\n  no transaction changed bucket")
    return 0


def _add_db_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", type=Path, help="run config carrying run_log.path")
    p.add_argument("--db", type=Path, help="path to the run-log SQLite directly")


def main(argv: list[str], *, command: str) -> int:
    if command == "history":
        parser = argparse.ArgumentParser(prog="expense-recon history")
        _add_db_args(parser)
        parser.add_argument("--run", help="show one run's decisions (id or unique prefix)")
        parser.add_argument("--limit", type=int, default=20, help="how many runs to list")
        return cmd_history(parser.parse_args(argv))

    parser = argparse.ArgumentParser(prog="expense-recon diff")
    _add_db_args(parser)
    parser.add_argument("run_a", help="earlier run id (or unique prefix)")
    parser.add_argument("run_b", help="later run id (or unique prefix)")
    return cmd_diff(parser.parse_args(argv))
