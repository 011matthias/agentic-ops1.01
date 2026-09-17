"""A month is complete, and only a complete month publishes (items 99 + 100).

`ready_to_post` answers "is anything left to decide": no pending pairing and
a healthy month (item 57). On 2026-09-17 July 2026 read it true while 24
purchase charges had no receipt and 11 receipts had no charge, because a
charge with no receipt offers nothing to click. The pill turned green and
Publish, the month's sign-off since item 88, was enabled on it; the route
itself refused nothing, and the classic page published any run at all.

Owner rulings 2026-09-17: a month is COMPLETE when nothing is left to decide
AND

* every charge holds a receipt or carries an existing verdict that closes it:
  a credit (refund / payment / reversal), a charge already booked (Criss's
  yellow fill or the reviewer's already-posted verdict), or a fee / interest
  line the statement itself printed as one;
* every receipt holds a charge unless it is set aside: settled outside the
  card, a decided duplicate copy, or quarantined (a quarantined file never
  enters the pool). A receipt another month's charge already settled has a
  charge, so it does not count either;
* no receiptless charge still carries a category that is only the tool's
  guess (the row's own "confirm first" state, `receiptless_suggested`).

No new verdict is invented here. A gray "subscription" fill is an annotation
(and the tool can derive it from history), not a verdict, so it closes
nothing. A charge that needs a receipt is counted once, under
`n_charges_need_receipt`, even when it also carries a guess: attaching the
receipt replaces the guess. `n_charges_category_guessed` counts the guesses
on charges whose receipt requirement is otherwise closed (a fee line).

Pure functions over the run payload's own rows, so the pill, the counts and
the publish gate read one rule.
"""
from __future__ import annotations

PUBLISH_NOT_A_MONTH = "not_a_month"
PUBLISH_NO_STATEMENT = "no_statement"
PUBLISH_MONTH_NOT_COMPLETE = "month_not_complete"

_RECEIPTLESS_GUESS = "receiptless_suggested"


def charge_needs_receipt(row: dict) -> bool:
    """A purchase charge that holds no receipt and no verdict closes.

    `section == "posted"` is the already-booked flag (yellow fill or the
    already-posted verdict), whatever the verdict column says. A pending
    pairing is not here: it holds a receipt and is `n_undecided`'s."""
    return (
        row.get("effective_bucket") == "unmatched"
        and row.get("section") != "posted"
        and (row.get("row_type") or "purchase") == "purchase"
    )


def charge_category_guessed(row: dict) -> bool:
    """A receiptless charge whose category is still the tool's guess, counted
    only where no receipt is due (a charge that needs one is counted there)."""
    review = row.get("review") or {}
    return (
        review.get("reason_code") == _RECEIPTLESS_GUESS
        and not charge_needs_receipt(row)
    )


def receipt_needs_charge(receipt: dict) -> bool:
    """An element of `unmatched_receipts` that no charge holds anywhere.

    The list already leaves out settled-outside receipts and decided copies;
    a receipt another month's charge settled carries `settled_by`."""
    return "settled_by" not in receipt


def completeness_counts(rows: list[dict], unmatched_receipts: list[dict]) -> dict:
    return {
        "n_charges_need_receipt": sum(1 for r in rows if charge_needs_receipt(r)),
        "n_receipts_need_charge": sum(
            1 for r in unmatched_receipts if receipt_needs_charge(r)
        ),
        "n_charges_category_guessed": sum(
            1 for r in rows if charge_category_guessed(r)
        ),
    }


def is_month_complete(*, ready_to_post: bool, counts: dict) -> bool:
    return bool(ready_to_post) and not any(
        counts[k] for k in (
            "n_charges_need_receipt",
            "n_receipts_need_charge",
            "n_charges_category_guessed",
        )
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def not_complete_detail(summary: dict) -> str:
    """One English sentence naming what blocks the month; the SPA localizes
    from the counts, this is the fallback text of the refusal."""
    parts: list[str] = []
    if (summary.get("month_health") or {}).get("state") == "broken":
        parts.append("the month's inputs are broken (see month health)")
    if summary.get("n_undecided"):
        parts.append(_plural(summary["n_undecided"], "pairing to decide", "pairings to decide"))
    if summary.get("n_charges_need_receipt"):
        parts.append(_plural(
            summary["n_charges_need_receipt"],
            "charge still needs a receipt", "charges still need a receipt",
        ))
    if summary.get("n_receipts_need_charge"):
        parts.append(_plural(
            summary["n_receipts_need_charge"],
            "receipt has no charge", "receipts have no charge",
        ))
    if summary.get("n_charges_category_guessed"):
        parts.append(_plural(
            summary["n_charges_category_guessed"],
            "charge's category is still the tool's guess",
            "charges' categories are still the tool's guess",
        ))
    blockers = "; ".join(parts) or "it is not complete"
    return (
        f"This month cannot be published yet: {blockers}. "
        "Publish with override to sign it off anyway."
    )


READINESS_KEYS = (
    "month_complete",
    "ready_to_post",
    "n_undecided",
    "n_charges_need_receipt",
    "n_receipts_need_charge",
    "n_charges_category_guessed",
)


def readiness_of(summary: dict) -> dict:
    """The run summary's readiness fields, plus the month-health state, as
    the refusal carries them."""
    out = {k: summary.get(k) for k in READINESS_KEYS}
    out["month_health_state"] = (summary.get("month_health") or {}).get("state")
    return out
