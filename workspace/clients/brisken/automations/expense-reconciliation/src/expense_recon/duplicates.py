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
indistinguishable candidates for one charge. It deletes nothing: every copy
stays in the snapshot and on screen with its marker. Since item 94
(2026-09-17) the month's count, totals and exports leave a decided copy out
and name it on a "copies set aside" line (`web.service.decided_copies`).

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


# ── Front 4 (2026-09-25): one number read two ways, and the mail body ─────
#
# `reference_key` keeps every letter and digit, so one slip read once as
# "169518087198" and once as "Operação #169518087198", or "NFC-e 246836" and
# "NFC-e no 246836 Serie 406", reads as two documents and rung 4 calls them
# two purchases. July 2026 held six such groups, each a Criss upload beside a
# charge-named copy of the same photo, all counted twice. The number a
# document IS is the long digit run inside whatever the extractor wrote, and
# the extractor sometimes puts it in `invoice_number` while `reference` holds
# the authorisation protocol, so all three fields are read.

_DIGIT_RUN = re.compile(r"\d+")
# A digit core shorter than this is a till counter or a series number
# ("Serie 406"); six digits is the shortest NFC-e / invoice number measured
# on the live months that identifies a document on its own.
_MIN_DIGIT_CORE = 6
_RENDERED_BODY_STEM = "rendered-body"


def _digit_core(text: str | None, receipt: Receipt) -> str | None:
    """The longest digit run of ``text`` (the first of equal-length runs), or
    None when it is shorter than ``_MIN_DIGIT_CORE`` digits, has fewer than
    ``_MIN_REFERENCE_LEN`` digits once leading zeros go (a padded counter), or
    only repeats the receipt's own date or total (``reference_key``'s rule)."""
    runs = _DIGIT_RUN.findall(text or "")
    if not runs:
        return None
    core = max(runs, key=len)
    if len(core) < _MIN_DIGIT_CORE or len(core.lstrip("0")) < _MIN_REFERENCE_LEN:
        return None
    d = receipt.detected_date
    if d is not None and core in {d.strftime(layout) for layout in _DATE_LAYOUTS}:
        return None
    total = receipt.detected_total
    if total is not None and core in {
        _NON_DIGIT.sub("", f"{total:f}"),
        _NON_DIGIT.sub("", f"{total:.2f}"),
        _NON_DIGIT.sub("", str(int(total))),
    }:
        return None
    return core


def document_number_cores(receipts: list[Receipt]) -> dict[str, frozenset[str]]:
    """``document_id -> the digit cores it prints`` over ONE list, read from
    ``detected_reference``, ``invoice_number`` and ``receipt_number``, with
    account ids taken out exactly as ``reference_keys`` does: a core carried
    by receipts of DIFFERENT totals is not a document number. Receipts with
    no core are absent."""
    per_doc: dict[str, set[str]] = {}
    totals_by_core: dict[str, set[str]] = defaultdict(set)
    for r in receipts:
        cores = {
            c for c in (
                _digit_core(r.detected_reference, r),
                _digit_core(getattr(r, "invoice_number", None), r),
                _digit_core(getattr(r, "receipt_number", None), r),
            ) if c
        }
        if not cores:
            continue
        per_doc[r.document_id] = cores
        if r.detected_total is not None:
            for c in cores:
                totals_by_core[c].add(str(r.detected_total))
    account = {c for c, totals in totals_by_core.items() if len(totals) > 1}
    out = {}
    for doc, cores in per_doc.items():
        kept = frozenset(cores - account)
        if kept:
            out[doc] = kept
    return out


def _vendor_identity(r: Receipt) -> list[str]:
    from .merchant_identity import identity_key

    return identity_key(r.detected_vendor).split()


