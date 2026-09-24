"""Which curated GL leaf a receipt posts to, and why, or a refusal saying so.

This replaces receipt -> bucket -> translation table -> account. Both known
silent mis-posts happened in that middle step (OpenAI landing in Advertising
& Promotion; 6 of 9 sandbox rows falling back to `Office Infra and Admin`
because an account arrived as a NAME where a numeric id was expected).
Neither errored. Both posted. So this module prefers a refusal that names a
row over a default that is right most of the time.

THE CHAIN

    (entity, vendor) rule in the per-entity learning store
      -> trip-purpose inheritance  [deferred: refuses, never falls through]
      -> direct LLM match against this entity's curated leaves
      -> refuse: account_unresolved

WHAT A REFUSAL IS FOR

A refusal is not a failure mode here, it is the product. The owner's worry,
in his words: if an expense is sorted into the wrong Zoho GL account, nobody
would notice for months. A row that reaches a human as `(assign)` costs a
minute; a row that posts to a plausible wrong account costs a reconciliation
nobody knows to run. Every refusal carries the reason `curated_leaves` kept
apart (Dirk marked it N here, Zoho deactivated it, it is a roll-up, this org
has no such account, this org is not curated), because those send different
people to look.

WHERE THIS DELIBERATELY DOES NOT FALL THROUGH

A learned rule that names a leaf this entity cannot post to REFUSES. Falling
through to the model there would silently replace a human's decision with a
machine's, which is the same substitution the translation table made, one
layer up.

A learned rule that names no leaf at all is different and does fall through:
a bucket-only rule answers "which bucket", not "which account", so passing it
on overrides nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..category_vocabulary import recognize
from ..learning.consult import (
    RECALL_COMPANY,
    RECALL_NO_COMPANY,
    MerchantCategoryLookup,
)
from . import curated_leaves

__all__ = [
    "ACCOUNT_UNRESOLVED",
    "ENTITY_MISSING",
    "NOT_EXPENSE_RELEVANT",
    "SOURCE_LEARNED_RULE",
    "SOURCE_LLM_LEAF",
    "SOURCE_REFUSED",
    "TIER2_DEFERRED",
    "PostingResolution",
    "refusal_text",
    "resolve_posting_account",
]

SOURCE_LEARNED_RULE = "learned_rule"
SOURCE_LLM_LEAF = "llm_leaf"
SOURCE_REFUSED = "refused"

# Nothing in the chain resolved an account. The catch-all, distinct from
# every reason `curated_leaves` can give for a leaf it DOES know about.
ACCOUNT_UNRESOLVED = "account_unresolved"

# Trip-purpose inheritance is RULED OUT by the owner (2026-09-24): "trip does
# not define category because during a trip there can be expenses from
# multiple categories." This branch stays so the ruling is visible in the code
# rather than implied by its absence, and it keeps refusing. A purpose cannot
# pick a leaf: Conferences, CRM and general Travel each split into
# Transportation, Accommodation and Food, so `conference -> ...| Food` silently
# chooses one of three. `cost_centers.py:44` already ruled that co-varying the
# two dimensions destroys the point of cutting the money a second way, and the
# retired category table refused this exact shortcut for `Travel & Transport`:
# a default that is wrong half the time is worse than a refusal that names the
# row. Do not wire `cost_center` to an account.
TIER2_DEFERRED = "trip_purpose_inheritance_deferred"


NOT_EXPENSE_RELEVANT = "not_expense_relevant"

# The receipt names no legal entity at all, so there is no chart to judge it
# against. Kept apart from `org_not_curated` (a named company with no curated
# list) because the fixes differ: this one is "set the company", that one is
# "provision the company".
ENTITY_MISSING = "entity_missing"

# What each refusal says to the person who has to act on it. One sentence per
# code, naming what is missing and who fixes it, because "No category yet"
# over a refused row reads as "the tool has not looked yet" when it looked and
# declined on purpose.
_REFUSAL_TEXT = {
    ENTITY_MISSING: (
        "This expense has no company yet, so no account was picked. Set the "
        "company, then pick the account."
    ),
    curated_leaves.NOT_COVERED: (
        "No curated Zoho account list is set up for this company, so the "
        "tool did not guess an account. Pick one by hand."
    ),
    curated_leaves.NO_SUCH_CODE: (
        "The account remembered for this merchant does not exist in this "
        "company's Zoho chart. Pick one by hand."
    ),
    NOT_EXPENSE_RELEVANT: (
        "The account remembered for this merchant is not one a card expense "
        "may post to in this company. Pick one by hand."
    ),
    ACCOUNT_UNRESOLVED: (
        "The tool could not tell which Zoho account this belongs to. Pick "
        "one by hand."
    ),
    TIER2_DEFERRED: (
        "A trip does not decide the account. Pick one by hand."
    ),
}


def refusal_text(code: str | None) -> str:
    """The reviewer-facing sentence for a refusal code; generic if unknown."""
    return _REFUSAL_TEXT.get(code or "", _REFUSAL_TEXT[ACCOUNT_UNRESOLVED])


@dataclass(frozen=True)
class PostingResolution:
    """One row's answer. `account_id` is numeric or absent, never a name."""

    account_id: str | None
    code: str | None
    source: str
    reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.account_id is not None

    def __post_init__(self) -> None:
        if self.account_id is not None and not self.account_id.isdigit():
            # The 2026-09-22 mis-post happened because an account arrived as
            # a NAME where a numeric id was expected: it did not error, it
            # defaulted. This is the assertion that would have caught it.
            raise ValueError(
                "account_id must be numeric, got %r" % (self.account_id,))


