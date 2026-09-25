"""Expense categorization — BLUEPRINT LD-1 + LD-2.

Two implementations behind the same `categorize_receipts(...)` entry:

* **LLM path** (production) — `client: LLMClient` argument. Sends
  one batched call per receipt's line items to the provider, plus an
  optional vendor-fallback call when line items are absent/vague.
  Production setting since slice 2 (provider: OpenAI gpt-4o-mini per
  the 2026-06-01 stack pivot).
* **Keyword stub** (fallback, tests, no-LLM mode) — deterministic
  regex/substring mapping. Same return shape, slightly worse
  accuracy. Used when no `LLMClient` is wired (slice 1 behaviour
  preserved) or when the keyword path is explicitly requested.

The strict LD-2 rule applies to both implementations:

* **Tier 1 (LINE)** — categorize from line-item description ONLY.
  Vendor name is NOT a classifier input. (Enforced in the prompt for
  the LLM path; enforced by code path in the keyword stub.)
* **Tier 2 (VENDOR ⚠)** — only triggered when the receipt has no
  line items OR every line item is too vague to classify. Vendor
  name is the input, result is marked with ⚠ so Chris confirms.
* **Tier 3 (REVIEW)** — confidence below `REVIEW_THRESHOLD`, OR no
  vendor + no line items, OR the LLM returned `category: null`.
  Category cell blank; Chris assigns.
"""
from __future__ import annotations

import re
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Mapping

from .coa_provision import org_id_for_entity
from .learning.consult import (
    RECALL_NO_COMPANY,
    RECALL_VENDOR_ONLY,
    LearnedRecall,
)
from .llm.client import (
    ClassificationResult,
    LineItemInput,
    LLMClient,
)
from .category_vocabulary import recognize as recognize_category
from .merchant_registry import company_account
from .matching.types import (
    EXPENSE_CATEGORIES,
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)
from .zoho import curated_leaves
from .zoho.posting_resolution import (  # noqa: F401 (refusal_text re-exported)
    ACCOUNT_UNRESOLVED,
    ENTITY_MISSING,
    MODEL_PICKED_PARENT,
    PostingResolution,
    refusal_text,
    resolve_posting_account,
)

if TYPE_CHECKING:
    from .ingest.chart_of_accounts import Account, ChartOfAccounts
    from .learning import MerchantCategoryLookup


STUB_LINE_REASON = "[STUB-KEYWORD] line-item keyword match (slice-1 placeholder)"
STUB_VENDOR_REASON = "[STUB-KEYWORD] vendor keyword match — confirm category"
NO_SIGNAL_REASON = "No classification signal — Chris assigns category"

# Confidence below this routes to Tier 3 REVIEW regardless of source.
REVIEW_THRESHOLD = 0.6

# Recorded on `Categorization.decision` when a remembered category was
# applied to a receipt whose line items read something else (item 115). The
# review layer turns it into the glance the row deserves; it is NOT one of
# the WS2 adjudication verdicts below.
DECISION_LEARNED_OVER_LINE = "learned_over_line"

# Stub confidence: all keyword hits get the same value so it's visually
# obvious in the report that no real ranking is happening yet.
STUB_CONFIDENCE = 0.7

# Descriptions matching this pattern are too vague to drive line-item
# classification — fall through to vendor fallback. BLUEPRINT LD-2
# vagueness rule (slice 4.2).
_VAGUE_DESCRIPTION_TOKENS = (
    "item",
    "misc",
    "service",
    "charge",
    "fee",
    "subtotal",
    "total",
)


# Keyword → category mapping. Slice-1 starter set; replaced by LLM
# in slice 2. Kept deliberately small to avoid the false-confidence
# trap of an ever-growing rule list.
_LINE_KEYWORDS: dict[str, str] = {
    # Travel & Transport
    "uber": "Travel & Transport",
    "lyft": "Travel & Transport",
    "taxi": "Travel & Transport",
    "flight": "Travel & Transport",
    "airline": "Travel & Transport",
    "hotel": "Travel & Transport",
    "train": "Travel & Transport",
    "parking": "Travel & Transport",
    "fuel": "Travel & Transport",
    "gas": "Travel & Transport",
    # Meals & Entertainment
    "coffee": "Meals & Entertainment",
    "latte": "Meals & Entertainment",
    "espresso": "Meals & Entertainment",
    "lunch": "Meals & Entertainment",
    "dinner": "Meals & Entertainment",
    "restaurant": "Meals & Entertainment",
    "cafe": "Meals & Entertainment",
    "bar": "Meals & Entertainment",
    "meal": "Meals & Entertainment",
    "food": "Meals & Entertainment",
    "wine": "Meals & Entertainment",
    "beer": "Meals & Entertainment",
    # Software & Subscriptions
    "subscription": "Software & Subscriptions",
    "license": "Software & Subscriptions",
    "saas": "Software & Subscriptions",
    "cloud": "Software & Subscriptions",
    "aws": "Software & Subscriptions",
    "gcp": "Software & Subscriptions",
    "azure": "Software & Subscriptions",
    "domain": "Software & Subscriptions",
    "hosting": "Software & Subscriptions",
    # Office Supplies & Consumables
    "paper": "Office Supplies & Consumables",
    "pen": "Office Supplies & Consumables",
    "ink": "Office Supplies & Consumables",
    "stationery": "Office Supplies & Consumables",
    "cleaning": "Office Supplies & Consumables",
    "tea": "Office Supplies & Consumables",
    # Equipment & Hardware
    "laptop": "Equipment & Hardware",
    "monitor": "Equipment & Hardware",
    "chair": "Equipment & Hardware",
    "desk": "Equipment & Hardware",
    "phone": "Equipment & Hardware",
    "cable": "Equipment & Hardware",
    "keyboard": "Equipment & Hardware",
    "mouse": "Equipment & Hardware",
    "hdmi": "Equipment & Hardware",
    "printer": "Equipment & Hardware",
    # Marketing & Advertising
    "ads": "Marketing & Advertising",
    "advertising": "Marketing & Advertising",
    "sponsorship": "Marketing & Advertising",
    "swag": "Marketing & Advertising",
    # Professional Services
    "legal": "Professional Services",
    "accounting": "Professional Services",
    "consulting": "Professional Services",
    "consultant": "Professional Services",
    "contractor": "Professional Services",
    "freelancer": "Professional Services",
    # Utilities & Premises
    "rent": "Utilities & Premises",
    "internet": "Utilities & Premises",
    "electricity": "Utilities & Premises",
    "water": "Utilities & Premises",
    "coworking": "Utilities & Premises",
    "insurance": "Utilities & Premises",
}


