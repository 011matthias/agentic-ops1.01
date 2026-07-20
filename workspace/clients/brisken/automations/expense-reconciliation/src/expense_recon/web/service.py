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
from ..coa_provision import apply_to_config as apply_coa_provisioning
from ..duplicates import find_duplicate_charges, find_duplicate_receipts
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
from ..learning import (
    LearningStore,
    MatchMemory,
    MerchantCategoryLookup,
    learn_from_run,
    normalize_vendor,
)
from ..output.reconciled_csv import write_reconciled_csv
from ..output.report_xlsx import write_report
from ..output.zoho_export import write_zoho_export
from .serialize import (
    categorization_from_dict,
    categorization_to_dict,
    snapshot_from_dict,
    snapshot_to_dict,
)
from .store import (
    INTAKE_RECEIVED,
    STATUS_ALREADY_POSTED,
    STATUS_CONFIRMED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Decision,
    IntakeRow,
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
    # Full Zoho Expense report fields (2026-06-16). Header names are the
    # documented-format template; an absent optional column is skipped, not
    # an error, so these are safe to list even when an export lacks some.
    "payment_mode": "Payment Mode",
    "paid_through": "Paid Through",
    "category": "Category",
    "exchange_rate": "Exchange Rate",
    "amount_base": "Amount (USD)",
    "reimbursable": "Reimbursable",
    "location": "Expense Location",
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
    # Account -> legal entity map (Dirk 2026-06-16: the legal entity should
    # be derived from the card/account that paid, not typed up front). The
    # run's legal entity is looked up from `account_id`; an unmapped account
    # falls back to the account name itself (never a fabricated "brisken"),
    # which is visibly "not yet mapped" rather than a confident wrong guess.
    account_legal_entities: dict[str, str]
    account_card_currency: str
    sheet_name: str | None
    column_map_overrides: dict[str, str]
    receipts_source: str            # "csv" | "expense_csv"
    expense_column_map: dict[str, str]
    # Receipts currency. Blank means "unknown": we do NOT default to USD
    # (Dirk 2026-06-16). A receipt with neither a per-row currency nor this
    # default keeps `detected_currency=None` and is flagged for review.
    receipts_default_currency: str
    use_llm: bool

    def resolve_legal_entity(self) -> str:
        """Derive this run's legal entity from the paying account."""
        account_id = self.account_id or "card"
        return self.account_legal_entities.get(account_id) or account_id


def _safe_name(name: str, fallback: str) -> str:
    """Strip directory components from an uploaded filename, keep a sane
    suffix. Uploads are written inside the run's own work dir, but never
    trust a client-supplied path."""
    base = Path(name).name.strip() if name else ""
    return base or fallback


@dataclass
class PreparedRun:
    """The fast, fail-fast result of `prepare_run` (uploads saved, column
    map resolved, config built, cross-run memory loaded). `execute_run`
    consumes it to run the pipeline and persist the snapshot. The split
    lets the web layer validate synchronously (a bad column map is a form
    error) and run the slow pipeline in the background (PR F)."""

    run_id: str
    work_dir: Path
    stmt_name: str
    cfg: dict
    form: RunForm
    learned: object | None
    match_memory: object | None
    ai_unavailable: bool
    use_llm_effective: bool
    now_iso: str
    operator: str | None
    intake_id: str | None = None


def prepare_run(
    data_root: Path,
    *,
    statement_bytes: bytes,
    statement_filename: str,
    receipts_bytes: bytes,
    receipts_filename: str,
    form: RunForm,
    now_iso: str,
    operator: str | None,
    learning_db_path: Path | None = None,
    intake_id: str | None = None,
) -> PreparedRun:
    """Save the uploads and resolve everything the pipeline needs, fast and
    fail-fast. Raises `RunInputError` for a user-fixable problem (an
    unmappable statement). No pipeline run and no DB row yet.

    `learning_db_path` (Phase 2): when given, confirmed merchant->category
    decisions from prior runs are consulted on the vendor-fallback path so
    a known merchant auto-promotes to Tier-1 LEARNED."""
    run_id = uuid.uuid4().hex[:12]
    work_dir = data_root / "runs" / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    stmt_name = _safe_name(statement_filename, "statement.csv")
    rcpt_name = _safe_name(receipts_filename, "receipts.csv")
    stmt_path = work_dir / stmt_name
    rcpt_path = work_dir / rcpt_name
    stmt_path.write_bytes(statement_bytes)
    rcpt_path.write_bytes(receipts_bytes)

    # Chase statement PDF (2026-06-16): the parser reads the statement's own
    # structure, so there is no column map to auto-detect, and the account id
    # comes per-card from the PDF's cycle markers (one statement spans several
    # cards), not the form. column_map=None marks the PDF path; _build_config
    # emits the PDF-shaped statement block and the CLI's _load_statement routes
    # on the .pdf suffix. CSV / Excel still auto-detect their column map.
    if stmt_path.suffix.lower() == ".pdf":
        column_map = None
    else:
        column_map = _resolve_statement_map(stmt_path, form)

    # Zoho Expense report PDF (2026-07-16): sniffed from the upload, not
    # picked by the form -- the report-PDF source needs no column map, so
    # forcing it here means the operator never has to remember to flip the
    # receipts_source dropdown when Chris sends the PDF instead of the CSV.
    # The reverse mismatch (dropdown says report PDF, upload is not a .pdf)
    # is a user-fixable form error, not a deep parser failure.
    if rcpt_path.suffix.lower() == ".pdf":
        form = replace(form, receipts_source="expense_report_pdf")
    elif form.receipts_source == "expense_report_pdf":
        raise RunInputError(
            "Receipts source 'Zoho Expense report PDF' needs a .pdf upload; "
            f"this receipts file is {rcpt_path.suffix or 'without an extension'}. "
            "Upload the report PDF, or pick a CSV source."
        )

    # A requested-but-unavailable AI key must NOT block the run. The
    # keyword classifier always produces a complete reconciliation, so we
    # drop the `llm:` block, run the deterministic path, and record an
    # informational notice the workbench surfaces. Never a hard error.
    ai_unavailable = form.use_llm and not os.environ.get("OPENAI_API_KEY")
    use_llm_effective = form.use_llm and not ai_unavailable

    cfg = _build_config(
        stmt_name, rcpt_name, column_map, form, use_llm=use_llm_effective
    )
    # Phase-5 COA gate on the hosted surface: inject a per-entity
    # `coa_validation` block from the /data provisioning file (env
    # EXPENSE_RECON_COA_PROVISION) keyed on the run's legal entity, so the
    # export is validated against the paying entity's chart. Env unset /
    # entity not provisioned => cfg unchanged (fail-open). See coa_provision.
    cfg = apply_coa_provisioning(cfg, form.resolve_legal_entity())

    learned = match_memory = None
    if learning_db_path is not None:
        learned = MerchantCategoryLookup.from_db_path(learning_db_path)
        match_memory = MatchMemory.from_db_path(learning_db_path)

    return PreparedRun(
        run_id=run_id,
        work_dir=work_dir,
        stmt_name=stmt_name,
        cfg=cfg,
        form=form,
        learned=learned,
        match_memory=match_memory,
        ai_unavailable=ai_unavailable,
        use_llm_effective=use_llm_effective,
        now_iso=now_iso,
        operator=operator,
        intake_id=intake_id,
    )


def _statement_source_advisory(
    stmt_name: str, transactions: list, receipts: list
) -> str | None:
    """3.15: warn when a foreign-heavy receipt set met a non-PDF statement.

    The Chase statement PDF prints each foreign charge's ORIGINAL amount +
    currency (the two-line FX detail), which is what the deterministic
    exact-FX match consumes; the activity CSV does not carry it, so on a
    foreign-heavy month the statement source alone decides whether most
    matching is deterministic or needs judgment. Thresholds mirror
    doctor.py's `_check_statement_source`. Returns None when no advisory
    applies."""
    if Path(stmt_name).suffix.lower() == ".pdf":
        return None
    if not receipts:
        return None
    card_ccy = (
        transactions[0].account_card_currency if transactions else "USD"
    ).upper()
    foreign = sum(
        1
        for r in receipts
        if r.detected_currency and r.detected_currency.upper() != card_ccy
    )
    if foreign < 3 or foreign / len(receipts) < 0.3:
        return None
    return (
        f"{foreign} of {len(receipts)} receipts are foreign-currency but the "
        f"statement is {Path(stmt_name).suffix or 'tabular'} — the Chase "
        f"statement PDF carries each charge's original foreign amount, which "
        f"lets these match deterministically. Prefer uploading the statement "
        f"PDF for this month."
    )


def execute_run(
    store: RunStore, prepared: PreparedRun, *, on_stage=None
) -> str:
    """Run the pipeline for a prepared run and persist the snapshot. Returns
    the run id. This is the slow part (LLM OCR / categorization / judgment);
    the web layer runs it in the background and polls for completion.
    `on_stage` (optional) receives pass-boundary names for staged progress."""
    try:
        result = reconcile(
            prepared.cfg,
            prepared.work_dir,
            learned=prepared.learned,
            match_memory=prepared.match_memory,
            on_stage=on_stage,
        )
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
        "n_refunds": len(outcome.refunds),
        "n_unmatched_rec": len(outcome.unmatched_receipts),
        "n_parse_errors": len(result.parse_errors),
        "match_rate": round(len(outcome.matches) / n_tx * 100, 1) if n_tx else 0.0,
        "llm_cost_usd": (
            str(result.cost_tracker.total_cost_usd) if result.cost_tracker else "0"
        ),
        "ai_unavailable": prepared.ai_unavailable,
    }
    # 3.15 statement-source advisory: a foreign-heavy receipt set against a
    # tabular (non-PDF) statement loses the per-charge original-currency
    # detail only the Chase statement PDF carries — the input to the
    # deterministic exact-FX match. Advisory only; the run still completes.
    advisory = _statement_source_advisory(
        prepared.stmt_name, result.transactions, result.receipts
    )
    if advisory:
        summary["statement_advisory"] = advisory
    snapshot = snapshot_to_dict(
        result.transactions, result.receipts, outcome, result.parse_errors
    )
    # Slice 10: the receiptless-charge categorization side-map rides in
    # the snapshot under its own key (snapshot_from_dict ignores extras,
    # so pre-Slice-10 readers stay compatible) — the workbench renders it
    # on the no-receipt rows without re-running categorization.
    if result.charge_categorizations:
        snapshot["charge_categorizations"] = {
            tx_id: categorization_to_dict(cat)
            for tx_id, cat in result.charge_categorizations.items()
        }
    label = (
        f"{prepared.form.account_id or prepared.stmt_name} "
        f"{prepared.now_iso[:10]}"
    ).strip()

    if on_stage is not None:
        try:
            on_stage("saving")
        except Exception:  # noqa: BLE001
            pass
    store.create_run(
        run_id=prepared.run_id,
        created_at=prepared.now_iso,
        label=label,
        operator=prepared.operator,
        summary=summary,
        snapshot=snapshot,
        config=prepared.cfg,
        work_dir=str(prepared.work_dir),
        llm_enabled=prepared.use_llm_effective,
        has_coa=result.chart_of_accounts is not None,
        intake_id=prepared.intake_id,
    )
    return prepared.run_id


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
    learning_db_path: Path | None = None,
) -> str:
    """Synchronous one-call path: prepare then execute. Preserves the
    original API for the sync request path and the tests."""
    prepared = prepare_run(
        data_root,
        statement_bytes=statement_bytes,
        statement_filename=statement_filename,
        receipts_bytes=receipts_bytes,
        receipts_filename=receipts_filename,
        form=form,
        now_iso=now_iso,
        operator=operator,
        learning_db_path=learning_db_path,
    )
    return execute_run(store, prepared)


