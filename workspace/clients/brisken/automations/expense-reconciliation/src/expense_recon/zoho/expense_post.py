"""Turn the reviewed expense export into Zoho expenses, and post them once.

Three jobs, in order: read the CSV a human actually reviewed, build a
payload whose every account is a resolved numeric id, and post each one
exactly once through the 4.8 ledger.

**Post the reviewed artifact, not a rebuild.** Entries come from the
expense export CSV rather than from the receipts, so what reaches Zoho is
what someone saw and approved. Same discipline as the journal path and as
`rule_brisken_graph_send_by_id`: an explicit enumeration, never a
regeneration that could drift from what was reviewed.

**One receipt is one expense.** The CSV writes one row per ACCOUNT,
because a split receipt posts to several, and those rows share a
`Reference#` (`build_expense_rows`). Zoho's own model for that is a single
itemized expense with `line_items`, which is what the 2026-09-22 trial
produced (header `Itemized`, 2,400.00 + 447.31 across two COGS accounts).
So rows are grouped back by reference: one purchase, one record, one place
to attach the receipt later. The amounts tie out either way; the grouping
is about the books reading like what happened.

**The audit envelope is built in exactly one place.** In the trial it was
present on 7 of 9 rows and missing on precisely the split, because the
itemized path wrote a different description format. Here every payload,
single or itemized, goes through `audit_note`, so there is no second path
for it to fall out of. `test_expense_post.py` asserts that on both shapes.

**What this refuses.** Deny-by-default, because a wrong expense that posts
cleanly is worse than one that fails:

* any account that does not resolve to a numeric id (`zoho.accounts`)
* a row whose amount is missing or unparseable
* a foreign-currency row. Zoho wants a `currency_id`, not a code, and the
  re-consented grant dropped `settings.READ`, so `/settings/currencies`
  now 401s and there is no way to resolve one. Guessing the base currency
  for a BRL charge would misstate the amount, so it refuses and says why.
* a reference already in the ledger for this org, or in flight, or
  ambiguous
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

from ..output.zoho_expense_export import EXPENSE_COLUMNS
from .accounts import AccountRefusal, ResolvedAccount, resolve_account_id
from .idempotent import PostedConflictError, PostLedger

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import ChartOfAccounts
    from .client import ZohoClient

__all__ = [
    "REFUSAL_AMOUNT",
    "REFUSAL_ACCOUNT",
    "REFUSAL_CURRENCY",
    "REFUSAL_LEDGER",
    "ExpenseGroup",
    "ExpensePlan",
    "ExpensePostReport",
    "PlannedExpense",
    "PostRefusal",
    "audit_note",
    "build_expense_payload",
    "execute_expense_post",
    "group_by_reference",
    "plan_expense_post",
    "read_expense_csv",
]

REFUSAL_ACCOUNT = "account_unresolved"
REFUSAL_AMOUNT = "amount_unreadable"
REFUSAL_CURRENCY = "foreign_currency_unresolvable"
REFUSAL_LEDGER = "already_in_ledger"

AUDIT_PREFIX = "[External Match Audit]"


# ── reading the reviewed artifact ───────────────────────────────────


def read_expense_csv(path: str | Path) -> list[dict[str, str]]:
    """Read an expense export CSV and return its data rows as dicts.

    Stops at the FIRST blank row. `write_zoho_expense_export` appends a
    prose footer (item 94) and any single-currency note under a blank
    row, in the first column only. A reader that merely skipped blanks
    would then hit a one-cell prose line and either fail a column count
    or, worse, parse an English sentence as an expense date.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"expense CSV is empty: {path}") from None
        if tuple(header) != EXPENSE_COLUMNS:
            raise ValueError(
                f"expense CSV header mismatch in {path}: expected "
                f"{list(EXPENSE_COLUMNS)}, found {header}"
            )
        rows: list[dict[str, str]] = []
        for lineno, row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in row):
                break  # footer boundary; everything after is prose
            if len(row) != len(EXPENSE_COLUMNS):
                raise ValueError(
                    f"{path} line {lineno}: expected {len(EXPENSE_COLUMNS)} "
                    f"cells, found {len(row)}"
                )
            rows.append(dict(zip(EXPENSE_COLUMNS, row, strict=True)))
    return rows


@dataclass(frozen=True)
class ExpenseGroup:
    """The rows of ONE purchase: a single row, or the split of a receipt
    across several accounts, sharing a `Reference#`."""

    reference: str
    rows: tuple[dict[str, str], ...]

    @property
    def is_split(self) -> bool:
        return len(self.rows) > 1

    def cell(self, column: str) -> str:
        """A header-level value, taken from the first row. Date, card,
        vendor and currency are per-expense, not per-line."""
        return (self.rows[0].get(column) or "").strip()