# Vendor keyword map for Tier 2. Same shape as _LINE_KEYWORDS; matches
# vendor name when the receipt has no usable line items.
_VENDOR_KEYWORDS: dict[str, str] = {
    "uber": "Travel & Transport",
    "lyft": "Travel & Transport",
    "delta": "Travel & Transport",
    "marriott": "Travel & Transport",
    "hilton": "Travel & Transport",
    "starbucks": "Meals & Entertainment",
    "mcdonald": "Meals & Entertainment",
    "amazon": "Equipment & Hardware",   # weak; LLM in slice 2 should do better
    "adobe": "Software & Subscriptions",
    "github": "Software & Subscriptions",
    "openai": "Software & Subscriptions",
    "anthropic": "Software & Subscriptions",
    "stripe": "Software & Subscriptions",
}


def categorize_receipts(
    receipts: list[Receipt],
    *,
    client: LLMClient | None = None,
    chart_of_accounts: list[str] | None = None,
    learned: "MerchantCategoryLookup | None" = None,
    override_er_category: bool = False,
    judge_each_receipt: "frozenset[str] | None" = None,
    merchant_profiles: "dict[str, str] | None" = None,
    entity_orgs: "Mapping[str, str] | None" = None,
) -> list[Receipt]:
    """Return a new list of receipts with line_items carrying
    Categorization results per LD-2.

    `entity_orgs` (Phase 1, item 3) switches the run to direct-to-GL
    categorization: legal-entity label -> Zoho org id, as
    `coa_provision.entity_org_ids` builds it. Present (even empty), every
    receipt is judged against ITS entity's curated leaves and either carries
    a leaf code as `category` or refuses with `category=None` and a named
    `refusal` (see `_categorize_one_gl`). `chart_of_accounts` and
    `override_er_category` do not apply on that path. None keeps the bucket
    path below byte for byte.

    When `client` is provided, uses LLM calls. When None (default),
    falls back to the keyword stub — preserves slice-1 behaviour for
    callers that haven't wired an LLM yet.

    `chart_of_accounts` is the in-scope Zoho account labels (slice 4.1
    `ChartOfAccounts.llm_account_labels()`). When supplied, the LLM is
    asked to also pick the specific `zoho_account` leaf per LD-2; the
    keyword stub ignores it (no account mapping). Ignored entirely
    without an LLM client.

    `learned` (Phase 2) is a cross-run memory of confirmed
    merchant->category decisions. Since item 115 it is consulted on EVERY
    receipt, not only the weak vendor-fallback path: a rule a person taught
    (a correction saved at sign-off or the button, a Memory-page edit, or a
    validated row) applies to a receipt with readable line items too, and
    the row says so when it disagreed with the line read. A rule seeded
    from Zoho Books posting history that nobody has validated still stays
    below a confident line read. None / empty => behaviour unchanged.

    A merchant with a registry default category never reaches this function
    (note item M1, 2026-09-18): `categorize_receipts_with_registry` stamps
    it before the line read, so item 115's `registry_backed` plumbing is
    gone. `judge_each_receipt` (item 115, internal) names the documents
    whose merchant is marked multi-category: that mark is an instruction to
    judge every receipt on its own items, so no remembered category
    flattens its lines.

    `merchant_profiles` (note item M4, internal) maps document_id -> the
    registry's free prose for that receipt's merchant, and rides into the
    two LLM classify calls as fenced untrusted context. A document with no
    entry, or an empty registry, makes exactly the calls it made before M4.

    `override_er_category` (2026-07-21 owner decision) flips who owns the
    posting account. Default False keeps the 2026-06-16 behaviour (the
    Zoho Expense report's own GL account is authoritative). True makes the
    tool's own category + account authoritative: the LLM's / memory's
    `zoho_account` pick is kept, and the report's `zoho_category` is only
    a fallback when the line has no account of its own. See
    `_carry_zoho_account`.

    Pure function; does not mutate inputs.
    """
    if entity_orgs is not None:
        return [
            _categorize_one_gl(
                r, client, learned,
                org_id=org_id_for_entity(r.legal_entity_id, entity_orgs),
                judge_each_receipt=bool(
                    judge_each_receipt and r.document_id in judge_each_receipt
                ),
                merchant_profile=(merchant_profiles or {}).get(r.document_id),
            )
            for r in receipts
        ]
    return [
        _categorize_one(
            r, client, chart_of_accounts, learned,
            override_er_category=override_er_category,
            judge_each_receipt=bool(
                judge_each_receipt and r.document_id in judge_each_receipt
            ),
            merchant_profile=(merchant_profiles or {}).get(r.document_id),
        )
        for r in receipts
    ]


REGISTRY_DEFAULT_REASONING = "merchant registry default"


def apply_registry_category(
    receipt: Receipt,
    category: str | None,
    zoho_account: str | None,
    *,
    override_er_category: bool = False,
    reasoning: str = REGISTRY_DEFAULT_REASONING,
) -> Receipt:
    """Stamp a deterministic REGISTRY categorization on every line of a
    receipt whose merchant carries a registry default category (2026-07-29).

    Deterministic and LLM-preempting: the caller does not run the LLM for
    these receipts. `confidence=1.0`, `source=REGISTRY`. `zoho_account` is
    whatever the caller resolved for this receipt's COMPANY (note item M1:
    the company's rule first, the registry's own account second), and
    `reasoning` says which; when neither names one, the account resolves
    from the ER `zoho_category` / chart exactly as the LLM path does, via
    `_carry_zoho_account`.

    No-op when the registry entry carries no category (naming-only merchant);
    the caller then runs the LLM as usual and only the canonical display name
    changes."""
    if not category:
        return receipt
    cat = Categorization(
        # Same reason as `merchant_registry._match`: this is the second of two
        # filters on one stored value, and the value reaching here has already
        # passed that one. Fixing either alone leaves the leaf code dropped,
        # so both move together.
        category=recognize_category(category),
        zoho_account=zoho_account or None,
        confidence=1.0,
        source=ClassificationSource.REGISTRY,
        reasoning=reasoning,
    )
    items = receipt.line_items or (_synthesize_total_line(receipt),)
    stamped = replace(receipt, line_items=tuple(replace(li, categorization=cat) for li in items))
    # A registry-provided account must survive; force the keep-account policy
    # so `_carry_zoho_account` fills from the ER category only when the
    # registry gave no account of its own.
    return _carry_zoho_account(
        stamped, override_er_category=override_er_category or bool(zoho_account)
    )


