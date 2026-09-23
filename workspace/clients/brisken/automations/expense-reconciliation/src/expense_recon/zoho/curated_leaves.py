"""Read side of Dirk's curated per-entity Zoho expense accounts.

The data is the generated `_curated_leaves_data` module; this file is the only
thing that reads it. Together they replace the category-to-account translation
table (`category_accounts.py`), whose middle step is where both known silent
mis-posts happened.

THREE PROPERTIES THIS MODULE EXISTS TO HOLD

*The code is the identity; the name never is.* `E100010-31` is `Travel Expense |
Food` in Cloud Services and Consulting and `CorpServ | Travel Expense | Food` in
Corporate Services. Every lookup is keyed on the code, and a name reaches a key
only through `code_of`, which resolves it within ONE org.

*Only a numeric `account_id` may leave here.* The 2026-09-22 sandbox mis-post
happened because an account arrived as a NAME where a numeric id was expected,
which did not error, it defaulted: 6 of 9 rows landed in `Office Infra and
Admin`. `account_id_for` returns digits or nothing, and asserts it.

*Not-postable is four different facts, and a refusal has to say which.* Dirk
marked it N in this org, Zoho deactivated it, it is a roll-up, or this org has
no such account at all. A single "unknown reference" would send the wrong person
to look.

The branch is built from parent NAMES at compile time, never from the code,
because the code is not a path: `Business Travel Expenses - CRM` is `E600010-20`
while its children are `E600010-10-20-*`, nested under the Conferences parent in
all three sheets. A prefix-derived hierarchy mis-resolves CRM travel.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Mapping

from . import _curated_leaves_data as _data

__all__ = [
    "CuratedLeaf",
    "EntityBinding",
    "CuratedLeavesError",
    "NOT_COVERED",
    "NO_SUCH_CODE",
    "account_id_for",
    "binding",
    "code_of",
    "covers_org",
    "curated_orgs",
    "curated_revision",
    "display_category_for",
    "is_postable",
    "leaf",
    "llm_leaf_labels",
    "postable_codes",
    "source_sha256",
]


# Corporate Services prefixes its own account names ("CorpServ | Travel Expense
# | Food") where the other two orgs do not. The prefix is presentation, not
# identity, so it never reaches a key or a category.
_ENTITY_PREFIX = re.compile(r"^(CorpServ|BCS|BTS)\s*\|\s*", re.I)


def _strip_entity_prefix(name: str) -> str:
    return _ENTITY_PREFIX.sub("", name).strip()


class CuratedLeavesError(RuntimeError):
    """The compiled asset is missing, malformed, or internally inconsistent."""


# Reasons that are NOT stored per binding, because they are absences.
NOT_COVERED = "org_not_curated"
NO_SUCH_CODE = "no_such_code_in_org"


@dataclass(frozen=True)
class EntityBinding:
    """One account as it exists in one legal entity."""

    org_id: str
    account_id: str
    name: str
    postable: bool
    reason: str = ""


@dataclass(frozen=True)
class CuratedLeaf:
    code: str
    branch: tuple[str, ...]
    bindings: Mapping[str, EntityBinding]

    @property
    def display_category(self) -> str:
        """The root of the branch; for a root account, its own name.

        Kept so a classification can carry a human-readable grouping alongside
        the account without reintroducing a translation table: this is derived
        from the chart, not mapped onto it.

        Eight of Dirk's postable leaves have no parent at all (`R&D`, `Bank Fees
        and Charges`, `Interest Expense`, `Tax Paid`, the two OpeEx headers and
        two more). That is his convention rather than a gap: outside the COGS
        tree a parent is postable, and Corporate Services' chart is coarse
        enough that `MS | OpeEx` is the whole card-expense operating tree. Such
        an account IS its own category, so its name stands in for the branch.

        The entity prefix is stripped and the lowest org id wins, so one code
        yields one category whichever entity is asked.
        """
        if self.branch:
            return self.branch[0]
        for org_id in sorted(self.bindings):
            return _strip_entity_prefix(self.bindings[org_id].name)
        return ""


def _build() -> dict[str, CuratedLeaf]:
    out: dict[str, CuratedLeaf] = {}
    for code, (branch, bindings) in _data.LEAVES.items():
        built = {}
        for org_id, (account_id, name, postable, reason) in bindings.items():
            if postable and not account_id.isdigit():
                # The whole point of carrying the id is that it is numeric.
                # A non-numeric postable id means the compile read the wrong
                # column, and it must not reach a payload.
                raise CuratedLeavesError(
                    "leaf %s in org %s is postable with a non-numeric "
                    "account_id %r" % (code, org_id, account_id))
            built[org_id] = EntityBinding(
                org_id=org_id, account_id=account_id, name=name,
                postable=postable, reason=reason)
        out[code] = CuratedLeaf(
            code=code, branch=tuple(branch), bindings=MappingProxyType(built))
    if not out:
        raise CuratedLeavesError("the compiled asset carries no leaves")
    for org_id, want in _data.POSTABLE_COUNTS.items():
        got = sum(1 for lf in out.values()
                  if org_id in lf.bindings and lf.bindings[org_id].postable)
        if got != want:
            # A partial load reads exactly like a small chart. The pull this
            # asset replaced truncated silently at a page boundary and nobody
            # noticed for a day, so the count is checked rather than trusted.
            raise CuratedLeavesError(
                "org %s materialised %d postable leaves, asset declares %d"
                % (org_id, got, want))
    return out


@lru_cache(maxsize=1)
def _leaves() -> Mapping[str, CuratedLeaf]:
    return MappingProxyType(_build())


def curated_revision() -> str:
    return _data.CURATED_REVISION


def source_sha256() -> str:
    return _data.SOURCE_SHA256


def curated_orgs() -> tuple[str, ...]:
    return tuple(_data.CURATED_ORG_IDS)


def covers_org(org_id: str | None) -> bool:
    """False for None and for any org outside the compiled set.

    This is the rollout and the rollback lever: an uncovered org refuses rather
    than guessing, so a new entity is opted in by a reviewed diff.
    """
    return bool(org_id) and org_id in _data.CURATED_ORG_IDS


def leaf(code: str | None) -> CuratedLeaf | None:
    if not code:
        return None
    return _leaves().get(code)


def binding(code: str | None, org_id: str | None) -> EntityBinding | None:
    lf = leaf(code)
    if lf is None or not org_id:
        return None
    return lf.bindings.get(org_id)


def is_postable(org_id: str | None, code: str | None) -> bool:
    b = binding(code, org_id)
    return bool(b and b.postable and covers_org(org_id))


def account_id_for(org_id: str | None, code: str | None) -> str | None:
    """The numeric Zoho account_id, or None. Never a name, never a code.

    None is returned for every non-postable case alike; callers that need to
    tell the reasons apart ask `refusal_reason`, which is what lets a refusal
    name the person who has to fix it.
    """
    if not covers_org(org_id):
        return None
    b = binding(code, org_id)
    if b is None or not b.postable:
        return None
    assert b.account_id.isdigit(), b.account_id
    return b.account_id


def refusal_reason(org_id: str | None, code: str | None) -> str:
    """Why this code is not postable here. "" when it is."""
    if not covers_org(org_id):
        return NOT_COVERED
    b = binding(code, org_id)
    if b is None:
        return NO_SUCH_CODE
    return "" if b.postable else b.reason


def postable_codes(org_id: str | None) -> frozenset[str]:
    if not covers_org(org_id):
        return frozenset()
    return frozenset(
        code for code, lf in _leaves().items()
        if org_id in lf.bindings and lf.bindings[org_id].postable)


@lru_cache(maxsize=8)
def llm_leaf_labels(org_id: str | None) -> tuple[str, ...]:
    """"CODE name" per postable leaf, this org's own wording, code order.

    Cached per org because the candidate list is built once per run and a
    per-receipt rebuild would walk the whole chart each time.
    """
    if not covers_org(org_id):
        return ()
    rows = []
    for code in sorted(postable_codes(org_id)):
        b = _leaves()[code].bindings[org_id]
        rows.append("%s %s" % (code, b.name))
    return tuple(rows)


def display_category_for(code: str | None) -> str | None:
    lf = leaf(code)
    return lf.display_category if lf else None


def code_of(ref: str | None, org_id: str | None) -> str | None:
    """Resolve a reference to a curated code, within ONE org.

    Accepts the code itself, an `"CODE name"` label of the shape
    `llm_leaf_labels` emits, or this org's own account name. A name is resolved
    only against the org asked for: the same name means different accounts in
    different entities, and resolving it globally is how a Cloud Services
    account would end up on a Corporate Services expense.
    """
    if not ref or not covers_org(org_id):
        return None
    ref = ref.strip()
    if ref in _leaves():
        return ref
    head = ref.split(None, 1)[0] if ref.split(None, 1) else ""
    if head in _leaves():
        return head
    for code, lf in _leaves().items():
        b = lf.bindings.get(org_id)
        if b is not None and b.name == ref:
            return code
    return None