def _refuse(reason: str, code: str | None = None) -> PostingResolution:
    return PostingResolution(
        account_id=None, code=code, source=SOURCE_REFUSED, reason=reason)


def _resolved(org_id: str, code: str, source: str) -> PostingResolution:
    return PostingResolution(
        account_id=curated_leaves.account_id_for(org_id, code),
        code=code, source=source)


def _leaf_named_by_rule(recall, org_id: str) -> str | None:
    """The curated code a learned rule points at, or None if it names none.

    A rule can name one two ways, and both are live. Since the write paths
    took leaf codes the `category` field carries one directly. Older rules
    carry the posting account in `zoho_account`, as this org's account name
    or as a code, which `code_of` resolves WITHIN this org: the same name
    means different accounts in different entities, and resolving it
    globally is how a Cloud Services account reaches a Corporate Services
    expense.

    A rule whose category is one of the eight buckets and whose account is
    empty names no leaf, and gets None.
    """
    from_category = recognize(recall.category)
    if from_category and curated_leaves.leaf(from_category) is not None:
        return from_category
    return curated_leaves.code_of(recall.zoho_account, org_id)


def resolve_posting_account(
    *,
    org_id: str | None,
    legal_entity_id: str | None,
    vendor: str | None,
    lookup: MerchantCategoryLookup | None = None,
    llm_leaf: str | None = None,
    cost_center: str | None = None,
) -> PostingResolution:
    """Walk the chain for one receipt and answer with an account or a reason.

    `llm_leaf` is whatever the model named: a code, a `"CODE name"` label, or
    this org's own account name. It is resolved within `org_id` only.

    `cost_center` is the trip purpose, present only on a trip row. Its
    presence fires the deferred Tier 2 branch, which refuses.
    """
    org = str(org_id or "").strip()
    if not curated_leaves.covers_org(org):
        # The rollout and rollback lever: an entity outside the curated set
        # refuses rather than guessing, so a new one is opted in by a
        # reviewed diff rather than by a receipt arriving.
        return _refuse(curated_leaves.NOT_COVERED)

    # ── Tier 1: the (entity, vendor) rule a person taught ────────────────
    recall = lookup.recall(legal_entity_id, vendor) if lookup else None
    if recall is not None and recall.kind in (
        RECALL_COMPANY, RECALL_NO_COMPANY,
    ):
        code = _leaf_named_by_rule(recall, org)
        if code is not None:
            if curated_leaves.is_postable(org, code):
                return _resolved(org, code, SOURCE_LEARNED_RULE)
            # Named, and unpostable here. Refuse rather than fall through:
            # the model must not overrule a person.
            return _refuse(curated_leaves.refusal_reason(org, code), code)
    # A `vendor_only` recall is deliberately not consulted for an account.
    # It aggregates rules that belong to OTHER companies, and an account
    # belongs to one company's chart, so agreeing on a category says nothing
    # about agreeing on an account id. Its category may still be used
    # elsewhere; it never decides money's destination here.

    # ── Tier 2: deferred, and refusing on purpose (see TIER2_DEFERRED) ───
    if str(cost_center or "").strip():
        return _refuse(TIER2_DEFERRED)

    # ── Tier 3: the model's own pick, against THIS entity's leaves ───────
    code = curated_leaves.code_of(llm_leaf, org)
    if code is not None:
        if curated_leaves.is_postable(org, code):
            return _resolved(org, code, SOURCE_LLM_LEAF)
        return _refuse(curated_leaves.refusal_reason(org, code), code)

    return _refuse(ACCOUNT_UNRESOLVED)