def categorize_receipts_with_registry(
    receipts: list[Receipt],
    *,
    registry=None,
    client: LLMClient | None = None,
    chart_of_accounts: list[str] | None = None,
    learned: "MerchantCategoryLookup | None" = None,
    override_er_category: bool = False,
    cat_chart=None,
    scope_groups=None,
    entity_orgs: "Mapping[str, str] | None" = None,
) -> tuple[list[Receipt], dict]:
    """Categorize a batch of receipt-first expenses with the merchant registry
    as the deterministic tier above the LLM (2026-07-29).

    Tier order since note item M1 (owner directive 2026-09-18, Dirk's rule:
    binding a merchant to ONE category is right about 90% of the time, and
    the exceptions vary by company on the ACCOUNT): a reviewer override >
    REGISTRY (the merchant's default category, with the account the
    (company, vendor) rule names, see `_registry_account`) > LEARNED (a rule
    a person taught, on a merchant with no registry default) > a confident
    LINE read > LEARNED (a Zoho-seeded rule nobody validated) > LLM /
    keyword vendor guess > REVIEW. A receipt with no readable line items has
    no LINE tier, so there memory leads outright, as it has since Phase 2.

    This retires the 2026-08-07 order for the CATEGORY only: a per-company
    learned row used to outrank the registry default outright, which meant
    a merchant with a default was judged one way for a company with a rule
    and another way for a company without one. The reason for that order
    (the same merchant books to a different ACCOUNT per company) is kept
    whole: the rule still decides the account. A merchant marked
    `multi_category` resolves its name only and is judged per receipt.

    For each receipt it resolves a canonical merchant (stamping
    `canonical_vendor` + `vendor_source="registry"` on every match; naming is
    independent of categorization). A match that carries a default category
    is stamped a REGISTRY categorization and SKIPS the LLM
    (deterministic-first); the rest run through `categorize_receipts`, and
    through `adjudicate_receipts` when `cat_chart` is supplied and
    `override_er_category` is on. An empty / None registry behaves exactly
    like `categorize_receipts` alone.

    Returns `(receipts, registry_matches)` where `registry_matches` maps
    document_id -> MerchantMatch, for the grid's display vendor + provenance.
    Order is preserved. Consulted in the expense paths and, since M1, for a
    month's receiptless charges (`categorize_charges`); `reconcile()` itself
    never calls it.

    `entity_orgs` (Phase 1, item 3) runs the batch on the GL engine. The
    registry stays the tier above the model, but its answer has to name a
    leaf THIS receipt's entity may post to (`_registry_gl`): a default that
    names no leaf (one of the eight buckets) falls through to the engine
    rather than stamping a bucket, and no ER adjudication runs."""
    registry_matches: dict = {}
    if registry:
        for r in receipts:
            m = registry.resolve(r.vendor_clean, r.detected_vendor)
            if m is not None:
                registry_matches[r.document_id] = m
        receipts = [
            replace(
                r,
                canonical_vendor=registry_matches[r.document_id].canonical_name,
                vendor_source="registry",
            )
            if r.document_id in registry_matches
            else r
            for r in receipts
        ]
    # Note item M1 (2026-09-18): every merchant with a registry default is
    # stamped here, whatever memory holds for it. The 2026-08-07 order let a
    # per-company learned row outrank the default (Brisken's own books post
    # `anthropic` to "Other Infra and IT Costs" for Corporate Services and
    # to "COGS - DEV Infrastructure" for Cloud Services), and item 115 then
    # had to route those receipts around the line read. Dirk's 2026-09-18
    # clarification separates the two facts the old order conflated: the
    # CATEGORY is the merchant's (one per merchant, the registry's), and
    # what varies by company is the ACCOUNT, which the (company, vendor)
    # rule still decides through `_registry_account`.
    cat_docs = {doc for doc, m in registry_matches.items() if m.category}
    gl = entity_orgs is not None
    gl_stamped: dict[str, Receipt] = {}
    if gl:
        for r in receipts:
            m = registry_matches.get(r.document_id)
            if m is None:
                continue
            org_id = org_id_for_entity(r.legal_entity_id, entity_orgs)
            # Items 180/181: a merchant with no default category still
            # decides the account for a company its map names.
            if r.document_id not in cat_docs and company_account(
                getattr(m, "accounts", ()), org_id, entity_orgs
            ) is None:
                continue
            stamped = _registry_gl(
                r, m, learned, org_id, entity_orgs=entity_orgs,
            )
            if stamped is not None:
                gl_stamped[r.document_id] = stamped
        cat_docs = set(gl_stamped)
    to_llm = [r for r in receipts if r.document_id not in cat_docs]
    multi_category = frozenset(
        doc for doc, m in registry_matches.items() if m.multi_category
    )
    # Note item M4: the merchant's free prose rides into the classify calls
    # for every receipt that still needs judging. Only these do: a receipt
    # the registry stamped a category on never reaches the model at all, so
    # a profile on a merchant with a default category is background for the
    # Memory page and the editor, not a prompt cost.
    profiles = {
        doc: m.profile
        for doc, m in registry_matches.items()
        if m.profile
    }
    categorized = categorize_receipts(
        to_llm, client=client, chart_of_accounts=chart_of_accounts,
        learned=learned, override_er_category=override_er_category,
        judge_each_receipt=multi_category,
        merchant_profiles=profiles,
        entity_orgs=entity_orgs,
    )
    if not gl and override_er_category and cat_chart is not None:
        categorized = adjudicate_receipts(
            categorized, cat_chart, scope_groups=scope_groups
        )
    by_doc = {r.document_id: r for r in categorized}
    for r in receipts:
        if r.document_id in gl_stamped:
            by_doc[r.document_id] = gl_stamped[r.document_id]
        elif r.document_id in cat_docs:
            m = registry_matches[r.document_id]
            account, reasoning = _registry_account(r, m, learned)
            by_doc[r.document_id] = apply_registry_category(
                r, m.category, account,
                override_er_category=override_er_category,
                reasoning=reasoning,
            )
    return [by_doc[r.document_id] for r in receipts], registry_matches


def _registry_account(
    receipt: Receipt, match, learned: "MerchantCategoryLookup | None"
) -> tuple[str | None, str]:
    """The posting account for a receipt whose merchant has a registry
    default category, and the provenance sentence that names its source
    (note item M1).

    The (company, vendor) rule memory holds for this receipt decides the
    account: the rule saved under the receipt's own company, else one saved
    with no company, else (for a receipt with no company) the vendor's
    rules when they agree on it (`MerchantCategoryLookup.recall`, item
    115). A rule contributes its account only when it agrees with the
    registry on the category or a person stands behind it (a sign-off
    correction, a Memory-page edit or a validated row): a row seeded from
    Zoho Books posting history under ANOTHER category is how the books
    once posted, not an account for this category, so it is left alone.
    With no rule, or a rule that names no account, the registry's own
    account stands, which may be nothing."""
    recall = _recall_for(receipt, learned)
    if (
        recall is None
        or not recall.zoho_account
        or (recall.category != match.category and not recall.taught_by_person)
    ):
        return match.zoho_account, REGISTRY_DEFAULT_REASONING
    if recall.kind == RECALL_VENDOR_ONLY:
        companies = ", ".join(
            r.legal_entity_id or "no company" for r in recall.rows
        )
        rule = f"the rules for {companies}, which agree"
    else:
        company = recall.rows[0].legal_entity_id
        rule = (
            f"the rule saved for {company}" if company
            else "the rule saved with no company"
        )
    return recall.zoho_account, f"{REGISTRY_DEFAULT_REASONING}; account from {rule}"


