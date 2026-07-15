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
    named = bool((first or "").strip() or (last or "").strip())
    parts = [first or "", last or "", company or ""]
    # NAMED email-less rows key on content (name + company) so the SAME person
    # stays one contact across sheet reorders; the old key mixed in the
    # source-row ordinal, which shifts on any insert/sort above the row and so
    # duplicated the person on every re-sync. True same-name/same-company
    # collisions surface in the migrate duplicate report.
    #
    # NAMELESS org-only rows (e.g. TA Cook PII-withheld opt-outs: distinct
    # attendees recorded as company-only, blank name) are indistinguishable by
    # content, so a content key would collapse several distinct people from one
    # org into a single contact - real data loss. They keep the source-row
    # ordinal. These rows are off-board (never contacted), so the reorder
    # duplication is cosmetic, which is the far lesser evil than losing headcount.
    if not named and ordinal is not None:
        parts.append(f"#{ordinal}")
    basis = "|".join(parts).strip().lower()
    return "anon:" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def contact_id_for(nk: str) -> str:
    return hashlib.sha1(nk.encode("utf-8")).hexdigest()[:16]
