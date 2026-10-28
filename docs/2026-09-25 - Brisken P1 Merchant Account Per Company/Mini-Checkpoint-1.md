# Mini-Checkpoint: Brisken P1 Merchant Account Per Company

**Date:** 2026-09-25
**Status:** Items 180/181 live on Fly `5efbbcd6`; item 183 half A and item 172 handed on, with 183's owner decisions already taken
**Type:** mini

---

## Summary
A merchant can now hold one Zoho account per company, and on a GL month that account books the merchant's receipts and charges with no model call. It shipped in PRs #1377 and #1383, deployed as Fly `0d0e45ef`, then `5efbbcd6`, and was checked on the live API and in a cold SPA drive. No merchant carries an account yet: the per-vendor suggestions are with the owner for Dirk.

## What Was Done
- **Backend (#1377).**
  - `merchants[].accounts` `{company: leaf code}` decides first in `categorize._registry_gl`. It matches on the company's Zoho org, so both spellings of a company work, and it works for a merchant with no default category and for receiptless charges.
  - A code the company cannot post to refuses with its reason. Bucket months never read the map.
  - The settings PUT keeps a stored map when a save omits the key; `{}` or null clears it.
  - The published editor already carries unknown merchant keys through a save (`Vi()` / `Hi()` spread `extra`, read off the live bundle).
- **Read side.** `GET /api/settings` gains `account_companies`, `merchant_accounts` and `needs_account`.
- **Re-run route.** `POST /api/runs/{id}/recategorize-refused` (typed confirm, job) re-runs a GL month's refused rows only. **Not run:** it writes on Criss's months and needs an owner order.
- **Tests.** `tests/test_merchant_accounts_item_180.py`: 11 tests, a model client that fails if called. Eleven wiring points proven RED. Full suite 3495 passed / 2 skipped. CI 8/8 on both PRs.
- **Follow-up (#1383), found by reading the live list.** `needs_account` keyed on the grid's `vendor.source`, which is stamped at ingest. It missed pre-registry rows and listed merchants already covered by a single `zoho_account`. Live now, 8 real gaps:
  - Anthropic × Corporate Services / Consulting;
  - Lovable Labs and Lovable Labs Incorporated × Corporate Services / Consulting;
  - Brave × Consulting;
  - ZOHO Corp. × Corporate Services.
- **Suggestions for Dirk.** vendor × company → code + name + evidence + postable, built by a read-only agent from Books 24 months, the seeded rules, the live months and the curated chart. File: `workspace/clients/brisken/context/expense-reconciliation/merchant-account-suggestions-260925.md` (gitignored). Seven open questions for Dirk are in it.
- **Item 183: owner decisions taken (AskUserQuestion, 2026-09-25).**
  - Corrections start ticked, conflicts unticked.
  - An unticked lesson is dropped and offered again next time.
  - Publish with zero lessons ticked still publishes.
- **SPA half.** `docs/lovable-merchant-accounts-per-company-prompt.md` (EN + PT-BR) with its PROMPT-STATUS row. Not pasted.

## What Did NOT Work (and why)
- **`needs_account` keyed on `vendor.source == "registry"`:** the flag is stamped at ingest. After the GL switch, 29 of 34 live Anthropic rows still read `extraction`, so the first live list missed Cloud Services and Consulting, and listed food merchants that book through `E100010-31`.
- **"Anthropic, PBC" against the registry's "Anthropic":** it does not resolve. `pbc` is not in `vendor_names._LEGAL_SUFFIXES`, so it counts as a distinctive word and the fuzzy score is 75 of the 88 needed. Open lead: a per-company Anthropic account reaches only the rows spelled plainly.
- **Storing a map key under the long spelling ("Brisken Cloud Services, LLC"):** a month resolves keys through its own frozen entity map, which may lack that spelling, so the model was asked. Keys are now stored under the picker spelling (`account_companies[].label`).
- **The first two cold drives of Settings read every merchant MISSING:** the probe read the page before it rendered. A 3 s wait fixed the instrument; the page was fine.
- **A 48-line heredoc carrying a Python triple-quoted block:** refused by the heredoc gate. Use Edit or Write.
- **`accounts` read as an attribute of every registry match:** `test_gl_engine`'s duck-typed stub has no `accounts`. It is read with `getattr`.

## Current Status
Fly `5efbbcd6` runs items 180/181. 33 merchants, none with an `accounts` map. July to September keep their 126 "model unsure" refusals until Dirk's accounts are entered AND the owner orders the refused-rows re-run. Item 207 is still open: the chart file on the server is unverified, which matters for item 172's card check. Ops status: platform unknown plan (no `platform` section for this FastAPI client).

Worktrees `agentic-ops1-i180`, `-deploy-i180` and `-ckpt180` are merged and clean after this PR (the `.venv` inside is ignored), ready to prune.

## Next Steps
1. Item 183 half A, with the decisions above; see the prompt below.
2. Item 172, after checking item 207.
3. The "Anthropic, PBC" lead: add `pbc` to the legal suffixes with a measured matcher impact, or have Dirk alias the merchant when he enters accounts.
4. When Dirk returns accounts: the owner's call to write them (OpenAI / Anthropic / Lovable are owner-gated), then an owner-ordered `recategorize-refused` per month.

## Files to Read First
- workspace/clients/brisken/status/p1-improvement-backlog.md (items 180, 181, 183, 172, 207)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/service.py (`commit_month_memory`, `plan_month_memory`, `commit_to_memory` ~5179)
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/learning/commits.py
- workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/merchant_accounts.py

## Continuation prompt

````
resume brisken

Continue Brisken p1 expense-recon: item 183 half A (Publish shows what it will remember), then item 172 (each card's paid-through account checked). Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)
Last checkpoint: `docs/2026-09-25 - Brisken P1 Merchant Account Per Company/Mini-Checkpoint-1.md`

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first. The clone is shared with live sibling sessions: work in a worktree off origin/main, one branch per item.
- Read `/healthz` on brisken-expense-recon.fly.dev (it was `5efbbcd6`).
- Module suite: 3495 passed / 2 skipped, run serially (xdist is not installed; about 11 min).
- Claim backlog numbers only after grepping `^### ` on origin/main AND the open PR diffs.
- Live API reads: `POST /api/login {"code"}` returns a `token`; send `Authorization: Bearer`. GET only.

## 1. ESTABLISHED. Do not re-derive.
- **Items 180/181 are live** (#1377, #1383):
  - `merchants[].accounts` `{company: leaf code}` decides first on a GL month (`categorize._registry_gl`, matched on org via `merchant_registry.company_account`);
  - PUT keeps a stored map when a save omits the key;
  - read side is `web/merchant_accounts.py`;
  - `POST /api/runs/{id}/recategorize-refused` (typed confirm) is built and NOT run: owner order only.
- **No merchant has an account yet.** Suggestions for Dirk: `context/expense-reconciliation/merchant-account-suggestions-260925.md`. OpenAI, Anthropic and Lovable registry writes are owner-gated; never write accounts to live settings without an owner order.
- **Open lead:** "Anthropic, PBC" (29 of 34 live Anthropic rows) does not resolve to registry "Anthropic", because `pbc` is not in `vendor_names._LEGAL_SUFFIXES`.
- **Item 183 half B is live** (2026-09-24): an account disagreement is a conflict in BOTH learners (`registry_upserts_from_expense_run` counts `skipped_account_conflict`; `_learn_categories` in `learning/capture.py`), and a conflicting merchant is skipped, so it produces NO planned write today.
- **Item 163 is live and its SPA prompt is APPLIED:** `GET /api/runs/{id}/memory-plan` (real learners against `learning.commits.RecordingStore`), the `/api/memory/commits` journal, undo. Publish (`app.py` `publish_run`) calls `commit_month_memory(..., trigger=MEMORY_TRIGGER_PUBLISH, only_if_changed=True)`, which calls `commit_to_memory` for real. `commit_to_memory` takes `store_factory` / `persist=False`, and `apply_plan` replays PlannedWrites with kwargs.
- **Owner decisions for 183 (AskUserQuestion 2026-09-25, do not re-ask):**
  - corrections start ticked, conflicts start unticked;
  - an unticked lesson is dropped and offered again next time (no declined store);
  - Publish with zero lessons ticked still publishes.
- `web/` must not import `..zoho`; chart reads go in `category_vocabulary.py` (`gl_leaf_status`, `gl_postable_ref`, `gl_companies` exist).

## 2. Item 183 half A: build
1. **Lesson ids and descriptions.** `memory-plan` entries get a stable id (derive from table + key, e.g. `merchant_category:<entity>|<vendor>`, `registry:<merchant>`) and a plain description: vendor, company, category or account, and the correction row(s) it came from.
2. **Conflicts.** Surface them from half B's learners as marked, UNTICKED lessons, one per candidate. A ticked candidate must produce its write through the real learner (for example re-run the learner on that candidate's rows only), never a hand-built call.
3. **Publish.** `POST /api/runs/{id}/publish` accepts `keep` (or `skip`) lesson ids. Filter what `RecordingStore` recorded, then `apply_plan` the filtered writes and apply only the kept registry changes, so the plan shown and the write done cannot differ. The journal records exactly what was written. Nothing unticked is saved. Zero kept still publishes.
4. **Item 180's map.** On a GL month, a kept correction of a vendor's account writes that company's entry in `merchants[].accounts` (code only, key = `account_companies[].label`).
5. **Owner-gated merchants.** OpenAI, Anthropic and Lovable stay owner-gated even when ticked: the registry write for them is refused and named in the reply.
6. **Tests**, route-level through `memory-plan` → `publish` with a skip list:
   - the skipped lesson is absent from the learning store and the registry;
   - the kept one is present;
   - the plan and the commit ledger match;
   - a conflict pair is not auto-saved;
   - a kept GL account correction lands in `accounts`.
   Regress-check the filter.
7. **SPA half.** `docs/lovable-publish-checklist-prompt.md` (EN + PT-BR, checkboxes, conflicts highlighted), a PROMPT-STATUS row, and the prompt text in the reply inside a FOUR-backtick fence labeled "paste into Lovable".

## 3. Item 172: each card's paid-through account checked
- **Item 207 first.** If the live chart file is unverified, every card flag must say it may be the chart that is stale.
- **Build.** `GET /api/settings` per-card `account_check`: ok / not_in_chart / wrong_type / inactive, plus the closest name. Reuse item 184's `zoho.accounts.resolve_paid_through` logic through `category_vocabulary`.
- **No live card edits.** List the failing cards with the suggested account in the reply. Card 3645 → `CHASE VISA - 2838 - TRAVEL` (backlog item 172).
- **Tests**, route-level: a real credit-card account passes; a non-existent name fails with the closest match; an expense account fails `wrong_type`.
- **SPA half.** `docs/lovable-card-account-check-prompt.md`, a PROMPT-STATUS row, the fenced prompt.

## 4. Hazards
- **B6 chain.** Commit, push and PR are autonomous after real verification. Read `mergeable_state` before polling checks. Merge on green in a separate call; never end a turn with a PR waiting.
- **Deploys** (pre-authorized): from a clean detached origin/main worktree, `MW=$(cygpath -w "$M")`, `FLY_API_TOKEN` read from `~/.fly/config.yml`, `--build-arg GIT_COMMIT`. Verify `/healthz`, then read the changed fields. Drive the SPA cold with `uv run --with playwright` (headless `channel="chrome"`), wait about 3 s after login before reading, and read input VALUES, not only `inner_text`.
- **Criss's months and live settings:** no writes without an owner order. Never inject July. No writes to production Zoho orgs.
- **Heredocs:** no Python triple-quoted blocks, nothing over 80 lines. Bash mangles leading-slash args: prefix `MSYS_NO_PATHCONV=1`.
- **Records:** each item goes in `status/p1-improvement-backlog.md` and rolls up in `p1-expense-reconciliation.md`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````
