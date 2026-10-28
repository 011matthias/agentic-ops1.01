"""One company, one key (item 220 step 5, front 2 of the 2026-09-25 round).

The app holds two spellings of most companies: the provisioning file's
("Corporate Services", what cards and charges carry) and the settings
registry's Zoho legal name ("Brisken Corp Services, LLC"). Both name one org,
but every comparison downstream of a pick compared the label STRING, so a
receipt picked with the long spelling never paired with its own charge (live
August 2026: LOVABLE 15.00 on card 2838 sat unmatched beside its receipt for
this reason alone), and the reviewer's picker offered eight names for five
companies.

``entity_key`` is the one resolver. A label's key is the provisioning
spelling of the label's org when that org has exactly one provisioning
spelling; any other label is its own key. Keying on the org alone would be
wrong: the live registry gives "Brisken Holding, LLC" the org id of
"Brisken GmbH" (696750461; Zoho's own Holding org is 813627567), and an
org-only key would make two companies one. Only a provisioning spelling
joins labels, and neither of those two has one.

Stored values are never rewritten: a row carrying the long spelling keeps
it, and every comparison resolves it through here.
"""
from __future__ import annotations

import os
from typing import Mapping

from .coa_provision import PROVISION_ENV, entity_org_ids, load_provisioning

__all__ = [
    "company_labels",
    "entities_same",
    "entity_key",
    "entity_key_map",
    "norm_entity",
]


def norm_entity(label: str | None) -> str:
    """Case- and whitespace-insensitive form of a company label, the form
    every entity lookup in this package compares on."""
    return " ".join(str(label or "").split()).casefold()


def _provisioning(provisioning: dict | None) -> dict | None:
    if provisioning is not None:
        return provisioning
    path = os.environ.get(PROVISION_ENV)
    try:
        return load_provisioning(path) if path else None
    except Exception:  # noqa: BLE001 - fail-open like every provisioning read
        return None


def entity_key_map(
    settings: dict | None, provisioning: dict | None = None
) -> dict[str, str]:
    """``{norm_entity(label): key}`` for every label the settings registry or
    the provisioning file names. ``provisioning`` defaults to the
    ``EXPENSE_RECON_COA_PROVISION`` file; absent, nothing joins and the map
    says every label is itself."""
    prov = _provisioning(provisioning)
    orgs = entity_org_ids(settings, prov)
    prov_labels = {
        str(k).strip() for k in ((prov or {}).get("entities") or {}) if str(k).strip()
    }
    by_org: dict[str, set[str]] = {}
    for label in prov_labels:
        org = orgs.get(label)
        if org:
            by_org.setdefault(org, set()).add(label)
    spelling = {org: next(iter(s)) for org, s in by_org.items() if len(s) == 1}
    out: dict[str, str] = {}
    for label, org in orgs.items():
        out[norm_entity(label)] = spelling.get(org, label)
    return out


def entity_key(
    label: str | None,
    settings: dict | None = None,
    *,
    keys: Mapping[str, str] | None = None,
) -> str:
    """The company a label names: its org's provisioning spelling, else the
    label as written (trimmed). Blank stays blank. Pass ``keys`` (an
    ``entity_key_map``) when resolving many labels against one settings."""
    text = str(label or "").strip()
    if not text:
        return ""
    if keys is None:
        keys = entity_key_map(settings)
    return keys.get(norm_entity(text), text)


def entities_same(
    a: str | None, b: str | None, keys: Mapping[str, str] | None
) -> bool:
    """Whether two NAMED labels are one company. Either side blank is
    unscoped, never a difference (the matcher's rule since 2026-09-11)."""
    if not str(a or "").strip() or not str(b or "").strip():
        return True
    return norm_entity(entity_key(a, keys=keys or {})) == norm_entity(
        entity_key(b, keys=keys or {})
    )


def company_labels(
    labels, keys: Mapping[str, str], carried=(),
) -> list[str]:
    """One picker name per company: each label's key, deduped on its
    normalized form, first spelling wins. ``carried`` are spellings rows
    actually hold; each is kept as written when its key is not already
    offered under that exact spelling, so a row whose stored company is the
    long form still renders in a select that offers only listed values."""
    out: list[str] = []
    seen: set[str] = set()
    for label in labels:
        key = entity_key(label, keys=keys)
        n = norm_entity(key)
        if key and n not in seen:
            seen.add(n)
            out.append(key)
    offered = {norm_entity(x) for x in out}
    for label in carried:
        text = str(label or "").strip()
        if text and norm_entity(text) not in offered:
            offered.add(norm_entity(text))
            out.append(text)
    return out
