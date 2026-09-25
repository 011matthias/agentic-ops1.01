# Mini-Checkpoint: Expense-Recon Item 215 Attach Month Guard

**Date:** 2026-09-25
**Status:** Item 215 shipped and live (Fly `418c3c6d`); SPA half written, not pasted. Loop done: queue empty, no new feedback note (store 87, backlog covers #87).
**Type:** mini

---

## Summary
A statement attach to a company month now keeps only that month's own charges when the file prints post dates (Criss's lifetime SharePoint sheets), drops charges a neighbour month or another of its files already holds under a different reading, and records what it left out; a restart-killed attach's upload is discarded at boot.

## What Was Done
- PR #1412 (merge `418c3c6d`, deployed, `/healthz` commit matches): `keep_month_charges` / `prints_post_dates` / `neighbour_month_charges` in `web/service.py`; `statements[].month_filter {month, n_file_rows, n_kept, n_left_out, outside_month, already_held}`, job `result.month_filter` + warning sentence; refusal `statement_outside_month` (job `result.code`); re-read filters only entries carrying `month_filter`; `.attach-pending/{job_id}.json` marker + boot `sweep_interrupted_attaches`.
- Tests: `tests/test_attach_month_guard_item_215.py` (13, route-level incl. a second `create_app` boot); four wiring points RED under `regress_check` (attach gate, re-read gate, boot sweep, job warning); CI green.
- Live drill on scratch months TEST - October / November 2025 (no live neighbour, pool empty, both deleted, 404): all 8 assertions PASS (cycle file folds whole; lifetime export kept 2 of 7, outside {2024-11, 2025-10, 2025-12, 2026-06}, already_held {2025-10: 1}; June-only file refused, no entry; Criss's seven months untouched). Cold SPA drive (headless Chrome, raw CDP, from the gate): the loaded-statement line rendered the kept count, no fallback strings; recon API saw only the login POST (the other POST was Lovable's own `~api/analytics`).
- SPA half `docs/lovable-attach-month-filter-prompt.md` (loaded-line note, attach toast, translated refusal, EN + PT); PROMPT-STATUS Not-applied row; `docs/api-contract.md` section.
- Record PR #1417 (`6e6ab80a`): backlog item 215 SHIPPED paragraph + top line in `status/p1-expense-reconciliation.md` (conflict with a sibling's item-214 paragraph resolved, both kept).

## What Did NOT Work (and why)
- **Cutting files with no post date by transaction date (the brief's proposed fallback):** a Chase cycle PDF spans two months by design (August's 9693 PDF runs Jul 3 to Aug 4), so its July rows would land in no month; the first full suite run stopped at 40 failures, every one a cycle-shaped file. Narrowed: only files that print post dates are filtered.
- **Seeding a neighbour's cycle file through the guarded attach in the neighbour test:** under the first design May's own attach dropped its April row, so May never held it and the test failed; live neighbours were attached before the guard, so the test seeds them that way (`_attach_before_the_guard`).
- **50-line heredoc with Python triple quotes to patch the test file:** refused by the heredoc gate, a dead end already listed in WHAT NOT TO RETRY; Edit used instead.
- **Polling #1417's checks without `mergeable_state`:** checks went green but the merge was refused on a conflict with a sibling's backlog edit; read `mergeable_state` inside the poll.
- **Ending a turn with #1412 still in CI:** the stop pattern flagged it; the chain was resumed next turn. Wait in-turn.

## Current Status
- Backend live `418c3c6d`. No live month was written; every live `statements[]` entry predates the guard and re-reads as before. April's stray `Chase9693_2026-04_posted_0401-0430_from-SharePoint.xlsx` predates the markers and stays (inert, nothing reads it).
- Owner: paste `docs/lovable-attach-month-filter-prompt.md`; until then the page shows the kept count but not the left-out count (a refusal shows the English `error`).
- Criss: can upload the whole weekly 9693 / 1176 / 2838 sheets into a month; the month keeps its own rows.
- brisken ops status: platform unknown plan (no `platform` section assessed).

## Next Steps
1. Owner pastes `lovable-attach-month-filter-prompt.md`; then bundle-audit for `month_filter` / `n_left_out` / "Ficaram de fora" and drive a TEST month given a multi-month file (EN + PT), deleting it after.
2. No build queue item is open from this brief; the loop is done.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 215 (shipped paragraph)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` section "A statement attach keeps only the month's own charges"
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-attach-month-filter-prompt.md`
