"""Empty the TEST-BTS sandbox so a rehearsal starts from a known state.

A rehearsal is only evidence if it starts clean, and TEST-BTS accumulates
rows from every run. This deletes them. It is the only destructive path in
the tool, so the guards are the module.

**Why a clone is the dangerous case.** TEST-BTS was cloned from a
production org. Same chart, same account-name spellings, same id shape.
Every signal that would normally shout "this is only a test" is missing,
and a sandbox reset pointed one digit wrong is an irreversible delete of a
client's books. So:

* The org is asserted against `SANDBOX_ORG_ID` by equality, before
  anything is read and long before anything is deleted. Production is not
  merely absent from a list, it is refused by name.
* Deletion is by explicitly enumerated id, one call each. No filter, no
  bulk endpoint, no "delete everything matching". Same reasoning as
  `rule_brisken_graph_send_by_id`: a query that decides what to destroy
  can always match one row more than you meant.
* `plan_reset` is pure and read-only. Nothing is deleted without a second
  call and an explicit `go=True`, so the plan can always be printed and
  read first.
* The caller verifies afterwards by re-listing, because a 200 per delete
  means each call was accepted, not that the org is empty.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .orgs import PRODUCTION_ORG_IDS, SANDBOX_ORG_ID

if TYPE_CHECKING:
    from .client import ZohoClient

__all__ = [
    "ResetPlan",
    "ResetReport",
    "SandboxGuardError",
    "execute_reset",
    "plan_reset",
]


class SandboxGuardError(RuntimeError):
    """Raised when a reset is aimed anywhere but the sandbox."""


@dataclass(frozen=True)
class ResetPlan:
    """Exactly which expenses would be deleted, enumerated by id."""

    org_id: str
    expense_ids: tuple[str, ...]
    lines: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.expense_ids)


@dataclass(frozen=True)
class ResetReport:
    org_id: str
    deleted: tuple[str, ...] = field(default_factory=tuple)
    failed: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    remaining: int | None = None

    @property
    def ok(self) -> bool:
        """Clean only when every delete succeeded AND a re-list confirms
        the org is empty. `remaining is None` means the verification did
        not run, which is not the same as passing."""
        return not self.failed and self.remaining == 0


def _assert_sandbox(org_id: str) -> None:
    org = str(org_id or "").strip()
    if org in PRODUCTION_ORG_IDS:
        raise SandboxGuardError(
            f"refusing to reset org {org}: that is one of Brisken's real "
            "books. The sandbox is " + SANDBOX_ORG_ID
        )
    if org != SANDBOX_ORG_ID:
        raise SandboxGuardError(
            f"refusing to reset org {org!r}: resets are allowed only in the "
            f"sandbox org {SANDBOX_ORG_ID} (TEST-BTS). An org this code does "
            "not recognise is not safe by default"
        )


def plan_reset(client: "ZohoClient", *, org_id: str) -> ResetPlan:
    """Enumerate the sandbox's expenses. Read-only; deletes nothing."""
    _assert_sandbox(org_id)
    rows = client.list_expenses()
    ids: list[str] = []
    lines: list[str] = []
    for r in rows:
        eid = str(r.get("expense_id") or "").strip()
        if not eid:
            continue
        ids.append(eid)
        lines.append(
            f"{eid}  {r.get('date')}  {r.get('total')}  "
            f"{r.get('paid_through_account_name') or '(no card)'}  "
            f"{(r.get('reference_number') or r.get('description') or '')[:32]}"
        )
    return ResetPlan(org_id=org_id, expense_ids=tuple(ids), lines=tuple(lines))


def execute_reset(
    client: "ZohoClient", plan: ResetPlan, *, go: bool = False
) -> ResetReport:
    """Delete every expense in `plan`, then verify the org is empty.

    Refuses without `go`. Keeps going past an individual failure so the
    report names all of them rather than only the first, but a single
    failure still makes the report not-ok.
    """
    _assert_sandbox(plan.org_id)
    if not go:
        raise SandboxGuardError(
            f"refusing to delete {len(plan)} expense(s) from {plan.org_id} "
            "without go=True; print the plan and read it first"
        )

    deleted: list[str] = []
    failed: list[tuple[str, str]] = []
    for eid in plan.expense_ids:
        try:
            client.delete_expense(eid)
        except Exception as exc:  # noqa: BLE001 - report all, not just the first
            failed.append((eid, f"{type(exc).__name__}: {exc}"))
        else:
            deleted.append(eid)

    # A 200 per call says each was accepted. Only a re-list says the org
    # is actually empty, which is the claim a rehearsal depends on.
    try:
        remaining: int | None = len(client.list_expenses())
    except Exception:  # noqa: BLE001 - unverified is not verified
        remaining = None

    return ResetReport(
        org_id=plan.org_id,
        deleted=tuple(deleted),
        failed=tuple(failed),
        remaining=remaining,
    )
