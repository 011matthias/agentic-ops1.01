"""Cost centers — a settings-backed dimension attributing spend to projects
and purposes (backlog item 47, owner directive 2026-09-08, build ordered
2026-09-10).

Sibling to category, legal entity and person: one more fact about an expense
row, resolved through the same override > learned > registry chain the rest
of the tool already uses, and never guessed silently.

Dirk's own examples are deliberately heterogeneous — Lidar is a project,
marketing is a function, Brazil is a trip, work on this tool is a person's —
so the registry is ONE FLAT LIST carrying a display-only ``kind``. No
hierarchy in v1.

Shape::

    settings["cost_centers"] = {
        "<name>": {
            "kind": "project" | "function" | "trip" | "",
            "note": "",
            "active": bool,
        },
        ...
    }

**The list is owner-authored, full stop** (design D1, decided against the
recommended grow-while-reviewing option). The tool never invents a cost
center and never learns a new NAME; learning only ever re-uses a name the
owner has already defined. ``kind`` groups the roll-up and never
participates in resolution.

**The empty-registry contract, which is the load-bearing part.** An empty
registry resolves nothing AND flags nothing. This mirrors the merchant
registry's own contract ("an empty registry resolves nothing, so a tenant
with no ``merchants`` key behaves exactly as before"), and without it the
day this field ships every row in every month reads ``needs_cost_center``.
A review state that fires at 100% is noise, not signal. The flag starts
firing only once the owner has defined at least one cost center, because
only then does "this row has none" mean anything.

**Resolution order** (``resolve``): explicit override, then the trip, then
the learned merchant default, then the card's ``default_cost_center``, else
unresolved. Person is deliberately NOT a resolver: it cannot separate
Dirk's own "Nicolas in Brazil" from "Nicolas on Lidar", and only ranks the
picker. Category is not one either — co-varying the two dimensions destroys
the point of cutting the money a second way.

v1 refuses splits: one row, one cost center. The v2 shape, if a genuinely
shared cost turns up, is per-line-item through the ``books_as`` fan-out.
"""
from __future__ import annotations

from dataclasses import dataclass

# Display-only grouping for the roll-up. Never consulted during resolution.
COST_CENTER_KINDS = ("project", "function", "trip", "")

# Resolution sources, in the order `resolve` tries them. The enum travels on
# the API beside a human-readable label (contract rule 5).
SOURCE_OVERRIDE = "override"
SOURCE_TRIP = "trip"
SOURCE_MERCHANT = "merchant"
SOURCE_CARD = "card"
SOURCE_NONE = ""

_SOURCE_LABELS = {
    SOURCE_OVERRIDE: "set by reviewer",
    SOURCE_TRIP: "from the trip",
    SOURCE_MERCHANT: "learned for this merchant",
    SOURCE_CARD: "default for this card",
    SOURCE_NONE: "",
}


@dataclass(frozen=True)
class CostCenterResolution:
    """What the chain decided for one expense row.

    ``needs`` is the review flag and is NOT simply ``name is None``: an
    empty registry leaves every row unresolved and flags none of them.
    """

    name: str | None
    source: str
    needs: bool

    @property
    def source_label(self) -> str:
        return _SOURCE_LABELS.get(self.source, "")

    def as_fields(self) -> dict:
        """The parallel API fields (contract rule 1: never repurpose an
        existing name, add beside it)."""
        return {
            "cost_center": self.name,
            "cost_center_source": self.source,
            "cost_center_source_label": self.source_label,
            "needs_cost_center": self.needs,
        }


UNRESOLVED_SILENT = CostCenterResolution(None, SOURCE_NONE, False)


