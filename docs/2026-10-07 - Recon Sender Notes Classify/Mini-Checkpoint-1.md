# Mini-Checkpoint: Recon Sender Notes Classify

**Date:** 2026-10-07
**Status:** item 250 LIVE (Fly `27ab0ec4`); item 251 (apply notes to existing rows) being built
**Type:** mini

---

## Summary
The note a mail sender types above a forwarded receipt now classifies new
receipts (company, split, account), live since PR #1589. The owner then
ordered the same for receipts already in the months ("change existing rows,
reread if need be"); that backfill is mid-build.

## What Was Done
- Read-only census of the live intake (148 archives, 72 notes; 89 noted rows:
  note agrees with the tool's company 40, fills 5, contradicts the card 17,
  split 5, no company 25, 14 of those only Criss's signature).
- Owner rulings via three questions (after he asked for the card/company
  relation explained): company "note always wins" over the card (only
  Criss's row pick beats it); split books whole in Corporate Services on its
  OWN never-allocated account ("own account, never split", allocation rule
  N/A); account "decide when clear" (model >= 0.85, source NOTE, origin
  person, never learned).
- Backlog item 250 built + shipped: `sender_note.py`,
  `intake_mail.trusted_sender_notes`, three serialized receipt fields stamped
  at both arrival paths, row tier override > sender_note > card, categorizer
  NOTE tier, `classify_by_note`. PR #1589 (renumbered from 246, siblings took
  246-249), record PR #1591. Full suite 4235 passed; CI green; four
  `regress_check` bites; deployed via `deploy.py` (`/healthz` commit
  verified); cold read-only SPA drive of October renders.
- Lovable prompt `docs/lovable-sender-note-classify-prompt.md` handed to the
  owner in chat (paste pending; the live hint still says "Nothing was decided
  from it").
- Item 251 delegated to a subagent in worktree `agentic-ops1-notebackfill`
  (branch `client/brisken/p1-recon-note-backfill`): route
  `POST /api/runs/{id}/sender-notes/apply {confirm, dry_run}` mirroring the
  item-240 reread route, re-reading `operator_note` from the archive for
  receipts ingested before 2026-09-20.

## What Did NOT Work (and why)
- **Full suite with `-n auto`:** the module env has no pytest-xdist, so the
  run died on a usage error; its "exit 0" was `tail`'s. Run pytest plainly,
  logged to a file.
- **`cd ... && gh pr merge` in one call:** blocked by
  `block-merge-chained-after-any-command`; the merge gate reads CI once for
  the whole command. Merge as its own Bash call.
- **Ending a turn with the PR waiting on CI:** the merge then depends on a
  notification. Block on `gh pr checks --watch` in the same turn.

## Current Status
Item 250 live, no existing row changed by it. Item 251 subagent running
(watch `note-backfill-build-subagent-ite`). Months holding noted receipts:
Sep `51a22ad72864`, Aug `074a7b8905d7`, Oct `4ac14cb8b9e8`, Jul
`50622baec444`, Jun `a5f97a85b1d0`, May `86929f2a909a` (Jun/May are bucket
months: company tier only).

## Next Steps
1. Review the subagent's diff and test report; commit, PR, block on CI, merge.
2. Deploy via `deploy.py` from a clean detached origin/main worktree.
3. Dry-run the route on each month above (owner already ordered the write),
   read the consequences, then apply month by month; verify rows by API and a
   cold SPA read.
4. Record item 251 live (backlog + `status/p1-expense-reconciliation.md`).
5. Full checkpoint: log the `warn-send-output-truncated` false positive (fires
   on any command containing "sender").

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 250, 251
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "What our senders' notes decide"
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/sender_note.py`