def group_by_reference(rows: "list[dict[str, str]]") -> list[ExpenseGroup]:
    """Group rows into purchases, preserving first-appearance order.

    A row with an EMPTY reference gets a group of its own rather than
    joining every other blank-referenced row. Merging on a shared absence
    would fuse unrelated purchases into one expense, which is the kind of
    quiet wrong that ties out to the cent and still misstates the books.
    """
    groups: list[ExpenseGroup] = []
    index: dict[str, int] = {}
    for row in rows:
        ref = (row.get("Reference#") or "").strip()
        if ref and ref in index:
            pos = index[ref]
            existing = groups[pos]
            groups[pos] = ExpenseGroup(
                reference=ref, rows=existing.rows + (row,)
            )
            continue
        if ref:
            index[ref] = len(groups)
        groups.append(ExpenseGroup(reference=ref, rows=(row,)))
    return groups


# ── payload ─────────────────────────────────────────────────────────


def audit_note(group: ExpenseGroup, *, source: str) -> str:
    """The audit envelope. The ONLY place it is built.

    Every payload passes through here, single-account or itemized, which
    is the fix for the trial's 7-of-9: there the split took a different
    code path and wrote a different description, so the envelope was
    absent on exactly the row whose provenance mattered most.
    """
    own = group.cell("Expense Description")
    parts = [
        f"{AUDIT_PREFIX} Ref: {group.reference or '(none)'}",
        f"Source: {source}",
    ]
    if group.is_split:
        parts.append(f"Split: {len(group.rows)} accounts")
    entity = group.cell("Legal Entity")
    if entity:
        parts.append(f"Entity: {entity}")
    envelope = " | ".join(parts)
    return f"{envelope} | {own}" if own else envelope


def _amount(text: str) -> Decimal | None:
    cleaned = (text or "").strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


@dataclass(frozen=True)
class PostRefusal:
    reference: str
    reason: str
    detail: str


@dataclass(frozen=True)
class PlannedExpense:
    """One purchase, resolved and ready to POST."""

    reference: str
    payload: dict
    content_hash: str
    total: Decimal


def build_expense_payload(
    group: ExpenseGroup,
    coa: "ChartOfAccounts",
    *,
    paid_through_account_id: str,
    base_currency: str,
    source: str = "expense-recon",
    org_id: str | None = None,
) -> "dict | PostRefusal":
    """The Zoho POST body for one purchase, or a refusal naming why not.

    `org_id` is passed to account resolution so this org's category
    fallback applies; without it, a category label refuses as before.
    """
    currency = group.cell("Currency Code") or base_currency
    if currency.upper() != base_currency.upper():
        return PostRefusal(
            reference=group.reference,
            reason=REFUSAL_CURRENCY,
            detail=(
                f"{currency} is not the org's base currency ({base_currency}) "
                "and Zoho needs a currency_id, not a code. The grant no "
                "longer carries settings.READ, so /settings/currencies "
                "cannot resolve one; posting it would misstate the amount"
            ),
        )

    lines: list[dict] = []
    total = Decimal("0")
    for row in group.rows:
        amount = _amount(row.get("Expense Amount", ""))
        if amount is None:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_AMOUNT,
                detail=(
                    "a line has no readable Expense Amount; the export "
                    "writes a blank amount when a receipt's total was "
                    "never read, and a blank is not a zero"
                ),
            )
        resolved = resolve_account_id(
            row.get("Expense Account"), coa, org_id=org_id
        )
        if isinstance(resolved, AccountRefusal):
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_ACCOUNT,
                detail=f"{resolved.reason}: {resolved.detail}",
            )
        assert isinstance(resolved, ResolvedAccount)
        total += amount
        lines.append(
            {
                "account_id": resolved.account_id,
                "amount": float(amount),
                "description": (row.get("Expense Description") or "").strip(),
            }
        )

    payload: dict = {
        "date": group.cell("Expense Date"),
        "paid_through_account_id": paid_through_account_id,
        "reference_number": group.reference,
        "description": audit_note(group, source=source),
        "currency_code": currency,
    }
    if len(lines) == 1:
        # A single-account expense posts flat; Zoho's line_items form is
        # for genuine splits and shows as "Itemized" in the UI.
        payload["account_id"] = lines[0]["account_id"]
        payload["amount"] = lines[0]["amount"]
    else:
        payload["line_items"] = lines
    vendor = group.cell("Vendor")
    if vendor:
        # MEASURED 2026-09-23, and the hope below did not survive: Zoho
        # accepts `vendor_name` and stores NOTHING. All 13 rehearsal
        # expenses read back `vendor_name=""` and `vendor_id=""`, so the
        # field is silently discarded without a contact to link to, and
        # it does NOT keep the name visible as this once assumed.
        # Vendor attribution is therefore absent from every posted
        # record, and the audit note does not carry it either. Fixing it
        # means resolving contacts to a real `vendor_id`, or folding the
        # vendor into `audit_note`. Left in place because it is inert
        # rather than harmful, and removing it would hide the gap.
        payload["vendor_name"] = vendor
    return payload


def content_hash(payload: dict) -> str:
    """A stable hash of what is being posted, so the ledger can tell a
    re-run of the SAME expense from a changed one wearing the same
    reference."""
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ── planning ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpensePlan:
    org_id: str
    postable: tuple[PlannedExpense, ...] = field(default_factory=tuple)
    refusals: tuple[PostRefusal, ...] = field(default_factory=tuple)

    @property
    def total(self) -> Decimal:
        return sum((p.total for p in self.postable), Decimal("0"))


