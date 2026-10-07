# Checkpoint: Recon Save Memory Ticks

**Date:** 2026-10-07
**Status:** Backend LIVE (Fly v280, `68beb63a`); SPA prompt written, not pasted

---

## Summary
Answered "how much matching uses the Memory tab" (none: the matcher reads only vendor aliases and FX means, both empty live), then shipped backlog item 246: "Save corrections to memory" saves only the ticked lessons, and a save overwrites the rule memory holds for that case, including rules under other spellings of the same merchant.

---

## What Was Done This Session

### Analysis (read-only, live API)
1. Memory tab = `GET /api/memory`, 111 rows: 108 category rules (102 Zoho-seeded, 0 validated), 1 merchant entity, 2 field corrections, **0 vendor aliases, 0 FX means**. The matcher (`MatchMemory`) reads only those two empty tables, through the same store the tab shows: 0% of matching. Even filled they are tie-break only, and the learned FX mean loses to the polled daily rate.
2. Category share: across 8 months, memory (`LEARNED`) decided 1 of 888 receipt lines and 1 of 288 posting accounts; the merchant list (`REGISTRY`) decided 450 lines / 136 accounts. One memory save ever (September, button), undone.

### Item 246 (PR #1580, then #1582 records it live)
1. `POST /commit-memory` takes Publish's `keep` / `skip` lesson ids via one shared parser `_lesson_lists`; no body = defaults (stale SPA safe).
2. Lessons carry `effect` (new / replaces / same / adds), `replaces[]` and `already_saved`; sentences end "Replaces <old>." / "Already saved from this month." A lesson this month already saved (still held as saved) starts unticked and is skipped; a button click with nothing left answers `nothing_to_save`, journals nothing.
3. `learning.one_rule_per_merchant`: a category write deletes the same (company, merchant identity) rules under other spellings, journaled (undo restores), carrying over the half the save did not name (person over seeded); left alone when those rules disagree on that half.
4. 11 route-level tests (`tests/test_save_memory_ticks_item_246.py`), regress-checked at 4 wiring points; full module suite 4181 passed / 2 skipped.
5. Lovable prompt `docs/lovable-save-memory-ticks-prompt.md` + PROMPT-STATUS row; backlog item 246; p1 status line.

---

## Key Decisions Made

### "Overwrite the existing rule" = one rule per merchant per company
- **Choice:** a save replaces rules recall folds into the same identity, not only the exact key.
- **Rationale:** the store was already latest-wins per key; the real gap was recall's fold refusing disagreeing spellings, so an older spelling kept answering after a save and stayed on the Memory page.

### Already-saved = this month's kept id AND value unchanged
- **Choice:** skip only when this month's un-undone save wrote the lesson and memory still holds it as written.
- **Rationale:** an id-only skip would block exactly the overwrite the owner asked for (a changed correction keeps its id); a value-only skip would stop other months' confirmations from counting.

### Owner rulings left intact
- Decided accounts (item 219) move only via their drift lesson; OpenAI / Anthropic / Lovable merchant-list writes stay held; FX samples accumulate.

---

## What Did NOT Work (and why)
- **`pytest -n auto` in the expense-recon env:** pytest-xdist is not installed, usage error before any test ran (the warn fired on that call).
- **Playwright MCP for the consumer drive:** it attaches over CDP to :9222 and no browser was listening (ECONNREFUSED); a standalone Python Playwright headless Chrome worked.
- **`regress_check.py --file <repo-relative> --cwd <module>`:** `--file` resolves against `--cwd`; pass the module-relative path.
- **Predicting the deploy's plan effect from the morning's `memory-plan` read:** May had been edited since, so the prediction said 0 deletes where the live plan shows 2; the before/after diff caught it.
- **`gh pr merge` chained after `cd`:** blocked by `block-merge-chained-after-any-command`; run the merge as its own call.
- **First SPA drive click:** the fresh-session "Leave feedback anywhere" hint dialog (`fb-hint-title`) intercepts clicks; Escape it first.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/learning/commits.py` | edit | delete op, `one_rule_per_merchant` |
| `.../expense-reconciliation/src/expense_recon/learning/__init__.py` | edit | export |
| `.../expense-reconciliation/src/expense_recon/web/memory_lessons.py` | edit | effect / replaces / already_saved, expand at apply |
| `.../expense-reconciliation/src/expense_recon/web/service.py` | edit | stored rows in plan, skip already-saved, `rules_replaced`, delete view |
| `.../expense-reconciliation/src/expense_recon/web/app.py` | edit | `_lesson_lists`, button takes ticks |
| `.../expense-reconciliation/tests/test_save_memory_ticks_item_246.py` | new | 11 route tests |
| `.../expense-reconciliation/docs/lovable-save-memory-ticks-prompt.md` | new | SPA half |
| `.../expense-reconciliation/docs/PROMPT-STATUS.md` | edit | not-applied row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 246 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | status line |

---

## Current Status
Backend live on Fly v280 and verified with 0 writes: plan before/after diff, route probe (malformed `keep` 400 vs control 404), consumer drive of May's published Save dialog rendering "Replaces the rule saved as railway corporation" (every non-GET aborted, none attempted). SPA prompt not pasted. Platform: brisken ops status unknown in `infrastructure.yaml` (no assessed plan). Stale status files flagged by `pre`: `p1-recon-loop-prompt.md`, `p2-lead-gen-general.md`, `p2-lovable-rebuild.md`, `p2-rome.md` (not this session's workstreams).

---

## Next Steps
1. Owner pastes `docs/lovable-save-memory-ticks-prompt.md`; then audit the published bundle for its keys and drive April's dialog cold to Cancel (checkbox count = `lessons.length`).
2. May's next save will replace two other-spelling rules (Lovable Labs Incorporated, Railway Corporation; same category, account carried): read the Memory tab after it to confirm.
3. Consider promoting `warn-stop-merge-left-pending` and `warn-pytest-xdist-not-installed` to blocks (both fired this session and were not heeded the first time).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 246)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-save-memory-ticks-prompt.md`

### Open Questions
- None blocking.

### Working Notes
- Instrument for any memory change: `GET /api/runs/{id}/memory-plan` per month (0.1-0.6 s, writes nothing), read before and after a deploy, diff writes modulo `op` and lesson ids.
- A non-writing proof the new route serves: POST `commit-memory` with `{"keep": "x"}` on a fake run id answers 400; old code answered 404.

### Reference Materials
- PR #1580, PR #1582; Fly `brisken-expense-recon` v280

---

## How to Continue
`/resume brisken`; if the owner says the prompt is published, run the bundle audit and the cold April drive (read-only, Cancel).

---

## Strategic Feedback

### What Worked Well This Session
- Reading the store's upsert SQL and recall's fold before building turned "make it overwrite" into the one real gap (fold refusal across spellings) instead of re-implementing latest-wins that already existed.

### Suggestions
- Promote `warn-stop-merge-left-pending` to a Stop-time block: it caught two turns ending with the ship chain pending, both only on the next prompt.

### System Health
- Pattern rules carried the session's discipline (heredoc size, merge isolation, pending chain, prompt naming); the warns that fire after the fact are where recurrences still land. Autonomy: 0 corrective human interventions (fully autonomous on the owner's 4 directive prompts).
