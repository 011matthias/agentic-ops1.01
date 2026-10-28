# Mini-Checkpoint: Single Card Gate And The Zoho Account Answer

**Date:** 2026-09-24
**Status:** Items 169 + 173 live; 171 and 173's second half open; 172 answered, awaiting a hand
**Type:** mini

---

## Summary

The second half of the attribution session. Item 169's win was measured again
and found to be the wrong kind: all 12 rows it filled were OpenAI, on a card
the evidence contradicts 8 to 1. The owner ruled to gate it, item 173 shipped
the gate, and the 12 rows are deliberately blank again. Item 172's answer was
then read straight out of Zoho rather than left as a question.

## What Was Done

- **Item 173 shipped and deployed** (PR #1228, merge `46130b06`, Fly machine
  `7843d54b579598`). `service.merchant_vouches_one_card` applies a remembered
  card only to a brand the registry vouches is paid on ONE card, mirroring the
  rule note item M2 already applies to the registry's own card learner. A brand
  the registry cannot resolve is deliberately NOT vouched, which is what makes
  it bite: OpenAI is not in the registry, and adding it is the owner's call.
- **The read that produced the ruling.** Across all seven live batches, every
  row sitting on a remembered card was OpenAI, and OpenAI's hard evidence (a
  printed card number, a reviewer's own pick, or the statement) is card-9693
  eight times against 3645 once. Ten vendors carry evidence on more than one
  card. Put to the owner with that split; he chose to gate.
- **Item 172 answered** (PR #1242) from Zoho's own `chartofaccounts`, read-only:
  Corporate Services (`822741658`) has exactly ONE Chase Visa credit-card
  account, `CHASE VISA - 2838 - TRAVEL`, and cards `3876` and `card-0340`
  already point at it. There is no 3645 account and none is needed; the entry is
  a typo of the right idea. Not written: a settings write on Criss's live master
  data is hers.
- **Item 170 closed** (PR #1224) on the owner's direction that category work
  stops. Its measurement is kept as record under a banner saying not to resume.
- **Checkpoint addendum** (PR #1230): yesterday's checkpoint claimed 12 rows
  filled, which item 173 reversed hours later. Corrected rather than left to
  mislead.

## What Did NOT Work (and why)

- **`GET /books/v3/organizations`**: 401. The Books token's scope is now
  `expenses.CREATE expenses.READ contacts.READ accountants.READ` -- it has LOST
  `settings.READ`, which that endpoint needs, and GAINED `expenses.CREATE`,
  which `project_brisken_zoho_books` still records as the missing grant blocking
  any post. Org ids had to come from `coa_gate.py` instead.
- **First chart-of-accounts filter**: returned nothing for all eight orgs, which
  looked like "no card accounts exist". A raw dump proved the probe wrong: 177
  and 199 accounts, with the card accounts present under plain names. The filter
  was blind, not the data empty.
- **A browser drive buried inside a compound Bash command**: the deploy gate
  did not see it and refused the stop, correctly. Separate foreground
  `agent-browser` calls (`open`, `fill`, `click`, `eval`) are what register.
- **Writing the 3645 fix**: not attempted. Correct value known, but a
  `PUT /api/settings` on Criss's live master data is hers or the owner's.

## Current Status

Live on Fly `46130b06`. September: card-less 26, no entity 25, no person 25 --
the pre-169 numbers, on purpose. Confirmed in the rendered SPA: 12 of 19 OpenAI
rows read "No legal entity yet. Assign the paying card or set the entity", and
the one row still naming 3645 is Criss's own override, which correctly stands.
July and August unmoved throughout.

Item 169's structural fix survives the gate and is still worth having: a
correction is no longer frozen at ingest, so the day a single-card brand is
corrected, every existing month takes it.

No live writes were made to Criss's months or master data.

## Next Steps

1. **Item 171** -- pass `settled_cards` into the sign-off learner's resolution,
   with a statement-attached month, a publish, and a regress-checked bite test.
   24 rows waiting, zero live effect until a month is signed off. Consider
   whether item 173's single-card gate should apply there too.
2. **Item 173's second half** -- `ExpenseMemory.apply` still stamps a remembered
   card at INGEST without the gate.
3. **Item 172 (a hand, not a build)** -- set card `3645`'s `zoho_account` to
   `CHASE VISA - 2838 - TRAVEL` in the Cards editor.
4. **Criss's** -- the two August rows where her card pick contradicts the
   statement she confirmed.

## Files to Read First

- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 169-173)
- `tools/recon-attribution-replay.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py`
  (`merchant_vouches_one_card`, `fill_remembered_cards`, `resolve_batch_row_cards`)
