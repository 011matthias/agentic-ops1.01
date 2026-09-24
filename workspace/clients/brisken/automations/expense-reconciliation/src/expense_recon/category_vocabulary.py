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

import os

from .coa_provision import PROVISION_ENV, entity_org_ids, load_provisioning
from .matching.types import EXPENSE_CATEGORIES
from .zoho import curated_leaves

__all__ = [
    "gl_account_options",
    "gl_revision",
    "is_recognized",
    "recognize",
]


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


# ── serving the new vocabulary, beside the old one ──────────────────────


def gl_revision() -> str:
    """The compiled taxonomy's revision, so a stale client is diagnosable.

    Empty rather than raising when the asset cannot be read: a payload that
    is missing this line is a smaller problem than one that never arrives.
    """
    try:
        return curated_leaves.curated_revision()
    except curated_leaves.CuratedLeavesError:
        return ""


def _current_entity_orgs(settings: dict | None) -> dict[str, str]:
    """The entity -> org map a batch created NOW would carry: the settings
    registry first, the /data provisioning file second, per label, exactly
    as `coa_provision.apply_to_config` builds it. Fail-open to settings only:
    an unreadable file must not take down a render."""
    try:
        prov_path = os.environ.get(PROVISION_ENV)
        provisioning = load_provisioning(prov_path) if prov_path else None
    except Exception:  # noqa: BLE001 - presentation, never a reason to 500
        provisioning = None
    return entity_org_ids(settings, provisioning)


def gl_account_options(
    settings: dict | None, entity_orgs: dict[str, str] | None = None,
) -> dict[str, list[dict]]:
    """Per legal entity, the curated leaves that entity may actually post to.

    Keyed by the SAME entity -> org map the engine categorized with, so a
    row's `legal_entity_id` finds its list. A month on the GL engine passes
    its own frozen `gl_entity_orgs`; anything else gets the map a batch
    created now would carry. Reading the settings registry alone missed the
    labels only the provisioning file names, and live those are exactly the
    labels receipts carry (`Corporate Services`, `Cloud Services`,
    `Consulting`; the registry holds `Brisken Corp Services, LLC` and the
    like), so every GL row would have looked uncovered.

    Served BESIDE `categories` / `category_options`, never in place of them
    (`cost_centers.py:104`: never repurpose a name, add beside it). The
    published SPA keeps rendering the eight buckets from the old keys until
    the owner publishes a bundle that reads this one.

    Keyed by the entity LABEL the rest of the app holds (a batch's
    `legal_entity_id`, a settings `entities` key), because the org id it
    maps to is an implementation detail of the chart.

    An entity the map gives no org, or an org outside the curated set, gets
    NO entry at all rather than an empty list.
    Absent says "this entity is not covered by the curated chart"; an empty
    list would say "covered, and there is nothing here to post to". Those
    send different people to look, which is the distinction
    `curated_leaves` was built to preserve.

    Each row carries the code to send back, this entity's own wording to
    show, and the branch root to group under. The name is presentation and
    is deliberately not a key: the same code is named differently across
    entities.
    """
    if entity_orgs is None:
        entity_orgs = _current_entity_orgs(settings)
    out: dict[str, list[dict]] = {}
    for label, org in (entity_orgs or {}).items():
        name = str(label or "").strip()
        org_id = str(org or "").strip()
        if not name:
            continue
        try:
            if not curated_leaves.covers_org(org_id):
                continue
            out[name] = [
                {
                    "code": code,
                    "name": curated_leaves.binding(code, org_id).name,
                    "category": curated_leaves.display_category_for(code) or "",
                }
                for code in sorted(curated_leaves.postable_codes(org_id))
            ]
        except curated_leaves.CuratedLeavesError:
            # Same reasoning as `_is_curated_code`: a malformed asset must
            # not take down a render. It surfaces at the posting path.
            return {}
    return out
