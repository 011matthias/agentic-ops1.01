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
    Categorization,
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


# ── override_er_category: who owns the posting account (2026-07-21) ──

# The ER expenses (ADOBE/ANTHROPIC) arrive with EMPTY line_items → the
# vendor-aware fallback path, and carry the report's own (wrong) account.
_ER_ACCT = "E100010-31 - Travel Expense | Food"
_LLM_ACCT = "E600020-01 - Software & Subscriptions"


def _adobe_receipt():
    return _receipt(items=[], detected_vendor="Adobe", zoho_category=_ER_ACCT)


def _software_vendor_mock():
    return MockLLMClient(responses=[
        ClassificationResult(
            category="Software & Subscriptions", zoho_account=_LLM_ACCT,
            confidence=0.95, reasoning="Adobe is a software subscription.",
        ),
    ])


def test_er_category_clobbers_account_by_default():
    """Default (2026-06-16): the report's account is authoritative and
    overwrites the LLM's correct pick. Pins the pre-override behaviour."""
    [out] = categorize_receipts(
        [_adobe_receipt()], client=_software_vendor_mock(),
        chart_of_accounts=[_LLM_ACCT],
    )
    cat = out.line_items[0].categorization
    assert cat.category == "Software & Subscriptions"  # LLM category always survived
    assert cat.zoho_account == _ER_ACCT  # but the report's account clobbered the pick


def test_override_lets_llm_account_win():
    """override_er_category=True: the LLM's own account is authoritative;
    ADOBE no longer posts to 'Travel Expense | Food'."""
    [out] = categorize_receipts(
        [_adobe_receipt()], client=_software_vendor_mock(),
        chart_of_accounts=[_LLM_ACCT], override_er_category=True,
    )
    cat = out.line_items[0].categorization
    assert cat.category == "Software & Subscriptions"
    assert cat.zoho_account == _LLM_ACCT


def test_override_keeps_learned_account_over_report():
    """override_er_category=True keeps a LEARNED (memory) account; the default
    still clobbers it with the report's."""
    from expense_recon.learning import (
        MerchantCategory,
        MerchantCategoryLookup,
        normalize_vendor,
    )

    learned = MerchantCategoryLookup([
        MerchantCategory(
            "le1", normalize_vendor("Adobe"), "Software & Subscriptions",
            _LLM_ACCT, 1, "2026-05-01T00:00:00", "r1",
        )
    ])
    # No client → the vendor-fallback path takes the LEARNED categorization.
    [dflt] = categorize_receipts([_adobe_receipt()], learned=learned)
    assert dflt.line_items[0].categorization.zoho_account == _ER_ACCT  # clobbered

    [ovr] = categorize_receipts(
        [_adobe_receipt()], learned=learned, override_er_category=True
    )
    assert ovr.line_items[0].categorization.zoho_account == _LLM_ACCT  # memory wins


def test_override_falls_back_to_report_when_llm_has_no_account():
    """override on, but the LLM returned no account (no chart of accounts
    wired) → fall back to the report's account, never post nothing."""
    [out] = categorize_receipts(
        [_adobe_receipt()],
        client=MockLLMClient(responses=[
            ClassificationResult(
                category="Software & Subscriptions", zoho_account=None,
                confidence=0.95, reasoning="no COA to pick from",
            ),
        ]),
        override_er_category=True,  # no chart_of_accounts → LLM returns None
    )
    assert out.line_items[0].categorization.zoho_account == _ER_ACCT


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

    def fake_openai_client(*, model, api_key, cost_tracker, vision_model=None):
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


# ── WS2 top-level adjudication gate (2026-07-21) ────────────────────
#
# Synthetic two-root chart: Travel Expense (E100 + leaves Food/Flights) and
# IT: Computer and Internet Expenses (E500 + leaf Cloud Subscriptions). The
# static EXPENSE_CATEGORY_ROOT_GROUP map targets these real root names.

from expense_recon.categorize import (  # noqa: E402
    DECISION_AI_OVERRIDE_HEAVY,
    DECISION_KEPT_ER,
    DECISION_REVIEW_UNRESOLVED,
    adjudicate_receipts,
)
from expense_recon.ingest.chart_of_accounts import ChartOfAccounts  # noqa: E402

_ADJ_RECORDS = [
    {"account_id": "1", "account_name": "Travel Expense", "account_code": "E100",
     "account_type": "expense", "parent_account_name": None, "is_active": True},
    {"account_id": "2", "account_name": "Travel: Food", "account_code": "E100-31",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "3", "account_name": "Travel: Flights", "account_code": "E100-21",
     "account_type": "expense", "parent_account_name": "Travel Expense", "is_active": True},
    {"account_id": "4", "account_name": "IT: Computer and Internet Expenses",
     "account_code": "E500", "account_type": "expense", "parent_account_name": None,
     "is_active": True},
    {"account_id": "5", "account_name": "Cloud Subscriptions", "account_code": "E500-10",
     "account_type": "expense", "parent_account_name": "IT: Computer and Internet Expenses",
     "is_active": True},
]


def _adj_chart() -> ChartOfAccounts:
    return ChartOfAccounts.from_api(_ADJ_RECORDS)


def _adj_receipt(zoho_category, *, cat_account, cat_category="Travel & Transport") -> Receipt:
    li = LineItem(
        description="x", line_total=Decimal("10"),
        categorization=Categorization(
            category=cat_category, zoho_account=cat_account, confidence=0.9,
            source=ClassificationSource.LINE, reasoning="t",
        ),
    )
    return _receipt([li], zoho_category=zoho_category, detected_vendor="V")


def _verdict(receipt):
    cat = adjudicate_receipts([receipt], _adj_chart())[0].line_items[0].categorization
    return cat.decision, cat.zoho_account


