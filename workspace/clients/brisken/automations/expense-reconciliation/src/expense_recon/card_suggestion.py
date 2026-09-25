"""What a receipt that names no card is waiting for, and which card its
recurring charge suggests (backlog item 204, case 9, steps 1 and 5).

A card-less receipt used to read "No legal entity yet. Assign this expense's
paying card..." whether or not any statement that could name the card was
loaded. Most of the time none was: September 2026 had no statement for the
2838 family, 1176 or 0113, and 9693 covered only to Sep 4. So the row was
asking a person for something the next statement would answer on its own.

Two facts, both read off what is loaded in ANY month, never guessed:

* **Coverage by date.** A card's statement covers a day when an upload that
  printed that card spans the day (the upload's own first and last charge
  date, `statements[].period_start/period_end`). One Chase activity export
  carries every subcard of an account, so an upload that printed one card of
  a family (`Card.parent`) covers the whole family for its span: an August
  2838 export covers 0340 even in a month 0340 did not spend. A receipt dated
  on a day some active card's statements do not cover WAITS for those cards.
* **The recurring charge.** Every loaded charge within 45 days of the receipt
  whose description carries the vendor's first word and whose amount sits
  within 3% of the receipt's. When all of them are on ONE card, that card is
  a SUGGESTION with its evidence. Measured 44 right / 8 wrong as an automatic
  rule (item 204 section 5), so it is never applied: the owner's rulings
  (item 173 "a blank beats a wrong card", D6 "nothing is spread without
  Criss's own click") keep the card empty until a person picks it.

Neither fact re-derives a row's card. Both read `card` / `card_source` off
the resolved row and act only where it is empty.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from .matching.deterministic import _card_keys

WAITS_FOR_STATEMENT = "waits_for_statement"

# Lever E as measured (item 204 section 5): amount within 3% of the receipt,
# charge within 45 days either side.
AMOUNT_BAND = Decimal("0.03")
WINDOW_DAYS = 45
# A first word shorter than this matches too much ("at" for AT&T, "db").
MIN_VENDOR_TOKEN = 3

_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class LoadedCharge:
    """One loaded statement charge, reduced to what the scan reads."""

    card_key: str            # the registry card, "" when the registry cannot name it
    day: date
    amount: Decimal          # absolute, in `currency`
    currency: str
    original_amount: Decimal | None
    original_currency: str
    description: str
    month: str               # "YYYY-MM" of the month page holding it; "" for a trip


@dataclass
class StatementEvidence:
    """Everything the estate has loaded, keyed for the two questions."""

    active: dict[str, str] = field(default_factory=dict)       # key -> label
    periods: dict[str, list[tuple[date, date]]] = field(default_factory=dict)
    charges: list[LoadedCharge] = field(default_factory=list)

    def covers(self, card_key: str, day: date) -> bool:
        return any(a <= day <= b for a, b in self.periods.get(card_key, ()))

    def waits_for(self, day: date | None) -> list[str]:
        """The labels of the active cards whose loaded statements do not
        cover `day`, sorted; empty when every one does (or no date)."""
        if day is None:
            return []
        return sorted(
            label for key, label in self.active.items() if not self.covers(key, day)
        )


class EvidenceSource:
    """The estate's statement evidence, read from the store at most once
    per view and only when a row asks for it (a month with no card-less row
    pays nothing)."""

    def __init__(self, store) -> None:
        self._store = store
        self._value: StatementEvidence | None = None
        self._read = False

    def get(self) -> StatementEvidence | None:
        if not self._read:
            self._read = True
            try:
                self._value = statement_evidence(self._store)
            except Exception:  # noqa: BLE001 - a status line must never break the page
                self._value = None
        return self._value


def statement_evidence(store) -> StatementEvidence:
    """Read every expense batch's loaded statements into one
    `StatementEvidence`. Active cards come from the LIVE registry (what
    Settings defines), because "is this card defined" is the registry's
    question, not a batch snapshot's."""
    from .cards import effective_cards
    from .cards_provision import load_cards
    from .web.service import (
        MODE_EXPENSE_GENERATION,
        _batch_cards,
        _charge_card_identity,
        _printed_by_upload,
        _statement_card_identities,
        is_trip_batch,
        month_statements,
        month_transactions,
    )
    from .batch_period import month_from_label

    live = effective_cards(store.get_settings(), load_cards())
    active = {k: c.display_label for k, c in live.items() if c.active}
    family = _families(live)
    out = StatementEvidence(active=active)
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        statements = month_statements(run)
        if not statements:
            continue
        try:
            transactions = month_transactions(run)
        except Exception:  # noqa: BLE001 - one unreadable month must not hide the rest
            continue
        cards = _batch_cards(run.config)
        ym = None if is_trip_batch(run) else month_from_label(run.label)
        month = f"{ym[0]:04d}-{ym[1]:02d}" if ym else ""
        identity = {tx.transaction_id: _charge_card_identity(tx, cards) for tx in transactions}
        printed = _printed_by_upload(run)
        for entry in statements:
            span = _span(entry)
            if span is None:
                continue
            for ident in _statement_card_identities(entry, printed, identity, cards):
                for key in family.get(ident.card_key, {ident.card_key} - {""}):
                    out.periods.setdefault(key, []).append(span)
        for tx in transactions:
            if tx.is_credit or not tx.transaction_date:
                continue
            out.charges.append(LoadedCharge(
                card_key=identity[tx.transaction_id].card_key,
                day=tx.transaction_date,
                amount=abs(tx.amount),
                currency=(tx.transaction_currency or "").upper(),
                original_amount=(
                    abs(tx.original_amount) if tx.original_amount is not None else None
                ),
                original_currency=(tx.original_currency or "").upper(),
                description=tx.vendor_from_statement or "",
                month=month,
            ))
    return out