def _categorize_one(
    receipt: Receipt,
    client: LLMClient | None,
    chart_of_accounts: list[str] | None,
    learned: "MerchantCategoryLookup | None" = None,
    *,
    override_er_category: bool = False,
    judge_each_receipt: bool = False,
    merchant_profile: str | None = None,
) -> Receipt:
    """Apply the LD-2 tier rules to a single receipt."""
    recall = _recall_for(receipt, learned)
    has_lines = bool(receipt.line_items) and not _all_vague(receipt.line_items)

    if has_lines:
        # LINE path (Tier 1). Item 115: memory IS consulted here now, but it
        # only leads when a person stands behind the rule (a correction saved
        # at sign-off or the button, a Memory-page edit, a validated row). A
        # Zoho-seeded row nobody has validated still sits below the line read
        # (the Phase-2 invariant, kept: those rows are how the books posted,
        # not what a person said about this merchant). A multi-category
        # merchant is never flattened. A merchant with a registry default
        # never arrives here (note item M1: the registry stamps it first).
        leads = (
            recall is not None
            and not judge_each_receipt
            and recall.taught_by_person
        )
        if not leads:
            if client is not None:
                categorized = _classify_lines_via_llm(
                    receipt.line_items, client, chart_of_accounts,
                    merchant_profile,
                )
            else:
                categorized = tuple(
                    _classify_line_keyword(li) for li in receipt.line_items
                )
            return _carry_zoho_account(
                replace(receipt, line_items=categorized),
                override_er_category=override_er_category,
            )
        return _carry_zoho_account(
            _apply_learned_over_lines(
                receipt, recall, client, chart_of_accounts,
            ),
            override_er_category=override_er_category,
        )

    # No usable line items → the weak path that today re-pays for a vendor
    # guess and lands Tier-2. Memory FALLBACK first: a confirmed
    # merchant->category recalled from a prior month upgrades it to Tier-1
    # LEARNED and skips the LLM/keyword vendor call (the deterministic-first
    # win).
    # `judge_each_receipt` is not consulted here: a multi-category merchant's
    # mark says to judge a receipt on its own items, and this receipt has
    # none, so memory leads exactly as it has since Phase 2.
    synthesized = _synthesize_total_line(receipt)
    learned_cat = None if recall is None else _learned_categorization(recall)
    if learned_cat is not None:
        return _carry_zoho_account(
            replace(
                receipt, line_items=(replace(synthesized, categorization=learned_cat),)
            ),
            override_er_category=override_er_category,
        )
    if client is not None:
        classified = _classify_vendor_via_llm(
            synthesized, receipt.detected_vendor, receipt.detected_total,
            client, chart_of_accounts, merchant_profile,
        )
    else:
        classified = _classify_vendor_keyword(synthesized, receipt.detected_vendor)
    return _carry_zoho_account(
        replace(receipt, line_items=(classified,)),
        override_er_category=override_er_category,
    )


def _carry_zoho_account(
    receipt: Receipt, *, override_er_category: bool = False
) -> Receipt:
    """Reconcile the report's own Zoho GL account with the tool's per-line
    posting account.

    Two policies, selected by `override_er_category`:

    * **False (default, Dirk 2026-06-16):** the Zoho Expense report's account
      is authoritative for posting — copy `receipt.zoho_category` onto every
      line's `zoho_account`, overwriting whatever the LLM/keyword/memory pass
      chose. The tool's own category (our 8) is left untouched so the reviewer
      sees both.
    * **True (2026-07-21 owner decision):** the tool's own judgment is
      authoritative — KEEP the line's existing `zoho_account` (the LLM's or
      memory's pick) and fall back to `receipt.zoho_category` only when the
      line has no account of its own (e.g. no chart of accounts was wired, so
      the LLM had nothing to choose). This never loses a posting account, and
      the report's often-wrong account (ADOBE/ANTHROPIC -> "Travel Expense |
      Food") no longer clobbers a correct pick. The export-time COA gate still
      validates the surviving account and diverts a bad one to REVIEW.

    No-op when the receipt carries no Zoho category (nothing to carry or fall
    back to)."""
    if not receipt.zoho_category:
        return receipt
    new_items = []
    for li in receipt.line_items:
        cat = li.categorization
        if cat is None:
            new_items.append(li)
            continue
        if override_er_category and cat.zoho_account:
            # Keep the tool's own account; the report's label is display-only.
            new_items.append(li)
            continue
        new_items.append(
            replace(li, categorization=replace(cat, zoho_account=receipt.zoho_category))
        )
    return replace(receipt, line_items=tuple(new_items))


def _recall_for(
    receipt: Receipt, learned: "MerchantCategoryLookup | None"
) -> "LearnedRecall | None":
    """What memory remembers for this receipt's merchant, or None."""
    if learned is None or not receipt.detected_vendor:
        return None
    return learned.recall(receipt.legal_entity_id, receipt.detected_vendor)


def _learned_categorization(recall: "LearnedRecall") -> Categorization:
    """A Tier-1 LEARNED categorization from a recall. The provenance
    reasoning carries the month of the confirming decision so the workbench
    can show it; rows seeded from Zoho Books posting history (L2, source_run
    "zoho-seed:*") name that history instead of a reviewer decision, and a
    recall that fired on the vendor alone names the rule it used (item
    115), because that rule was written for another company or for none."""
    seeded = all(
        (r.source_run or "").startswith("zoho-seed") for r in recall.rows
    )
    if seeded:
        provenance = "from your earlier posting history"
    else:
        months = [r.last_confirmed_at[:7] for r in recall.rows if r.last_confirmed_at]
        when = max(months) if months else None
        provenance = (
            f"learned from your {when} decision" if when
            else "learned from your confirmed decision"
        )
    if recall.kind == RECALL_VENDOR_ONLY:
        rule = ", ".join(
            f"{r.legal_entity_id or 'no company'} / {r.vendor_norm}"
            for r in recall.rows
        )
        provenance += f" ({rule}; this expense has no company yet)"
    elif recall.kind == RECALL_NO_COMPANY:
        provenance += " (a rule saved with no company)"
    return Categorization(
        category=recall.category,
        zoho_account=recall.zoho_account,
        confidence=1.0,
        source=ClassificationSource.LEARNED,
        reasoning=provenance,
    )


