# Mini-Checkpoint: Brisken P1 R2 Flip Live

**Date:** 2026-09-07
**Status:** R2 round CLOSED — auto-materialize live, pool drained
**Type:** mini

---

## Summary
Completed the R2 staged flip with the owner watching: set
`EXPENSE_RECON_AUTO_MATERIALIZE=1` on Fly, ran the operator backfill
(three months minted by intake, 0 failures, all 24 pooled mails claimed),
and triaged the 10 sweep-re-pooled stranded archives with the owner
(5 TEST- drills dismissed, 5 real mails claimed into August by their
receipt-read dates — all `receipt_month_source == "receipt"`).

## What Was Done
- Verified the flag-OFF deploy inert (pool byte-identical to snapshot, 409
  probe naming the flag, split fields serving), incl. SPA drive via
  agent-browser (Playwright CDP :9222 was down)
- Owner approved via AskUserQuestion: leave the Hostinger marketing mail
  pooled (it filed into July), flip now; later: dismiss TEST, file real
  mails by receipt dates
- Flip + watched backfill: July 4 / August 14->21 / September 10 expenses,
  `created_by: intake`, "Filed into {month}" labels rendering in the SPA;
  Hostinger dedupe held (2 copies stayed dismissed, original filed once)
- Second claim pass filed the 5 real stranded mails into August
  (OpenAI, Anthropic, Moghul Mahal, Colmar train, Pressmaster)
- Ledger flip PR #695 merged (loop prompt R2 block -> LIVE, backlog item
  39 LIVE note, PROMPT-STATUS gate text)

## Current Status
Pool 0, held 0, 58 ingested / 17 dismissed. Live app serves R2+R3+R4
(item-38 program closed per #694). Rollback order if needed: flag OFF
first, then delete the month. Friction: none (1 `gate-fired-red-merge`
candidate discarded — merge was on green CI, gate misread the chained
form).

## Next Steps
1. OWNER: paste `lovable-months-origin-refusals-prompt.md` into Lovable
   (months "From email" badge + refusals split line), verify by field
   names `created_by` / `n_refused_ours` / `n_probes` / `kind_label`
2. Watch item 43 residuals (materialize watch-only list) now that the
   flag is on
3. The August month now holds R1/R3 candidates (Moghul Mahal personal
   card -> person/private surface; Colmar train -> trips): normal
   in-month review, no build work

## Files to Read First
- workspace/clients/brisken/status/p1-recon-loop-prompt.md (R2 status
  block, now LIVE)
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 39,
  42, 43)
