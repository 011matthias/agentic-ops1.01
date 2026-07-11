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

import re
from collections import defaultdict
from datetime import date

from .matching.types import Receipt, Transaction

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_MIN_DATE = date.min


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
