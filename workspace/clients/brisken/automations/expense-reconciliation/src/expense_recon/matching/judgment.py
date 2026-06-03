"""LLM judgment layer — v2 spec §15.2.

Invoked only when the deterministic layer returns FX_JUDGMENT, AMBIGUOUS,
or POSSIBLE. The common USD-on-USD case never reaches this module.

Slice-1 status: stub. The function signatures are the final shape, but
they return placeholder Match objects flagged for human review instead
of calling Anthropic Claude. The real call lands when API access to
Brisken's Pro subscription is provisioned (v2 spec §38.2, pending Dirk
task-list item).

The stub deliberately does NOT silently mark FX cases as resolved.
Every FX/ambiguous case still requires human review until the LLM is
wired — preserves the reconciliation guarantee (v2 spec §25.5).
"""
from __future__ import annotations

from typing import Any

from .types import Match, MatchType, Receipt, Transaction


STUB_REASON = (
    "[STUB] LLM judgment layer not yet wired (Anthropic API access pending). "
    "Human review required."
)


def judge_fx_match(
    tx: Transaction,
    receipt: Receipt,
    *,
    client: Any | None = None,
) -> Match:
    """Score an FX-mismatch candidate pair.

    Real implementation (slice 2): prompts Claude with the transaction
    + receipt context and asks whether the receipt is plausibly the
    same purchase after FX conversion. Returns a confidence-scored
    Match.

    Stub: returns the candidate as-is, still flagged for review.
    """
    return Match(
        transaction_id=tx.transaction_id,
        document_id=receipt.document_id,
        match_type=MatchType.FX_JUDGMENT,
        confidence=0.5,
        reason=STUB_REASON,
        requires_review=True,
    )


def judge_ambiguous(
    tx: Transaction,
    candidates: list[Match],
    receipts_by_id: dict[str, Receipt],
    *,
    client: Any | None = None,
) -> Match | None:
    """Pick the best of multiple tied candidates, or return None to
    leave them all in the ambiguous bucket.

    Stub: returns None — every ambiguous case stays for human review.
    """
    return None
