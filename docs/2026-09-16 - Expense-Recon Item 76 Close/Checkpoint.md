# Checkpoint: Expense-Recon Item 76 Close

**Date:** 2026-09-16
**Status:** Item 76 shipped, applied and published; items 83+75, 84, 85+86, 88, 87, 82 open with a continuation prompt handed to the owner

---

## Summary
The session opened the wave named in the owner's brief: it verified the five published prompts (items 73/74/77/80/81), took three owner rulings, and shipped item 76 end to end (backend, deploy, live application, SPA prompt, owner publish, cold drive). It closed on a new standing rule: no live writes on Criss's months.

---

## What Was Done This Session

### Verification and rulings
1. `/feedback.jsonl`: 51 notes, none after #51 (16:16 UTC).
2. Bundle audit for items 73/74/77/80/81 (48 chunks, controls hit, 19/20 names; the absent `n_duplicate_groups_open` is never read by the render rule) plus a cold drive of July and August in EN, and August in PT. Every check with a live case passed, 0 writes. PR #924.
3. One AskUserQuestion round: item 76 vendor floor 75; item 84 MISSING ENTITY + NEEDS PERSON merge; item 88 corrections saved at month sign-off with the Memory page as undo. Recorded on the items in PR #924.

### Item 76
1. Backend, PR #925 (merge `a299174f`), Fly v139: `rows[].turn`, `decided_by` / `decided_rule`, `summary.n_self_confirmed`; `apply_self_confirmations` after every `rematch_month` commit; `RunStore.set_tool_decision` conditional upsert; `decisions.decided_by` / `decided_rule` migrated in place. Suite 1907 -> 1929 passed / 2 skipped; three regress proofs bite.
2. Owner-approved refresh-master-data on July and August: exactly the five predicted pairs confirmed (July ELEVENLABS 5.00, ANTHROPIC 50.54; August LOVABLE 15.00 / 25.00, ANTHROPIC 51.38), nothing else moved, 0 master-data changes, 0 model calls.
3. `docs/lovable-turn-prompt.md` handed over; owner published; bundle 5/5; cold drive of every view on both months, EN + PT, 0 writes. Recorded in PR #927.
4. Mini-checkpoint PR #926; continuation prompt for items 83+75, 84, 85+86, 88, 87, 82 handed in chat.

---

## Key Decisions Made

### The self-confirmation is a stored decision, not a view-time derivation
- **Choice:** the tool writes an ordinary `confirmed` decision marked `decided_by: tool`, re-judged at each re-match, never over a person's verdict (enforced in the upsert's WHERE).
- **Rationale:** exports, reports, `ready_to_post` and the cross-batch claims registry all read stored decisions; a derived confirm would be invisible to them. The conditional write closes the race with a reviewer's click.

### Two deny-by-default narrowings of the ruling
- **Choice:** a candidate borrowed from another batch (`from_batch`) or held by another charge (`held_by`) never self-confirms.
- **Rationale:** the ruling was made on same-batch exact pairs; neither case has a live instance.

