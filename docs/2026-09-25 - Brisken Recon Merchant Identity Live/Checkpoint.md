# Checkpoint: Brisken Recon Merchant Identity Live

**Date:** 2026-09-25
**Status:** Item 216 cause 3 LIVE (PR #1441 merge `8102be21`, Fly `8102be21`); record PR #1442 merged; nothing written on Criss's months

---

## Summary

The alias learner is wired into the memory save and every memory lesson is keyed on the registry-aware merchant identity; merged on green CI, deployed through `deploy.py`, and the memory-save preview was driven cold on August with every write aborted. Live plans are unchanged today, as predicted, because no live correction or person-confirmed pairing touches a registry merchant yet.

---

## What Was Done This Session

### Gate and merge
1. Build 1 (PR #1437, correction path) was on main; merged `origin/main` into the identity branch (one status-row conflict, both sides kept). Merged tree: 36 identity tests green, full module suite 3784 passed / 2 skipped.

### Wiring (`web/service.py`, `web/memory_lessons.py`)
2. `registry_upserts_from_expense_run(..., alias_candidates=())`: step 1b appends each person-proven spelling to a merchant the registry ALREADY holds (a new merchant stays a person's call).
3. `memory_identity(settings)` = `MerchantIdentityResolver(MerchantRegistry.from_settings(settings))`, the same construction recall uses at ingest.
4. `commit_to_memory`: identity into `learn_from_expense_run` and `learn_from_run`; on a statement month `identity_alias_candidates` over `reviewer_confirmed_tx_ids(decisions)` and the decision-applied outcome, passed to the registry upsert; the dry run returns the candidates, which `_memory_plan` pops (never served, never journaled) into `LessonContext.alias_pairs`.
5. `memory_lessons`: `LessonContext.identity` + `alias_pairs`; `category_groups` and both `learn_category_candidate` calls take the identity; a merchant's registry lesson lists the pairing's charge and receipt as sources.

### Verification
6. Five route tests through `GET /api/runs/{id}/memory-plan` and Publish (41 in `test_merchant_identity_216.py`): person-confirmed pairing offers "new spelling" and Publish saves the alias; tool-confirmed offers none; Anthropic shown, `owner_gated`, refused; a correction on `CONTOSO` is planned under `contoso cloud` with its row; a kept conflict candidate is saved under `contoso cloud`.
7. `regress_check`: seven wiring points red under mutation, green restored. Full suite on the wired code 3789 passed / 2 skipped; CI all eight checks green.

### Measure, ship, drive
8. Fresh read-only prefetch (12 GETs, 15 s apart, all < 1.3 s) incl. each month's memory-plan. Charge A/B, base = main `e2516eb6` vs build: 7 -> 24 of 191 answered by a rule, same 17 changed, Zoho join 11 right / 0 wrong / 6 not booked. Live person-confirmed pairs: 3 (Amazon.de, Network Solutions, Obsidian), none with a registry side.
9. Deployed from the detached base tree (`deploy.py`: tree == origin/main, size OK, `/healthz` on `8102be21`). Post-deploy plans byte-identical to pre-deploy on all three months (prediction held). Cold Playwright drive (`channel="chrome"`, replayed payloads, non-GET aborted): gate rendered with no session; August's "Save this month's corrections" preview named all 11 vendors of the plan's 20 keys, no `undefined`/`NaN`/`[object Object]`; 7 replayed, 0 aborted, live only `/api/cards`, `/api/cards/status`, `/api/inbound/log`, login.
10. Backlog item 216 "Cause 3" build note (numbers, merge-list check, fuzzy-tier limit, what only a person can add) + status row LIVE (PR #1442).

---

## Key Decisions Made

### The conflict re-run takes no alias candidates
- **Choice:** `_registry_candidate` (memory_lessons ~249, named in the brief as a candidate site) stays alias-free; the plan gets aliases only through `commit_to_memory`'s dry run.
- **Rationale:** `apply_selection` re-runs `_registry_candidate` on the working merchant map for each kept conflict group; passing aliases there would re-add a spelling the reviewer unticked.

### No new keys on `learned` / the registry summary
- **Choice:** alias counts fold into the existing `aliases_added`; the candidate list is popped before serving.
- **Rationale:** the published SPA renders `learned` generically (a refusal once printed as something taught); a new key risks a wrong line on Criss's screen.

---

## What Did NOT Work (and why)

- **First pre-read jobs check:** `flyctl logs ... | grep -E "/jobs/|POST|healthz"` without `MSYS_NO_PATHCONV=1`; Git Bash rewrote the leading-slash pattern to a Windows path, so `/jobs/` lines could never match (the MSYS-MANGLE advisory fired and was passed). The deploy-time check used `MSYS_NO_PATHCONV=1`.
- **`truth17.py` on the first run:** reads `SP/payloads/`, not the `PAYLOADS` env var; FileNotFoundError until the payloads were copied there.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/service.py` | Edited | `memory_identity`, alias step in the registry upsert, identity + candidates in `commit_to_memory`, `_memory_plan` context |
| `.../src/expense_recon/web/memory_lessons.py` | Edited | `LessonContext.identity` / `alias_pairs`, identity on grouping and conflict re-learns, pair sources |
| `.../tests/test_merchant_identity_216.py` | Edited | 5 route tests (41 total) |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | Edited | Item 216 "Cause 3" note |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Edited | Item 216 row: D LIVE |

---

## Current Status

Live on Fly `8102be21`. Criss's months: nothing written, nothing re-matched. The 17 charges change at each month's own next re-match. brisken ops status line from `pre`: platform unknown plan, comms-log none (no comms in scope).

---

## Next Steps

1. At the next natural re-match of July / August / September, confirm the 17 charges read a rule answer (list in `truth17.py` output: BASE44 x4, Wix x2, PRESSMASTER, SERVERPILOT x3, DIGITALOCEAN x3, ANTHROPIC x2 Cloud, GITHUB x2).
2. Item 216 remaining causes (the five-build split in the 2026-09-25 prompts): Build 2 (code half, fresh session), B account map + Dirk's draft, C invoices out of the card queue.
3. SPA: `lovable-publish-checklist-prompt.md` (183a) still not pasted; once it is, the "new spelling" lesson renders as a tickable row (today it reaches the screen only through item 163's preview and the registry diff).

---

## Context for Next Session

### Files to Read First
- Backlog item 216, "Cause 3" paragraph (`workspace/clients/brisken/status/p1-improvement-backlog.md`)
- `web/service.py` `commit_to_memory` / `_memory_plan`; `web/memory_lessons.py` `LessonContext`

### Open Questions
- Dirk (gated, counted not proposed): alias `ANTHROPIC* CLAUDE SUB`, an OpenAI entry, the Lovable merchant held twice.

### Working Notes
- `GET /api/runs/{id}/memory-plan` is a safe live read (RecordingStore, `persist=False`) and costs ~0.2 s: it is the instrument for any memory-learner change.
- Live decision provenance today: July 2 reviewer / 2 tool confirmed of 120 rows, August 1 / 3 of 143, September 0 / 1 of 51; everything else pending.
- The drive script `drive_plan.py` (scratchpad `dac88eb5`) replays by path on either host and aborts every non-GET except `/api/login`; "Save corrections to memory" opens item 163's preview, clicked via `el.click()` after removing the feedback hint.

### Reference Materials
- PR #1441 (code), PR #1442 (record); first-half checkpoint `docs/2026-09-25 - Brisken Recon Merchant Identity/` (scripts)

---

## How to Continue

Nothing of Build 3 is open. Resume on item 216's next cause from the parallel-session prompts; re-measure with `tools/recon-categorization-score.py` after any re-match.

---

## Strategic Feedback

### What Worked Well This Session
- The pre/post memory-plan pair (one GET each side of the deploy) turned "the change is invisible live" into a checked prediction, and the three person-confirmed pairs explained why before the deploy happened.

### Suggestions
- `warn-stop-merge-left-pending` has now recurred four times on 2026-09-24/25 as a next-prompt warning; make it a Stop-event block (or an ask) when the closing text names a pending PR, so the turn cannot end there.

### System Health
- Autonomy: 0 human interventions (fully autonomous session). Gates B1:0 B2:5 B3:0 skipped:1 (B6 closing, hook-caught).
