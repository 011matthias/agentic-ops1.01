"""Pre-write chart-of-accounts (COA) validation gate.

Before any categorized expense line is written to the Zoho Books
journal-entry export, this gate validates that its posting account
exists and is postable in the TARGET legal entity's chart of accounts.
Any line whose account fails validation is DIVERTED to review (account
blanked, a note appended, the categorization source forced to REVIEW),
so a bad / nonexistent / inactive / "DO NOT USE" / non-leaf account
never reaches the Books export.

This is distinct from `categorization_gate.py`. That module is an LLM
categorization-ACCURACY ratchet used in `calibrate`. This module is
account-EXISTENCE / postability validation, run at export time.

The account string validated is `Categorization.zoho_account` — per
Dirk 2026-06-16 (`categorize._carry_zoho_account`), the posting account
on each line comes from the Zoho Expense report's own category
(`receipt.zoho_category`), authoritative for posting; the LLM's COA pick
is secondary. So `zoho_account` is what posts, and what this gate
checks.

Three pieces:

* `validate_postings(receipts, chart, ...)` — PURE; returns a
  `CoaGateReport` with one `LineVerdict` per posting line plus summary
  counts. No mutation.
* `apply_gate(receipts, report, ...)` — returns NEW receipts where every
  non-OK line has its `zoho_account` cleared, a note appended, and its
  `source` set to `ClassificationSource.REVIEW`. OK lines pass through
  unchanged. This is what guarantees a bad account can't be exported.
* `load_entity_chart(json_path, org_id)` — builds a `ChartOfAccounts`
  for ONE legal entity from the gitignored Books COA JSON (the two
  Brisken entities are Corporate Services org_id 822741658 and Cloud
  Services org_id 697686691). The real JSON is sensitive client data and
  is never committed; tests use synthetic in-memory charts only.

`CoaGate` bundles a loaded chart + the run's scope so the export seam
takes one object. A run targets ONE legal entity, so one `CoaGate` per
run.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path

from .ingest.chart_of_accounts import (
    EXPENSE_ACCOUNT_TYPES,
    Account,
    ChartOfAccounts,
)
from .matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)


def _resolve_label(ref: str, chart: ChartOfAccounts) -> Account | None:
    """Resolve a posting-account reference to a chart Account using the
    SAME logic the Zoho export uses (`zoho_export._resolve_account`): exact
    code-or-name first, then the leading token as a code, then the
    remainder as a name. Validating with weaker resolution than the export
    would divert a `"CODE name"` label the export would have resolved — so
    the gate and the export must agree on what resolves."""
    ref = ref.strip()
    if not ref:
        return None
    acct = chart.resolve(ref)
    if acct is None:
        head, _, tail = ref.partition(" ")
        acct = chart.by_code(head.strip())
        if acct is None and tail.strip():
            acct = chart.by_name(tail.strip())
    return acct


class CoaVerdict(str, Enum):
    """The postability verdict for one expense line's posting account.

    Only `OK` lines reach the Books export untouched; every other verdict
    is diverted to review by `apply_gate`.
    """

    OK = "OK"                          # active leaf, not DO-NOT-USE, in scope
    MISSING_ACCOUNT = "MISSING_ACCOUNT"  # zoho_account empty / None
    UNKNOWN = "UNKNOWN"                # does not resolve in the chart
    INACTIVE = "INACTIVE"             # resolves but not active
    DO_NOT_USE = "DO_NOT_USE"         # resolves but is_do_not_use
    NON_LEAF = "NON_LEAF"             # resolves but a parent / header account
    OUT_OF_SCOPE = "OUT_OF_SCOPE"     # postable but root_group not in scope


# Human-readable reason fragments for the appended review note, keyed by
# verdict. Kept terse; the note also carries the account string + entity.
_VERDICT_REASON: dict[CoaVerdict, str] = {
    CoaVerdict.MISSING_ACCOUNT: "no posting account on the line",
    CoaVerdict.UNKNOWN: "account not found in chart",
    CoaVerdict.INACTIVE: "account is inactive",
    CoaVerdict.DO_NOT_USE: "account is marked DO NOT USE",
    CoaVerdict.NON_LEAF: "account is a parent/header, not postable",
    CoaVerdict.OUT_OF_SCOPE: "account is outside the run's scope groups",
}


@dataclass(frozen=True)
class LineVerdict:
    """The validation result for one posting line.

    Identifies the line by its receipt `document_id` and the line item's
    index within that receipt, so `apply_gate` can divert exactly the
    failing lines. `zoho_account` is the raw account string that was
    validated (carried for the review note). `account` is the resolved
    chart Account when the string resolved, else None.
    """

    document_id: str
    line_index: int
    zoho_account: str | None
    verdict: CoaVerdict
    account: Account | None = None

    @property
    def is_ok(self) -> bool:
        return self.verdict is CoaVerdict.OK


@dataclass(frozen=True)
class CoaGateReport:
    """All per-line verdicts for a run plus summary counts.

    `entity` labels the target legal entity (the org id or its name) for
    the review notes. `counts` maps each `CoaVerdict` value to how many
    lines got it. `verdicts` is one `LineVerdict` per posting line, in
    receipt-then-line order.
    """

    entity: str
    verdicts: tuple[LineVerdict, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def n_lines(self) -> int:
        return len(self.verdicts)

    @property
    def n_ok(self) -> int:
        return sum(1 for v in self.verdicts if v.is_ok)

    @property
    def n_diverted(self) -> int:
        return self.n_lines - self.n_ok

    @property
    def all_ok(self) -> bool:
        return self.n_diverted == 0

    def failing(self) -> tuple[LineVerdict, ...]:
        """The non-OK verdicts (the lines `apply_gate` diverts)."""
        return tuple(v for v in self.verdicts if not v.is_ok)


def classify_account(
    zoho_account: str | None,
    chart: ChartOfAccounts,
    *,
    scope_groups: Iterable[str] | None = None,
    types: Iterable[str] = EXPENSE_ACCOUNT_TYPES,
) -> tuple[CoaVerdict, Account | None]:
    """Verdict + resolved Account for one posting-account string.

    Resolution mirrors the export's own `ChartOfAccounts.resolve` (exact
    code, then exact name). The checks are ordered most-specific-failure
    first so a single, actionable reason is reported:

    1. empty / None        -> MISSING_ACCOUNT
    2. does not resolve     -> UNKNOWN
    3. not active           -> INACTIVE
    4. DO NOT USE           -> DO_NOT_USE
    5. parent / header      -> NON_LEAF
    6. scope_groups set and root_group not in it -> OUT_OF_SCOPE
    7. otherwise            -> OK

    `types` is intentionally NOT a divert reason here. A line's account
    type rarely matters to "can this post"; the type filter is the
    candidate-set narrower used when BUILDING the postable set, and is
    applied to the OK check only when an explicit `types` set is given
    that the account falls outside of. Keeping the account-type check as
    a soft narrower (it widens OK by default to EXPENSE_ACCOUNT_TYPES)
    avoids diverting a legitimately-posted liability/asset card line that
    the report itself produced.
    """
    ref = (zoho_account or "").strip()
    if not ref:
        return CoaVerdict.MISSING_ACCOUNT, None

    account = _resolve_label(ref, chart)
    if account is None:
        return CoaVerdict.UNKNOWN, None

    if not account.is_active:
        return CoaVerdict.INACTIVE, account
    if account.is_do_not_use:
        return CoaVerdict.DO_NOT_USE, account

    # Leaf check: a parent / header account is not postable in Zoho.
    if account.name in chart._parent_names():  # noqa: SLF001 (intentional reuse)
        return CoaVerdict.NON_LEAF, account

    if scope_groups is not None:
        scope_set = {g.strip() for g in scope_groups}
        if chart.root_group(account) not in scope_set:
            return CoaVerdict.OUT_OF_SCOPE, account

    return CoaVerdict.OK, account


def validate_postings(
    receipts: Sequence[Receipt],
    chart: ChartOfAccounts,
    *,
    scope_groups: Iterable[str] | None = None,
    types: Iterable[str] = EXPENSE_ACCOUNT_TYPES,
    entity: str = "",
) -> CoaGateReport:
    """Validate every categorized posting line across `receipts`.

    Pure: reads receipts + chart, returns a `CoaGateReport`. One
    `LineVerdict` per line item that carries a categorization (a line with
    no categorization has no posting account to validate, and is skipped;
    the export already flags it `(uncategorized - assign)`).

    `scope_groups` restricts OK to lines whose account's `root_group` is
    in the set (the same card-expense scope the export's
    `postable_expense_accounts` applies). `entity` labels the target legal
    entity for the review notes.
    """
    verdicts: list[LineVerdict] = []
    counts: dict[str, int] = {v.value: 0 for v in CoaVerdict}

    for receipt in receipts:
        for idx, item in enumerate(receipt.line_items):
            cat = item.categorization
            if cat is None:
                continue
            verdict, account = classify_account(
                cat.zoho_account, chart, scope_groups=scope_groups, types=types
            )
            counts[verdict.value] += 1
            verdicts.append(
                LineVerdict(
                    document_id=receipt.document_id,
                    line_index=idx,
                    zoho_account=cat.zoho_account,
                    verdict=verdict,
                    account=account,
                )
            )

    return CoaGateReport(entity=entity, verdicts=tuple(verdicts), counts=counts)


def _review_note(verdict: LineVerdict, entity: str) -> str:
    """The note appended to a diverted line, e.g.
    `account 'Z999 Bogus' not postable in 822741658: UNKNOWN (account
    not found in chart)`."""
    acct = verdict.zoho_account or "(none)"
    reason = _VERDICT_REASON.get(verdict.verdict, "")
    where = entity or "target entity"
    base = f"account {acct!r} not postable in {where}: {verdict.verdict.value}"
    return f"{base} ({reason})" if reason else base


def apply_gate(
    receipts: Sequence[Receipt],
    report: CoaGateReport,
) -> list[Receipt]:
    """Return NEW receipts with every non-OK line diverted to review.

    For each failing `LineVerdict`: the line item's `zoho_account` is
    cleared, a note is appended to the categorization `reasoning`, and the
    `source` is forced to `ClassificationSource.REVIEW`. OK lines pass
    through unchanged; receipts with no failing line are returned as-is
    (same object). Pure: does not mutate inputs (frozen dataclasses,
    rebuilt via `replace`).

    This is the guarantee step: after `apply_gate`, no line carries a
    posting account that failed validation, so `build_journal_rows`
    leaves every such line flagged `(uncategorized - assign)` rather than
    resolving a bad account.
    """
    # Group the failing line indices by receipt for an O(1) lookup.
    fails_by_doc: dict[str, dict[int, LineVerdict]] = {}
    for v in report.failing():
        fails_by_doc.setdefault(v.document_id, {})[v.line_index] = v

    out: list[Receipt] = []
    for receipt in receipts:
        fail_map = fails_by_doc.get(receipt.document_id)
        if not fail_map:
            out.append(receipt)
            continue

        new_items: list[LineItem] = []
        for idx, item in enumerate(receipt.line_items):
            verdict = fail_map.get(idx)
            cat = item.categorization
            if verdict is None or cat is None:
                new_items.append(item)
                continue
            note = _review_note(verdict, report.entity)
            reasoning = f"{cat.reasoning} | {note}" if cat.reasoning else note
            new_items.append(
                replace(
                    item,
                    categorization=replace(
                        cat,
                        zoho_account=None,
                        source=ClassificationSource.REVIEW,
                        reasoning=reasoning,
                    ),
                )
            )
        out.append(replace(receipt, line_items=tuple(new_items)))

    return out


@dataclass(frozen=True)
class CoaGate:
    """A loaded chart + the run's scope, bundled for the export seam.

    A run targets ONE legal entity, so one `CoaGate` per run. The export
    function (`write_zoho_export` / `build_journal_rows`) takes a
    `CoaGate | None`; None = no validation (existing behavior, byte for
    byte). `run(receipts)` validates then diverts, returning
    `(new_receipts, report)`.
    """

    chart: ChartOfAccounts
    scope_groups: tuple[str, ...] | None = None
    types: tuple[str, ...] = EXPENSE_ACCOUNT_TYPES
    entity: str = ""

    def validate(self, receipts: Sequence[Receipt]) -> CoaGateReport:
        return validate_postings(
            receipts,
            self.chart,
            scope_groups=self.scope_groups,
            types=self.types,
            entity=self.entity,
        )

    def run(self, receipts: Sequence[Receipt]) -> tuple[list[Receipt], CoaGateReport]:
        """Validate + divert in one call. Returns the gated receipts and
        the report (counts for logging / surfacing)."""
        report = self.validate(receipts)
        return apply_gate(receipts, report), report


# ── entity chart loader ─────────────────────────────────────────────


def load_books_coa_json(json_path: str | Path) -> dict:
    """Load the multi-entity Books COA JSON. The shape is

        { "<org_id>": { "org": {...}, "accounts": [ {...}, ... ] }, ... }

    The real file is sensitive client data and is never committed.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Books COA JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def chart_for_org(data: dict, org_id: str | int) -> ChartOfAccounts:
    """Build a `ChartOfAccounts` for ONE entity from already-loaded
    multi-entity COA JSON. `org_id` keys the entity (str or int; coerced
    to str). The entity's `accounts` list uses the same field names
    `ChartOfAccounts.from_api` consumes."""
    key = str(org_id)
    entity = data.get(key)
    if entity is None:
        available = ", ".join(sorted(data.keys())) or "(none)"
        raise KeyError(
            f"org_id {key!r} not in COA JSON; available entities: {available}"
        )
    accounts = entity.get("accounts") or []
    return ChartOfAccounts.from_api(accounts)


def load_entity_chart(json_path: str | Path, org_id: str | int) -> ChartOfAccounts:
    """Load the Books COA JSON and build the chart for ONE entity. The
    convenience wrapper over `load_books_coa_json` + `chart_for_org`."""
    return chart_for_org(load_books_coa_json(json_path), org_id)
