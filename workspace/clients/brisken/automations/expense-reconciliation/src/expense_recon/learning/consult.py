"""Read-model the Sort pass consults for learned merchant categories
(PR 2b). Built once per run from the learning store and passed into
`categorize_receipts`, so the categorizer stays a pure function with no DB
handle of its own.

Lookups normalize the vendor the same way keys were stored, so the caller
passes a raw vendor string as it appears on the receipt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .store import LearningStore, MerchantCategory, normalize_vendor


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