# Statement / receipts extensions the intake accepts. Deliberately the same
# set the run form accepts; anything else is a wrong-file mistake worth
# catching at upload time with friendly copy.
_STATEMENT_SUFFIXES = (".csv", ".xlsx", ".xlsm", ".pdf")
# .pdf (2026-07-16): the consolidated Zoho Expense report PDF Chris actually
# has, alongside the slice-1 extracted-fields CSV.
_RECEIPTS_SUFFIXES = (".csv", ".pdf")


def create_intake(
    store: RunStore,
    data_root: Path,
    *,
    statement_bytes: bytes,
    statement_filename: str,
    receipts_bytes: bytes | None,
    receipts_filename: str | None,
    label: str,
    card_key: str | None,
    now_iso: str,
    uploaded_by: str | None,
) -> IntakeRow:
    """Save an uploaded document set WITHOUT running the pipeline (testing
    mode: users upload, operators run). Blocking validation is minimal --
    files present with sane extensions; the column-map auto-detect runs
    best-effort into `detect_note` (advisory for the operator queue, never
    a wall in front of the uploader). Raises `RunInputError` only for the
    user-fixable minimum."""
    if not statement_bytes:
        raise RunInputError("No statement file uploaded.")
    stmt_name = _safe_name(statement_filename or "", "statement.csv")
    if Path(stmt_name).suffix.lower() not in _STATEMENT_SUFFIXES:
        raise RunInputError(
            "The statement file should be a .csv, .xlsx or .pdf export from "
            "the bank."
        )
    rcpt_name: str | None = None
    if receipts_bytes:
        rcpt_name = _safe_name(receipts_filename or "", "receipts.csv")
        if Path(rcpt_name).suffix.lower() not in _RECEIPTS_SUFFIXES:
            raise RunInputError(
                "The receipts file should be a .csv export or a Zoho Expense "
                "report .pdf."
            )
    if not label.strip():
        raise RunInputError("Please pick which card this statement is from.")

    intake_id = uuid.uuid4().hex[:12]
    work_dir = data_root / "intakes" / intake_id
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / stmt_name).write_bytes(statement_bytes)
    if rcpt_name is not None:
        (work_dir / rcpt_name).write_bytes(receipts_bytes or b"")

    detect_note = _detect_note(work_dir / stmt_name)

    store.create_intake(
        intake_id=intake_id,
        created_at=now_iso,
        label=label.strip(),
        uploaded_by=uploaded_by,
        statement_name=stmt_name,
        receipts_name=rcpt_name,
        card_key=(card_key or "").strip() or None,
        work_dir=str(work_dir),
        detect_note=detect_note,
    )
    intake = store.get_intake(intake_id)
    assert intake is not None
    return intake


