# Checkpoint: Expense-Recon Items 83-88

**Date:** 2026-09-17
**Status:** Items 83 + 75, 84, 85 + 86 and 88 shipped (Fly v142); all four SPA prompts published by the owner, not yet verified; items 87 and 82 not started

---

## Summary
One session took the 2026-09-16 feedback wave from backlog to production: the unmatched lists say what they hold, the Expenses boxes open their rows, text-looking controls became buttons, and Publish now saves a month's corrections to memory. The owner pasted and published all four prompts at the end; verifying them is the first job of the next session.

---

## What Was Done This Session

### Items 83 + 75 (PR #932, Fly v140)
1. Measured against `labels.csv` before building. The date edge read before the card names 11 of 14 labelled live receipts correctly; item 69's card-first order names 9.
2. `unmatched_reasons.py` + a view-time split in `build_view`. Decided copies go to `copies_set_aside[]` and leave the open counts. Receipts carry 5 reason codes; charges carry their own 4.
3. Live matched the predictions exactly: July 13 -> 11 + 2 set aside, August 21 -> 10 + 11; receipt match rate 75.0 -> 78.0% and 32.3 -> 50.0%.

### Item 84 (PR #935, Fly v141)
1. Resolved the two open questions first. Categorized 49 vs 51 is three two-line receipts. MISSING RECEIPT IMAGE 2/1 was false: the image endpoint served all three files (200, PDF).
2. `expenses[].boxes[]` on every row, every box count summed from rows, and `n_needs_company_or_person`. Live: all 11 counts equal their rows on both months.

### Items 85 + 86 (PR #938)
1. One SPA-only prompt: 20 controls anchored by i18n key at SPA head `dcd875a7`, fold toggles that name what they show, and the booked fold naming `statements[].file`.

### Item 88 (PR #940, Fly v142)
1. The month sign-off in code is Publish. Publishing saves through `commit_month_memory`; a digest in the new `memory_commits` table blocks double counting; a failed save never fails the publish.
2. Nothing has fired live: `published_runs` is empty and memory counts are 103 / 0 / 0 / 0 / 0.

### Ledger and handoff
1. Mini-checkpoints #934, #937, #939, #941; memory `project_brisken_expense_recon_usability_loop.md` updated; every worktree and branch removed.
2. A continuation prompt for a fresh chat was handed to the owner (verify the four published prompts, then 87, then 82).

---

## Key Decisions Made

### Charges get their own reason codes
- **Choice:** `not_a_purchase`, `receipt_held_by_another_charge`, `already_booked`, `no_receipt_found`, instead of the brief's five receipt codes.
- **Rationale:** the receipt vocabulary says false things about a card charge ("not a card charge").

