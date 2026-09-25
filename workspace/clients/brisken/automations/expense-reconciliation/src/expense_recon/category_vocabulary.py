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

import json
import os
from datetime import datetime, timezone

from .coa_provision import (
    PROVISION_ENV,
    entity_org_ids,
    load_provisioning,
    org_id_for_entity,
)
from .matching.types import EXPENSE_CATEGORIES
from .zoho import curated_leaves

__all__ = [
    "chart_coverage",
    "gl_account_options",
    "gl_companies",
    "gl_leaf_account_name",
    "gl_leaf_status",
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


def gl_companies(
    settings: dict | None, entity_orgs: dict[str, str] | None = None,
) -> list[dict]:
    """One row per company the curated chart covers (items 180/181):
    ``{label, org_id, labels}``.

    The app holds two spellings of every company, the provisioning file's
    ("Corporate Services", what receipts carry) and the settings registry's
    ("Brisken Corp Services, LLC"), and both name one org. A per-company
    picker built from `gl_account_options` keys would show each company
    twice. `label` is the provisioning spelling when there is one, else the
    alphabetically first; `labels` lists every spelling of that org."""
    if entity_orgs is None:
        entity_orgs = _current_entity_orgs(settings)
    try:
        prov_path = os.environ.get(PROVISION_ENV)
        provisioning = load_provisioning(prov_path) if prov_path else None
    except Exception:  # noqa: BLE001 - presentation, never a reason to 500
        provisioning = None
    preferred = set(entity_org_ids(None, provisioning))
    by_org: dict[str, list[str]] = {}
    for label, org in (entity_orgs or {}).items():
        name, org_id = str(label or "").strip(), str(org or "").strip()
        if not name or not curated_leaves.covers_org(org_id):
            continue
        by_org.setdefault(org_id, []).append(name)
    out = []
    for org_id, labels in by_org.items():
        labels = sorted(set(labels))
        best = [lbl for lbl in labels if lbl in preferred] or labels
        out.append({"label": best[0], "org_id": org_id, "labels": labels})
    return sorted(out, key=lambda r: r["label"].lower())


def gl_leaf_status(code: str | None, org_id: str | None) -> dict:
    """What one curated leaf CODE is in one org (items 180-181, 172):
    ``{code, name, postable, reason}``. `name` is this org's own wording (""
    when the org has no such account); `reason` is "" when postable, else
    the refusal code the engine would give (`curated_leaves.refusal_reason`).
    Never raises on a malformed asset: a settings render must not 500."""
    try:
        b = curated_leaves.binding(code, org_id)
        return {
            "code": code or "",
            "name": b.name if b is not None else "",
            "postable": curated_leaves.is_postable(org_id, code),
            "reason": curated_leaves.refusal_reason(org_id, code),
        }
    except curated_leaves.CuratedLeavesError:
        return {"code": code or "", "name": "", "postable": False,
                "reason": "chart_unreadable"}


def gl_leaf_account_name(
    code: str | None, entity: str | None, entity_orgs: dict | None
) -> str | None:
    """Item 201: the account a curated leaf CODE names in this row's company.

    On a GL month the category IS the account: a hand pick stores only the
    code (`E100010-31`), and the name the export needs sits in the company's
    curated chart. Resolved at READ time from the row's company as it stands
    now, never stored at save time, so a company change afterwards reads the
    new company's wording (`CorpServ | Travel Expense | Food` against
    `Travel Expense | Food` for the same code).

    Returns the same name the engine stamps for its own pick
    (`categorize._gl_categorization`). None on a bucket month (no map), for a
    blank or uncurated company, and for a code this company cannot post to:
    the row then keeps its visible "(account unmapped - assign)".
    """
    if not entity_orgs or not code:
        return None
    org_id = org_id_for_entity(entity, entity_orgs)
    if not curated_leaves.is_postable(org_id, code):
        return None
    binding = curated_leaves.binding(code, org_id)
    return binding.name if binding is not None else None


_COVERAGE_CACHE: dict[tuple, dict] = {}


def chart_coverage(provisioning_path: str | None = None) -> dict | None:
    """Item 207: which of Dirk's postable accounts the export check's chart
    file does not hold, per curated company.

    The export gate checks every account against the chart file the
    provisioning names (`chart_path`), on the server's disk. On 2026-09-25
    that file was the 1 July pull, which predates 18 of the 64 accounts Dirk
    marks postable for Cloud Services, and the gate blanked each one to
    "(account unmapped - assign)" with nothing to say why. This names the
    gap: `missing` lists the leaf codes whose account id the file lacks.

    Read from the provisioning file (default: `EXPENSE_RECON_COA_PROVISION`)
    and cached on the chart file's mtime and size, because `/healthz` asks
    every 30 seconds. None when nothing is provisioned; an unreadable chart
    answers with `error` rather than raising.
    """
    path = provisioning_path or os.environ.get(PROVISION_ENV)
    prov = load_provisioning(path) if path else None
    if not prov:
        return None
    chart_path = str(prov.get("chart_path") or "")
    try:
        st = os.stat(chart_path)
    except OSError as exc:
        return {"chart_path": chart_path, "error": f"{type(exc).__name__}: {exc}"}
    key = (chart_path, st.st_mtime_ns, st.st_size, repr(prov.get("entities")))
    if key in _COVERAGE_CACHE:
        return _COVERAGE_CACHE[key]
    try:
        with open(chart_path, encoding="utf-8") as f:
            chart = json.load(f)
    except (OSError, ValueError) as exc:
        return {"chart_path": chart_path, "error": f"{type(exc).__name__}: {exc}"}
    companies = []
    for label, spec in sorted((prov.get("entities") or {}).items()):
        org_id = str((spec or {}).get("org_id") or "")
        if not curated_leaves.covers_org(org_id):
            continue
        held = {
            str(a.get("account_id"))
            for a in ((chart.get(org_id) or {}).get("accounts") or [])
            if isinstance(a, dict)
        }
        codes = sorted(curated_leaves.postable_codes(org_id))
        companies.append({
            "company": label,
            "org_id": org_id,
            "n_postable": len(codes),
            "missing": [
                c for c in codes
                if curated_leaves.account_id_for(org_id, c) not in held
            ],
        })
    out = {
        "chart_path": chart_path,
        "chart_modified": datetime.fromtimestamp(st.st_mtime, timezone.utc)
        .isoformat(timespec="seconds"),
        "chart_bytes": st.st_size,
        "companies": companies,
        "ok": not any(c["missing"] for c in companies),
    }
    _COVERAGE_CACHE.clear()
    _COVERAGE_CACHE[key] = out
    return out