def replace_intake_files(
    store: RunStore,
    intake: IntakeRow,
    *,
    statement_bytes: bytes | None,
    statement_filename: str | None,
    receipts_bytes: bytes | None,
    receipts_filename: str | None,
    now_iso: str,
) -> IntakeRow:
    """Replace (or late-add) the statement and/or receipts file on a queued
    intake (2026-07-16 user feedback: a wrongly-attached file needs a way
    out). Only intakes still in `received` may be edited -- once a run
    exists the files are the run's provenance and must not shift under it.
    Validation mirrors `create_intake`; the replaced file is deleted from
    the work dir so the operator can never grab the stale one."""
    if intake.status != INTAKE_RECEIVED:
        raise RunInputError(
            "These documents are already being processed; they can no "
            "longer be swapped. Send a new upload instead."
        )
    if not statement_bytes and not receipts_bytes:
        raise RunInputError("Pick at least one file to replace.")

    work_dir = Path(intake.work_dir)
    new_stmt_name: str | None = None
    new_rcpt_name: str | None = None
    detect_note: str | None = None

    if statement_bytes:
        new_stmt_name = _safe_name(statement_filename or "", "statement.csv")
        if Path(new_stmt_name).suffix.lower() not in _STATEMENT_SUFFIXES:
            raise RunInputError(
                "The statement file should be a .csv, .xlsx or .pdf export "
                "from the bank."
            )
    if receipts_bytes:
        new_rcpt_name = _safe_name(receipts_filename or "", "receipts.csv")
        if Path(new_rcpt_name).suffix.lower() not in _RECEIPTS_SUFFIXES:
            raise RunInputError(
                "The receipts file should be a .csv export or a Zoho Expense "
                "report .pdf."
            )

    # Validation passed for everything requested; now touch the disk.
    if new_stmt_name is not None:
        (work_dir / new_stmt_name).write_bytes(statement_bytes)
        if intake.statement_name and intake.statement_name != new_stmt_name:
            (work_dir / intake.statement_name).unlink(missing_ok=True)
        detect_note = _detect_note(work_dir / new_stmt_name)
    if new_rcpt_name is not None:
        (work_dir / new_rcpt_name).write_bytes(receipts_bytes)
        if intake.receipts_name and intake.receipts_name != new_rcpt_name:
            (work_dir / intake.receipts_name).unlink(missing_ok=True)

    store.update_intake_files(
        intake.intake_id,
        statement_name=new_stmt_name,
        receipts_name=new_rcpt_name,
        detect_note=detect_note,
        updated_at=now_iso,
    )
    updated = store.get_intake(intake.intake_id)
    assert updated is not None
    return updated


def _detect_note(stmt_path: Path) -> str:
    """Best-effort column-map advisory for the operator queue. Never raises:
    a detection failure is exactly the information the operator needs."""
    suffix = stmt_path.suffix.lower()
    if suffix == ".pdf":
        return "Chase PDF: no column map needed"
    try:
        guessed, missing, _headers = stmt_inspect.inspect(stmt_path)
    except Exception as exc:  # noqa: BLE001 - advisory only
        return f"auto-detect failed: {exc}"
    if missing:
        return "auto-detect missing: " + ", ".join(missing)
    return "column map auto-detected: " + ", ".join(
        f"{k}={v}" for k, v in sorted(guessed.items())
    )


