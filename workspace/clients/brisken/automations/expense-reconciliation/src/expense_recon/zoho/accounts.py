"""Numeric `account_id` resolution for the API posting path.

The file exports post an account NAME and a human reads it. The API posts
an `account_id` and nobody reads it, which is why this module exists and
why it refuses instead of guessing.

**The failure this prevents, measured.** In the 2026-09-22 TEST-BTS trial,
expenses were posted with the account passed as a NAME. Zoho did not
reject them and did not warn: it accepted every row and silently assigned
its own default, so **6 of 9 rows landed in `Office Infra and Admin`**
instead of the account they were meant for, with a 201 and a valid
`expense_id` on each. A wrong account that posts cleanly is worse than one
that fails, because nothing downstream ever asks again.

So every refusal here is deliberate. `resolve_account_id` returns either a
`ResolvedAccount` carrying a real id, or an `AccountRefusal` naming why
not; there is no third branch and no default. The caller reports the
refusals and posts nothing, which is the same deny-by-default shape the
4.8 ledger uses for duplicates.

Resolution order is NOT re-derived here. It comes from
`output.posting_common.resolve_ref`, the one function the file exports
also use, so the CSV a human reviews and the payload the API receives can
never disagree about which account a reference meant.

**Postable is decided by the org's own rules, and there are two.** An org
Dirk curated (`curated_leaves`, the `Expense Relevant` marking) is judged
by that marking alone, because it already answers both questions a chart
cannot: which roll-ups take postings and which subtrees a card may reach.
The marking makes 35 chart PARENTS postable across the three orgs
(`Travel Expense`, `IT: Computer and Internet Expenses`, ...) and every
COGS roll-up not, and Zoho does accept a posting on a parent: Brisken's
own books hold 8 such expenses over 2024-09..2026-09. So the chart's
parent/leaf shape is the wrong test there, and applying it would refuse
a fifth of what was approved. An org nobody curated (the sandbox) has
only its chart, so there a parent refuses, the rule
`coa_gate.classify_account` applies at export.

The category-to-account fallback table that lived beside this module is
retired: a category label is not an account, and every reference now has
to name one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..output.posting_common import (
    _CARD_ACCOUNT,
    _REIMBURSABLE_PLACEHOLDER,
    _UNCATEGORIZED,
    _UNMAPPED,
    resolve_ref,
)
from ..output.zoho_expense_export import (
    ENTITY_PLACEHOLDER,
    PAID_THROUGH_PLACEHOLDER,
)
from . import curated_leaves

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import Account, ChartOfAccounts

__all__ = [
    "REASON_CHART_ORG_MISMATCH",
    "REASON_DO_NOT_USE",
    "REASON_EMPTY",
    "REASON_INACTIVE",
    "REASON_NON_LEAF",
    "REASON_NOT_EXPENSE_RELEVANT",
    "REASON_NO_ACCOUNT_ID",
    "REASON_OUT_OF_SCOPE",
    "REASON_PLACEHOLDER",
    "REASON_UNKNOWN",
    "AccountRefusal",
    "ResolvedAccount",
    "resolve_account_id",
    "resolve_all",
]

REASON_EMPTY = "empty_reference"
REASON_PLACEHOLDER = "unresolved_placeholder"
REASON_UNKNOWN = "not_in_chart"
REASON_NO_ACCOUNT_ID = "chart_carries_no_account_id"
REASON_INACTIVE = "account_inactive"
REASON_DO_NOT_USE = "account_marked_do_not_use"
# An org nobody curated: the account is a roll-up in its chart.
REASON_NON_LEAF = "account_is_a_parent"
# A curated org: Dirk marked this account N ("nothing a person buys ever
# lands here"). Dirk's call, so the sheet is where it changes.
REASON_NOT_EXPENSE_RELEVANT = "account_not_expense_relevant"
# A curated org: the account's code is not on the sheet for this org at
# all. Distinct from the N case because the fix differs: this one is a
# chart that moved on since the sheet was marked, or the wrong org.
REASON_OUT_OF_SCOPE = "account_outside_curated_list"
# A curated org: the code is on the sheet, but the chart's id for it is
# not the id the sheet carries for this org. Codes are shared across the
# three orgs, so a chart loaded for one org and posted under another
# passes every other check here and would send another company's ids.
REASON_CHART_ORG_MISMATCH = "chart_disagrees_with_org"

# The export layer's visible gaps. Each one means a human still has to
# decide something, so each one is a hard stop rather than an input:
# posting a placeholder would turn "someone must assign this" into a real
# number in the books.
_PLACEHOLDERS = frozenset(
    {
        _UNCATEGORIZED,
        _UNMAPPED,
        _REIMBURSABLE_PLACEHOLDER,
        PAID_THROUGH_PLACEHOLDER,
        ENTITY_PLACEHOLDER,
    }
)
# `_CARD_ACCOUNT` is a format string ("Card: {account_id}"), so it is
# matched by its literal prefix rather than by equality.
_CARD_PREFIX = _CARD_ACCOUNT.split("{", 1)[0]


@dataclass(frozen=True)
class ResolvedAccount:
    """An account reference that resolved to a real, postable GL id."""

    ref: str
    account_id: str
    name: str
    code: str


@dataclass(frozen=True)
class AccountRefusal:
    """An account reference that did NOT resolve, and exactly why.

    `detail` is written for the person who has to fix it, so it names the
    reference and the remedy rather than restating the reason code.
    """

    ref: str
    reason: str
    detail: str


def resolve_account_id(
    ref: str | None, coa: "ChartOfAccounts", *, org_id: str | None = None
) -> ResolvedAccount | AccountRefusal:
    """The numeric `account_id` for one account reference, or a refusal.

    Never returns a fallback ACCOUNT. Every branch below is a case where
    posting would put money somewhere nobody chose.

    `org_id` picks whose rules decide postable (module docstring): Dirk's
    marking for an org he curated, the chart's parent/leaf shape for any
    other org and for a call that names none.
    """
    text = (ref or "").strip()
    if not text:
        return AccountRefusal(
            ref="",
            reason=REASON_EMPTY,
            detail=(
                "no account reference on this line; categorize it before "
                "posting"
            ),
        )
    if text in _PLACEHOLDERS or text.startswith(_CARD_PREFIX):
        return AccountRefusal(
            ref=text,
            reason=REASON_PLACEHOLDER,
            detail=(
                f"{text!r} is a placeholder the export writes when a human "
                "still has to assign the account; assign it, then post"
            ),
        )

    acct: "Account | None" = resolve_ref(text, coa)
    if acct is None:
        return AccountRefusal(
            ref=text,
            reason=REASON_UNKNOWN,
            detail=(
                f"{text!r} matches no code or name in this org's chart; "
                "either it belongs to a different org or the chart is stale"
            ),
        )
    if not acct.account_id:
        return AccountRefusal(
            ref=text,
            reason=REASON_NO_ACCOUNT_ID,
            detail=(
                f"{text!r} resolved to {acct.name!r}, but this chart carries "
                "no Zoho ids. A CSV-exported chart cannot post; load the "
                "chart from the API for the target org"
            ),
        )
    if not acct.is_active:
        return AccountRefusal(
            ref=text,
            reason=REASON_INACTIVE,
            detail=(
                f"{acct.name!r} is inactive in this org; Zoho would reject "
                "or misfile the posting"
            ),
        )
    if acct.is_do_not_use:
        return AccountRefusal(
            ref=text,
            reason=REASON_DO_NOT_USE,
            detail=f"{acct.name!r} is marked DO NOT USE in this org's chart",
        )
    refusal = _postability_refusal(text, acct, coa, org_id)
    if refusal is not None:
        return refusal
    return ResolvedAccount(
        ref=text,
        account_id=acct.account_id,
        name=acct.name,
        code=acct.code,
    )


def _postability_refusal(
    text: str, acct: "Account", coa: "ChartOfAccounts", org_id: str | None
) -> AccountRefusal | None:
    """Leaf-ness and scope, judged by whichever source owns them here."""
    if curated_leaves.covers_org(org_id):
        why = curated_leaves.refusal_reason(org_id, acct.code)
        if why == curated_leaves.NO_SUCH_CODE:
            return AccountRefusal(
                ref=text,
                reason=REASON_OUT_OF_SCOPE,
                detail=(
                    f"{acct.name!r} ({acct.code or 'no code'}) is not on the "
                    f"curated expense list for org {org_id}; either the chart "
                    "gained it after the list was marked or it is another "
                    "org's account"
                ),
            )
        if why:
            return AccountRefusal(
                ref=text,
                reason=REASON_NOT_EXPENSE_RELEVANT,
                detail=(
                    f"{acct.name!r} ({acct.code}) is marked not expense "
                    f"relevant for org {org_id}; pick an account marked Y, "
                    "or have the marking changed at its source"
                ),
            )
        expected = curated_leaves.account_id_for(org_id, acct.code)
        if expected != acct.account_id:
            return AccountRefusal(
                ref=text,
                reason=REASON_CHART_ORG_MISMATCH,
                detail=(
                    f"{acct.code} is {expected} in org {org_id} but "
                    f"{acct.account_id} in the chart supplied; load the "
                    "chart for the org being posted to"
                ),
            )
        return None
    if acct.name in coa._parent_names():  # noqa: SLF001 (the gate's own test)
        return AccountRefusal(
            ref=text,
            reason=REASON_NON_LEAF,
            detail=(
                f"{acct.name!r} is a parent account in this chart and org "
                f"{org_id or '(none)'} has no curated list saying it takes "
                "postings; post to one of its children"
            ),
        )
    return None


def resolve_all(
    refs: "list[str | None]",
    coa: "ChartOfAccounts",
    *,
    org_id: str | None = None,
) -> tuple[list[ResolvedAccount], list[AccountRefusal]]:
    """Resolve many references, partitioned into resolved and refused.

    Order-preserving within each half. A caller that posts anything while
    `refusals` is non-empty has defeated the point of this module: the
    refusals are the rows that would otherwise have gone to a default
    account, which is the 6-of-9 failure in this module's docstring.
    """
    resolved: list[ResolvedAccount] = []
    refusals: list[AccountRefusal] = []
    for ref in refs:
        out = resolve_account_id(ref, coa, org_id=org_id)
        if isinstance(out, ResolvedAccount):
            resolved.append(out)
        else:
            refusals.append(out)
    return resolved, refusals
