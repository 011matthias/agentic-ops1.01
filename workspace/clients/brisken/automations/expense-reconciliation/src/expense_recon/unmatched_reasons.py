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
is never "not a card charge"), so charges carry their own four codes, from the
row's own facts: the statement line is not a purchase; the receipt the matcher
found is held by another charge (item 60's rule); the reviewer's workbook marks
the row as already booked (yellow); otherwise no receipt was found.
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
RECEIPT_REASON_CODES = (
    DUPLICATE_COPY,
    CARD_STATEMENT_NOT_LOADED,
    NOT_A_CARD_CHARGE,
    CHARGE_IN_NEIGHBOURING_PERIOD,
    NO_CHARGE_ON_ANY_LOADED_STATEMENT,
)

# ── charges ─────────────────────────────────────────────────────────────
NOT_A_PURCHASE = "not_a_purchase"
RECEIPT_HELD_BY_ANOTHER_CHARGE = "receipt_held_by_another_charge"
ALREADY_BOOKED = "already_booked"
NO_RECEIPT_FOUND = "no_receipt_found"
CHARGE_REASON_CODES = (
    NOT_A_PURCHASE,
    RECEIPT_HELD_BY_ANOTHER_CHARGE,
    ALREADY_BOOKED,
    NO_RECEIPT_FOUND,
)

# Verbatim from `tools/recon-match-attribution.py` (NON_CARD_TENDER, BOUNDARY_DAYS).
NON_CARD_TENDER = re.compile(
    r"\b(debit|ec[- ]?karte|girocard|maestro|cash|dinheiro|pix|bank transfer|"
    r"transfer[êe]ncia|boleto|paypal|cheque|check)\b",
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
) -> str:
    """The reason one unmatched receipt has no charge here (never
    `duplicate_copy`: a set-aside copy is named by the list it sits in)."""
    if settled_elsewhere:
        return CHARGE_IN_NEIGHBOURING_PERIOD
    keys = _card_keys(receipt.payment_mode)
    if not keys and receipt.payment_mode and NON_CARD_TENDER.search(receipt.payment_mode):
        return NOT_A_CARD_CHARGE
    if _near_edge(receipt.detected_date, period):
        return CHARGE_IN_NEIGHBOURING_PERIOD
    if keys and not (keys & loaded_cards):
        return CARD_STATEMENT_NOT_LOADED
    return NO_CHARGE_ON_ANY_LOADED_STATEMENT


def charge_reason_code(
    *, row_type: str | None, entry_status: str | None, candidates: list[dict]
) -> str:
    """The reason one unmatched charge has no receipt."""
    if row_type and row_type != "purchase":
        return NOT_A_PURCHASE
    if candidates and all(c.get("held_by") for c in candidates):
        return RECEIPT_HELD_BY_ANOTHER_CHARGE
    if entry_status == "posted":
        return ALREADY_BOOKED
    return NO_RECEIPT_FOUND
