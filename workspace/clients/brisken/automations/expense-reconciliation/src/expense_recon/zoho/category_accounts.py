"""Per-org fallback from the app's own category to a GL account code.

**The gap this fills, measured.** In the 2026-09-23 July dry run, 36 of 46
purchases carried a category name in the `Expense Account` column
(`Software & Subscriptions` x22, `Meals & Entertainment` x11,
`Professional Services` x4) and refused to post, because no Brisken chart
has an account by those names. The cause is one branch in
`output.posting_common._debit_account_and_note`: with no chart loaded the
export passes `cat.zoho_account or cat.category` straight through, so a
receipt whose vendor has no account rule leaks its CATEGORY into the
account column. The July export ran with no chart, which is why the column
holds raw labels and not one `(account unmapped - assign)`.

So the category is a real signal that was being thrown away. This module
turns it into a postable account, without loosening any of the refusals
that make the posting path safe.

**Fallback only, never an override.** Precedence is unchanged from the M1
registry design: a (company, vendor) rule that already picked an account
resolves first and wins. This map is consulted ONLY after
`posting_common.resolve_ref` has failed to match the reference as a code
or a name. A vendor rule always outranks its category's default.

**Keyed by org, because the same category means different accounts.**
Brisken's own Zoho history is the reason, not theory: `anthropic` posts to
"Other Infra and IT Costs" under Corporate Services and to "COGS - DEV
Infrastructure" under Cloud Services. A single global category->account
table would be wrong in at least one org by construction. Charts also
differ per org, so a code that exists in one need not exist in another.

**Production orgs are deliberately absent.** Only the sandbox is mapped
here. Picking which GL account a category posts to is an accounting
decision that belongs to Brisken, and an unmapped org refuses exactly as
it does today rather than inheriting a sandbox guess. Adding a production
org to this table is an owner call, not an agent one.

**Maps to a CODE, not to an `account_id`.** The code goes back through the
same `resolve_ref` the file exports use, so there is still ONE resolution
order, and the resolved account still passes the inactive / DO-NOT-USE /
no-id checks in `accounts.py`. A code that is wrong or stale then fails
loudly as a refusal instead of posting money to a number nobody checked.
"""
from __future__ import annotations

from .orgs import SANDBOX_ORG_ID

__all__ = [
    "CATEGORY_ACCOUNT_CODES",
    "NEVER_MAPPED",
    "category_account_code",
    "mapped_categories",
]


# Markers the export writes when a human still has to decide something.
# They are never mapped: turning "someone must assign this" into a real
# account is precisely the silent-default failure this whole path exists
# to prevent. `accounts.py` already refuses them by placeholder before
# reaching here; this set keeps the guarantee local and testable.
NEVER_MAPPED = frozenset(
    {
        "(uncategorized - assign)",
        "(account unmapped - assign)",
        "(reimbursable clearing - assign)",
        "(paid-through - assign)",
        "(entity - assign)",
    }
)


# TEST-BTS (sandbox).
#
# **Every target must be a LEAF account.** Zoho posts only to leaves;
# parent accounts are roll-ups (`ChartOfAccounts.leaf_accounts`). The
# first draft of this table mapped three categories to parents
# (Professional Fees, Travel Expense, Marketing & Selling Expenses),
# which the chart itself would have rejected. `test_zoho_category_accounts`
# now asserts leafness so the same mistake cannot ship twice.
#
# Each pick is grounded in this org's chart and in the July rows that
# carry the category, not in what the category name suggests:
#
#   Meals & Entertainment -> E100010-31 is not a judgment call at all. It
#   is the exact account the nine July rows that ALREADY resolve post to,
#   via the label "E100010-31 - Travel Expense | Food".
#
#   Software & Subscriptions -> E500010-30 is the unbranded leaf of the
#   IT: Computer and Internet Expenses parent. Its siblings -20 (Microsoft
#   office) and the ZOHO ERP leaf stay reserved for vendor rules, which
#   outrank this fallback.
#
#   Professional Services -> E600060-70, the catch-all leaf UNDER
#   Professional Fees. July's rows are consulting (Konsultancy Finance,
#   Rodrigo Tanure IT consulting), which is a professional fee that is
#   specifically not accounting, legal, permits or recruitment. The
#   catch-all lands them in the right family without claiming which kind.
#
#   Marketing & Advertising -> E600010-05-09. July's single row is a
#   360Crossmedia directory listing, which is a promotion channel rather
#   than LinkedIn / Google / Facebook spend.
#
# DELIBERATELY UNMAPPED: "Travel & Transport". Its two July rows are
# gasoline (POSTO ARCA DE NOE) and a vehicle rental (E A LOCACOES), which
# belong to different leaves (E100010-01 vs E100010-36), and Travel
# Expense has no generic leaf to hold both. A default that is wrong half
# the time is worse than a refusal that names the row, so these keep
# asking a human. Map it only if a generic leaf appears.
_TEST_BTS: dict[str, str] = {
    "Software & Subscriptions": "E500010-30",  # IT: Cloud Subscriptions-Others
    "Meals & Entertainment": "E100010-31",  # Travel Expense:Meals
    "Professional Services": "E600060-70",  # Professional Fees > Other Expenses
    "Office Supplies & Consumables": "E500030-20",  # Office Supplies
    "Equipment & Hardware": "E500010-40",  # IT: equipment, peripherals, ...
    "Marketing & Advertising": "E600010-05-09",  # Other Promotions and Ad Channels
    "Utilities & Premises": "E500030-60",  # Utilities
}

CATEGORY_ACCOUNT_CODES: dict[str, dict[str, str]] = {
    SANDBOX_ORG_ID: _TEST_BTS,
}


def _norm(text: str | None) -> str:
    """Fold a category for lookup: case and surrounding space only.

    Deliberately not fuzzy. A near-miss should refuse and be fixed at the
    source, because a fuzzy match here would post money on a guess.
    """
    return " ".join((text or "").split()).casefold()


_BY_ORG_NORMALIZED: dict[str, dict[str, str]] = {
    org: {_norm(cat): code for cat, code in table.items()}
    for org, table in CATEGORY_ACCOUNT_CODES.items()
}


def category_account_code(org_id: str | None, category: str | None) -> str | None:
    """The GL code this org posts `category` to, or None to refuse.

    None for an unmapped org, an unmapped category, or any never-mapped
    placeholder. The caller treats None as "keep refusing".
    """
    text = (category or "").strip()
    if not text or text in NEVER_MAPPED:
        return None
    return _BY_ORG_NORMALIZED.get(str(org_id or ""), {}).get(_norm(text))


def mapped_categories(org_id: str | None) -> tuple[str, ...]:
    """The categories this org can post, for diagnostics and runbooks."""
    return tuple(sorted(CATEGORY_ACCOUNT_CODES.get(str(org_id or ""), {})))
