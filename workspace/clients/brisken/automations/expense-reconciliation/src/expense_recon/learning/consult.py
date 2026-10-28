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


# Which rule a recall used (item 115). `company`: the receipt's own company
# and vendor. `no_company`: a rule saved from a row that had no company, used
# for a receipt whose company is known but has no rule of its own; it never
# belonged to another company. `vendor_only`: the receipt has no company, so
# the vendor's rules decide, and only when they agree on the category.
RECALL_COMPANY = "company"
RECALL_NO_COMPANY = "no_company"
RECALL_VENDOR_ONLY = "vendor_only"

# Rows seeded from Zoho Books posting history carry this source_run prefix.
ZOHO_SEED_PREFIX = "zoho-seed"


@dataclass(frozen=True)
class LearnedRecall:
    """What memory recalls for one receipt (item 115): the category and
    account to apply, the rows that decided it, and which rule fired."""

    category: str
    zoho_account: str | None
    rows: tuple[MerchantCategory, ...]
    kind: str

    @property
    def taught_by_person(self) -> bool:
        """At least one deciding row is a person's decision: a correction
        saved at sign-off or by the button, or a Memory-page edit. A row
        seeded from Zoho Books history is not, until someone validates it."""
        return any(
            not (r.source_run or "").startswith(ZOHO_SEED_PREFIX)
            or r.validated_at
            for r in self.rows
        )

    @property
    def validated(self) -> bool:
        """A person validated at least one deciding row on the Memory page."""
        return any(r.validated_at for r in self.rows)


def _person_row(r: MerchantCategory) -> bool:
    """`LearnedRecall.taught_by_person` for one row."""
    return not (r.source_run or "").startswith(ZOHO_SEED_PREFIX) or bool(r.validated_at)


@dataclass(frozen=True)
class IdentityFold:
    """One (company, merchant) whose stored rules sit under two or more
    spellings (item 216 cause 3). `decided` is False when they disagree: then
    no spelling speaks for the merchant and each keeps answering only for its
    own exact spelling, as before."""

    legal_entity_id: str
    key: str
    vendor_norms: tuple[str, ...]
    decided: bool
    category: str | None = None
    zoho_account: str | None = None


def fold_rows(
    rows: list[MerchantCategory],
) -> tuple[tuple[MerchantCategory, ...] | None, bool]:
    """The rows that speak for one merchant in one company, or None when they
    disagree. Rules a person stands behind outrank rules seeded from Zoho
    history (the recall's own `taught_by_person` order); within the deciding
    tier every row must name the same category and account."""
    person = [r for r in rows if _person_row(r)]
    deciding = person or rows
    values = {(r.category, r.zoho_account) for r in deciding}
    if len(values) != 1:
        return None, False
    return tuple(sorted(deciding, key=lambda r: r.vendor_norm)), True


