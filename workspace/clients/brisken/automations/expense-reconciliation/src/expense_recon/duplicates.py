"""Duplicate receipt detection (Tier-1 #4, decided by the tool since item 74).

Receipts only. The charge-side detector (``find_duplicate_charges``) is gone
(owner ruling 2026-09-15, notes #37/#41): the card statement is the truth of
what was charged, so two charges to one vendor are two charges, and every
group it ever raised on the live months was a set of real, distinct
transactions. Double ingest of one statement is prevented by stable
transaction identity (item 29), which left the detector no job.

``find_duplicate_receipts`` finds the same receipt uploaded more than once:
identical normalized merchant + date + total + currency across two or more
distinct document ids. Pure functions; no LLM, no network.

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

The tool decides (item 74, 2026-09-16, notes #45/#46). The keys above (plus
a content-hash key) only NOMINATE a group; ``decide_receipt_groups`` runs a
ladder over each one, first rung that applies wins, and records the rung as
the group's ``basis``: identical bytes, one document number, one page
printing the other's number, two different numbers, two different cards,
vendor + date + total + currency. After a match,
``restore_copies_with_their_own_charge`` (the statement check) returns a
set-aside copy whose own exact charge sits unmatched. A reviewer's ruling
outranks every rung. Nobody is asked: a copy is set aside and reported, and
"Not a copy" stays as an undo.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, replace

from .matching.deterministic import _card_keys
from .matching.types import Receipt, Transaction

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_NON_ALNUM_UPPER = re.compile(r"[^A-Z0-9]+")
_NON_DIGIT = re.compile(r"\D+")
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
    A group whose verdict is ``distinct`` (item 74: the tool or the reviewer
    decided the documents are two purchases) yields nothing for the same
    reason: it is not a duplicate, so no row says it is one.

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
        if group.get("verdict") == VERDICT_DISTINCT:
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
    digests: dict[str, str] | None = None,
) -> list[tuple[list[str], str | None]]:
    """Every CANDIDATE receipt duplicate group with the key that found it:
    ``(members, None)`` for a vendor/date group, ``(members, "reference")``
    for a group ONLY the reference key finds, ``(members, "hash")`` for a
    group only identical bytes find (item 74; needs ``digests``, document id
    -> byte digest). Which key found a group is not what the group IS:
    ``decide_receipt_groups`` answers that.

    Groups from the keys are never merged into a bigger group. A group is a
    set of members: a group whose membership equals an earlier key's group
    IS that group (same members, same ``duplicate_group_id``), and
    overlapping-but-different memberships stay separate groups. Reviewer
    resolutions are keyed by group id and the live months hold saved ones,
    so an existing group's membership must not move under a new key.
    Vendor/date groups come first, then the reference-only groups, then the
    hash-only groups, each in its detector's sorted order.
    """
    vendor_date = find_duplicate_receipts(receipts)
    known = {tuple(g) for g in vendor_date}
    out: list[tuple[list[str], str | None]] = [(g, None) for g in vendor_date]
    for g in find_duplicate_receipts_by_reference(receipts):
        if tuple(g) in known:
            continue
        known.add(tuple(g))
        out.append((g, REFERENCE_BASIS))
    if digests:
        for g in find_duplicate_receipts_by_hash(receipts, digests):
            if tuple(g) in known:
                continue
            known.add(tuple(g))
            out.append((g, BASIS_HASH))
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
    receipts: list[Receipt],
    resolutions: dict[str, str] | None = None,
    *,
    digests: dict[str, str] | None = None,
    text_of=None,
    statement_distinct=None,
) -> set[str]:
    """The document ids a duplicate group contributes BEYOND its first copy,
    for every group whose verdict is ``copy``.

    Item 74 (2026-09-16): the verdict is ``decide_receipt_groups``'s, so a
    group the ladder decides is two purchases (two different document
    numbers nobody's page cross-prints, two different cards, the statement
    check) is not collapsed, and a reviewer's ruling still outranks the
    ladder in both directions. ``digests`` / ``text_of`` are the evidence
    rungs 1 and 3 read; without them those rungs cannot fire, so a caller
    deciding a live month passes both.

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
    THAT group's verdict is not ``copy``. A document collapsed by one group
    and kept by another is collapsed.
    """
    return copies_to_collapse(decide_receipt_groups(
        receipts, digests=digests, text_of=text_of,
        resolutions=resolutions, statement_distinct=statement_distinct,
    ))


# ── Item 74: the ladder that decides every receipt group ─────────────
#
# Owner rulings 2026-09-15/16 (notes #37, #41, #45, #46): two charges to one
# vendor are two charges (charge-side detection is deleted), and the tool
# decides every receipt group itself and never asks. A group is a CANDIDATE
# from one of three keys (vendor/date, reference, content hash); the ladder
# below decides what it is, first rung that applies wins, and records that
# rung as the group's `basis`.

BASIS_HASH = "hash"
BASIS_REFERENCE = REFERENCE_BASIS
BASIS_PRINTED_REFERENCE = "printed_reference"
BASIS_DISTINCT_REFERENCE = "distinct_reference"
BASIS_RECEIPT_CARD = "receipt_card"
BASIS_VENDOR_DATE = "vendor_date"
BASIS_STATEMENT = "statement"
LADDER_BASES = (
    BASIS_HASH, BASIS_REFERENCE, BASIS_PRINTED_REFERENCE,
    BASIS_DISTINCT_REFERENCE, BASIS_RECEIPT_CARD, BASIS_VENDOR_DATE,
    BASIS_STATEMENT,
)

VERDICT_COPY = "copy"
VERDICT_DISTINCT = "distinct"
STATE_OPEN = "open"
STATE_DECIDED = "decided"
DECIDED_BY_TOOL = "tool"
DECIDED_BY_REVIEWER = "reviewer"

# How a reviewer's stored resolution reads as a verdict. `confirmed` is
# "Real duplicate", `ignore` is "Not a duplicate"; the words the store keeps
# are unchanged, so every saved ruling on the live months keeps its meaning.
_REVIEWER_VERDICT = {"confirmed": VERDICT_COPY, "ignore": VERDICT_DISTINCT}

# A printed reference is looked for across at most this many adjacent
# whitespace-separated tokens, so "2506 5524" printed with a space still
# reads as `25065524` without the whole page collapsing into one string in
# which any short digit key would find itself by accident.
_PRINTED_TOKEN_WINDOW = 3


def find_duplicate_receipts_by_hash(
    receipts: list[Receipt], digests: dict[str, str]
) -> list[list[str]]:
    """Group document ids of receipts whose stored bytes are identical (the
    same ``digests`` value). Receipts with no known digest are skipped.
    Each group has 2+ distinct ids, sorted; order is deterministic."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for r in receipts:
        digest = (digests or {}).get(r.document_id)
        if digest:
            buckets[digest].append(r.document_id)
    groups = [sorted(set(ids)) for ids in buckets.values() if len(set(ids)) >= 2]
    groups.sort()
    return groups


