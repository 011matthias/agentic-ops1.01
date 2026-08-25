"""Harvest confirmed reviewer decisions into the learning store — PR 2a.

`learn_from_run` is the capture half of Phase 2: it reads a finalized run
(the reviewer's confirmed matches + explicit category reclassifications)
and writes the durable facts the consult paths will read in 2b / 2c.

What counts as a teachable, EXPLICIT signal (the finalize-gate honors
decision #2: a half-reviewed month must never teach wrong facts):

* **vendor_alias** and **merchant_fx** come from CONFIRMED matches only.
  Confirming a match is Chris asserting "this charge IS this receipt", so
  the (statement-vendor, receipt-vendor) equivalence and the implied FX
  rate are ground truth.
* **merchant_category** comes from explicit category OVERRIDES only (a
  reclassification). Confirming a match does NOT by itself confirm the
  category the LLM guessed for that receipt, so an un-reclassified Tier-1/
  Tier-2 category is left unlearned. A vendor whose overridden lines
  disagree on category is skipped (counted), never taught a wrong single
  mapping.

The function is pure w.r.t. the web layer: it takes matching-domain types
plus the already-computed `confirmed_tx_ids` set and the raw overrides
map, so `learning` never imports `web`. The caller (web.service) owns the
translation from reviewer state to those inputs.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..matching.types import ClassificationSource, MatchOutcome, Receipt, Transaction
from .store import LearningStore, normalize_vendor

# Line-item category sources we treat as a real, learnable category. After
# an override, web.service rewrites the line as source=LINE with reasoning
# "reclassified by reviewer", so reclassifications land here; REVIEW /
# UNCLASSIFIED never do.
_CONCRETE_SOURCES = (ClassificationSource.LINE, ClassificationSource.VENDOR)


@dataclass(frozen=True)
class LearnSummary:
    confirmed_pairs: int          # confirmed matches inspected
    vendor_aliases: int           # alias rows written
    merchant_fx: int              # FX samples written
    merchant_categories: int      # category mappings written (from overrides)
    skipped_mixed_category: int   # vendors whose overrides disagreed -> skipped

    def as_dict(self) -> dict:
        return {
            "confirmed_pairs": self.confirmed_pairs,
            "vendor_aliases": self.vendor_aliases,
            "merchant_fx": self.merchant_fx,
            "merchant_categories": self.merchant_categories,
            "skipped_mixed_category": self.skipped_mixed_category,
        }


def learn_from_run(
    store: LearningStore,
    *,
    transactions: list[Transaction],
    receipts: list[Receipt],
    outcome: MatchOutcome,
    confirmed_tx_ids: set[str],
    category_overrides: dict[tuple[str, int], dict],
    source_run: str,
    now_iso: str,
) -> LearnSummary:
    """Write the teachable facts from one finalized run. `outcome` is the
    decision-applied (effective) outcome; `confirmed_tx_ids` are the
    transactions the reviewer explicitly confirmed; `category_overrides`
    is the raw (document_id, line_index) -> {category, zoho_account} map."""
    tx_by_id = {t.transaction_id: t for t in transactions}
    rec_by_id = {r.document_id: r for r in receipts}

    confirmed_pairs = n_alias = n_fx = 0

    for m in outcome.matches:
        if m.transaction_id not in confirmed_tx_ids:
            continue
        tx = tx_by_id.get(m.transaction_id)
        r = rec_by_id.get(m.document_id)
        if tx is None or r is None:
            continue
        confirmed_pairs += 1

        # vendor alias: teaches the truncated-name equivalence the matcher
        # re-fuzzes every month. Only when both sides carry a vendor.
        if tx.vendor_from_statement and r.detected_vendor:
            sv = normalize_vendor(tx.vendor_from_statement)
            rv = normalize_vendor(r.detected_vendor)
            if sv and rv:
                store.record_vendor_alias(tx.legal_entity_id, sv, rv, now_iso, source_run)
                n_alias += 1

        # per-merchant FX: record the implied rate for a currency-mismatch
        # pair so 2c can refine the band score toward this merchant's DCC.
        if (
            r.detected_currency
            and r.detected_currency != tx.transaction_currency
            and r.detected_total is not None
            and r.detected_total > 0
            and tx.amount > 0
        ):
            vnorm = normalize_vendor(r.detected_vendor or tx.vendor_from_statement or "")
            if vnorm:
                implied = tx.amount / r.detected_total
                store.record_merchant_fx(
                    tx.legal_entity_id,
                    vnorm,
                    r.detected_currency,
                    tx.transaction_currency,
                    implied,
                    now_iso,
                    source_run,
                )
                n_fx += 1

    n_category, n_skipped = _learn_categories(
        store, rec_by_id, category_overrides, source_run, now_iso
    )

    return LearnSummary(
        confirmed_pairs=confirmed_pairs,
        vendor_aliases=n_alias,
        merchant_fx=n_fx,
        merchant_categories=n_category,
        skipped_mixed_category=n_skipped,
    )


@dataclass(frozen=True)
class ExpenseLearnSummary:
    """What one finalized expense batch taught (receipt-first, Phase 6)."""

    merchant_categories: int      # category mappings written (from overrides)
    skipped_mixed_category: int   # vendors whose overrides disagreed -> skipped
    merchant_entities: int        # vendor -> entity mappings written
    field_corrections: int        # (vendor, field) -> value corrections written

    def as_dict(self) -> dict:
        return {
            "merchant_categories": self.merchant_categories,
            "skipped_mixed_category": self.skipped_mixed_category,
            "merchant_entities": self.merchant_entities,
            "field_corrections": self.field_corrections,
        }


# Header fields a reviewer edit teaches as a per-merchant correction. The
# key is the ORIGINAL extracted vendor (what OCR will read again next
# month); `vendor` teaches the canonical spelling itself.
_LEARNABLE_FIELDS = ("vendor", "tax_label", "paid_through")


def learn_from_expense_run(
    store: LearningStore,
    *,
    receipts: list[Receipt],
    effective_receipts: list[Receipt],
    field_overrides: dict[str, dict[str, str]],
    category_overrides: dict[tuple[str, int], dict],
    manual_payloads: dict[str, dict] | None = None,
    source_run: str,
    now_iso: str,
) -> ExpenseLearnSummary:
    """Harvest one finalized expense batch (receipt-first, Phase 6).

    Only EXPLICIT edits teach — the same finalize-gate discipline as
    `learn_from_run`; an untouched LLM guess and the batch-level default
    entity never do:

    * **merchant_category** — explicit line reclassifications, via the
      shared `_learn_categories`, keyed on the EFFECTIVE (post-edit)
      vendor + entity so a corrected spelling learns under its canon.
    * **merchant_entity** — a per-expense entity OVERRIDE, or a manual
      add whose payload names the entity. The batch default is a bulk
      choice, not a per-merchant judgment; it teaches nothing.
    * **field_correction** — vendor / tax_label / paid_through edits,
      keyed on the ORIGINAL extracted vendor (what OCR will produce
      again) under the expense's effective entity.

    `receipts` is the ORIGINAL snapshot pool (pre-overlay); the caller
    passes `effective_receipts` (post `apply_expense_edits`) so both
    vendor spellings are visible here without re-deriving the overlay.
    """
    orig_by_id = {r.document_id: r for r in receipts}
    eff_by_id = {r.document_id: r for r in effective_receipts}

    n_entity = n_field = 0

    for document_id, fields in field_overrides.items():
        eff = eff_by_id.get(document_id)
        if eff is None:
            continue  # edit on a deleted / unknown expense teaches nothing
        orig = orig_by_id.get(document_id)
        # Per-expense entity override -> merchant -> entity mapping, keyed
        # on BOTH the original extracted vendor (what OCR will read again
        # next month) and the effective one (the canonical spelling), so
        # the mapping hits whether or not a vendor correction also applies.
        if fields.get("legal_entity"):
            keys = {
                normalize_vendor(v)
                for v in (
                    (orig.detected_vendor if orig else None),
                    eff.detected_vendor,
                )
                if v
            } - {""}
            for vnorm in keys:
                store.record_merchant_entity(
                    vnorm, fields["legal_entity"].strip(), now_iso, source_run
                )
                n_entity += 1
        # Header corrections, keyed on the ORIGINAL extracted vendor. A
        # manual add has no OCR original to correct — skipped by design.
        if orig is None or not orig.detected_vendor:
            continue
        okey = normalize_vendor(orig.detected_vendor)
        if not okey:
            continue
        for f in _LEARNABLE_FIELDS:
            value = (fields.get(f) or "").strip()
            if value:
                store.record_field_correction(
                    eff.legal_entity_id, okey, f, value, now_iso, source_run
                )
                n_field += 1

    # A manual add that names its entity is an explicit vendor -> entity
    # statement too.
    for document_id, payload in (manual_payloads or {}).items():
        entity = str(payload.get("legal_entity") or "").strip()
        vendor = str(payload.get("vendor") or "").strip()
        if not entity or not vendor:
            continue
        vnorm = normalize_vendor(vendor)
        if vnorm:
            store.record_merchant_entity(vnorm, entity, now_iso, source_run)
            n_entity += 1

    n_category, n_skipped = _learn_categories(
        store, eff_by_id, category_overrides, source_run, now_iso
    )

    return ExpenseLearnSummary(
        merchant_categories=n_category,
        skipped_mixed_category=n_skipped,
        merchant_entities=n_entity,
        field_corrections=n_field,
    )


def _learn_categories(
    store: LearningStore,
    rec_by_id: dict[str, Receipt],
    category_overrides: dict[tuple[str, int], dict],
    source_run: str,
    now_iso: str,
) -> tuple[int, int]:
    """Collapse per-line reclassifications to one (legal_entity, vendor) ->
    category mapping each, skipping vendors whose overrides disagree."""
    # (legal_entity_id, vendor_norm) -> {"category","zoho_account","conflict"}
    pending: dict[tuple[str, str], dict] = {}

    for (document_id, _line_index), ov in category_overrides.items():
        category = ov.get("category")
        if not category:
            continue
        r = rec_by_id.get(document_id)
        if r is None or not r.detected_vendor:
            continue
        vnorm = normalize_vendor(r.detected_vendor)
        if not vnorm:
            continue
        key = (r.legal_entity_id, vnorm)
        prior = pending.get(key)
        if prior is None:
            pending[key] = {
                "category": category,
                "zoho_account": ov.get("zoho_account"),
                "conflict": False,
            }
        elif prior["category"] != category:
            prior["conflict"] = True

    n_category = n_skipped = 0
    for (legal_entity_id, vnorm), val in pending.items():
        if val["conflict"]:
            n_skipped += 1
            continue
        store.record_merchant_category(
            legal_entity_id,
            vnorm,
            val["category"],
            val["zoho_account"],
            now_iso,
            source_run,
        )
        n_category += 1

    return n_category, n_skipped
