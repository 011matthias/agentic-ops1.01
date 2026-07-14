"""Brisken Lead Desk: a single-source-of-truth lead-generation tracker.

Contacts plus an append-only outreach event log live in one SQLite database.
Pipeline stage and every status bucket are DERIVED from the event log, never
hand-stamped, so the board cannot drift the way the old spreadsheet-plus-
Planner-plus-notes sprawl did.
"""

__version__ = "0.1.0"
