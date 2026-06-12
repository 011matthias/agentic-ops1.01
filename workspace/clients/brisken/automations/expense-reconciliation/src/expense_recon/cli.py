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
        "path": "expense-may.csv",             # Zoho Expense CSV, an
        "source": "expense_csv",               #   extracted-fields CSV, or a
        "column_map": {                        #   folder of images/PDFs
          "expense_date": "Expense Date",      #   ("expense_csv"|"csv"|"folder";
          "amount": "Amount",                  #   inferred from path if absent).
          "vendor": "Merchant"                 # column_map is required for
        },                                     #   source "expense_csv" only.
        "default_currency": "USD"
      },
      "output": {
        "path": "report-may.xlsx"
      },
      "run_log": {                             # optional (slice 5b)
        "path": "history.sqlite",              # opt-in run history; omit
        "operator": "chris"                    #   the block to disable
      },
      "store": {                               # optional (8.2/8.3) — persist
        "statements_path": "statements.sqlite",#   the tool's own tables so the
        "reports_path": "reports.sqlite"       #   run survives the Zoho exit
      },
      "hosting": {                             # optional (8.4) — content-address
        "root": "receipt-store",               #   filename-only receipts and
        "receipts_dir": "receipts"             #   carry a stable URL into 8.5
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
import uuid
from datetime import datetime, timezone
from pathlib import Path

import os
from decimal import Decimal

from .categorize import categorize_receipts
from .ingest._common import ParseIssue
from .ingest.chart_of_accounts import ChartOfAccounts
from .ingest.expense_csv import parse_expense_csv_tolerant
from .ingest.receipts_csv import parse_receipts_csv_tolerant
from .ingest.receipts_folder import parse_receipts_folder
from .ingest.statement_csv import parse_statement_csv_tolerant
from .ingest.statement_xlsx import parse_statement_xlsx_tolerant
from .llm.client import LLMClient, OpenAIClient
from .llm.cost import CostTracker
from .matching.deterministic import match_month
from .matching.judgment import judge_ambiguous, judge_fx_match
from .matching.types import Match, MatchOutcome, Receipt, Transaction
from .output.report_xlsx import write_report
from .runlog import RunLog, decisions_from_outcome
from .output.zoho_export import write_zoho_export
from .store import (
    ReportConflictError,
    ReportStore,
    StatementConflictError,
    StatementStore,
    group_by_report,
)
from .hosting import DEFAULT_URL_TEMPLATE, ReceiptStore, resolve_receipt_urls
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
    cfg: dict,
    config_dir: Path,
    legal_entity_id: str,
    llm_client: LLMClient | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Load receipts from a Zoho Expense CSV (Path A, BLUEPRINT 8.1), a
    slice-1 extracted-fields CSV, or a folder of images/PDFs (slice 2.2
    OCR).

    `receipts.source` is "expense_csv" | "csv" | "folder"; when absent
    it is inferred from the path (directory → folder, else "csv").
    Folder mode needs an `llm:` block — OCR has no keyword-stub
    fallback. The "expense_csv" source is config-driven and requires a
    `receipts.column_map` (logical field → Zoho export column header).
    """
    r = cfg.get("receipts")
    if not isinstance(r, dict):
        raise ConfigError("config.receipts is missing or not an object")
    if "path" not in r:
        raise ConfigError("config.receipts.path is required")

    path = (config_dir / r["path"]).resolve()
    if not path.exists():
        raise ConfigError(f"receipts path not found: {path}")

    source = r.get("source") or ("folder" if path.is_dir() else "csv")
    if source == "expense_csv":
        if path.is_dir():
            raise ConfigError(
                f"receipts.source is 'expense_csv' but {path} is a directory"
            )
        column_map = r.get("column_map")
        if not isinstance(column_map, dict) or not column_map:
            raise ConfigError(
                "receipts.source 'expense_csv' needs a `column_map` "
                "(logical field → Zoho export column header) in the config."
            )
        return parse_expense_csv_tolerant(
            path=path,
            legal_entity_id=legal_entity_id,
            column_map=column_map,
            default_currency=r.get("default_currency"),
        )
    if source == "folder":
        if not path.is_dir():
            raise ConfigError(f"receipts.source is 'folder' but {path} is not a directory")
        if llm_client is None:
            raise ConfigError(
                "receipts.source 'folder' needs an `llm:` block in the config — "
                "receipt OCR runs through the LLM and has no stub fallback."
            )
        return parse_receipts_folder(
            path=path,
            legal_entity_id=legal_entity_id,
            client=llm_client,
            default_currency=r.get("default_currency"),
        )
    if source == "csv":
        if path.is_dir():
            raise ConfigError(f"receipts.source is 'csv' but {path} is a directory")
        return parse_receipts_csv_tolerant(
            path=path,
            legal_entity_id=legal_entity_id,
            default_currency=r.get("default_currency"),
        )
    raise ConfigError(
        f"config.receipts.source {source!r} not supported "
        f"(use 'expense_csv', 'csv', or 'folder')"
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

    # LLM client first: folder-mode receipt ingest (slice 2.2 OCR)
    # needs it before any receipt is read.
    llm_client, cost_tracker = _build_llm_client(cfg)
    logger.info("LLM client: %s", "enabled" if llm_client else "none (keyword stub)")

    transactions, stmt_issues = _load_statement(cfg, config_dir)
    receipts, receipt_issues = _load_receipts(
        cfg,
        config_dir,
        legal_entity_id=cfg["statement"]["legal_entity_id"],
        llm_client=llm_client,
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

    # BLUEPRINT 8.2/8.3: persist the tool's own tables (opt-in `store:`
    # block) so the run's statement + reports survive the Zoho switch-off.
    # Returns a document_id -> report_number lookup for the export.
    report_lookup = _persist_store(cfg, config_dir, transactions, receipts)

    # BLUEPRINT 8.4: content-address filename-only receipts (opt-in
    # `hosting:` block) and resolve every receipt to a stable URL.
    receipt_urls = _host_receipts(cfg, config_dir, receipts)

    # BLUEPRINT 4.6 + 4.9 + 8.5: write the Zoho journal-entry import CSV
    # when a chart of accounts is loaded and an export path is configured.
    # The CoA resolves the debit accounts; `card_accounts` resolves the
    # balancing credit; the 8.5 reference columns carry the receipt URL
    # (8.4) + report reference (8.3). Journal POSTING to Zoho (4b) stays gated.
    if chart_of_accounts is not None and zoho_cfg.get("export_path"):
        export_path = (config_dir / zoho_cfg["export_path"]).resolve()
        write_zoho_export(
            outcome,
            transactions,
            receipts,
            export_path,
            chart_of_accounts=chart_of_accounts,
            card_accounts=zoho_cfg.get("card_accounts"),
            receipt_urls=receipt_urls,
            report_for=report_lookup,
        )
        logger.info("wrote Zoho journal export: %s", export_path)
        print(f"Wrote Zoho export: {export_path}")

    # BLUEPRINT 5.7-5.10: append this run to the SQLite run-log when a
    # `run_log:` block is configured (opt-in; no block = no file, no
    # behaviour change). Records audit metadata + one row per tx decision
    # so `expense-recon history` / `diff` can answer "what did we do".
    _record_run_log(
        cfg, config_path, config_dir, outcome, transactions, receipts,
        parse_errors, cost_tracker, report_path,
    )

    return report_path


def _persist_store(
    cfg: dict,
    config_dir: Path,
    transactions: list[Transaction],
    receipts: list[Receipt],
) -> "Callable[[str], str | None] | None":
    """Persist the tool's own tables when a `store:` block is configured
    (opt-in; no block = no file, no behaviour change — the `run_log:`
    precedent). Returns a `document_id -> report_number` lookup (8.3 cross-
    reference) for the export's report-reference column, or None when
    reports are not persisted.

    Shape:
        {
          "store": {
            "statements_path": "statements.sqlite",  # 8.2; omit to skip
            "reports_path": "reports.sqlite",         # 8.3; omit to skip
            "statement_id": "chase-2838-2026-04"      # optional; default
          }                                           #   "{account_id}:{period}"
        }
    """
    s = cfg.get("store")
    if not isinstance(s, dict):
        return None

    stmt = cfg.get("statement") or {}

    # 8.2 — bank-statement table. Dedup is global by content fingerprint;
    # statement_id is the batch identity for statement-number validation,
    # defaulting to account + the statement's date span so a re-run of the
    # same month matches (and a revised charge surfaces as a conflict).
    sp = s.get("statements_path")
    if sp:
        db_path = (config_dir / sp).resolve()
        account_id = stmt.get("account_id", "")
        statement_id = s.get("statement_id") or f"{account_id}:{_period_label(transactions)}"
        source_path = str((config_dir / stmt["path"]).resolve()) if stmt.get("path") else None
        try:
            with StatementStore(db_path) as store:
                res = store.ingest_transactions(
                    transactions, statement_id=statement_id, source_path=source_path
                )
            logger.info(
                "persisted statement %s: +%d new, %d duplicate(s)",
                statement_id, res.inserted, res.duplicates,
            )
            print(
                f"Statement persisted: {statement_id} "
                f"(+{res.inserted} new, {res.duplicates} dup)"
            )
        except StatementConflictError as exc:
            # A re-download with a revised charge under the same id. Surface
            # it rather than silently replacing the stored batch.
            logger.warning("statement not persisted (content changed): %s", exc)
            print(
                f"WARNING: statement {statement_id} changed since last run; "
                f"not persisted ({exc})"
            )

    # 8.3 — report table + per-expense cross-reference. Header fields the
    # expense lines don't carry (submitter, status) stay None (B4); period,
    # currency totals, and the count are derived from the expense group.
    report_lookup: "Callable[[str], str | None] | None" = None
    rp = s.get("reports_path")
    if rp:
        db_path = (config_dir / rp).resolve()
        with ReportStore(db_path) as store:
            for report_number, group in group_by_report(receipts).items():
                if report_number is None:
                    continue
                try:
                    store.ingest_report(group, report_number=report_number)
                except ReportConflictError as exc:
                    logger.warning("report %s not persisted: %s", report_number, exc)
                    print(
                        f"WARNING: report {report_number} changed since last run; "
                        f"not persisted ({exc})"
                    )
            # Materialize the lookup so it outlives the store handle.
            report_map = {r.document_id: store.report_for(r.document_id) for r in receipts}
        n_linked = sum(1 for v in report_map.values() if v)
        n_reports = len({v for v in report_map.values() if v})
        logger.info("persisted %d report(s), %d expense(s) cross-referenced", n_reports, n_linked)
        print(f"Reports persisted: {n_reports} report(s), {n_linked} expense(s) linked")
        report_lookup = report_map.get

    return report_lookup


def _host_receipts(
    cfg: dict, config_dir: Path, receipts: list[Receipt]
) -> "dict[str, str | None] | None":
    """Host filename-only receipts content-addressed when a `hosting:`
    block is configured (opt-in). Returns a `document_id -> URL` map for
    the export's receipt-URL column, or None when not configured.

    Shape:
        {
          "hosting": {
            "root": "receipt-store",               # content-addressed store dir
            "url_template": "/receipts/{relpath}", # optional; host-agnostic default
            "receipts_dir": "receipts"             # folder to resolve receipt_name
          }
        }
    """
    h = cfg.get("hosting")
    if not isinstance(h, dict):
        return None
    root = (config_dir / h.get("root", "receipt-store")).resolve()
    store = ReceiptStore(root, url_template=h.get("url_template", DEFAULT_URL_TEMPLATE))
    receipts_dir = h.get("receipts_dir")
    search_dir = (config_dir / receipts_dir).resolve() if receipts_dir else None
    urls = resolve_receipt_urls(receipts, store=store, search_dir=search_dir)
    n_hosted = sum(1 for v in urls.values() if v)
    logger.info("hosted/linked %d of %d receipt URL(s)", n_hosted, len(urls))
    print(f"Receipts hosted: {n_hosted} of {len(urls)} addressed")
    return urls


def _period_label(transactions: list[Transaction]) -> str:
    """A stable batch label from the statement's date span, the default
    `statement_id` when the config supplies none."""
    dates = [t.transaction_date for t in transactions if t.transaction_date]
    if not dates:
        return "all"
    return f"{min(dates).isoformat()}..{max(dates).isoformat()}"


def _record_run_log(
    cfg: dict,
    config_path: Path,
    config_dir: Path,
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    parse_errors: list[tuple[str, int, str]],
    cost_tracker: CostTracker | None,
    report_path: Path,
) -> None:
    rl_cfg = cfg.get("run_log")
    if not isinstance(rl_cfg, dict) or not rl_cfg.get("path"):
        return

    db_path = (config_dir / rl_cfg["path"]).resolve()
    run_id = uuid.uuid4().hex[:12]
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    operator = (
        rl_cfg.get("operator")
        or os.environ.get("EXPENSE_RECON_OPERATOR")
        or os.environ.get("USERNAME")
        or os.environ.get("USER")
    )

    n_review = len(outcome.judgment_required) + len(
        {m.transaction_id for m in outcome.ambiguous}
    )
    stmt = cfg.get("statement") or {}
    summary = {
        "config_path": str(config_path),
        "statement_path": stmt.get("path"),
        "account_id": stmt.get("account_id"),
        "legal_entity_id": stmt.get("legal_entity_id"),
        "report_path": str(report_path),
        "n_transactions": len(transactions),
        "n_receipts": len(receipts),
        "n_matched": len(outcome.matches),
        "n_review": n_review,
        "n_unmatched": len(outcome.unmatched_transactions),
        "n_parse_errors": len(parse_errors),
        "llm_calls": cost_tracker.call_count if cost_tracker else 0,
        "llm_cost_usd": cost_tracker.total_cost_usd if cost_tracker else Decimal("0"),
    }
    with RunLog(db_path) as rl:
        rl.record_run(
            run_id=run_id,
            created_at=created_at,
            summary=summary,
            decisions=decisions_from_outcome(outcome),
            operator=operator,
        )
    logger.info("recorded run %s to run-log %s", run_id, db_path)
    print(f"Run logged: {run_id}")


def _build_llm_client(cfg: dict) -> tuple[LLMClient | None, CostTracker | None]:
    """Read `llm:` block from config and instantiate a client.

    Returns `(None, None)` when no `llm:` block is present —
    categorize_receipts falls back to the keyword stub.

    Shape:
        {
          "llm": {
            "provider": "openai",            # required if block present
            "model": "gpt-4o-mini",          # optional, defaults shown
            "vision_model": "gpt-4o-mini",   # optional; OCR calls (2.2);
                                             #   defaults to `model`
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
    client = OpenAIClient(
        model=model,
        vision_model=llm_cfg.get("vision_model"),
        api_key=api_key,
        cost_tracker=tracker,
    )
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
    # Count distinct transactions needing review, never pair-rows (A9):
    # judgment_required holds one entry per candidate receipt.
    n_review = len(
        {m.transaction_id for m in outcome.judgment_required}
        | {m.transaction_id for m in outcome.ambiguous}
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
    if argv is None:
        argv = sys.argv[1:]

    # `expense-recon doctor --config X` routes to the pre-flight checker
    # (BLUEPRINT 5.14). The bare `expense-recon --config X` run interface
    # below is unchanged, so existing configs / docs keep working.
    if argv and argv[0] == "doctor":
        from .doctor import main as doctor_main

        return doctor_main(argv[1:])

    # `expense-recon history` / `diff` — read-only run-log views (5.8/5.9).
    if argv and argv[0] in ("history", "diff"):
        from .runlog_cli import main as runlog_main

        return runlog_main(argv[1:], command=argv[0])

    # `expense-recon calibrate --config X` — calibration metrics view
    # (slice 3b / E8). Runs the matcher, prints metrics, writes no report.
    if argv and argv[0] == "calibrate":
        from .calibrate import main as calibrate_main

        return calibrate_main(argv[1:])

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
