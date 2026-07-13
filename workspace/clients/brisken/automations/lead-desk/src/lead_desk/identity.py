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
                company: str | None, ordinal: int | None = None) -> str:
    if email:
        return email.strip().lower()
    # No email: key on identity plus the stable source-row ordinal, so two
    # anonymous booth taps (blank name/company) never merge into one contact.
    # Losing distinct booth records (under-merge) is worse than over-splitting,
    # which the same-name duplicate report surfaces for review.
    parts = [first or "", last or "", company or ""]
    if ordinal is not None:
        parts.append(f"#{ordinal}")
    basis = "|".join(parts).strip().lower()
    return "anon:" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def contact_id_for(nk: str) -> str:
    return hashlib.sha1(nk.encode("utf-8")).hexdigest()[:16]
