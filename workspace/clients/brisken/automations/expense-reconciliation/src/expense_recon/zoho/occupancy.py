"""Month-occupancy pre-flight: refuse to post into a month someone else
has already entered.

The 4.8 ledger guarantees THIS tool never posts the same entry twice. It
cannot see the other writer. Criss enters these charges by hand, in
catch-up bursts, weeks after the fact, and a live probe on 2026-09-22
found no bank feed anywhere in the tenant: **0 of 39 sampled expense rows
carried `imported_transactions`**. Corporate Services' 108 July rows were
created across 13 days ending 09-08, 45 of them on that last day. So the
realistic way this tool doubles a month is not a re-run, it is posting
into a month a human already did.

Nothing in the ledger would notice that, because from the ledger's side a
first post into a fresh month looks identical whether or not Zoho already
holds 108 rows for it. Hence a second gate that asks Zoho instead of
asking our own records.

Two refusals, deliberately different in kind:

* `LOCKED_PERIOD` is a standing rule and needs no network call. July 2026
  is closed **in the production orgs**: 108 hand-entered rows in Corporate
  Services, 10 in Cloud Services. It is configuration rather than a
  constant so a closed month can be added without a code change, but the
  default is not empty.
* `ALREADY_OCCUPIED` is measured per run, against the target org, card and
  month. This is what makes the guard hold for months nobody has thought
  to lock yet, which is every month until it goes wrong once.

**The standing lock is production-only, and that is the point of it.**
What makes July dangerous is 118 real rows a human typed, and those exist
only in the production orgs. In the sandbox July is empty and is the most
useful month to rehearse, because a full month is the shape the tool has
to survive. A global lock would forbid exactly the rehearsal that de-risks
the real run, which is a safety rule protecting nothing at the cost of the
thing it exists to make safe. So `LOCKED_PERIOD` applies when
`is_production_org(org_id)`, and a sandbox run says so in its verdict
rather than skipping the rule silently.

`ALREADY_OCCUPIED` is NOT waived for the sandbox. A rehearsal that
double-posts is still a bug, and catching it there is the whole reason to
rehearse.

Deny-by-default throughout: an unreadable answer refuses, because "I could
not tell whether this month is occupied" and "this month is empty" must
never take the same branch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING

from .orgs import is_production_org

if TYPE_CHECKING:
    from .client import ZohoClient

__all__ = [
    "VERDICT_ALREADY_OCCUPIED",
    "VERDICT_CLEAR",
    "VERDICT_LOCKED_PERIOD",
    "VERDICT_UNVERIFIABLE",
    "DEFAULT_LOCKED_PERIODS",
    "OccupancyVerdict",
    "check_month_occupancy",
    "month_bounds",
]

VERDICT_CLEAR = "CLEAR"
VERDICT_ALREADY_OCCUPIED = "ALREADY_OCCUPIED"
VERDICT_LOCKED_PERIOD = "LOCKED_PERIOD"
VERDICT_UNVERIFIABLE = "UNVERIFIABLE"

# Months closed to posting regardless of what a live query returns.
# 2026-07 is here because it is fully hand-entered in both target orgs.
DEFAULT_LOCKED_PERIODS = frozenset({"2026-07"})


@dataclass(frozen=True)
class OccupancyVerdict:
    """The pre-flight answer. `ok` is true ONLY for VERDICT_CLEAR, so a
    caller cannot accidentally treat "unverifiable" as permission."""

    verdict: str
    period: str
    org_id: str
    detail: str
    existing_count: int = 0
    sample: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.verdict == VERDICT_CLEAR


def month_bounds(period: str) -> tuple[str, str]:
    """Inclusive ISO date bounds for a `YYYY-MM` period.

    Computed rather than tabled so the December rollover and February in a
    leap year are arithmetic, not a maintained list.
    """
    text = (period or "").strip()
    parts = text.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError(f"period must be YYYY-MM, got {period!r}")
    try:
        year, month = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ValueError(f"period must be YYYY-MM, got {period!r}") from exc
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range in {period!r}")
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    # Last day of `month` = day before the first of the next month.
    last = date(next_year, next_month, 1) - timedelta(days=1)
    return f"{year:04d}-{month:02d}-01", last.isoformat()


def _paid_through_matches(record: "dict", paid_through: str | None) -> bool:
    """Whether an existing Zoho expense sits on the card we are about to
    post to. With no card named, every row in the month counts: a
    month-wide post has a month-wide blast radius.
    """
    if not paid_through:
        return True
    name = (record.get("paid_through_account_name") or "").strip().lower()
    return name == paid_through.strip().lower()


def check_month_occupancy(
    client: "ZohoClient",
    *,
    org_id: str,
    period: str,
    paid_through: str | None = None,
    locked_periods: "frozenset[str] | set[str] | None" = None,
    sample_size: int = 5,
) -> OccupancyVerdict:
    """Ask Zoho whether this org, card and month already hold expenses.

    Returns CLEAR only when the period is not locked AND the live query
    succeeded AND it came back empty. Every other outcome refuses.
    """
    locked = DEFAULT_LOCKED_PERIODS if locked_periods is None else locked_periods
    # Validate the period before anything else, so a malformed period is a
    # loud ValueError rather than a query that quietly matches nothing.
    start, end = month_bounds(period)

    # The standing lock guards real books. A clone has no hand-entered
    # rows to duplicate, and July is the month most worth rehearsing.
    if period in locked and is_production_org(org_id):
        return OccupancyVerdict(
            verdict=VERDICT_LOCKED_PERIOD,
            period=period,
            org_id=org_id,
            detail=(
                f"{period} is a locked period in production org {org_id}: it "
                "is already entered by hand and posting into it would "
                "duplicate real rows. Rehearse it in the sandbox instead, or "
                "unlock it deliberately if that is genuinely wrong"
            ),
        )

    try:
        existing = client.list_expenses(date_start=start, date_end=end)
    except Exception as exc:  # noqa: BLE001 - any failure must refuse
        return OccupancyVerdict(
            verdict=VERDICT_UNVERIFIABLE,
            period=period,
            org_id=org_id,
            detail=(
                f"could not read existing {period} expenses for org {org_id} "
                f"({type(exc).__name__}: {exc}). Refusing: an unreadable "
                "month is not an empty one"
            ),
        )

    hits = [r for r in existing if _paid_through_matches(r, paid_through)]
    if hits:
        sample = tuple(
            f"{r.get('date')} {r.get('total')} "
            f"{(r.get('reference_number') or r.get('description') or '')[:40]}".strip()
            for r in hits[:sample_size]
        )
        where = f" on {paid_through!r}" if paid_through else ""
        return OccupancyVerdict(
            verdict=VERDICT_ALREADY_OCCUPIED,
            period=period,
            org_id=org_id,
            detail=(
                f"org {org_id} already holds {len(hits)} expense(s) for "
                f"{period}{where}. Posting would duplicate them; clear them "
                "or pick a different month"
            ),
            existing_count=len(hits),
            sample=sample,
        )

    waived = (
        f" (the {period} lock is waived here: {org_id} is not a production org)"
        if period in locked
        else ""
    )
    return OccupancyVerdict(
        verdict=VERDICT_CLEAR,
        period=period,
        org_id=org_id,
        detail=(
            f"org {org_id} holds no {period} expenses"
            + (f" on {paid_through!r}" if paid_through else "")
            + waived
        ),
    )
