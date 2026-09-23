"""What a stored category may be while two vocabularies overlap.

Receipts are moving from the eight coarse buckets (`EXPENSE_CATEGORIES`) to
Dirk's curated per-entity Zoho GL leaves. Both are live at once: months
reconciled under the buckets keep loading, the published SPA keeps sending
bucket strings until the owner publishes a new bundle, and the new chain
writes leaf codes. Every write path that used to refuse anything outside the
eight has to let both through without refusing either.

WHY NOTHING HERE RAISES

`PUT /api/settings` validates before it patches, and the SPA sends the whole
settings map back on every merchant save. One merchant carrying a category
string the server no longer knows would 400 the entire save, the cards and
entities tabs included, for an edit that never touched it. The precedent is
`RETIRED_ENTITY_KEYS` / `RETIRED_SETTINGS_KEYS` (`web/store.py`): a value the
app no longer stores is dropped and named in the reply, never refused. So
`recognize` answers None and the caller drops that one value and reports it;
the caller does not refuse the request.

Dropping rather than storing matters most where the write is durable memory.
A learned `(entity, vendor)` rule is consulted ahead of the model on every
later run, so a string from neither vocabulary must not become one: it would
never match anything again and would sit there looking like a decision
somebody made.

WHY THIS IS ORG-BLIND, AND WHY THAT IS SAFE

A leaf CODE means the same account in every entity; only the NAME is
entity-specific (`E100010-31` is `Travel Expense | Food` in two orgs and
`CorpServ | Travel Expense | Food` in the third). So a code is recognizable
without knowing the entity, and a bare name is not recognized here at all,
which is what keeps a Cloud Services account off a Corporate Services
expense.

This is a storage-tolerance gate, not a posting gate. Whether THIS entity may
post to that leaf is `curated_leaves.account_id_for(org_id, code)`, which is
strictly org-scoped and is the only thing that yields an account id. Nothing
here returns an account, and recognizing a code does not make it postable.
"""
from __future__ import annotations

from .matching.types import EXPENSE_CATEGORIES
from .zoho import curated_leaves

__all__ = ["recognize", "is_recognized"]


def _is_curated_code(text: str) -> bool:
    """True when `text` is a code in the compiled taxonomy, in any entity.

    A malformed taxonomy asset degrades this to "no codes" rather than
    raising. A tolerance gate runs on every settings save, and the compiled
    asset being wrong is not a reason for a merchant edit to 500; the posting
    path still raises loudly, which is where a broken asset has to be heard.
    """
    try:
        return curated_leaves.leaf(text) is not None
    except curated_leaves.CuratedLeavesError:
        return False


def recognize(value: str | None) -> str | None:
    """The canonical stored form of `value`, or None if it is neither
    vocabulary.

    One of the eight buckets stays itself. A curated leaf code stays itself.
    A `"CODE name"` label, the shape `curated_leaves.llm_leaf_labels` emits
    and a client may echo back, reduces to the bare code: the name is one
    entity's presentation, and storing it would make one account read as
    several.
    """
    text = str(value or "").strip()
    if not text:
        return None
    if text in EXPENSE_CATEGORIES:
        return text
    if _is_curated_code(text):
        return text
    head = text.split(None, 1)[0]
    if head != text and _is_curated_code(head):
        return head
    return None


def is_recognized(value: str | None) -> bool:
    return recognize(value) is not None
