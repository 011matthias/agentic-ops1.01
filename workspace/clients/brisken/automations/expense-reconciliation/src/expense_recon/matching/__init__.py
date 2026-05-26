"""Matching engine — v2 spec §15.

Two layers, deliberately separated:

- `deterministic` — pure logic, no LLM. Common case (USD card +
  USD receipt) lands here. Dirk: "does not want AI where a
  deterministic match works" (call-outcomes "Matching approach").
- `judgment` — LLM judgment layer, invoked only when the
  deterministic layer cannot resolve (e.g., EUR-on-USD-card FX
  case). Pending Anthropic API access (v2 spec §38.2).
"""
