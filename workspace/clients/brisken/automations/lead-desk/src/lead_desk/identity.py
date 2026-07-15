"""Contact identity: the natural key and the derived contact_id.

One person = one global contact row, keyed by email (lowercased) or an
``anon:`` hash of name+company+ordinal when no email exists. Campaign
membership lives on ``enrollments``, never in the key: the same person
enrolled in two campaigns is ONE contact with one timeline, so suppression
(consent) and reply detection apply everywhere at once.

Shared by the migration importer and the campaign upload route so both
adopt existing contacts instead of duplicating them.
"""
from __future__ import annotations

import hashlib


def natural_key(email: str | None, first: str | None, last: str | None,
                company: str | None) -> str:
    if email:
        return email.strip().lower()
    # No email: key on identity content only (name + company). The old key
    # mixed in the source-row ordinal, which is stable only within one fixed
    # file order and shifts whenever a row is inserted/sorted above it, so the
    # SAME person re-keyed and duplicated on every sheet reorder. A content key
    # is stable across reorders; genuine same-name/same-company collisions are
    # surfaced by the migrate duplicate report for review.
    basis = "|".join([first or "", last or "", company or ""]).strip().lower()
    return "anon:" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def contact_id_for(nk: str) -> str:
    return hashlib.sha1(nk.encode("utf-8")).hexdigest()[:16]
