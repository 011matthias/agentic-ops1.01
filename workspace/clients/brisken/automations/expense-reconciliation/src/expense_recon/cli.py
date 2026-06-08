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
- FX judgment: real LLM call when the config has an `llm:` block
  (D1b); the keyword/no-LLM path falls back to the [STUB] reason.
  Either way every FX case lands in Needs Review. Ambiguous-candidate
  judgment is still stubbed (BLUEPRINT 2.4).
- Zoho journal POSTING (slice 4b) — irreversible, stays gated. The
  tool writes a Zoho-import CSV (`zoho:` block, slice 4.6/4.9) but
  never posts journals to Zoho itself.
- Persistence / audit log / multi-tenant DB — slice 1 is a single
  process invocation. Re-runs overwrite the output file.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import os
from decimal import Decimal

from .categorize import categorize_receipts
from .ingest._common import ParseIssue
from .ingest.chart_of_accounts import ChartOfAccounts
from .ingest.receipts_csv import parse_receipts_csv_tolerant
from .ingest.statement_csv import parse_statement_csv_tolerant
from .ingest.statement_xlsx import parse_statement_xlsx_tolerant
from .llm.client import LLMClient, OpenAIClient
from .llm.cost import CostTracker
from .matching.deterministic import match_month
from .matching.judgment import judge_ambiguous, judge_fx_match
from .matching.types import Match, MatchOutcome, Receipt, Transaction
from .output.report_xlsx import write_report
from .output.zoho_export import write_zoho_export
from .zoho.client import ZohoClient, ZohoConfig


logger = logging.getLogger("expense_recon")


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


