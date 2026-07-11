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

    Pure function; does not mutate inputs.
    """
    return [_categorize_one(r, client, chart_of_accounts, learned) for r in receipts]


def _categorize_one(
    receipt: Receipt,
    client: LLMClient | None,
    chart_of_accounts: list[str] | None,
    learned: "MerchantCategoryLookup | None" = None,
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
        return _carry_zoho_account(replace(receipt, line_items=categorized))

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
            )
        )
    if client is not None:
        classified = _classify_vendor_via_llm(
            synthesized, receipt.detected_vendor, receipt.detected_total,
            client, chart_of_accounts,
        )
    else:
        classified = _classify_vendor_keyword(synthesized, receipt.detected_vendor)
    return _carry_zoho_account(replace(receipt, line_items=(classified,)))


def _carry_zoho_account(receipt: Receipt) -> Receipt:
    """Carry the Zoho Expense GL category onto each line's categorization as
    the posting account (Dirk 2026-06-16: Zoho expenses arrive pre-classified,
    so Zoho's account is authoritative for posting; the tool's own AI category
    is the verify pass shown alongside it). Only `zoho_account` is set from the
    report; the AI/keyword category (our 8) is left untouched so the reviewer
    sees both. No-op when the receipt carries no Zoho category."""
    if not receipt.zoho_category:
        return receipt
    new_items = []
    for li in receipt.line_items:
        cat = li.categorization
        if cat is not None:
            new_items.append(
                replace(li, categorization=replace(cat, zoho_account=receipt.zoho_category))
            )
        else:
            new_items.append(li)
    return replace(receipt, line_items=tuple(new_items))


def _learned_categorization(
    receipt: Receipt, learned: "MerchantCategoryLookup | None"
) -> Categorization | None:
    """A Tier-1 LEARNED categorization for this receipt's merchant, or None
    when there is no learned mapping. The provenance reasoning carries the
    month of the confirming decision so the workbench can show it."""
    if learned is None or not receipt.detected_vendor:
        return None
    hit = learned.get(receipt.legal_entity_id, receipt.detected_vendor)
    if hit is None or not hit.category:
        return None
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