def printed_reference_tokens(text: str | None) -> set[str]:
    """Every normalized string a text layer prints across 1 to
    ``_PRINTED_TOKEN_WINDOW`` adjacent tokens, in ``reference_key``'s own
    alphabet (upper-cased alphanumerics), so a key is compared for EQUALITY
    against something the page actually printed, never as a substring of
    the whole page."""
    tokens = [_NON_ALNUM_UPPER.sub("", t.upper()) for t in (text or "").split()]
    tokens = [t for t in tokens if t]
    out: set[str] = set()
    for n in range(1, _PRINTED_TOKEN_WINDOW + 1):
        for i in range(len(tokens) - n + 1):
            out.add("".join(tokens[i:i + n]))
    return out


@dataclass(frozen=True)
class ReceiptGroupDecision:
    """One receipt group and what it is.

    ``basis`` is the ladder rung the TOOL decided on (None only when no rung
    applies, which the candidate keys make structurally impossible); a
    reviewer's ruling does not rewrite it, so a group the reviewer overruled
    still says what the tool found. ``verdict`` / ``decided_by`` are the
    EFFECTIVE answer: the reviewer's when there is one (a reviewer verdict
    outranks the tool), the tool's otherwise. ``state`` is ``open`` only
    while nobody has decided."""

    members: tuple[str, ...]
    group_id: str
    basis: str | None
    tool_verdict: str | None
    resolution: str | None
    verdict: str | None
    decided_by: str | None
    state: str

    @property
    def is_copy(self) -> bool:
        return self.verdict == VERDICT_COPY


