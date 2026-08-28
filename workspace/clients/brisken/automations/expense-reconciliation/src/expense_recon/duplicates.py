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
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date

from .matching.types import Receipt, Transaction

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_MIN_DATE = date.min


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
    """
    flags: dict[str, dict] = {}
    for group in groups:
        if group.get("kind") != kind or group.get("resolution") == "ignore":
            continue
        members = [m for m in (group.get("members") or []) if m]
        if len(members) < 2:
            continue
        for i, member in enumerate(members, start=1):
            flags[member] = {
                "group_id": group.get("group_id") or "",
                "kind": kind,
                "n_copies": len(members),
                "copy": i,
                "of": members[0],
                "is_extra": i > 1,
                "resolution": group.get("resolution"),
            }
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
