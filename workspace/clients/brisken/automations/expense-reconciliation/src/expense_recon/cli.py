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
        "path": "report-may.xlsx",
        "reconciled_csv": "reconciled-may.csv"  # optional flat reconciled
      },                                         #   CSV; omit to skip
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
      },
      "matching": {                            # optional (2026-07-17) — load
        "tuning_path": "match-tuning.json"     #   MatchingConfig tunables from
      },                                       #   a file (the optimize asset)
      "categorization": {                      # optional (2026-07-21) — when
        "override_er_category": true           #   true, the tool's OWN category
      }                                        #   + Zoho account win over the
    }                                          #   report's (reverses 2026-06-16;
                                               #   default false = report wins)

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
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import os
from decimal import Decimal

from .categorize import adjudicate_receipts, categorize_receipts
from .categorize_charges import categorize_charges, derive_subscription_status
from .ingest._common import ParseIssue
from .ingest.chart_of_accounts import ChartOfAccounts
from .ingest.expense_csv import parse_expense_csv_tolerant
from .ingest.expense_report_pdf import parse_expense_report_pdf_tolerant
from .ingest.receipts_csv import parse_receipts_csv_tolerant
from .ingest.receipts_folder import parse_receipts_folder
from .ingest.statement_csv import parse_statement_csv_tolerant
from .ingest.statement_pdf import parse_statement_pdf_tolerant
from .ingest.statement_xlsx import parse_statement_xlsx_tolerant
from .llm.client import LLMClient, OpenAIClient
from .llm.cost import CostTracker
from .matching.deterministic import MatchingConfig, match_month
from .matching.judgment import judge_ambiguous, judge_fx_match, judge_unmatched
from .matching.types import Categorization, Match, MatchOutcome, Receipt, Transaction
from .output.reconciled_csv import write_reconciled_csv
from .output.report_xlsx import write_report
from .output.sheet_writeback import write_sheet_writeback
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

    if "path" not in s:
        raise ConfigError("config.statement missing: path")
    if "legal_entity_id" not in s:
        raise ConfigError("config.statement missing: legal_entity_id")

    path = (config_dir / s["path"]).resolve()
    if not path.exists():
        raise ConfigError(f"statement file not found: {path}")

    suffix = path.suffix.lower()

    # Chase statement PDF (2026-06-16): account_id comes from the per-card
    # markers in the statement, and there is no column map. Only the path +
    # legal entity (and an optional card currency) are needed.
    if suffix == ".pdf":
        return parse_statement_pdf_tolerant(
            path=path,
            legal_entity_id=s["legal_entity_id"],
            account_card_currency=s.get("account_card_currency", "USD"),
        )

    # Tabular sources (CSV / Excel) carry one account and need a column map.
    required = ("account_id", "account_card_currency", "column_map")
    missing = [k for k in required if k not in s]
    if missing:
        raise ConfigError(f"config.statement missing: {', '.join(missing)}")

    kwargs = dict(
        path=path,
        column_map=s["column_map"],
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
        f"statement.path must end in .csv / .xlsx / .xlsm / .pdf, got {suffix!r}"
    )