def _apply_learned_over_lines(
    receipt: Receipt,
    recall: "LearnedRecall",
    client: LLMClient | None,
    chart_of_accounts: list[str] | None,
) -> Receipt:
    """Stamp a remembered category on every line of a receipt that HAS
    readable line items (item 115).

    A rule nobody has validated is checked against the line read before it
    wins: the same read the LINE tier would have paid for anyway, and when
    it disagrees the row says so (`decision = learned_over_line`) and the
    review state asks for a glance. A validated rule is applied without the
    call: a person has already certified that answer for this merchant.

    Note item M4: this read deliberately gets NO merchant profile. Its job is
    to be an INDEPENDENT second opinion on a remembered category, and prose
    describing what the business usually buys from this merchant is evidence
    for the same answer memory already holds. Feeding it in would teach the
    detector to agree with itself, and the disagreement glance item 115
    exists for would quietly stop firing."""
    cat = _learned_categorization(recall)
    if not recall.validated:
        if client is not None:
            read = _classify_lines_via_llm(
                receipt.line_items, client, chart_of_accounts
            )
        else:
            read = tuple(_classify_line_keyword(li) for li in receipt.line_items)
        disagreed = sorted({
            li.categorization.category
            for li in read
            if li.categorization is not None
            and li.categorization.category
            and li.categorization.category != recall.category
        })
        if disagreed:
            cat = replace(
                cat,
                reasoning=(
                    f"{cat.reasoning}; the receipt's items read "
                    f"{', '.join(disagreed)}"
                ),
                decision=DECISION_LEARNED_OVER_LINE,
            )
    return replace(
        receipt,
        line_items=tuple(
            replace(li, categorization=cat) for li in receipt.line_items
        ),
    )


# ── Direct-to-GL engine (Phase 1, item 3) ───────────────────────────
#
# One invariant carries the whole path: `bool(cat.category)` is False
# exactly when the engine REFUSED. A resolved line's `category` is the curated
# leaf CODE (the cross-entity identity) and its `zoho_account` that leaf's
# name in the receipt's own org; a refused line has `category=None`, no
# account, source REVIEW and a named `refusal`. No placeholder string ever
# stands in for a category, so the seventeen truthiness gates downstream read
# a refusal as "uncategorized" and never as an answer.
#
# Every answer, whichever tier produced it, goes through
# `resolve_posting_account`, so there is one place a reference becomes an
# account and it is org-scoped: a Cloud Services name cannot resolve on a
# Corporate Services receipt.


def _refused_cat(
    code: str, *, confidence: float = 0.0, detail: str = ""
) -> Categorization:
    text = refusal_text(code)
    return Categorization(
        category=None,
        zoho_account=None,
        confidence=confidence,
        source=ClassificationSource.REVIEW,
        reasoning=f"{text} ({detail})" if detail else text,
        refusal=code,
    )


def _gl_categorization(
    res: PostingResolution,
    org_id: str,
    *,
    source: ClassificationSource,
    confidence: float,
    reasoning: str,
    decision: str | None = None,
) -> Categorization:
    """A resolution as a line's categorization: the leaf, or the refusal."""
    if not res.resolved:
        return _refused_cat(
            res.reason or ACCOUNT_UNRESOLVED, confidence=confidence,
            detail=reasoning,
        )
    binding = curated_leaves.binding(res.code, org_id)
    return Categorization(
        category=res.code,
        zoho_account=binding.name if binding is not None else None,
        confidence=confidence,
        source=source,
        reasoning=reasoning,
        decision=decision,
    )


def _stamp_lines(receipt: Receipt, cat: Categorization) -> Receipt:
    items = receipt.line_items or (_synthesize_total_line(receipt),)
    return replace(
        receipt,
        line_items=tuple(replace(li, categorization=cat) for li in items),
    )


def _gl_leaf_labels(org_id: str | None) -> tuple[str, ...]:
    """This org's `"CODE name"` labels. Takes the ORG ID, never an entity
    name: `llm_leaf_labels` answers a name with an empty tuple, silently, so
    the caller must have resolved the org first (`org_id_for_entity`)."""
    if not org_id or not org_id.isdigit():
        return ()
    return curated_leaves.llm_leaf_labels(org_id)


def _gl_model_result(
    result: ClassificationResult,
    org_id: str,
    *,
    source_on_hit: ClassificationSource,
) -> Categorization:
    """The model's pick as a leaf of THIS org, or a refusal. The reply is
    resolved only within `org_id` (`code_of`), so a leaf the model names from
    another entity's wording refuses rather than posting.

    A summary account with postable accounts under it refuses too (owner,
    2026-09-25). The model is no longer offered one (`llm_leaf_labels`); this
    catches a reply that names one anyway. Only the model passes here: the
    merchant list, a remembered rule and a person may still pick a parent."""
    if result.category is None or result.confidence < REVIEW_THRESHOLD:
        return _refused_cat(
            ACCOUNT_UNRESOLVED, confidence=result.confidence,
            detail=result.reasoning or "",
        )
    res = resolve_posting_account(
        org_id=org_id, legal_entity_id=None, vendor=None,
        llm_leaf=result.category or result.zoho_account,
    )
    if res.resolved and curated_leaves.has_postable_children(org_id, res.code):
        return _refused_cat(
            MODEL_PICKED_PARENT, confidence=result.confidence,
            detail=f"{res.code}; {result.reasoning or ''}".rstrip("; "),
        )
    return _gl_categorization(
        res, org_id, source=source_on_hit, confidence=result.confidence,
        reasoning=result.reasoning,
    )


def _gl_read_lines(
    items: tuple[LineItem, ...],
    labels: tuple[str, ...],
    org_id: str,
    client: LLMClient,
    merchant_profile: str | None = None,
) -> tuple[LineItem, ...]:
    """Tier 3 on a receipt with readable lines: one batched call, the
    entity's leaves as the only choices."""
    assert labels, "an empty leaf list is a refusal, never a prompt"
    inputs = [
        LineItemInput(
            description=it.description,
            line_total=it.line_total,
            quantity=it.quantity,
        )
        for it in items
    ]
    results = client.classify_line_items(
        inputs, categories=list(labels), chart_of_accounts=None,
        **_profile_kwarg(merchant_profile),
    )
    out = []
    for i, item in enumerate(items):
        cat = (
            _gl_model_result(
                results[i], org_id, source_on_hit=ClassificationSource.LINE)
            if i < len(results)
            else _refused_cat(ACCOUNT_UNRESOLVED)
        )
        out.append(replace(item, categorization=cat))
    return tuple(out)


def _gl_learned(
    receipt: Receipt,
    recall: "LearnedRecall",
    org_id: str,
    learned: "MerchantCategoryLookup",
    labels: tuple[str, ...],
    client: LLMClient | None,
    has_lines: bool,
) -> Receipt | None:
    """Tier 1, the (entity, vendor) rule a person taught. None when the rule
    names no leaf (a bucket-only rule, or a vendor-only recall, which never
    decides an account): the engine then asks the model, overriding nothing.

    A rule naming a leaf this entity cannot post to REFUSES rather than
    falling through (`posting_resolution`: the model must not overrule a
    person). A rule nobody validated still gets the item-115 second read on a
    receipt with lines, and says so when the lines disagree."""
    res = resolve_posting_account(
        org_id=org_id, legal_entity_id=receipt.legal_entity_id,
        vendor=receipt.detected_vendor, lookup=learned,
    )
    if not res.resolved and res.code is None:
        return None
    reasoning = _learned_categorization(recall).reasoning
    decision = None
    if res.resolved and has_lines and not recall.validated and client is not None:
        read = _gl_read_lines(receipt.line_items, labels, org_id, client)
        disagreed = sorted({
            li.categorization.category
            for li in read
            if li.categorization is not None
            and li.categorization.category
            and li.categorization.category != res.code
        })
        if disagreed:
            reasoning = (
                f"{reasoning}; the receipt's items read {', '.join(disagreed)}"
            )
            decision = DECISION_LEARNED_OVER_LINE
    cat = _gl_categorization(
        res, org_id, source=ClassificationSource.LEARNED, confidence=1.0,
        reasoning=reasoning, decision=decision,
    )
    return _stamp_lines(receipt, cat)


