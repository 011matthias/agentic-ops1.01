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
    LEARNED = "LEARNED"    # Tier 1: confirmed merchant->category recalled from memory (Phase 2)
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
    """A line on a card / bank statement (v2 spec §23.8).

    Currency layers (v2 spec §20, three distinct concepts — E7):

    * `transaction_currency` — what THIS transaction posted in. Usually
      the card currency, but for a foreign purchase it is the merchant's
      currency. This is the layer the matcher compares against a
      receipt's `detected_currency`; a mismatch routes to FX judgment.
    * `account_card_currency` — the card / account's own currency (the
      EUR card, the USD card). Stable across the account's transactions.
    * book / legal-entity currency — NOT stored here; it is fixed per
      legal entity and lives at the entity level (§20). Reporting
      converts into it; matching never uses it.
    """

    transaction_id: str
    legal_entity_id: str
    account_id: str
    transaction_date: date
    posting_date: date | None
    amount: Decimal
    transaction_currency: str       # layer 1 — what this transaction posted in (§20)
    account_card_currency: str      # layer 2 — the card / account currency (§20)
    vendor_from_statement: str
    raw_text: str = ""

    # Foreign-purchase detail from the statement (2026-06-16, Chase PDF
    # ingest). A USD card posts the converted USD in `amount`; the statement
    # also prints the original purchase as a two-line FX detail
    # ("EURO / 27.00 X 1.175185185 (EXCHG RATE)"). Captured so the bank
    # data is preserved in full (Dirk: "all data from the bank statement
    # must stay as it was") and a foreign receipt can later be matched on
    # the original amount/currency rather than only the implied-rate band.
    # None for same-currency (USD) charges.
    original_amount: Decimal | None = None     # purchase amount before conversion
    original_currency: str | None = None       # ISO of the original currency (EUR, BRL, ...)
    fx_rate: Decimal | None = None             # rate the bank applied (original -> card)


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

    Path-A provenance fields (BLUEPRINT 8.1, populated by the Zoho
    Expense CSV adapter; None for the slice-1 receipts CSV and the
    slice-2 OCR folder):

    * `report_number` — the Zoho Expense report this line belongs to
      (ER-NNNNN). Carried into the 8.3 reports cross-reference and the
      8.5 Books journal export.
    * `receipt_url` — a stable URL to the receipt image when the export
      carries one directly. The receipt-URL design fork (8.1): use this
      when present.
    * `receipt_name` — the receipt attachment filename when no URL is
      exported. The other side of the fork: 8.4 receipt-URL hosting
      resolves it to a URL by matching the file in the receipts folder.
    """

    document_id: str
    legal_entity_id: str
    detected_date: date | None
    detected_total: Decimal | None
    detected_currency: str | None   # compared against tx.transaction_currency (layer 1, §20); mismatch → FX judgment
    detected_vendor: str | None
    detected_reference: str | None = None
    report_number: str | None = None
    receipt_url: str | None = None
    receipt_name: str | None = None
    ocr_text: str = ""
    line_items: tuple[LineItem, ...] = ()

    # Zoho Expense report fields (BLUEPRINT 8.1 extension, 2026-06-16). A
    # Zoho Expense report (ER-NNNNN) carries far more per line than the
    # slice-1 receipts CSV; capturing it lets the tool's data and output hold
    # the same information as the report. All optional (None for the slice-1
    # receipts CSV and the slice-2 OCR folder). See ER-00214 for the shapes:
    #
    # * `payment_mode` — the paying card/account, e.g.
    #   "1 - CorpServ 2838/1672 (Chase)". This is the bank/card the expense
    #   was paid through; it is the account Dirk's "legal entity derived from
    #   the account" (2026-06-16) keys on, the card a charge reconciles
    #   against, and the cash/personal signal for the reimbursement case.
    # * `paid_through` — the Zoho "Paid Through" account
    #   ("ZZZ | Cash In Hand | DO NOT USE").
    # * `zoho_category` — the Zoho GL category/account the report assigns,
    #   e.g. "E100010 - Travel Expense". Carried as the posting account; the
    #   tool's own AI category is the verify pass alongside it.
    # * `exchange_rate` / `base_amount` — the report's own FX rate and
    #   book-currency amount (1 BRL = 0.187586 USD -> $581.51), preserved
    #   rather than re-derived.
    # * `reimbursable` — the report "Reimbursable" / "Non Reimbursable" flag.
    # * `expense_location` — the report "Expense Location".
    payment_mode: str | None = None
    paid_through: str | None = None
    zoho_category: str | None = None
    exchange_rate: Decimal | None = None
    base_amount: Decimal | None = None
    reimbursable: bool | None = None
    expense_location: str | None = None


@dataclass(frozen=True)
class Match:
    """A scored candidate pairing of a transaction and a receipt.

    `confidence` is the bucket/judgment confidence that drives assignment
    and back-compat. `score` is a graded 0-100 triage number blending
    amount, date, and fuzzy-vendor agreement (Tier-1 #1); it orders the
    review workbench so the weakest matches surface first and never
    changes which bucket a pair lands in. 0 means "not scored" (e.g. a
    reviewer-confirmed match built outside the matcher).
    """

    transaction_id: str
    document_id: str
    match_type: MatchType
    confidence: float
    reason: str
    requires_review: bool = False
    score: int = 0
    # The three sub-scores blended into `score` (each 0.0-1.0), kept so the
    # workbench can show WHY a candidate scored as it did (PR D match
    # transparency). 0.0 when not scored (a reviewer-built match).
    amount_score: float = 0.0
    date_score: float = 0.0
    vendor_score: float = 0.0


@dataclass(frozen=True)
class MatchOutcome:
    """The result of running the matcher across a month of data.

    Fields are intentionally explicit and side-by-side so that the
    reconciliation guarantee (v2 spec §25.5) can be verified at a
    glance: every transaction either has a match, is in
    `unmatched_transactions`, or is in `judgment_required`. Nothing
    is silently dropped.

    Frozen (E6): the dataclass is immutable so a consumer cannot
    accidentally rebind a bucket (`outcome.matches = [...]`) and break
    the invariant. The lists themselves are still mutable — populate
    and revise them in place (`.append()`, `.extend()`, slice-assign
    `outcome.judgment_required[:] = judged`), never by reattaching a
    new list to the attribute.
    """

    matches: list[Match] = field(default_factory=list)
    unmatched_transactions: list[str] = field(default_factory=list)
    unmatched_receipts: list[str] = field(default_factory=list)
    judgment_required: list[Match] = field(default_factory=list)
    ambiguous: list[Match] = field(default_factory=list)
