"""Domain types for the matching engine.

Faithful to v2 spec §15 and §23: deterministic-first matching with
LLM-only-for-judgment, three currency layers (transaction /
account-card / book), tenant-scoped and legal-entity-scoped entities.
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
    """An extracted receipt (v2 spec §23.9)."""

    document_id: str
    legal_entity_id: str
    detected_date: date | None
    detected_total: Decimal | None
    detected_currency: str | None
    detected_vendor: str | None
    detected_reference: str | None = None
    ocr_text: str = ""


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
