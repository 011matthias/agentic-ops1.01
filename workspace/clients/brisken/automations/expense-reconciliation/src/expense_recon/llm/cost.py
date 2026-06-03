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
}


@dataclass(frozen=True)
class TokenUsage:
    """One LLM call's token counts + estimated cost."""

    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal

    @classmethod
    def from_counts(
        cls, model: str, input_tokens: int, output_tokens: int
    ) -> TokenUsage:
        in_rate, out_rate = _PRICING_PER_MILLION.get(
            model, (Decimal("0"), Decimal("0"))
        )
        cost = (
            (Decimal(input_tokens) * in_rate)
            + (Decimal(output_tokens) * out_rate)
        ) / Decimal("1000000")
        return cls(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
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