def _categorize_one_gl(
    receipt: Receipt,
    client: LLMClient | None,
    learned: "MerchantCategoryLookup | None" = None,
    *,
    org_id: str | None,
    judge_each_receipt: bool = False,
    merchant_profile: str | None = None,
) -> Receipt:
    """The GL chain for one receipt: rule -> model -> refuse.

    `org_id` is the receipt's entity already resolved to its Zoho org. An
    entity with no org id, or one outside the curated set, refuses
    `org_not_curated` before anything is asked, and so does an org whose leaf
    list comes back empty: an empty list is a refusal, not a prompt.

    The keyword stub has no leaf vocabulary, so without a client a receipt no
    rule resolves refuses `account_unresolved` rather than being given a
    bucket. The ER report's own account is not consulted: this path is the
    tool's own judgment against Dirk's curated chart.
    """
    if not str(receipt.legal_entity_id or "").strip():
        return _stamp_lines(receipt, _refused_cat(ENTITY_MISSING))
    labels = _gl_leaf_labels(org_id)
    if not curated_leaves.covers_org(org_id) or not labels:
        return _stamp_lines(receipt, _refused_cat(curated_leaves.NOT_COVERED))

    recall = _recall_for(receipt, learned)
    has_lines = bool(receipt.line_items) and not _all_vague(receipt.line_items)
    leads = recall is not None and (
        not has_lines or (not judge_each_receipt and recall.taught_by_person)
    )
    if leads:
        taught = _gl_learned(
            receipt, recall, org_id, learned, labels, client, has_lines)
        if taught is not None:
            return taught

    if client is None:
        return _stamp_lines(receipt, _refused_cat(ACCOUNT_UNRESOLVED))
    if has_lines:
        return replace(receipt, line_items=_gl_read_lines(
            receipt.line_items, labels, org_id, client, merchant_profile))
    if not receipt.detected_vendor:
        return _stamp_lines(receipt, _refused_cat(
            ACCOUNT_UNRESOLVED, detail="no vendor and no line items"))
    result = client.classify_by_vendor(
        vendor=receipt.detected_vendor,
        total=receipt.detected_total or Decimal("0"),
        categories=list(labels),
        chart_of_accounts=None,
        **_profile_kwarg(merchant_profile),
    )
    return _stamp_lines(receipt, _gl_model_result(
        result, org_id, source_on_hit=ClassificationSource.VENDOR))


def _registry_gl(
    receipt: Receipt, match, learned: "MerchantCategoryLookup | None",
    org_id: str | None, *, entity_orgs: "Mapping[str, str] | None" = None,
) -> Receipt | None:
    """The registry tier on the GL engine, or None to hand the receipt to it.

    Items 180/181: the merchant's own account for THIS company (its
    per-company map, matched on the org) decides first. A person set it for
    exactly this merchant and this company, which is more specific than
    anything below. A code this org cannot post to refuses with its reason
    rather than falling through, as a taught rule does: the model must not
    overrule a person.

    Otherwise the account the M1 order picks (`_registry_account`: the
    company's rule, else the registry's own) is tried, then the default
    category itself, each resolved within THIS org. The first that names a
    leaf decides: postable stamps it, anything else refuses. A default naming
    no leaf, and an uncovered org, return None; the engine then answers (and
    an uncovered org refuses there, without a model call)."""
    if not curated_leaves.covers_org(org_id):
        return None
    mapped = company_account(getattr(match, "accounts", ()), org_id, entity_orgs)
    if mapped is not None:
        label, code = mapped
        reasoning = f"merchant registry account for {label}"
        if not curated_leaves.is_postable(org_id, code):
            return _stamp_lines(receipt, _refused_cat(
                curated_leaves.refusal_reason(org_id, code),
                detail=f"{reasoning}: {code}"))
        res = resolve_posting_account(
            org_id=org_id, legal_entity_id=None, vendor=None, llm_leaf=code)
        return _stamp_lines(receipt, _gl_categorization(
            res, org_id, source=ClassificationSource.REGISTRY,
            confidence=1.0, reasoning=reasoning,
        ))
    if not match.category:
        return None
    account, reasoning = _registry_account(receipt, match, learned)
    for ref in (account, match.category):
        code = curated_leaves.code_of(ref, org_id)
        if code is None:
            continue
        res = resolve_posting_account(
            org_id=org_id, legal_entity_id=None, vendor=None, llm_leaf=code)
        return _stamp_lines(receipt, _gl_categorization(
            res, org_id, source=ClassificationSource.REGISTRY,
            confidence=1.0, reasoning=reasoning,
        ))
    return None


# ── LLM-path implementations (slice 2) ──────────────────────────────


def _profile_kwarg(merchant_profile: str | None) -> dict:
    """`{"merchant_profile": ...}` when the merchant has prose, else `{}`
    (note item M4).

    The parallel-field contract applied to a call signature: a merchant with
    no profile produces the exact call the categorizer made before M4, so no
    existing `LLMClient` implementation — the mock, a test fake, a provider
    subclass written against the old Protocol — has to change to keep
    working. Only a merchant somebody wrote a profile for sees the new
    keyword."""
    text = str(merchant_profile or "").strip()
    return {"merchant_profile": text} if text else {}


def _classify_lines_via_llm(
    items: tuple[LineItem, ...],
    client: LLMClient,
    chart_of_accounts: list[str] | None = None,
    merchant_profile: str | None = None,
) -> tuple[LineItem, ...]:
    """Tier 1 via LLM. One batched call per receipt regardless of
    line-item count (cost discipline).

    `merchant_profile` (note item M4) is the registry's free prose about this
    receipt's merchant. It is forwarded ONLY when the merchant actually has
    one, so a client implementation that predates M4 keeps being called with
    exactly the arguments it already accepts."""
    inputs = [
        LineItemInput(
            description=it.description,
            line_total=it.line_total,
            quantity=it.quantity,
        )
        for it in items
    ]
    results = client.classify_line_items(
        inputs, categories=list(EXPENSE_CATEGORIES),
        chart_of_accounts=chart_of_accounts,
        **_profile_kwarg(merchant_profile),
    )

    out: list[LineItem] = []
    for item, result in zip(items, results):
        out.append(
            replace(
                item,
                categorization=_categorization_from_result(
                    result, source_on_hit=ClassificationSource.LINE
                ),
            )
        )
    return tuple(out)


