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

if TYPE_CHECKING:
    from ..ingest.chart_of_accounts import Account, ChartOfAccounts

__all__ = [
    "REASON_DO_NOT_USE",
    "REASON_EMPTY",
    "REASON_INACTIVE",
    "REASON_NO_ACCOUNT_ID",
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

# The export layer's visible gaps. Each one means a human still has to
# decide something, so each one is a hard stop rather than an input:
# posting a placeholder would turn "someone must assign this" into a real
# number in the books.
_PLACEHOLDERS = frozenset(
    {
        _UNCATEGORIZED,
        _UNMAPPED,
        _REIMBURSABLE_PLACEHOLDER,
        "(paid-through - assign)",
        "(entity - assign)",
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
    ref: str | None, coa: "ChartOfAccounts"
) -> ResolvedAccount | AccountRefusal:
    """The numeric `account_id` for one account reference, or a refusal.

    Never returns a fallback account. Every branch below is a case where
    posting would put money somewhere nobody chose.
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
    return ResolvedAccount(
        ref=text, account_id=acct.account_id, name=acct.name, code=acct.code
    )


def resolve_all(
    refs: "list[str | None]", coa: "ChartOfAccounts"
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
        out = resolve_account_id(ref, coa)
        if isinstance(out, ResolvedAccount):
            resolved.append(out)
        else:
            refusals.append(out)
    return resolved, refusals
