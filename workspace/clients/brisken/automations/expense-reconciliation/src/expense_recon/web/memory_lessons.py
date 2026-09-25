"""Item 183 half A: Publish shows what it will remember, one lesson per tick.

Item 163 made a memory save a plan first (`learning.commits`): the real
learners run against `RecordingStore`, so the preview and the save are one
list. This module cuts that list into LESSONS a reviewer ticks on the Publish
checklist, and turns the ticks back into exactly the writes that are made.

- A lesson is one learning row (`merchant_category:<entity>|<vendor>`, ...) or
  one merchant-list entry (`registry:<merchant>`). Its id is derived from the
  table and the key, so the same correction offers the same id every time.
- Corrections start ticked. A conflict (rows that disagree, which the
  learners refuse since item 183 half B) is offered as one UNTICKED lesson
  per candidate value; a ticked candidate is written by re-running the real
  learner over that candidate's rows, never by a call built here.
- OpenAI, Anthropic and Lovable are owner-gated in the merchant list: their
  registry lesson is shown, never ticked, and refused if sent as kept.
- Item 219: a merchant whose accounts are decided (`accounts_locked`) is never
  re-pointed by a correction. Rows booked in a company to an account other
  than the decided one are offered as ONE unticked drift lesson per account
  ("change the default for <vendor> in <company>?"); ticking it is the only
  learner path that changes that company's account. The memory rule the same
  rows would teach rides inside it and is never written on its own.

Owner decisions (2026-09-25): corrections ticked, conflicts unticked; an
unticked lesson is dropped and offered again next time (no declined store);
Publish with nothing ticked still publishes.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from ..category_vocabulary import gl_leaf_status, gl_postable_ref
from ..coa_provision import org_id_for_entity
from ..learning import (
    TABLE_KEYS,
    RecordingStore,
    category_groups,
    learn_category_candidate,
    learn_from_expense_run,
    merge_taught,
    normalize_vendor,
)
from ..learning.capture import category_key
from ..merchant_identity import identity_key
from ..merchant_registry import company_account, is_accounts_locked

KIND_CORRECTION = "correction"
KIND_CONFLICT = "conflict"
KIND_DRIFT = "drift"
REGISTRY = "registry"

# Owner 2026-09-18: these three are written into the merchant list only when
# the owner raises it. A lesson about them is shown and never written.
OWNER_GATED_MERCHANTS = ("anthropic", "openai", "lovable")


def is_owner_gated(merchant: str | None) -> bool:
    squashed = normalize_vendor(merchant or "").replace(" ", "")
    return any(squashed.startswith(g) for g in OWNER_GATED_MERCHANTS)


def lesson_id(table: str, key) -> str:
    return f"{table}:{'|'.join(str(k) for k in key)}"


@dataclass
class Lesson:
    id: str
    kind: str
    table: str
    key: dict
    description: str
    sources: list[dict]
    default_keep: bool
    owner_gated: bool = False
    conflict_group: str = ""
    # Not served: what applying the lesson needs.
    writes: list = field(default_factory=list)
    merchant: str = ""
    rows: list = field(default_factory=list)

    def view(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "table": self.table,
            "key": self.key,
            "description": self.description,
            "sources": self.sources,
            "default_keep": self.default_keep,
            "owner_gated": self.owner_gated,
            "conflict_group": self.conflict_group,
        }


@dataclass
class LessonContext:
    """Everything the lessons are built from, read once per plan."""

    run: Any
    writes: list
    merchants_before: dict
    merchants_after: dict | None
    overrides: dict
    field_overrides: dict
    receipts: list
    effective: list
    manual_payloads: dict
    rec_by_id: dict
    gl: dict | None
    now_iso: str
    # Item 216 cause 3: the resolver the learners keyed this plan's rows
    # with, so a lesson's rows and a conflict candidate's re-learn use the
    # same key; and, per merchant, the person-confirmed pairings
    # `(transaction_id, document_id)` behind a new spelling in its entry.
    identity: Any = None
    alias_pairs: dict = field(default_factory=dict)


# ── describing ──────────────────────────────────────────────────────────


def _company(ctx: LessonContext, entity: str) -> tuple[str, str | None]:
    """(the company's display name, its org id on a GL month)."""
    if not ctx.gl:
        return entity or "no company", None
    org = org_id_for_entity(entity, ctx.gl.get("entity_orgs") or {})
    return (ctx.gl.get("labels") or {}).get(org or "", entity or "no company"), org


def _account_text(code: str | None, org: str | None) -> str:
    if not code:
        return ""
    name = gl_leaf_status(code, org).get("name") if org else ""
    return f"{code} {name}".strip()


def _value_text(category, account, org=None) -> str:
    parts = []
    if category:
        parts.append(f"category {_account_text(category, org) if org else category}")
    if account:
        parts.append(f"account {_account_text(account, org) if org else account}")
    return " and ".join(parts) or "nothing"


def _row_source(ctx: LessonContext, document_id: str, line_index=None) -> dict:
    r = ctx.rec_by_id.get(document_id)
    out = {
        "document_id": document_id,
        "kind": "charge" if document_id.startswith("charge:") else "receipt",
        "vendor": (r.detected_vendor if r else "") or "",
        "date": r.detected_date.isoformat() if r and r.detected_date else "",
        "total": str(r.detected_total) if r and r.detected_total is not None else "",
        "currency": (r.detected_currency if r else "") or "",
    }
    if line_index is not None:
        out["line_index"] = line_index
    return out


def _rows_text(sources: list[dict]) -> str:
    if not sources:
        return ""
    shown = ", ".join(
        " ".join(p for p in (s["vendor"], s["total"], s["currency"], s["date"]) if p)
        for s in sources[:3]
    )
    more = f" and {len(sources) - 3} more" if len(sources) > 3 else ""
    noun = "row" if len(sources) == 1 else "rows"
    return f" From {len(sources)} corrected {noun}: {shown}{more}."


# ── attributing a learning row to the rows that taught it ───────────────


def _field_sources(ctx: LessonContext) -> dict[tuple, list[str]]:
    """`(table, key) -> [document ids]` for the entity and field-correction
    rows, found by running the real learner over ONE row at a time and
    reading which key it writes, so attribution cannot drift from teaching."""
    out: dict[tuple, list[str]] = {}

    def _run(field_overrides, manual):
        rec = RecordingStore()
        learn_from_expense_run(
            rec, receipts=ctx.receipts, effective_receipts=ctx.effective,
            field_overrides=field_overrides, category_overrides={},
            manual_payloads=manual, transactions=None,
            source_run=ctx.run.run_id, now_iso=ctx.now_iso,
        )
        return rec.writes

    singles = [({doc: fields}, None, doc) for doc, fields in ctx.field_overrides.items()]
    singles += [({}, {doc: p}, doc) for doc, p in ctx.manual_payloads.items()]
    for fo, manual, doc in singles:
        for w in _run(fo, manual):
            ids = out.setdefault((w.table, w.key), [])
            if doc not in ids:
                ids.append(doc)
    return out


# ── the lessons ─────────────────────────────────────────────────────────


def _describe_write(ctx: LessonContext, table: str, key: tuple, last) -> str:
    if table == "merchant_category":
        entity, vendor = key
        company, org = _company(ctx, entity)
        return f"{vendor} in {company}: {_value_text(last.args[2], last.args[3], org)}."
    if table == "merchant_entity":
        return f"{key[0]} belongs to {last.args[1]}."
    if table == "field_correction":
        entity, vendor, fname = key
        company, _org = _company(ctx, entity)
        return f"{vendor} in {company}: its {fname} reads {last.args[3]}."
    if table == "vendor_alias":
        return f"The bank's {key[1]} is the receipt vendor {key[2]}."
    if table == "merchant_fx":
        return f"{key[1]}: {key[2]} to {key[3]} at {last.args[4]}."
    return f"{table} {'|'.join(key)}."


def _registry_changes(before: dict | None, after: dict | None) -> str:
    b, a = before or {}, after or {}
    parts = []
    new_aliases = [x for x in a.get("aliases") or [] if x not in (b.get("aliases") or [])]
    if new_aliases:
        parts.append("new spelling " + ", ".join(new_aliases))
    for fld, label in (("category", "category"), ("zoho_account", "account"),
                       ("cost_center", "cost center"), ("card_key", "card")):
        if a.get(fld) != b.get(fld) and a.get(fld):
            parts.append(f"{label} {a.get(fld)}")
    accounts_a, accounts_b = a.get("accounts") or {}, b.get("accounts") or {}
    for company in sorted(accounts_a):
        if accounts_a[company] != accounts_b.get(company):
            parts.append(f"account in {company} {accounts_a[company]}")
    seen = [c for c in a.get("cards_seen") or [] if c not in (b.get("cards_seen") or [])]
    if seen:
        parts.append("seen on card " + ", ".join(seen))
    return "; ".join(parts) or "entry updated"


def _registry_rows(ctx: LessonContext, merchant: str) -> list[tuple]:
    from .service import registry_category_groups

    groups = registry_category_groups(
        effective_receipts=ctx.effective, field_overrides=ctx.field_overrides,
        category_overrides=ctx.overrides, gl=ctx.gl,
    )
    rows: list[tuple] = []
    for (canonical, _company), members in groups.items():
        if canonical == merchant:
            rows += [row for row, _v in members if row not in rows]
    return rows


def _registry_candidate(ctx: LessonContext, base: dict, rows: list[tuple]) -> dict:
    """The merchant list the REAL registry learner writes from `rows` alone."""
    from .service import registry_upserts_from_expense_run

    docs = {doc for doc, _line in rows}
    out, _summary = registry_upserts_from_expense_run(
        base,
        receipts=ctx.receipts,
        effective_receipts=ctx.effective,
        field_overrides={d: f for d, f in ctx.field_overrides.items() if d in docs},
        category_overrides={k: ctx.overrides[k] for k in rows if k in ctx.overrides},
        gl=ctx.gl,
    )
    return out


def _drift_lessons(ctx: LessonContext, cat_groups: dict) -> tuple[list[Lesson], set]:
    """Item 219: `(drift lessons, the memory keys they replace)`.

    A memory group `(company, merchant)` is a decided cell when the merchant
    is locked in the merchant list and its map names an account for that
    company (matched on the org, as the categorizer matches it). Rows there
    booked to another postable account are drift, one lesson per account,
    unticked; their memory rule is folded into the lesson. A cell whose rows
    all agree with the decision keeps its ordinary lesson."""
    if not ctx.gl:
        return [], set()
    locked = {
        identity_key(name): name
        for name, entry in ctx.merchants_before.items()
        if is_accounts_locked(entry)
    }
    entity_orgs = ctx.gl.get("entity_orgs") or {}
    lessons: list[Lesson] = []
    folded: set = set()
    for key, members in cat_groups.items():
        entity, vendor = key
        merchant = locked.get(vendor)
        if not merchant:
            continue
        company, org = _company(ctx, entity)
        decided = company_account(
            ctx.merchants_before[merchant].get("accounts") or {}, org, entity_orgs)
        if decided is None:
            continue
        label, decided_code = decided
        by_code: dict[str, list] = {}
        for row, (category, account) in members:
            code = next(
                (c for c in (gl_postable_ref(ref, org) for ref in (category, account)) if c),
                None,
            )
            if code and code != decided_code:
                by_code.setdefault(code, []).append(row)
        if not by_code:
            continue
        folded.add(key)
        total = sum(
            1 for r in ctx.rec_by_id.values() if category_key(r, ctx.identity) == key
        )
        group = f"drift:{merchant}|{label}"
        for code, rows in by_code.items():
            rec = RecordingStore()
            learn_category_candidate(
                rec, ctx.rec_by_id, ctx.overrides, rows, ctx.run.run_id, ctx.now_iso,
                identity=ctx.identity,
            )
            sources = [_row_source(ctx, d, ln) for d, ln in rows]
            booked = len({d for d, _ln in rows})
            lessons.append(Lesson(
                id=f"{group}:{code}",
                kind=KIND_DRIFT,
                table=REGISTRY,
                key={"merchant": merchant, "company": label, "account": code},
                description=(
                    f"Change the default for {merchant} in {company} to "
                    f"{_account_text(code, org)}? {booked} of this month's "
                    f"{max(total, booked)} {merchant} rows there were booked to it; "
                    f"the decided account is {_account_text(decided_code, org)}."
                    + _rows_text(sources)
                ),
                sources=sources,
                default_keep=False,
                conflict_group=group,
                writes=rec.writes,
                merchant=merchant,
                rows=rows,
            ))
    return lessons, folded


def build_lessons(ctx: LessonContext) -> list[Lesson]:
    lessons: list[Lesson] = []

    # 1) Learning rows, one lesson per (table, key), in first-write order.
    by_key: dict[tuple, list] = {}
    for w in ctx.writes:
        by_key.setdefault((w.table, w.key), []).append(w)
    cat_groups = category_groups(ctx.rec_by_id, ctx.overrides, ctx.identity)
    drift, folded = _drift_lessons(ctx, cat_groups)
    field_src = _field_sources(ctx) if ctx.field_overrides or ctx.manual_payloads else {}
    for (table, key), writes in by_key.items():
        if table == "merchant_category" and key in folded:
            continue
        if table == "merchant_category":
            sources = [_row_source(ctx, d, ln) for (d, ln), _v in cat_groups.get(key, [])]
        else:
            sources = [_row_source(ctx, d) for d in field_src.get((table, key), [])]
        lessons.append(Lesson(
            id=lesson_id(table, key),
            kind=KIND_CORRECTION,
            table=table,
            key=dict(zip(TABLE_KEYS[table], key)),
            description=_describe_write(ctx, table, key, writes[-1]) + _rows_text(sources),
            sources=sources,
            default_keep=True,
            writes=writes,
        ))

    # 2) Merchant-list entries, one lesson per merchant the save changes.
    after = ctx.merchants_after if ctx.merchants_after is not None else ctx.merchants_before
    for merchant in sorted(set(ctx.merchants_before) | set(after)):
        b, a = ctx.merchants_before.get(merchant), after.get(merchant)
        if b == a:
            continue
        gated = is_owner_gated(merchant)
        sources = [_row_source(ctx, d, ln) for d, ln in _registry_rows(ctx, merchant)]
        for tx_id, doc in ctx.alias_pairs.get(merchant, ()):
            sources += [_row_source(ctx, f"charge:{tx_id}"), _row_source(ctx, doc)]
        held = " Held for the owner: never written from a checklist." if gated else ""
        lessons.append(Lesson(
            id=lesson_id(REGISTRY, (merchant,)),
            kind=KIND_CORRECTION,
            table=REGISTRY,
            key={"merchant": merchant},
            description=(f"Merchant list, {merchant}: {_registry_changes(b, a)}."
                         + _rows_text(sources) + held),
            sources=sources,
            default_keep=not gated,
            owner_gated=gated,
            merchant=merchant,
        ))

    # 3) Conflicts, one UNTICKED lesson per candidate value.
    for key, members in cat_groups.items():
        if key in folded or not merge_taught(v for _r, v in members)[2]:
            continue
        entity, vendor = key
        company, org = _company(ctx, entity)
        group = lesson_id("merchant_category", key)
        for value in dict.fromkeys(v for _r, v in members):
            rows = [r for r, v in members if v == value]
            rec = RecordingStore()
            learn_category_candidate(
                rec, ctx.rec_by_id, ctx.overrides, rows, ctx.run.run_id, ctx.now_iso,
                identity=ctx.identity,
            )
            sources = [_row_source(ctx, d, ln) for d, ln in rows]
            lessons.append(Lesson(
                id=f"conflict:{group}:{value[0] or ''}|{value[1] or ''}",
                kind=KIND_CONFLICT,
                table="merchant_category",
                key={"legal_entity_id": entity, "vendor_norm": vendor},
                description=(f"{vendor} in {company}: rows disagree. This option "
                             f"remembers {_value_text(*value, org)}." + _rows_text(sources)),
                sources=sources,
                default_keep=False,
                conflict_group=group,
                writes=rec.writes,
                rows=rows,
            ))

    from .service import registry_category_groups

    reg_groups = registry_category_groups(
        effective_receipts=ctx.effective, field_overrides=ctx.field_overrides,
        category_overrides=ctx.overrides, gl=ctx.gl,
    )
    for (merchant, company), members in reg_groups.items():
        if not merge_taught(v for _r, v in members)[2]:
            continue
        gated = is_owner_gated(merchant)
        group = lesson_id(REGISTRY, (merchant, company))
        where = f" in {company}" if company else ""
        for value in dict.fromkeys(v for _r, v in members):
            rows = [r for r, v in members if v == value]
            candidate = _registry_candidate(ctx, ctx.merchants_before, rows)
            if candidate.get(merchant) == ctx.merchants_before.get(merchant):
                continue
            sources = [_row_source(ctx, d, ln) for d, ln in rows]
            held = " Held for the owner: never written from a checklist." if gated else ""
            lessons.append(Lesson(
                id=f"conflict:{group}:{value[0] or ''}|{value[1] or ''}",
                kind=KIND_CONFLICT,
                table=REGISTRY,
                key={"merchant": merchant, "company": company},
                description=(f"Merchant list, {merchant}{where}: rows disagree. This "
                             f"option remembers {_value_text(*value)}."
                             + _rows_text(sources) + held),
                sources=sources,
                default_keep=False,
                owner_gated=gated,
                conflict_group=group,
                merchant=merchant,
                rows=rows,
            ))
    return lessons + drift


# ── from ticks to writes ────────────────────────────────────────────────


def select(lessons: list[Lesson], keep=None, skip=None) -> dict:
    """Which lesson ids are written. `keep` (when given) is the whole list of
    ticked ids; otherwise the defaults stand, minus `skip`. An owner-gated
    lesson is never kept, and ids the plan does not hold are named."""
    ids = {lsn.id for lsn in lessons}
    if keep is not None:
        wanted = {str(k) for k in keep}
        unknown = sorted(wanted - ids)
        kept = wanted & ids
    else:
        dropped = {str(s) for s in (skip or ())}
        unknown = sorted(dropped - ids)
        kept = {lsn.id for lsn in lessons if lsn.default_keep} - dropped
    gated = {lsn.id for lsn in lessons if lsn.owner_gated}
    return {
        "kept": [lsn.id for lsn in lessons if lsn.id in kept - gated],
        "skipped": [lsn.id for lsn in lessons if lsn.id not in kept],
        "refused_owner_gated": [lsn.id for lsn in lessons if lsn.id in kept & gated],
        "unknown": unknown,
    }


def apply_selection(ctx: LessonContext, lessons: list[Lesson], kept_ids) -> dict:
    """The learning writes and the merchant list for the kept lessons only.

    Main lessons contribute the writes the plan recorded for their key, in
    the plan's order. Kept conflict candidates are re-learned per group over
    the UNION of their rows by the real learner: one candidate writes its
    value, two that disagree teach nothing (`unresolved`), exactly as the
    learner would have answered."""
    kept = set(kept_ids)
    by_id = {lsn.id: lsn for lsn in lessons}
    main_keys = {
        (lsn.table, tuple(lsn.key.values()))
        for lsn in lessons
        if lsn.id in kept and lsn.kind == KIND_CORRECTION and lsn.table != REGISTRY
    }
    writes = [w for w in ctx.writes if (w.table, w.key) in main_keys]

    merchants = copy.deepcopy(ctx.merchants_before)
    after = ctx.merchants_after if ctx.merchants_after is not None else ctx.merchants_before
    for lsn in lessons:
        if lsn.id in kept and lsn.kind == KIND_CORRECTION and lsn.table == REGISTRY:
            if lsn.merchant in after:
                merchants[lsn.merchant] = copy.deepcopy(after[lsn.merchant])
            else:
                merchants.pop(lsn.merchant, None)

    unresolved: list[str] = []
    groups: dict[str, list[Lesson]] = {}
    drift: dict[str, list[Lesson]] = {}
    for lid in kept:
        lsn = by_id[lid]
        if lsn.kind == KIND_CONFLICT:
            groups.setdefault(lsn.conflict_group, []).append(lsn)
        elif lsn.kind == KIND_DRIFT:
            drift.setdefault(lsn.conflict_group, []).append(lsn)
    # Item 219: a ticked drift lesson re-points ONE company's decided account
    # and writes the memory rule its rows teach. Two accounts ticked for one
    # company decide nothing.
    for group, members in sorted(drift.items()):
        if len(members) != 1:
            unresolved.append(group)
            continue
        lsn = members[0]
        entry = copy.deepcopy(merchants.get(lsn.merchant) or {})
        entry["accounts"] = dict(sorted({
            **(entry.get("accounts") or {}), lsn.key["company"]: lsn.key["account"],
        }.items()))
        merchants[lsn.merchant] = entry
        writes.extend(lsn.writes)
    for group, members in sorted(groups.items()):
        rows = [r for lsn in members for r in lsn.rows]
        if members[0].table == REGISTRY:
            merchant = members[0].merchant
            out = _registry_candidate(ctx, merchants, rows)
            if out.get(merchant) == merchants.get(merchant):
                unresolved.append(group)
            elif merchant in out:
                merchants[merchant] = copy.deepcopy(out[merchant])
            continue
        rec = RecordingStore()
        n_written, _n_conflict = learn_category_candidate(
            rec, ctx.rec_by_id, ctx.overrides, rows, ctx.run.run_id, ctx.now_iso,
            identity=ctx.identity,
        )
        if not n_written:
            unresolved.append(group)
        writes.extend(rec.writes)
    return {"writes": writes, "merchants": merchants, "unresolved_conflicts": unresolved}
