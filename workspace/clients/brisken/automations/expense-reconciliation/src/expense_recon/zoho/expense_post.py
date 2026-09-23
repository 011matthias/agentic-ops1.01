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
* a foreign-currency row, UNLESS the caller supplies a `currencies` map
  (code -> the target org's numeric `currency_id`). Zoho wants the id, not
  the code. The RATE is never invented: it is read from the reviewed CSV's
  own `Exchange Rate` column, so the posted amount is the one a human
  signed off. Still refused: a currency the target org does not define
  (TEST-BTS has 11 and BRL is not among them), and a foreign row with no
  usable rate, because Zoho would then apply one nobody chose.
* a reference already in the ledger for this org, or in flight, or
  ambiguous
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from collections.abc import Mapping
from typing import TYPE_CHECKING

from ..output.zoho_expense_export import EXPENSE_COLUMNS
from .accounts import AccountRefusal, ResolvedAccount, resolve_account_id
from .idempotent import PostedConflictError, PostLedger
from .occupancy import month_bounds

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import ChartOfAccounts
    from .client import ZohoClient

__all__ = [
    "DEFAULT_STALE_DAYS",
    "MAX_DESCRIPTION_CHARS",
    "REFUSAL_AMOUNT",
    "REFUSAL_ACCOUNT",
    "REFUSAL_CURRENCY",
    "REFUSAL_CURRENCY_UNDEFINED",
    "REFUSAL_EXCHANGE_RATE",
    "REFUSAL_LEDGER",
    "REFUSAL_STALE_DATE",
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
# A foreign currency the TARGET ORG does not define. Distinct from
# REFUSAL_CURRENCY: that one means we cannot resolve a currency at all,
# this one means the org has no such currency and somebody must add it
# there. TEST-BTS defines 11 currencies and BRL is not among them, while
# 20 of July's purchases are BRL.
REFUSAL_CURRENCY_UNDEFINED = "currency_not_defined_in_org"
# A foreign row whose `Exchange Rate` cell is blank or unusable. Posting
# a foreign amount without a rate lets Zoho apply one nobody chose, which
# misstates the amount in exactly the silent way this path refuses.
REFUSAL_EXCHANGE_RATE = "exchange_rate_missing"
# A row dated long before the period being posted. July's batch held a
# 2026-03-30 invoice (ref 360172592, 360Crossmedia EUR 900): four months
# out is not a statement-vs-transaction-date nuance, it is an outlier
# that should reach the books only with a human's explicit sign-off.
REFUSAL_STALE_DATE = "date_precedes_period_window"

AUDIT_PREFIX = "[External Match Audit]"

# How far before a period's first day a purchase may be dated before it
# needs sign-off. 45 days clears the ordinary case (a charge posting in
# the next statement cycle, like July's three June-dated rows) without
# clearing a months-old invoice.
DEFAULT_STALE_DAYS = 45

# Zoho rejects an expense whose description reaches 500 characters
# ("Please ensure that the \"Description\" has less than 500
# characters", 400). Measured 2026-09-23 on two Brazilian grocery
# receipts whose itemisation runs 370 and 459 characters; adding the
# vendor and the original-amount tags to the envelope pushed both over.
MAX_DESCRIPTION_CHARS = 499


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


def audit_note(
    group: ExpenseGroup, *, source: str, original: str = ""
) -> str:
    """The audit envelope. The ONLY place it is built.

    Every payload passes through here, single-account or itemized, which
    is the fix for the trial's 7-of-9: there the split took a different
    code path and wrote a different description, so the envelope was
    absent on exactly the row whose provenance mattered most.

    `original` names the pre-conversion amount and rate for a row posted
    in the statement currency. Without it the books would show a USD
    figure with no trace of the EUR or BRL receipt behind it, and the
    conversion would be unauditable from the record itself.
    """
    own = group.cell("Expense Description")
    parts = [
        f"{AUDIT_PREFIX} Ref: {group.reference or '(none)'}",
        f"Source: {source}",
    ]
    # The vendor rides in the envelope because `vendor_name` does not
    # survive the POST: measured 2026-09-23, all 13 rehearsal expenses
    # read back `vendor_name=""` and `vendor_id=""`. Zoho accepts the
    # field, answers 201 and stores nothing without a contact to link.
    # Without this line a reviewer in the Zoho UI sees no vendor at all,
    # which is the attribution half of what makes a row checkable.
    vendor = group.cell("Vendor")
    if vendor:
        parts.append(f"Vendor: {vendor}")
    if original:
        parts.append(f"Original: {original}")
    if group.is_split:
        parts.append(f"Split: {len(group.rows)} accounts")
    entity = group.cell("Legal Entity")
    if entity:
        parts.append(f"Entity: {entity}")
    envelope = " | ".join(parts)
    if not own:
        return envelope
    full = f"{envelope} | {own}"
    if len(full) <= MAX_DESCRIPTION_CHARS:
        return full

    # Over Zoho's limit. Trim the RECEIPT'S OWN PROSE and never the
    # envelope: the envelope is the audit trail that makes a posted row
    # traceable, while the prose is a line-item list whose tail is the
    # least load-bearing text in the record. The marker states how much
    # was dropped, because a silent truncation reads as a short receipt.
    room = MAX_DESCRIPTION_CHARS - len(envelope) - 3
    if room <= 0:
        # The envelope alone fills the budget. Return it whole rather
        # than cutting audit data; an envelope this size is its own bug
        # and should surface as one.
        return envelope
    template = "... (+{} chars)"
    marker_width = len(template.format("0" * len(str(len(own)))))
    keep = max(0, room - marker_width)
    return f"{envelope} | {own[:keep]}{template.format(len(own) - keep)}"


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


_CENT = Decimal("0.01")


def _to_base(amount: Decimal, rate: Decimal) -> Decimal:
    """One foreign amount in the base currency, rounded to the cent."""
    return (amount * rate).quantize(_CENT, rounding=ROUND_HALF_UP)


def _convert_lines(
    line_amounts: "list[Decimal]", rate: Decimal
) -> "tuple[list[Decimal], Decimal]":
    """Convert a purchase's lines, keeping them summed to the converted
    TOTAL exactly.

    Rounding each line independently does not give the rounded total:
    two lines of 10.005 each round to 10.01 + 10.01 = 20.02 while the
    total rounds to 20.01. So the total is converted once and the
    residual lands on the largest line, the same allocation rule
    `posting_common._posting_amounts` already uses for the split case.
    A one-cent disagreement between an expense and its own line items is
    exactly the kind of quiet wrong that survives review.
    """
    total = _to_base(sum(line_amounts, Decimal("0")), rate)
    out = [_to_base(a, rate) for a in line_amounts]
    residual = total - sum(out, Decimal("0"))
    if residual and out:
        biggest = max(range(len(out)), key=lambda i: out[i])
        out[biggest] += residual
    return out, total


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
    currencies: "Mapping[str, str] | None" = None,
    convert_foreign_to_base: bool = False,
    period: str | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> "dict | PostRefusal":
    """The Zoho POST body for one purchase, or a refusal naming why not.

    `org_id` is passed to account resolution so this org's category
    fallback applies; without it, a category label refuses as before.

    Foreign currency has three policies, checked in this order:

    * `convert_foreign_to_base` posts in the STATEMENT currency, the
      house rule `posting_common` already states for the journal: the
      bank statement is what the company actually paid, so a EUR receipt
      on a USD card posts as `amount x rate` USD. Needs no `currency_id`
      and no paid Zoho plan, and the original amount and rate ride in the
      audit note so the conversion stays auditable from the record.
    * `currencies` (code -> the org's numeric `currency_id`) posts
      NATIVELY in the receipt's own currency. Correct, and blocked on
      TEST-BTS: `plan_name = 'FREE'` rejects any expense whose currency
      is not the org's base, with a 400 naming the plan.
    * neither: refuse, which is the default and keeps deny-by-default.

    The RATE is never invented here under either policy. It comes from
    the reviewed CSV's own `Exchange Rate` cell, so what posts is the
    rate a human signed off rather than one fetched at post time.

    `period` (YYYY-MM) enables the stale-date guard: a purchase dated
    more than `stale_days` before that period's first day refuses rather
    than posting quietly. Omit `period` and the guard is off.
    """
    when_text = group.cell("Expense Date")
    if period:
        window_start, _ = month_bounds(period)
        cutoff = date.fromisoformat(window_start) - timedelta(days=stale_days)
        try:
            when = date.fromisoformat(when_text)
        except ValueError:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_STALE_DATE,
                detail=(
                    f"date {when_text!r} is not a readable ISO date, so it "
                    f"cannot be checked against the {period} window; a row "
                    "whose date cannot be verified is not posted"
                ),
            )
        if when < cutoff:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_STALE_DATE,
                detail=(
                    f"dated {when.isoformat()}, more than {stale_days} days "
                    f"before {period} begins ({window_start}); cutoff is "
                    f"{cutoff.isoformat()}. An outlier this far out needs "
                    "explicit sign-off rather than posting silently with "
                    "the month"
                ),
            )

    currency = (group.cell("Currency Code") or base_currency).upper()
    base = base_currency.upper()
    fx: dict[str, object] = {}
    original = ""
    convert = False
    rate = Decimal("1")
    if currency != base and convert_foreign_to_base:
        got = _amount(group.cell("Exchange Rate"))
        if got is None or got <= 0:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_EXCHANGE_RATE,
                detail=(
                    f"the {currency} row carries no usable Exchange Rate "
                    f"({group.cell('Exchange Rate')!r}), so it cannot be "
                    "converted to the statement currency; inventing a rate "
                    "would misstate what the card was charged"
                ),
            )
        rate = got
        convert = True
    elif currency != base:
        if not currencies:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_CURRENCY,
                detail=(
                    f"{currency} is not the org's base currency ({base}) and "
                    "Zoho needs a currency_id, not a code; no currency map "
                    "was supplied, so posting it would misstate the amount"
                ),
            )
        currency_id = currencies.get(currency)
        if not currency_id:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_CURRENCY_UNDEFINED,
                detail=(
                    f"org {org_id or '(unknown)'} defines no {currency} "
                    f"currency (it has: {', '.join(sorted(currencies)) or 'none'}). "
                    "Add it in that org's settings before posting; this is a "
                    "config gap in the target org, not a problem with the data"
                ),
            )
        rate = _amount(group.cell("Exchange Rate"))
        if rate is None or rate <= 0:
            return PostRefusal(
                reference=group.reference,
                reason=REFUSAL_EXCHANGE_RATE,
                detail=(
                    f"the {currency} row carries no usable Exchange Rate "
                    f"({group.cell('Exchange Rate')!r}); without one Zoho "
                    "applies a rate nobody chose and the posted amount stops "
                    "matching the reviewed export"
                ),
            )
        fx = {"currency_id": currency_id, "exchange_rate": float(rate)}

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

    if convert:
        # Post what hit the card. The lines are converted together so
        # they still sum to the converted total exactly.
        converted, total_base = _convert_lines(
            [Decimal(str(li["amount"])) for li in lines], rate
        )
        for li, value in zip(lines, converted, strict=True):
            li["amount"] = float(value)
        original = f"{currency} {total:f} @ {rate:f}"
        total = total_base
        currency = base

    payload: dict = {
        "date": when_text,
        "paid_through_account_id": paid_through_account_id,
        "reference_number": group.reference,
        "description": audit_note(group, source=source, original=original),
        "currency_code": currency,
        **fx,
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
    currencies: "Mapping[str, str] | None" = None,
    convert_foreign_to_base: bool = False,
    period: str | None = None,
    stale_days: int = DEFAULT_STALE_DAYS,
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
            currencies=currencies,
            convert_foreign_to_base=convert_foreign_to_base,
            period=period,
            stale_days=stale_days,
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
