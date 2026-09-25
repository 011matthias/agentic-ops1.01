# Checkpoint: Brisken Recon Item 216 Build 2

**Date:** 2026-09-25
**Status:** Build 2 complete and live: steps 1-3 on Fly, both SPA prompts published and driven. Levers 1/1b wait on Dirk and the owner.

---

## Summary
Step 3 gave both month payloads a who-answered count, `summary.categories_by_origin`. The owner then re-pasted the step-4 "Suggested" prompt, which the 13:50 audit had found missing, and the new count-line prompt; both are verified on the published app.

---

## What Was Done This Session

### Step 3: counts carry who answered (PR #1455, Fly `2b6eeb7f`)
1. Measured before code on the 03:05 backup, all three GL months: the 164 receiptless model guesses sit on 25 yellow, 61 gray, 76 receipt-owing charges and 1 fee line, so `n_charges_category_guessed` = 0 / 0 / 1 is the correct BLOCKER count, and nothing answered "who answered".
2. `service.row_answer_origin` + `categories_by_origin`: `{person, rule, suggestion, none}` read off each row's own `posting_category` / `suggested_category`; one row, one count, under its least decided answer. Wired into the run summary (over `rows[]`) and the grid summary (over the rows `n_expenses` counts, copies and bills out).
3. Tests: 2 route-level (grid: Stripe invoice+receipt copy, a move to Bills, a Confirm; run: open / ruled / gray / yellow charges + the charge category PUT reply) + the view-contract partition test. Five wiring points bite under `regress_check`. Suite 3865 passed; CI green; merged `b15a2639`; `deploy.py` verified `/healthz` + machine size.
4. Live, read-only: September grid 0/1/31/36 and run 0/1/43/7, each equal to the rows; blocker 1, need_receipt 28 unchanged.
5. Docs: api-contract "Who answered: `categories_by_origin`"; `docs/lovable-categories-by-origin-prompt.md` + PROMPT-STATUS row; backlog step-3 paragraph + Shipped row 139; memory `project_brisken_recon_categorization_analysis` (never widen the blocker). Mini-checkpoint 4 (PR #1456).

### Published SPA verified after the owner's paste
1. SPA repo carries both prompts (`630e9a4`, `68b1f09`); bundle carries every EN + PT key.
2. September, cold drive, published app: Expenses 31 badges + 31 Confirm buttons (= the 31 counted suggestion rows; the 5 others are copies/bills), both "Who answered" lines equal the payloads, the line is hidden inside a card tab; Matching's charge tabs show the badge on 29 receiptless + 12 matched rows (the missing one per tab is presumably a decided row the default filter hides; not checked).
3. PROMPT-STATUS rows for both prompts are the sibling's PR #1461 (same verification on July, including an aborted Confirm POST); not duplicated.

---

## Key Decisions Made

### The blocker keeps its meaning
- **Choice:** did not turn `n_charges_category_guessed` into "a count of suggestions" as the handover prompt worded it; added a separate split instead.
- **Rationale:** it is the month-complete blocker the SPA pill lists beside `n_charges_need_receipt`. Widening it would put 45 booked July charges in the pill (against the 2026-09-17 gray ruling) and list 76 charges twice in August/September.

### Split counts over the rows that count
- **Choice:** grid split over `n_expenses` rows (decided copy and bill excluded), run split over every charge row including yellow and gray.
- **Rationale:** the grid's box counts already exclude copies and bills, so the split partitions the same set and can be pinned as a sum; the run view's question is who answered each charge, booked or not.

---

## What Did NOT Work (and why)
- **Widening `n_charges_category_guessed` (the prompt's wording):** not built; the blocker's 0/0/1 is correct and a wider count double-lists receipt-owing charges and blocks on gray ones (see Key Decisions).
- **Copy exclusion under `regress_check`, first pass:** TEST DOES NOT BITE; no fixture held a decided copy in the grid. A Stripe-named invoice + receipt pair (the tool decides the copy itself) made it bite.
- **Run-view test expecting `n_charges_need_receipt == 1`:** it is 2; the rule-answered FIGMA charge owes a receipt too.
- **Counting Matching badges on the tab's default view:** 0 badges on "Receipts without a charge", which has no category column. Deep-linking `?view=unmatched` did not switch either: the page reloads stored filters on mount and overwrites the view from the link (SPA defect, pre-existing). Clicking the tab worked.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py` | Edit | `row_answer_origin`, `categories_by_origin`, wired into both summaries |
| `.../src/expense_recon/web/month_readiness.py` | Edit | docstring: the blocker is not the guess count |
| `.../tests/test_counts_by_origin_item_216_build2_step3.py` | New | 2 route-level tests |
| `.../tests/test_view_contract.py` | Edit | partition test |
| `.../docs/api-contract.md` | Edit | step-3 section + summary row |
| `.../docs/lovable-categories-by-origin-prompt.md` | New | SPA prompt (published) |
| `.../docs/PROMPT-STATUS.md` | Edit | step-3 prompt row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edit | step-3 paragraph, Shipped row 139 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edit | item-216 row: step 3 live, both prompts published |

---

## Current Status
Item 216 Build 2 is finished end to end: the model is offered leaves only (step 1), its answer is a labelled suggestion that never posts (step 2), the payloads say who answered (step 3), and the SPA shows the badge, the Confirm and the count line (step 4 + step-3 prompt). Nothing written on Criss's months. brisken ops: platform unknown plan, ~?/? ops/mo, last assessed ?; comms-log none. Live Fly commit is a sibling's later deploy (`9d945667`), which carries step 3.

---

## Next Steps
1. **Dirk + owner:** item 216 lever 1, the per-company account map (Dirk's 7 questions in `context/expense-reconciliation/merchant-account-suggestions-260925.md`; owner call on OpenAI / Anthropic / Lovable). Lever 1b non-gated registry aliases are operator edits.
2. After the next Zoho re-pull: `tools/recon-categorization-score.py` to judge Builds 1-3 by right answers.
3. Optional SPA fix: honour `?view=` on first load (the stored-filter reload in `RunWorkbench.tsx` overwrites it).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 (levers table, "Build 2 step 3, built")
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "The model suggests..." + "Who answered"

### Open Questions
- None open in this session's scope.

### Working Notes
- Matching tab entry: it opens on "Receipts without a charge" (no category column). Probe category cells by clicking "Charges without a receipt" / "Matched"; the `?view=` query is ignored on first load.
- The 5 September suggestion rows without a badge on Expenses are counts_in_total=false rows (36 suggested_category vs 31 in the split on the same payload).
- Instruments in `agentic-ops1-build2c/.scratch/`: `measure_step3.py`, `regress_step3.sh`, `drive_step3.py` (live, one read each), `dump_sep.py` + `drive_views.py` (published SPA fed backup payloads, zero live month reads).

### Reference Materials
- PR #1455 (step 3), #1456 (mini-checkpoint 4), sibling #1461 (PROMPT-STATUS verified)
- SPA commits `630e9a4`, `68b1f09` in `011matthias/brisken-expense-review`

---

## How to Continue
Resume brisken; item 216's remaining levers are data and decisions, not code. Before any code on the categorizer, re-run the score tool against a fresh Zoho pull.

---

## Strategic Feedback

### What Worked Well This Session
- Stating cause, symptom patch and measurement before code caught that the prompt's own step would have broken an owner ruling; the 164-row breakdown (yellow / gray / receipt-owing / fee) made the call checkable in one table.
- `regress_check` over every wiring point found the one exclusion (copies) no test could see, before merge.

### Suggestions
- Promote `warn-merge-chained-after-checks-watch` to `block`: two warn rules exist for it and it still happened (docs PR #1456). Chained, the merge runs whatever the watch returns.

### System Health
- The drive scripts are copied per step (`drive_step1..3`, `drive_publish`, `drive_views`) with the same login / replay / guard code; a shared `tools/` drive helper that caches each month's payload on disk would make "read each month once" the default rather than discipline.
- Autonomy: 1 human intervention (the owner's Lovable paste, an owner-only action).
