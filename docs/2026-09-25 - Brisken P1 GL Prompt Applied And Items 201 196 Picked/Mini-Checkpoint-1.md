# Mini-Checkpoint: Brisken P1 GL Prompt Applied And Items 201 196 Picked

**Date:** 2026-09-25
**Status:** GL prompt applied and driven; owner picked item 201 (fix now) and item 196 (land the sure rows); no code started, stopped at the 500k band
**Type:** mini

---

## Summary
The owner published the GL accounts prompt. It was bundle-verified and driven
cold in EN and PT on July and on a purged `TEST - GL drive` batch (PR #1339).
The drive found items 201 and 202; the owner then picked both code items, but
context crossed 500k before any code was written.

## What Was Done
- Gate B open. Every runtime marker is in the live bundle, and the five controls were found. `accountsFor` is an exported helper the build renames and `gl_revision` is a type-only field the build strips, so neither can be a bundle marker; the previous brief listed the first as one.
- July (cold): the picker lists exactly the eight buckets, with no account code and no `gl.` key.
- TEST batch `96a0380ff774` (two synthetic receipts by direct upload, never published) was driven in EN and PT, all passing: company-specific names ("CorpServ | Travel Expense | Food" against "Travel Expense | Food"), 68 / 64 accounts under the company's headings, search by name and code, the no-match line, a disabled "Set the company first" picker, pick + reload persistence (one PUT each, to that batch only), and no Radix Zoho-account Select on GL rows. It was purged afterwards: 404, absent from `/api/expense-batches`, nothing re-pooled.
- Recorded in PR #1339: PROMPT-STATUS moved the prompt to Applied, and backlog items 201 and 202 were added (198-200 were taken by siblings).
- The owner picked (AskUserQuestion): item 201 "Fix it now", item 196 "Land the sure rows".

## What Did NOT Work (and why)
- **Prompt check 3 (review half) and check 4:** they cannot pass. `needs_entity`, and then `needs_person`, outrank every category verdict (`service.py` ~7196), so `gl.refusal.entity_missing` never shows on the Expenses page for a non-private row. No `category_refused` sentence was driven.
- **Backlog numbers 198/199:** taken by siblings (198 on main, 199 in open PR #1335, 200 on main). Grep `^### ` numbers AND the open PR diffs before claiming one.
- **Picker count 64 vs 65 in the PT pass:** the extra item is the prompt's undo entry (`__undo__ Desfazer minha categoria`). Count items whose `data-value` is not `__undo__` / `__clear__`.

## Current Status
Live Fly is still `69de469b` (no deploy this segment). No GL month exists live, so October 2026 will be the first. Item 201 affects every manual pick in it, and no code has been written for 201 or 196. The review xlsx still has its `~$` lock.

## Next Steps
1. Item 201 (owner: fix now), then deploy.
2. Item 196 (owner: land the sure rows), then deploy.
3. Item 202: measure over the stored receipts before choosing a guard.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 196, 201, 202)
- workspace/clients/brisken/automations/expense-reconciliation/docs/PROMPT-STATUS.md (the GL row)

## Continuation prompt

````
resume brisken

Continue Brisken p1 expense-recon. Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first; shared clone with live siblings; work in a worktree off origin/main, one branch per item.
- Live Fly = `69de469b`. Module suite 3312 passed / 2 skipped there (no `-n`).
- Claim backlog numbers only after grepping `^### ` in `status/p1-improvement-backlog.md` on origin/main AND the open PR diffs (siblings took 198-200 last session).

## 1. ESTABLISHED (2026-09-24/25). Do not re-derive.
- The GL accounts prompt is APPLIED and driven (PROMPT-STATUS). No GL month exists live; October 2026 will be the first.
- Owner decisions (AskUserQuestion, 2026-09-25): item 201 = fix now; item 196 = land the sure rows.
- 9693 is loaded in August and September. Item 197 is live. August's two Anthropic rows recover at the next natural re-match; do not trigger one.

## 2. This session, in order
1. **Item 201: a hand-picked account on a GL month exports as "(account unmapped - assign)".** Design (already traced, do not re-derive):
   - Fix at READ time, not save time. `recategorize_after_entity_change` never touches the reviewer's overrides, so a name stored at save time would carry the old company's wording after a company change.
   - Add one helper in `web/service.py`: (month's frozen `gl_entity_orgs`, row company label, code) -> `curated_leaves.binding(code, org_id).name`. Match the label trimmed and case-insensitive; return None when the org is not covered or the code is not bound. Use it as the fallback in `override_base_account(category, base, *, entity=None, entity_orgs=None)` after the existing "same category keeps the base account" rule. An explicit `ov["zoho_account"]` still wins.
   - Thread `entity_orgs=(run.config or {}).get(GL_ENTITY_ORGS_KEY)` through `apply_overrides` (8 callers: `regenerate_report`, `regenerate_zoho`, `regenerate_reconciled`, `regenerate_writeback`, `batch_list_summary`, `build_expense_view`, `_expense_export_inputs`, `rematch_month`; the entity comes from `r.legal_entity_id`), through `_row_posting_category` (3 callers), and through the charge-override builder near `service.py` ~2688 (the entity comes from the charge).
   - The export reads only `cat.zoho_account` (`output/posting_common.py` `_debit_account_and_note`; nothing in `output/` uses `curated_leaves`).
   - Tests: GL-month fixtures exist in `tests/test_gl_engine.py` / `test_categorization_gate.py`. Assert through the category edit route AND the Zoho export (account name present, no placeholder), plus a charge-category case. A bucket month stays byte-identical. Then a regress proof on the wired fallback, and deploy.
2. **Item 196: land the sure rows.** When the model is unavailable (429 `credit_balance_exhausted`), the attach saves the rows the matcher places without the model, and the judgment pairs wait in review. The attach currently fails whole at `judging`. `matching.judgment.judge_fx_match` with `client=None` already returns a `requires_review` stub. Test with a client that raises the 429 and assert through the attach job. Mail intake's `held_body_only` path stays as it is (it is recoverable), but record the key as the cause.
3. Item 202 (US date read day-first): measure first, do not build.

## 3. Hazards
- Never inject July. Do not write to production orgs. No agent writes on Criss's months.
- Deploy with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)` from a clean detached origin/main worktree; verify `/healthz` commit, then drive the consumer.
- SPA drive: headless `channel="chrome"` Python Playwright. On the gate, type the code until Log in enables, then click. The GL picker trigger is `button[role=combobox][aria-haspopup=dialog]`; items are `[cmdk-item]` (data-value = "name code"). Month workbenches collapse card sections and hide reconciled rows.
- Force-push is gated. Heredocs: no Python triple-quoted blocks, nothing >80 lines. Bash mangles leading-slash args: prefix MSYS_NO_PATHCONV=1.
- The review xlsx `CoA BRISKEN - 6 accounts for Dirk to decide 260924.xlsx`: delete only when the `~$` lock is gone AND sha256 is still `eed95ea3785b1bd7caabde8d8151ec1e0efe57ba9d3e16e7832adb3c8b350789`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````
