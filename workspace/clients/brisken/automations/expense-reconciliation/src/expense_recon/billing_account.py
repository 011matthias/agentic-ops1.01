"""The card a billing account has always been paid with (backlog item 204,
step 4; owner decision D4, 2026-09-25).

A subscription invoice carries a Stripe-shaped number: an 8-character
customer prefix and a counter (`WWT1PNYP-0016`). The prefix is the billing
ACCOUNT, one login paying with one card at a time, which is what splits the
vendors that are paid on several cards (Anthropic is four accounts on four
cards). Keyed on the vendor NAME instead (item 200, not built) the same
memory gave the wrong person 3 times in 21, because grocery and restaurant
receipts carry no account and several people share the same shops.

The rule, measured leave-one-out over 64 checkable receipts at 34 right,
0 wrong, 30 silent:

* **Key.** From `invoice_number`, else the receipt's reference, matching
  `^[A-Z0-9]{8}[- ]?\\d{4}$` with a prefix that is not all digits. A Stripe
  receipt number (`2642-9215-3921`) is all digits and never a key; a POS or
  grocery receipt has no key at all, so it is out by construction.
* **Evidence, per PURCHASE.** Copies of one purchase (the invoice and its
  receipt carry the same invoice number) count once, and a decided copy
  (`counts_in_total: false`) never counts. A printed Brisken card number, a
  statement charge that settles the receipt and a reviewer's pick COUNT. A
  two-digit ending and a hint word assigned to a card may CONTRADICT but
  never count. A remembered card, a merchant card, this rule's own answer,
  a confirmed private row and a row settled outside the card system are no
  evidence at all.
* **Decision.** At least 2 purchases of the account on one card and none on
  any other card, across every company batch, derived on every read and
  never stored (the 2026-09-24 ruling: only corrections are memorized). The
  purchase being judged is left out of its own evidence.

The chain (`web.service.resolve_batch_row_cards`) asks this last among the
decisions about the row itself: after a pick, a printed number and the
settling charge, before a remembered card and the merchant registry. So a
pick stays on its own row (D6): one pick is one purchase of evidence, which
decides nothing.

The index is built from the store, so it is scoped to one request: the app
sets a lazy scope per request (`request_scope`) and each surface that
resolves the chain with live settings passes `request_account_cards()`.
Nothing is read until a row that carries an account key and no card reaches
the link, and then the index is built once for the whole request.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:  # pragma: no cover
    from .matching.types import Receipt
    from .web.store import RunStore

log = logging.getLogger(__name__)

# The Stripe customer prefix plus the invoice counter, with or without the
# separator the invoice prints ("WWT1PNYP-0016"; the reference field stores
# "HMVWDWIL0023").
ACCOUNT_KEY_RE = re.compile(r"^([A-Z0-9]{8})[- ]?(\d{4})$")

# Owner D4: two purchases on one card, none on another.
MIN_PURCHASES = 2

# The card sources that carry evidence at all. `hint` is split further by
# `row_evidence`: a printed number counts, an alias or a two-digit ending
# may only contradict.
_EVIDENCE_SOURCES = frozenset({"override", "settled_charge", "hint"})

# A batch whose label starts with one of these is a test fixture, never
# company spend (repo convention: fixtures are namespaced `TEST -` / `UTIL -`).
_FIXTURE_PREFIXES = ("TEST", "UTIL")

# purchase id -> (cards the purchase counts for, cards it only names)
Purchases = dict[str, tuple[frozenset[str], frozenset[str]]]
# account -> purchases
AccountIndex = dict[str, Purchases]


def account_key(receipt: "Receipt") -> tuple[str, str] | None:
    """`(account, purchase)` for a receipt, or None when it carries no
    billing-account number. The purchase is the account plus the counter, so
    an invoice and its receipt name the same purchase."""
    for raw in (
        getattr(receipt, "invoice_number", None),
        getattr(receipt, "detected_reference", None),
    ):
        m = ACCOUNT_KEY_RE.match(str(raw or "").strip())
        if m and not m.group(1).isdigit():
            return m.group(1), m.group(1) + m.group(2)
    return None


def row_evidence(res: dict, hints_map: dict | None) -> tuple[str, bool] | None:
    """`(card key, counts)` for one row's card resolution, or None when the
    row says nothing about its card.

    `counts` is True for a reviewer's pick, the settling charge and a card
    number the receipt printed. A hint the batch assigned to a card by its
    exact words, and a card named only by a two-digit ending, name a card but
    do not count: they can contradict an account's card, never establish it.
    """
    card = res.get("card")
    source = res.get("card_source")
    if card is None or source not in _EVIDENCE_SOURCES:
        return None
    if res.get("private") or res.get("settled_off_card"):
        return None
    key = str(getattr(card, "key", "") or "").strip()
    if not key:
        return None
    if source in ("override", "settled_charge"):
        return key, True
    from .matching.deterministic import _card_keys

    hint = str(res.get("hint") or "").strip()
    # A number of the card, printed: not a two-digit ending (`_card_keys`
    # already reads no 3+ digit run in one; the flag keeps that true if the
    # ending grammar ever widens), not the batch's word-for-word assignment.
    by_number = bool(_card_keys(hint) & card.digit_keys())
    alias = bool((hints_map or {}).get(hint))
    printed = by_number and not alias and not res.get("card_ending")
    return key, printed


def decide(purchases: Purchases | None, own_purchase: str) -> str | None:
    """The card an account's OTHER purchases agree on, or None.

    None unless every purchase except `own_purchase` that names a card names
    the same one, and at least `MIN_PURCHASES` of them count for it."""
    named: set[str] = set()
    support: Counter[str] = Counter()
    for purchase, (counts, names) in (purchases or {}).items():
        if purchase == own_purchase:
            continue
        named |= counts | names
        support.update(counts)
    if len(named) != 1:
        return None
    (key,) = named
    return key if support[key] >= MIN_PURCHASES else None


def _add(index: AccountIndex, account: str, purchase: str, key: str, counts: bool) -> None:
    per = index.setdefault(account, {})
    old_counts, old_names = per.get(purchase, (frozenset(), frozenset()))
    if counts:
        per[purchase] = (old_counts | {key}, old_names)
    else:
        per[purchase] = (old_counts, old_names | {key})


def month_evidence(
    run,
    *,
    field_overrides: dict[str, dict[str, str]],
    edits: list[dict],
    decisions: dict | None,
    resolutions: dict[str, str] | None,
) -> list[tuple[str, str, str, bool]]:
    """`[(account, purchase, card key, counts)]` for one batch.

    The rows are the grid's own receipts with the reviewer's edits applied
    and the grid's twin inheritance (`inherit_card_from_copies`), resolved
    by the card chain WITHOUT any memory (no remembered card, no merchant
    map, no account index), with the charge that settles each one and the
    month's settled-outside dispositions, exactly as the grid reads them.

    A decided copy is not a purchase of its own, but what it prints is the
    purchase's evidence: live, a Stripe invoice is the kept document and
    its receipt, the decided copy, is the one that prints the card
    (September's `HMVWDWIL-0033` / `Receipt-2253-2007-8117`). So every copy
    reports under the purchase of the document it repeats, and the purchase
    is keyed by whichever member carries an account number. Dropping the
    copies instead left only August's three 2838 picks for `HMVWDWIL` and
    lent May's Lovable invoice a card the account's other cards contradict
    (v237, 2026-09-25)."""
    from .web.service import (
        _batch_card_hints,
        apply_expense_edits,
        baseline_receipts,
        decided_copies,
        duplicate_decisions,
        export_settled_cards,
        inherit_card_from_copies,
        resolve_batch_row_cards,
        settled_outside_map,
    )

    default_entity = (
        ((run.config or {}).get("expense") or {}).get("legal_entity_id", "")
    )
    receipts = apply_expense_edits(
        baseline_receipts(run), field_overrides, edits,
        default_entity=default_entity,
    )
    if not any(account_key(r) for r in receipts):
        return []
    hints_map = _batch_card_hints(run.config)
    receipts = inherit_card_from_copies(
        receipts, resolutions, hints_map,
        duplicate_decisions(run, receipts, resolutions),
    )
    copies = decided_copies(
        run, receipts, resolutions, charge_decisions=decisions,
    )
    # document -> the document it repeats (itself when it is no copy), and
    # each such group's account: the key any member carries, none when two
    # members name different accounts.
    root_of = {r.document_id: copies.get(r.document_id, r.document_id) for r in receipts}
    group_key: dict[str, tuple[str, str] | None] = {}
    for r in receipts:
        key = account_key(r)
        if key is None:
            continue
        root = root_of[r.document_id]
        if root not in group_key:
            group_key[root] = key
        elif group_key[root] is not None and group_key[root] != key:
            group_key[root] = None
    res_by_doc = resolve_batch_row_cards(
        receipts, run.config, field_overrides,
        settled_cards=export_settled_cards(run, decisions),
        settled_outside=settled_outside_map(run.snapshot or {}),
    )
    out: list[tuple[str, str, str, bool]] = []
    for r in receipts:
        key = group_key.get(root_of[r.document_id])
        if key is None:
            continue
        evidence = row_evidence(res_by_doc.get(r.document_id) or {}, hints_map)
        if evidence is not None:
            out.append((key[0], key[1], evidence[0], evidence[1]))
    return out


def build_account_index(store: "RunStore") -> AccountIndex:
    """Every billing account's evidence across the store's expense batches,
    months and trips alike, test fixtures left out.

    A batch whose evidence cannot be read empties the WHOLE index: evidence
    missing from one month can hide the card that contradicts another
    month's, and a partial index decides exactly where it should not (a
    blank beats a wrong card, item 173). The link is silent until it reads."""
    from .web.service import MODE_EXPENSE_GENERATION

    index: AccountIndex = {}
    for run in store.list_runs():
        if (run.config or {}).get("mode") != MODE_EXPENSE_GENERATION:
            continue
        if str(run.label or "").strip().upper().startswith(_FIXTURE_PREFIXES):
            continue
        try:
            rows = month_evidence(
                run,
                field_overrides=store.get_expense_field_overrides(run.run_id),
                edits=store.get_expense_edits(run.run_id),
                decisions=store.get_decisions(run.run_id),
                resolutions=store.get_duplicate_resolutions(run.run_id),
            )
        except Exception:  # noqa: BLE001 - the link goes silent, never the page
            log.warning("billing-account index empty: %s unreadable", run.run_id,
                        exc_info=True)
            return {}
        for account, purchase, key, counts in rows:
            _add(index, account, purchase, key, counts)
    return index


class AccountCards:
    """The account index as the card chain reads it: `card_for(receipt)`.

    Lazy: built from `factory` the first time a receipt that carries an
    account key asks, and only once. A factory that fails leaves the link
    silent for the rest of the request rather than failing the page."""

    def __init__(self, factory: Callable[[], AccountIndex]):
        self._factory = factory
        self._index: AccountIndex | None = None
        self._built = False

    @classmethod
    def of(cls, index: AccountIndex) -> "AccountCards":
        """An already-built index (tests, tools)."""
        return cls(lambda: index)

    def index(self) -> AccountIndex:
        if not self._built:
            # Set before building, so a surface the build itself resolves
            # through reads an empty link instead of recursing.
            self._built = True
            try:
                self._index = self._factory() or {}
            except Exception:  # noqa: BLE001 - the link fails silent, never the page
                log.warning("billing-account index unavailable", exc_info=True)
                self._index = {}
        return self._index or {}

    def card_for(self, receipt: "Receipt") -> str | None:
        """The card key this receipt's billing account has always been paid
        with, or None."""
        key = account_key(receipt)
        if key is None:
            return None
        return decide(self.index().get(key[0]), key[1])


_SCOPE: ContextVar[AccountCards | None] = ContextVar(
    "billing_account_scope", default=None
)


@contextmanager
def request_scope(factory: Callable[[], AccountIndex]) -> Iterator[AccountCards]:
    """One request's lazy index. The app enters it per request, so every
    surface of one request reads one index and nothing is shared between
    requests."""
    scope = AccountCards(factory)
    token = _SCOPE.set(scope)
    try:
        yield scope
    finally:
        _SCOPE.reset(token)


def request_account_cards() -> AccountCards | None:
    """The current request's account cards, or None outside a request (a
    caller with no store in hand behaves as before this rule existed)."""
    return _SCOPE.get()
