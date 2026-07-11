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
