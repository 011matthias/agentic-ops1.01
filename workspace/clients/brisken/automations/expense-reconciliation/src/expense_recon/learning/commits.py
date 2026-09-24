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
