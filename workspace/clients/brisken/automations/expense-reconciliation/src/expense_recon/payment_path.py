"""Which way a receipt was paid: a company card, or a bill paid by bank
transfer (Build 4 / backlog item 218, owner decisions 2026-09-25).

July 2026 held four invoices no card paid: Konsultancy Finance (EUR
15,972), Redis (USD 13,200), 360Crossmedia (EUR 900) and Rodrigo Tanure
Tricarico (BRL 27,203.34). Each sat in the card queue waiting for a
statement that will never cover it. Item 62's "settled outside the card"
retired them from the reconciliation side one click at a time; this module
names the path itself, so a bill leaves the CARD side as a whole: the card
counts, the month's total, `expenses.csv` and the Zoho journal. It stays in
its month, in a Bills section, and goes out as `bills.csv` for Criss to
book by hand. Nothing posts anywhere.

Owner decision 2 (the trigger). A row takes the bill path BY ITSELF only
when the document's stated payment method reads as a bank payment and names
no card (`stated_bank_payment`), or when the reviewer's item-62 disposition
says `how="bank_transfer"`. A row that only PRINTS the supplier's bank
details gets a one-click suggestion (`printed_bank_details`), never a move.
A person can move any row either way (the `payment_path` field override).
Routing by supplier NAME is forbidden: SAP and Redis are also charged to
Brisken cards every month, so there is no vendor list here.

Pure: no service import, so the rules are testable on their own and the
service keeps only the call sites.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterable, Mapping
from typing import NamedTuple

PATH_CARD = "card"
PATH_BILL = "bill"
PATHS = (PATH_CARD, PATH_BILL)

# Why a row is on its path, the parallel field beside `payment_path`.
SOURCE_PERSON = "person"                    # the `payment_path` override
SOURCE_SETTLED_OUTSIDE = "settled_outside"  # item 62, how="bank_transfer"
SOURCE_STATED = "stated"                    # the document's payment method
SOURCE_STATEMENT = "statement"              # a charge holds a row that would be a bill
SOURCE_NONE = ""                            # the default: a card
SOURCES = (
    SOURCE_PERSON, SOURCE_SETTLED_OUTSIDE, SOURCE_STATED, SOURCE_STATEMENT,
    SOURCE_NONE,
)

# The per-row field override a person moves a row with (the existing
# expense-field PUT, so `edited_fields` carries it). Read at view time only:
# it is not a match field, and it moves no company.
OVERRIDE_FIELD = "payment_path"

EVIDENCE_MAX = 120

# The service's `_CARD_TOKEN_RE`, copied because this module imports nothing
# from the service (a test holds the two patterns equal). A mode that names a
# card is a card: "Electronic Funds Transfer ...2838" is a transfer that
# names the card it posted to. Four consecutive digits is the card-tail
# shape; an amount like "13,200.00" never carries four in a row.
_CARD_TOKEN_RE = re.compile(
    r"visa|master|maestro|amex|american\s+express|discover|elo\b|"
    r"card|karte|cart[aã]o|cr[eé]dito|d[eé]bito|debit|credit|\d{4}",
    re.IGNORECASE,
)

# A bank payment, word-bounded. The service's `bank_transfer_tender` rule
# (its `_TENDER_PATTERNS["bank_transfer"]` minus TEF) plus the two Brazilian
# bank rails boleto and PIX and a bare "wire", so every mode that answers
# `bank_transfer_tender` answers here too. TEF is NOT here: on a cupom
# fiscal it is the card terminal (July's Fenix groceries receipt prints TEF
# and settles a card charge).
_BANK_PAYMENT_RE = re.compile(
    r"\b(?:bank|wire|electronic\s+funds?)\s+transfers?\b"
    r"|\bwire\b"
    r"|\btransfer[eê]ncia\b|\btransferencia\b|\b[uü]berweisung\b"
    r"|\bsepa\b|\bach\b|\bvirement\b|\bbonifico\b"
    r"|\bboleto\b|\bpix\b",
    re.IGNORECASE,
)

# An invoice's payment OPTION, not how it was paid: "Pay $15.00 with a bank
# transfer". Item 62's owner ruling (2026-09-15) counts that line as a signal
# for a SUGGESTION, and says why it can be no more: the one live instance sat
# on an August Lovable receipt that DID post to a card. An automatic move
# needs the stated method, so the offer wording suggests and never moves.
_PAYMENT_OFFER_RE = re.compile(
    r"^\W*(?:to\s+|you\s+(?:can|may)\s+)?pay\b", re.IGNORECASE,
)

# Printed payment bank details, one pattern per label. Case matters where the
# label is an acronym that is also a word ("BIC" pens, an "Aba" surname).
# "Remittance" is deliberately absent: Redis's past-due reminder says "Please
# send payment remittance to ..." and prints no account, and the reminder is
# not a bill.
_BANK_DETAIL_RES = (
    re.compile(r"\biban\b", re.IGNORECASE),
    # An IBAN-shaped run: country, check digits, then at least two groups of
    # four. A German VAT id (DE123456789) has one group and a remainder, so
    # it does not match.
    re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?\b"),
    re.compile(r"\bswift\b", re.IGNORECASE),
    re.compile(r"\bBIC\b"),
    re.compile(r"\bABA\b"),
    re.compile(r"\brouting\s+(?:number|no\b\.?|#)", re.IGNORECASE),
    re.compile(r"\bwire\s+transfers?\b", re.IGNORECASE),
    re.compile(r"\bbank\s+account\s+(?:number|no\b\.?|#)", re.IGNORECASE),
    re.compile(r"\bbankverbindung\b", re.IGNORECASE),
    re.compile(r"\bdados\s+banc[aá]rios\b", re.IGNORECASE),
)


def _evidence(text: str) -> str:
    return " ".join(text.split())[:EVIDENCE_MAX]


def names_a_card(text: str | None) -> bool:
    """Whether a payment method names a card (the service's card-token rule)."""
    return bool(_CARD_TOKEN_RE.search(text or ""))


def stated_bank_payment(payment_mode: str | None) -> str | None:
    """The evidence text when the document's STATED payment method reads as a
    bank payment and names no card, else None.

    Reads wire / bank transfer / electronic funds transfer / transferência /
    transferencia / Überweisung / SEPA / ACH / virement / bonifico / boleto /
    PIX. A superset of the service's `bank_transfer_tender` (boleto, PIX and a
    bare "wire" added), so the tool never offers "paid by bank transfer" on
    one screen and routes the same words to the card queue on another. Two
    exclusions: a mode naming a card ("Electronic Funds Transfer ...2838" is
    a card), and an invoice's payment offer ("Pay $15.00 with a bank
    transfer"), which is a signal for a suggestion and never a move."""
    text = (payment_mode or "").strip()
    if not text or names_a_card(text) or _PAYMENT_OFFER_RE.search(text):
        return None
    if _BANK_PAYMENT_RE.search(text):
        return _evidence(text)
    return None


def offered_bank_payment(payment_mode: str | None) -> str | None:
    """The evidence text when the payment method is an invoice's bank-payment
    OFFER ("Pay $15.00 with a bank transfer") naming no card, else None.
    Feeds the suggestion, never the path."""
    text = (payment_mode or "").strip()
    if not text or names_a_card(text) or not _PAYMENT_OFFER_RE.search(text):
        return None
    if _BANK_PAYMENT_RE.search(text):
        return _evidence(text)
    return None


def printed_bank_details(text: str | None) -> str | None:
    """The first line (at most 120 characters) of a document that prints the
    supplier's payment bank details, else None.

    An IBAN label or an IBAN-shaped string, a SWIFT or BIC label, "ABA", a
    routing number, wire-transfer instructions, a bank account number,
    "Bankverbindung", "dados bancários". A document that prints these is
    probably an invoice paid into that account, which is a suggestion and
    never a move: a card-paid invoice can print its supplier's bank details
    too. "Remittance" alone never fires (the Redis reminder)."""
    for line in (text or "").splitlines():
        if any(p.search(line) for p in _BANK_DETAIL_RES):
            return _evidence(line)
    return None


def normalize_override(value: object) -> str:
    """A stored `payment_path` override as `card`, `bill` or "" (none)."""
    text = str(value or "").strip().lower()
    return text if text in PATHS else ""


def resolve_payment_path(
    *,
    override: object,
    settled_entry: Mapping | None,
    payment_mode: str | None,
    held_by_charge: bool,
) -> tuple[str, str]:
    """`(path, source)` for one row, in this precedence:

    1. a charge of this month holds the receipt: `(card, "statement")`. A
       statement charge is proof a card paid it, as item 62's "the match
       wins" rule already says for a settled-outside receipt;
    2. a person's override, either way: `(card|bill, "person")`;
    3. the reviewer's item-62 disposition says bank transfer:
       `(bill, "settled_outside")`;
    4. the document states a bank payment and names no card:
       `(bill, "stated")`;
    5. otherwise `(card, "")`."""
    if held_by_charge:
        return PATH_CARD, SOURCE_STATEMENT
    chosen = normalize_override(override)
    if chosen:
        return chosen, SOURCE_PERSON
    if isinstance(settled_entry, Mapping) and settled_entry.get("how") == "bank_transfer":
        return PATH_BILL, SOURCE_SETTLED_OUTSIDE
    if stated_bank_payment(payment_mode):
        return PATH_BILL, SOURCE_STATED
    return PATH_CARD, SOURCE_NONE


class LazyDocs:
    """A document set read only when first asked. `month_held_docs` parses the
    month's snapshot; most rows never need it, so a month with no bill signal
    never pays for the read."""

    def __init__(self, source: "Collection[str] | Callable[[], Iterable[str]] | None"):
        self._source = source
        self._docs: frozenset[str] | None = None

    def __contains__(self, doc: object) -> bool:
        if self._docs is None:
            src = self._source
            self._docs = frozenset(src() if callable(src) else (src or ()))
        return doc in self._docs


class MonthPaths(NamedTuple):
    """One month's payment paths, decided once per payload.

    `paths`: document_id -> `(path, source)` for every receipt.
    `bills`: document_id -> source, the bill rows only.
    `effective_settled`: the settled-outside map every reconciliation and
    exemption consumer reads (see `effective_settled_outside`).
    `displayed_settled`: the stored dispositions minus the ones a person has
    overruled, which is what a row displays and `n_settled_outside` counts.
    `held`: the receipts a charge holds (lazy)."""

    paths: dict
    bills: dict
    effective_settled: dict
    displayed_settled: dict
    held: LazyDocs


def displayed_settled_outside(
    stored: Mapping[str, Mapping], field_overrides: Mapping[str, Mapping],
) -> dict[str, dict]:
    """The stored item-62 dispositions minus a bank-transfer one whose row a
    person has since moved to the card path. The later explicit decision
    wins, and a disposition it overruled would otherwise still display.
    Nothing is deleted: clearing the override brings it back."""
    out: dict[str, dict] = {}
    for doc, entry in stored.items():
        if (
            entry.get("how") == "bank_transfer"
            and normalize_override(
                (field_overrides.get(doc) or {}).get(OVERRIDE_FIELD)
            ) == PATH_CARD
        ):
            continue
        out[doc] = dict(entry)
    return out


def effective_settled_outside(
    displayed: Mapping[str, Mapping], paths: Mapping[str, tuple[str, str]],
) -> dict[str, dict]:
    """The settled-outside map the reconciliation side and the card exemptions
    read: the displayed dispositions, plus a derived bank-transfer entry for
    every bill row that has no stored one. The derived entry names why the
    row is a bill (`derived`: its source) and carries no note and no time,
    because nobody wrote one."""
    out = {doc: dict(entry) for doc, entry in displayed.items()}
    for doc, (path, source) in paths.items():
        if path != PATH_BILL:
            continue
        if (out.get(doc) or {}).get("how") == "bank_transfer":
            continue
        out[doc] = {"how": "bank_transfer", "note": "", "at": None, "derived": source}
    return out


def month_paths(
    receipts: Iterable,
    field_overrides: Mapping[str, Mapping],
    stored_settled: Mapping[str, Mapping],
    held: "LazyDocs | Collection[str] | Callable[[], Iterable[str]] | None" = None,
) -> MonthPaths:
    """Every row's path for one month.

    The hold is consulted only for a row carrying a signal (an override, a
    bank-transfer disposition, a stated bank payment): on a row with none it
    cannot change the path, so `statement` names a charge that overrode a
    signal, and a month with no signal never reads its holds at all."""
    held_docs = held if isinstance(held, LazyDocs) else LazyDocs(held)
    field_overrides = field_overrides or {}
    stored_settled = stored_settled or {}
    paths: dict[str, tuple[str, str]] = {}
    for r in receipts:
        doc = r.document_id
        unheld = resolve_payment_path(
            override=(field_overrides.get(doc) or {}).get(OVERRIDE_FIELD),
            settled_entry=stored_settled.get(doc),
            payment_mode=r.payment_mode,
            held_by_charge=False,
        )
        if unheld != (PATH_CARD, SOURCE_NONE) and doc in held_docs:
            paths[doc] = (PATH_CARD, SOURCE_STATEMENT)
        else:
            paths[doc] = unheld
    displayed = displayed_settled_outside(stored_settled, field_overrides)
    return MonthPaths(
        paths=paths,
        bills={doc: src for doc, (path, src) in paths.items() if path == PATH_BILL},
        effective_settled=effective_settled_outside(displayed, paths),
        displayed_settled=displayed,
        held=held_docs,
    )


def bill_suggestion(
    receipt,
    *,
    path: str,
    source: str,
    has_card: bool,
    private: bool,
    suggested_private: bool,
    settled_entry: Mapping | None,
    held: "LazyDocs | Collection[str]",
) -> dict | None:
    """`{"evidence": ...}` when a card-path row looks like a bank-paid bill,
    else None. Never applied: the reviewer moves the row or does not.

    Offered on an OPEN card row only: no card resolved, not private or
    suggested private, no settled-outside disposition, not moved back to the
    card by a person, and no charge holding it. Evidence is the printed bank
    details, else an invoice's bank-payment offer. The caller leaves a
    decided copy out (its original carries the suggestion)."""
    if path != PATH_CARD or source in (SOURCE_PERSON, SOURCE_STATEMENT):
        return None
    if has_card or private or suggested_private or settled_entry:
        return None
    evidence = printed_bank_details(receipt.ocr_text) or offered_bank_payment(
        receipt.payment_mode
    )
    if evidence is None or receipt.document_id in held:
        return None
    return {"evidence": evidence}


# ── the stamp the Expenses payload reads ─────────────────────────────────


def stamp_card_resolution(
    card_res: dict[str, dict], receipts: Iterable, paths: MonthPaths,
) -> None:
    """Put each row's path, its source and any suggestion on the row's card
    resolution (`resolve_batch_row_cards`), the one per-row record every
    surface of the Expenses payload already reads, so the grid, the boxes
    and the strip cannot answer "is this a bill" twice."""
    for r in receipts:
        res = card_res.get(r.document_id)
        if res is None:
            continue
        path, source = paths.paths.get(r.document_id, (PATH_CARD, SOURCE_NONE))
        res["payment_path"] = path
        res["payment_path_source"] = source
        hit = bill_suggestion(
            r, path=path, source=source,
            has_card=res.get("card") is not None,
            private=bool(res.get("private")),
            suggested_private=bool(res.get("suggested_private")),
            settled_entry=paths.displayed_settled.get(r.document_id),
            held=paths.held,
        )
        if hit is not None:
            res["bill_suggestion"] = hit


# ── bills.csv rows ───────────────────────────────────────────────────────

# English, because the CSV is English throughout (the expenses.csv contract).
HOW_DECIDED = {
    SOURCE_STATED: "The invoice states a bank payment",
    SOURCE_SETTLED_OUTSIDE: "Marked paid by bank transfer",
    SOURCE_PERSON: "Moved to Bills by hand",
}


def bill_evidence(receipt, source: str, settled_entry: Mapping | None) -> str:
    """What the bills.csv `Evidence` column says for one bill row."""
    if source == SOURCE_STATED:
        return stated_bank_payment(receipt.payment_mode) or ""
    if source == SOURCE_SETTLED_OUTSIDE:
        return _evidence(str((settled_entry or {}).get("note") or ""))
    return ""
