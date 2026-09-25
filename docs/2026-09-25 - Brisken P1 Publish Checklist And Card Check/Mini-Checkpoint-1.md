# Mini-Checkpoint: Brisken P1 Publish Checklist And Card Check

**Date:** 2026-09-25
**Status:** Items 183 half A and 172 live on Fly `904b3f34`; both SPA prompts written, not pasted
**Type:** mini

---

## Summary
Publish now saves only the lessons a reviewer keeps, from the plan's own recorded writes (item 183 half A, PR #1396, Fly `b360333c`). Settings checks each card's paid-through account against its company's chart (item 172, PR #1401, Fly `904b3f34`). Both were read on the live API and driven cold in the SPA, read-only.

## What Was Done
- **Item 183 half A.**
  - `memory-plan` `lessons[]`: stable id, plain description, source rows, `default_keep`, `owner_gated`, `conflict_group`. New module `web/memory_lessons.py`.
  - Conflicts are offered unticked, one per candidate; a kept candidate is re-learned by the real learner (`learning.learn_category_candidate`, the registry learner over the subset).
  - `POST /publish` takes `keep` / `skip`; the save applies the plan's recorded writes filtered (`apply_plan`); the journal and `learned` counts reflect what was written.
  - GL month: a kept account correction fills `merchants[].accounts[<company label>]`.
  - Leak closed: the registry learner taught the model's category after a Confirm or an account-only fix (`learning.taught_value` now shared).
  - 10 route-level tests, six wires RED. Suite 3622 passed / 2 skipped + 2 item-171 fixture failures from the owner gate, fixed by renaming the fixture's vendors.
- **Item 172.** `cards_effective[].account_check` via `category_vocabulary.card_account_check`, held to item 184's `resolve_paid_through`; `closest` prefers the card's four-digit groups; stale-chart sentence when `chart_coverage` is not ok. 7 tests, four wires RED.
- **Live reads.**
  - Lessons on July (12), August (23) and September (3); `registry:Anthropic` and `registry:Lovable Labs` gated on July and August.
  - Cards: 8 of 9 `ok`, `3645` `not_in_chart`, closest `CHASE VISA - 2838 - TRAVEL`, chart verified.
  - Cold drives: September's memory preview dialog and Settings > Cards rendered the new payloads with 0 non-GET requests.
- **Prompts:** `docs/lovable-publish-checklist-prompt.md`, `docs/lovable-card-account-check-prompt.md`, PROMPT-STATUS rows.

## What Did NOT Work (and why)
- **The digit-hint regress check on item 172:** it did not bite at first. Fuzzy matching alone picked `CHASE VISA - 2838 - TRAVEL` for "Credit Card - 2838" because `2838` is a shared token. A case where only the card's digits point right ("Master Card" with digits 2838) made it bite.
- **Merging main into the 172 branch while its suite ran:** `memory_lessons.py` arrived after the old `learning` package was imported, so one test failed with an ImportError. The failure came from the race, not the code. Merge before the suite starts, or after it ends.
- **A 26-line heredoc with a Python triple-quoted block** to edit `learning/__init__.py`: the heredoc gate refused it. Use Edit.
- **An Edit on a scratch file never Read:** it was refused, and the drive that followed asserted nothing while the consumer gate still reported "driven". Re-read and re-ran with assertions.

## Current Status
Fly `904b3f34` serves both items. Live Publish sends no `keep` until the checklist prompt is pasted, so it applies the defaults: corrections kept, conflicts skipped, and the merchant list never written for OpenAI, Anthropic and Lovable. **Behaviour change to put to the owner:** the live registry holds `Anthropic` and `Lovable Labs`. Because the gate refuses every merchant-list write for them, publishing July or August no longer records their `cards_seen` (one learned card key among them). Narrowing the gate to category and account fields is a small change if he wants the card observations back. Ops status: platform unknown plan (no `platform` section for this FastAPI client).

