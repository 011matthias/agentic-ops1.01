"""Service layer between the FastAPI routes and the pipeline.

Three jobs:

* `create_run` takes the uploaded statement + receipts, auto-detects the
  statement column map (reusing `inspect.guess_column_map`), builds the
  same run config the CLI consumes, runs `cli.reconcile`, and persists a
  snapshot.
* `build_view` turns a stored snapshot plus the reviewer's decision
  overlay into a plain dict the workbench template renders.
* `regenerate_report` / `regenerate_zoho` rebuild the pipeline objects
  from the snapshot, apply the reviewer's decisions and category
  overrides, and write the export files; this is what makes the
  workbench edits actually land in the deliverables.

No framework types leak in here, the routes pass bytes and form values,
which keeps the layer unit-testable without an HTTP client.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from .. import inspect as stmt_inspect
from ..cli import ConfigError, reconcile
from ..matching.types import (
    Categorization,
    ClassificationSource,
    EXPENSE_CATEGORIES,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from ..output.report_xlsx import write_report
from .serialize import snapshot_from_dict, snapshot_to_dict
from .store import (
    STATUS_CONFIRMED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Decision,
    RunRow,
    RunStore,
)

# The documented Zoho Expense export header map (run.with-expense-csv
# example). Prefilled in the form so the common Path-A case needs no
# hand-mapping; the header names are a documented-format template and
# stay editable, per the example's "CONFIRM against a real export" note.
DEFAULT_EXPENSE_COLUMN_MAP: dict[str, str] = {
    "expense_date": "Expense Date",
    "amount": "Amount",
    "vendor": "Merchant",
    "currency": "Currency",
    "report_number": "Report Number",
    "reference": "Reference",
    "document_id": "Expense ID",
    "receipt_url": "Receipt URL",
    "receipt_name": "Receipt Name",
}

# Logical statement-column fields the form exposes for manual override.
STATEMENT_MAP_FIELDS = (
    "transaction_date",
    "amount",
    "vendor",
    "posting_date",
    "transaction_currency",
)
REQUIRED_STATEMENT_FIELDS = ("transaction_date", "amount", "vendor")


class RunInputError(Exception):
    """A user-fixable problem with the uploaded files or form values.

    `headers` and `partial_map` are populated when the statement column
    map could not be fully auto-detected, so the form can re-prompt with
    the file's real headers and whatever was guessed.
    """

    def __init__(
        self,
        message: str,
        *,
        headers: list[str] | None = None,
        partial_map: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.headers = headers
        self.partial_map = partial_map


@dataclass
class RunForm:
    account_id: str
    legal_entity_id: str
    account_card_currency: str
    sheet_name: str | None
    column_map_overrides: dict[str, str]
    receipts_source: str            # "csv" | "expense_csv"
    expense_column_map: dict[str, str]
    receipts_default_currency: str
    use_llm: bool


def _safe_name(name: str, fallback: str) -> str:
    """Strip directory components from an uploaded filename, keep a sane
    suffix. Uploads are written inside the run's own work dir, but never
    trust a client-supplied path."""
    base = Path(name).name.strip() if name else ""
    return base or fallback


def create_run(
    store: RunStore,
    data_root: Path,
    *,
    statement_bytes: bytes,
    statement_filename: str,
    receipts_bytes: bytes,
    receipts_filename: str,
    form: RunForm,
    now_iso: str,
    operator: str | None,
) -> str:
    """Save the uploads, run the pipeline, persist a snapshot. Returns the
    new run id. Raises `RunInputError` for user-fixable problems."""
    run_id = uuid.uuid4().hex[:12]
    work_dir = data_root / "runs" / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    stmt_name = _safe_name(statement_filename, "statement.csv")
    rcpt_name = _safe_name(receipts_filename, "receipts.csv")
    stmt_path = work_dir / stmt_name
    rcpt_path = work_dir / rcpt_name
    stmt_path.write_bytes(statement_bytes)
    rcpt_path.write_bytes(receipts_bytes)

    column_map = _resolve_statement_map(stmt_path, form)

    cfg = _build_config(stmt_name, rcpt_name, column_map, form)

    if form.use_llm and not os.environ.get("OPENAI_API_KEY"):
        raise RunInputError(
            "AI categorization was requested but OPENAI_API_KEY is not set "
            "in the server environment. Start the server with the key set, "
            "or leave AI off to use the keyword fallback."
        )

    try:
        result = reconcile(cfg, work_dir)
    except ConfigError as exc:
        raise RunInputError(str(exc)) from exc

    outcome = result.outcome
    n_review = len(
        {m.transaction_id for m in outcome.judgment_required}
        | {m.transaction_id for m in outcome.ambiguous}
    )
    n_tx = len(result.transactions)
    summary = {
        "n_transactions": n_tx,
        "n_receipts": len(result.receipts),
        "n_matched": len(outcome.matches),
        "n_review": n_review,
        "n_unmatched_tx": len(outcome.unmatched_transactions),
        "n_unmatched_rec": len(outcome.unmatched_receipts),
        "n_parse_errors": len(result.parse_errors),
        "match_rate": round(len(outcome.matches) / n_tx * 100, 1) if n_tx else 0.0,
        "llm_cost_usd": (
            str(result.cost_tracker.total_cost_usd) if result.cost_tracker else "0"
        ),
    }
    snapshot = snapshot_to_dict(
        result.transactions, result.receipts, outcome, result.parse_errors
    )
    label = f"{form.account_id or stmt_name} {now_iso[:10]}".strip()

    store.create_run(
        run_id=run_id,
        created_at=now_iso,
        label=label,
        operator=operator,
        summary=summary,
        snapshot=snapshot,
        config=cfg,
        work_dir=str(work_dir),
        llm_enabled=form.use_llm,
        has_coa=result.chart_of_accounts is not None,
    )
    return run_id


def _resolve_statement_map(stmt_path: Path, form: RunForm) -> dict[str, str]:
    """Auto-detect the statement column map, let form overrides win, and
    fail loudly (with the file's headers) if a required field is still
    unmapped."""
    try:
        guessed, _missing, headers = stmt_inspect.inspect(
            stmt_path, sheet_name=form.sheet_name or None
        )
    except ValueError as exc:
        raise RunInputError(str(exc)) from exc

    column_map = dict(guessed)
    for field, header in form.column_map_overrides.items():
        if header:
            column_map[field] = header

    missing = [f for f in REQUIRED_STATEMENT_FIELDS if f not in column_map]
    if missing:
        raise RunInputError(
            "Could not auto-detect these required statement columns: "
            + ", ".join(missing)
            + ". Fill them in from the file's headers and re-run.",
            headers=headers,
            partial_map=column_map,
        )
    return column_map


def _build_config(
    stmt_name: str, rcpt_name: str, column_map: dict[str, str], form: RunForm
) -> dict:
    statement = {
        "path": stmt_name,
        "account_id": form.account_id or "card",
        "legal_entity_id": form.legal_entity_id or "brisken",
        "account_card_currency": form.account_card_currency or "USD",
        "column_map": column_map,
    }
    if form.sheet_name:
        statement["sheet_name"] = form.sheet_name

    receipts: dict = {
        "path": rcpt_name,
        "source": form.receipts_source,
        "default_currency": form.receipts_default_currency or "USD",
    }
    if form.receipts_source == "expense_csv":
        receipts["column_map"] = form.expense_column_map or DEFAULT_EXPENSE_COLUMN_MAP

    cfg: dict = {
        "statement": statement,
        "receipts": receipts,
        "output": {"path": "report.xlsx"},
    }
    if form.use_llm:
        cfg["llm"] = {"provider": "openai", "model": "gpt-4o-mini"}
    return cfg


# --------------------------------------------------------------------------
# Applying reviewer decisions + overrides (shared by render and export)
# --------------------------------------------------------------------------


def _candidates_by_tx(outcome: MatchOutcome) -> dict[str, list[Match]]:
    by_tx: dict[str, list[Match]] = {}
    for bucket in (outcome.matches, outcome.judgment_required, outcome.ambiguous):
        for m in bucket:
            by_tx.setdefault(m.transaction_id, []).append(m)
    return by_tx


def apply_overrides(
    receipts: list[Receipt], overrides: dict[tuple[str, int], dict]
) -> list[Receipt]:
    """Return receipts with reviewer category reclassifications applied to
    the named line items. Frozen dataclasses, so each change is a
    `replace`, not a mutation."""
    if not overrides:
        return receipts
    out: list[Receipt] = []
    for r in receipts:
        changed = False
        new_items = []
        for i, li in enumerate(r.line_items):
            ov = overrides.get((r.document_id, i))
            if ov and ov.get("category"):
                base = li.categorization
                new_items.append(
                    replace(
                        li,
                        categorization=Categorization(
                            category=ov["category"],
                            zoho_account=ov.get("zoho_account")
                            or (base.zoho_account if base else None),
                            confidence=1.0,
                            source=ClassificationSource.LINE,
                            reasoning="reclassified by reviewer",
                        ),
                    )
                )
                changed = True
            else:
                new_items.append(li)
        out.append(replace(r, line_items=tuple(new_items)) if changed else r)
    return out


def apply_decisions(
    outcome: MatchOutcome,
    transactions: list[Transaction],
    receipts: list[Receipt],
    decisions: dict[str, Decision],
) -> MatchOutcome:
    """Rebuild a MatchOutcome reflecting the reviewer's verdicts.

    confirmed -> the (picked) match moves to `matches`; rejected -> the
    transaction moves to `unmatched_transactions`; pending -> the original
    bucket stands. The reconciliation guarantee is preserved: every
    transaction lands in exactly one bucket, and every receipt is either
    consumed by a kept match/candidate or listed in `unmatched_receipts`.
    """
    by_tx = _candidates_by_tx(outcome)
    matched_ids = {m.transaction_id for m in outcome.matches}
    judgment_ids = {m.transaction_id for m in outcome.judgment_required}
    ambiguous_ids = {m.transaction_id for m in outcome.ambiguous}

    new_matches: list[Match] = []
    new_judgment: list[Match] = []
    new_ambiguous: list[Match] = []
    new_unmatched_tx: list[str] = []
    consumed: set[str] = set()

    for tx in transactions:
        tx_id = tx.transaction_id
        cands = by_tx.get(tx_id, [])
        decision = decisions.get(tx_id)
        status = decision.status if decision else STATUS_PENDING

        if status == STATUS_CONFIRMED:
            chosen = decision.chosen_document_id if decision else None
            if chosen is None:
                chosen = next(
                    (m.document_id for m in outcome.matches if m.transaction_id == tx_id),
                    cands[0].document_id if cands else None,
                )
            if chosen is None:
                new_unmatched_tx.append(tx_id)
                continue
            orig = next((m for m in cands if m.document_id == chosen), None)
            confirmed = (
                replace(orig, requires_review=False, reason="confirmed by reviewer")
                if orig
                else Match(
                    transaction_id=tx_id,
                    document_id=chosen,
                    match_type=MatchType.POSSIBLE,
                    confidence=1.0,
                    reason="confirmed by reviewer",
                    requires_review=False,
                )
            )
            new_matches.append(confirmed)
            consumed.add(chosen)
        elif status == STATUS_REJECTED:
            new_unmatched_tx.append(tx_id)
        else:  # pending: keep the original bucket
            if tx_id in matched_ids:
                for m in outcome.matches:
                    if m.transaction_id == tx_id:
                        new_matches.append(m)
                        consumed.add(m.document_id)
            elif tx_id in judgment_ids:
                for m in outcome.judgment_required:
                    if m.transaction_id == tx_id:
                        new_judgment.append(m)
                        consumed.add(m.document_id)
            elif tx_id in ambiguous_ids:
                for m in outcome.ambiguous:
                    if m.transaction_id == tx_id:
                        new_ambiguous.append(m)
                        consumed.add(m.document_id)
            else:
                new_unmatched_tx.append(tx_id)

    new_unmatched_rec = [r.document_id for r in receipts if r.document_id not in consumed]
    return MatchOutcome(
        matches=new_matches,
        unmatched_transactions=new_unmatched_tx,
        unmatched_receipts=new_unmatched_rec,
        judgment_required=new_judgment,
        ambiguous=new_ambiguous,
    )


# --------------------------------------------------------------------------
# View model for the workbench template
# --------------------------------------------------------------------------


def _fmt_amount(value: Decimal | None) -> str:
    return "" if value is None else f"{value:,.2f}"


def _receipt_view(r: Receipt, overrides: dict[tuple[str, int], dict]) -> dict:
    items = []
    for i, li in enumerate(r.line_items):
        ov = overrides.get((r.document_id, i))
        cat = li.categorization
        if ov and ov.get("category"):
            category = ov["category"]
            source = "EDITED"
            confidence = 1.0
        elif cat is not None:
            category = cat.category
            source = cat.source.value
            confidence = cat.confidence
        else:
            category = None
            source = "UNCLASSIFIED"
            confidence = 0.0
        items.append(
            {
                "index": i,
                "description": li.description,
                "line_total": _fmt_amount(li.line_total),
                "category": category,
                "source": source,
                "confidence": confidence,
            }
        )
    return {
        "document_id": r.document_id,
        "vendor": r.detected_vendor or "",
        "date": r.detected_date.isoformat() if r.detected_date else "",
        "total": _fmt_amount(r.detected_total),
        "currency": r.detected_currency or "",
        "reference": r.detected_reference or "",
        "report_number": r.report_number or "",
        "receipt_url": r.receipt_url or "",
        "receipt_name": r.receipt_name or "",
        "line_items": items,
    }


def build_view(run: RunRow, decisions: dict[str, Decision], overrides: dict) -> dict:
    """Compose the render model: per-transaction rows with candidates and
    the reviewer's effective verdict, plus the unmatched-receipt list and
    a decision-aware summary."""
    transactions, receipts, outcome, parse_errors = snapshot_from_dict(run.snapshot)
    rec_by_id = {r.document_id: r for r in receipts}
    by_tx = _candidates_by_tx(outcome)

    matched_ids = {m.transaction_id for m in outcome.matches}
    judgment_ids = {m.transaction_id for m in outcome.judgment_required}
    ambiguous_ids = {m.transaction_id for m in outcome.ambiguous}

    def initial_bucket(tx_id: str) -> str:
        if tx_id in matched_ids:
            return "matched"
        if tx_id in judgment_ids or tx_id in ambiguous_ids:
            return "review"
        return "unmatched"

    rows = []
    n_reconciled = n_review = n_unmatched_tx = 0
    for tx in transactions:
        tx_id = tx.transaction_id
        decision = decisions.get(tx_id)
        status = decision.status if decision else STATUS_PENDING
        chosen_doc = decision.chosen_document_id if decision else None
        init = initial_bucket(tx_id)

        if status == STATUS_CONFIRMED:
            effective = "reconciled"
        elif status == STATUS_REJECTED:
            effective = "unmatched"
        else:
            effective = {"matched": "reconciled", "review": "review", "unmatched": "unmatched"}[init]

        if effective == "reconciled":
            n_reconciled += 1
        elif effective == "review":
            n_review += 1
        else:
            n_unmatched_tx += 1

        cands = []
        for m in by_tx.get(tx_id, []):
            r = rec_by_id.get(m.document_id)
            cands.append(
                {
                    "document_id": m.document_id,
                    "match_type": m.match_type.value,
                    "confidence": m.confidence,
                    "reason": m.reason,
                    "requires_review": m.requires_review,
                    "is_chosen": (m.document_id == chosen_doc)
                    or (chosen_doc is None and init == "matched"),
                    "receipt": _receipt_view(r, overrides) if r else None,
                }
            )

        rows.append(
            {
                "transaction_id": tx_id,
                "date": tx.transaction_date.isoformat() if tx.transaction_date else "",
                "vendor": tx.vendor_from_statement,
                "amount": _fmt_amount(tx.amount),
                "currency": tx.transaction_currency,
                "account_id": tx.account_id,
                "initial_bucket": init,
                "effective_bucket": effective,
                "status": status,
                "chosen_document_id": chosen_doc,
                "candidates": cands,
            }
        )

    consumed = {c["document_id"] for row in rows for c in row["candidates"]}
    unmatched_receipts = [
        _receipt_view(r, overrides) for r in receipts if r.document_id not in consumed
    ]

    n_tx = len(transactions)
    summary = {
        "n_transactions": n_tx,
        "n_receipts": len(receipts),
        "n_reconciled": n_reconciled,
        "n_review": n_review,
        "n_unmatched_tx": n_unmatched_tx,
        "n_unmatched_rec": len(unmatched_receipts),
        "match_rate": round(n_reconciled / n_tx * 100, 1) if n_tx else 0.0,
        "invariant_ok": (n_reconciled + n_review + n_unmatched_tx) == n_tx,
        "n_parse_errors": len(parse_errors),
        "llm_cost_usd": run.summary.get("llm_cost_usd", "0"),
    }

    return {
        "run_id": run.run_id,
        "label": run.label,
        "created_at": run.created_at,
        "llm_enabled": run.llm_enabled,
        "has_coa": run.has_coa,
        "summary": summary,
        "rows": rows,
        "unmatched_receipts": unmatched_receipts,
        "category_options": list(EXPENSE_CATEGORIES),
        "parse_errors": parse_errors,
    }


def regenerate_report(
    run: RunRow, decisions: dict[str, Decision], overrides: dict
) -> Path:
    """Write the xlsx report for a run with the reviewer's decisions +
    category overrides applied. Returns the path."""
    transactions, receipts, outcome, parse_errors = snapshot_from_dict(run.snapshot)
    receipts = apply_overrides(receipts, overrides)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    out_path = Path(run.work_dir) / "report.xlsx"
    write_report(effective, transactions, receipts, out_path, parse_errors=parse_errors)
    return out_path
