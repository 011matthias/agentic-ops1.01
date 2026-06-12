"""Snapshot (de)serialization for the web app.

The matching pipeline returns frozen dataclasses holding `Decimal`,
`date`, and string-enum fields. To render a run's review workbench
without re-running the LLM on every page load (cost, latency, and
non-determinism), the web app snapshots the reconcile result to a JSON
blob in SQLite and rebuilds the objects on read.

These converters are explicit per type rather than a generic
`dataclasses.asdict`, so the round-trip is exact: `Decimal` survives as
`Decimal` (string-encoded, never a lossy float), `date` survives as
`date`, and enums survive as their typed members. An exact round-trip is
load-bearing, the exports are regenerated from the rebuilt objects and a
float-ified amount would corrupt a journal entry.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..matching.types import (
    Categorization,
    ClassificationSource,
    LineItem,
    Match,
    MatchOutcome,
    MatchType,
    Receipt,
    Transaction,
)

SNAPSHOT_VERSION = 1


def _dec(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _as_dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _as_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def categorization_to_dict(c: Categorization | None) -> dict | None:
    if c is None:
        return None
    return {
        "category": c.category,
        "zoho_account": c.zoho_account,
        "confidence": c.confidence,
        "source": c.source.value,
        "reasoning": c.reasoning,
    }


def categorization_from_dict(d: dict | None) -> Categorization | None:
    if d is None:
        return None
    return Categorization(
        category=d["category"],
        zoho_account=d["zoho_account"],
        confidence=d["confidence"],
        source=ClassificationSource(d["source"]),
        reasoning=d.get("reasoning", ""),
    )


def lineitem_to_dict(li: LineItem) -> dict:
    return {
        "description": li.description,
        "line_total": _dec(li.line_total),
        "quantity": _dec(li.quantity),
        "unit_price": _dec(li.unit_price),
        "categorization": categorization_to_dict(li.categorization),
    }


def lineitem_from_dict(d: dict) -> LineItem:
    return LineItem(
        description=d["description"],
        line_total=_as_dec(d["line_total"]),
        quantity=_as_dec(d["quantity"]),
        unit_price=_as_dec(d["unit_price"]),
        categorization=categorization_from_dict(d["categorization"]),
    )


def transaction_to_dict(t: Transaction) -> dict:
    return {
        "transaction_id": t.transaction_id,
        "legal_entity_id": t.legal_entity_id,
        "account_id": t.account_id,
        "transaction_date": _date(t.transaction_date),
        "posting_date": _date(t.posting_date),
        "amount": _dec(t.amount),
        "transaction_currency": t.transaction_currency,
        "account_card_currency": t.account_card_currency,
        "vendor_from_statement": t.vendor_from_statement,
        "raw_text": t.raw_text,
    }


def transaction_from_dict(d: dict) -> Transaction:
    return Transaction(
        transaction_id=d["transaction_id"],
        legal_entity_id=d["legal_entity_id"],
        account_id=d["account_id"],
        transaction_date=_as_date(d["transaction_date"]),
        posting_date=_as_date(d["posting_date"]),
        amount=_as_dec(d["amount"]),
        transaction_currency=d["transaction_currency"],
        account_card_currency=d["account_card_currency"],
        vendor_from_statement=d["vendor_from_statement"],
        raw_text=d.get("raw_text", ""),
    )


def receipt_to_dict(r: Receipt) -> dict:
    return {
        "document_id": r.document_id,
        "legal_entity_id": r.legal_entity_id,
        "detected_date": _date(r.detected_date),
        "detected_total": _dec(r.detected_total),
        "detected_currency": r.detected_currency,
        "detected_vendor": r.detected_vendor,
        "detected_reference": r.detected_reference,
        "report_number": r.report_number,
        "receipt_url": r.receipt_url,
        "receipt_name": r.receipt_name,
        "ocr_text": r.ocr_text,
        "line_items": [lineitem_to_dict(li) for li in r.line_items],
    }


def receipt_from_dict(d: dict) -> Receipt:
    return Receipt(
        document_id=d["document_id"],
        legal_entity_id=d["legal_entity_id"],
        detected_date=_as_date(d["detected_date"]),
        detected_total=_as_dec(d["detected_total"]),
        detected_currency=d["detected_currency"],
        detected_vendor=d["detected_vendor"],
        detected_reference=d["detected_reference"],
        report_number=d.get("report_number"),
        receipt_url=d.get("receipt_url"),
        receipt_name=d.get("receipt_name"),
        ocr_text=d.get("ocr_text", ""),
        line_items=tuple(lineitem_from_dict(x) for x in d.get("line_items", [])),
    )


def match_to_dict(m: Match) -> dict:
    return {
        "transaction_id": m.transaction_id,
        "document_id": m.document_id,
        "match_type": m.match_type.value,
        "confidence": m.confidence,
        "reason": m.reason,
        "requires_review": m.requires_review,
    }


def match_from_dict(d: dict) -> Match:
    return Match(
        transaction_id=d["transaction_id"],
        document_id=d["document_id"],
        match_type=MatchType(d["match_type"]),
        confidence=d["confidence"],
        reason=d["reason"],
        requires_review=d.get("requires_review", False),
    )


def outcome_to_dict(o: MatchOutcome) -> dict:
    return {
        "matches": [match_to_dict(m) for m in o.matches],
        "unmatched_transactions": list(o.unmatched_transactions),
        "unmatched_receipts": list(o.unmatched_receipts),
        "judgment_required": [match_to_dict(m) for m in o.judgment_required],
        "ambiguous": [match_to_dict(m) for m in o.ambiguous],
    }


def outcome_from_dict(d: dict) -> MatchOutcome:
    return MatchOutcome(
        matches=[match_from_dict(x) for x in d.get("matches", [])],
        unmatched_transactions=list(d.get("unmatched_transactions", [])),
        unmatched_receipts=list(d.get("unmatched_receipts", [])),
        judgment_required=[match_from_dict(x) for x in d.get("judgment_required", [])],
        ambiguous=[match_from_dict(x) for x in d.get("ambiguous", [])],
    )


def snapshot_to_dict(
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    parse_errors: list[tuple[str, int, str]],
) -> dict:
    """Serialize a full reconcile result to a JSON-able dict."""
    return {
        "version": SNAPSHOT_VERSION,
        "transactions": [transaction_to_dict(t) for t in transactions],
        "receipts": [receipt_to_dict(r) for r in receipts],
        "outcome": outcome_to_dict(outcome),
        "parse_errors": [list(e) for e in parse_errors],
    }


def snapshot_from_dict(
    d: dict,
) -> tuple[list[Transaction], list[Receipt], MatchOutcome, list[tuple[str, int, str]]]:
    """Rebuild (transactions, receipts, outcome, parse_errors) from a snapshot."""
    transactions = [transaction_from_dict(x) for x in d.get("transactions", [])]
    receipts = [receipt_from_dict(x) for x in d.get("receipts", [])]
    outcome = outcome_from_dict(d.get("outcome", {}))
    parse_errors = [tuple(e) for e in d.get("parse_errors", [])]
    return transactions, receipts, outcome, parse_errors
