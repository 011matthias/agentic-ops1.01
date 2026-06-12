"""Persistent tables for the standalone pipeline (BLUEPRINT Path A).

Under Path A (confirmed 2026-06-12) the tool owns its own tables rather
than recomputing from loose files each run. This is one of Path A's
load-bearing reasons: the tables are the source of truth that survives
the Zoho switch-off.

Modules:

* ``statements`` (8.2) — one persistent table of bank-statement
  transactions across all banks/cards, with content-fingerprint dedup
  so overlapping re-exports (the Chase historic-activity file overlaps
  every monthly download) are counted once.
* ``reports`` (8.3) — Zoho Expense report metadata + per-expense
  cross-reference (``report_for`` / ``expenses_for``), carried into the
  Books journal export.

Both follow the run-log pattern (``runlog.py``): a thin SQLite wrapper,
schema-on-open, opt-in (no table is created unless a caller opens the
store), and a caller-provided timestamp so behaviour is deterministic
under test.
"""
from __future__ import annotations

from .reports import (
    Report,
    ReportConflictError,
    ReportIngestResult,
    ReportStore,
    group_by_report,
)
from .statements import (
    IngestResult,
    StatementConflictError,
    StatementStore,
    fingerprint,
)

__all__ = [
    "IngestResult",
    "Report",
    "ReportConflictError",
    "ReportIngestResult",
    "ReportStore",
    "StatementConflictError",
    "StatementStore",
    "fingerprint",
    "group_by_report",
]
