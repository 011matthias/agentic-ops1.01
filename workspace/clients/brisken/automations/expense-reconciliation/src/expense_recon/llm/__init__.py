"""LLM integration — slice 2.

`client` exposes the provider-agnostic `LLMClient` protocol plus
`OpenAIClient` (production) and `MockLLMClient` (tests). `cost`
tracks token usage + USD cost per run.

The protocol abstracts provider so the §38.2 stack decision can
swap (today: OpenAI, picked 2026-06-01; was originally scoped to
Anthropic Claude). The categorizer + (future) receipt-vision +
(future) FX-judgment all call through `LLMClient` only — provider
swap is one file.
"""
from .client import (
    ClassificationResult,
    LineItemInput,
    LLMClient,
    MockLLMClient,
    OpenAIClient,
)
from .cost import CostTracker, TokenUsage

__all__ = [
    "ClassificationResult",
    "CostTracker",
    "LineItemInput",
    "LLMClient",
    "MockLLMClient",
    "OpenAIClient",
    "TokenUsage",
]