## Next Steps
1. Owner: paste `lovable-publish-checklist-prompt.md` and `lovable-card-account-check-prompt.md`; then bundle-check and drive each read-only (never Publish a live month; never Save a card).
2. Owner ruling: keep the gate on card observations for Anthropic and Lovable Labs, or narrow it to category and account.
3. The "Anthropic, PBC" lead: `pbc` in `vendor_names._LEGAL_SUFFIXES`, with the matcher impact measured, or Dirk aliases the merchant.
4. Dirk: card 3645's account (`CHASE VISA - 2838 - TRAVEL`, per the check) and the per-company merchant accounts; each live write needs an owner order.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 183, 172)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/memory_lessons.py
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/category_vocabulary.py (`card_account_check`)

## Continuation prompt

````
resume brisken

Continue Brisken p1 expense-recon: the "Anthropic, PBC" lead (a per-company Anthropic account reaches only rows spelled plainly), then verify the two new SPA prompts if the owner has pasted them. Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)
Last checkpoint: `docs/2026-09-25 - Brisken P1 Publish Checklist And Card Check/Mini-Checkpoint-1.md`

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first. The clone is shared with live sibling sessions: work in a worktree off origin/main, one branch per item. Merge main BEFORE starting a suite, never during one.
- Read `/healthz` on brisken-expense-recon.fly.dev (it was `904b3f34`).
- Module suite about 3640 tests, run serially (xdist is not installed; about 10 min).
- Claim backlog numbers only after grepping `^### ` on origin/main AND the open PR diffs.
- Live API reads: `POST /api/login {"code"}` (vault "Expense Recon App", `operator_code`) returns a `token`; send `Authorization: Bearer`. GET only.

## 1. ESTABLISHED. Do not re-derive.
- **Item 183 half A is live** (#1396, Fly `b360333c`): `GET /api/runs/{id}/memory-plan` `lessons[]` (`id`, `kind`, `table`, `key`, `description`, `sources`, `default_keep`, `owner_gated`, `conflict_group`); `POST /publish` takes `keep` / `skip`; the save applies the plan's recorded writes filtered; OpenAI / Anthropic / Lovable merchant-list writes are refused (card observations included); a GL month's kept account correction fills `merchants[].accounts[<account_companies label>]`. Logic in `web/memory_lessons.py`; shared learner helpers in `learning/capture.py` (`taught_value`, `category_groups`, `merge_taught`, `learn_category_candidate`).
- **Item 172 is live** (#1401, Fly `904b3f34`): `GET /api/settings` `cards_effective[].account_check`. Live: 8 of 9 cards `ok`, `3645` `not_in_chart`, closest `CHASE VISA - 2838 - TRAVEL`, chart verified. No card was edited; the value is Dirk's.
- **The live registry holds `Anthropic` and `Lovable Labs`** (the 2026-09-18 note saying it did not is stale). Whether the gate should also stop their card observations is an open owner question; do not change it unasked.
- **Prompts not pasted:** `docs/lovable-publish-checklist-prompt.md`, `docs/lovable-card-account-check-prompt.md` (PROMPT-STATUS Not applied). Verify by bundle + read-only drive: never Publish a live month, never Save a card.
- **Open lead:** "Anthropic, PBC" (29 of 34 live Anthropic rows) does not resolve to registry "Anthropic" because `pbc` is not in `vendor_names._LEGAL_SUFFIXES` (fuzzy 75 of 88 needed). Measure the matcher impact of adding it over every live vendor string before changing it.
- `web/` must not import `..zoho`; chart reads go in `category_vocabulary.py`.

## 2. Hazards
- **B6 chain.** Commit, push and PR are autonomous after real verification. Read `mergeable_state` before polling checks. Merge on green in a separate call; never end a turn with a PR waiting.
- **Deploys** (pre-authorized): from a clean detached origin/main worktree, `M` a `C:/` path, `FLY_API_TOKEN` read from `~/.fly/config.yml`, `--build-arg GIT_COMMIT`. Check the live commit is an ancestor of main first. Verify `/healthz`, then read the changed fields. Drive the SPA cold with `uv run --with playwright` (headless `channel="chrome"`), wait about 3 s after login, remove the first-visit feedback hint, and read input VALUES.
- **Criss's months and live settings:** no writes without an owner order. Never inject July. No writes to production Zoho orgs.
- **Heredocs:** no Python triple-quoted blocks, nothing over 80 lines. Bash mangles leading-slash args: prefix `MSYS_NO_PATHCONV=1`.
- **Records:** each item goes in `status/p1-improvement-backlog.md` and rolls up in `p1-expense-reconciliation.md`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````
