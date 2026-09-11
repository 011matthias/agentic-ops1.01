"""Month health: the structural check readiness cannot answer on its own.

`ready_to_post` used to be `n_undecided == 0`. On 2026-09-10 August 2026
was uploaded with every purchase printed negative; the matcher saw 111
credits and no purchases, proposed nothing, and the month reported
``ready_to_post: true`` with 0 of 111 matched and 31 receipts in the pool,
four of them the same amount on the same day as a charge. Nothing was
undecided because nothing had been proposed. A month the matcher could
not see at all read as finished.

The rule here is the one a reviewer applies by eye: if the pool holds
receipts that are the same amount on the same day as a charge and the
matcher still proposed nothing, the inputs are broken, not the month. It
names WHICH input, from the scoping rule that dropped each pair:

* ``sign``     - the charge is a credit (canonical purchases are positive);
                 a workbook whose sign was never canonicalized.
* ``currency`` - the receipt and the charge post in different currencies
                 (same number, different money).
* ``entity``   - both name a legal entity and they differ.
* ``card``     - the receipt's payment mode names a card that is on the
                 statement but is not this charge's card.
* ``unknown``  - the pair looks pairable and was still not proposed.

It only ever REFUSES readiness. A healthy month is judged by the reviewer's
decisions exactly as before, and a month with no statement, no receipts, or
no exact pair is not this rule's business (``checked: false`` or ``ok``).
"""
from __future__ import annotations

from datetime import date, timedelta

from ..matching.deterministic import _card_keys, _tx_card_keys
from ..matching.types import MatchOutcome, Receipt, Transaction

HEALTH_OK = "ok"
HEALTH_BROKEN = "broken"

REASON_ZERO_MATCH_WITH_EXACT_PAIRS = "zero_match_with_exact_pairs"

SUSPECT_SIGN = "sign"
SUSPECT_CURRENCY = "currency"
SUSPECT_ENTITY = "entity"
SUSPECT_CARD = "card"
SUSPECT_UNKNOWN = "unknown"

# Fixed order, so the sentence and the list read the same way every time.
_SUSPECT_ORDER = (
    SUSPECT_SIGN, SUSPECT_CURRENCY, SUSPECT_ENTITY, SUSPECT_CARD, SUSPECT_UNKNOWN,
)

_SUSPECT_TEXT = {
    SUSPECT_SIGN: "the statement's sign (purchases arrived as credits)",
    SUSPECT_CURRENCY: "the currency (same amounts in different currencies)",
    SUSPECT_ENTITY: "the legal entity (receipts and charges name different entities)",
    SUSPECT_CARD: "the card scoping (receipts name a different card than the charge)",
    SUSPECT_UNKNOWN: "something the tool cannot name",
}


def unchecked() -> dict:
    """The field's shape on a month this rule has nothing to say about."""
    return {
        "checked": False,
        "state": HEALTH_OK,
        "reason": None,
        "n_exact_pairs": 0,
        "suspects": [],
        "detail": None,
    }


def exact_pairs(
    transactions: list[Transaction],
    receipts: list[Receipt],
    *,
    window_days: int = 1,
    card_scoping: bool = True,
) -> list[dict]:
    """Every (charge, receipt) pair with the same absolute amount within
    ``window_days`` of the charge date, with the blockers the matcher's own
    scoping rules would apply to it. Amount and date are compared exactly
    as the deterministic exact tier does (absolute amount equal, date within
    the exact window); everything else is a reason the pair was dropped.
    """
    present_keys: set[str] = set()
    tx_keys: dict[str, set[str]] = {}
    for tx in transactions:
        keys = _tx_card_keys(tx)
        tx_keys[tx.transaction_id] = keys
        present_keys |= keys

    window = timedelta(days=window_days)
    out: list[dict] = []
    for tx in transactions:
        amount = abs(tx.amount)
        tx_date = tx.transaction_date
        if not isinstance(tx_date, date):
            continue
        for r in receipts:
            if r.detected_total is None or r.detected_date is None:
                continue
            if abs(r.detected_total) != amount:
                continue
            if abs(r.detected_date - tx_date) > window:
                continue
            blockers: list[str] = []
            if tx.is_credit or tx.amount < 0:
                blockers.append(SUSPECT_SIGN)
            tx_ccy = (tx.transaction_currency or "").upper()
            r_ccy = (r.detected_currency or "").upper()
            if tx_ccy and r_ccy and tx_ccy != r_ccy:
                blockers.append(SUSPECT_CURRENCY)
            if (
                r.legal_entity_id
                and tx.legal_entity_id
                and r.legal_entity_id != tx.legal_entity_id
            ):
                blockers.append(SUSPECT_ENTITY)
            if card_scoping:
                pm_keys = _card_keys(r.payment_mode)
                if (
                    pm_keys
                    and pm_keys & present_keys
                    and not (pm_keys & tx_keys[tx.transaction_id])
                ):
                    blockers.append(SUSPECT_CARD)
            out.append({
                "transaction_id": tx.transaction_id,
                "document_id": r.document_id,
                "blockers": blockers,
            })
    return out


def n_proposed(outcome: MatchOutcome) -> int:
    """How many charges the matcher put a receipt beside, in any tier."""
    return (
        len(outcome.matches)
        + len(outcome.judgment_required)
        + len(outcome.ambiguous)
    )


def month_health(
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    *,
    window_days: int = 1,
    card_scoping: bool = True,
) -> dict:
    """The verdict for one month, as both review payloads carry it.

    ``broken`` exactly when the matcher proposed nothing for any charge and
    at least one exact same-day same-amount pair sits in the pool. Every
    such pair was dropped by a scoping rule or never scored, so the
    blockers found across the pairs are the suspects; a pair with no
    identifiable blocker names ``unknown`` rather than nothing.
    """
    if not transactions or not receipts:
        return unchecked()
    pairs = exact_pairs(
        transactions, receipts,
        window_days=window_days, card_scoping=card_scoping,
    )
    base = {
        "checked": True,
        "state": HEALTH_OK,
        "reason": None,
        "n_exact_pairs": len(pairs),
        "suspects": [],
        "detail": None,
    }
    if not pairs or n_proposed(outcome) > 0:
        return base
    found: set[str] = set()
    for p in pairs:
        if p["blockers"]:
            found.update(p["blockers"])
        else:
            found.add(SUSPECT_UNKNOWN)
    suspects = [s for s in _SUSPECT_ORDER if s in found]
    n = len(pairs)
    named = "; ".join(_SUSPECT_TEXT[s] for s in suspects)
    detail = (
        f"The matcher proposed nothing for this month, yet {n} receipt"
        f"{'s' if n != 1 else ''} in the pool "
        f"{'are' if n != 1 else 'is'} the same amount on the same day as a "
        f"charge. Something in the inputs is broken: {named}. Fix that and "
        "re-read the statement before posting anything."
    )
    return {
        **base,
        "state": HEALTH_BROKEN,
        "reason": REASON_ZERO_MATCH_WITH_EXACT_PAIRS,
        "suspects": suspects,
        "detail": detail,
    }


def card_scoping_on(cfg: dict | None) -> bool:
    """Whether the run's matching config keeps card scoping on (default)."""
    matching = (cfg or {}).get("matching") or {}
    value = matching.get("card_scoping", True)
    return bool(value) if value is not None else True