### No live writes on Criss's months (owner, end of session)
- **Choice:** ship, read the live API, drive read-only, stop. Never offer a refresh, reset or re-match; report which rows will change at the next natural re-match instead.
- **Rationale:** her month is her working data and her clicks are hers. The two July duplicate rulings (Hostinger 0000/0002, Redis 0004/0070) stay as she left them.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | Modified | turn, decided_by, self-confirm pass, wiring into `rematch_month` + `build_view` (#925) |
| `automations/expense-reconciliation/src/expense_recon/web/store.py` | Modified | decisions columns + migration, `set_tool_decision` (#925) |
| `automations/expense-reconciliation/tests/test_self_confirm.py` | Created | 21 route-level + store + rule-edge tests (#925) |
| `automations/expense-reconciliation/tests/test_view_contract.py` | Modified | turn / decided_by contract pin (#925) |
| `automations/expense-reconciliation/docs/api-contract.md` | Modified | item 76 section + counts row (#925) |
| `automations/expense-reconciliation/docs/lovable-turn-prompt.md` | Created | SPA half (#925) |
| `automations/expense-reconciliation/docs/PROMPT-STATUS.md` | Modified | five prompts Applied (#924); turn prompt Pending then Applied (#925, #927) |
| `status/p1-improvement-backlog.md` | Modified | rulings 76/84/88 (#924); item 76 Shipped + row 51 (#925) |
| `status/p1-expense-reconciliation.md` | Modified | item 76 row (#925, #927) |
| memory `feedback_recon_no_live_writes_criss_acts.md` | Created | the no-live-writes rule |
| memory `project_brisken_expense_recon_usability_loop.md` + `MEMORY.md` | Modified | item 76 facts, index lines |

(Module paths are under `workspace/clients/brisken/`.)

---

## Current Status
Live on Fly v139 with the turn prompt published. July: 1 row to decide, 2 self-confirmed, 84 booked rows read "Already booked". August: 7 to decide, 3 self-confirmed. Clean non-exact pairs still asking by ruling: 2 (August `fx_reference` CLAUDE SUB 247.32, PETIT TRAIN 37.48). brisken ops status: platform unknown (no plan/ops assessment in `infrastructure.yaml`); comms-log 8 days stale.

---

## Next Steps
1. Items 83 + 75: set-aside copies out of `unmatched_receipts` / `assignable_receipts` and the counts, into a parallel list; `reason_code` on every unmatched receipt and charge; invariant and by-index pairing intact.
2. Item 84: per-row box membership from the summary code; resolve Categorized 49 vs 51 and `has_receipt_image` vs `receipt_image_available` first; ENTITY + PERSON become one box.
3. Items 85 + 86: one SPA prompt (control inventory in the continuation prompt; re-fetch line numbers).
4. Item 88 (find "month sign-off" in code first), item 87 (read July's card strip first), item 82 (simulate with the S1 scorer first).
5. Add the no-live-writes rule to `PARALLEL-ROUND-PROTOCOL.md` §3 on the next client branch so it stops depending on memory.

---

## Context for Next Session

### Files to Read First
- The continuation prompt handed in chat (self-contained)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` items 75, 83, 84, 85-88, 82
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)

### Open Questions
- What code event is "month sign-off" for item 88: Publish, `ready_to_post` turning true, or confirm-all?

### Working Notes
- Every July/August re-match trigger is a live write (no pure re-match route), and live writes are now off the table. A shipped rule reaches a month only when Criss or mail causes a re-match.
- `candidates[]` lists only the pairs the matcher ASSIGNED, so a same-amount rival with lower vendor never shows as a second candidate; a rival test needs an edit that drops vendor agreement, not a second receipt.
- Identical uploaded bytes are deduped as a re-upload; test fixtures need distinct bytes per file.
- The SPA source is readable via `gh api repos/011matthias/brisken-expense-review/contents/src/...`; the Lovable repo main tracks what the owner edits, so re-read before anchoring a prompt.
- Decided and booked rows render inside collapsed folds; click "Show" before asserting. The deploy-consumer Stop hook only counts literal `agent-browser ... eval|snapshot` commands in the foreground.
- `checkpoint_scaffold.py`: `pre` has no `--root` (it prints a primary-clone target), `--root` goes BEFORE `finalize`, and a mini re-run numbered Mini-Checkpoint-2 against the file already written (INDEX link hand-repaired to -1).

### Reference Materials
- PRs #924, #925, #926, #927; Fly release v139
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops1\workspace\clients\brisken\context\expense-reconciliation\expense-reports\csv\by-month\` (labels, gitignored)

---

## How to Continue
Paste the continuation prompt into a new chat. It opens with the feedback read and a payload re-read, then works items 83+75, 84, 85+86, 88, 87, 82 in order, one branch/PR/deploy each, under the no-live-writes rule.

---

## Strategic Feedback

### What Worked Well This Session
- Predicting the live effect from the payload before building (`predict76.py` over the saved run JSON) turned the owner-approved refresh into a checkable claim: five named rows, nothing else, and the diff confirmed it exactly.
- Reading the SPA's real component source through `gh api` let the Lovable prompt name `RowStatusBadge`, the action cell and `bulkTargets` precisely, and the first publish rendered every check.

### Suggestions
- Move the no-live-writes rule from memory into `PARALLEL-ROUND-PROTOCOL.md` §3, which every recon session is told to read; today the brief itself still instructs asking for per-action live writes, which is what produced the correction.

### System Health
- Documented environment traps still cost roughly ten calls this session (cd-guard, `MSYS_NO_PATHCONV` with a `/c/` path, heredoc triple-quote and size caps, chained `sleep`): every hook caught its case, but recall did not prevent the attempt. Autonomy: 4 human interventions (elevated; three were decisions the brief required, one was the no-live-writes correction).
