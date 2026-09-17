# Checkpoint: Expense-Recon Item 87

**Date:** 2026-09-17
**Status:** Item 87 live (Fly v143); prompts for 87 and 89 pending the owner's paste; item 82 not started

---

## Summary
The four SPA prompts the owner published are applied and render as specified. A receipt that prints no usable card now gets a card picked on its own row, remembered for the vendor when the month is published. Mini-Checkpoint-1 in this folder holds the per-step evidence; this file adds the decisions, working notes and the session audit.

---

## What Was Done This Session

### Prompts verified (PR #943)
1. Bundle audit: 48 chunks, 1,047 KB, controls hit, all 15 decisive names present.
2. Cold drive, EN + PT on July and August, 236 GET / 7 OPTIONS / 0 writes. The evidence rows are in `PROMPT-STATUS.md`, and the Not-applied table was empty until #947 added two rows.

### Item 87 (PR #947, Fly v143)
1. Read: the notice is true where shown. Two strip assignments never stuck, and 24 of July's 33 no-company rows had no path but Confirm private.
2. Built: the `card_key` per-row fix, `expenses[].card_source`, and memory at Publish via a vendor field correction on `Receipt.card_key`. Also the exact-alias precedence in `resolve_card` and the masked-BIN rule in `learnable_hint_tokens`.
3. Suite 1974 -> 1983 / 2 skipped. Seven regress proofs, and the live payload diff was exactly as predicted.

### Item 89 (owner, mid-session)
1. Traced the green "Reconciled" badge to `MonthsHome.tsx` (shown on `has_statement`) and wrote `lovable-matched-with-statement-prompt.md`.

---

## Key Decisions Made

### The per-row fix is remembered by vendor, and only where no card number is printed
- **Choice:** Publish saves a `card_key` field correction for the vendor. The chain applies it only when the receipt's hint yields no `_card_keys`, so a printed number, known or unknown, always wins.
- **Rationale:** The brief named "one fix card action per row" as the build, and "Item 88 is shipped, so a remembered fix is now possible". The 2026-08-22 ruling bars learning a tender word, and nothing here keys on one. Item 88's ruling already accepts a one-off becoming a rule until Forget.

### The remembered card rides on the receipt, not the view
- **Choice:** `ExpenseMemory.apply` fills `Receipt.card_key` at ingest; the view never reads the learning store.
- **Rationale:** Reading memory at view time would silently move Criss's current months the moment another month was published. Ingest-time memory matches how every other learned field reaches a month.

### No provenance note for a remembered card
- **Choice:** `card_key` is skipped in the "Auto-filled from a prior correction" note.
- **Rationale:** The fill is only a candidate; when a printed number wins, the note would lie. `card_source: learned` is the honest signal.

### Item 82 handed off, not started
- **Choice:** Checkpoint and a continuation prompt instead of starting the simulation.
- **Rationale:** About 205 tool calls by count after item 87, against the brief's ~250 cap. Item 82 needs a Fly volume copy, a replay, a build and a deploy.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/cards.py` | Edit | exact alias beats shared word aliases; masked BIN learns as string |
| `.../src/expense_recon/web/service.py` | Edit | `card_key` header field, chain override/learned, `card_source`, `prepare_row_card_fix` |
| `.../src/expense_recon/web/app.py` | Edit | route validation off the event loop |
| `.../src/expense_recon/matching/types.py`, `web/serialize.py` | Edit | `Receipt.card_key` + snapshot round-trip |
| `.../src/expense_recon/learning/capture.py`, `consult.py` | Edit | learn and apply `card_key` per vendor |
| `.../tests/test_card_fix_per_row.py` | Create | 8 route-level and unit tests |
| `.../tests/test_view_contract.py`, `docs/api-contract.md` | Edit | pin `card_source` |
| `.../docs/lovable-card-fix-prompt.md`, `lovable-matched-with-statement-prompt.md` | Create | SPA halves of 87 and 89 |
| `.../docs/PROMPT-STATUS.md` | Edit | four rows Applied; two Not applied |
| `workspace/clients/brisken/status/p1-improvement-backlog.md`, `p1-expense-reconciliation.md` | Edit | items 85/86 applied, 87 shipped, 89 new, Shipped row 55 |