def vendors_agree(a: Receipt, b: Receipt) -> bool:
    """One merchant, by ``merchant_identity.identity_key``: equal keys, or one
    key's words are the start or the end of the other's with a word of four
    letters or more among them ("zoho" / "zoho books", "e a locacoes" /
    "b91 e a locacoes"). Raw spellings never have to agree."""
    ka, kb = _vendor_identity(a), _vendor_identity(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    short, long_ = (ka, kb) if len(ka) < len(kb) else (kb, ka)
    if not any(len(w) >= 4 for w in short):
        return False
    n = len(short)
    return long_[:n] == short or long_[-n:] == short


def _one_misread_digit(a: str, b: str) -> bool:
    return len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 1


def _days_apart(a: Receipt, b: Receipt) -> int | None:
    if a.detected_date is None or b.detected_date is None:
        return None
    return abs((a.detected_date - b.detected_date).days)


def _same_money(a: Receipt, b: Receipt) -> bool:
    return (
        a.detected_total is not None
        and a.detected_total == b.detected_total
        and (a.detected_currency or "").upper() == (b.detected_currency or "").upper()
    )


def _number_link(a: Receipt, b: Receipt, cores: dict[str, frozenset[str]]) -> str | None:
    """How two receipts are one document by their numbers: ``reference_digits``
    (a shared digit core, one merchant, one amount, dates at most a day
    apart), ``misread_digit`` (cores of one length differing in exactly one
    position, one merchant, one amount, the SAME date), else None."""
    ca, cb = cores.get(a.document_id), cores.get(b.document_id)
    if not ca or not cb or not _same_money(a, b):
        return None
    days = _days_apart(a, b)
    if days is None or days > 1 or not vendors_agree(a, b):
        return None
    if ca & cb:
        return BASIS_REFERENCE_DIGITS
    if days == 0 and any(_one_misread_digit(x, y) for x in ca for y in cb):
        return BASIS_MISREAD_DIGIT
    return None


def _union_groups(ids: list[str], linked) -> list[list[str]]:
    parent = {d: d for d in ids}

    def find(d):
        while parent[d] != d:
            parent[d] = parent[parent[d]]
            d = parent[d]
        return d

    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if linked(a, b):
                parent[find(a)] = find(b)
    groups: dict[str, list[str]] = defaultdict(list)
    for d in ids:
        groups[find(d)].append(d)
    return [sorted(g) for g in groups.values() if len(g) >= 2]


def find_duplicate_receipts_by_number(receipts: list[Receipt]) -> list[list[str]]:
    """Groups of receipts that are one document by their digit core or by a
    one-digit misread of it (``_number_link``), whatever the vendor spelling
    or the wrapper words around the number. Sorted, deterministic."""
    cores = document_number_cores(receipts)
    by_id = {r.document_id: r for r in receipts}
    buckets: dict[tuple, list[str]] = defaultdict(list)
    for r in receipts:
        if r.document_id in cores and r.detected_total is not None:
            buckets[(str(r.detected_total), (r.detected_currency or "").upper())].append(r.document_id)
    out: list[list[str]] = []
    for ids in buckets.values():
        if len(ids) < 2:
            continue
        out.extend(_union_groups(
            sorted(set(ids)),
            lambda a, b: _number_link(by_id[a], by_id[b], cores) is not None,
        ))
    out.sort()
    return out


def is_rendered_body(receipt: Receipt) -> bool:
    """The mail body the intake rendered to a PDF (`NNNN__rendered-body.pdf`),
    read from the file name's stem."""
    name = (receipt.receipt_name or _NAME_PREFIX.sub("", receipt.document_id or "")).lower()
    return name.rsplit(".", 1)[0].endswith(_RENDERED_BODY_STEM)


def body_twin_partners(receipts: list[Receipt]) -> list[tuple[str, list[str]]]:
    """``(body id, [partner ids])`` for every rendered mail body that repeats
    a non-body document: same total and currency, dates at most a day apart,
    one merchant (``vendors_agree``). The body prints the vendor its own way,
    carries no invoice number and has its own bytes, so none of the other
    keys ever nominates it (September 2026: Zoho 50.00, Lovable 60.00,
    Anthropic 100.00, Lovable 50.00; August: Zoho Books 576.00)."""
    bodies = [r for r in receipts if is_rendered_body(r)]
    others = [r for r in receipts if not is_rendered_body(r)]
    out: list[tuple[str, list[str]]] = []
    for body in sorted(bodies, key=lambda r: r.document_id):
        partners = sorted(
            o.document_id for o in others
            if _same_money(body, o)
            and (_days_apart(body, o) or 0) <= 1 and _days_apart(body, o) is not None
            and vendors_agree(body, o)
        )
        if partners:
            out.append((body.document_id, partners))
    return out


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
    # Front 4: a number read two ways, then a mail body beside the document
    # it repeats. Appended after every older key, so no existing group's
    # membership (and so no saved ruling's group id) moves. A body group
    # lists its partners first and the body last: the body is never the
    # kept member.
    for g in find_duplicate_receipts_by_number(receipts):
        if tuple(g) in known:
            continue
        known.add(tuple(g))
        out.append((g, BASIS_REFERENCE_DIGITS))
    for body, partners in body_twin_partners(receipts):
        members = [*partners, body]
        if tuple(sorted(members)) in known:
            continue
        known.add(tuple(sorted(members)))
        out.append((members, BASIS_BODY_TWIN))
    return out


def lending_groups(
    receipts: list[Receipt],
    resolutions: dict[str, str] | None = None,
    decisions: "list[ReceiptGroupDecision] | None" = None,
) -> list[list[str]]:
    """The groups whose copies lend each other a card: every reference group
    (item 69 round A), then every group the app SHOWS as one document, i.e.
    the groups behind ``expenses[].duplicate`` (``duplicate_row_flags``'s
    filter: not ruled ``ignore``, not decided ``distinct``). A group both
    lists hold is listed once.

    Item 204 step 2 (case 9, 2026-09-25). A Stripe vendor mails the INVOICE,
    which prints no card, and the RECEIPT, which prints "Visa - 9693"; the
    two carry different numbers (``HMVWDWIL-0032`` / ``2811-8284-7349``), so
    no reference group holds them and the invoice read "No legal entity yet"
    beside a twin the grid already marks as its copy (rung 3: the receipt
    prints the invoice's number). A group the ladder decides is two
    purchases (two numbers nobody cross-prints, two different cards, the
    statement check) is not shown and lends nothing: the three OpenAI 80.12
    invoices of 16 September 2026 are that case.

    ``decisions`` are the caller's own (``web.service.duplicate_decisions``,
    which reads the stored files for rungs 1 and 3 and the last re-match's
    rung 7). Without them the ladder runs here with no file evidence, so a
    pair only rung 3 can join stays apart: an evidence-free caller lends
    less, never more.
    """
    groups = find_duplicate_receipts_by_reference(receipts)
    known = {tuple(g) for g in groups}
    if decisions is None:
        decisions = decide_receipt_groups(receipts, resolutions=resolutions)
    for d in decisions:
        if d.resolution == "ignore" or d.verdict == VERDICT_DISTINCT:
            continue
        members = sorted({m for m in d.members if m})
        if len(members) < 2 or tuple(members) in known:
            continue
        known.add(tuple(members))
        groups.append(members)
    return groups


def inherit_card_from_copies(
    receipts: list[Receipt],
    resolutions: dict[str, str] | None = None,
    card_hints: dict[str, str] | None = None,
    decisions: "list[ReceiptGroupDecision] | None" = None,
) -> list[Receipt]:
    """The same list, where every copy of one document that names no card
    carries the card its copies name, and every copy with no legal entity
    carries the one entity its copies name. The groups are
    ``lending_groups``: the reference groups, and since item 204 every group
    the app shows as one document (``decisions``, the caller's ladder
    verdicts; None decides them here without file evidence).

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
      one keeps it;
    * a member two groups would lend two different cards (or entities)
      receives neither (item 204): a blank prompts Criss to look, a wrong
      card silently books the receipt to the wrong entity and person.
    """
    resolutions = resolutions or {}
    hinted = {k for k in (card_hints or {}) if k}
    by_id = {r.document_id: r for r in receipts}
    lent_mode: dict[str, str] = {}
    lent_entity: dict[str, str] = {}
    torn: set[tuple[str, str]] = set()
    for members in lending_groups(receipts, resolutions, decisions):
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
            doc = r.document_id
            if (
                lend_mode is not None
                and not _card_keys(r.payment_mode)
                and (r.payment_mode or "").strip() not in hinted
            ):
                prev = lent_mode.setdefault(doc, lend_mode)
                if _card_keys(prev) != _card_keys(lend_mode):
                    torn.add((doc, "payment_mode"))
            if lend_entity is not None and not (r.legal_entity_id or "").strip():
                if lent_entity.setdefault(doc, lend_entity) != lend_entity:
                    torn.add((doc, "legal_entity_id"))
    patched: dict[str, Receipt] = {}
    for doc, r in by_id.items():
        kw: dict = {}
        if doc in lent_mode and (doc, "payment_mode") not in torn:
            kw["payment_mode"] = lent_mode[doc]
        if doc in lent_entity and (doc, "legal_entity_id") not in torn:
            kw["legal_entity_id"] = lent_entity[doc]
        if kw:
            patched[doc] = replace(r, **kw)
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

    Here only the pool shrinks. Every copy stays in the month's snapshot and
    keeps its duplicate marker; the run payload sets it aside (items 83 +
    75), and the month's count, totals and exports leave it out through
    `web.service.decided_copies`, which reads this same set (item 94).

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
# Front 4 (2026-09-25). Rungs 3a/3b sit between the printed number and
# `distinct_reference`; `body_twin` decides only the groups the body key
# nominates.
BASIS_REFERENCE_DIGITS = "reference_digits"
BASIS_MISREAD_DIGIT = "misread_digit"
BASIS_BODY_TWIN = "body_twin"
LADDER_BASES = (
    BASIS_HASH, BASIS_REFERENCE, BASIS_PRINTED_REFERENCE,
    BASIS_DISTINCT_REFERENCE, BASIS_RECEIPT_CARD, BASIS_VENDOR_DATE,
    BASIS_STATEMENT, BASIS_REFERENCE_DIGITS, BASIS_MISREAD_DIGIT,
    BASIS_BODY_TWIN,
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


def _cards_conflict(group: list[Receipt]) -> bool:
    """Two members name cards that share no identifier (rung 5's test)."""
    carded = [k for k in (_card_keys(r.payment_mode) for r in group) if k]
    return any(
        not (a & b) for i, a in enumerate(carded) for b in carded[i + 1:]
    )


def _ladder(
    members: list[str],
    by_id: dict[str, Receipt],
    keys: dict[str, str],
    digests: dict[str, str],
    text_of,
    cores: dict[str, frozenset[str]] | None = None,
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

    # 3a/3b (front 4). reference_digits / misread_digit: the numbers differ
    # only in the words around them, or in one misread digit, and merchant,
    # amount and date agree (``_number_link``); every member linked. Never
    # over two members that name different cards (rung 5's evidence).
    if cores is not None and not _cards_conflict(group):
        ids = [r.document_id for r in group]
        links = {
            (a.document_id, b.document_id): _number_link(a, b, cores)
            for i, a in enumerate(group) for b in group[i + 1:]
        }

        def connects(allowed):
            def linked(x, y):
                return (links.get((x, y)) or links.get((y, x))) in allowed
            groups = _union_groups(ids, linked)
            return len(groups) == 1 and len(groups[0]) == len(ids)

        if connects({BASIS_REFERENCE_DIGITS}):
            return BASIS_REFERENCE_DIGITS, VERDICT_COPY
        if connects({BASIS_REFERENCE_DIGITS, BASIS_MISREAD_DIGIT}):
            return BASIS_MISREAD_DIGIT, VERDICT_COPY

    # 4. distinct_reference: every member carries a usable number, the
    # numbers differ, and no page prints another's (rung 3 was negative).
    if all(group_keys) and len(set(group_keys)) > 1:
        return BASIS_DISTINCT_REFERENCE, VERDICT_DISTINCT

    # 5. receipt_card: two members name cards that share no identifier.
    if _cards_conflict(group):
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
    cores = document_number_cores(receipts)
    out: list[ReceiptGroupDecision] = []
    copy_sets: set[tuple[str, ...]] = set()
    for members, _key in find_duplicate_receipt_groups(receipts, digests):
        gid = duplicate_group_id("receipt", members)
        if _key == BASIS_BODY_TWIN:
            # The body repeats ONE document: its only partner, or partners
            # an earlier group already calls one document. Two purchases
            # beside one body cannot say which the body repeats: no group.
            partners = tuple(sorted(members[:-1]))
            if len(partners) > 1 and partners not in copy_sets:
                continue
            basis, tool_verdict = BASIS_BODY_TWIN, VERDICT_COPY
        else:
            basis, tool_verdict = _ladder(members, by_id, keys, digests, text_of, cores)
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
        if verdict == VERDICT_COPY:
            copy_sets.add(tuple(sorted(members)))
    return out


# ── Item 217: which copy is the real expense ─────────────────────────
#
# Notes #89 / #90 (owner, 2026-09-25, on September's Pressmaster pair): "the
# real expense should be big and duplicate should be small so they should
# effectively switch places". Every copy after a group's FIRST member is the
# one set aside, and "first" used to be the sorted document id, i.e. the
# order the mail's attachments arrived in. A Stripe vendor attaches the
# INVOICE before the RECEIPT, so the tool kept the bill and set aside the
# proof of payment in every such pair (19 of 19 in September 2026).
#
# The kept copy is chosen at MATCH time and nowhere else, because a charge's
# confirmed decision names the exact document it settled: swapping the copy a
# charge already holds would leave that decision claiming the invoice while
# the receipt sat unmatched, and both would count. So a copy a charge holds
# stays kept, and only a group no charge holds moves to its receipt.

KIND_RECEIPT = "receipt"
KIND_INVOICE = "invoice"
_NAME_PREFIX = re.compile(r"^\d+__")


def payment_document_kind(receipt: Receipt) -> str | None:
    """``receipt`` for a document that proves a payment, ``invoice`` for the
    bill it pays, None when the document says neither.

    The extraction's own numbers decide first (a read ``receipt_number`` is a
    receipt; an ``invoice_number`` with no receipt number is an invoice), then
    the file name, which is how the stored months tell them apart: the
    amendment fields exist only on receipts read since 2026-09-16, while
    Stripe names its two attachments ``Invoice-...`` and ``Receipt-...``."""
    if (getattr(receipt, "receipt_number", None) or "").strip():
        return KIND_RECEIPT
    if (getattr(receipt, "invoice_number", None) or "").strip():
        return KIND_INVOICE
    name = (receipt.receipt_name or _NAME_PREFIX.sub("", receipt.document_id or "")).lower()
    if name.startswith("receipt"):
        return KIND_RECEIPT
    if name.startswith("invoice"):
        return KIND_INVOICE
    return None


def kept_member(
    members: tuple[str, ...] | list[str],
    by_id: dict[str, Receipt],
    held: set[str] | frozenset[str] = frozenset(),
) -> str | None:
    """The member a group keeps as its real expense. First rule that applies:

    1. the one member a charge holds (two or more held are all real spend, so
       nothing moves);
    2. the one payment receipt in a group that also holds its invoice, when
       every member reads the same total and currency;
    3. the first member, as before."""
    members = [m for m in members if m]
    if not members:
        return None
    held_members = [m for m in members if m in held]
    if len(held_members) == 1:
        return held_members[0]
    if held_members:
        return members[0]
    group = [by_id.get(m) for m in members]
    if any(r is None for r in group):
        return members[0]
    # Front 4: a rendered mail body is never the real expense beside the
    # document it repeats (a body a charge holds stays kept by rule 1).
    documents = [(m, r) for m, r in zip(members, group) if not is_rendered_body(r)]
    if documents and len(documents) < len(group):
        members = [m for m, _ in documents]
        group = [r for _, r in documents]
    money = {(str(r.detected_total), (r.detected_currency or "").upper()) for r in group}
    if len(money) != 1 or None in {r.detected_total for r in group}:
        return members[0]
    kinds = [payment_document_kind(r) for r in group]
    receipts = [m for m, k in zip(members, kinds) if k == KIND_RECEIPT]
    if len(receipts) == 1 and KIND_INVOICE in kinds:
        return receipts[0]
    return members[0]


def with_kept_first(
    decisions: list[ReceiptGroupDecision], kept: dict[str, str] | None
) -> list[ReceiptGroupDecision]:
    """The same decisions with each group's kept document (``kept``: group id
    -> document id) moved to the front of ``members``, so every reader of
    ``members[0]`` (the collapse, the row markers, the copies set aside, the
    statement check) agrees on it. An id that is not a member changes
    nothing; the group id hashes the sorted members, so it does not move."""
    if not kept:
        return decisions
    kept_docs = set(kept.values())
    out: list[ReceiptGroupDecision] = []
    for d in decisions:
        doc = kept.get(d.group_id)
        if doc is None:
            # Front 4: a group the stored choice predates (a mail body's
            # group, nominated after the month last re-matched) keeps the
            # document another group already keeps, so no document is kept
            # by one group and set aside by the other.
            doc = next((m for m in d.members if m in kept_docs), None)
        if doc and doc in d.members and d.members[0] != doc:
            rest = tuple(m for m in d.members if m != doc)
            d = replace(d, members=(doc, *rest))
        out.append(d)
    return out


def choose_kept(
    decisions: list[ReceiptGroupDecision],
    receipts: list[Receipt],
    held: set[str] | frozenset[str] = frozenset(),
) -> dict[str, str]:
    """group id -> kept document for every group whose verdict is ``copy``
    (``kept_member`` over the group). Only a re-match calls this."""
    by_id = {r.document_id: r for r in receipts}
    out: dict[str, str] = {}
    for d in decisions:
        if not d.is_copy:
            continue
        doc = kept_member(d.members, by_id, held)
        if doc:
            out[d.group_id] = doc
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
