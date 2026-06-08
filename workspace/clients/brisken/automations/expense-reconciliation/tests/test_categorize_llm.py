"""Tests for the LLM-path categorizer (slice 2)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from expense_recon.categorize import categorize_receipts
from expense_recon.llm.client import (
    ClassificationResult,
    MockLLMClient,
)
from expense_recon.llm.cost import CostTracker, TokenUsage
from expense_recon.matching.types import (
    EXPENSE_CATEGORIES,
    ClassificationSource,
    LineItem,
    Receipt,
)


def _receipt(items, **overrides) -> Receipt:
    base = dict(
        document_id="r1",
        legal_entity_id="le1",
        detected_date=date(2026, 4, 7),
        detected_total=Decimal("200"),
        detected_currency="USD",
        detected_vendor="Amazon",
        detected_reference=None,
        line_items=tuple(items),
    )
    base.update(overrides)
    return Receipt(**base)


# ── LLM-path Tier 1 (LINE) ──────────────────────────────────────────


def test_llm_classifier_tier_1_categories_each_line_item():
    """LD-2 contract: each line item gets its own category from the
    LLM, not from vendor name. Mock returns the canonical 'right'
    answers for the Amazon-chair-coffee-cable example."""
    items = [
        LineItem(description="Herman Miller chair", line_total=Decimal("150")),
        LineItem(description="Coffee beans 2kg", line_total=Decimal("30")),
        LineItem(description="HDMI cable", line_total=Decimal("20")),
    ]
    receipt = _receipt(items)

    mock = MockLLMClient(responses=[
        [
            ClassificationResult(
                category="Equipment & Hardware", zoho_account=None,
                confidence=0.95,
                reasoning="An office chair is durable equipment.",
            ),
            ClassificationResult(
                category="Office Supplies & Consumables", zoho_account=None,
                confidence=0.85,
                reasoning="Coffee beans 2kg is office pantry stock, not a meal.",
            ),
            ClassificationResult(
                category="Equipment & Hardware", zoho_account=None,
                confidence=0.90,
                reasoning="HDMI cable is computer peripheral hardware.",
            ),
        ]
    ])

    [out] = categorize_receipts([receipt], client=mock)
    sources = [li.categorization.source for li in out.line_items]
    categories = [li.categorization.category for li in out.line_items]

    assert sources == [ClassificationSource.LINE] * 3
    # Critical: coffee beans → Office Supplies, NOT Meals & Entertainment
    # (the keyword stub gets this wrong; the LLM gets it right).
    assert categories == [
        "Equipment & Hardware",
        "Office Supplies & Consumables",
        "Equipment & Hardware",
    ]


def test_llm_classifier_one_batched_call_per_receipt():
    """Cost discipline: each receipt = exactly one batched call,
    regardless of line-item count. Non-vague descriptions so the
    LD-2 line-item path (not vendor fallback) fires.
    """
    items = [
        LineItem(description="Herman Miller chair", line_total=Decimal("150")),
        LineItem(description="Coffee beans 2kg", line_total=Decimal("30")),
        LineItem(description="HDMI cable", line_total=Decimal("20")),
        LineItem(description="USB-C dock", line_total=Decimal("80")),
        LineItem(description="Mechanical keyboard", line_total=Decimal("120")),
    ]
    receipt = _receipt(items)
    mock = MockLLMClient()  # uses default heuristic

    categorize_receipts([receipt], client=mock)

    assert len(mock.calls) == 1
    assert mock.calls[0][0] == "classify_line_items"


def test_llm_classifier_review_threshold_routes_low_confidence_to_tier_3():
    """LD-2: confidence < REVIEW_THRESHOLD (0.6) → Tier 3 REVIEW even
    when the LLM returned a category. Defends against over-eager
    classification on ambiguous items."""
    items = [
        LineItem(description="Item 1", line_total=Decimal("100")),
    ]
    receipt = _receipt(items)
    mock = MockLLMClient(responses=[
        [
            ClassificationResult(
                category="Equipment & Hardware", zoho_account=None,
                confidence=0.4,  # below threshold
                reasoning="Genuinely not sure what 'Item 1' is",
            ),
        ]
    ])
    [out] = categorize_receipts([receipt], client=mock)
    cat = out.line_items[0].categorization
    assert cat.source == ClassificationSource.REVIEW
    assert cat.category is None  # blanked since we're not confident


def test_llm_classifier_invalid_category_routes_to_review():
    """LD-2: if the LLM hallucinates a category outside the 8-list,
    treat as REVIEW (don't propagate the bad value)."""
    items = [LineItem(description="Weird thing", line_total=Decimal("50"))]
    receipt = _receipt(items)
    mock = MockLLMClient(responses=[
        [
            ClassificationResult(
                category="Hallucinated Category", zoho_account=None,
                confidence=0.95,
                reasoning="LLM made up a non-existent category",
            ),
        ]
    ])
    [out] = categorize_receipts([receipt], client=mock)
    cat = out.line_items[0].categorization
    assert cat.source == ClassificationSource.REVIEW
    assert cat.category is None


# ── LLM-path Tier 2 (VENDOR) ────────────────────────────────────────


def test_llm_vendor_fallback_when_no_line_items():
    """LD-2: receipt with no line items → Tier 2 vendor LLM call."""
    receipt = _receipt(items=[], detected_vendor="Uber")
    mock = MockLLMClient(responses=[
        ClassificationResult(
            category="Travel & Transport", zoho_account=None,
            confidence=0.85,
            reasoning="Uber is rideshare → travel category",
        ),
    ])
    [out] = categorize_receipts([receipt], client=mock)
    assert len(out.line_items) == 1
    cat = out.line_items[0].categorization
    assert cat.source == ClassificationSource.VENDOR
    assert cat.category == "Travel & Transport"

    # The call shape was vendor, not line_items.
    assert mock.calls[0][0] == "classify_by_vendor"


def test_llm_vendor_fallback_when_all_items_vague():
    """LD-2: every line item description is too vague → vendor fallback."""
    items = [
        LineItem(description="Item 1", line_total=Decimal("50")),
        LineItem(description="Misc.", line_total=Decimal("30")),
    ]
    receipt = _receipt(items, detected_vendor="Starbucks")
    mock = MockLLMClient(responses=[
        ClassificationResult(
            category="Meals & Entertainment", zoho_account=None,
            confidence=0.8, reasoning="Starbucks → meals",
        ),
    ])
    [out] = categorize_receipts([receipt], client=mock)
    assert mock.calls[0][0] == "classify_by_vendor"
    assert out.line_items[0].categorization.source == ClassificationSource.VENDOR


def test_no_vendor_no_line_items_lands_in_review():
    """LD-2 corner case: nothing to work with → REVIEW, no LLM call needed."""
    receipt = _receipt(items=[], detected_vendor=None)
    mock = MockLLMClient()
    [out] = categorize_receipts([receipt], client=mock)
    assert out.line_items[0].categorization.source == ClassificationSource.REVIEW
    assert mock.calls == []  # didn't bother calling the LLM


# ── Cost tracking ───────────────────────────────────────────────────


def test_cost_tracker_accumulates_one_per_call():
    """MockLLMClient records one usage per call; tracker sums them."""
    items = [LineItem(description="Coffee", line_total=Decimal("5"))]
    receipts = [_receipt(items), _receipt(items, document_id="r2")]
    tracker = CostTracker()
    mock = MockLLMClient(cost_tracker=tracker)
    categorize_receipts(receipts, client=mock)
    assert tracker.call_count == 2
    assert tracker.total_cost_usd == Decimal("0.002")  # 2 × $0.001 mock cost


def test_token_usage_cost_calculation_matches_published_pricing():
    """gpt-4o-mini: $0.15/M input + $0.60/M output. 1M input + 1M output
    should be $0.75."""
    usage = TokenUsage.from_counts("gpt-4o-mini", 1_000_000, 1_000_000)
    assert usage.cost_usd == Decimal("0.75")


def test_token_usage_unknown_model_zero_cost():
    """Unlisted model → zero cost (defensive; tracker still records the call)."""
    usage = TokenUsage.from_counts("unknown-model", 1000, 500)
    assert usage.cost_usd == Decimal("0")


# ── Zoho account mapping (slice 4.2) ────────────────────────────────


def test_chart_of_accounts_forwarded_and_zoho_account_flows_through():
    """4.2: in-scope account labels reach the client, and the picked
    zoho_account propagates onto the Categorization."""
    items = [LineItem(description="Flight to Berlin", line_total=Decimal("420"))]
    receipt = _receipt(items)
    labels = ["E100010-21 Travel Expense:Flights", "E600010-05 Advertising"]
    mock = MockLLMClient(responses=[
        [
            ClassificationResult(
                category="Travel & Transport",
                zoho_account="E100010-21 Travel Expense:Flights",
                confidence=0.95, reasoning="flight → travel",
            ),
        ]
    ])

    [out] = categorize_receipts([receipt], client=mock, chart_of_accounts=labels)

    assert mock.last_chart_of_accounts == labels
    assert out.line_items[0].categorization.zoho_account == "E100010-21 Travel Expense:Flights"


def test_zoho_account_forwarded_on_vendor_fallback():
    """4.2: the account list also reaches the Tier-2 vendor call."""
    receipt = _receipt(items=[], detected_vendor="Uber")
    labels = ["E100010-41 Travel Expense:Taxi/Uber"]
    mock = MockLLMClient(responses=[
        ClassificationResult(
            category="Travel & Transport",
            zoho_account="E100010-41 Travel Expense:Taxi/Uber",
            confidence=0.85, reasoning="Uber → taxi",
        ),
    ])

    [out] = categorize_receipts([receipt], client=mock, chart_of_accounts=labels)

    assert mock.calls[0][0] == "classify_by_vendor"
    assert mock.last_chart_of_accounts == labels
    assert out.line_items[0].categorization.zoho_account == "E100010-41 Travel Expense:Taxi/Uber"


# ── Keyword fallback preserved when no LLM ──────────────────────────


def test_no_llm_client_uses_keyword_stub_fallback():
    """Slice-1 behavior preserved: categorize_receipts() with no
    client uses the keyword stub. Coffee → Meals (the known stub
    quirk that the LLM path fixes)."""
    items = [LineItem(description="Coffee beans 2kg", line_total=Decimal("30"))]
    receipt = _receipt(items)
    [out] = categorize_receipts([receipt])  # no client kwarg
    cat = out.line_items[0].categorization
    # The keyword stub matches 'coffee' → Meals (the bug we're
    # fixing with the LLM path — verified inverted in the LLM test
    # above).
    assert cat.category == "Meals & Entertainment"
    assert cat.source == ClassificationSource.LINE
    assert "STUB" in cat.reasoning


# ── CLI integration with mock client ────────────────────────────────


def test_cli_loads_llm_config_and_uses_openai_client(tmp_path, monkeypatch):
    """End-to-end: config has `llm:` block → CLI instantiates
    OpenAIClient. We don't make a real network call here; we patch
    the OpenAIClient constructor to fail loudly if invoked with the
    wrong arguments.
    """
    import json
    from expense_recon import cli as cli_module

    # Use the fixture statement+receipts already proved in test_cli_integration.
    statement_csv = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE SHOP NYC,5.75,M\n"
    )
    receipts_csv = (
        'document_id,detected_date,detected_total,detected_currency,'
        'detected_vendor,detected_reference,line_items\n'
        'rcpt-001,2026-04-01,5.75,USD,Coffee Shop NYC,,'
        '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")

    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        "output": {"path": "report.xlsx"},
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "api_key_env": "FAKE_KEY"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    # Patch OpenAIClient at the CLI's import site so _build_llm_client
    # gets a mock instead of trying to reach the network.
    mock_client = MockLLMClient(responses=[
        [
            ClassificationResult(
                category="Meals & Entertainment", zoho_account=None,
                confidence=0.95, reasoning="latte is a coffee beverage",
            ),
        ]
    ])
    instantiate_calls = []

    def fake_openai_client(*, model, api_key, cost_tracker):
        instantiate_calls.append({"model": model, "api_key": api_key})
        mock_client.cost_tracker = cost_tracker
        return mock_client

    monkeypatch.setattr(cli_module, "OpenAIClient", fake_openai_client)
    monkeypatch.setenv("FAKE_KEY", "sk-fake-for-test")

    result = cli_module.run(config_path)
    assert result is not None
    assert result.exists()

    # OpenAIClient was instantiated with the configured model + api_key.
    assert len(instantiate_calls) == 1
    assert instantiate_calls[0]["model"] == "gpt-4o-mini"
    assert instantiate_calls[0]["api_key"] == "sk-fake-for-test"


def test_cli_llm_block_without_env_var_raises_configerror(tmp_path):
    """If `llm:` is in config but the env var is not set, fail clean."""
    import json
    from expense_recon.cli import ConfigError, run

    (tmp_path / "statement.csv").write_text(
        "Date,Description,Amount,Card Member\n04/01/2026,X,1.0,M\n",
        encoding="utf-8",
    )
    (tmp_path / "receipts.csv").write_text(
        "document_id,detected_date,detected_total,detected_vendor\n", encoding="utf-8",
    )
    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv"},
        "llm": {"provider": "openai", "api_key_env": "DEFINITELY_UNSET_VAR_XYZ_123"},
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ConfigError, match=r"DEFINITELY_UNSET_VAR_XYZ_123"):
        run(config_path)