def _apply_judgment(
    outcome: MatchOutcome, tx_by_id, rec_by_id, client: LLMClient | None
) -> None:
    """Replace each judgment_required entry with the judgment verdict.

    With an `LLMClient`, every FX case gets a real model judgment
    (D1b); without one, `judge_fx_match` returns the stub Match. Either
    way the entry stays in `judgment_required` with
    `requires_review=True` — the reconciliation guarantee holds and
    Chris reviews every FX case (call-outcomes D2).
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
        judged.append(judge_fx_match(tx, rec, client=client))
    # In-place: MatchOutcome is frozen (E6); rebinding the attribute
    # would raise. Slice-assignment revises the same list object.
    outcome.judgment_required[:] = judged


def _apply_ambiguous_judgment(
    outcome: MatchOutcome, tx_by_id, rec_by_id, client: LLMClient | None
) -> None:
    """Ask the LLM to break each ambiguous tie (D-series, judge_ambiguous).

    The model's pick is promoted to the front of that transaction's
    candidate group and annotated; every candidate stays in the bucket
    so no receipt is silently dropped (reconciliation guarantee). No-op
    without a client — the tie stands for human review.
    """
    if client is None or not outcome.ambiguous:
        return

    groups: dict[str, list[Match]] = {}
    for m in outcome.ambiguous:
        groups.setdefault(m.transaction_id, []).append(m)

    rebuilt: list[Match] = []
    for tx_id, group in groups.items():
        tx = tx_by_id.get(tx_id)
        pick = judge_ambiguous(tx, group, rec_by_id, client=client) if tx else None
        if pick is None:
            rebuilt.extend(group)
            continue
        others = [m for m in group if m.document_id != pick.document_id]
        rebuilt.append(pick)
        rebuilt.extend(others)
    outcome.ambiguous[:] = rebuilt


def run(
    config_path: Path,
    out_override: Path | None = None,
    *,
    dry_run: bool = False,
    explain: bool = False,
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
    logger.info("run started: config=%s", config_path)

    transactions, stmt_issues = _load_statement(cfg, config_dir)
    receipts, receipt_issues = _load_receipts(
        cfg, config_dir, legal_entity_id=cfg["statement"]["legal_entity_id"]
    )
    logger.info(
        "ingested %d transactions, %d receipts", len(transactions), len(receipts)
    )

    parse_errors: list[tuple[str, int, str]] = [
        (issue.file_name, issue.line_number, issue.message)
        for issue in (*stmt_issues, *receipt_issues)
    ]
    if parse_errors:
        logger.warning("%d parse error(s) — see Errors sheet", len(parse_errors))
        for file_name, line_no, msg in parse_errors:
            logger.debug("parse error %s:%s %s", file_name, line_no, msg)

    llm_client, cost_tracker = _build_llm_client(cfg)
    logger.info("LLM client: %s", "enabled" if llm_client else "none (keyword stub)")

    # BLUEPRINT 4.9: load Brisken's chart of accounts (live API pull or
    # cached CSV) and narrow it to the owner-approved operating-expense
    # groups, so the categorizer picks a real Zoho leaf account per LD-2.
    chart_of_accounts, zoho_cfg = _build_chart_of_accounts(cfg, config_dir)
    account_labels: list[str] | None = None
    if chart_of_accounts is not None:
        postable = chart_of_accounts.postable_expense_accounts(
            scope_groups=zoho_cfg.get("scope_groups")
        )
        account_labels = chart_of_accounts.llm_account_labels(postable)
        logger.info(
            "chart of accounts: %d accounts, %d in-scope postable",
            len(chart_of_accounts), len(postable),
        )

    # BLUEPRINT LD-2: categorize per line item BEFORE matching so the
    # report writer sees Tier 1/2/3 sources on every receipt's items.
    receipts = categorize_receipts(
        receipts, client=llm_client, chart_of_accounts=account_labels
    )

    outcome = match_month(transactions, receipts)
    logger.info(
        "matched=%d, judgment=%d, ambiguous=%d, unmatched_tx=%d, unmatched_rec=%d",
        len(outcome.matches),
        len(outcome.judgment_required),
        len(outcome.ambiguous),
        len(outcome.unmatched_transactions),
        len(outcome.unmatched_receipts),
    )

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    _apply_judgment(outcome, tx_by_id, rec_by_id, llm_client)
    _apply_ambiguous_judgment(outcome, tx_by_id, rec_by_id, llm_client)
    if cost_tracker and cost_tracker.call_count:
        logger.info(
            "LLM: %d call(s), est. $%.4f",
            cost_tracker.call_count,
            cost_tracker.total_cost_usd,
        )

    if dry_run:
        _print_dry_run_summary(
            outcome, transactions, receipts, parse_errors, cost_tracker
        )
        return None

    out_cfg = cfg.get("output") or {}
    out_path = out_override or (config_dir / (out_cfg.get("path") or "report.xlsx"))

    report_path = write_report(
        outcome,
        transactions,
        receipts,
        out_path,
        parse_errors=parse_errors,
        llm_cost=cost_tracker.total_cost_usd if cost_tracker else None,
        explain=explain,
    )

    # BLUEPRINT 4.6 + 4.9: write the Zoho journal-entry import CSV when a
    # chart of accounts is loaded and an export path is configured. The
    # CoA resolves the debit accounts; `card_accounts` resolves the
    # balancing credit. Journal POSTING to Zoho (4b) stays gated.
    if chart_of_accounts is not None and zoho_cfg.get("export_path"):
        export_path = (config_dir / zoho_cfg["export_path"]).resolve()
        write_zoho_export(
            outcome,
            transactions,
            receipts,
            export_path,
            chart_of_accounts=chart_of_accounts,
            card_accounts=zoho_cfg.get("card_accounts"),
        )
        logger.info("wrote Zoho journal export: %s", export_path)
        print(f"Wrote Zoho export: {export_path}")

    return report_path


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


def _build_chart_of_accounts(
    cfg: dict, config_dir: Path
) -> tuple[ChartOfAccounts | None, dict]:
    """Read the `zoho:` block and load Brisken's chart of accounts.

    Returns `(None, {})` when there is no `zoho:` block (or it is
    disabled) — the categorizer then runs without account labels and no
    Zoho export is written, preserving slice 1–3 behaviour.

    Shape:
        {
          "zoho": {
            "enabled": true,                  // optional, default true
            "coa_source": "api",              // "api" | "csv"
            "coa_csv_path": "chart.csv",      // required when source == "csv"
            "coa_column_map": { ... },        // optional, csv only
            "scope_groups": [                 // approved root-group names;
              "Travel Expense",               //   lives in the run config,
              "Marketing & Selling Expenses", //   NOT in the tool. Omit to
              "Professional Fees",            //   leave the candidate set
              "Office Infra and Admin",       //   un-narrowed.
              "IT: Computer and Internet Expenses",
              "Bank Fees and Charges",
              "Lodging"
            ],
            "export_path": "zoho-journal.csv",   // optional; no export if absent
            "card_accounts": {                   // statement account_id ->
              "amex-usd": "A200 Amex Card"       //   Zoho bank/card account ref
            }
          }
        }

    Credentials for the API source come from the environment
    (`ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`,
    `ZOHO_ORG_ID`), never the config file. Brisken's real chart of
    accounts is sensitive client data and is pulled live; it is never
    committed to this repo.
    """
    z = cfg.get("zoho")
    if not isinstance(z, dict) or not z.get("enabled", True):
        return None, {}

    source = z.get("coa_source", "api")
    if source == "csv":
        if "coa_csv_path" not in z:
            raise ConfigError("config.zoho.coa_csv_path required when coa_source is 'csv'")
        coa_path = (config_dir / z["coa_csv_path"]).resolve()
        if not coa_path.exists():
            raise ConfigError(f"chart-of-accounts CSV not found: {coa_path}")
        coa = ChartOfAccounts.from_csv(coa_path, column_map=z.get("coa_column_map"))
    elif source == "api":
        try:
            client = ZohoClient(ZohoConfig.from_env())
        except ValueError as exc:
            raise ConfigError(str(exc)) from exc
        coa = ChartOfAccounts.from_api(client.list_chart_of_accounts())
    else:
        raise ConfigError(
            f"config.zoho.coa_source {source!r} not supported (use 'api' or 'csv')"
        )
    return coa, z


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

    print("DRY RUN: no xlsx written")
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
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="DEBUG-level pipeline logging to stderr (C3). Default is quiet.",
    )
    parser.add_argument(
        "--explain", action="store_true",
        help="Append an Explain sheet: per-transaction outcome + reason (A8).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        report_path = run(
            args.config, args.out, dry_run=args.dry_run, explain=args.explain
        )
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if report_path is not None:
        print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
