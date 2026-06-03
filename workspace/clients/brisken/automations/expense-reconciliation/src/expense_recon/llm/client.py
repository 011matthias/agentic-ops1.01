"""LLMClient protocol + OpenAI + Mock implementations.

The protocol is intentionally narrow — only the categorization shape
slice-2-part-1 needs today. Vision OCR (receipt extraction) and FX
judgment are sketched as future protocol additions but not implemented
in this slice. The provider swap is one line in `OpenAIClient.model`.

LD-2 invariants the LLM call must honour:

* Line-item classification reads ONLY the line item's description.
  Vendor name is NEVER in the prompt. Prompts that drift from this
  are a Tier-1 contract violation.
* `confidence < 0.6` routes to REVIEW (caller responsibility, but the
  prompt instructs the LLM to use the full 0.0–1.0 range honestly).
* Vendor fallback is a separate call (Tier 2) with its own prompt;
  vendor name IS the input here, and the result is marked
  `Source: VENDOR`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .cost import CostTracker, TokenUsage


@dataclass(frozen=True)
class LineItemInput:
    """One line item to classify. Vendor is NOT carried here on purpose
    (LD-2: per-line classification reads description only)."""

    description: str
    line_total: Decimal
    quantity: Decimal | None = None


@dataclass(frozen=True)
class ClassificationResult:
    """One classification decision from the LLM.

    `category` is None when the LLM is not confident enough; the
    caller routes that to REVIEW. `zoho_account` is populated only
    when a chart-of-accounts was supplied (slice 4).
    """

    category: str | None
    zoho_account: str | None
    confidence: float
    reasoning: str


class LLMClient(Protocol):
    """Provider-agnostic client interface used by the categorizer."""

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        """Tier 1 path (LD-2). One batched call per receipt."""
        ...

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        """Tier 2 fallback (LD-2). Triggered only when line items are
        absent or all vague."""
        ...


# ── OpenAI implementation ────────────────────────────────────────────


_LINE_ITEMS_PROMPT_TEMPLATE = """You categorize line items from a business expense receipt.

Categories (pick exactly one per line item, or null if you're not confident):
{categories_block}

Rules:
- Classify each line item from its DESCRIPTION ALONE.
- Do NOT consider vendor name or any other context. The description must justify the category by itself.
- If a line item is too vague to classify confidently (e.g., "Item 1", "Service charge", short or generic text), set category to null and confidence below 0.6.
- Confidence is your honest assessment in the range 0.0 to 1.0.
- Reasoning is one short sentence (max ~15 words) explaining your pick.

Line items to classify:
{items_block}

Return a JSON object with key "results" whose value is an array of {n_items} objects, one per input item, in the same order. Each object has: index (1-based, matching the input), category (one of the listed names or null), confidence (number), reasoning (string).
"""

_VENDOR_PROMPT_TEMPLATE = """You categorize a business expense receipt using only the vendor name and total amount. The receipt has no line-item breakdown.

Categories (pick exactly one, or null if you cannot infer with reasonable confidence):
{categories_block}

Rules:
- The vendor name is your only clue. Use it conservatively — if multiple categories are plausible, prefer the most common business interpretation but lower your confidence.
- Confidence is your honest assessment in 0.0–1.0.
- Reasoning is one short sentence (max ~15 words).

Vendor: {vendor}
Total: {total}

Return a single JSON object with: category (one of the listed names or null), confidence (number), reasoning (string).
"""


_LINE_ITEMS_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "category": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["index", "category", "confidence", "reasoning"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

_VENDOR_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["category", "confidence", "reasoning"],
    "additionalProperties": False,
}


class OpenAIClient:
    """OpenAI-backed implementation. Provider swap = subclass with the
    same method signatures and instantiate that instead.

    The API key comes from the `OPENAI_API_KEY` environment variable
    by default; pass `api_key=` to override (mostly for tests).
    Never accept the key value via a committed config file.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package not installed; run `uv sync`"
            ) from exc

        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OpenAI API key missing — set OPENAI_API_KEY env var or "
                "pass api_key= to OpenAIClient(...)."
            )
        self._client = OpenAI(api_key=key)
        self.model = model
        self.cost_tracker = cost_tracker or CostTracker()

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        if not items:
            return []

        items_block = "\n".join(
            f"  {i+1}. {it.description!r} — total {it.line_total}"
            for i, it in enumerate(items)
        )
        prompt = _LINE_ITEMS_PROMPT_TEMPLATE.format(
            categories_block="\n".join(f"  - {c}" for c in categories),
            items_block=items_block,
            n_items=len(items),
        )

        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "line_item_classifications",
                    "schema": _LINE_ITEMS_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)

        payload = json.loads(response.choices[0].message.content or "{}")
        raw_results = payload.get("results", [])

        # Index the results by the LLM's reported index, then re-emit
        # in input order — defends against the model returning a
        # reordered list.
        by_index = {r["index"]: r for r in raw_results}
        out: list[ClassificationResult] = []
        for i, _ in enumerate(items, start=1):
            r = by_index.get(i)
            if r is None:
                out.append(_review_result("LLM did not return a result for this item"))
                continue
            out.append(
                ClassificationResult(
                    category=r.get("category"),
                    zoho_account=None,
                    confidence=float(r.get("confidence", 0.0)),
                    reasoning=str(r.get("reasoning", "")),
                )
            )
        return out

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        prompt = _VENDOR_PROMPT_TEMPLATE.format(
            categories_block="\n".join(f"  - {c}" for c in categories),
            vendor=vendor,
            total=total,
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "vendor_classification",
                    "schema": _VENDOR_SCHEMA,
                    "strict": True,
                },
            },
            temperature=0,
        )
        self._record_usage(response)

        payload = json.loads(response.choices[0].message.content or "{}")
        return ClassificationResult(
            category=payload.get("category"),
            zoho_account=None,
            confidence=float(payload.get("confidence", 0.0)),
            reasoning=str(payload.get("reasoning", "")),
        )

    def _record_usage(self, response) -> None:
        try:
            usage = response.usage
            input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(usage, "completion_tokens", 0) or 0
        except AttributeError:
            input_tokens = 0
            output_tokens = 0
        self.cost_tracker.record(
            TokenUsage.from_counts(self.model, input_tokens, output_tokens)
        )


