# Mini-Checkpoint: Zoho Posting Refuses Unassigned Cards

**Date:** 2026-09-23
**Status:** Shipped (PR #1211, `b4186a7a`). Sandbox only, nothing deployed.
**Type:** mini

---

## Summary

`(paid-through - assign)` / `(entity - assign)` in the `Paid Through` and
`Legal Entity` cells are now the hard refusal `card_or_entity_unassigned`,
put in place while both columns are still cosmetic so per-org multi-card
routing is built on top of a guard rather than behind one. Read-only
investigation answered both double-count questions: August's two USD 576.00
Zoho charges are ONE charge, and July's Hostinger `H_46243348` is the same
shape and larger.

## What Was Done

- **The refusal**, in `build_expense_payload`, with its own reason code so
  the summary tells it apart from `account_unresolved` (different question,
  different people, different fix). The two strings are imported from the
  module that writes them; `accounts.py` lost its re-spelled copy and a test
  pins `NEVER_MAPPED` to the imported values.
- **Two ordering calls, each proven with `tools/regress_check.py`** rather
  than asserted. The ledger is now read BEFORE the payload is built (an
  already-posted row is history, so `already_in_ledger` answers first);
  inside the build the stale-date guard still outranks the new one.
- **Measured both months rather than guessing.** Against the durable ledger
  the refusal mix is byte-identical to before: July 41/3/2, August 19/1. On
  a FRESH ledger, which is the production case: July 41 -> 30 postable (11
  held, carrying USD 54,235.71 of 56,340.44) and August 19 -> 17.
- **The scan reads every row of a purchase.** July's `H_46243348` has two
  rows that disagree, the first naming the card, the second reading both
  placeholders; a header-only check passes it.
- **Task 2 answered read-only.** August's statement holds exactly one
  `ZOHOCORP` line at 576.00 on 2026-08-30. `0006` is the Zoho Store payment
  confirmation (Payment ID `RPS2004132748584`) which says the invoice
  follows separately; `0007` is that invoice (`50102456463`, "Payment Made
  (-) 576.00 / Balance Due US$0.00"). Dedup could not group them: a payment
  id and an invoice number share nothing, and the vendor strings differ.
- **A second double-count found while measuring.** July's Hostinger
  `H_46243348`: two documents 25 days apart share one reused invoice number,
  `group_by_reference` merged them into USD 345.22 dated the earlier one,
  and July's statement backs a single 172.61 charge. TEST-BTS is overstated
  by 748.61 in total.

## What Did NOT Work (and why)

- **Showing the new guard's effect through `run_month` on a fresh ledger:**
  occupancy for both months is `ALREADY_OCCUPIED` and a fresh ledger holds
  none of the batch, so the runner aborts at stage 2 by design. Measured
  through `plan_expense_post` with a throwaway ledger and the live chart
  instead, which is the same posting path minus the occupancy stage.
- **A header-only placeholder check (`group.cell`):** it under-reports.
  July's `H_46243348` carries the placeholder on its second row only, so the
  census built on `cell()` missed it and the any-row scan caught it. The
  gap is what justified scanning every row.

## Current Status

PR #1211 merged to main (`b4186a7a`), suite 3055 passed / 2 skipped, ruff
clean, both regress checks green. Nothing deployed and no live month
touched. TEST-BTS still holds both double-counted purchases; correcting
either needs the sandbox expense deleted plus its ledger row, which is the
owner's call.

## Next Steps

1. **Owner decision on the two double-counts** (748.61 in TEST-BTS): correct
   them, or leave the rehearsal as-is and fix the source data before the
   production run.
2. **Card and entity assignment is the gate on production.** 11 of July's 46
   purchases and 2 of August's 20 are unassigned; the 11 carry 96% of July's
   value.
3. **A same-reference group spanning different dates is not refused.** The
   Hostinger case shows `group_by_reference`'s one-reference-one-purchase
   assumption breaking on a vendor that reuses invoice numbers. Wants the
   owner's read on the pair before a guard is built.
4. Tasks 3 to 5 from the brief stay owner-side: the five residual review
   rows, production GL mapping sign-off, and the manual-entry freeze cutoff.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md` (the two 2026-09-23 sections at the end)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/expense_post.py`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