def _families(cards: dict) -> dict[str, set[str]]:
    """card key -> every key in its family (the root and all its subcards),
    for cards that have a parent or are one."""
    def root(key: str, seen: frozenset = frozenset()) -> str:
        parent = getattr(cards.get(key), "parent", "") or ""
        if not parent or parent in seen or parent not in cards:
            return key
        return root(parent, seen | {key})

    groups: dict[str, set[str]] = {}
    for key in cards:
        groups.setdefault(root(key), set()).add(key)
    return {k: g for g in groups.values() if len(g) > 1 for k in g}


def _span(entry: dict) -> tuple[date, date] | None:
    try:
        a = date.fromisoformat(str(entry.get("period_start") or ""))
        b = date.fromisoformat(str(entry.get("period_end") or ""))
    except ValueError:
        return None
    return (a, b) if a <= b else None


def is_open_cardless(res: dict, settled_outside: bool) -> bool:
    """A row the case-9 facts speak to: the card chain found no card, it is
    not private (confirmed or suggested by its printed tender), it printed no
    card digits of its own (a printed number that names no card is a
    different problem), and it was not settled outside the card system."""
    return (
        res.get("card") is None
        and not res.get("private")
        and not res.get("suggested_private")
        and not _card_keys(res.get("hint") or "")
        and not settled_outside
    )


def waits_for_row(receipt, res: dict, source, settled_outside: bool) -> list[str]:
    """`waits_for_statements` for one expense row, or [] when it does not
    wait (it has a card, or every active card's statement covers its date,
    or no evidence could be read)."""
    if source is None or not is_open_cardless(res, settled_outside):
        return []
    evidence = source.get()
    if evidence is None:
        return []
    return evidence.waits_for(receipt.detected_date)


def vendor_token(vendor: str) -> str:
    """The vendor's first word, lowercased, or "" when it is too short to
    tell one merchant from another."""
    words = _TOKEN.findall((vendor or "").casefold())
    return words[0] if words and len(words[0]) >= MIN_VENDOR_TOKEN else ""


def _amount_for(charge: LoadedCharge, currency: str) -> Decimal | None:
    if charge.currency == currency:
        return charge.amount
    if charge.original_amount is not None and charge.original_currency == currency:
        return charge.original_amount
    return None


def suggest_card(receipt, vendor: str, evidence: StatementEvidence | None) -> dict | None:
    """The recurring-charge suggestion for a card-less receipt, or None.

    Every loaded charge within `WINDOW_DAYS` of the receipt whose
    description carries the vendor's first word and whose amount, in the
    receipt's currency, is within `AMOUNT_BAND` of the receipt's. All of
    them on ONE registry card (none unnamed) -> that card, with the charges
    as its evidence. Anything else -> None."""
    if evidence is None:
        return None
    token = vendor_token(vendor)
    day, total = receipt.detected_date, receipt.detected_total
    currency = (receipt.detected_currency or "").upper()
    if not token or day is None or total is None or not currency or total == 0:
        return None
    total = abs(Decimal(total))
    window = timedelta(days=WINDOW_DAYS)
    hits: list[LoadedCharge] = []
    for charge in evidence.charges:
        if abs(charge.day - day) > window:
            continue
        # Joined without separators, so "NETWORKSOLUTIONS" carries "network"
        # as well as "NETWORK SOLUTIONS" does.
        if token not in "".join(_TOKEN.findall(charge.description.casefold())):
            continue
        amount = _amount_for(charge, currency)
        if amount is None or abs(amount - total) > total * AMOUNT_BAND:
            continue
        hits.append(charge)
    cards = {c.card_key for c in hits}
    if not hits or len(cards) != 1 or "" in cards:
        return None
    (key,) = cards
    hits.sort(key=lambda c: c.day)
    return {
        "card_key": key,
        "label": evidence.active.get(key, key),
        "evidence": [
            {
                "month": c.month,
                "date": c.day.isoformat(),
                "amount": f"{_amount_for(c, currency):.2f}",
                "currency": currency,
                "description": c.description,
            }
            for c in hits
        ],
    }


