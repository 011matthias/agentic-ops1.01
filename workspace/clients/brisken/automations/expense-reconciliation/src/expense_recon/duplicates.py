"""Duplicate / double-charge detection (Tier-1 #4).

Two deterministic passes that FLAG, never drop:

* ``find_duplicate_charges`` - statement transactions that look like the
  same charge billed twice: identical normalized merchant + exact amount
  + currency, within a short date window of each other (a re-swipe, a
  double-post, an auth that settled twice).
* ``find_duplicate_receipts`` - the same receipt uploaded more than once:
  identical normalized merchant + date + total + currency across two or
  more distinct document ids.

Both are advisory. They return id groups for the reviewer to confirm and
change nothing about the reconciliation, so they cannot break the
reconciliation guarantee. Pure functions; no LLM, no I/O.

One consumer does act on a receipt group: ``collapsed_duplicate_copies``
(item 56, owner ruling 2026-09-11) names the copies a re-match keeps OUT of
the candidate pool, so an invoice and its receipt stop presenting as two
indistinguishable candidates for one charge. It still drops nothing: every
copy stays in the snapshot, the counts and the exports.

A second receipt key (item 69 round A, 2026-09-15): one purchase is one
candidate BY ITS NUMBER. ``find_duplicate_receipts_by_reference`` groups
receipts whose normalized document reference + total + currency agree,
whatever the vendor spelling or the printed date, because the copies that
escaped the vendor/date key are exactly those: a Stripe invoice PDF and
its receipt PDF print the vendor differently ("Anthropic, PBC" vs
"Anthropic, PBC (@anthropic)"), a re-mailed body carries the mail's date.
``find_duplicate_receipt_groups`` lists both kinds with their basis, and
``inherit_card_from_copies`` lets the kept copy borrow the card its copy
names, so it stays inside that card's statement scope instead of binding a
stranger's charge of the same amount.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import replace
from datetime import date

from .matching.deterministic import _card_keys
from .matching.types import Receipt, Transaction

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_NON_ALNUM_UPPER = re.compile(r"[^A-Z0-9]+")
_NON_DIGIT = re.compile(r"\D+")
_MIN_DATE = date.min
# A reference shorter than this is a till counter ("4563", "1514") that
# repeats across unrelated receipts; only a longer one identifies a document.
_MIN_REFERENCE_LEN = 5
# Digit-only "references" that are really the receipt's own date, in the
# layouts extractors print them (measured on the live months, 2026-09-15).
_DATE_LAYOUTS = ("%Y%m%d", "%d%m%Y", "%m%d%Y", "%y%m%d", "%d%m%y", "%m%d%y")

REFERENCE_BASIS = "reference"


def duplicate_group_id(kind: str, member_ids: list[str]) -> str:
    """A stable, content-derived id for one duplicate group (§18).

    The id is a hash of the group's KIND (`charge` / `receipt`) plus its
    sorted member ids, so the same group yields the same id across
    re-renders of a run (the reviewer's resolution keyed on it survives a
    reload). Membership-order-independent; kind-scoped so a charge group and
    a receipt group that happen to share ids never collide.
    """
    payload = f"{kind}:" + "|".join(sorted(member_ids))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def duplicate_row_flags(groups: list[dict], *, kind: str) -> dict[str, dict]:
    """What each ROW has to say about the duplicate group it belongs to.

    The detector has flagged duplicates since Tier-1 #4, but only into a
    side list of id groups. A reviewer reading a 40-row grid has no way to
    see that rows 39 and 40 are the same invoice unless they cross-check a
    panel against document ids, so in practice the flag was found by
    whoever happened to notice the amount twice. This turns the group into
    something a row can carry.

    Keyed by member id, for the given `kind` only: a charge group and a
    receipt group can hold the same id string without it meaning the same
    thing, and one merged map would put a receipt's verdict on a charge.
    Each entry:

    * ``group_id`` - the group's stable id, so a row can post a resolution
    * ``kind``, ``n_copies`` - what it is, and how many there are
    * ``copy`` - this row's 1-based place in the group
    * ``of`` - the FIRST member's id: the copy the others repeat
    * ``is_extra`` - true for every copy after the first, which is exactly
      the population that inflates a count or a total

    A group the reviewer dismissed (``resolution == "ignore"``) yields
    nothing: they have ruled it is not a duplicate, and a marker that
    outlives the ruling is a marker nobody trusts. A ``confirmed`` group
    keeps its marker, because acknowledging a duplicate is not removing it.

    A document can sit in two live groups since the reference key (item 69
    round A): a vendor/date pair and a reference pair with overlapping but
    different membership. One row carries ONE marker, chosen
    deterministically: the group in which the row is an EXTRA copy wins
    over one in which it is the first copy, so the marker never hides a
    collapse (``collapsed_duplicate_copies`` keeps every extra copy out of
    the pool); between two groups of the same standing, the first listed
    wins, and the list order is itself deterministic (vendor/date groups
    first, then reference groups, each sorted).
    """
    flags: dict[str, dict] = {}
    for group in groups:
        if group.get("kind") != kind or group.get("resolution") == "ignore":
            continue
        members = [m for m in (group.get("members") or []) if m]
        if len(members) < 2:
            continue
        for i, member in enumerate(members, start=1):
            flag = {
                "group_id": group.get("group_id") or "",
                "kind": kind,
                "n_copies": len(members),
                "copy": i,
                "of": members[0],
                "is_extra": i > 1,
                "resolution": group.get("resolution"),
            }
            prev = flags.get(member)
            if prev is None or (flag["is_extra"] and not prev["is_extra"]):
                flags[member] = flag
    return flags


def n_extra_copies(flags: dict[str, dict]) -> int:
    """How many rows are redundant copies: the number that answers "is my
    count inflated, and by how much".

    Deliberately a different question from ``n_duplicate_groups`` (how many
    duplicate SITUATIONS there are), and named for the one it answers. One
    count doing both jobs is how ``n_categorized`` came to mean two things
    on 2026-08-22.
    """
    return sum(1 for f in flags.values() if f.get("is_extra"))


def _norm_vendor(v: str | None) -> str:
    return _NON_ALNUM.sub(" ", (v or "").lower()).strip()


def _date_gap(a: date | None, b: date | None) -> int | None:
    if a is None or b is None:
        return None
    return abs((a - b).days)


def find_duplicate_charges(
    transactions: list[Transaction], *, window_days: int = 3
) -> list[list[str]]:
    """Group transaction ids that look like the same charge billed more
    than once.

    A bucket is (normalized merchant, exact amount, currency). Within a
    bucket, transactions are clustered by date proximity; only entries
    within ``window_days`` of an adjacent one join a cluster, so the same
    merchant + amount months apart (a legitimate recurring charge) does
    NOT flag. Each returned group has 2+ ids. A transaction with no
    amount is skipped (cannot be compared). Order is deterministic.
    """
    buckets: dict[tuple, list[Transaction]] = defaultdict(list)
    for tx in transactions:
        if tx.amount is None:
            continue
        key = (
            _norm_vendor(tx.vendor_from_statement),
            str(tx.amount),
            tx.transaction_currency,
        )
        buckets[key].append(tx)

    groups: list[list[str]] = []
    for txs in buckets.values():
        if len(txs) < 2:
            continue
        txs_sorted = sorted(
            txs,
            key=lambda t: (t.transaction_date is None, t.transaction_date or _MIN_DATE),
        )
        cluster = [txs_sorted[0]]
        for prev, cur in zip(txs_sorted, txs_sorted[1:]):
            gap = _date_gap(prev.transaction_date, cur.transaction_date)
            if gap is not None and gap <= window_days:
                cluster.append(cur)
            else:
                if len(cluster) >= 2:
                    groups.append([t.transaction_id for t in cluster])
                cluster = [cur]
        if len(cluster) >= 2:
            groups.append([t.transaction_id for t in cluster])

    groups.sort()
    return groups


def find_duplicate_receipts(receipts: list[Receipt]) -> list[list[str]]:
    """Group document ids of receipts that look like the same receipt
    uploaded more than once: identical normalized merchant + date + total
    + currency. Each group has 2+ distinct document ids. Receipts missing
    a total or date are skipped. Order is deterministic.
    """
    buckets: dict[tuple, list[str]] = defaultdict(list)
    for r in receipts:
        if r.detected_total is None or r.detected_date is None:
            continue
        key = (
            _norm_vendor(r.detected_vendor),
            r.detected_date.isoformat(),
            str(r.detected_total),
            r.detected_currency or "",
        )
        buckets[key].append(r.document_id)

    groups = [sorted(set(ids)) for ids in buckets.values() if len(set(ids)) >= 2]
    groups.sort()
    return groups


def reference_key(receipt: Receipt) -> str | None:
    """The normalized document reference a receipt can be twinned on, or
    None when the field holds nothing that identifies a document.

    Upper-cased alphanumerics of ``detected_reference`` ("H0LHY2WQ-0032" and
    "H0LHY2WQ0032" are one key), at least ``_MIN_REFERENCE_LEN`` characters.
    Measured on the live months (2026-09-15) the extractor puts three kinds
    of thing in the field: a real invoice / receipt number (most rows), a
    short till counter ("4563", "1514": repeats across receipts, too short
    to trust, hence the floor), and a digit string that is only the
    receipt's own date or total printed again. The last kind is excluded
    here, because two unrelated receipts for the same amount on the same
    day would otherwise twin on it: a digit-only reference equal to the
    receipt's date in any of ``_DATE_LAYOUTS``, or to the digits of its
    total (with or without the cents), is no reference.
    """
    ref = _NON_ALNUM_UPPER.sub("", (receipt.detected_reference or "").upper())
    if not ref.isdigit():
        return ref if len(ref) >= _MIN_REFERENCE_LEN else None
    # A digit-only reference is measured without its leading zeros: a till
    # counter printed padded ("00144", "00184" on the 01-06-2025 bundle) is
    # still the counter "144", under the floor, not a five-digit number.
    if len(ref.lstrip("0")) < _MIN_REFERENCE_LEN:
        return None
    d = receipt.detected_date
    if d is not None and ref in {d.strftime(layout) for layout in _DATE_LAYOUTS}:
        return None
    total = receipt.detected_total
    if total is not None:
        as_printed = {
            _NON_DIGIT.sub("", f"{total:f}"),
            _NON_DIGIT.sub("", f"{total:.2f}"),
            _NON_DIGIT.sub("", str(int(total))),
        }
        if ref in as_printed:
            return None
    return ref


def find_duplicate_receipts_by_reference(receipts: list[Receipt]) -> list[list[str]]:
    """Group document ids of receipts that are copies of ONE document by its
    number: identical ``reference_key`` + total + currency (upper-cased),
    whatever the vendor spelling or the printed date. Each group has 2+
    distinct document ids, sorted; receipts with no usable reference or no
    total are skipped. Order is deterministic.

    Item 69 round A (2026-09-15). The vendor/date key of
    ``find_duplicate_receipts`` misses the copies that matter most: a Stripe
    invoice PDF and its receipt PDF for one purchase print the vendor
    differently, and a re-mailed copy of an invoice carries the mail's date.
    Both copies then stay in the pool, and the copy that names no card binds
    a stranger's charge of the same amount (August 2026: the Lovable 50
    invoice took BASE44 50.00; an Anthropic 51.38 invoice took ANTHROPIC
    51.16 while its receipt copy held the real 51.38 charge).
    """
    keys = reference_keys(receipts)
    buckets: dict[tuple, list[str]] = defaultdict(list)
    for r in receipts:
        ref = keys.get(r.document_id)
        if ref is None or r.detected_total is None:
            continue
        key = (ref, str(r.detected_total), (r.detected_currency or "").upper())
        buckets[key].append(r.document_id)

    groups = [sorted(set(ids)) for ids in buckets.values() if len(set(ids)) >= 2]
    groups.sort()
    return groups


def reference_keys(receipts: list[Receipt]) -> dict[str, str]:
    """``document_id -> reference_key`` over ONE list, with the account ids
    taken out: a normalized reference that appears on two or more receipts
    of the list with DIFFERENT totals is not a document number, and no
    receipt carrying it gets a key.

    The per-receipt rule cannot see this; only the list can. July 2026
    carries Anthropic's account id ``NQTJA4FE`` on five top-ups (48.49 /
    45.44 / 45.35 / 47.23 / 48.31), bundle 01-10-2024_ER-00181 two Bella
    Sky Hotel receipts on one folio ``37939838``. Today the totals keep them
    apart; two top-ups of one amount under one account id would twin, the
    second would leave the pool, and its charge would sit unmatched with no
    candidate while the collapsed receipt renders as a copy: a silent lost
    match. Every real twin shares one total, so the rule costs nothing
    (measured on both live months and the six bundles, 2026-09-15: it
    silences ``NQTJA4FE`` and the folio, moves no group). A receipt with no
    total does not vote.
    """
    per_doc: dict[str, str] = {}
    totals_by_ref: dict[str, set[str]] = defaultdict(set)
    for r in receipts:
        ref = reference_key(r)
        if ref is None:
            continue
        per_doc[r.document_id] = ref
        if r.detected_total is not None:
            totals_by_ref[ref].add(str(r.detected_total))
    account_ids = {ref for ref, totals in totals_by_ref.items() if len(totals) > 1}
    if not account_ids:
        return per_doc
    return {doc: ref for doc, ref in per_doc.items() if ref not in account_ids}


def find_duplicate_receipt_groups(
    receipts: list[Receipt],
) -> list[tuple[list[str], str | None]]:
    """Every receipt duplicate group with the basis it was found on:
    ``(members, None)`` for a vendor/date group, ``(members, "reference")``
    for a group ONLY the reference key finds.

    Groups from the two keys are never merged into a bigger group. A group
    is a set of members: a reference group whose membership equals a
    vendor/date group IS that group (same members, same
    ``duplicate_group_id``, basis None), and overlapping-but-different
    memberships stay two groups. Reviewer resolutions are keyed by group id
    and the live months hold saved ones, so an existing group's membership
    must not move under the new key. Vendor/date groups come first, then
    the reference-only groups, each in its detector's sorted order.
    """
    vendor_date = find_duplicate_receipts(receipts)
    known = {tuple(g) for g in vendor_date}
    out: list[tuple[list[str], str | None]] = [(g, None) for g in vendor_date]
    for g in find_duplicate_receipts_by_reference(receipts):
        if tuple(g) in known:
            continue
        out.append((g, REFERENCE_BASIS))
    return out


def inherit_card_from_copies(
    receipts: list[Receipt],
    resolutions: dict[str, str] | None = None,
    card_hints: dict[str, str] | None = None,
) -> list[Receipt]:
    """The same list, where every copy of one document (by its reference)
    that names no card carries the card its copies name, and every copy
    with no legal entity carries the one entity its copies name.

    ``resolutions`` is the run's duplicate resolutions (group id ->
    ``ignore`` / ``confirmed``): a group the reviewer ruled "not a
    duplicate" lends nothing, because the ruling says the two documents are
    two purchases, and a card lent across them would keep the card-less one
    scoped to the other's card while its own charge sits on the statement
    unmatched (reviewer probe 2026-09-15: after ``ignore`` the group
    re-expanded but the invoice copy still carried the receipt copy's card).
    ``card_hints`` is the batch's operator hint -> card assignments
    (``expense.card_hints``): a member whose CURRENT payment mode is one the
    operator assigned keeps it, because ``resolve_hinted_card_ex`` keys that
    assignment on the exact stored string and rewriting "Link" to the twin's
    card label would silently lose the operator's ruling to the twin's card.

    Item 69 round A (2026-09-15). ``collapsed_duplicate_copies`` keeps one
    copy of a document in the pool, and for a Stripe pair the kept copy is
    the INVOICE, which names no card; the RECEIPT copy names it. In August
    2026 the Lovable 50 invoice, carrying no card, matched BASE44 50.00 on
    the Corporate Services statement, while its receipt copy named card
    1176, a Consulting card the statement does not carry. Lending the card
    puts the kept copy where its money actually is: the card chain
    (``resolve_batch_row_cards``) derives the entity from it and the pair
    leaves the other entity's statement scope.

    Pure, over the month's FULL effective receipt list: a copy item 56 has
    already collapsed still lends its card, which is why the caller runs
    this before the collapse and before the card chain. Rules:

    * a member whose payment mode already names a card (``_card_keys``
      non-empty) keeps its own; only members with no card-bearing mode
      (None, "Link", "PAYE", a bank-transfer note) receive one;
    * the group lends a card only when every card-bearing copy names the
      SAME card (identical ``_card_keys``); copies naming different cards
      lend nothing, because then the document does not say which card paid;
    * a member with an empty ``legal_entity_id`` receives the group's entity
      only when exactly one is named across the group; a member that names
      one keeps it.
    """
    resolutions = resolutions or {}
    hinted = {k for k in (card_hints or {}) if k}
    by_id = {r.document_id: r for r in receipts}
    patched: dict[str, Receipt] = {}
    for members in find_duplicate_receipts_by_reference(receipts):
        if resolutions.get(duplicate_group_id("receipt", members)) == "ignore":  # lends nothing
            continue
        group = [by_id[d] for d in members if d in by_id]
        card_modes = [r.payment_mode for r in group if _card_keys(r.payment_mode)]
        lend_mode: str | None = None
        if card_modes:
            keys = {frozenset(_card_keys(m)) for m in card_modes}
            if len(keys) == 1:
                lend_mode = card_modes[0]
        entities = {(r.legal_entity_id or "").strip() for r in group} - {""}
        lend_entity = next(iter(entities)) if len(entities) == 1 else None
        for r in group:
            kw: dict = {}
            if (
                lend_mode is not None
                and not _card_keys(r.payment_mode)
                and (r.payment_mode or "").strip() not in hinted
            ):
                kw["payment_mode"] = lend_mode
            if lend_entity is not None and not (r.legal_entity_id or "").strip():
                kw["legal_entity_id"] = lend_entity
            if kw:
                patched[r.document_id] = replace(r, **kw)
    if not patched:
        return receipts
    return [patched.get(r.document_id, r) for r in receipts]


def collapsed_duplicate_copies(
    receipts: list[Receipt], resolutions: dict[str, str] | None = None
) -> set[str]:
    """The document ids a duplicate group contributes BEYOND its first copy,
    for every group the reviewer has not ruled "not a duplicate".

    Owner ruling 2026-09-11 (backlog item 56). Stripe-style vendors mail
    both an invoice PDF and a receipt PDF for one purchase; both land, both
    are the same merchant + date + total + currency, and the matcher saw
    two indistinguishable candidates for one charge and filed the pairing
    as AMBIGUOUS. In August 23 of 31 receipts sat in such pairs, so the
    reviewer was asked to pick between two copies of the same document a
    dozen times a month. Removing the extra copies from the candidate pool
    turns each of those into the exact match it always was.

    Only the pool shrinks. Every copy stays in the month's snapshot, its
    counts, its exports and its duplicate markers; a suppressed copy simply
    surfaces as unmatched, flagged as the copy it is.

    ``ignore`` is the escape hatch and it is load-bearing: two real
    purchases from one merchant on one day for one amount are a real thing
    (two identical coffees, two seats on the same booking), and a reviewer
    who has ruled a group "not a duplicate" gets both copies back in the
    pool on the next re-match. A ``confirmed`` group stays collapsed;
    acknowledging a duplicate is not un-duplicating it.

    Reference groups (item 69 round A) collapse exactly as vendor/date
    groups do: every member after the first of the sorted members, unless
    the reviewer ruled THAT group ``ignore``. A document collapsed by one
    group and kept by another is collapsed.
    """
    resolutions = resolutions or {}
    out: set[str] = set()
    for members, _basis in find_duplicate_receipt_groups(receipts):
        if resolutions.get(duplicate_group_id("receipt", members)) == "ignore":
            continue
        out.update(members[1:])
    return out
