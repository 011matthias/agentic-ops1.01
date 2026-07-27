"""Read-model the Sort pass consults for learned merchant categories
(PR 2b). Built once per run from the learning store and passed into
`categorize_receipts`, so the categorizer stays a pure function with no DB
handle of its own.

Lookups normalize the vendor the same way keys were stored, so the caller
passes a raw vendor string as it appears on the receipt.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path

from .store import (
    FieldCorrection,
    LearningStore,
    MerchantCategory,
    MerchantEntity,
    normalize_vendor,
)


class MerchantCategoryLookup:
    """An in-memory (legal_entity_id, vendor_norm) -> MerchantCategory map.
    Empty by construction when there is nothing learned, so an absent or
    fresh store leaves Sort behaving exactly as before."""

    def __init__(self, rows: list[MerchantCategory] | None = None):
        self._by_key: dict[tuple[str, str], MerchantCategory] = {
            (r.legal_entity_id, r.vendor_norm): r for r in (rows or [])
        }

    def get(self, legal_entity_id: str, vendor: str | None) -> MerchantCategory | None:
        if not vendor:
            return None
        return self._by_key.get((legal_entity_id, normalize_vendor(vendor)))

    def __len__(self) -> int:
        return len(self._by_key)

    def __bool__(self) -> bool:
        return bool(self._by_key)

    @classmethod
    def from_store(cls, store: LearningStore) -> "MerchantCategoryLookup":
        return cls(store.all_merchant_categories())

    @classmethod
    def from_db_path(cls, db_path) -> "MerchantCategoryLookup":
        """Load from a learning.sqlite path; an absent file yields an empty
        lookup (no learned data, no behavior change)."""
        if not Path(db_path).exists():
            return cls([])
        with LearningStore(db_path) as store:
            return cls.from_store(store)


@dataclass(frozen=True)
class MatchMemory:
    """What the Match pass recalls (PR 2c): confirmed vendor aliases and
    per-merchant FX means. Both feed scoring/tie-break only — they never
    change which bucket a pair lands in, so the reconciliation guarantee is
    untouched. Empty => Match behaves exactly as before.

    * `vendor_aliases` — confirmed (legal_entity_id, statement-vendor-norm,
      receipt-vendor-norm) equivalences; a hit pins vendor similarity high.
    * `merchant_fx` — (legal_entity_id, vendor-norm, from_ccy, to_ccy) ->
      mean observed implied rate; re-centers the FX amount sub-score toward
      a merchant's known DCC pattern, WITHIN the LD-5 band (never widens it).
    """

    vendor_aliases: frozenset[tuple[str, str, str]] = frozenset()
    merchant_fx: dict[tuple[str, str, str, str], Decimal] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.vendor_aliases or self.merchant_fx)

    @classmethod
    def from_store(cls, store: LearningStore) -> "MatchMemory":
        aliases = frozenset(
            (a.legal_entity_id, a.stmt_vendor_norm, a.receipt_vendor_norm)
            for a in store.get_vendor_aliases()
        )
        fx: dict[tuple[str, str, str, str], Decimal] = {}
        for f in store.all_merchant_fx():
            if f.mean is not None:
                fx[(f.legal_entity_id, f.vendor_norm, f.from_ccy, f.to_ccy)] = f.mean
        return cls(aliases, fx)

    @classmethod
    def from_db_path(cls, db_path) -> "MatchMemory":
        if not Path(db_path).exists():
            return cls()
        with LearningStore(db_path) as store:
            return cls.from_store(store)


class MerchantEntityLookup:
    """vendor_norm -> learned legal entity (receipt-first, Phase 6). Empty
    by construction when nothing is learned."""

    def __init__(self, rows: list[MerchantEntity] | None = None):
        self._by_vendor: dict[str, str] = {
            r.vendor_norm: r.legal_entity_id for r in (rows or [])
        }

    def get(self, vendor: str | None) -> str | None:
        if not vendor:
            return None
        return self._by_vendor.get(normalize_vendor(vendor))

    def __bool__(self) -> bool:
        return bool(self._by_vendor)

    @classmethod
    def from_store(cls, store: LearningStore) -> "MerchantEntityLookup":
        return cls(store.all_merchant_entities())


class FieldCorrectionLookup:
    """(legal_entity_id, vendor_norm) -> {field: value} (receipt-first,
    Phase 6). Keys are the ORIGINAL extracted vendor, so next month's
    identical OCR output hits the same correction."""

    def __init__(self, rows: list[FieldCorrection] | None = None):
        self._by_key: dict[tuple[str, str], dict[str, str]] = {}
        for r in rows or []:
            if r.value:
                self._by_key.setdefault(
                    (r.legal_entity_id, r.vendor_norm), {}
                )[r.field] = r.value

    def get(self, legal_entity_id: str, vendor: str | None) -> dict[str, str]:
        if not vendor:
            return {}
        return self._by_key.get((legal_entity_id, normalize_vendor(vendor)), {})

    def __bool__(self) -> bool:
        return bool(self._by_key)

    @classmethod
    def from_store(cls, store: LearningStore) -> "FieldCorrectionLookup":
        return cls(store.all_field_corrections())


# Header fields a stored correction may auto-fill. `vendor` REPLACES the
# extracted spelling (that is the point of the correction); the others fill
# or replace the extracted value the same way the reviewer's edit did.
_CORRECTABLE_FIELDS = ("vendor", "tax_label", "paid_through")


@dataclass(frozen=True)
class ExpenseMemory:
    """What receipt-first expense generation recalls (Phase 6): learned
    merchant -> entity mappings and per-merchant field corrections. Applied
    ONLY in `generate_expenses` — `reconcile()` never consults this, so
    statement-mode behaviour cannot change. Empty => receipts pass through
    untouched."""

    entities: MerchantEntityLookup = field(default_factory=MerchantEntityLookup)
    fields: FieldCorrectionLookup = field(default_factory=FieldCorrectionLookup)

    def __bool__(self) -> bool:
        return bool(self.entities) or bool(self.fields)

    def apply(self, receipts: list) -> list:
        """Return receipts with learned entity + field corrections applied.
        Lookups key on the ORIGINAL extracted vendor; the entity mapping is
        applied first so field corrections resolve under the effective
        entity (the one they were learned under). Every auto-fill appends a
        plain provenance note to `data_quality_note`, which the review grid
        already renders — the reviewer always sees what memory changed."""
        if not self:
            return receipts
        out = []
        for r in receipts:
            original_vendor = r.detected_vendor
            kw: dict = {}
            filled: list[str] = []
            mapped_entity = self.entities.get(original_vendor)
            if mapped_entity and mapped_entity != r.legal_entity_id:
                kw["legal_entity_id"] = mapped_entity
                filled.append("legal entity")
            effective_entity = mapped_entity or r.legal_entity_id
            corr = self.fields.get(effective_entity, original_vendor)
            for f in _CORRECTABLE_FIELDS:
                value = corr.get(f)
                if not value:
                    continue
                current = {
                    "vendor": r.detected_vendor,
                    "tax_label": r.tax_label,
                    "paid_through": r.paid_through,
                }[f]
                if value != current:
                    kw[
                        "detected_vendor" if f == "vendor" else f
                    ] = value
                    filled.append(f)
            if not kw:
                out.append(r)
                continue
            note = "Auto-filled from a prior correction: " + ", ".join(filled)
            existing_note = r.data_quality_note
            kw["data_quality_note"] = (
                f"{existing_note} | {note}" if existing_note else note
            )
            out.append(replace(r, **kw))
        return out

    @classmethod
    def from_store(cls, store: LearningStore) -> "ExpenseMemory":
        return cls(
            MerchantEntityLookup.from_store(store),
            FieldCorrectionLookup.from_store(store),
        )

    @classmethod
    def from_db_path(cls, db_path) -> "ExpenseMemory":
        if db_path is None or not Path(db_path).exists():
            return cls()
        with LearningStore(db_path) as store:
            return cls.from_store(store)