class CostCenterRegistry:
    """The owner-authored list, and the resolution chain over it."""

    def __init__(self, cost_centers: object | None = None) -> None:
        entries: dict[str, dict] = {}
        if isinstance(cost_centers, dict):
            for name, entry in cost_centers.items():
                key = str(name or "").strip()
                if key and isinstance(entry, dict):
                    entries[key] = entry
        self._entries = entries
        # Case-insensitive lookup, because a picked name and a learned name
        # can differ only in case and they are the same cost center.
        self._by_key = {k.casefold(): k for k in entries}

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> dict[str, dict]:
        return dict(self._entries)

    def canonical(self, name: object) -> str | None:
        """The registry's own spelling of ``name``, or None when the
        registry does not define it. An INACTIVE entry still canonicalizes:
        deactivating a cost center must not silently unlabel the history
        already attributed to it."""
        key = str(name or "").strip().casefold()
        if not key:
            return None
        return self._by_key.get(key)

    def is_active(self, name: object) -> bool:
        canon = self.canonical(name)
        if canon is None:
            return False
        return self._entries[canon].get("active", True) is not False

    def options(self) -> list[dict]:
        """The picker's list: active entries only, name-sorted, each with
        its display-only kind."""
        out = [
            {"name": name,
             "kind": str(entry.get("kind") or ""),
             "note": str(entry.get("note") or "")}
            for name, entry in self._entries.items()
            if entry.get("active", True) is not False
        ]
        out.sort(key=lambda o: o["name"].casefold())
        return out

    def resolve(
        self,
        *,
        override: object = None,
        trip: object = None,
        merchant: object = None,
        card: object = None,
    ) -> CostCenterResolution:
        """Run the chain. Every candidate must already be a name the owner
        defined; anything else is ignored rather than invented.

        An empty registry short-circuits to ``UNRESOLVED_SILENT`` before any
        candidate is examined, so a tenant that has never defined a cost
        center sees no cost-center review state anywhere.
        """
        if not self._entries:
            return UNRESOLVED_SILENT
        for value, source in (
            (override, SOURCE_OVERRIDE),
            (trip, SOURCE_TRIP),
            (merchant, SOURCE_MERCHANT),
            (card, SOURCE_CARD),
        ):
            canon = self.canonical(value)
            if canon is None:
                continue
            # An override names an inactive centre deliberately (correcting
            # history); a DEFAULT must not resurrect one.
            if source is not SOURCE_OVERRIDE and not self.is_active(canon):
                continue
            return CostCenterResolution(canon, source, False)
        return CostCenterResolution(None, SOURCE_NONE, True)

    @classmethod
    def from_settings(cls, settings: dict | None) -> "CostCenterRegistry":
        raw = settings.get("cost_centers") if isinstance(settings, dict) else None
        return cls(raw)


def normalize_cost_centers_setting(raw: object) -> dict:
    """Validate + clean a ``cost_centers`` settings payload into the stored
    shape.

    Raises ValueError on a malformed structure (the settings PUT surfaces it
    as HTTP 400). Same contract family as ``merchants`` / ``cards`` /
    ``entities``: the whole map replaces the stored one, a blank name is
    dropped, each entry must be an object. Two names differing only in case
    are the same cost center and the second is a conflict, not a silent
    overwrite: they would resolve to one another and the owner would never
    see which survived.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("cost_centers must be an object of {name: entry}")
    out: dict[str, dict] = {}
    seen: dict[str, str] = {}
    for name, entry in raw.items():
        clean_name = str(name or "").strip()
        if not clean_name:
            continue
        folded = clean_name.casefold()
        if folded in seen:
            raise ValueError(
                f"cost_centers has two entries differing only in case: "
                f"{seen[folded]!r} and {clean_name!r}"
            )
        seen[folded] = clean_name
        if not isinstance(entry, dict):
            raise ValueError(f"cost_centers[{clean_name!r}] must be an object")
        kind = str(entry.get("kind") or "").strip().lower()
        if kind not in COST_CENTER_KINDS:
            raise ValueError(
                f"cost_centers[{clean_name!r}].kind {kind!r} is not one of "
                f"{', '.join(k or '(blank)' for k in COST_CENTER_KINDS)}"
            )
        cleaned: dict = {}
        if kind:
            cleaned["kind"] = kind
        note = str(entry.get("note") or "").strip()
        if note:
            cleaned["note"] = note
        # Stored only when False, so an ordinary entry keeps the smallest
        # shape and a settings diff stays honest.
        if entry.get("active") is False:
            cleaned["active"] = False
        out[clean_name] = cleaned
    return out
