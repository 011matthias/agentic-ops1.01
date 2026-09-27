"""Every model the app reads with has a price (item 227, 2026-09-27).

`llm/cost.py` carried no price for gpt-5-mini, the vision model every
photographed receipt and rendered mail body is read with, so the cost tracker
recorded those calls at USD 0. Four A/B passes over 251 stored documents cost
USD 2.32 at list price while the tracker said USD 0.21. The price is now in the
table with its cached-input rate, the client passes the cached part of the
prompt, and a model named anywhere in the source's LLM configuration without a
price fails here instead of costing nothing.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from expense_recon.llm.client import OpenAIClient
from expense_recon.llm.cost import CostTracker, TokenUsage, is_priced

SRC = Path(__file__).resolve().parents[1] / "src" / "expense_recon"

# The shapes a model name takes in the configuration: a config dict value, a
# `.get(...)` default, an environment default, a constructor default.
_MODEL_LITERALS = re.compile(
    r'"(?:vision_)?model"\s*:\s*"(gpt-[^"]+)"'
    r'|\.get\(\s*"(?:vision_)?model"\s*,\s*"(gpt-[^"]+)"\s*\)'
    r'|_MODEL"\s*,\s*"(gpt-[^"]+)"\s*\)'
    r'|model:\s*str\s*=\s*"(gpt-[^"]+)"'
)


def _configured_models() -> set[str]:
    found: set[str] = set()
    for path in SRC.rglob("*.py"):
        for m in _MODEL_LITERALS.finditer(path.read_text(encoding="utf-8")):
            found.update(g for g in m.groups() if g)
    return found


def test_every_model_the_configuration_names_has_a_price():
    models = _configured_models()
    # The two live ones must be found, or the scan is blind.
    assert {"gpt-4o-mini", "gpt-5-mini"} <= models, models
    assert {m for m in models if not is_priced(m)} == set()


def test_a_receipt_read_is_costed_at_list_price():
    """The step-4 A/B's first reading: 6,416 prompt tokens, none cached, 1,098
    completion tokens (960 of them reasoning) cost USD 0.0038 at list."""
    usage = TokenUsage.from_counts("gpt-5-mini", 6416, 1098)
    assert usage.cost_usd == Decimal("0.001604") + Decimal("0.002196")


def test_the_cached_part_of_the_prompt_bills_at_the_cached_rate():
    full = TokenUsage.from_counts("gpt-5-mini", 10_000, 0)
    half = TokenUsage.from_counts("gpt-5-mini", 10_000, 0, cached_input_tokens=5_000)
    assert full.cost_usd == Decimal("0.0025")
    assert half.cost_usd == Decimal("0.00125") + Decimal("0.000125")
    assert half.cached_input_tokens == 5_000
    # A count the provider could never report is clamped, not trusted.
    assert TokenUsage.from_counts("gpt-5-mini", 100, 0, 500).cached_input_tokens == 100


def _client_reading_one_receipt(usage) -> OpenAIClient:
    tracker = CostTracker()
    client = OpenAIClient(api_key="sk-test-not-real", vision_model="gpt-5-mini",
                          cost_tracker=tracker)
    payload = json.dumps({
        "document_type": "receipt", "date": "2026-09-16", "total": "100.00",
        "currency": "USD", "vendor": "Lovable Labs", "vendor_clean": "Lovable",
        "reference": "2810-5339-6113", "tax": None, "tax_label": None,
        "payment_hint": None, "card_last4": None, "line_items": [],
        "confidence": 0.9, "notes": "", "time": None, "invoice_number": None,
        "receipt_number": None, "document_kind": "receipt",
    })

    def _create(**_kw):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=payload))],
            usage=usage,
        )

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))
    return client


def test_a_photo_read_through_the_client_is_no_longer_free():
    """Through the caller: a vision read records its model and a real cost."""
    usage = SimpleNamespace(
        prompt_tokens=6416, completion_tokens=1098,
        prompt_tokens_details=SimpleNamespace(cached_tokens=0),
    )
    client = _client_reading_one_receipt(usage)
    client.extract_receipt(file_name="receipt.jpg", images=[(b"\xff\xd8", "image/jpeg")])
    (recorded,) = client.cost_tracker.usages
    assert recorded.model == "gpt-5-mini"
    assert recorded.cost_usd == Decimal("0.003800")


def test_the_client_passes_the_cached_part_and_tolerates_its_absence():
    cached = SimpleNamespace(prompt_tokens=10_000, completion_tokens=0,
                             prompt_tokens_details=SimpleNamespace(cached_tokens=5_000))
    client = _client_reading_one_receipt(cached)
    client.extract_receipt(file_name="receipt.jpg", images=[(b"\xff\xd8", "image/jpeg")])
    assert client.cost_tracker.usages[0].cached_input_tokens == 5_000
    # An older SDK response carries no details object at all.
    bare = SimpleNamespace(prompt_tokens=10_000, completion_tokens=0)
    client = _client_reading_one_receipt(bare)
    client.extract_receipt(file_name="receipt.jpg", images=[(b"\xff\xd8", "image/jpeg")])
    assert client.cost_tracker.usages[0].cost_usd == Decimal("0.0025")