def _ladder(
    members: list[str],
    by_id: dict[str, Receipt],
    keys: dict[str, str],
    digests: dict[str, str],
    text_of,
) -> tuple[str | None, str | None]:
    """Rungs 1 to 6 for one candidate group: ``(basis, verdict)``."""
    group = [by_id[d] for d in members if d in by_id]
    if len(group) < 2:
        return None, None

    # 1. hash: identical bytes.
    group_digests = [digests.get(r.document_id) for r in group]
    if all(group_digests) and len(set(group_digests)) == 1:
        return BASIS_HASH, VERDICT_COPY

    totals = {str(r.detected_total) for r in group}
    currencies = {(r.detected_currency or "").upper() for r in group}
    same_money = (
        None not in {r.detected_total for r in group}
        and len(totals) == 1 and len(currencies) == 1
    )
    group_keys = [keys.get(r.document_id) for r in group]

    # 2. reference: one document number + total + currency.
    if same_money and all(group_keys) and len(set(group_keys)) == 1:
        return BASIS_REFERENCE, VERDICT_COPY

    # 3. printed_reference: one document's text layer prints another's
    # number (a Stripe receipt carries its own receipt number AND prints the
    # invoice's). Linked pairwise; the group is one document when the links
    # connect every member. Read only when some member has a number to find.
    if any(group_keys) and text_of is not None:
        printed = {}
        for r in group:
            try:
                printed[r.document_id] = printed_reference_tokens(text_of(r.document_id))
            except Exception:  # noqa: BLE001 - an unreadable file prints nothing
                printed[r.document_id] = set()
        ids = [r.document_id for r in group]
        linked = {ids[0]}
        grew = True
        while grew:
            grew = False
            for a in ids:
                if a in linked:
                    continue
                for b in linked:
                    ka, kb = keys.get(a), keys.get(b)
                    if (kb and kb in printed[a]) or (ka and ka in printed[b]):
                        linked.add(a)
                        grew = True
                        break
        if len(linked) == len(ids):
            return BASIS_PRINTED_REFERENCE, VERDICT_COPY

    # 4. distinct_reference: every member carries a usable number, the
    # numbers differ, and no page prints another's (rung 3 was negative).
    if all(group_keys) and len(set(group_keys)) > 1:
        return BASIS_DISTINCT_REFERENCE, VERDICT_DISTINCT

    # 5. receipt_card: two members name cards that share no identifier.
    carded = [k for k in (_card_keys(r.payment_mode) for r in group) if k]
    for i, a in enumerate(carded):
        if any(not (a & b) for b in carded[i + 1:]):
            return BASIS_RECEIPT_CARD, VERDICT_DISTINCT

    # 6. vendor_date: vendor + date + total + currency, nothing disagreeing.
    if (
        same_money
        and None not in {r.detected_date for r in group}
        and len({r.detected_date for r in group}) == 1
        and len({_norm_vendor(r.detected_vendor) for r in group}) == 1
    ):
        return BASIS_VENDOR_DATE, VERDICT_COPY
    return None, None


def decide_receipt_groups(
    receipts: list[Receipt],
    *,
    digests: dict[str, str] | None = None,
    text_of=None,
    resolutions: dict[str, str] | None = None,
    statement_distinct=None,
) -> list[ReceiptGroupDecision]:
    """Every receipt duplicate group with what it is, in the order
    ``find_duplicate_receipt_groups`` lists the candidates (vendor/date,
    then reference-only, then hash-only), which is the order the legacy
    ``duplicate_receipts`` list and ``duplicate_groups`` share.

    ``digests``: document id -> byte digest (rung 1). ``text_of``: document
    id -> the PDF text layer or None (rung 3; called only for groups that
    reach rung 3). ``resolutions``: the reviewer's stored rulings, which
    outrank the tool. ``statement_distinct``: group ids the last re-match's
    statement check (rung 7) restored; they read ``basis: "statement"``,
    verdict distinct, decided by the tool.
    """
    digests = digests or {}
    resolutions = resolutions or {}
    restored = set(statement_distinct or ())
    by_id = {r.document_id: r for r in receipts}
    keys = reference_keys(receipts)
    out: list[ReceiptGroupDecision] = []
    for members, _key in find_duplicate_receipt_groups(receipts, digests):
        gid = duplicate_group_id("receipt", members)
        basis, tool_verdict = _ladder(members, by_id, keys, digests, text_of)
        if gid in restored and tool_verdict == VERDICT_COPY:
            basis, tool_verdict = BASIS_STATEMENT, VERDICT_DISTINCT
        resolution = resolutions.get(gid)
        reviewer = _REVIEWER_VERDICT.get(resolution) if resolution else None
        if reviewer is not None:
            verdict, decided_by = reviewer, DECIDED_BY_REVIEWER
        elif tool_verdict is not None:
            verdict, decided_by = tool_verdict, DECIDED_BY_TOOL
        else:
            verdict = decided_by = None
        out.append(ReceiptGroupDecision(
            members=tuple(members),
            group_id=gid,
            basis=basis,
            tool_verdict=tool_verdict,
            resolution=resolution,
            verdict=verdict,
            decided_by=decided_by,
            state=STATE_DECIDED if verdict is not None else STATE_OPEN,
        ))
    return out


