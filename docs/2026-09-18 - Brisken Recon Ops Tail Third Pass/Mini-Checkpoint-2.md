# Mini-Checkpoint: Brisken Recon Ops Tail Third Pass

**Date:** 2026-09-18
**Status:** Ops-tail fence complete; everything left is owner-gated
**Type:** mini

---

## Summary

Third ops pass over backlog items 123, 125, 127, 128 and the UI prompt for 129.
All five were already shipped; this pass verified the two that were still only
asserted, and closed the cron question with a control instead of another
zero-count report. One PR, docs only, no code and no deploy: #1112 (merge
`938c533e`).

## What Was Done

- **Item 129 is applied and verified.** The owner published
  `lovable-rematch-visible-prompt.md` between the second and third pass, so the
  standing "written, not pasted" rows were false. Verified by field name on a
  closed corpus (44 chunks / 1,186 KB, a second discovery pass found 0 further
  references): `last_rematch` and `rematch_pending` are read in
  `chunk-SettledByBadge-BWMNqN58.js`, and `mh.rematch.last` plus all 12
  `mh.rematch.trigger.*` labels sit in the i18n chunk in both languages. Then
  driven cold twice in headless Chrome on August `/runs/074a7b8905d7`. EN:
  "Last matched Sep 17, 2026, 01:35 PM (an expense was edited): 9 of 114 charges
  paired, 1 to review." PT: "Última comparação 17 de set. de 2026, 13:35 (uma
  despesa foi editada): 9 de 114 cobranças pareadas, 1 para revisar." Both agree
  field for field with the payload read minutes earlier. One non-GET per drive,
  the login POST. Row moved from Not applied to Applied.
- **Item 123: the cron has never fired, and now with a control behind it.**
  `event=schedule` is still `total_count` 0 at 16:49Z, 2h37m after the workflow
  landed on main with `*/10 * * * *`; all three runs it has ever had are
  `workflow_dispatch`. Configuration was ruled out from the API rather than the
  local tree (schedule on main, workflow `active`, Actions enabled, repo public,
  not a fork, not archived). The differential probe is what makes it a finding:
  GitHub's scheduler HAS worked in this repo (morning-briefing 20 scheduled runs
  through 2026-06-27, eod-capture 14, weekly-review 3), all three are
  `disabled_manually` since, and `ai-visibility-probe` declares no `schedule:` so
  it is not a control. Three options and a recommendation are recorded in the
  backlog item. Nothing was built.
- **Item 125 leg 2 is dated, not merely pending.** `transport_tls` is absent from
  all 85 `submitted_by` blocks across the seven live batches because the newest
  arrival in the store (2026-09-18T12:02:48Z) predates the release that records
  it (Fly v187, 14:46:41Z) by 2h44m. Leg 1 re-verified live, read-only: EHLO
  advertises STARTTLS, TLS 1.3, no MAIL FROM.
- Feedback log read first: 70 notes, unchanged, newest is the owner's #70
  (2026-09-18 10:19Z, "add receipts function ... does not really add it"),
  untriaged and outside this fence. Nothing new from Criss.
- Two sentences that had gone false were fixed in place rather than appended
  around: Shipped row 96's "deploy + Lovable paste pending" and row 94's
  "deploy + EHLO + first-mail check pending". The Not-applied intro no longer
  hardcodes a count (it read "One prompt is out" above four rows, because four
  sessions append to that table in parallel); it now points at the rows.

## What Did NOT Work (and why)

- **The first Portuguese cold drive returned a confident negative.** It reported
  no header and an English page. The app reads
  `localStorage.getItem('brisken.lang') === 'pt' ? 'pt' : 'en'`, so the `pt-BR`
  I set (the tag the prompt and PROMPT-STATUS both use for the LANGUAGE) silently
  became `en`. The tell was an unplanned control: the rendered body was 6,571
  characters in both runs, to the character. Identical output across two states
  that must differ is the signature of a probe that never changed the state. With
  `pt` the body is 6,753 and the header is Portuguese. This is the fourth blind
  instrument in four sessions on this surface and is written up beside the other
  three in PROMPT-STATUS.
- **The first bundle grep reported `last_rematch` and `rematch_pending` absent.**
  It had fetched only the five bundles the SPA shell names, while the app
  lazy-loads ~44. The negative was an artefact of a partial corpus; both names are
  present in a chunk the shell does not reference. Fixed by crawling to closure
  and re-running, which is the only reason the positive is trustworthy.
- **`ai-visibility-probe` as a scheduler control.** It is `active` with zero
  scheduled runs, which looks like corroboration, but it declares only
  `workflow_dispatch`. A workflow with no cron proves nothing about cron delivery,
  so it was discarded rather than cited.

## Current Status

All five fenced items (123, 125, 127, 128, 129) are shipped, and the two that
carried unverified halves now carry evidence. Fly is at **v189**
(2026-09-18T16:31:32Z); siblings deployed v188 and v189 during this pass, so the
brief's "still v187" was already stale. This pass deployed nothing. `main` is at
`938c533e`. No ops worktree or branch of mine is left.

The ops tail has nothing left that is mine to do autonomously. The remainder is
owner-gated, so no continuation prompt was written (session-loop step 9).

## Next Steps

1. **Owner decides where the uptime watcher lives** (item 123): wait on GitHub's
   best-effort scheduler, add a redundant local runner (the `MejiWeeklyReview`
   precedent, but back on the laptop item 121 already judged insufficient), or
   point a free external monitor at `/healthz` as the item originally proposed.
   Recommendation: the external monitor, with the cron left running underneath at
   no cost, because it is the only option whose vantage point shares a failure
   mode with neither GitHub nor the laptop.
2. **Owner decides when to fire item 123's real alert path.** It has still never
   run for real; only the dry run has. Deliberately not fired unattended: the
   mail's subject reads "expenses.brisken.com is down" and would reach the owner
   as a false alarm. When wanted: `gh workflow run expense-recon-uptime.yml -R
   011matthias/agentic-ops1.01 -f api_override=https://127.0.0.1:9`, then re-run
   with no override to close the issue and send the recovery mail.
3. **Item 125 leg 2 closes itself** on the first mail that arrives after
   2026-09-18T14:46:41Z: read `submitted_by.transport_tls` on the newest
   mail-sourced receipt. A `false` names a sender still delivering in the clear.
4. Owner's call on the recorded residues: 127's per-month verdict tally, 128's
   reader-version stamp, 129's per-file "matched with X" line, 125's CA
   certificate, 123's Brisken-mailbox recipient.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 123, 125,
  129; the cron options are in 123's body)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md`
  (item 129's Applied row; the four blind-instrument write-ups)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (rows for 123,
  125, 129)
- `docs/2026-09-18 - Brisken Recon Ops Tail Second Pass/Mini-Checkpoint-1.md`
  (the pass this one continues)