def plan_expense_post(
    groups: "list[ExpenseGroup]",
    coa: "ChartOfAccounts",
    ledger: PostLedger,
    *,
    org_id: str,
    paid_through_account_id: str,
    base_currency: str,
    source: str = "expense-recon",
) -> ExpensePlan:
    """Resolve every group and cross-reference the ledger. Pure apart
    from ledger READS; posts nothing."""
    postable: list[PlannedExpense] = []
    refusals: list[PostRefusal] = []
    for group in groups:
        built = build_expense_payload(
            group,
            coa,
            paid_through_account_id=paid_through_account_id,
            base_currency=base_currency,
            source=source,
            org_id=org_id,
        )
        if isinstance(built, PostRefusal):
            refusals.append(built)
            continue
        existing = ledger.status_for(org_id, group.reference)
        if existing is not None:
            refusals.append(
                PostRefusal(
                    reference=group.reference,
                    reason=REFUSAL_LEDGER,
                    detail=(
                        f"the ledger already holds {group.reference!r} for org "
                        f"{org_id} in state {existing.state!r}; this expense "
                        "has been posted or is unresolved from an earlier run"
                    ),
                )
            )
            continue
        payload = built
        total = Decimal(str(payload.get("amount", 0))) if "amount" in payload else sum(
            (Decimal(str(li["amount"])) for li in payload.get("line_items", ())),
            Decimal("0"),
        )
        postable.append(
            PlannedExpense(
                reference=group.reference,
                payload=payload,
                content_hash=content_hash(payload),
                total=total,
            )
        )
    return ExpensePlan(
        org_id=org_id, postable=tuple(postable), refusals=tuple(refusals)
    )


# ── posting ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpensePostReport:
    org_id: str
    posted: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    rejected: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    ambiguous: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    aborted: bool = False

    @property
    def ok(self) -> bool:
        return not self.rejected and not self.ambiguous and not self.aborted


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute_expense_post(
    client: "ZohoClient",
    plan: ExpensePlan,
    ledger: PostLedger,
    *,
    go: bool = False,
    expect: int | None = None,
) -> ExpensePostReport:
    """Post each planned expense exactly once.

    Write-ahead intent: the ledger records `inflight` and COMMITS before
    the POST fires, so there is no instant in which an expense can reach
    Zoho without a ledger row. A clean 4xx rejection means Zoho answered
    and wrote nothing, so the intent rolls back and the batch continues.
    Anything else (a timeout, a 5xx, a response with no `expense_id`)
    leaves the state unknown, marks `ambiguous`, and ABORTS the rest:
    continuing past an unknown commit is how one uncertainty becomes
    many.
    """
    if plan.refusals:
        raise ValueError(
            f"refusing to post: the plan carries {len(plan.refusals)} "
            "refusal(s). Fix or drop them first; a partial post leaves a "
            "month half-entered"
        )
    if expect is not None and len(plan.postable) != expect:
        raise ValueError(
            f"expected exactly {expect} expense(s), plan has "
            f"{len(plan.postable)}; refusing the whole batch"
        )
    if not go:
        raise ValueError(
            f"refusing to post {len(plan.postable)} expense(s) without "
            "go=True; print the plan and read it first"
        )

    posted: list[tuple[str, str]] = []
    rejected: list[tuple[str, str]] = []
    ambiguous: list[tuple[str, str]] = []
    aborted = False

    for item in plan.postable:
        try:
            ledger.mark_inflight(
                plan.org_id,
                item.reference,
                item.content_hash,
                now_iso=_now(),
                source="expense",
            )
        except PostedConflictError as exc:
            rejected.append((item.reference, str(exc)))
            continue

        try:
            created = client.create_expense(item.payload)
        except Exception as exc:  # noqa: BLE001 - the split is by status
            status = getattr(exc, "status", None)
            if status is not None and 400 <= int(status) < 500:
                # Zoho answered and wrote nothing: safe to release.
                ledger.remove(plan.org_id, item.reference)
                rejected.append((item.reference, f"{status}: {exc}"))
                continue
            ledger.mark_ambiguous(
                plan.org_id,
                item.reference,
                now_iso=_now(),
                content_hash=item.content_hash,
            )
            ambiguous.append((item.reference, str(exc)))
            aborted = True
            break

        # The ledger's column is named for journals; it stores this
        # expense's id. Reusing the table rather than migrating a live
        # SQLite schema for a name no human reads, the same call item 23
        # made for `category_overrides.zoho_account`.
        ledger.mark_posted(
            plan.org_id,
            item.reference,
            zoho_journal_id=str(created.get("expense_id") or ""),
            entry_number=None,
            now_iso=_now(),
            content_hash=item.content_hash,
        )
        posted.append((item.reference, str(created.get("expense_id") or "")))

    return ExpensePostReport(
        org_id=plan.org_id,
        posted=tuple(posted),
        rejected=tuple(rejected),
        ambiguous=tuple(ambiguous),
        aborted=aborted,
    )