def copies_to_collapse(
    decisions: list[ReceiptGroupDecision], restored=()
) -> set[str]:
    """The document ids the candidate pool drops: every member after the
    first of each group whose effective verdict is ``copy``, except a group
    in ``restored`` (rung 7, applied only to the tool's own verdicts). A
    document collapsed by one group and kept by another is collapsed."""
    restored = set(restored or ())
    out: set[str] = set()
    for d in decisions:
        if not d.is_copy:
            continue
        if d.group_id in restored and d.decided_by == DECIDED_BY_TOOL:
            continue
        out.update(d.members[1:])
    return out


def restore_copies_with_their_own_charge(
    decisions: list[ReceiptGroupDecision],
    receipts: list[Receipt],
    transactions: list[Transaction],
    outcome,
    cfg=None,
    *,
    collapsed=(),
) -> set[str]:
    """Rung 7, the statement check, run once after a match: the group ids
    whose set-aside copy has its OWN exact charge sitting unmatched.

    A group qualifies when the TOOL called it a copy (a reviewer's ruling is
    never overruled here), its kept copy settled a charge in this outcome,
    and one of its set-aside copies pairs EXACTLY (the matcher's own
    ``match_one`` tier: same currency, exact amount, date window) with a
    charge nothing holds, inside the matcher's own entity and card scope.
    Two documents that each have a charge are two purchases, whatever the
    documents look like: the bank printed two lines. The kept-copy
    condition keeps a lone document that merely resembles a stranger's
    charge from being called two purchases. The caller re-matches once with
    these groups restored; there is no second check.
    """
    from .matching.deterministic import (
        MatchingConfig,
        _tx_card_keys,
        match_one,
        pair_in_scope,
        receipt_card_scope,
    )
    from .matching.types import MatchType

    cfg = cfg or MatchingConfig()
    collapsed = set(collapsed or ())
    if not collapsed:
        return set()
    by_id = {r.document_id: r for r in receipts}
    held_tx = {
        m.transaction_id
        for m in (*outcome.matches, *outcome.judgment_required, *outcome.ambiguous)
    }
    settled_docs = {m.document_id for m in outcome.matches}
    charges = [t for t in transactions if not t.is_credit]
    tx_keys = {t.transaction_id: _tx_card_keys(t) for t in charges}
    present: set[str] = set()
    for k in tx_keys.values():
        present |= k
    free = [t for t in charges if t.transaction_id not in held_tx]

    restored: set[str] = set()
    for d in decisions:
        if d.decided_by != DECIDED_BY_TOOL or d.verdict != VERDICT_COPY:
            continue
        if d.members[0] not in settled_docs:
            continue
        for doc in d.members[1:]:
            r = by_id.get(doc)
            if r is None or doc not in collapsed:
                continue
            scope = receipt_card_scope(r, present, cfg)
            hit = False
            for t in free:
                if (r.detected_currency or "") != t.transaction_currency:
                    continue
                if not pair_in_scope(t, r, tx_keys[t.transaction_id], scope):
                    continue
                m = match_one(t, r, cfg)
                if m is not None and m.match_type == MatchType.EXACT:
                    hit = True
                    break
            if hit:
                restored.add(d.group_id)
                break
    return restored