class MerchantCategoryLookup:
    """An in-memory (legal_entity_id, merchant) -> MerchantCategory map.
    Empty by construction when there is nothing learned, so an absent or
    fresh store leaves Sort behaving exactly as before.

    Item 216 cause 3: recall keys on the merchant IDENTITY
    (`merchant_identity.MerchantIdentityResolver.key`), not on the raw
    spelling, so a rule stored under `anthropic` answers a receipt reading
    `Anthropic, PBC (@anthropic)`, and rules stored under several spellings of
    one merchant fold into one. The fold happens here, at read time, rather
    than by rewriting the store: nothing on disk changes, the Memory page and
    the undo journal keep their keys, and a disagreement is simply not
    folded (`folds` reports it) so each spelling keeps answering for itself
    exactly as before. Pass `identity` built on the registry so the
    registry's aliases join the fold; without one the name-only identity
    applies."""

    def __init__(
        self, rows: list[MerchantCategory] | None = None, *, identity=None,
    ):
        from ..merchant_identity import MerchantIdentityResolver

        self._rows: list[MerchantCategory] = list(rows or [])
        self.identity = identity or MerchantIdentityResolver()
        self._by_key: dict[tuple[str, str], MerchantCategory] = {
            (r.legal_entity_id, r.vendor_norm): r for r in self._rows
        }
        self._by_vendor: dict[str, list[MerchantCategory]] = {}
        for r in self._by_key.values():
            self._by_vendor.setdefault(r.vendor_norm, []).append(r)
        grouped: dict[tuple[str, str], list[MerchantCategory]] = {}
        for r in self._by_key.values():
            ikey = self.identity.key(r.vendor_norm) or r.vendor_norm
            grouped.setdefault((r.legal_entity_id, ikey), []).append(r)
        # (entity, identity key) -> the rows that speak for it; absent when
        # its spellings disagree.
        self._by_ident: dict[tuple[str, str], tuple[MerchantCategory, ...]] = {}
        self._ident_vendor: dict[str, list[tuple[MerchantCategory, ...]]] = {}
        self.folds: list[IdentityFold] = []
        for (entity, ikey), group in sorted(grouped.items()):
            speaking, decided = fold_rows(group)
            if len(group) > 1:
                first = speaking[0] if speaking else None
                self.folds.append(IdentityFold(
                    entity, ikey, tuple(sorted(r.vendor_norm for r in group)),
                    decided,
                    first.category if first else None,
                    first.zoho_account if first else None,
                ))
            if speaking:
                self._by_ident[(entity, ikey)] = speaking
                self._ident_vendor.setdefault(ikey, []).append(speaking)

    def with_identity(self, identity) -> "MerchantCategoryLookup":
        """The same rules folded by another resolver (one carrying the
        registry, so its aliases join the fold)."""
        return MerchantCategoryLookup(self._rows, identity=identity)

    def _speaking(
        self, entity: str, vendor: str, vnorm: str, ikey: str,
    ) -> tuple[MerchantCategory, ...] | None:
        """The rows answering for (entity, merchant): the folded identity,
        else, when the merchant's spellings disagree, the exact spelling's own
        row as before item 216."""
        hit = self._by_ident.get((entity, ikey))
        if hit is not None:
            return hit
        exact = self._by_key.get((entity, vnorm))
        return (exact,) if exact is not None else None

    def get(self, legal_entity_id: str, vendor: str | None) -> MerchantCategory | None:
        if not vendor:
            return None
        return self._by_key.get((legal_entity_id, normalize_vendor(vendor)))

    def recall(
        self, legal_entity_id: str | None, vendor: str | None
    ) -> LearnedRecall | None:
        """The remembered category for a receipt, or None (item 115).

        A receipt takes the rule saved under its own company and vendor
        first -- and a receipt with no company has one of those too, the
        rule saved with no company. A receipt with a company but no rule of
        its own falls back to a rule saved with no company, which never
        belonged to another company. Only a receipt with no company and no
        company-less rule reaches the vendor's other rules, and then only
        when they agree on the category (or exactly one exists); rules that
        disagree decide nothing, so one company's rule never files another
        company's receipt against the other rules. The account is kept on
        that path only when every rule names the same one, because an
        account belongs to one company's chart."""
        if not vendor:
            return None
        vnorm = normalize_vendor(vendor)
        if not vnorm:
            return None
        ikey = self.identity.key(vendor) or vnorm
        entity = (legal_entity_id or "").strip()
        hit = self._speaking(entity, vendor, vnorm, ikey)
        if hit is not None and hit[0].category:
            return LearnedRecall(
                hit[0].category, hit[0].zoho_account, hit, RECALL_COMPANY
            )
        if entity:
            no_company = self._speaking("", vendor, vnorm, ikey)
            if no_company is not None and no_company[0].category:
                return LearnedRecall(
                    no_company[0].category, no_company[0].zoho_account,
                    no_company, RECALL_NO_COMPANY,
                )
            return None
        groups = self._ident_vendor.get(ikey)
        if groups is None:
            groups = [(r,) for r in self._by_vendor.get(vnorm, [])]
        rows = [r for g in groups for r in g if g[0].category]
        if not rows or len({r.category for r in rows}) != 1:
            return None
        accounts = {r.zoho_account for r in rows}
        return LearnedRecall(
            rows[0].category,
            accounts.pop() if len(accounts) == 1 else None,
            tuple(sorted(rows, key=lambda r: r.legal_entity_id)),
            RECALL_VENDOR_ONLY,
        )

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
# `card_key` (item 87) is only a candidate: the card chain applies it when
# the receipt's own payment method names no card number.
_CORRECTABLE_FIELDS = ("vendor", "tax_label", "paid_through", "card_key")


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
                    "card_key": r.card_key,
                }[f]
                if value != current:
                    kw[
                        "detected_vendor" if f == "vendor" else f
                    ] = value
                    if f == "card_key":
                        # Only a candidate; the row's `card_source`
                        # "learned" says when it actually decided the card.
                        continue
                    filled.append(f)
                    if f == "vendor":
                        # Mark where the DISPLAY vendor came from so the grid
                        # can label a learned correction distinctly from a
                        # registry canonicalization (the registry pass runs
                        # after this and overwrites the marker on a hit).
                        kw["vendor_source"] = "learned"
            if not kw:
                out.append(r)
                continue
            if filled:
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
