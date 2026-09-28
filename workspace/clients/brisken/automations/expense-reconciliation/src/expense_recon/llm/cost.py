"""Token / cost tracking for LLM calls.

Per-run aggregate that the report writer surfaces on the Summary
sheet ("LLM cost this run"). Costs are estimates from the public
per-model pricing table; the real bill comes from the provider
dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


# OpenAI prices in USD per 1M tokens (as of 2026-06). Update when
# the provider revises. Vision-input tokens are billed at the same
# rate as text input on gpt-4o / gpt-4o-mini per OpenAI's current
# pricing — image bytes are converted to "image tokens" by their
# API and counted against the input pool.
_PRICING_PER_MILLION: dict[str, tuple[Decimal, Decimal]] = {
    # model_name: (input $/M, output $/M)
    "gpt-4o-mini": (Decimal("0.150"), Decimal("0.600")),
    "gpt-4o": (Decimal("2.500"), Decimal("10.000")),
    "gpt-4.1-mini": (Decimal("0.400"), Decimal("1.600")),
    "gpt-4.1": (Decimal("2.000"), Decimal("8.000")),
    # Item 227 (2026-09-27): the vision model every photographed receipt and
    # rendered mail body is read with (`web.service.VISION_MODEL`). Unpriced
    # until now, so the tracker recorded about 93% of the real spend at 0.
    # Output includes the reasoning tokens (1,300-1,440 per receipt read).
    "gpt-5-mini": (Decimal("0.250"), Decimal("2.000")),
    # Item 239 (2026-09-28): Gemini as the receipt reader. Paid tier, prompts
    # up to 200k tokens, read 2026-09-27 from
    # https://ai.google.dev/gemini-api/docs/pricing (page dated 2026-09-24).
    # Images and PDF pages bill at the input rate; output includes thinking
    # tokens. 3.8 Flash doubles to 1.50 / 7.50 from 2027-01-01.
    "gemini-3.8-flash": (Decimal("0.750"), Decimal("3.750")),
    "gemini-3.1-pro-preview": (Decimal("2.000"), Decimal("12.000")),
    "gemini-3.5-flash-lite": (Decimal("0.300"), Decimal("2.500")),
}

# Cached input, USD per 1M tokens: the part of `prompt_tokens` the provider
# served from its prompt cache (`prompt_tokens_details.cached_tokens`).
# OpenAI Standard tier, read 2026-09-27 from
# https://developers.openai.com/api/docs/pricing. A model missing here bills
# its cached tokens at the full input rate.
_CACHED_INPUT_PER_MILLION: dict[str, Decimal] = {
    "gpt-4o-mini": Decimal("0.075"),
    "gpt-4o": Decimal("1.250"),
    "gpt-4.1-mini": Decimal("0.100"),
    "gpt-4.1": Decimal("0.500"),
    "gpt-5-mini": Decimal("0.025"),
}


def is_priced(model: str) -> bool:
    """Whether a call to ``model`` is costed, rather than recorded at 0."""
    return model in _PRICING_PER_MILLION


@dataclass(frozen=True)
class TokenUsage:
    """One LLM call's token counts + estimated cost."""

    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    # Item 227: the part of `input_tokens` served from the prompt cache.
    cached_input_tokens: int = 0

    @classmethod
    def from_counts(
        cls, model: str, input_tokens: int, output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> TokenUsage:
        in_rate, out_rate = _PRICING_PER_MILLION.get(
            model, (Decimal("0"), Decimal("0"))
        )
        cached = max(0, min(cached_input_tokens, input_tokens))
        cached_rate = _CACHED_INPUT_PER_MILLION.get(model, in_rate)
        cost = (
            (Decimal(input_tokens - cached) * in_rate)
            + (Decimal(cached) * cached_rate)
            + (Decimal(output_tokens) * out_rate)
        ) / Decimal("1000000")
        return cls(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            cached_input_tokens=cached,
        )


@dataclass
class CostTracker:
    """Accumulates token usage across a run.

    The categorizer calls `record()` after every LLM call; the CLI
    reads `total_cost_usd` and `call_count` at the end to surface
    on the Summary sheet.
    """

    usages: list[TokenUsage] = field(default_factory=list)

    def record(self, usage: TokenUsage) -> None:
        self.usages.append(usage)

    @property
    def call_count(self) -> int:
        return len(self.usages)

    @property
    def total_cost_usd(self) -> Decimal:
        return sum(
            (u.cost_usd for u in self.usages), start=Decimal("0")
        )

    @property
    def total_input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usages)

    @property
    def total_output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usages)