def _classify_vendor_via_llm(
    item: LineItem,
    vendor: str | None,
    total: Decimal | None,
    client: LLMClient,
    chart_of_accounts: list[str] | None = None,
    merchant_profile: str | None = None,
) -> LineItem:
    """Tier 2 via LLM. Single call with vendor name + total, plus the
    merchant's profile when the registry carries one (note item M4). This is
    the tier the prose helps most: the vendor name is otherwise the only
    clue this path has."""
    if not vendor:
        return replace(
            item,
            categorization=Categorization(
                category=None, zoho_account=None,
                confidence=0.0, source=ClassificationSource.REVIEW,
                reasoning="No vendor + no line items — Chris assigns",
            ),
        )
    result = client.classify_by_vendor(
        vendor=vendor,
        total=total or Decimal("0"),
        categories=list(EXPENSE_CATEGORIES),
        chart_of_accounts=chart_of_accounts,
        **_profile_kwarg(merchant_profile),
    )
    return replace(
        item,
        categorization=_categorization_from_result(
            result, source_on_hit=ClassificationSource.VENDOR
        ),
    )


def _categorization_from_result(
    result: ClassificationResult,
    *,
    source_on_hit: ClassificationSource,
) -> Categorization:
    """Apply the REVIEW_THRESHOLD policy to an LLM result.

    Below threshold, OR null category, OR category not in our 8 →
    Tier 3 REVIEW. Above threshold → Tier 1/Tier 2 per source_on_hit.
    """
    if (
        result.category is None
        or result.confidence < REVIEW_THRESHOLD
        or result.category not in EXPENSE_CATEGORIES
    ):
        return Categorization(
            category=None,
            zoho_account=result.zoho_account,
            confidence=result.confidence,
            source=ClassificationSource.REVIEW,
            reasoning=result.reasoning or NO_SIGNAL_REASON,
        )
    return Categorization(
        category=result.category,
        zoho_account=result.zoho_account,
        confidence=result.confidence,
        source=source_on_hit,
        reasoning=result.reasoning,
    )


# ── Keyword-stub implementations (slice 1 fallback) ──────────────────


def _all_vague(items: tuple[LineItem, ...]) -> bool:
    """True if every line item's description is too vague to classify
    on (matches a vagueness token or is < 4 chars after stripping).
    """
    if not items:
        return True
    return all(_is_vague(li.description) for li in items)


_WORD_RE = re.compile(r"[a-z]+")


def _is_vague(description: str) -> bool:
    """True iff the description is too vague to drive line-item
    classification on its own. Word-boundary match against the
    vagueness tokens — NOT substring match, since `"fee" in "coffee"`
    would falsely flag "coffee beans" as vague.
    """
    desc = (description or "").strip().lower()
    if len(desc) < 4:
        return True
    words = set(_WORD_RE.findall(desc))
    return any(token in words for token in _VAGUE_DESCRIPTION_TOKENS)


def _classify_line_keyword(item: LineItem) -> LineItem:
    """Tier 1 fallback: line-item description → category via keyword
    table. No vendor input. Used when no LLMClient is wired."""
    desc = (item.description or "").lower()
    for keyword, category in _LINE_KEYWORDS.items():
        if keyword in desc:
            return replace(
                item,
                categorization=Categorization(
                    category=category,
                    zoho_account=None,
                    confidence=STUB_CONFIDENCE,
                    source=ClassificationSource.LINE,
                    reasoning=f"{STUB_LINE_REASON}: '{keyword}'",
                ),
            )

    # No keyword hit → Tier 3 REVIEW.
    return replace(
        item,
        categorization=Categorization(
            category=None,
            zoho_account=None,
            confidence=0.0,
            source=ClassificationSource.REVIEW,
            reasoning=NO_SIGNAL_REASON,
        ),
    )


def _classify_vendor_keyword(item: LineItem, vendor: str | None) -> LineItem:
    """Tier 2 fallback via vendor keyword table. Marked VENDOR.
    Used when no LLMClient is wired."""
    if not vendor:
        return replace(
            item,
            categorization=Categorization(
                category=None,
                zoho_account=None,
                confidence=0.0,
                source=ClassificationSource.REVIEW,
                reasoning="No vendor + no line items — Chris assigns",
            ),
        )

    vlow = vendor.lower()
    for keyword, category in _VENDOR_KEYWORDS.items():
        if keyword in vlow:
            return replace(
                item,
                categorization=Categorization(
                    category=category,
                    zoho_account=None,
                    confidence=STUB_CONFIDENCE,
                    source=ClassificationSource.VENDOR,
                    reasoning=f"{STUB_VENDOR_REASON}: vendor '{vendor}' → '{keyword}'",
                ),
            )

    # Vendor present but no keyword match → still REVIEW (we don't
    # invent a category just because a vendor name exists).
    return replace(
        item,
        categorization=Categorization(
            category=None,
            zoho_account=None,
            confidence=0.0,
            source=ClassificationSource.REVIEW,
            reasoning=f"Vendor '{vendor}' not in keyword map — Chris assigns",
        ),
    )


def _synthesize_total_line(receipt: Receipt) -> LineItem:
    """Build a placeholder LineItem carrying the receipt total when
    OCR found no itemization. Marked clearly so the report writer
    can flag it visually.
    """
    return LineItem(
        description="(receipt total, no itemization)",
        line_total=receipt.detected_total or Decimal("0"),
    )


# ── Top-level adjudication (WS2, 2026-07-21) ─────────────────────────
#
# The owner's decision: under `override_er_category` the tool's own category /
# account should not win UNCONDITIONALLY (PR1), only when it HEAVILY
# contradicts the Zoho report -- a different Zoho ROOT-GROUP (top-level).
# When both the tool's pick and the report's category roll up into the same
# root-group, trust the report and keep its category. This gate is
# deterministic (no LLM call): both sides resolve through the chart of
# accounts to their root-group and the roots are compared.

# Adjudication verdicts recorded on `Categorization.decision`, surfaced in the
# reconciled CSV "Category Decision" column.
DECISION_KEPT_ER = "kept_er"
DECISION_AI_OVERRIDE_HEAVY = "ai_override_heavy"
DECISION_REVIEW_UNRESOLVED = "review_unresolved"