def case9_row_fields(
    receipt, res: dict, vendor: str, source, settled_outside: bool,
    *, copy: bool = False,
) -> dict:
    """The parallel fields an expense row gains (absent, never null):
    `waits_for_statements` when an open card-less row's date is not covered,
    `card_suggestion` when its recurring charge names one card. A decided
    copy (out of the totals) keeps its waiting status but is never offered a
    card: a click there would write an override on a row that counts for
    nothing, and the row it repeats carries the same suggestion."""
    if source is None or not is_open_cardless(res, settled_outside):
        return {}
    evidence = source.get()
    if evidence is None:
        return {}
    out: dict = {}
    waits = evidence.waits_for(receipt.detected_date)
    if waits:
        out["waits_for_statements"] = waits
    if copy:
        return out
    suggestion = suggest_card(receipt, vendor, evidence)
    if suggestion is not None:
        out["card_suggestion"] = suggestion
    return out


def uncovered_for_receipt(receipt, source) -> list[str]:
    """For the run payload's unmatched list: the active cards whose loaded
    statements do not cover this receipt's date, when it printed no card
    digits; [] otherwise. `receipt_reason_code` reads it."""
    if source is None or _card_keys(receipt.payment_mode or ""):
        return []
    evidence = source.get()
    if evidence is None:
        return []
    return evidence.waits_for(receipt.detected_date)


def reason_coverage(receipt, source, card_key: str | None = None) -> dict | None:
    """What the loaded statements say about one unmatched receipt's date,
    for `unmatched_reasons.receipt_reason_code` (item 220). None when there
    is no evidence, or when the receipt printed card digits that the card
    chain could not resolve to a registry card (the reason then keeps its
    date-first order: August's two Google invoices print account numbers,
    not cards).

    `card_key` is the card the chain resolved for the row (printed, picked,
    assigned, remembered or lent by a settled charge). With one, only THAT
    card's statements decide; without one, every active card's do, the same
    set `waits_for_statements` reads on the Expenses tab.

    {"cards": [registry keys asked], "waits_for": [labels of those whose
    statements do not cover the date], "never_loaded": [the subset of
    `waits_for` with no statement loaded in any month]}."""
    if source is None:
        return None
    if not card_key and _card_keys(receipt.payment_mode or ""):
        return None
    evidence = source.get()
    if evidence is None:
        return None
    day = receipt.detected_date
    if card_key:
        cards = [card_key]
        labels = {card_key: evidence.active.get(card_key, card_key)}
    else:
        cards = sorted(evidence.active)
        labels = dict(evidence.active)
    waits = [] if day is None else [k for k in cards if not evidence.covers(k, day)]
    return {
        "cards": cards,
        "waits_for": sorted(labels[k] for k in waits),
        "never_loaded": sorted(labels[k] for k in waits if not evidence.periods.get(k)),
    }


def attached_month(run) -> str:
    """"YYYY-MM" of a company month's label, "" for a trip or a label that
    names no month."""
    from .batch_period import month_from_label
    from .web.service import is_trip_batch

    if is_trip_batch(run):
        return ""
    ym = month_from_label(run.label)
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else ""


def month_suggestion(transactions: list, attached_month: str = "") -> dict | None:
    """The month holding most of an upload's dated charges, in the receipt
    side's `period_suggestion` shape: {month, label_month, n_dates,
    n_in_month}. None when the file dated nothing or two months tie (no
    clear month to suggest). `label_month` is the month the file is being
    attached to ("YYYY-MM"), None when that is not a month (a trip)."""
    counts: dict[tuple[int, int], int] = {}
    for t in transactions:
        d = getattr(t, "transaction_date", None)
        if d:
            counts[(d.year, d.month)] = counts.get((d.year, d.month), 0) + 1
    if not counts:
        return None
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    (y, m), n = ranked[0]
    return {
        "month": f"{y:04d}-{m:02d}",
        "label_month": attached_month or None,
        "n_dates": sum(counts.values()),
        "n_in_month": n,
    }


def card_by_vendor_targets(expenses: list[dict], vendor: str) -> list[str]:
    """The rows `POST .../cards/by-vendor` writes: every row of the display
    vendor `vendor` (trimmed, case-insensitive) that has no card, is not
    private or suggested private, printed no card digits, was not settled
    outside, and counts (a decided copy does not). Read off the RESOLVED
    rows, so a printed, picked, learned or statement card is never touched."""
    want = (vendor or "").strip().casefold()
    if not want:
        return []
    out = []
    for e in expenses:
        display = str((e.get("vendor") or {}).get("display") or "").strip().casefold()
        if display != want:
            continue
        if (
            e.get("card") is not None
            or e.get("card_source", "none") != "none"
            or e.get("private")
            or e.get("suggested_private")
            or _card_keys(e.get("payment_hint") or "")
            or "settled_outside" in e
            or e.get("payment_path") == "bill"  # Build 4 / item 218: no card
            or e.get("counts_in_total") is False
        ):
            continue
        out.append(str(e.get("document_id")))
    return out
