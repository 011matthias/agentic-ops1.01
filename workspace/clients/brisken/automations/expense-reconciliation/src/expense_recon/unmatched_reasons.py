"""Why a receipt or a charge is unmatched (backlog items 75 + 83).

The Unmatched lists printed conclusions with no basis: "Unmatched 73" on July
read as 73 misses, while most of it was coverage (a card whose statement is
not loaded, a debit card, a charge that posts next month) and some of it was
copies of documents that had already settled their charge. This names one
reason per row, read off facts the month already holds. Pure functions: no
LLM, no network, no store.

Receipt side. The rules are the coverage classes of item 69's attribution
table (`tools/recon-match-attribution.py`: its non-card tender pattern, its
two-day statement edge, the matcher's own "cards present on the statement"),
with three changes, each measured on the 14 live receipts whose label names a
coverage kind (July + August 2026, `labels.csv`):

* the date edge is read BEFORE the card. The attribution table reads the
  labeler's evidence first, so its card-first order never met an unlabelled
  receipt; applied alone it called August's two 08-31 Google invoices
  "card not loaded" (they print `...2544` / `...9129`, and their charges post
  on 09-01 in September). Date-first: 11 of 14 name the labelled kind, the
  card-first order 9, and date-first gets none wrong that card-first gets
  right. Of the other three, two are bank-transfer invoices that print no
  payment method at all, so they read `no_charge_on_any_loaded_statement`,
  which is true of them; one (Konsultancy, dated 07-30, the statement's last
  day but one) reads `charge_in_neighbouring_period`, which is not.
* the edge is bounded to a month either side, so an invoice dated in March
  and mailed in July is not "neighbouring".
* a tender word counts only when the mode names no card digits: "Visa Debit
  ...3645" is a card the statement carries, not a debit card of someone's.

A receipt another month's charge has already claimed (`settled_by`) is in the
neighbouring period by proof, not by its date.

Charge side. The receipt vocabulary does not describe a charge (a card charge
is never "not a card charge"), so charges carry their own codes, from the
row's own facts: the statement line is not a purchase; the receipt the matcher
found is held by another charge (item 60's rule); the row is already booked
(the workbook's yellow, or the reviewer's already-posted verdict); it is booked
through Zoho recurring expenses (the gray fill); a reviewer ruled no receipt
will exist; otherwise no receipt was found. The last three before "no receipt
found" are the verdicts that close a charge for the month gate, so the list
and the gate name the same charges as settled (front 1, 2026-09-25).
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .matching.deterministic import _card_keys, _tx_card_keys
from .matching.types import Receipt, Transaction

# ── receipts ────────────────────────────────────────────────────────────
DUPLICATE_COPY = "duplicate_copy"
CARD_STATEMENT_NOT_LOADED = "card_statement_not_loaded"
NOT_A_CARD_CHARGE = "not_a_card_charge"
CHARGE_IN_NEIGHBOURING_PERIOD = "charge_in_neighbouring_period"
NO_CHARGE_ON_ANY_LOADED_STATEMENT = "no_charge_on_any_loaded_statement"
# Item 220: the card's statements are loaded, just not up to this date.
STATEMENT_NOT_LOADED_FOR_DATE = "statement_not_loaded_for_date"
RECEIPT_REASON_CODES = (
    DUPLICATE_COPY,
    CARD_STATEMENT_NOT_LOADED,
    NOT_A_CARD_CHARGE,
    CHARGE_IN_NEIGHBOURING_PERIOD,
    NO_CHARGE_ON_ANY_LOADED_STATEMENT,
    STATEMENT_NOT_LOADED_FOR_DATE,
)
# The two codes that mean "a statement is still to come", which is what the
# month's completeness sentence names separately (item 220).
WAITING_FOR_STATEMENT_CODES = frozenset(
    {CARD_STATEMENT_NOT_LOADED, STATEMENT_NOT_LOADED_FOR_DATE}
)

# ── charges ─────────────────────────────────────────────────────────────
NOT_A_PURCHASE = "not_a_purchase"
RECEIPT_HELD_BY_ANOTHER_CHARGE = "receipt_held_by_another_charge"
ALREADY_BOOKED = "already_booked"
NO_RECEIPT_FOUND = "no_receipt_found"
# Front 1 (2026-09-25): the two verdicts `month_readiness` already closes a
# charge on, which the list used to call "no receipt found".
CLOSED_RECURRING = "closed_recurring"
NO_RECEIPT_EXPECTED = "no_receipt_expected"
CHARGE_REASON_CODES = (
    NOT_A_PURCHASE,
    RECEIPT_HELD_BY_ANOTHER_CHARGE,
    ALREADY_BOOKED,
    NO_RECEIPT_FOUND,
    CLOSED_RECURRING,
    NO_RECEIPT_EXPECTED,
)

# ── the screen's words (item 96) ────────────────────────────────────────
#
# The reconciliation PDF prints these, so a receipt reads the same on paper
# as on the month page. Verbatim the SPA's EN strings
# (`docs/lovable-unmatched-reasons-prompt.md` section 5): a change there is a
# change here. `duplicate_copy` has no line: a copy is named by the list it
# sits in.
RECEIPT_REASON_TEXT = {
    NO_CHARGE_ON_ANY_LOADED_STATEMENT:
        "No charge on the loaded statement matches this receipt.",
    CARD_STATEMENT_NOT_LOADED: "Paid with a card whose statement is not loaded.",
    CHARGE_IN_NEIGHBOURING_PERIOD: (
        "Dated at the edge of this statement; the charge is likely in the "
        "previous or next month."
    ),
    NOT_A_CARD_CHARGE: "Paid by debit card, cash or transfer, not on this card.",
    STATEMENT_NOT_LOADED_FOR_DATE: (
        "The card's statement is not loaded up to this date yet; the charge "
        "appears when it is."
    ),
}
RECEIPT_REASON_SHORT = {
    NO_CHARGE_ON_ANY_LOADED_STATEMENT: "no charge found",
    CARD_STATEMENT_NOT_LOADED: "card not loaded",
    CHARGE_IN_NEIGHBOURING_PERIOD: "next or previous month",
    NOT_A_CARD_CHARGE: "not a card payment",
    STATEMENT_NOT_LOADED_FOR_DATE: "statement not loaded yet",
}

# From `tools/recon-match-attribution.py` (NON_CARD_TENDER, BOUNDARY_DAYS),
# plus the German till words (item 220): "Bar" / "Barzahlung" is cash,
# "girocard" often prints fused to its mode ("girocardOLV"), and "Kartenzahlung
# erhalten" is the German till's line for a girocard (EC) payment. Every one
# stays word-bounded, so "Barcelona" and "Bargain" never match.
NON_CARD_TENDER = re.compile(
    r"\b(debit|ec[- ]?karte|girocard(?:olv)?|maestro|cash|dinheiro|pix|bank transfer|"
    r"transfer[êe]ncia|boleto|paypal|cheque|check|bar(?:zahlung|geld)?|"
    r"kartenzahlung\s+erhalten)\b",
    re.IGNORECASE,
)
BOUNDARY_DAYS = 2
NEIGHBOUR_WINDOW_DAYS = 31


def loaded_card_keys(transactions: list[Transaction]) -> set[str]:
    """Every card identifier the month's loaded charges carry, the way the
    matcher reads a charge's card (`_tx_card_keys`), credits excluded like
    the statement check (`restore_copies_with_their_own_charge`) excludes
    them."""
    keys: set[str] = set()
    for t in transactions:
        if not t.is_credit:
            keys |= _tx_card_keys(t)
    return keys


def _near_edge(d: date | None, period: tuple[date, date] | None) -> bool:
    if d is None or period is None:
        return False
    start, end = period
    window = timedelta(days=NEIGHBOUR_WINDOW_DAYS)
    edge = timedelta(days=BOUNDARY_DAYS)
    return (start - window <= d < start + edge) or (end - edge < d <= end + window)


def receipt_reason_code(
    receipt: Receipt,
    *,
    loaded_cards: set[str],
    period: tuple[date, date] | None,
    settled_elsewhere: bool = False,
    uncovered_cards: list | tuple | set = (),
    coverage: dict | None = None,
) -> str:
    """The reason one unmatched receipt has no charge here (never
    `duplicate_copy`: a set-aside copy is named by the list it sits in).

    `uncovered_cards` (item 204, case 9 step 1): the active cards whose
    loaded statements, in any month, do not cover this receipt's date
    (`card_suggestion.uncovered_for_receipt`). A receipt that printed no
    card is then waiting for a statement, the same fact the Expenses row
    reads as `waits_for_statement`; before, `card_statement_not_loaded`
    needed printed digits, so such a receipt read "no charge found".

    `coverage` (item 220, `card_suggestion.reason_coverage`): what the
    loaded statements of the receipt's card (or, with no card, of every
    active card) say about its date. When present the CARD is read before
    the edge: September 2026 told 38 receipts dated after the last loaded
    charge that their charge was "likely in the previous or next month"
    while the Expenses tab said "waiting for the statement" for the same
    rows. A card with no statement loaded anywhere is
    `card_statement_not_loaded`; one whose statements stop short of the date
    is `statement_not_loaded_for_date`; a covered date reads the edge as
    before, and a card covered by ANOTHER month's statement is neighbouring
    by construction. Absent (no evidence, or printed digits no registry card
    names), the order stays date-first."""
    if settled_elsewhere:
        return CHARGE_IN_NEIGHBOURING_PERIOD
    keys = _card_keys(receipt.payment_mode)
    if not keys and receipt.payment_mode and NON_CARD_TENDER.search(receipt.payment_mode):
        return NOT_A_CARD_CHARGE
    if coverage is not None:
        waits = coverage.get("waits_for") or []
        if waits:
            if set(waits) <= set(coverage.get("never_loaded") or ()):
                return CARD_STATEMENT_NOT_LOADED
            return STATEMENT_NOT_LOADED_FOR_DATE
        if len(coverage.get("cards") or ()) == 1:
            card_keys = _card_keys(coverage["cards"][0])
            if card_keys and not (card_keys & loaded_cards):
                return CHARGE_IN_NEIGHBOURING_PERIOD
        if _near_edge(receipt.detected_date, period):
            return CHARGE_IN_NEIGHBOURING_PERIOD
        return NO_CHARGE_ON_ANY_LOADED_STATEMENT
    if _near_edge(receipt.detected_date, period):
        return CHARGE_IN_NEIGHBOURING_PERIOD
    if keys and not (keys & loaded_cards):
        return CARD_STATEMENT_NOT_LOADED
    if not keys and uncovered_cards:
        return CARD_STATEMENT_NOT_LOADED
    return NO_CHARGE_ON_ANY_LOADED_STATEMENT


def charge_reason_code(
    *,
    row_type: str | None,
    entry_status: str | None,
    candidates: list[dict],
    booked: bool = False,
    closed_recurring: bool = False,
    no_receipt_expected: bool = False,
) -> str:
    """The reason one unmatched charge has no receipt.

    Front 1 (2026-09-25). The list said `no_receipt_found` for every charge
    a verdict closes except Criss's yellow fill, so July's 24 and August's 40
    gray charges, which the month counts as closed, read as owed. The caller
    passes the verdicts it already holds, read by the same predicates the
    month gate reads: `booked` is the row's `section == "posted"` (yellow OR
    the reviewer's already-posted verdict, which `entry_status` alone never
    showed), `closed_recurring` is `month_readiness.charge_booked_recurring`
    (the gray fill, never a derived mark), and `no_receipt_expected` is the
    reviewer's item-107 mark."""
    if row_type and row_type != "purchase":
        return NOT_A_PURCHASE
    if candidates and all(c.get("held_by") for c in candidates):
        return RECEIPT_HELD_BY_ANOTHER_CHARGE
    if entry_status == "posted" or booked:
        return ALREADY_BOOKED
    if closed_recurring:
        return CLOSED_RECURRING
    if no_receipt_expected:
        return NO_RECEIPT_EXPECTED
    return NO_RECEIPT_FOUND


# Rule 5 (`docs/api-contract.md`): the charge vocabulary grew, so every
# element carrying a charge `reason_code` also carries `reason_label`, the
# English sentence an SPA that does not know the code can print instead of
# somebody else's label.
CHARGE_REASON_TEXT = {
    NOT_A_PURCHASE: "Not a purchase (a payment, fee or interest line); no receipt is needed.",
    RECEIPT_HELD_BY_ANOTHER_CHARGE: "The receipt found for this charge is held by another charge.",
    ALREADY_BOOKED: "Already booked in Zoho (yellow in the workbook, or marked by a reviewer); no receipt is needed.",
    NO_RECEIPT_FOUND: "No receipt found for this charge yet.",
    CLOSED_RECURRING: "Booked through a Zoho recurring expense (gray in the workbook); no receipt is needed.",
    NO_RECEIPT_EXPECTED: "Marked by a reviewer: no receipt will exist for this charge.",
}