# Fallback map used ONLY when the LLM produced one of our 8 categories but no
# specific GL leaf (no chart wired for the pick, or none clearly fit): the
# category maps to the Zoho root-GROUP it belongs to, so a heavy top-level
# mismatch can still be detected without an LLM account. The target names are
# the Brisken operating root-groups (confirmed against zoho-books-coa.json:
# every entity's postable operating subtree uses these root names, e.g. Cloud
# Services / Holding / Consulting). A mapped root that is not an actual root of
# the run's chart (or not in the run's scope_groups) counts as UNRESOLVED, so
# the gate stays conservative on a chart whose roots are named differently.
EXPENSE_CATEGORY_ROOT_GROUP: dict[str, str] = {
    "Travel & Transport": "Travel Expense",
    # Brisken's in-scope operating charts roll travel meals into Travel Expense
    # (no standalone Meals root in the card-expense scope groups).
    "Meals & Entertainment": "Travel Expense",
    "Software & Subscriptions": "IT: Computer and Internet Expenses",
    "Office Supplies & Consumables": "Office Infra and Admin",
    "Equipment & Hardware": "Office Infra and Admin",
    "Marketing & Advertising": "Marketing & Selling Expenses",
    "Professional Services": "Professional Fees",
    "Utilities & Premises": "Office Infra and Admin",
}


def _resolve_account(chart: "ChartOfAccounts", ref: str | None) -> "Account | None":
    """Resolve a posting-account reference to a chart Account, mirroring the
    Zoho export's / COA gate's resolution: exact code-or-name first, then the
    leading token as a code and the remainder as a name. Handles BOTH the
    report's "CODE - Name" print form and the categorizer's "CODE Name" label
    form."""
    ref = (ref or "").strip()
    if not ref:
        return None
    acct = chart.resolve(ref)
    if acct is not None:
        return acct
    head, _, tail = ref.partition(" ")
    acct = chart.by_code(head.strip())
    if acct is None and tail.strip():
        acct = chart.by_name(tail.strip().lstrip("-").strip())
    return acct


def _root_of(chart: "ChartOfAccounts", ref: str | None) -> str | None:
    """The Zoho root-group of the account `ref` resolves to, or None when it
    does not resolve in the chart."""
    acct = _resolve_account(chart, ref)
    return chart.root_group(acct) if acct is not None else None


def _norm_label(ref: str | None) -> str:
    """Normalize a posting-account label for equality (lowercase, collapse
    non-alphanumerics), so the report's "E100010-31 - Travel..." and a
    fallback copy compare equal regardless of separator noise."""
    return re.sub(r"[^a-z0-9]", "", (ref or "").lower())


def adjudicate_receipts(
    receipts: list[Receipt],
    chart: "ChartOfAccounts",
    *,
    scope_groups: "list[str] | None" = None,
) -> list[Receipt]:
    """Apply the top-level adjudication gate to every receipt.

    For each categorized line, compare the tool's category/account to the
    report's `zoho_category` at the Zoho root-group level. Different root-group
    => HEAVY mismatch => the tool's account is inserted (it posts) and the line
    is flagged for review. Same root-group (or an unresolvable comparison) =>
    the report's category is kept. The verdict is recorded on each line's
    `Categorization.decision`. Pure; does not mutate inputs.

    Runs only under `override_er_category` with a chart wired (the caller
    gates); without a chart there is no root-group to compare and PR1's
    `_carry_zoho_account` behaviour stands unchanged.
    """
    chart_roots = {chart.root_group(a) for a in chart.accounts}
    scope_set = {g.strip() for g in scope_groups} if scope_groups else None
    return [
        adjudicate_categorization(
            r, chart, scope_groups=scope_groups,
            _chart_roots=chart_roots, _scope_set=scope_set,
        )
        for r in receipts
    ]


def adjudicate_categorization(
    receipt: Receipt,
    chart: "ChartOfAccounts",
    *,
    scope_groups: "list[str] | None" = None,
    _chart_roots: "set[str] | None" = None,
    _scope_set: "set[str] | None" = None,
) -> Receipt:
    """Adjudicate one receipt's line categorizations against the report's
    `zoho_category` at the Zoho root-group level (see `adjudicate_receipts`).

    No-op (returns the receipt unchanged) when the report carries no
    `zoho_category` -- there is nothing to adjudicate against, so the tool's
    own pick (already kept by `_carry_zoho_account`) stands.
    """
    if not receipt.zoho_category:
        return receipt

    chart_roots = (
        _chart_roots if _chart_roots is not None
        else {chart.root_group(a) for a in chart.accounts}
    )
    scope_set = (
        _scope_set if _scope_set is not None
        else ({g.strip() for g in scope_groups} if scope_groups else None)
    )

    report_root = _root_of(chart, receipt.zoho_category)
    norm_report = _norm_label(receipt.zoho_category)

    new_items: list[LineItem] = []
    for li in receipt.line_items:
        cat = li.categorization
        if cat is None:
            new_items.append(li)
            continue

        # The LLM's OWN account is its zoho_account UNLESS `_carry_zoho_account`
        # already fell that back to the report's category (no leaf picked).
        own_account = cat.zoho_account
        if own_account and _norm_label(own_account) == norm_report:
            own_account = None

        tool_root = _root_of(chart, own_account) if own_account else None
        if tool_root is None and cat.category:
            mapped = EXPENSE_CATEGORY_ROOT_GROUP.get(cat.category)
            if mapped and _is_real_root(mapped, chart_roots, scope_set):
                tool_root = mapped

        decision, final_account = _adjudicate_line(
            report_root=report_root,
            tool_root=tool_root,
            own_account=own_account,
            report_category=receipt.zoho_category,
            has_tool_signal=bool(cat.category or own_account),
        )
        new_items.append(
            replace(li, categorization=replace(
                cat, zoho_account=final_account, decision=decision,
            ))
        )

    return replace(receipt, line_items=tuple(new_items))


def _is_real_root(
    root_name: str, chart_roots: set[str], scope_set: set[str] | None
) -> bool:
    """A fallback-mapped root name counts only when it is an actual root-group
    of this run's chart AND (when a scope is set) within scope -- so the
    semantic default map does not force a spurious mismatch on a chart whose
    roots are named differently (e.g. entity-bucket roots)."""
    if root_name not in chart_roots:
        return False
    if scope_set is not None:
        return root_name in scope_set
    return True


def _adjudicate_line(
    *,
    report_root: str | None,
    tool_root: str | None,
    own_account: str | None,
    report_category: str,
    has_tool_signal: bool,
) -> tuple[str, str | None]:
    """The gate decision for one line. Returns (decision, posting account).

    * no tool signal at all (pure REVIEW), or either side unresolvable
      => keep the report's category (conservative).
    * different root-group => insert the tool's account (heavy override; it
      becomes a review row -- `own_account` may be None when the tool had a
      category but no GL leaf, in which case the reviewer assigns the leaf).
    * same root-group => keep the report's category.
    """
    if not has_tool_signal or report_root is None or tool_root is None:
        return DECISION_REVIEW_UNRESOLVED, report_category
    if tool_root != report_root:
        return DECISION_AI_OVERRIDE_HEAVY, own_account
    return DECISION_KEPT_ER, report_category