def _load_receipts(
    cfg: dict,
    config_dir: Path,
    legal_entity_id: str,
    llm_client: LLMClient | None = None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """Load receipts from a Zoho Expense CSV (Path A, BLUEPRINT 8.1), a
    consolidated Zoho Expense report PDF (2026-07-16), a slice-1
    extracted-fields CSV, or a folder of images/PDFs (slice 2.2 OCR).

    `receipts.source` is "expense_csv" | "expense_report_pdf" | "csv" |
    "folder"; when absent it is inferred from the path (directory ->
    folder, .pdf -> expense_report_pdf, else "csv"). Folder mode needs
    an `llm:` block — OCR has no keyword-stub fallback. The
    "expense_csv" source is config-driven and requires a
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

    source = r.get("source") or (
        "folder" if path.is_dir()
        else "expense_report_pdf" if path.suffix.lower() == ".pdf"
        else "csv"
    )
    if source == "expense_report_pdf":
        if path.is_dir():
            raise ConfigError(
                f"receipts.source is 'expense_report_pdf' but {path} is a directory"
            )
        return parse_expense_report_pdf_tolerant(
            path=path,
            legal_entity_id=legal_entity_id,
            default_currency=r.get("default_currency"),
        )
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
        f"(use 'expense_csv', 'expense_report_pdf', 'csv', or 'folder')"
    )


def _apply_vision_receipts(
    cfg: dict,
    config_dir: Path,
    receipts: list[Receipt],
    llm_client: LLMClient | None,
) -> tuple[list[Receipt], list[ParseIssue]]:
    """WS2 vision stage: read the report PDF's receipt IMAGES and attach each
    receipt's real merchant + line items to its EXPENSE SUMMARY row.

    Gated by `categorization.vision_receipts: true` AND an LLM client AND a
    `receipts.source` of `expense_report_pdf` (the receipt-image pages live in
    the consolidated report PDF). A no-op returning the receipts unchanged in
    every other case — the summary stays the deterministic matching backbone.
    """
    if not (cfg.get("categorization") or {}).get("vision_receipts", False):
        return receipts, []
    if llm_client is None or not receipts:
        return receipts, []

    r = cfg.get("receipts") or {}
    if "path" not in r:
        return receipts, []
    path = (config_dir / r["path"]).resolve()
    source = r.get("source") or (
        "folder" if path.is_dir()
        else "expense_report_pdf" if path.suffix.lower() == ".pdf"
        else "csv"
    )
    if source != "expense_report_pdf" or not path.exists():
        return receipts, []

    from .ingest.expense_report_images import extract_receipt_images

    try:
        return extract_receipt_images(
            path, client=llm_client, summary_receipts=receipts
        )
    except Exception as exc:  # noqa: BLE001 - vision must never break a run
        logger.warning("vision receipt-image pass failed: %s", exc, exc_info=True)
        return receipts, [
            ParseIssue(path.name, 0, f"vision receipt-image pass failed: {exc}",
                       severity="warning")
        ]


def _apply_judgment(
    outcome: MatchOutcome, tx_by_id, rec_by_id, client: LLMClient | None,
    *, suggest_floor: float = 0.0,
) -> None:
    """Replace each judgment_required entry with the judgment verdict.

    With an `LLMClient`, every FX case gets a real model judgment
    (D1b); without one, `judge_fx_match` returns the stub Match and the
    entry stays in `judgment_required` with `requires_review=True`.

    A real verdict BELOW `suggest_floor` is unbound instead of kept
    (owner call 2026-07-24): showing a pair the model itself rejected
    at p=0.10 as "the suggested receipt" wastes the reviewer and reads
    as a tool error. The charge and the receipt fall to the plain
    unmatched buckets when nothing else claims them, so every id still
    lands in a bucket and the reconciliation guarantee holds.
    """
    if not outcome.judgment_required:
        return
    judged: list = []
    suppressed: list = []
    for m in outcome.judgment_required:
        tx = tx_by_id.get(m.transaction_id)
        rec = rec_by_id.get(m.document_id)
        if tx is None or rec is None:
            judged.append(m)
            continue
        verdict = judge_fx_match(tx, rec, client=client)
        # The judgment layer builds a fresh Match around the model's
        # verdict, which dropped the deterministic sub-scores the matcher
        # had already computed. Carry them over: every FX row otherwise
        # reaches the workbench scoring 0/100 on amount, date, vendor, and
        # card, so the review queue could not sort them and the reviewer
        # could not see WHY a pair was proposed. The verdict itself
        # (match_type, confidence, reason) still comes from the judgment.
        full = replace(
            verdict,
            score=m.score,
            amount_score=m.amount_score,
            date_score=m.date_score,
            vendor_score=m.vendor_score,
            card_score=m.card_score,
        )
        # Only a REAL model verdict can be suppressed; the no-client stub
        # (confidence 0.5) always stays, so no-LLM runs are unaffected.
        if client is not None and full.confidence < suggest_floor:
            suppressed.append(full)
            continue
        judged.append(full)
    # In-place: MatchOutcome is frozen (E6); rebinding the attribute
    # would raise. Slice-assignment revises the same list object.
    outcome.judgment_required[:] = judged
    if suppressed:
        logger.info(
            "%d FX pair(s) below suggest floor %.2f unbound to unmatched",
            len(suppressed), suggest_floor,
        )
        claimed_tx = (
            {m.transaction_id for m in outcome.matches}
            | {m.transaction_id for m in judged}
            | {m.transaction_id for m in outcome.ambiguous}
        )
        claimed_rec = (
            {m.document_id for m in outcome.matches}
            | {m.document_id for m in judged}
            | {m.document_id for m in outcome.ambiguous}
        )
        for m in suppressed:
            if (
                m.transaction_id not in claimed_tx
                and m.transaction_id not in outcome.unmatched_transactions
            ):
                outcome.unmatched_transactions.append(m.transaction_id)
                claimed_tx.add(m.transaction_id)
            if (
                m.document_id not in claimed_rec
                and m.document_id not in outcome.unmatched_receipts
            ):
                outcome.unmatched_receipts.append(m.document_id)
                claimed_rec.add(m.document_id)


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


# WS3 (2026-07-21) second-chance pass defaults. Read from the run config's
# `matching` block; every one of them only ever narrows the pass.
_SECOND_PASS_TOP_K = 3
_SECOND_PASS_MAX_CALLS = 40
_SECOND_PASS_MIN_CONFIDENCE = 0.6

# `matching` block keys this module consumes itself; everything else in the
# block is a MatchingConfig tunable and is passed through to `from_dict`,
# which raises on an unknown key (a silent typo would measure nothing).
_MATCHING_NON_TUNABLE = frozenset({
    "tuning_path",
    "llm_second_pass_unmatched",
    "llm_second_pass_top_k",
    "llm_second_pass_max_calls",
    "llm_second_pass_min_confidence",
    "llm_second_pass_date_window_days",
})


def _apply_unmatched_judgment(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    client: LLMClient | None,
    match_cfg: MatchingConfig,
    cfg: dict,
) -> None:
    """Optional second-chance LLM pass over the leftovers (WS3).

    Off unless the run config sets `matching.llm_second_pass_unmatched`.
    For each unmatched transaction it asks the model about a bounded
    shortlist of still-free receipts (see `judge_unmatched`) and, on a
    confident verdict, moves the pair from `unmatched` into
    `judgment_required`.

    The reconciliation guarantee holds by construction: ids only ever
    move between those two buckets, a receipt is claimed at most once, and
    nothing lands in `matches` — every rescue is review-flagged. Off, or
    without a client, this is a no-op.
    """
    block = cfg.get("matching") or {}
    if not block.get("llm_second_pass_unmatched"):
        return
    if client is None or not outcome.unmatched_transactions:
        return

    top_k = int(block.get("llm_second_pass_top_k", _SECOND_PASS_TOP_K))
    max_calls = int(block.get("llm_second_pass_max_calls", _SECOND_PASS_MAX_CALLS))
    min_confidence = float(
        block.get("llm_second_pass_min_confidence", _SECOND_PASS_MIN_CONFIDENCE)
    )
    date_window = int(
        block.get("llm_second_pass_date_window_days", match_cfg.fx_date_window_days)
    )

    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    free_docs = list(outcome.unmatched_receipts)

    calls_used = 0
    rescued_tx: set[str] = set()
    claimed_docs: set[str] = set()
    for tx_id in outcome.unmatched_transactions:
        if calls_used >= max_calls:
            break
        tx = tx_by_id.get(tx_id)
        if tx is None:
            continue
        available = [
            rec_by_id[doc]
            for doc in free_docs
            if doc not in claimed_docs and doc in rec_by_id
        ]
        if not available:
            break
        judged, calls = judge_unmatched(
            tx,
            available,
            client=client,
            cfg=match_cfg,
            top_k=top_k,
            date_window_days=date_window,
            min_confidence=min_confidence,
        )
        calls_used += calls
        if judged is None:
            continue
        outcome.judgment_required.append(judged)
        rescued_tx.add(tx_id)
        claimed_docs.add(judged.document_id)

    if not rescued_tx:
        logger.info(
            "second-chance pass: no rescue from %d LLM call(s)", calls_used
        )
        return

    # In-place: MatchOutcome is frozen (E6), so revise the same list objects.
    outcome.unmatched_transactions[:] = [
        tx_id for tx_id in outcome.unmatched_transactions if tx_id not in rescued_tx
    ]
    outcome.unmatched_receipts[:] = [
        doc for doc in outcome.unmatched_receipts if doc not in claimed_docs
    ]
    logger.info(
        "second-chance pass: %d transaction(s) moved to judgment from "
        "%d LLM call(s)", len(rescued_tx), calls_used,
    )


@dataclass
class ReconcileResult:
    """The in-memory result of the reconciliation pipeline, before any
    file is written.

    Produced by `reconcile()` and consumed by both the CLI `run()` (which
    writes the xlsx / Zoho export / run-log) and the web app (which
    persists a snapshot and renders the review workbench). Keeping the
    pipeline output as data, separate from the writers, is what lets the
    browser UI reuse the exact same matching/judgment path as the CLI.
    """

    outcome: MatchOutcome
    transactions: list[Transaction]
    receipts: list[Receipt]
    parse_errors: list[tuple[str, int, str]]
    cost_tracker: CostTracker | None
    chart_of_accounts: ChartOfAccounts | None
    zoho_cfg: dict
    # Slice 10 side-map: transaction_id -> Categorization for the
    # receiptless (unmatched) charges. A side-map, NOT a Transaction
    # field, so Tier 1's frozen types stay untouched; annotation only —
    # bucket membership never changes.
    charge_categorizations: dict[str, Categorization] = field(default_factory=dict)


def _load_learned(cfg: dict, config_dir: Path):
    """Build the Phase-2 learned-category lookup from a `learning:` config
    block (`{"path": "learning.sqlite"}`), opt-in like `store:`/`run_log:`.
    Absent block, or absent file, => None (no consult, no behaviour change)."""
    block = cfg.get("learning")
    if not isinstance(block, dict) or not block.get("path"):
        return None
    from .learning import MerchantCategoryLookup

    return MerchantCategoryLookup.from_db_path((config_dir / block["path"]).resolve())


def _load_match_memory(cfg: dict, config_dir: Path):
    """Build the Phase-2 (PR 2c) Match memory (vendor aliases + per-merchant
    FX) from the same `learning:` config block. Absent => None."""
    block = cfg.get("learning")
    if not isinstance(block, dict) or not block.get("path"):
        return None
    from .learning import MatchMemory

    return MatchMemory.from_db_path((config_dir / block["path"]).resolve())


def reconcile(
    cfg: dict, config_dir: Path, *, learned=None, match_memory=None,
    on_stage=None,
) -> ReconcileResult:
    """Run ingest -> categorize -> match -> judgment and return the
    in-memory result, writing nothing to disk.

    `cfg` is the parsed run config (same shape `run()` loads from a JSON
    file); `config_dir` is the base for resolving the config's relative
    paths. This is the side-effect-free core shared by the CLI and the
    web UI.

    `learned` (Phase 2) is a `MerchantCategoryLookup` consulted on the
    weak vendor-fallback path of categorization. `match_memory` (PR 2c)
    is a `MatchMemory` (vendor aliases + per-merchant FX) feeding match
    scoring/tie-break. The web UI passes both directly; the CLI falls back
    to a `learning:` config block. None => no memory consult.

    `on_stage(name)` (optional) is called at the pass boundaries
    ("reading" / "receipts" / "categorizing" / "matching" / "judging"),
    so a caller can show staged progress instead of one opaque spinner.
    Exceptions from the callback are swallowed: progress display must
    never break a run.
    """
    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                logger.debug("on_stage(%r) callback failed", name, exc_info=True)

    # LLM client first: folder-mode receipt ingest (slice 2.2 OCR)
    # needs it before any receipt is read.
    llm_client, cost_tracker = _build_llm_client(cfg)
    logger.info("LLM client: %s", "enabled" if llm_client else "none (keyword stub)")

    _stage("reading")
    transactions, stmt_issues = _load_statement(cfg, config_dir)
    _stage("receipts")
    receipts, receipt_issues = _load_receipts(
        cfg,
        config_dir,
        legal_entity_id=cfg["statement"]["legal_entity_id"],
        llm_client=llm_client,
    )
    logger.info(
        "ingested %d transactions, %d receipts", len(transactions), len(receipts)
    )

    # WS2 (2026-07-21): read the report PDF's receipt IMAGES with vision and
    # attach each receipt's real merchant + line items to its EXPENSE SUMMARY
    # row BEFORE categorization, so the ~half of summary rows with no printed
    # vendor take the vendor-aware / LINE categorization path instead of REVIEW.
    # Gated by `categorization.vision_receipts` + an LLM client; a no-op
    # otherwise (the summary stays the deterministic backbone for matching).
    _stage("receipt-images")
    receipts, vision_issues = _apply_vision_receipts(
        cfg, config_dir, receipts, llm_client
    )

    # 2026-07-22: carry each issue's SEVERITY through as a 4th element.
    # It was dropped here, so the workbench counted an advisory note
    # ("sign convention inferred", where the parser did the right thing)
    # as an error: the real April run reported "6 parse errors" of which
    # none was an error in the user's sense. Readers tolerate the old
    # 3-tuple, so snapshots written before today still load.
    parse_errors: list[tuple[str, int, str, str]] = [
        (issue.file_name, issue.line_number, issue.message, issue.severity)
        for issue in (*stmt_issues, *receipt_issues, *vision_issues)
    ]
    if parse_errors:
        logger.warning("%d parse issue(s) — see Errors sheet", len(parse_errors))
        for file_name, line_no, msg, *_ in parse_errors:
            logger.debug("parse issue %s:%s %s", file_name, line_no, msg)

    # BLUEPRINT 4.9: load Brisken's chart of accounts (live API pull or
    # cached CSV) and narrow it to the owner-approved operating-expense
    # groups, so the categorizer picks a real Zoho leaf account per LD-2.
    chart_of_accounts, zoho_cfg = _build_chart_of_accounts(cfg, config_dir)
    # WS2 (2026-07-21): when there is no `zoho:` block (the hosted web run,
    # built from an upload form) fall back to the per-entity `coa_validation`
    # chart the COA-gate provisioning injects, so the categorizer gets the
    # in-scope account labels AND the root-group adjudication has a chart to
    # resolve against on hosted runs. Without this the account override and
    # the adjudication were no-ops on every hosted upload (only the CLI's
    # explicit `zoho:` block wired a chart).
    cat_chart, account_labels, scope_groups = _resolve_categorizer_chart(
        cfg, config_dir, chart_of_accounts, zoho_cfg
    )
    # The categorizer chart (COA-validation fallback included) is the one the
    # export + workbench should see as "the run's chart".
    chart_of_accounts = cat_chart
    if cat_chart is not None and account_labels is not None:
        logger.info(
            "chart of accounts: %d accounts, %d in-scope postable",
            len(cat_chart), len(account_labels),
        )

    # BLUEPRINT LD-2: categorize per line item BEFORE matching so the
    # report writer sees Tier 1/2/3 sources on every receipt's items.
    # Phase 2: a learned merchant->category (memory) upgrades the weak
    # vendor-fallback path to Tier-1 LEARNED; a good line read still wins.
    if learned is None:
        learned = _load_learned(cfg, config_dir)
    # 2026-07-21 owner decision: when categorization.override_er_category is
    # set, the tool's own category + account are authoritative and the Zoho
    # report's often-wrong GL account no longer clobbers a correct pick.
    # Default False preserves the 2026-06-16 "report is authoritative" rule.
    override_er_category = bool(
        (cfg.get("categorization") or {}).get("override_er_category", False)
    )
    _stage("categorizing")
    receipts = categorize_receipts(
        receipts, client=llm_client, chart_of_accounts=account_labels, learned=learned,
        override_er_category=override_er_category,
    )

    # WS2 (2026-07-21): top-level adjudication. Under override_er_category the
    # tool's account no longer wins unconditionally -- only on a HEAVY mismatch
    # (a different Zoho root-group between the tool's pick and the report's
    # category). Same root-group => the report's category is kept. Deterministic
    # (no LLM call); runs only with a chart to resolve root-groups against.
    if override_er_category and cat_chart is not None:
        receipts = adjudicate_receipts(
            receipts, cat_chart, scope_groups=scope_groups
        )

    # PR 2c: learned vendor aliases + per-merchant FX feed match scoring /
    # tie-break (never bucket membership). Empty memory => default config.
    # 2026-07-17: an optional matching.tuning_path loads the file-tunable
    # scalars (MatchingConfig.from_file); learned memory merges on top.
    if match_memory is None:
        match_memory = _load_match_memory(cfg, config_dir)
    # 2026-07-22: the same tunables may also be given INLINE in the
    # `matching` block, which is how the hosted surface passes the month's
    # FX reference rates from stored settings — there is no tuning file on
    # the server, and inlining carries the rates into `run.local.json`, so a
    # run pulled off the volume reproduces the hosted match. Inline keys win
    # over the file's, so a run can override one rate without copying the
    # whole file. The second-pass keys are consumed elsewhere in this module
    # and are not MatchingConfig tunables, so they never reach from_dict.
    match_cfg = None
    matching_block = dict(cfg.get("matching") or {})
    tuning_path = matching_block.pop("tuning_path", None)
    inline = {
        k: v
        for k, v in matching_block.items()
        if k not in _MATCHING_NON_TUNABLE
    }
    if tuning_path:
        tuning = json.loads(
            (config_dir / tuning_path).read_text(encoding="utf-8")
        )
        match_cfg = MatchingConfig.from_dict({**tuning, **inline})
    elif inline:
        match_cfg = MatchingConfig.from_dict(inline)
    if match_memory:
        match_cfg = replace(
            match_cfg or MatchingConfig(),
            vendor_aliases=match_memory.vendor_aliases,
            merchant_fx=dict(match_memory.merchant_fx),
        )
    _stage("matching")
    outcome = match_month(transactions, receipts, match_cfg)
    logger.info(
        "matched=%d, judgment=%d, ambiguous=%d, unmatched_tx=%d, unmatched_rec=%d",
        len(outcome.matches),
        len(outcome.judgment_required),
        len(outcome.ambiguous),
        len(outcome.unmatched_transactions),
        len(outcome.unmatched_receipts),
    )

    _stage("judging")
    tx_by_id = {tx.transaction_id: tx for tx in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    _apply_judgment(
        outcome, tx_by_id, rec_by_id, llm_client,
        suggest_floor=(match_cfg or MatchingConfig()).fx_judgment_suggest_floor,
    )
    _apply_ambiguous_judgment(outcome, tx_by_id, rec_by_id, llm_client)
    # WS3: opt-in second chance for the leftovers, after the deterministic
    # buckets are settled so it only ever sees genuinely free receipts.
    _apply_unmatched_judgment(
        outcome, transactions, receipts, llm_client,
        match_cfg or MatchingConfig(), cfg,
    )

    # Slice 10: categorize the receiptless charges (unmatched after
    # judgment). Reads the outcome only; the result is a side-map so no
    # bucket, transaction, or receipt changes. LEARNED-first, then
    # VENDOR fallback, never LINE (charge-level LD-2 tier).
    charge_categorizations = categorize_charges(
        outcome,
        transactions,
        client=llm_client,
        chart_of_accounts=account_labels,
        learned=learned,
        override_er_category=override_er_category,
    )
    if charge_categorizations:
        n_categorized = sum(
            1 for c in charge_categorizations.values() if c.category
        )
        logger.info(
            "categorized %d of %d receiptless charge(s)",
            n_categorized, len(charge_categorizations),
        )

    if cost_tracker and cost_tracker.call_count:
        logger.info(
            "LLM: %d call(s), est. $%.4f",
            cost_tracker.call_count,
            cost_tracker.total_cost_usd,
        )

    return ReconcileResult(
        outcome=outcome,
        transactions=transactions,
        receipts=receipts,
        parse_errors=parse_errors,
        cost_tracker=cost_tracker,
        chart_of_accounts=chart_of_accounts,
        zoho_cfg=zoho_cfg,
        charge_categorizations=charge_categorizations,
    )


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

    result = reconcile(cfg, config_dir)
    outcome = result.outcome
    transactions = result.transactions
    receipts = result.receipts
    parse_errors = result.parse_errors
    cost_tracker = result.cost_tracker
    chart_of_accounts = result.chart_of_accounts
    zoho_cfg = result.zoho_cfg
    charge_categorizations = result.charge_categorizations

    if dry_run:
        _print_dry_run_summary(
            outcome, transactions, receipts, parse_errors, cost_tracker,
            charge_categorizations=charge_categorizations,
        )
        return None

    # Slice 11 (P1): derive entry_status="subscription" for vendors that
    # recur across prior months in the statements store. Annotation only;
    # fill/operator precedence (an already-set entry_status wins).
    transactions = _derive_subscriptions(cfg, config_dir, transactions)

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
        charge_categorizations=charge_categorizations,
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
        # Pre-write COA validation gate (opt-in `coa_validation:` block).
        # When present, any posting account that is not postable in the
        # target legal entity's chart is diverted to review before the
        # Books export is written. Absent block => unguarded (no change).
        coa_gate = _build_coa_gate(cfg, config_dir)
        # Slice 10 posting policy: receiptless LEARNED charges become
        # posting-eligible ONLY behind the opt-in flag (withheld-until-
        # confirmed default); VENDOR/REVIEW charges stay review-only.
        write_zoho_export(
            outcome,
            transactions,
            receipts,
            export_path,
            chart_of_accounts=chart_of_accounts,
            card_accounts=zoho_cfg.get("card_accounts"),
            receipt_urls=receipt_urls,
            report_for=report_lookup,
            coa_gate=coa_gate,
            charge_categorizations=charge_categorizations,
            include_receiptless_learned=bool(
                zoho_cfg.get("export_receiptless_learned")
            ),
        )
        logger.info("wrote Zoho journal export: %s", export_path)
        print(f"Wrote Zoho export: {export_path}")

    # Flat reconciled CSV (2026-06-16): the CSV twin of the xlsx report —
    # one row per statement line, enriched with its matched expense. Written
    # when `output.reconciled_csv` is set; reuses the same 8.4 receipt-URL /
    # 8.3 report-reference lookups as the Zoho export so the references match,
    # and needs no chart of accounts (it's the reconciliation view, not a
    # posting file).
    recon_csv = out_cfg.get("reconciled_csv")
    if recon_csv:
        recon_csv_path = (config_dir / recon_csv).resolve()
        write_reconciled_csv(
            outcome,
            transactions,
            receipts,
            recon_csv_path,
            receipt_urls=receipt_urls,
            report_for=report_lookup,
            charge_categorizations=charge_categorizations,
        )
        logger.info("wrote reconciled CSV: %s", recon_csv_path)
        print(f"Wrote reconciled CSV: {recon_csv_path}")

    # L3 sheet writeback (2026-07-15 walkthrough): hand Chris HER OWN
    # workbook back with one appended "Zoho Account (tool)" column — the
    # resolved posting account per statement row. Opt-in via
    # `output.sheet_writeback`; Excel statements only (the row anchor is
    # the sheet row number, which PDF/CSV ids don't carry).
    stmt_cfg = cfg.get("statement") or {}
    stmt_path = (
        (config_dir / stmt_cfg["path"]).resolve() if stmt_cfg.get("path") else None
    )
    if (
        out_cfg.get("sheet_writeback")
        and stmt_path is not None
        and stmt_path.suffix.lower() in (".xlsx", ".xlsm")
    ):
        writeback_path = Path(report_path).parent / (
            f"{stmt_path.stem}-categorized{stmt_path.suffix}"
        )
        write_sheet_writeback(
            stmt_path,
            writeback_path,
            outcome,
            transactions,
            receipts,
            sheet_name=stmt_cfg.get("sheet_name"),
            chart_of_accounts=chart_of_accounts,
            charge_categorizations=charge_categorizations,
        )
        logger.info("wrote sheet writeback: %s", writeback_path)
        print(f"Wrote sheet writeback: {writeback_path}")

    # BLUEPRINT 5.7-5.10: append this run to the SQLite run-log when a
    # `run_log:` block is configured (opt-in; no block = no file, no
    # behaviour change). Records audit metadata + one row per tx decision
    # so `expense-recon history` / `diff` can answer "what did we do".
    _record_run_log(
        cfg, config_path, config_dir, outcome, transactions, receipts,
        parse_errors, cost_tracker, report_path,
    )

    return report_path


def _derive_subscriptions(
    cfg: dict, config_dir: Path, transactions: list[Transaction]
) -> list[Transaction]:
    """Slice 11 (P1): annotate recurring vendors as subscriptions from
    the statements store's prior months. Opt-in by construction — it
    fires only when a `store.statements_path` is configured AND the DB
    already exists on disk (a first run has no history; never create the
    store file as a side effect of a read)."""
    s = cfg.get("store")
    if not isinstance(s, dict) or not s.get("statements_path"):
        return transactions
    db_path = (config_dir / s["statements_path"]).resolve()
    if not db_path.exists():
        return transactions
    with StatementStore(db_path) as store:
        annotated = derive_subscription_status(transactions, store)
    n_derived = sum(
        1
        for before, after in zip(transactions, annotated)
        if before.entry_status is None and after.entry_status == "subscription"
    )
    if n_derived:
        logger.info(
            "derived subscription status for %d charge(s) from statement history",
            n_derived,
        )
        print(f"Subscriptions derived from history: {n_derived}")
    return annotated


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
            "coa_source": "api",              // "api" | "csv" | "none"
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
    if source == "none":
        # The zoho block carries run config (card_accounts, export flags)
        # but explicitly no chart source. The hosted upload path fabricates
        # such a block from stored master data; its categorizer chart comes
        # from the coa_validation fallback in _resolve_categorizer_chart,
        # and a live API pull would demand ZOHO_* env vars the hosted
        # environment does not have.
        return None, z
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
            f"config.zoho.coa_source {source!r} not supported (use 'api', 'csv' or 'none')"
        )
    return coa, z


def _resolve_categorizer_chart(
    cfg: dict,
    config_dir: Path,
    chart_of_accounts: ChartOfAccounts | None,
    zoho_cfg: dict,
) -> tuple[ChartOfAccounts | None, list[str] | None, list[str] | None]:
    """Resolve the chart + in-scope account labels + scope_groups the
    categorizer and the WS2 adjudication use.

    Prefers the `zoho:` block's chart (the CLI path). When there is none — the
    hosted web run built from an upload form carries only the per-entity
    `coa_validation` block the COA-gate provisioning injects — it builds the
    chart from THAT block instead, so the account override and the root-group
    adjudication fire on hosted runs (previously no-ops there). Returns
    `(None, None, None)` when no chart can be built. Fail-open on the fallback:
    a bad `coa_validation` chart leaves the categorizer label-less rather than
    breaking the run (the export-time gate reports the real error separately).
    """
    if chart_of_accounts is not None:
        scope = zoho_cfg.get("scope_groups")
        postable = chart_of_accounts.postable_expense_accounts(scope_groups=scope)
        return chart_of_accounts, chart_of_accounts.llm_account_labels(postable), scope

    block = cfg.get("coa_validation")
    if not (
        isinstance(block, dict)
        and block.get("enabled", True)
        and block.get("chart_path")
        and block.get("org_id")
    ):
        return None, None, None

    from .coa_gate import load_entity_chart

    try:
        chart_path = (config_dir / block["chart_path"]).resolve()
        chart = load_entity_chart(chart_path, block["org_id"])
    except (KeyError, FileNotFoundError, ValueError, OSError) as exc:
        logger.warning(
            "categorizer chart from coa_validation failed (%s); "
            "categorizing without account labels", exc,
        )
        return None, None, None

    scope = block.get("scope_groups")
    postable = chart.postable_expense_accounts(scope_groups=scope)
    return chart, chart.llm_account_labels(postable), scope


def _build_coa_gate(cfg: dict, config_dir: Path):
    """Read the `coa_validation:` block and build the pre-write COA gate.

    Returns `None` when there is no `coa_validation:` block (or it is
    disabled) — the Zoho export then runs unguarded, preserving prior
    behaviour byte for byte.

    The gate validates every posting account against ONE legal entity's
    chart of accounts (a run targets one entity) and diverts any
    non-postable line to review before it reaches the Books export.

    Shape:
        {
          "coa_validation": {
            "enabled": true,                    // optional, default true
            "chart_path": "books-coa.json",     // path to the Books COA JSON
            "org_id": "822741658",              // which entity's chart
            "scope_groups": [ "Travel Expense", ... ],  // optional; restrict
            "types": [ "expense", ... ],        // optional; account-type set
            "entity_label": "Corporate Services" // optional; for review notes
          }
        }

    The Books COA JSON has the shape
    `{ "<org_id>": { "org": {...}, "accounts": [...] }, ... }`; it is
    sensitive client data and is never committed to this repo.
    """
    block = cfg.get("coa_validation")
    if not isinstance(block, dict) or not block.get("enabled", True):
        return None

    from .coa_gate import CoaGate, load_entity_chart
    from .ingest.chart_of_accounts import EXPENSE_ACCOUNT_TYPES

    chart_path = block.get("chart_path")
    if not chart_path:
        raise ConfigError("config.coa_validation.chart_path is required")
    org_id = block.get("org_id")
    if not org_id:
        raise ConfigError("config.coa_validation.org_id is required")

    path = (config_dir / chart_path).resolve()
    if not path.exists():
        raise ConfigError(f"COA validation chart_path not found: {path}")

    try:
        chart = load_entity_chart(path, org_id)
    except (KeyError, FileNotFoundError, ValueError) as exc:
        raise ConfigError(f"COA validation: {exc}") from exc

    scope_groups = block.get("scope_groups")
    types = block.get("types") or EXPENSE_ACCOUNT_TYPES
    entity = block.get("entity_label") or str(org_id)
    return CoaGate(
        chart=chart,
        scope_groups=tuple(scope_groups) if scope_groups else None,
        types=tuple(types),
        entity=entity,
    )


def _print_dry_run_summary(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    parse_errors: list[tuple[str, int, str]],
    cost_tracker: CostTracker | None,
    charge_categorizations: dict[str, Categorization] | None = None,
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
    if charge_categorizations:
        n_charge_cat = sum(
            1 for c in charge_categorizations.values() if c.category
        )
        print(f"  ... categorized (receiptless): {n_charge_cat} of {n_unmatched}")
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

    # `expense-recon label propose|accept|check` — ground-truth pairing
    # labels for matcher calibration (optimize-loop prep).
    if argv and argv[0] == "label":
        from .labeling import main as label_main

        return label_main(argv[1:])

    # `expense-recon memory list|forget|reset` — inspect / correct the
    # cross-run learning store (Phase 2 escape hatch, 2d).
    if argv and argv[0] == "memory":
        from .learning_cli import main as memory_main

        return memory_main(argv[1:])

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