---

## Current Status
Backend v143. No stored card fix exists on July or August, and memory holds 0 field corrections, so nothing moves until Criss picks a card and publishes. brisken ops status: platform unknown (no infrastructure assessment); comms-log none.

---

## Next Steps
1. Item 82: run the simulation described under Working Notes, and report July/August bucket changes against labels before any build.
2. After the owner's paste: bundle audit on `card_source`, `expx.cardFix.pick`, `expx.cardFix.source.learned`, `expx.cardFix.boxHint`, `months.state.matchedStatement`, `months.state.matchedStatement.tip`. Then drive cold: open one card select and Escape it, never pick on Criss's month.
3. Structural fix for this session's worst friction: gate `PARALLEL-ROUND-PROTOCOL.md` section 10 cleanup on `gh pr view --json state` == MERGED.

---

## Context for Next Session

### Files to Read First
- `docs/2026-09-17 - Expense-Recon Item 87/Mini-Checkpoint-1.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 82, 87, 89)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)

### Open Questions
- PT wording for the item-89 badge, and whether the Matching card's PT "Conciliadas" should change too (Criss).

### Working Notes
- **`seen_undefined` reads statement charges, never receipt hints.** It is empty whenever every statement card is defined, so "Define card" can never reach a receipt-only card.
- **Offline learnability replay.** The scratch script was `learn_replay.py`: fold `learnable_hint_tokens` into the live `/api/cards` registry, then `resolve_hinted_card_ex(hint, cards, None)`. It is a cheap check for any future strip change.
- **Tender and junk aliases.** Still learnable as aliases, not changed: "Link" (a wallet), "PAYE" (French "paid"), "Pay $15.00 with a bank transfer". A future `is_generic_tender` extension could refuse them.
- **`hint_digit_run` in the card strip.** It still groups "42463153XXXXXX38" under "Cards by number", although it now learns as a string. Cosmetic.
- **Item 82 simulation path.** `tools/recon-match-attribution.py --live recon-web.sqlite --run-id 50622baec444 --run-id 074a7b8905d7 --learning learning.sqlite --labels ...`. It needs an sftp copy of the Fly volume (memory `project_brisken_expense_recon_testing_loop`). Settings rate today: EUR:USD 1.162275.
- **agent-browser.** The first `open` in a new session hangs ~2 min, and the page loads anyway; `get url` confirms it.
- **Hover tooltips.** Radix tooltips open on a dispatched `pointermove` on the trigger span; `hover "text=..."` misses StaticText.

### Reference Materials
- PRs #943, #947, #949; Fly release v143
- ECB Data API series `EXR/M.USD.EUR.SP00.A`, `EXR/M.BRL.EUR.SP00.A`

---

## How to Continue
Paste the item-82 continuation prompt from the session's final reply (it is also summarized in Next Steps 1). Work in a fresh worktree off origin/main; no live writes on Criss's months.

---

## Strategic Feedback

### What Worked Well This Session
- **Predicting the live diff before deploying**, "July 19 hint / 33 none, August 18 / 13, nothing else changes", turned the post-deploy read into a pass/fail test instead of a look.
- **Reading item 87 before building it** found the two silent non-learning bugs. A copy-only fix would have shipped past them.

### Suggestions
- **Gate the round protocol's cleanup block on the PR state.** A merge conflict on a docs PR is routine with parallel sessions, and the chained cleanup turned a conflict into a recovery.

### System Health
- **Shell-trap and pressure-meter frictions recurred** on the same day they were first logged (both rows unresolved). Recall is not holding, and both are structural candidates.
- **Autonomy:** 1 human intervention (a new request mid-session, not a correction).
