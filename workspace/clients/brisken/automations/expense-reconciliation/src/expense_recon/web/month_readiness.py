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
  yellow fill or the reviewer's already-posted verdict), a charge booked
  through Zoho recurring expenses (Criss's gray fill), or a fee / interest
  line the statement itself printed as one;
* every receipt holds a charge unless it is set aside: settled outside the
  card, a decided duplicate copy, quarantined (a quarantined file never
  enters the pool), or a confirmed private expense (paid on someone's own
  card, PR #987). A receipt another month's charge already settled has a
  charge, so it does not count either;
* no receiptless charge still carries a category that is only the tool's
  guess (the row's own "confirm first" state, `receiptless_suggested`).

Owner ruling 2026-09-17 (final), the gray fill: a charge Criss filled gray is
closed the way a yellow one is. Gray means "já estão no recurring": the
charge is already booked through Zoho's recurring expenses, so it needs no
receipt, and its category lives in that recurring entry, so the tool's guess
on it blocks nothing either. It first shipped the other way ("an annotation,
not a verdict, so it closes nothing"), and July 2026 then read 24 blocking
charges that were all gray and all already booked. The ruling covers the
FILL only. The tool also writes `entry_status: "subscription"` when a vendor
recurs in its statement history (`derive_subscription_status`, which marks
the row `entry_status_source: "derived"`); that is the tool's guess that a
charge is recurring, not Criss's record that it was booked, so it closes
nothing. `n_charges_closed_recurring` counts the charges the gray fill closed
while they hold no receipt, so the closure stays visible.

Item 107 adds the reviewer's two chase states, and only one of them is a
verdict. "No receipt expected", with its reason, closes the charge the way an
already-booked one does: an annual card fee has no receipt to find, so
counting it as an open receipt keeps a month permanently incomplete.
"Requested on {date}" closes nothing at all: the holder has been asked and
the receipt is still missing, which is precisely a charge that needs one.
`n_charges_receipt_requested` says how many of the open charges are already
chased, and `n_charges_no_receipt_expected` keeps the closure visible.

No verdict beyond those is invented here. A charge that needs a receipt is
counted once, under `n_charges_need_receipt`, even when it also carries a
guess: attaching the receipt replaces the guess. `n_charges_category_guessed`
counts the guesses on charges whose receipt requirement is otherwise closed
(a fee line), except on a gray-filled charge.

Pure functions over the run payload's own rows, so the pill, the counts and
the publish gate read one rule.
"""
from __future__ import annotations

PUBLISH_NOT_A_MONTH = "not_a_month"
PUBLISH_NO_STATEMENT = "no_statement"
PUBLISH_MONTH_NOT_COMPLETE = "month_not_complete"

_RECEIPTLESS_GUESS = "receiptless_suggested"
_SUBSCRIPTION = "subscription"
_DERIVED = "derived"


def charge_booked_recurring(row: dict) -> bool:
    """Criss's gray fill: the charge is booked through Zoho recurring expenses
    (owner ruling 2026-09-17). A subscription mark the tool derived from
    statement history (`entry_status_source: "derived"`) is a guess and books
    nothing; an absent source is the workbook fill."""
    return (
        row.get("entry_status") == _SUBSCRIPTION
        and row.get("entry_status_source") != _DERIVED
    )


def _charge_without_receipt(row: dict) -> bool:
    """A charge no receipt and no already-booked verdict settles.

    `section == "posted"` is the already-booked flag (yellow fill or the
    already-posted verdict), whatever the verdict column says. A pending
    pairing is not here: it holds a receipt and is `n_undecided`'s."""
    return (
        row.get("effective_bucket") == "unmatched"
        and row.get("section") != "posted"
    )


def charge_no_receipt_expected(row: dict) -> bool:
    """Item 107: the reviewer's verdict that no receipt will ever exist for
    this charge, carrying the reason (an annual card fee, interest, a bank
    charge). A verdict, so it closes the charge exactly as an already-booked
    one does; the reason is the whole content of it, so a blank string is no
    mark at all."""
    return bool(str(row.get("no_receipt_expected") or "").strip())


def charge_needs_receipt(row: dict) -> bool:
    """A purchase charge that holds no receipt and no verdict closes."""
    return (
        _charge_without_receipt(row)
        and (row.get("row_type") or "purchase") == "purchase"
        and not charge_booked_recurring(row)
        and not charge_no_receipt_expected(row)
    )


def charge_receipt_requested(row: dict) -> bool:
    """Item 107: a charge whose holder has been ASKED for the receipt and
    that still needs one. Asking closes nothing, so this is a subset of
    `n_charges_need_receipt` and never changes it: it says how much of the
    chase is already out, which is the difference between "nobody has looked
    at this" and "Dirk owes us a PDF"."""
    return bool(row.get("receipt_requested_at")) and charge_needs_receipt(row)


def charge_closed_recurring(row: dict) -> bool:
    """A charge holding no receipt that only the gray fill closes: what
    `n_charges_closed_recurring` counts, so the closure stays visible."""
    return _charge_without_receipt(row) and charge_booked_recurring(row)


def charge_category_guessed(row: dict) -> bool:
    """A receiptless charge whose category is still the tool's guess, counted
    only where no receipt is due (a charge that needs one is counted there)
    and never on a gray-filled charge, whose category lives in the recurring
    entry it was booked through."""
    if charge_booked_recurring(row):
        return False
    review = row.get("review") or {}
    return (
        review.get("reason_code") == _RECEIPTLESS_GUESS
        and not charge_needs_receipt(row)
    )


def receipt_needs_charge(
    receipt: dict, *, private_docs=frozenset(), copy_docs=frozenset()
) -> bool:
    """A receipt no charge holds (an `unmatched_receipts` or
    `copies_set_aside` element) that still needs one.

    Not a decided copy (`copy_docs`: `service.decided_copies`, the one
    predicate every listing and total on the month reads, item 94). Not a
    receipt another month's charge settled (`settled_by`). Not a CONFIRMED
    private expense (`private_docs`: the flag AND who is reimbursed,
    `service._private_reimbursements`): it was paid on someone's own card, so
    no company card charge will ever exist for it. Settled-outside receipts
    never reach the lists, and neither do bills paid by bank transfer (Build 4
    / item 218: `build_view` drops both through its effective map)."""
    doc = receipt.get("document_id")
    return (
        "settled_by" not in receipt
        and doc not in private_docs
        and doc not in copy_docs
    )


def completeness_counts(
    rows: list[dict],
    receipts_without_charge: list[dict],
    *,
    private_docs=frozenset(),
    copy_docs=frozenset(),
) -> dict:
    return {
        "n_charges_need_receipt": sum(1 for r in rows if charge_needs_receipt(r)),
        "n_receipts_need_charge": sum(
            1 for r in receipts_without_charge
            if receipt_needs_charge(
                r, private_docs=private_docs, copy_docs=copy_docs
            )
        ),
        "n_charges_category_guessed": sum(
            1 for r in rows if charge_category_guessed(r)
        ),
        # Never blocks: the gray-filled charges the ruling closed.
        "n_charges_closed_recurring": sum(
            1 for r in rows if charge_closed_recurring(r)
        ),
        # Item 107, neither blocks. The first is a SUBSET of
        # `n_charges_need_receipt` (asking closes nothing), the second is
        # what the "no receipt expected" verdict closed, kept visible for
        # the same reason `n_charges_closed_recurring` is.
        "n_charges_receipt_requested": sum(
            1 for r in rows if charge_receipt_requested(r)
        ),
        "n_charges_no_receipt_expected": sum(
            1 for r in rows
            if _charge_without_receipt(r) and charge_no_receipt_expected(r)
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
    "n_charges_closed_recurring",
    "n_charges_receipt_requested",
    "n_charges_no_receipt_expected",
)


def readiness_of(summary: dict) -> dict:
    """The run summary's readiness fields, plus the month-health state, as
    the refusal carries them."""
    out = {k: summary.get(k) for k in READINESS_KEYS}
    out["month_health_state"] = (summary.get("month_health") or {}).get("state")
    return out
