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
from typing import TYPE_CHECKING

from .llm.client import (
    ClassificationResult,
    LineItemInput,
    LLMClient,
)
from .matching.types import (
    EXPENSE_CATEGORIES,
    Categorization,
    ClassificationSource,
    LineItem,
    Receipt,
)

if TYPE_CHECKING:
    from .ingest.chart_of_accounts import Account, ChartOfAccounts
    from .learning import MerchantCategoryLookup


STUB_LINE_REASON = "[STUB-KEYWORD] line-item keyword match (slice-1 placeholder)"
STUB_VENDOR_REASON = "[STUB-KEYWORD] vendor keyword match — confirm category"
NO_SIGNAL_REASON = "No classification signal — Chris assigns category"

# Confidence below this routes to Tier 3 REVIEW regardless of source.
REVIEW_THRESHOLD = 0.6

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
) -> list[Receipt]:
    """Return a new list of receipts with line_items carrying
    Categorization results per LD-2.

    When `client` is provided, uses LLM calls. When None (default),
    falls back to the keyword stub — preserves slice-1 behaviour for
    callers that haven't wired an LLM yet.

    `chart_of_accounts` is the in-scope Zoho account labels (slice 4.1
    `ChartOfAccounts.llm_account_labels()`). When supplied, the LLM is
    asked to also pick the specific `zoho_account` leaf per LD-2; the
    keyword stub ignores it (no account mapping). Ignored entirely
    without an LLM client.

    `learned` (Phase 2) is a cross-run memory of confirmed
    merchant->category decisions. It is consulted ONLY on the weak
    vendor-fallback path (a receipt with no usable line items); a
    confident line read always wins. None / empty => behaviour unchanged.

    `override_er_category` (2026-07-21 owner decision) flips who owns the
    posting account. Default False keeps the 2026-06-16 behaviour (the
    Zoho Expense report's own GL account is authoritative). True makes the
    tool's own category + account authoritative: the LLM's / memory's
    `zoho_account` pick is kept, and the report's `zoho_category` is only
    a fallback when the line has no account of its own. See
    `_carry_zoho_account`.

    Pure function; does not mutate inputs.
    """
    return [
        _categorize_one(
            r, client, chart_of_accounts, learned,
            override_er_category=override_er_category,
        )
        for r in receipts
    ]


def _categorize_one(
    receipt: Receipt,
    client: LLMClient | None,
    chart_of_accounts: list[str] | None,
    learned: "MerchantCategoryLookup | None" = None,
    *,
    override_er_category: bool = False,
) -> Receipt:
    """Apply the LD-2 tier rules to a single receipt."""

    if receipt.line_items and not _all_vague(receipt.line_items):
        # LINE path (Tier 1). A confident line read ALWAYS wins; memory is
        # never consulted here, so a learned merchant->category can never
        # preempt a good line read (Phase 2 invariant: fallback, not override).
        if client is not None:
            categorized = _classify_lines_via_llm(
                receipt.line_items, client, chart_of_accounts
            )
        else:
            categorized = tuple(_classify_line_keyword(li) for li in receipt.line_items)
        return _carry_zoho_account(
            replace(receipt, line_items=categorized),
            override_er_category=override_er_category,
        )

    # No usable line items → the weak path that today re-pays for a vendor
    # guess and lands Tier-2. Memory FALLBACK first: a confirmed
    # merchant->category recalled from a prior month upgrades it to Tier-1
    # LEARNED and skips the LLM/keyword vendor call (the deterministic-first
    # win). Only here, never above the line path.
    synthesized = _synthesize_total_line(receipt)
    learned_cat = _learned_categorization(receipt, learned)
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
            client, chart_of_accounts,
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


def _learned_categorization(
    receipt: Receipt, learned: "MerchantCategoryLookup | None"
) -> Categorization | None:
    """A Tier-1 LEARNED categorization for this receipt's merchant, or None
    when there is no learned mapping. The provenance reasoning carries the
    month of the confirming decision so the workbench can show it; rows
    seeded from Zoho Books posting history (L2, source_run "zoho-seed:*")
    name that history instead of a reviewer decision."""
    if learned is None or not receipt.detected_vendor:
        return None
    hit = learned.get(receipt.legal_entity_id, receipt.detected_vendor)
    if hit is None or not hit.category:
        return None
    if hit.source_run and hit.source_run.startswith("zoho-seed"):
        provenance = "from your Zoho Books posting history"
    else:
        when = hit.last_confirmed_at[:7] if hit.last_confirmed_at else None
        provenance = (
            f"learned from your {when} decision" if when
            else "learned from your confirmed decision"
        )
    return Categorization(
        category=hit.category,
        zoho_account=hit.zoho_account,
        confidence=1.0,
        source=ClassificationSource.LEARNED,
        reasoning=provenance,
    )


# ── LLM-path implementations (slice 2) ──────────────────────────────


def _classify_lines_via_llm(
    items: tuple[LineItem, ...],
    client: LLMClient,
    chart_of_accounts: list[str] | None = None,
) -> tuple[LineItem, ...]:
    """Tier 1 via LLM. One batched call per receipt regardless of
    line-item count (cost discipline)."""
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
) -> LineItem:
    """Tier 2 via LLM. Single call with vendor name + total."""
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