### Date edge before card, bounded to 31 days
- **Choice:** diverge from item 69's card-first order.
- **Rationale:** measured on labels, +2 correct (August's two 08-31 Google invoices), none lost; an invoice dated in March is not "neighbouring".

### Missing receipt image = no file AND no reference, on both payloads
- **Choice:** fix the count's answer rather than add a new count name.
- **Rationale:** the question stayed the same; the answer was wrong, and one name must answer one question on both payloads.

### Publish is the sign-off, built without re-asking
- **Choice:** wire item 88 to Publish although no month has ever been published.
- **Rationale:** it is the app's only sign-off and the ruling said not to re-ask; the empty `published_runs` is reported instead.

### Item 88 not driven live
- **Choice:** route tests + no-regression reads and drive only.
- **Rationale:** publishing is a write on Criss's months, and a scratch month could claim pooled mail.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/unmatched_reasons.py` | created | reason-code classifier (83 + 75) |
| `.../src/expense_recon/web/service.py` | edited | view-time copy split; boxes + `is_categorized` + `receipt_image_missing`; `commit_month_memory` + digest |
| `.../src/expense_recon/web/store.py` | edited | `memory_commits` table, get/set, delete cascade |
| `.../src/expense_recon/web/app.py` | edited | publish saves memory; the button uses the shared helper |
| `.../tests/test_unmatched_reasons.py`, `test_expense_boxes.py`, `test_memory_at_signoff.py` | created | route-level proofs |
| `.../tests/test_view_contract.py`, `test_duplicate_collapse.py`, `test_duplicate_rows.py`, `test_reference_duplicates.py`, `test_web_duplicates.py`, `test_web_publish.py` | edited | new pins; old placement assertions updated |
| `.../docs/api-contract.md` | edited | three sections + counts rows |
| `.../docs/lovable-unmatched-reasons-prompt.md`, `lovable-expense-boxes-prompt.md`, `lovable-controls-as-buttons-prompt.md`, `lovable-memory-at-signoff-prompt.md` | created | SPA halves |
| `.../docs/PROMPT-STATUS.md`, `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | edited | Shipped rows 52-54, item paragraphs, status rows |

---

## Current Status
Backend v142 live, module suite 1974 passed / 2 skipped. The owner reports all four prompts published (2026-09-17); PROMPT-STATUS still lists them as Not applied until a bundle audit and cold drive confirm them. Items 87 and 82 are open. brisken ops status: platform unknown (no infrastructure assessment); comms-log none. Two p2 status files are stale (`p2-product-decks`, `p2-targeting`); they are untouched here and belong to their own sessions.

---

## Next Steps
1. Verify the four published prompts: bundle audit on the PROMPT-STATUS names, cold drive of July + August through each prompt's check section, move the rows to Applied (item 88's toast is bundle-only).
2. Item 87: read July's card-review strip first (rows, path per row, whether digit-bearing hints really are not remembered).
3. Item 82: simulate ECB monthly rates with `tools/recon-match-attribution.py` on six bundles + both live months, report bucket changes, then build.
4. Structural fixes from the friction rows below (scaffold renumbering, consumer-gate background close, regress_check unparsed-summary verdict, pressure meter in worktrees).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md` (Not applied table)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 87, 82; Shipped rows 52-54)
- `docs/2026-09-16 - Expense-Recon Item 88/Mini-Checkpoint-1.md`

### Open Questions
- None needing the owner. Item 82's simulation may produce one (a pair that changes bucket against its label).

### Working Notes
- CI DOES run the module suite (`.github/workflows/expense-recon-tests.yml`, check `test`); the brief and older memory lines said it does not.
- July booked fold under Charges without a receipt holds 48 rows (47 already_booked + the held GOOGLE Workspace 71.64, also yellow); duplicates panel = 2 copies + 3 kept apart.
- `gh pr checks --watch` right after a push exits 0 with "no checks reported"; wait on `gh run list --branch` filtered by head SHA until both workflows complete.
- `session_state.py --status` run from a worktree read `calls=1`; the critical band (~250 calls) was judged by count.

### Reference Materials
- Live API `https://brisken-expense-recon.fly.dev`, SPA `https://expenses.brisken.com`, SPA repo `011matthias/brisken-expense-review`
- ECB Data API series `EXR/M.USD.EUR.SP00.A`, `EXR/M.BRL.EUR.SP00.A`

---

## How to Continue
Paste the continuation prompt handed over at the end of this session into a fresh chat; it carries the context, the hard no-live-writes rule, the verification steps and the traps above.

---

## Strategic Feedback

### What Worked Well This Session
- Predicting live numbers from the payload before each deploy, then reading them back: every prediction for 83 + 75 and 84 matched exactly, so deploy verification was a comparison rather than an impression.
- Treating "RED (no pytest summary line)" as unproven and reproducing both mutations by hand before counting them.

### Suggestions
- Make `checkpoint_scaffold.py` accept the prose file already written at `pre`'s target path (or name the target only at `finalize`). The renumbering trap hit three sessions in one day and is documented, not fixed.

### System Health
- Four enforcement tools misreported state in one session (scaffold numbering, consumer gate closing on a backgrounded drive, regress_check verdict without a parsed summary, pressure meter reading 1 call). Each was caught by the agent, but together they mean a hook saying "closed" or "bites" still needs a second look.
- Autonomy: 0 human interventions (the owner's prompt pastes are designed owner steps) — fully autonomous session.