def test_cli_no_llm_block_uses_keyword_fallback(tmp_path):
    """Backward compat: omitting `llm:` is the same as slice 1.5."""
    import json
    from expense_recon.cli import run

    statement_csv = (
        "Date,Description,Amount,Card Member\n"
        "04/01/2026,COFFEE,5.75,M\n"
    )
    receipts_csv = (
        'document_id,detected_date,detected_total,detected_currency,'
        'detected_vendor,detected_reference,line_items\n'
        'rcpt-001,2026-04-01,5.75,USD,Coffee,,'
        '"[{""description"":""Latte"",""line_total"":""5.75""}]"\n'
    )
    (tmp_path / "statement.csv").write_text(statement_csv, encoding="utf-8")
    (tmp_path / "receipts.csv").write_text(receipts_csv, encoding="utf-8")
    config = {
        "statement": {
            "path": "statement.csv",
            "account_id": "amex-9001",
            "legal_entity_id": "brisken-llc",
            "account_card_currency": "USD",
            "column_map": {"transaction_date": "Date", "amount": "Amount", "vendor": "Description"},
        },
        "receipts": {"path": "receipts.csv", "default_currency": "USD"},
        # No `llm:` block.
    }
    config_path = tmp_path / "run.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = run(config_path)
    assert result is not None  # ran without an LLM
    assert result.exists()
