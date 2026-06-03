"""Slice-1 CLI: end-to-end reconciliation against one statement +
one receipts CSV, producing an Excel review report.

Usage:

    expense-recon --config run.json
    expense-recon --config run.json --out alt-report.xlsx

The config is a JSON file (stdlib only — no YAML dep) of the shape:

    {
      "statement": {
        "path": "amex-may.csv",                # .csv or .xlsx
        "account_id": "amex-9001",
        "legal_entity_id": "brisken-llc",
        "account_card_currency": "USD",
        "column_map": {
          "transaction_date": "Date",
          "amount": "Amount",
          "vendor": "Description"
        },
        "sheet_name": null                     # optional, xlsx only
      },
      "receipts": {
        "path": "receipts-may.csv",
        "default_currency": "USD"              # optional
      },
      "output": {
        "path": "report-may.xlsx"
      }
    }

What this slice does NOT do (deferred):
- Receipt OCR / Claude-vision extraction — receipts come in already-
  extracted (slice 2 will swap `parse_receipts_csv` for a vision
  pipeline; nothing else here changes).
- LLM judgment on FX / ambiguous cases — stubbed; the rows land in
  Needs Review with the [STUB] reason.
- Zoho journal-entry export — deferred until the review-report shape
  is validated against Chris's first real month.
- Persistence / audit log / multi-tenant DB — slice 1 is a single
  process invocation. Re-runs overwrite the output file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import os
from decimal import Decimal

from .categorize import categorize_receipts
from .ingest._common import ParseIssue
from .ingest.receipts_csv import parse_receipts_csv_tolerant
from .ingest.statement_csv import parse_statement_csv_tolerant
from .ingest.statement_xlsx import parse_statement_xlsx_tolerant
from .llm.client import LLMClient, OpenAIClient
from .llm.cost import CostTracker
from .matching.deterministic import match_month
from .matching.judgment import judge_fx_match
from .matching.types import MatchOutcome, Receipt, Transaction
from .output.report_xlsx import write_report


class ConfigError(ValueError):
    """Raised when the run config is malformed or points at missing files."""


def _load_statement(
    cfg: dict, config_dir: Path
) -> tuple[list[Transaction], list[ParseIssue]]:
    s = cfg.get("statement")
    if not isinstance(s, dict):
        raise ConfigError("config.statement is missing or not an object")

    required = ("path", "account_id", "legal_entity_id", "account_card_currency", "column_map")
    missing = [k for k in required if k not in s]
    if missing:
        raise ConfigError(f"config.statement missing: {', '.join(missing)}")

    path = (config_dir / s["path"]).resolve()
    if not path.exists():
        raise ConfigError(f"statement file not found: {path}")

    suffix = path.suffix.lower()
    column_map = s["column_map"]
    kwargs = dict(
        path=path,
        column_map=column_map,
        account_id=s["account_id"],
        legal_entity_id=s["legal_entity_id"],
        account_card_currency=s["account_card_currency"],
    )

    if suffix == ".csv":
        return parse_statement_csv_tolerant(**kwargs)
    if suffix in (".xlsx", ".xlsm"):
        sheet_name = s.get("sheet_name")
        return parse_statement_xlsx_tolerant(**kwargs, sheet_name=sheet_name)
    raise ConfigError(
        f"statement.path must end in .csv / .xlsx / .xlsm, got {suffix!r}"
    )


def _load_receipts(
    cfg: dict, config_dir: Path, legal_entity_id: str
) -> tuple[list[Receipt], list[ParseIssue]]:
    r = cfg.get("receipts")
    if not isinstance(r, dict):
        raise ConfigError("config.receipts is missing or not an object")
    if "path" not in r:
        raise ConfigError("config.receipts.path is required")

    path = (config_dir / r["path"]).resolve()
    if not path.exists():
        raise ConfigError(f"receipts file not found: {path}")

    return parse_receipts_csv_tolerant(
        path=path,
        legal_entity_id=legal_entity_id,
        default_currency=r.get("default_currency"),
    )


def _apply_judgment_stub(outcome: MatchOutcome, tx_by_id, rec_by_id) -> None:
    """Replace each judgment_required entry with the stub's verdict.

    Today the stub returns the same Match flagged for review; this
    keeps the call shape stable for slice 2 when Claude is wired in.
    """
    if not outcome.judgment_required:
        return
    judged: list = []
    for m in outcome.judgment_required:
        tx = tx_by_id.get(m.transaction_id)
        rec = rec_by_id.get(m.document_id)
        if tx is None or rec is None:
            judged.append(m)
            continue
        judged.append(judge_fx_match(tx, rec))
    outcome.judgment_required = judged


def run(
    config_path: Path,
    out_override: Path | None = None,
    *,
    dry_run: bool = False,
) -> Path | None:
    """Execute the reconciliation pipeline.

    Returns the report path on a normal run. Returns None on
    `dry_run=True` (Summary is printed to stdout, no xlsx written —
    ANNEALING B4).
    """
    config_path = config_path.resolve()
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    config_dir = config_path.parent

    transactions, stmt_issues = _load_statement(cfg, config_dir)
    receipts, receipt_issues = _load_receipts(
        cfg, config_dir, legal_entity_id=cfg["statement"]["legal_entity_id"]
    )

    parse_errors: list[tuple[str, int, str]] = [
        (issue.file_name, issue.line_number, issue.message)
        for issue in (*stmt_issues, *receipt_issues)
    ]

    llm_client, cost_tracker = _build_llm_client(cfg)

    # BLUEPRINT LD-2: categorize per line item BEFORE matching so the
    # report writer sees Tier 1/2/3 sources on every receipt's items.
    receipts = categorize_receipts(receipts, client=llm_client)

    outcome = match_month(transactions, receipts)

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    _apply_judgment_stub(outcome, tx_by_id, rec_by_id)

    if dry_run:
        _print_dry_run_summary(
            outcome, transactions, receipts, parse_errors, cost_tracker
        )
        return None

    out_cfg = cfg.get("output") or {}
    out_path = out_override or (config_dir / (out_cfg.get("path") or "report.xlsx"))

    return write_report(
        outcome,
        transactions,
        receipts,
        out_path,
        parse_errors=parse_errors,
        llm_cost=cost_tracker.total_cost_usd if cost_tracker else None,
    )


def _build_llm_client(cfg: dict) -> tuple[LLMClient | None, CostTracker | None]:
    """Read `llm:` block from config and instantiate a client.

    Returns `(None, None)` when no `llm:` block is present —
    categorize_receipts falls back to the keyword stub.

    Shape:
        {
          "llm": {
            "provider": "openai",            # required if block present
            "model": "gpt-4o-mini",          # optional, defaults shown
            "api_key_env": "OPENAI_API_KEY"  # optional, defaults shown
          }
        }
    """
    llm_cfg = cfg.get("llm")
    if not isinstance(llm_cfg, dict):
        return None, None

    provider = llm_cfg.get("provider", "openai")
    if provider != "openai":
        raise ConfigError(
            f"config.llm.provider {provider!r} not supported in slice 2 "
            f"(only 'openai'); per the 2026-06-01 stack pivot"
        )

    model = llm_cfg.get("model", "gpt-4o-mini")
    api_key_env = llm_cfg.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ConfigError(
            f"LLM API key not found in env var {api_key_env!r}. "
            f"Either set it before running, or remove the `llm:` block "
            f"from the config to use the keyword-stub fallback."
        )

    tracker = CostTracker()
    client = OpenAIClient(model=model, api_key=api_key, cost_tracker=tracker)
    return client, tracker


def _print_dry_run_summary(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    parse_errors: list[tuple[str, int, str]],
    cost_tracker: CostTracker | None,
) -> None:
    """B4 dry-run output: terse counts to stdout, no file write."""
    n_tx = len(transactions)
    n_rec = len(receipts)
    n_matched = len(outcome.matches)
    n_review = len(outcome.judgment_required) + len(
        {m.transaction_id for m in outcome.ambiguous}
    )
    n_unmatched = len(outcome.unmatched_transactions)
    match_rate = (n_matched / n_tx * 100) if n_tx else 0.0

    print("DRY RUN — no xlsx written")
    print(f"  Transactions: {n_tx}")
    print(f"  Receipts:     {n_rec}")
    print(f"  Matched:      {n_matched}  ({match_rate:.1f}%)")
    print(f"  Needs review: {n_review}")
    print(f"  Unmatched tx: {n_unmatched}")
    print(f"  Parse errors: {len(parse_errors)}")
    if cost_tracker and cost_tracker.call_count > 0:
        print(
            f"  LLM calls:    {cost_tracker.call_count}  "
            f"(${cost_tracker.total_cost_usd:.4f})"
        )
    if parse_errors:
        print()
        print("First parse errors (max 5):")
        for file_name, line_no, msg in parse_errors[:5]:
            print(f"  {file_name}:{line_no}  {msg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="expense-recon",
        description="Brisken expense reconciliation tool (slice 1).",
    )
    parser.add_argument(
        "--config", required=True, type=Path,
        help="Path to the JSON run config (see cli.py docstring for shape).",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Override the output report path from the config.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print Summary counts to stdout, skip xlsx write (ANNEALING B4).",
    )
    args = parser.parse_args(argv)

    try:
        report_path = run(args.config, args.out, dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if report_path is not None:
        print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
