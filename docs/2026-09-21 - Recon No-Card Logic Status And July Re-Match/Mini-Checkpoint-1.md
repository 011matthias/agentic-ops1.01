# Mini-Checkpoint: Recon No-Card Logic Status And July Re-Match

**Date:** 2026-09-21
**Status:** Item 151 record corrected and merged; live July re-matched; September's statement is the next live test
**Type:** mini

---

## Summary

Answered where the no-card matching logic stands (backlog item 151, owner note
X1), found the status record stale in three ways, then re-matched live July on
the owner's order and recorded the measured result. The description fix moved
both rows it was built for and changed nothing else.

## What Was Done

- **Read the live state rather than the record.** Backend PR #1096 is merged at
  Fly v186, the SPA half was bundle-verified 2026-09-20, and both status entries
  still read "PR pending, Fly release pending, SPA NOT pasted". Live `/healthz`
  confirms the app runs today's `main` (640be61b).
- **Re-matched live July on owner order**, read-first: saved the whole pre-state
  (`/api/runs/50622baec444` + `/api/expense-batches/50622baec444` + `/api/settings`),
  then `POST /api/expense-batches/{id}/refresh-master-data`, then diffed every
  row, candidate, expense and summary field against the saved copy.
- **Result:** Microsoft 718.20 `vendor_pct` 50 to 100 and score 92 to 100; Amazon
  315.56 `vendor_pct` 57 to 100 and score 80 to 87. 31 reconciled / 7 review / 73
  unmatched unchanged. No row changed bucket; no decision, entity or expense
  field moved. `changes: []` (the card snapshot already equalled Settings), 13
  judgments reused, 0 new model calls, cost delta $0.00085.
- **Corrected a wrong prediction in the record.** The 2026-09-18 line said the
  Microsoft row was "waiting for a click" under the self-confirm floor. Both rows
  were already in the `reconciled` bucket (Microsoft `turn: posted`, Amazon
  `confirmed`), and `confirmable_pair` requires `turn: decide`, so neither could
  ever have self-confirmed. The fix was cosmetic on July's live rows and
  structural for the next month whose merchant words sit behind a reference
  number.
- **Shipped the record** as PR #1162, merge `2a72ea41`, six CI checks green.
  Docs-only, two status files.
- **August deliberately not re-matched:** its two `none`-evidence pairs are
  already reconciled, so a re-match would move nothing.

## What Did NOT Work (and why)

- **`gh pr checks <n> --watch` immediately after `gh pr create`:** exited at once
  with "no checks reported on the branch" instead of waiting. The workflow run
  had not registered yet, so `--watch` had nothing to attach to and treated the
  empty set as terminal. A bounded poll on the rollup (`checks=N`) worked on the
  first try 30 seconds later.
- **Reading expenses off the run payload:** `/api/runs/{id}` returns
  `expenses: []` for a statement month; the expense spine lives on
  `/api/expense-batches/{id}`. The first probe therefore reported "expenses 0,
  card_source {}" for July and August, which reads like an empty month and is
  not. Both surfaces are needed for a complete month picture.

## Current Status

Item 151 is shipped, deployed, SPA-applied and now correctly recorded. Live July
carries the corrected scores as of 2026-09-20 22:10 UTC. The no-card review
clause (`no_card_rival_on_other_card`) still fires on 0 pairs across all nine
datasets; it has not yet had a case to catch. September holds 27 no-card
receipts and no statement, which is the first real test.

brisken platform: unknown plan, ops/mo not assessed.

## Next Steps

1. When September's statement lands, read `review_code` on the resulting
   candidates: first live exercise of the no-card fallback and its review clause.
2. Item 154's merchant-card learner pays off as Criss signs off months; the 28
   live merchants still carry no learned card.
3. brisken comms-log is 13 days stale.
4. Two p2 status files are stale (`p2-product-decks` 60d, `p2-targeting` 61d).
   Untouched by this session and out of its scope; bring current from a p2
   session rather than guessing from p1.

## Files to Read First

- workspace/clients/brisken/status/p1-improvement-backlog.md (item 151, the live
  re-match block)
- workspace/clients/brisken/status/p1-expense-reconciliation.md (the item 151 row)
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md
