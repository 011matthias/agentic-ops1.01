"""Cross-run learning (Phase 2): remember confirmed reviewer decisions so
next month's reconciliation pile is smaller.

PR 2a (this package) is capture-only — `learn_from_run` harvests confirmed
decisions into `LearningStore`. Nothing reads the store yet; the consult
paths (Sort in 2b, Match in 2c) and the inspect/forget/reset CLI (2d) come
next, the escape hatch deliberately before any auto-consult.
"""
from __future__ import annotations

from .capture import (
    ExpenseLearnSummary,
    LearnSummary,
    learn_from_expense_run,
    learn_from_run,
)
from .consult import (
    ExpenseMemory,
    FieldCorrectionLookup,
    MatchMemory,
    MerchantCategoryLookup,
    MerchantEntityLookup,
)
from .store import (
    FieldCorrection,
    LearningStore,
    MerchantCategory,
    MerchantEntity,
    MerchantFx,
    VendorAlias,
    normalize_vendor,
)

__all__ = [
    "LearningStore",
    "MerchantCategory",
    "MerchantEntity",
    "FieldCorrection",
    "VendorAlias",
    "MerchantFx",
    "normalize_vendor",
    "LearnSummary",
    "ExpenseLearnSummary",
    "learn_from_run",
    "learn_from_expense_run",
    "MerchantCategoryLookup",
    "MerchantEntityLookup",
    "FieldCorrectionLookup",
    "ExpenseMemory",
    "MatchMemory",
]
