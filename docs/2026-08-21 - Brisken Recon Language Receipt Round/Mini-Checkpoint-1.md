# Mini-Checkpoint: Brisken Recon Language Receipt Round

**Date:** 2026-08-21
**Status:** Round 7 of the 8-PR feedback wave shipped; every unblocked round done
**Type:** mini

---

## Summary

Language contract + honest receipt column (Themes E+F, notes 4/8)
shipped as PR #567 and deployed. With it, rounds 1-7 of the 2026-08-21
feedback wave are complete in one day; only Cards R4 remains, gated on
owner answers.

## What Was Done

- Language contract "backend emits stable codes, SPA localizes":
  `review.missing` structured list beside the prose; books_as parts are
  `{account: str|null, unassigned: bool, amount}` (the export CSV keeps
  its English literal — the Zoho artifact's contract; grid==export
  amounts hold); dead `reason_label` dropped from set-aside entries.
  The issue-code-on-upload-prose piece was PARKED as backlog item 20
  with a shape suggestion (rare surface, lockstep contract break).
- Honest receipt column: `receipt_image_available` no longer claims a
  document for typed-in manual expenses (the 404 View button, note 8);
  the adversarial-review carry is fixed and pinned — workbench-attached
  `manual:`/`folder:` receipts on a graduated batch keep availability
  via the exact glob the image endpoint serves from. Rows gain
  `source_file` (which upload/mail they came from).
- Review: single-lens pass, verdict OK-TO-SHIP; both carries handled
  (availability false-negative fixed; the Lovable prompt ships the
  books_as mapping marked APPLY FIRST — the deployed SPA renders a
  blank account label on uncategorized split parts until applied).
- Suite 1214/2 (+4 tests); calibrate OK; deployed; live-verified on the
  January batch (15/15 rows source_file + honest availability, 1
  unassigned sentinel, 0 English literals).

## Current Status

Feedback wave: rounds 1-7 of 8 shipped
(#555/#556/#559/#561/#563/#565/#567), all deployed and live-verified.
Seven Lovable prompts wait on the owner: memory-edit is REQUIRED (SPA
Reset is a safe no-op until applied), language-receipt item 1 is APPLY
FIRST. Cards R4 waits on backlog item 10 answers. The loop returns to
REACTIVE.

## Next Steps

1. Cards R4 once the owner answers item 10; items 18/19/20 ride
   whichever code round touches their surfaces.
2. DOM-probe the SPA after any Lovable publish.
3. Owner calls pending: item 19 (re-ingest after month delete), the
   restore decision on Dirk's rendered credit notice.

## Files to Read First

- workspace/clients/brisken/status/p1-recon-loop-prompt.md
- workspace/clients/brisken/status/p1-improvement-backlog.md
- ~/.claude/plans/looks-like-there-is-keen-aurora.md (Cards R4 design)