def _review_result(reason: str) -> ClassificationResult:
    return ClassificationResult(
        category=None, zoho_account=None, confidence=0.0, reasoning=reason
    )


# ── Mock for tests ───────────────────────────────────────────────────


class MockLLMClient:
    """In-memory client for tests. Configurable canned responses.

    Two modes:
    * `responses` — pre-recorded queue; each `classify_*` call pops one.
    * Default — deterministic naive mapping from description/vendor
      via simple substring match (different from production but useful
      to exercise the call shape).
    """

    def __init__(
        self,
        responses: list[list[ClassificationResult] | ClassificationResult] | None = None,
        *,
        cost_tracker: CostTracker | None = None,
    ):
        self._queue = list(responses or [])
        self.calls: list[tuple[str, object]] = []
        self.cost_tracker = cost_tracker or CostTracker()
        # Record a fixed nominal cost per call so tests can verify
        # cost-tracking behavior without coupling to provider pricing.
        self._per_call_cost = TokenUsage(
            model="mock", input_tokens=100, output_tokens=50, cost_usd=Decimal("0.001")
        )

    def classify_line_items(
        self,
        items: list[LineItemInput],
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> list[ClassificationResult]:
        self.calls.append(("classify_line_items", items))
        self.cost_tracker.record(self._per_call_cost)

        if self._queue:
            queued = self._queue.pop(0)
            if isinstance(queued, list):
                return queued
            return [queued]
        return [_default_for_description(it.description, categories) for it in items]

    def classify_by_vendor(
        self,
        vendor: str,
        total: Decimal,
        categories: list[str],
        chart_of_accounts: list[str] | None = None,
    ) -> ClassificationResult:
        self.calls.append(("classify_by_vendor", (vendor, total)))
        self.cost_tracker.record(self._per_call_cost)

        if self._queue:
            queued = self._queue.pop(0)
            if isinstance(queued, list):
                return queued[0] if queued else _review_result("empty queue entry")
            return queued
        return _default_for_vendor(vendor, categories)


def _default_for_description(
    description: str, categories: list[str]
) -> ClassificationResult:
    """Deterministic mock heuristic — not for production. Used only
    when no `responses` queue is supplied to MockLLMClient.
    """
    d = description.lower()
    if "coffee" in d or "latte" in d or "lunch" in d or "food" in d:
        cat = "Meals & Entertainment"
    elif "chair" in d or "cable" in d or "monitor" in d or "laptop" in d:
        cat = "Equipment & Hardware"
    elif "uber" in d or "taxi" in d or "flight" in d:
        cat = "Travel & Transport"
    else:
        return _review_result("mock: no description match")
    if cat not in categories:
        return _review_result(f"mock: '{cat}' not in supplied categories")
    return ClassificationResult(
        category=cat, zoho_account=None, confidence=0.9,
        reasoning=f"mock: matched on '{description}'",
    )


def _default_for_vendor(
    vendor: str, categories: list[str]
) -> ClassificationResult:
    v = vendor.lower()
    if "uber" in v or "lyft" in v:
        cat = "Travel & Transport"
    elif "starbucks" in v or "cafe" in v:
        cat = "Meals & Entertainment"
    else:
        return _review_result("mock: vendor not in defaults")
    if cat not in categories:
        return _review_result(f"mock: '{cat}' not in supplied categories")
    return ClassificationResult(
        category=cat, zoho_account=None, confidence=0.75,
        reasoning=f"mock: vendor '{vendor}' matched on keyword",
    )