def test_adjudicate_same_root_group_keeps_report():
    # LLM picked a distinct Travel leaf; report is another Travel leaf -> same
    # root group -> report category kept.
    decision, account = _verdict(
        _adj_receipt("E100-31 - Travel: Food", cat_account="E100-21 Travel: Flights")
    )
    assert decision == DECISION_KEPT_ER
    assert account == "E100-31 - Travel: Food"


def test_adjudicate_heavy_mismatch_inserts_llm_account():
    # LLM picked an IT account; report is Travel -> different root -> heavy
    # override; the LLM's own account posts.
    decision, account = _verdict(
        _adj_receipt(
            "E100-31 - Travel: Food",
            cat_account="E500-10 Cloud Subscriptions",
            cat_category="Software & Subscriptions",
        )
    )
    assert decision == DECISION_AI_OVERRIDE_HEAVY
    assert account == "E500-10 Cloud Subscriptions"


def test_adjudicate_static_fallback_heavy_when_no_llm_account():
    # LLM has the Software category but NO GL leaf. The static map routes it to
    # the IT root; report is Travel -> heavy override, no leaf (reviewer assigns).
    decision, account = _verdict(
        _adj_receipt(
            "E100-31 - Travel: Food", cat_account=None,
            cat_category="Software & Subscriptions",
        )
    )
    assert decision == DECISION_AI_OVERRIDE_HEAVY
    assert account is None


def test_adjudicate_static_fallback_same_root_keeps_report():
    decision, account = _verdict(
        _adj_receipt(
            "E100-31 - Travel: Food", cat_account=None,
            cat_category="Travel & Transport",
        )
    )
    assert decision == DECISION_KEPT_ER
    assert account == "E100-31 - Travel: Food"


def test_adjudicate_report_fallback_pollution_still_detects_heavy():
    # PR1's _carry_zoho_account fell the no-leaf line back to the report's own
    # account. Adjudication must ignore that fallback (== report) and still use
    # the category's static root to catch a heavy Software-vs-Travel mismatch.
    decision, account = _verdict(
        _adj_receipt(
            "E100-31 - Travel: Food",
            cat_account="E100-31 - Travel: Food",   # report fallback, not a real pick
            cat_category="Software & Subscriptions",
        )
    )
    assert decision == DECISION_AI_OVERRIDE_HEAVY
    assert account is None


def test_adjudicate_unresolvable_report_keeps_conservatively():
    decision, account = _verdict(
        _adj_receipt(
            "Z999 - Not In Chart",
            cat_account="E500-10 Cloud Subscriptions",
            cat_category="Software & Subscriptions",
        )
    )
    assert decision == DECISION_REVIEW_UNRESOLVED
    assert account == "Z999 - Not In Chart"


def test_adjudicate_noop_without_report_category():
    r = _adj_receipt(None, cat_account="E500-10 Cloud Subscriptions")
    cat = adjudicate_receipts([r], _adj_chart())[0].line_items[0].categorization
    assert cat.decision is None
    assert cat.zoho_account == "E500-10 Cloud Subscriptions"  # untouched


def test_adjudicate_scope_filters_static_fallback():
    # The static map target (IT root) is out of the run's scope_groups -> the
    # fallback comparison is treated as unresolvable -> report kept.
    r = _adj_receipt(
        "E100-31 - Travel: Food", cat_account=None,
        cat_category="Software & Subscriptions",
    )
    cat = adjudicate_receipts(
        [r], _adj_chart(), scope_groups=["Travel Expense"]
    )[0].line_items[0].categorization
    assert cat.decision == DECISION_REVIEW_UNRESOLVED
    assert cat.zoho_account == "E100-31 - Travel: Food"


# ── "null"-string sanitization at the payload parse (2026-08-13) ─────
#
# The classification json-schema allows JSON null, but gpt-4o-mini
# intermittently returns the STRING "null" instead. That string is
# truthy, so it slipped past every no-category guard and reached the
# Zoho Expenses export as a literal "null" Expense Account (caught live
# 2026-08-13 on the PagBank receipt, sets NEW/NEW2). The parse layer now
# collapses sentinel spellings of "no value" to real None.


def test_opt_label_collapses_sentinel_strings():
    from expense_recon.llm.client import _opt_label

    for raw in ("null", "NULL", "None", "n/a", "NA", "nil", "-", "(none)", "", "  "):
        assert _opt_label(raw) is None, raw
    assert _opt_label(None) is None
    assert _opt_label("Meals & Entertainment") == "Meals & Entertainment"
    # A real label that merely CONTAINS a sentinel word survives.
    assert _opt_label("Null Island Consulting") == "Null Island Consulting"


def test_openai_parse_turns_null_string_category_into_review():
    """End-to-end through the real OpenAIClient payload parse: a
    payload with the string "null" must come back as category=None
    (-> the (uncategorized - assign) path), never the literal string."""
    import json as _json
    from types import SimpleNamespace

    pytest.importorskip("openai")
    from expense_recon.llm.client import OpenAIClient

    client = OpenAIClient(api_key="sk-test-not-real")

    def _fake_create(**kwargs):
        body = _json.dumps({
            "results": [{
                "index": 1, "category": "null", "zoho_account": "null",
                "confidence": 0.9, "reasoning": "model said null as a string",
            }]
        })
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=body))],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
        )

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
    )

    from expense_recon.llm.client import LineItemInput

    [result] = client.classify_line_items(
        [LineItemInput(description="PagBank charge", line_total=Decimal("68"))],
        categories=list(EXPENSE_CATEGORIES),
    )
    assert result.category is None
    assert result.zoho_account is None
