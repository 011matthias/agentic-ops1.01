"""Phase 2 (receipt-first): generate_expenses() — statement-free expense
generation. CI-safe via MockLLMClient (no API key)."""
from __future__ import annotations

import pytest

from expense_recon.cli import generate_expenses
from expense_recon.llm.client import (
    ExtractedLineItem,
    ExtractedReceipt,
    MockLLMClient,
)
from expense_recon.matching.types import EXPENSE_CATEGORIES


def _extraction(vendor="Uber", total="24.50", currency="USD", line_items=()):
    return ExtractedReceipt(
        date="2026-06-02", total=total, currency=currency, vendor=vendor,
        reference=None, line_items=line_items, confidence=0.9, notes="",
    )


def _folder(tmp_path, names):
    folder = tmp_path / "receipts"
    folder.mkdir()
    for n in names:
        (folder / n).write_bytes(b"x")
    return folder


def test_generate_expenses_needs_no_statement(tmp_path):
    """The whole point: a batch of receipts, no statement, one expense each."""
    _folder(tmp_path, ["a.jpg", "b.jpg"])
    client = MockLLMClient(extraction_responses=[
        _extraction(vendor="Uber"), _extraction(vendor="Amazon"),
    ])
    cfg = {  # NOTE: no "statement" block at all
        "expense": {"legal_entity_id": "brisken-llc"},
        "receipts": {"path": "receipts", "default_currency": "USD"},
    }

    result = generate_expenses(cfg, tmp_path, llm_client=client)

    # receipt-spine: no transactions, every receipt is an expense
    assert result.transactions == []
    assert len(result.receipts) == 2
    assert sorted(result.outcome.unmatched_receipts) == ["a.jpg", "b.jpg"]
    assert result.outcome.matches == []
    assert result.charge_categorizations == {}
    # no statement => no statement parse issues can appear
    assert all(f in ("a.jpg", "b.jpg") for f, *_ in result.parse_errors)


def test_generate_expenses_accepts_missing_legal_entity(tmp_path):
    """Cards R3 (2026-08-21): the legal entity is optional at batch level —
    the old guard is gone. Receipts run through with entity "" (per-receipt
    card resolution / the needs_entity review state take over downstream);
    the batch is generated, never refused."""
    _folder(tmp_path, ["a.jpg"])
    client = MockLLMClient(extraction_responses=[_extraction()])
    cfg = {"receipts": {"path": "receipts", "default_currency": "USD"}}  # no expense

    result = generate_expenses(cfg, tmp_path, llm_client=client)
    assert len(result.receipts) == 1
    assert result.receipts[0].legal_entity_id == ""


def test_generate_expenses_categorizes_into_predetermined_set(tmp_path):
    """The categorize pass runs and assigns one of the fixed categories."""
    _folder(tmp_path, ["uber.jpg"])
    client = MockLLMClient(extraction_responses=[_extraction(
        vendor="Uber",
        line_items=(ExtractedLineItem("Uber trip downtown", "24.50"),),
    )])
    cfg = {
        "expense": {"legal_entity_id": "brisken-llc"},
        "receipts": {"path": "receipts", "default_currency": "USD"},
    }

    result = generate_expenses(cfg, tmp_path, llm_client=client)

    r = result.receipts[0]
    cats = [
        li.categorization.category
        for li in r.line_items
        if li.categorization and li.categorization.category
    ]
    assert cats, "expected the categorize pass to assign a category"
    # categories are pre-determined: every assigned category is in the fixed set
    assert all(c in EXPENSE_CATEGORIES for c in cats)
