# Mini-Checkpoint: Recon Learning Rules And Spotcheck Ruling

**Date:** 2026-09-24
**Status:** Three owner rulings captured and verified against the code; two of them open bounded work that is specified but not started
**Type:** mini

---

## Summary

The owner answered the three open questions. Two of the answers turned into
investigations rather than acceptances: "only corrections may be memorized" is
a condition the code does NOT currently meet (three leaks, each verified in
source), and "cross reference the six SPOT-CHECK accounts against old Zoho
data" could not settle them, for an instrument reason worth not re-deriving.

## What Was Done

- **Ruling 1, "Publish may keep teaching, but only corrections may be
  memorized."** Audited all five learners on the Publish path. Two are clean
  (entity, field corrections). **Three leaks, each verified by reading the
  source, not taken from the agent's report:**
  1. `confirm_expense_category` stores the LLM's own guess into
     `category_overrides` and its docstring says it is then "taught at sign-off
     like any other correction".
  2. `PUT .../expenses/{id}` with `field="zoho_account"` writes
     `category = ov.get("category") or base.category` alongside the human's
     account, so an account-only edit teaches the model's category.
  3. `apply_self_confirmations` writes `STATUS_CONFIRMED` with
     `decided_by = tool`; the Publish-time filter feeding the vendor-alias and
     FX learner is `if d.status == STATUS_CONFIRMED` with **no `decided_by`
     check**, so pairings nobody looked at teach durable memory.
- **Ruling 2, the six SPOT-CHECK accounts.** Cross-referenced against
  `zoho-books-24mo.json` (2024-09-01..2026-09-18, 2,346 expenses, 1,171 bills,
  three real orgs). Probe validated first on five known-used accounts plus two
  negatives and a bogus id. All six returned zero card-expense rows, and the
  zero is nearly uninformative (see below). Owner then ruled: **flip the five
  `Y` rows to `N` pending Dirk.**
- **Ruling 3, Tier 2 ruled out** (not deferred): "during a trip there can be
  expenses from multiple categories", which is the reasoning already written
  into `posting_resolution.py`.
- **Probed the live Zoho scope** rather than trusting the memory that asserted
  it: `expenses.CREATE expenses.READ contacts.READ accountants.READ`.
  `bills.READ` is REVOKED, confirmed.
- Memory written: new `project_brisken_recon_learning_rules.md` (both rulings,
  leak locations), and `project_brisken_coa_expense_relevant.md` extended with
  the flip, the counts, and the regeneration path.

## What Did NOT Work (and why)

- **Settling the six SPOT-CHECK accounts from Zoho history.** All six read
  zero, and the zero cannot carry an N for two structural reasons. (1) The
  1,171 bills in the pull carry **no account field at all**, verified against
  the union of every key on every bill, so any account used only through
  supplier invoices is invisible. The proof is one of the six: `COGS - Support
  BRISKEN Tech / JB` reads zero card expenses while carrying 205,996.20 USD
  across 24 unbroken monthly bills from the contractor Juliano Carlo Brugnago
  Ltda. (2) Zero is the base case: over 24 months the expenses module touched
  13 of 125 postable accounts in BCS, 16 of 104 in BTS, 40 of 97 in CorpServ.
- **Deepening the invoice data.** Not possible: `bills.READ` is revoked, probed
  live. The 24-month file on disk is the last invoice snapshot without an owner
  re-grant in the Zoho console.
- **Two of the six are now known to be unanswerable by this route for their own
  reasons.** `R&D`'s zero means nothing (its Zoho id sorts between records
  created 2026-02-19 and later, so it did not exist for most of the window),
  and the JB row's mark `N` is right for a card allowlist while its stated
  reason "intercompany" is wrong (it is a contractor, already one of Dirk's own
  N classes).

## Current Status

`origin/main` moved to `0726b428` during the session (siblings are active).
Nothing from this checkpoint's rulings is implemented yet: all three items
below are specified and unstarted. Item 183 half B and the day's earlier
ledger are already merged (`f10edaa9`, `d326ae91`).

brisken: comms-log 16 days stale; platform ops status unknown.

## Next Steps

1. **Close the three learning leaks** so "memorized" means "a human stated
   this". Leaks 1 and 2 need a provenance marker distinguishing a human-stated
   category from a carried-through machine one; leak 3 is a `decided_by` filter
   on the alias/FX learner. Measure and report how much alias learning leak 3's
   fix removes, since most matches are tool-confirmed.
2. **Flip the five SPOT-CHECK rows Y -> N**: `Travel Expense: Per diem` (BCS),
   `Tax Management Services - Holding` (BCS and BTS, code E900020), `R&D`
   (BCS), `COGS - CONS - Travel Expense (Third Party Reimbursement)` (BTS).
   Edit `derive_expense_relevant.py` (our derivation, not Dirk's marks), then
   the workbook, then
   `uv run tools/compile-brisken-gl-taxonomy.py --workbook <sheet> --revision
   <date> --expected-counts <org=n,...>`. New counts: BCS 64, BTS 62, CorpServ
   68, total 194. Update every test asserting 199 / 67 / 64.
3. Fix the JB row's reason from "intercompany" to "contractor".
4. Change `TIER2_DEFERRED`'s comment from deferred-pending-a-ruling to ruled
   out, with the owner's reason.
5. Then the engine conversion (the original queue item 2 onward).

## Files to Read First

- `~/.claude/.../memory/project_brisken_recon_learning_rules.md`
- `~/.claude/.../memory/project_brisken_coa_expense_relevant.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 183, 184
- `<module>/src/expense_recon/zoho/posting_resolution.py`
