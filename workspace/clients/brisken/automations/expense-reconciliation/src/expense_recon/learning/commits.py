"""Item 163: a memory save is a PLAN first, then an apply.

Feedback note #81 (2026-09-23), on the "Save corrections to memory" button:
"based on what? this should be reversible for now, and state explicitly
where these are saved so user can manage this". Three asks, one mechanism:
the writes a save would make are computed as a list BEFORE anything is
written, so the same list can be shown before the click, recorded with the
pre-image of every row it touches, and put back afterwards.

`RecordingStore` stands in for a `LearningStore` while the capture module's
learners run: it accepts the five `record_*` calls they make and keeps them
as `PlannedWrite`s instead of writing. `apply_plan` replays those calls on
a real store. What the preview listed and what the save wrote are therefore
one list by construction, not two code paths kept in step by hand.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Primary-key columns per learning table, in the order the `record_*` call
# passes them: the leading positional arguments of each call ARE the key.
TABLE_KEYS: dict[str, tuple[str, ...]] = {
    "merchant_category": ("legal_entity_id", "vendor_norm"),
    "merchant_entity": ("vendor_norm",),
    "field_correction": ("legal_entity_id", "vendor_norm", "field"),
    "vendor_alias": ("legal_entity_id", "stmt_vendor_norm", "receipt_vendor_norm"),
    "merchant_fx": ("legal_entity_id", "vendor_norm", "from_ccy", "to_ccy"),
}

_METHOD_TABLE: dict[str, str] = {
    "record_merchant_category": "merchant_category",
    "record_merchant_entity": "merchant_entity",
    "record_field_correction": "field_correction",
    "record_vendor_alias": "vendor_alias",
    "record_merchant_fx": "merchant_fx",
    # Item 246: a save replaces the rules recall folds into the one it writes
    # (`one_rule_per_merchant`). Never called by a learner.
    "delete_merchant_category": "merchant_category",
}


@dataclass(frozen=True)
class PlannedWrite:
    """One `record_*` call a save would make: which table, which primary
    key (as strings, in `TABLE_KEYS` order) and the exact arguments."""

    table: str
    key: tuple[str, ...]
    method: str
    args: tuple[Any, ...]
    # Item 183: `record_merchant_category` takes `keep_account`, and a plan
    # that dropped it would preview "the account is kept" and then apply a
    # write that wipes it. A dry run is only exact if it carries the whole
    # call.
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def key_dict(self) -> dict[str, str]:
        return dict(zip(TABLE_KEYS[self.table], self.key))

    @property
    def is_delete(self) -> bool:
        return self.method.startswith("delete_")


class RecordingStore:
    """A `LearningStore` look-alike that records instead of writing.

    The learners in `learning.capture` only ever CALL `record_*`; they read
    nothing back, which is what makes a dry run exact rather than
    approximate."""

    def __init__(self, _db_path: Any = None) -> None:
        self.writes: list[PlannedWrite] = []

    # The learners are called inside `with LearningStore(path) as store:`,
    # so the stand-in is a context manager taking the same one argument.
    def __enter__(self) -> "RecordingStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        table = _METHOD_TABLE[method]
        n = len(TABLE_KEYS[table])
        key = tuple("" if a is None else str(a) for a in args[:n])
        self.writes.append(
            PlannedWrite(table, key, method, tuple(args), dict(kwargs))
        )

    def record_merchant_category(self, *args: Any, **kwargs: Any) -> None:
        self._record("record_merchant_category", *args, **kwargs)

    def record_merchant_entity(self, *args: Any, **kwargs: Any) -> None:
        self._record("record_merchant_entity", *args, **kwargs)

    def record_field_correction(self, *args: Any, **kwargs: Any) -> None:
        self._record("record_field_correction", *args, **kwargs)

    def record_vendor_alias(self, *args: Any, **kwargs: Any) -> None:
        self._record("record_vendor_alias", *args, **kwargs)

    def record_merchant_fx(self, *args: Any, **kwargs: Any) -> None:
        self._record("record_merchant_fx", *args, **kwargs)


def one_rule_per_merchant(
    writes: list[PlannedWrite], stored: list, identity: Any,
) -> list[PlannedWrite]:
    """Item 246 (owner 2026-10-07: "when save to memory is clicked the
    existing rule for that case is overwritten"): each category write also
    replaces the rules stored for the same merchant in the same company under
    another spelling.

    Recall folds every spelling of one merchant into one identity
    (`MerchantCategoryLookup`), and when those rules disagree it folds none of
    them: each spelling keeps answering for itself. So a save written under
    `anthropic` left a rule under `anthropic pbc` answering every receipt
    spelled that way, and the Memory page still showed it. Here the save
    deletes those rules, and the one it writes is the case's only rule.

    A write that keeps a half it did not name (`keep_category` /
    `keep_account`, item 183) takes that half from the rules being replaced,
    the person's over the seeded, so deleting them loses nothing. When those
    rules disagree on that half, nothing says which to keep, and the write is
    left exactly as the learner made it, siblings and all.

    `stored` is every `MerchantCategory` row; `identity` the resolver recall
    uses (`MerchantIdentityResolver`). Pure: it reads nothing and writes
    nothing, so the plan, the lessons and the save expand the same way."""
    from .consult import _person_row

    if not writes or not stored or identity is None:
        return list(writes)

    def ikey(vendor: str) -> str:
        return identity.key(vendor) or vendor

    out: list[PlannedWrite] = []
    for w in writes:
        if w.method != "record_merchant_category":
            out.append(w)
            continue
        entity, vendor = w.key
        target = ikey(vendor)
        case = [r for r in stored
                if r.legal_entity_id == entity and ikey(r.vendor_norm) == target]
        siblings = [r for r in case if r.vendor_norm != vendor]
        if not siblings:
            out.append(w)
            continue
        deciding = [r for r in case if _person_row(r)] or case
        args = list(w.args)
        ambiguous = False
        for keep, index, column in (
            ("keep_category", 2, "category"), ("keep_account", 3, "zoho_account"),
        ):
            if not w.kwargs.get(keep):
                continue
            values = {getattr(r, column) for r in deciding if getattr(r, column)}
            if len(values) > 1:
                ambiguous = True
                break
            args[index] = values.pop() if values else None
        if ambiguous:
            out.append(w)
            continue
        out.append(PlannedWrite(w.table, w.key, w.method, tuple(args), {}))
        for r in siblings:
            key = (r.legal_entity_id, r.vendor_norm)
            out.append(PlannedWrite(
                "merchant_category", key, "delete_merchant_category", key, {},
            ))
    return out


def apply_plan(store: Any, writes: list[PlannedWrite]) -> int:
    """Replay the plan on a real `LearningStore`, in order. Returns the
    number of calls made."""
    for w in writes:
        getattr(store, w.method)(*w.args, **(w.kwargs or {}))
    return len(writes)


def distinct_keys(writes: list[PlannedWrite]) -> list[tuple[str, tuple[str, ...]]]:
    """Every `(table, key)` a plan touches, first-seen order, no repeats
    (an FX key can be written several times in one save)."""
    out: list[tuple[str, tuple[str, ...]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for w in writes:
        k = (w.table, w.key)
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def registry_diff(before: dict | None, after: dict | None) -> dict[str, dict]:
    """`{merchant: {"before": entry|None, "after": entry|None}}` for every
    registry entry a save changes, adds or (never today) removes. Both maps
    absent means the plan had no registry half; an unchanged map yields
    `{}`."""
    b = before or {}
    a = after or {}
    out: dict[str, dict] = {}
    for name in sorted(set(b) | set(a)):
        if b.get(name) != a.get(name):
            out[name] = {"before": b.get(name), "after": a.get(name)}
    return out
