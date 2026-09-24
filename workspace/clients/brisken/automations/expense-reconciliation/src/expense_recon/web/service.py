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

import copy
import hashlib
import json
import os
import re
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from typing import NamedTuple
from decimal import Decimal
from pathlib import Path

from .. import inspect as stmt_inspect
from ..batch_period import (
    batch_period,
    month_from_dates,
    month_from_label,
    outside_period,
)
from ..cli import NON_RECEIPT_LABELS, ConfigError, generate_expenses, reconcile
from ..cli import (  # item 105
    INVOICE_READ_AS_STATEMENT_NOTE,
    keep_invoice_read_as_statement,
)
from ..coa_provision import apply_to_config as apply_coa_provisioning
from ..coa_provision import GL_ENTITY_ORGS_KEY, entity_from_settings
from ..correspondence import quarantine_correspondence
from ..error_codes import Refusal, code_of, detail_of, fields_of
from ..duplicates import (
    STATE_OPEN,
    copies_to_collapse,
    decide_receipt_groups,
    duplicate_row_flags,
    find_duplicate_receipt_groups,
    inherit_card_from_copies,
    n_extra_copies,
    restore_copies_with_their_own_charge,
)
from ..ingest._common import merge_transactions
from ..matching.types import (
    Categorization,
    ClassificationSource,
    EXPENSE_CATEGORIES,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)
from ..learning import (
    CATEGORY_SOURCE_HUMAN,
    CATEGORY_SOURCE_INHERITED,
    ExpenseMemory,
    LearningStore,
    MatchMemory,
    MerchantCategoryLookup,
    learn_confirmed_pairs,
    learn_from_expense_run,
    learn_from_run,
    normalize_vendor,
)
from ..output.reconciled_csv import write_reconciled_csv
from ..output.report_xlsx import write_report
from ..output.single_currency import (
    BASE_CURRENCY,
    convert_rows,
    needs_conversion,
    summary_lines,
)
from ..output.zoho_expense_export import (
    EXPENSE_COLUMNS,
    _UNCATEGORIZED,
    build_expense_row_groups,
    expense_posting_parts,
    gated_for_posting,
    resolve_paid_through,
    write_zoho_expense_export,
)
from ..output.zoho_export import write_zoho_export
from ..cost_centers import COST_CENTER_SCOPE_NOTE
from ..cost_centers import (
    UNRESOLVED_SILENT as UNRESOLVED_COST_CENTER,
)
from ..cost_centers import CostCenterRegistry, CostCenterResolution
from ..category_vocabulary import gl_account_options, gl_revision
from ..merchant_registry import (
    MerchantRegistry,
    drop_unvouched_remembered_cards,
    normalize_merchants_setting,
)
# Note item M1: the registry's bare provenance sentence (a line whose
# account came from a company's rule says more) and the seed marker the
# Memory page flags a Zoho-history row with.
from ..categorize import REGISTRY_DEFAULT_REASONING
from ..learning.consult import ZOHO_SEED_PREFIX
from .month_health import (
    HEALTH_OK,
    card_scoping_on,
    month_health,
    unchecked as unchecked_month_health,
)
from .month_readiness import completeness_counts, is_month_complete
# Note item T3: which upload printed a charge, and where. Defined in its
# own module because `store.py` reads the same record and must not import
# the service layer.
from .statement_origin import (
    STATEMENT_ORIGINS_KEY,
    origin_fields,
    origins_from_snapshot,
    upload_origins,
)
from .serialize import (
    categorization_from_dict,
    categorization_to_dict,
    outcome_to_dict,
    receipt_from_dict,
    receipt_to_dict,
    snapshot_from_dict,
    snapshot_to_dict,
    transaction_from_dict,
)
from .store import (
    DISPOSITION_BUSINESS,
    DISPOSITION_REIMBURSABLE,
    INTAKE_RECEIVED,
    STATUS_ALREADY_POSTED,
    STATUS_CONFIRMED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Decision,
    IntakeRow,
    RunRow,
    RunStore,
    TripRow,
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
    # WS3: the per-row card column. `guess_column_map` claims it from tight
    # header patterns; this is the escape hatch for a statement that spells
    # the column some other way, where the alternative is silently losing
    # card scoping with no way to fix it from either front end.
    "card",
)
REQUIRED_STATEMENT_FIELDS = ("transaction_date", "amount", "vendor")

# Reading a receipt is a different call from categorizing a line of text, and
# it is the one that was failing. Measured 2026-08-24 on the April batch's
# problem receipts: gpt-4o-mini reads 3 of 6 dates and 2 of 5 cards; gpt-5-mini
# reads 5 of 6 and 4 of 5, and where it cannot read a date it returns null
# rather than a confident wrong one. Categorization stays on gpt-4o-mini.
VISION_MODEL = os.environ.get("EXPENSE_RECON_VISION_MODEL", "gpt-5-mini")


class RunInputError(Exception):
    """A user-fixable problem with the uploaded files or form values.

    `headers` and `partial_map` are populated when the statement column
    map could not be fully auto-detected, so the form can re-prompt with
    the file's real headers and whatever was guessed.

    `code` names the CONDITION (item 130), stable across rewordings, and
    the keyword arguments are the named values the sentence used, so the
    front end builds its own sentence from data instead of translating
    English with numbers baked in. `message` is unchanged and stays the
    body's `error`.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "invalid_input",
        headers: list[str] | None = None,
        partial_map: dict[str, str] | None = None,
        **fields: object,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.fields = dict(fields)
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
    # Which provisioned card preset this upload was made against, when the
    # SPA sent one. Recorded per statement (PR 2b-2b-2) so a month can tell
    # that two uploads are the SAME card, which is what makes an account-id
    # change between them worth saying out loud. Defaulted: every existing
    # construction site predates it and means "no card preset".
    card_key: str = ""

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


def _unique_upload_name(work_dir: Path, name: str) -> str:
    """`name`, or the first `stem-N.suffix` that is free in `work_dir`.

    Statement uploads land directly in the run's work dir (receipts go to
    subfolders), so the only thing a statement can collide with is another
    statement — which stopped being impossible when the month began taking
    several. Criss's per-card exports carry the bank's own filename, so two
    cards genuinely arrive as the same `statement.xlsx`.

    Overwriting is the dangerous outcome, not the confusing one: the first
    upload's charges keep their `source_row`, the bytes underneath them are
    replaced, and the sheet writeback then annotates the second file's rows
    with the first file's accounts. The first free suffix is returned instead,
    so a fresh batch (nothing to collide with) keeps the exact name it always
    had and the one-shot path is unchanged.
    """
    if not (work_dir / name).exists():
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    n = 2
    while (work_dir / f"{stem}-{n}{suffix}").exists():
        n += 1
    return f"{stem}-{n}{suffix}"


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
    settings: dict | None = None,
) -> PreparedRun:
    """Save the uploads and resolve everything the pipeline needs, fast and
    fail-fast. Raises `RunInputError` for a user-fixable problem (an
    unmappable statement). No pipeline run and no DB row yet.

    `settings` (2026-07-22) is the stored master data (`store.get_settings`):
    the month's FX reference rates, the card -> legal-entity map, and the
    card -> Zoho bank-account map. Omitted / empty => byte-for-byte the
    prior behaviour, so the CLI and the tests are unaffected.

    The uploaded statement + receipts are written into
    `data_root/runs/<run_id>/`, and a self-contained no-API-key
    `run.local.json` is written beside them so the run dir can be pulled off
    the volume and reconciled locally with no OpenAI call (the local test
    loop). Every run-creation path (`POST /runs`, the SPA `POST /api/runs`,
    and the intake run-from-queue) funnels through here, so uploads from the
    Lovable UI are persisted and locally reproducible the same way.

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
            "Upload the report PDF, or pick a CSV source.",
            code="receipts_source_needs_pdf",
            suffix=rcpt_path.suffix or "",
        )

    # 2026-07-21: the LLM path is the default for a hosted run (the OpenAI key
    # is set on the server, and the whole point of the tool is the AI read).
    # `EXPENSE_RECON_DEFAULT_LLM=0` opts a deployment back out. An explicit
    # form checkbox still forces it on. When no key is present the run silently
    # falls back to the deterministic keyword path; the "AI unavailable" notice
    # stays tied to an EXPLICIT request (checkbox on, no key), so a default run
    # in a keyless env is deterministic without a misleading banner.
    have_key = bool(os.environ.get("OPENAI_API_KEY"))
    want_llm = form.use_llm or _default_llm_on()
    ai_unavailable = form.use_llm and not have_key
    use_llm_effective = want_llm and have_key

    # 2026-07-21 owner decision: for a hosted run the tool's own category +
    # account are authoritative over the Zoho report's (see
    # categorization.override_er_category). Only meaningful when the LLM
    # actually picks accounts; a no-op on the keyword path. Auditable /
    # reversible via EXPENSE_RECON_OVERRIDE_ER_CATEGORY=0.
    cfg = _build_config(
        stmt_name, rcpt_name, column_map, form,
        use_llm=use_llm_effective,
        override_er_category=use_llm_effective and _override_er_category_on(),
    )
    # Phase-5 COA gate on the hosted surface: inject a per-entity
    # `coa_validation` block from the /data provisioning file (env
    # EXPENSE_RECON_COA_PROVISION) keyed on the run's legal entity, so the
    # export is validated against the paying entity's chart. Env unset /
    # entity not provisioned => cfg unchanged (fail-open). See coa_provision.
    # Master data (2026-07-22): the month's FX reference rates, the card ->
    # legal-entity map, and the card -> Zoho bank-account map, all from the
    # stored settings. Without these a hosted run had no reference rate (so
    # every cross-currency receipt fell through to LLM judgment: the real
    # April run matched 0 of 94 where the same files matched 29/36 locally
    # with a rate file), resolved no COA entity, and credited a placeholder
    # card account. Written into the run config, so `run.local.json` carries
    # them too and a pulled-down run reproduces the hosted match.
    cfg = apply_master_data(cfg, form, settings)
    entity = resolve_entity(form, settings)
    # Phase 5: the settings entity registry (definable in the UI) wins over
    # the /data provisioning file; empty registry => file behaviour intact.
    cfg = apply_coa_provisioning(cfg, entity, settings=settings)

    # Local-repro config: write a self-contained `run.local.json` next to the
    # uploaded files so pulling this run dir off the /data volume (flyctl
    # sftp) is a one-command, no-API-key local reconciliation. The `llm:` and
    # `coa_validation:` blocks are stripped: the first so a local run never
    # calls (and never pays for) the OpenAI API even when a key is present in
    # the dev env, the second because its chart paths point at /data files a
    # local machine does not have. The remaining statement/receipts/output
    # blocks carry relative paths that resolve against this dir on the volume
    # AND after a local pull. See project_brisken_expense_recon_testing_loop.
    _write_local_run_config(work_dir, cfg)

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


def available_entities(settings: dict | None, extra: str | None = None) -> list[str]:
    """The legal entities a reviewer can pick, deduped and in the operator's
    own order.

    Unions four sources so the picker is never empty: the CoA provisioning
    file (authoritative, `/data`), the card registry's entity TARGETS (the
    composed `cards.effective_cards`, which folds the legacy `card_entities`
    map in), the Phase-5 `settings['entities']` registry, and an optional
    run default. The provisioning + card sources are what populate the
    dropdown in the real Brisken case, where `settings['entities']` is
    empty but the entities do exist on `/data` and in the card map.

    Order (item 92): the names `settings['entity_order']` lists, in that
    order, then everything it does not name, alphabetically. A-Z was
    nobody's order; the entity Criss books every day sat wherever its
    initial put it, in the Settings list and in every per-expense dropdown,
    with no way to move it. Two properties make the ordering safe to read
    anywhere: a name the order no longer matches is ignored, and an entity
    the order never names still appears (at the back), so this list can
    neither hide an entity a charge needs nor go stale into a wrong answer.
    """
    from ..cards import effective_cards
    from ..coa_provision import provisioned_entity_labels

    s = settings or {}
    opts: set[str] = set(provisioned_entity_labels())
    opts |= {str(k).strip() for k in (s.get("entities") or {}) if str(k).strip()}
    opts |= {
        card.entity for card in effective_cards(s).values() if card.entity
    }
    if extra and extra.strip():
        opts.add(extra.strip())
    order = s.get("entity_order") or []
    ranked: list[str] = []
    for name in order:
        label = str(name).strip()
        if label in opts and label not in ranked:
            ranked.append(label)
    return ranked + sorted(opts - set(ranked))


def resolve_entity(form: RunForm, settings: dict | None) -> str:
    """The run's legal entity: the settings `card_entities` map first, then
    the form's own account -> entity mapping.

    `RunForm.resolve_legal_entity` falls back to the raw account id when no
    mapping exists, which is what silently disabled the COA gate on every
    hosted run: an operator types the card number ("2838"), which matches no
    entity key in the COA provisioning ("Corporate Services"), so the run
    came back `has_coa: false` with no warning. The card registry is the
    home for that association (composed via `cards.effective_cards`, which
    folds the legacy `card_entities` map in). Matching (`cards.resolve_card`)
    is on the card number as a digit token anywhere in the label, so
    "2838", "card-2838", and "2838 - May 2026" all resolve the same way;
    the 2026-08-06 card-first Chase label case stays covered.
    """
    from ..cards import effective_cards, entity_for

    account_id = (form.account_id or "").strip()
    if account_id:
        # The composed card registry (settings `cards` first, legacy
        # `card_entities` folded in at read time) is the association's home
        # since 2026-08-21; resolution semantics match the old
        # `_card_key_matches` loop (digit-token first, first match wins).
        resolved = entity_for(account_id, effective_cards(settings))
        if resolved:
            return resolved
    return form.resolve_legal_entity()


def apply_master_data(
    cfg: dict, form: RunForm, settings: dict | None
) -> dict:
    """Return `cfg` with the stored master data folded in: the card's Zoho
    bank account as the `zoho.card_accounts` entry the journal's balancing
    credit resolves against.

    It used to fold in the month's typed FX reference rates as well. The
    owner retired that on 2026-09-23 ("no more typing them in settings"), so
    a month's rates now come from the daily OpenTickers poll
    (`apply_fx_daily_rates`, refreshed on every re-match) and the ECB
    monthly average (`apply_ecb_rates`, fetched at creation and attach).
    Empty settings => `cfg` unchanged.
    """
    from ..cards import effective_cards, zoho_account_for

    settings = settings or {}
    # Card -> Zoho account resolution reads the composed card registry
    # (settings `cards` + legacy `card_accounts`, `cards.effective_cards`)
    # since 2026-08-21; same digit-token matching as before.
    cards = effective_cards(settings)
    have_accounts = any(c.zoho_account for c in cards.values() if c.active)
    if not have_accounts:
        return cfg

    out = dict(cfg)
    account_id = (form.account_id or "").strip()
    if have_accounts and account_id:
        resolved = zoho_account_for(account_id, cards)
        if resolved:
            zoho = dict(out.get("zoho") or {})
            card_accounts = dict(zoho.get("card_accounts") or {})
            card_accounts.setdefault(account_id, resolved)
            zoho["card_accounts"] = card_accounts
            # A zoho block with no coa_source defaults to a live API chart
            # pull, which demands ZOHO_* credentials the hosted environment
            # does not have (2026-07-24: every upload died on it). This block
            # exists only to carry card_accounts; the hosted categorizer
            # chart comes from the coa_validation fallback.
            zoho.setdefault("coa_source", "none")
            out["zoho"] = zoho
    return out


def parse_issue_severity(issue: "tuple") -> str:
    """The severity of one parse issue, tolerant of the pre-2026-07-22
    3-tuple (which reads as "error", its behaviour at the time)."""
    return (issue[3] if len(issue) > 3 else "error") or "error"


def count_parse_issues(issues: "list[tuple]") -> dict[str, int]:
    """Split parse issues into real errors vs advisory notes.

    The workbench used to call every issue an error. On the real April run
    that read "6 parse errors" where one was the parser correctly inferring
    the Chase sign convention and five were receipt images that carried no
    matching expense row: nothing there was an error in the user's sense,
    and a count that cries wolf gets ignored.
    """
    errors = sum(1 for i in issues if parse_issue_severity(i) == "error")
    return {"errors": errors, "notes": len(issues) - errors}


# Near-miss thresholds (2026-07-22). A charge only carries the "near miss"
# hint when a free receipt is within this much of its amount and this many
# days of its date. Both are deliberately wider than the matcher's own
# probable bands (0.20 / 5 days) — the point is to show the pair the matcher
# just barely rejected — but narrow enough that a receiptless subscription
# charge no longer points at an unrelated receipt.
_NEAR_MISS_AMOUNT_PCT = Decimal("0.35")
_NEAR_MISS_DATE_DAYS = 10

LOCAL_RUN_CONFIG_NAME = "run.local.json"
# Config blocks stripped from the local-repro config: `llm` (never call the
# paid API from a local test run) and `coa_validation` (its chart paths live
# on /data, absent locally). Everything else the CLI needs to reconcile
# deterministically is kept.
_LOCAL_CONFIG_STRIP = ("llm", "coa_validation")


def _write_local_run_config(work_dir: Path, cfg: dict) -> None:
    """Write a self-contained, no-API-key copy of the run config into the run
    dir as `run.local.json`, so `expense-recon --config run.local.json` (or
    `python -m expense_recon.cli --config .../run.local.json`) reproduces the
    reconciliation locally against the same uploaded files, with no OpenAI
    call. Best-effort: a write failure never blocks the run."""
    local = {k: v for k, v in cfg.items() if k not in _LOCAL_CONFIG_STRIP}
    try:
        (work_dir / LOCAL_RUN_CONFIG_NAME).write_text(
            json.dumps(local, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # provenance still lives in the DB; a missing file is not fatal


def _setup_advisories(
    cfg: dict,
    transactions: list,
    receipts: list,
    *,
    has_coa: bool,
) -> list[dict]:
    """Actionable notices about master data this run needed and did not have.

    Each entry is `{setting, message}`: the settings key to fix and one
    plain sentence naming what its absence cost THIS run. Silence used to
    be the failure mode — the real April run reported 0 matches and
    `has_coa: false` with nothing on screen tying either to a missing
    setting, so the tool looked broken rather than unconfigured.
    """
    out: list[dict] = []

    # Cross-currency receipts with no reference rate for their pair: the
    # single cause of the 0-of-94 April run.
    configured: set[str] = set()
    card_ccy = (
        transactions[0].account_card_currency if transactions else "USD"
    ).upper()
    # Item 82: a currency the month's ECB table can cross into the card
    # currency needs nothing typed. Rates come from the ECB now, so the
    # advisory speaks only when neither source has one.
    ecb_table = (cfg.get("matching") or {}).get("fx_ecb_monthly_rates") or {}
    ecb_ccys = {"EUR"} | {
        str(c).upper() for per_eur in ecb_table.values() for c in (per_eur or {})
    }
    if ecb_table and card_ccy in ecb_ccys:
        configured |= ecb_ccys
    # Note #79: likewise a currency the polled daily table covers.
    daily_table = (cfg.get("matching") or {}).get("fx_daily_rates") or {}
    daily_ccys = {"EUR"} | {
        str(c).upper() for per_eur in daily_table.values() for c in (per_eur or {})
    }
    if daily_table and card_ccy in daily_ccys:
        configured |= daily_ccys
    missing: dict[str, int] = {}
    for r in receipts:
        ccy = (r.detected_currency or "").upper()
        if ccy and ccy != card_ccy and ccy not in configured:
            missing[ccy] = missing.get(ccy, 0) + 1
    for ccy, count in sorted(missing.items(), key=lambda kv: -kv[1]):
        out.append({
            "setting": "fx_reference_rates",
            "code": "fx_rate_missing",
            "currency": ccy,
            "card_currency": card_ccy,
            "n_receipts": count,
            "message": (
                f"{count} receipt(s) are in {ccy} but no {ccy}:{card_ccy} "
                f"reference rate is available (no daily rate has been polled "
                f"for it and the ECB publishes no monthly average for this "
                f"month), so they cannot match deterministically."
            ),
        })

    if not has_coa:
        out.append({
            "setting": "cards",
            "code": "no_chart_of_accounts",
            "message": (
                "No chart of accounts was resolved for this run, so posting "
                "accounts are not validated and the journal exports "
                "placeholder accounts. Map this card to its legal entity in "
                "Settings > Cards."
            ),
        })

    # Per-card and Zoho-optional (Cards R2, 2026-08-21, feedback notes
    # 9/11): name the actual card, say the account is optional, and say
    # what the gap costs. The old advisory fired only on an EMPTY map and
    # called the account required ("This card has no bank account"),
    # which is the wording the owner pushed back on.
    acct = ""
    stmt = cfg.get("statement")
    if isinstance(stmt, dict):
        acct = str(stmt.get("account_id") or "").strip()
    if not acct and transactions:
        acct = str(transactions[0].account_id or "").strip()
    mapped = (cfg.get("zoho") or {}).get("card_accounts") or {}
    # The exact resolver the journal export applies (Cards R2:
    # `resolve_account_map`, exact + bare-digit-unique), so the advisory
    # is silent precisely when the export resolves and fires precisely
    # when it placeholders.
    from ..cards import resolve_account_map

    resolvable = bool(resolve_account_map(acct, dict(mapped)))
    if acct and not resolvable:
        out.append({
            "setting": "cards",
            "code": "card_posting_account_missing",
            "card": acct,
            "message": (
                f"Card '{acct}' has no posting account set "
                "(optional: only the data export uses it). Export "
                "entries balance to a visible 'Card: ...' placeholder until "
                "one is set in Settings > Cards."
            ),
        })
    return out


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
    return Refusal(
        f"{foreign} of {len(receipts)} receipts are foreign-currency but the "
        f"statement is {Path(stmt_name).suffix or 'tabular'} — the Chase "
        f"statement PDF carries each charge's original foreign amount, which "
        f"lets these match deterministically. Prefer uploading the statement "
        f"PDF for this month.",
        code="statement_not_pdf",
        n_foreign=foreign,
        n_receipts=len(receipts),
        suffix=Path(stmt_name).suffix or "",
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
        raise RunInputError(
            str(exc), code="pipeline_config_invalid"
        ) from exc

    outcome = result.outcome
    # Item 103: the same effective derivation the re-match commit and the
    # months list use, so one name means one thing on every screen. A fresh
    # run has no verdicts yet, and the difference is still real: a charge
    # whose only receipt a tie on another charge holds is unmatched on the
    # page from the first render.
    committed = effective_charge_counts(
        result.transactions, outcome, result.receipts, {}
    )
    n_review = committed["n_review"]
    n_tx = len(result.transactions)
    summary = {
        "n_transactions": n_tx,
        "n_receipts": len(result.receipts),
        "n_matched": committed["n_matched"],
        "n_review": n_review,
        "n_unmatched_tx": committed["n_unmatched_tx"],
        "n_refunds": committed["n_refunds"],
        "n_unmatched_rec": len(outcome.unmatched_receipts),
        "n_parse_errors": count_parse_issues(result.parse_errors)["errors"],
        "n_parse_notes": count_parse_issues(result.parse_errors)["notes"],
        # `match_rate` divides matched charges by ALL charges, which reads
        # low on a month where most charges never had a receipt (57 of 94 in
        # April 2026) and made the tool look broken when it placed 34/37
        # receipts. `receipt_match_rate` is the honest denominator: receipts
        # placed on a charge over receipts that exist. Both are exposed; the
        # SPA leads with the receipt rate. (2026-07-27)
        "match_rate": round(committed["n_matched"] / n_tx * 100, 1) if n_tx else 0.0,
        "n_receipts_matched": max(
            len(result.receipts) - len(outcome.unmatched_receipts), 0
        ),
        "receipt_match_rate": (
            round(
                (len(result.receipts) - len(outcome.unmatched_receipts))
                / len(result.receipts) * 100, 1
            )
            if result.receipts else 0.0
        ),
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
        # Item 130: the same advisory as a code plus its numbers, so the
        # screen can say it in the reviewer's language. Parallel field.
        summary["statement_advisory_detail"] = detail_of(advisory)
    # 2026-07-22: master data that is MISSING now says so. Absent settings
    # used to fail silently — the April run came back 0-matched and
    # has_coa:false with nothing on screen explaining that no FX reference
    # rate and no entity mapping existed. Each advisory names the setting
    # and what it cost this run, so the fix is one click away.
    summary["setup_advisories"] = _setup_advisories(
        prepared.cfg,
        result.transactions,
        result.receipts,
        has_coa=result.chart_of_accounts is not None,
    )
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
    # §16: snapshot the live export policy into the run config so the run
    # reproduces under the policy that was in effect when it ran, not
    # whatever the setting later becomes. Absent/False => current behaviour.
    settings = store.get_settings()
    cfg = {
        **prepared.cfg,
        "policy": {
            "export_approved_only": bool(settings.get("export_approved_only")),
        },
    }
    store.create_run(
        run_id=prepared.run_id,
        created_at=prepared.now_iso,
        label=label,
        operator=prepared.operator,
        summary=summary,
        snapshot=snapshot,
        config=cfg,
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
        raise RunInputError(
            "No statement file uploaded.", code="no_statement_file"
        )
    stmt_name = _safe_name(statement_filename or "", "statement.csv")
    if Path(stmt_name).suffix.lower() not in _STATEMENT_SUFFIXES:
        raise RunInputError(
            "The statement file should be a .csv, .xlsx or .pdf export from "
            "the bank.",
            code="unsupported_statement_file",
            suffix=Path(stmt_name).suffix or "",
        )
    rcpt_name: str | None = None
    if receipts_bytes:
        rcpt_name = _safe_name(receipts_filename or "", "receipts.csv")
        if Path(rcpt_name).suffix.lower() not in _RECEIPTS_SUFFIXES:
            raise RunInputError(
                "The receipts file should be a .csv export or a Zoho Expense "
                "report .pdf.",
                code="unsupported_receipts_file",
            )
    if not label.strip():
        raise RunInputError(
            "Please pick which card this statement is from.",
            code="card_required",
        )

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
            "longer be swapped. Send a new upload instead.",
            code="intake_already_processing",
        )
    if not statement_bytes and not receipts_bytes:
        raise RunInputError(
            "Pick at least one file to replace.", code="no_replacement_file"
        )

    work_dir = Path(intake.work_dir)
    new_stmt_name: str | None = None
    new_rcpt_name: str | None = None
    detect_note: str | None = None

    if statement_bytes:
        new_stmt_name = _safe_name(statement_filename or "", "statement.csv")
        if Path(new_stmt_name).suffix.lower() not in _STATEMENT_SUFFIXES:
            raise RunInputError(
                "The statement file should be a .csv, .xlsx or .pdf export "
                "from the bank.",
                code="unsupported_statement_file",
                suffix=Path(new_stmt_name).suffix or "",
            )
    if receipts_bytes:
        new_rcpt_name = _safe_name(receipts_filename or "", "receipts.csv")
        if Path(new_rcpt_name).suffix.lower() not in _RECEIPTS_SUFFIXES:
            raise RunInputError(
                "The receipts file should be a .csv export or a Zoho Expense "
                "report .pdf.",
                code="unsupported_receipts_file",
            )

    # Validation passed for everything requested; now touch the disk.
    # Item 66: archive every file this call is about to destroy BEFORE writing
    # anything. Pre-fix a swap wrote the new bytes over the old ones when the
    # name matched and unlinked the old file when it did not, so either way
    # the superseded upload left the volume with no copy and no record. The
    # replaced file now survives the replacement; it is moved aside, never
    # deleted, so it is still there when the batch commits and afterwards.
    archive_dir = work_dir / "superseded"
    doomed: list[str] = []
    if new_stmt_name is not None:
        doomed += [n for n in (intake.statement_name, new_stmt_name) if n]
    if new_rcpt_name is not None:
        doomed += [n for n in (intake.receipts_name, new_rcpt_name) if n]
    for name in dict.fromkeys(doomed):
        prior = work_dir / name
        if prior.is_file():
            _archive_superseded_file(prior, archive_dir, now_iso)
    if new_stmt_name is not None:
        (work_dir / new_stmt_name).write_bytes(statement_bytes)
        detect_note = _detect_note(work_dir / new_stmt_name)
    if new_rcpt_name is not None:
        (work_dir / new_rcpt_name).write_bytes(receipts_bytes)

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
    settings: dict | None = None,
) -> PreparedRun:
    """Prepare a pipeline run from a stored intake's files (the operator's
    run-from-queue path). Reads the uploaded bytes back from the intake's
    work dir and delegates to `prepare_run`, tagging the run with the
    intake id so publish can flip the intake to `ready`."""
    intake_dir = Path(intake.work_dir)
    statement_bytes = (intake_dir / intake.statement_name).read_bytes()
    if intake.receipts_name is None:
        raise RunInputError(
            "This upload has no receipts file yet; ask for it before running.",
            code="intake_missing_receipts",
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
        settings=settings,
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
        raise RunInputError(
            str(exc), code="statement_unreadable"
        ) from exc

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
            code="statement_columns_missing",
            headers=headers,
            partial_map=column_map,
            missing=list(missing),
        )
    return column_map


def _default_llm_on() -> bool:
    """The hosted run uses the LLM by default (a key is set on the server).
    `EXPENSE_RECON_DEFAULT_LLM=0` opts a deployment out."""
    return os.environ.get("EXPENSE_RECON_DEFAULT_LLM", "1") != "0"


def _override_er_category_on() -> bool:
    """The tool's own category + account win over the Zoho report's by default
    on the hosted surface (2026-07-21 owner decision).
    `EXPENSE_RECON_OVERRIDE_ER_CATEGORY=0` restores the report-authoritative
    behaviour."""
    return os.environ.get("EXPENSE_RECON_OVERRIDE_ER_CATEGORY", "1") != "0"


def _vision_receipts_on() -> bool:
    """WS2: read the report PDF's receipt IMAGES with vision by default on the
    hosted surface (the fix for the ~half of ER summary rows that carry no
    printed merchant). Only fires for the `expense_report_pdf` receipts source
    and with the LLM effective; a no-op elsewhere.
    `EXPENSE_RECON_VISION_RECEIPTS=0` opts a deployment out (e.g. to cap
    per-run vision cost)."""
    return os.environ.get("EXPENSE_RECON_VISION_RECEIPTS", "1") != "0"


def _build_config(
    stmt_name: str,
    rcpt_name: str,
    column_map: dict[str, str],
    form: RunForm,
    *,
    use_llm: bool,
    override_er_category: bool = False,
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
        cfg["llm"] = {"provider": "openai", "model": "gpt-4o-mini", "vision_model": VISION_MODEL}
    # WS2: the tool's own category can override the report's (heavy mismatch),
    # and vision reads the report PDF's receipt images. Both need the LLM;
    # vision additionally only fires for the report-PDF receipts source (gated
    # in cli._apply_vision_receipts), so setting it for a CSV upload is a no-op.
    categorization: dict = {}
    if override_er_category:
        categorization["override_er_category"] = True
    if use_llm and _vision_receipts_on():
        categorization["vision_receipts"] = True
    if categorization:
        cfg["categorization"] = categorization
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
                            # Item 70: the line's own account only survives
                            # an override that keeps its category.
                            zoho_account=ov.get("zoho_account")
                            or override_base_account(ov["category"], base),
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


def categorized_counts(receipts: list[Receipt]) -> tuple[int, int]:
    """`(categorized, uncategorized)` for an expense pool under ONE rule,
    used by every screen: an expense is categorized when every line item on
    it carries a category. An expense with no line items at all is not
    categorized (it exports as `(uncategorized - assign)`).

    The rule answers exactly one question — "how many expenses still need
    someone to pick a category" — and nothing else. It deliberately ignores
    whether the row is otherwise ready to export (entity, currency, a
    vendor guess worth a look); those are their own counts. Pass receipts
    with the reviewer's category overrides already applied
    (`apply_overrides`), or an edit will not move the number.

    Was open-coded at five sites with two different meanings; the batch
    page counted `review == "ready"` and so reported 30 categorized-but-
    entity-less rows as uncategorized while the list screen counted the
    same batch honestly (operator note, 2026-08-22).
    """
    n = sum(1 for r in receipts if is_categorized(r))
    return n, len(receipts) - n


def is_categorized(receipt: Receipt) -> bool:
    """`categorized_counts`' rule for ONE expense (item 84: the Categorized
    box lists exactly the rows its count counts). Every line carries a
    category; a row whose first line is categorized and whose second is not
    shows a category and is still uncategorized."""
    return bool(receipt.line_items) and all(
        li.categorization and li.categorization.category
        for li in receipt.line_items
    )


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
            "already posted in the books (reviewer)"
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

    Item 101: this is the raw set, and no longer what the button confirms.
    `confirm_matched_pairs` narrows it to the owner's pairing rule.
    """
    _, _, outcome, _ = snapshot_from_dict(run.snapshot)
    return autopick_pairs(outcome, decisions)


def autopick_pairs(
    outcome: MatchOutcome, decisions: dict[str, Decision]
) -> list[tuple[str, str]]:
    """`matched_autopick_decisions` over an outcome the caller already read
    (`build_view` has one), so the count and the route read one rule."""
    matched_doc_by_tx = {m.transaction_id: m.document_id for m in outcome.matches}
    out: list[tuple[str, str]] = []
    for tx_id, doc_id in matched_doc_by_tx.items():
        decision = decisions.get(tx_id)
        if decision is not None and decision.status != STATUS_PENDING:
            continue
        out.append((tx_id, doc_id))
    return out


def bulk_decisions(
    run: RunRow,
    decisions: dict[str, Decision],
    transaction_ids: "list[str]",
    status: str,
) -> list[tuple[str, str | None]]:
    """The (transaction_id, document_id) writes for a bulk confirm / reject.

    Confirming takes each charge's own top candidate, exactly as confirming
    that row by hand would; rejecting clears the document. A charge with no
    candidate cannot be confirmed and is skipped, so a bulk action can never
    invent a pairing. Ids already acted on are skipped, mirroring
    `matched_autopick_decisions` — a bulk click never stomps an explicit
    earlier verdict.

    Added 2026-07-22: the review bucket was 34 rows on the real April run
    with no way to clear them except one at a time.

    Item 101: a charge booked in the workbook (yellow, `turn: posted`) is
    never confirmed either; a booked row never offers Confirm, so a bulk
    click must not confirm it. Rejecting is unchanged.
    """
    transactions, _, outcome, _ = snapshot_from_dict(run.snapshot)
    booked = {t.transaction_id for t in transactions if t.entry_status == "posted"}
    top_doc: dict[str, str] = {}
    for bucket in (outcome.matches, outcome.judgment_required, outcome.ambiguous):
        for m in bucket:
            best = top_doc.get(m.transaction_id)
            if best is None:
                top_doc[m.transaction_id] = m.document_id
    wanted = list(dict.fromkeys(transaction_ids))  # de-dup, keep order
    out: list[tuple[str, str | None]] = []
    for tx_id in wanted:
        decision = decisions.get(tx_id)
        if decision is not None and decision.status != STATUS_PENDING:
            continue
        if status == STATUS_CONFIRMED:
            if tx_id in booked:
                continue  # already booked: nothing to confirm (item 101)
            doc_id = top_doc.get(tx_id)
            if not doc_id:
                continue  # nothing to confirm against; never fabricate a pair
            out.append((tx_id, doc_id))
        else:
            out.append((tx_id, None))
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
        return Refusal(
            "Unknown transaction for this run.", code="transaction_not_found"
        )
    rec = next((r for r in receipts if r.document_id == document_id), None)
    if rec is None:
        return Refusal(
            "Unknown receipt for this run.", code="receipt_not_found"
        )
    # The matcher's own rule since 2026-09-11: an EMPTY entity on either
    # side is unscoped (a mailed receipt before its card is known, a charge
    # on a card the registry cannot name, item 59); only two NAMED entities
    # that differ refuse.
    if (
        rec.legal_entity_id
        and tx.legal_entity_id
        and rec.legal_entity_id != tx.legal_entity_id
    ):
        return Refusal(
            "Receipt and charge belong to different legal entities.",
            code="entity_differs",
        )
    return None


MANUAL_RECEIPT_MAX_BYTES = 15 * 1024 * 1024
MANUAL_RECEIPT_SUFFIXES = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
)


# --------------------------------------------------------------------------
# Stored-file retention (backlog item 66)
# --------------------------------------------------------------------------
# Two paths used to destroy bytes this system had already accepted: replacing
# a file on a queued upload deleted the file it replaced, and re-attaching a
# receipt to the same charge under the same name wrote straight over it.
# Neither kept a prior version and neither left a record, in a system whose
# whole purpose is retaining what arrived
# (docs/electronic-storage-system-description.md section 12, rows 3 and 14).
# Nothing here deletes: a superseded file is moved aside under a versioned
# name and stays on the volume.


def _archive_superseded_file(path: Path, archive_dir: Path, now_iso: str) -> str:
    """Move `path` into `archive_dir` under a versioned name; return that
    name. The rename keeps the bytes on the same volume and takes them out of
    every glob the live resolvers use, so an archived copy can never be served
    in place of the current one."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = re.sub(r"[^0-9]", "", now_iso or "")[:14] or "00000000000000"
    target = archive_dir / f"{stamp}__{path.name}"
    n = 1
    while target.exists():
        n += 1
        target = archive_dir / f"{stamp}-{n}__{path.name}"
    path.replace(target)
    return target.name


def _store_manual_receipt(
    dest_dir: Path,
    fs_tx: str,
    fs_name: str,
    file_bytes: bytes,
    now_iso: str,
) -> tuple[Path, list[dict]]:
    """Store one hand-attached receipt for a charge without ever writing over
    stored bytes.

    A charge holds exactly ONE current file. Every file it already holds is
    archived first, which closes both halves of the pre-fix defect: a
    re-attach under the SAME name destroyed the earlier bytes in place, and
    one under a DIFFERENT name left two files behind, from which the image
    endpoint and `_attached_receipt_file` both take `sorted(...)[0]` and so
    could serve the superseded version. Re-uploading byte-identical content is
    a no-op. Returns the current path and one record per archived file.
    """
    dest = dest_dir / f"{fs_tx}__{fs_name}"
    existing = sorted(p for p in dest_dir.glob(f"{fs_tx}__*") if p.is_file())
    if [p.name for p in existing] == [dest.name] and dest.read_bytes() == file_bytes:
        return dest, []  # the stored file already IS this upload
    archive_dir = dest_dir / "superseded"
    superseded = [
        {
            "stored": p.name,
            "archived": _archive_superseded_file(p, archive_dir, now_iso),
            "at": now_iso,
        }
        for p in existing
    ]
    dest.write_bytes(file_bytes)
    return dest, superseded


def _record_receipt_file(
    snapshot: dict | None,
    document_id: str,
    stored: str,
    superseded: list[dict],
    now_iso: str,
) -> dict:
    """The snapshot's record of which file backs an attached receipt and what
    that attachment replaced, keyed by document id. `superseded` accumulates,
    so a charge re-attached three times names all three prior versions and the
    archived file each one became. Stored only; neither view payload exposes
    it, because item 66 asks for a record, not an SPA field."""
    files = dict((snapshot or {}).get("receipt_files") or {})
    entry = dict(files.get(document_id) or {})
    files[document_id] = {
        "stored": stored,
        "at": now_iso,
        "superseded": list(entry.get("superseded") or []) + list(superseded),
    }
    return files


def attach_emailed_receipt(
    store,
    run: "RunRow",
    transaction_id: str,
    file_name: str,
    file_bytes: bytes,
    now_iso: str,
) -> tuple[str | None, str | None]:
    """Attach a receipt that arrived OUTSIDE the ER export to one charge.

    Some receipts reach Criss by email instead of Zoho Expense (owner
    directive 2026-07-24), so their charges sit in unmatched with no
    receipt to pair. The uploaded file is stored beside the run's other
    artifacts (`work_dir/manual-receipts/`), read into a Receipt (with
    the run's LLM when configured, a bare filename-only Receipt
    otherwise), appended to the snapshot's receipt pool, and immediately
    paired with the charge as a confirmed decision — the same mechanism
    as a manual match, so review, exports, and memory treat it like any
    other confirmed pair. Re-uploading for the same charge replaces the
    prior attachment. Returns (error, document_id).
    """
    from ..cli import _build_llm_client
    from ..ingest.receipts_folder import parse_receipt_file

    transactions, receipts, outcome, _parse_errors = snapshot_from_dict(
        run.snapshot
    )
    tx = next(
        (t for t in transactions if t.transaction_id == transaction_id), None
    )
    if tx is None:
        return Refusal(
            "Unknown transaction for this run.",
            code="transaction_not_found",
        ), None
    safe_name = Path(file_name or "").name
    suffix = Path(safe_name or "receipt").suffix.lower()
    if suffix not in MANUAL_RECEIPT_SUFFIXES:
        return Refusal(
            f"Unsupported receipt file type {suffix or '(none)'}.",
            code="unsupported_attachment_type",
            suffix=suffix or "",
        ), None
    if not file_bytes:
        return Refusal("Empty file.", code="empty_file"), None
    if len(file_bytes) > MANUAL_RECEIPT_MAX_BYTES:
        return Refusal(
            "File too large (15 MB max).",
            code="file_too_large",
            limit_mb=MANUAL_RECEIPT_MAX_BYTES // (1024 * 1024),
        ), None

    dest_dir = Path(run.work_dir) / "manual-receipts"
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Transaction ids carry slashes/colons (statement row keys); flatten
    # both name parts so the file lands IN manual-receipts, not a subdir.
    fs_tx = re.sub(r"[^A-Za-z0-9._-]", "_", transaction_id)
    fs_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    # Item 66: a re-attach archives whatever this charge already holds under a
    # versioned name instead of writing over it. `superseded` is recorded on
    # the snapshot below, inside the same commit, so the replacement is not
    # only survivable but findable.
    dest, superseded = _store_manual_receipt(
        dest_dir, fs_tx, fs_name, file_bytes, now_iso
    )

    # One manual receipt per charge: a stable id makes re-upload replace.
    document_id = f"manual:{transaction_id}"
    receipt = None
    llm_client, _tracker = _build_llm_client(run.config or {})
    if llm_client is not None:
        try:
            parsed = parse_receipt_file(
                dest,
                legal_entity_id=tx.legal_entity_id,
                client=llm_client,
            )
            receipt = replace(
                parsed, document_id=document_id, receipt_name=safe_name
            )
        except Exception:  # noqa: BLE001 - extraction is best-effort
            receipt = None
    if receipt is None:
        # No LLM (or extraction failed): the file itself is still the
        # evidence. Store a bare receipt; the reviewer sees the filename
        # and the charge's own categorization carries the export.
        receipt = Receipt(
            document_id=document_id,
            legal_entity_id=tx.legal_entity_id,
            detected_date=None,
            detected_total=None,
            detected_currency=None,
            detected_vendor=safe_name,
            receipt_name=safe_name,
        )

    # Commit under the batch writer lock against a FRESH re-read, the shape
    # `rematch_month` already uses (item 66). The read at the top of this
    # function happened before the vision call, which takes seconds; rebuilding
    # the period record from `dict(run.snapshot)` afterwards silently threw
    # away everything another writer had committed in between -- a mailed-in
    # receipt, a card assignment, a re-match -- because the whole record was
    # rewritten from a stale copy, with no lock held and no re-read.
    with _BATCH_ADD_LOCK:  # item 66: manual per-charge attach
        fresh = store.get_run(run.run_id)
        if fresh is None:
            # Deleted while the receipt was being read. Refuse honestly rather
            # than write a snapshot UPDATE that matches zero rows.
            return Refusal(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            ), None
        run = fresh
        fresh_tx, receipts, outcome, _ = snapshot_from_dict(fresh.snapshot)
        if not any(t.transaction_id == transaction_id for t in fresh_tx):
            # A statement re-read retires transaction ids by design. Confirming
            # a decision against a charge the month no longer holds would
            # strand it, so refuse with the sentence the up-front check uses.
            return Refusal(
                "Unknown transaction for this run.",
                code="transaction_not_found",
            ), None
        receipts = [r for r in receipts if r.document_id != document_id]
        receipts.append(receipt)
        if document_id not in outcome.unmatched_receipts:
            outcome.unmatched_receipts.append(document_id)

        # Preserve extra snapshot keys (charge_categorizations, version):
        # revise only the entries this attachment touches.
        new_snapshot = dict(fresh.snapshot)
        new_snapshot["receipts"] = [receipt_to_dict(r) for r in receipts]
        new_snapshot["outcome"] = outcome_to_dict(outcome)
        # Item 70: a re-attach replaces the document with a DIFFERENT file, so
        # the old file's extraction must not stay its baseline: the re-match
        # bakes from the baseline, and would resurrect the superseded read.
        baseline = new_snapshot.get(EXTRACTED_RECEIPTS_KEY)
        if isinstance(baseline, list):
            new_snapshot[EXTRACTED_RECEIPTS_KEY] = [
                d for d in baseline
                if not (isinstance(d, dict) and d.get("document_id") == document_id)
            ]
        if superseded:
            new_snapshot["receipt_files"] = _record_receipt_file(
                fresh.snapshot, document_id, dest.name, superseded, now_iso
            )
        store.update_run_snapshot(run.run_id, new_snapshot)
        store.set_decision(
            run.run_id, transaction_id, STATUS_CONFIRMED, document_id, now_iso
        )
    # R4: a confirmed manual attach settles its receipt -- record the
    # claim. The receipt was just created in this run, so no other run can
    # hold it; the sync is for the registry, not for a conflict.
    sync_claim_for_decision(
        store, run, transaction_id, STATUS_CONFIRMED, document_id, now_iso
    )
    return None, document_id


# --------------------------------------------------------------------------
# Bulk digital-receipt folder attach (2026-07-27)
# --------------------------------------------------------------------------

FOLDER_RECEIPT_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})
FOLDER_RECEIPT_MAX_BYTES = 15 * 1024 * 1024
# The same number the reviewer reads in the rejection sentence, so the
# prose and the machine-readable `limit` cannot disagree.
FOLDER_RECEIPT_MAX_MB = FOLDER_RECEIPT_MAX_BYTES // (1024 * 1024)
# One bulk upload is one operator action on one run. The cap bounds vision
# cost and a zip's blast radius PER INGEST CALL; it is sized for the
# Receipts drop page, whose legitimate load is a multi-month backfill pile,
# not one month's ~20-40 receipts (owner 2026-09-08: 80 was too small).
# The drop router marks anything past the cap `upload-cap` in its ledger
# BEFORE the ingest call, so a truncation is never silent there.
FOLDER_MAX_FILES = 500
# Charges the reviewer has decided; held out of the re-match entirely so a
# folder upload can never disturb confirmed / rejected / already-posted work.
_FOLDER_TERMINAL = frozenset(
    {STATUS_CONFIRMED, STATUS_REJECTED, STATUS_ALREADY_POSTED}
)


# Upload rejections carry a stable CODE beside the English sentence, so the
# SPA can say it in the reviewer's language (backlog item 20). The prose is
# unchanged and `issues` stays `list[str]`: retyping a live list field in
# place is what took the batch page down on 2026-08-22 (see
# docs/api-contract.md). Every detail object carries the same four keys —
# `suffix` and `limit` are null where the code does not use them — so a
# consumer can map over the list without shape checks.
UPLOAD_ISSUE_CAP = "upload_cap"
UPLOAD_ISSUE_UNSUPPORTED = "unsupported_type"
UPLOAD_ISSUE_EMPTY = "empty_or_unreadable"
UPLOAD_ISSUE_TOO_LARGE = "too_large"


def upload_issue(
    code: str, file: str, *, suffix: str | None = None, limit: float | None = None
) -> tuple[str, dict]:
    """`(prose, detail)` for one rejected upload, from ONE place: the English
    sentence and its code are built together, so a reworded message can never
    drift from what the SPA localizes.

    Callers append the prose to `issues` (unchanged contract) and the detail
    to the parallel `issue_details`. `file` is the display name the reviewer
    uploaded, never the spooled path.
    """
    if code == UPLOAD_ISSUE_CAP:
        prose = f"upload cap {int(limit or 0)} reached; {file} and later skipped"
    elif code == UPLOAD_ISSUE_UNSUPPORTED:
        prose = f"{file}: unsupported type {suffix or '(none)'} (skipped)"
    elif code == UPLOAD_ISSUE_EMPTY:
        prose = f"{file}: empty or unreadable (skipped)"
    elif code == UPLOAD_ISSUE_TOO_LARGE:
        prose = f"{file}: too large ({int(limit or 0)} MB max) (skipped)"
    else:  # pragma: no cover - a new code must add its sentence above
        raise ValueError(f"unknown upload issue code: {code!r}")
    return prose, {"code": code, "file": file, "suffix": suffix, "limit": limit}


def _folder_receipt_files(staging_dir: Path):
    """Yield (display_name, data_bytes) for every receipt in a staging dir,
    expanding a `.zip` member-by-member so memory stays bounded to one file at
    a time. A bad zip yields a single empty entry so the caller surfaces it as
    an issue; unsupported members are yielded too and the caller's suffix
    check turns them into a visible issue rather than a silent drop."""
    import zipfile

    for p in sorted(Path(staging_dir).iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(p) as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        name = Path(info.filename).name
                        if not name or name.startswith("."):
                            continue
                        with zf.open(info) as fh:
                            yield name, fh.read(FOLDER_RECEIPT_MAX_BYTES + 1)
            except zipfile.BadZipFile:
                yield p.name, b""
            continue
        yield p.name, p.read_bytes()


def ingest_receipts_folder_into_run(
    store, run: "RunRow", staging_dir: str | Path, now_iso: str, *, on_stage=None,
) -> dict:
    """Bulk sibling of `attach_emailed_receipt`: ingest a FOLDER of receipts
    (Criss has them digitally, not in the Zoho ER export) against an EXISTING
    run and propose pairings for the charges she has NOT decided yet, without
    touching anything she already confirmed / rejected / marked posted.

    Unlike the single-file attach, this does not pre-assign. It re-runs the
    real matcher (`match_month` + the FX judgment layer, reusing the run's own
    `MatchingConfig` so the 0.2 FX suggest floor and card scoping apply) over
    the sub-universe of {charges with no terminal decision} x {new receipts +
    still-unmatched existing receipts}, then splices the result back beside the
    untouched decided work. New receipts that pair land in the review bucket as
    candidates she confirms, exactly like ER receipts; new receipts that do not
    pair land in `unmatched_receipts` (reconciliation guarantee). The reviewer's
    stored decisions are never written here — `apply_decisions` overlays them at
    view time, so confirmed pairs render exactly as before.

    `staging_dir` holds the raw uploaded files (the endpoint spools them there,
    off the request); a `.zip` among them is expanded. Returns a summary dict
    (counts + LLM cost + possible-duplicate count), also persisted onto the
    snapshot as `folder_ingest` so the SPA can show it once the job finishes.
    """
    from ..cli import (
        _apply_ambiguous_judgment,
        _apply_judgment,
        _apply_unmatched_judgment,
        _build_llm_client,
        _load_match_memory,
        build_match_cfg,
    )
    from ..ingest.receipts_folder import parse_receipt_file
    from ..matching.deterministic import MatchingConfig, match_month

    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass

    transactions, receipts, outcome, _parse_errors = snapshot_from_dict(run.snapshot)
    decisions = store.get_decisions(run.run_id)
    work_dir = Path(run.work_dir)
    dest_dir = work_dir / "folder-receipts"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # LLM client for OCR (constraint 5). Prefer the run's own llm block; if the
    # run had none, source the deployment default so a folder still gets read,
    # with the cost made visible below. Without any client every receipt falls
    # to bare-filename, which carries no amount/date and so cannot match — the
    # summary flags `llm_source == "none"` so the operator knows why.
    llm_client, tracker, llm_source = None, None, "none"
    try:
        llm_client, tracker = _build_llm_client(run.config or {})
        if llm_client is not None:
            llm_source = "run"
    except ConfigError:
        llm_client = None
    if llm_client is None and _default_llm_on() and os.environ.get("OPENAI_API_KEY"):
        llm_client, tracker = _build_llm_client(
            {"llm": {"provider": "openai", "model": "gpt-4o-mini", "vision_model": VISION_MODEL}}
        )
        llm_source = "env-default"

    entity = (
        transactions[0].legal_entity_id
        if transactions
        else ((run.config or {}).get("statement") or {}).get("legal_entity_id", "")
    )
    default_ccy = ((run.config or {}).get("receipts") or {}).get("default_currency")

    _stage("ingesting")
    existing_doc_ids = {r.document_id for r in receipts}
    new_receipts: list[Receipt] = []
    seen_hashes: set[str] = set()
    issues: list[str] = []
    issue_details: list[dict] = []

    def _issue(code: str, file: str, **kw) -> None:
        prose, detail = upload_issue(code, file, **kw)
        issues.append(prose)
        issue_details.append(detail)

    n_seen = 0
    for name, data in _folder_receipt_files(staging_dir):
        n_seen += 1
        if n_seen > FOLDER_MAX_FILES:
            _issue(UPLOAD_ISSUE_CAP, name, limit=FOLDER_MAX_FILES)
            break
        safe_name = Path(name or "").name
        suffix = Path(safe_name or "receipt").suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES:
            _issue(UPLOAD_ISSUE_UNSUPPORTED, safe_name, suffix=suffix or None)
            continue
        if not data:
            _issue(UPLOAD_ISSUE_EMPTY, safe_name)
            continue
        if len(data) > FOLDER_RECEIPT_MAX_BYTES:
            _issue(UPLOAD_ISSUE_TOO_LARGE, safe_name, limit=FOLDER_RECEIPT_MAX_MB)
            continue
        digest = hashlib.sha1(data).hexdigest()[:16]
        if digest in seen_hashes:
            continue  # identical bytes twice in one upload
        seen_hashes.add(digest)
        document_id = f"folder:{digest}"
        fs_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
        # Stable, content-addressed name so a re-upload of the same file lands
        # on the same path and the image endpoint can glob it by hash.
        dest = dest_dir / f"{digest}__{fs_name}"
        dest.write_bytes(data)
        if document_id in existing_doc_ids:
            continue  # already in the pool from a prior upload; file refreshed
        receipt = None
        if llm_client is not None:
            try:
                parsed = parse_receipt_file(
                    dest,
                    legal_entity_id=entity,
                    client=llm_client,
                    default_currency=default_ccy,
                )
                receipt = replace(
                    parsed, document_id=document_id, receipt_name=safe_name
                )
            except Exception:  # noqa: BLE001 - extraction is best-effort
                receipt = None
        if receipt is None:
            # No LLM (or extraction failed): the file itself is still evidence.
            receipt = Receipt(
                document_id=document_id,
                legal_entity_id=entity,
                detected_date=None,
                detected_total=None,
                detected_currency=None,
                detected_vendor=safe_name,
                receipt_name=safe_name,
            )
        new_receipts.append(receipt)

    new_ids = {r.document_id for r in new_receipts}
    pool = [r for r in receipts if r.document_id not in new_ids] + new_receipts

    _stage("matching")
    # Partition. Terminal-decision charges (and every receipt a terminal
    # decision owns) are held out; only not-yet-decided, non-credit charges are
    # re-matched, and only against receipts no terminal decision owns.
    def _terminal(tx_id: str) -> bool:
        d = decisions.get(tx_id)
        return d is not None and d.status in _FOLDER_TERMINAL

    held_tx = {t.transaction_id for t in transactions if _terminal(t.transaction_id)}
    held_docs: set[str] = set()
    for tx_id in held_tx:
        d = decisions.get(tx_id)
        if d and d.chosen_document_id:
            held_docs.add(d.chosen_document_id)
    for m in (*outcome.matches, *outcome.judgment_required, *outcome.ambiguous):
        if m.transaction_id in held_tx:
            held_docs.add(m.document_id)

    in_play_tx = [
        t for t in transactions
        if t.transaction_id not in held_tx and not t.is_credit
    ]
    available = [r for r in pool if r.document_id not in held_docs]

    match_memory = _load_match_memory(run.config or {}, work_dir)
    match_cfg = build_match_cfg(run.config or {}, work_dir, match_memory)
    sub = match_month(in_play_tx, available, match_cfg)

    _stage("judging")
    tx_by_id = {t.transaction_id: t for t in in_play_tx}
    rec_by_id = {r.document_id: r for r in available}
    _apply_judgment(
        sub, tx_by_id, rec_by_id, llm_client,
        suggest_floor=(match_cfg or MatchingConfig()).fx_judgment_suggest_floor,
        cfg=match_cfg or MatchingConfig(),
    )
    _apply_ambiguous_judgment(sub, tx_by_id, rec_by_id, llm_client)
    _apply_unmatched_judgment(
        sub, in_play_tx, available, llm_client,
        match_cfg or MatchingConfig(), run.config or {},
    )

    # Merge: the decided work is spliced back verbatim; the in-play portion is
    # replaced wholesale by the fresh sub-outcome. Every charge and receipt
    # lands in exactly one bucket (reconciliation guarantee): held ones via
    # their kept entry, in-play ones via `sub`, all credits via refunds.
    merged = MatchOutcome(
        matches=[m for m in outcome.matches if m.transaction_id in held_tx]
        + sub.matches,
        unmatched_transactions=[
            t for t in outcome.unmatched_transactions if t in held_tx
        ]
        + sub.unmatched_transactions,
        unmatched_receipts=[d for d in outcome.unmatched_receipts if d in held_docs]
        + sub.unmatched_receipts,
        judgment_required=[
            m for m in outcome.judgment_required if m.transaction_id in held_tx
        ]
        + sub.judgment_required,
        ambiguous=[m for m in outcome.ambiguous if m.transaction_id in held_tx]
        + sub.ambiguous,
        refunds=list(outcome.refunds),
    )

    _stage("saving")
    # Dedup surfacing (constraint 4): a new receipt whose vendor+date+total+ccy
    # equals an existing one is flagged, never dropped. Reuse the view-time
    # detector so the headline count matches the §18 duplicate panel the
    # reviewer then works.
    dup_new_docs: set[str] = set()
    for grp, _basis in find_duplicate_receipt_groups(pool):
        grp_new = [d for d in grp if d in new_ids]
        if grp_new and any(d not in new_ids for d in grp):
            dup_new_docs.update(grp_new)

    n_matched_new = sum(1 for m in sub.matches if m.document_id in new_ids)
    n_review_new = sum(
        1
        for m in (*sub.judgment_required, *sub.ambiguous)
        if m.document_id in new_ids
    )
    n_unmatched_new = sum(1 for d in sub.unmatched_receipts if d in new_ids)
    summary = {
        "at": now_iso,
        "n_files": n_seen,
        "n_ingested": len(new_receipts),
        "n_matched_new": n_matched_new,
        "n_review_new": n_review_new,
        "n_unmatched_new": n_unmatched_new,
        "n_possible_duplicates": len(dup_new_docs),
        "llm_source": llm_source,
        "llm_calls": tracker.call_count if tracker else 0,
        # float(): same latent Decimal-into-json.dumps bug as the expense
        # add path (caught live 2026-07-28); a real tracker returns Decimal.
        "cost_usd": float(round(tracker.total_cost_usd, 4)) if tracker else 0.0,
        "issues": issues,
        # Same rejections, machine-readable (item 20). `issues` keeps the
        # English prose for any existing reader.
        "issue_details": issue_details,
    }

    # Commit under the batch writer lock against a FRESH re-read, the shape
    # `rematch_month` already uses (item 66). Everything above runs vision over
    # a whole folder and then the matcher, which is minutes; rebuilding the
    # period record from `dict(run.snapshot)` afterwards rewrote it from the
    # row read before any of that started, so a concurrent write was erased
    # with no trace and no error.
    with _BATCH_ADD_LOCK:  # item 66: bulk receipt-folder ingest
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        fresh_tx, fresh_receipts, _, _ = snapshot_from_dict(fresh.snapshot)
        # Never drop a charge the month already holds. `merged` buckets the
        # charges this ingest read minutes ago, so a statement upload that
        # landed in between would leave its charges in no bucket at all and
        # break the reconciliation guarantee. Refuse instead: nothing is
        # written, so nothing is lost, and the folder can be re-uploaded.
        committing = {t.transaction_id for t in transactions}
        dropped = [
            t.transaction_id for t in fresh_tx
            if t.transaction_id not in committing
        ]
        if dropped:
            raise RunInputError(
                f"another statement upload added {len(dropped)} charge(s) to "
                "this month while the folder was read; nothing was written, so "
                "no charge was lost. Upload the folder again.",
                code="concurrent_statement_upload",
                n_charges=len(dropped),
            )
        # Receipts that arrived mid-ingest (mail, a hand attach) join the pool
        # as unmatched rather than vanishing -- the same treatment the
        # `rematch_month` commit gives them.
        known_ids = {r.document_id for r in pool}
        extra = [r for r in fresh_receipts if r.document_id not in known_ids]
        if extra:
            pool = pool + extra
            merged.unmatched_receipts.extend(r.document_id for r in extra)
        new_snapshot = dict(fresh.snapshot)
        new_snapshot["receipts"] = [receipt_to_dict(r) for r in pool]
        new_snapshot["outcome"] = outcome_to_dict(merged)
        new_snapshot["folder_ingest"] = summary
        store.update_run_snapshot(run.run_id, new_snapshot)
    return summary


# --------------------------------------------------------------------------
# View model for the workbench template
# --------------------------------------------------------------------------


def _fmt_amount(value: Decimal | None) -> str:
    return "" if value is None else f"{value:,.2f}"


def _fmt_rate(value: Decimal | None) -> str:
    """A conversion rate, trimmed to six significant decimals with trailing
    zeros removed (0.196078, 0.2298). Empty for None/non-finite."""
    if value is None or not value.is_finite():
        return ""
    q = value.quantize(Decimal("0.000001"))
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _fx_breakdown(
    tx: "Transaction",
    receipt: "Receipt | None",
    reference: "FxReference | None" = None,
) -> dict | None:
    """Side-by-side FX comparison for a cross-currency candidate pair, so a
    reviewer sees WHY an uncertain pair is uncertain without decoding the
    prose reason (owner directive 2026-07-25).

    Returns None when the pair is same-currency, or either amount/currency is
    missing (nothing to compare). Otherwise a flat dict the SPA renders as a
    table:

    * charge_* — what the BANK STATEMENT charged (the card currency).
    * receipt_* — what the RECEIPT says (its own currency).
    * zoho_rate / zoho_converted — the receipt's own booked rate and the
      charge-currency amount it implies (Zoho's `exchange_rate` /
      `base_amount`); the "the receipt is worth $X" figure. None when the
      receipt carried no Zoho conversion (a manual/emailed receipt).
    * implied_rate — the rate THIS pairing would require (charge / receipt
      total), directly comparable to zoho_rate: a wide gap is the FX
      coincidence tell.
    * converted_gap / converted_gap_pct — charge minus Zoho's converted
      amount, the discrepancy the amount score reflects. None without a Zoho
      conversion.

    All money/rate values are preformatted strings; direction is always
    "charge currency per one unit of receipt currency", so zoho_rate and
    implied_rate sit in the same column and compare at a glance.

    * reference_* (item 81) — the receipt converted at the rate the MATCHER
      used for this pair, handed in as `reference` (see
      `fx_reference_lookup`). All six keys absent when the pair has no rate.
    """
    if receipt is None:
        return None
    charge_amt = tx.amount
    charge_ccy = tx.transaction_currency
    rec_amt = receipt.detected_total
    rec_ccy = receipt.detected_currency
    if not charge_ccy or not rec_ccy or charge_ccy == rec_ccy:
        return None
    if charge_amt is None or rec_amt is None:
        return None

    implied = (
        (charge_amt / rec_amt) if rec_amt and rec_amt != 0 else None
    )
    zoho_converted = receipt.base_amount
    gap = (
        (charge_amt - zoho_converted) if zoho_converted is not None else None
    )
    gap_pct = None
    if gap is not None and charge_amt and charge_amt != 0:
        gap_pct = round(abs(gap) / abs(charge_amt) * 100)

    return {
        "charge_amount": _fmt_amount(charge_amt),
        "charge_currency": charge_ccy,
        "receipt_amount": _fmt_amount(rec_amt),
        "receipt_currency": rec_ccy,
        # "USD per BRL" — labels the rate column without the SPA guessing.
        "rate_label": f"{charge_ccy} per {rec_ccy}",
        "implied_rate": _fmt_rate(implied),
        "zoho_rate": _fmt_rate(receipt.exchange_rate),
        "zoho_converted": _fmt_amount(zoho_converted),
        "converted_gap": _fmt_amount(gap) if gap is not None else "",
        "converted_gap_pct": gap_pct,
        # Item 81: the conversion at the tool's own rate. Parallel keys,
        # ABSENT (not empty) when the pair has no reference rate.
        **_fx_reference_fields(charge_amt, rec_amt, reference),
    }


# Item 81. The matcher's name for where a rate came from, as the payload
# says it. `configured` is Settings to anyone reading the screen; every other
# source passes through unchanged, so a source the matcher gains later (item
# 82's `ecb_month`) reaches the payload without a change here.
# Rename map for `fx.reference_rate_source`. Empty since 2026-09-23: its
# one entry renamed the retired `configured` rung to "settings". Kept as
# the seam the payload builder already reads, so a future rename needs no
# change at the call site.
_FX_REFERENCE_SOURCE_NAMES: dict[str, str] = {}


@dataclass(frozen=True)
class FxReference:
    """The reference rate the matcher uses for one (receipt, charge) pair,
    with the two thresholds that decide its band. `source` is the matcher's
    own name (`configured` / `statement` / `receipts`)."""

    rate: Decimal
    source: str
    match_pct: Decimal
    review_pct: Decimal
    # Item 82: the month whose ECB average the rate is ('2026-07'), only
    # for `ecb_month`; it can differ from the charge's month when that
    # month's average was not in the table. Note #79: the DAY the polled
    # rate is for ('2026-09-22'), only for `opentickers_day`; it differs
    # from the charge's date when that day had no fix (weekend, holiday).
    period: str | None = None


def fx_reference_lookup(run: "RunRow", transactions: list, receipts: list):
    """Build, once per view, the function that answers "which reference rate
    does the matcher use for this pair".

    It reads the run's FROZEN config through `cli.build_match_cfg` (the
    assembly `rematch_month` uses) and asks the matcher's own
    `derive_fx_reference_rates` and `_reference_rate_for`, looked up on the
    module at call time. There is deliberately no second derivation here: a
    rate the screen shows that the matcher did not use would be the drift
    item 81 exists to prevent. Because it reads the stored config and
    snapshot, it answers for a month matched before this code shipped.

    One consequence of retiring the typed rates (2026-09-23) is visible
    here: a month matched BEFORE the retirement was paired at its typed
    rate, and this function now answers with the rung below it, so the FX
    panel prints the fetched rate while the stored pairing still reflects
    the typed one. The two converge at that month's next natural re-match
    (a receipt arriving, a reviewer's edit). Nothing is re-matched on the
    reviewer's behalf.

    Charges go in with credits removed, the matcher's own first filter.
    Receipts are the month's current pool, so a rate DERIVED from receipt
    lines is re-derived from what the month holds now; a configured rate and
    a statement-derived rate reproduce the matcher's exactly.

    A config the matcher could not read either (a `tuning_path` file that is
    not on this machine, an unknown key, an unparseable rate) yields no
    rates: the fields stay absent and the page renders as before.
    """
    from ..cli import build_match_cfg
    from ..matching import deterministic

    try:
        cfg = (
            build_match_cfg(run.config or {}, Path(run.work_dir))
            or deterministic.MatchingConfig()
        )
    except (OSError, ValueError, ArithmeticError):
        return lambda tx, receipt: None
    derived = deterministic.derive_fx_reference_rates(
        [t for t in transactions if not t.is_credit], list(receipts), cfg
    )

    def lookup(tx: "Transaction", receipt: "Receipt | None") -> FxReference | None:
        if receipt is None or not receipt.detected_currency:
            return None
        hit = deterministic._reference_rate_for(
            cfg, receipt.detected_currency, tx.transaction_currency, derived,
            on=tx.transaction_date,
        )
        if hit is None:
            return None
        rate, source, _n = hit
        period = None
        if source == "ecb_month":
            ecb = cfg.ecb_monthly_rate(
                receipt.detected_currency, tx.transaction_currency,
                tx.transaction_date,
            )
            period = ecb[1] if ecb is not None else None
        elif source == "opentickers_day":
            daily = cfg.daily_rate(
                receipt.detected_currency, tx.transaction_currency,
                tx.transaction_date,
            )
            period = daily[1] if daily is not None else None
        return FxReference(
            rate=rate,
            source=source,
            match_pct=cfg.reference_match_pct(source),
            review_pct=cfg.fx_reference_review_pct,
            period=period,
        )

    return lookup


def _fx_reference_fields(
    charge_amt: Decimal, rec_amt: Decimal, reference: FxReference | None
) -> dict:
    """The six `reference_*` keys of an FX block, or `{}` so they are absent.

    Arithmetic follows the matcher (`match_one`): converted = receipt total x
    rate, deviation = (charge - converted) / converted, band decided on the
    UNROUNDED deviation against `fx_reference_match_pct` /
    `fx_reference_review_pct`. The printed difference is the charge minus the
    converted amount AS PRINTED, so the two figures on screen add up to the
    charge to the cent; the percentage keeps the matcher's basis.
    """
    from decimal import ROUND_HALF_UP

    from ..matching.deterministic import reference_gap

    if reference is None or rec_amt is None or rec_amt <= 0:
        return {}
    # Item 131: the conversion, deviation and band live in the matcher's
    # module, where the judgment layer reads the same band to decide whether
    # a pair the model rejected stays in review.
    arithmetic = reference_gap(
        charge_amt, rec_amt, reference.rate, reference.match_pct, reference.review_pct,
    )
    if arithmetic is None:
        return {}
    converted, deviation, band = arithmetic
    cent = Decimal("0.01")
    shown = converted.quantize(cent, ROUND_HALF_UP)
    gap = (charge_amt - shown).quantize(cent, ROUND_HALF_UP)
    gap_text = "0.00" if gap == 0 else f"{gap:+,.2f}"
    pct = float((deviation * 100).quantize(cent, ROUND_HALF_UP))
    return {
        "reference_rate": _fmt_rate(reference.rate),
        "reference_rate_source": _FX_REFERENCE_SOURCE_NAMES.get(
            reference.source, reference.source
        ),
        "reference_converted": _fmt_amount(shown),
        "reference_gap": gap_text,
        # `or 0.0`: a zero deviation must not serialize as -0.0.
        "reference_gap_pct": pct or 0.0,
        "reference_gap_band": band,
        # Item 82: which month's ECB average, absent for every other source.
        **({"reference_rate_period": reference.period} if reference.period else {}),
    }


def _receipt_view(
    r: Receipt,
    overrides: dict[tuple[str, int], dict],
    *,
    work_dir: Path,
    expense_mode: bool,
) -> dict:
    """One receipt, as both review payloads render it.

    `work_dir` and `expense_mode` are required rather than defaulted: they
    decide `receipt_image_available`, and a caller that forgets them would
    silently tell the reviewer that every receipt is unopenable. That is the
    shape item 52's defect had.
    """
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
            # Note item M1: a REGISTRY line whose ACCOUNT came from a
            # company's rule says so too; the bare default stays silent.
            if cat.source is ClassificationSource.LEARNED or (
                cat.source is ClassificationSource.REGISTRY
                and cat.reasoning
                and cat.reasoning != REGISTRY_DEFAULT_REASONING
            ):
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
        # Receipt preview (2026-07-25): True when the backend can serve this
        # receipt's image via GET /api/runs/{id}/receipts/{doc}/image — a
        # vision-mapped ER-PDF page, or a file the endpoint would find.
        # Resolved against DISK by `receipt_image_file`, never from the shape
        # of the document id: a mail-arrived receipt is neither `manual:` nor
        # `folder:` and the id test called every one of them unavailable.
        "receipt_image_available": (
            r.receipt_image_page is not None
            or receipt_image_file(
                work_dir, r.document_id, expense_mode=expense_mode
            )
            is not None
        ),
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
        # WS2: a note when the vision receipt-image read disagreed with the
        # report's amount/currency (the report value was kept for matching).
        "data_quality_note": r.data_quality_note or "",
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
        # Item 109: a reviewer set this one by hand, so the SPA renders EDIT
        # where it renders EDIT on a receipt line, and the row stops asking
        # to be confirmed. ABSENT (not false) on every guessed category.
        **({"is_edited": True} if cat.source is ClassificationSource.EDITED else {}),
    }


# ── Item 109: a category set on a CHARGE, not on a receipt ─────────────
#
# Stored in the one `category_overrides` table the receipt edits already
# use, under the charge's pseudo-receipt document id (`charge:{tx_id}`,
# the id `categorize_charges` itself mints) at line 0. No second storage
# mechanism, and because the table is keyed on (run_id, document_id,
# line_index) and nothing but `delete_run` deletes from it, the edit
# survives a re-match that rewrites the whole snapshot.

CHARGE_CATEGORY_LINE = 0


def charge_category_key(transaction_id: str) -> tuple[str, int]:
    """The `category_overrides` key a charge's own category is stored at."""
    from ..categorize_charges import CHARGE_DOC_PREFIX

    return (f"{CHARGE_DOC_PREFIX}{transaction_id}", CHARGE_CATEGORY_LINE)


def apply_charge_category_overrides(
    charge_cats: dict, overrides: dict, charge_ids
) -> dict:
    """The receiptless-charge categorization map with the reviewer's own
    picks laid over the tool's guesses (item 109).

    `charge_ids` is the transaction-id set the map may cover — the snapshot
    outcome's `unmatched_transactions`, the same list that produced
    `charge_cats`. An override for any other charge is ignored, so a charge
    that has since been paired can never print a charge-level category beside
    its receipt's.

    A reviewer's pick reads `source=EDITED` and keeps the account she named,
    or the guess's own account when she re-picked the guess's category
    (`override_base_account`, the rule the receipt lines use). Clearing the
    pick (a stored NULL category) leaves the tool's guess showing."""
    from ..categorize_charges import CHARGE_DOC_PREFIX

    allowed = set(charge_ids)
    out = dict(charge_cats)
    for (document_id, line_index), ov in (overrides or {}).items():
        if line_index != CHARGE_CATEGORY_LINE:
            continue
        if not document_id.startswith(CHARGE_DOC_PREFIX):
            continue
        tx_id = document_id[len(CHARGE_DOC_PREFIX):]
        if tx_id not in allowed:
            continue
        category = (ov or {}).get("category")
        if not category:
            continue  # cleared: the tool's guess stands again
        base = charge_cats.get(tx_id)
        out[tx_id] = Categorization(
            category=category,
            zoho_account=(
                (ov or {}).get("zoho_account")
                or override_base_account(category, base)
            ),
            confidence=1.0,
            source=ClassificationSource.EDITED,
            reasoning="set by the reviewer on the charge",
        )
    return out


def _row_posting_category(
    matched_receipt: "Receipt | None",
    overrides: dict[tuple[str, int], dict],
    charge_cat_view: dict | None,
) -> dict | None:
    """The category + Zoho account a charge will post to, resolved onto the
    workbench row (2026-07-27).

    The row previously exposed a category only for a RECEIPTLESS charge
    (`charge_category`, None on matched rows); a matched charge's category
    lived nested in the chosen candidate's receipt line items, and the
    posting ACCOUNT was not in the view at all, so the SPA could not show
    what a reconciled charge posts to. This resolves it server-side (the
    api.ts "frontend does zero business logic" rule):

    - matched charge: aggregate the chosen receipt's line-item categories +
      accounts, distinct values joined with '; ', override-aware (a reviewer
      reclassification wins). Mirrors the journal export's `_ai_category_cells`
      so the workbench and the journal agree.
    - receiptless charge: the Slice-10 `charge_category` view.
    - neither (an uncategorized receipt, e.g. a not-yet-categorized folder
      upload): None, so the UI shows a plain "assign" state, not noise.
    """
    if matched_receipt is not None:
        cats: list[str] = []
        accts: list[str] = []
        srcs: list[str] = []
        for i, li in enumerate(matched_receipt.line_items):
            ov = overrides.get((matched_receipt.document_id, i))
            base = li.categorization
            if ov and ov.get("category"):
                category = ov["category"]
                # Item 70: same rule as `apply_overrides` -- a reclassified
                # line never keeps the account chosen for its old category.
                account = ov.get("zoho_account") or override_base_account(category, base)
                src = "EDITED"
            elif base is not None:
                category = base.category
                account = base.zoho_account
                src = base.source.value if base.source else None
            else:
                continue
            if category and category not in cats:
                cats.append(category)
            if account and account not in accts:
                accts.append(account)
            if src and src not in srcs:
                srcs.append(src)
        if not cats and not accts:
            return None
        return {
            "category": "; ".join(cats),
            "zoho_account": "; ".join(accts),
            "source": "; ".join(srcs),
        }
    return charge_cat_view


# Categorization.decision verdicts that mean "category and account may not
# agree, glance before posting" (categorize.DECISION_AI_OVERRIDE_HEAVY /
# _REVIEW_UNRESOLVED; kept_er / None do not need a look). Literal here to
# avoid importing categorize into the view layer; the values are the ones
# serialize.py round-trips onto the snapshot.
_ADJ_DISAGREE = frozenset({"ai_override_heavy", "review_unresolved"})
# Every WS2 adjudication verdict, so the run payload's
# `adjudication_available` answers "did this run adjudicate" and is not
# turned on by a decision from another feature (item 115).
_ADJ_VERDICTS = _ADJ_DISAGREE | {"kept_er"}
# Item 115: a remembered category was applied to a receipt whose line items
# read something else, and nobody has validated the rule. The row asks for
# the same glance a vendor-name guess does -- the category came from the
# merchant's name, not from this receipt's items.
_LEARNED_OVER_LINE = "learned_over_line"
# Source tiers that are trusted enough to post without a glance. REGISTRY
# (2026-07-29) is a curated merchant default — a deterministic top tier like
# LEARNED — so it reads `ready`, not `check`.
_TRUSTED_SOURCE = frozenset({"LINE", "LEARNED", "EDITED", "REGISTRY"})

# Coarse provenance the expense grid shows for WHY a category / vendor is what
# it is (2026-07-29): the fine ClassificationSource tiers collapse to the
# reviewer-facing set registry | learned | llm | override (REVIEW /
# UNCLASSIFIED fold to "review"). Expense-grid only; the reconcile workbench
# keeps the fine tiers.
_COARSE_SOURCE = {
    "EDITED": "override",
    "REGISTRY": "registry",
    "LEARNED": "learned",
    "LINE": "llm",
    "VENDOR": "llm",
    "REVIEW": "review",
    "UNCLASSIFIED": "review",
}


def _coarse_source_join(joined: str | None) -> str:
    """Map a '; '-joined run of fine source tiers to distinct coarse tokens."""
    out: list[str] = []
    for tok in (joined or "").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        coarse = _COARSE_SOURCE.get(tok, "llm")
        if coarse not in out:
            out.append(coarse)
    return "; ".join(out)


def _expense_vendor_view(eff: Receipt, orig: "Receipt | None", field_ov: dict) -> dict:
    """The grid's `{display, raw, source}` vendor object (2026-07-29).

    `raw` is the ORIGINAL extracted name (pre-edit snapshot), always kept for
    audit. `display` + `source` follow the precedence a reviewer expects:
    a manual vendor edit (override) wins, then the registry canonical, then a
    Phase-6 learned spelling correction, else the extracted name as-is. The
    override / learned displays read from `eff` because `apply_expense_edits` /
    `ExpenseMemory.apply` have already folded those into `detected_vendor`."""
    raw = ((orig.detected_vendor if orig else None) or eff.detected_vendor) or ""
    if str(field_ov.get("vendor") or "").strip():
        return {"display": eff.detected_vendor or "", "raw": raw, "source": "override"}
    if eff.canonical_vendor:
        return {"display": eff.canonical_vendor, "raw": raw, "source": "registry"}
    if eff.vendor_source == "learned":
        return {"display": eff.detected_vendor or "", "raw": raw, "source": "learned"}
    return {"display": eff.detected_vendor or "", "raw": raw, "source": "extraction"}


def _review(state: str, reason: str | None = None, code: str | None = None) -> dict:
    # `reason` is the English hint; `reason_code` is a stable enum the SPA
    # localizes (EN + PT) so a PT reviewer reads the hint in her language.
    return {"state": state, "reason": reason, "reason_code": code}


def category_vocabulary(run) -> str:
    """Which vocabulary this month's categories are written in.

    "gl" when the batch was created on the GL engine (its config carries
    `gl_entity_orgs`), so a line's category is a curated leaf CODE and the
    picker offers `gl_accounts[entity]`. "buckets" for every month made
    before that, which keeps the eight names and `category_options`. The
    category route accepts both vocabularies on any batch, and every entity
    a bucket-era month names is covered by `gl_accounts` too, so neither the
    route nor the entity can tell the SPA which picker to show. The batch
    can, and a month is never categorized in two vocabularies
    (`coa_provision.GL_ENTITY_ORGS_KEY`).
    """
    return "gl" if GL_ENTITY_ORGS_KEY in ((run.config or {}) if run else {}) else "buckets"


def _refusal_review(cats) -> dict | None:
    """A `pick` verdict that says WHY the engine refused, or None.

    The GL engine refuses on purpose (no curated chart for the company, a
    remembered account the company cannot post to, nothing it could place)
    and a refused line has no category, exactly like a line nobody looked at.
    "No category yet" over it reads as "the tool has not looked", so the
    verdict carries the refusal's own sentence and its code instead. None when
    any line lacks a refusal: a line from the bucket path, or one with no
    categorization at all, keeps the generic sentence."""
    codes = []
    for cat in cats:
        code = getattr(cat, "refusal", None) if cat is not None else None
        if not code:
            return None
        codes.append(code)
    if not codes:
        return None
    # Through the engine, not `zoho.*`: the web layer imports nothing from
    # the posting package (`test_zoho_posting_is_gated`).
    from ..categorize import refusal_text

    return {
        **_review("pick", refusal_text(codes[0]), "category_refused"),
        "refusal": codes[0],
    }


def uncategorized_line_indexes(rec: "Receipt | None", overrides: dict) -> list[int]:
    """The indexes of the line items that carry no category (item 160).

    ONE predicate, read by two callers: `_matched_category_review`, which
    turns it into the `uncategorized` / `partial_uncategorized` verdict, and
    `build_expense_view`, which names those lines on the row. They have to be
    the same set or the row names a line the verdict is not about, which is
    worse than the generic sentence it replaces.

    A reviewer's own edit categorizes the line whatever the extraction read,
    so an override counts as categorized here exactly as it does there.
    """
    if rec is None or not rec.line_items:
        return []
    out: list[int] = []
    for i, li in enumerate(rec.line_items):
        ov = overrides.get((rec.document_id, i))
        if ov and ov.get("category"):
            continue
        base = li.categorization
        if base is None or not base.category:
            out.append(i)
    return out


def _matched_category_review(rec: "Receipt | None", overrides: dict) -> dict:
    """Review-state for a matched/held receipt, judged from the CATEGORY it
    will post (2026-07-27). Verdict order is pick > check > ready.

    Judged STRUCTURALLY over the receipt's own line items, not the row's
    "; "-joined posting source: `_row_posting_category` silently drops a line
    with no categorization object, so a partly-uncategorized receipt can read
    as all-trusted in that string. Iterating the lines is the only way to see
    the gap (adversarial-verify finding, 2026-07-27).
    """
    if rec is None or not rec.line_items:
        return _review("pick", "No category yet. Assign one before this charge can post.", "uncategorized")
    srcs: list[str | None] = []
    decs: list[str | None] = []
    # Item 160: the same predicate the row's `uncategorized_lines` is built
    # from, so the verdict and the lines it names cannot disagree.
    uncategorized = bool(uncategorized_line_indexes(rec, overrides))
    for i, li in enumerate(rec.line_items):
        ov = overrides.get((rec.document_id, i))
        if ov and ov.get("category"):
            srcs.append("EDITED")
            decs.append(None)
            continue
        base = li.categorization
        if base is None or not base.category:
            # A line with no category cannot post cleanly; counted above,
            # and contributing neither a source nor a decision token.
            continue
        srcs.append(base.source.value if base.source else None)
        decs.append(getattr(base, "decision", None))
    if uncategorized:
        # `srcs` holds a token per CATEGORIZED line; empty => nothing is
        # categorized (fully uncategorized), non-empty => some lines are and
        # some are not (partial). The hint and code differ so the SPA can say
        # "assign a category" vs "one line still needs a category".
        if not srcs:
            refused = _refusal_review(
                rec.line_items[i].categorization
                for i in uncategorized_line_indexes(rec, overrides)
            )
            if refused is not None:
                return refused
            return _review("pick", "No category yet. Assign one before this charge can post.", "uncategorized")
        return _review("pick", "One or more receipt lines still need a category before this can post.", "partial_uncategorized")
    if any(d in _ADJ_DISAGREE for d in decs):
        return _review("check", "The receipt's category and the account it would post to don't agree. A quick look to confirm the account is right.", "category_account_mismatch")
    if any(d == _LEARNED_OVER_LINE for d in decs):
        # Item 115. Same code (and so the same SPA sentence and the same
        # Keep button) as a vendor-name guess, because it is the same
        # question: the category came from the merchant's name rather than
        # from this receipt's items. Keeping it makes it the reviewer's own.
        return _review("check", "A remembered category for this merchant was used instead of what the receipt's items read. If it fits, keep it.", "vendor_guess")
    if any(s == "VENDOR" for s in srcs):
        return _review("check", "The category was guessed from the merchant name, not the receipt's line items. A quick look to confirm it fits.", "vendor_guess")
    if any(s not in _TRUSTED_SOURCE for s in srcs):
        # categorized, but the provenance is unknown/empty: not a trusted tier.
        return _review("check", "The tool couldn't record how it chose this category. Confirm it fits before posting.", "unknown_provenance")
    return _review("ready")


# Category verdicts a reviewer settles by keeping the category as it is. Not
# `category_account_mismatch`: that one questions the ACCOUNT, and keeping the
# category would clear it without anyone looking at the account.
_CONFIRMABLE_CATEGORY_CODES = frozenset({"vendor_guess", "unknown_provenance"})


def category_confirmable(rec: "Receipt | None", overrides: dict) -> bool:
    """Whether this receipt's category is a guess a reviewer can keep as it
    is (note #62): the category verdict is `vendor_guess` or
    `unknown_provenance`. Before this, the only way to clear either was to
    pick a DIFFERENT category, so a right guess stayed "needs a look"."""
    review = _matched_category_review(rec, overrides)
    if _kept_invoice_unconfirmed(rec, overrides) and review["state"] != "pick":
        return True  # item 105: keeping its categories is the check
    return review.get("reason_code") in _CONFIRMABLE_CATEGORY_CODES


def _kept_invoice_unconfirmed(rec: "Receipt | None", overrides: dict) -> bool:
    """Item 105: a document the reader called a statement page, kept as an
    expense on the invoice rule, until the reviewer has made every line's
    category their own (a category edit, or the Confirm that note #62
    added). Until then it must not read ready: a wrong keep would otherwise
    file itself with the rows nobody needs to open, and self-confirm."""
    if rec is None or not rec.line_items:
        return False
    if INVOICE_READ_AS_STATEMENT_NOTE not in (rec.data_quality_note or ""):
        return False
    return not all(
        (overrides.get((rec.document_id, i)) or {}).get("category")
        for i in range(len(rec.line_items))
    )


def confirm_expense_category(
    store: RunStore, run: RunRow, document_id: str, now_iso: str
) -> str | None:
    """Keep a receipt's categories as they are, as the reviewer's own (note
    #62). Writes one category override per line holding that line's current
    category and account, so a multi-line receipt keeps each line's own
    category (the generic category PUT sets every line to one value). The
    row then reads `EDITED` provenance: ready on the category, so it stops
    asking her to look.

    It is NOT taught at sign-off (2026-09-24 owner ruling: only corrections
    are memorized). Keeping a guess as it stands says the row needs no more
    of her attention; it is not her stating the category, and the line this
    writes says so with `category_source=inherited`. A line that already held
    a category of HERS keeps its own provenance instead of being downgraded
    by the confirm, which is reachable on the item-105 kept invoice where
    only some lines are hers. Returns an error, or None."""
    rec = category_edit_receipt(store, run, document_id)
    if rec is None:
        return Refusal("unknown expense", code="expense_not_found")
    overrides = store.get_category_overrides(run.run_id)
    if not category_confirmable(rec, overrides):
        return Refusal(
            "this expense's category is not a guess to confirm: pick a "
            "category instead, or check the account",
            code="category_not_a_guess",
        )
    for i, li in enumerate(rec.line_items):
        ov = overrides.get((document_id, i)) or {}
        base = li.categorization
        if ov.get("category"):
            category = ov["category"]
            source = ov.get("category_source") or CATEGORY_SOURCE_HUMAN
        else:
            category = base.category if base else None
            source = CATEGORY_SOURCE_INHERITED
        # The same account rule as the category PUT re-sending the current
        # category: a picked account stays, else the line's own is inherited.
        account = category_edit_account(category, None, ov, base)
        store.set_category_override(
            run.run_id, document_id, i, category, account, now_iso,
            category_source=source,
        )
    return None


def set_charge_category(
    store: RunStore,
    run: RunRow,
    transaction_id: str,
    category: str | None,
    zoho_account: str | None,
    now_iso: str,
) -> str | None:
    """Set (or clear) a category on a CHARGE row — item 109.

    Criss's real month-end job is to categorize every charge, and 71 of July's
    112 carried a model guess with no control to correct it: the category
    routes all need a receipt. This writes the same `category_overrides` row a
    receipt edit writes, under the charge's own pseudo-receipt id, so the
    export path needs no second override mechanism and the edit outlives every
    re-match.

    Refuses a charge this run does not hold, and one a receipt already
    settles (its category belongs to the receipt's lines). `category` None /
    "" clears the pick and the tool's guess shows again. Returns an error
    string, or None."""
    _transactions, _receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    known = {t.transaction_id for t in _transactions}
    if transaction_id not in known:
        return Refusal("unknown charge", code="charge_not_found")
    if transaction_id not in set(outcome.unmatched_transactions):
        return Refusal(
            "this charge holds a receipt: set the category on the expense, "
            "not on the charge",
            code="charge_holds_a_receipt",
        )
    document_id, line_index = charge_category_key(transaction_id)
    overrides = store.get_category_overrides(run.run_id)
    base = {
        tx_id: categorization_from_dict(d)
        for tx_id, d in (run.snapshot.get("charge_categorizations") or {}).items()
    }.get(transaction_id)
    # The same account rule the receipt lines use: an explicit account wins,
    # an unchanged category keeps the account it already had, a changed one
    # books to none rather than to the account picked for the old category.
    account = category_edit_account(
        category, zoho_account, overrides.get((document_id, line_index)), base
    )
    store.set_category_override(
        run.run_id, document_id, line_index, category or None, account, now_iso,
        # Item 109's control is a category picker: whatever arrives here is
        # the category she chose for this charge (or a clear), never a guess
        # carried along.
        category_source=CATEGORY_SOURCE_HUMAN,
    )
    return None


def resolve_review(
    *, is_posted: bool, effective_bucket: str, status: str,
    matched_rec: "Receipt | None", overrides: dict, charge_category: dict | None,
    charge_categorization: "Categorization | None" = None,
) -> dict:
    """The review-state a workbench row needs, so the SPA can review by
    exception instead of reading every row (2026-07-27).

    { "state": "ready" | "check" | "pick" | "none", "reason": str | None }

    - ready: reconciled, categorized from a trusted tier, in agreement. Safe
      to confirm in bulk; nothing to do.
    - check: needs one human glance (uncertain match, a vendor-name guess, a
      category/account disagreement, or a receiptless suggested category).
    - pick: a category (every matched line) still has to be assigned by hand.
    - none: not a review target (already posted, refund, rejected, or a plain
      no-receipt row with no signal).

    First-match-wins, top to bottom. `reason` is a plain human "why", non-null
    only where a hint helps (check + pick). A confirmed MATCH is not a
    confirmed CATEGORY: a confirmed row still flows through the category tests,
    so a confirmed-but-uncategorized row is `pick`, not a false `ready`
    (adversarial-verify finding, 2026-07-27). Confirm-all excludes it anyway
    because it is not pending.
    """
    if is_posted:
        return _review("none")
    if effective_bucket == "refund":
        return _review("none")
    if status == STATUS_REJECTED:
        return _review("none")
    if effective_bucket == "review":
        return _review("check", "This match isn't certain. More than one receipt could be this charge, or the best candidate scored low. Confirm which receipt belongs here, or that none does.", "uncertain_match")
    if effective_bucket == "reconciled":
        return _matched_category_review(matched_rec, overrides)
    # unmatched / receiptless
    if charge_category is not None:
        # Item 109: a category the REVIEWER set on the charge is an answer,
        # not a question, so the row stops asking and drops out of
        # `n_charges_category_guessed` (which counts guesses, and this is
        # no longer one).
        if charge_category.get("source") == ClassificationSource.EDITED.value:
            return _review("none")
        return _review("check", "No receipt is attached, so the tool guessed this category from the bank's description. Pick the right one on the row, or attach the receipt, before it posts.", "receiptless_suggested")
    # A charge the GL engine refused is a question with a named reason, not
    # a plain no-receipt row with no signal (`charge_categorization` is the
    # raw categorization `charge_category` is the view of; None on the view
    # means there is no category to show).
    if charge_categorization is not None:
        refused = _refusal_review([charge_categorization])
        if refused is not None:
            return refused
    return _review("none")


def ready_confirm_pairs(run, decisions: dict, overrides: dict) -> list:
    """The (transaction_id, auto-picked document_id) writes a SAFE
    "Confirm all Ready" should make: exactly the rows the view classifies
    review.state == "ready", intersected with the matcher's pending auto-pick
    set (`matched_autopick_decisions`). A check / pick / none row is never in
    this set, and the intersection guarantees every id is a real
    `outcome.matches` pairing, so a bulk confirm can only ratify rows that
    need no further work (adversarial-verify: never wire Confirm-all to the
    broader bulk path). Callers apply `_BULK_DECISION_LIMIT` and report any
    remainder rather than silently truncating.

    Item 133 (2026-09-17): `ready` is a CATEGORY verdict, so the row must
    also pass the owner's pairing rule (`confirmable_pair`, the one "Confirm
    all matched" uses since item 101). Before, a same-amount receipt from
    another merchant (BASE44 100.00 holding an Anthropic receipt, vendor 22)
    was `ready` and one click booked it.
    """
    view = build_view(run, decisions, overrides)
    ready = {
        r["transaction_id"] for r in view["rows"]
        if r.get("review", {}).get("state") == "ready" and confirmable_pair(r)
    }
    return [
        (tx_id, doc_id)
        for tx_id, doc_id in matched_autopick_decisions(run, decisions)
        if tx_id in ready
    ]


def effective_disposition(
    matched_receipt: Receipt | None, decision: Decision | None
) -> tuple[str, str]:
    """The (effective, default) §17 disposition for one transaction.

    The default is seeded from the matched receipt: a receipt flagged
    reimbursable in Zoho Expense seeds `reimbursable_personal` (it posts to
    the reimbursement clearing account); everything else seeds `business`.
    An explicit reviewer verdict (`decision.disposition`) overrides the
    seed. Disposition is annotation only — it never enters bucketing or the
    reconciliation invariant.
    """
    default = (
        DISPOSITION_REIMBURSABLE
        if matched_receipt is not None and matched_receipt.reimbursable is True
        else DISPOSITION_BUSINESS
    )
    effective = (
        decision.disposition
        if decision is not None and decision.disposition
        else default
    )
    return effective, default


def _dispositions(
    transactions: list[Transaction],
    receipts: list[Receipt],
    effective: "MatchOutcome",
    decisions: dict[str, Decision],
) -> dict[str, str]:
    """The §17 disposition map (transaction_id -> disposition) the export
    writers consume, emitting only NON-`business` entries. A run with no
    disposition verdicts and no reimbursable-flagged matched receipts yields
    an empty map, so the Zoho journal stays byte-for-byte unchanged; the
    reconciled CSV / report render `business` for absent txs via their own
    default."""
    rec_by_id = {r.document_id: r for r in receipts}
    match_by_tx = {m.transaction_id: m for m in effective.matches}
    out: dict[str, str] = {}
    for tx in transactions:
        m = match_by_tx.get(tx.transaction_id)
        matched_rec = rec_by_id.get(m.document_id) if m else None
        eff, _default = effective_disposition(
            matched_rec, decisions.get(tx.transaction_id)
        )
        if eff != DISPOSITION_BUSINESS:
            out[tx.transaction_id] = eff
    return out


def build_view(
    run: RunRow,
    decisions: dict[str, Decision],
    overrides: dict,
    resolutions: dict[str, str] | None = None,
    settled_elsewhere: dict[str, dict] | None = None,
    edited_at: str | None = None,
    field_overrides: dict[str, dict[str, str]] | None = None,
    settings: dict | None = None,
) -> dict:
    """Compose the render model: per-transaction rows with candidates and
    the reviewer's effective verdict, plus the unmatched-receipt list and
    a decision-aware summary.

    `resolutions` (§18, group_id -> `ignore`/`confirmed`) attaches the
    reviewer's advisory verdict to each duplicate group in the SPA-facing
    `duplicate_groups` list. None => every group unresolved; advisory only,
    it never touches buckets or the invariant.

    `settled_elsewhere` (R4, item 38): document_id -> `{run_id, label,
    transaction_id}` for receipts in this run's pool that another run's
    charge has claimed. Attached as `settled_by` on the matching
    unmatched / assignable receipt entries -- parallel field, ABSENT (not
    null) everywhere else, so a month with no cross-batch settlements
    renders byte-identically to before the field existed.

    `edited_at` (2026-09-16): the latest stamp in this run's edit tables,
    read by the GET route, folded into the payload's `updated_at`. None from
    every other caller, whose `updated_at` then reads the snapshot and the
    decisions alone (see `month_updated_at`).

    `field_overrides` (items 99 + 100): the run's expense header edits, read
    by the GET route and the publish gate, so a confirmed private expense
    (flag AND reimburse_to) does not count as a receipt needing a charge.

    `settings` (item 107): the stored settings, passed by the GET route so
    `receipt_chase[]` can carry each holder's address and the merchant
    registry's portal hints. None from every other caller, and then the
    chase list is still built (it is derived from the rows) with no address
    and no hint on it: the groups and their counts never depend on it."""
    transactions, receipts, outcome, parse_errors = snapshot_from_dict(run.snapshot)
    rec_by_id = {r.document_id: r for r in receipts}
    # Note item T3: which upload printed each charge, and where. Read once
    # per payload (it walks `statements[]` and one map per upload) and put
    # on every row below, so a booked expense traces back to the statement
    # line it settles without the reader joining anything by hand.
    charge_origin = origins_from_snapshot(run.snapshot)
    # What `receipt_image_available` is resolved against (item 52). Read
    # once per payload; `receipt_image_file` gates the receipts-dir branch
    # on the mode exactly as the image endpoint does.
    rv_work_dir = Path(run.work_dir)
    rv_expense_mode = run_mode(run) == MODE_EXPENSE_GENERATION
    # R4b: borrowed trip receipts referenced by the outcome ride the
    # snapshot as copies; fold them into the lookup so a cross-batch
    # pairing renders its receipt. They are NOT part of `receipts`: the
    # month's own pool, counts, and export never absorb them.
    for bd in (run.snapshot or {}).get(BORROWED_RECEIPTS_KEY) or []:
        try:
            br = receipt_from_dict(bd)
        except (KeyError, TypeError, ValueError):
            continue
        rec_by_id.setdefault(br.document_id, br)
    # Where each borrowed receipt lives. Read once here because both the
    # candidate rows below and the settled-row badge further down name it,
    # and item 61 made the map hold two kinds (a trip, a neighbouring
    # month). Empty on every month borrowing nothing, which is most of them.
    borrow_sources = (run.snapshot or {}).get(RECEIPT_SOURCES_KEY) or {}
    by_tx = _candidates_by_tx(outcome)
    # Item 57: the structural check readiness cannot answer on its own. A
    # month the matcher could not see (sign / entity / currency / card
    # broken) has nothing undecided BECAUSE nothing was proposed; this
    # names the broken input and closes the post gate below.
    # Item 62: receipts the reviewer settled outside the card (bank
    # transfer, cash, PayPal). They stay in the month and in the grid; the
    # RECONCILIATION side lets them go, starting here -- a receipt no card
    # will ever carry must not count as an exact pair the matcher "missed"
    # and so must never make a healthy month read broken.
    settled_outside = settled_outside_map(run.snapshot or {})
    health_receipts = (
        [r for r in receipts if r.document_id not in settled_outside]
        if settled_outside else receipts
    )
    health = month_health(
        transactions, health_receipts, outcome,
        card_scoping=card_scoping_on(run.config),
    )

    # Slice 10: receiptless-charge categorizations (extra snapshot key;
    # absent on pre-Slice-10 runs => empty map, rows render as before).
    # Item 109: the reviewer's own picks lie over the tool's guesses.
    charge_cats = apply_charge_category_overrides(
        {
            tx_id: categorization_from_dict(d)
            for tx_id, d in (run.snapshot.get("charge_categorizations") or {}).items()
        },
        overrides,
        outcome.unmatched_transactions,
    )

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
    # Item 102: charges Criss marked as keyed into her books (yellow) that
    # no receipt settles. They stay out of `unreconciled` (booked is booked)
    # but are counted here, because booked and evidenced are two questions.
    booked_no_receipt: dict[str, Decimal] = {}
    n_booked_no_receipt = 0
    # Item 107: the money behind the "no receipt expected" verdict, kept
    # beside the unreconciled total rather than inside it. The COUNT comes
    # from `completeness_counts` over the same rows, so there is one rule
    # and the two cannot drift apart.
    no_receipt_expected_ccy: dict[str, Decimal] = {}
    # Item 137: a receipt held on a charge of ANOTHER card than the one the
    # tool resolved for it (a pick, the printed method, a remembered card).
    # Same chain the grid shows, same test the matcher demotes by, so a pair
    # confirmed before item 137 (live August 2026: LOVABLE 25.00 on 3645
    # with a receipt picked as 2838) is named on the page, not only the next
    # proposal.
    from ..matching.deterministic import _tx_card_keys, card_evidence, cards_differ

    card_res_view = resolve_batch_row_cards(receipts, run.config, field_overrides or {})
    card_scope_view = {
        r.document_id: r for r in bake_card_scope(receipts, card_res_view)
    }
    n_cards_differ = 0
    # The reviewer's effective verdict per charge, derived ONCE (PR 3): the
    # rows below, the summary's four counters, and the per-card coverage
    # roll-up all read this map rather than each deciding a bucket for
    # itself. See `charge_states`.
    states = charge_states(transactions, effective, decisions)
    coverage, coverage_key_by_tx = month_coverage(
        run, transactions, states
    )
    # Item 60: which charge currently HOLDS each receipt, under the effective
    # verdict. `candidates` come from the raw outcome (every receipt the
    # matcher scored against this charge) while the bucket comes from the
    # assignment, and one receipt settles one charge. So a charge whose
    # candidates were all won by other charges renders with candidates and a
    # bucket of `unmatched`, and the SPA, deriving its label from the bucket,
    # said "No receipt found" about a receipt that is sitting on the row
    # above. Naming the holder is the fact the label was missing; it is the
    # charge's own id on its own row, so a candidate is only ever "taken"
    # from somebody else's perspective.
    holder_by_doc: dict[str, str] = {}
    for m in effective.matches:
        holder_by_doc.setdefault(m.document_id, m.transaction_id)
    for tx_id_, st in states.items():
        if st["held_doc"]:
            holder_by_doc[st["held_doc"]] = tx_id_
    # 2026-09-16: a PENDING review row holds its receipts too. Its `held_doc`
    # is the reviewer's pick, None until one exists, yet `apply_decisions`
    # pass 2 has already consumed every receipt it keeps, so a later charge
    # the matcher paired with the same receipt falls to `unmatched` with no
    # holder named (August 2026: ANTHROPIC 52.46 lost 0023 to a judgment row
    # and read `n_charges_receipt_taken` 0). `assignable_receipts` below
    # already counts these. setdefault, so a reconciled match or a
    # reviewer's pick keeps precedence.
    for pending in (*effective.judgment_required, *effective.ambiguous):
        holder_by_doc.setdefault(pending.document_id, pending.transaction_id)
    tx_by_id_all = {t.transaction_id: t for t in transactions}
    # Item 81: the reference rate each FX candidate's block shows, from the
    # matcher's own lookup over the run's frozen config, built once here.
    fx_reference = fx_reference_lookup(run, transactions, list(rec_by_id.values()))

    def _from_batch(document_id: str) -> dict:
        """`{"from_batch": {...}}` when this candidate's receipt is borrowed
        from another batch, else `{}` so the key is absent rather than null.

        Item 61: a borrowed receipt was anonymous until it was CHOSEN (the
        row's `settled_by` badge), so an offered one read as if it belonged
        to this month. Same object on both sides now, and it names a trip or
        a neighbouring month by the same key."""
        src = borrowed_source_view(borrow_sources.get(document_id))
        return {"from_batch": src} if src else {}

    def _held_by(document_id: str, by_tx_id: str) -> dict:
        """`{"held_by": {...}}` when another charge holds this receipt, else
        `{}` so the key is absent rather than null."""
        holder = holder_by_doc.get(document_id)
        if not holder or holder == by_tx_id:
            return {}
        htx = tx_by_id_all.get(holder)
        if htx is None:
            return {}
        return {
            "held_by": {
                "transaction_id": holder,
                "vendor": htx.vendor_from_statement,
                "amount": _fmt_amount(htx.amount),
                "currency": htx.transaction_currency,
                "date": htx.transaction_date.isoformat()
                if htx.transaction_date else None,
            }
        }

    # Item 16: a rejected verdict releases the charge's whole proposal --
    # `apply_decisions` pass 3 sends the charge to unmatched and consumes
    # none of its receipts -- but `candidates` still come from the raw
    # outcome, so every receipt the reviewer just pushed away re-renders
    # underneath the row exactly as it did before, offered again as if it
    # were still on the table. Nothing in the payload said a pairing had
    # been turned down, so no affordance could answer "what now". The flag
    # is the fact that was missing, and it reads the CURRENT verdict, so
    # resetting the charge to pending clears it.
    #
    # Charge-level, because a reject is: `apply_decisions`,
    # `effective_settlements` and `sync_claim_for_decision` all read the
    # status alone and ignore `chosen_document_id`, and a bulk reject
    # writes that column NULL, so marking only a named document would
    # leave the commonest path unmarked.
    def _rejected_pairing(charge_status: str) -> dict:
        """`{"rejected": True}` on every candidate of a rejected charge,
        else `{}` so the key is absent rather than false."""
        return {"rejected": True} if charge_status == STATUS_REJECTED else {}

    def _candidate_card_evidence(tx, doc: str) -> dict:
        """Item X1: `card_evidence: {receipt, charge}` from the matcher's own
        definition, read on the receipt as the matcher saw it (the card
        scope baked). Always present on a candidate; `{}` only when the
        receipt is not in the pool at all (a borrowed copy the view has
        lost), so the key is absent rather than invented."""
        receipt = card_scope_view.get(doc) or rec_by_id.get(doc)
        if receipt is None:
            return {}
        rec_src, chg_src = card_evidence(tx, receipt)
        return {"card_evidence": {"receipt": rec_src, "charge": chg_src}}

    for tx in transactions:
        tx_id = tx.transaction_id
        decision = decisions.get(tx_id)
        status = decision.status if decision else STATUS_PENDING
        init = initial_bucket(tx_id)

        state = states[tx_id]
        effective_bucket, held_doc = state["bucket"], state["held_doc"]
        # PR-E: the workbench section this row renders in. "posted" wins
        # (her yellow / the reviewer's z-key); review needs attention; a
        # still-pending unmatched row with candidates is worth attention
        # too; everything else unmatched is "no receipt yet".
        is_posted = state["is_posted"]

        if effective_bucket == "reconciled":
            n_reconciled += 1
        elif effective_bucket == "review":
            n_review += 1
        elif effective_bucket == "refund":
            n_refunds += 1
        else:
            n_unmatched_tx += 1

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
                    # WS3 — card agreement between the charge's card and the
                    # receipt's Zoho payment mode. 50 means neither side named
                    # a card, so it neither corroborates nor contradicts.
                    "card_pct": round(m.card_score * 100),
                    "receipt": (
                        _receipt_view(
                            r, overrides, work_dir=rv_work_dir,
                            expense_mode=rv_expense_mode,
                        )
                        if r else None
                    ),
                    # Cross-currency comparison (charge vs receipt vs Zoho's
                    # own conversion); None for same-currency pairs.
                    "fx": _fx_breakdown(tx, r, fx_reference(tx, r)),
                    # Item 60: the charge that currently holds this receipt,
                    # when it is not this one. Parallel field, ABSENT (not
                    # null) on a candidate nobody else holds, so a month with
                    # no contested receipt renders exactly as before.
                    **_held_by(m.document_id, tx_id),
                    # Item 16: the reviewer turned this pairing down.
                    # Parallel field, ABSENT (not false) everywhere else,
                    # so a month with no reject renders as it did before.
                    **_rejected_pairing(status),
                    # Item 61: the batch this candidate's receipt lives in,
                    # when it is not this one. Parallel field, ABSENT on
                    # every candidate from the month's own pool.
                    **_from_batch(m.document_id),
                    # Item 80: charge date minus receipt date and its zone
                    # (none / lag / mismatch). Label only; ABSENT when
                    # either date is missing.
                    **_candidate_date_gap(tx, r),
                    # Item X1: where each side's card came from, on every
                    # candidate; and the matcher's review code, ABSENT
                    # unless it flagged the pair.
                    **_candidate_card_evidence(tx, m.document_id),
                    **({"review_code": m.review_code} if m.review_code else {}),
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
                    "receipt": _receipt_view(
                        rec_by_id[held_doc], overrides,
                        work_dir=rv_work_dir,
                        expense_mode=rv_expense_mode,
                    ),
                    "fx": _fx_breakdown(
                        tx, rec_by_id[held_doc],
                        fx_reference(tx, rec_by_id[held_doc]),
                    ),
                    **_from_batch(held_doc),
                    **_candidate_date_gap(tx, rec_by_id[held_doc]),
                    **_candidate_card_evidence(tx, held_doc),
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
        if is_posted and effective_bucket == "unmatched":
            n_booked_no_receipt += 1
            booked_no_receipt[tx.transaction_currency] = (
                booked_no_receipt.get(tx.transaction_currency, Decimal("0"))
                + abs(tx.amount)
            )
        # Item 107: a charge the reviewer ruled no receipt will ever exist
        # for is decided, so it leaves the unreconciled total the way a
        # booked one does, and its money gets its own name beside it
        # (item 102's shape). The annual card fee stops reading as money
        # nobody has evidenced, without disappearing from the month.
        no_receipt_due = bool(str(
            (decision.no_receipt_expected if decision else "") or ""
        ).strip()) and effective_bucket == "unmatched" and not is_posted
        if no_receipt_due:
            no_receipt_expected_ccy[tx.transaction_currency] = (
                no_receipt_expected_ccy.get(tx.transaction_currency, Decimal("0"))
                + abs(tx.amount)
            )
        if (
            effective_bucket not in ("reconciled", "refund")
            and not is_posted
            and not no_receipt_due
        ):
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

        # §17 disposition: the matched receipt (the held candidate) seeds the
        # default; an explicit reviewer verdict overrides it. Annotation only.
        matched_rec = rec_by_id.get(held_doc) if held_doc else None
        eff_disp, disp_default = effective_disposition(matched_rec, decision)

        # Categorization on the row: the receiptless suggestion, the resolved
        # posting category+account, and the review-by-exception state, computed
        # once here so the SPA groups + bulk-confirms with no logic of its own.
        charge_cat_view = _charge_category_view(charge_cats.get(tx_id))
        posting_category = _row_posting_category(
            matched_rec, overrides, charge_cat_view
        )
        # Item 70: a needs-review row holds no receipt until confirmed, so a
        # category set on its candidate saved and never showed. Show the one
        # the Confirm would book, flagged as proposed. Display only: the
        # readiness below still reads `matched_rec`, which stays None.
        proposed_flag: dict = {}
        if matched_rec is None and effective_bucket == "review":
            proposed = proposed_posting_category(cands, rec_by_id, overrides)
            if proposed is not None:
                posting_category = proposed
                proposed_flag = {"posting_category_proposed": True}
        review = resolve_review(
            is_posted=is_posted,
            effective_bucket=effective_bucket,
            status=status,
            matched_rec=matched_rec,
            overrides=overrides,
            charge_category=charge_cat_view,
            charge_categorization=charge_cats.get(tx_id),
        )
        cards_flag: dict = {}
        scoped_rec = card_scope_view.get(held_doc) if held_doc else None
        if scoped_rec is not None and effective_bucket in ("reconciled", "review"):
            tx_keys = _tx_card_keys(tx)
            if cards_differ(tx_keys, scoped_rec):
                picked = card_res_view[held_doc]["card"]
                cards_flag = {
                    "cards_differ": {
                        "document_id": held_doc,
                        "charge_card": "/".join(sorted(tx_keys)),
                        "receipt_card": "/".join(scoped_rec.card_scope_keys),
                        "receipt_card_key": picked.key,
                        "receipt_card_label": picked.display_label,
                        "receipt_card_source": scoped_rec.card_scope_source,
                    }
                }
                n_cards_differ += 1

        rows.append(
            {
                "transaction_id": tx_id,
                "date": tx.transaction_date.isoformat() if tx.transaction_date else "",
                "vendor": tx.vendor_from_statement,
                "amount": _fmt_amount(tx.amount),
                "currency": tx.transaction_currency,
                "account_id": tx.account_id,
                "legal_entity_id": tx.legal_entity_id,
                # PR 3: the `coverage[]` row this charge counts in. Carried
                # on the row so the reconciliation document groups charges
                # by the IDENTICAL assignment the coverage panel totals
                # them under, rather than re-deriving a card from
                # `account_id` and quietly splitting one card in two.
                "coverage_key": coverage_key_by_tx.get(tx_id, ""),
                "initial_bucket": init,
                "effective_bucket": effective_bucket,
                "status": status,
                "chosen_document_id": held_doc,
                # Item 137: ABSENT unless the held receipt's card and the
                # charge's card disagree.
                **cards_flag,
                "candidates": cands,
                "has_learned": has_learned,
                # L1: her workbook's fill-color annotation (yellow=posted,
                # gray=subscription); drives the workbench chips.
                "entry_status": tx.entry_status,
                # Owner ruling 2026-09-17: "derived" when the tool inferred
                # the subscription mark from history, which closes nothing
                # (a gray fill does). Parallel field, ABSENT on every row
                # whose mark came from the workbook or a verdict.
                **(
                    {"entry_status_source": tx.entry_status_source}
                    if tx.entry_status_source is not None else {}
                ),
                # Item 162 (owner directive 2026-09-20): every coloured cell
                # on the source workbook row, named but NOT interpreted. A
                # record of what the sheet is marked with; `entry_status`
                # above stays the only verdict any colour produces. Parallel
                # field, ABSENT on a row with no readable fill and on every
                # month read before the item (the parse happens at upload).
                **({"fills": _fills_view(tx)} if tx.fills else {}),
                # Slice 10: the tool's suggested category for a receiptless
                # charge (None on matched rows and pre-Slice-10 snapshots).
                "charge_category": charge_cat_view,
                # The category + Zoho account this charge posts to, resolved
                # for BOTH matched and receiptless rows (2026-07-27), so the
                # SPA can show categorization on reconciled rows too. None when
                # the matched receipt is not categorized (e.g. a folder upload).
                "posting_category": posting_category,
                # Item 70: `posting_category` came from the candidate the
                # Confirm would take, not a held receipt. Parallel field,
                # ABSENT (not false) on every other row.
                **proposed_flag,
                # Review-by-exception state (2026-07-27): ready / check / pick
                # / none + a plain "why". Server-computed so the SPA groups and
                # bulk-confirms on it, never re-derives it.
                "review": review,
                # §17: the reviewer's effective disposition + the seeded
                # default (so the SPA can show "auto: reimbursable" hints).
                "disposition": eff_disp,
                "disposition_default": disp_default,
                "section": section,
                "triage_score": max(
                    (c["score"] for c in cands if c["score"]), default=None
                ),
                # Item 76: whose move this row is (`decide` is the reviewer's
                # turn, the `n_undecided` set; every other value is nothing
                # to do, and says why), and who wrote the verdict when there
                # is one. `decided_by` / `decided_rule` are ABSENT on a
                # pending row.
                "turn": row_turn(status, is_posted, effective_bucket),
                **decided_by_view(decision),
                # Item 107: the chase states, both ABSENT unless a reviewer
                # set them. `receipt_requested_at` + `requested_to` leave
                # the charge open; `no_receipt_expected` (the reason) closes
                # it. See `receipt_chase_view`.
                **receipt_chase_view(decision),
                # Note item T3: where this charge was printed --
                # `statement_file`, `statement_id`, and `source_row` (a
                # workbook line) or `source_page` (a PDF one). Each one
                # parallel and ABSENT when not recorded, so a month whose
                # uploads predate the record renders as it did before.
                **origin_fields(charge_origin.get(tx_id)),
            }
        )

    # Receipt groups, every one DECIDED by the ladder (item 74). Decided once
    # per payload (the ladder reads digests and text layers) and read twice:
    # items 83 + 75 need the set-aside copies before the near-miss offer and
    # the unmatched list are built, the duplicate lists below need the groups.
    resolutions = resolutions or {}
    receipt_decisions = duplicate_decisions(run, receipts, resolutions)
    # Items 83 + 75 (note #46): a copy the tool or a reviewer has decided
    # leaves every open list on the month. Exactly the copies the re-match
    # keeps out of the pool (`copies_to_collapse`), and only while the
    # effective outcome leaves them unmatched: a copy a reviewer hand-matched
    # holds a charge and renders as that match.
    # Item 94: the one predicate every listing and total on the month reads.
    set_aside_copy_ids = set(decided_copies(
        run, receipts, resolutions,
        receipt_decisions=receipt_decisions, effective=effective,
    ))

    # Unmatched receipts come straight from the resolved outcome, so a
    # receipt freed by a reject (or stolen by a manual match) reappears
    # here and can be re-assigned.
    # Item 62: scoped to what the EFFECTIVE outcome leaves unmatched, so a
    # receipt that (however it got there) holds a charge renders as the
    # match it is rather than disappearing from both sides of the screen.
    settled_outside_ids = {
        d for d in effective.unmatched_receipts
        if d in settled_outside and d in rec_by_id
    }
    unmatched_receipts = [
        _receipt_view(
            rec_by_id[d], overrides,
            work_dir=rv_work_dir, expense_mode=rv_expense_mode,
        )
        for d in effective.unmatched_receipts
        if d in rec_by_id and d not in settled_outside_ids
    ]
    # The suggestion, never the disposition: a mode the scan read as a
    # tender no card statement carries. Parallel and ABSENT when there is
    # no signal, so a receipt with an empty payment mode -- which is what
    # July's Redis, Konsultancy and 360Crossmedia invoices actually carry
    # -- offers nothing and waits for the reviewer.
    for rec in unmatched_receipts:
        hit = suggested_settled_outside(rec.get("payment_mode"))
        if hit is not None:
            rec["suggested_settled_outside"] = hit

    # PR D — for each unmatched charge, the closest free receipt by amount
    # ("closest was $58.40, 4 days off"), so Chris sees the near-miss the
    # matcher just barely rejected and can hand-match it if it's right.
    tx_by_id = {t.transaction_id: t for t in transactions}
    free_recs = [
        rec_by_id[d]
        for d in effective.unmatched_receipts
        if d in rec_by_id and rec_by_id[d].detected_total is not None
        and d not in set_aside_copy_ids
    ]

    def _near_miss(tx: Transaction) -> dict | None:
        if not free_recs or tx.amount is None:
            return None
        # 2026-07-22: a near miss must actually be NEAR. This used to return
        # the closest free receipt however far away it was, so every
        # receiptless subscription charge (ANTHROPIC, GOOGLE Workspace) wore
        # a "NEAR MISS" chip pointing at an unrelated BRL meal — a signal
        # that fires on everything tells the reviewer nothing. Restricted to
        # the case the chip claims: the SAME currency, a comparable amount,
        # and a plausible posting gap. Cross-currency pairs are not compared
        # by raw amount (10.32 USD vs 60.00 BRL is meaningless); when one is
        # genuinely plausible the FX candidate path already surfaces it as a
        # candidate, which carries the rate reasoning this chip cannot.
        same_ccy = [
            r for r in free_recs if r.detected_currency == tx.transaction_currency
        ]
        if not same_ccy:
            return None
        best = min(same_ccy, key=lambda r: abs(tx.amount - r.detected_total))
        amount_diff = abs(tx.amount - best.detected_total)
        if tx.amount and amount_diff / abs(tx.amount) > _NEAR_MISS_AMOUNT_PCT:
            return None
        date_diff = (
            abs((best.detected_date - tx.transaction_date).days)
            if best.detected_date and tx.transaction_date
            else None
        )
        if date_diff is not None and date_diff > _NEAR_MISS_DATE_DAYS:
            return None
        return {
            "vendor": best.detected_vendor or "",
            "total": _fmt_amount(best.detected_total),
            "currency": best.detected_currency or "",
            "amount_diff": _fmt_amount(amount_diff),
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

    # Item 74 (owner ruling 2026-09-15): charge-side duplicate detection is
    # deleted. The statement is the truth of what was charged, so two charges
    # to one vendor are two charges. `duplicate_charges` stays in the payload
    # as an always-empty list and `kind` stays on every group, so a consumer
    # that pairs the lists by kind does not break; neither ever carries a
    # charge again.
    duplicate_charges: list = []
    # Receipt groups (`receipt_decisions`, decided above), listed once so the
    # legacy list, `duplicate_groups` and the counts read the same groups in
    # the same order. Every group stays in both lists, decided or not: the
    # SPA pairs `duplicate_groups` with `duplicate_receipts` BY INDEX within
    # a kind, and filtering one list would mislabel rows.
    duplicate_receipts = [
        [
            _receipt_view(
                rec_by_id[d], overrides,
                work_dir=rv_work_dir, expense_mode=rv_expense_mode,
            )
            for d in dec.members if d in rec_by_id
        ]
        for dec in receipt_decisions
    ]

    # §18: a flat, SPA-facing view of the duplicate groups with a stable,
    # content-derived group_id and the reviewer's resolution, plus (item 74)
    # the rung that decided it (`basis`), who decided (`decided_by`), what
    # it is (`verdict`) and whether anything is still open (`state`).
    duplicate_groups = [duplicate_group_entry(dec) for dec in receipt_decisions]  # run view

    # §18 (2026-08-28): the same groups, carried ON the row. A group is only
    # actionable if the reviewer can see which row is in it; until now the
    # ids lived in a side list, so the two Pressmaster copies in the April
    # batch sat on screen with nothing to tell them apart from any other
    # pair of rows. Parallel field: `duplicate` is None on every row in no
    # live group, and on every payload built before this. A charge row is
    # never in a group any more (item 74) and keeps the field as None.
    receipt_dup_flags = duplicate_row_flags(duplicate_groups, kind="receipt")
    for row in rows:
        row["duplicate"] = None
    for rec in unmatched_receipts:
        rec["duplicate"] = receipt_dup_flags.get(rec.get("document_id"))
    # `assignable_receipts` is the hand-match picker and holds EVERY
    # receipt, matched ones included. It is the one place a reviewer could
    # assign both copies of an invoice to two different charges, and it is
    # what makes `n_duplicate_copies` fully backed by rows on screen: a
    # duplicate receipt that matched a charge appears here even though it
    # is in neither `rows` nor `unmatched_receipts`.
    for rec in assignable_receipts:
        rec["duplicate"] = receipt_dup_flags.get(rec.get("document_id"))

    # R4 (item 38): name the run that settled a receipt this pool still
    # holds. Absent-unless-set, like `mixed_months` on the inbound log: a
    # month with no cross-batch settlements renders exactly as before.
    if settled_elsewhere:
        for rec in (*unmatched_receipts, *assignable_receipts):
            hit = settled_elsewhere.get(rec.get("document_id"))
            if hit is not None:
                rec["settled_by"] = hit
    # R4b, the month side of the same provenance: a charge settled with a
    # borrowed receipt names where the receipt came from. Absent on every
    # row settled from the month's own pool. Item 61 added the second kind:
    # a trip entry still renders `{run_id, trip_id, label}` byte for byte,
    # and a neighbouring month's carries `kind: "adjacent"` instead of a
    # trip id, so the badge can say which it is without guessing.
    if borrow_sources:
        for row in rows:
            src = borrowed_source_view(
                borrow_sources.get(row.get("chosen_document_id"))
            )
            if src is not None:
                row["settled_by"] = src

    # Item 73 (note #42): what kind of statement line each charge is, and
    # where its company came from. The bucket answers "was this matched"
    # and keeps doing so; `refund` there means "money back to the card,
    # never receipt-matched", which a card payoff also is. `row_type` says
    # which: July's -9,664.81 "Payment Thank You-Mobile" printed Type
    # `Payment` and is a `payment`, not a refund. `entity_source` names the
    # basis of `legal_entity_id` (card / batch / none), so an entity the
    # upload lent a row reads as lent rather than as a fact about the row.
    from ..ingest._common import row_type_of

    view_cards = _batch_cards(run.config)
    for row in rows:
        row_tx = tx_by_id[row["transaction_id"]]
        row["row_type"] = row_type_of(row_tx)
        row["entity_source"] = charge_entity_source(row_tx, view_cards)

    # Items 83 + 75 (notes #40, #46): the unmatched lists say what they hold.
    # A decided copy moves out of `unmatched_receipts` and the hand-match
    # picker into `copies_set_aside` (its marker and undo travel with it; the
    # duplicate lists above are untouched, so the by-index pairing of
    # `duplicate_groups` with `duplicate_receipts` does not move). Every
    # receipt still sits in exactly one place: held by a charge, unmatched,
    # settled outside, or set aside as a copy. And every unmatched receipt and
    # charge carries a parallel `reason_code` (`unmatched_reasons`).
    from ..unmatched_reasons import (
        DUPLICATE_COPY,
        charge_reason_code,
        loaded_card_keys,
        receipt_reason_code,
    )

    copies_set_aside = [
        rec for rec in unmatched_receipts
        if rec.get("document_id") in set_aside_copy_ids
    ]
    if copies_set_aside:
        unmatched_receipts[:] = [
            rec for rec in unmatched_receipts
            if rec.get("document_id") not in set_aside_copy_ids
        ]
        assignable_receipts[:] = [
            rec for rec in assignable_receipts
            if rec.get("document_id") not in set_aside_copy_ids
        ]
    for rec in copies_set_aside:
        rec["reason_code"] = DUPLICATE_COPY
    reason_cards = loaded_card_keys(transactions)
    reason_period = statement_period_for_month(run, transactions)
    for rec in unmatched_receipts:
        rec["reason_code"] = receipt_reason_code(
            rec_by_id[rec["document_id"]],
            loaded_cards=reason_cards,
            period=reason_period,
            settled_elsewhere="settled_by" in rec,
        )
    charge_reasons: dict[str, str] = {}
    for row in rows:
        if row["effective_bucket"] != "unmatched":
            continue
        row["reason_code"] = charge_reasons[row["transaction_id"]] = charge_reason_code(
            row_type=row.get("row_type"),
            entry_status=row.get("entry_status"),
            candidates=row["candidates"],
        )
    for tx_entry in unmatched_transactions:
        tx_entry["reason_code"] = charge_reasons[tx_entry["transaction_id"]]

    # Items 99 + 100: what still stands between this month and complete,
    # read off the rows and the unmatched list the page renders. The publish
    # gate reads the same summary.
    # Every receipt no charge holds, copies included, so the decided-copy
    # exclusion reads `decided_copies` (item 94) rather than trusting the
    # list split above. `field_overrides` (the expense header edits) carries
    # the confirmed private expenses; a caller that passes none counts every
    # private receipt as needing a charge.
    completeness = completeness_counts(
        rows, [*unmatched_receipts, *copies_set_aside],
        private_docs=frozenset(_private_reimbursements(field_overrides or {})),
        copy_docs=frozenset(set_aside_copy_ids),
    )
    ready_to_post = n_undecided == 0 and health["state"] == HEALTH_OK

    n_tx = len(transactions)
    # Item 62: the pool a card statement can actually settle. Items 83 + 75:
    # a set-aside copy is not a second purchase for a card to settle either.
    n_matchable_receipts = (
        len(receipts) - len(settled_outside_ids) - len(copies_set_aside)
    )
    n_unknown_currency = sum(1 for r in receipts if r.detected_currency is None)
    # L4 noise guard: the missing-image badge renders only when this run's
    # receipt source carries image references at all.
    has_image_info = any(r.has_receipt_image for r in receipts)
    # Item 84: the expense payload's rule, so the one name answers one
    # question on both payloads.
    n_missing_receipt_image = sum(
        1 for r in receipts
        if receipt_image_missing(
            has_image_info=has_image_info,
            available=receipt_image_file(
                rv_work_dir, r.document_id, expense_mode=rv_expense_mode
            ) is not None,
            referenced=r.has_receipt_image,
        )
    ) if has_image_info else 0
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
        # Item 62: its own name, its own question -- how many receipts the
        # reviewer settled outside the card. `n_receipts` still answers
        # "how many receipts are in the month" and does NOT move: they are
        # still in the month, still in the grid, still in the report.
        "n_settled_outside": len(settled_outside_ids),
        # Items 83 + 75: how many decided duplicate copies were set aside
        # rather than listed as unmatched. `n_duplicate_copies` keeps its
        # question (every redundant copy, matched or not).
        "n_copies_set_aside": len(copies_set_aside),
        # See the run-summary note above: charge-based `match_rate` under-reads
        # a receiptless-heavy month; `receipt_match_rate` reports receipts
        # placed (reconciled + review) over receipts that exist. The SPA leads
        # with the receipt rate and keeps the charge rate as a labelled
        # secondary figure. (2026-07-27)
        "match_rate": round(n_reconciled / n_tx * 100, 1) if n_tx else 0.0,
        "n_receipts_matched": max(
            n_matchable_receipts - len(unmatched_receipts), 0
        ),
        # Over the receipts a card COULD settle. A month whose only
        # stragglers were paid by transfer reads 100%, which is the true
        # answer: nothing is left for the statement to explain.
        "receipt_match_rate": (
            round(
                (n_matchable_receipts - len(unmatched_receipts))
                / n_matchable_receipts * 100, 1
            )
            if n_matchable_receipts else 0.0
        ),
        "invariant_ok": (
            n_reconciled + n_review + n_unmatched_tx + n_refunds
        ) == n_tx,
        "n_parse_errors": count_parse_issues(parse_errors)["errors"],
        # Carried from the run's stored summary: both advisories are decided
        # at run time from the inputs. `statement_advisory` was written at
        # creation but never rebuilt here, so it had never actually reached
        # the review screen.
        "statement_advisory": run.summary.get("statement_advisory"),
        "statement_advisory_detail": run.summary.get(
            "statement_advisory_detail"
        ),
        "setup_advisories": run.summary.get("setup_advisories", []),
        "llm_cost_usd": run.summary.get("llm_cost_usd", "0"),
        "ai_unavailable": run.summary.get("ai_unavailable", False),
        "n_duplicate_groups": len(duplicate_receipts),
        # How many COPIES are redundant (every copy after the first in a
        # live group): the question "is this month's count inflated, and by
        # how much". `n_duplicate_groups` answers a different one and keeps
        # its meaning. Not "rows": a duplicate receipt that matched a charge
        # counts here and is not one of `rows[]`.
        "n_duplicate_copies": n_extra_copies(receipt_dup_flags),
        # Item 74(d): how many groups nobody has decided, the only ones that
        # belong in a to-do list. The tool decides every group it can, so
        # this is 0 unless a group escaped every rung.
        "n_duplicate_groups_open": sum(
            1 for dec in receipt_decisions if dec.state == STATE_OPEN
        ),
        # PR A — "Ready to post?" bar. Item 57: a broken month is never
        # ready, whatever the reviewer has (not) decided; `month_health`
        # says which input is broken.
        "n_undecided": n_undecided,
        # Its question is unchanged: nothing is left to decide. It is NOT
        # "the month is complete" (item 99); `month_complete` is.
        "ready_to_post": ready_to_post,
        "month_health": health,
        # Item 99 (owner ruling 2026-09-17): the month is complete, so it may
        # read Ready to post and be published. Nothing left to decide, every
        # charge holds a receipt or a closing verdict, every receipt holds a
        # charge or is set aside, and no receiptless charge's category is
        # still a guess. The three counts say what blocks it;
        # `n_charges_closed_recurring` says what the gray fill closed
        # (owner ruling 2026-09-17) and never blocks.
        "month_complete": is_month_complete(
            ready_to_post=ready_to_post, counts=completeness
        ),
        **completeness,
        # Item 59: charges whose card the registry cannot name carry no
        # entity; the fix is defining the card once, not a row edit.
        "n_charges_no_entity": sum(
            1 for t in transactions if not (t.legal_entity_id or "").strip()
        ),
        "n_unmapped_accounts": n_unmapped,
        "unreconciled_by_ccy": {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(unreconciled.items())
        },
        # Item 102: booked in the workbook, no receipt holding it. Sits next
        # to `unreconciled_by_ccy`, never inside it.
        "n_booked_no_receipt": n_booked_no_receipt,
        # Item 137: rows carrying `cards_differ`.
        "n_cards_differ": n_cards_differ,
        "booked_no_receipt_by_ccy": {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(booked_no_receipt.items())
        },
        # Item 107: money on charges the reviewer ruled will never have a
        # receipt (the annual fee, interest). Beside `unreconciled_by_ccy`
        # and out of it, exactly as `booked_no_receipt_by_ccy` is; the count
        # is `n_charges_no_receipt_expected` in `completeness` above.
        "no_receipt_expected_by_ccy": {
            ccy: f"{amt:,.2f}"
            for ccy, amt in sorted(no_receipt_expected_ccy.items())
        },
        # Item 60: charges the tool found receipts for that another charge
        # now holds. Its own name because it is its own question: these rows
        # are not "no receipt found", they are waiting on a contested pick.
        "n_charges_receipt_taken": sum(
            1 for r in rows
            if r["effective_bucket"] == "unmatched"
            and r["candidates"]
            and all(c.get("held_by") for c in r["candidates"])
        ),
        # Item 16: (charge, receipt) pairings the reviewer turned down.
        # Pairings, not rows: a rejected charge that never had a
        # candidate contributes nothing, because no pairing was refused.
        # Reversible until export, and `POST .../decisions` with
        # `"pending"` is the reversal, so this falls as the reviewer
        # undoes.
        "n_rejected_pairings": sum(
            1 for r in rows for c in r["candidates"] if c.get("rejected")
        ),
        # Item 61: receipts this month is using from the months either side
        # of it. Counted off the committed source map, so it is what the
        # month actually holds rather than what the pool offered; 0 on every
        # month whose neighbours lent it nothing.
        "n_adjacent_borrowed": sum(
            1 for e in borrow_sources.values()
            if isinstance(e, dict) and e.get("kind") == ADJACENT_BORROW_KIND
        ),
        # PR C — memory legibility.
        "n_learned_lines": n_learned_lines,
        # L4 — missing receipt images (0 when the source has no image info).
        "has_image_info": has_image_info,
        "n_missing_receipt_image": n_missing_receipt_image,
        # L1 — fill-color annotations from the statement workbook.
        "n_parse_notes": count_parse_issues(parse_errors)["notes"],
        "n_already_posted": sum(
            1 for t in transactions if t.entry_status == "posted"
        ),
        "n_subscription": sum(
            1 for t in transactions if t.entry_status == "subscription"
        ),
        # Item 76: rows whose current verdict the tool wrote under the
        # self-confirmation rule. Falls as a reviewer takes one back.
        "n_self_confirmed": sum(
            1 for r in rows if r.get("decided_by") == DECIDED_BY_TOOL
        ),
        # Item 101: how many rows "Confirm all matched" confirms right now,
        # from the function the route writes with.
        "n_confirm_matched": len(confirm_matched_pairs(
            rows, dict(autopick_pairs(outcome, decisions))
        )),
    }
    # Item 129: the last committed re-match and any owed one, off the
    # snapshot as stored, so the month page can say a re-match ran.
    visibility = rematch_visibility(run.snapshot)

    return {
        "run_id": run.run_id,
        "label": run.label,
        "created_at": run.created_at,
        # When the month last changed (2026-09-16); the SPA's "Last updated"
        # reads `updated_at ?? created_at`, so it printed the creation day.
        "updated_at": month_updated_at(run, decisions=decisions, edited_at=edited_at),
        # Item 129 (2026-09-18): when the month was last re-matched and
        # whether one is still owed, so the page prints it instead of
        # reading `/api/operator/state`. Null / null until a re-match commits
        # / while nothing is owed.
        "last_rematch": visibility["last_rematch"],
        "rematch_pending": visibility["rematch_pending"],
        # Item 100: the sign-off, on the page that shows the month. Who
        # published (the session's operator label), when, and whether the
        # completeness gate was overridden; null / false while unpublished.
        "published": run.published,
        "published_at": run.published_at if run.published else None,
        "published_by": run.published_by if run.published else None,
        "published_override": bool(run.published and run.published_override),
        "llm_enabled": run.llm_enabled,
        "has_coa": run.has_coa,
        "summary": summary,
        "rows": rows,
        "unmatched_receipts": unmatched_receipts,
        "unmatched_transactions": unmatched_transactions,
        "assignable_receipts": assignable_receipts,
        "copies_set_aside": copies_set_aside,
        "duplicate_charges": duplicate_charges,
        "duplicate_receipts": duplicate_receipts,
        "duplicate_groups": duplicate_groups,
        "category_options": list(EXPENSE_CATEGORIES),
        # The curated GL leaves this batch may post to, per entity,
        # served BESIDE the eight rather than replacing them: a
        # published SPA keeps rendering category_options until a
        # bundle that reads these is published. Absent entity = not
        # covered by the curated chart, which is not the same fact
        # as an entity with nothing to post to.
        "gl_accounts": gl_account_options(
            settings, (run.config or {}).get(GL_ENTITY_ORGS_KEY)),
        "gl_revision": gl_revision(),
        "category_vocabulary": category_vocabulary(run),
        "parse_errors": parse_errors,
        # Severity-tagged view of the same issues, so the UI can separate a
        # real error from an advisory note (2026-07-22). `parse_errors`
        # keeps its raw shape for any existing reader.
        "parse_issues": [
            {
                "file": i[0],
                "line": i[1],
                "message": i[2],
                "severity": parse_issue_severity(i),
            }
            for i in parse_errors
        ],
        # L3: xlsx statements can be written back with the resolved accounts.
        "writeback_available": writeback_available(run),
        # The uploads this month has taken (PR 2b-2b-2). Parallel field:
        # empty on every run that predates it, including reconciling ones.
        "statements": month_statements(run),
        # Per-card coverage (PR 3): which cards this month holds charges
        # for, which uploads covered them, over what span, and how far each
        # one has got. `statements[]` answers the file question; this
        # answers the card question, which is the one the work is organized
        # around. Parallel field, empty on a month with nothing loaded.
        "coverage": coverage,
        # Item 107: the month's missing-receipt list, grouped by card
        # holder, so the chase Criss runs by hand every month is a list the
        # tool hands her. Membership is `charge_needs_receipt`, read off the
        # rows above, so the groups' charges sum to
        # `summary.n_charges_need_receipt` and the two cannot disagree.
        # Empty on a month with nothing to chase.
        "receipt_chase": receipt_chase_groups(
            rows, run=run, transactions=transactions, coverage=coverage,
            settings=settings,
        ),
        # Bulk receipts-folder attach (2026-07-27): the last upload's summary
        # (n_ingested / n_matched_new / n_review_new / n_possible_duplicates /
        # llm_source / cost_usd / issues), or None when no folder was uploaded.
        # Stored on the snapshot by ingest_receipts_folder_into_run; surfaced
        # here so the SPA can show a post-upload report next to the new
        # suggestions instead of the reviewer guessing what landed.
        "folder_ingest": run.snapshot.get("folder_ingest"),
        # Whether this run has the category-vs-account adjudication signal
        # (Categorization.decision), which only exists on override-on +
        # chart-wired runs. False => a review.state of "ready" means "category
        # source is trusted", NOT "the account was verified against the chart";
        # the SPA must phrase Confirm-all honestly and not claim account
        # verification on a run that never adjudicated (adversarial-verify
        # finding, 2026-07-27).
        "adjudication_available": any(
            li.categorization is not None
            and getattr(li.categorization, "decision", None) in _ADJ_VERDICTS
            for r in rec_by_id.values()
            for li in r.line_items
        ),
    }


def _charge_cats(run: RunRow, overrides: dict, charge_ids) -> dict:
    """The receiptless-charge categorization side-map (Slice 10), rebuilt
    from the run snapshot keyed by transaction_id. Threaded into every
    regenerated export so web downloads carry the same receiptless-charge
    categories the workbench shows; `build_view` loads it the same way
    (see the `charge_cats` block there). Empty dict when the snapshot has
    none, so the writers behave exactly as before on receipt-only runs.

    Item 109: `overrides` + `charge_ids` (the snapshot outcome's
    `unmatched_transactions`) lay the reviewer's own charge categories over
    the guesses, so the CSV, the journal, the workbook and the report carry
    what she set, not what the model guessed."""
    return apply_charge_category_overrides(
        {
            tx_id: categorization_from_dict(d)
            for tx_id, d in (run.snapshot.get("charge_categorizations") or {}).items()
        },
        overrides,
        charge_ids,
    )


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
        charge_categorizations=_charge_cats(
            run, overrides, outcome.unmatched_transactions
        ),
        dispositions=_dispositions(transactions, receipts, effective, decisions),
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
    # §16 export-approved gate: when the run's snapshotted policy requires
    # it, only reviewer-CONFIRMED matches export; a still-pending auto-match
    # is withheld from the journal (it stays visible in the report /
    # reconciled CSV). Default (absent / False) => the current behaviour,
    # where the writer's own posting policy is the only filter.
    if (run.config or {}).get("policy", {}).get("export_approved_only"):
        confirmed_ids = {
            tid for tid, d in decisions.items() if d.status == STATUS_CONFIRMED
        }
        effective = replace(
            effective,
            matches=[
                m for m in effective.matches if m.transaction_id in confirmed_ids
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
        charge_categorizations=_charge_cats(
            run, overrides, outcome.unmatched_transactions
        ),
        include_receiptless_learned=bool(
            (run.config or {}).get("zoho", {}).get("export_receiptless_learned")
        ),
        dispositions=_dispositions(transactions, receipts, effective, decisions),
        reimbursable_account=(run.config or {}).get("zoho", {}).get(
            "reimbursable_account"
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
        charge_categorizations=_charge_cats(
            run, overrides, outcome.unmatched_transactions
        ),
        dispositions=_dispositions(transactions, receipts, effective, decisions),
    )
    return out_path


def writeback_available(run: RunRow) -> bool:
    """True when the run's statement is an Excel workbook the L3 writeback
    can annotate (her own sheet + the resolved-account column)."""
    stmt = (run.config or {}).get("statement", {}).get("path", "")
    return Path(stmt).suffix.lower() in (".xlsx", ".xlsm")


def writeback_statement_name(
    run: RunRow, requested: str = "", statement_id: str = "",
) -> str | None:
    """Which statement file a writeback should annotate, or None.

    Default is the run's current `config.statement.path`, which is the last
    upload and the only one a single-statement month ever had. `requested`
    names a different one, and is resolved ONLY against this run's recorded
    `statements[]`: the parameter reaches the writeback route from a query
    string, and a name that is merely sanitized would still let a caller
    address any file in the work dir. Matching an entry is the check.

    `statement_id` (note item T2) addresses an upload by its content id
    instead, for the month where two per-card exports share a filename;
    resolved against `statements[].statement_id` the same way, first entry
    wins, and an id the month never recorded is None (a 404 at the route).
    When both are given the id decides, since it is the more specific name.
    """
    statement_id = (statement_id or "").strip()
    if statement_id:
        entry = statement_entry_by_id(run, statement_id)
        if entry is None:
            return None
        return str(entry.get("file") or "") or None
    requested = (requested or "").strip()
    if not requested:
        stmt = (run.config or {}).get("statement", {}).get("path", "")
        return stmt or None
    for entry in month_statements(run):
        if entry.get("file") == requested:
            return requested
    return None


def regenerate_writeback(
    run: RunRow,
    decisions: dict[str, Decision],
    overrides: dict,
    statement_file: str = "",
    statement_id: str = "",
) -> Path | None:
    """Write the L3 sheet writeback for a run: HER OWN uploaded workbook
    with one new "Zoho Account (tool)" column, after the reviewer's
    decisions + overrides. Returns None when the statement is not an
    Excel workbook (CSV / PDF runs have no sheet to write back into).

    A month can hold several statements now, so this writes ONE of them:
    `statement_file` when given, the run's current statement otherwise, and
    exactly the charges THAT file contains, each at the row it occupies
    there (`statement_anchors`). Writing every charge into whichever workbook
    happened to be current is the wrong-cell bug this scoping exists to
    prevent, and scoping on the charge's own first-read row instead would
    leave the closing cycle blank wherever the partial got there first.
    """
    from ..output.sheet_writeback import write_sheet_writeback

    name = writeback_statement_name(run, statement_file, statement_id)
    if name is None or Path(name).suffix.lower() not in (".xlsx", ".xlsm"):
        return None

    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    receipts = apply_overrides(receipts, overrides)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    stmt_cfg = run.config.get("statement", {})
    # The sheet this workbook was read from. `config.statement` describes the
    # LATEST upload only, so an earlier statement takes its own recorded
    # sheet name and falls back to the config's just for the runs that
    # predate `statements[]` and have exactly one statement anyway.
    sheet_name = stmt_cfg.get("sheet_name")
    for entry in month_statements(run):
        if entry.get("file") == name:
            sheet_name = entry.get("sheet_name")
            break
    stmt_path = Path(run.work_dir) / name
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
        sheet_name=sheet_name,
        chart_of_accounts=chart,
        charge_categorizations=_charge_cats(
            run, overrides, outcome.unmatched_transactions
        ),
        anchors=statement_anchors(run, name),
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


def registry_upserts_from_expense_run(
    merchants: dict,
    *,
    receipts: list[Receipt],
    effective_receipts: list[Receipt],
    field_overrides: dict[str, dict[str, str]],
    category_overrides: dict,
) -> tuple[dict, dict]:
    """Fold reviewer vendor / category corrections into a COPY of the merchants
    registry (2026-07-29, the self-improving half). Returns
    `(new_merchants, summary)`.

    - A VENDOR edit teaches canonicalization: the CHOSEN (edited) name is the
      canonical merchant; the ORIGINAL extracted string becomes one of its
      aliases (so next month's identical OCR output resolves to the canonical).
    - A CATEGORY reclassification teaches the merchant default: the chosen
      category (+ account) is set on the receipt's canonical merchant. The
      merchant is the edited vendor if one was given, else the registry
      canonical, else the effective vendor. A merchant whose category edits
      disagree across its lines is skipped (mirrors Phase-6 `_learn_categories`).

    Only explicit edits teach; the batch default and untouched OCR values do
    not. Pure: it never touches the store, so it is unit-testable and the
    caller decides whether to persist the changed map.

    Item 116 (2026-09-17): every entry is carried WHOLE. Only a merchant an
    edit actually changed is rewritten, and only its aliases / category /
    account move; `multi_category`, `cost_center` and any other key stay as
    stored. A run whose edits change nothing returns a map equal to the one
    passed in, so the caller writes nothing, and the counts name exactly the
    changes the returned map carries (a re-affirmed category is not counted)."""
    orig_by_id = {r.document_id: r for r in receipts}
    eff_by_id = {r.document_id: r for r in effective_receipts}
    base: dict = merchants or {}
    # Merchants an edit reached, each a deep copy of its WHOLE stored entry
    # (or a fresh entry for a new canonical name). Untouched entries are never
    # copied into this, so nothing can strip them.
    work: dict[str, dict] = {}
    aliases_added: dict[str, int] = {}
    category_changed: set[str] = set()

    def _ensure(canonical: str) -> dict:
        entry = work.get(canonical)
        if entry is None:
            prior = base.get(canonical)
            entry = (
                copy.deepcopy(prior)
                if isinstance(prior, dict)
                else {"aliases": [], "category": None, "zoho_account": None}
            )
            entry["aliases"] = list(entry.get("aliases") or [])
            work[canonical] = entry
        return entry

    n_skipped = 0
    n_account_skipped = 0

    # 1) Vendor edits -> canonical + alias.
    for document_id, fields in (field_overrides or {}).items():
        canonical = str((fields or {}).get("vendor") or "").strip()
        if not canonical:
            continue
        orig = orig_by_id.get(document_id)
        raw = (orig.detected_vendor if orig else None) or ""
        raw = raw.strip()
        if not raw or normalize_vendor(raw) == normalize_vendor(canonical):
            continue  # nothing to alias (renamed to itself / no original)
        entry = _ensure(canonical)
        have = {normalize_vendor(a) for a in entry["aliases"]}
        if normalize_vendor(raw) not in have:
            entry["aliases"].append(raw)
            aliases_added[canonical] = aliases_added.get(canonical, 0) + 1

    # 2) Category reclassifications -> merchant default (conflict-skipped).
    pending: dict[str, dict] = {}
    for (document_id, _line), ov in (category_overrides or {}).items():
        category = (ov or {}).get("category")
        if not category:
            continue
        eff = eff_by_id.get(document_id)
        if eff is None:
            continue
        canonical = (
            str((field_overrides or {}).get(document_id, {}).get("vendor") or "").strip()
            or eff.canonical_vendor
            or eff.detected_vendor
            or ""
        ).strip()
        if not canonical:
            continue
        prior = pending.get(canonical)
        account = (ov or {}).get("zoho_account")
        if prior is None:
            pending[canonical] = {
                "category": category,
                "zoho_account": account,
                "conflict": False,
                "account_conflict": False,
            }
            continue
        if prior["category"] != category:
            prior["conflict"] = True
        # Item 183: two rows agreeing on the category and naming DIFFERENT
        # accounts used to agree. The per-row `cell` was discarded from the
        # second row on, so only the first account ever survived and the
        # disagreement was invisible. Under a design where the account IS
        # the answer rather than a detail hanging off the category, that is
        # a nearest-plausible default sitting inside the writer of durable
        # memory, which later runs consult ahead of the model.
        #
        # Absence is not disagreement. A row that names no account is
        # silent, not a second opinion, so the first account NAMED wins over
        # rows that name none; only two rows naming different accounts
        # conflict.
        if account:
            if not prior["zoho_account"]:
                prior["zoho_account"] = account
            elif account != prior["zoho_account"]:
                prior["account_conflict"] = True

    for canonical, val in pending.items():
        if val["conflict"]:
            n_skipped += 1
            continue
        if val["account_conflict"]:
            # Item 183: the rows agree on the category and disagree on where
            # the money posts. Teach nothing for this merchant rather than
            # letting the first row's account win, and leave whatever is
            # already stored exactly where it is: the registry carries no
            # provenance on `zoho_account` (unlike `card_key_learned`), so a
            # clear here could not tell a value Dirk typed on the Settings
            # screen from one a run learned. The count is what keeps that
            # choice from being silent.
            n_account_skipped += 1
            continue
        entry = _ensure(canonical)
        before = (entry.get("category"), entry.get("zoho_account"))
        entry["category"] = val["category"]
        if val["zoho_account"]:
            entry["zoho_account"] = val["zoho_account"]
        if (entry["category"], entry.get("zoho_account")) != before:
            category_changed.add(canonical)

    # Fold only the merchants that actually changed back into a copy of the
    # stored map, validating each one (dedup aliases, confirm the category)
    # and laying the cleaned aliases / category / account over the WHOLE
    # entry. Fail-open per merchant: a malformed entry keeps its stored form
    # and is not counted.
    new_merchants = copy.deepcopy(base)
    n_alias = n_category = 0
    for canonical, entry in work.items():
        n_new_aliases = aliases_added.get(canonical, 0)
        changed_category = canonical in category_changed
        if not n_new_aliases and not changed_category:
            continue
        try:
            cleaned = normalize_merchants_setting({canonical: entry}).get(canonical)
        except ValueError:
            continue
        if cleaned is None:
            continue
        new_merchants[canonical] = {**entry, **cleaned}
        n_alias += n_new_aliases
        n_category += int(changed_category)
    summary = {
        "aliases_added": n_alias,
        "categories_set": n_category,
        "skipped_conflict": n_skipped,
        "skipped_account_conflict": n_account_skipped,
    }
    return new_merchants, summary


# Note item M2 (2026-09-18): the card sources that count as an OBSERVATION of
# where a merchant's spend actually lands. `merchant` is deliberately absent —
# a card the registry itself lent must never teach itself back — and so is
# `none`. `learned` is in: a card remembered per receipt is still a card the
# tool resolved for this merchant this month.
_CARD_OBSERVATION_SOURCES = frozenset({"override", "hint", "settled_charge", "learned"})


def registry_card_upserts_from_expense_run(
    merchants: dict,
    *,
    effective_receipts: "list[Receipt]",
    card_res: dict[str, dict],
) -> tuple[dict, dict]:
    """Fold the month's resolved cards into a COPY of the merchants registry
    (note item M2, the card half of the self-improving registry). Returns
    `(new_merchants, summary)`.

    A merchant's spend is often exclusively on one card: measured over live
    July, August and September 2026, 34 of the 60 merchants that carry a card
    at all were seen on exactly one, and 5 (the three AI vendors and the two
    spellings around them) on several. So the tool keeps the evidence rather
    than a guess:

    * ``cards_seen`` accumulates every card this merchant's receipts resolved
      to, across months. It is the machine's record and grows monotonically.
    * ``card_key`` is written by this learner ONLY while ``cards_seen`` holds
      exactly one card and the entry has no key yet, and is marked
      ``card_key_learned``. A second card drops the learned key in the same
      pass — two cards mean the tool cannot say which one paid, and saying
      nothing is the correct answer.
    * A key an editor typed carries no ``card_key_learned`` mark and is NEVER
      touched, whatever the observations say. The person outranks the record.

    Pure: it never touches the store, so the caller decides whether to
    persist. Every entry is carried WHOLE (item 116's rule): only a merchant
    an observation actually changed is rewritten, and only its card fields
    move.
    """
    from ..merchant_registry import MerchantRegistry

    base: dict = merchants or {}
    empty = {"cards_seen": 0, "card_keys_learned": 0, "card_keys_dropped": 0}
    registry = MerchantRegistry.from_settings({"merchants": base})
    if not registry:
        return base, empty

    seen: dict[str, set[str]] = {}
    for r in effective_receipts:
        res = card_res.get(r.document_id) or {}
        card = res.get("card")
        if card is None or res.get("card_source") not in _CARD_OBSERVATION_SOURCES:
            continue
        match = registry.resolve(r.vendor_clean, r.detected_vendor)
        if match is None:
            continue
        key = str(getattr(card, "key", "") or "").strip()
        if key:
            seen.setdefault(match.canonical_name, set()).add(key)
    if not seen:
        return base, empty

    new_merchants = copy.deepcopy(base)
    n_seen = n_learned = n_dropped = 0
    for canonical, observed in seen.items():
        stored_entry = new_merchants.get(canonical)
        if not isinstance(stored_entry, dict):
            continue
        entry = copy.deepcopy(stored_entry)
        was = {
            str(c or "").strip()
            for c in (entry.get("cards_seen") or [])
            if str(c or "").strip()
        }
        union = sorted(was | observed)
        if set(union) != was:
            entry["cards_seen"] = union
            n_seen += 1
        typed_key = str(entry.get("card_key") or "").strip()
        machine_key = bool(entry.get("card_key_learned")) and bool(typed_key)
        if len(union) == 1 and not typed_key:
            entry["card_key"] = union[0]
            entry["card_key_learned"] = True
            n_learned += 1
        elif len(union) > 1 and machine_key:
            entry.pop("card_key", None)
            entry.pop("card_key_learned", None)
            n_dropped += 1
        if entry == stored_entry:
            continue
        try:
            cleaned = normalize_merchants_setting({canonical: entry}).get(canonical)
        except ValueError:
            continue
        if cleaned is None:
            continue
        # The cleaned entry is authoritative about the card fields, including
        # their ABSENCE: a dropped learned key must not survive in `entry`.
        merged = {**entry, **cleaned}
        for k in ("card_key", "card_key_learned", "cards_seen"):
            if k not in cleaned:
                merged.pop(k, None)
        new_merchants[canonical] = merged
    return new_merchants, {
        "cards_seen": n_seen,
        "card_keys_learned": n_learned,
        "card_keys_dropped": n_dropped,
    }


def registry_cost_center_upserts_from_expense_run(
    merchants: dict,
    *,
    effective_receipts: "list[Receipt]",
    field_overrides: dict[str, dict[str, str]],
    cost_centers: dict | None,
) -> tuple[dict, dict]:
    """Fold the month's explicit cost-center picks into a COPY of the
    merchants registry (backlog item 118, the missing half of item 47's D2
    step 3). Returns `(new_merchants, summary)`.

    Item 47 designed a learned merchant -> cost centre and the build shipped
    only the carrier: `merchants[].cost_center` resolved a row, and nothing
    ever wrote it, so every vendor had to be typed by hand in Settings once
    and for all. A reviewer picking a centre on a row is the same kind of
    explicit human decision a category reclassification is, and it teaches
    the same way:

    * only an EXPLICIT per-row override teaches; a centre the row merely
      inherited from the trip, the card or the merchant entry is the tool's
      own answer coming back and teaches nothing;
    * a merchant whose picks disagree across the month is SKIPPED, exactly as
      the category pass skips one (a vendor split across two projects is a
      fact about the vendor, not a conflict to resolve by guessing);
    * only a name Dirk has already DEFINED and left active is written. Item
      47 D1 is explicit that the tool never invents a cost centre and never
      learns a new NAME, and the field is free text on the row, so this is
      the guard that keeps a typo out of the registry. An empty or absent
      cost-centre registry therefore learns nothing at all, which is the same
      empty-registry contract the resolver and the review state already keep.

    Pure: it never touches the store, so the caller decides whether to
    persist. Every entry is carried WHOLE (item 116's rule): only a merchant
    a pick actually changed is rewritten, and only its `cost_center` moves.
    """
    from ..merchant_registry import MerchantRegistry

    base: dict = merchants or {}
    empty = {"cost_centers_set": 0, "cost_centers_skipped_conflict": 0}
    defined = {
        str(name).strip(): entry
        for name, entry in (cost_centers or {}).items()
        if str(name or "").strip() and isinstance(entry, dict)
    }
    active = {
        name for name, entry in defined.items()
        if entry.get("active", True)
    }
    if not active:
        return base, empty
    registry = MerchantRegistry.from_settings({"merchants": base})
    if not registry:
        return base, empty

    # merchant -> the picked centre, or None once two picks disagree.
    picked: dict[str, str | None] = {}
    by_id = {r.document_id: r for r in effective_receipts}
    for document_id, fields in (field_overrides or {}).items():
        name = str((fields or {}).get("cost_center") or "").strip()
        if not name or name not in active:
            continue
        receipt = by_id.get(document_id)
        if receipt is None:
            continue
        match = registry.resolve(receipt.vendor_clean, receipt.detected_vendor)
        if match is None:
            continue
        canonical = match.canonical_name
        if canonical not in picked:
            picked[canonical] = name
        elif picked[canonical] != name:
            picked[canonical] = None
    if not picked:
        return base, empty

    new_merchants = copy.deepcopy(base)
    n_set = n_conflict = 0
    for canonical, name in sorted(picked.items()):
        if name is None:
            n_conflict += 1
            continue
        stored_entry = new_merchants.get(canonical)
        if not isinstance(stored_entry, dict):
            continue
        if str(stored_entry.get("cost_center") or "").strip() == name:
            continue
        entry = copy.deepcopy(stored_entry)
        entry["cost_center"] = name
        try:
            cleaned = normalize_merchants_setting({canonical: entry}).get(canonical)
        except ValueError:
            continue
        if cleaned is None:
            continue
        new_merchants[canonical] = {**entry, **cleaned}
        n_set += 1
    return new_merchants, {
        "cost_centers_set": n_set,
        "cost_centers_skipped_conflict": n_conflict,
    }


def commit_to_memory(
    run: RunRow,
    decisions: dict[str, Decision],
    overrides: dict,
    learning_db_path: Path,
    now_iso: str,
    *,
    field_overrides: dict[str, dict[str, str]] | None = None,
    edits: list[dict] | None = None,
    settings_store=None,
    store_factory=None,
    persist: bool = True,
) -> dict:
    """Harvest this run's confirmed decisions into the durable learning
    store (Phase 2 capture). This is the explicit finalize gate: only
    confirmed matches (alias + FX) and explicit category reclassifications
    (merchant -> category) teach; a half-reviewed run teaches nothing
    wrong. Returns a summary of what was written.

    An expense batch (Phase 6) branches to `learn_from_expense_run`: entity
    overrides teach merchant -> entity, header edits teach per-merchant
    field corrections (keyed on the ORIGINAL extracted vendor), category
    reclassifications teach merchant -> category. `field_overrides` /
    `edits` are the expense-mode overlays; ignored in statement mode.

    Item 163 (feedback note #81): `store_factory` and `persist` are the one
    seam a DRY RUN needs. `plan_month_memory` passes
    `learning.RecordingStore`, which accepts the same `record_*` calls and
    keeps them instead of writing, and `persist=False`, which computes the
    registry half without saving it and returns the map it would have saved
    as `merchants_after`. So the preview and the save are the same code
    reading the same inputs, rather than two implementations kept in step
    by hand."""
    store_factory = store_factory or LearningStore
    if run_mode(run) == MODE_EXPENSE_GENERATION:
        # The baseline, because this path keys what it learns on the ORIGINAL
        # extracted vendor: harvesting a baked pool would teach the
        # correction against the corrected name and learn nothing.
        receipts = baseline_receipts(run)
        default_entity = (
            ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
        )
        edits = edits or []
        effective = apply_expense_edits(
            receipts, field_overrides or {}, edits,
            category_overrides=overrides, default_entity=default_entity,
        )
        manual_payloads = {
            e["document_id"]: e["payload"] for e in edits if e["op"] == "add"
        }
        with store_factory(learning_db_path) as store:
            summary = learn_from_expense_run(
                store,
                receipts=receipts,
                effective_receipts=effective,
                field_overrides=field_overrides or {},
                category_overrides=overrides,
                manual_payloads=manual_payloads,
                # Item 109: the month's charges, so a category she set on a
                # receiptless charge is taught under the bank's description.
                # Empty until a statement is attached, which is exactly when
                # there is no charge to have edited.
                transactions=[
                    transaction_from_dict(t)
                    for t in (run.snapshot or {}).get("transactions") or []
                ],
                source_run=run.run_id,
                now_iso=now_iso,
            )
            # Item 115: a receipt-first month with a statement also RECONCILES,
            # and its confirmed pairs are the only proof of which truncated
            # bank description belongs to which receipt, and of what a
            # merchant's card actually converted at. Only the statement-mode
            # branch below taught those, and no live month goes through it, so
            # the store held 0 aliases and 0 FX rates while the contract
            # promised both. Same inputs the matcher itself read: the
            # snapshot's charges and baked receipt pool, the decisions applied,
            # and only pairs a verdict confirmed.
            pairs = alias = fx = 0
            if has_statement(run):
                txs, pool, pool_outcome, _ = snapshot_from_dict(run.snapshot)
                pool = pool + borrowed_receipts(run)
                pairs, alias, fx = learn_confirmed_pairs(
                    store,
                    transactions=txs,
                    receipts=pool,
                    outcome=apply_decisions(pool_outcome, txs, pool, decisions),
                    confirmed_tx_ids=reviewer_confirmed_tx_ids(decisions),
                    source_run=run.run_id,
                    now_iso=now_iso,
                )
        result = summary.as_dict()
        result["confirmed_pairs"] = pairs
        result["vendor_aliases"] = alias
        result["merchant_fx"] = fx
        # Self-improving registry (2026-07-29): the same explicit vendor /
        # category edits also upsert the canonical merchant registry, so the
        # human-editable, seeded registry grows from corrections. Persist only
        # when the map actually changed; skip silently without a settings store.
        if settings_store is not None:
            settings = settings_store.get_settings()
            new_merchants, reg_summary = registry_upserts_from_expense_run(
                settings.get("merchants") or {},
                receipts=receipts,
                effective_receipts=effective,
                field_overrides=field_overrides or {},
                category_overrides=overrides,
            )
            # Note item M2: and the month's resolved cards per merchant.
            # Resolved WITHOUT the registry on purpose — a card the registry
            # lent this month is not evidence about the merchant, and feeding
            # it back would let one observation harden into a fact.
            # Item 171: WITH the statement's own answer, though. A receipt a
            # charge of this month settles was paid by that charge's card,
            # and the bank naming it is the hardest evidence this tool ever
            # gets about which plastic a merchant is on.
            # `_CARD_OBSERVATION_SOURCES` has listed `settled_charge` since
            # item 111, but this resolution was the one caller that never
            # passed `settled_cards`, so the branch was unreachable and the
            # learner could not see it. Empty for a month with no statement,
            # which is every month before its first one.
            #
            # The map is the EFFECTIVE reconciled bucket, not the narrower
            # set of pairs the reviewer confirmed by hand, and that is
            # deliberate. Measured over the live months 2026-09-24: confining
            # it to confirmed pairs leaves August teaching `Anthropic -> 3645`
            # and July teaching nothing, so Anthropic would enter `cards_seen`
            # as a SINGLE-card merchant -- the exact false singleton item 173
            # gates against, on one of the three vendors item 154 forbids
            # guessing. The full bucket sees Anthropic on both cards and the
            # upsert then refuses to pin either, which is the safe direction.
            # Under-observing this learner invents facts; over-observing it
            # only makes it say nothing. A reconciled pair is also exactly as
            # trustworthy as what already ships: it is the pairing the grid
            # shows, the CSV exports and the month report prints.
            #
            # No item-173 vouch is needed on this side. The upsert already
            # IS that rule for the write direction: `cards_seen` accumulates,
            # `card_key` is written only while it holds exactly one card, and
            # a second card drops a learned key in the same pass.
            new_merchants, card_summary = registry_card_upserts_from_expense_run(
                new_merchants,
                effective_receipts=effective,
                card_res=resolve_batch_row_cards(
                    effective, run.config, field_overrides or {},
                    settled_cards=export_settled_cards(run, decisions),
                ),
            )
            reg_summary.update(card_summary)
            # Item 118: and the month's explicit cost-center picks, so the
            # centre Dirk defines is typed once per vendor instead of once
            # per receipt. Only a name he has defined and left active is
            # learned, so an empty cost-center registry teaches nothing.
            new_merchants, cc_summary = registry_cost_center_upserts_from_expense_run(
                new_merchants,
                effective_receipts=effective,
                field_overrides=field_overrides or {},
                cost_centers=settings.get("cost_centers") or {},
            )
            reg_summary.update(cc_summary)
            if persist:
                if new_merchants != (settings.get("merchants") or {}):
                    settings_store.set_settings({"merchants": new_merchants}, now_iso)
            else:
                # Item 163: the dry run hands the map back instead of
                # storing it, so the caller can diff it against the live one
                # and show which merchants a save would change.
                result["merchants_after"] = new_merchants
            result["registry"] = reg_summary
        return result

    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    confirmed_tx_ids = reviewer_confirmed_tx_ids(decisions)
    with store_factory(learning_db_path) as store:
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


def build_memory_view(
    learning_db_path: Path | None, unvalidated_only: bool = False,
    merchants: dict | None = None,
) -> dict:
    """Render model for the /memory page: everything the tool has learned,
    grouped by table. Read-only; an absent store yields an empty view.
    ``unvalidated_only`` filters the categories table to rows no human has
    validated yet (the review-the-103 workflow).

    ``merchants`` (note item M1, 2026-09-18) is `settings["merchants"]`.
    With it, `by_vendor[]` groups the category rules per vendor with one
    line per company, and names the registry merchant the vendor resolves
    to and the category its receipts will actually read (the registry's
    default when it has one, else "" for judged-per-receipt), so a reader
    sees where one merchant's account splits by company. Built from the
    same rows as `categories[]`, so the `unvalidated` filter applies to
    both. Each vendor line also carries the merchant's `profile` (note item
    M4), the free prose the categorizer reads as context for its receipts."""
    empty = {
        "categories": [], "aliases": [], "fx": [],
        "entities": [], "field_corrections": [],
        "by_vendor": [],
        "counts": {
            "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
            "merchant_entity": 0, "field_correction": 0,
        },
        "total": 0,
    }
    if learning_db_path is None or not Path(learning_db_path).exists():
        return empty

    with LearningStore(learning_db_path) as s:
        cats = s.all_merchant_categories()
        aliases = s.get_vendor_aliases()
        fx = s.all_merchant_fx()
        entities = s.all_merchant_entities()
        corrections = s.all_field_corrections()
        counts = s.count_rows()

    if unvalidated_only:
        cats = [c for c in cats if not c.validated_at]
    categories = [
        {
            "entity": c.legal_entity_id, "vendor": c.vendor_norm,
            "category": c.category or "", "zoho_account": c.zoho_account or "",
            "count": c.decision_count, "last": (c.last_confirmed_at or "")[:10],
            "validated": (c.validated_at or "")[:10],
            "validated_by": c.validated_by or "",
            # Note item M1: a row seeded from Zoho Books posting history,
            # not a person's decision (until someone validates it).
            "seeded": (c.source_run or "").startswith(ZOHO_SEED_PREFIX),
        }
        for c in cats
    ]
    # Note item M1: the same rows, per vendor, one line per company. The
    # registry is consulted for the vendor line so the page can say what a
    # receipt of this vendor will READ: the registry default when the
    # merchant has one (the company lines then carry the account), else
    # "" (no default; the company's own rule or the model decides).
    registry = MerchantRegistry(merchants) if merchants else None
    grouped: dict[str, list[dict]] = {}
    for row in categories:
        grouped.setdefault(row["vendor"], []).append(row)
    by_vendor = []
    for vendor_norm in sorted(grouped):
        hit = registry.resolve(None, vendor_norm) if registry else None
        by_vendor.append({
            "vendor": vendor_norm,
            "merchant": hit.canonical_name if hit else "",
            "category": (hit.category or "") if hit else "",
            "multi_category": bool(hit and hit.multi_category),
            # Note item M4: the merchant's free-prose profile, so the page
            # shows the background the categorizer is actually reading for
            # this vendor. "" when the merchant has none, or when the vendor
            # resolves to no merchant at all.
            "profile": (hit.profile or "") if hit else "",
            "companies": sorted(
                (
                    {k: v for k, v in row.items() if k != "vendor"}
                    for row in grouped[vendor_norm]
                ),
                key=lambda r: r["entity"],
            ),
        })
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
    # Receipt-first memory (Phase 6): merchant -> entity mappings and
    # per-merchant field corrections, so the /memory screen shows what
    # will auto-fill next batch and "forget" can target it.
    entity_rows = [
        {
            "vendor": e.vendor_norm, "entity": e.legal_entity_id,
            "count": e.decision_count, "last": (e.last_confirmed_at or "")[:10],
        }
        for e in entities
    ]
    correction_rows = [
        {
            "entity": c.legal_entity_id, "vendor": c.vendor_norm,
            "field": c.field, "value": c.value or "",
            "count": c.decision_count, "last": (c.last_confirmed_at or "")[:10],
        }
        for c in corrections
    ]
    return {
        "categories": categories, "aliases": alias_rows, "fx": fx_rows,
        "entities": entity_rows, "field_corrections": correction_rows,
        "by_vendor": by_vendor,
        "counts": counts, "total": sum(counts.values()),
    }


def forget_memory_vendor(
    learning_db_path: Path | None, legal_entity_id: str, vendor: str
) -> dict:
    """Drop everything learned for one merchant in one entity. Returns the
    per-table delete counts (zero everywhere when nothing matched)."""
    zero = {
        "merchant_category": 0, "vendor_alias": 0, "merchant_fx": 0,
        "merchant_entity": 0, "field_correction": 0,
    }
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


# --------------------------------------------------------------------------
# Receipt-first expense mode (Phase 4, behind EXPENSE_RECON_RECEIPT_FIRST)
#
# The statement-free sibling of the run pipeline above: an expense BATCH is
# a run whose config carries `mode: expense_generation`, whose snapshot has
# `transactions=[]` and every receipt in `unmatched_receipts` (the shape
# `cli.generate_expenses` returns), and whose review surface is a
# receipt-spine grid (`build_expense_view`) instead of the transaction-spine
# workbench (`build_view`, NOT modified). Reviewer edits overlay at
# render/export time exactly like decisions do in statement mode:
# header-field edits in `expense_field_overrides`, whole-expense add/delete
# in `expense_edits`, line-level category reclassification in the existing
# `category_overrides`.
# --------------------------------------------------------------------------

MODE_EXPENSE_GENERATION = "expense_generation"


def run_mode(run: RunRow) -> str:
    """The run's pipeline mode, from its stored config. Statement runs
    predate the marker, so an absent key reads as reconciliation."""
    return (run.config or {}).get("mode") or "reconciliation"


# The two batch functions (item 38, owner directive 2026-09-06): overall
# monthly company expenses, and trips. The type is DECLARED at creation
# and never inferred from content; an absent marker reads as a company
# month because every batch that predates the split is one.
BATCH_TYPE_COMPANY = "company-month"
BATCH_TYPE_TRIP = "trip"
VALID_BATCH_TYPES = (BATCH_TYPE_COMPANY, BATCH_TYPE_TRIP)


def batch_type(run: RunRow) -> str:
    """The batch's declared kind: ``company-month`` or ``trip``."""
    return (run.config or {}).get("batch_type") or BATCH_TYPE_COMPANY


def is_trip_batch(run: RunRow) -> bool:
    return batch_type(run) == BATCH_TYPE_TRIP


# ---------------------------------------------------------------- trips --
# The trip entity (item 38): named, date-ranged, VARIABLE roster of
# travelers. Created empty (a name and a roster only a human knows, so a
# trip can never be auto-created); its expense batch materializes when
# the first receipt joins it.

MAX_TRIP_TRAVELERS = 50


def validate_trip_fields(payload: dict) -> tuple[dict | None, str | None]:
    """Clean a trip create/update payload. Returns (cleaned, None) or
    (None, error). ``travelers`` is a list of PERSON names (item 40's
    vocabulary), whole-list replace, may be empty while the roster is
    still being collected.

    ``cost_center`` (item 47) is the trip's project or purpose, stored as
    typed and NOT checked against the cost-center registry: trips and
    cost centers are edited independently, so the edit ORDER must not
    matter. Blank is a normal state and clears it."""
    if not isinstance(payload, dict):
        return None, Refusal("body must be an object", code="invalid_body")
    name = str(payload.get("name") or "").strip()[:200]
    if not name:
        return None, Refusal("name is required", code="trip_name_required")
    start_raw = str(payload.get("start") or "").strip()
    end_raw = str(payload.get("end") or "").strip()
    try:
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
    except ValueError:
        return None, Refusal(
            "start and end must be YYYY-MM-DD dates",
            code="trip_dates_invalid",
        )
    if end < start:
        return None, Refusal(
            "end must not be before start", code="trip_dates_reversed"
        )
    travelers_raw = payload.get("travelers", [])
    if travelers_raw is None:
        travelers_raw = []
    if not isinstance(travelers_raw, list) or not all(
        isinstance(t, str) for t in travelers_raw
    ):
        return None, Refusal(
            "travelers must be a list of names", code="travelers_invalid"
        )
    travelers = list(dict.fromkeys(
        t.strip() for t in travelers_raw if t.strip()
    ))
    if len(travelers) > MAX_TRIP_TRAVELERS:
        return None, Refusal(
            f"travelers holds at most {MAX_TRIP_TRAVELERS} names",
            code="too_many_travelers",
            limit=MAX_TRIP_TRAVELERS,
        )
    return {
        "name": name,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "travelers": travelers,
        "cost_center": str(payload.get("cost_center") or "").strip()[:200],
    }, None


def find_trip_batch(store: RunStore, trip_id: str) -> RunRow | None:
    """The expense batch holding this trip's receipts, or None while no
    receipt has joined yet. The link lives on the BATCH
    (``config["trip_id"]``), so this scan is the one lookup."""
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if not is_trip_batch(run):
            continue
        if str((run.config or {}).get("trip_id") or "") == str(trip_id):
            return run
    return None


# One batch per trip is a fact only if creation is single-winner. A run
# row appears only when the OCR job COMMITS — minutes after the create
# was accepted — so a store scan alone is blind for the whole job
# duration (adversarial review 2026-09-06, finding 1): two uploads
# declaring the same trip, or an upload racing a join click, would each
# pass the "already has a batch" check and commit two batches, the older
# of which no list can reach. This in-process registry closes the
# window: a trip id is CLAIMED before its create starts and released
# when the job commits or dies. In-process is sufficient for the same
# reason the intake day-budget is: the app is one process, and a crash
# that loses the set also loses the uncommitted job it was tracking.
# Deleting the trip entity goes through the same lock, which closes the
# delete-during-create window (finding 2) as well.
_TRIP_BATCH_PENDING: set[str] = set()
_TRIP_BATCH_LOCK = threading.Lock()


def claim_trip_batch_slot(store: RunStore, trip_id: str) -> dict | None:
    """Reserve the right to create THE batch for this trip. Returns None
    on success (caller MUST release via `release_trip_batch_slot` when
    its create commits or fails), or an error body carrying ``code``
    (http status) — and ``batch_id`` when a batch already exists."""
    tid = str(trip_id)
    with _TRIP_BATCH_LOCK:
        if store.get_trip(tid) is None:
            return {"code": 404, "error": "trip not found",
                    "error_code": "trip_not_found"}
        if tid in _TRIP_BATCH_PENDING:
            return {"code": 409, "error": (
                "this trip's expense batch is being created right now; "
                "retry when that upload finishes"
            ), "error_code": "trip_batch_being_created"}
        existing = find_trip_batch(store, tid)
        if existing is not None:
            return {"code": 409, "error": (
                "this trip already has an expense batch; add receipts "
                "to it instead"
            ), "error_code": "trip_batch_exists", "batch_id": existing.run_id}
        _TRIP_BATCH_PENDING.add(tid)
    return None


def release_trip_batch_slot(trip_id: str) -> None:
    with _TRIP_BATCH_LOCK:
        _TRIP_BATCH_PENDING.discard(str(trip_id))


def delete_trip_entity(store: RunStore, trip_id: str) -> dict | None:
    """Delete a trip entity, refusing while a batch exists OR one is
    mid-creation. Runs entirely under the trip-batch lock, so a claim
    and a delete serialize: whichever wins, the other sees it. Returns
    None on success or an error body carrying ``code`` (http status)."""
    tid = str(trip_id)
    with _TRIP_BATCH_LOCK:
        if store.get_trip(tid) is None:
            return {"code": 404, "error": "Trip not found",
                    "error_code": "trip_not_found"}
        if tid in _TRIP_BATCH_PENDING:
            return {"code": 409, "error": (
                "this trip's expense batch is being created right now; "
                "retry when that upload finishes"
            ), "error_code": "trip_batch_being_created"}
        batch = find_trip_batch(store, tid)
        if batch is not None:
            return {"code": 409, "error": (
                "this trip still has an expense batch; delete the "
                "batch first"
            ), "error_code": "trip_has_batch", "batch_id": batch.run_id}
        store.delete_trip(tid)
    return None


def trip_view(store: RunStore, trip: TripRow, batch: RunRow | None) -> dict:
    """One row of the trips list. ``batch_id`` / ``summary`` are null until
    a receipt has joined (the batch materializes on first join); a null is
    the honest answer, never an empty fabricated summary."""
    return {
        "trip_id": trip.trip_id,
        "name": trip.name,
        "start": trip.start_date,
        "end": trip.end_date,
        "travelers": list(trip.travelers),
        # Item 47: parallel field, always present. A stale SPA reading
        # it gets "" rather than undefined.
        "cost_center": trip.cost_center,
        "created_at": trip.created_at,
        "updated_at": trip.updated_at,
        "batch_id": batch.run_id if batch is not None else None,
        "summary": (
            batch_list_summary(store, batch) if batch is not None else None
        ),
    }


def covering_trips(
    trips: list[TripRow], dates: list[str],
) -> list[TripRow]:
    """The trips whose inclusive date range contains at least one of the
    given ISO dates. Feeds the pool-row SUGGESTION (exactly one covering
    trip suggests; joining stays a click, never an inference)."""
    parsed: list[date] = []
    for raw in dates or []:
        try:
            parsed.append(date.fromisoformat(str(raw)[:10]))
        except ValueError:
            continue
    if not parsed:
        return []
    out: list[TripRow] = []
    for trip in trips:
        try:
            start = date.fromisoformat(trip.start_date)
            end = date.fromisoformat(trip.end_date)
        except ValueError:
            continue
        if any(start <= d <= end for d in parsed):
            out.append(trip)
    return out


# Header-level fields a reviewer may edit on one expense. `category` /
# `zoho_account` are deliberately NOT here: they are line-level and fold
# into the existing `category_overrides` path (the endpoint does that).
# `customer` is export-only passthrough (Zoho's Customer Name column);
# Receipt has no field for it, so it rides in the overrides map alone.
EXPENSE_HEADER_FIELDS = frozenset({
    "vendor", "date", "total", "currency", "tax", "tax_label",
    "paid_through", "legal_entity", "reference", "customer",
    # Item 41: the private-expense confirmation pair. Stored like any
    # other per-expense decision; the sugar route
    # POST .../expenses/{doc}/private sets both and enforces that a
    # confirmation names who gets reimbursed.
    "private", "reimburse_to",
    # Item 47: the cost-center override, the top of that chain. It
    # rides the existing field-override mechanism rather than a second
    # path, so it lands in `edited_fields` like every other override
    # and the export needs no new machinery. Blank clears it. Validated
    # against the registry in the route, which is where settings are
    # readable (`validate_expense_field` is pure by design).
    "cost_center",
    # Item 87: the card that paid this one expense, by registry key, for
    # a receipt whose printed payment method names no card or the wrong
    # one. Validated against the live registry in the route; publishing
    # the month remembers it for the vendor (item 88).
    "card_key",
})
EXPENSE_CATEGORY_FIELDS = frozenset({"category", "zoho_account"})


def validate_expense_field(field: str, value: str) -> str | None:
    """Validate one header-field edit at the edge, so stored overrides are
    always parseable. Returns an error string, or None when valid."""
    if field == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            return Refusal(
                "date must be YYYY-MM-DD", code="invalid_date", field="date"
            )
    elif field in ("total", "tax"):
        try:
            if not Decimal(value).is_finite():
                raise ValueError(value)
        except (ArithmeticError, ValueError):
            return Refusal(
                f"{field} must be a number", code="invalid_number", field=field
            )
    elif field == "currency":
        if not (len(value) == 3 and value.isalpha()):
            return Refusal(
                "currency must be a 3-letter code", code="invalid_currency"
            )
    elif field == "legal_entity":
        if not value.strip():
            return Refusal(
                "legal_entity cannot be blank", code="legal_entity_required"
            )
    elif field == "private":
        if value != "1":
            return Refusal(
                'private must be "1" (or empty to clear)',
                code="invalid_private_value",
            )
    return None


@dataclass
class PreparedExpenseBatch:
    """The fail-fast result of `create_expense_batch` (uploads validated and
    spooled, config built). `execute_expense_batch` consumes it to run the
    OCR + categorization pipeline in the background — the expense-mode twin
    of `PreparedRun` / `execute_run`."""

    run_id: str
    work_dir: Path
    cfg: dict
    label: str
    learned: object | None
    ai_unavailable: bool
    use_llm_effective: bool
    now_iso: str
    operator: str | None
    upload_issues: list[str]
    upload_issue_details: list[dict]
    # Phase 6: learned merchant->entity + field corrections, consulted by
    # generate_expenses only (never reconcile).
    expense_memory: object | None = None
    # Merchant registry (2026-07-29): canonical vendor + default category,
    # built from settings["merchants"]; also generate_expenses-only.
    registry: object | None = None
    # Item 39: "intake" when a mailed receipt materialized this batch
    # itself. Stored in the run summary; absent on operator-created batches.
    created_by: str = ""
    # Submitter provenance for mail-created batches (item 39's
    # auto-materialization AND R3's trip-join create-with-receipt), keyed
    # by the STORED receipt file name — the same shape
    # `add_receipts_to_expense_batch` writes, so the grid's submitted_by
    # chip works from the first render. None/empty => not mailed.
    intake_provenance: dict | None = None


def create_expense_batch(
    data_root: Path,
    *,
    files: "list[tuple[str, bytes]]",
    legal_entity: str,
    default_currency: str = "",
    label: str = "",
    now_iso: str,
    operator: str | None,
    learning_db_path: Path | None = None,
    settings: dict | None = None,
    created_by: str = "",
    batch_type: str = "",
    trip_id: str = "",
    provenance_by_digest: dict[str, dict] | None = None,
    allow_empty: bool = False,
) -> PreparedExpenseBatch:
    """Validate + spool an uploaded batch of receipts and build the
    expense-generation config. No statement, no run row yet — this is the
    decoupled upload step (POST /api/expense-batches), a top-level object of
    its own rather than an attachment to an existing run.

    `files` is [(filename, bytes)]; a `.zip` among them is expanded
    member-by-member (`_folder_receipt_files`). Invalid entries (wrong type,
    empty, oversized) become `upload_issues`, mirroring the folder-ingest
    tolerance; zero valid files raises `RunInputError`.

    `legal_entity` is OPTIONAL since Cards R3 (2026-08-21, owner ruling:
    the tool takes receipts from ANY entity): each receipt's entity
    resolves from its paying card (the registry snapshotted into the
    config below), the batch value is only a fallback, and an unresolved
    entity is a review state (`needs_entity`) that never blocks an export.

    `batch_type` (item 38) is the DECLARED kind: "" / "company-month"
    for a company month (the marker is stored only when declared, so an
    undeclared create produces the exact pre-split config), "trip" for a
    trip batch, which requires `trip_id` (the caller has verified the
    trip exists). `provenance_by_digest` (sha1[:16] -> person dict)
    carries mail provenance for a batch created FROM a mailed receipt.
    """
    if not files and not allow_empty:
        raise RunInputError(
            "No receipt files uploaded.", code="no_receipt_files"
        )
    if batch_type and batch_type not in VALID_BATCH_TYPES:
        raise RunInputError(
            f"batch_type must be one of {', '.join(VALID_BATCH_TYPES)}.",
            code="invalid_batch_type",
            allowed=sorted(VALID_BATCH_TYPES),
        )
    if batch_type == BATCH_TYPE_TRIP and not str(trip_id).strip():
        raise RunInputError(
            "A trip batch needs a trip_id.", code="trip_id_required"
        )

    run_id = uuid.uuid4().hex[:12]
    work_dir = data_root / "runs" / run_id
    receipts_dir = work_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    # Spool raw uploads, then re-walk them through the shared folder reader
    # so zips expand and validation matches the folder-ingest path exactly.
    staging = work_dir / "upload-staging"
    staging.mkdir(parents=True, exist_ok=True)
    for i, (name, data) in enumerate(files):
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name or "file").name) or "file"
        (staging / f"{i:04d}__{safe}").write_bytes(data or b"")

    issues: list[str] = []
    issue_details: list[dict] = []

    def _issue(code: str, file: str, **kw) -> None:
        prose, detail = upload_issue(code, file, **kw)
        issues.append(prose)
        issue_details.append(detail)

    seen_hashes: set[str] = set()
    intake_provenance: dict[str, dict] = {}
    n_saved = n_seen = 0
    for name, data in _folder_receipt_files(staging):
        n_seen += 1
        # Staged files carry the spool prefix; strip it for the stored name.
        display = re.sub(r"^\d{4}__", "", Path(name).name)
        if n_seen > FOLDER_MAX_FILES:
            _issue(UPLOAD_ISSUE_CAP, display, limit=FOLDER_MAX_FILES)
            break
        suffix = Path(display or "receipt").suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES:
            _issue(UPLOAD_ISSUE_UNSUPPORTED, display, suffix=suffix or None)
            continue
        if not data:
            _issue(UPLOAD_ISSUE_EMPTY, display)
            continue
        if len(data) > FOLDER_RECEIPT_MAX_BYTES:
            _issue(UPLOAD_ISSUE_TOO_LARGE, display, limit=FOLDER_RECEIPT_MAX_MB)
            continue
        digest = hashlib.sha1(data).hexdigest()[:16]
        if digest in seen_hashes:
            continue  # identical bytes twice in one upload
        seen_hashes.add(digest)
        fs_name = re.sub(r"[^A-Za-z0-9._-]", "_", display) or f"receipt{suffix}"
        dest_name = f"{n_saved:04d}__{fs_name}"
        (receipts_dir / dest_name).write_bytes(data)
        if provenance_by_digest and digest in provenance_by_digest:
            # Keyed by the STORED name, which is the document_id the
            # folder pipeline assigns — the same key the incremental add
            # path uses, so `submitted_by` renders identically.
            intake_provenance[dest_name] = provenance_by_digest[digest]
        n_saved += 1
    import shutil as _shutil

    _shutil.rmtree(staging, ignore_errors=True)

    if n_saved == 0 and not (allow_empty and not files):
        # `allow_empty` sanctions a deliberately RECEIPTLESS month (the
        # empty container a statement lands in; receipts arrive via mail
        # or the drop page). It never sanctions an upload whose every file
        # the validation rejected: that refusal is the floor the mail
        # materializer and the drop path both stand on — a month is never
        # created from files that could not be read.
        _shutil.rmtree(work_dir, ignore_errors=True)
        detail = f" ({issues[0]})" if issues else ""
        raise RunInputError(
            f"No readable receipt files uploaded.{detail}",
            code="no_readable_receipt_files",
        )

    # LLM: folder OCR has no keyword fallback, so without a key the batch
    # will fail honestly at execute time (ConfigError -> job error). The
    # cfg carries the llm block only when a key is present, mirroring
    # prepare_run's default-on policy.
    have_key = bool(os.environ.get("OPENAI_API_KEY"))
    use_llm_effective = _default_llm_on() and have_key

    cfg: dict = {
        "mode": MODE_EXPENSE_GENERATION,
        "expense": {"legal_entity_id": legal_entity.strip()},
        "receipts": {"path": "receipts", "source": "folder"},
    }
    # Item 38: the declared type, stored only when declared — an
    # undeclared create keeps the exact pre-split config shape, and an
    # absent marker reads as a company month everywhere.
    if batch_type:
        cfg["batch_type"] = batch_type
    if batch_type == BATCH_TYPE_TRIP:
        cfg["trip_id"] = str(trip_id).strip()
    if default_currency.strip():
        cfg["receipts"]["default_currency"] = default_currency.strip()
    # Phase 5: the entity registry's default Paid Through account rides in
    # the run config, so the export resolves it with no per-expense edit.
    entity_entry = entity_from_settings(settings, legal_entity)
    if entity_entry and entity_entry.get("default_paid_through"):
        cfg["expense"]["default_paid_through"] = str(
            entity_entry["default_paid_through"]
        )
    # The card-number -> Zoho account map rides in the run config too, so
    # the export resolves each receipt's Paid Through from the card it
    # prints, ahead of the entity default. Since 2026-08-21 it flattens
    # from the composed card registry (settings `cards` + legacy
    # `card_accounts`, `cards.effective_cards`) — with no settings cards
    # this reproduces the legacy map exactly. Snapshotted, so a run
    # reproduces its mapping (incl. the local no-API replay).
    from ..cards import cards_to_setting, effective_cards, legacy_card_accounts
    from ..cards_provision import load_cards

    composed = effective_cards(settings, load_cards())
    card_accts = legacy_card_accounts(composed)
    if card_accts:
        cfg["expense"]["card_accounts"] = card_accts
    # Cards R3: snapshot the COMPOSED card registry into the run config, so
    # per-receipt entity resolution reads a fixed, replayable state (the
    # same snapshot discipline as card_accounts). Settings edits reach an
    # existing batch only through the explicit refresh-master-data pass.
    if composed:
        cfg["expense"]["cards"] = cards_to_setting(composed)
    if use_llm_effective:
        cfg["llm"] = {"provider": "openai", "model": "gpt-4o-mini", "vision_model": VISION_MODEL}
    # Per-entity chart provisioning (the same gate a statement run gets):
    # the export validates posting accounts against the paying entity's
    # chart when the entity is provisioned (settings registry first, /data
    # file fallback); absent => unguarded, unchanged.
    cfg = apply_coa_provisioning(cfg, legal_entity.strip(), settings=settings)
    # Item 82: a company month carries the ECB monthly averages around its
    # own month from creation. A trip is matched inside the company months
    # that borrow it, against their rates, so it fetches nothing.
    if batch_type != BATCH_TYPE_TRIP:
        cfg = apply_ecb_rates(cfg, ecb_months_for(label))
    _write_local_run_config(work_dir, cfg)

    learned = expense_memory = None
    if learning_db_path is not None:
        learned = MerchantCategoryLookup.from_db_path(learning_db_path)
        expense_memory = ExpenseMemory.from_db_path(learning_db_path)
    # Merchant registry from the settings snapshot; empty => no-op.
    registry = MerchantRegistry.from_settings(settings)

    return PreparedExpenseBatch(
        run_id=run_id,
        work_dir=work_dir,
        cfg=cfg,
        label=(
            label.strip()
            or " ".join(
                p for p in ("Expenses", legal_entity.strip(), now_iso[:10]) if p
            )
        ),
        learned=learned,
        ai_unavailable=not have_key,
        use_llm_effective=use_llm_effective,
        now_iso=now_iso,
        operator=operator,
        upload_issues=issues,
        upload_issue_details=issue_details,
        expense_memory=expense_memory,
        registry=registry,
        created_by=created_by,
        intake_provenance=intake_provenance or None,
    )


def execute_expense_batch(
    store: RunStore, prepared: PreparedExpenseBatch, *, on_stage=None,
    pre_commit=None, learning_db_path: Path | None = None,
) -> str:
    """Run OCR + categorization for a prepared expense batch and persist the
    run row (mode marker in config AND summary). Slow (vision per file);
    the web layer runs it in the background and the SPA polls the job.

    ``pre_commit(store)``, when given, runs immediately before the run row
    is written and may raise to abort the commit (no row is created; the
    exception propagates). The mail-intake materializer uses it to
    re-check that no competing batch for the same month landed while the
    OCR ran — this function itself stays policy-free."""
    try:
        result = generate_expenses(
            prepared.cfg,
            prepared.work_dir,
            learned=prepared.learned,
            on_stage=on_stage,
            expense_memory=prepared.expense_memory,
            registry=prepared.registry,
        )
    except ConfigError as exc:
        raise RunInputError(
            str(exc), code="pipeline_config_invalid"
        ) from exc

    receipts = result.receipts
    n_categorized, n_uncategorized = categorized_counts(receipts)
    counts = count_parse_issues(result.parse_errors)
    set_aside = [
        _set_aside_entry(r, prepared.now_iso)
        for r in result.set_aside_receipts
    ]
    summary = {
        "mode": MODE_EXPENSE_GENERATION,
        "n_expenses": len(receipts),
        "n_receipts": len(receipts),
        "n_categorized": n_categorized,
        "n_uncategorized": n_uncategorized,
        "n_set_aside": len(set_aside),
        "n_parse_errors": counts["errors"],
        "n_parse_notes": counts["notes"],
        "llm_cost_usd": (
            str(result.cost_tracker.total_cost_usd) if result.cost_tracker else "0"
        ),
        "ai_unavailable": prepared.ai_unavailable,
        "upload_issues": prepared.upload_issues,
        "upload_issue_details": prepared.upload_issue_details,
    }
    if prepared.created_by:
        # Origin marker (item 39): parallel, absent on operator-created
        # batches, so /months can say which months materialized themselves.
        summary["created_by"] = prepared.created_by
    snapshot = snapshot_to_dict([], receipts, result.outcome, result.parse_errors)
    if set_aside:
        snapshot["set_aside"] = set_aside
    if prepared.intake_provenance:
        # A batch created FROM mailed receipts (item 39 materialization,
        # R3 trip join) carries the submitters the same way the
        # incremental add path records them.
        snapshot["intake_provenance"] = dict(prepared.intake_provenance)

    if on_stage is not None:
        try:
            on_stage("saving")
        except Exception:  # noqa: BLE001
            pass
    if pre_commit is not None:
        pre_commit(store)
    store.create_run(
        run_id=prepared.run_id,
        created_at=prepared.now_iso,
        label=prepared.label,
        operator=prepared.operator,
        summary=summary,
        snapshot=snapshot,
        config=prepared.cfg,
        work_dir=str(prepared.work_dir),
        llm_enabled=prepared.use_llm_effective,
        has_coa=result.chart_of_accounts is not None,
    )
    # R4b: a trip batch materializing (its first receipts) is a pool
    # change for every reconciling month the trip's dates span -- the
    # same trigger the gradual-add path fires (item 38 ruling 3).
    created = store.get_run(prepared.run_id)
    if created is not None and is_trip_batch(created):
        # R4.1: `learning_db_path` is threaded so a month re-matched by a
        # trip MATERIALIZING reconciles with the same MatchMemory the
        # gradual-add path gives it; before it was passed, whether a month
        # saw its learned corrections depended on which of the two trip
        # entrances fired.
        rematch_months_after_trip_change(
            store, created, learning_db_path=learning_db_path
        )
    return prepared.run_id


def _apply_header_overrides(r: Receipt, fields: dict[str, str]) -> Receipt:
    """One expense with its header-field edits applied (frozen dataclass,
    so a `replace`). Values were validated at the edge; a corrupt stored
    value is skipped rather than breaking the whole view."""
    kw: dict = {}
    for field, value in fields.items():
        try:
            if field == "vendor":
                kw["detected_vendor"] = value or None
            elif field == "date":
                kw["detected_date"] = date.fromisoformat(value) if value else None
            elif field == "total":
                kw["detected_total"] = Decimal(value) if value else None
            elif field == "currency":
                kw["detected_currency"] = value.upper() if value else None
            elif field == "tax":
                kw["detected_tax"] = Decimal(value) if value else None
            elif field == "tax_label":
                kw["tax_label"] = value or None
            elif field == "paid_through":
                kw["paid_through"] = value or None
            elif field == "legal_entity":
                if value.strip():
                    kw["legal_entity_id"] = value.strip()
            elif field == "reference":
                kw["detected_reference"] = value or None
            # `customer` is export passthrough only — no Receipt field.
        except (ArithmeticError, ValueError):
            continue
    return replace(r, **kw) if kw else r


def _manual_expense_receipt(
    document_id: str, payload: dict, default_entity: str
) -> Receipt:
    """Build the Receipt for a manually-added expense (Note 3: expenses
    with no receipt file). Always synthesizes one full-total line item so
    category overrides, the view, and the export treat it like any
    categorized receipt. Payload values were validated at the edge."""
    def _s(key: str) -> str | None:
        v = str(payload.get(key) or "").strip()
        return v or None

    def _d(key: str) -> Decimal | None:
        v = _s(key)
        try:
            return Decimal(v) if v else None
        except ArithmeticError:
            return None

    try:
        detected_date = date.fromisoformat(_s("date")) if _s("date") else None
    except ValueError:
        detected_date = None
    total = _d("total")
    vendor = _s("vendor")
    currency = _s("currency")
    categorization = None
    if _s("category") or _s("zoho_account"):
        categorization = Categorization(
            category=_s("category"),
            zoho_account=_s("zoho_account"),
            confidence=1.0,
            source=ClassificationSource.LINE,
            reasoning="entered by reviewer",
        )
    line = LineItem(
        description=_s("description") or vendor or "manual expense",
        line_total=total,
        quantity=None,
        unit_price=None,
        categorization=categorization,
    )
    return Receipt(
        document_id=document_id,
        legal_entity_id=_s("legal_entity") or default_entity,
        detected_date=detected_date,
        detected_total=total,
        detected_currency=currency.upper() if currency else None,
        detected_vendor=vendor,
        detected_reference=_s("reference"),
        receipt_name=None,
        line_items=(line,),
        paid_through=_s("paid_through"),
        detected_tax=_d("tax"),
        tax_label=_s("tax_label"),
    )


# ── The extraction baseline (2026-08-25, living-month prerequisite) ──
# `rematch_month` bakes the reviewer's corrections into the receipt pool the
# matcher sees and then COMMITS that pool as the run's snapshot. But the
# snapshot is also the audit baseline: the grid lays the overlay on top of it
# and shows its values as the vendor object's `raw` ("the ORIGINAL extracted
# name ... always kept for audit"). Baking over it made `raw` echo the very
# edit it exists to distinguish, and left `set_expense_field_override(None)`
# -- documented as "the expense reverts to its extracted value" -- with
# nothing to revert to.
#
# So the pre-bake receipts are preserved once, in a parallel snapshot key,
# and every overlay-composing read (grid, export, learning harvest) starts
# from them instead of from the baked pool. Matching, the reports and the
# reconciliation views keep reading `receipts`: that pool is baseline +
# overlay by construction, and it is re-derived on the next re-match.
#
# First write wins PER DOCUMENT, which is the whole trick. A second re-match
# reads an ALREADY baked snapshot, so refreshing the baseline each time would
# capture the baked values and lose the truth it holds. Growing it per
# document is what lets a living month keep receiving receipts: each one is
# pristine when it arrives and joins the baseline at the next bake.
#
# Runs whose statement was attached BEFORE this shipped have no baseline and
# their pre-edit values are already gone; they fall back to the baked pool,
# which is what they had. Nothing at rest migrates.
EXTRACTED_RECEIPTS_KEY = "extracted_receipts"


def baseline_receipts(run: RunRow) -> list[Receipt]:
    """The run's receipts as EXTRACTION read them, before any reviewer edit
    was baked in. Falls back to the snapshot's own receipts when no baseline
    was captured (any run older than the key, and every statement-less run,
    whose receipts have never been baked).

    Iterates the CURRENT receipt list so membership and order follow the
    snapshot: a baseline entry for a receipt the snapshot no longer carries
    must not resurrect it.
    """
    snapshot = run.snapshot or {}
    current = snapshot.get("receipts") or []
    baseline = snapshot.get(EXTRACTED_RECEIPTS_KEY)
    if not isinstance(baseline, list) or not baseline:
        return [receipt_from_dict(d) for d in current]
    by_id = {
        d.get("document_id"): d
        for d in baseline
        if isinstance(d, dict) and d.get("document_id")
    }
    out: list[Receipt] = []
    for d in current:
        pristine = by_id.get(d.get("document_id"))
        try:
            out.append(receipt_from_dict(pristine if pristine else d))
        except (KeyError, TypeError, ValueError):
            # A corrupt baseline entry degrades to the live row rather than
            # breaking the whole view.
            out.append(receipt_from_dict(d))
    return out


def _extended_baseline(existing, receipt_dicts: list[dict]) -> list[dict]:
    """The baseline to persist: whatever it already holds, plus a pristine
    entry for every document it does not cover yet. Never overwrites."""
    out: list[dict] = [
        d for d in (existing or []) if isinstance(d, dict) and d.get("document_id")
    ]
    known = {d["document_id"] for d in out}
    for d in receipt_dicts:
        doc_id = d.get("document_id")
        if doc_id and doc_id not in known:
            out.append(d)
            known.add(doc_id)
    return out


def apply_expense_edits(
    receipts: list[Receipt],
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    category_overrides: dict | None = None,
    default_entity: str = "",
) -> list[Receipt]:
    """The expense-mode overlay: drop soft-deleted expenses, append manual
    adds, apply header-field edits. Line-level category overrides stay in
    `apply_overrides` / `_receipt_view` (the shared path); they are taken
    here ONLY to synthesize a line item on a bare receipt (failed OCR left
    no lines) so a category assigned to it has somewhere to land."""
    deleted = {e["document_id"] for e in edits if e["op"] == "delete"}
    out: list[Receipt] = []
    for r in receipts:
        if r.document_id in deleted:
            continue
        fields = field_overrides.get(r.document_id)
        if fields:
            r = _apply_header_overrides(r, fields)
        if (
            not r.line_items
            and category_overrides
            and (r.document_id, 0) in category_overrides
        ):
            r = replace(
                r,
                line_items=(
                    LineItem(
                        description=r.detected_vendor or "",
                        line_total=r.detected_total,
                        quantity=None,
                        unit_price=None,
                        categorization=None,
                    ),
                ),
            )
        out.append(r)
    # A manual add whose document already sits in the pool is never appended
    # twice: after a statement attach BAKES the effective receipts into the
    # snapshot, the edit rows stay (they still feed learning), and this guard
    # keeps the overlay idempotent instead of duplicating every manual expense.
    #
    # Item 70: the baked copy is REPLACED in place rather than kept. Once the
    # edit routes reopened on a reconciling month, a manual add can be edited
    # and its edit cleared after a bake, and the baked copy still carries the
    # cleared value. The add's payload is its extraction, so rebuilding from
    # it keeps the overlay both idempotent and reversible, at the same pool
    # position so the matcher's input order does not move.
    position = {r.document_id: i for i, r in enumerate(out)}
    for e in edits:
        if e["op"] != "add" or e["document_id"] in deleted:
            continue
        r = _manual_expense_receipt(e["document_id"], e["payload"], default_entity)
        fields = field_overrides.get(r.document_id)
        if fields:
            r = _apply_header_overrides(r, fields)
        if r.document_id in position:
            out[position[r.document_id]] = r
        else:
            position[r.document_id] = len(out)
            out.append(r)
    return out


# ── Cards R3 (2026-08-21): per-receipt card + entity resolution ─────
# The batch-level legal entity became optional; each receipt's entity
# resolves from its paying card via ONE chain used by BOTH the grid and
# the export (grid == export by construction, the books_as pattern):
#   field override -> batch hint assignment / card registry -> the
#   receipt's own stamped entity (batch default or learned) -> "" (review
#   state `needs_entity`). Cards come from the batch CONFIG snapshot, so
#   an existing batch's rows never move because settings drifted; the
#   explicit refresh-master-data pass is how settings reach a batch.


def _batch_cards(cfg: dict | None) -> dict:
    """The batch's snapshotted card registry, as Card objects."""
    from ..cards import cards_from_setting

    return cards_from_setting(((cfg or {}).get("expense") or {}).get("cards"))


def _batch_card_hints(cfg: dict | None) -> dict[str, str]:
    """The batch's operator-confirmed hint -> card-key assignments."""
    raw = ((cfg or {}).get("expense") or {}).get("card_hints")
    if not isinstance(raw, dict):
        return {}
    return {
        str(k).strip(): str(v).strip()
        for k, v in raw.items()
        if str(k).strip() and str(v).strip()
    }


def bank_transfer_tender(hint: str | None) -> bool:
    """Whether a payment method reads as a bank transfer and names no card.

    The rule is the settled-outside chip's own (`suggested_settled_outside`
    answering `bank_transfer`), so the tool cannot offer "paid by bank
    transfer" and "paid with a private card" for the same words. Minus the
    Brazilian POS word TEF: on a cupom fiscal it is a card payment (July's
    Fenix groceries receipt prints TEF and settles a card charge), and a card
    tender is exactly what the private suggestion is for.
    """
    text = (hint or "").strip()
    if not text:
        return False
    hit = suggested_settled_outside(re.sub(r"\btef\b", " ", text, flags=re.IGNORECASE))
    return hit is not None and hit["how"] == "bank_transfer"


def settled_off_card(entry: object) -> bool:
    """Whether one row's settled-outside disposition takes it out of the
    card system (item 144).

    The argument is one value of `settled_outside_map` (`{how, note, at}`),
    or None for a row with no disposition. It is settled off the card when
    it carries a `how`: the reviewer has stated how the money moved, and
    that answer is never a company card.

    Called ONCE per row, by `resolve_batch_row_cards`, which stamps the
    answer on the resolution as `settled_off_card`. Everything that acts on
    it downstream (the private option, the boxes, the review sentence, the
    card strip's `n_needs_person`) reads that stamp rather than deciding
    again, so no two surfaces of one payload can disagree about one row.
    """
    return bool(isinstance(entry, dict) and entry.get("how"))


def merchant_vouches_one_card(merchants: dict | None, registry, r) -> bool:
    """Item 173, read-time half: may a REMEMBERED card lend itself to this
    receipt? The rule itself is `MerchantRegistry.vouches_one_card` and its
    reasoning lives there, because the ingest stamp asks the same question
    (item 173's second half) and a gate held in one layer and not the other
    is the bug this was split in half by.

    `merchants` stays in the signature as the caller's own "is there a
    registry at all" evidence; the cards themselves now come off the match.
    """
    if not merchants or registry is None:
        return False
    return registry.vouches_one_card(r.vendor_clean, r.detected_vendor)


def fill_remembered_cards(
    receipts: "list[Receipt]",
    learning_db_path: "Path | None",
    merchants: dict | None = None,
) -> "list[Receipt]":
    """Item 169: read the remembered card LIVE, the way every link beside it
    is read.

    `resolve_batch_row_cards` takes its `learned` candidate off
    `Receipt.card_key`, and the only thing that ever writes that field is
    `ExpenseMemory.apply` during `generate_expenses`. So a card correction is
    frozen at the moment a month was ingested: it reaches the months ingested
    after it and can never reach the ones ingested before, which is not a rule
    anybody chose. Every other link in the same chain resolves against current
    state -- the reviewer's pick, the batch's hint assignments, the settled
    charge, and (note item M2, in as many words) the merchant registry, "read
    LIVE like the cost-center registry rather than from the batch snapshot, so
    the day a merchant gains a card the existing months resolve without a
    refresh pass". This closes the one exception.

    Measured on the live store 2026-09-23, before anything was changed:
    September held 26 receipts with no card, 25 with no legal entity and 25
    with no person; the correction `('', 'openai') -> 3645` had been saved
    that morning, names a card the batch holds, and matched 12 of those rows
    on a key that already lined up. It reached none of them. Filling the field
    here moves all three columns by 12, because every entity-less and
    person-less row in all three live months is a card-less row.

    Only rows carrying no card key are filled, so a value the batch already
    holds is never overwritten, and the chain's own precedence is untouched:
    the remembered card still loses to a reviewer's pick, a printed card
    number and the settled charge. An absent or unreadable learning store
    leaves every receipt exactly as it was.
    """
    if learning_db_path is None or not Path(learning_db_path).exists():
        return receipts
    from ..learning.consult import FieldCorrectionLookup
    from ..learning.store import LearningStore

    with LearningStore(Path(learning_db_path)) as store:
        lookup = FieldCorrectionLookup.from_store(store)
    if not lookup:
        return receipts
    registry = None
    if merchants:
        from ..merchant_registry import MerchantRegistry

        registry = MerchantRegistry.from_settings({"merchants": merchants}) or None
    out: list[Receipt] = []
    for r in receipts:
        if not (r.card_key or "").strip():
            remembered = lookup.get(
                (r.legal_entity_id or "").strip(), r.detected_vendor
            ).get("card_key")
            # Item 173: only for a brand the registry vouches is paid on one
            # card. Without that gate this fires hardest exactly where it is
            # least safe, because the vendors a human bothers to correct are
            # the multi-card ones.
            if remembered and merchant_vouches_one_card(merchants, registry, r):
                r = replace(r, card_key=remembered)
        out.append(r)
    return out


def resolve_batch_row_cards(
    receipts: "list[Receipt]",
    cfg: dict | None,
    field_overrides: dict[str, dict[str, str]],
    *,
    settled_cards: dict[str, str] | None = None,
    settled_outside: dict[str, dict] | None = None,
    merchants: dict | None = None,
) -> dict[str, dict]:
    """Per-document card + entity resolution for an expense batch:
    ``{document_id: {hint, card: Card|None, entity, entity_source}}``.

    `receipts` are the POST-overlay pool (edits applied), so the entity
    fallback step reads what the reviewer sees; the override step reads
    `field_overrides` directly so an explicit edit is labeled as such.
    `entity_source` is override | card | batch | learned | none — "learned"
    meaning the stamped value differs from the batch default (memory or an
    earlier card stamp), so the UI can say why without guessing.

    `person` / `person_source` (backlog item 40): who the expense belongs
    to, resolved as the LAST link of the SAME card chain — the resolved
    card's own `person`, source "card", else "" / "none". There is NO
    sender-based fallback by explicit owner ruling: `submitted_by` stays
    ingest provenance and never becomes attribution, which is why this
    function never sees it.

    `card_map_blocked` (per doc) tells the paid-through resolver the
    registry chain already ANSWERED the identity question in a way the
    flat digit->account map must not second-guess: the hint was ambiguous
    between cards, or it resolved to a card with no Zoho account set
    (R3 adversarial review — the flat map's fuzzy fallback was guessing a
    wrong account exactly where the chain had refused to).

    `private` / `reimburse_to` / `suggested_private` (backlog item 41,
    owner directive 2026-09-06): a payment method that resolves to NO
    registered card is SUGGESTED as a private expense — never stamped.
    The suggestion fires on a non-empty hint the chain refused (not on
    ambiguity, which is a known-card contest). The operator resolves it
    by confirming private (the `private` + `reimburse_to` field
    overrides; the row becomes a reimbursement row and its person IS
    `reimburse_to`, source "private" — the one bounded exception to item
    40's card-only rule, operator-confirmed) or by assigning/registering
    the real card, which clears it. An entity override no longer clears
    the suggestion (owner 2026-09-17): the entity says which company the
    expense books to, not how it was paid, and the old exemption left an
    "EC-Karte" restaurant bill in August on needs_person, pointing at a
    Settings card that does not exist.

    `can_mark_private` (owner 2026-09-17: "expenses on cards that are not
    defined in settings ... the option of defining as an expense that went
    through private card"): whether the private-card option applies to the
    row at all. True when no defined company card paid it (no card, not a
    two-card contest) or when the card is only REMEMBERED from an earlier
    month (memory is not a decision on this row, and the reviewer has no
    way to take it off). False once the row IS private (item 176, operator
    2026-09-23: "no need to set this as private again, if user has already
    set as private") -- the control that belongs on a confirmed private row
    is undo, which the screen keys on `private` itself, never on this flag.
    A company card from the printed number, a strip assignment or this row's
    own card pick means the company paid: nothing to reimburse. A confirmed
    private row never picks up a remembered card.

    `settled_cards` (item 111, `settled_charge_cards`): `{document_id: card
    key}` of the charge in this month that settles the receipt. Only the
    Expenses payload passes it, never the matcher's bake (the pairing would
    feed its own card scope). It applies where memory would, and before it:
    no per-row pick, no card from the printed method or a hint, no card
    number printed, not confirmed private. Source `settled_charge`; the
    company paid, so `can_mark_private` is false.

    `settled_outside` (residual R3, `settled_outside_map`): the month's
    settled-outside dispositions. A receipt the reviewer settled outside the
    card, and a payment method that reads as a bank transfer
    (`bank_transfer_tender`), suggest NO private card: the suggestion asks
    which card paid, and a wire is not a card. July's restored Tricarico
    invoice (BRL 27,203.34, "Payment Method: Wire Transfer", settled outside
    by bank transfer) read `suggested_private` while the tool's own ruling
    of 2026-09-15 calls a settled-outside receipt real company spend.

    Item 144 (owner ruling 2026-09-17) closed the half this left open. A
    row the reviewer has settled OFF the card system (`settled_off_card`:
    its disposition carries a `how`) also reads `can_mark_private` false.
    Both exits the screen offered on July's Tricarico invoice stated
    something untrue: picking a company card says a card paid it, and
    confirming a private card says the reviewer paid it out of her own
    pocket. A wire is neither. The printed tender alone
    (`bank_transfer_tender`) does NOT take the option away, because that
    is the document's claim about itself; only the reviewer's own
    disposition does.

    `merchants` (note item M2, 2026-09-18) is `settings["merchants"]`, read
    LIVE like the cost-center registry rather than from the batch snapshot,
    so the day a merchant gains a card the existing months resolve without a
    refresh pass. It adds ONE link at the END of the chain, source
    `merchant`: a merchant whose registry entry names a `card_key` lends it
    to a receipt that prints no card number, names no assigned hint, is not
    confirmed private, is not settled by a charge of this month and is not
    remembered from an earlier one. It is memory about the brand, not a
    decision about this row, so `can_mark_private` stays true exactly as it
    does for `learned`. A caller that passes nothing behaves as before, which
    is every caller with no settings in hand (the CSV without a store, the
    matcher's re-match) -- and the matcher is deliberate: `merchant` is not
    in `CARD_SCOPE_SOURCES`, so a card the registry lends never scopes
    matching.
    """
    from ..cards import masked_short_ending, resolve_hinted_card_ex
    from ..matching.deterministic import _card_keys

    cards = _batch_cards(cfg)
    hints_map = _batch_card_hints(cfg)
    # Note item M2: built once, and only when a merchant map was passed. The
    # per-row lookup is a fuzzy sweep, so it runs lazily inside the loop for
    # the rows that reach the last link -- the ones with no card at all.
    merchant_registry = None
    if merchants:
        from ..merchant_registry import MerchantRegistry

        merchant_registry = MerchantRegistry.from_settings(
            {"merchants": merchants}
        ) or None
    batch_entity = ((cfg or {}).get("expense") or {}).get("legal_entity_id", "")
    out: dict[str, dict] = {}
    for r in receipts:
        hint = (r.payment_mode or "").strip()
        # Residual R3: a tender no card carries (a wire), or a receipt the
        # reviewer already settled outside the card, answers the private
        # suggestion's question with "no card at all".
        settled_off = settled_off_card((settled_outside or {}).get(r.document_id))
        not_a_card = bank_transfer_tender(hint) or settled_off
        card, ambiguous = resolve_hinted_card_ex(hint, cards, hints_map)
        card_source = "hint" if card is not None else "none"
        # Note #60: the two digits the card was named by, when a masked
        # ending was the only card number the receipt printed. Weaker than a
        # last-4, so the screen says so; empty for every other resolution.
        ending = masked_short_ending(hint) if card is not None else None
        card_ending = (
            ending
            if ending
            and not (hints_map or {}).get(hint)
            and any(str(d).endswith(ending) for d in card.digits)
            else ""
        )
        # Item 87: the reviewer's per-row card fix wins over everything the
        # receipt printed; a card REMEMBERED from an earlier month's fix
        # applies only when the printed payment method carries no card
        # number (a tender word, or nothing), so memory never overrides a
        # number the document shows. A key the batch's cards do not hold,
        # or an inactive card, decides nothing.
        fields = field_overrides.get(r.document_id) or {}
        reimburse_to = str(fields.get("reimburse_to") or "").strip()
        # A confirmation IS the pair: the flag AND who gets reimbursed.
        # A `private` flag without a person (reachable through the
        # generic field PUT's one-field-at-a-time writes) is NOT a
        # decision — honoring it would let "owed to nobody" exit
        # MISSING ENTITY and reach the report (adversarial review,
        # 2026-09-06). Such a row stays suggested until both halves
        # exist.
        private = (
            str(fields.get("private") or "").strip() == "1"
            and bool(reimburse_to)
        )
        fixed = _batch_row_card(cards, fields.get("card_key"))
        if fixed is not None:
            card, card_source = fixed, "override"
            card_ending = ""
        elif card is None and not _card_keys(hint) and not private:
            # Item 111: the statement names the card a settled pair was paid
            # with, which outranks a card remembered from another month.
            settled = _batch_row_card(
                cards, (settled_cards or {}).get(r.document_id)
            )
            remembered = _batch_row_card(cards, r.card_key)
            if settled is not None:
                card, card_source = settled, "settled_charge"
            elif remembered is not None:
                card, card_source = remembered, "learned"
            elif merchant_registry is not None:
                # Note item M2: the brand's own card, last. A merchant whose
                # spend is exclusively on one card answers "which card paid"
                # for a receipt that prints nothing -- and a merchant seen on
                # two cards carries no key, so it stays unanswered.
                match = merchant_registry.resolve(r.vendor_clean, r.detected_vendor)
                from_merchant = _batch_row_card(
                    cards, match.card_key if match is not None else None
                )
                if from_merchant is not None:
                    card, card_source = from_merchant, "merchant"
        override = fields.get("legal_entity", "")
        if override.strip():
            entity, source = override.strip(), "override"
        elif card is not None and card.entity:
            entity, source = card.entity, "card"
        elif (r.legal_entity_id or "").strip():
            entity = r.legal_entity_id.strip()
            source = "batch" if entity == (batch_entity or "").strip() else "learned"
        else:
            entity, source = "", "none"
        if private:
            person, person_source = reimburse_to, "private"
        elif card is not None and card.person:
            person, person_source = card.person, "card"
        else:
            person, person_source = "", "none"
        out[r.document_id] = {
            "hint": hint,
            "card": card,
            "entity": entity,
            "entity_source": source,
            "person": person,
            "person_source": person_source,
            "private": private,
            "reimburse_to": reimburse_to if private else "",
            "suggested_private": bool(
                hint and card is None and not ambiguous and not private
                and not not_a_card
            ),
            "can_mark_private": (
                not private
                and not settled_off
                and not ambiguous
                and (card is None or card_source in ("learned", "merchant"))
            ),
            "ambiguous": ambiguous,
            # A reviewer's (or remembered) pick settles the ambiguity the
            # hint left, so the pick's own account decides, as for a hint.
            "card_map_blocked": (ambiguous and card is None)
            or (card is not None and not card.zoho_account),
            "card_source": card_source,
            "card_ending": card_ending,
            # Item 144: the row's settled-off-the-card state, decided ONCE
            # here and carried on the resolution so every surface that
            # answers a person-owed question reads the same fact. The
            # boxes, the review sentence and the card strip's
            # `n_needs_person` all take it from here; a caller that passes
            # no `settled_outside` map gets False for every row, which is
            # correct (only the Expenses payload knows the dispositions).
            "settled_off_card": settled_off,
        }
    return out


def bake_card_scope(
    receipts: "list[Receipt]", card_res: dict[str, dict]
) -> "list[Receipt]":
    """Stamp the card the tool resolved for each receipt onto the match pool
    (item 137, `Receipt.card_scope_keys` / `card_scope_source`).

    Before item 137 only a card the receipt PRINTED scoped its matching, and
    note #63 bolted a picked card on by rewriting the printed payment mode,
    and only where the pick contradicted a printed card. The card resolved
    by the same chain the grid shows (`resolve_batch_row_cards`: a pick on
    the row, the printed method or a hint word assigned to a card, a card
    remembered from an earlier month) now reaches the matcher for every
    receipt, and `match_month` decides what each source may do. Pool only:
    the fields are never serialized and are re-derived on every re-match,
    and `rematch_month` and the attribution tool both call this."""
    from ..matching.deterministic import CARD_SCOPE_SOURCES

    out = []
    for r in receipts:
        res = card_res.get(r.document_id) or {}
        card, source = res.get("card"), res.get("card_source")
        keys = tuple(sorted(card.digit_keys())) if card is not None else ()
        if keys and source in CARD_SCOPE_SOURCES:
            r = replace(r, card_scope_keys=keys, card_scope_source=source)
        out.append(r)
    return out


def _batch_row_card(cards: dict, key: object):
    """The active batch card a per-row fix (or its memory) names, else None."""
    key = str(key or "").strip()
    card = cards.get(key) if key else None
    return card if card is not None and card.active else None


def prepare_row_card_fix(store: RunStore, run_id: str, key: str) -> str | None:
    """Item 87: make a per-row card fix resolvable on this batch. The key must
    name an active card in the live registry (what `GET /api/cards` offered);
    a card defined after the batch was created is copied into the batch's card
    snapshot, exactly as a strip assignment does, so the row resolves without a
    refresh of every other row's master data. Returns an error, or None."""
    from ..cards import cards_to_setting, effective_cards
    from ..cards_provision import load_cards

    live = effective_cards(store.get_settings(), load_cards()).get(key)
    if live is None:
        return Refusal(
            f"card_key {key!r} is not a defined card; define it in "
            "Settings, Cards first",
            code="card_not_defined",
            card=key,
        )
    if not live.active:
        return Refusal(
            f"card {key!r} is inactive; reactivate it before assigning "
            "receipts to it",
            code="card_inactive",
            card=key,
        )
    with _BATCH_ADD_LOCK:
        run = store.get_run(run_id)
        if run is None:
            return Refusal(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        cfg = dict(run.config or {})
        exp = dict(cfg.get("expense") or {})
        batch_cards = dict(exp.get("cards") or {})
        if key not in batch_cards:
            batch_cards[key] = cards_to_setting({key: live})[key]
            exp["cards"] = batch_cards
            cfg["expense"] = exp
            store.update_run_config(run_id, cfg)
    return None


def resolve_batch_row_cost_centers(
    receipts: list[Receipt],
    field_overrides: dict[str, dict[str, str]],
    *,
    settings: dict | None,
    trip: dict | None,
    card_res: dict[str, dict],
) -> dict[str, CostCenterResolution]:
    """Per-document cost-center resolution for an expense batch (item 47):
    ``{document_id: CostCenterResolution}``.

    Runs the chain in `CostCenterRegistry.resolve` over four candidates, in
    its precedence order:

    1. the row's own ``cost_center`` field override -- a reviewer decision,
       beats everything;
    2. the batch's TRIP, whose cost center a human DECLARED at creation
       (item 38), which is why it outranks anything inferred;
    3. the merchant registry entry for this row's vendor;
    4. the resolved card's ``default_cost_center``, the weakest link
       because a card belongs to a project only loosely.

    Person and category are deliberately absent: person cannot separate
    "Nicolas in Brazil" from "Nicolas on Lidar" (both of Dirk's own
    examples), and letting category co-vary destroys the point of cutting
    the money a second way.

    Both registries are read LIVE from settings rather than from the
    batch's config snapshot, and that is the point: the whole first phase
    of this feature is an EMPTY registry, and the day the owner defines the
    first cost center the existing months must start resolving without a
    refresh pass. The card's `default_cost_center` is the exception by
    construction -- it rides the card snapshot like `person`, so it reaches
    an existing batch through refresh-master-data.

    An empty registry returns a silent unresolved for every row (resolves
    nothing AND flags nothing), which is the contract this whole feature
    rests on: a review state firing on 100% of rows is noise, not signal.
    """
    registry = CostCenterRegistry.from_settings(settings)
    # The merchant sweep is the expensive link (a fuzzy match per row), and
    # nothing it found could resolve against an empty registry, so it is
    # skipped. The empty-registry CONTRACT is deliberately NOT re-stated
    # here: it lives in `registry.resolve` alone, so a change that unwires
    # it reddens these rows instead of being masked by a second copy.
    merchants = MerchantRegistry.from_settings(settings) if registry else None
    trip_cc = str((trip or {}).get("cost_center") or "").strip()
    out: dict[str, CostCenterResolution] = {}
    for r in receipts:
        card = (card_res.get(r.document_id) or {}).get("card")
        merchant_cc = None
        if merchants:
            match = merchants.resolve(r.vendor_clean, r.detected_vendor)
            if match is not None:
                merchant_cc = match.cost_center
        out[r.document_id] = registry.resolve(
            override=(field_overrides.get(r.document_id) or {}).get("cost_center"),
            trip=trip_cc,
            merchant=merchant_cc,
            card=getattr(card, "default_cost_center", "") if card else "",
        )
    return out


def build_card_review(
    resolution: dict[str, dict], *, copy_docs: "set[str] | None" = None,
) -> dict:
    """The batch's card-review strip, grouped server-side (the SPA renders,
    never judges): unresolved hints (with the rows they cover, generic
    tenders marked — those never auto-resolve BY DESIGN and can only be
    assigned explicitly), resolved cards with their hit counts, and the
    no-hint rest.

    Digit-bearing unresolved hints group by their CANONICAL digit run
    (backlog item 35: five spellings of 0340 rendered as five assignable
    rows). The group key is the run's zero-stripped form — the same
    equivalence `_card_keys` gives the matcher, so "0340" and a label
    printing "340" are one group — while `digits` keeps the longest
    printed spelling for display (a human knows the card as the statement
    prints it, leading zero included). `hint` stays the row's own field
    per api-contract rule 1: it carries the group's most-frequent member
    spelling, so a stale SPA renders one truthful row and its Assign
    still submits a hint string that exists in the batch (the digit fold
    on assignment then resolves every sibling spelling). The full member
    list rides in the PARALLEL `spellings[]`. Digit-less hints (generic
    tenders, word-only hints) keep one row per verbatim string —
    `digits: null` + the `generic` flag are what the SPA partitions the
    no-card-number sub-strip on.

    `copy_docs` (item 146) are the documents the grid has decided are
    copies (`decided_copies`). The four counters at the bottom, the ones
    that have a `summary` twin, skip them: those twins are box counts
    (`n_box`), and `expense_boxes` puts a decided copy in NO box by item
    94's ruling. A strip that counted copies made one payload answer the
    same question twice on one screen; live July 2026 read
    `summary.n_needs_person` 13 beside `card_review.n_needs_person` 15,
    the gap being exactly the two decided copies (Aposto Karlsruhe,
    Lovable Labs Incorporated). All four take the exemption together: a
    twin left unexcluded only moves the disagreement to another chip.

    The GROUPING keeps every copy, deliberately. `unresolved_hints`,
    `resolved`, per-entry `n_rows`, `n_resolved_rows`, `n_unresolved_rows`
    and `n_no_hint` describe the card-ASSIGNMENT surface, where a decided
    copy is still a row on screen carrying a payment hint the reviewer can
    assign; dropping it would take an assignable row she is looking at off
    the strip. None of them has a `summary` twin, so none of them can
    disagree with anything. A caller that passes no `copy_docs` counts
    every row, which is right for a caller outside the Expenses payload:
    only that payload knows the month's copy decisions."""
    from ..cards import hint_digit_run, is_generic_tender

    unresolved: dict[str, dict] = {}
    spelling_rows: dict[str, dict[str, int]] = {}
    resolved: dict[str, dict] = {}
    n_no_hint = 0
    for doc, res in resolution.items():
        hint, card = res["hint"], res["card"]
        if card is not None:
            entry = resolved.setdefault(card.key, {
                "card": {
                    "key": card.key,
                    "label": card.display_label,
                    "entity": card.entity,
                    "person": card.person,
                    "zoho_account": card.zoho_account,
                },
                "n_rows": 0,
                "hints": set(),
            })
            entry["n_rows"] += 1
            if hint:
                entry["hints"].add(hint)
        elif hint:
            run = hint_digit_run(hint)
            group = (
                f"digits:{run.lstrip('0') or '0'}" if run else f"hint:{hint}"
            )
            entry = unresolved.setdefault(group, {
                "hint": "",  # representative spelling, chosen after the loop
                "digits": None,
                "n_rows": 0,
                "documents": [],
                "generic": is_generic_tender(hint),
                # True = two or more cards claim this hint; assigning it
                # explicitly is the only resolution path.
                "ambiguous": False,
            })
            entry["n_rows"] += 1
            entry["documents"].append(doc)
            entry["ambiguous"] = entry["ambiguous"] or bool(res.get("ambiguous"))
            # Item 41: any member row still suggested-private marks the
            # entry, so the sub-strip can say "suggested as a private
            # expense" without judging (confirmed/ambiguous rows do not).
            entry["suggested_private"] = entry.get(
                "suggested_private", False
            ) or bool(res.get("suggested_private"))
            if run and len(run) > len(entry["digits"] or ""):
                entry["digits"] = run
            counts = spelling_rows.setdefault(group, {})
            counts[hint] = counts.get(hint, 0) + 1
        else:
            n_no_hint += 1
    for group, entry in unresolved.items():
        counts = spelling_rows[group]
        entry["spellings"] = sorted(counts, key=lambda s: (-counts[s], s))
        # The representative must be able to HEAL the group on a stale
        # SPA: assigning it folds its digit into the card only when the
        # spelling carries exactly ONE digit run (`learnable_hint_tokens`
        # refuses multi-run hints — BIN/expiry ambiguity), so prefer the
        # most frequent single-run member. A Zoho payment-mode label
        # ("1 - CorpServ 2838/1672 (Chase)") must not become the
        # representative just by being frequent: assigning it alone would
        # teach no digit and leave its siblings unresolved (adversarial
        # review, 2026-09-06). A group with no single-run member falls
        # back to the most frequent spelling — no member could teach a
        # digit there anyway.
        healing = [
            s for s in entry["spellings"]
            if len(re.findall(r"\d{3,8}", s)) == 1
        ]
        entry["hint"] = (healing or entry["spellings"])[0]
    # Item 146: the rows the four box-twin counters below read. The
    # grouping above read every row, decided copies included, by design.
    counted = [
        res for doc, res in resolution.items()
        if doc not in (copy_docs or ())
    ]
    return {
        "unresolved_hints": sorted(
            unresolved.values(), key=lambda e: (-e["n_rows"], e["hint"])
        ),
        "resolved": [
            {**e, "hints": sorted(e["hints"])}
            for e in sorted(
                resolved.values(), key=lambda e: (-e["n_rows"], e["card"]["key"])
            )
        ],
        "n_resolved_rows": sum(e["n_rows"] for e in resolved.values()),
        "n_unresolved_rows": sum(e["n_rows"] for e in unresolved.values()),
        "n_no_hint": n_no_hint,
        # A confirmed private row needs NO entity by design (item 41).
        #
        # Item 146: this one DOES take the decided-copy exemption, even
        # though it deliberately does NOT take item 144's
        # `settled_off_card` exemption below. Two different rulings, not an
        # inconsistency: item 144 says the company question still stands on
        # a row settled off the card system, because a card was never what
        # was going to answer it; item 94 says a decided copy is in NO box
        # at all, `needs_entity` included, because nothing done to its
        # company, person, cost center or private flag changes the month.
        # `expense_boxes` is the authority for both and already reads them
        # that way, which is why `counted` is the exemption's only home.
        "n_needs_entity": sum(
            1 for res in counted
            if not res["entity"] and not res.get("private")
        ),
        # Item 40: rows no person owns yet — the count beside MISSING
        # ENTITY. Resolution is card-only, so the fix is a person on the
        # card (Settings > Cards), not a per-row edit.
        #
        # Item 144: which is why a row settled OFF the card system is not
        # counted here either. There is no card to put a person on, so the
        # fix this count points at does not exist for it. It reads the same
        # `settled_off_card` fact `expense_boxes` reads, off the same
        # resolution, so `card_review.n_needs_person` and
        # `summary.n_needs_person` cannot disagree about a row: they were
        # both 1 on July's Tricarico invoice before the ruling and are both
        # 0 after. `n_needs_entity` above deliberately does NOT take THIS
        # exemption: the company question stands on such a row. It does
        # take item 146's decided-copy one, which is a different ruling
        # about a different population; see the note beside it.
        "n_needs_person": sum(
            1 for res in counted
            if not res.get("person") and not res.get("settled_off_card")
        ),
        # Item 41: the private-expense pair, beside the two above.
        "n_suggested_private": sum(
            1 for res in counted if res.get("suggested_private")
        ),
        "n_private": sum(
            1 for res in counted if res.get("private")
        ),
    }


def _row_untrusted(r: Receipt, intake_provenance: dict) -> list[dict]:
    """Every untrusted-text flag that applies to one expense row: the ones
    found in the receipt's own document/file name at parse time, plus the
    ones the carrying mail was stamped with at route time. Deduped by kind."""
    prov = intake_provenance.get(r.document_id) or {}
    out: dict[str, dict] = {}
    for f in (*(r.untrusted_instructions or ()),
              *(prov.get("untrusted_instructions") or ())):
        if isinstance(f, dict) and f.get("kind"):
            out.setdefault(str(f["kind"]), dict(f))
    return [out[k] for k in sorted(out)]


def _expense_review(
    r: Receipt,
    overrides: dict,
    *,
    untrusted_flags: tuple | list = (),
    entity: str | None = None,
    period: tuple[date, date] | None = None,
    date_is_human: bool = False,
    person: str | None = None,
    private: bool = False,
    suggested_private: bool = False,
    needs_cost_center: bool = False,
    settled_outside: bool = False,
) -> dict:
    """Review-by-exception for one expense (receipt-spine). Missing core
    fields first (an expense cannot export cleanly without date / amount /
    currency), then a date that cannot belong to this month (backlog item
    25), then a missing legal entity (Cards R3 — resolves from the
    paying card; unresolved = review, and the export still runs with a
    visible placeholder), then text in the document or its mail that is
    addressed to the tool (`untrusted_flags`, rule_untrusted_inbound), then
    the shared category judgment — the same ready / check / pick vocabulary
    the statement workbench uses.

    `person` (backlog item 40) is checked LAST, only on a row that would
    otherwise be ready: the fix (a person on the card, in Settings) is
    registry work, not row work, so it must never hide a more actionable
    per-row exception. `None` keeps the pre-item-40 behavior (statement-
    workbench callers do not attribute persons).

    `needs_cost_center` (backlog item 47) is checked LAST OF ALL, after
    `person`, for the same reason and one stronger: the fix is registry
    work in Settings, and the flag is silent entirely until the owner has
    defined at least one cost center (the caller passes False while the
    registry is empty). It must never hide a more actionable per-row
    exception.

    `suggested_private` (backlog item 41) takes the entity check's slot:
    a payment method no registered card matches SUGGESTS private money,
    and confirming private or assigning the card is the same decision
    needs_entity was asking for, sharpened. A CONFIRMED private row
    (`private`) skips the entity check entirely — a reimbursement row
    needs a person (`reimburse_to`), not a company entity.

    `settled_outside` (item 144, owner ruling 2026-09-17) is the row's
    settled-off-the-card state (`settled_off_card`). It changes WHICH
    sentence the two card-shaped asks use, never whether they fire. The
    entity ask stops naming the paying card, because on such a row there
    is none to assign and the instruction cannot be followed; it asks for
    the entity directly instead. The person ask goes quiet altogether, for
    the reason the boxes drop `needs_person` (`expense_boxes`): person
    resolution is card-only, so on a row no card paid it is an ask nobody
    can answer."""
    missing = [
        label
        for label, value in (
            ("date", r.detected_date),
            ("amount", r.detected_total),
            ("currency", r.detected_currency),
        )
        if value is None
    ]
    if missing:
        # `missing` rides as structured data so the SPA composes the
        # sentence from its own localized field names; the English prose
        # stays as the fallback (language-contract round, note 4).
        return {
            **_review(
                "check",
                "Missing " + ", ".join(missing) + ". Fill these in before "
                "this expense can export cleanly.",
                "missing_fields",
            ),
            "missing": missing,
        }
    # A date years away from the month it was filed under is the vision
    # read being wrong, not the month (backlog item 25). Never corrected
    # here — the read is reported and a human decides, because inventing
    # the "right" date would be the same mistake with better manners.
    #
    # `date_is_human` is the release valve: the guard questions what the
    # MACHINE read, so once the reviewer has typed a date (or entered the
    # whole expense by hand) her judgment stands and the flag goes quiet.
    # Without it a genuinely old invoice could never be cleared.
    if not date_is_human and outside_period(r.detected_date, period):
        # `outside_period` is false for either None, so both are real here.
        seen, (start, end) = r.detected_date, period  # type: ignore[misc]
        return {
            **_review(
                "check",
                f"Dated {seen.isoformat()}, outside this batch's "
                "month. Receipts print the year in forms that are easy to "
                "misread; check the receipt and correct the date, or leave "
                "it if the receipt really is that old.",
                "date_outside_period",
            ),
            # Structured beside the prose so the SPA composes its own
            # localized sentence (the language contract, round 14+15).
            "date": seen.isoformat(),
            "period": {"start": start.isoformat(), "end": end.isoformat()},
        }
    if suggested_private and not private:
        return _review(
            "check",
            "No registered company card matches this payment method, so "
            "this is suggested as a private expense someone paid out of "
            "pocket. Confirm it as private (naming who gets reimbursed), "
            "or assign or register the company card if there is one.",
            "suggested_private",
        )
    if entity is not None and not entity and not private:
        if settled_outside:
            # Item 144. Same question, an answerable instruction. The
            # generic sentence below opens with "assign this expense's
            # paying card", and on a row settled off the card there is no
            # card to assign and never will be, so the first thing the
            # screen told Criss to do was the one thing she could not.
            return _review(
                "check",
                "This expense was settled outside the card system, so no "
                "card will name the company it belongs to. Set the legal "
                "entity on the row; the export shows a placeholder until "
                "then.",
                "needs_entity_settled_outside",
            )
        return _review(
            "check",
            "No legal entity yet. Assign this expense's paying card (or set "
            "the entity directly) so it posts to the right company; the "
            "export shows a placeholder until then.",
            "needs_entity",
        )
    # Text addressed to an assistant, found in this receipt's document, its
    # file name or the mail that carried it (rule_untrusted_inbound). It is
    # reported, never obeyed. Ranked HERE, not first: the four checks above
    # are per-row work the reviewer can actually finish, and this flag never
    # clears (nothing un-writes what the document said), so first would let a
    # sticky warning hide a missing amount forever. It still outranks the
    # category judgment and the registry-work flags below, because a document
    # steering the tool matters more than which account it posts to. The flag
    # itself is not hidden either way: `expenses[].untrusted_instructions`
    # rides on the row independently of which exception names it.
    flags = tuple(untrusted_flags or ()) or tuple(r.untrusted_instructions or ())
    if flags:
        kinds = ", ".join(sorted({str(f.get("kind")) for f in flags if f.get("kind")}))
        return {
            **_review(
                "check",
                "This receipt (or the mail that carried it) contains text "
                "written at the tool rather than a purchase: " + kinds + ". "
                "It was extracted as data and changed nothing. Read it before "
                "you approve the row.",
                "untrusted_instructions",
            ),
            "untrusted_instructions": [dict(f) for f in flags],
        }
    review = _matched_category_review(r, overrides)
    if review["state"] != "pick" and _kept_invoice_unconfirmed(r, overrides):
        # Item 105. A missing category (pick) is the more actionable ask and
        # still wins; picking one also clears this check.
        return _review(
            "check",
            "The reader took this document for a bank or card statement page, "
            "but it prints its own invoice number and line items, so it was "
            "kept as an expense. Check it is one purchase, then confirm its "
            "category.",
            "invoice_read_as_statement",
        )
    if (
        review["state"] == "ready"
        and person is not None
        and not person
        and not settled_outside
    ):
        # Item 40: every expense belongs to a person, through the card.
        # A row whose card carries no person is not done — but the fix
        # lives in Settings > Cards, so this fires only when nothing
        # more actionable is wrong with the row itself.
        #
        # Item 144: silent on a row settled off the card, which the same
        # ruling drops from the `needs_person` box. The fix this sentence
        # names (a person on its paying card) does not exist for a row no
        # card paid, so the screen and the box would otherwise disagree
        # about whether the row still owes an answer.
        return _review(
            "check",
            "No person owns this expense yet. Add a person to its paying "
            "card in Settings > Cards, so every expense is attributed.",
            "needs_person",
        )
    if review["state"] == "ready" and needs_cost_center:
        # Item 47: registry work of the same class as needs_person, and
        # ranked below it -- a row with no owner is the more actionable
        # gap. Unreachable while the cost-center registry is empty.
        return _review(
            "check",
            "No cost center on this expense yet. Pick the project or purpose "
            "it belongs to, so project spend can be totalled.",
            "needs_cost_center",
        )
    return review


def _expense_account_options(run: RunRow) -> list[str]:
    """The account picker for an expense batch (Phase 5): the scoped
    postable-account labels the categorizer was constrained to (rebuilt from
    the run's `coa_validation` block via `_resolve_categorizer_chart`'s
    fallback). Empty when no chart — the picker offers nothing rather than
    the full unscoped chart.

    Always the company's chart: the per-entity `account_picks` shortlist
    was removed on the owner's ruling 2026-09-17 (note #61), and a value
    stored before then is ignored here."""
    try:
        from ..cli import _resolve_categorizer_chart

        _, labels, _ = _resolve_categorizer_chart(
            run.config or {}, Path(run.work_dir), None, {}
        )
        return labels or []
    except Exception:  # noqa: BLE001 - picker degrades, view never breaks
        return []


def batch_list_summary(store: RunStore, run: RunRow) -> dict:
    """The batch-list row's summary, with the counts the operator compares
    against the batch page derived from the SAME live state that page
    renders — the stored summary is frozen at ingest, so before this a
    reviewer's category edit or manual add never moved the list screen.

    Only the derivable counts are replaced; everything else (cost, parse
    issues, upload issues, statement figures) stays as stored. A batch whose
    summary predates expense counts, or whose snapshot cannot be read, keeps
    exactly what it had: the landing screen must render regardless.
    """
    summary = dict(run.summary or {})
    # Item 67 stores the per-document render outcomes on the run summary, one
    # entry per receipt. The list screen has no use for them and this is the
    # one place the stored summary is served through as-is, so they stop here;
    # the batch page reads them as `receipt_render` per row and one count.
    summary.pop("receipt_render", None)
    snapshot = run.snapshot or {}
    # Item 103: the four charge counters (and the rate over them) are the
    # page's, derived here from the reviewer's effective verdict rather than
    # served as the matcher committed them. A month with no statement has no
    # charges to count and keeps what it stored; a snapshot that cannot be
    # read keeps it too, for the same reason the expense counts below do.
    if has_statement(run):
        try:
            charges, states = month_charge_states(run, store.get_decisions(run.run_id))
        except (KeyError, TypeError, ValueError):
            charges, states = [], {}
        if states:
            summary.update(bucket_counts(states))
            summary["match_rate"] = (
                round(summary["n_matched"] / len(charges) * 100, 1) if charges else 0.0
            )
    # A run whose summary predates expense counts, or whose snapshot has no
    # receipts block yet (created, ingest still running or failed), keeps
    # what it stored: deriving from an empty snapshot would report a real
    # batch as 0 expenses, which is worse than a slightly stale count.
    if "n_categorized" not in summary or "receipts" not in snapshot:
        return summary
    try:
        receipts = baseline_receipts(run)
        overrides = store.get_category_overrides(run.run_id)
        receipts = apply_expense_edits(
            receipts,
            store.get_expense_field_overrides(run.run_id),
            store.get_expense_edits(run.run_id),
            category_overrides=overrides,
            default_entity=(
                ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
            ),
        )
        # Item 94: the list screen's expense count is the batch page's, so
        # it leaves out the same decided copies (the grid's card inheritance
        # first, exactly as the batch page decides them).
        resolutions = store.get_duplicate_resolutions(run.run_id)
        copies = decided_copies(
            run,
            inherit_card_from_copies(
                receipts, resolutions, _batch_card_hints(run.config)
            ),
            resolutions,
            charge_decisions=store.get_decisions(run.run_id),
        )
        # A copy is in no box on the batch page (`expense_boxes`), so the
        # categorized pair counts the same expenses `n_expenses` does.
        counted = [r for r in receipts if r.document_id not in copies]
        n_categorized, n_uncategorized = categorized_counts(
            apply_overrides(counted, overrides)
        )
    except (KeyError, TypeError, ValueError):
        # A malformed snapshot hides ONE batch's counts (it keeps the stored
        # pair) rather than breaking the landing screen. Deliberately narrow:
        # a blind `except Exception` here swallowed a closed-store bug in
        # this very function and served stale numbers that looked fine.
        return summary
    summary["n_expenses"] = len(receipts) - len(copies)
    summary["n_receipts"] = len(receipts)
    summary["n_copies_set_aside"] = len(copies)
    summary["n_categorized"] = n_categorized
    summary["n_uncategorized"] = n_uncategorized
    return summary


def build_expense_view(
    run: RunRow,
    overrides: dict,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    resolutions: dict[str, str] | None = None,
    settings: dict | None = None,
    decisions: dict | None = None,
    trip: dict | None = None,
    settled_elsewhere: dict[str, dict] | None = None,
    edited_at: str | None = None,
    month_batch=None,
    learning_db_path: "Path | None" = None,
) -> dict:
    """Compose the receipt-spine render model for an expense batch: one row
    per expense with the reviewer's edits applied, review-by-exception
    states, duplicate flags, and a receipt-centric summary. The parallel of
    `build_view` (which is NOT modified); the SPA renders `expenses`, never
    `rows`. `settings` (Phase 5) feeds the curated account picker and the
    entity picker options.

    `decisions` (PR 3) is the reviewer's per-charge verdicts, needed only by
    the per-card coverage roll-up: a rejected match un-matches a charge, and
    a card row that ignored that would report a month as further along than
    the workbench says it is. Omitting it is honest for a month with no
    charges (there is nothing to have decided) and wrong for a reconciling
    one, which is why the route passes it.

    `edited_at` (2026-09-16): as on `build_view`, the route's read of the
    edit tables, folded into `updated_at`. A field edit on a month without a
    statement is recorded nowhere else."""
    parse_errors = [tuple(e) for e in (run.snapshot or {}).get("parse_errors", [])]
    # Compose from the EXTRACTION BASELINE, not the stored receipt block: on
    # a month whose statement has been attached the latter is the baked pool
    # (overlay already folded in), so laying the overlay on it again would
    # show a cleared edit as still-edited and report the reviewer's own value
    # as `raw`. Pre-attach the two are identical.
    orig_receipts = baseline_receipts(run)
    # Keep the pre-edit receipts so the vendor object can always show the
    # ORIGINAL extracted name as `raw`, even after a reviewer vendor edit
    # folded a new spelling into `detected_vendor`.
    orig_by_id = {r.document_id: r for r in orig_receipts}
    default_entity = (
        ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
    )
    receipts = apply_expense_edits(
        orig_receipts, field_overrides, edits,
        category_overrides=overrides, default_entity=default_entity,
    )
    # Item 77: typed-in expenses (a delete overwrites the add row, so these
    # are the live ones), as opposed to receipts attached to a charge by hand.
    manual_add_ids = {e["document_id"] for e in edits if e["op"] == "add"}
    # Item 69 round A: the same card inheritance `rematch_month` bakes, so the
    # row's card / entity and the match outcome cannot disagree. Applied to
    # every batch, statement or not: on a collecting month (September 2026 on
    # deploy) a card-less invoice copy leaves "No legal entity yet" the moment
    # its receipt copy names the card. A group ruled `ignore` lends nothing,
    # and an operator-assigned hint word is never overwritten (grid).
    grid_hints = _batch_card_hints(run.config)
    receipts = inherit_card_from_copies(receipts, resolutions, grid_hints)  # grid
    # Item 169: and the card a correction remembers, read live rather than
    # off the stamp ingest left, so a fix taught after this month was
    # ingested reaches it. Silent without a learning store.
    receipts = fill_remembered_cards(
        receipts, learning_db_path, (settings or {}).get("merchants")
    )  # grid
    receipts_dir = Path(run.work_dir) / "receipts"
    intake_provenance = (run.snapshot or {}).get("intake_provenance") or {}
    # Override-applied twins for the `books_as` fan-out (backlog item 2):
    # the export applies category overrides before splitting, so the grid's
    # depiction must too, or the two would disagree after a reclassify.
    # Residual R1: and the chart gate the export runs (`gated_for_posting`,
    # the same call `build_expense_row_groups` makes), with the same chart,
    # or a line whose account the company's chart rejects reads as that
    # account here and as its category in the CSV for the same purchase.
    grid_gate = _coa_gate_from_config(run.config, run.work_dir)
    grid_chart = getattr(grid_gate, "chart", None) if grid_gate is not None else None
    ov_by_doc = {x.document_id: x for x in gated_for_posting(apply_overrides(receipts, overrides), grid_gate)}

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

    expenses = []
    # Item 68: document_id -> whether a file was found behind it. Item 67's
    # render state covers the files; this covers the rows that have none,
    # which are decided without any report build.
    has_file_by_doc: dict[str, bool] = {}
    totals: dict[str, Decimal] = {}
    # Two different questions, two boxes: `ready` is "needs nothing from the
    # reviewer", `categorized` is "has a category" (item 84: both decided per
    # row after the loop, over the same override-applied receipts the rows
    # and the export are built from, and counted from the rows).
    # document_id -> (receipt, card resolution, cost center): the inputs
    # each row's `boxes` are decided from.
    box_inputs: dict[str, tuple] = {}
    # Master data the export uses to resolve Paid Through, so the grid shows
    # the same account (and how it was chosen). coa is None here, matching
    # posting_category above: the grid renders raw names, the export resolves
    # against the chart, and the two agree for the card/default cases.
    exp_cfg = (run.config or {}).get("expense") or {}
    default_pt = exp_cfg.get("default_paid_through")
    card_accts = exp_cfg.get("card_accounts")
    # Per-card coverage (PR 3) reads the charges and their effective states;
    # one read of the snapshot feeds it and item 111 below.
    charges, charge_state_map = month_charge_states(run, decisions or {})
    # Cards R3: one resolution pass feeds the rows' card/entity, the
    # review states, the paid-through card step, and the card_review
    # strip — the same pass the export runs, so they cannot disagree.
    # Item 111: on this payload only, a receipt a charge of this month
    # settles takes that charge's card when it names none of its own.
    # Residual R3: and a receipt settled outside the card suggests no
    # private card (the reviewer already said no card paid it).
    grid_settled_outside = settled_outside_map(run.snapshot or {})
    card_res = resolve_batch_row_cards(
        receipts, run.config, field_overrides,
        settled_cards=settled_charge_cards(run, charges, charge_state_map),
        settled_outside=grid_settled_outside,
        merchants=(settings or {}).get("merchants"),
    )
    # Item 47: the cost-center chain, over the same pass's cards. Silent
    # for every row while the owner has defined no cost centers.
    cost_res = resolve_batch_row_cost_centers(
        receipts, field_overrides, settings=settings, trip=trip,
        card_res=card_res,
    )
    # The window this batch's dates are expected in, for the date guard
    # (backlog item 25). A company month derives it from the operator's
    # label first and the batch's own dates second, over the EDITED
    # receipts, so correcting dates moves the consensus with them. A TRIP
    # takes its own declared range (item 38: trips span month boundaries
    # freely, so a label- or plurality-derived month would flag legitimate
    # rows), padded a month either side because travel spend books early
    # (flights) and settles late; a trip whose entity is gone gets no
    # window at all — never a label-derived one.
    if is_trip_batch(run):
        period = None
        if trip is not None:
            try:
                period = (
                    date.fromisoformat(str(trip.get("start"))) - timedelta(days=31),
                    date.fromisoformat(str(trip.get("end"))) + timedelta(days=31),
                )
            except ValueError:
                period = None
    else:
        period = batch_period(
            run.label, [r.detected_date for r in receipts if r.detected_date]
        )
    # Item 38 x item 40: on a trip, an expense paid by a person who is
    # not on the roster is worth a flag. The person comes off the card
    # chain (or `reimburse_to` on a private row) exactly as item 40
    # resolves it; the roster is the trip's. A flag, never a block, and
    # never a review state: the likely fix is adding the traveler to the
    # roster (a trip edit), not touching the row. None = not a trip (or
    # the entity is gone), so company months carry no key at all; an
    # EMPTY roster flags nothing — there is no stated roster to miss.
    roster = None
    if is_trip_batch(run) and trip is not None:
        roster = {
            str(t).strip().casefold()
            for t in (trip.get("travelers") or [])
            if str(t).strip()
        }
    # Backlog item 36: what month do these receipts collectively read as?
    # Confirm-first surface for the SPA banner — the label stays the only
    # authority (item 25 ruling: nothing about dates is auto-corrected);
    # this exposes the dates-plurality consensus the guard above already
    # computes internally, so the operator can be OFFERED the rename
    # instead of having to notice the mismatch. None when fewer than 4
    # dated expenses or no clear winner (month_from_dates rules).
    _dated = [r.detected_date for r in receipts if r.detected_date]
    # A trip spans month boundaries freely (item 38), so the month-rename
    # banner is meaningless there: never offer one on a trip batch.
    _consensus = None if is_trip_batch(run) else month_from_dates(_dated)
    if _consensus is None:
        period_suggestion = None
    else:
        _label_month = month_from_label(run.label)
        period_suggestion = {
            "month": f"{_consensus[0]:04d}-{_consensus[1]:02d}",
            "label_month": (
                f"{_label_month[0]:04d}-{_label_month[1]:02d}"
                if _label_month else None
            ),
            "n_dates": len(_dated),
            "n_in_month": sum(
                1 for d in _dated if (d.year, d.month) == _consensus
            ),
        }
    # §18 duplicate groups, receipt-kind only (no charges in an expense
    # batch), each decided by the item-74 ladder with the reviewer's rulings
    # outranking it: the same decisions, evidence and fields the run payload
    # carries, so the grid and the workbench cannot disagree on a group.
    # Decided before the rows because item 94 needs the copies for the total.
    resolutions = resolutions or {}
    grid_decisions = duplicate_decisions(run, receipts, resolutions)
    # Item 94 (owner ruling 2026-09-17): a decided copy stays on screen as a
    # row, marker and "Not a copy" undo included, and leaves the count and
    # the totals. The one predicate every listing surface reads.
    grid_copies = decided_copies(
        run, receipts, resolutions,
        charge_decisions=decisions, receipt_decisions=grid_decisions,
    )
    for r in receipts:
        res = card_res.get(r.document_id) or {
            "hint": "", "card": None, "entity": r.legal_entity_id or "",
            "entity_source": "batch", "person": "", "person_source": "none",
            "private": False, "reimburse_to": "", "suggested_private": False,
            "can_mark_private": True,
            "ambiguous": False, "card_map_blocked": False,
            # The card pass sees every receipt, so this branch is defensive
            # only; it still spells the item-144 fact rather than assuming
            # False, because a row that fell back here and WAS settled
            # outside would silently get the pre-ruling answers.
            "settled_off_card": settled_off_card(
                grid_settled_outside.get(r.document_id)
            ),
        }
        cost = cost_res.get(r.document_id) or UNRESOLVED_COST_CENTER
        # Item 144: one fact, read off the resolution the card pass stamped
        # it on, so the boxes, the review sentence and the card strip's
        # `n_needs_person` cannot answer the same question differently.
        row_settled_outside = bool(res.get("settled_off_card"))
        box_inputs[r.document_id] = (r, res, cost, row_settled_outside)
        review = _expense_review(
            r, overrides, entity=res["entity"], period=period,
            untrusted_flags=_row_untrusted(r, intake_provenance),
            person=res["person"],
            private=res["private"],
            suggested_private=res["suggested_private"],
            needs_cost_center=cost.needs,
            settled_outside=row_settled_outside,
            # A hand-typed date, or a whole expense entered by hand, is the
            # reviewer's own value; the guard only questions the machine's.
            date_is_human=(
                "date" in field_overrides.get(r.document_id, {})
                or r.document_id.startswith("manual:")
            ),
        )
        posting = _row_posting_category(r, overrides, None)
        # Expense grid shows WHY the category is what it is in the reviewer's
        # coarse vocabulary (registry | learned | llm | override); the fine
        # tiers stay on each line item and on the reconcile workbench.
        if posting is not None:
            posting = {**posting, "source": _coarse_source_join(posting.get("source"))}
        pt_account, pt_source = resolve_paid_through(
            r,
            field_overrides.get(r.document_id, {}).get("paid_through") or None,
            default_pt, None, None, None, card_accts,
            card_hint_account=(
                res["card"].zoho_account if res["card"] is not None else None
            ),
            card_map_blocked=res["card_map_blocked"],
        )
        # Item 41: a confirmed private expense was paid out of somebody's
        # pocket, not through a company account. Same strings the CSV
        # writes (_expense_export_inputs), so grid and export agree.
        if res["private"]:
            pt_account = (
                f"Private ({res['reimburse_to']})"
                if res["reimburse_to"] else "Private"
            )
            pt_source = "private"
        rv = _receipt_view(
            r, overrides, work_dir=receipts_dir.parent, expense_mode=True,
        )
        # An expense batch's receipt files live under the run's receipts
        # dir named `<document_id>`. HONEST availability: a manual expense
        # add has a `manual:` id and NO file — the generic prefix claim
        # rendered a View button that 404s (note 8). `receipt_image_file`
        # is that resolution, and since item 52 it is also what fills
        # `receipt_image_available` on BOTH payloads, so the run payload
        # can no longer answer the same question differently.
        hit = receipt_image_file(
            receipts_dir.parent, r.document_id, expense_mode=True
        )
        has_file = hit is not None
        # attach files are stored `{key}__{original-name}`; a file sitting
        # in receipts/ IS the document id.
        source_name = (
            r.document_id
            if hit is None or hit.parent == receipts_dir
            else hit.name.split("__", 1)[-1]
        )
        # Item 68: whether the report builder would find anything to read
        # for this row, resolved exactly the way `_evidence_item` does.
        has_file_by_doc[r.document_id] = has_file
        # Which upload/mail this row came from (spool prefix stripped);
        # empty for rows the operator typed in with no document.
        rv["source_file"] = _display_name(source_name) if has_file else ""
        books_as = [
            {
                # `(uncategorized - assign)` is the EXPORT artifact's
                # placeholder (English is the CSV's contract); the grid
                # gets a sentinel the SPA localizes instead.
                "account": None if account == _UNCATEGORIZED else account,
                "unassigned": account == _UNCATEGORIZED,
                "amount": _fmt_amount(amt),
            }
            for account, amt, _descs in expense_posting_parts(
                ov_by_doc.get(r.document_id, r), chart_of_accounts=grid_chart
            )
        ]
        ccy = r.detected_currency or "?"
        if r.detected_total is not None and r.document_id not in grid_copies:
            totals[ccy] = totals.get(ccy, Decimal("0")) + r.detected_total
        expenses.append({
            **rv,
            # Cards R3: the row's entity is the RESOLVED chain value
            # (override -> card -> stamped), with its provenance beside it;
            # the paying-card object renders the assignment state and the
            # raw hint stays visible for the review strip.
            "legal_entity_id": res["entity"],
            "entity_source": res["entity_source"],
            # Item 40: who this expense belongs to, through the card — the
            # last link of the same chain, with its provenance beside it.
            # Parallel fields; "" / "none" until the card carries a person.
            "person": res["person"],
            "person_source": res["person_source"],
            # Item 47: which project or purpose this expense belongs to,
            # with its provenance and a parallel human-readable label:
            # an un-updated SPA degrades to correct text instead of
            # somebody else's copy (contract rule 5).
            **cost.as_fields(),
            # Item 41: the private-expense state. `reimburse_to_prefill` is
            # the ONE sanctioned use of the sender claim — offered only on
            # a suggested/confirmed private row, shown as the claim it is,
            # and never resolved into `person` without operator confirm.
            "private": res["private"],
            "reimburse_to": res["reimburse_to"],
            "suggested_private": res["suggested_private"],
            # Owner 2026-09-17: the private-card option applies only where
            # no company card paid (see resolve_batch_row_cards). The two
            # write routes refuse the same rows, so the SPA gates on this.
            "can_mark_private": res.get("can_mark_private", True),
            "reimburse_to_prefill": (
                ((intake_provenance.get(r.document_id) or {}).get("person") or "")
                if (res["suggested_private"] or res["private"]) else ""
            ),
            "payment_hint": res["hint"],
            # Item 87: where `card` came from: hint (the printed payment
            # method or a batch hint assignment), override (a per-row fix
            # this month), learned (remembered from an earlier month's
            # fix), settled_charge (item 111: the card of this month's
            # charge the receipt settles), or none.
            "card_source": res.get("card_source", "none"),
            # Note #60: "38" when the card was named by a masked two-digit
            # ending alone; "" otherwise. Parallel to `card_source`, which
            # keeps its four values.
            "card_ending": res.get("card_ending", ""),
            "card": (
                {
                    "key": res["card"].key,
                    "label": res["card"].display_label,
                    "entity": res["card"].entity,
                    "person": res["card"].person,
                    "hint": res["hint"],
                }
                if res["card"] is not None
                else None
            ),
            # Canonical vendor provenance (2026-07-29): replace the bare
            # `vendor` string from _receipt_view with {display, raw, source}
            # so the grid shows the canonical name AND why it differs. This is
            # an expense-grid-only shape; the reconcile workbench keeps the
            # string (_receipt_view is unchanged there).
            "vendor": _expense_vendor_view(
                r, orig_by_id.get(r.document_id),
                field_overrides.get(r.document_id, {}),
            ),
            # Receipt-first fields _receipt_view does not carry (build_view
            # consumers are unchanged; these are expense-row additions).
            "tax": _fmt_amount(r.detected_tax),
            "tax_label": r.tax_label or "",
            "customer": field_overrides.get(r.document_id, {}).get("customer", ""),
            "posting_category": posting,
            "posting_paid_through": {"account": pt_account, "source": pt_source},
            "review": review,
            # Note #62: the category is the tool's guess and a reviewer can
            # keep it as it is (`POST .../confirm-category`). Judged on the
            # category alone, so it is offered even while another exception
            # is the row's headline.
            "category_confirmable": category_confirmable(r, overrides),
            "is_manual": r.document_id.startswith("manual:"),
            "edited_fields": sorted(field_overrides.get(r.document_id, {})),
            # Split depiction (backlog item 2): how THIS receipt will book
            # in the Zoho export — one part per account, sums exact, the
            # same fan-out `build_expense_rows` writes (shared helper).
            "books_as": books_as,
            "is_split": len(books_as) > 1,
            # Mail-intake provenance (who submitted this receipt): present
            # only for receipts that arrived via the intake mailbox —
            # {person, source: alias|sender, address, received_at}.
            "submitted_by": intake_provenance.get(r.document_id),
            # Agent-directed text found in this receipt or its mail
            # (rule_untrusted_inbound): shown for a human, acted on by nothing.
            "untrusted_instructions": _row_untrusted(r, intake_provenance),
        })
        if roster is not None:
            # Trip batches only (the key is absent on company months).
            # A row with no resolved person is n_needs_person's business,
            # not a mismatch; exact match after trim+casefold, because
            # persons and roster entries share item 40's one vocabulary
            # (free-text names entered by the same operator).
            expenses[-1]["roster_mismatch"] = bool(
                res["person"] and roster
                and str(res["person"]).strip().casefold() not in roster
            )
        # Item 155: the filing instruction the sender typed above the
        # forward, lifted out of provenance to its own row key the way
        # `untrusted_instructions` is, so the screen renders it beside the
        # entity decision it speaks to. Absent when the mail carried none.
        _note = (intake_provenance.get(r.document_id) or {}).get("operator_note")
        if _note:
            expenses[-1]["operator_note"] = str(_note)
        # Item 160 (feedback note #71): name the lines the category verdict
        # is actually about. `posting_category` is the roll-up of the lines
        # that DO carry one, so "Software & Subscriptions" and "one or more
        # receipt lines still need a category" are both true at once; beside
        # a filled category field the sentence reads as a mistake while it
        # names nothing. Built from `uncategorized_line_indexes`, the same
        # predicate the verdict reads, so the two cannot drift. Absent on
        # every row whose lines all carry a category, which is every row an
        # older backend served.
        _unc = uncategorized_line_indexes(r, overrides)
        if _unc:
            _lines = r.line_items or ()
            expenses[-1]["uncategorized_lines"] = [
                {
                    "index": i,
                    "description": _lines[i].description or "",
                    "line_total": _fmt_amount(_lines[i].line_total),
                }
                for i in _unc
            ]
        if r.document_id in grid_copies:
            # Item 94: the row stays, the money does not count. Absent on
            # every row that counts, which is every row an older backend
            # served, so absent keeps reading "counts".
            expenses[-1]["counts_in_total"] = False
        # Item 77: a reviewer-typed date that puts this receipt in another
        # month offers the move (POST .../expenses/{id}/move). A `manual:` id
        # that is not a typed-in add is a receipt attached to a charge by
        # hand; it belongs to that charge, not to a month, so it is never
        # offered. `month_batch` (the route's lookup) names the batch the
        # move would join; absent when the move would create the month.
        move_to = month_move_for_row(
            r, period=period, is_trip=is_trip_batch(run),
            date_is_human=(
                "date" in field_overrides.get(r.document_id, {})
                or r.document_id in manual_add_ids
            ),
        )
        if move_to is not None and (
            not r.document_id.startswith("manual:")
            or r.document_id in manual_add_ids
        ):
            from .intake_mail import _month_human

            offer = {"month": move_to, "label": _month_human(move_to)}
            joins = month_batch(move_to) if month_batch is not None else None
            if joins:
                offer["batch_id"] = joins
            expenses[-1]["month_move"] = offer
        # Item 77 amendment: what the receipt prints beside its date and its
        # labelled numbers. Absent when not read (every receipt read before
        # the fields existed), never null.
        for key, value in (
            ("time", r.detected_time),
            ("invoice_number", r.invoice_number),
            ("receipt_number", r.receipt_number),
        ):
            if value:
                expenses[-1][key] = value

    # Category-variance chip (backlog item 8): a vendor whose receipts in
    # THIS batch carry different (non-null) posting categories gets flagged
    # on every one of its rows, so the SPA renders the chip + the vendor
    # drill-down with no client-side judgment. Grouping keys on the DISPLAY
    # vendor (canonical when the registry knows it), case-insensitive.
    by_vendor: dict[str, list[dict]] = {}
    for e in expenses:
        display = str((e.get("vendor") or {}).get("display") or "").strip()
        if display:
            by_vendor.setdefault(display.casefold(), []).append(e)
    for group in by_vendor.values():
        cats = sorted({
            (e.get("posting_category") or {}).get("category")
            for e in group
            if (e.get("posting_category") or {}).get("category")
        })
        for e in group:
            e["category_variance"] = {
                "varies": len(cats) > 1,
                "categories": cats,
                "n_vendor_receipts": len(group),
            }
    for e in expenses:
        e.setdefault("category_variance", {
            "varies": False, "categories": [], "n_vendor_receipts": 1,
        })

    duplicate_groups = [duplicate_group_entry(dec) for dec in grid_decisions]  # grid

    # The same groups carried ON the row (2026-08-28). This is the one
    # that matters most: an expense batch is where a twice-forwarded
    # invoice becomes two expenses, and this grid is where somebody has to
    # notice. None on a row in no live group.
    dup_flags = duplicate_row_flags(duplicate_groups, kind="receipt")
    for e in expenses:
        e["duplicate"] = dup_flags.get(e["document_id"])

    # R4 (item 38): a receipt of this batch settled by another run's
    # charge (a trip receipt matched by a company month's statement) names
    # its settler. Absent-unless-set, mirroring the run payload.
    if settled_elsewhere:
        for e in expenses:
            hit = settled_elsewhere.get(e.get("document_id"))
            if hit is not None:
                e["settled_by"] = hit

    # Item 67: what the last report build did with this expense's receipt.
    # "ok" means its pages are in the document; "failed" means the file could
    # not be turned into pages at all, so the report carries a caption naming
    # it and nothing behind that caption. ABSENT until a report has been built
    # for the month, because renderability is not knowable before then: a
    # missing key means "not established", never "fine".
    render_state = (run.summary or {}).get("receipt_render") or {}
    for e in expenses:
        state = (render_state.get(e.get("document_id")) or {}).get("render")
        if state:
            e["receipt_render"] = state
    # Item 68: `receipt_image_available` answers "is there a file the app can
    # show you", and item 67's `receipt_render` answers "did that file
    # break". Neither answers the one the reader of the report is holding:
    # does this expense have a PAGE. It is the positive form, it covers the
    # rows the render state says nothing about (no file, so no page, and no
    # build needed to know it), and it is what a coverage count can be
    # summed from. Derived from 67's state rather than decided again: one
    # fact, one channel. PARALLEL and ABSENT until known, per rule 1.
    pages_known: dict[str, bool] = {}
    for e in expenses:
        doc = e["document_id"]
        if not has_file_by_doc.get(doc, False):
            pages_known[doc] = False
        elif e.get("receipt_render"):
            pages_known[doc] = e["receipt_render"] == "ok"
        else:
            continue
        e["receipt_in_report"] = pages_known[doc]

    # Item 62: the disposition rides the grid row, absent unless set. This
    # view removes NOTHING -- the receipt is still an expense of this month
    # and still prints in the report; only the reconciliation pool on the
    # run payload lets it go. (Read above the row loop since residual R3:
    # the card pass needs it to stop suggesting a private card on a receipt
    # the reviewer already settled outside the card.)
    if grid_settled_outside:
        for e in expenses:
            hit = grid_settled_outside.get(e.get("document_id"))
            if hit is not None:
                e["settled_outside"] = hit

    has_image_info = any(r.has_receipt_image for r in receipts)
    # Item 84: the boxes each row belongs to, decided once per row, and every
    # box count below is the number of rows carrying that box, so a box that
    # opens its rows can never list a different number than it shows.
    for e in expenses:
        receipt, res, cost, row_settled_outside = box_inputs[e["document_id"]]
        e["boxes"] = expense_boxes(
            categorized=is_categorized(ov_by_doc.get(e["document_id"], receipt)),
            review_state=e["review"]["state"],
            res=res,
            needs_cost_center=cost.needs,
            image_missing=receipt_image_missing(
                has_image_info=has_image_info,
                available=bool(e.get("receipt_image_available")),
                referenced=receipt.has_receipt_image,
            ),
            render_failed=e.get("receipt_render") == "failed",
            # Item 94: a decided copy is in no box, so every box count
            # below leaves it out the way `n_expenses` does.
            copy=e["document_id"] in grid_copies,
            # Item 144: a row settled off the card system is in no
            # `needs_person` box; the same fact the review sentence read.
            settled_outside=row_settled_outside,
        )

    # Note item T3: the statement line this expense settles, inside this
    # month. The charge side is read from `charge_state_map`, the month's
    # EFFECTIVE settlement (the same map the coverage roll-up reads), not
    # from the raw decisions: item 103 closed the split where the stored
    # outcome named one receipt on two charges while the page named one.
    # A receipt that settles nothing here carries none of these keys; a
    # cross-batch settlement keeps answering with `settled_by`, which
    # names the other month and is a different question.
    tx_by_settled_doc: dict[str, str] = {}
    for charge_tx_id, charge_state in (charge_state_map or {}).items():
        held = (charge_state or {}).get("held_doc")
        if held and held not in tx_by_settled_doc:
            tx_by_settled_doc[str(held)] = str(charge_tx_id)
    if tx_by_settled_doc:
        grid_origin = origins_from_snapshot(run.snapshot)
        for e in expenses:
            settling_tx = tx_by_settled_doc.get(e.get("document_id"))
            if not settling_tx:
                continue
            e["transaction_id"] = settling_tx
            e.update(origin_fields(grid_origin.get(settling_tx)))

    def n_box(box: str) -> int:
        return sum(1 for e in expenses if box in e["boxes"])

    n_categorized, n_uncategorized = n_box("categorized"), n_box("uncategorized")
    n_ready = n_box("ready")
    set_aside = set_aside_view(run.snapshot or {}, receipts_dir.parent)
    summary = {
        "mode": MODE_EXPENSE_GENERATION,
        # Item 94: the expenses the month counts, decided copies left out.
        # `n_receipts` keeps counting every document on screen, so
        # n_receipts == n_expenses + n_copies_set_aside. A copy is in no box
        # either, so n_categorized + n_uncategorized == n_expenses.
        "n_expenses": len(expenses) - len(grid_copies),
        "n_receipts": len(expenses),
        # Item 94: the copies the count and `totals_by_ccy` leave out, and
        # what they add up to per currency. Same name and same set as the
        # run payload's count (items 83 + 75).
        "n_copies_set_aside": len(grid_copies),
        "copies_set_aside_by_ccy": {
            ccy: f"{amt:,.2f}"
            for ccy, amt in sorted(
                copies_set_aside_totals(receipts, grid_copies).items()
            )
        },
        "n_set_aside": sum(1 for e in set_aside if not e["restored"]),
        # Item 62, same name and same question as the run payload.
        "n_settled_outside": len(grid_settled_outside),
        "n_categorized": n_categorized,
        "n_uncategorized": n_uncategorized,
        # Rows the reviewer can leave alone entirely (category AND entity
        # AND the core fields). The batch page's headline count until
        # 2026-08-22, when it was mislabelled as "categorized".
        "n_ready": n_ready,
        # Item 57: the same verdict the workbench carries, so whichever
        # payload the SPA renders for a reconciling month says the month
        # is broken. `checked: false` before a statement is loaded.
        "month_health": run_month_health(run),
        "n_review": sum(
            1 for e in expenses if e["review"]["state"] in ("check", "pick")
        ),
        "n_unknown_currency": sum(1 for r in receipts if r.detected_currency is None),
        # Cards R3: rows whose entity the chain could not resolve — the
        # `needs_entity` review population (never an export blocker).
        # A confirmed private row needs NO entity by design (item 41), so
        # it does not count as missing one.
        "n_needs_entity": n_box("needs_entity"),
        # Item 40: rows no person owns yet. Sits beside n_needs_entity;
        # the fix is a person on the card, not a per-row edit.
        "n_needs_person": n_box("needs_person"),
        # Item 84 (owner ruling 2026-09-16): the two boxes above are one box
        # on the page, because the fix is one action either way (pick the
        # card, or mark the receipt private). Rows missing either.
        "n_needs_company_or_person": n_box("needs_company_or_person"),
        # Item 47: rows with no cost center, once at least one is
        # defined. Structurally 0 while the registry is empty, which is
        # the whole first phase; the SPA hides the chip at 0.
        "n_needs_cost_center": n_box("needs_cost_center"),
        # Item 41: unconfirmed private-expense suggestions, and rows the
        # operator has confirmed private (reimbursement rows).
        "n_suggested_private": n_box("suggested_private"),
        "n_private": n_box("private"),
        "n_learned_lines": n_learned_lines,
        "has_image_info": has_image_info,
        # Item 84: a row whose receipt the app can show is not missing its
        # image, whatever the extraction recorded (`receipt_image_missing`).
        "n_missing_receipt_image": n_box("missing_receipt_image"),
        "n_duplicate_groups": len(duplicate_groups),
        # Copies that are redundant (here, one per extra row: an expense
        # batch's spine IS the receipts). Since item 94 `totals_by_ccy`
        # below leaves out every DECIDED copy (`n_copies_set_aside`); this
        # count keeps its question and also counts a copy nobody decided.
        "n_duplicate_copies": n_extra_copies(dup_flags),
        # Item 74(d): groups nobody has decided; same rule as the run view.
        "n_duplicate_groups_open": sum(
            1 for dec in grid_decisions if dec.state == STATE_OPEN
        ),
        "totals_by_ccy": {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(totals.items())
        },
        "n_parse_errors": count_parse_issues(parse_errors)["errors"],
        "n_parse_notes": count_parse_issues(parse_errors)["notes"],
        "llm_cost_usd": run.summary.get("llm_cost_usd", "0"),
        "ai_unavailable": run.summary.get("ai_unavailable", False),
        "upload_issues": run.summary.get("upload_issues", []),
        # Absent on every run created before item 20; the SPA falls back to
        # the prose whenever this list is empty.
        "upload_issue_details": run.summary.get("upload_issue_details", []),
        # Item 39 origin marker: "intake" when a mailed receipt created
        # this month itself; null on operator-created batches (parallel).
        "created_by": run.summary.get("created_by"),
    }
    if roster is not None:
        # Trip batches only: how many rows a person OUTSIDE the roster
        # paid for. Absent on company months, like the row flag.
        summary["n_roster_mismatch"] = sum(
            1 for e in expenses if e.get("roster_mismatch")
        )
    # Item 77: rows whose typed date belongs to another month.
    summary["n_month_moves"] = sum(1 for e in expenses if e.get("month_move"))
    # Item 68: how many expenses have a receipt PAGE in the built report.
    # ABSENT while any row's verdict is still unknown, rather than present
    # and quietly short by the rows nobody has decided yet — an undercount
    # here would read as "receipts are missing" and send somebody hunting
    # for files that are fine. Complete once the month's report has been
    # built, which is also when item 67's render state arrives.
    if len(pages_known) == len(expenses):
        summary["n_receipts_in_report"] = sum(
            1 for known in pages_known.values() if known
        )

    # Phase 5 pickers: entities the reviewer can assign (the real entities
    # from the CoA provisioning + the card->entity map + the settings
    # registry, plus this batch's own default), and the curated account list.
    entity_options = available_entities(settings, default_entity)

    # Per-card coverage (PR 3). The charges and states read above, so every
    # charge rolled up has a state that was computed for it.
    coverage, _keys = month_coverage(run, charges, charge_state_map)
    # Item 59: same count the workbench carries, from the same charge set
    # the coverage panel rolls up. 0 before a statement is loaded.
    summary["n_charges_no_entity"] = sum(
        1 for t in charges if not (t.legal_entity_id or "").strip()
    )
    # Item 65: expenses whose amount could not be read, so they are in no
    # total -- `totals_by_ccy` above skips them and the report's listing
    # cannot print them. The payload half of the report's "excluded from
    # the total" footer; 0 on a month where every amount parsed.
    summary["n_amounts_unreadable"] = sum(
        1 for r in receipts
        if r.detected_total is None and r.document_id not in grid_copies
    )
    # Item 67: how many of this month's receipts produced no page in the
    # report. Present only once a report has been built, the same rule the
    # row's `receipt_render` follows: a 0 that actually means "nobody has
    # built one yet" is the confidently-wrong shape contract rule 5 exists to
    # prevent, and this count's whole job is telling a reviewer to go look.
    if render_state:
        summary["n_receipts_unrenderable"] = n_box("receipts_unrenderable")
    # Item 129: same helper and same snapshot keys as the run payload.
    visibility = rematch_visibility(run.snapshot)

    return {
        "run_id": run.run_id,
        "label": run.label,
        "created_at": run.created_at,
        # When the month last changed (2026-09-16), same helper and same
        # sources as the run payload, plus the edit list this view receives.
        "updated_at": month_updated_at(
            run, decisions=decisions, edits=edits, edited_at=edited_at
        ),
        # Item 129 (2026-09-18): the last committed re-match and any owed
        # one, same shape and same null rule as on the run payload.
        "last_rematch": visibility["last_rematch"],
        "rematch_pending": visibility["rematch_pending"],
        "mode": MODE_EXPENSE_GENERATION,
        # Item 38: the declared kind, "company-month" on every batch that
        # predates the split (absent marker reads as company). Scalar,
        # parallel — a stale SPA renders exactly what it rendered before.
        "batch_type": batch_type(run),
        # The trip this batch belongs to (entity fields incl. the
        # travelers roster), null on every company month.
        "trip": trip,
        "llm_enabled": run.llm_enabled,
        "has_coa": run.has_coa,
        "legal_entity_id": default_entity,
        # Batch lifecycle: True once a statement was attached. The month is
        # NOT frozen by it (2b-2); reconciliation review lives in the
        # workbench while receipts and further statements keep arriving.
        "has_statement": has_statement(run),
        # Which statements have been loaded, over what periods, and what each
        # upload added (PR 2b-2b-2). The month page is where the next one is
        # uploaded, so it is where the answer belongs. Parallel field: empty
        # on every run created before it, reconciling ones included.
        "statements": month_statements(run),
        # The same uploads seen per CARD (PR 3), which is how the loading is
        # actually organized. Identical to the run payload's `coverage` for
        # the same month, by construction: both roll up the one
        # `charge_states` map, so the grid and the workbench cannot report
        # a month at two different stages of done.
        "coverage": coverage,
        # The last incremental receipt-add's summary (counts / cost /
        # skipped files), or None when receipts only came in at creation.
        "expense_ingest": run.snapshot.get("expense_ingest"),
        # Backlog item 36: the dates-plurality month these receipts read
        # as, for the SPA's confirm-first rename banner. Object or null;
        # null whenever no consensus exists. The label stays authoritative.
        "period_suggestion": period_suggestion,
        "summary": summary,
        "expenses": expenses,
        # Cards R3: the card-review strip — unresolved payment hints
        # grouped server-side (generic tenders marked: assignable, never
        # auto-resolved), resolved cards with hit counts, and the
        # needs-entity population.
        # Item 146: the month's decided copies, so the strip's four
        # box-twin counters answer `summary` exactly. `grid_copies` is the
        # same set every listing surface reads.
        "card_review": build_card_review(card_res, copy_docs=set(grid_copies)),
        # The set-aside strip (backlog item 1): what the quarantine
        # excluded, why, and whether the reviewer restored it.
        "set_aside": set_aside,
        "duplicate_groups": duplicate_groups,
        "category_options": list(EXPENSE_CATEGORIES),
        # The curated GL leaves this batch may post to, per entity,
        # served BESIDE the eight rather than replacing them: a
        # published SPA keeps rendering category_options until a
        # bundle that reads these is published. Absent entity = not
        # covered by the curated chart, which is not the same fact
        # as an entity with nothing to post to.
        "gl_accounts": gl_account_options(
            settings, (run.config or {}).get(GL_ENTITY_ORGS_KEY)),
        "gl_revision": gl_revision(),
        "category_vocabulary": category_vocabulary(run),
        "account_options": _expense_account_options(run),
        "entity_options": entity_options,
        # Item 47: the row picker's list, active entries only, name-sorted,
        # each with its display-only kind. Empty while the owner has defined
        # none, which is the state the picker renders as "no cost centers
        # defined yet" rather than as an error.
        "cost_center_options": CostCenterRegistry.from_settings(
            settings
        ).options(),
        "parse_errors": parse_errors,
        "parse_issues": [
            {
                "file": i[0],
                "line": i[1],
                "message": i[2],
                "severity": parse_issue_severity(i),
            }
            for i in parse_errors
        ],
    }


def _private_reimbursements(
    field_overrides: dict[str, dict[str, str]],
) -> dict[str, str]:
    """The batch's operator-CONFIRMED private expenses (backlog item 41):
    ``{document_id: reimburse_to}``. Confirmation lives in the same
    field-override store as every other per-expense decision, so it
    survives re-ingest and clears with `private: false`. A `private`
    flag WITHOUT a reimburse_to is not a confirmation (same rule as
    `resolve_batch_row_cards`): a report must never state a
    reimbursement owed to nobody."""
    return {
        doc: str(fields.get("reimburse_to") or "").strip()
        for doc, fields in field_overrides.items()
        if str(fields.get("private") or "").strip() == "1"
        and str(fields.get("reimburse_to") or "").strip()
    }


def _expense_export_inputs(
    run: RunRow,
    overrides: dict,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    dup_resolutions: dict[str, str] | None = None,
    settled_cards: dict[str, str] | None = None,
    merchants: dict | None = None,
    learning_db_path: "Path | None" = None,
) -> tuple[list, dict]:
    """`(receipts, kwargs)` for the expense export — the overlay order the
    view uses (`apply_expense_edits` then `apply_overrides`) plus the card /
    entity / chart resolution the rows need.

    Extracted so the CSV and the month's PDF report are built from ONE setup:
    the report quotes the export's rows, and a change to how a row resolves
    reaches both or neither.

    `dup_resolutions` (item 69 round A) is the run's duplicate resolutions,
    so a group the reviewer ruled "not a duplicate" lends no card here
    either; a caller without a store in hand passes None (no group ruled).

    `settled_cards` (item 111, `export_settled_cards`): the CSV and the month
    report pass the Expenses payload's card of the charge each receipt
    settles, so a row the screen resolved from its charge never prints
    `(entity - assign)` there. The match-time readers of this function (the
    adjacent and trip pools) pass nothing and stay as they were."""
    # The extraction baseline, for the same reason the grid uses it: the
    # export applies the overlay, and on an attached month the stored receipt
    # block already has it baked in. Grid and export move together.
    receipts = baseline_receipts(run)
    default_entity = (
        ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
    )
    receipts = apply_expense_edits(
        receipts, field_overrides, edits,
        category_overrides=overrides, default_entity=default_entity,
    )
    # Item 69 round A: the grid's card inheritance, so grid and export move
    # together on a copy that borrowed its card.
    export_hints = _batch_card_hints(run.config)
    receipts = inherit_card_from_copies(receipts, dup_resolutions, export_hints)  # export
    # Item 169: the grid's live read of a remembered card, so the file a
    # reviewer downloads files a receipt under the card the screen showed it
    # on. Cards R3 is the whole reason this sits on both paths.
    receipts = fill_remembered_cards(
        receipts, learning_db_path, merchants
    )  # export
    receipts = apply_overrides(receipts, overrides)
    coa_gate = _coa_gate_from_config(run.config, run.work_dir)
    chart = getattr(coa_gate, "chart", None) if coa_gate is not None else None
    customer_by_doc = {
        doc: fields["customer"]
        for doc, fields in field_overrides.items()
        if fields.get("customer")
    }
    # Cards R3: the export runs the SAME card/entity resolution pass the
    # grid renders (assign a card after an export, re-export, and the new
    # file carries it — exports are regenerable, never stale by design).
    card_res = resolve_batch_row_cards(
        receipts, run.config, field_overrides, settled_cards=settled_cards,
        merchants=merchants,
    )
    # Item 41: a confirmed private expense was paid out of somebody's
    # pocket. In the one-file export it stays a row (mixed-entity ruling:
    # one file, entity as a column) with both columns saying so — the
    # same strings the grid renders, so the two cannot disagree.
    private_by_doc = _private_reimbursements(field_overrides)
    entity_by_doc = {
        doc: res["entity"] for doc, res in card_res.items() if res["entity"]
    }
    paid_through_by_doc: dict[str, str] = {}
    for doc, person in private_by_doc.items():
        entity_by_doc[doc] = "(private expense)"
        paid_through_by_doc[doc] = f"Private ({person})" if person else "Private"
    kwargs = dict(
        chart_of_accounts=chart,
        coa_gate=coa_gate,
        default_paid_through=(
            (run.config or {}).get("expense") or {}
        ).get("default_paid_through"),
        card_accounts=(
            (run.config or {}).get("expense") or {}
        ).get("card_accounts"),
        customer_by_doc=customer_by_doc,
        entity_by_doc=entity_by_doc,
        paid_through_by_doc=paid_through_by_doc,
        card_hint_accounts={
            doc: res["card"].zoho_account
            for doc, res in card_res.items()
            if res["card"] is not None and res["card"].zoho_account
        },
        card_map_blocked_docs={
            doc for doc, res in card_res.items() if res["card_map_blocked"]
        },
    )
    return receipts, kwargs


def regenerate_expense_export(
    run: RunRow,
    overrides: dict,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    dup_resolutions: dict[str, str] | None = None,
    charge_decisions: dict | None = None,
    merchants: dict | None = None,
    learning_db_path: "Path | None" = None,
) -> Path:
    """Write the expense CSV for a batch with every reviewer edit applied.
    Returns the path.

    Item 94: a decided copy (`decided_copies`) writes no row; one line under
    the rows names the copies set aside and what they add up to.

    Item 111: a receipt this month's charge settles resolves its company and
    paid-through from that charge's card, as the Expenses page shows it."""
    csv_settled = export_settled_cards(run, charge_decisions)
    receipts, kwargs = _expense_export_inputs(
        run, overrides, field_overrides, edits, dup_resolutions,
        settled_cards=csv_settled, merchants=merchants,
        learning_db_path=learning_db_path,
    )
    copies = decided_copies(
        run, receipts, dup_resolutions, charge_decisions=charge_decisions,
    )
    out_path = Path(run.work_dir) / "expenses.csv"
    write_zoho_expense_export(
        [r for r in receipts if r.document_id not in copies], out_path,
        footer=copies_set_aside_line(receipts, copies),
        single_currency=single_currency_for_export(run, charge_decisions),
        **kwargs,
    )
    return out_path


def single_currency_for_export(run: RunRow, charge_decisions: dict | None):
    """Item 98: the callback `write_zoho_expense_export` uses to fill the
    `Exchange Rate` column and state the month's one total.

    Built here rather than in the writer because pricing a row needs this
    month's settled charges and its frozen FX config, and the writer owns
    neither. The per-row conversion is `convert_rows`, the same function the
    month report calls, so one purchase can never be converted at two rates.

    The two documents' TOTALS can legitimately differ, and on a month with a
    private expense they do: this CSV exports every expense, while the
    report's listing is company expenses only (private ones go to their own
    reimbursements section). Each figure covers the rows of the document it
    sits in, which is the only thing either could honestly mean.

    A row already in the base currency gets no rate printed: an "Exchange
    Rate" of 1 on a USD expense is noise in a column a reader scans for the
    rows that actually converted.
    """
    settled = export_settled_amounts(run, charge_decisions)
    rate_of = usd_reference_rate(run)

    def fill(groups):
        rows = [row for _doc, doc_rows in groups for row in doc_rows]
        if not needs_conversion(rows, EXPENSE_COLUMNS):
            # A month entirely in the filing currency has nothing to say
            # here, and the CSV goes out exactly as it did before.
            return {}, ()
        numbers_by_doc: dict[str, list[int]] = {}
        pos = 1
        for doc, doc_rows in groups:
            numbers_by_doc.setdefault(doc, []).extend(
                range(pos, pos + len(doc_rows))
            )
            pos += len(doc_rows)
        converted, totals, unconverted, no_amount = convert_rows(
            rows, EXPENSE_COLUMNS,
            numbers_by_doc=numbers_by_doc,
            settled_amounts=settled,
            reference_rate=rate_of,
        )
        rates = {
            n: f"{c.rate:f}" for n, c in converted.items() if c.rate is not None
        }
        # The CSV prints no row numbers, and its row order is not the
        # report's, so a note here names each row the way the copies line
        # does: by what is printed on it.
        cols = {name: i for i, name in enumerate(EXPENSE_COLUMNS)}
        labels = {
            n: " ".join(
                x for x in (
                    str(rows[n - 1][cols["Vendor"]] or "").strip(),
                    str(rows[n - 1][cols["Expense Date"]] or "").strip(),
                    str(rows[n - 1][cols["Currency Code"]] or "").strip(),
                    str(rows[n - 1][cols["Expense Amount"]] or "").strip(),
                ) if x
            ) or f"expense {n}"
            for n in set(unconverted) | set(no_amount)
        }
        return rates, summary_lines(
            totals, unconverted, converted,
            no_amount=no_amount, labels=labels,
        )

    return fill


def copies_set_aside_entries(receipts: list[Receipt], copies: dict[str, str]) -> list[dict]:
    """One entry per decided copy among `receipts`, in the receipts' order:
    `{document_id, of, vendor, date, amount, currency}` (item 94). What the
    "copies set aside" line on each surface is written from."""
    return [
        {
            "document_id": r.document_id,
            "of": copies[r.document_id],
            "vendor": r.canonical_vendor or r.detected_vendor or "(no vendor)",
            "date": str(r.detected_date or ""),
            "amount": _fmt_amount(r.detected_total) or "",
            "currency": r.detected_currency or "?",
        }
        for r in receipts
        if r.document_id in copies
    ]


def copies_set_aside_line(receipts: list[Receipt], copies: dict[str, str]) -> str:
    """The one-line statement of the copies a listing left out (item 94), or
    "" when there are none, so a month without copies writes exactly what it
    wrote before. Amounts sit inside the sentence, never in an amount column,
    so a reader summing that column cannot count a copy again."""
    entries = copies_set_aside_entries(receipts, copies)
    if not entries:
        return ""
    totals = copies_set_aside_totals(receipts, copies)
    summed = "; ".join(
        f"{ccy} {amt:,.2f}" for ccy, amt in sorted(totals.items())
    ) or "no amounts read"
    listed = "; ".join(
        " ".join(x for x in (e["vendor"], e["date"], e["currency"], e["amount"]) if x)
        for e in entries
    )
    n = len(entries)
    return (
        f"Copies set aside, not counted above: {n} "
        f"{'document' if n == 1 else 'documents'} that repeat another "
        f"({summed}): {listed}"
    )


def build_expense_report(
    run: RunRow,
    overrides: dict,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    trip: "TripRow | None" = None,
    settings: dict | None = None,
    render_outcomes: dict | None = None,
    dup_resolutions: dict[str, str] | None = None,
    charge_decisions: dict | None = None,
    learning_db_path: "Path | None" = None,
) -> bytes:
    """The month's report PDF: the listing, then every receipt (owner
    directive 2026-08-23 — nothing imports the output any more, so the
    deliverable is a document).

    A decided copy (`decided_copies`, item 94, owner ruling 2026-09-17) is
    in neither the listing nor its totals, company or reimbursement side.
    A "Copies set aside" line under the listing names each one with the
    expense it repeats, and its pages follow the original's, captioned as
    the copy. "Not a copy" brings the document back as a listed expense.

    The listing is the export's own rows. Evidence is per DOCUMENT: a receipt
    that books to two accounts writes two listing rows and appears once,
    captioned with both expense numbers. The row-to-document map comes from
    the same pass that writes the rows (`build_expense_row_groups`, item 97),
    so a caption names exactly the rows written for its document. A receipt
    whose total was never read writes one row with a blank amount, marked
    "amount unreadable, not in total" and counted in the footer; a receipt
    that wrote no row says "not in the listing" on its caption.

    Confirmed private expenses (backlog item 41) are PARTITIONED out of the
    company listing into a reimbursements-owed section, grouped per person
    with sums — a private row in the company listing would read as an
    unfinished company row, which is the exact ambiguity the directive
    removes. Their receipts stay in the evidence, numbered after the
    listing's rows.

    A TRIP batch (item 38, R4b) sections the listing PER PERSON — item
    40's field, resolved through the card chain — in roster order, other
    named persons after, unowned rows last, numbering continuous. `trip`
    is the trip entity when the caller has it (title, range, roster);
    a trip batch whose entity is gone still sections. Should the rows ever
    fail to line up with their receipts the report falls back to the flat
    listing and says so in its closing note rather than mislabelling a
    section boundary.

    A COMPANY month (item 47) sections the listing PER COST CENTER once
    the chain resolves or flags any row: named centres in name order,
    then an unassigned section, never hidden, with the stated limit above
    the partition (card-and-receipt spend, not total project cost). With
    no cost center defined the chain is silent for every row and the flat
    listing stays exactly as it was; that decision is derived from
    `CostCenterRegistry.resolve` (the empty-registry contract's only
    home) rather than re-checked here. `settings` is the live settings
    map both registries read from.

    A COMPANY month no cost center partitions sections the listing PER
    CARD (item 138, owner 2026-09-17: the PDFs were "not organized by the
    cards that were reconciled"). The sections are `card_sections` over
    `report_view` and `report_receipt_cards`, the grouping the
    reconciliation report uses, so both documents file a receipt under the
    same card. Each card section carries a line on what its statement
    settled (`card_statement_line`) and names any receipt its charge holds
    whose own card is another (item 137); its receipt pages follow its
    sums rather than the whole document. Reimbursements and copies keep
    their current places. A month whose listed receipts fall in a single
    section (one card, or none) keeps the flat listing.

    A month with cost centers AND two cards or more nests the cards inside
    the cost centers (owner ruling 2026-09-17): one section per cost center,
    its expenses ordered by the card that paid (same grouping, same order,
    "No card" last), and a cost center spanning two card groups or more
    gets a sub-heading and sums per card. The card's statement line stays
    out (its figures are the whole statement's); a held pair whose cards
    differ is still named, under its card. Receipt pages stay at the end,
    in listing order.
    `charge_decisions` feeds the view that sections are read from.
    """
    from ..cards import card_parents
    from ..output._pdf_common import (
        NO_CARD_SECTION_LABEL,
        card_sections,
        card_statement_line,
    )
    from ..output.month_report_pdf import build_expense_report_pdf

    # Item 111: the Expenses page's card of the charge a receipt settles, for
    # the listing's rows (company, paid-through) and the card pass below.
    report_settled = export_settled_cards(run, charge_decisions)
    report_merchants = (settings or {}).get("merchants")
    receipts, kwargs = _expense_export_inputs(
        run, overrides, field_overrides, edits, dup_resolutions,
        settled_cards=report_settled, merchants=report_merchants,
        learning_db_path=learning_db_path,
    )
    copies = decided_copies(
        run, receipts, dup_resolutions, charge_decisions=charge_decisions,
    )
    private_by_doc = _private_reimbursements(field_overrides)
    company = [
        r for r in receipts
        if r.document_id not in private_by_doc and r.document_id not in copies
    ]
    private = [
        r for r in receipts
        if r.document_id in private_by_doc and r.document_id not in copies
    ]

    sections: list[dict] | None = None
    sections_heading = ""
    sections_note = ""
    # Item 138: set when the listing sections per card, which is also when
    # each section's receipt pages follow that section.
    by_card_receipts = False
    card_section_by_key: dict[str, dict] = {}
    # Item 138 (owner ruling 2026-09-17): set when a cost-center listing
    # groups each section's expenses by card; `card_of` is each listed
    # receipt's card key.
    cards_in_sections = False
    card_of: dict[str, str] = {}
    # A partition of the company listing into contiguous slices: the
    # ordered keys, the receipts under each, and a function giving the
    # caption fields a section carries. A trip keys on person (item 38);
    # a company month keys on cost center (item 47). Either way the
    # listing is rebuilt in section order and the export's own fan-out
    # widths decide where each slice starts.
    groups: dict[str, list] | None = None
    ordered_keys: list[str] = []
    section_fields = None  # key -> the section's caption fields
    roster: list[str] = list(trip.travelers) if trip is not None else []
    # The same card pass the grid runs: it names the person a trip
    # sections on and the card whose default a cost center falls back to.
    card_res_report = resolve_batch_row_cards(
        company, run.config, field_overrides, settled_cards=report_settled,
        merchants=report_merchants,
    )
    if is_trip_batch(run):
        def _person_of(r) -> str:
            res = card_res_report.get(r.document_id) or {}
            return str(res.get("person") or "").strip()

        def _order_key(p: str):
            pf = p.casefold()
            for i, t in enumerate(roster):
                if t.strip().casefold() == pf:
                    return (0, i, "")
            return (1, 0, pf) if p else (2, 0, "")

        groups = {}
        for r in company:
            groups.setdefault(_person_of(r), []).append(r)
        ordered_keys = sorted(groups, key=_order_key)
        roster_fold = {t.strip().casefold() for t in roster}

        def _person_fields(p: str) -> dict:
            return {
                "person": p,
                "on_roster": (p.casefold() in roster_fold) if p else None,
            }

        section_fields = _person_fields
    else:
        def _card_grouping() -> tuple[dict[str, list], dict[str, dict], list[str]]:
            # Item 138: the listed company receipts per card, from
            # `card_sections` over the same view and card chain the
            # reconciliation report sections on, so the two documents file
            # every receipt under the same card: a receipt a charge holds
            # follows that charge's card, an unheld one its own resolved
            # card, the rest "No card", last. Only the listed company
            # receipts are placed, so a card whose receipts are all private
            # or copies gets no empty table. Returns the receipts per card
            # key, the card section per key, and the keys in document order.
            _, snapshot_receipts, _, _ = snapshot_from_dict(run.snapshot)
            card_view = report_view(
                run, receipts, snapshot_receipts, charge_decisions or {},
                overrides, dup_resolutions, field_overrides=field_overrides,
            )
            listed = {r.document_id: r for r in company}
            by_card: dict[str, list] = {}
            sec_by_key: dict[str, dict] = {}
            for sec in card_sections(
                card_view,
                report_receipt_cards(
                    receipts, run.config, field_overrides,
                    merchants=report_merchants,
                ),
                card_parents(_batch_cards(run.config)),
            ):
                for doc in sec["receipt_docs"]:
                    if doc in listed:
                        by_card.setdefault(sec["key"], []).append(listed.pop(doc))
                if sec["key"] in by_card:
                    sec_by_key[sec["key"]] = sec
            if listed:
                # Never drop a row: a listed receipt the sections did not
                # place goes with the ones that have no card.
                by_card.setdefault("", []).extend(
                    r for r in company if r.document_id in listed
                )
            keys = [k for k in sec_by_key if k]
            if "" in by_card:
                keys.append("")
            return by_card, sec_by_key, keys

        # Item 47: the chain over the same card pass, exactly as the grid
        # runs it. It partitions only once it resolves or flags a row: an
        # empty registry is silent for every row, so a month with no cost
        # center defined keeps its flat listing. That silence is decided
        # in `CostCenterRegistry.resolve` alone and deliberately NOT
        # re-checked here, so the contract stays load-bearing.
        cost_res = resolve_batch_row_cost_centers(
            company, field_overrides, settings=settings, trip=None,
            card_res=card_res_report,
        )
        if any(c.name or c.needs for c in cost_res.values()):
            registry = CostCenterRegistry.from_settings(settings)
            groups = {}
            for r in company:
                groups.setdefault(
                    cost_res[r.document_id].name or "", []
                ).append(r)
            # Named centres in name order; the unassigned slice LAST and
            # never dropped: a row nobody attributed is exactly what the
            # reader of a cost-center roll-up needs to see.
            ordered_keys = sorted(
                groups, key=lambda k: (1, "") if not k else (0, k.casefold())
            )

            def _cost_center_fields(name: str) -> dict:
                if not name:
                    return {"caption": "Unassigned (no cost center)",
                            "label": "Unassigned"}
                kind = str(
                    (registry.entries.get(name) or {}).get("kind") or ""
                )
                return {"caption": f"{name} ({kind})" if kind else name,
                        "label": name}

            section_fields = _cost_center_fields
            sections_heading = "Listing by cost center"
            sections_note = COST_CENTER_SCOPE_NOTE
            # Item 138, owner ruling 2026-09-17: cards inside cost centers.
            # A month on two cards or more (the card listing's own rule)
            # keeps one section per cost center and orders each one's
            # expenses by the card that paid, in card-section order, "No
            # card" last; a cost center on two card groups or more gets a
            # sub-heading and sums per group. Receipt pages stay at the end,
            # in this listing order.
            by_card, sec_by_key, card_keys = _card_grouping()
            if sum(1 for k in by_card if k) >= 2:
                card_section_by_key = sec_by_key
                card_of = {
                    r.document_id: k for k in card_keys for r in by_card[k]
                }
                groups = {k: [] for k in groups}
                for k in card_keys:
                    for r in by_card[k]:
                        groups[cost_res[r.document_id].name or ""].append(r)
                cards_in_sections = True
        else:
            # Item 138: no cost center applies, so the month is organized
            # the way it is reconciled, card by card (`_card_grouping`).
            # The listing sections only when its receipts span two sections
            # or more, one of them a card: a single section (one card, or
            # only "No card") would put a heading over the flat listing and
            # push the copies line and the reimbursements off its first
            # page, organizing nothing.
            by_card, card_section_by_key, card_keys = _card_grouping()
            # Two cards or more, the reconciliation report's own rule: a
            # one-card month (with or without no-card receipts) keeps the
            # flat listing, whose header already is that card's.
            if sum(1 for k in by_card if k) >= 2:
                groups = by_card
                ordered_keys = card_keys
                # Item 147 (owner ruling 2026-09-18): an account and the
                # subcards under it are ONE section, a table per card inside
                # it, so the document reads the way the tabs do and the
                # account's receipt pages follow the whole group. Reuses the
                # sub-heading machinery the cost-center listing already has.
                # A card with no account keeps a section of its own.
                account_of = {
                    kid: key
                    for key in card_keys
                    for kid in (
                        (card_section_by_key.get(key) or {}).get("subcards") or []
                    )
                    if kid in by_card
                }
                if account_of:
                    ordered_keys = [k for k in card_keys if k not in account_of]
                    groups = {}
                    card_of = {}
                    for key in ordered_keys:
                        members = [key] + [
                            k for k in card_keys if account_of.get(k) == key
                        ]
                        listed_here = []
                        for member in members:
                            for r in by_card.get(member, []):
                                card_of[r.document_id] = member
                                listed_here.append(r)
                        groups[key] = listed_here
                    cards_in_sections = True

                def _card_fields(key: str) -> dict:
                    sec = card_section_by_key.get(key) or {
                        "key": "", "label": NO_CARD_SECTION_LABEL,
                        "coverage": None, "rows": [],
                    }
                    return {
                        "caption": sec["label"],
                        "label": sec["label"],
                        "detail": card_statement_line(sec),
                    }

                section_fields = _card_fields
                sections_heading = "Listing by card"
                by_card_receipts = True
    if groups is not None:
        company = [r for k in ordered_keys for r in groups[k]]

    # Item 97: the listing and the captions come from ONE pass. Each
    # receipt's listing numbers are the rows the export actually wrote for
    # it, so a caption can only name its own purchase. The numbers used to
    # come from a second fan-out run without the chart and the COA gate;
    # whenever the two counted differently the captions fell back to 1..N
    # and, from the first split receipt on, named someone else's purchase.
    row_groups = build_expense_row_groups(company, **kwargs)
    rows = [row for _doc, doc_rows in row_groups for row in doc_rows]
    aligned = [doc for doc, _rows in row_groups] == [r.document_id for r in company]
    numbers_by_doc: dict[str, list[int]] = {}
    pos = 1
    for doc, doc_rows in row_groups if aligned else ():
        numbers_by_doc[doc] = list(range(pos, pos + len(doc_rows)))
        pos += len(doc_rows)

    if groups is not None and section_fields is not None and aligned:
        sections = []
        pos = 1
        vendor_col = EXPENSE_COLUMNS.index("Vendor")

        def _differ_notes(card_key: str, docs: set[str] | None, on: str) -> list[str]:
            # Item 137 on paper: a listed receipt this card's charge holds
            # while the tool resolved it to another card. It stays beside
            # the charge it settles, and says so. `docs` narrows it to the
            # receipts of one cost center's card group; `on` names where
            # the charge is ("this card" under a card heading).
            notes = []
            for charge in (card_section_by_key.get(card_key) or {}).get("rows") or []:
                differ = charge.get("cards_differ") or {}
                doc = str(differ.get("document_id") or "")
                numbers = numbers_by_doc.get(doc)
                if not numbers or (docs is not None and doc not in docs):
                    continue
                vendor = str(rows[numbers[0] - 1][vendor_col] or "").strip()
                which = (
                    f"Expense {numbers[0]}" if len(numbers) == 1
                    else "Expenses " + ", ".join(str(x) for x in numbers)
                )
                single = len(numbers) == 1
                verb = "is" if single else "are"
                whose = "its" if single else "the receipt's"
                named = f" ({vendor})" if vendor else ""
                other = differ.get("receipt_card_label") or "another card"
                notes.append(
                    f"{which}{named} {verb} held on a charge {on}, but "
                    f"{whose} own card is {other}."
                )
            return notes

        for key in ordered_keys:
            count = sum(len(numbers_by_doc[r.document_id]) for r in groups[key])
            section = {**section_fields(key), "start": pos, "count": count}
            # Item 147: with subcards inside the section the per-card notes
            # are the subsections' own, below; naming them here too would
            # print each one twice.
            if by_card_receipts and not cards_in_sections and (
                key in card_section_by_key
            ):
                notes = _differ_notes(key, None, "on this card")
                if notes:
                    section["notes"] = notes
            if cards_in_sections:
                # Item 138, owner ruling 2026-09-17: this cost center's
                # expenses by the card that paid, contiguous (the listing
                # was ordered by card above). A group whose receipts wrote
                # no row has nothing to head. The card's statement line is
                # left out: its figures are the whole statement's, not this
                # cost center's share of it.
                runs: list[tuple[str, list, int]] = []
                sub_pos = pos
                for r in groups[key]:
                    k = card_of.get(r.document_id, "")
                    width = len(numbers_by_doc[r.document_id])
                    if runs and runs[-1][0] == k:
                        runs[-1][1].append(r)
                        runs[-1] = (k, runs[-1][1], runs[-1][2] + width)
                    else:
                        runs.append((k, [r], width))
                subsections = []
                for k, run_receipts, width in runs:
                    if width:
                        docs = {r.document_id for r in run_receipts}
                        name = (card_section_by_key.get(k) or {}).get("label") or (
                            NO_CARD_SECTION_LABEL
                        )
                        sub = {
                            "caption": name, "label": name,
                            "start": sub_pos, "count": width,
                            "card_key": k, "docs": docs,
                        }
                        subsections.append(sub)
                    sub_pos += width
                if len(subsections) >= 2:
                    for sub in subsections:
                        notes = _differ_notes(
                            sub["card_key"], sub["docs"], "on this card"
                        )
                        if notes:
                            sub["notes"] = notes
                    section["subsections"] = subsections
                elif subsections:
                    # One card, no sub-heading: the note names the card.
                    (sub,) = subsections
                    on = (
                        f"on {sub['label']}" if sub["card_key"]
                        else "with no card"
                    )
                    notes = _differ_notes(sub["card_key"], sub["docs"], on)
                    if notes:
                        section["notes"] = notes
            sections.append(section)
            pos += count
    receipts_dir = Path(run.work_dir) / "receipts"
    # Backlog item 25: the document says which of its own dates it distrusts.
    # Same period and same human-owns-it rule as the review grid, so the PDF
    # and the screen cannot disagree about which rows are in question.
    period = batch_period(
        run.label, [r.detected_date for r in receipts if r.detected_date]
    )
    suspect: list[int] = []
    evidence: list[dict] = []

    def _evidence_item(
        r, numbers: list[int], extra_detail: str = "", *, copy: bool = False,
    ) -> dict:
        # A copy's date questions no listed expense: its numbers are the
        # original's, which carries its own date (item 94).
        if not copy and outside_period(r.detected_date, period) and not (
            "date" in field_overrides.get(r.document_id, {})
            or r.document_id.startswith("manual:")
        ):
            suspect.extend(numbers)
        path = receipts_dir / r.document_id
        if not path.is_file():
            hit = _attached_receipt_file(receipts_dir.parent, r.document_id)
            path = hit if hit is not None else None
        item: dict = {
            "rows": numbers,
            # Item 68: which expense this evidence belongs to. The builder
            # ignores it; the verdict recorder keys on it.
            "document_id": r.document_id,
            "label": r.detected_vendor or "(no vendor)",
            "detail": "  ·  ".join(x for x in (
                str(r.detected_date or ""),
                (f"{r.detected_total} {r.detected_currency or ''}".strip()
                 if r.detected_total is not None else ""),
                r.legal_entity_id or "",
                extra_detail,
            ) if x),
        }
        # The document this evidence proves, so the build's per-file render
        # outcome can be keyed back to the ROW that is missing its pages
        # (item 67). The builders ignore keys they do not use.
        item["document_id"] = r.document_id
        if copy:
            item["copy"] = True
        if path is not None:
            item["name"] = _display_name(path.name)
            item["data"] = path.read_bytes()
        return item

    n = len(rows) + 1
    # Item 62 (owner ruling 2026-09-15): a receipt settled outside the card
    # STILL prints. It is real company spend whose evidence is the invoice,
    # and dropping it would hide the spend from the accountant; the caption
    # names the tender so the reader knows why no card line matches it.
    report_settled_outside = settled_outside_map(run.snapshot or {})
    # Item 97: the listing numbers of the rows written for a receipt whose
    # total was never read. Their Amount cell is blank, which the total reads
    # as zero, so the report is told which rows those are.
    unreadable_numbers: list[int] = []
    for r in company:
        numbers = numbers_by_doc.get(r.document_id, [])
        if r.detected_total is None:
            unreadable_numbers.extend(numbers)
        so = report_settled_outside.get(r.document_id)
        evidence.append(_evidence_item(
            r, numbers,
            extra_detail="  ·  ".join(x for x in (
                settled_outside_caption(so["how"]) if so else "",
                "" if numbers or not aligned else "not in the listing",
            ) if x),
        ))

    # The reimbursements-owed section: one numbered row per private
    # expense (no account fan-out — a reimbursement is owed whole),
    # grouped per person, sums per currency, numbering continuing the
    # listing's so every receipt page still names a unique number.
    reimb_groups: dict[str, dict] = {}
    for r in private:
        person = private_by_doc.get(r.document_id) or "(person not named)"
        group = reimb_groups.setdefault(person, {
            "person": person, "rows": [], "totals": {},
        })
        group["rows"].append({
            "n": n,
            "date": str(r.detected_date or ""),
            "vendor": r.canonical_vendor or r.detected_vendor or "(no vendor)",
            "amount": _fmt_amount(r.detected_total) or "",
            "currency": r.detected_currency or "?",
        })
        if r.detected_total is not None:
            ccy = r.detected_currency or "?"
            group["totals"][ccy] = (
                group["totals"].get(ccy, Decimal("0")) + r.detected_total
            )
        evidence.append(_evidence_item(
            r, [n], extra_detail=f"private, reimburse {person}",
        ))
        n += 1
    reimbursements = [
        {
            "person": g["person"],
            "rows": g["rows"],
            "totals": {
                ccy: f"{amt:,.2f}" for ccy, amt in sorted(g["totals"].items())
            },
        }
        for g in sorted(reimb_groups.values(), key=lambda g: g["person"])
    ]

    # Item 94: each decided copy's pages follow the expense it repeats,
    # captioned with that expense's numbers, and the listing states the
    # copies it left out. Walked in reverse and inserted right behind the
    # original, so several copies of one expense keep the receipts' order.
    copy_lines: list[dict] = []
    if copies:
        by_doc = {r.document_id: r for r in receipts}
        for entry in copies_set_aside_entries(receipts, copies):
            original = next(
                (e for e in evidence if e.get("document_id") == entry["of"]),
                None,
            )
            copy_lines.append({
                **entry,
                "rows": list(original["rows"]) if original is not None else [],
            })
        for line in reversed(copy_lines):
            item = _evidence_item(
                by_doc[line["document_id"]], line["rows"],
                extra_detail="copy set aside, not counted", copy=True,
            )
            at = next(
                (i for i, e in enumerate(evidence)
                 if e.get("document_id") == line["of"]),
                None,
            )
            if at is None:
                evidence.append(item)
            else:
                evidence.insert(at + 1, item)
    copies_totals = {
        ccy: f"{amt:,.2f}"
        for ccy, amt in sorted(copies_set_aside_totals(receipts, copies).items())
    }

    label = run.label or run.run_id
    # Item 138: sectioned per card, the receipts sit behind each card's
    # listing, so this note (after the last section) cannot say "below".
    in_sections = by_card_receipts and sections is not None
    note = (
        "Every amount above is the amount the CSV export writes. Each "
        "receipt follows behind the expense number it proves."
    )
    if in_sections:
        note = (
            "Every amount above is the amount the CSV export writes. Each "
            "card's receipts follow its listing, each behind the expense "
            "number it proves."
        )
    if not aligned:
        # Item 97: never renumber in silence. Defensive: the one pass above
        # keeps the receipts in order, so this should not print.
        note += (
            " The receipt pages could not be tied to the listing's expense "
            "numbers, so each caption names the receipt instead."
        )
    if suspect:
        suspect_numbers = ", ".join(str(i) for i in sorted(suspect))
        note += (
            f" The date read on {'expense' if len(suspect) == 1 else 'expenses'} "
            f"{suspect_numbers} falls outside this month, so check "
            f"{'it' if len(suspect) == 1 else 'them'} against the receipt "
            f"{'page' if len(suspect) == 1 else 'pages'}"
            f"{'' if in_sections else ' below'}."
        )
    # A colon, never an em-dash: the house deliverable standard bans every
    # dash form from a client-facing document, and the colon is what the rest
    # of both documents already uses for a label ("Statement: ...",
    # "Owed to Dirk: ...").
    title = f"Expense report: {label}"
    subtitle = ""
    if is_trip_batch(run):
        title = f"Trip report: {trip.name if trip is not None else label}"
        if trip is not None:
            who = ", ".join(roster) if roster else "no travelers entered"
            subtitle = (
                f"{trip.start_date} to {trip.end_date}  ·  travelers: {who}"
            )
    # Item 98: one figure for the month, and per row how it was reached.
    # `numbers_by_doc` is the map this function already built to caption
    # receipt pages, so a split receipt converts once as one purchase; the
    # unreadable rows are skipped because they are already out of every
    # other total on the page. `aligned` false means the fan-out and the
    # receipts disagree and the listing has fallen back to 1..N, where the
    # document boundaries this needs are exactly what is not trustworthy.
    report_conversions: dict = {}
    report_total = report_unconverted = ""
    if aligned and needs_conversion(rows, EXPENSE_COLUMNS):
        report_conversions, base_totals, missing, _blank = convert_rows(
            rows, EXPENSE_COLUMNS,
            numbers_by_doc=numbers_by_doc,
            settled_amounts=export_settled_amounts(run, charge_decisions),
            reference_rate=usd_reference_rate(run),
            skip=set(unreadable_numbers),
        )
        # `_blank` stays out of the lines here: an unreadable amount already
        # has its own caption on the row and its own line in the footer
        # (item 65), and saying it twice in two vocabularies is worse than
        # saying it once.
        lines = summary_lines(base_totals, missing, report_conversions)
        report_total = lines[0] if lines else ""
        report_unconverted = lines[1] if len(lines) > 1 else ""
    pdf = build_expense_report_pdf(
        rows,
        EXPENSE_COLUMNS,
        title=title,
        subtitle=subtitle,
        conversions=report_conversions,
        conversion_total=report_total,
        conversion_note=report_unconverted,
        evidence=evidence,
        prepared_note=note,
        reimbursements=reimbursements,
        sections=sections,
        sections_heading=sections_heading,
        sections_note=sections_note,
        copies_set_aside=copy_lines,
        copies_set_aside_totals=copies_totals,
        receipts_by_section=in_sections,
        amounts_unreadable=unreadable_numbers,
    )
    # Item 67: `prepare_evidence` wrote each file's render outcome back onto
    # its evidence dict during the build. The builder returns one `bytes`, so
    # this dict is the channel; a caller that passes one gets
    # {document_id: {"render", "note"}} for every expense that HAD a file,
    # which is what lets the review screen name the blocked receipt instead of
    # the reviewer finding out by opening the PDF.
    if render_outcomes is not None:
        for item in evidence:
            doc = str(item.get("document_id") or "")
            if not doc or "receipt_render" not in item:
                continue
            render_outcomes[doc] = {
                "render": item["receipt_render"],
                "note": str(item.get("render_note") or ""),
            }
    return pdf


def receipt_card_counts(view: dict) -> dict[str, dict[str, int]]:
    """Receipts per card on an Expenses page payload: `expenses[].card_section`
    over the rows that count, decided copies left out, which is exactly what
    the month's own card tabs count (`card_sections[].n_expenses`). The key
    "" is the no-card section.

    Each key carries `n_expenses` and `n_without_charge` (item 192): of those
    rows, the ones `expenses[].without_charge` marks, so the overview's
    "without a charge" is the month's own verdict and never a second one.

    And `n_needs_category` (item 193): the rows in the NEEDS CATEGORY box
    (`"uncategorized"` in `expenses[].boxes`), the set `summary.n_uncategorized`
    counts, so a month's cards plus its no-card section add up to the months
    list's Needs category column."""
    counts: dict[str, dict[str, int]] = {}
    for expense in view.get("expenses") or []:
        if expense.get("counts_in_total") is False:
            continue
        key = str(expense.get("card_section") or "")
        entry = counts.setdefault(
            key, {"n_expenses": 0, "n_without_charge": 0, "n_needs_category": 0},
        )
        entry["n_expenses"] += 1
        if expense.get("without_charge"):
            entry["n_without_charge"] += 1
        if "uncategorized" in (expense.get("boxes") or []):
            entry["n_needs_category"] += 1
    return counts


def build_card_status(
    store: RunStore,
    receipt_cards: Callable[[RunRow], dict[str, int | dict[str, int]]] | None = None,
    parents: dict[str, str] | None = None,
) -> dict:
    """The cross-month card roll-up (item 185, owner 2026-09-24): "the same
    per card filter system inside the months should be outside of the
    months".

    Inside a month, the card strip answers "what is open on this card, this
    month". Every question note #86 asks is the same one asked of the
    estate instead: which cards are missing, which charges have no receipt,
    which receipts have no charge, and above all WHICH MONTH a thing is on,
    which is exactly what a per-month surface cannot say.

    The numbers are `month_coverage`'s, per month, summed. Not a second
    derivation: a card row here and the same card's row on its month page
    are the same arithmetic over the same charge states, which is the rule
    that stops two screens reporting one card at two stages of done (the
    `n_categorized` failure of 2026-08-22).

    Every expense batch counts, trips included, because a card does not
    stop being spent on when the spending happens on a trip. Each month
    entry carries its own `batch_type`, so a page can separate them; a
    roll-up that quietly left trips out would report a card as never used
    while a trip had used it.

    Two identities for one card are folded, in one direction only: an
    UNKNOWN row (digits nobody has defined) folds into a KNOWN row with
    exactly the same digits. That is the card defined after a month was
    already created, which otherwise appears twice, once under `3645` and
    once under `card-3645`. Nothing folds two known cards, and an unknown
    row with no defined twin keeps its own line: April's `digits:4700` is a
    real card the registry is still missing (item 26) and burying it would
    hide the gap.

    A run whose snapshot cannot be read is named in `unreadable` and
    skipped, never fatal: an unreadable month is a reason to report fewer
    months, not none.

    Item 190 (owner 2026-09-24: the card filter leaves the month and "a
    month is clicked on ... he should then only see data from the card that
    he selected") adds the receipt side, as parallel fields so nothing above
    changes: `cards[].receipt_months[]` names each month holding receipts on
    the card, and `no_card` the months holding receipts on no card. Without
    them a month with receipts and no statement yet (September, while Criss
    works it) is on no card at all. `receipt_cards` is the Expenses page's
    own per-card count for a run (`receipt_card_counts`), so a month's tab
    and its line here cannot disagree; a month it fails on is named in
    `unreadable` and keeps its charge figures.

    Item 191 (owner 2026-09-24: the subcards of 2838 should "not be next to
    the 2838 tab but rather only appear once viewer clicks on 2838") adds
    the tree, again as parallel fields: `cards[].parent` names the account a
    card sits under ("" when it stands alone) and `cards[].subcards` the
    cards under an account, in the strip's own order. `parents` is
    `card_parents` over the LIVE registry, not a month's snapshot: this is
    a navigation aid over every month, and a month keeps the registry it
    was created with. A link survives only when both cards are on the list,
    so a strip never nests a card under a tab it does not show. Nothing
    else here reads the tree; the figures stay each card's own.

    Item 192 (owner 2026-09-24: `/cards` "should just be an overview and
    not another gate to inside the months. we can insert more relevant
    data") makes the receipt side a figure and not only a list of months,
    so the page can say what note #86 asks per card without opening one:
    each `receipt_months[]` entry adds `n_without_charge` (the month's own
    verdict, `receipt_card_counts`) and `statement` (this card has a
    statement in that month), and each card adds `n_receipts`,
    `n_receipts_without_charge` and `n_receipts_no_statement` (receipts in
    months where the card has no statement: waiting for one, not
    unmatched). `no_card` adds `n_without_charge`. Parallel fields again;
    nothing above changes.

    Item 193 (owner 2026-09-24: the number beside each card on the months
    strip "ha[s] to be consistent in [its] meaning"; it was `n_transactions`,
    statement lines with credits, on no label) picks one meaning: expenses
    needing a category, all months. `n_needs_category` on each receipt month,
    each card (its own, not its subcards': picking 2838 shows 2838's rows) and
    `no_card`.
    """
    from ..output._pdf_common import _add_money

    months: list[dict] = []
    per_card: dict[str, dict] = {}
    unreadable: list[str] = []
    no_card_months: list[dict] = []

    def _slot(row: dict) -> dict:
        slot = per_card.get(row["key"])
        if slot is None:
            slot = per_card[row["key"]] = {
                "key": row["key"],
                "card_key": row.get("card_key") or "",
                "label": row.get("label") or "",
                "digits": list(row.get("digits") or []),
                "entity": row.get("entity") or "",
                "known": bool(row.get("known")),
                "n_transactions": 0,
                "n_reconciled": 0,
                "n_review": 0,
                "n_unmatched_tx": 0,
                "n_refunds": 0,
                "statements": [],
                "period_start": None,
                "period_end": None,
                "months": [],
                "receipt_months": [],
                "_ccy": [],
            }
        # The entity is the registry's and only a known row carries one;
        # keep the first non-empty rather than letting a later blank win.
        if not slot["entity"] and row.get("entity"):
            slot["entity"] = row["entity"]
        return slot

    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        snapshot = run.snapshot or {}
        try:
            transactions, receipts, outcome, _cfg = snapshot_from_dict(snapshot)
        except Exception:  # noqa: BLE001 - one bad month must not blank the page
            unreadable.append(run.run_id)
            continue
        decisions = store.get_decisions(run.run_id)
        effective = apply_decisions(outcome, transactions, receipts, decisions)
        states = charge_states(transactions, effective, decisions)
        coverage, _keys = month_coverage(run, transactions, states)
        month = {
            "run_id": run.run_id,
            "label": run.label or run.run_id,
            "batch_type": batch_type(run),
            "created_at": run.created_at,
            "n_transactions": sum(
                int(c.get("n_transactions") or 0) for c in coverage
            ),
            "n_cards": sum(
                1 for c in coverage
                if c.get("n_transactions") or c.get("statements")
            ),
            # The month's own span, from its charges. Not `created_at`:
            # two months created inside one second tie on it, and the
            # order of the months a card is on then depends on nothing.
            # Not the label either, which is free text.
            "period_start": min(
                (c["period_start"] for c in coverage if c.get("period_start")),
                default=None,
            ),
            "period_end": max(
                (c["period_end"] for c in coverage if c.get("period_end")),
                default=None,
            ),
        }
        months.append(month)
        for row in coverage:
            slot = _slot(row)
            for field in (
                "n_transactions", "n_reconciled", "n_review",
                "n_unmatched_tx", "n_refunds",
            ):
                slot[field] += int(row.get(field) or 0)
            files = [str(f) for f in (row.get("statements") or []) if str(f)]
            for file in files:
                slot["statements"].append({
                    "file": file,
                    "run_id": run.run_id,
                    "month": month["label"],
                })
            for field, better in (
                ("period_start", min), ("period_end", max),
            ):
                iso = row.get(field)
                if iso:
                    slot[field] = (
                        iso if slot[field] is None
                        else better(slot[field], iso)
                    )
            slot["_ccy"].append(row.get("unreconciled_by_ccy") or {})
            slot["months"].append({
                "run_id": run.run_id,
                "label": month["label"],
                "batch_type": month["batch_type"],
                "n_transactions": int(row.get("n_transactions") or 0),
                "n_reconciled": int(row.get("n_reconciled") or 0),
                "n_review": int(row.get("n_review") or 0),
                "n_unmatched_tx": int(row.get("n_unmatched_tx") or 0),
                "n_refunds": int(row.get("n_refunds") or 0),
                "statements": files,
                "period_start": row.get("period_start"),
                "period_end": row.get("period_end"),
                "unreconciled_by_ccy": dict(row.get("unreconciled_by_ccy") or {}),
            })
        if receipt_cards is None:
            continue
        try:
            counts = receipt_cards(run)
        except Exception:  # noqa: BLE001 - one bad month must not blank the page
            unreadable.append(run.run_id)
            continue
        # The cards this month holds a statement for, in the coverage's own
        # key space, which is the space `card_section` is stamped in.
        stated = {
            str(row.get("key") or "") for row in coverage
            if any(str(f) for f in (row.get("statements") or []))
        }
        for key, figures in sorted(counts.items()):
            if not isinstance(figures, dict):
                figures = {"n_expenses": int(figures)}
            entry = {
                "run_id": run.run_id,
                "label": month["label"],
                "batch_type": month["batch_type"],
                "n_expenses": int(figures.get("n_expenses") or 0),
                "n_without_charge": int(figures.get("n_without_charge") or 0),
                "n_needs_category": int(figures.get("n_needs_category") or 0),
            }
            if key:
                entry["statement"] = key in stated
                _slot({"key": key, "label": key})["receipt_months"].append(entry)
            else:
                no_card_months.append(entry)

    _fold_unknown_cards(per_card)

    cards = []
    for slot in per_card.values():
        slot["unreconciled_by_ccy"] = _add_money(slot.pop("_ccy"))
        slot["n_statements"] = len(slot["statements"])
        # The months this card is actually ON, which is the question note
        # #86 opens with. A month that merely listed the card in its
        # registry with nothing in it is not one of them.
        slot["months"] = [
            m for m in slot["months"]
            if m["n_transactions"] or m["statements"]
        ]
        slot["n_months"] = len(slot["months"])
        # "Which cards are missing": no charge and no statement anywhere,
        # which today is only answerable by querying every month by hand.
        slot["never_loaded"] = not (
            slot["n_transactions"] or slot["n_statements"]
        )
        # Item 192: the receipt side as figures, over the folded months.
        receipt_months = slot["receipt_months"]
        slot["n_receipts"] = sum(m["n_expenses"] for m in receipt_months)
        slot["n_receipts_without_charge"] = sum(
            m["n_without_charge"] for m in receipt_months
        )
        slot["n_receipts_no_statement"] = sum(
            m["n_expenses"] for m in receipt_months if not m["statement"]
        )
        # Item 193: the months strip's chip number, each card's own.
        slot["n_needs_category"] = sum(
            m["n_needs_category"] for m in receipt_months
        )
        cards.append(slot)

    months.sort(
        key=lambda m: (
            m["period_start"] or "", m["created_at"] or "", m["run_id"],
        ),
        reverse=True,
    )
    order = {m["run_id"]: i for i, m in enumerate(months)}
    for card in cards:
        card["months"].sort(key=lambda m: order.get(m["run_id"], 1 << 30))
        card["receipt_months"].sort(key=lambda m: order.get(m["run_id"], 1 << 30))
        card["statements"].sort(key=lambda s: order.get(s["run_id"], 1 << 30))
    no_card_months.sort(key=lambda m: order.get(m["run_id"], 1 << 30))
    # The month strip's own order: the busiest card first, the ones with
    # nothing in them last, alphabetical inside each.
    cards.sort(key=lambda c: (
        -c["n_transactions"], -c["n_statements"], c["label"].lower(), c["key"],
    ))
    # The tree (item 191). `parents` is keyed by registry key; a row's key
    # is the registry key for a known card, but translate through
    # `card_key` rather than assume it.
    row_key = {c["card_key"]: c["key"] for c in cards if c["card_key"]}
    subcards: dict[str, list[str]] = {}
    for card in cards:
        account = row_key.get((parents or {}).get(card["card_key"], ""), "")
        card["parent"] = account if account != card["key"] else ""
        if card["parent"]:
            subcards.setdefault(card["parent"], []).append(card["key"])
    for card in cards:
        card["subcards"] = subcards.get(card["key"], [])
    return {
        "cards": cards,
        "months": months,
        "no_card": {
            "months": no_card_months,
            "n_expenses": sum(m["n_expenses"] for m in no_card_months),
            "n_without_charge": sum(
                m["n_without_charge"] for m in no_card_months
            ),
            "n_needs_category": sum(
                m["n_needs_category"] for m in no_card_months
            ),
        },
        "unreadable": unreadable,
        # Rendered verbatim as the page's footnote, so it is prose for
        # Criss, not a field guide: the first version named the payload key
        # `never_loaded` and shipped that identifier onto the screen.
        "note": (
            # Item 192: the overview folds away only a card with no receipt
            # either, so the footnote says what the fold now holds.
            "Per card, across every month and trip. Each figure is that "
            "month's own card total, added up; the cards listed as having "
            "nothing loaded carry no charge, no statement and no receipt "
            "anywhere."
        ),
    }


def _fold_unknown_cards(per_card: dict[str, dict]) -> None:
    """Fold an UNKNOWN card row into the KNOWN row with the same digits.

    One direction only. A card defined after a month was created appears
    under its digit token in the old month and its registry key in the new
    one, and reporting that as two cards is worse than useless on a surface
    whose whole purpose is one line per card. An unknown row with no
    defined twin keeps its own line, because it is a card the registry is
    missing rather than a duplicate."""
    known = {}
    for slot in per_card.values():
        if slot["known"] and slot["digits"]:
            known.setdefault(tuple(sorted(slot["digits"])), slot)
    for key, slot in list(per_card.items()):
        if slot["known"] or not slot["digits"]:
            continue
        target = known.get(tuple(sorted(slot["digits"])))
        if target is None:
            continue
        for field in (
            "n_transactions", "n_reconciled", "n_review",
            "n_unmatched_tx", "n_refunds",
        ):
            target[field] += slot[field]
        target["statements"].extend(slot["statements"])
        target["months"].extend(slot["months"])
        target["receipt_months"].extend(slot["receipt_months"])
        target["_ccy"].extend(slot["_ccy"])
        for field, better in (("period_start", min), ("period_end", max)):
            if slot[field]:
                target[field] = (
                    slot[field] if target[field] is None
                    else better(target[field], slot[field])
                )
        del per_card[key]


def build_cost_center_totals(
    store: RunStore,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    """The cross-month roll-up (item 47, step 5): per cost center, per
    currency, over every expense batch the store holds, months and trips
    alike. The only surface that aggregates ACROSS batches: "what has
    Lidar cost since January" is the question a project raises, and no
    month report can answer it.

    Rows are the export's own rows (`_expense_export_inputs`), resolved
    through the same chain the grid and the month report run, so the
    three cannot disagree about where a row belongs. Confirmed private
    expenses are left out: they are reimbursements owed, not company
    spend. A decided copy (`decided_copies`, item 94) is in no bucket and
    not in `n_rows` / `n_undated`; `copies_set_aside` counts and sums the
    ones inside the range. The range is inclusive on the row's (edited) expense date; a
    row that carries no date cannot be excluded by a range, so it always
    counts and `n_undated` says how many such rows the figures contain.

    Every ACTIVE cost center is listed, at zero when nothing reached it;
    an inactive one appears only while history still sits on it. The
    unassigned bucket is explicit and never hidden. With no cost center
    defined the list is empty and every row is unassigned: the roll-up
    stating a fact, not a review state (the review state stays silent per
    the empty-registry contract, which this function does not re-check).

    The stated limit rides in `note`: card and receipt spend only, never
    contractor invoices or salaries, so none of these figures is a total
    project cost.
    """
    settings = store.get_settings()
    registry = CostCenterRegistry.from_settings(settings)

    def _bucket() -> dict:
        return {"n_rows": 0, "batches": set(), "totals": {}}

    def _add(bucket: dict, run_id: str, r) -> None:
        bucket["n_rows"] += 1
        bucket["batches"].add(run_id)
        if r.detected_total is not None:
            ccy = r.detected_currency or "?"
            bucket["totals"][ccy] = (
                bucket["totals"].get(ccy, Decimal("0")) + r.detected_total
            )

    by_center: dict[str, dict] = {}
    unassigned = _bucket()
    # Item 94: decided copies in range, never in a centre or `unassigned`.
    copies_bucket = _bucket()
    n_batches = 0
    n_rows = 0
    n_undated = 0
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        n_batches += 1
        overrides = store.get_category_overrides(run.run_id)
        field_overrides = store.get_expense_field_overrides(run.run_id)
        edits = store.get_expense_edits(run.run_id)
        trip = None
        if is_trip_batch(run):
            trip_row = store.get_trip(
                str((run.config or {}).get("trip_id") or "")
            )
            if trip_row is not None:
                trip = {"cost_center": trip_row.cost_center}
        resolutions = store.get_duplicate_resolutions(run.run_id)
        receipts, _kwargs = _expense_export_inputs(
            run, overrides, field_overrides, edits, resolutions,
        )
        # Item 94: the month report's own copies, left out of every bucket
        # and counted on their own line.
        copies = decided_copies(
            run, receipts, resolutions,
            charge_decisions=store.get_decisions(run.run_id),
        )
        private_by_doc = _private_reimbursements(field_overrides)
        company = [r for r in receipts if r.document_id not in private_by_doc]
        card_res = resolve_batch_row_cards(
            company, run.config, field_overrides,
            merchants=(settings or {}).get("merchants"),
        )
        cost_res = resolve_batch_row_cost_centers(
            company, field_overrides, settings=settings, trip=trip,
            card_res=card_res,
        )
        for r in company:
            d = r.detected_date
            if d is not None:
                if date_from is not None and d < date_from:
                    continue
                if date_to is not None and d > date_to:
                    continue
            if r.document_id in copies:
                _add(copies_bucket, run.run_id, r)
                continue
            if d is None:
                n_undated += 1
            name = cost_res[r.document_id].name
            bucket = by_center.setdefault(name, _bucket()) if name else unassigned
            _add(bucket, run.run_id, r)
            n_rows += 1
    for name, entry in registry.entries.items():
        if entry.get("active", True) is not False:
            by_center.setdefault(name, _bucket())

    def _emit(bucket: dict) -> dict:
        return {
            "n_rows": bucket["n_rows"],
            "n_batches": len(bucket["batches"]),
            "totals": {
                ccy: _fmt_amount(amt)
                for ccy, amt in sorted(bucket["totals"].items())
            },
        }

    centers = []
    for name in sorted(by_center, key=str.casefold):
        entry = registry.entries.get(name) or {}
        centers.append({
            "name": name,
            "kind": str(entry.get("kind") or ""),
            "active": entry.get("active", True) is not False,
            **_emit(by_center[name]),
        })
    return {
        "from": date_from.isoformat() if date_from else None,
        "to": date_to.isoformat() if date_to else None,
        "note": COST_CENTER_SCOPE_NOTE,
        "cost_centers": centers,
        "unassigned": _emit(unassigned),
        # Item 94: what the buckets above leave out as decided copies.
        "copies_set_aside": _emit(copies_bucket),
        "n_batches": n_batches,
        "n_rows": n_rows,
        "n_undated": n_undated,
    }


def report_view(
    run: RunRow,
    receipts: "list[Receipt]",
    snapshot_receipts: "list[Receipt]",
    decisions: dict,
    overrides: dict,
    resolutions: dict[str, str] | None,
    field_overrides: dict[str, dict[str, str]] | None = None,
) -> dict:
    """`build_view` over the reviewer's live pool, for a document.

    Hand `build_view` the live pool rather than post-filtering its output:
    the unmatched list, the duplicate groups, the candidates and the counts
    are all derived there, and re-deriving any of them in a report would be
    a second implementation of the same rules, the exact shape that let the
    two documents disagree in the first place.

    `field_overrides` reach `build_view` too, as they do on the GET route:
    the card a reviewer picked is what `rows[].cards_differ` (item 137)
    compares against, and without it the document never named a held pair
    whose cards disagree (found building item 138)."""
    if {r.document_id for r in receipts} != {
        r.document_id for r in snapshot_receipts
    }:
        run = replace(run, snapshot={
            **(run.snapshot or {}),
            "receipts": [receipt_to_dict(r) for r in receipts],
        })
    return build_view(
        run, decisions, overrides, resolutions, field_overrides=field_overrides
    )


def report_receipt_cards(
    receipts: "list[Receipt]",
    cfg: dict | None,
    field_overrides: dict[str, dict[str, str]] | None,
    *,
    merchants: dict | None = None,
) -> dict[str, tuple[str, str]]:
    """Item 138: `{document_id: (card key, card label)}` for every receipt,
    in pool order, `("", "")` for one with no card. The card is the one
    `resolve_batch_row_cards` resolves (a pick on the row, the printed
    method or an assigned hint, a remembered card), the same chain
    `bake_card_scope` hands the matcher (item 137), so a document files a
    receipt under the card it was matched on."""
    res = resolve_batch_row_cards(
        receipts, cfg, field_overrides or {}, merchants=merchants
    )
    out: dict[str, tuple[str, str]] = {}
    for r in receipts:
        card = (res.get(r.document_id) or {}).get("card")
        out[r.document_id] = (
            (card.key, card.display_label) if card is not None else ("", "")
        )
    return out


def month_card_tabs(
    view: dict,
    receipt_cards: dict[str, tuple[str, str]],
    cfg: dict | None,
) -> tuple[list[dict], dict[str, str], dict[str, str]]:
    """Item 138, the month page's half (owner ruling 2026-09-17: "a tab per
    card showing whether its statement is loaded, how many charges matched
    and what's still open, plus 'All' and 'No card'").

    `(sections, section key per transaction_id, section key per document_id)`.
    The grouping IS `_pdf_common.card_sections` over a `build_view` payload
    and the card chain `report_receipt_cards` resolves, the two inputs the
    PDFs section on, and each section's figures are `card_statement_figures`,
    the numbers its PDF heading line prints. A tab and its PDF section can
    therefore not disagree: a receipt a charge holds follows that charge's
    card, an unheld receipt goes to its resolved card (item 137), everything
    else to the no-card section, which is never dropped.

    Each section: `key` (the `coverage[].key`; "" is the no-card section,
    and since the registry drops a blank card key "" can never name a card),
    `label`, `digits` (the coverage entry's, else the registry card's, for a
    card only receipts name), the statement figures, `n_receipts` (every
    receipt filed there, copies and settled-outside ones included) and
    `n_receipts_without_charge` (those in the view's `unmatched_receipts`,
    the page's "Receipts without a charge").

    Item 147 (owner ruling 2026-09-18: "card 2838 for example should be an
    account with others as subcards") adds the tree, and ONLY when the
    registry names a parent: an account section carries `subcards` (the keys
    under it, in tab order), every figure above summed over itself and them,
    and `own` with the account card's own figures under the same names; a
    subcard carries `parent` and `statement_on_account`. A registry with no
    parent anywhere produces the list this returned before, field for field,
    which is what leaves every other month alone. A consumer that sums a
    figure across tabs sums the sections with no `parent`, or it counts the
    subcards twice.

    A month with fewer than two cards gets no sections, the PDFs' own rule
    (a heading restating the only card organizes nothing); the two maps are
    filled either way."""
    from ..cards import card_parents
    from ..output._pdf_common import (
        card_own_figures,
        card_sections,
        card_statement_figures,
    )

    cards = _batch_cards(cfg)
    grouped = card_sections(view, receipt_cards, card_parents(cards))
    by_tx = {
        str(row.get("transaction_id") or ""): sec["key"]
        for sec in grouped for row in sec["rows"]
    }
    by_doc = {doc: sec["key"] for sec in grouped for doc in sec["receipt_docs"]}
    unmatched = {
        str(rec.get("document_id") or "")
        for rec in view.get("unmatched_receipts") or []
    }
    sections: list[dict] = []
    for sec in grouped:
        digits = [
            str(d) for d in ((sec.get("coverage") or {}).get("digits") or [])
            if str(d).strip()
        ]
        if sec["key"] and not digits and sec["key"] in cards:
            digits = [str(d) for d in cards[sec["key"]].digits]
        sections.append({
            "key": sec["key"],
            "label": sec["label"],
            "digits": digits if sec["key"] else [],
            **card_statement_figures(sec),
            "n_receipts": len(sec["receipt_docs"]),
            "n_receipts_without_charge": sum(
                1 for doc in sec["receipt_docs"] if doc in unmatched
            ),
        })
    # Item 147: the receipt counts are the only figures this function owns, so
    # the account adds its subcards' here while `card_statement_figures` has
    # already summed the statement ones. `own` is filled from the pre-sum
    # values, which is why it is written before the addition.
    by_section = {s["key"]: s for s in sections}
    for sec, entry in zip(grouped, sections):
        subcards = [kid["key"] for kid in (sec.get("children") or [])]
        if subcards:
            entry["subcards"] = subcards
            entry["own"] = {
                **card_own_figures(sec),
                "n_receipts": entry["n_receipts"],
                "n_receipts_without_charge": entry["n_receipts_without_charge"],
            }
            entry["n_receipts"] += sum(
                by_section[key]["n_receipts"] for key in subcards
            )
            entry["n_receipts_without_charge"] += sum(
                by_section[key]["n_receipts_without_charge"] for key in subcards
            )
        elif sec.get("parent"):
            entry["parent"] = sec["parent"]
            entry["statement_on_account"] = bool(sec.get("statement_on_account"))
    if sum(1 for s in sections if s["key"]) < 2:
        sections = []
    return sections, by_tx, by_doc


def attach_run_card_tabs(
    view: dict, run: RunRow, field_overrides: dict[str, dict[str, str]] | None
) -> dict:
    """Item 138 on `GET /api/runs/{id}` (the Matching page): `card_sections`,
    and `card_section` on every element of `rows[]`, `unmatched_receipts[]`,
    `copies_set_aside[]` and `assignable_receipts[]`. Mutates and returns
    `view`, the route's own `build_view` payload.

    The cards are resolved over the pool that view was built on (the
    snapshot's receipts), the chain `build_view`'s `cards_differ` already
    reads; the reconciliation report files every receipt the same way on a
    month whose edits are baked, which is every month with a statement."""
    _, receipts, _, _ = snapshot_from_dict(run.snapshot)
    sections, by_tx, by_doc = month_card_tabs(
        view, report_receipt_cards(receipts, run.config, field_overrides), run.config
    )
    for row in view.get("rows") or []:
        row["card_section"] = by_tx.get(str(row.get("transaction_id") or ""), "")
    for listing in ("unmatched_receipts", "copies_set_aside", "assignable_receipts"):
        for rec in view.get(listing) or []:
            rec["card_section"] = by_doc.get(str(rec.get("document_id") or ""), "")
    view["card_sections"] = sections
    return view


def attach_expense_card_tabs(
    view: dict,
    run: RunRow,
    *,
    overrides: dict,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    resolutions: dict[str, str] | None,
    decisions: dict | None,
) -> dict:
    """Item 138 on `GET /api/expense-batches/{id}` (the Expenses page):
    `card_sections` and `expenses[].card_section`. Mutates and returns
    `view`, the route's own `build_expense_view` payload.

    The sections are the month report's: `report_view` and
    `report_receipt_cards` over `_expense_export_inputs`' pool, exactly as
    `build_expense_report` builds them, so a copy that borrowed its card
    (item 69) files where the grid shows it. On top of the reconciliation
    figures each section carries what the Expenses page counts, from the
    rows it renders: `n_expenses` (rows that count, decided copies left out,
    item 94) and `totals_by_ccy` (their totals, summed in Decimal as
    `summary.totals_by_ccy` is). On an account (item 147) both are the
    group's and `own` carries the account card's own, exactly as the
    statement figures behave, so the page never adds a tab's rows up for
    itself.

    A trip gets no sections: its documents section per traveler, not per
    card. Only the page GETs carry the tabs, so the edit routes that reply
    with this payload's summary pay nothing for them."""
    receipts, _kwargs = _expense_export_inputs(
        run, overrides, field_overrides, edits, resolutions
    )
    _, snapshot_receipts, _, _ = snapshot_from_dict(run.snapshot)
    card_view = report_view(
        run, receipts, snapshot_receipts, decisions or {}, overrides,
        resolutions, field_overrides=field_overrides,
    )
    sections, _by_tx, by_doc = month_card_tabs(
        card_view, report_receipt_cards(receipts, run.config, field_overrides),
        run.config,
    )
    if is_trip_batch(run):
        sections = []
    total_of = {
        r.document_id: (r.detected_currency or "?", r.detected_total)
        for r in receipts
    }
    # Item 192: whether a charge holds the row, from the same set the tab's
    # "{n} without a charge" counts (`month_card_tabs`), stamped on every row
    # because a month with fewer than two cards has no sections to carry it.
    unmatched = {
        str(rec.get("document_id") or "")
        for rec in card_view.get("unmatched_receipts") or []
    }
    counted: dict[str, int] = {}
    sums: dict[str, dict[str, Decimal]] = {}
    for expense in view.get("expenses") or []:
        doc = str(expense.get("document_id") or "")
        key = by_doc.get(doc, "")
        expense["card_section"] = key
        expense["without_charge"] = doc in unmatched
        if expense.get("counts_in_total") is False:
            continue
        counted[key] = counted.get(key, 0) + 1
        ccy, amount = total_of.get(doc, ("?", None))
        if amount is not None:
            per = sums.setdefault(key, {})
            per[ccy] = per.get(ccy, Decimal("0")) + amount
    # Every row is placed: the grid's rows and the export pool are one set of
    # documents (both are `apply_expense_edits` over the baseline, then the
    # copy card inheritance), and `card_sections` files every one of them.
    def _per_ccy(per: dict) -> dict:
        return {ccy: f"{amt:,.2f}" for ccy, amt in sorted(per.items())}

    for sec in sections:
        own_n = counted.get(sec["key"], 0)
        own_sums = dict(sums.get(sec["key"]) or {})
        n_total, sums_total = own_n, dict(own_sums)
        subcards = sec.get("subcards") or []
        if subcards:
            # Item 147: an account's pair is the group's, like every other
            # figure on its tab, and its own card's pair joins the rest of
            # its own figures in `own`.
            sec["own"]["n_expenses"] = own_n
            sec["own"]["totals_by_ccy"] = _per_ccy(own_sums)
            for key in subcards:
                n_total += counted.get(key, 0)
                for ccy, amount in (sums.get(key) or {}).items():
                    sums_total[ccy] = sums_total.get(ccy, Decimal("0")) + amount
        sec["n_expenses"] = n_total
        sec["totals_by_ccy"] = _per_ccy(sums_total)
    view["card_sections"] = sections
    return view


def reconciliation_captions(
    view: dict,
    receipts: "list[Receipt]",
    settled_outside: dict[str, dict],
    names: dict[str, str],
) -> dict[str, tuple[str, str]]:
    """`{document_id: (label, detail)}`: the caption over each receipt's
    pages in the reconciliation report, in the screen's words (item 96).

    Every receipt the view places sits in exactly one of five places, and
    the caption names which, read off `view` (`build_view`'s payload, the
    one the month page renders), never re-derived:

    * held by a charge: "Charge <date> · <vendor>", as before;
    * a decided copy (`copies_set_aside`): "Copy set aside", naming the
      receipt it repeats by vendor and file (the row's `duplicate.of`, the
      screen's own marker);
    * settled outside the card: the month report's tender caption
      (`settled_outside_caption`, item 62);
    * proposed for a charge still in review: "Waiting for review", naming
      the charge. A review row holds no `chosen_document_id` until a pick,
      so this receipt used to read as if nothing settled it;
    * none of those (`unmatched_receipts`): "Receipt with no charge" with
      the screen's reason line for its `reason_code` (items 75 + 83).

    `names` is `{document_id: display file name}` for the receipts with a
    stored file. "Unmatched receipt" is gone: it was printed over all five.
    """
    from ..unmatched_reasons import (
        NO_CHARGE_ON_ANY_LOADED_STATEMENT,
        RECEIPT_REASON_TEXT,
    )

    rows_by_tx = {
        str(row.get("transaction_id") or ""): row for row in view.get("rows") or []
    }
    charge_by_doc: dict[str, dict] = {}
    for row in view.get("rows") or []:
        doc = row.get("chosen_document_id")
        if doc:
            charge_by_doc[str(doc)] = row
    # `assignable_receipts[].held_by` names the charge holding a receipt,
    # a pending review row included; copies are not in that list.
    for entry in view.get("assignable_receipts") or []:
        holder = rows_by_tx.get(str(entry.get("held_by") or ""))
        if holder is not None:
            charge_by_doc.setdefault(str(entry.get("document_id") or ""), holder)
    reason_by_doc = {
        str(rec.get("document_id") or ""): str(rec.get("reason_code") or "")
        for rec in view.get("unmatched_receipts") or []
    }
    copy_of = {
        str(rec.get("document_id") or ""):
            str((rec.get("duplicate") or {}).get("of") or "")
        for rec in view.get("copies_set_aside") or []
    }
    vendor_of = {r.document_id: r.detected_vendor or "" for r in receipts}

    def _charge(row: dict) -> str:
        return " ".join(x for x in (
            str(row.get("vendor") or ""), str(row.get("amount") or ""),
            str(row.get("currency") or ""),
        ) if x) + (f" of {row.get('date')}" if row.get("date") else "")

    out: dict[str, tuple[str, str]] = {}
    for r in receipts:
        doc = r.document_id
        vendor = r.detected_vendor or "(no vendor)"
        facts = (
            str(r.detected_date or ""),
            (f"{r.detected_total} {r.detected_currency or ''}".strip()
             if r.detected_total is not None else ""),
        )
        charge = charge_by_doc.get(doc)
        if charge is not None and (
            charge.get("chosen_document_id") == doc
            or charge.get("effective_bucket") != "review"
        ):
            label = (
                f"Charge {charge.get('date') or ''} · "
                f"{charge.get('vendor') or ''}".strip(" ·")
            )
            detail = "  ·  ".join(x for x in (
                f"{charge.get('amount') or ''} {charge.get('currency') or ''}".strip(),
                f"receipt: {r.detected_vendor or ''}".strip(),
            ) if x.strip())
            out[doc] = (label, detail)
            continue
        if doc in copy_of:
            # Vendor and file both: live originals are often a mail body
            # named rendered-body.pdf, which alone finds nothing.
            of = copy_of[doc]
            original = " ".join(x for x in (
                vendor_of.get(of, ""), f"({names[of]})" if names.get(of) else "",
            ) if x) or "another receipt"
            label, why = f"Copy set aside · {vendor}", f"copy of {original}, set aside"
        elif charge is not None:
            label = f"Waiting for review · {vendor}"
            why = f"proposed for the charge {_charge(charge)}, not confirmed yet"
        elif doc in settled_outside and doc not in reason_by_doc:
            how = settled_outside_caption(settled_outside[doc]["how"])
            label, why = f"{how[:1].upper()}{how[1:]} · {vendor}", ""
        else:
            label = f"Receipt with no charge · {vendor}"
            why = RECEIPT_REASON_TEXT.get(
                reason_by_doc.get(doc, ""),
                RECEIPT_REASON_TEXT[NO_CHARGE_ON_ANY_LOADED_STATEMENT],
            )
        out[doc] = (label, "  ·  ".join(x for x in (*facts, why) if x))
    return out


def build_reconciliation_report(
    run: RunRow,
    decisions: dict,
    overrides: dict,
    resolutions: dict[str, str] | None = None,
    field_overrides: dict[str, dict[str, str]] | None = None,
    edits: list[dict] | None = None,
) -> bytes:
    """The statement reconciliation as a document (owner directive
    2026-08-23: nothing imports this either, so what serves the work is
    evidence that the month is complete, not a data file).

    Built from `build_view` — the workbench's OWN payload — so the document
    and the review screen cannot state different reconciliations. Evidence is
    every receipt the run holds: matched ones captioned with the charge they
    settle, every other one with where the screen puts it and why
    (`reconciliation_captions`, item 96), because a receipt nobody could
    place is exactly what a reader needs to see.

    `field_overrides` / `edits` are the expense-mode overlay (item 68). They
    are not an extra source: they are THE source, the same one the expense
    report and the review grid are built from. Without them this document
    read the stored receipt pool, which only catches up with the reviewer at
    the next re-match — so an expense deleted on a statement-less month left
    the expense report at once and stayed here, caption page, receipt pages
    and all, in a document whose whole job is to be the evidence that a
    month is complete. The overlay is idempotent by construction
    (`apply_expense_edits`), so applying it to an already-baked pool changes
    nothing; on a pool that was never baked the two reports now agree the
    moment the reviewer acts. Omitted => the pre-item-68 behaviour, which is
    what the CLI and the offline callers want.
    """
    from ..cards import card_parents
    from ..output.reconciliation_report_pdf import build_reconciliation_report_pdf

    _, snapshot_receipts, _, _ = snapshot_from_dict(run.snapshot)
    receipts = snapshot_receipts
    if field_overrides or edits:
        receipts = apply_expense_edits(
            snapshot_receipts, field_overrides or {}, edits or [],
            category_overrides=overrides,
            default_entity=(
                ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
            ),
        )
    view = report_view(
        run, receipts, snapshot_receipts, decisions, overrides, resolutions,
        field_overrides=field_overrides,
    )
    receipts_dir = Path(run.work_dir) / "receipts"
    path_by_doc: dict[str, Path] = {}
    for r in receipts:
        path = receipts_dir / r.document_id
        if not path.is_file():
            path = _attached_receipt_file(receipts_dir.parent, r.document_id)
        if path is not None:
            path_by_doc[r.document_id] = path
    captions = reconciliation_captions(
        view, receipts, settled_outside_map(run.snapshot or {}),
        {doc: _display_name(p.name) for doc, p in path_by_doc.items()},
    )

    evidence: list[dict] = []
    for r in receipts:
        label, detail = captions[r.document_id]
        item: dict = {
            "label": label, "detail": detail, "document_id": r.document_id,
        }
        path = path_by_doc.get(r.document_id)
        if path is not None:
            item["name"] = _display_name(path.name)
            item["data"] = path.read_bytes()
        evidence.append(item)

    label = run.label or run.run_id
    return build_reconciliation_report_pdf(
        # A colon, never an em-dash (the house deliverable standard; the same
        # call as the month report's title above).
        view, title=f"Reconciliation: {label}", evidence=evidence,
        # Item 138: the card each receipt nobody holds files under, from the
        # same chain the matcher scopes by (item 137).
        receipt_cards=report_receipt_cards(
            receipts, run.config, field_overrides
        ),
        # Item 147: which cards sit under an account, so the document's
        # sections nest the way the month page's tabs do.
        card_parents=card_parents(_batch_cards(run.config)),
    )


def assign_batch_cards(
    store: RunStore,
    run: RunRow,
    *,
    assignments: "list[dict]",
    new_cards: dict | None,
    learn: bool,
    now_iso: str,
) -> dict:
    """Apply operator hint -> card assignments to a batch (Cards R3), and
    optionally persist what they teach into ``settings["cards"]``.

    Deterministic persistence, never inference: an assignment records the
    EXACT hint string in the batch config (``expense.card_hints``) and
    folds the hint's identifying tokens into the card entry — its last
    digit run, or the digitless hint as an alias. Generic tender words
    ("Visa", "Cartão de crédito") assign for THIS batch only and are
    refused as learned tokens (owner ruling: they never auto-resolve).
    ``learn`` additionally writes the same tokens into the stored settings
    registry, so the NEXT batch resolves the hint on its own.

    Raises RunInputError on an unknown card key, an inactive card, a hint
    not present in the batch, or a malformed new-card payload.
    """
    from ..cards import normalize_cards_setting

    if not assignments and not new_cards:
        raise RunInputError(
            "Nothing to apply: no assignments and no new cards.",
            code="nothing_to_apply",
        )
    try:
        new_cards_clean = normalize_cards_setting(new_cards or {})
    except ValueError as exc:
        raise RunInputError(
            str(exc),
            code=code_of(exc, "card_definition_invalid"),
            **fields_of(exc),
        ) from exc

    # Same serialization as add_receipts_to_expense_batch: the config /
    # snapshot read-modify-write below must not interleave with a
    # concurrent ingest, assignment, or refresh on this batch (an
    # unserialized pair is last-write-wins). Re-fetch inside the lock so
    # the RMW starts from the current row.
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        # No statement refusal since 2b-2. A card assignment is exactly what
        # an operator needs mid-month: matching is entity-scoped, so a card
        # with no entity is what leaves a month matching nothing.
        out = _assign_batch_cards_locked(
            store, run,
            assignments=assignments,
            new_cards_clean=new_cards_clean,
            learn=learn,
            now_iso=now_iso,
        )
    # Outside the lock; see rematch_after_change. An assignment that does not
    # reach the matcher is the R3 F1 failure (silent 0-match month), so the
    # re-match is the point of allowing this at all.
    rematch = rematch_after_change(store, run.run_id, trigger="cards")
    if rematch is not None:
        out["rematch"] = rematch
    return out


def _assign_batch_cards_locked(
    store: RunStore,
    run: RunRow,
    *,
    assignments: "list[dict]",
    new_cards_clean: dict,
    learn: bool,
    now_iso: str,
) -> dict:
    from ..cards import (
        cards_from_setting,
        cards_to_setting,
        effective_cards,
        learnable_hint_tokens,
        legacy_card_accounts,
        normalize_cards_setting,
    )
    from ..cards_provision import load_cards

    _, receipts, _, _ = snapshot_from_dict(run.snapshot)
    batch_hints = {
        (r.payment_mode or "").strip()
        for r in receipts
        if (r.payment_mode or "").strip()
    }

    cfg = dict(run.config or {})
    exp = dict(cfg.get("expense") or {})
    cards_map = dict(exp.get("cards") or {})
    hints_map = dict(exp.get("card_hints") or {})

    settings = store.get_settings()
    composed_live = effective_cards(settings, load_cards())

    # A new card must actually be NEW: silently replacing an existing
    # entry through this endpoint would overwrite money-path master data
    # (digits, zoho_account) with a partial payload (adversarial review).
    for slug in new_cards_clean:
        if (
            slug in cards_map
            or slug in composed_live
            or slug in (settings.get("cards") or {})
        ):
            raise RunInputError(
                f"card {slug!r} already exists; edit it in Settings > Cards "
                "instead of re-creating it here",
                code="card_already_exists",
                card=slug,
            )
    for slug, entry in new_cards_clean.items():
        cards_map[slug] = dict(entry)

    parsed: list[tuple[str, str]] = []
    seen_hints: set[str] = set()
    for a in assignments:
        if not isinstance(a, dict):
            raise RunInputError(
                "each assignment must be an object", code="invalid_body"
            )
        hint = str(a.get("hint") or "").strip()
        card_key = str(a.get("card") or "").strip()
        if not hint or not card_key:
            raise RunInputError(
                "each assignment needs a hint and a card key",
                code="assignment_incomplete",
            )
        if hint in seen_hints:
            # Two assignments for one hint would teach BOTH cards the
            # hint's tokens and leave it permanently ambiguous — refuse
            # the contradiction instead of last-wins.
            raise RunInputError(
                f"hint {hint!r} is assigned more than once",
                code="hint_assigned_twice",
                hint=hint,
            )
        seen_hints.add(hint)
        if hint not in batch_hints:
            raise RunInputError(
                f"hint {hint!r} does not appear in this batch's receipts",
                code="hint_not_in_batch",
                hint=hint,
            )
        if card_key not in cards_map:
            # Materialize the batch-config entry from the live registry the
            # assignment UI offered (GET /api/cards). Unknown = typo, 400.
            live = composed_live.get(card_key)
            if live is None:
                raise RunInputError(
                    f"unknown card {card_key!r}",
                    code="card_not_defined",
                    card=card_key,
                )
            cards_map[card_key] = cards_to_setting({card_key: live})[card_key]
        if cards_map[card_key].get("active") is False:
            raise RunInputError(
                f"card {card_key!r} is inactive; reactivate it before "
                "assigning receipts to it",
                code="card_inactive",
                card=card_key,
            )
        parsed.append((hint, card_key))

    results: list[dict] = []
    settings_cards = dict(settings.get("cards") or {})
    settings_dirty = bool(new_cards_clean) and learn
    if learn:
        for slug, entry in new_cards_clean.items():
            settings_cards[slug] = dict(entry)

    def _fold_tokens(entry: dict, digit: str | None, alias: str | None) -> dict:
        out = dict(entry)
        if digit:
            digits = [str(d) for d in (out.get("digits") or [])]
            if digit not in digits:
                digits.append(digit)
            out["digits"] = digits
        if alias:
            aliases = [str(x) for x in (out.get("aliases") or [])]
            if alias not in aliases:
                aliases.append(alias)
            out["aliases"] = aliases
        return out

    for hint, card_key in parsed:
        hints_map[hint] = card_key
        digit, alias, refusal = learnable_hint_tokens(hint)
        cards_map[card_key] = _fold_tokens(cards_map[card_key], digit, alias)
        learned = False
        if learn and refusal is None:
            base = settings_cards.get(card_key)
            if base is None:
                # First explicit persistence of a composed/legacy card:
                # materialize exactly this one entry into settings.
                live = composed_live.get(card_key)
                base = (
                    cards_to_setting({card_key: live})[card_key]
                    if live is not None
                    else dict(cards_map[card_key])
                )
            settings_cards[card_key] = _fold_tokens(base, digit, alias)
            settings_dirty = True
            learned = True
        n_rows = sum(
            1 for r in receipts if (r.payment_mode or "").strip() == hint
        )
        results.append({
            "hint": hint,
            "card": card_key,
            "n_rows": n_rows,
            "learned": learned,
            **({"note": refusal} if refusal else {}),
        })

    if settings_dirty:
        # Validate ONLY the entries this request touched, then merge over
        # the stored map: re-normalizing unrelated stored entries would
        # 400 the whole request on pre-existing state this operator never
        # touched (adversarial review — a legacy generic alias elsewhere
        # in settings must not block learning on a clean card; stored-but-
        # invalid aliases are already inert at read time in resolve_card).
        touched = {
            k: settings_cards[k]
            for k in (set(new_cards_clean) | {ck for _, ck in parsed})
            if k in settings_cards
        }
        try:
            # Item 147: `known` is the stored map this partial one merges
            # over, so a subcard's `parent` still resolves when the account
            # it names is not one of the entries this request touched.
            normalized = normalize_cards_setting(touched, known=settings_cards)
        except ValueError as exc:  # defense in depth; tokens are pre-filtered
            raise RunInputError(
                str(exc),
                code=code_of(exc, "card_definition_invalid"),
                **fields_of(exc),
            ) from exc
        merged = dict(settings.get("cards") or {})
        merged.update(normalized)
        store.set_settings({"cards": merged}, now_iso)

    # The card -> Zoho account flat map the paid-through/export paths read:
    # grow it with the newly-taught digits, never shrink or repoint an
    # existing digit (money path; a full re-derive is refresh-master-data).
    flat = legacy_card_accounts(cards_from_setting(cards_map))
    merged_accounts = {**flat, **(exp.get("card_accounts") or {})}
    exp["cards"] = cards_map
    exp["card_hints"] = hints_map
    if merged_accounts:
        exp["card_accounts"] = merged_accounts
    cfg["expense"] = exp
    store.update_run_config(run.run_id, cfg)
    return {"ok": True, "results": results, "learned_to_settings": learn}


def refresh_batch_master_data(
    store: RunStore, run: RunRow, *, now_iso: str, operator: str | None
) -> dict:
    """Re-derive a batch's snapshotted master data from the CURRENT stored
    settings (Cards R3 — the explicit, audited fix for the snapshot trap:
    config is stamped at batch creation, so a later settings edit never
    reached an existing batch).

    Replaces `expense.cards` and `expense.card_accounts` with the freshly
    composed registry, re-resolves `expense.default_paid_through` from the
    entity registry, and injects a `coa_validation` block when the batch
    entity is provisioned and none exists. The batch's own operator
    assignments (`expense.card_hints`) are preserved — they are batch
    facts, not settings state. Every change is returned AND appended to
    the snapshot's `master_data_refreshes` audit trail. FX rates are
    statement-mode master data and have no expense-mode consumer.
    """
    # Same serialization + re-fetch as add_receipts_to_expense_batch: the
    # snapshot append below must not clobber a concurrent ingest's write.
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        # No statement refusal since 2b-2: the same reasoning as the card
        # assignment above, of which this is the bulk form.
        out = _refresh_batch_master_data_locked(
            store, run, now_iso=now_iso, operator=operator
        )
    rematch = rematch_after_change(store, run.run_id, trigger="master_data")
    if rematch is not None:
        out["rematch"] = rematch
    return out


def _refresh_batch_master_data_locked(
    store: RunStore, run: RunRow, *, now_iso: str, operator: str | None
) -> dict:
    from ..cards import cards_to_setting, effective_cards, legacy_card_accounts
    from ..cards_provision import load_cards
    from ..coa_provision import entity_from_settings

    settings = store.get_settings()
    composed = effective_cards(settings, load_cards())
    cfg = dict(run.config or {})
    exp = dict(cfg.get("expense") or {})
    changes: list[dict] = []

    old_cards = exp.get("cards") or {}
    new_cards = cards_to_setting(composed)
    # Operator assignment TARGETS survive the refresh: a card created for
    # this batch (`new_cards` + learn:false) exists only here, and
    # replacing the map wholesale would undo the operator's confirmed
    # work — rows flip back to needs_entity with a dangling hint mapping
    # (adversarial review). Batch-local entries NOT referenced by an
    # assignment are settings-derived and re-derive freely.
    hint_targets = set(_batch_card_hints(cfg).values())
    preserved = sorted(
        k for k in hint_targets if k in old_cards and k not in new_cards
    )
    for k in preserved:
        new_cards[k] = old_cards[k]
    if new_cards != old_cards:
        changed_keys = sorted(
            k
            for k in (set(old_cards) | set(new_cards))
            if old_cards.get(k) != new_cards.get(k)
        )
        entry: dict = {
            "field": "cards",
            "n_before": len(old_cards),
            "n_after": len(new_cards),
            "changed_keys": changed_keys,
        }
        if preserved:
            entry["preserved_assignment_targets"] = preserved
        changes.append(entry)
        if new_cards:
            exp["cards"] = new_cards
        else:
            exp.pop("cards", None)

    old_accounts = exp.get("card_accounts") or {}
    new_accounts = legacy_card_accounts(composed)
    if new_accounts != old_accounts:
        changes.append({
            "field": "card_accounts",
            "added": sorted(set(new_accounts) - set(old_accounts)),
            "removed": sorted(set(old_accounts) - set(new_accounts)),
            "changed": sorted(
                k
                for k in (set(old_accounts) & set(new_accounts))
                if old_accounts[k] != new_accounts[k]
            ),
        })
        if new_accounts:
            exp["card_accounts"] = new_accounts
        else:
            exp.pop("card_accounts", None)

    batch_entity = str(exp.get("legal_entity_id") or "")
    ent = entity_from_settings(settings, batch_entity) if batch_entity else None
    old_dpt = exp.get("default_paid_through")
    new_dpt = str(ent.get("default_paid_through") or "") if ent else ""
    # Only replace when the entity registry states one: an absent registry
    # entry keeps the creation-time value rather than silently clearing it.
    if new_dpt and new_dpt != (old_dpt or ""):
        changes.append({
            "field": "default_paid_through", "before": old_dpt, "after": new_dpt,
        })
        exp["default_paid_through"] = new_dpt

    cfg["expense"] = exp
    if cfg.get("coa_validation") is None and batch_entity:
        with_coa = apply_coa_provisioning(cfg, batch_entity, settings=settings)
        if with_coa.get("coa_validation") is not None:
            changes.append({
                "field": "coa_validation",
                "before": None,
                "after": with_coa["coa_validation"].get("entity_label"),
            })
            cfg = with_coa

    if changes:
        # Row impact: how many rows' RESOLVED entity this refresh moves —
        # the registry-level diff alone hides that one click can flip a
        # whole reviewed batch (adversarial review). Same chain the grid
        # and export run.
        try:
            _, receipts, _, _ = snapshot_from_dict(run.snapshot)
            fo = store.get_expense_field_overrides(run.run_id)
            reg_merchants = (settings or {}).get("merchants")
            before = resolve_batch_row_cards(
                receipts, run.config, fo, merchants=reg_merchants
            )
            after = resolve_batch_row_cards(
                receipts, cfg, fo, merchants=reg_merchants
            )
            n_moved = sum(
                1
                for doc in before
                if before[doc]["entity"] != after.get(doc, before[doc])["entity"]
            )
            if n_moved:
                changes.append({"field": "row_entities", "n_rows_changed": n_moved})
            # Item 40: person moves are the same one-click-flips-a-batch
            # hazard — a person added to a card re-attributes every row
            # on that card, and the audit should say how many.
            n_person_moved = sum(
                1
                for doc in before
                if before[doc].get("person")
                != after.get(doc, before[doc]).get("person")
            )
            if n_person_moved:
                changes.append(
                    {"field": "row_persons", "n_rows_changed": n_person_moved}
                )
            # Item 47: a card's `default_cost_center` reaches an existing
            # batch only through this refresh, so the audit says how many
            # rows' RESOLVED cost center it moved. The chain runs on both
            # sides with the batch's real trip, so a trip that outranks
            # the card default masks the move here exactly as on the row.
            trip_cc = None
            if is_trip_batch(run):
                trip_row = store.get_trip(
                    str((run.config or {}).get("trip_id") or "")
                )
                if trip_row is not None:
                    trip_cc = {"cost_center": trip_row.cost_center}
            cc_before = resolve_batch_row_cost_centers(
                receipts, fo, settings=settings, trip=trip_cc, card_res=before,
            )
            cc_after = resolve_batch_row_cost_centers(
                receipts, fo, settings=settings, trip=trip_cc, card_res=after,
            )
            n_cc_moved = sum(
                1
                for doc in cc_before
                if cc_before[doc].name != cc_after.get(doc, cc_before[doc]).name
            )
            if n_cc_moved:
                changes.append(
                    {"field": "row_cost_centers", "n_rows_changed": n_cc_moved}
                )
        except Exception:  # noqa: BLE001 - impact count must not break refresh
            pass
        store.update_run_config(run.run_id, cfg)
        snapshot = dict(run.snapshot or {})
        audit = list(snapshot.get("master_data_refreshes") or [])
        audit.append({"at": now_iso, "operator": operator, "changes": changes})
        snapshot["master_data_refreshes"] = audit
        store.update_run_snapshot(run.run_id, snapshot)
    return {"ok": True, "changes": changes}


# --------------------------------------------------------------------------
# Batch lifecycle (owner directive 2026-07-28): receipts arrive gradually
# all month, the statement only at month end. An expense batch is the
# month's container — receipts get ADDED to it over time, and attaching a
# statement later graduates it into a full reconciliation on the SAME run
# row (the "same object at two life-stages" model). No statement, no card
# id needed to start; both are asked at attach time.
# --------------------------------------------------------------------------


def has_statement(run: RunRow) -> bool:
    """True once a statement was attached to this run (the snapshot carries
    transactions). Statement runs are always True; a pre-attach expense
    batch is False."""
    return bool((run.snapshot or {}).get("transactions"))


def month_transactions(run: RunRow) -> list:
    """The charges this month currently holds, rebuilt from its snapshot.

    What a statement upload folds into (`merge_transactions`). Reads the
    transaction block ALONE rather than going through `snapshot_from_dict`,
    which would rebuild every receipt and the whole match outcome to reach
    it; the same narrow read `has_statement` does one function up.
    """
    return [
        transaction_from_dict(x)
        for x in (run.snapshot or {}).get("transactions") or []
    ]


# ── The uploads a month has taken (PR 2b-2b-2) ──────────────────────────
# `has_statement` answers "is this month reconciling"; it cannot answer
# "which cards have I loaded, over what periods, and what did each upload
# actually contribute". A month takes several statements now, so that
# question has an answer worth keeping, and the writeback needs it to know
# which workbook it is annotating.
#
# Parallel field, per the SPA contract (docs/api-contract.md rule 1):
# nothing existing changes type or meaning, so a stale SPA renders exactly
# what it rendered before.


def run_month_health(run: RunRow) -> dict:
    """Item 57 for a caller that has not unpacked the snapshot (the expense
    grid). Reads the same committed pool and outcome the workbench judges,
    so the two payloads cannot disagree about whether a month is broken.
    Unchecked before the first statement: there is nothing to judge."""
    if not has_statement(run):
        return unchecked_month_health()
    try:
        transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    except (KeyError, TypeError, ValueError):
        return unchecked_month_health()
    return month_health(
        transactions, receipts, outcome,
        card_scoping=card_scoping_on(run.config),
    )


# Item 58: every commit of `rematch_month` records one event here, so the
# dev-side notifier can announce a re-match by its counts ("August 2026: 14
# of 111, pool 7") instead of only a new run. Capped: the snapshot is not
# a log, and fifty events outlive any notifier polling window.
REMATCH_LOG_KEY = "rematch_log"
REMATCH_LOG_CAP = 50


def append_rematch_event(existing, event: dict, cap: int = REMATCH_LOG_CAP) -> list[dict]:
    """The log with `event` appended and the oldest entries dropped past
    `cap`. Tolerates a malformed stored value (drops it rather than raising:
    a corrupt log must never block a commit)."""
    log = [e for e in (existing or []) if isinstance(e, dict)] if isinstance(existing, list) else []
    log.append(dict(event))
    return log[-cap:] if cap > 0 else log


# Item 113 (2026-09-17 voids audit): a re-match that is OWED and has not yet
# committed. Every arrival re-matches its month after the receipt is stored,
# so a re-match that raised (a model outage) or was cut off by a restart
# (every deploy is one) left the month describing itself as it was before,
# and nothing recorded that the second step never ran; re-running the
# interrupted job found no new files and skipped the re-pairing too. The
# mark is written with the change, cleared by the commit of a re-match that
# READ it (same `id`: a change landing mid-match writes a new id and keeps
# its debt), carries the last error, and is re-paired at startup.
REMATCH_PENDING_KEY = "rematch_pending"


def rematch_pending_mark(snapshot: dict | None, trigger: str) -> dict:
    """A fresh owed-re-match mark (new `id`), keeping how long the month has
    owed one (`since`) and any recorded failure from an earlier mark."""
    prior = (snapshot or {}).get(REMATCH_PENDING_KEY)
    prior = prior if isinstance(prior, dict) else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    mark = {
        "id": uuid.uuid4().hex[:12],
        "since": str(prior.get("since") or now),
        "changed_at": now,
        "trigger": str(trigger or ""),
    }
    for key in ("error", "failed_at", "attempts"):
        if key in prior:
            mark[key] = prior[key]
    return mark


def rematch_pending(run) -> dict | None:
    """The run's owed-re-match mark, or None."""
    if run is None:
        return None
    mark = (run.snapshot or {}).get(REMATCH_PENDING_KEY)
    return mark if isinstance(mark, dict) and mark.get("id") else None


# Item 129 (2026-09-18): the keys of a `rematch_log` event the month payload
# repeats. `run_id` and `label` are the payload's own top-level fields, and
# `match_rate` is `n_matched` over `n_transactions`, which are both here.
_LAST_REMATCH_KEYS = (
    "at", "trigger", "n_transactions", "n_matched", "n_review",
    "n_unmatched_tx", "n_receipts", "n_unmatched_rec", "event_id",
)


def rematch_visibility(snapshot: dict | None) -> dict:
    """Item 129 (2026-09-18): what the month page prints about re-matching,
    read off two stored snapshot keys and nothing else. A re-match happened
    silently: neither the drop page nor the month page said it ran, because
    neither payload carried the last commit or the owed mark, and the SPA
    cannot render what it is not handed.

    `last_rematch`: the newest `rematch_log` event (the log is oldest first)
    reduced to `_LAST_REMATCH_KEYS`; None when the month has never committed
    a re-match, an empty or malformed log included. `rematch_pending`: the
    owed mark as stored minus its `id` (a correlation handle for the commit
    that pays it, not a fact for a reader); None when nothing is owed, by
    the same rule `rematch_pending` applies (a mark without an id is not a
    mark). Never raises: a corrupt value reads as null.
    """
    snap = snapshot if isinstance(snapshot, dict) else {}
    last = None
    log = snap.get(REMATCH_LOG_KEY)
    if isinstance(log, list):
        events = [e for e in log if isinstance(e, dict)]
        if events:
            last = {key: events[-1].get(key) for key in _LAST_REMATCH_KEYS}
    mark = snap.get(REMATCH_PENDING_KEY)
    pending = None
    if isinstance(mark, dict) and mark.get("id"):
        pending = {key: value for key, value in mark.items() if key != "id"}
    return {"last_rematch": last, "rematch_pending": pending}


def _record_rematch_failure(store: RunStore, run_id: str, trigger: str, error: str) -> None:
    """Write a failed re-match onto the month's mark (creating the mark when
    the change that owed it did not write one). Best-effort: a failure to
    record never turns a reported error into a raised one."""
    try:
        with _BATCH_ADD_LOCK:
            fresh = store.get_run(run_id)
            if fresh is None or not has_statement(fresh):
                return
            snapshot = dict(fresh.snapshot or {})
            # A NEW id: a re-match that read the month before this failed
            # attempt must not clear the failure when it commits (review).
            mark = rematch_pending_mark(snapshot, trigger)
            snapshot[REMATCH_PENDING_KEY] = {
                **mark,
                "error": str(error)[:400],
                "failed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "attempts": int(mark.get("attempts") or 0) + 1,
            }
            store.update_run_snapshot(run_id, snapshot)
    except Exception:  # noqa: BLE001 - the error is already in the result
        pass


def _ensure_rematch_pending(store: RunStore, run_id: str, trigger: str) -> None:
    """Owe a re-match before running it, so a restart mid-match leaves the
    debt on the month. Always a NEW id (keeping `since` and any recorded
    failure): a re-match already in flight read the month before this
    change, so its commit must not clear this change's debt (review)."""
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run_id)
        if fresh is None:
            return
        snapshot = dict(fresh.snapshot or {})
        snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(snapshot, trigger)
        store.update_run_snapshot(run_id, snapshot)


def resume_pending_rematches(db_path, learning_db_path=None) -> list[str]:
    """Startup: re-pair every statement month still owing a re-match. The
    months it re-matched (or tried to; a failure stays on the mark)."""
    done: list[str] = []
    with RunStore(db_path) as store:
        owed = [
            r.run_id for r in store.list_runs()
            if rematch_pending(r) is not None and has_statement(r)
        ]
        for run_id in owed:
            rematch_after_change(
                store, run_id, learning_db_path=learning_db_path,
                trigger="resume",
            )
            done.append(run_id)
    return done


STATEMENTS_KEY = "statements"
# {stored file name: {transaction_id: sheet row}} — each upload's own row
# map, kept out of `statements[]` because it is machinery for the sheet
# writeback and not something a reviewer or the SPA reads.
STATEMENT_ANCHORS_KEY = "statement_anchors"


def statement_anchors(run: RunRow, file: str) -> dict[str, int] | None:
    """One statement's transaction-id to sheet-row map, or None when the run
    has none recorded (every run created before PR 2b-2b-2, and the CLI).

    A charge occupies a row in EVERY file that prints it, at a different row
    in each: a mid-month partial and the closing cycle both contain it. The
    row therefore cannot live on the charge, which can only name one file.
    Recording it per upload is what lets each of Criss's workbooks be
    annotated completely and correctly, rather than each getting only the
    charges it happened to introduce.

    "Recorded and EMPTY" is not "not recorded", and the difference is
    load-bearing: a PDF statement has a real, empty map, and treating that
    as "no map" would drop the writeback back to placing every charge in the
    month by its own row number. The other way to reach an empty map used to
    be a workbook that parsed no rows; since item 51 that upload is refused
    before it is recorded, so a workbook always has the rows it printed.
    """
    per_file = (run.snapshot or {}).get(STATEMENT_ANCHORS_KEY) or {}
    if file not in per_file:
        return None
    return {str(k): int(v) for k, v in (per_file[file] or {}).items()}


def _upload_anchors(transactions: list) -> dict[str, int]:
    """The id-to-row map for one parsed upload. Empty for a PDF statement,
    whose charges have no tabular row at all."""
    return {
        t.transaction_id: t.source_row
        for t in transactions
        if t.source_row is not None
    }


def month_statements(run: RunRow) -> list[dict]:
    """The statement uploads this month has taken, oldest first.

    Empty for every run created before this field existed, including months
    that are reconciling. Absence means "not recorded", never "none loaded";
    `has_statement` stays the answer to whether a month has a statement at
    all.
    """
    return list((run.snapshot or {}).get(STATEMENTS_KEY) or [])


# Note item T2 (2026-09-18): a statement upload's identity is its BYTES.
STATEMENT_ID_HEX = 16


def statement_content_id(path: Path) -> str:
    """The content-derived id of one stored statement file: the first 16 hex
    characters of the sha256 over its bytes, or "" when the file cannot be
    read (nothing then records an id, and absence means "not recorded").

    The same bytes uploaded twice, or re-read after a restore, yield the
    same id; a corrected file yields a new one. That is what `file` cannot
    say: `file` is the name on disk, made unique per upload
    (`statement-2.xlsx`), so two per-card exports that share the bank's
    filename get two names for what may be one file, and a re-upload of the
    same workbook gets a second name for the same bytes. The CLI store
    (`store/statements.py`) hashes the parsed transactions instead; this
    hashes the file, because it is the file a person can put beside the id.
    """
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return ""
    return digest[:STATEMENT_ID_HEX]


def _anchor_keys(entry: dict) -> list[str]:
    """The keys one upload's anchors are recorded under: its stored file
    name, and its `statement_id` when the entry carries one. Recording the
    same map twice is deliberate: the writeback and the re-read can address
    an upload by id when two per-card exports share a filename, and every
    reader that only knows the file name keeps working."""
    keys = [str(entry.get("file") or "")]
    sid = str(entry.get("statement_id") or "")
    if sid and sid not in keys:
        keys.append(sid)
    return [k for k in keys if k]


def statement_entry_by_id(run: RunRow, statement_id: str) -> dict | None:
    """The FIRST `statements[]` entry recorded with this id, or None.

    Two entries can share an id (the same bytes attached twice, which the
    fold absorbs as `n_new: 0`); they printed the same rows at the same
    sheet rows, so their anchors are the same map and the first is as good
    as the second."""
    wanted = (statement_id or "").strip()
    if not wanted:
        return None
    for entry in month_statements(run):
        if str(entry.get("statement_id") or "") == wanted:
            return entry
    return None


def _parse_utc(value) -> datetime | None:
    """One stored timestamp as an aware UTC datetime, or None when it is not
    a readable ISO string. A naive value is read as UTC, which is what every
    writer in this app records (`_now_iso` is UTC)."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def month_updated_at(
    run: RunRow,
    *,
    decisions: dict | None = None,
    edits: list[dict] | None = None,
    edited_at: str | None = None,
) -> str:
    """When this month last changed, as `YYYY-MM-DDTHH:MM:SS+00:00`.

    Both review payloads carry it top-level (2026-09-16). The SPA rendered
    `updated_at ?? created_at` as "Last updated" and neither payload had one,
    so every month printed its creation day: September read Sep 07 while its
    last receipt arrived on the 16th.

    The latest of: the month's creation, the last receipt add
    (`expense_ingest.at`), every statement upload, every re-match commit,
    every settled-outside disposition, every set-aside and restore, every
    decision the builder was handed, every edit row carrying a stamp, and
    `edited_at` -- the route's read of the edit tables
    (`RunStore.latest_edit_at`), because a field edit on a month without a
    statement leaves no trace in the snapshot at all.

    Never raises: an unreadable or empty stamp is skipped. When nothing
    parses, `run.created_at` comes back exactly as stored.
    """
    snapshot = run.snapshot if isinstance(run.snapshot, dict) else {}
    candidates: list = [run.created_at]
    ingest = snapshot.get("expense_ingest")
    if isinstance(ingest, dict):
        candidates.append(ingest.get("at"))
    for entry in month_statements(run):
        if isinstance(entry, dict):
            candidates.append(entry.get("uploaded_at"))
    rematches = snapshot.get(REMATCH_LOG_KEY)
    if isinstance(rematches, list):
        candidates.extend(e.get("at") for e in rematches if isinstance(e, dict))
    candidates.extend(e.get("at") for e in settled_outside_map(snapshot).values())
    set_aside = snapshot.get("set_aside")
    if isinstance(set_aside, list):
        for e in set_aside:
            if isinstance(e, dict):
                candidates.extend((e.get("at"), e.get("restored_at")))
    for decision in (decisions or {}).values():
        candidates.append(getattr(decision, "updated_at", None))
    for edit in edits or []:
        if isinstance(edit, dict):
            candidates.append(edit.get("updated_at"))
    candidates.append(edited_at)

    parsed = [p for p in map(_parse_utc, candidates) if p is not None]
    if not parsed:
        return run.created_at
    return max(parsed).replace(microsecond=0).isoformat()


def _statement_period(transactions: list) -> tuple[str | None, str | None]:
    """(earliest, latest) transaction date in one upload, ISO, or (None,
    None) when it parsed no rows."""
    dates = [t.transaction_date for t in transactions if t.transaction_date]
    if not dates:
        return None, None
    return min(dates).isoformat(), max(dates).isoformat()


def statement_read_nothing(upload_name: str, sheet_name: str | None) -> str:
    """The refusal for a statement file that mapped cleanly and then yielded
    no charge at all (item 51).

    The column-map 400 already catches a file MISSING a required column. It
    cannot catch a file whose columns map fine and whose rows the parser
    then reads as nothing, which is what a wrong worksheet, a header row
    that is not the first row, and a date format the parser rejects all
    look like from here. Before this refusal the attach returned
    `200 {"ok": true}`, the job finished `done`, and the month recorded
    `n_rows: 0` — and then graduated to the reconciliation workbench with
    zero charges, so on screen it read as a month that had taken its
    statement. Criss would have had no way to tell that from a month that
    reconciled.

    Deliberately keyed on `n_rows`, never on `n_new`. Zero NEW charges is
    the ordinary result of the same file arriving twice, which the fold
    exists to absorb; zero ROWS means the file held nothing, and that is
    never a legitimate outcome for a statement.
    """
    where = f" (sheet {sheet_name})" if sheet_name else ""
    return (
        f"{upload_name}{where} mapped cleanly but held no charge the parser "
        "could read, so nothing was added and this month is unchanged. The "
        "usual causes are the wrong worksheet, a header row below the first "
        "row, or a date format the parser does not read. Check the file and "
        "attach it again."
    )


def build_statement_entry(
    *,
    stored_name: str,
    upload_name: str,
    account_id: str,
    card_key: str,
    sheet_name: str | None,
    transactions: list,
    n_new: int,
    uploaded_at: str,
    column_map: dict | None = None,
    card_currency: str = "",
    statement_id: str = "",
) -> dict:
    """One `statements[]` row: what this upload was and what it added.

    `statement_id` (note item T2, 2026-09-18) is the content-derived id of
    the stored file (`statement_content_id`). Parallel and ABSENT on every
    entry written before it, never null; both callers compute it from the
    bytes on disk, so an attach and a later re-read of the same file agree.

    `file` is the name on disk, which is what `Transaction.source_file`
    carries and what the writeback selector addresses; `upload_name` is what
    Criss actually sent, kept because the two differ whenever two of her
    per-card exports share the bank's filename.

    `n_rows` is what the file held, `n_new` what the fold put in the month.
    The difference is charges the month already had, which is the ordinary
    result of a partial followed by the full cycle rather than a problem.

    `column_map` and `card_currency` record HOW this upload was read (item
    64). Both are parallel fields and both are ABSENT on every entry written
    before 2026-09-15, never null, so a reader can tell "not recorded" from
    "recorded as nothing". A PDF statement has no column map and gets no
    key. Before they existed, a re-read recovered the map from
    `config.statement`, which only ever describes the LATEST upload, and
    applied that upload's currency to every file in the month.
    """
    period_start, period_end = _statement_period(transactions)
    recorded_map = dict(column_map) if column_map else None
    currency = (card_currency or "").strip().upper()
    return {
        "file": stored_name,
        "upload_name": upload_name,
        "card_key": card_key or "",
        "account_id": account_id or "",
        # The worksheet inside THIS workbook. Recorded per upload because
        # `config.statement` only ever describes the latest one, and writing
        # an earlier statement back into the current statement's sheet name
        # is the same class of wrong-cell write as ignoring `source_file`.
        "sheet_name": sheet_name or None,
        "period_start": period_start,
        "period_end": period_end,
        "n_rows": len(transactions),
        "n_new": n_new,
        "uploaded_at": uploaded_at,
        "writeback": Path(stored_name).suffix.lower() in (".xlsx", ".xlsm"),
        # Filled in at commit time by `statement_advisory`, against the
        # entries the month holds at that moment.
        "advisory": None,
        # How this upload was read (item 64), for the re-read to reuse
        # instead of guessing again. Absent, not null, when unrecorded.
        **({"column_map": recorded_map} if recorded_map else {}),
        **({"card_currency": currency} if currency else {}),
        # What the bytes are (note item T2). Absent when not computed.
        **({"statement_id": statement_id} if statement_id else {}),
        # This file's own id-to-row map. Underscored and popped at commit
        # into `statement_anchors`, so it never reaches the SPA: it is a
        # per-row map the size of the statement, and nothing renders it.
        "_anchors": _upload_anchors(transactions),
        # Every charge this upload printed, with wherever it printed it
        # (note item T3). Popped at commit into `statement_origins`, the
        # same way and for the same reason as the anchors. Distinct from
        # them: the anchors keep only the rows the writeback can address,
        # so a PDF's charges are absent from them entirely and would have
        # no upload to name.
        "_origins": upload_origins(transactions),
    }


def _periods_overlap(a: dict, b: dict) -> bool:
    """Whether two entries' date ranges touch. False when either has none,
    because an upload that parsed no dated rows makes no claim about a
    period and must not produce an advisory out of nothing."""
    a0, a1, b0, b1 = (
        a.get("period_start"), a.get("period_end"),
        b.get("period_start"), b.get("period_end"),
    )
    if not (a0 and a1 and b0 and b1):
        return False
    return a0 <= b1 and b0 <= a1


def statement_advisory(prior: list[dict], entry: dict) -> str | None:
    """One sentence about an upload that looks like it doubled the month, or
    None.

    Two shapes reach the same outcome, and the outcome is deliberate: the
    fold surfaces a disagreement as two rows and never picks a winner. That
    is right (deduping a contradiction would silently choose whichever file
    arrived first) but it is not self-explanatory on screen, where the month
    simply holds twice the charges it should. So both get said out loud, and
    neither is refused.

    * **The same card typed against a different account id.** `account_id`
      is part of transaction identity, so the two uploads dedupe against
      nothing. Honest at the fold layer, since the rows really do claim to
      be different accounts, and the route cannot silently correct it
      without overriding what the operator explicitly typed. Needs a
      `card_key` on both uploads: without a card preset there is nothing
      that says the two files are one card, and the second shape below is
      what catches it instead.
    * **An upload over a period the same account already covers, with no row
      in common.** The usual cause is a sign inference that differs between
      a partial and a full export, which gives one printed row two content
      ids (see `ingest._common.assign_content_ids`).

    Advisory only. Nothing is dropped, merged, or refused on the strength of
    a heuristic about what an operator probably meant.
    """
    card = (entry.get("card_key") or "").strip()
    account = (entry.get("account_id") or "").strip()
    for other in prior:
        if (
            card
            and (other.get("card_key") or "").strip() == card
            and (other.get("account_id") or "").strip() != account
        ):
            return Refusal(
                f"This card's earlier statement ({other['file']}) was read as "
                f"account {other.get('account_id') or '(none)'}, this one as "
                f"{account or '(none)'}. A charge cannot be recognized as the "
                "same charge under two account ids, so anything that appears "
                "in both files is now in the month twice. Check the account "
                "id before working from these numbers.",
                code="statement_account_differs",
                other_file=str(other["file"]),
                other_account=str(other.get("account_id") or ""),
                account=account,
            )
    n_rows, n_new = entry.get("n_rows") or 0, entry.get("n_new") or 0
    if n_rows and n_new == n_rows:
        for other in prior:
            if (
                (other.get("account_id") or "").strip() == account
                and _periods_overlap(other, entry)
            ):
                return Refusal(
                    f"All {n_rows} charges in this upload are new, but "
                    f"{other['file']} already covers "
                    f"{other['period_start']} to {other['period_end']} on the "
                    "same account. If this is that statement re-exported, the "
                    "two files disagree about the rows (a flipped sign is the "
                    "usual cause) and the month now holds both readings.",
                    code="statement_period_overlap",
                    n_rows=n_rows,
                    other_file=str(other["file"]),
                    period_start=str(other["period_start"]),
                    period_end=str(other["period_end"]),
                )
    return None


# ── Per-card coverage (PR 3 of the living month) ────────────────────────
# `statements[]` says which FILES a month has taken. It cannot say which
# CARDS those files covered, over what span, or how far along each one is,
# and that is the question an accountant working a living month actually
# has: "I load per card, several times a month; which of my cards is done,
# which is half in, which have I not loaded at all?"
#
# Live evidence for why the card is the right axis: the January 2026 run
# holds 80 charges across THREE card identities (2838 / 3645 / 0340), zero
# reconciled, USD 20,228.68 unreconciled. Flat, that is one number nobody
# can act on. Split per card it is three, each belonging to a different
# piece of plastic and a different pile of receipts.
#
# Parallel field per the SPA contract (docs/api-contract.md rule 1): empty
# on every month that has taken no statement, so absence keeps meaning
# "nothing loaded", and no existing field changes type or meaning.

# The four buckets the run summary counts (`n_reconciled` / `n_review` /
# `n_unmatched_tx` / `n_refunds`), whose sum is `n_transactions`. Coverage
# carries the SAME four names for the same questions, per the one-name-
# one-question rule, so a card's row and the month's summary can be added
# up against each other, and must agree.
_BUCKET_COUNTER = {
    "reconciled": "n_reconciled",
    "review": "n_review",
    "refund": "n_refunds",
    "unmatched": "n_unmatched_tx",
}

# What a charge that names no card at all is called on screen. Composed
# here rather than in the SPA for the same reason `status_label` is
# (docs/api-contract.md rule 5): the backend is the only side that knows
# the difference between "no card printed on this charge" and "a card we
# have not met", and a consumer guessing between them mislabels money.
NO_CARD_LABEL = "No card on the charge"

# Prefix for the key of a card the registry does not know, so a bare digit
# token can never collide with a registry key. Cards are keyed by an
# operator-chosen slug, and nothing stops that slug from being digits that
# are not the card's own ("2838" as the key of a card whose digits are
# 9999). Without the prefix, charges on the REAL 2838 would land in that
# card's row and its money would be reported against the wrong plastic.
_UNKNOWN_KEY_PREFIX = "digits:"


class _CardIdentity(NamedTuple):
    """Which coverage row something belongs to, and what to call it."""

    key: str
    card_key: str   # the registry's key, "" when the registry has not met it
    label: str      # always renderable; "" only for the no-card identity
    digits: tuple[str, ...]


_NO_CARD = _CardIdentity("", "", "", ())


def charge_states(
    transactions: list,
    effective: MatchOutcome,
    decisions: dict[str, Decision],
) -> dict[str, dict]:
    """Per charge: `{bucket, held_doc, is_posted}` under the reviewer's
    effective verdict.

    ONE derivation, because three consumers have to agree about it: the
    workbench rows, the run summary's four counters, and the per-card
    coverage roll-up. A card row reading "reconciled" while the summary
    reads "unmatched" is the `n_categorized` failure of 2026-08-22
    (docs/api-contract.md, "Summary counts: one name, one question") with
    money attached to it, and the only structural way to prevent it is for
    both to read one map instead of each computing a bucket.

    `bucket` is a key of `_BUCKET_COUNTER`; `held_doc` is the receipt the
    charge currently holds (None when it holds none); `is_posted` is the
    settled-by-definition flag, from Criss's own yellow fill or the
    reviewer's already-posted verdict, which is why a posted charge never
    counts as unreconciled money.
    """
    eff_match_by_tx = {m.transaction_id: m for m in effective.matches}
    eff_review_tx = {m.transaction_id for m in effective.judgment_required} | {
        m.transaction_id for m in effective.ambiguous
    }
    eff_refund_tx = set(effective.refunds)

    states: dict[str, dict] = {}
    for tx in transactions:
        tx_id = tx.transaction_id
        decision = decisions.get(tx_id)
        status = decision.status if decision else STATUS_PENDING
        if tx_id in eff_match_by_tx:
            bucket, held_doc = "reconciled", eff_match_by_tx[tx_id].document_id
        elif tx_id in eff_review_tx:
            bucket = "review"
            held_doc = decision.chosen_document_id if decision else None
        elif tx_id in eff_refund_tx:
            bucket, held_doc = "refund", None
        else:
            bucket, held_doc = "unmatched", None
        states[tx_id] = {
            "bucket": bucket,
            "held_doc": held_doc,
            "is_posted": (
                tx.entry_status == "posted" or status == STATUS_ALREADY_POSTED
            ),
        }
    return states


def month_charge_states(
    run: RunRow, decisions: dict
) -> tuple[list, dict[str, dict]]:
    """`(charges, states)` for a caller that has not already built the
    effective outcome: the expense grid, which is receipt-spine and never
    needed one.

    Returns the charges as well as their states so `month_coverage` can be
    handed BOTH from one read. A caller that re-read the snapshot for the
    second half could be rolling up charges whose states it never computed,
    and the roll-up would then have to invent a bucket for them.

    Reads the snapshot itself rather than borrowing the grid's receipts: the
    grid composes from the extraction BASELINE (pre-bake) and matching ran
    against the baked pool, so feeding the baseline into `apply_decisions`
    would answer a subtly different question than the workbench does. Same
    input, same answer, or it is not one definition.

    Empty for a month with no charges, which is every month before its first
    statement, and the reason this costs nothing on the common path.
    """
    if not has_statement(run):
        return [], {}
    transactions, receipts, outcome, _ = snapshot_from_dict(run.snapshot)
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    return transactions, charge_states(transactions, effective, decisions)


def effective_charge_counts(
    transactions: list,
    outcome: MatchOutcome,
    receipts: list,
    decisions: dict,
) -> dict[str, int]:
    """The four charge counters in the STORED summary's vocabulary
    (`n_matched` / `n_review` / `n_unmatched_tx` / `n_refunds`), derived from
    the same `charge_states` map the run page counts (`_BUCKET_COUNTER`,
    where the reconciled bucket is called `n_reconciled`).

    Item 103: the stored summary and the months list counted the RAW outcome
    -- `len(outcome.matches)` and the transactions named in
    `judgment_required` / `ambiguous` -- while the page counts the effective
    one. A receipt a pending pick holds is dropped from the second charge
    that scored it, so the list reported a month as further along than its
    own workbench (live July 2026: list 8 in review / 72 unmatched, page 7 /
    73; both numbers are of the same month on the same day). One derivation,
    so the two screens cannot disagree, and a reviewer's later confirm or
    reject moves both.
    """
    effective = apply_decisions(outcome, transactions, receipts, decisions)
    return bucket_counts(charge_states(transactions, effective, decisions))


# The stored summary / months list name for each `charge_states` bucket. The
# page's own names are `_BUCKET_COUNTER`; only the reconciled bucket differs
# (`n_matched` here, `n_reconciled` there), because the two vocabularies
# predate item 103 and renaming a served field would break the SPA.
_STORED_BUCKET_COUNTER = {
    "reconciled": "n_matched",
    "review": "n_review",
    "refund": "n_refunds",
    "unmatched": "n_unmatched_tx",
}


def bucket_counts(states: dict[str, dict]) -> dict[str, int]:
    """`charge_states` counted into the stored summary's four names."""
    counts = dict.fromkeys(_STORED_BUCKET_COUNTER.values(), 0)
    for state in states.values():
        counts[_STORED_BUCKET_COUNTER[state["bucket"]]] += 1
    return counts


def settled_charge_cards(
    run: RunRow, charges: list, states: dict[str, dict]
) -> dict[str, str]:
    """Item 111: `{document_id: card key}` for every receipt of this month a
    charge of this month settles, keyed to that charge's card in the batch's
    registry snapshot.

    July 2026 asked Criss for a company and a person on 33 receipts while 19
    of them already settled a charge whose card names both. "Settles" is the
    reviewer's effective verdict (`charge_states`, the one map the workbench
    reads): a pending or confirmed pair in the reconciled bucket, so a
    rejected pair lends nothing and a pair still in review lends nothing
    either. The card is the charge's coverage identity (`_charge_card_identity`,
    the same string the matcher's scoping reads), and a card the registry
    cannot name lends nothing. A borrowed receipt (`receipt_sources`) is
    another month's expense, and its id can equal one of this month's own,
    so any held id in that map lends nothing here."""
    cards = _batch_cards(run.config)
    if not cards or not states:
        return {}
    borrowed = set((run.snapshot or {}).get(RECEIPT_SOURCES_KEY) or {})
    tx_by_id = {t.transaction_id: t for t in charges}
    out: dict[str, str] = {}
    for tx_id, state in states.items():
        doc = state.get("held_doc")
        tx = tx_by_id.get(tx_id)
        if state.get("bucket") != "reconciled" or not doc or tx is None:
            continue
        if doc in borrowed:
            continue
        key = _charge_card_identity(tx, cards).card_key
        if key:
            out[doc] = key
    return out


def export_settled_cards(run: RunRow, charge_decisions: dict | None) -> dict[str, str]:
    """`settled_charge_cards` for the CSV, the month report and (item 171)
    the sign-off card learner, from the same snapshot read and verdicts the
    Expenses payload uses (`decisions or {}`), so a document resolves a row
    exactly as the screen does. Empty for a month with no statement.

    The name is older than the third caller and now undersells it: every
    consumer OUTSIDE the grid's own payload reads its settled cards here,
    which is the point. A learner deriving "which charge settled this
    receipt" its own way would eventually teach a card the screen never
    showed."""
    charges, states = month_charge_states(run, charge_decisions or {})
    return settled_charge_cards(run, charges, states)


def settled_charge_amounts(
    run: RunRow, charges: list, states: dict[str, dict]
) -> dict[str, tuple[Decimal, str]]:
    """Item 98: `{document_id: (charge amount, charge currency)}` for every
    receipt of this month a charge of this month settles.

    The money-side twin of `settled_charge_cards`, sharing its rules to the
    letter on purpose: the same effective verdict (a reconciled pending or
    confirmed pair, so a rejected pair lends nothing and one still in review
    lends nothing either) and the same refusal to read a borrowed receipt,
    whose id can equal one of this month's own. Two derivations of "which
    charge settled this receipt" would eventually disagree, and then the
    company a row prints and the rate it converts at would be describing
    different charges.

    What it adds over the card twin is only the money: the amount and the
    currency the charge posted in, so a converter can refuse a charge that
    did not post in the base currency rather than convert through two rates.
    """
    if not states:
        return {}
    borrowed = set((run.snapshot or {}).get(RECEIPT_SOURCES_KEY) or {})
    tx_by_id = {t.transaction_id: t for t in charges}
    out: dict[str, tuple[Decimal, str]] = {}
    for tx_id, state in states.items():
        doc = state.get("held_doc")
        tx = tx_by_id.get(tx_id)
        if state.get("bucket") != "reconciled" or not doc or tx is None:
            continue
        if doc in borrowed or tx.amount is None:
            continue
        out[doc] = (tx.amount, (tx.transaction_currency or "").upper())
    return out


def export_settled_amounts(
    run: RunRow, charge_decisions: dict | None
) -> dict[str, tuple[Decimal, str]]:
    """`settled_charge_amounts` read the way `export_settled_cards` reads its
    own, so one pass over one set of verdicts feeds both what a document
    attributes a row to and what it converts the row at."""
    charges, states = month_charge_states(run, charge_decisions or {})
    return settled_charge_amounts(run, charges, states)


def usd_reference_rate(run: RunRow):
    """Item 98 rung 3: the rate for a receipt NO charge settled, taken from
    the matcher's own lookup bound to this month's frozen config.

    `_reference_rate_for` is the function the on-screen FX block already
    calls, so a document and the screen quote one rate for one purchase, and
    its precedence stands untouched: a rate typed in Settings is operator
    intent and wins, then this run's self-derived rates (a hosted month has
    none), then the ECB monthly average for the row's month. `build_match_cfg`
    assembles the config because it is the one place that knows how a
    `matching:` block becomes a `MatchingConfig`.

    Returns `(currency, date) -> (rate, source, ecb month)`, or None when the
    month froze no matching block at all. None is the honest outcome there:
    every foreign row then reports no figure and says so, rather than
    converting at a rate borrowed from somewhere this month never used.
    """
    import re

    from ..cli import build_match_cfg
    from ..matching.deterministic import _reference_rate_for

    _MONTH_SHAPE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")

    if not ((run.config or {}).get("matching") or {}):
        return None
    try:
        cfg = build_match_cfg(run.config or {}, Path(run.work_dir))
    except Exception:  # noqa: BLE001 - a document never fails over a rate
        # A month whose tuning file has gone missing still has to render.
        # The rows then say they have no figure, which is true and visible,
        # instead of the download 500ing on a currency question.
        return None
    if cfg is None:
        return None

    def lookup(currency: str, on: str):
        # The listing cell is a full ISO date, and `ecb_monthly_rate` accepts
        # a `date` or a "YYYY-MM" string, nothing else: handing it
        # "2026-09-05" fails its month-key match and the ECB rung silently
        # returns None, which made a document quote a different rate from the
        # screen for the same purchase. The matcher passes a `date`
        # (`on=tx.transaction_date`), so this does too.
        when: "date | str | None" = None
        text = (on or "").strip()
        if text:
            try:
                when = date.fromisoformat(text)
            except ValueError:
                when = text[:7] if _MONTH_SHAPE.fullmatch(text[:7]) else None
        hit = _reference_rate_for(cfg, currency, BASE_CURRENCY, None, on=when)
        if hit is None:
            return None
        rate, source, _n = hit
        month = ""
        if source == "ecb_month":
            ecb = cfg.ecb_monthly_rate(currency, BASE_CURRENCY, when)
            month = ecb[1] if ecb else ""
        elif source == "opentickers_day":
            daily = cfg.daily_rate(currency, BASE_CURRENCY, when)
            month = daily[1] if daily else ""
        return rate, source, month

    return lookup


def _identity_from_observed(observed: str | None, cards: dict) -> _CardIdentity:
    """The coverage identity of one card-bearing string, or `_NO_CARD` when
    it names no card.

    Three outcomes, and the middle one is the one that matters here:

    * the registry recognizes it -> that card, so the Chase cycle marker
      "2838" and the plastic's "1672" are ONE row rather than two.
      Resolution goes through `cards.resolve_card`, the same function the
      per-receipt card chain uses, which means the registry's aliases count
      and an AMBIGUOUS string resolves to nothing (the house ruling:
      ambiguity surfaces instead of guessing).
    * digits the registry has never heard of -> a row of their own, keyed by
      the normalized tokens and labelled with what the statement printed.
      Not folded into anything: cards 3645 and 0340 are real charges on real
      plastic the registry is simply missing (backlog item 26), and hiding
      them in an "other" bucket would bury the gap instead of showing it.
    * nothing card-like at all -> the no-card identity. "Unknown card" is
      never "some card we already listed"; the same rule `_tx_card_keys`
      states, and generic tender words ("Visa", "cash") land here because
      `resolve_card` refuses to let them identify anything.
    """
    from ..cards import resolve_card
    from ..matching.deterministic import _card_keys

    text = (observed or "").strip()
    if not text:
        return _NO_CARD
    if cards:
        card = resolve_card(text, cards, on_ambiguity="none")
        if card is not None:
            return _CardIdentity(
                card.key, card.key, card.display_label, tuple(card.digits)
            )
    tokens = tuple(sorted(_card_keys(text)))
    if not tokens:
        return _NO_CARD
    return _CardIdentity(
        _UNKNOWN_KEY_PREFIX + "-".join(tokens), "", text, tokens
    )


def _charge_card_identity(tx, cards: dict) -> _CardIdentity:
    """The coverage identity of one charge.

    The observed string is picked exactly the way the matcher's
    `_tx_card_keys` picks it: the per-row card column when it carries
    digits, the account id otherwise. Two derivations of "which string names
    this charge's card" would be two answers, and the matcher's is the one
    the scoping already uses.
    """
    from ..matching.deterministic import _card_keys

    observed = tx.card_last4 if _card_keys(tx.card_last4) else tx.account_id
    return _identity_from_observed(observed, cards)


def stamp_charge_entities(transactions: list, cards: dict) -> list:
    """Item 59 (owner ruling 2026-09-11): a charge's legal entity comes from
    ITS card, not from the card the upload was filed under.

    The parsers stamp the upload's entity on every row, which on a Chase
    multi-card workbook filed as card-2838 put all 111 August charges under
    Corporate Services while 77 of them sat on cards 3645 and 3876. Here,
    for every row that PRINTED a card (the per-row `card_last4` the WS3
    column map fills), the entity is the registry card's entity, and a
    card the registry cannot name, or names without an entity, leaves the
    row BLANK: a visible gap beats a wrong posting, and the coverage panel
    already lists that card as "not in your card list". A row with no card
    column keeps what the upload said: the account id IS the card there,
    and `resolve_entity` already read the registry for it.

    Resolution is `resolve_card` on the same observed string the matcher's
    scoping and the coverage identity use, ambiguity to nothing, so the row,
    the coverage row and the card scoping cannot disagree about which
    plastic a charge is on. An empty registry stamps nothing: a batch that
    predates the card registry keeps the upload's entity on every row.

    Ids are content-derived without the entity, so re-stamping on every
    re-match (this runs inside `rematch_month`, which every attach, re-read,
    card assignment and master-data refresh passes through) never moves a
    charge or its decisions.
    """
    from ..cards import resolve_card
    from ..matching.deterministic import _card_keys

    if not cards or not transactions:
        return transactions
    out: list = []
    for tx in transactions:
        if not _card_keys(tx.card_last4):
            out.append(tx)
            continue
        card = resolve_card(tx.card_last4, cards, on_ambiguity="none")
        entity = (card.entity or "") if card is not None else ""
        out.append(
            replace(tx, legal_entity_id=entity)
            if entity != (tx.legal_entity_id or "") else tx
        )
    return out


def charge_entity_source(tx, cards: dict) -> str:
    """Item 73: where a charge's `legal_entity_id` came from, in the grid's
    `entity_source` vocabulary.

    * ``card``  - the row printed a card and the registry named its entity
      (`stamp_charge_entities` above, same condition).
    * ``batch`` - the upload's entity, which a row with no card column, or a
      batch with no registry, keeps. Lent, not established by the row.
    * ``none``  - no entity at all.

    Reads the batch's CURRENT registry snapshot, the one every re-match
    stamps with, so it describes the stamp the month's last re-match made.
    """
    from ..matching.deterministic import _card_keys

    if not (tx.legal_entity_id or "").strip():
        return "none"
    if cards and _card_keys(tx.card_last4):
        return "card"
    return "batch"


def _statement_card_identities(
    entry: dict,
    printed: dict,
    charge_identity: dict[str, _CardIdentity],
    cards: dict,
) -> list[_CardIdentity]:
    """The coverage rows one statement upload covers.

    Two joins, unioned, because each alone is blind somewhere real:

    * the operator's own `card_key`, a provisioned preset resolved through
      the registry so a preset that merged into a settings card lands on the
      composed key. An explicit assertion about what this file is for, so it
      counts even when the file then printed nothing on that card: "loaded a
      statement for this card, got no charges out of it" is worth seeing.
      Blind when the upload named no preset, which is every upload made
      through the plain form.
    * the charges the file actually printed, via `statement_origins`
      (note item T3), which records every charge an upload printed, PDF and
      workbook alike. It used to read `statement_anchors` instead, and the
      anchors are the WRITEBACK's map: empty by construction for a PDF,
      whose charges have no tabular row. That emptiness read as "this file
      printed nothing" and parked every PDF statement in the no-card row.
      `_printed_by_upload` keeps the anchors as the fallback for a month
      recorded before the origins existed, which is the same rule
      `origins_from_snapshot` follows, so a workbook of that vintage still
      resolves and a PDF of that vintage still cannot.

    Two LAST resorts, reached only when both joins came back empty, in this
    order:

    * the digit runs the FILE NAME carries, kept only where a run resolves
      to a card the registry DEFINES. `20260804-statements-1176-.pdf` names
      one such card and one date that is no card at all, and an unknown run
      never mints a `digits:` row here: a date is not a card, and inventing
      a coverage row out of one would be worse than the no-card row this
      replaces. Two different defined cards in one name is ambiguity, which
      stays silent per the house ruling.
    * `account_id`, and deliberately not a voice beside the two joins. It
      names an ACCOUNT, not a card: on the real corpserv export every row
      carries `chase-2838-family` while the rows themselves span 2838 /
      3645 / 3876 / 0340, so treating it as a card identity would invent a
      coverage row for a card that does not exist and park the file in it.
      It goes after the file name because a run that resolves to a defined
      card names a card, while an account id can name a family of four.
      Where it IS the card (the Chase statement PDF, whose account id is
      the cycle marker, and every single-card CSV with no Card column) it
      is still the only thing that can answer.

    Nothing here picks a winner between the two joins: this surface reports
    coverage, it does not adjudicate what an operator meant.
    """
    out: dict[str, _CardIdentity] = {}
    identity = _identity_from_observed(entry.get("card_key"), cards)
    if identity.key:
        out[identity.key] = identity
    for tx_id in (printed.get(entry.get("file")) or {}):
        identity = charge_identity.get(tx_id)
        if identity is not None:
            out[identity.key] = identity
    if not out:
        for identity in _identities_from_file_name(entry, cards):
            out[identity.key] = identity
    if not out:
        identity = _identity_from_observed(entry.get("account_id"), cards)
        if identity.key:
            out[identity.key] = identity
    return list(out.values()) or [_NO_CARD]


def _printed_by_upload(run: RunRow) -> dict[str, dict]:
    """`{statement file: {transaction_id: where}}` for every upload the
    month holds: which charges each file printed.

    `statement_origins` (note item T3) is the record; `statement_anchors`
    is the fallback for a month written before it existed, where a workbook
    still has a row per charge it printed and a PDF has nothing. A file
    whose origins entry is recorded and EMPTY keeps that emptiness rather
    than falling back, because "this upload printed no charge we kept" is
    an answer and the anchors would only repeat it.
    """
    snapshot = run.snapshot or {}
    origins = snapshot.get(STATEMENT_ORIGINS_KEY) or {}
    anchors = snapshot.get(STATEMENT_ANCHORS_KEY) or {}
    out: dict[str, dict] = {}
    for file in set(origins) | set(anchors):
        found = origins.get(file)
        if found is None:
            found = anchors.get(file) or {}
        out[str(file)] = found if isinstance(found, dict) else {}
    return out


def _identities_from_file_name(entry: dict, cards: dict) -> list[_CardIdentity]:
    """The one DEFINED card a statement's own file name names, or nothing.

    Read from the stored name and the name Criss sent, unioned, because a
    collision suffix or a per-card export sharing the bank's filename makes
    the two differ. Only a digit run that resolves through the registry
    counts: `20260804-statements-1176-.pdf` yields card 1176 and drops the
    cycle date, and a name that resolves to nothing stays silent rather
    than minting a card out of a number. Two different defined cards in one
    name is ambiguity and also stays silent.
    """
    seen: dict[str, _CardIdentity] = {}
    for name in (entry.get("file"), entry.get("upload_name")):
        for run_of_digits in _printed_digits(Path(str(name or "")).stem):
            identity = _identity_from_observed(run_of_digits, cards)
            if identity.card_key:
                seen[identity.key] = identity
    return list(seen.values()) if len(seen) == 1 else []


def _printed_digits(observed: str) -> list[str]:
    """The card-like digit runs exactly as the statement printed them,
    leading zeros intact. `_card_keys` strips those to make one match key
    out of Chase's "0340" and Zoho's "340"; this is the other direction,
    for a screen a person reads."""
    import re as _re

    return _re.findall(r"\d{3,}", observed or "")


def cards_seen_but_undefined(runs: list, cards: dict) -> list[dict]:
    """Cards the tool has actually MET, that the registry does not know.

    `/api/cards` composed the registry and the shipped presets, so the
    settings screen listed the cards somebody had already defined and
    nothing else. On the live April month that meant 2838 and four cards
    with no charges on screen, while 0340, 3645 and 4700 carried 53 of the
    94 charges and were nowhere on the page where a card gets defined. The
    reviewer's move (define the card these charges are on) was the one the
    screen could not start.

    So the same identity derivation the coverage panel uses runs across the
    months and reports what it found that the registry cannot name. The
    identity comes from `_charge_card_identity`, not a second reading of
    `account_id`, so a card listed here is the same card the coverage row
    is about.

    One entry per unknown identity, newest month first inside each:

    * ``suggested_key`` - what to define it as, taken from what the
      statement PRINTED rather than from the match key. `_card_keys`
      strips leading zeros on purpose, so that Chase's "0340" and the
      Zoho payment mode's "340" land on one key; that is right for
      matching and wrong for a human, who would be handed "340" for a
      card they know as "0340" and could define it under a name that
      never appears on their statement. Never a `digits:`-namespaced
      internal key either.
    * ``observed`` - the string the statement actually printed, which is
      what makes it findable when the digits are not obvious
    * ``digits``, ``n_charges``, ``months`` - enough to decide whether it
      is worth defining before opening the definition form

    Runs whose snapshot cannot be read are skipped rather than failing the
    settings screen: an unreadable month is a reason to show fewer cards,
    never a reason to show none.
    """
    seen: dict[str, dict] = {}
    for run in runs:
        snapshot = getattr(run, "snapshot", None) or {}
        if not snapshot.get("transactions"):
            continue
        try:
            transactions, _receipts, _outcome, _cfg = snapshot_from_dict(snapshot)
        except Exception:
            continue
        label = getattr(run, "label", "") or getattr(run, "run_id", "")
        for tx in transactions:
            ident = _charge_card_identity(tx, cards)
            if ident.card_key or not ident.key:
                continue  # the registry knows it, or the charge names no card
            printed = _printed_digits(ident.label)
            entry = seen.setdefault(ident.key, {
                "key": ident.key,
                "suggested_key": printed[0] if printed else ident.label,
                "observed": ident.label,
                "digits": printed or list(ident.digits),
                "n_charges": 0,
                "months": [],
            })
            entry["n_charges"] += 1
            if label and label not in entry["months"]:
                entry["months"].append(label)

    return sorted(
        seen.values(), key=lambda e: (-e["n_charges"], e["suggested_key"])
    )


def month_coverage(
    run: RunRow, transactions: list, states: dict[str, dict]
) -> tuple[list[dict], dict[str, str]]:
    """`(coverage rows, {transaction_id: coverage key})` for a month.

    `transactions` and `states` must come from ONE read of the snapshot: the
    roll-up looks every charge's state up unconditionally, so a charge whose
    state is missing raises rather than being counted under a guessed
    bucket. Both callers hand over a matched pair, which is what makes that
    lookup total.

    One row per card the month knows about: every card its charges name,
    every card an upload covered, and every card in the batch's own registry
    snapshot. That last group is the point of the surface rather than
    padding, because "which cards have I not loaded yet" is only answerable
    from a list that includes the ones with nothing in them.

    Empty for a month with no charges and no uploads. That keeps absence
    meaning "nothing loaded" rather than "this backend does not report
    coverage", and stops a receipt-only month from opening with a column of
    registry cards it has no business asking about yet.

    The registry is the batch's SNAPSHOT (`run.config["expense"]["cards"]`),
    the same one per-receipt card resolution reads, so the two cannot
    disagree and a settings edit reaches an existing month only through the
    explicit refresh-master-data pass. A run with no snapshot (a plain
    statement run, or a batch older than the card registry) still works:
    every charge falls to its digit tokens, which on the real January month
    is exactly the three rows 2838 / 3645 / 0340.
    """
    statements = month_statements(run)
    if not transactions and not statements:
        return [], {}

    cards = _batch_cards(run.config)
    printed = _printed_by_upload(run)
    entries: dict[str, dict] = {}

    def row(identity: _CardIdentity) -> dict:
        entry = entries.get(identity.key)
        if entry is None:
            entry = entries[identity.key] = {
                "key": identity.key,
                # The registry key, or "" when the registry does not know
                # this card. Kept apart from `key` so a consumer tells a
                # named card from a bare digit token without parsing.
                "card_key": identity.card_key,
                "label": identity.label or NO_CARD_LABEL,
                "entity": "",
                "digits": list(identity.digits),
                "known": bool(identity.card_key),
                "statements": [],
                # Note item T2: the `statement_id` of each entry in
                # `statements` that carries one. Not positional with
                # `statements`: an upload recorded before ids existed is
                # named there and has nothing to add here.
                "statement_ids": [],
                "period_start": None,
                "period_end": None,
                "n_transactions": 0,
                "n_reconciled": 0,
                "n_review": 0,
                "n_unmatched_tx": 0,
                "n_refunds": 0,
                "unreconciled_by_ccy": {},
            }
        return entry

    # 1. the registry's own cards, so the ones with nothing loaded are
    #    visible rather than merely absent.
    for card in cards.values():
        if not card.active:
            continue
        entry = row(_CardIdentity(
            card.key, card.key, card.display_label, tuple(card.digits)
        ))
        entry["entity"] = card.entity

    # 2. the charges, which is where every count comes from.
    charge_identity: dict[str, _CardIdentity] = {}
    unreconciled: dict[str, dict[str, Decimal]] = {}
    for tx in transactions:
        identity = _charge_card_identity(tx, cards)
        charge_identity[tx.transaction_id] = identity
        entry = row(identity)
        state = states[tx.transaction_id]
        bucket = state["bucket"]
        entry["n_transactions"] += 1
        entry[_BUCKET_COUNTER[bucket]] += 1
        if tx.transaction_date:
            iso = tx.transaction_date.isoformat()
            if entry["period_start"] is None or iso < entry["period_start"]:
                entry["period_start"] = iso
            if entry["period_end"] is None or iso > entry["period_end"]:
                entry["period_end"] = iso
        # The summary's own rule, so a card's unreconciled money and the
        # month's total are the same arithmetic: reconciled and refunded
        # charges are settled, and a posted charge is settled by definition.
        if bucket not in ("reconciled", "refund") and not state["is_posted"]:
            per_ccy = unreconciled.setdefault(identity.key, {})
            per_ccy[tx.transaction_currency] = (
                per_ccy.get(tx.transaction_currency, Decimal("0")) + abs(tx.amount)
            )

    # 3. the uploads, which can cover a card whose charges all arrived under
    #    a different identity, or whose rows the month already held.
    for stmt in statements:
        name = stmt.get("file")
        if not name:
            continue
        for identity in _statement_card_identities(
            stmt, printed, charge_identity, cards
        ):
            target = row(identity)
            if name not in target["statements"]:
                target["statements"].append(name)
            sid = str(stmt.get("statement_id") or "")
            if sid and sid not in target["statement_ids"]:
                target["statement_ids"].append(sid)

    for key, per_ccy in unreconciled.items():
        entries[key]["unreconciled_by_ccy"] = {
            ccy: f"{amt:,.2f}" for ccy, amt in sorted(per_ccy.items())
        }

    rows = sorted(
        entries.values(),
        key=lambda e: (
            -e["n_transactions"], -len(e["statements"]), e["label"].lower(), e["key"],
        ),
    )
    return rows, {tx_id: i.key for tx_id, i in charge_identity.items()}


def _batch_llm_client(cfg: dict):
    """(client, tracker, source) for batch-lifecycle OCR, mirroring the
    folder-ingest sourcing: the run's own llm block first, the deployment
    default when the run had none and a key exists, else no client (bare
    filename-only receipts, honestly flagged)."""
    from ..cli import _build_llm_client

    llm_client, tracker, source = None, None, "none"
    try:
        llm_client, tracker = _build_llm_client(cfg or {})
        if llm_client is not None:
            source = "run"
    except ConfigError:
        llm_client = None
    if llm_client is None and _default_llm_on() and os.environ.get("OPENAI_API_KEY"):
        llm_client, tracker = _build_llm_client(
            {"llm": {"provider": "openai", "model": "gpt-4o-mini", "vision_model": VISION_MODEL}}
        )
        source = "env-default"
    return llm_client, tracker, source


# ── Set-aside strip (backlog item 1) ────────────────────────────────────
# The quarantine's reviewer-facing half: every excluded file is a snapshot
# `set_aside` entry {file, display, reason, at, receipt?, restored?} that
# the grid renders as a visible strip, with a one-click restore. The entry
# keeps the excluded receipt's full extraction so a restore is a categorize
# pass, never a second vision call.


def _display_name(stored: str) -> str:
    """The upload's own filename, without the `NNNN__` spool prefix the
    receipts dir adds for ordering."""
    return re.sub(r"^\d{4}__", "", stored)


def receipt_image_file(
    work_dir: Path, document_id: str, *, expense_mode: bool
) -> Path | None:
    """The file `GET /api/runs/{id}/receipts/{doc}/image` would serve for
    this document, or None when that route would 404.

    One implementation of "can this receipt be shown", because the answer is
    the ENDPOINT's and nothing else can give it. It was previously guessed
    twice: the batch payload resolved it from disk (correct), and the run
    payload from the SHAPE of the document id -- `manual:` or `folder:` or a
    vision-mapped page. Every receipt that arrives by mail or through the
    receipts drop has a plain `NNNN__name.pdf` id and matches none of those,
    so the run payload answered `false` for all 17 unmatched receipts of
    Criss's live August month while the endpoint served every one of them
    200 (item 52, measured 2026-09-15).

    Ordered and gated exactly as the endpoint is: the `manual:` / `folder:`
    globs apply to every run, and the receipts-dir branch only to a
    receipt-first batch. The resolved path is confined to the receipts dir
    the same way, so a crafted id cannot address a file outside it.
    """
    hit = _attached_receipt_file(work_dir, document_id)
    if hit is not None:
        return hit
    if not expense_mode:
        return None
    exp_dir = (work_dir / "receipts").resolve()
    try:
        target = (exp_dir / document_id).resolve()
    except (OSError, ValueError):
        return None
    if exp_dir in target.parents and target.is_file():
        return target
    return None


def _attached_receipt_file(work_dir: Path, document_id: str) -> Path | None:
    """The on-disk file behind a workbench-attached `manual:`/`folder:`
    receipt, resolved with the SAME glob the image endpoint serves from
    (manual-receipts/{tx}__*, folder-receipts/{digest}__*). None for ids
    with no attached file — a typed-in manual expense."""
    for prefix, folder in (("manual:", "manual-receipts"),
                           ("folder:", "folder-receipts")):
        if not document_id.startswith(prefix):
            continue
        key = re.sub(r"[^A-Za-z0-9._-]", "_", document_id[len(prefix):])
        d = work_dir / folder
        hits = sorted(d.glob(f"{key}__*")) if d.is_dir() else []
        return hits[0] if hits else None
    return None


def _set_aside_entry(r: Receipt, now_iso: str) -> dict:
    return {
        "file": r.document_id,
        "display": r.receipt_name or _display_name(r.document_id),
        "reason": r.document_type,
        "at": now_iso,
        "receipt": receipt_to_dict(r),
    }


def _derive_legacy_set_aside(parse_errors: list) -> list[dict]:
    """Set-aside entries for a run recorded before the snapshot carried
    them (e.g. the May batch): recover file + reason from the quarantine's
    own warning messages. No stored receipt — a restore re-extracts from
    the file on disk (extraction-cache hit when the reading is cached)."""
    entries: list[dict] = []
    for issue in parse_errors:
        file, _line, msg = issue[0], issue[1], issue[2]
        if "not a purchase receipt" not in msg or "excluded" not in msg:
            continue
        reason = next(
            (code for code, label in NON_RECEIPT_LABELS.items()
             if f"looks like {label}" in msg),
            "other",
        )
        entries.append({
            "file": file,
            "display": _display_name(file),
            "reason": reason,
            "at": None,
        })
    return entries


def set_aside_entries(snapshot: dict) -> list[dict]:
    """The canonical set-aside list for a batch: the snapshot's own record,
    falling back to legacy derivation from the quarantine parse issues."""
    stored = snapshot.get("set_aside")
    if stored is not None:
        return [dict(e) for e in stored]
    return _derive_legacy_set_aside(snapshot.get("parse_errors", []))


def _set_aside_document_id(entry: dict) -> dict:
    """`{"document_id": ...}` for a set-aside entry that records the
    receipt it set aside, `{}` for a legacy one that does not."""
    stored = entry.get("receipt")
    document_id = (stored or {}).get("document_id") if isinstance(
        stored, dict) else None
    return {"document_id": document_id} if document_id else {}


def set_aside_view(snapshot: dict, work_dir: Path | None = None) -> list[dict]:
    """The SPA-facing shape: internal receipt dict withheld. `reason` is
    the machine code ("statement" | "report_summary" | "other") the SPA
    keys its own wording (EN/PT) on — the English reason_label was dead
    weight the prompt already forbade showing (language-contract round).

    Note #52: `receipt_image_available` says whether the receipt viewer can
    open the file (`GET /api/runs/{id}/receipts/{file}/image`, resolved by
    `receipt_image_file`, the endpoint's own rule), so the reviewer can look
    at a page before deciding it is a receipt. Present when `work_dir` is
    given, which the expense batch payload always does."""
    out = []
    for e in set_aside_entries(snapshot):
        row = {
            "file": e["file"],
            "display": e.get("display") or _display_name(e["file"]),
            "reason": e.get("reason") or "other",
            "restored": bool(e.get("restored")),
            "at": e.get("at"),
            # Note item T3/T1: the receipt this entry set aside, under
            # the name every other surface calls it. `file` has always
            # HELD the document id (`_set_aside_entry` writes
            # `r.document_id` into it) but says `file`, so a reader
            # joining this strip to a receipt had to know that. Read
            # from the stored receipt rather than from `file`, because
            # that is the authoritative copy: a legacy entry
            # (`_derive_legacy_set_aside`, recovered from the
            # quarantine's parse issues) carries no receipt and its
            # `file` is a parse-issue file name that is NOT provably a
            # document id, so it gets no key. Parallel and absent,
            # never null; `file` keeps its name, its value and its
            # place in the restore route.
            **_set_aside_document_id(e),
        }
        if work_dir is not None:
            row["receipt_image_available"] = (
                receipt_image_file(work_dir, e["file"], expense_mode=True)
                is not None
            )
        out.append(row)
    return out


def restore_set_aside_file(
    store: RunStore,
    run: RunRow,
    file: str,
    now_iso: str,
    *,
    learning_db_path: Path | None = None,
) -> dict:
    """The reviewer's "this really is a receipt" override: move one
    set-aside file into the expense pool. Uses the entry's stored
    extraction when present (no vision call); a legacy entry re-extracts
    from the file on disk. The receipt is re-marked `document_type
    "receipt"` — the human's classification outranks the model's — then
    runs the same memory + registry + categorize pass a mid-month add
    gets. The set-aside entry stays, flagged `restored`, so the strip
    keeps showing what happened.

    Serialized under the batch-mutation lock with a fresh re-read (R3
    adversarial review A1: an unlocked restore working from a stale row
    clobbered a concurrent mid-month add's receipt out of the pool)."""
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        # No statement refusal since 2b-2: a restored page is a receipt
        # joining the pool, the same class as an arrival.
        out = _restore_set_aside_locked(
            store, run, file, now_iso, learning_db_path=learning_db_path
        )
    rematch = rematch_after_change(
        store, run.run_id, learning_db_path=learning_db_path,
        trigger="set_aside",
    )
    if rematch is not None:
        out["rematch"] = rematch
    return out


def _restore_set_aside_locked(
    store: RunStore,
    run: RunRow,
    file: str,
    now_iso: str,
    *,
    learning_db_path: Path | None = None,
) -> dict:
    from ..categorize import categorize_receipts_with_registry
    from ..cli import _resolve_categorizer_chart
    from ..ingest.receipts_folder import parse_receipt_file

    snapshot = dict(run.snapshot)
    entries = set_aside_entries(snapshot)
    entry = next((e for e in entries if e["file"] == file), None)
    if entry is None:
        raise RunInputError(
            f"{file} is not in this batch's set-aside list.",
            code="set_aside_file_not_found",
            file=file,
        )
    if entry.get("restored"):
        raise RunInputError(
            f"{file} was already restored.",
            code="set_aside_already_restored",
            file=file,
        )

    _, receipts, outcome, _parse_errors = snapshot_from_dict(snapshot)
    if any(r.document_id == file for r in receipts):
        raise RunInputError(
            f"{file} is already an expense in this batch.",
            code="set_aside_already_expense",
            file=file,
        )

    cfg = run.config or {}
    if entry.get("receipt"):
        restored = receipt_from_dict(entry["receipt"])
    else:
        # Legacy entry (recorded before the snapshot kept the extraction):
        # re-extract from the stored file. Cheap when the reading is in the
        # extraction cache; honest bare receipt when no LLM is available.
        source = Path(run.work_dir) / "receipts" / file
        if not source.is_file():
            raise RunInputError(
                f"{file} is no longer on disk; re-upload it instead.",
                code="file_missing_on_disk",
                file=file,
            )
        llm_client, _tracker, _src = _batch_llm_client(cfg)
        restored = None
        if llm_client is not None:
            try:
                restored = parse_receipt_file(
                    source,
                    legal_entity_id=(
                        (cfg.get("expense") or {}).get("legal_entity_id", "")
                    ),
                    client=llm_client,
                    default_currency=(
                        (cfg.get("receipts") or {}).get("default_currency")
                    ),
                )
            except Exception:  # noqa: BLE001 - extraction is best-effort
                restored = None
        if restored is None:
            restored = Receipt(
                document_id=file,
                legal_entity_id=(
                    (cfg.get("expense") or {}).get("legal_entity_id", "")
                ),
                detected_date=None,
                detected_total=None,
                detected_currency=None,
                detected_vendor=_display_name(file),
                receipt_name=_display_name(file),
            )

    note = "restored from set-aside by reviewer"
    restored = replace(
        restored,
        document_type="receipt",
        data_quality_note=(
            f"{restored.data_quality_note}; {note}"
            if restored.data_quality_note else note
        ),
    )

    # The same enrichment a mid-month add gets: learned memory, card
    # entity stamping (Cards R3 — the paying card resolves the entity
    # before categorization, so learned lookups see it), merchant
    # registry, categorization. The quarantine skipped all of it.
    from ..cards import stamp_card_entities as _stamp

    registry = MerchantRegistry.from_settings(store.get_settings())
    memory = ExpenseMemory.from_db_path(learning_db_path)
    batch = memory.apply([restored])
    # Item 173, second half: same card gate as the full ingest and the add
    # job, and before the entity stamping for the same reason.
    batch = drop_unvouched_remembered_cards(batch, registry)
    batch = _stamp(batch, _batch_cards(cfg), _batch_card_hints(cfg))
    learned = (
        MerchantCategoryLookup.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    llm_client, _tracker, _src = _batch_llm_client(cfg)
    try:
        _, account_labels, _scope = _resolve_categorizer_chart(
            cfg, Path(run.work_dir), None, {}
        )
    except Exception:  # noqa: BLE001 - labels degrade, restore never breaks
        account_labels = None
    batch, _ = categorize_receipts_with_registry(
        batch,
        registry=registry,
        client=llm_client,
        chart_of_accounts=account_labels,
        learned=learned,
        entity_orgs=cfg.get(GL_ENTITY_ORGS_KEY),
    )
    restored = batch[0]

    pool = receipts + [restored]
    outcome.unmatched_receipts.append(restored.document_id)
    entry["restored"] = True
    entry["restored_at"] = now_iso
    n_categorized, n_uncategorized = categorized_counts(pool)
    snapshot["receipts"] = [receipt_to_dict(r) for r in pool]
    snapshot["outcome"] = outcome_to_dict(outcome)
    snapshot["set_aside"] = entries
    store.update_run_snapshot(run.run_id, snapshot)
    n_set_aside = sum(1 for e in entries if not e.get("restored"))
    store.update_run_summary(run.run_id, {
        **run.summary,
        "n_expenses": len(pool),
        "n_receipts": len(pool),
        "n_categorized": n_categorized,
        "n_uncategorized": n_uncategorized,
        "n_set_aside": n_set_aside,
    })
    return {
        "ok": True,
        "file": file,
        "n_expenses": len(pool),
        "n_set_aside": n_set_aside,
    }


# One writer at a time on a batch snapshot: mail-intake threads, the SPA
# add job, and replay-held all funnel through add_receipts_to_expense_batch,
# whose read-modify-write on the snapshot is only safe serialized.
#
# Two constraints ride on this being an in-process lock. It serializes writers
# WITHIN one process only, so scaling the app past a single machine breaks the
# model outright (today the Fly volume pins us to one); and an OCR ingest holds
# it for minutes, so no `async def` handler may block on it — that parks the
# event loop and takes /healthz down with everything else. Handlers either run
# sync (delete_run) or hand the locked span to run_in_threadpool
# (set-aside/restore, cards). See tests/test_web_batch_lock_threadpool.py.
_BATCH_ADD_LOCK = threading.Lock()


def batch_write_lock() -> threading.Lock:
    """The batch-snapshot writer lock, for callers outside this module
    whose mutation must not interleave with an in-flight RMW (the
    delete-month cascade: rows must not vanish under a writer, and a
    writer entering after the delete re-fetches None and refuses)."""
    return _BATCH_ADD_LOCK


def recategorize_after_entity_change(
    db_path, learning_db_path, run_id: str, document_id: str,
) -> dict | None:
    """Re-run the GL engine for ONE receipt after its company was set.

    Owner decision 2026-09-24: a receipt that arrived with no company halts
    with `entity_missing`, and assigning the company must categorize it
    against THAT company's leaves, or every such receipt becomes a manual
    pick. Also right when the company CHANGES: a leaf chosen for one entity
    need not be postable in another.

    Only a batch on the GL engine (its config carries `gl_entity_orgs`) is
    touched; a bucket-era batch returns None and keeps its vocabulary. The
    reviewer's own category overrides are separate rows and are never
    touched here: this rewrites the TOOL's answer only, in both the current
    receipts and the extraction baseline (the views and every re-match read
    the baseline). The model call runs outside the batch lock; the write
    re-reads the row inside it, like the add job. Returns what changed, or
    None when there was nothing to do.
    """
    from ..categorize import categorize_receipts_with_registry

    with RunStore(db_path) as store:
        run = store.get_run(run_id)
        if run is None:
            return None
        cfg = run.config or {}
        entity_orgs = cfg.get(GL_ENTITY_ORGS_KEY)
        if entity_orgs is None:
            return None
        base = next(
            (r for r in baseline_receipts(run) if r.document_id == document_id),
            None,
        )
        if base is None:
            return None  # a manual add or a borrowed receipt: nothing extracted
        default_entity = (cfg.get("expense") or {}).get("legal_entity_id", "")
        entity = (
            (store.get_expense_field_overrides(run_id).get(document_id) or {})
            .get("legal_entity")
            or base.legal_entity_id
            or default_entity
        )
        registry = MerchantRegistry.from_settings(store.get_settings())
    learned = (
        MerchantCategoryLookup.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    llm_client, _tracker, _src = _batch_llm_client(cfg)
    (new,), _ = categorize_receipts_with_registry(
        [replace(base, legal_entity_id=entity)],
        registry=registry,
        client=llm_client,
        learned=learned,
        entity_orgs=entity_orgs,
    )

    def _swap(d: dict) -> dict:
        old = receipt_from_dict(d)
        if len(old.line_items) == len(new.line_items):
            items = tuple(
                replace(li, categorization=n.categorization)
                for li, n in zip(old.line_items, new.line_items)
            )
        else:
            items = new.line_items
        return receipt_to_dict(replace(old, line_items=items))

    with _BATCH_ADD_LOCK:
        with RunStore(db_path) as store:
            fresh = store.get_run(run_id)
            if fresh is None:
                return None
            snapshot = dict(fresh.snapshot or {})
            touched = False
            for key in ("receipts", EXTRACTED_RECEIPTS_KEY):
                rows = snapshot.get(key)
                if not isinstance(rows, list):
                    continue
                out = []
                for d in rows:
                    if isinstance(d, dict) and d.get("document_id") == document_id:
                        d = _swap(d)
                        touched = True
                    out.append(d)
                snapshot[key] = out
            if not touched:
                return None
            store.update_run_snapshot(run_id, snapshot)
    refusals = sorted({
        li.categorization.refusal
        for li in new.line_items
        if li.categorization is not None and li.categorization.refusal
    })
    return {"document_id": document_id, "entity": entity, "refusals": refusals}


def add_receipts_to_expense_batch(
    store: RunStore,
    run: RunRow,
    staging_dir: str | Path,
    now_iso: str,
    *,
    learning_db_path: Path | None = None,
    on_stage=None,
    provenance_by_digest: dict[str, dict] | None = None,
    text_by_digest: dict[str, str] | None = None,
) -> dict:
    """Add receipts to an EXISTING expense batch (they arrive gradually all
    month). Only the new files are OCR'd (never a re-read of the pool),
    memory auto-fill + categorization run on them exactly as at batch
    creation, and they append to the snapshot's receipt pool. Identical
    bytes (within this upload or vs an already-stored file) are skipped.
    Refused once a statement is attached — the pool is then the
    reconciliation's provenance and must not shift under it.

    `text_by_digest` (sha1[:16] -> the document's own text) supplies text for
    a file the extractor cannot read one from. A mail body renders to an
    IMAGE pdf, so `ocr_text` would otherwise be the model's notes rather than
    the body; the correspondence rung needs the real words. Only ever applied
    when the extraction produced no text of its own."""

    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass

    # Serialize the whole read-modify-write span: mail intake, the SPA add
    # job, and replay-held can all land concurrently on one batch, and an
    # unserialized pair loses the first writer's receipts (last-write-wins
    # on the snapshot; adversarial review 2026-08-20). One writer at a time
    # is the intended operating mode — volume is a shared mailbox's trickle.
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            # The month was deleted while this mail/upload waited on the
            # lock. Refuse honestly (the ingest job goes held_failed and
            # the mail stays replayable) instead of writing a snapshot
            # UPDATE that matches zero rows and reporting the receipts
            # as ingested into a batch that no longer exists.
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        # Note #54 (owner, 2026-09-16) / audit item 108: a receipt arriving
        # into a month that already exists goes through what the month's
        # other receipts went through, and that includes the CURRENT card
        # list. The month kept the copy of the registry it was created with,
        # so September, opened by mail before the cards had people and
        # companies, resolved every arrival against that copy: 40 rows with
        # no person while Settings knew all nine cards. The arrival now
        # refreshes the copy first, through the same audited pass as the
        # manual button (overrides and the month's own assignments survive
        # it), so the new receipt and the rows already there both read the
        # registry as it is today.
        refresh = _refresh_batch_master_data_locked(
            store, run, now_iso=now_iso, operator="auto: receipt arrival"
        )
        if refresh.get("changes"):
            run = store.get_run(run.run_id) or run
        # Item 113: a re-match this month still owes from an earlier change
        # (it raised, or a restart cut it off) is paid by THIS arrival too,
        # even when every file turns out to be a duplicate.
        owed_before = rematch_pending(run) is not None
        result = _add_receipts_locked(
            store, run, staging_dir, now_iso,
            learning_db_path=learning_db_path,
            on_stage=on_stage,
            provenance_by_digest=provenance_by_digest,
            text_by_digest=text_by_digest,
            _stage=_stage,
            rematch_owed=bool(refresh.get("changes")),
        )
        if refresh.get("changes"):
            result["master_data_refresh"] = refresh["changes"]
        # Item 112: a neighbouring month whose statement period covers a new
        # receipt owes a re-match from this write on, in the same lock span.
        # A failure to owe never fails an add that is already committed.
        neighbours: list[str] = []
        if result.get("n_added"):
            try:
                neighbours = _owe_neighbour_rematches_locked(
                    store, run, list(result.get("documents") or [])
                )
            except Exception as exc:  # noqa: BLE001 - reported in the result
                result["neighbour_rematch_error"] = f"{type(exc).__name__}: {exc}"
        # R4.1: the same debt for a TRIP add, owed in this same span. The
        # months are chosen by the trip's dates rather than the receipts'
        # (a trip lends its whole pool), so this does not gate on
        # `documents`, only on something having been added.
        trip_months: list[str] = []
        if result.get("n_added") and is_trip_batch(run):
            try:
                trip_months = _owe_trip_month_rematches_locked(store, run)
            except Exception as exc:  # noqa: BLE001 - reported in the result
                result["trip_rematch_error"] = f"{type(exc).__name__}: {exc}"

    # OUTSIDE the lock (`rematch_month` takes the same non-reentrant lock to
    # commit). A month whose statement is already loaded reconciles the
    # arrival now; one without a statement does nothing here and pays
    # nothing. Skipped when the upload added no receipt -- an all-duplicate
    # add changed nothing to re-match -- unless the arrival's refresh moved
    # the month's card list, which the matcher reads too.
    if result.get("n_added") or result.get("master_data_refresh") or owed_before:
        rematch = rematch_after_change(
            store, run.run_id,
            learning_db_path=learning_db_path, on_stage=on_stage,
            trigger="receipts",
        )
        if rematch is not None:
            result["rematch"] = rematch
        # R4b: a receipt joining a TRIP is a candidate for every
        # reconciling month whose charges span the trip -- their pools
        # span it (item 38 ruling 3), so they re-match now rather than
        # waiting for their own next change.
        if is_trip_batch(run):
            # The debt was already written inside the lock span above, so
            # this only PAYS it; a restart in between leaves the mark and
            # `resume_pending_rematches` finishes the job at boot.
            cross = rematch_trip_months(
                store, trip_months, learning_db_path=learning_db_path
            )
            if cross:
                result["months_rematched"] = cross
    # Item 112: the neighbours this arrival owed, after the month's own
    # re-match (so a receipt both statements could take goes home first).
    if neighbours:
        cross = rematch_neighbour_months(
            store, neighbours, learning_db_path=learning_db_path
        )
        if cross:
            result["months_rematched"] = cross
    return result


def _add_receipts_locked(
    store: RunStore,
    run: RunRow,
    staging_dir: str | Path,
    now_iso: str,
    *,
    learning_db_path: Path | None,
    on_stage,
    provenance_by_digest: dict[str, dict] | None,
    text_by_digest: dict[str, str] | None = None,
    _stage,
    rematch_owed: bool = False,
) -> dict:
    from ..categorize import categorize_receipts_with_registry
    from ..cli import _resolve_categorizer_chart
    from ..ingest.receipts_folder import parse_receipt_file

    # No statement refusal here since 2b-2: receipts arrive all month,
    # including after the statement has, and the month stays open for them.
    # `add_receipts_to_expense_batch` re-matches once this returns, so an
    # arrival reconciles rather than just landing in the pool.

    _, receipts, outcome, _parse_errors = snapshot_from_dict(run.snapshot)
    work_dir = Path(run.work_dir)
    receipts_dir = work_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    cfg = run.config or {}
    entity = (cfg.get("expense") or {}).get("legal_entity_id", "")
    default_ccy = (cfg.get("receipts") or {}).get("default_currency")

    llm_client, tracker, llm_source = _batch_llm_client(cfg)

    # Existing content hashes: a re-upload of a file already in the pool is
    # a no-op, not a duplicate expense. Keyed on the files the SNAPSHOT
    # references (pool + set-aside), never the raw directory listing: a
    # killed job can leave orphan files on disk that no snapshot knows, and
    # disk-keyed dedupe would then block re-adding those receipts forever
    # (adversarial review 2026-08-20).
    referenced = {r.document_id for r in receipts} | {
        str(e.get("file", "")) for e in set_aside_entries(run.snapshot)
    }
    existing_hashes = set()
    existing_files = [
        p for p in sorted(receipts_dir.iterdir())
        if p.is_file() and p.name in referenced
    ]
    # Item 74: the same digests, kept by stored name, so the batch snapshot
    # persists them (`RECEIPT_DIGESTS_KEY`) the way a statement run's
    # `folder:{digest}` id always has.
    add_digests: dict[str, str] = {}
    for p in existing_files:
        add_digests[p.name] = hashlib.sha1(p.read_bytes()).hexdigest()[:16]
        existing_hashes.add(add_digests[p.name])
    # Item 106: which stored file a skipped duplicate matched, and whether
    # that file is itself a set-aside page (then the bytes are not an
    # expense anywhere, and "already on file, no action" would mislead).
    stored_by_digest = {d: n for n, d in add_digests.items()}
    set_aside_by_file = {
        str(e.get("file", "")): e
        for e in set_aside_entries(run.snapshot) if not e.get("restored")
    }

    _stage("ingesting")
    issues: list[str] = []
    issue_details: list[dict] = []
    # Item 106: every file that did NOT become an expense, with why, in
    # upload order. Mail intake stamps it on the archive so the log row and
    # the sender's acknowledgement can say "nothing was added, because ..."
    # instead of "Added" about a forward that created no expense.
    not_added: list[dict] = []

    def _issue(code: str, file: str, **kw) -> None:
        prose, detail = upload_issue(code, file, **kw)
        issues.append(prose)
        issue_details.append(detail)
        not_added.append({"file": file, "why": code})

    new_receipts: list[Receipt] = []
    new_set_aside: list[dict] = []
    new_provenance: dict[str, dict] = {}
    n_seen = 0
    # Next free index from EVERYTHING on disk (referenced or orphan), so a
    # new dest name can never overwrite a referenced file across index gaps
    # left by deletions, nor an orphan another job wrote before dying.
    n_index = 0
    for p in receipts_dir.iterdir():
        m = re.match(r"^(\d{4})__", p.name)
        if m:
            n_index = max(n_index, int(m.group(1)) + 1)
    for name, data in _folder_receipt_files(staging_dir):
        n_seen += 1
        display = re.sub(r"^\d{4}__", "", Path(name).name)
        if n_seen > FOLDER_MAX_FILES:
            _issue(UPLOAD_ISSUE_CAP, display, limit=FOLDER_MAX_FILES)
            break
        suffix = Path(display or "receipt").suffix.lower()
        if suffix not in FOLDER_RECEIPT_SUFFIXES:
            _issue(UPLOAD_ISSUE_UNSUPPORTED, display, suffix=suffix or None)
            continue
        if not data:
            _issue(UPLOAD_ISSUE_EMPTY, display)
            continue
        if len(data) > FOLDER_RECEIPT_MAX_BYTES:
            _issue(UPLOAD_ISSUE_TOO_LARGE, display, limit=FOLDER_RECEIPT_MAX_MB)
            continue
        digest = hashlib.sha1(data).hexdigest()[:16]
        if digest in existing_hashes:
            # already in the pool (or earlier in this upload)
            stored = stored_by_digest.get(digest, "")
            prior = set_aside_by_file.get(stored)
            if prior is not None:
                not_added.append({
                    "file": display, "why": "set_aside",
                    "reason": str(prior.get("reason") or ""),
                    "document_id": stored,
                })
            else:
                not_added.append({
                    "file": display, "why": "already_on_file",
                    "document_id": stored,
                })
            continue
        existing_hashes.add(digest)
        fs_name = re.sub(r"[^A-Za-z0-9._-]", "_", display) or f"receipt{suffix}"
        dest = receipts_dir / f"{n_index:04d}__{fs_name}"
        n_index += 1
        dest.write_bytes(data)
        add_digests[dest.name] = digest
        stored_by_digest.setdefault(digest, dest.name)
        if provenance_by_digest and digest in provenance_by_digest:
            new_provenance[dest.name] = provenance_by_digest[digest]
        receipt = None
        if llm_client is not None:
            try:
                parsed = parse_receipt_file(
                    dest,
                    legal_entity_id=entity,
                    client=llm_client,
                    default_currency=default_ccy,
                )
                receipt = replace(parsed, receipt_name=display)
            except Exception:  # noqa: BLE001 - extraction is best-effort
                receipt = None
        if receipt is None:
            receipt = Receipt(
                document_id=dest.name,
                legal_entity_id=entity,
                detected_date=None,
                detected_total=None,
                detected_currency=None,
                detected_vendor=display,
                receipt_name=display,
            )
        # Non-receipt quarantine (2026-08-13): mirror generate_expenses —
        # a statement page / report-summary page added mid-month must not
        # join the expense pool. The exclusion reaches the reviewer via the
        # ingest summary's issues list AND the snapshot's set-aside strip
        # (which survives later adds and carries the restore path); the
        # stored file stays on disk (its hash also keeps a re-upload from
        # costing another OCR call).
        # A mail body renders to an image PDF, so the extractor keeps the
        # model's notes as `ocr_text` rather than the body's words. Carry the
        # real text in, and only where the extraction found none of its own.
        if text_by_digest and not (receipt.ocr_text or "").strip():
            carried = text_by_digest.get(digest)
            if carried:
                receipt = replace(receipt, ocr_text=carried)
        receipt = keep_invoice_read_as_statement(receipt) or receipt  # item 105
        # Correspondence rung (2026-09-24): a payment reminder / past-due
        # notice about ANOTHER document is not a purchase. Read the STORED
        # file's own text, never the mail that carried it — a "Reminder
        # Invoice" mail legitimately attaches the real invoice, and judging
        # the mail would set the invoice aside with it. This is the path a
        # mailed receipt actually takes, so it is the one that matters.
        receipt = quarantine_correspondence(receipt) or receipt
        label = NON_RECEIPT_LABELS.get(receipt.document_type)
        if label is not None:
            issues.append(
                f"{display}: looks like {label}, not a purchase receipt — "
                "excluded (no expense created)"
            )
            new_set_aside.append(_set_aside_entry(receipt, now_iso))
            set_aside_by_file[dest.name] = new_set_aside[-1]
            not_added.append({
                "file": display, "why": "set_aside",
                "reason": receipt.document_type,
                "document_id": dest.name,
            })
            continue
        new_receipts.append(receipt)

    if new_receipts:
        _stage("categorizing")
        # Hoisted above the memory pass (item 173): the card gate below needs
        # it, and the categorizer further down reads the same one.
        registry = MerchantRegistry.from_settings(store.get_settings())
        memory = ExpenseMemory.from_db_path(learning_db_path)
        new_receipts = memory.apply(new_receipts)
        # Item 173, second half: the remembered CARD only for a brand the
        # registry vouches is paid on one card, the same gate the full
        # ingest and the grid hold. Before the entity stamping below, not
        # after: the card resolves the company and the person, so a card
        # nobody vouched for must not be allowed to answer either.
        new_receipts = drop_unvouched_remembered_cards(new_receipts, registry)
        # Cards R3: same post-OCR entity stamping as generate_expenses —
        # the paying card (batch config snapshot + explicit assignments)
        # resolves each added receipt's entity before categorization, so
        # learned (entity, vendor) lookups see the card-resolved entity.
        from ..cards import stamp_card_entities

        new_receipts = stamp_card_entities(
            new_receipts, _batch_cards(cfg), _batch_card_hints(cfg)
        )
        learned = (
            MerchantCategoryLookup.from_db_path(learning_db_path)
            if learning_db_path is not None else None
        )
        try:
            _, account_labels, _scope = _resolve_categorizer_chart(
                cfg, work_dir, None, {}
            )
        except Exception:  # noqa: BLE001 - labels degrade, ingest never breaks
            account_labels = None
        new_receipts, _ = categorize_receipts_with_registry(
            new_receipts,
            registry=registry,
            client=llm_client,
            chart_of_accounts=account_labels,
            learned=learned,
            # A batch created before the GL engine carries no map and keeps
            # its bucket vocabulary for every receipt added later.
            entity_orgs=cfg.get(GL_ENTITY_ORGS_KEY),
        )

    _stage("saving")
    pool = receipts + new_receipts
    outcome.unmatched_receipts.extend(r.document_id for r in new_receipts)
    n_categorized, n_uncategorized = categorized_counts(pool)
    summary = {
        "at": now_iso,
        "n_files": n_seen,
        "n_added": len(new_receipts),
        # The rows THIS add created, so mail intake can stamp its archive
        # with the resulting expenses (empty = everything was a duplicate).
        "documents": [r.document_id for r in new_receipts],
        "llm_source": llm_source,
        # float(): CostTracker.total_cost_usd is a Decimal, and this summary
        # goes straight into json.dumps via update_run_snapshot (caught live
        # 2026-07-28: the add job died at "saving" with a real tracker).
        "cost_usd": float(round(tracker.total_cost_usd, 4)) if tracker else 0.0,
        "issues": issues,
        # Same rejections, machine-readable (item 20); prose unchanged.
        "issue_details": issue_details,
        # Item 106: per file, why it created no expense (set_aside with its
        # reason, already_on_file, or an upload-issue code).
        "not_added": not_added,
    }
    new_snapshot = dict(run.snapshot)
    new_snapshot["receipts"] = [receipt_to_dict(r) for r in pool]
    new_snapshot["outcome"] = outcome_to_dict(outcome)
    new_snapshot["expense_ingest"] = summary
    # Item 74: every stored receipt's byte digest, merged over what the
    # snapshot already held (the ladder's rung 1 reads it).
    new_snapshot[RECEIPT_DIGESTS_KEY] = {
        **(run.snapshot.get(RECEIPT_DIGESTS_KEY) or {}),
        **add_digests,
    }
    # Merge, don't replace: creation-time entries (and a legacy run's
    # derived ones, normalized here on first add) stay restorable.
    all_set_aside = set_aside_entries(run.snapshot) + new_set_aside
    if all_set_aside:
        new_snapshot["set_aside"] = all_set_aside
    # Intake provenance (who mailed this in): merge, first-write wins per
    # stored file, so a direct-alias submission is never overwritten by a
    # later bulk re-upload of the same bytes under a new name.
    all_provenance = dict(run.snapshot.get("intake_provenance") or {})
    for k, v in new_provenance.items():
        all_provenance.setdefault(k, v)
    if all_provenance:
        new_snapshot["intake_provenance"] = all_provenance
    # Item 113: the receipts and the debt to re-pair them are ONE write, so
    # no restart can store the one without the other.
    if (new_receipts or rematch_owed) and has_statement(run):
        new_snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(
            run.snapshot, "receipts"
        )
    store.update_run_snapshot(run.run_id, new_snapshot)
    store.update_run_summary(run.run_id, {
        **run.summary,
        "n_expenses": len(pool),
        "n_receipts": len(pool),
        "n_categorized": n_categorized,
        "n_uncategorized": n_uncategorized,
        "n_set_aside": sum(
            1 for e in all_set_aside if not e.get("restored")
        ),
    })
    return summary


def prepare_statement_attach(
    run: RunRow,
    *,
    statement_bytes: bytes,
    statement_filename: str,
    form: RunForm,
) -> tuple[str, dict | None]:
    """The fail-fast half of a statement attach: save the file into the
    batch's work dir and resolve the column map. Raises `RunInputError`
    (with the file's headers) for a user-fixable mapping problem, so the
    form can re-prompt synchronously; the slow match runs in the
    background. Returns (stmt_name, column_map) — column_map None for the
    Chase PDF path.

    Since PR 2b-2b-2 a second upload is ALLOWED and appends (the living
    month: a statement arrives per card, several times a month). The
    refusal that used to stand here was lifted deliberately, together with
    the route gate above it, and `tests/test_living_month.py` pins the new
    behavior in place of the old one.

    Each upload gets its OWN name on disk (`_unique_upload_name`). Two of
    Criss's per-card exports are both plausibly called `statement.xlsx`,
    and letting the second overwrite the first would leave the first file's
    charges pointing `source_row` into a workbook whose rows are somebody
    else's — the same wrong-cell write `Transaction.source_file` exists to
    prevent, arriving by a different road."""
    if not statement_bytes:
        raise RunInputError(
            "No statement file uploaded.", code="no_statement_file"
        )
    stmt_name = _safe_name(statement_filename or "", "statement.csv")
    if Path(stmt_name).suffix.lower() not in _STATEMENT_SUFFIXES:
        raise RunInputError(
            "The statement file should be a .csv, .xlsx or .pdf export from "
            "the bank.",
            code="unsupported_statement_file",
            suffix=Path(stmt_name).suffix or "",
        )
    work_dir = Path(run.work_dir)
    stmt_name = _unique_upload_name(work_dir, stmt_name)
    stmt_path = work_dir / stmt_name
    stmt_path.write_bytes(statement_bytes)
    if stmt_path.suffix.lower() == ".pdf":
        return stmt_name, None
    return stmt_name, _resolve_statement_map(stmt_path, form)


def execute_statement_attach(
    store: RunStore,
    run: RunRow,
    *,
    stmt_name: str,
    column_map: dict | None,
    form: RunForm,
    settings: dict | None,
    now_iso: str,
    learning_db_path: Path | None = None,
    on_stage=None,
    upload_name: str = "",
) -> dict:
    """Graduate an expense batch into a reconciliation: load the attached
    statement, then hand off to `rematch_month`, which runs the SAME
    matching + judgment + receiptless-charge categorization primitives
    `reconcile()` uses over the batch's reviewer-corrected receipt pool
    and persists transactions + outcome onto the run. From here every
    statement-mode surface (workbench, decisions, confirm-ready,
    journal/report/reconciled exports) works on this run unchanged.

    Since PR 2b-1 this function owns only the STATEMENT half: resolving
    the statement config and reading the file. Everything after that
    lives in `rematch_month`, because the living month re-runs exactly
    that work whenever a receipt arrives or another statement is
    appended, and it must be one implementation rather than two that
    drift.

    `reconcile()` itself is untouched: this reuses the module-level
    pipeline pieces exactly as the folder-ingest re-match already does.

    Since PR 2b-2b-1 the read and the fold are their own steps
    (`read_statement_upload` + `merge_transactions`), and since PR 2b-2b-2
    this IS the append path: a second upload is no longer refused, so
    `existing` is whatever the month already holds and the fold is what
    keeps a re-supplied charge from landing twice. The one-shot attach is
    the degenerate case (`existing` empty), not a separate implementation.

    The upload is recorded in `statements[]`, written by `rematch_month`
    inside the commit lock so the month has one writer and the advisory is
    judged against the entries that are actually there at that moment.
    """
    transactions, stmt_issues, new_cfg, entity = read_statement_upload(
        run,
        stmt_name=stmt_name,
        column_map=column_map,
        form=form,
        settings=settings,
        on_stage=on_stage,
    )
    if not transactions:
        # Item 51. Refuse before the fold, so the month keeps exactly the
        # state it had: no charge, no `statements[]` entry, no graduation
        # to the workbench. The saved upload stays on disk and is inert —
        # nothing reads the work dir, only `statements[]`.
        raise RunInputError(
            statement_read_nothing(
                upload_name or stmt_name,
                (new_cfg.get("statement") or {}).get("sheet_name"),
            ),
            code="statement_read_nothing",
            file=upload_name or stmt_name,
            sheet=(new_cfg.get("statement") or {}).get("sheet_name") or "",
        )
    merged = merge_transactions(month_transactions(run), transactions)

    return rematch_month(
        store,
        run,
        transactions=merged.transactions,
        cfg=new_cfg,
        entity=entity,
        statement_issues=stmt_issues,
        now_iso=now_iso,
        learning_db_path=learning_db_path,
        on_stage=on_stage,
        statement_entry=build_statement_entry(
            stored_name=stmt_name,
            upload_name=upload_name or stmt_name,
            account_id=(new_cfg.get("statement") or {}).get("account_id", ""),
            card_key=form.card_key,
            sheet_name=(new_cfg.get("statement") or {}).get("sheet_name"),
            transactions=transactions,
            n_new=len(merged.added),
            uploaded_at=now_iso,
            # Read back off the block `read_statement_upload` just wrote, the
            # same source `account_id` and `sheet_name` come from, so the
            # entry records what the parser was actually handed.
            column_map=(new_cfg.get("statement") or {}).get("column_map"),
            card_currency=(new_cfg.get("statement") or {}).get(
                "account_card_currency", ""
            ),
            statement_id=statement_content_id(Path(run.work_dir) / stmt_name),
        ),
        trigger="statement",
    )


def read_statement_upload(
    run: RunRow,
    *,
    stmt_name: str,
    column_map: dict | None,
    form: RunForm,
    settings: dict | None,
    on_stage=None,
) -> tuple[list, list, dict, str]:
    """Resolve one uploaded statement file's config block and read it.

    The STATEMENT half of an attach, split out so the append path
    (PR 2b-2b) reads its file exactly the way the first one was read
    rather than growing a parallel copy that drifts — the same reason
    `rematch_month` exists for the half after it.

    Returns `(transactions, issues, cfg, entity)`. The cfg is the run's
    config with this file's `statement` block written over it and master
    data applied; the entity is the statement's own, which the caller
    hands to `rematch_month` for the cross-entity advisory.
    """
    from ..cli import _load_statement

    work_dir = Path(run.work_dir)
    cfg = run.config or {}

    entity = resolve_entity(form, settings)
    stmt_block: dict = {
        "path": stmt_name,
        "legal_entity_id": entity,
        "account_card_currency": form.account_card_currency or "USD",
    }
    if column_map is not None:
        stmt_block["account_id"] = form.account_id or "card"
        stmt_block["column_map"] = column_map
        if form.sheet_name:
            stmt_block["sheet_name"] = form.sheet_name
    new_cfg = {**cfg, "statement": stmt_block}
    new_cfg = apply_master_data(new_cfg, form, settings)

    if on_stage is not None:
        try:
            on_stage("reading")
        except Exception:  # noqa: BLE001 - progress is best-effort
            pass
    try:
        transactions, stmt_issues = _load_statement(new_cfg, work_dir)
    except ConfigError as exc:
        raise RunInputError(
            str(exc), code="statement_unreadable"
        ) from exc
    # Item 82: refresh the ECB monthly averages for every month this
    # statement's charges fall in (and the month's own neighbours), so a
    # month created before its average was published reads it from here.
    new_cfg = apply_ecb_rates(new_cfg, ecb_months_for(run.label, transactions))
    return transactions, stmt_issues, new_cfg, entity


def reread_statements(
    store: RunStore,
    run: RunRow,
    *,
    settings: dict | None,
    now_iso: str,
    learning_db_path: Path | None = None,
    on_stage=None,
) -> dict:
    """Rebuild a month's charges from the statement files it already holds,
    then re-match. The repair path for a month whose stored charges were
    parsed wrong (2026-09-11: the Excel parser kept Chase's printed sign,
    so July and August 2026 held every purchase as a negative amount and
    reconciled 0 against receipts that were sitting right there).

    Why a re-read and not a re-upload: `transaction_id` is content-derived
    from the CANONICAL amount, so re-uploading the same file after the
    parser fix would fold 111 new ids in beside the 111 old ones and double
    the month. This reads every entry in `statements[]` from disk, in
    upload order, through the same `read_statement_upload` + `merge` the
    attach uses, and hands `rematch_month` the rebuilt set as a REPLACEMENT
    (`replace_statements`), which is the one thing the append path may
    never do.

    Deny-by-default, nothing partial: a missing file, a column map that no
    longer resolves, or a reviewer decision that cannot be carried over
    aborts before anything is written. Decisions ride over by sheet row
    (`statement_anchors`: old id -> row -> new id); a decision on a charge
    with no anchor and no surviving id is the one case that refuses, so a
    verdict is never silently orphaned.

    The column map and the card currency for each file are the ones that
    upload recorded (item 64). Falling back, in order: the config's own map
    for the upload it still describes, then a fresh guess. The fallbacks
    only reach entries written before 2026-09-15, and both are worse than
    what they replace: `config.statement` describes the LATEST upload only,
    so on a multi-statement month it lends its map and its currency to files
    that were read with neither, and a guess cannot reproduce the operator's
    manual picks at all.
    """
    entries = month_statements(run)
    if not entries:
        raise RunInputError(
            "this month has no recorded statement upload to re-read",
            code="no_statement_to_reread",
        )
    work_dir = Path(run.work_dir)
    cfg = run.config or {}
    stmt_cfg = dict(cfg.get("statement") or {})
    old_anchors: dict[str, dict] = dict(
        (run.snapshot or {}).get(STATEMENT_ANCHORS_KEY) or {}
    )
    old_ids = {
        str(td.get("transaction_id"))
        for td in (run.snapshot or {}).get("transactions") or []
    }

    transactions: list = []
    issues: list = []
    rebuilt: list[dict] = []
    new_cfg: dict = cfg
    entity = ""
    for entry in entries:
        stored = str(entry.get("file") or "")
        stmt_path = work_dir / stored
        if not stored or not stmt_path.is_file():
            raise RunInputError(
                f"statement file {stored or '?'} is missing from this "
                "month's folder; nothing was changed",
                code="statement_file_missing",
                file=stored or "",
            )
        account_id = str(
            entry.get("account_id") or stmt_cfg.get("account_id") or ""
        )
        form = RunForm(
            account_id=account_id,
            account_legal_entities={},
            # This upload's OWN currency when it recorded one (item 64).
            # `config.statement` describes only the latest upload, so on a
            # month holding a USD and a EUR card statement the fallback
            # re-reads both at whichever currency arrived last, and a charge
            # whose currency moved stops matching its receipt.
            account_card_currency=str(
                entry.get("card_currency")
                or stmt_cfg.get("account_card_currency")
                or "USD"
            ),
            sheet_name=entry.get("sheet_name") or None,
            column_map_overrides={},
            receipts_source="csv",
            expense_column_map={},
            receipts_default_currency="",
            use_llm=False,
            card_key=str(entry.get("card_key") or ""),
        )
        column_map: dict | None
        if stmt_path.suffix.lower() == ".pdf":
            column_map = None
        elif entry.get("column_map"):
            # The map this upload was actually read with (item 64), which
            # may carry the operator's manual picks for headers the guess
            # cannot name at all.
            column_map = dict(entry["column_map"])
        elif stored == stmt_cfg.get("path") and stmt_cfg.get("column_map"):
            column_map = dict(stmt_cfg["column_map"])
        else:
            column_map = _resolve_statement_map(stmt_path, form)
        txs, stmt_issues, new_cfg, entity = read_statement_upload(
            run,
            stmt_name=stored,
            column_map=column_map,
            form=form,
            settings=settings,
            on_stage=on_stage,
        )
        if not txs and (entry.get("n_rows") or 0):
            # Item 51 through the other door, and worse here: a re-read
            # REPLACES the charge set, so a file that used to hold rows and
            # now reads none takes its charges out of the month silently.
            # Same deny-by-default as a missing file or an unresolvable map.
            # Keyed on the RECORDED count so a month that already holds a
            # zero-row entry (recorded before the attach refused one) can
            # still be re-read rather than being wedged by this guard.
            raise RunInputError(
                f"statement file {stored} held {entry['n_rows']} charges "
                "when it was uploaded and now reads none; nothing was "
                "changed",
                code="statement_reads_nothing_now",
                file=stored,
                n_rows=entry["n_rows"],
            )
        merged = merge_transactions(transactions, txs)
        transactions = merged.transactions
        issues.extend(stmt_issues)
        rebuilt.append(
            build_statement_entry(
                stored_name=stored,
                upload_name=str(entry.get("upload_name") or stored),
                account_id=(new_cfg.get("statement") or {}).get(
                    "account_id", ""
                ),
                card_key=form.card_key,
                sheet_name=(new_cfg.get("statement") or {}).get("sheet_name"),
                transactions=txs,
                n_new=len(merged.added),
                uploaded_at=str(entry.get("uploaded_at") or now_iso),
                # Re-record what THIS re-read used, so an entry written
                # before item 64 carries both from here on.
                column_map=column_map,
                card_currency=form.account_card_currency,
                # Same bytes, same id (note item T2): a re-read after a
                # restore keeps the id the attach recorded, and an entry
                # written before the id existed gains one here.
                statement_id=statement_content_id(stmt_path),
            )
        )

    # Carry the reviewer's verdicts over by sheet row. Every old id that has
    # an anchor maps to the new id at the same (file, row); an id the re-read
    # kept maps to itself. A DECISION on an id that has neither is the one
    # thing that refuses the whole re-read: silently dropping a verdict is
    # worse than leaving the month as it is.
    new_ids = {t.transaction_id for t in transactions}
    new_by_row: dict[tuple[str, int], str] = {}
    for e in rebuilt:
        for tid, row in (e.get("_anchors") or {}).items():
            new_by_row[(str(e["file"]), int(row))] = tid
    rekey: dict[str, str] = {}
    for file_name, anchors in old_anchors.items():
        for old_id, row in (anchors or {}).items():
            if old_id in new_ids:
                continue
            target = new_by_row.get((str(file_name), int(row)))
            if target is not None:
                rekey[str(old_id)] = target
    stranded = [
        tid
        for tid in store.get_decisions(run.run_id)
        if tid in old_ids and tid not in new_ids and tid not in rekey
    ]
    if stranded:
        raise RunInputError(
            f"{len(stranded)} reviewer decision(s) sit on charges this "
            "re-read would retire and no sheet row carries them over; "
            "nothing was changed",
            code="reread_strands_decisions",
            n_decisions=len(stranded),
        )

    result = rematch_month(
        store,
        run,
        transactions=transactions,
        cfg=new_cfg,
        entity=entity,
        statement_issues=issues,
        now_iso=now_iso,
        learning_db_path=learning_db_path,
        on_stage=on_stage,
        replace_statements=rebuilt,
        rekey_decisions=rekey,
        trigger="reread",
    )
    result["n_statements"] = len(rebuilt)
    result["n_transactions_before"] = len(old_ids)
    result["n_transactions"] = len(transactions)
    result["n_decisions_rekeyed"] = len(rekey)
    return result


# ---------------------------------------------------------------------------
# Cross-run receipt claims (R4, backlog item 38)
# ---------------------------------------------------------------------------
# A receipt must never settle two charges across two batches. Within one run
# the matcher's own assignment pass guarantees single consumption; across
# runs the `receipt_claims` table is the arbiter (store.py). The protocol,
# in `rematch_month`: an advisory read excludes receipts another run has
# already settled from the candidate pool, a commit-time re-check inside
# `_BATCH_ADD_LOCK` downgrades any pairing whose receipt was claimed while
# the match ran, and the commit then records this run's own settlements.
# Reviewer decisions keep the table current (`sync_claim_for_decision`).
# With no cross-batch receipts in play (every month before trips exist),
# every claim is a run's own and none of this changes a match result.


# Snapshot keys for the trip-spanning pool (R4b). `borrowed_receipts`
# holds COPIES of the trip receipts this month's outcome references, so
# the workbench renders a cross-batch match without a store join; the
# receipt itself keeps living in its trip. `receipt_sources` maps each
# borrowed document to its origin ({run_id, trip_id, label}) -- the claims
# protocol keys on it, and the view names the trip from it. Both keys are
# ABSENT on a month referencing no trip receipt, which keeps the
# zero-trips snapshot byte-identical to pre-R4.
BORROWED_RECEIPTS_KEY = "borrowed_receipts"
RECEIPT_SOURCES_KEY = "receipt_sources"


def borrowed_receipts(run: RunRow) -> list[Receipt]:
    """The copies of the receipts this month's outcome borrowed from a trip
    or a neighbouring month (item 38 ruling 3, item 61). They are not part
    of the month's own pool, so anything that reads a PAIRING has to fold
    them in or the receipt side of it is missing (item 115: a confirmed
    pair on a borrowed receipt taught nothing at sign-off). Empty on every
    month that borrows nothing, which is most of them."""
    out: list[Receipt] = []
    for bd in (run.snapshot or {}).get(BORROWED_RECEIPTS_KEY) or []:
        try:
            out.append(receipt_from_dict(bd))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def receipt_source_run(run: RunRow, document_id: str) -> str:
    """The run a receipt LIVES in: its origin per the snapshot's
    `receipt_sources` map for a borrowed trip receipt, else the run
    itself. Claims must be keyed on the home run, not the borrower."""
    sources = (run.snapshot or {}).get(RECEIPT_SOURCES_KEY) or {}
    entry = sources.get(document_id)
    if isinstance(entry, dict):
        return str(entry.get("run_id") or run.run_id)
    return str(entry or run.run_id)


def trip_pool_for_month(
    store: RunStore,
    run: RunRow,
    transactions: list,
    own_doc_ids: set[str],
) -> tuple[list, dict[str, dict]]:
    """The receipts a month's statement may settle from TRIPS (item 38
    ruling 3): every trip whose inclusive date range overlaps the span of
    charge dates the month holds contributes its batch's receipts to the
    candidate pool. Returns `(receipts, origins)`; `origins` maps each
    borrowed document to `{run_id, trip_id, label}`.

    Four exclusions, each deliberate: a trip batch never borrows
    (statements live on months); a receipt another run already settled is
    out (the claims table, advisory read -- the cross-batch never-settle
    guard); a confirmed private expense is not company-card money and
    never meets a company statement; and a document id the month's own
    pool already holds is dropped -- the month's own copy wins. That last
    one is a real tradeoff, not just dedupe: receipt ids are
    position-prefixed per batch (`0000__a.jpg`), so two DIFFERENT
    receipts sharing a filename and slot collide across batches, and the
    colliding trip receipt then simply is not borrowed (it stays
    matchable in later months and by hand). Offering two receipts under
    one id would corrupt the matcher's consumption set and the view's
    lookup, which is worse than a narrower pool."""
    if is_trip_batch(run):
        return [], {}
    dates = [t.transaction_date for t in transactions if t.transaction_date]
    if not dates:
        return [], {}
    lo, hi = min(dates), max(dates)
    borrowed: list = []
    origins: dict[str, dict] = {}
    for trip in store.list_trips():
        try:
            t0 = date.fromisoformat(trip.start_date)
            t1 = date.fromisoformat(trip.end_date)
        except ValueError:
            continue
        if t1 < lo or t0 > hi:
            continue
        batch = find_trip_batch(store, trip.trip_id)
        if batch is None or batch.run_id == run.run_id:
            continue
        t_field = store.get_expense_field_overrides(batch.run_id)
        t_receipts, t_kwargs = _expense_export_inputs(
            batch,
            store.get_category_overrides(batch.run_id),
            t_field,
            store.get_expense_edits(batch.run_id),
            store.get_duplicate_resolutions(batch.run_id),
        )
        private = _private_reimbursements(t_field)
        claims = store.get_claims_on_receipts(batch.run_id)
        entity_by_doc = t_kwargs.get("entity_by_doc") or {}
        for r in t_receipts:
            doc = r.document_id
            if doc in own_doc_ids or doc in origins or doc in private:
                continue
            c = claims.get(doc)
            if c is not None and c["claimed_by_run_id"] != run.run_id:
                continue
            ent = entity_by_doc.get(doc)
            if ent and ent != r.legal_entity_id:
                r = replace(r, legal_entity_id=ent)
            borrowed.append(r)
            origins[doc] = {
                "run_id": batch.run_id,
                "trip_id": trip.trip_id,
                "label": trip.name,
            }
    return borrowed, origins


TRIP_REMATCH_TRIGGER = "trip"


def trip_months_covering(
    store: RunStore,
    trip_batch: RunRow,
    *,
    ranges: "list[tuple[date, date]] | None" = None,
) -> list[RunRow]:
    """The RECONCILING company months whose charge span overlaps the trip,
    the sibling of `neighbour_months_covering` for the trip trigger.

    `ranges` overrides the trip's own current range, which is what a date
    EDIT needs: the months owed a re-match are the union of those the OLD
    range covered and those the NEW one does, or a month the trip has just
    stopped overlapping would keep the receipts it may no longer borrow.
    Passing an empty list selects nothing; passing None reads the trip.

    A candidate is skipped unless it is an expense-generation run: a legacy
    statement-mode run cannot borrow from a trip, and re-matching it on
    every trip add is work with no effect (the neighbour path has carried
    this filter since item 112)."""
    tid = str((trip_batch.config or {}).get("trip_id") or "")
    if ranges is None:
        trip = store.get_trip(tid) if tid else None
        if trip is None:
            return []
        try:
            ranges = [(
                date.fromisoformat(trip.start_date),
                date.fromisoformat(trip.end_date),
            )]
        except ValueError:
            return []
    if not ranges:
        return []
    found: list[RunRow] = []
    for candidate in store.list_runs():
        if candidate.run_id == trip_batch.run_id or is_trip_batch(candidate):
            continue
        if (candidate.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if not has_statement(candidate):
            continue
        dates = []
        for td in (candidate.snapshot or {}).get("transactions") or []:
            raw = str(td.get("transaction_date") or "")[:10]
            try:
                dates.append(date.fromisoformat(raw))
            except ValueError:
                continue
        if not dates:
            continue
        lo, hi = min(dates), max(dates)
        if any(not (hi < t0 or lo > t1) for t0, t1 in ranges):
            found.append(candidate)
    return found


def _owe_trip_month_rematches_locked(
    store: RunStore,
    trip_batch: RunRow,
    *,
    ranges: "list[tuple[date, date]] | None" = None,
) -> list[str]:
    """Write the owed-re-match mark on every month the trip overlaps, and
    return their ids. Caller holds `_BATCH_ADD_LOCK`.

    The sibling of `_owe_neighbour_rematches_locked`, and it exists for the
    same reason: the debt has to be on the month BEFORE the lock is
    released, or a restart between the trip's own commit and the month's
    turn in the paying loop loses it silently, leaving a month reporting
    charges as settled by receipts it can no longer see (measured
    2026-09-21: July read 33 reconciled where 31 was true)."""
    owed: list[str] = []
    for other in trip_months_covering(store, trip_batch, ranges=ranges):
        current = store.get_run(other.run_id)
        if current is None:
            continue
        snapshot = dict(current.snapshot or {})
        snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(
            snapshot, TRIP_REMATCH_TRIGGER
        )
        store.update_run_snapshot(other.run_id, snapshot)
        owed.append(other.run_id)
    return owed


def owe_trip_month_rematches(
    store: RunStore,
    trip_batch: RunRow,
    *,
    ranges: "list[tuple[date, date]] | None" = None,
) -> list[str]:
    """`_owe_trip_month_rematches_locked` for a caller that does NOT already
    hold `_BATCH_ADD_LOCK` (the trip routes, the create path). The lock is
    not reentrant, so the two entrances stay separate."""
    with _BATCH_ADD_LOCK:
        return _owe_trip_month_rematches_locked(
            store, trip_batch, ranges=ranges
        )


def rematch_trip_months(
    store: RunStore,
    run_ids: list[str],
    *,
    learning_db_path: Path | None = None,
) -> list[dict]:
    """Pay the months' owed re-matches, outside every lock. Never raises:
    the trip change that owed them is committed, so a failure stays on that
    month's mark for the operator state, the notifier and the boot retry,
    and the REMAINING months are still paid. Mirrors
    `rematch_neighbour_months`; before this existed a raise on the first
    month aborted every month after it."""
    results: list[dict] = []
    for run_id in run_ids:
        try:
            rematch = rematch_after_change(
                store, run_id, learning_db_path=learning_db_path,
                trigger=TRIP_REMATCH_TRIGGER,
            )
        except Exception as exc:  # noqa: BLE001 - recorded on the trip mark
            error = f"{type(exc).__name__}: {exc}"
            _record_rematch_failure(
                store, run_id, TRIP_REMATCH_TRIGGER, error
            )
            rematch = {"error": error}
        if rematch is not None:
            results.append({"run_id": run_id, **rematch})
    return results


def rematch_months_after_trip_change(
    store: RunStore,
    trip_batch: RunRow,
    *,
    learning_db_path: Path | None = None,
    ranges: "list[tuple[date, date]] | None" = None,
) -> list[dict]:
    """A trip's receipt pool or date range changed; every RECONCILING
    company month whose charge span overlaps it re-matches, because its
    candidate pool spans this trip. Owes the debt under the lock first,
    then pays it outside, so a restart in between leaves the debt rather
    than a month whose counts silently disagree with its receipts.

    For a caller that already holds `_BATCH_ADD_LOCK`, owe inside its own
    span with `_owe_trip_month_rematches_locked` and pay with
    `rematch_trip_months` instead of calling this."""
    owed = owe_trip_month_rematches(store, trip_batch, ranges=ranges)
    return rematch_trip_months(
        store, owed, learning_db_path=learning_db_path
    )


def effective_settlements(
    outcome_matches: dict[str, str], decisions: dict
) -> dict[str, str]:
    """transaction_id -> document_id for every charge the run currently
    SETTLES: the matcher's deterministic matches, overlaid with the
    reviewer's verdicts (a reject releases, an explicit pick replaces).
    Review-bucket proposals settle nothing until confirmed."""
    settled = dict(outcome_matches)
    for tx_id, dec in decisions.items():
        if dec.status == STATUS_REJECTED:
            settled.pop(tx_id, None)
        elif (
            dec.status in (STATUS_CONFIRMED, STATUS_ALREADY_POSTED)
            and dec.chosen_document_id
        ):
            settled[tx_id] = dec.chosen_document_id
    return settled


def sync_claim_for_decision(
    store: RunStore,
    run: RunRow,
    transaction_id: str,
    status: str,
    chosen_document_id: str | None,
    now_iso: str,
) -> str | None:
    """Bring the claims table in line with one reviewer verdict. Returns a
    conflict sentence (and writes NO claim) when the receipt is already
    settled by another run -- the caller refuses the verdict rather than
    letting one receipt settle two charges across two batches. None means
    the claim state now matches the verdict."""
    if status == STATUS_REJECTED:
        store.delete_claims_for_tx(run.run_id, transaction_id)
        return None
    doc = chosen_document_id
    if status == STATUS_PENDING or doc is None:
        # Back to (or still on) the matcher's own state: the settlement is
        # the outcome's match for this charge, or nothing. Re-derive the
        # claim from that rather than from whatever pick the verdict
        # carried, so un-confirming a hand-pick releases the picked
        # receipt.
        doc = next(
            (
                m.get("document_id")
                for m in ((run.snapshot or {}).get("outcome") or {}).get(
                    "matches", []
                )
                if m.get("transaction_id") == transaction_id
            ),
            None,
        )
        if doc is None:
            store.delete_claims_for_tx(run.run_id, transaction_id)
            return None
    explicit_pick = (
        status in (STATUS_CONFIRMED, STATUS_ALREADY_POSTED)
        and chosen_document_id is not None
    )
    source = receipt_source_run(run, doc)
    prior = store.get_claims_on_receipts(source).get(doc)
    if prior is not None and prior["claimed_by_run_id"] != run.run_id:
        if explicit_pick:
            other = store.get_run(prior["claimed_by_run_id"])
            holder = (other.label or other.run_id) if other else prior[
                "claimed_by_run_id"]
            return Refusal(
                f"this receipt already settles a charge in {holder!r}; a "
                "receipt can only settle one charge. Reject it there "
                "first, or pick another receipt.",
                code="receipt_settled_elsewhere",
                batch=holder,
            )
        # A pending reset (or a bare ratify) onto a foreign-settled receipt
        # claims nothing and refuses nothing: the row simply goes back to
        # holding no claim, and the next re-match sorts the pairing out.
        store.delete_claims_for_tx(run.run_id, transaction_id)
        return None
    # A re-pick moves the charge's claim: release the old receipt first so
    # one charge never pins two.
    store.delete_claims_for_tx(run.run_id, transaction_id)
    ok = store.upsert_receipt_claim(
        source, doc, run.run_id, transaction_id, now_iso
    )
    if not ok and explicit_pick:
        return Refusal(
            "this receipt was just settled by another batch; a receipt "
            "can only settle one charge.",
            code="receipt_just_settled",
        )
    return None


def _downgrade_claimed_pairs(
    outcome, claimed_docs: set[str], pool_doc_ids: set[str]
) -> bool:
    """Strip every pairing that consumes a receipt another run settled
    while this match ran, sending the charge to unmatched and leaving the
    receipt to the run that claimed it. Returns whether anything moved."""
    stripped_tx: set[str] = set()
    changed = False
    for bucket in ("matches", "judgment_required", "ambiguous"):
        pairs = getattr(outcome, bucket)
        kept = [m for m in pairs if m.document_id not in claimed_docs]
        if len(kept) != len(pairs):
            changed = True
            stripped_tx.update(
                m.transaction_id for m in pairs
                if m.document_id in claimed_docs
            )
            pairs[:] = kept
    if not changed:
        return False
    # Every charge that lost its LAST pairing surfaces as unmatched rather
    # than vanishing -- the same never-drop shape as the fresh-row check.
    placed = (
        {m.transaction_id for m in outcome.matches}
        | {m.transaction_id for m in outcome.judgment_required}
        | {m.transaction_id for m in outcome.ambiguous}
        | set(outcome.refunds)
        | set(outcome.unmatched_transactions)
    )
    outcome.unmatched_transactions.extend(
        tx_id for tx_id in sorted(stripped_tx) if tx_id not in placed
    )
    # The receipt stays visible in this run's pool (settled elsewhere, so
    # unmatched HERE); ids not in the pool are another run's business.
    have = set(outcome.unmatched_receipts)
    outcome.unmatched_receipts.extend(
        d for d in sorted(claimed_docs & pool_doc_ids) if d not in have
    )
    return True


def rematch_month(
    store: RunStore,
    run: RunRow,
    *,
    transactions: list,
    cfg: dict,
    entity: str,
    statement_issues=(),
    now_iso: str = "",
    learning_db_path: Path | None = None,
    on_stage=None,
    statement_entry: dict | None = None,
    replace_statements: list[dict] | None = None,
    rekey_decisions: dict[str, str] | None = None,
    trigger: str = "",
) -> dict:
    """Match a month's transactions against its receipt pool and commit.

    `trigger` (item 58) names what caused this re-match ("statement",
    "reread", "receipts", "cards", "master_data", "set_aside", "trip") and
    rides on the `rematch_log` event the commit records; it changes nothing
    about the match itself.

    `replace_statements` (the statement re-read, 2026-09-11) is the one
    caller allowed to REPLACE the month's charge set instead of growing it:
    it hands in the `statements[]` entries it rebuilt from the stored files,
    and the commit swaps the whole `statements[]` + `statement_anchors`
    blocks for them. The never-drop invariant below is then judged against
    the UPLOADS rather than the ids (a re-read changes ids by design), and
    `rekey_decisions` carries the reviewer's verdicts from the ids the
    re-read retires to the ids the same sheet rows now have, inside the
    same lock, before the settlements are read.

    Extracted from `execute_statement_attach` (PR 2b-1) so the living
    month has ONE implementation of "reconcile what this month currently
    holds". The attach path calls it with transactions freshly read off a
    statement file; the incremental paths call it with the transactions
    the snapshot already carries, after a receipt arrives or another
    statement is appended.

    The sequence is unchanged from the attach path it came from: bake the
    reviewer's corrections into the receipt pool the matcher sees, match,
    judge, categorize receiptless charges, then commit under
    `_BATCH_ADD_LOCK` against a FRESH re-read of the row.

    One invariant guards every caller, enforced inside the commit lock: a
    commit never DROPS a charge the month already holds. Both paths read
    their transaction set minutes before they write it, and since PR
    2b-2b-2 a concurrent statement upload can genuinely add charges in
    between; committing the older set would erase them with no trace. This
    replaces the narrower `require_no_statement` check, which asked whether
    a statement existed at all and stopped meaning anything once a second
    one was allowed. It is strictly stronger: an attach that raced another
    attach still fails, and so does a receipt re-match that would have
    quietly rolled an append back.

    `statement_entry`, when given, is appended to `statements[]` here rather
    than by the caller, so the month has ONE writer under ONE lock and the
    entry's advisory is judged against the entries that are really there at
    commit time.

    LLM judgments are memoized in the snapshot by `JudgmentCache`, so a
    re-match only pays for pairs it has not judged before. On the attach
    path the cache starts empty and nothing changes.
    """
    from ..categorize import categorize_receipts  # noqa: F401 (parity import)
    from ..categorize_charges import categorize_charges
    from ..cli import (
        _apply_ambiguous_judgment,
        _apply_judgment,
        _apply_unmatched_judgment,
        _resolve_categorizer_chart,
        build_match_cfg,
    )
    from ..matching.deterministic import MatchingConfig, match_month
    from .judgment_cache import JudgmentCache

    def _stage(name: str) -> None:
        if on_stage is not None:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - progress is best-effort
                pass

    work_dir = Path(run.work_dir)
    batch_entity = (cfg.get("expense") or {}).get("legal_entity_id", "")
    # Note #79: the daily reference rates the app polls, read from the
    # store on EVERY re-match so a month sees the days polled since its
    # last one, and committed with the run's config below, so the screen's
    # FX block and a pulled-down replay read the table the matcher did.
    cfg = apply_fx_daily_rates(cfg, store, run.label, transactions)
    # 2026-09-23: and the ECB monthly averages, for any month this re-match
    # can reach that the stored table does not already hold. Until now they
    # were fetched at creation and statement attach only, so July 2026 --
    # created 2026-09-07, before item 82 shipped, and never re-attached --
    # carried no ECB table at all and leaned entirely on the typed Settings
    # rates. Retiring those without this top-up would leave its
    # cross-currency pairs with no rate on any rung.
    cfg = top_up_ecb_rates(cfg, run.label, transactions)

    # Bake the reviewer's truth into the receipt pool the matcher sees.
    _, receipts0, _, parse_errors = snapshot_from_dict(run.snapshot)
    overrides = store.get_category_overrides(run.run_id)
    field_overrides = store.get_expense_field_overrides(run.run_id)
    edits = store.get_expense_edits(run.run_id)
    # Item 70: bake from the EXTRACTION baseline, not from `receipts0`. The
    # snapshot pool is already baked, so a re-match after a CLEARED edit laid
    # the overlay on the old edit and the matcher kept pairing on a value the
    # reviewer took back. Same membership and order as the snapshot.
    bake_input = baseline_receipts(run)
    receipts = apply_expense_edits(
        bake_input, field_overrides, edits,
        category_overrides=overrides, default_entity=batch_entity,
    )
    receipts = apply_overrides(receipts, overrides)
    # Item 69 round A: the kept copy of a document inherits the card its
    # copies name, BEFORE the card chain below, so the chain derives the
    # entity from the inherited card and an invoice copy whose receipt copy
    # names another entity's card leaves this statement's scope (August
    # 2026: the Lovable 50 invoice took BASE44 50.00 on Corporate Services
    # while its receipt named card 1176, Consulting). Computed over the
    # full effective list, so a copy item 56 collapses below still lends.
    # The inherited values persist into the snapshot's `receipts` with the
    # entity bake, and are re-derived from the extraction baseline on every
    # re-match (item 70), so nothing accumulates. A group the reviewer ruled
    # `ignore` lends nothing (the card-less copy's own charge is then free
    # to match), and a hint word the operator assigned is kept.
    dup_resolutions = store.get_duplicate_resolutions(run.run_id)
    bake_hints = _batch_card_hints(cfg)
    receipts = inherit_card_from_copies(receipts, dup_resolutions, bake_hints)  # before the card chain
    # Cards R3: bake the SAME per-receipt entity the grid and the export
    # showed (override -> hint assignment -> card registry -> stamped
    # value) into the pool the matcher sees. Matching is entity-scoped
    # (`match_month` drops cross-entity pairs), so without this a card
    # assignment made after ingest never reaches the matcher and the
    # month silently reconciles 0 (adversarial review F1).
    card_res_bake = resolve_batch_row_cards(receipts, cfg, field_overrides)
    receipts = [
        (
            replace(r, legal_entity_id=res["entity"])
            if (res := card_res_bake.get(r.document_id)) is not None
            and res["entity"] != r.legal_entity_id
            else r
        )
        for r in receipts
    ]
    # Note #63 / item 137: the card the chain resolved (a pick on the row, the
    # printed method or an assigned hint, a remembered card) reaches the
    # matcher, which scopes and demotes by it (`match_month`).
    receipts = bake_card_scope(receipts, card_res_bake)

    # Item 59: the charge side of the same rule. Each charge that printed a
    # card carries THAT card's entity from the batch's registry snapshot
    # (blank when the registry cannot name it), so the entity scope below
    # and the coverage panel read one truth. Stamped before the match and
    # committed with the snapshot; ids do not hash the entity.
    transactions = stamp_charge_entities(transactions, _batch_cards(cfg))

    llm_client, tracker, _source = _batch_llm_client(cfg)
    # Judgments already paid for on this run answer from the snapshot;
    # only genuinely new pairs reach the model.
    judgments = JudgmentCache.from_snapshot(run.snapshot)
    llm_client = judgments.wrap(llm_client)

    match_memory = (
        MatchMemory.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    match_cfg = build_match_cfg(cfg, work_dir, match_memory)
    _stage("matching")
    # R4 advisory read: a receipt another run has already settled is out of
    # the candidate pool before the matcher sees it -- it cannot settle a
    # second charge here. Advisory because it races (the authoritative
    # re-check runs inside the commit lock below); keyed on the receipt's
    # HOME run, so a run's own claims never gate its own re-match. The
    # receipt itself stays in the snapshot pool and surfaces as unmatched,
    # with the view naming who settled it.
    foreign_claims = {
        doc: c
        for doc, c in store.get_claims_on_receipts(run.run_id).items()
        if c["claimed_by_run_id"] != run.run_id
    }
    pool = (
        [r for r in receipts if r.document_id not in foreign_claims]
        if foreign_claims else receipts
    )
    # Item 56 (owner ruling 2026-09-11): an invoice and its receipt for one
    # purchase are ONE candidate. Without this the matcher sees two
    # indistinguishable documents for one charge and files the pairing as
    # ambiguous, which in August was 23 of 31 receipts and a reviewer
    # picking between two copies of the same document a dozen times. The
    # suppressed copies rejoin `unmatched_receipts` below, keeping the
    # reconciliation guarantee and their duplicate markers; a group the
    # reviewer ruled "not a duplicate" (`ignore`) is never collapsed.
    # Item 74: the ladder decides each group first (identical bytes, one
    # document number, a page printing the other's number, two numbers, two
    # cards, vendor + date), and only a `copy` verdict collapses.
    pool_before_collapse = pool
    pool, collapsed, dup_decisions = duplicate_pool(
        run, pool, dup_resolutions
    )
    receipt_digest_map = receipt_digests(run, receipts)
    # R4b (item 38 ruling 3): the pool spans trips. Receipts from trips
    # overlapping this month's charge span join the candidate set --
    # already excluding anything another run settled (the same advisory
    # read, applied at the source). The borrowed list is empty on every
    # month while no trip overlaps, and the match input is then the same
    # object as before.
    borrowed, borrowed_origins = trip_pool_for_month(
        store, run, transactions,
        own_doc_ids={r.document_id for r in receipts},
    )
    # Item 61: and it spans the ADJACENT company months. A receipt printed
    # on the last day of a month is filed in THAT month while its charge
    # posts on the 1st, inside this statement's period; the neighbours'
    # receipts whose dates fall in this period join the same borrowed set,
    # so everything downstream (the claims re-check, the snapshot copies,
    # the view) treats both borrow kinds identically. Empty on a month with
    # no neighbouring batch, and the match input is then unchanged.
    adjacent, adjacent_origins = adjacent_pool_for_month(
        store, run, transactions,
        own_doc_ids=(
            {r.document_id for r in receipts} | set(borrowed_origins)
        ),
    )
    if adjacent:
        borrowed = [*borrowed, *adjacent]
        borrowed_origins = {**borrowed_origins, **adjacent_origins}
    match_input = [*pool, *borrowed] if borrowed else pool
    outcome = match_month(transactions, match_input, match_cfg)
    # Item 74, rung 7, once per re-match: a copy set aside while its own
    # exact charge sits unmatched (and its kept twin settled another) is two
    # purchases. Restore those groups and match ONCE more; nothing checks
    # again, so the month cannot oscillate.
    statement_restored, pool, collapsed = duplicate_statement_pass(
        pool_before_collapse, dup_decisions, collapsed, transactions,
        outcome, match_cfg,
    )
    if statement_restored:
        match_input = [*pool, *borrowed] if borrowed else pool
        outcome = match_month(transactions, match_input, match_cfg)

    _stage("judging")
    tx_by_id = {t.transaction_id: t for t in transactions}
    rec_by_id = {r.document_id: r for r in receipts}
    for _br in borrowed:
        rec_by_id.setdefault(_br.document_id, _br)
    _apply_judgment(
        outcome, tx_by_id, rec_by_id, llm_client,
        suggest_floor=(match_cfg or MatchingConfig()).fx_judgment_suggest_floor,
        cfg=match_cfg or MatchingConfig(),  # item 131: the band a rejection keeps
    )
    _apply_ambiguous_judgment(outcome, tx_by_id, rec_by_id, llm_client)
    _apply_unmatched_judgment(
        outcome, transactions, match_input, llm_client,
        match_cfg or MatchingConfig(), cfg,
    )
    # Excluded receipts still belong to this month's pool and its totals;
    # they are unmatched HERE because they are settled elsewhere.
    if foreign_claims or collapsed:
        _in_pool = {r.document_id for r in receipts}
        _have = set(outcome.unmatched_receipts)
        outcome.unmatched_receipts.extend(
            d for d in (*foreign_claims, *sorted(collapsed))
            if d in _in_pool and d not in _have
        )
    # A borrowed receipt the matcher did not consume simply stays in its
    # trip: it is not one of this month's unmatched receipts, and nothing
    # about it persists here. Only borrowed receipts an outcome pairing
    # references ride the snapshot (copies, for rendering), with their
    # origins beside them for the claims protocol and the view.
    if borrowed:
        _borrowed_ids = set(borrowed_origins)
        outcome.unmatched_receipts[:] = [
            d for d in outcome.unmatched_receipts if d not in _borrowed_ids
        ]

    learned = (
        MerchantCategoryLookup.from_db_path(learning_db_path)
        if learning_db_path is not None else None
    )
    try:
        _, account_labels, _scope = _resolve_categorizer_chart(
            cfg, work_dir, None, {}
        )
    except Exception:  # noqa: BLE001 - labels degrade, attach never breaks
        account_labels = None
    charge_categorizations = categorize_charges(
        outcome,
        transactions,
        client=llm_client,
        chart_of_accounts=account_labels,
        learned=learned,
        # Note item M1: a receiptless charge takes its merchant's default
        # category from the same registry the month's receipts consult.
        registry=MerchantRegistry.from_settings(store.get_settings()),
        entity_orgs=cfg.get(GL_ENTITY_ORGS_KEY),
    )

    _stage("saving")
    all_issues = list(parse_errors) + [
        (i.file_name, i.line_number, i.message, i.severity)
        for i in statement_issues
    ]
    base = snapshot_to_dict(transactions, receipts, outcome, all_issues)

    # The match ran for minutes on a row read before it started; commit
    # under the SAME lock the other batch writers hold, against a fresh
    # re-read (adversarial review B1/C1: an unlocked final write erased a
    # mid-match card assignment / refresh, and a racing refresh erased the
    # attach). Non-owned keys come from the FRESH row: the expense config
    # block (cards / hints / accounts an assignment wrote mid-match) and
    # every snapshot key outside the matcher's own four. Receipts mailed
    # in mid-match join the pool as unmatched rather than vanishing.
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "this batch was deleted while it reconciled",
                code="batch_deleted",
            )
        committing = {t.transaction_id for t in transactions}
        if replace_statements is not None:
            # The re-read replaces ids on purpose, so the never-drop check
            # moves up one level: the set of UPLOADS this commit rebuilt has
            # to be exactly the set the month holds right now. An upload
            # that landed while the files were being re-read is not in the
            # rebuilt set, and committing would erase its charges.
            fresh_files = [
                str(e.get("file") or "") for e in month_statements(fresh)
            ]
            rebuilt_files = [
                str(e.get("file") or "") for e in replace_statements
            ]
            if fresh_files != rebuilt_files:
                raise RunInputError(
                    "another statement upload landed on this month while its "
                    "files were re-read; nothing was written, so no charge "
                    "was lost. Run the re-read again.",
                    code="concurrent_statement_upload",
                )
            if rekey_decisions:
                store.rekey_decisions(run.run_id, rekey_decisions)
        else:
            dropped = [
                str(td.get("transaction_id"))
                for td in (fresh.snapshot or {}).get("transactions") or []
                if td.get("transaction_id") not in committing
            ]
            if dropped:
                raise RunInputError(
                    f"another statement upload added {len(dropped)} charge(s) "
                    "to this month while it reconciled; nothing was written, "
                    "so no charge was lost. Upload again.",
                    code="concurrent_statement_upload",
                    n_charges=len(dropped),
                )
        fresh_cfg = fresh.config or {}
        if fresh_cfg.get("expense") is not None:
            cfg = {**cfg, "expense": fresh_cfg["expense"]}
        known_ids = {r.document_id for r in receipts0}
        extra = [
            rd
            for rd in (fresh.snapshot or {}).get("receipts") or []
            if rd.get("document_id") and rd["document_id"] not in known_ids
        ]
        if extra:
            base["receipts"] = list(base.get("receipts") or []) + extra
            out_dict = dict(base.get("outcome") or {})
            out_dict["unmatched_receipts"] = list(
                out_dict.get("unmatched_receipts") or []
            ) + [rd["document_id"] for rd in extra]
            base["outcome"] = out_dict
            receipts = receipts + [
                r
                for r in snapshot_from_dict(fresh.snapshot)[1]
                if r.document_id in {rd["document_id"] for rd in extra}
            ]
            outcome.unmatched_receipts.extend(rd["document_id"] for rd in extra)
        # R4 commit-time re-check, the authoritative half of the claims
        # protocol: the advisory read above ran minutes ago, and a reviewer
        # confirm in another run can settle one of our paired receipts in
        # between. Re-read the claims FRESH under the same lock the commit
        # holds and downgrade any pairing whose receipt is now another
        # run's -- the charge goes to unmatched, nothing is lost, and the
        # next re-match sees the claim at the advisory read.
        pool_doc_ids = {r.document_id for r in receipts}

        def _src(doc: str) -> str:
            hit = borrowed_origins.get(doc)
            if hit is not None:
                return str(hit["run_id"])
            return receipt_source_run(run, doc)

        pair_docs = {
            m.document_id
            for m in (
                *outcome.matches,
                *outcome.judgment_required,
                *outcome.ambiguous,
            )
        }
        claim_sources = {_src(d) for d in pair_docs}
        claim_sources.add(run.run_id)
        claims_now: dict[str, dict] = {}
        for src in sorted(claim_sources):
            for doc, c in store.get_claims_on_receipts(src).items():
                if c["claimed_by_run_id"] != run.run_id:
                    claims_now[doc] = c
        downgraded = False
        lost_docs = pair_docs & set(claims_now)
        if lost_docs:
            downgraded = _downgrade_claimed_pairs(
                outcome, lost_docs, pool_doc_ids
            )
        # Record this run's own settlements: deterministic matches overlaid
        # with the reviewer's standing verdicts. One receipt, one claim;
        # a refused insert is the same race as above, downgraded the same
        # way, so the table and the committed snapshot cannot disagree.
        settled = effective_settlements(
            {m.transaction_id: m.document_id for m in outcome.matches},
            store.get_decisions(run.run_id),
        )
        triples: list[tuple[str, str, str]] = []
        seen_claim_keys: set[tuple[str, str]] = set()
        for tx_id in sorted(settled):
            doc = settled[tx_id]
            key = (_src(doc), doc)
            if key in seen_claim_keys:
                continue
            seen_claim_keys.add(key)
            triples.append((key[0], doc, tx_id))
        conflicts = store.replace_claims_by_run(
            run.run_id, triples, now_iso or datetime.now().isoformat()
        )
        if conflicts:
            downgraded = _downgrade_claimed_pairs(
                outcome, {doc for _, doc, _ in conflicts}, pool_doc_ids
            ) or downgraded
        if downgraded:
            base["outcome"] = outcome_to_dict(outcome)
        # Borrowed trip receipts the FINAL outcome references ride the
        # snapshot as copies with their origins, so the workbench renders
        # a cross-batch pairing without a store join. Recomputed after the
        # downgrades above so a stripped pairing leaves nothing behind;
        # both keys are absent whenever no pairing borrows.
        referenced = (
            {
                m.document_id
                for m in (
                    *outcome.matches,
                    *outcome.judgment_required,
                    *outcome.ambiguous,
                )
            }
            # A reviewer-confirmed pick holds its receipt even when this
            # pass's matcher no longer proposes it; keep its copy too.
            | set(settled.values())
        ) & set(borrowed_origins)
        new_snapshot = {**dict(fresh.snapshot), **base}
        if referenced:
            new_snapshot[BORROWED_RECEIPTS_KEY] = [
                receipt_to_dict(r) for r in borrowed
                if r.document_id in referenced
            ]
            new_snapshot[RECEIPT_SOURCES_KEY] = {
                doc: borrowed_origins[doc] for doc in sorted(referenced)
            }
        else:
            new_snapshot.pop(BORROWED_RECEIPTS_KEY, None)
            new_snapshot.pop(RECEIPT_SOURCES_KEY, None)
        # Preserve what extraction read, BEFORE this commit replaces the
        # receipt block with the baked pool. `receipts0` is the snapshot as
        # this match read it and `extra` arrived while it ran; both are
        # pristine for any document the baseline does not already cover, and
        # first-write-wins keeps an earlier bake's capture authoritative.
        new_snapshot[EXTRACTED_RECEIPTS_KEY] = _extended_baseline(
            (fresh.snapshot or {}).get(EXTRACTED_RECEIPTS_KEY),
            [receipt_to_dict(r) for r in receipts0] + list(extra),
        )
        # Item 74: the byte digests the ladder's first rung read (merged over
        # the fresh row, so a receipt added mid-match keeps the digest its add
        # wrote), and the groups this match's statement check restored, which
        # the views read as `basis: "statement"`. Rewritten on every re-match.
        new_snapshot[RECEIPT_DIGESTS_KEY] = {
            **((fresh.snapshot or {}).get(RECEIPT_DIGESTS_KEY) or {}),
            **receipt_digest_map,
        }
        if statement_restored:
            new_snapshot[DUPLICATE_STATEMENT_KEY] = sorted(statement_restored)
        else:
            new_snapshot.pop(DUPLICATE_STATEMENT_KEY, None)
        if charge_categorizations:
            new_snapshot["charge_categorizations"] = {
                tx_id: categorization_to_dict(c)
                for tx_id, c in charge_categorizations.items()
            }
        else:
            new_snapshot.pop("charge_categorizations", None)
        # Judgments MERGE onto the fresh row rather than replacing it,
        # for the same reason the receipt pool does above: this match ran
        # for minutes on a row read before it started, and a re-match that
        # committed meanwhile paid for entries of its own. Overwriting
        # would throw those away and re-buy them later. Ours win on a key
        # collision, which is a no-op — the same key means the same call.
        merged_judgments = dict(
            (fresh.snapshot or {}).get("llm_judgments") or {}
        )
        merged_judgments.update(judgments.to_dict())
        if merged_judgments:
            new_snapshot["llm_judgments"] = merged_judgments
        else:
            new_snapshot.pop("llm_judgments", None)
        # Record the upload against the entries the month holds RIGHT NOW,
        # not against the ones this call read minutes ago: the advisory's
        # whole job is to compare this file with what is already loaded.
        statement_advice = None
        if replace_statements is not None:
            # The re-read rebuilt every upload the month holds; replace the
            # whole block and its anchors, judging each entry's advisory
            # against the entries before it exactly as the appends did.
            rebuilt_entries: list[dict] = []
            rebuilt_anchors: dict[str, dict] = {}
            rebuilt_origins: dict[str, dict] = {}
            for raw in replace_statements:
                entry = dict(raw)
                anchors = entry.pop("_anchors", {})
                origins = entry.pop("_origins", {})
                entry["advisory"] = statement_advisory(rebuilt_entries, entry)
                entry["advisory_detail"] = detail_of(entry["advisory"])
                rebuilt_entries.append(entry)
                for anchor_key in _anchor_keys(entry):
                    rebuilt_anchors[anchor_key] = anchors
                # Note item T3: keyed by the file name alone. The anchors
                # are keyed by id as well because the writeback addresses
                # an upload by id; this record is only ever walked through
                # `statements[]`, where every entry has its file name.
                rebuilt_origins[str(entry.get("file") or "")] = origins
            new_snapshot[STATEMENTS_KEY] = rebuilt_entries
            new_snapshot[STATEMENT_ANCHORS_KEY] = rebuilt_anchors
            new_snapshot[STATEMENT_ORIGINS_KEY] = rebuilt_origins
        elif statement_entry is not None:
            prior = list((fresh.snapshot or {}).get(STATEMENTS_KEY) or [])
            entry = dict(statement_entry)
            anchors = entry.pop("_anchors", {})
            origins = entry.pop("_origins", {})
            statement_advice = statement_advisory(prior, entry)
            entry["advisory"] = statement_advice
            entry["advisory_detail"] = detail_of(statement_advice)
            new_snapshot[STATEMENTS_KEY] = [*prior, entry]
            new_snapshot[STATEMENT_ANCHORS_KEY] = {
                **((fresh.snapshot or {}).get(STATEMENT_ANCHORS_KEY) or {}),
                # Keyed by file AND by `statement_id` (note item T2).
                **{anchor_key: anchors for anchor_key in _anchor_keys(entry)},
            }
            # Note item T3: what this upload printed, keyed by its file
            # name (see the re-read branch for why the id is not a key).
            new_snapshot[STATEMENT_ORIGINS_KEY] = {
                **((fresh.snapshot or {}).get(STATEMENT_ORIGINS_KEY) or {}),
                str(entry.get("file") or ""): origins,
            }
        n_tx = len(transactions)
        # Item 103: what this commit stores, logs and returns is the
        # EFFECTIVE count -- the reviewer's verdicts over the outcome, which
        # is what the page and the months list show. The raw outcome can
        # name one receipt on two charges (a pending pick holds it; the
        # second charge falls to unmatched), and counting that pairing was
        # how a re-match event reported one more matched charge than the
        # workbench it had just rebuilt.
        committed = effective_charge_counts(
            transactions, outcome, receipts, store.get_decisions(run.run_id)
        )
        n_review = committed["n_review"]
        counts = count_parse_issues(all_issues)
        summary = {
            **fresh.summary,
            "n_transactions": n_tx,
            "n_receipts": len(receipts),
            "n_expenses": len(receipts),
            "n_matched": committed["n_matched"],
            "n_review": n_review,
            "n_unmatched_tx": committed["n_unmatched_tx"],
            "n_refunds": committed["n_refunds"],
            "n_unmatched_rec": len(outcome.unmatched_receipts),
            "n_parse_errors": counts["errors"],
            "n_parse_notes": counts["notes"],
            "match_rate": (
                round(committed["n_matched"] / n_tx * 100, 1) if n_tx else 0.0
            ),
            "n_receipts_matched": max(
                len(receipts) - len(outcome.unmatched_receipts), 0
            ),
            "receipt_match_rate": (
                round(
                    (len(receipts) - len(outcome.unmatched_receipts))
                    / len(receipts) * 100, 1
                )
                if receipts else 0.0
            ),
            "llm_cost_usd": (
                str(tracker.total_cost_usd) if tracker else
                fresh.summary.get("llm_cost_usd", "0")
            ),
            "has_statement": True,
        }
        summary["setup_advisories"] = _setup_advisories(
            cfg, transactions, receipts,
            has_coa=bool(cfg.get("coa_validation")),
        )
        # Item 113: this commit pays the owed re-match it READ. A change that
        # landed while it ran wrote a new mark id, and that debt stays.
        owed = rematch_pending(fresh)
        read = rematch_pending(run)
        if owed is not None and read is not None and owed.get("id") == read.get("id"):
            new_snapshot.pop(REMATCH_PENDING_KEY, None)
        # Item 58: one event per commit, appended to the FRESH row's log so
        # a re-match that committed while this one ran keeps its entry.
        new_snapshot[REMATCH_LOG_KEY] = append_rematch_event(
            (fresh.snapshot or {}).get(REMATCH_LOG_KEY),
            {
                "event_id": uuid.uuid4().hex[:12],
                # The COMMIT clock, in the app's own format, never the
                # caller's `now_iso` (an upload's timestamp, or empty on the
                # incremental paths): events from every path sort together.
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "trigger": str(trigger or ""),
                "n_transactions": n_tx,
                "n_matched": committed["n_matched"],
                "n_review": n_review,
                "n_unmatched_tx": committed["n_unmatched_tx"],
                "n_receipts": len(receipts),
                "n_unmatched_rec": len(outcome.unmatched_receipts),
                "match_rate": summary["match_rate"],
            },
        )
        store.update_run_config(run.run_id, cfg)
        store.update_run_snapshot(run.run_id, new_snapshot)
        store.update_run_summary(run.run_id, summary)

    # Matching is entity-scoped, so a card/entity mapping gap yields a
    # silent 0-match month. Judge against the POOL's actual entities
    # (post-bake, R3: a batch can legitimately mix entities), not just
    # the batch-level default — an entity-less batch has no default and
    # the old check never fired for it. Loud, never silent.
    entity_mismatch = None
    pool_entities = {
        e for e in ((r.legal_entity_id or "").strip() for r in receipts) if e
    }
    stmt_entity = (entity or "").strip()
    if receipts and stmt_entity and stmt_entity.lower() not in {
        e.lower() for e in pool_entities
    }:
        described = (
            f"this batch's expenses belong to {sorted(pool_entities)!r}"
            if pool_entities
            else "this batch's expenses have no legal entity assigned yet"
        )
        entity_mismatch = (
            f"The statement's card resolves to legal entity {stmt_entity!r} "
            f"but {described}; nothing will match across entities. Check "
            "the card / entity mapping."
        )
    # Item 76: clean exact pairs confirm themselves, judged against the
    # outcome just committed. After the lock, like every decision write. The
    # match itself is committed already, so a failure here is reported in
    # the result, never raised into the caller's success.
    try:
        self_confirm = apply_self_confirmations(store, run.run_id)
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        self_confirm = {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "n_transactions": n_tx,
        "n_matched": committed["n_matched"],
        "n_review": n_review,
        "n_unmatched_tx": committed["n_unmatched_tx"],
        "n_refunds": committed["n_refunds"],
        "entity_mismatch": entity_mismatch,
        "judgments_reused": judgments.hits,
        "judgments_new": judgments.misses,
        # None on every re-match and on an upload that folded cleanly.
        "statement_advisory": statement_advice,
        "self_confirm": self_confirm,
    }


def rematch_after_change(
    store: RunStore,
    run_id: str,
    *,
    learning_db_path: Path | None = None,
    on_stage=None,
    trigger: str = "",
) -> dict | None:
    """Re-reconcile a statement-bearing month whose inputs just changed.

    The living month (2b-2): a statement is an input stream, not a closing
    event, so the operations that used to be refused once one was attached
    -- receipts arriving, a set-aside page restored, a card assigned, master
    data refreshed -- are allowed and each is followed by this. Without it
    they would be allowed but inert: the new receipt would sit in the pool
    while the match outcome still described the month as it was before.

    Called AFTER the caller's `_BATCH_ADD_LOCK` span, never inside it:
    `rematch_month` takes that same lock to commit and it is not reentrant.
    Every incremental path goes through this one function rather than
    growing its own copy, the same reason `rematch_month` itself exists.

    Returns None (and costs nothing) when there is no statement to match
    against, which is the ordinary pre-attach case and every non-expense
    run. Re-reads the row rather than trusting the caller's: the caller
    read its copy before it made its change.
    """
    fresh = store.get_run(run_id)
    if fresh is None or not has_statement(fresh):
        return None
    try:
        transactions, _, _, _ = snapshot_from_dict(fresh.snapshot)
    except Exception as exc:  # noqa: BLE001 - see the contract below
        error = f"{type(exc).__name__}: {exc}"
        _record_rematch_failure(store, run_id, trigger, error)
        return {"error": error}
    if not transactions:
        return None
    # Item 113: owe the re-match on the month before running it, and run it
    # on the row that carries the mark, so its commit can clear exactly it.
    try:
        _ensure_rematch_pending(store, run_id, trigger)
        fresh = store.get_run(run_id) or fresh
    except Exception:  # noqa: BLE001 - the mark is a safety net, not a gate
        pass
    cfg = fresh.config or {}
    return _rematch_or_error(
        store,
        fresh,
        transactions=transactions,
        cfg=cfg,
        # The statement's own entity, recovered from the config the attach
        # wrote, so the cross-entity "nothing will match" advisory keeps
        # firing on a re-match. That advisory earns its keep exactly here:
        # a card assignment is what most often leaves a month unable to
        # match anything (Cards R3 adversarial review F1).
        entity=str((cfg.get("statement") or {}).get("legal_entity_id") or ""),
        learning_db_path=learning_db_path,
        on_stage=on_stage,
        trigger=trigger,
    )


def _rematch_or_error(*args, **kwargs) -> dict:
    """`rematch_month`, with a failure reported rather than raised.

    The caller's change is ALREADY COMMITTED when this runs -- the receipt
    is in the pool, the card assignment is in the config -- because the
    re-match deliberately happens after the lock span that wrote it. So a
    re-match that throws must not make the caller look like it failed: a
    mailed receipt would be marked `held_failed` and replayed despite
    having landed, and an OpenAI outage would do that to every receipt
    Dirk sends.

    Not silent either. The error rides back in the result (`rematch`), so
    the job and the log say the month did not re-reconcile, and the next
    trigger retries against a pool that already holds the receipt. The
    month's own match state is simply the one it had before, which is a
    truthful stale rather than a wrong fresh.
    """
    try:
        return rematch_month(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        error = f"{type(exc).__name__}: {exc}"
        # Item 113: the mail and drop callers discard the result, so the
        # failure also lands on the month's owed-re-match mark, where the
        # operator state, the notifier and the next arrival see it.
        store = args[0] if args else kwargs.get("store")
        run = args[1] if len(args) > 1 else kwargs.get("run")
        if store is not None and run is not None:
            _record_rematch_failure(
                store, run.run_id, str(kwargs.get("trigger") or ""), error
            )
        return {"error": error}


# ---------------------------------------------------------------------------
# The adjacent-month pool (backlog item 61)
# ---------------------------------------------------------------------------
# A receipt is routed to a batch by the month PRINTED ON IT, while a charge
# lands in the statement that BILLED it, and the two boundaries do not line
# up: August's workbook opens on 07-31 and July's on 06-30, so a subscription
# invoiced on the last day of a month posts on the 1st of the next statement
# and its receipt is already filed one batch away. Live on 2026-09-15: August
# holds two Google receipts dated 08-31 (71.64 and 75.09) whose charges post
# on 09-01, while August's own 08-01 Google 71.64 charge sits unmatched with
# no candidate at all.
#
# So the month's candidate pool spans its NEIGHBOURS the way it already spans
# trips (R4b): same borrowed_receipts / receipt_sources keys, same claims
# arbitration, same one-receipt-one-charge guarantee. Eligibility is the
# statement's OWN period rather than a calendar month, because the period is
# the thing that actually decides whether a charge could be on this workbook.

ADJACENT_BORROW_KIND = "adjacent"
# Item 112: the re-match a neighbouring month owes when a receipt dated
# inside its statement period lands in this month (`rematch_log` trigger).
ADJACENT_REMATCH_TRIGGER = "adjacent_receipts"
# Only reached by a month that has no statement yet, where there are no
# charges to derive a period from and nothing to match either. The calendar
# month plus this margin is the widest window such a month could plausibly
# bill, and it keeps the helper answerable instead of undefined.
ADJACENT_FALLBACK_DAYS = 3


def adjacent_months(ym: tuple[int, int]) -> set[tuple[int, int]]:
    """The calendar months either side of `(year, month)`: the one definition
    of "neighbour" the borrow (item 61) and the arrival trigger (item 112)
    share."""
    year, month = ym
    return {
        (year - 1, 12) if month == 1 else (year, month - 1),
        (year + 1, 1) if month == 12 else (year, month + 1),
    }


def statement_period_for_month(
    run: RunRow, transactions: list
) -> tuple[date, date] | None:
    """The span of dates this run's statement actually covers.

    Derived from the run's OWN charges (min..max transaction date), which is
    the only source that knows where the workbook was cut: Chase opens
    August on 07-31 and July on 06-30, and no calendar rule predicts that.
    The label's calendar month widened by `ADJACENT_FALLBACK_DAYS` is the
    fallback for a month with no statement yet, and None when the label does
    not name a month either."""
    dates = [t.transaction_date for t in transactions if t.transaction_date]
    if dates:
        return min(dates), max(dates)
    ym = month_from_label(run.label)
    if ym is None:
        return None
    year, month = ym
    first = date(year, month, 1)
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (
        first - timedelta(days=ADJACENT_FALLBACK_DAYS),
        nxt - timedelta(days=1) + timedelta(days=ADJACENT_FALLBACK_DAYS),
    )


def adjacent_pool_for_month(
    store: RunStore,
    run: RunRow,
    transactions: list,
    own_doc_ids: set[str],
) -> tuple[list, dict[str, dict]]:
    """The receipts this month's statement may settle from the company
    months either side of it (item 61). Returns `(receipts, origins)`;
    `origins` maps each borrowed document to
    `{run_id, label, kind: "adjacent"}`.

    Neighbours are decided by LABEL (`month_from_label`), previous and next,
    so "August 2026" reaches "July 2026" and "September 2026" and nothing
    else; a batch whose label names no month neither borrows nor lends.
    Eligibility is the statement period above: a receipt joins only when its
    printed date falls inside the span this run's charges actually cover,
    which is what keeps the borrow narrow rather than a second month's worth
    of noise.

    The exclusions are `trip_pool_for_month`'s, for the same reasons: a trip
    batch is not a neighbour, a receipt another run has already claimed is
    out (the advisory read of the cross-batch never-settle guard), a
    confirmed private expense is not company-card money, and a document id
    this month's own pool already holds is dropped. That last one bites
    harder here than it does on trips, because neighbouring months are
    ingested the same way and collide by construction: July and August share
    four ids today, all `NNNN__rendered-body.pdf`. The colliding receipt
    simply is not borrowed; offering two receipts under one id would corrupt
    the matcher's consumption set and the view's lookup."""
    if is_trip_batch(run):
        return [], {}
    ym = month_from_label(run.label)
    if ym is None:
        return [], {}
    period = statement_period_for_month(run, transactions)
    if period is None:
        return [], {}
    lo, hi = period
    wanted = adjacent_months(ym)
    neighbours = []
    for other in store.list_runs():
        if other.run_id == run.run_id:
            continue
        if (other.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if is_trip_batch(other):
            continue
        oym = month_from_label(other.label)
        if oym not in wanted:
            continue
        neighbours.append((oym, str(other.run_id), other))
    # Deterministic order, so which side wins an id collision is a fact
    # rather than a store-ordering accident: the previous month first.
    neighbours.sort(key=lambda n: (n[0], n[1]))

    borrowed: list = []
    origins: dict[str, dict] = {}
    for _oym, _rid, other in neighbours:
        o_field = store.get_expense_field_overrides(other.run_id)
        o_receipts, o_kwargs = _expense_export_inputs(
            other,
            store.get_category_overrides(other.run_id),
            o_field,
            store.get_expense_edits(other.run_id),
            store.get_duplicate_resolutions(other.run_id),
        )
        private = _private_reimbursements(o_field)
        claims = store.get_claims_on_receipts(other.run_id)
        entity_by_doc = o_kwargs.get("entity_by_doc") or {}
        for r in o_receipts:
            doc = r.document_id
            if doc in own_doc_ids or doc in origins or doc in private:
                continue
            if r.detected_date is None or not (lo <= r.detected_date <= hi):
                continue
            c = claims.get(doc)
            if c is not None and c["claimed_by_run_id"] != run.run_id:
                continue
            ent = entity_by_doc.get(doc)
            if ent and ent != r.legal_entity_id:
                r = replace(r, legal_entity_id=ent)
            borrowed.append(r)
            origins[doc] = {
                "run_id": other.run_id,
                "label": other.label or other.run_id,
                "kind": ADJACENT_BORROW_KIND,
            }
    return borrowed, origins


# Item 112 (2026-09-17 audit draft #110): the borrow above is read only when
# the BORROWING month re-matches. A receipt dated 07-31 that lands in July
# after August's last re-match waited in July for an unrelated August event,
# while a receipt joining a trip already re-matched every month the trip
# spans (`rematch_months_after_trip_change`). An arrival now owes a re-match
# to each neighbouring month whose loaded statement period covers the
# receipt's date: owed inside the arrival's own lock span (item 113's mark,
# so a restart before the neighbour's turn cannot lose it), paid after the
# lock through `rematch_after_change`, whose failure lands on that mark.


def neighbour_months_covering(
    store: RunStore,
    run: RunRow,
    dates: list,
    *,
    exclude: set[str] | tuple = (),
) -> list[RunRow]:
    """The company months either side of `run` (by label, as
    `adjacent_pool_for_month` decides neighbours) holding a statement whose
    period (`statement_period_for_month`) covers any of `dates`, previous
    month first. A trip batch has no neighbours: its receipts reach the
    months through the trip trigger. A neighbour whose snapshot cannot be
    parsed is included, so its re-match records why it cannot run."""
    if is_trip_batch(run) or not dates:
        return []
    ym = month_from_label(run.label)
    if ym is None:
        return []
    wanted = adjacent_months(ym)
    skip = {run.run_id, *exclude}
    found: list[tuple] = []
    for other in store.list_runs():
        if other.run_id in skip:
            continue
        if (other.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if is_trip_batch(other) or not has_statement(other):
            continue
        oym = month_from_label(other.label)
        if oym not in wanted:
            continue
        try:
            transactions = snapshot_from_dict(other.snapshot)[0]
        except Exception:  # noqa: BLE001 - owed; its re-match reports the error
            found.append((oym, str(other.run_id), other))
            continue
        if not transactions:
            continue
        period = statement_period_for_month(other, transactions)
        if period is None:
            continue
        lo, hi = period
        if any(lo <= d <= hi for d in dates):
            found.append((oym, str(other.run_id), other))
    found.sort(key=lambda n: (n[0], n[1]))
    return [other for _oym, _rid, other in found]


def _owe_neighbour_rematches_locked(
    store: RunStore,
    run: RunRow,
    document_ids: list[str],
    *,
    exclude: set[str] | tuple = (),
) -> list[str]:
    """Write the owed-re-match mark on every neighbouring month the receipts
    `document_ids` (just added to `run`) fall inside, and return their ids.
    Caller holds `_BATCH_ADD_LOCK`. Dates are the rows' effective dates (a
    typed date wins), read from the row as it stands after the add."""
    if not document_ids:
        return []
    fresh = store.get_run(run.run_id)
    if fresh is None:
        return []
    wanted = set(document_ids)
    rows = apply_expense_edits(
        baseline_receipts(fresh),
        store.get_expense_field_overrides(fresh.run_id),
        store.get_expense_edits(fresh.run_id),
    )
    dates = [
        r.detected_date for r in rows
        if r.document_id in wanted and r.detected_date is not None
    ]
    owed: list[str] = []
    for other in neighbour_months_covering(store, fresh, dates, exclude=exclude):
        # The row as it stands now (the lock is held), never the listing's copy.
        current = store.get_run(other.run_id)
        if current is None:
            continue
        snapshot = dict(current.snapshot or {})
        snapshot[REMATCH_PENDING_KEY] = rematch_pending_mark(
            snapshot, ADJACENT_REMATCH_TRIGGER
        )
        store.update_run_snapshot(other.run_id, snapshot)
        owed.append(other.run_id)
    return owed


def rematch_neighbour_months(
    store: RunStore,
    run_ids: list[str],
    *,
    learning_db_path: Path | None = None,
) -> list[dict]:
    """Pay the neighbours' owed re-matches, outside every lock. Never raises:
    the arrival that owed them is committed, and a failure stays on the
    neighbour's mark for the operator state, the notifier and the retry."""
    results: list[dict] = []
    for run_id in run_ids:
        try:
            rematch = rematch_after_change(
                store, run_id, learning_db_path=learning_db_path,
                trigger=ADJACENT_REMATCH_TRIGGER,
            )
        except Exception as exc:  # noqa: BLE001 - recorded on the mark
            error = f"{type(exc).__name__}: {exc}"
            _record_rematch_failure(store, run_id, ADJACENT_REMATCH_TRIGGER, error)
            rematch = {"error": error}
        if rematch is not None:
            results.append({"run_id": run_id, **rematch})
    return results


def relabel_borrowed_sources(
    store: RunStore, lender_run_id: str, label: str
) -> list[str]:
    """Carry a lender's new label onto every month that borrowed from it,
    and return those months (R4.1).

    A borrowing month records `{run_id, trip_id, label}` in its snapshot at
    BORROW time, and `rows[].settled_by` renders that copy. So renaming a
    trip moved its batch label and left every borrowing month's badge
    naming the old one until that month happened to re-match. Rewriting the
    stored copies keeps the snapshot self-consistent, which is how the rest
    of the month's record already works, and costs one write per borrowing
    month on an operation that happens rarely."""
    touched: list[str] = []
    with _BATCH_ADD_LOCK:
        for run in store.list_runs():
            snapshot = run.snapshot or {}
            sources = snapshot.get("receipt_sources") or {}
            if not isinstance(sources, dict):
                continue
            hits = [
                doc for doc, entry in sources.items()
                if isinstance(entry, dict)
                and str(entry.get("run_id") or "") == str(lender_run_id)
                and str(entry.get("label") or "") != str(label)
            ]
            if not hits:
                continue
            fresh = store.get_run(run.run_id)
            if fresh is None:
                continue
            snap = dict(fresh.snapshot or {})
            live = dict(snap.get("receipt_sources") or {})
            for doc in hits:
                entry = live.get(doc)
                if isinstance(entry, dict):
                    live[doc] = {**entry, "label": label}
            snap["receipt_sources"] = live
            store.update_run_snapshot(run.run_id, snap)
            touched.append(run.run_id)
    return touched


def borrowed_source_view(entry: object) -> dict | None:
    """One `receipt_sources` entry as the SPA reads it, or None.

    The map holds both borrow kinds: a trip entry carries `trip_id`, an
    adjacent-month entry carries `kind: "adjacent"`. Each key is emitted
    only when the entry has it, so a trip's object is exactly the
    `{run_id, trip_id, label}` the workbench already renders and an
    adjacent one is `{run_id, label, kind}`. Absent, never null."""
    if not isinstance(entry, dict):
        return None
    out: dict = {"run_id": entry.get("run_id")}
    if entry.get("trip_id"):
        out["trip_id"] = entry.get("trip_id")
    out["label"] = entry.get("label")
    if entry.get("kind"):
        out["kind"] = entry.get("kind")
    return out
# ── Settled outside the card (backlog item 62) ──────────────────────────
# Some receipts never post to a card at all. July 2026 holds a Redis
# invoice for 13,200.00 USD, a Konsultancy Finance one for 15,972.00 EUR
# and a 360Crossmedia one for 900.00 EUR; every one was paid by bank
# transfer, so no card statement will ever settle them. They sat in
# `unmatched_receipts` and in the pool counts with no disposition that
# could ever retire them, which is the whole of backlog item 62.
#
# This is that disposition, and it is bookkeeping rather than matching.
# The receipt stays in the month, in the snapshot, in the expense grid and
# in the month report, behind a caption naming the tender (owner ruling
# 2026-09-15: a bank transfer is real company spend whose evidence is the
# invoice, and dropping the row would hide that spend from the
# accountant). What it leaves is the RECONCILIATION side: the unmatched
# list, the pool counts, and month health's exact-pair scan.
#
# Applied at VIEW time from a snapshot key, never by re-matching, so the
# disposition costs no model call and the undo is immediate. It is scoped
# to receipts the EFFECTIVE outcome leaves unmatched, so a receipt that
# holds a charge renders as the match it is instead of vanishing from both
# sides of the screen.

SETTLED_OUTSIDE_KEY = "settled_outside"
SETTLED_OUTSIDE_HOWS = ("bank_transfer", "cash", "paypal", "other")
SETTLED_OUTSIDE_NOTE_MAX = 500

# What the month report prints under the expense number. English here
# because the PDF is English throughout; the SPA localizes from `how`.
SETTLED_OUTSIDE_CAPTION = {
    "bank_transfer": "paid by bank transfer",
    "cash": "paid in cash",
    "paypal": "paid by PayPal",
    "other": "settled outside the card",
}

# A mode that names a card wins outright: "Electronic Funds Transfer
# ...2838" is a transfer that names the card it posted to, so it suggests
# nothing. Four consecutive digits is the card-tail shape ("...2838",
# "x3876", "124631******3876"); an amount like "15.00" never matches it.
_CARD_TOKEN_RE = re.compile(
    r"visa|master|maestro|amex|american\s+express|discover|elo\b|"
    r"card|karte|cart[aã]o|cr[eé]dito|d[eé]bito|debit|credit|\d{4}",
    re.IGNORECASE,
)

# Tenders a card statement will never carry. Word-bounded, so "cashback"
# is not cash and "PAYE" is not PayPal.
_TENDER_PATTERNS = (
    ("bank_transfer", re.compile(
        r"\b(?:bank|wire|electronic\s+funds?)\s+transfers?\b"
        r"|\btransfer[eê]ncia\b|\btransferencia\b|\b[uü]berweisung\b"
        r"|\bsepa\b|\btef\b|\bach\b|\bvirement\b|\bbonifico\b",
        re.IGNORECASE)),
    ("paypal", re.compile(r"\bpay\s?pal\b", re.IGNORECASE)),
    ("cash", re.compile(
        r"\bcash\b|\bdinheiro\b|\besp[eè]ces\b|\bcontanti\b|\bbargeld\b"
        r"|\bem\s+esp[eé]cie\b",
        re.IGNORECASE)),
)


def settled_outside_map(snapshot: dict | None) -> dict[str, dict]:
    """The month's dispositions, document_id -> `{how, note, at}`.

    Absent on every month that has none, so a snapshot written before this
    key existed reads as an empty map and renders exactly as it did."""
    stored = (snapshot or {}).get(SETTLED_OUTSIDE_KEY)
    if not isinstance(stored, dict):
        return {}
    out: dict[str, dict] = {}
    for doc_id, entry in stored.items():
        if not isinstance(entry, dict):
            continue
        how = entry.get("how")
        if how not in SETTLED_OUTSIDE_HOWS:
            continue
        out[str(doc_id)] = {
            "how": how,
            "note": str(entry.get("note") or ""),
            "at": entry.get("at"),
        }
    return out


def settled_outside_caption(how: str) -> str:
    """The month report's caption for one tender."""
    return SETTLED_OUTSIDE_CAPTION.get(how, SETTLED_OUTSIDE_CAPTION["other"])


def suggested_settled_outside(payment_mode: str | None) -> dict | None:
    """The suggestion chip for one unmatched receipt, or None.

    Reads the payment mode the scan lifted off the document (item 28) and
    names the tender when it reads as something a card statement will
    never carry. NEVER auto-applied: the reviewer confirms every one.

    Owner ruling 2026-09-15: an invoice's payment-OPTION line ("Pay $15.00
    with a bank transfer") counts as a signal, not only a statement of how
    the thing was actually paid. The honest caveat is that the one live
    instance of that wording sits on an August Lovable receipt that DID
    post to a card. The chip renders only on already-unmatched receipts
    and fires on a handful a month, so a wrong one costs a glance while a
    missing one costs a receipt stuck in the pool forever.
    """
    text = (payment_mode or "").strip()
    if not text or _CARD_TOKEN_RE.search(text):
        return None
    for how, pattern in _TENDER_PATTERNS:
        if pattern.search(text):
            return {"how": how, "evidence": text[:120]}
    return None


def _settled_outside_unmatched_ids(store: RunStore, run: RunRow) -> set[str]:
    """Which of this month's receipts the effective outcome leaves
    unmatched, read the way `build_view` reads it so the route and the
    screen cannot disagree about what is settled."""
    transactions, receipts, outcome, _pe = snapshot_from_dict(run.snapshot)
    effective = apply_decisions(
        outcome, transactions, receipts, store.get_decisions(run.run_id)
    )
    return set(effective.unmatched_receipts)


def set_receipt_settled_outside(
    store: RunStore,
    run: RunRow,
    document_id: str,
    how: str,
    note: str,
    now_iso: str,
) -> dict:
    """Mark one receipt as settled outside the card.

    Serialized under the batch-mutation lock against a FRESH re-read, the
    `rematch_month` commit shape: a mid-month add or a restore running
    concurrently must not be clobbered by a read-modify-write working from
    a stale row.

    Refuses a receipt that currently settles a charge. Rejecting that
    match frees it first; marking it here while a charge holds it would
    leave the month claiming both that a card paid it and that none did.
    """
    how = (how or "").strip().lower()
    if how not in SETTLED_OUTSIDE_HOWS:
        raise RunInputError(
            "Say how it was settled: " + ", ".join(SETTLED_OUTSIDE_HOWS) + ".",
            code="settled_outside_how_required",
            allowed=sorted(SETTLED_OUTSIDE_HOWS),
        )
    note = (note or "").strip()[:SETTLED_OUTSIDE_NOTE_MAX]
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        snapshot = dict(run.snapshot or {})
        _tx, receipts, _outcome, _pe = snapshot_from_dict(snapshot)
        if not any(r.document_id == document_id for r in receipts):
            raise RunInputError(
                "That receipt is not in this month.",
                code="receipt_not_in_month",
            )
        if document_id not in _settled_outside_unmatched_ids(store, run):
            raise RunInputError(
                "That receipt is settled against a charge on the statement. "
                "Reject that match first, then mark it settled outside the "
                "card.",
                code="receipt_settled_by_charge",
            )
        entries = settled_outside_map(snapshot)
        entries[document_id] = {"how": how, "note": note, "at": now_iso}
        snapshot[SETTLED_OUTSIDE_KEY] = entries
        store.update_run_snapshot(run.run_id, snapshot)
    return {"ok": True, "document_id": document_id,
            "settled_outside": entries[document_id]}


def clear_receipt_settled_outside(
    store: RunStore,
    run: RunRow,
    document_id: str,
) -> dict:
    """The undo, shaped like the duplicates `ignore` resolution: the
    receipt rejoins the pool, the counts and the pair scan exactly as it
    was, because nothing about it was ever changed.

    Idempotent, so an undo clicked twice is not an error the second time;
    `removed` says whether this call was the one that did it."""
    with _BATCH_ADD_LOCK:
        fresh = store.get_run(run.run_id)
        if fresh is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        run = fresh
        snapshot = dict(run.snapshot or {})
        entries = settled_outside_map(snapshot)
        removed = entries.pop(document_id, None) is not None
        if removed:
            if entries:
                snapshot[SETTLED_OUTSIDE_KEY] = entries
            else:
                snapshot.pop(SETTLED_OUTSIDE_KEY, None)
            store.update_run_snapshot(run.run_id, snapshot)
    return {"ok": True, "document_id": document_id, "removed": removed}


# ---------------------------------------------------------------------------
# Item 70: changes in a month that did not stick (Criss 2026-09-14)
# ---------------------------------------------------------------------------
# The expense-edit fields the matcher actually reads. Enumerated from the
# matcher and the judgment layer, not from intuition: `match_month`,
# `reference_match` and `matching/judgment.py` read detected_date,
# detected_total, detected_currency, detected_vendor, detected_reference and
# legal_entity_id (plus payment_mode, which no edit route writes). An edit to
# any other field changes what a row BOOKS to, never what it PAIRS with, so it
# is not worth a re-match (time, and model calls for pairs not yet judged).
# `private` / `reimburse_to` are deliberately absent: the card chain derives a
# row's entity from the override / card / stamped value and never from the
# private flag, so confirming a private expense moves no pairing.
EXPENSE_MATCH_FIELDS = frozenset({
    "vendor", "date", "total", "currency", "legal_entity", "reference",
    # Note #63: the per-row card fix (item 87) decides the row's entity and,
    # through `bake_card_scope`, the card the matcher scopes it to.
    "card_key",
})


def override_base_account(override_category: str | None, base) -> str | None:
    """The account a category override inherits from the line's own
    categorization: the line's account when the override KEEPS the line's
    category, None when it changes it.

    An account is chosen for a category (the categorizer's pick from the
    chart, the report's account, a merchant default). Reclassifying the line
    to a different category makes that account stale, and inheriting it is
    how an iCloud receipt came to read "Software & Subscriptions" booked to
    the account picked for "Utilities & Premises". There is no deterministic
    category -> account map to fall back to (`EXPENSE_CATEGORY_ROOT_GROUP`
    names a root GROUP, not a postable leaf), so a changed category books to
    no account: the export shows its visible "(account unmapped - assign)"
    placeholder when a chart is wired and the category label when none is,
    never a guessed account."""
    if base is None or not override_category:
        return None
    if base.category != override_category:
        return None
    return base.zoho_account


def category_edit_account(
    category: str | None,
    zoho_account: str | None,
    existing_override: dict | None,
    base,
) -> str | None:
    """The account to STORE with a category edit that may or may not name one.

    An explicit account always wins. Without one, the account the line
    already had survives only when the category did not actually change
    (re-sending the current category keeps a reviewer-picked account);
    a changed category stores none, and `override_base_account` then stops
    the line's own stale account from coming back at read time."""
    if zoho_account:
        return zoho_account
    ov = existing_override or {}
    current = ov.get("category") or (base.category if base is not None else None)
    if category and category == current:
        return ov.get("zoho_account") or None
    return None


def category_edit_receipt(store: RunStore, run: RunRow, document_id: str):
    """The receipt a category edit targets, from the EFFECTIVE set (the
    extraction baseline with the expense overlay laid on it), so a manual add
    and a bare receipt resolve the way the expense grid shows them. A receipt
    borrowed from another batch for a candidate pairing is found among the
    snapshot's borrowed copies. None when the run holds no such receipt."""
    default_entity = (
        ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
    )
    effective = apply_expense_edits(
        baseline_receipts(run),
        store.get_expense_field_overrides(run.run_id),
        store.get_expense_edits(run.run_id),
        category_overrides=store.get_category_overrides(run.run_id),
        default_entity=default_entity,
    )
    rec = next((r for r in effective if r.document_id == document_id), None)
    if rec is not None:
        return rec
    for bd in (run.snapshot or {}).get(BORROWED_RECEIPTS_KEY) or []:
        if isinstance(bd, dict) and bd.get("document_id") == document_id:
            try:
                return receipt_from_dict(bd)
            except (KeyError, TypeError, ValueError):
                return None
    return None


def proposed_posting_category(
    candidates: list[dict],
    rec_by_id: dict,
    overrides: dict,
) -> dict | None:
    """The posting category a needs-review row will book to once confirmed.

    A review row holds no receipt until the reviewer confirms one, so its
    `posting_category` resolved to nothing and a category the reviewer set on
    the candidate saved and never showed. The SPA's Confirm takes the chosen
    candidate or else the first one; this reads the candidate carrying a
    reviewer category edit first (the one she just reclassified), then the
    first candidate in emitted order. Display only: readiness and the booking
    still follow the receipt actually confirmed."""
    edited = {
        doc for (doc, _line), ov in (overrides or {}).items()
        if (ov or {}).get("category")
    }
    order = [c.get("document_id") for c in candidates or []]
    picks = [d for d in order if d in edited][:1] + order[:1]
    for doc in picks:
        rec = rec_by_id.get(doc)
        if rec is None:
            continue
        hit = _row_posting_category(rec, overrides, None)
        if hit is not None:
            return hit
    return None


DATE_GAP_ZONES: tuple[tuple[str, int, int], ...] = (
    ("none", -1, 1),
    ("lag", 2, 7),
    ("lag", -3, -2),
)
"""Item 80 (note #44): how far a charge's date may sit from its receipt's
before the gap is worth saying, as `(zone, lo, hi)` inclusive bounds on
charge `transaction_date` minus receipt `detected_date` in calendar days.
Anything outside every band is `"mismatch"`. Owner ruling 2026-09-16.

A LABEL, not a matcher tunable: `date_exact_window_days`, `date_pct` and
every score are untouched (item 76's note keeps EXACT's window at one day).

Evidence, internal. Over 141 confirmed label pairs on eight statement
months (the six bundles plus live July and August), charge Transaction Date
minus receipt date was 0 days 124 times, +1 9, -1 3, -3 2 (one of them MSFT
4.26 USD against a Hotel Ibis 4.00 EUR receipt, very likely a wrong label),
+5 and +6 once each (MEGA CENTE CONSTR, Zoho-era dates), +14 once
(Namecheap, May). The one-day cases are midnight and time-zone boundaries
(Anthropic receipts, a late bar tab in Brazil, Google's 06-30 invoice
charged 07-01) and Amazon charging at shipment. Chase's Post Date minus
Transaction Date was 0 days 7 times, 1 day 94, 2 days 26 (every 2-day case
starting on a Friday): the processing lag lives in Post Date, which the
matcher does not use (`inspect.guess_column_map` keeps it as
`posting_date`).

Evidence, external (fetched 2026-09-16). Visa Core Rules (Apr 2026): the
Transaction Date is "the date on which a Transaction between a Cardholder
and a Merchant or an Acquirer occurs", e-commerce "on or after the date on
which the goods are shipped". Mastercard Transaction Processing Rules
(Moneris-hosted copy): the DE 12 date is the exchange of goods, shipment,
hotel checkout or ticket issue; presentment within 7 calendar days. Chase:
the transaction date is the purchase, the posting date is when the issuer
processes it, and a Saturday purchase may post Monday or Tuesday. Amazon
charges at shipment, multi-item orders "after all items have shipped or
five days after the order date, whichever occurs first". Stripe attempts
invoice payment one hour after `invoice.created`. Weekends and Fed holidays
move Post Date, not Transaction Date. No primary source gives a typical lag
per merchant class; the +7 bound coincides with Mastercard's 7-day
presentment window. URLs in `status/p1-improvement-backlog.md` item 80."""


def date_gap_zone(gap_days: int) -> str:
    """The `DATE_GAP_ZONES` band a signed day gap falls in, else
    `"mismatch"`."""
    for zone, lo, hi in DATE_GAP_ZONES:
        if lo <= gap_days <= hi:
            return zone
    return "mismatch"


def _candidate_date_gap(tx: "Transaction", receipt: "Receipt | None") -> dict:
    """`{date_gap_days, date_gap_zone}` for one `rows[].candidates[]` entry,
    or `{}` so both keys are ABSENT (never null) when the charge or the
    receipt has no date. Parallel fields (api-contract rule 1): `date_pct`
    beside them keeps meaning the matcher's score."""
    if receipt is None or tx.transaction_date is None or receipt.detected_date is None:
        return {}
    gap = (tx.transaction_date - receipt.detected_date).days
    return {"date_gap_days": gap, "date_gap_zone": date_gap_zone(gap)}


# ── Item 77: a corrected date moves the receipt to its month ─────────────
# A misread date misfiles a receipt: the drop routes a file by the month
# printed on it, so a 4 July slip read as a January date created a January
# month and landed there. Correcting the date did not move it, because a typed
# date is believed (item 25's release valve) and nothing else looks at where
# the row lives. So the grid OFFERS the move (`expenses[].month_move`) on a
# row whose reviewer-typed date falls outside the batch's window, and one POST
# carries it out: the receipt joins its own month (created when absent, the
# way a drop creates one) with its reading and every edit, and leaves this
# one as a soft delete that names where it went.


def month_move_for_row(
    r: Receipt,
    *,
    period: tuple[date, date] | None,
    date_is_human: bool,
    is_trip: bool,
) -> str | None:
    """The "YYYY-MM" this row belongs in, or None when it belongs here.

    Only a date the reviewer typed (or a whole expense entered by hand) can
    move a row: a machine reading outside the window is item 25's
    `date_outside_period` question, and moving on a reading the guard does
    not trust would file the receipt by the same mistake twice. A trip spans
    months freely, and a batch with no knowable month has no window to be
    outside of."""
    if is_trip or not date_is_human or r.detected_date is None:
        return None
    if not outside_period(r.detected_date, period):
        return None
    return f"{r.detected_date.year:04d}-{r.detected_date.month:02d}"


def _month_move_source(store: RunStore, run: RunRow, document_id: str):
    """(receipt, manual_payload) for a live expense of `run`, else raises.

    A file-backed receipt comes from the extraction BASELINE, never the
    baked pool: a statement month bakes the reviewer's edits into its
    receipts, and the move carries those edits separately, so carrying the
    baked copy too would apply them twice and make them unclearable."""
    edits = store.get_expense_edits(run.run_id)
    if any(
        e["document_id"] == document_id and e["op"] == "delete" for e in edits
    ):
        raise RunInputError(
            "This expense was already removed from this month.",
            code="expense_already_removed",
        )
    if document_id.startswith("manual:"):
        add = next(
            (e for e in edits
             if e["document_id"] == document_id and e["op"] == "add"),
            None,
        )
        if add is None:
            raise RunInputError("unknown expense", code="expense_not_found")
        return None, dict(add.get("payload") or {})
    rec = next(
        (r for r in baseline_receipts(run) if r.document_id == document_id),
        None,
    )
    if rec is None:
        raise RunInputError("unknown expense", code="expense_not_found")
    return rec, None


def move_expense_to_month(
    store: RunStore,
    run: RunRow,
    document_id: str,
    month: str,
    now_iso: str,
    *,
    data_root: Path,
    learning_db_path: Path | None = None,
) -> dict:
    """Move one expense of a company month into the month `month` names.

    The target is the batch month routing would pick for that month
    (`_open_batch_for_month`), created empty when there is none, under the
    same materialize lock the drop and the mail intake hold, so a month
    cannot be created twice. The receipt keeps its reading (no model call),
    its file (copied; the source keeps its bytes), its header and category
    edits and its intake provenance. Identical bytes already in the target
    are not added twice: the target's own row stands and only the source
    row goes. The source row becomes a soft delete whose payload names the
    target, and its claims are released. Both months re-match afterwards,
    outside the batch lock, exactly as any other edit does.
    """
    from .intake_mail import (
        _MATERIALIZE_LOCK, _month_human, _open_batch_for_month, _ym,
    )

    ym = _ym(month)
    if ym is None:
        raise RunInputError('month must be "YYYY-MM"', code="invalid_month")
    if run_mode(run) != MODE_EXPENSE_GENERATION:
        raise RunInputError("not an expense batch", code="not_an_expense_batch")
    if is_trip_batch(run):
        raise RunInputError(
            "A trip spans months; its receipts are not filed by month.",
            code="trip_not_by_month",
        )
    if month_from_label(run.label) == ym:
        raise RunInputError(
            f"This expense is already in {_month_human(month)}.",
            code="expense_already_in_month",
            month=month,
        )
    _month_move_source(store, run, document_id)  # fail before creating a month

    created = False
    with _MATERIALIZE_LOCK:
        target = _open_batch_for_month(store, ym)
        if target is None:
            prepared = create_expense_batch(
                Path(data_root),
                files=[],
                legal_entity="",
                label=_month_human(month),
                now_iso=now_iso,
                operator=None,
                learning_db_path=learning_db_path,
                settings=store.get_settings(),
                created_by="move",
                allow_empty=True,
            )
            target = store.get_run(execute_expense_batch(store, prepared))
            created = True
    if target is None:
        raise RunInputError(
            f"{_month_human(month)} could not be opened.",
            code="month_could_not_open",
            month=month,
        )
    if target.run_id == run.run_id:
        raise RunInputError(
            f"This expense is already in {_month_human(month)}.",
            code="expense_already_in_month",
            month=month,
        )

    with _BATCH_ADD_LOCK:
        source = store.get_run(run.run_id)
        target = store.get_run(target.run_id)
        if source is None or target is None:
            raise RunInputError(
                "This batch no longer exists (it was deleted).",
                code="batch_deleted",
            )
        rec, manual = _month_move_source(store, source, document_id)
        field_ov = dict(
            store.get_expense_field_overrides(source.run_id).get(document_id)
            or {}
        )
        cat_ov = {
            line: ov
            for (doc, line), ov in store.get_category_overrides(
                source.run_id
            ).items()
            if doc == document_id
        }
        already_there = False
        if manual is not None:
            new_doc = f"manual:{uuid.uuid4().hex[:12]}"
            store.set_expense_edit(target.run_id, new_doc, "add", manual, now_iso)
        else:
            src_file = Path(source.work_dir) / "receipts" / document_id
            if not src_file.is_file():
                raise RunInputError(
                    f"{_display_name(document_id)} is no longer on disk.",
                    code="file_missing_on_disk",
                    file=_display_name(document_id),
                )
            data = src_file.read_bytes()
            digest = hashlib.sha1(data).hexdigest()[:16]
            t_snapshot = dict(target.snapshot or {})
            _, t_receipts, t_outcome, _ = snapshot_from_dict(t_snapshot)
            t_dir = Path(target.work_dir) / "receipts"
            t_dir.mkdir(parents=True, exist_ok=True)
            same = next(
                (
                    r.document_id for r in t_receipts
                    if (t_dir / r.document_id).is_file()
                    and hashlib.sha1(
                        (t_dir / r.document_id).read_bytes()
                    ).hexdigest()[:16] == digest
                ),
                None,
            )
            if same is not None:
                new_doc, already_there = same, True
            else:
                n_index = 0
                for p in t_dir.iterdir():
                    m = re.match(r"^(\d{4})__", p.name)
                    if m:
                        n_index = max(n_index, int(m.group(1)) + 1)
                display = _display_name(document_id)
                fs_name = re.sub(r"[^A-Za-z0-9._-]", "_", display) or "receipt"
                new_doc = f"{n_index:04d}__{fs_name}"
                (t_dir / new_doc).write_bytes(data)
                pool = t_receipts + [replace(rec, document_id=new_doc)]
                t_outcome.unmatched_receipts.append(new_doc)
                t_snapshot["receipts"] = [receipt_to_dict(r) for r in pool]
                t_snapshot["outcome"] = outcome_to_dict(t_outcome)
                provenance = (
                    (source.snapshot or {}).get("intake_provenance") or {}
                ).get(document_id)
                if provenance:
                    t_snapshot["intake_provenance"] = {
                        **(t_snapshot.get("intake_provenance") or {}),
                        new_doc: provenance,
                    }
                store.update_run_snapshot(target.run_id, t_snapshot)
                n_cat, n_uncat = categorized_counts(pool)
                store.update_run_summary(target.run_id, {
                    **(target.summary or {}),
                    "n_expenses": len(pool),
                    "n_receipts": len(pool),
                    "n_categorized": n_cat,
                    "n_uncategorized": n_uncat,
                })
        if not already_there:
            for field, value in field_ov.items():
                store.set_expense_field_override(
                    target.run_id, new_doc, field, value, now_iso
                )
            for line, ov in cat_ov.items():
                store.set_category_override(
                    target.run_id, new_doc, line,
                    ov.get("category"), ov.get("zoho_account"), now_iso,
                    # Moving a receipt between months copies her decisions
                    # verbatim; whose category it was does not change with
                    # the month it sits in.
                    category_source=(
                        ov.get("category_source") or CATEGORY_SOURCE_HUMAN
                    ),
                )
        store.set_expense_edit(
            source.run_id, document_id, "delete",
            {"moved_to": target.run_id, "month": month, "document_id": new_doc},
            now_iso,
        )
        store.delete_claims_for_receipt(source.run_id, document_id)
        # Item 113: both months owe a re-match from this write on, in the
        # same lock span, so a restart while the source re-matches (minutes)
        # cannot leave the moved receipt unpaired in the target unrecorded.
        for owed_run in (source, target):
            owed_fresh = store.get_run(owed_run.run_id)
            if owed_fresh is not None and has_statement(owed_fresh):
                owed_snap = dict(owed_fresh.snapshot or {})
                owed_snap[REMATCH_PENDING_KEY] = rematch_pending_mark(
                    owed_snap, "month_move"
                )
                store.update_run_snapshot(owed_run.run_id, owed_snap)
        # Item 112: the target's OTHER neighbour (the source re-matches
        # anyway) owes a re-match when its statement period covers the
        # moved receipt's date. Nothing is owed when the target already
        # held the bytes: nothing arrived there.
        target_neighbours: list[str] = []
        neighbour_error = ""
        if not already_there:
            try:
                target_neighbours = _owe_neighbour_rematches_locked(
                    store, target, [new_doc], exclude={source.run_id}
                )
            except Exception as exc:  # noqa: BLE001 - the move is committed
                neighbour_error = f"{type(exc).__name__}: {exc}"
        remaining = len(apply_expense_edits(
            baseline_receipts(source),
            store.get_expense_field_overrides(source.run_id),
            store.get_expense_edits(source.run_id),
        ))

    out: dict = {
        "ok": True,
        "document_id": new_doc,
        "batch_id": target.run_id,
        "label": target.label,
        "month": month,
        "created_batch": created,
        "already_in_batch": already_there,
        "source": {"batch_id": source.run_id, "n_expenses": remaining},
    }
    for key, run_id in (("source_rematch", source.run_id),
                        ("rematch", target.run_id)):
        rematch = rematch_after_change(
            store, run_id, learning_db_path=learning_db_path,
            trigger="month_move",
        )
        if rematch is not None:
            out[key] = rematch
    if neighbour_error:
        out["neighbour_rematch_error"] = neighbour_error
    if target_neighbours:
        moved_cross = rematch_neighbour_months(
            store, target_neighbours, learning_db_path=learning_db_path
        )
        if moved_cross:
            out["months_rematched"] = moved_cross
    return out


# ── Item 74: duplicates mean one thing each ──────────────────────────
#
# The evidence the duplicate ladder reads (`duplicates.decide_receipt_groups`)
# and the one place both view builders, `rematch_month` and the attribution
# tool turn a month's receipts into decided groups.

# Snapshot key: document id -> sha1(bytes)[:16], the same digest a statement
# run's `folder:{digest}` id carries and the ingest dedupe compares. Persisted
# at add time and backfilled by every re-match, so a DB copy with no files
# still knows which receipts are byte-identical.
RECEIPT_DIGESTS_KEY = "receipt_digests"
# Snapshot key: the group ids the last re-match's statement check (rung 7)
# restored as two purchases. Rewritten by every re-match, never accumulated.
DUPLICATE_STATEMENT_KEY = "duplicate_statement_restored"

_FILE_EVIDENCE: dict[tuple[str, int, int, str], "str | None"] = {}
_FILE_EVIDENCE_MAX = 4096


def _file_evidence(path: Path, kind: str) -> "str | None":
    """`sha1` (the 16-hex digest) or `text` (the PDF text layer through the
    ingest's own `_pdf_text`, None for anything that is not a PDF) of one
    stored file, memoized on (path, mtime, size) so a page render does not
    re-read every receipt. Unreadable -> None, never an exception."""
    try:
        st = path.stat()
    except OSError:
        return None
    key = (str(path), st.st_mtime_ns, st.st_size, kind)
    if key in _FILE_EVIDENCE:
        return _FILE_EVIDENCE[key]
    value: "str | None"
    try:
        if kind == "sha1":
            value = hashlib.sha1(path.read_bytes()).hexdigest()[:16]
        elif path.suffix.lower() == ".pdf":
            from ..ingest.receipts_folder import _pdf_text

            value = _pdf_text(path)
        else:
            value = None
    except Exception:  # noqa: BLE001 - a damaged file is evidence of nothing
        value = None
    if len(_FILE_EVIDENCE) >= _FILE_EVIDENCE_MAX:
        _FILE_EVIDENCE.clear()
    _FILE_EVIDENCE[key] = value
    return value


def receipt_digests(
    run: RunRow, receipts: list[Receipt], *, work_dir: "Path | None" = None
) -> dict[str, str]:
    """document id -> byte digest for every receipt whose bytes are known:
    the persisted map first, then a statement run's `folder:{digest}` id
    (which IS the digest), then the stored file itself. `work_dir` overrides
    where the files are read from (a local copy of a hosted run)."""
    stored = (run.snapshot or {}).get(RECEIPT_DIGESTS_KEY) or {}
    expense_mode = run_mode(run) == MODE_EXPENSE_GENERATION
    wd = Path(work_dir) if work_dir is not None else Path(run.work_dir)
    out: dict[str, str] = {}
    for r in receipts:
        doc = r.document_id
        if stored.get(doc):
            out[doc] = str(stored[doc])
            continue
        if doc.startswith("folder:") and len(doc) > len("folder:"):
            out[doc] = doc[len("folder:"):]
            continue
        path = receipt_image_file(wd, doc, expense_mode=expense_mode)
        digest = _file_evidence(path, "sha1") if path is not None else None
        if digest:
            out[doc] = digest
    return out


def receipt_text_layer(run: RunRow, *, work_dir: "Path | None" = None):
    """document id -> the stored PDF's text layer, or None (no file, not a
    PDF, or a rendered body with no text layer). Resolved exactly as the
    image endpoint resolves the file (`receipt_image_file`). No model call."""
    expense_mode = run_mode(run) == MODE_EXPENSE_GENERATION
    wd = Path(work_dir) if work_dir is not None else Path(run.work_dir)

    def text_of(document_id: str) -> "str | None":
        path = receipt_image_file(wd, document_id, expense_mode=expense_mode)
        return _file_evidence(path, "text") if path is not None else None

    return text_of


def duplicate_decisions(
    run: RunRow,
    receipts: list[Receipt],
    resolutions: "dict[str, str] | None",
    *,
    work_dir: "Path | None" = None,
    with_statement_check: bool = True,
) -> list:
    """The month's receipt groups, each decided (`decide_receipt_groups`)
    with this run's evidence. `with_statement_check` reads the last
    re-match's rung-7 restorations off the snapshot; `rematch_month` passes
    False because it is about to run that check itself."""
    statement = (
        (run.snapshot or {}).get(DUPLICATE_STATEMENT_KEY) or []
        if with_statement_check else []
    )
    return decide_receipt_groups(
        receipts,
        digests=receipt_digests(run, receipts, work_dir=work_dir),
        text_of=receipt_text_layer(run, work_dir=work_dir),
        resolutions=resolutions or {},
        statement_distinct=statement,
    )


def decided_copies(
    run: RunRow,
    receipts: list[Receipt],
    resolutions: "dict[str, str] | None",
    *,
    charge_decisions: "dict | None" = None,
    receipt_decisions: "list | None" = None,
    effective=None,
) -> dict[str, str]:
    """THE copies a month does not count: document id -> the id of the
    document it repeats. One predicate for every surface that lists or sums
    the month (item 94, owner ruling 2026-09-17): the grid's count and
    `totals_by_ccy`, the months list, the expense CSV, the month report PDF,
    the cost-center roll-up, and the run payload's `copies_set_aside`.

    A copy is exactly what the matcher already keeps out of its pool
    (`copies_to_collapse` over the item-74 decisions: every member after the
    first of a group whose verdict is `copy`, decided by the tool or a
    reviewer), and only while no charge holds it. A copy a reviewer
    hand-matched to a charge holds that charge and is real spend again, which
    is why the run payload renders it as the match (items 83 + 75). A group
    ruled "Not a copy" (`ignore`) is not a copy, so ruling it brings the
    document back into every listing and total.

    `receipts` are the caller's own rows (the grid's, the export's, the
    snapshot pool), decided the same way over each. `receipt_decisions` /
    `effective` let a caller that already holds them pass them in;
    otherwise a month with a statement resolves its effective outcome from
    the snapshot and `charge_decisions` (the reviewer's verdicts).

    The value is the kept document, followed through a chain: a document
    kept by one group and collapsed by another is itself a copy, so the
    answer names the first document that is not."""
    if receipt_decisions is None:
        receipt_decisions = duplicate_decisions(run, receipts, resolutions)
    collapsed = copies_to_collapse(receipt_decisions)
    if not collapsed:
        return {}
    if effective is not None:
        pool_ids = {r.document_id for r in receipts}
    elif has_statement(run):
        transactions, pool, outcome, _errors = snapshot_from_dict(run.snapshot)
        effective = apply_decisions(
            outcome, transactions, pool, charge_decisions or {}
        )
        pool_ids = {r.document_id for r in pool}
    if effective is not None:
        free = set(effective.unmatched_receipts)
        # A row the pool does not hold (typed in since the last re-match)
        # holds no charge either.
        collapsed = {d for d in collapsed if d in free or d not in pool_ids}
    kept_by: dict[str, str] = {}
    for dec in receipt_decisions:
        if dec.is_copy:
            for member in dec.members[1:]:
                kept_by.setdefault(member, dec.members[0])
    out: dict[str, str] = {}
    for doc in collapsed:
        root, seen = kept_by.get(doc, doc), {doc}
        while root in kept_by and root not in seen:
            seen.add(root)
            root = kept_by[root]
        out[doc] = root
    return out


def copies_set_aside_totals(receipts: list[Receipt], copies) -> dict[str, Decimal]:
    """Per-currency sums of the copies among `receipts` (item 94): the
    amounts every surface prints on its "copies set aside" line. A copy whose
    amount was never read adds nothing, as it would add nothing to a total."""
    totals: dict[str, Decimal] = {}
    for r in receipts:
        if r.document_id in copies and r.detected_total is not None:
            ccy = r.detected_currency or "?"
            totals[ccy] = totals.get(ccy, Decimal("0")) + r.detected_total
    return totals


def duplicate_group_entry(decision) -> dict:
    """One `duplicate_groups[]` element. `resolution` keeps its meaning; the
    item-74 fields are parallel: `state` always (`open` | `decided`),
    `basis` / `decided_by` / `verdict` present when known and ABSENT
    otherwise, never null."""
    entry: dict = {
        "group_id": decision.group_id,
        "kind": "receipt",
        "members": list(decision.members),
        "resolution": decision.resolution,
        "state": decision.state,
    }
    if decision.basis:
        entry["basis"] = decision.basis
    if decision.decided_by:
        entry["decided_by"] = decision.decided_by
    if decision.verdict:
        entry["verdict"] = decision.verdict
    return entry


def duplicate_pool(
    run: RunRow,
    pool: list[Receipt],
    resolutions: "dict[str, str] | None",
    *,
    work_dir: "Path | None" = None,
):
    """`(pool without collapsed copies, collapsed ids, decisions)`: the
    candidate pool a re-match hands the matcher before the statement check.
    Shared by `rematch_month` and `tools/recon-match-attribution.py`, so the
    replay cannot assemble a different pool than the app."""
    decisions = duplicate_decisions(
        run, pool, resolutions, work_dir=work_dir, with_statement_check=False,
    )
    collapsed = copies_to_collapse(decisions)
    kept = [r for r in pool if r.document_id not in collapsed] if collapsed else pool
    return kept, collapsed, decisions


def duplicate_statement_pass(
    pool: list[Receipt],
    decisions: list,
    collapsed: set,
    transactions: list,
    outcome,
    match_cfg,
):
    """Rung 7 over one match: `(restored group ids, kept pool, collapsed)`.
    `pool` is the pool BEFORE the collapse. Nothing restored: the collapsed
    set comes back unchanged. Otherwise the caller matches ONCE more on the
    returned pool and does not check again."""
    restored = restore_copies_with_their_own_charge(
        decisions, pool, transactions, outcome, match_cfg, collapsed=collapsed,
    )
    if restored:
        collapsed = copies_to_collapse(decisions, restored)
    kept = [r for r in pool if r.document_id not in collapsed]
    return restored, kept, collapsed


# ---------------------------------------------------------------------------
# Whose turn a row is, and clean exact pairs confirm themselves (item 76)
# ---------------------------------------------------------------------------
# Notes #38 / #39 / #49 (owner, July): "things that are reconciled and there
# are no mismatches should not need confirmation", and a yellow row already
# booked in the workbook was still offered Reject / Confirm. `rows[].status`
# read `pending` on all 223 live rows, so the SPA printed "Awaiting decision"
# on finished work as loudly as on the 13 rows that were really the
# reviewer's to decide.
#
# Owner rulings 2026-09-16: exact pairs only, and the vendor must agree at
# 75 or better. Measured that evening, the six literal exact pairs on the two
# live months are all right per the labels; at 75 five confirm themselves
# and WEB*NETWORKSOLUTIONS 7.98 (vendor 46) keeps asking.

TURN_DECIDE = "decide"
TURN_CONFIRMED = "confirmed"
TURN_REJECTED = "rejected"
TURN_POSTED = "posted"
TURN_NONE = "none"

DECIDED_BY_TOOL = "tool"
DECIDED_BY_REVIEWER = "reviewer"


def reviewer_confirmed_tx_ids(decisions: dict | None) -> set[str]:
    """The charges a PERSON confirmed, which is what the alias and per-merchant
    FX learners may learn from (2026-09-24 owner ruling: only corrections are
    memorized).

    `apply_self_confirmations` writes STATUS_CONFIRMED with
    `decided_by = tool` after every re-match commit, and most matches in a
    real month are tool-confirmed. Both learning paths used to filter on the
    status alone, so pairings nobody had looked at taught durable vendor
    aliases and FX rates, which is the opposite of "confirming a match is
    Chris asserting this charge IS this receipt" that `learn_confirmed_pairs`
    justifies itself with.

    A NULL `decided_by` counts as a person: every such row predates the
    column and was written by one (or by a disposition seed that left the
    status pending, which this filter excludes anyway on status)."""
    return {
        tx_id for tx_id, d in (decisions or {}).items()
        if d.status == STATUS_CONFIRMED and d.decided_by != DECIDED_BY_TOOL
    }

SELF_CONFIRM_RULE = "exact_vendor_75"
SELF_CONFIRM_VENDOR_FLOOR = 75


def row_turn(status: str, is_posted: bool, effective_bucket: str) -> str:
    """Whose move a workbench row is.

    `decide` is the reviewer's turn and the only value that should offer
    Reject / Confirm: a pending pairing the tool holds a receipt for, on a
    charge nobody has booked. It is exactly the set `summary.n_undecided`
    counts. Everything else is nothing to do, and says why: an explicit
    verdict (by the tool or a person), a charge already booked in the
    workbook, or no pairing at all (no receipt, or a credit).

    A verdict outranks the yellow fill so a confirmed or rejected booked row
    still shows its undo."""
    if status == STATUS_CONFIRMED:
        return TURN_CONFIRMED
    if status == STATUS_REJECTED:
        return TURN_REJECTED
    if is_posted:
        return TURN_POSTED
    if effective_bucket in ("reconciled", "review"):
        return TURN_DECIDE
    return TURN_NONE


def receipt_chase_groups(
    rows: list[dict],
    *,
    run: RunRow,
    transactions: list,
    coverage: list[dict],
    settings: dict | None = None,
) -> list[dict]:
    """Item 107's missing-receipt list for one month, grouped by holder.

    Binds the payload's own rows to the card identities `coverage` already
    resolved, so a charge is chased from the person whose card the coverage
    panel totals it under. The amounts come from the transactions rather
    than the rows' formatted strings, so the per-currency totals are exact.
    `settings` adds the holders' addresses and the merchant registry's
    portal hints when the caller has them; without it the groups are
    identical minus those two display fields."""
    from ..cards import cards_from_setting
    from .receipt_chase import chase_groups, holder_addresses, portal_hints
    from .month_readiness import charge_needs_receipt

    cards = cards_from_setting(
        ((run.config or {}).get("expense") or {}).get("cards")
    )
    card_info = {
        cov["key"]: {
            "card_key": cov.get("card_key") or "",
            "label": cov.get("label") or cov["key"],
            "person": (
                cards[cov["card_key"]].person
                if cov.get("card_key") in cards else ""
            ),
        }
        for cov in coverage
    }
    open_rows = [r for r in rows if charge_needs_receipt(r)]
    if not open_rows:
        return []
    return chase_groups(
        rows,
        card_info=card_info,
        amounts={t.transaction_id: t.amount for t in transactions},
        addresses=holder_addresses(settings),
        hints=portal_hints(
            (settings or {}).get("merchants"),
            {r["transaction_id"]: r.get("vendor") or "" for r in open_rows},
        ),
    )


def receipt_chase_view(decision: "Decision | None") -> dict:
    """Item 107's two reviewer-set states as row fields, both ABSENT unless
    set, so a month nobody has chased renders byte-identically to before.

    `receipt_requested_at` / `requested_to` record the ask (it closes
    nothing); `no_receipt_expected` holds the reason no receipt will ever
    exist (it closes the charge). They live on the SAME `decisions` row as
    the pairing verdict, which is what carries them through a re-match and
    through a statement re-read's id rekey."""
    if decision is None:
        return {}
    out: dict = {}
    if decision.receipt_requested_at:
        out["receipt_requested_at"] = decision.receipt_requested_at
        if decision.receipt_requested_to:
            out["requested_to"] = decision.receipt_requested_to
    reason = str(decision.no_receipt_expected or "").strip()
    if reason:
        out["no_receipt_expected"] = reason
    return out


def decided_by_view(decision: "Decision | None") -> dict:
    """`{"decided_by": ..., "decided_rule": ...}` for a row carrying a
    verdict, else `{}` so both keys are ABSENT on a pending row. A verdict
    written before the column existed reads `reviewer`, which is true: the
    tool never wrote one before item 76."""
    if decision is None or decision.status == STATUS_PENDING:
        return {}
    if decision.decided_by == DECIDED_BY_TOOL:
        out = {"decided_by": DECIDED_BY_TOOL}
        if decision.rule:
            out["decided_rule"] = decision.rule
        return out
    return {"decided_by": DECIDED_BY_REVIEWER}


def confirmable_pair(row: dict) -> bool:
    """The owner's PAIRING rule on one `build_view` row (item 76 rulings
    2026-09-16), shared by the tool's self-confirmation and "Confirm all
    matched" (item 101).

    A pending row that is the reviewer's turn (`decide`, so never booked) in
    the `reconciled` bucket, with ONE candidate, that candidate chosen,
    `exact`, not flagged for review, and the vendor agreeing at
    `SELF_CONFIRM_VENDOR_FLOOR`. A candidate borrowed from another batch,
    held by another charge, or turned down never qualifies: each is a
    question the rule was not ruled on.

    Says nothing about the category: confirming a pairing is not a category
    verdict, so the category condition lives in `self_confirm_pairs`."""
    if row.get("status") != STATUS_PENDING:
        return False
    if row.get("turn") != TURN_DECIDE or row.get("effective_bucket") != "reconciled":
        return False
    cands = row.get("candidates") or []
    if len(cands) != 1:
        return False
    c = cands[0]
    if not c.get("is_chosen") or c.get("match_type") != MatchType.EXACT.value:
        return False
    if c.get("requires_review"):
        return False
    if (c.get("vendor_pct") or 0) < SELF_CONFIRM_VENDOR_FLOOR:
        return False
    if c.get("from_batch") or c.get("held_by") or c.get("rejected"):
        return False
    return True


def self_confirm_pairs(view: dict) -> dict[str, str]:
    """`{transaction_id: document_id}` for the rows that confirm themselves.

    Read off a `build_view` payload so the test is the one the page shows:
    the pairing rule (`confirmable_pair`) AND a category the tool may post
    (`review.state == "ready"`). The tool confirms without anyone looking,
    so it also needs the category settled."""
    out: dict[str, str] = {}
    for r in view.get("rows", []):
        if not confirmable_pair(r):
            continue
        if (r.get("review") or {}).get("state") != "ready":
            continue
        out[r["transaction_id"]] = r["candidates"][0]["document_id"]
    return out


def confirm_matched_pairs(
    rows: list[dict], autopick: dict[str, str]
) -> list[tuple[str, str]]:
    """The (transaction_id, document_id) writes "Confirm all matched" makes
    (item 101), in row order.

    Rows passing the pairing rule (`confirmable_pair`), whatever their
    category state: a person pressed the button, and the category keeps its
    own question. Intersected with the matcher's pending auto-pick
    (`autopick_pairs`) so every write is a real `outcome.matches` pairing on
    the receipt the row shows. `build_view` counts the same list as
    `summary.n_confirm_matched`, so the button's number is what it does."""
    out: list[tuple[str, str]] = []
    for r in rows:
        if not confirmable_pair(r):
            continue
        tx_id = r["transaction_id"]
        doc_id = r["candidates"][0]["document_id"]
        if autopick.get(tx_id) != doc_id:
            continue
        out.append((tx_id, doc_id))
    return out


def apply_self_confirmations(
    store: RunStore, run_id: str, now_iso: str | None = None
) -> dict:
    """Bring the tool's own verdicts on one month in line with the rule.

    Every tool verdict is judged afresh: the month is viewed as if the tool
    had written none, the qualifying pairs are selected, and then
    - a tool confirmation that no longer qualifies (a rival receipt arrived,
      the category changed) goes back to pending, still marked as the
      tool's, so it can qualify again later;
    - a qualifying pair nobody has decided is confirmed, marked
      `decided_by: tool` with the rule, and its receipt claim synced like
      any confirm.
    A person's verdict is never touched, pending included: resetting a
    self-confirmed row to pending is how a reviewer takes it back, and the
    store's conditional write keeps it that way.

    Runs after every re-match commit (`rematch_month`), outside the batch
    lock. Returns `{confirmed, withdrawn, refused}`."""
    result = {"confirmed": 0, "withdrawn": 0, "refused": 0}
    run = store.get_run(run_id)
    if run is None or not has_statement(run):
        return result
    decisions = store.get_decisions(run_id)
    tool_verdicts = {
        tx: d for tx, d in decisions.items()
        if d.decided_by == DECIDED_BY_TOOL and d.status != STATUS_PENDING
    }
    baseline = {tx: d for tx, d in decisions.items() if tx not in tool_verdicts}
    view = build_view(
        run, baseline, store.get_category_overrides(run_id),
        store.get_duplicate_resolutions(run_id),
    )
    autopick = dict(matched_autopick_decisions(run, baseline))
    wanted = {
        tx: doc for tx, doc in self_confirm_pairs(view).items()
        if autopick.get(tx) == doc
    }
    now = now_iso or datetime.now(timezone.utc).isoformat(timespec="seconds")
    for tx, d in sorted(tool_verdicts.items()):
        if d.status == STATUS_CONFIRMED and wanted.get(tx) == d.chosen_document_id:
            continue
        if store.set_tool_decision(run_id, tx, STATUS_PENDING, None, now, None):
            sync_claim_for_decision(store, run, tx, STATUS_PENDING, None, now)
            result["withdrawn"] += 1
    for tx, doc in sorted(wanted.items()):
        cur = tool_verdicts.get(tx)
        if (
            cur is not None and cur.status == STATUS_CONFIRMED
            and cur.chosen_document_id == doc
        ):
            continue
        if not store.set_tool_decision(
            run_id, tx, STATUS_CONFIRMED, doc, now, SELF_CONFIRM_RULE
        ):
            continue  # a person decided this charge; theirs stands
        if sync_claim_for_decision(
            store, run, tx, STATUS_CONFIRMED, doc, now
        ) is not None:
            # Another batch settled the receipt meanwhile: undo our write.
            store.set_tool_decision(run_id, tx, STATUS_PENDING, None, now, None)
            result["refused"] += 1
            continue
        result["confirmed"] += 1
    return result


# ── The Expenses view's boxes (backlog item 84, 2026-09-16) ─────────────
# Owner: "these should be the overview boxes, that a user should be able to
# click on and see all of the belonging data". A box that opens its rows has
# to list exactly the number it shows, so each row names the boxes it belongs
# to and each count is the number of rows carrying its box. A box's name is
# its count's name without `n_`.

EXPENSE_BOXES = (
    "categorized",
    "uncategorized",
    "ready",
    "needs_entity",
    "needs_person",
    "needs_company_or_person",
    "needs_cost_center",
    "suggested_private",
    "private",
    "missing_receipt_image",
    "receipts_unrenderable",
)


def receipt_image_missing(
    *, has_image_info: bool, available: bool, referenced: bool
) -> bool:
    """Whether a row counts as missing its receipt image.

    The flag used to read only `has_receipt_image` (a receipt URL or file
    name recorded at extraction), so a mailed body rendered to PDF, or a
    receipt moved between months, read "missing" while the image endpoint
    served its file (July 2026: 2 rows, August: 1, all three 200). A row is
    missing its image only when the app can show no file for it AND no image
    is referenced. `has_image_info` keeps the L4 noise guard: a source that
    records no image references at all flags nothing."""
    return has_image_info and not (available or referenced)


def expense_boxes(
    *,
    categorized: bool,
    review_state: str,
    res: dict,
    needs_cost_center: bool,
    image_missing: bool,
    render_failed: bool,
    copy: bool = False,
    settled_outside: bool = False,
) -> list[str]:
    """The boxes one expense row belongs to, in `EXPENSE_BOXES` order.

    `res` is the row's card resolution (`resolve_batch_row_cards`). The
    entity rule is `n_needs_entity`'s (a confirmed private row needs none),
    the person rule `n_needs_person`'s; `needs_company_or_person` is either
    (owner ruling 2026-09-16: one box, because the fix is one action).

    `copy` (item 94, owner ruling 2026-09-17): a decided copy
    (`decided_copies`, the row's `counts_in_total: false`) is in NO box. The
    boxes count the expenses the month counts, so a copy that leaves
    `n_expenses` leaves every box with it and `categorized` + `uncategorized`
    still partition exactly `n_expenses`. The to-do boxes go too: nothing
    done to a copy's company, person, cost center, private flag or file
    changes the month, because a copy writes no CSV row, no listing row, no
    reimbursement and no cost-center bucket. The one question a copy still
    asks, whether it really is one, has its own control ("Not a copy"), and
    that ruling brings the row back into every box it qualifies for.

    `settled_outside` (item 144, owner ruling 2026-09-17): a row the
    reviewer has settled OFF the card system (`settled_off_card`) is not in
    `needs_person`. Person resolution is card-only by the item-40 ruling,
    and a bill paid by wire will never have a card, so the box was holding
    a row on an ask nobody can answer: July's Tricarico invoice could not
    leave it by any sanctioned action. `needs_entity` is untouched. The
    company is genuinely unknown on such a row and a card was never what
    was going to name it, so the question stands and only the instruction
    changes (`_expense_review`). `needs_company_or_person` then follows
    from `needs_entity` alone, by the same either-half rule."""
    if copy:
        return []
    needs_entity = not res.get("entity") and not res.get("private")
    needs_person = not res.get("person") and not settled_outside
    member = {
        "categorized": categorized,
        "uncategorized": not categorized,
        "ready": review_state == "ready",
        "needs_entity": needs_entity,
        "needs_person": needs_person,
        "needs_company_or_person": needs_entity or needs_person,
        "needs_cost_center": needs_cost_center,
        "suggested_private": bool(res.get("suggested_private")),
        "private": bool(res.get("private")),
        "missing_receipt_image": image_missing,
        "receipts_unrenderable": render_failed,
    }
    return [box for box in EXPENSE_BOXES if member[box]]


# ── A month's corrections are saved to memory at sign-off (item 88) ─────
# Owner ruling 2026-09-16: save a month's corrections to memory automatically
# at month sign-off, with the Memory page as the undo. `commit_to_memory` had
# one caller, the "Save corrections to memory" button, and the live store held
# 0 learned entities and 0 field corrections: the button was never pressed.
# The app's sign-off is Publish ("Open a run, resolve every row, then hit
# Publish"), so publishing saves. Accepted trade-off (same ruling): a one-off
# exception becomes a rule until someone deletes it on the Memory page.

MEMORY_TRIGGER_BUTTON = "button"
MEMORY_TRIGGER_PUBLISH = "publish"


def memory_commit_digest(
    decisions: dict,
    overrides: dict,
    field_overrides: dict,
    edits: list[dict],
) -> str:
    """A digest of everything `commit_to_memory` can learn from on one run:
    each decision's verdict and receipt, category overrides, header field
    edits, whole-expense adds and deletes. Timestamps are left out, so
    re-clicking a verdict that did not change changes nothing."""
    payload = {
        "decisions": sorted(
            (tx, d.status, d.chosen_document_id or "")
            for tx, d in (decisions or {}).items()
        ),
        "overrides": sorted(
            (f"{doc}|{line}", json.dumps(v, sort_keys=True, default=str))
            for (doc, line), v in (overrides or {}).items()
        ),
        "field_overrides": json.dumps(field_overrides or {}, sort_keys=True, default=str),
        "edits": json.dumps(edits or [], sort_keys=True, default=str),
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def commit_month_memory(
    store: RunStore,
    run: RunRow,
    learning_db_path: Path,
    now_iso: str,
    *,
    trigger: str,
    only_if_changed: bool,
) -> dict:
    """Save one run's corrections to memory and record the save.

    `{"saved": True, "learned": {...}}` after a save. With
    `only_if_changed` (the publish path), `{"saved": False, "reason":
    "unchanged"}` when the run's corrections are exactly what was last saved,
    so publishing, unpublishing and publishing again does not count the same
    corrections twice in the Memory page's counts. The button always saves."""
    decisions = store.get_decisions(run.run_id)
    overrides = store.get_category_overrides(run.run_id)
    field_overrides = store.get_expense_field_overrides(run.run_id)
    edits = store.get_expense_edits(run.run_id)
    digest = memory_commit_digest(decisions, overrides, field_overrides, edits)
    if only_if_changed:
        last = store.get_memory_commit(run.run_id)
        if last is not None and last["digest"] == digest:
            return {"saved": False, "reason": "unchanged"}
    # Item 163: what this save is ABOUT to write, and what each of those
    # rows holds right now. Read before the write, so the journal's
    # pre-image is the state a later undo has to put back. A plan that
    # fails to compute must not silently disarm the undo, so it is not
    # wrapped: the save fails with it, which is the safe direction.
    plan = plan_month_memory(
        store, run, learning_db_path,
        decisions=decisions, overrides=overrides,
        field_overrides=field_overrides, edits=edits, now_iso=now_iso,
    )
    before_rows = _memory_pre_image(learning_db_path, plan["writes"])
    merchants_before = copy.deepcopy((store.get_settings() or {}).get("merchants") or {})
    learned = commit_to_memory(
        run, decisions, overrides, learning_db_path, now_iso,
        field_overrides=field_overrides, edits=edits, settings_store=store,
    )
    store.set_memory_commit(run.run_id, digest, now_iso, trigger)
    merchants_after = (store.get_settings() or {}).get("merchants") or {}
    journal_id = store.add_memory_journal(
        run_id=run.run_id,
        label=run.label,
        committed_at=now_iso,
        trigger=trigger,
        rows=before_rows,
        merchants_before=merchants_before,
        merchants_after=copy.deepcopy(merchants_after),
        learned=learned,
    )
    return {"saved": True, "learned": learned, "journal_id": journal_id}


# --------------------------------------------------------------------------
# Item 163: the memory-save plan, its journal, and the undo
#
# Feedback note #81 (2026-09-23) on "Save corrections to memory": "based on
# what? this should be reversible for now, and state explicitly where these
# are saved so user can manage this". So a save answers all three: the plan
# says what it would write and from which row of the month, the journal says
# where it went and keeps the pre-image, and the undo puts that pre-image
# back.
# --------------------------------------------------------------------------

# Which surface a reader manages each learning table on. Named here rather
# than in the SPA so the answer to "where is this saved" cannot drift from
# the code that saves it.
MEMORY_TABLE_SURFACE: dict[str, str] = {
    "merchant_category": "memory",
    "merchant_entity": "memory",
    "field_correction": "memory",
    "vendor_alias": "memory",
    "merchant_fx": "memory",
}


def plan_month_memory(
    store,
    run: RunRow,
    learning_db_path: Path,
    *,
    decisions=None,
    overrides=None,
    field_overrides=None,
    edits=None,
    now_iso: str,
) -> dict:
    """What saving this month's corrections WOULD write, writing nothing.

    Returns `{"writes": [...], "counts": {...}, "registry": {...},
    "learned": {...}}`. Each write names its table, its primary key, the
    surface that manages it, and the value it would set. The registry half
    is a per-merchant before/after diff.

    Computed by running the real learners against `RecordingStore`, so the
    preview cannot disagree with the save."""
    from ..learning import RecordingStore, distinct_keys, registry_diff

    decisions = store.get_decisions(run.run_id) if decisions is None else decisions
    overrides = (
        store.get_category_overrides(run.run_id) if overrides is None else overrides
    )
    field_overrides = (
        store.get_expense_field_overrides(run.run_id)
        if field_overrides is None else field_overrides
    )
    edits = store.get_expense_edits(run.run_id) if edits is None else edits

    recorder: dict = {}

    def factory(_path):
        rec = RecordingStore()
        recorder["store"] = rec
        return rec

    learned = commit_to_memory(
        run, decisions, overrides, learning_db_path, now_iso,
        field_overrides=field_overrides, edits=edits, settings_store=store,
        store_factory=factory, persist=False,
    )
    merchants_after = learned.pop("merchants_after", None)
    rec = recorder.get("store")
    writes = list(rec.writes) if rec is not None else []
    counts: dict[str, int] = {}
    for table, _key in distinct_keys(writes):
        counts[table] = counts.get(table, 0) + 1
    return {
        "writes": [_planned_write_view(w) for w in writes],
        "keys": [
            {"table": t, "key": list(k), "surface": MEMORY_TABLE_SURFACE.get(t, "")}
            for t, k in distinct_keys(writes)
        ],
        "counts": counts,
        "registry": registry_diff(
            (store.get_settings() or {}).get("merchants") or {}, merchants_after
        ) if merchants_after is not None else {},
        "learned": learned,
    }


def _planned_write_view(w) -> dict:
    """One planned write, as the screen reads it: which table, which key,
    where it is managed, and the value it sets. `value` is the column the
    row is ABOUT (the category, the entity, the corrected value); an FX
    sample and an alias carry their own shape, so those read as the key
    they add."""
    from ..learning import TABLE_KEYS

    value = ""
    if w.table == "merchant_category":
        value = str(w.args[2] or "")
    elif w.table == "merchant_entity":
        value = str(w.args[1] or "")
    elif w.table == "field_correction":
        value = str(w.args[3] or "")
    elif w.table == "merchant_fx":
        value = str(w.args[4])
    elif w.table == "vendor_alias":
        value = str(w.args[2] or "")
    return {
        "table": w.table,
        "key": dict(zip(TABLE_KEYS[w.table], w.key)),
        "surface": MEMORY_TABLE_SURFACE.get(w.table, ""),
        "value": value,
    }


def _memory_pre_image(learning_db_path: Path, writes: list[dict]) -> list[dict]:
    """The rows behind a plan's keys as they stand BEFORE it runs:
    `[{table, key, row|None}]`. `row: None` records a key that does not
    exist yet, which is what an undo deletes rather than restores."""
    out: list[dict] = []
    seen: set[tuple] = set()
    if not writes:
        return out
    with LearningStore(learning_db_path) as s:
        for w in writes:
            ident = (w["table"], tuple(sorted(w["key"].items())))
            if ident in seen:
                continue
            seen.add(ident)
            out.append({
                "table": w["table"],
                "key": w["key"],
                "row": s.read_row(w["table"], w["key"]),
            })
    return out


def undo_memory_commit(
    store, journal_id: int, learning_db_path: Path, now_iso: str
) -> dict:
    """Put one recorded save back the way it was (item 163).

    Every learning row the save touched is restored to its pre-image (a row
    that did not exist is deleted), the merchant registry is restored to the
    map that preceded the save, and the run's `memory_commits` digest is
    cleared so the next publish teaches those corrections again rather than
    reporting "unchanged" over a memory that no longer holds them.

    Refuses (`Refusal`) an unknown entry, one already reverted, and one that
    is not the LATEST save: saves stack on the same rows, so putting an
    older pre-image back would silently discard a newer save's values."""
    entry = store.get_memory_journal(journal_id)
    if entry is None:
        return Refusal(
            "no such memory save", code="memory_journal_not_found",
        )
    if entry["reverted_at"]:
        return Refusal(
            "this memory save was already undone",
            code="memory_journal_already_reverted",
            reverted_at=entry["reverted_at"],
        )
    latest = store.latest_memory_journal()
    if latest is not None and latest["id"] != journal_id:
        return Refusal(
            "only the most recent memory save can be undone; undo "
            f"save {latest['id']} first",
            code="memory_journal_not_latest",
            latest_id=latest["id"],
        )
    restored = 0
    if entry["rows"]:
        with LearningStore(learning_db_path) as s:
            for r in entry["rows"]:
                s.restore_row(r["table"], r["key"], r["row"])
                restored += 1
    registry_restored = False
    if entry["merchants_before"] != entry["merchants_after"]:
        store.set_settings({"merchants": entry["merchants_before"]}, now_iso)
        registry_restored = True
    store.clear_memory_commit(entry["run_id"])
    store.set_memory_journal_reverted(journal_id, now_iso)
    return {
        "undone": True,
        "journal_id": journal_id,
        "rows_restored": restored,
        "registry_restored": registry_restored,
        "run_id": entry["run_id"],
    }


# ---------------------------------------------------------------------------
# Item 82: ECB monthly reference rates in the run config
# ---------------------------------------------------------------------------


def ecb_months_for(label: str | None, transactions=()) -> list[str]:
    """The months whose ECB averages a month's matching can reach: the
    labelled month with one neighbour either side, plus the month of every
    charge (a statement opening on the 30th, a charge posted late)."""
    from . import ecb_rates

    months: set[str] = set()
    ym = month_from_label(label)
    if ym is not None:
        months.update(ecb_rates.months_around(f"{ym[0]:04d}-{ym[1]:02d}"))
    for tx in transactions or ():
        d = getattr(tx, "transaction_date", None)
        if d is not None:
            months.add(d.strftime("%Y-%m"))
    return sorted(months)


def apply_ecb_rates(cfg: dict, months) -> dict:
    """Return `cfg` with the ECB monthly averages for `months` merged into
    `matching.fx_ecb_monthly_rates` (item 82, owner ruling 2026-09-16).

    A fetched month replaces the stored one (a published average is final,
    so this only ever adds what the ECB has published since); months the
    fetch did not return stay as they were.
    Fail-open: when the ECB returns nothing, `cfg` comes back unchanged, key
    for key, so a month created offline is the month created before this
    item shipped."""
    from . import ecb_rates

    fetched = ecb_rates.rates_for_months(months)
    if not fetched:
        return cfg
    out = dict(cfg)
    matching = dict(out.get("matching") or {})
    table = {
        str(month): dict(per_eur or {})
        for month, per_eur in (matching.get("fx_ecb_monthly_rates") or {}).items()
    }
    table.update({month: dict(per_eur) for month, per_eur in fetched.items()})
    matching["fx_ecb_monthly_rates"] = dict(sorted(table.items()))
    out["matching"] = matching
    return out


# ---------------------------------------------------------------------------
# Note #79: the polled daily FX rates in the run config
# ---------------------------------------------------------------------------


def fx_days_for(label: str | None, transactions=()) -> tuple[str, str] | None:
    """The span of days a month's matching can reach, as (first, last) ISO
    days: the same months `ecb_months_for` names (the labelled month, one
    neighbour either side, every charge's month), whole. None when nothing
    names a month (a trip with no charges)."""
    import calendar

    months = ecb_months_for(label, transactions)
    if not months:
        return None
    y, m = int(months[-1][:4]), int(months[-1][5:7])
    return f"{months[0]}-01", f"{months[-1]}-{calendar.monthrange(y, m)[1]:02d}"


def apply_fx_daily_rates(cfg: dict, store, label: str | None, transactions=()) -> dict:
    """Return `cfg` with the store's polled daily rates for the span
    `fx_days_for` names as `matching.fx_daily_rates` (units per EUR by day,
    the provider's digits as text). The store is the truth, so the table is
    REPLACED, not merged: a re-match reads what has been polled by now. A
    store with nothing for the span leaves `cfg` unchanged, key for key, so
    a month matched before the poll ever ran keeps its rungs as they were."""
    span = fx_days_for(label, transactions)
    if span is None:
        return cfg
    try:
        table = store.fx_daily_rates(span[0], span[1])
    except Exception:  # noqa: BLE001 - a rate table never blocks a re-match
        import logging

        logging.getLogger(__name__).warning(
            "daily FX rates unreadable for %s..%s", *span, exc_info=True,
        )
        return cfg
    if not table:
        return cfg
    out = dict(cfg)
    matching = dict(out.get("matching") or {})
    matching["fx_daily_rates"] = {
        day: dict(per_eur) for day, per_eur in sorted(table.items())
    }
    out["matching"] = matching
    return out


def top_up_ecb_rates(cfg: dict, label: str | None, transactions=()) -> dict:
    """`cfg` with any ECB monthly average this month can reach that its
    stored table does not already carry (2026-09-23).

    `apply_ecb_rates` fetches; this decides whether a fetch is needed at
    all, so an ordinary re-match of a month whose table is already complete
    costs no request. A published monthly average never changes, so a month
    already present is never re-fetched. Fail-open rides on
    `apply_ecb_rates`: no network, no change.

    Months the ECB cannot have published yet (the current month and later)
    are not counted as missing -- `ecb_rates.rates_for_months` drops them
    before asking, so treating them as missing would fetch on every single
    re-match for the whole of the running month."""
    from datetime import date

    from . import ecb_rates

    wanted = ecb_months_for(label, transactions)
    if not wanted:
        return cfg
    now = date.today().strftime("%Y-%m")
    publishable = [
        m for m in wanted
        if ecb_rates.month_index(m) <= ecb_rates.month_index(now)
    ]
    have = set((cfg.get("matching") or {}).get("fx_ecb_monthly_rates") or {})
    if not [m for m in publishable if m not in have]:
        return cfg
    return apply_ecb_rates(cfg, publishable)


def _fills_view(tx) -> list[dict]:
    """The coloured cells of a charge's source workbook row (item 162).

    Four keys on every element, always present, so a consumer maps over
    them with no shape checks: `column` (the header text, `""` when the
    column has none), `index` (0-based, the identity when a header
    repeats), `hex` (six uppercase digits, no `#`) and `family` (the
    shade's name, from `ingest.statement_xlsx.colour_family`). The list
    reads left to right and is never empty: the whole key is absent
    instead (parallel-field contract, rule 1).

    Deliberately carries no verdict, no colour-to-meaning map and no
    suggestion. Whether orange means anything is Criss's to say, not the
    tool's; `entry_status` stays the only thing a colour decides.
    """
    return [
        {
            "column": f.column,
            "index": f.index,
            "hex": f.hex,
            "family": f.family,
        }
        for f in tx.fills
    ]
