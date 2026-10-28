# Mini-Checkpoint: Expense-Recon Notes 99-106 Duplicate

**Date:** 2026-09-27
**Status:** Loop done; queue empty, no feedback note past #106
**Type:** mini

---

## Summary
Notes #99-#106 (September Matching header) were built twice. This session wrote the SPA prompt as PR #1513 while a sibling wrote the same one as PR #1511 (items 232-235, merged 21:13 UTC), a superset of this design. #1513 was closed unmerged on the owner's choice, so nothing from this session reached main.

## What Was Done
- Claims check at start (about 21:00 UTC) was clean: `gh pr list --search "brisken p1"` showed only #1505, and origin/main's backlog had no item for feedback notes #99-#106 (the "#99"-"#106" hits there are 2026-09-17 audit-draft numbers).
- Read the published SPA source and one `/api/runs/51a22ad72864` (0 writes). Finding, also in #1511: the PDF statement's `account_id` and `card_key` are empty, but `card_sections[].statements` + `digits` name every statement file's card, so the last four need no backend change.
- Recorded the bundle baseline (48 chunks): `wb.statement.view.many`, `wb.status.cardsUncovered.view`, `wb.status.stillOpen.label`, `wb.status.bookedNoReceipt.label` absent, `wb.subtitle.template` present. #1511 uses other key names (e.g. `wb.status.stillOpen.rest`), so this baseline does not carry over to its post-publish check.
- PR #1513 closed unmerged (owner chose via AskUserQuestion); its branch was deleted locally and on origin and its worktree removed.

## What Did NOT Work (and why)
- **Claiming the queue item by a check at session start:** the sibling opened #1511 at 21:06 UTC, after this session's check, from the same continuation queue. Numbers are claimed only at merge, so two sessions handed the same queue both saw it free. This is the second session in a row (after items 223 step 6 / 227) that lost its work this way. An early claim (a draft PR titled with the note numbers, opened before any reading) is the structural candidate: it only works if every session's claims check also reads draft PRs.

## Current Status
p1 expense-recon: every feedback note (106) has an item; the queue in the last continuation prompt is empty. Waiting on the owner (Lovable pastes): `lovable-matching-header-prompt.md` (the #1511 version on main), `lovable-quiet-done-tiles-prompt.md`, `lovable-duplicate-reasons-gate-prompt.md`, the `intake_twin` line of `lovable-copies-kind-prompt.md`; PROMPT-STATUS "Not applied" has the full list. Sibling PR #1505 (months list, self-titled item 231) is still open and renumbers at its merge.

## Next Steps
1. Before handing one continuation queue to more than one session, split the queue by item across sessions, or open a draft claim PR as the first action of each item.
2. After the owner publishes, verify `lovable-matching-header-prompt.md` with the key names in #1511's PROMPT-STATUS row, not the names listed above.
3. Read `GET /feedback.jsonl` for notes past #106.

## Files to Read First
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md (Not applied table)
- workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md
