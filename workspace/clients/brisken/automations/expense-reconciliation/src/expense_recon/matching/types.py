"""Domain types for the matching engine.

Faithful to v2 spec §15 and §23: deterministic-first matching with
LLM-only-for-judgment, three currency layers (transaction /
account-card / book), tenant-scoped and legal-entity-scoped entities.

Categorization (slice-2/slice-4 work, BLUEPRINT LD-1 / LD-2):

* `LineItem` — one purchased item parsed from a receipt by OCR.
  Categorization is per line item, not per receipt; the vendor
  name is metadata only and never feeds the classifier.
* `Categorization` — attaches a tier-1/tier-2/tier-3 classification
  result to a line item. `source` drives row coloring in the
  Excel report (LD-4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class MatchType(str, Enum):
    """Outcomes the matching engine produces for a (transaction, receipt) pair.

    Mirrors v2 spec §15.4 matching outcomes.
    """

    EXACT = "exact"                # high-confidence deterministic match
    PROBABLE = "probable"          # deterministic with tolerance
    POSSIBLE = "possible"          # weaker signal; review required
    FX_JUDGMENT = "fx_judgment"    # currencies differ; LLM judgment needed
    AMBIGUOUS = "ambiguous"        # multiple equally-strong candidates


class ClassificationSource(str, Enum):
    """Where the line item's category came from. Drives report row color
    (BLUEPRINT LD-4) and Chris's review priority (BLUEPRINT LD-2).
    """

    LINE = "LINE"          # Tier 1: line-item LLM classifier; trusted
    VENDOR = "VENDOR"      # Tier 2: vendor-name fallback; mark with ⚠
    REVIEW = "REVIEW"      # Tier 3: confidence too low or no signal at all
    UNCLASSIFIED = "UNCLASSIFIED"  # pre-categorization default


# The eight expense categories Brisken uses (BLUEPRINT LD-1). The
# classifier returns one of these strings (or None for REVIEW tier).
# Changing this list is an explicit config change, never inferred.
EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Travel & Transport",
    "Meals & Entertainment",
    "Software & Subscriptions",
    "Office Supplies & Consumables",
    "Equipment & Hardware",
    "Marketing & Advertising",
    "Professional Services",
    "Utilities & Premises",
)


@dataclass(frozen=True)
class Categorization:
    """The classification result for one line item.

    `category` is one of `EXPENSE_CATEGORIES` (or None when source ==
    REVIEW and Chris must assign manually). `zoho_account` is the
    mapped Brisken Zoho chart-of-accounts entry (e.g.,
    "6420 - Office Equipment"); None until chart-of-accounts ingest
    is wired in slice 4.
    """

    category: str | None
    zoho_account: str | None
    confidence: float
    source: ClassificationSource
    reasoning: str = ""


@dataclass(frozen=True)
class LineItem:
    """One purchased item on a receipt.

    OCR (slice 2) populates `description`, `quantity`, `unit_price`,
    `line_total`. The categorizer (slice 4) populates `categorization`.

    `description` is the raw text from the receipt. For receipts with
    no itemization (restaurant credit-card slips, taxi receipts,
    parking meters), ingest synthesizes one LineItem with
    `description="(receipt total, no itemization)"` and the receipt's
    total as `line_total`, so the downstream pipeline is uniform —
    every classifiable receipt has at least one LineItem.

    Per BLUEPRINT LD-2: `categorization.source == VENDOR` indicates a
    synthesized or vague line item where the classifier had to fall
    back to vendor-name signal.
    """

    description: str
    line_total: Decimal
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    categorization: Categorization | None = None


@dataclass(frozen=True)
class Transaction:
    """A line on a card / bank statement (v2 spec §23.8)."""

    transaction_id: str
    legal_entity_id: str
    account_id: str
    transaction_date: date
    posting_date: date | None
    amount: Decimal
    transaction_currency: str       # currency the transaction posted in (§20)
    account_card_currency: str      # the card / account's currency (§20)
    vendor_from_statement: str
    raw_text: str = ""


@dataclass(frozen=True)
class Receipt:
    """An extracted receipt (v2 spec §23.9).

    `line_items` is the list of items OCR extracted from the receipt.
    Empty list = OCR found only a header/total (common for restaurant
    slips, taxi receipts, parking) → triggers the vendor-fallback
    categorization path per BLUEPRINT LD-2 Tier 2.

    `line_items` may carry categorization results; see `LineItem`.
    Sum of `line_total` across items should reconcile to
    `detected_total` (modulo tax/tip lines that may not be itemized).
    """

    document_id: str
    legal_entity_id: str
    detected_date: date | None
    detected_total: Decimal | None
    detected_currency: str | None
    detected_vendor: str | None
    detected_reference: str | None = None
    ocr_text: str = ""
    line_items: tuple[LineItem, ...] = ()


@dataclass(frozen=True)
class Match:
    """A scored candidate pairing of a transaction and a receipt."""

    transaction_id: str
    document_id: str
    match_type: MatchType
    confidence: float
    reason: str
    requires_review: bool = False


@dataclass
class MatchOutcome:
    """The result of running the matcher across a month of data.

    Fields are intentionally explicit and side-by-side so that the
    reconciliation guarantee (v2 spec §25.5) can be verified at a
    glance: every transaction either has a match, is in
    `unmatched_transactions`, or is in `judgment_required`. Nothing
    is silently dropped.
    """

    matches: list[Match] = field(default_factory=list)
    unmatched_transactions: list[str] = field(default_factory=list)
    unmatched_receipts: list[str] = field(default_factory=list)
    judgment_required: list[Match] = field(default_factory=list)
    ambiguous: list[Match] = field(default_factory=list)