def prepare_intake_run(
    data_root: Path,
    intake: IntakeRow,
    form: RunForm,
    *,
    now_iso: str,
    operator: str | None,
    learning_db_path: Path | None = None,
) -> PreparedRun:
    """Prepare a pipeline run from a stored intake's files (the operator's
    run-from-queue path). Reads the uploaded bytes back from the intake's
    work dir and delegates to `prepare_run`, tagging the run with the
    intake id so publish can flip the intake to `ready`."""
    intake_dir = Path(intake.work_dir)
    statement_bytes = (intake_dir / intake.statement_name).read_bytes()
    if intake.receipts_name is None:
        raise RunInputError(
            "This upload has no receipts file yet; ask for it before running."
        )
    receipts_bytes = (intake_dir / intake.receipts_name).read_bytes()
    return prepare_run(
        data_root,
        statement_bytes=statement_bytes,
        statement_filename=intake.statement_name,
        receipts_bytes=receipts_bytes,
        receipts_filename=intake.receipts_name,
        form=form,
        now_iso=now_iso,
        operator=operator,
        learning_db_path=learning_db_path,
        intake_id=intake.intake_id,
    )


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
    stmt_name: str,
    rcpt_name: str,
    column_map: dict[str, str],
    form: RunForm,
    *,
    use_llm: bool,
) -> dict:
    statement = {
        "path": stmt_name,
        # Derived from the paying account (Dirk 2026-06-16), not typed.
        "legal_entity_id": form.resolve_legal_entity(),
        "account_card_currency": form.account_card_currency or "USD",
    }
    if column_map is None:
        # PDF statement: no column map; the per-card account id comes from the
        # PDF's cycle markers, so account_id is omitted here too (the parser
        # ignores it). _load_statement routes on the .pdf suffix.
        pass
    else:
        statement["account_id"] = form.account_id or "card"
        statement["column_map"] = column_map
        if form.sheet_name:
            statement["sheet_name"] = form.sheet_name

    receipts: dict = {
        "path": rcpt_name,
        "source": form.receipts_source,
    }
    # Only set a default currency when one was given. Blank => omit it, so a
    # receipt with no currency stays unknown (detected_currency=None) and
    # gets flagged, instead of being silently stamped USD (Dirk 2026-06-16).
    if form.receipts_default_currency:
        receipts["default_currency"] = form.receipts_default_currency
    if form.receipts_source == "expense_csv":
        receipts["column_map"] = form.expense_column_map or DEFAULT_EXPENSE_COLUMN_MAP

    cfg: dict = {
        "statement": statement,
        "receipts": receipts,
        "output": {"path": "report.xlsx"},
    }
    if use_llm:
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

    Resolved in three passes so the one-receipt-one-transaction guarantee
    holds even when the reviewer manually re-assigns (steals) a receipt:

    1. confirmed decisions claim their picked receipt first; among several
       confirms contesting the same receipt the most recent one wins (by
       `updated_at`), so a fresh manual match beats a stale confirm.
    2. pending transactions keep their original bucket, but only claim a
       receipt that is still free; if the auto-picked receipt was taken in
       pass 1 the transaction falls to unmatched (this is how stealing an
       auto-matched receipt frees its former charge, with no explicit
       release step).
    3. rejected transactions go to unmatched.

    A confirmed `chosen_document_id` that was never an auto-candidate (a
    hand-made manual match) synthesizes a POSSIBLE match, so the picked
    receipt is consumed and lands in the export. Every transaction ends in
    exactly one bucket; every receipt is consumed once or listed in
    `unmatched_receipts`.
    """
    by_tx = _candidates_by_tx(outcome)
    matched_ids = {m.transaction_id for m in outcome.matches}
    judgment_ids = {m.transaction_id for m in outcome.judgment_required}
    ambiguous_ids = {m.transaction_id for m in outcome.ambiguous}

    def status_for(tx_id: str) -> str:
        d = decisions.get(tx_id)
        return d.status if d else STATUS_PENDING

    consumed: set[str] = set()
    match_by_tx: dict[str, Match] = {}
    judgment_by_tx: dict[str, list[Match]] = {}
    ambiguous_by_tx: dict[str, list[Match]] = {}

    # Pass 1: confirmed (explicit) claims, most-recent confirm first.
    # already_posted behaves like confirmed here (terminal, claims its
    # receipt so nothing else grabs it); the export layer excludes it.
    confirmed_txs = [
        tx
        for tx in transactions
        if status_for(tx.transaction_id) in (STATUS_CONFIRMED, STATUS_ALREADY_POSTED)
    ]
    confirmed_txs.sort(
        key=lambda tx: (decisions[tx.transaction_id].updated_at or ""), reverse=True
    )
    for tx in confirmed_txs:
        tx_id = tx.transaction_id
        cands = by_tx.get(tx_id, [])
        chosen = decisions[tx_id].chosen_document_id
        if chosen is None:
            chosen = next(
                (m.document_id for m in outcome.matches if m.transaction_id == tx_id),
                cands[0].document_id if cands else None,
            )
        if chosen is None or chosen in consumed:
            continue  # nothing to claim / receipt already taken -> unmatched
        orig = next((m for m in cands if m.document_id == chosen), None)
        reason = (
            "already posted in Zoho (reviewer)"
            if status_for(tx_id) == STATUS_ALREADY_POSTED
            else "confirmed by reviewer"
        )
        match_by_tx[tx_id] = (
            replace(orig, requires_review=False, reason=reason)
            if orig
            else Match(
                transaction_id=tx_id,
                document_id=chosen,
                match_type=MatchType.POSSIBLE,
                confidence=1.0,
                reason="manually matched by reviewer",
                requires_review=False,
            )
        )
        consumed.add(chosen)

    # Pass 2: pending transactions keep their bucket, claiming only free
    # receipts.
    for tx in transactions:
        tx_id = tx.transaction_id
        if status_for(tx_id) != STATUS_PENDING:
            continue
        if tx_id in matched_ids:
            m = next(m for m in outcome.matches if m.transaction_id == tx_id)
            if m.document_id not in consumed:
                match_by_tx[tx_id] = m
                consumed.add(m.document_id)
        elif tx_id in judgment_ids:
            kept = [
                m
                for m in outcome.judgment_required
                if m.transaction_id == tx_id and m.document_id not in consumed
            ]
            if kept:
                judgment_by_tx[tx_id] = kept
                consumed.update(m.document_id for m in kept)
        elif tx_id in ambiguous_ids:
            kept = [
                m
                for m in outcome.ambiguous
                if m.transaction_id == tx_id and m.document_id not in consumed
            ]
            if kept:
                ambiguous_by_tx[tx_id] = kept
                consumed.update(m.document_id for m in kept)

    # Assemble in transaction order for stable output. Refunds (3.10) keep
    # their own bucket unless the reviewer explicitly hand-matched one; any
    # other transaction not placed above (rejected, a pending claim that
    # lost its receipt, or one with no candidate) is unmatched.
    refund_ids = set(outcome.refunds)
    new_matches: list[Match] = []
    new_judgment: list[Match] = []
    new_ambiguous: list[Match] = []
    new_unmatched_tx: list[str] = []
    new_refunds: list[str] = []
    for tx in transactions:
        tx_id = tx.transaction_id
        if tx_id in match_by_tx:
            new_matches.append(match_by_tx[tx_id])
        elif tx_id in judgment_by_tx:
            new_judgment.extend(judgment_by_tx[tx_id])
        elif tx_id in ambiguous_by_tx:
            new_ambiguous.extend(ambiguous_by_tx[tx_id])
        elif tx_id in refund_ids:
            new_refunds.append(tx_id)
        else:
            new_unmatched_tx.append(tx_id)

    new_unmatched_rec = [r.document_id for r in receipts if r.document_id not in consumed]
    return MatchOutcome(
        matches=new_matches,
        unmatched_transactions=new_unmatched_tx,
        unmatched_receipts=new_unmatched_rec,
        judgment_required=new_judgment,
        ambiguous=new_ambiguous,
        refunds=new_refunds,
    )


# --------------------------------------------------------------------------
# Batch confirm (PR A — "Confirm all matched")
# --------------------------------------------------------------------------


def matched_autopick_decisions(
    run: RunRow, decisions: dict[str, Decision]
) -> list[tuple[str, str]]:
    """The (transaction_id, auto-picked document_id) pairs to confirm for a
    one-click "confirm all matched".

    Returns every transaction whose initial bucket is `matched` (it sits in
    `outcome.matches`) AND that the reviewer has not already acted on
    (status still pending). An explicit prior confirm/reject is never
    stomped. The picked document is the matcher's own assignment, so the
    batch reproduces what confirming each matched row by hand would do.
    """
    _, _, outcome, _ = snapshot_from_dict(run.snapshot)
    matched_doc_by_tx = {m.transaction_id: m.document_id for m in outcome.matches}
    out: list[tuple[str, str]] = []
    for tx_id, doc_id in matched_doc_by_tx.items():
        decision = decisions.get(tx_id)
        if decision is not None and decision.status != STATUS_PENDING:
            continue
        out.append((tx_id, doc_id))
    return out


def validate_manual_match(
    run: RunRow, transaction_id: str, document_id: str
) -> str | None:
    """Check a hand-made (charge, receipt) pairing against the run snapshot.

    Returns an error string for the caller to surface, or None when the
    pairing is allowed. Both must exist and share a legal entity (entity
    scope per v2 spec §4.2; the matcher never pairs across entities, so a
    manual pairing must not either). The receipt may currently be matched
    to another charge: confirming this pairing steals it, and the two-pass
    resolution in `apply_decisions` frees the former charge.
    """
    transactions, receipts, _, _ = snapshot_from_dict(run.snapshot)
    tx = next((t for t in transactions if t.transaction_id == transaction_id), None)
    if tx is None:
        return "Unknown transaction for this run."
    rec = next((r for r in receipts if r.document_id == document_id), None)
    if rec is None:
        return "Unknown receipt for this run."
    if rec.legal_entity_id != tx.legal_entity_id:
        return "Receipt and charge belong to different legal entities."
    return None


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
        provenance = ""
        if ov and ov.get("category"):
            category = ov["category"]
            source = "EDITED"
            confidence = 1.0
        elif cat is not None:
            category = cat.category
            source = cat.source.value
            confidence = cat.confidence
            # Phase 2: a LEARNED row carries its provenance ("learned from
            # your 2026-05 decision") so the reviewer sees why it auto-filled.
            if cat.source is ClassificationSource.LEARNED:
                provenance = cat.reasoning
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
                "provenance": provenance,
                "is_learned": source == "LEARNED",
            }
        )
    return {
        "document_id": r.document_id,
        "legal_entity_id": r.legal_entity_id,
        "vendor": r.detected_vendor or "",
        "date": r.detected_date.isoformat() if r.detected_date else "",
        "total": _fmt_amount(r.detected_total),
        "currency": r.detected_currency or "",
        # Dirk 2026-06-16: when the currency is unknown, say so in the UI
        # rather than showing a blank or a silently-assumed USD.
        "currency_unknown": r.detected_currency is None,
        # L4: the missing-comprovante state. The template renders the badge
        # only when the run-level `has_image_info` flag is set (noise guard).
        "has_receipt_image": r.has_receipt_image,
        "reference": r.detected_reference or "",
        "report_number": r.report_number or "",
        "receipt_url": r.receipt_url or "",
        "receipt_name": r.receipt_name or "",
        # Zoho Expense report fields (2026-06-16) so the workbench shows the
        # same information the ER document carries.
        "payment_mode": r.payment_mode or "",
        "paid_through": r.paid_through or "",
        "zoho_category": r.zoho_category or "",
        "exchange_rate": (str(r.exchange_rate) if r.exchange_rate is not None else ""),
        "base_amount": _fmt_amount(r.base_amount),
        "reimbursable": r.reimbursable,
        "expense_location": r.expense_location or "",
        "line_items": items,
    }


def _charge_category_view(cat) -> dict | None:
    """The render model for a receiptless charge's Slice-10 suggested
    category. None when nothing was categorized (REVIEW with no signal
    stays a plain no-receipt row, not noise)."""
    if cat is None or not cat.category:
        return None
    return {
        "category": cat.category,
        "zoho_account": cat.zoho_account or "",
        "source": cat.source.value,
        "provenance": cat.reasoning or "",
        "is_learned": cat.source is ClassificationSource.LEARNED,
    }


def build_view(run: RunRow, decisions: dict[str, Decision], overrides: dict) -> dict:
    """Compose the render model: per-transaction rows with candidates and
    the reviewer's effective verdict, plus the unmatched-receipt list and
    a decision-aware summary."""
    transactions, receipts, outcome, parse_errors = snapshot_from_dict(run.snapshot)
    rec_by_id = {r.document_id: r for r in receipts}
    by_tx = _candidates_by_tx(outcome)

    # Slice 10: receiptless-charge categorizations (extra snapshot key;
    # absent on pre-Slice-10 runs => empty map, rows render as before).
    charge_cats = {
        tx_id: categorization_from_dict(d)
        for tx_id, d in (run.snapshot.get("charge_categorizations") or {}).items()
    }

    # PR C — line items the cross-run memory auto-filled (Tier-1 LEARNED),
    # excluding any the reviewer has since reclassified. Surfaced as a stat
    # and a "show only memory-filled" filter so Chris can spot-check them.
    n_learned_lines = 0
    for r in receipts:
        for i, li in enumerate(r.line_items):
            ov = overrides.get((r.document_id, i))
            if ov and ov.get("category"):
                continue
            if (
                li.categorization
                and li.categorization.source is ClassificationSource.LEARNED
            ):
                n_learned_lines += 1

    # Resolve the reviewer's decisions once. The screen renders from the
    # SAME effective outcome the export regenerates from, so the buckets,
    # the consumed receipts, and the unmatched list can never disagree
    # between what Chris sees and what lands in the report (PR B).
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    eff_match_by_tx = {m.transaction_id: m for m in effective.matches}
    eff_review_tx = {m.transaction_id for m in effective.judgment_required} | {
        m.transaction_id for m in effective.ambiguous
    }
    eff_refund_tx = set(effective.refunds)

    matched_ids = {m.transaction_id for m in outcome.matches}
    judgment_ids = {m.transaction_id for m in outcome.judgment_required}
    ambiguous_ids = {m.transaction_id for m in outcome.ambiguous}
    refund_ids = set(outcome.refunds)

    def initial_bucket(tx_id: str) -> str:
        # The matcher's pre-decision view, shown as a hint next to the
        # reviewer's effective verdict.
        if tx_id in matched_ids:
            return "matched"
        if tx_id in judgment_ids or tx_id in ambiguous_ids:
            return "review"
        if tx_id in refund_ids:
            return "refund"
        return "unmatched"

    rows = []
    n_reconciled = n_review = n_unmatched_tx = n_refunds = 0
    # PR A — "Ready to post?" inputs. `n_undecided` counts rows the tool is
    # holding a receipt for (effective reconciled/review) that the reviewer
    # has not yet ratified or rejected (still pending); it drives the post
    # gate. `unreconciled` sums charge magnitude per currency for everything
    # not yet reconciled; `n_unmapped` counts reconciled line items that
    # would still export as "(uncategorized - assign)".
    n_undecided = n_unmapped = 0
    unreconciled: dict[str, Decimal] = {}
    for tx in transactions:
        tx_id = tx.transaction_id
        decision = decisions.get(tx_id)
        status = decision.status if decision else STATUS_PENDING
        init = initial_bucket(tx_id)

        if tx_id in eff_match_by_tx:
            effective_bucket = "reconciled"
            held_doc = eff_match_by_tx[tx_id].document_id
        elif tx_id in eff_review_tx:
            effective_bucket = "review"
            held_doc = decision.chosen_document_id if decision else None
        elif tx_id in eff_refund_tx:
            effective_bucket = "refund"
            held_doc = None
        else:
            effective_bucket = "unmatched"
            held_doc = None

        if effective_bucket == "reconciled":
            n_reconciled += 1
        elif effective_bucket == "review":
            n_review += 1
        elif effective_bucket == "refund":
            n_refunds += 1
        else:
            n_unmatched_tx += 1

        # PR-E: the workbench section this row renders in. "posted" wins
        # (her yellow / the reviewer's z-key); review needs attention;
        # a still-pending unmatched row with candidates is worth attention
        # too; everything else unmatched is "no receipt yet".
        is_posted = (
            tx.entry_status == "posted" or status == STATUS_ALREADY_POSTED
        )

        cands = []
        seen_docs = set()
        for m in by_tx.get(tx_id, []):
            r = rec_by_id.get(m.document_id)
            seen_docs.add(m.document_id)
            cands.append(
                {
                    "document_id": m.document_id,
                    "match_type": m.match_type.value,
                    "confidence": m.confidence,
                    "score": m.score,
                    "reason": m.reason,
                    "requires_review": m.requires_review,
                    "is_chosen": m.document_id == held_doc,
                    # PR D — the sub-scores behind `score`, as 0-100 ints for
                    # display, so a candidate can expand to show why it scored.
                    "amount_pct": round(m.amount_score * 100),
                    "date_pct": round(m.date_score * 100),
                    "vendor_pct": round(m.vendor_score * 100),
                    "receipt": _receipt_view(r, overrides) if r else None,
                }
            )
        # PR B — a hand-made manual match: the held receipt was never an
        # auto-candidate, so synthesize a candidate row to render it.
        if held_doc and held_doc not in seen_docs and held_doc in rec_by_id:
            cands.append(
                {
                    "document_id": held_doc,
                    "match_type": "manual",
                    "confidence": 1.0,
                    "score": None,
                    "reason": "manually matched by reviewer",
                    "requires_review": False,
                    "is_chosen": True,
                    "amount_pct": None,
                    "date_pct": None,
                    "vendor_pct": None,
                    "receipt": _receipt_view(rec_by_id[held_doc], overrides),
                }
            )

        if is_posted:
            section = "posted"
        elif effective_bucket == "review":
            section = "attention"
        elif effective_bucket == "reconciled":
            section = "matched"
        elif effective_bucket == "refund":
            section = "refund"
        elif status == STATUS_PENDING and cands:
            section = "attention"
        else:
            section = "noreceipt"

        # PR A — readiness accounting (uses the effective bucket + the
        # held receipt's lines). Posted rows are settled by definition:
        # they never block readiness and never count as unreconciled.
        if (
            status == STATUS_PENDING
            and effective_bucket in ("reconciled", "review")
            and not is_posted
        ):
            n_undecided += 1
        # Refunds (3.10) are money back, not unreconciled spend — they
        # never count toward the unreconciled-by-currency total.
        if effective_bucket not in ("reconciled", "refund") and not is_posted:
            unreconciled[tx.transaction_currency] = (
                unreconciled.get(tx.transaction_currency, Decimal("0"))
                + abs(tx.amount)
            )
        else:
            chosen_cand = next((c for c in cands if c["is_chosen"]), None)
            if chosen_cand and chosen_cand["receipt"]:
                for li in chosen_cand["receipt"]["line_items"]:
                    if not li["category"]:
                        n_unmapped += 1

        # PR C — does any candidate receipt carry a memory-filled line?
        has_learned = any(
            li["is_learned"]
            for c in cands
            if c["receipt"]
            for li in c["receipt"]["line_items"]
        )

        rows.append(
            {
                "transaction_id": tx_id,
                "date": tx.transaction_date.isoformat() if tx.transaction_date else "",
                "vendor": tx.vendor_from_statement,
                "amount": _fmt_amount(tx.amount),
                "currency": tx.transaction_currency,
                "account_id": tx.account_id,
                "legal_entity_id": tx.legal_entity_id,
                "initial_bucket": init,
                "effective_bucket": effective_bucket,
                "status": status,
                "chosen_document_id": held_doc,
                "candidates": cands,
                "has_learned": has_learned,
                # L1: her workbook's fill-color annotation (yellow=posted,
                # gray=subscription); drives the workbench chips.
                "entry_status": tx.entry_status,
                # Slice 10: the tool's suggested category for a receiptless
                # charge (None on matched rows and pre-Slice-10 snapshots).
                "charge_category": _charge_category_view(charge_cats.get(tx_id)),
                "section": section,
                "triage_score": max(
                    (c["score"] for c in cands if c["score"]), default=None
                ),
            }
        )

    # Unmatched receipts come straight from the resolved outcome, so a
    # receipt freed by a reject (or stolen by a manual match) reappears
    # here and can be re-assigned.
    unmatched_receipts = [
        _receipt_view(rec_by_id[d], overrides)
        for d in effective.unmatched_receipts
        if d in rec_by_id
    ]

    # PR D — for each unmatched charge, the closest free receipt by amount
    # ("closest was $58.40, 4 days off"), so Chris sees the near-miss the
    # matcher just barely rejected and can hand-match it if it's right.
    tx_by_id = {t.transaction_id: t for t in transactions}
    free_recs = [
        rec_by_id[d]
        for d in effective.unmatched_receipts
        if d in rec_by_id and rec_by_id[d].detected_total is not None
    ]

    def _near_miss(tx: Transaction) -> dict | None:
        if not free_recs or tx.amount is None:
            return None
        # closest by absolute amount difference; same currency preferred.
        best = min(
            free_recs,
            key=lambda r: (
                0 if r.detected_currency == tx.transaction_currency else 1,
                abs(tx.amount - r.detected_total),
            ),
        )
        date_diff = (
            abs((best.detected_date - tx.transaction_date).days)
            if best.detected_date and tx.transaction_date
            else None
        )
        return {
            "vendor": best.detected_vendor or "",
            "total": _fmt_amount(best.detected_total),
            "currency": best.detected_currency or "",
            "amount_diff": _fmt_amount(abs(tx.amount - best.detected_total)),
            "date_diff_days": date_diff,
        }

    for r in rows:
        r["near_miss"] = (
            _near_miss(tx_by_id[r["transaction_id"]])
            if r["effective_bucket"] == "unmatched"
            else None
        )

    # PR B — receipts the reviewer can pick from when hand-matching a
    # charge. Free receipts first, then any held one (picking a held one
    # steals it, freeing its current charge). `held_by` labels each so the
    # picker shows what a steal would cost.
    holder_by_doc: dict[str, str] = {}
    for m in effective.matches:
        holder_by_doc[m.document_id] = m.transaction_id
    for m in (*effective.judgment_required, *effective.ambiguous):
        holder_by_doc.setdefault(m.document_id, m.transaction_id)
    assignable_receipts = sorted(
        (
            {
                "document_id": r.document_id,
                "vendor": r.detected_vendor or "(no vendor)",
                "total": _fmt_amount(r.detected_total),
                "currency": r.detected_currency or "",
                "legal_entity_id": r.legal_entity_id,
                "held_by": holder_by_doc.get(r.document_id),
            }
            for r in receipts
        ),
        key=lambda a: (a["held_by"] is not None, a["vendor"].lower()),
    )

    # Tier-1 #1: surface the weakest items first. Unmatched transactions
    # (need a receipt) rank above review items, which rank above
    # reconciled; within a rank, low triage score first.
    _rank = {"unmatched": 0, "review": 1, "reconciled": 2, "refund": 3}
    rows.sort(
        key=lambda r: (
            _rank[r["effective_bucket"]],
            r["triage_score"] if r["triage_score"] is not None else 0,
        )
    )

    # Tier-1 #3: unmatched transactions as a first-class list (the mirror
    # of unmatched_receipts), from the post-decision effective bucket.
    unmatched_transactions = [
        {
            "transaction_id": r["transaction_id"],
            "vendor": r["vendor"],
            "date": r["date"],
            "amount": r["amount"],
            "currency": r["currency"],
            "account_id": r["account_id"],
        }
        for r in rows
        if r["effective_bucket"] == "unmatched"
    ]

    # Tier-1 #4: advisory duplicate / double-charge groups (flag only).
    tx_by_id = {t.transaction_id: t for t in transactions}
    duplicate_charges = [
        [
            {
                "transaction_id": tid,
                "vendor": tx_by_id[tid].vendor_from_statement,
                "date": tx_by_id[tid].transaction_date.isoformat()
                if tx_by_id[tid].transaction_date
                else "",
                "amount": _fmt_amount(tx_by_id[tid].amount),
                "currency": tx_by_id[tid].transaction_currency,
                "account_id": tx_by_id[tid].account_id,
            }
            for tid in grp
            if tid in tx_by_id
        ]
        for grp in find_duplicate_charges(transactions)
    ]
    duplicate_receipts = [
        [_receipt_view(rec_by_id[d], overrides) for d in grp if d in rec_by_id]
        for grp in find_duplicate_receipts(receipts)
    ]

    n_tx = len(transactions)
    n_unknown_currency = sum(1 for r in receipts if r.detected_currency is None)
    # L4 noise guard: the missing-image badge renders only when this run's
    # receipt source carries image references at all.
    has_image_info = any(r.has_receipt_image for r in receipts)
    n_missing_receipt_image = (
        sum(1 for r in receipts if not r.has_receipt_image) if has_image_info else 0
    )
    summary = {
        "n_transactions": n_tx,
        "n_receipts": len(receipts),
        # Dirk 2026-06-16: receipts whose currency we could not determine.
        # Surfaced so the reviewer sets them rather than the tool guessing.
        "n_unknown_currency": n_unknown_currency,
        "n_reconciled": n_reconciled,
        "n_review": n_review,
        "n_unmatched_tx": n_unmatched_tx,
        # 3.10: credits, partitioned before matching, never receipt-matched.
        "n_refunds": n_refunds,
        "n_unmatched_rec": len(unmatched_receipts),
        "match_rate": round(n_reconciled / n_tx * 100, 1) if n_tx else 0.0,
        "invariant_ok": (
            n_reconciled + n_review + n_unmatched_tx + n_refunds
        ) == n_tx,
        "n_parse_errors": len(parse_errors),
        "llm_cost_usd": run.summary.get("llm_cost_usd", "0"),
        "ai_unavailable": run.summary.get("ai_unavailable", False),
        "n_duplicate_groups": len(duplicate_charges) + len(duplicate_receipts),
        # PR A — "Ready to post?" bar.
        "n_undecided": n_undecided,
        "ready_to_post": n_undecided == 0,
        "n_unmapped_accounts": n_unmapped,
        "unreconciled_by_ccy": {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(unreconciled.items())
        },
        # PR C — memory legibility.
        "n_learned_lines": n_learned_lines,
        # L4 — missing receipt images (0 when the source has no image info).
        "has_image_info": has_image_info,
        "n_missing_receipt_image": n_missing_receipt_image,
        # L1 — fill-color annotations from the statement workbook.
        "n_already_posted": sum(
            1 for t in transactions if t.entry_status == "posted"
        ),
        "n_subscription": sum(
            1 for t in transactions if t.entry_status == "subscription"
        ),
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
        "unmatched_transactions": unmatched_transactions,
        "assignable_receipts": assignable_receipts,
        "duplicate_charges": duplicate_charges,
        "duplicate_receipts": duplicate_receipts,
        "category_options": list(EXPENSE_CATEGORIES),
        "parse_errors": parse_errors,
        # L3: xlsx statements can be written back with the resolved accounts.
        "writeback_available": writeback_available(run),
    }


def _charge_cats(run: RunRow) -> dict:
    """The receiptless-charge categorization side-map (Slice 10), rebuilt
    from the run snapshot keyed by transaction_id. Threaded into every
    regenerated export so web downloads carry the same receiptless-charge
    categories the workbench shows; `build_view` loads it the same way
    (see the `charge_cats` block there). Empty dict when the snapshot has
    none, so the writers behave exactly as before on receipt-only runs."""
    return {
        tx_id: categorization_from_dict(d)
        for tx_id, d in (run.snapshot.get("charge_categorizations") or {}).items()
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
    write_report(
        effective,
        transactions,
        receipts,
        out_path,
        parse_errors=parse_errors,
        charge_categorizations=_charge_cats(run),
    )
    return out_path


def _coa_gate_from_config(config: dict | None, work_dir: str):
    """Build the pre-write COA validation gate from a run's stored config
    when it carries a `coa_validation:` block, else None.

    The gate validates each posting account against the target legal
    entity's chart and diverts any non-postable line to review before the
    Zoho export is written. Absent / disabled block => None (unguarded,
    the prior web behaviour). A misconfigured block (missing chart /
    org_id / file) degrades to None rather than failing the download —
    the export still writes, with the lines flagged for the reviewer.
    """
    if not isinstance(config, dict):
        return None
    block = config.get("coa_validation")
    if not isinstance(block, dict) or not block.get("enabled", True):
        return None
    try:
        from ..cli import _build_coa_gate

        return _build_coa_gate(config, Path(work_dir))
    except Exception:  # noqa: BLE001 - never let a config slip break the download
        return None


def regenerate_zoho(
    run: RunRow, decisions: dict[str, Decision], overrides: dict
) -> Path:
    """Write the Zoho Books journal-entry import CSV for a run with the
    reviewer's decisions + category overrides applied. Returns the path.

    Mirrors `regenerate_report` but emits the Zoho import file. Only the
    effective MATCHED transactions are exported (the writer's posting
    policy); FX / review / unmatched are withheld until confirmed. Web runs
    carry no chart of accounts, so the writer's legacy path applies:
    category label on the debit side, `Card: {account_id}` on the credit
    side, both flagged for the reviewer to map in Zoho.

    When the stored run config carries a `coa_validation:` block, the
    pre-write COA gate validates each posting account against the target
    legal entity's chart and diverts any non-postable line to review, so
    the web export gets the same protection as the CLI path.
    """
    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    receipts = apply_overrides(receipts, overrides)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    # PR-E: a reviewer-marked already_posted charge never reaches the
    # journal (the fill-color "posted" path is excluded inside the writer;
    # this is the manual z-key sibling).
    posted_ids = {
        tid for tid, d in decisions.items() if d.status == STATUS_ALREADY_POSTED
    }
    if posted_ids:
        effective = replace(
            effective,
            matches=[
                m for m in effective.matches if m.transaction_id not in posted_ids
            ],
        )
    out_path = Path(run.work_dir) / "zoho_journal.csv"
    coa_gate = _coa_gate_from_config(run.config, run.work_dir)
    write_zoho_export(
        effective,
        transactions,
        receipts,
        out_path,
        coa_gate=coa_gate,
        charge_categorizations=_charge_cats(run),
        include_receiptless_learned=bool(
            (run.config or {}).get("zoho", {}).get("export_receiptless_learned")
        ),
    )
    return out_path


def regenerate_reconciled(
    run: RunRow, decisions: dict[str, Decision], overrides: dict
) -> Path:
    """Write the flat reconciled CSV for a run with the reviewer's
    decisions + category overrides applied. Returns the path.

    The CSV twin of `regenerate_report` (Dirk: "CSV + Excel of the
    reconciled data"): one row per statement line, every line's match
    status and matched-expense enrichment, after the reviewer's edits.
    Unlike the Zoho export, every statement line is written (matched,
    review, and unmatched) — it is the reconciliation view, not a posting
    file. Web runs carry no chart of accounts; the receipt's own 8.1
    fields populate the reference columns.
    """
    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    receipts = apply_overrides(receipts, overrides)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    out_path = Path(run.work_dir) / "reconciled.csv"
    write_reconciled_csv(
        effective,
        transactions,
        receipts,
        out_path,
        charge_categorizations=_charge_cats(run),
    )
    return out_path


def writeback_available(run: RunRow) -> bool:
    """True when the run's statement is an Excel workbook the L3 writeback
    can annotate (her own sheet + the resolved-account column)."""
    stmt = (run.config or {}).get("statement", {}).get("path", "")
    return Path(stmt).suffix.lower() in (".xlsx", ".xlsm")


def regenerate_writeback(
    run: RunRow, decisions: dict[str, Decision], overrides: dict
) -> Path | None:
    """Write the L3 sheet writeback for a run: HER OWN uploaded workbook
    with one new "Zoho Account (tool)" column, after the reviewer's
    decisions + overrides. Returns None when the statement is not an
    Excel workbook (CSV / PDF runs have no sheet to write back into)."""
    if not writeback_available(run):
        return None
    from ..output.sheet_writeback import write_sheet_writeback

    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    receipts = apply_overrides(receipts, overrides)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    stmt_cfg = run.config.get("statement", {})
    stmt_path = Path(run.work_dir) / stmt_cfg["path"]
    suffix = stmt_path.suffix
    out_path = Path(run.work_dir) / f"{stmt_path.stem}-categorized{suffix}"
    chart = None
    gate = _coa_gate_from_config(run.config, run.work_dir)
    if gate is not None:
        chart = getattr(gate, "chart", None)
    write_sheet_writeback(
        stmt_path,
        out_path,
        effective,
        transactions,
        receipts,
        sheet_name=stmt_cfg.get("sheet_name"),
        chart_of_accounts=chart,
        charge_categorizations=_charge_cats(run),
    )
    return out_path


# --------------------------------------------------------------------------
# Compare two runs (PR G — the browser mirror of the CLI `diff`)
# --------------------------------------------------------------------------

_COMPARE_DELTA_KEYS = (
    ("n_transactions", "Transactions"),
    ("n_matched", "Matched"),
    ("n_review", "Needs review"),
    ("n_unmatched_tx", "Unmatched charges"),
    ("n_unmatched_rec", "Unmatched receipts"),
)


def _run_buckets(snapshot: dict) -> dict[str, str]:
    """Each transaction's bucket (matched / review / refund / unmatched)
    from a run's stored matcher outcome, mirroring the CLI diff's
    `_bucket`."""
    transactions, _, outcome, _ = snapshot_from_dict(snapshot)
    matched = {m.transaction_id for m in outcome.matches}
    review = {m.transaction_id for m in outcome.judgment_required} | {
        m.transaction_id for m in outcome.ambiguous
    }
    refunds = set(outcome.refunds)
    out: dict[str, str] = {}
    for t in transactions:
        tid = t.transaction_id
        out[tid] = (
            "matched"
            if tid in matched
            else "review"
            if tid in review
            else "refund"
            if tid in refunds
            else "unmatched"
        )
    return out


def compare_runs(run_a: RunRow, run_b: RunRow) -> dict:
    """The browser mirror of `expense-recon diff`: summary count deltas plus
    which transactions changed bucket (matched / review / unmatched) between
    two runs. The id sets are unioned, so a charge present in only one run
    shows `(absent)` on the other side, the same way the CLI does. Useful
    after fixing a receipt and re-running the same month, and harmless
    across different months (no shared ids just means every row is absent
    on one side)."""
    sa, sb = run_a.summary, run_b.summary
    deltas = []
    for key, label in _COMPARE_DELTA_KEYS:
        a = int(sa.get(key, 0) or 0)
        b = int(sb.get(key, 0) or 0)
        deltas.append({"label": label, "a": a, "b": b, "delta": b - a})
    ra = float(sa.get("match_rate", 0.0) or 0.0)
    rb = float(sb.get("match_rate", 0.0) or 0.0)
    rate = {"a": ra, "b": rb, "delta": round(rb - ra, 1)}

    ba = _run_buckets(run_a.snapshot)
    bb = _run_buckets(run_b.snapshot)
    changes = [
        {
            "transaction_id": tid,
            "from": ba.get(tid, "(absent)"),
            "to": bb.get(tid, "(absent)"),
        }
        for tid in sorted(set(ba) | set(bb))
        if ba.get(tid) != bb.get(tid)
    ]
    return {"deltas": deltas, "rate": rate, "n_changed": len(changes), "changes": changes}


def commit_to_memory(
    run: RunRow,
    decisions: dict[str, Decision],
    overrides: dict,
    learning_db_path: Path,
    now_iso: str,
) -> dict:
    """Harvest this run's confirmed decisions into the durable learning
    store (Phase 2 capture). This is the explicit finalize gate: only
    confirmed matches (alias + FX) and explicit category reclassifications
    (merchant -> category) teach; a half-reviewed run teaches nothing
    wrong. Returns a summary of what was written."""
    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    confirmed_tx_ids = {
        tx_id for tx_id, d in decisions.items() if d.status == STATUS_CONFIRMED
    }
    with LearningStore(learning_db_path) as store:
        summary = learn_from_run(
            store,
            transactions=transactions,
            receipts=receipts,
            outcome=effective,
            confirmed_tx_ids=confirmed_tx_ids,
            category_overrides=overrides,
            source_run=run.run_id,
            now_iso=now_iso,
        )
    return summary.as_dict()


# --------------------------------------------------------------------------
# Memory view (PR 2e — the escape hatch in the browser, not just the CLI)
# --------------------------------------------------------------------------


def build_memory_view(learning_db_path: Path | None) -> dict:
    """Render model for the /memory page: everything the tool has learned,
    grouped by table. Read-only; an absent store yields an empty view."""
    empty = {
        "categories": [], "aliases": [], "fx": [],
        "counts": {"merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0},
        "total": 0,
    }
    if learning_db_path is None or not Path(learning_db_path).exists():
        return empty

    with LearningStore(learning_db_path) as s:
        cats = s.all_merchant_categories()
        aliases = s.get_vendor_aliases()
        fx = s.all_merchant_fx()
        counts = s.count_rows()

    categories = [
        {
            "entity": c.legal_entity_id, "vendor": c.vendor_norm,
            "category": c.category or "", "zoho_account": c.zoho_account or "",
            "count": c.decision_count, "last": (c.last_confirmed_at or "")[:10],
        }
        for c in cats
    ]
    alias_rows = [
        {
            "entity": a.legal_entity_id, "stmt": a.stmt_vendor_norm,
            "receipt": a.receipt_vendor_norm, "count": a.confirmed_count,
        }
        for a in aliases
    ]
    fx_rows = [
        {
            "entity": f.legal_entity_id, "vendor": f.vendor_norm,
            "pair": f"{f.from_ccy} -> {f.to_ccy}",
            "mean": f"{f.mean:.4f}" if f.mean is not None else "",
            "range": (f"{f.min:.4f} - {f.max:.4f}" if f.min is not None else ""),
            "n": f.count,
        }
        for f in fx
    ]
    return {
        "categories": categories, "aliases": alias_rows, "fx": fx_rows,
        "counts": counts, "total": sum(counts.values()),
    }


def forget_memory_vendor(
    learning_db_path: Path | None, legal_entity_id: str, vendor: str
) -> dict:
    """Drop everything learned for one merchant in one entity. Returns the
    per-table delete counts (zero everywhere when nothing matched)."""
    zero = {"merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0}
    vnorm = normalize_vendor(vendor)
    if learning_db_path is None or not Path(learning_db_path).exists() or not vnorm:
        return zero
    with LearningStore(learning_db_path) as s:
        return s.forget_vendor(legal_entity_id, vnorm)


def reset_memory(
    learning_db_path: Path | None,
    table: str | None = None,
    legal_entity_id: str | None = None,
) -> dict:
    """Delete learned rows (optionally scoped to one table / entity)."""
    if learning_db_path is None or not Path(learning_db_path).exists():
        return {}
    with LearningStore(learning_db_path) as s:
        return s.reset(table or None, legal_entity_id or None)
