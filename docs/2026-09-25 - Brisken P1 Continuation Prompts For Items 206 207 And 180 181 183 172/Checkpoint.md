# Checkpoint: Brisken P1 Continuation Prompts For Items 206 207 And 180 181 183 172

**Date:** 2026-09-25
**Status:** July to September are on the Zoho accounts and item 201 is live (see Mini-Checkpoint-1 of "Brisken P1 July To September On Zoho Accounts"). Two fresh-chat prompts are written: items 206/207, and items 180/181, 183 half A and 172. Nothing is in flight.

---

## Summary
This session closed the 2026-09-24/25 run. The 9693 load, item 197, the applied GL prompt, and the July to September switch with item 201 are covered in this topic's two mini-checkpoints and the July to September one. The owner asked for plain-language explanations of the remaining memory items, then for two paste-ready prompts that implement them in fresh chats. Both prompts are below.

---

## What Was Done This Session
### Since the last mini-checkpoint
1. Explained items 180/181, 183 and 172 in plain language, as the owner asked. For each: today, the problem, the change, and who acts.
2. Wrote a fresh-chat prompt for items 206 and 207 (Prompt A below).
3. Wrote a fresh-chat prompt for items 180/181, 183 half A and 172 (Prompt B below).
4. Added a new pattern rule, `block-flyctl-deploy-posix-path`, for the recurring Windows deploy failure.
   - It fires on the incident text and on a direct `/c/` path, and stays silent on the Windows-path form.
   - `tools/tests/test_pattern_rules_gate.py` passes.

### Earlier in the session (full record in the mini-checkpoints)
1. The 9693 statements were loaded into August and September. Item 197 (FX rung order) is fixed and live.
2. The GL accounts prompt was applied and driven in EN and PT; the TEST batch was purged.
3. Item 201 and the month switch (items 201, 205): PR #1356, Fly `071b19d7`.
   - The three months were switched after snapshot `vs_V9ka1J80opbTj8gxvqQ59X5`.
   - Record: PR #1359. Checkpoint: PR #1361.

---

## Key Decisions Made
### Criss's bucket picks on July to September
- **Choice:** owner, via AskUserQuestion: "Ignore her picks". The engine decides every row. The 35 picks are archived in each month's `gl_conversion` key.
- **Rationale:** no bucket maps to one account.

### The Publish checklist (item 183 half A) counts as owner-approved
- **Choice:** Prompt B treats the owner's "write a prompt to implement these solutions" as the go-ahead. The three open design questions still go to the owner through AskUserQuestion in that session: the default tick state, unticked lessons dropped or recorded as declined, and publishing with nothing ticked.
- **Rationale:** the owner asked for implementation. Those details change what Publish does, so they remain his call.

### No live master-data writes in Prompt B
- **Choice:** the vendor accounts (item 181) and the card accounts (item 172) arrive as suggestion tables for the owner and Dirk, never as writes to live settings. A re-run of the engine on July to September's blank rows is built behind a typed confirm and runs only on an owner order.
- **Rationale:** the Anthropic, OpenAI and Lovable registry entries are owner-gated, card accounts are Criss's or the owner's call, and no agent writes on Criss's months.

---

## What Did NOT Work (and why)
- **`pytest -n 4` on the module suite:** xdist is not installed in the module env, so it fails with a usage error. The 2026-09-24 session log already recorded this.
- **The first item 201 full-suite run:** `test_zoho_posting_is_gated` forbids `web/` importing `..zoho`. The lookup moved to `category_vocabulary`.
- **`flyctl deploy "$M"` with `M=/c/...` under `MSYS_NO_PATHCONV=1`:** flyctl chdir'd to `C:\c\Users\...` and failed. The 2026-09-24 row records the same failure. Now blocked by `block-flyctl-deploy-posix-path`.
- **A read-back regex `^E\d{6}(-\d{2})+$`:** suffix-less leaf codes (`E500010`) read as buckets. That produced a false "4 receipts and 16 charges still on buckets" alarm, caught before any claim.
- **The drive's retired-Zoho-picker probe (`aria-autocomplete=none` plus "|"):** it also matches the Paid through select, which gave a false FAIL on August.
- **A 78-line heredoc with a Python triple-quoted block:** blocked by the heredoc gate. It was rewritten via the Write tool.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.claude/patterns/block-flyctl-deploy-posix-path.md` | Created | Blocks a flyctl deploy given a Git-Bash `/c/` path under `MSYS_NO_PATHCONV=1` |
| `docs/2026-09-25 - Brisken P1 Continuation Prompts For Items 206 207 And 180 181 183 172/Checkpoint.md` | Created | This checkpoint, with Prompts A and B |
| memory `project_brisken_expense_recon_usability_loop.md` | Edited (earlier) | Switch facts, traps and leads 206/207 |
| (merged earlier) PRs #1356, #1359, #1361 | | Code, record and mini-checkpoint for the switch |

---

## Current Status
- Fly runs `071b19d7`. July, August and September read `category_vocabulary: "gl"`.
- Open leads:
  - item 206: a card fix does not re-run the engine;
  - item 207: the live export gate blanks E700030-30 on Cloud; the chart file on the server is likely stale.
- Waiting on others:
  - Dirk: vendor accounts per company (item 181) and card accounts (item 172, 3645 first);
  - owner: the Publish checklist details (item 183 half A).
- Ops: platform unknown plan (no `platform` section for this FastAPI client). The comms log is not tracked for brisken.

---

## Next Steps
1. Paste Prompt A into a fresh chat (items 206, 207). Item 207 settles whether the chart file on the server is current.
2. Then paste Prompt B (items 180/181, 183 half A, 172). Its card check depends on item 207's answer.
3. Still queued behind them: item 196 (land the sure rows), 202 (measure first), 195, the small outage leftovers, the review xlsx cleanup (only when the lock is gone and the sha matches), and Dirk's 0113 export.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (items 180, 181, 183, 172, 205, 206, 207)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/gl_conversion.py`
- `docs/2026-09-25 - Brisken P1 July To September On Zoho Accounts/Mini-Checkpoint-1.md`

### Open Questions
- Is the chart file on the Fly volume older than the local Sep 24 chart (item 207)?
- Does the published SPA rebuild merchant objects from known fields on a Settings save? If so, it would wipe a new per-company account map (Prompt B, step 3).
- Item 183 half B shipped 2026-09-24: does it already flag one vendor booked to two accounts in a month?

### Working Notes
- After the switch, the 126 "model unsure" lines are mostly AI vendors on Corporate Services. That chart has several fitting accounts: `CorpServ | IT Expenses`, `IT: Cloud Subscriptions-Others`, and the COGS infrastructure codes. So the model answers 0.5 against a review threshold of 0.6.
- Locally against `context/zoho-books-coa.json` (Sep 24), `coa_gate._resolve_label` + `_curated_verdict` pass E700030-30 as OK, with id `2031056000001432081`.

### Reference Materials
- Snapshot `vs_V9ka1J80opbTj8gxvqQ59X5` (before the switch); volume `vol_vgnplk8909y0q184`.
- The scratchpad helpers used this session (`api.py`, `write.py`, `gl_verify.py`, `gl_months_drive.py`) live in this session's scratchpad and are not durable; rebuild them from the prompts' descriptions if needed.

---

## How to Continue
Start a fresh chat and paste Prompt A. When it finishes, start another and paste Prompt B. Both carry the SESSION LOOP block.

### Prompt A: items 206 and 207

````
resume brisken

Continue Brisken p1 expense-recon: fix backlog items 206 and 207. Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)
Last checkpoint: `docs/2026-09-25 - Brisken P1 Continuation Prompts For Items 206 207 And 180 181 183 172/Checkpoint.md`

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first. The clone is shared with live sibling sessions: work in a worktree off origin/main, one branch per item.
- Live Fly was `071b19d7` at the last checkpoint; read `/healthz` for the current commit.
- Module suite: 3460 passed / 2 skipped, run serially (`pytest -n` fails: xdist is not installed).
- Claim a backlog number only after grepping `^### ` on origin/main AND the open PR diffs.

## 1. ESTABLISHED (2026-09-25). Do not re-derive.
- July (`50622baec444`), August (`074a7b8905d7`) and September (`51a22ad72864`) are GL months: `category_vocabulary: "gl"`. They were switched by `POST /api/runs/{id}/convert-to-gl` (`web/gl_conversion.py`). The switch is one-way; never re-run it.
- Item 201 is live. A hand-picked leaf code reads its account name in the company the row SHOWS: `category_vocabulary.gl_leaf_account_name`, fed by `service.resolved_entities(card_res)` from `resolve_batch_row_cards`.
- `web/` must not import `..zoho` (`tests/test_zoho_posting_is_gated.py`). Chart reads go in `category_vocabulary.py`.
- Most live rows carry NO company stamp of their own. The company the grid shows comes from the card chain at read time.

## 2. Item 206: a card that gives a row its company must re-run the engine
**Symptom.** On a GL month, a receipt that arrived with no company is refused `entity_missing`. Setting the company directly re-runs the engine for it. Giving the row a company through a CARD does not, so the row keeps its refusal while the grid names a company. Every GL month from October is affected.

**Where it lives.**
- `web/app.py`, the field route (`PUT /api/runs/{id}/expenses/{doc}`): only `if field == "legal_entity" and before != value: recategorize = document_id`. `PUT .../entity` has the same trigger. A `card_key` edit (item 87's per-row card fix) never triggers.
- `service.recategorize_after_entity_change(db_path, learning_db_path, run_id, document_id)` picks the company from the field override, else the receipt's stamp, else the batch default. It never reads the card chain. It returns None on a bucket month.
- Other ways a row gains its company through the card chain:
  - a card-hint assignment (find the route);
  - a statement charge settling the receipt (`settled_charge_cards`, applied at read time);
  - a remembered card (`fill_remembered_cards`).
- `web/gl_conversion.py` already categorizes for the SHOWN company: its route builds `entity_by_doc` from `_expense_view(store, run)["expenses"][].legal_entity_id`. Reuse that pattern; do not invent a second company resolver.

**Recommended design (confirm against the code first).** Make "the engine answers for the company the row shows" hold everywhere:
- Give `recategorize_after_entity_change` an optional explicit company, so a caller can pass the shown one.
- In the edit routes, compare the row's shown company before and after any edit that can move it (`card_key`, a card hint, `legal_entity`). When it changed, re-run the engine for the new shown company.
- After a re-match or attach on a GL month, sweep the rows that show a company but still carry an `entity_missing` refusal, and re-run the engine for those.

**Tests.** Route-level, through the card fix. The fixture pattern is in `tests/test_gl_hand_pick_account_item_201.py`, test `test_a_row_whose_company_comes_from_its_card_reads_that_companys_name`:
- `PUT /api/settings` with a `cards` entry that has an entity;
- a GL batch created with `legal_entity: ""`;
- `PUT .../expenses/{doc}` with `{"field": "card_key", "value": ...}`.

Assert that the row's `posting_category.category` becomes a leaf code of that company and that `review.reason_code` is no longer `category_refused`. Cover a card change from one company to another, and a bucket month that stays untouched. Prove every trigger with `uv run tools/regress_check.py` (green, then red under mutation, then green; pass `--file` relative to the module root, e.g. `src/...`).

**Live after deploy (read-only).** Count the rows on July to September that show a company and still carry `entity_missing`. The switch categorized for the shown company, so expect 0. If any exist, list them and ask the owner before re-categorizing. No agent writes on Criss's months without an owner order.

## 3. Item 207: the live export gate blanks an account Dirk marked postable
**Symptom.**
- The row: September's SendGrid receipt. Cloud Services, USD 89.95, 2026-09-03, ref `P-20637471`, paid through "Chase Visa | 9693 | Cloud Expenses".
- Its account: a learned rule files it to `E700030-30`, "COGS - Other Infra and IT Costs for Cloud Business". Curated leaves mark that postable for Cloud Services (org 697686691), account_id `2031056000001432081`.
- What goes wrong: the grid's `books_as` and `GET /runs/{id}/expenses.csv` both print `(account unmapped - assign)`. It is 1 row of 209 across the three exports.

**What is known.**
- Run locally against `workspace/clients/brisken/context/zoho-books-coa.json` (gitignored, 2026-09-24 00:13, 255 accounts for 697686691), `coa_gate._resolve_label(name, ChartOfAccounts.from_api(accounts))` finds E700030-30 with that id, and `coa_gate._curated_verdict(acct, "697686691")` answers `CoaVerdict.OK`.
- The live gate is built by `service._coa_gate_from_config(run.config, work_dir)` → `cli._build_coa_gate`. The config's `coa_validation` block came from `coa_provision.apply_to_config`; the provisioning file (env `EXPENSE_RECON_COA_PROVISION`) names the `chart_path`.
- Leading hypothesis: the chart file on the Fly volume predates the item 182 refresh. That pull was truncated and missed 19 of Dirk's accounts.
- Rule out first, from code and API only:
  - September's all-company gate maps "Cloud Services" to a different chart entry;
  - the near-namesake "COGS - Other Infra and IT Costs for Cloud Business(INTER COMPANY)" (E700040-30) breaks name resolution in the live chart.

**Confirming it needs a production read.** In the last session the permission classifier refused `flyctl ssh` sqlite reads and `GET /api/operator/state`. So before any read on the machine, ask the owner once via AskUserQuestion, with a recommendation. The read: a read-only `flyctl ssh console -C` that prints the live chart file's mtime and size, its account count for 697686691, and whether E700030-30 is present and under which id.
- Pass `FLY_API_TOKEN` read from `~/.fly/config.yml`, use `< /dev/null`, and keep the payload under about 1 KB (a 3.4 KB payload returned nothing).

**Fix.**
- If the live chart is stale, refresh it through the path that put it there. Find that path in `docs/operating.md`, item 182 and `tools/pull-brisken-zoho-coa.py`; do not invent one.
- The chart pull is a Zoho READ, which is allowed.
- Writing the file onto the volume is a production write: get an owner yes, take a Fly volume snapshot first (`flyctl volumes snapshots create vol_vgnplk8909y0q184 -a brisken-expense-recon`, then wait for `created`), then write. Re-read the September CSV afterwards and expect the SendGrid row named.
- Structural half, so a stale chart can never again blank an account silently: propose, and build if small, a check that lists curated postable codes missing from the live chart per org. Surface it where the operator already looks, e.g. `/healthz` or the export's advisory, and test it route-level. If it changes a verdict or a sentence the SPA shows, it needs the owner's go.

## 4. Ship chain and hazards
- B6: commit, push and PR are autonomous after real verification. Merge on green CI **in the same turn**: poll `gh pr checks`, then merge in a separate call, never chained with `--watch`. Do not end a turn with a PR waiting.
- Deploys are pre-authorized after a green merge:
  - build from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)`;
  - under `MSYS_NO_PATHCONV=1`, pass flyctl the WINDOWS path;
  - verify the `/healthz` commit, then drive the consumer cold.
- SPA drive:
  - `uv run --with playwright`, headless `channel="chrome"`;
  - on the gate, type the code until Log in enables, then click;
  - the GL picker is `button[role=combobox][aria-haspopup=dialog]`;
  - the Paid through select also matches `aria-autocomplete=none` plus "|".
- Leaf codes include suffix-less parents (`E500010`): the regex is `^E\d{6}(-\d{2})*$`.
- Never inject July. No writes to production Zoho orgs.
- Force-push is gated. Heredocs: no Python triple-quoted blocks, nothing over 80 lines (use the Write tool, then run the file). Bash mangles leading-slash args: prefix `MSYS_NO_PATHCONV=1`.
- Record both items in `workspace/clients/brisken/status/p1-improvement-backlog.md` (headings 206 and 207) and roll them up in `p1-expense-reconciliation.md`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````

### Prompt B: items 180/181, 183 half A and 172

````
resume brisken

Continue Brisken p1 expense-recon: implement backlog items 180/181 (a vendor's account per company), 183 half A (Publish shows what it will remember) and 172 (each card's paid-through account checked). Read this whole brief before acting.

Repo: `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`
Module root: `workspace/clients/brisken/automations/expense-reconciliation`
Lovable SPA repo: `011matthias/brisken-expense-review` (live at expenses.brisken.com)
Last checkpoint: `docs/2026-09-25 - Brisken P1 Continuation Prompts For Items 206 207 And 180 181 183 172/Checkpoint.md`

**Zoho token rule: `expenses.CREATE` is strictly NOT authorized for production.
Production orgs remain strictly read-only; writes are locked to sandbox 822116290.**

## 0. Handshake
- `git fetch origin` first. The clone is shared with live sibling sessions: work in a worktree off origin/main, one branch per item.
- Read `/healthz` for the live commit (it was `071b19d7` at the last checkpoint).
- Module suite: 3460 passed / 2 skipped, run serially (`pytest -n` fails: xdist is not installed).
- Claim backlog numbers only after grepping `^### ` on origin/main AND the open PR diffs. Siblings are working card attribution (item 204, the "no payment info" backbone). Check their open PRs for overlap before touching cards.
- Read first:
  - `status/p1-improvement-backlog.md` items 172, 177, 179, 180, 181, 183, 184, 205, 207;
  - `docs/zoho-gl-categorization-architecture.md`;
  - memories `project_brisken_expense_recon_merchant_registry`, `project_brisken_recon_learning_rules`, `project_brisken_coa_expense_relevant`.
- Check whether item 207 is resolved. It decides whether the chart file on the server is current. If it is still open, part 4's card check will produce false flags; do part 4 last or flag the dependency.

## 1. ESTABLISHED. Do not re-derive.
- Each expense books to two Zoho accounts: the expense account (a curated leaf CODE on GL months) and the paid-through account (the card's liability account).
- July, August and September are GL months (switched 2026-09-25); October onward are GL from creation. After the switch, 126 lines on July to September are refused as "model unsure". Most are AI vendors on Corporate Services (Anthropic, OpenRouter, Lovable, Wispr, Rize), where several accounts fit: `CorpServ | IT Expenses`, `IT: Cloud Subscriptions-Others`, and the COGS infrastructure accounts.
- Registry tier on the GL engine (`categorize._registry_gl`):
  - it tries `_registry_account` (the company's learned rule, else the merchant's single `zoho_account`), then the merchant's default category;
  - each is resolved within the receipt's org via `curated_leaves.code_of(ref, org_id)`;
  - a bucket default names no leaf and falls through to the model.
- `code_of` resolves a code or a name within ONE org. The name differs per company (`CorpServ | Travel Expense | Food` against `Travel Expense | Food` for E100010-31); the code is the identity.
- Brisken's own books put Anthropic under "Other Infra and IT Costs" in Corporate Services and "COGS - DEV Infrastructure" in Cloud Services (comment in `categorize.categorize_receipts_with_registry`). Evidence of that kind lives in the Zoho-seeded learned rules (`learning.consult.ZOHO_SEED_PREFIX`).
- 2026-09-24 owner ruling: only a person's CORRECTIONS may be memorized, never a model guess and never a confirm-as-is.
- Writes to the OpenAI, Anthropic and Lovable registry entries are owner-gated.
- Settings saves are WHOLESALE (item 177): the SPA sends the whole settings map back on every save, and `category_vocabulary.recognize` drops unknown values instead of refusing them.
- `web/` must not import `..zoho` (`tests/test_zoho_posting_is_gated.py`). Chart reads go in `category_vocabulary.py`.
- Item 163 is live: `GET /api/runs/{id}/memory-plan` is produced by the REAL learners through `learning/commits.py` `RecordingStore`. `GET /api/memory/commits` is the ledger, and `POST /api/memory/commits/{id}/undo` undoes the newest save. Its SPA prompt `docs/lovable-memory-journal-prompt.md` may still be unpasted; check PROMPT-STATUS.
- Owner request 2026-09-25: implement all three changes below.

## 2. Item 180/181: a vendor's account per company
**Today.** A merchant entry holds one `category` and one `zoho_account`, applied to every company, every month. The AI vendors hold no account at all.

**Build.**
1. **Data model.** An optional per-company account map on a merchant entry, e.g. `accounts: {"<entity label>": "<leaf code>"}`. Codes are stored, names never (a name is one company's wording). Normalize through `category_vocabulary.recognize`.
2. **Old entries keep working unchanged.** An entry without the map behaves exactly as today.
3. **Wholesale-save hazard (verify before relying on anything).** Run `tools/lovable-bundle-audit.py` against the published SPA and read how the settings page rebuilds a merchant before PUT. If it rebuilds from known fields, the published SPA will send merchants WITHOUT the new map on every unrelated save. In that case the backend must keep the stored map when an incoming entry omits the key: absent means "unchanged", an explicit `{}` or null means "clear". Pin that with a route-level test.
4. **Engine.** In `_registry_gl`, the receipt's company entry in the map wins, resolved with `code_of` in that org. A code that org cannot post to refuses with its reason, as the other tiers do. Receiptless charges take the same path through `categorize_charges` (registry passed in).
5. **Read side.**
   - `GET /api/settings` carries each merchant's map, with each code's name per company (reuse `gl_account_options` data).
   - It also carries a `needs_account` list: registry merchants with no account for a company they were booked to in the GL months.
6. **Suggestions for Dirk, not written.** From the Zoho-seeded learned rules, the three switched months and the curated charts, build a table for the AI and cloud vendors (Anthropic, OpenRouter, Lovable, Wispr, Rize, Zoho, Brave, OpenAI, SendGrid, Railway, Redis and any others found):
   - vendor × company → suggested leaf code + name;
   - the evidence behind each suggestion;
   - whether the code is postable in that company.

   Hand the table to the owner in the reply. Do NOT write these into live settings: the OpenAI, Anthropic and Lovable entries are owner-gated, and Dirk decides. Do not draft or send anything to Dirk.
7. **Existing blank rows.** New registry accounts reach July to September only through a re-run of the engine on the refused rows, which is a write on Criss's months. Build it as an operator route, tested and refusing without a typed confirm, and run it ONLY after the owner orders it (AskUserQuestion when the accounts exist). `convert-to-gl` answers `month_already_gl` and must not be reused.
8. **SPA half.**
   - Write `docs/lovable-merchant-accounts-per-company-prompt.md`: Settings > Merchants shows, per merchant, one account picker per company (grouped leaves from `gl_accounts[company]`) and the `needs_account` list, in EN and PT-BR.
   - Add its PROMPT-STATUS row.
   - Give the prompt text in your reply inside a FOUR-backtick fence, labeled "paste into Lovable".

**Tests.** Route-level through the settings route AND a GL batch's categorization:
- a merchant with a Corporate Services account and a Cloud Services account books each company's receipt to its own code, without a model call (use a client that fails if called);
- a wholesale save that omits the map keeps it;
- a code not postable in the company refuses;
- a bucket month is unchanged.

Regress-check each wiring point with `tools/regress_check.py` (pass `--file` relative to the module root, e.g. `src/...`).

## 3. Item 183 half A: Publish shows what it will remember
**First, verify what exists.** Item 183 half B shipped 2026-09-24. Read exactly what it covers. The account-aware conflict check (the same vendor booked to two accounts in one month) may already be live: do not rebuild it, surface it.

**Build.** Publish takes the reviewer's choice of which lessons to keep:
1. `memory-plan` entries get a stable id and a plain description: vendor, company, category or account, and the correction it came from.
2. Conflicting entries are marked, and neither is pre-selected.
3. `POST /api/runs/{id}/publish` accepts the ids to keep (or the ids to skip). The learners honor it: filter what `RecordingStore` recorded before the real write, so the plan shown and the write done cannot differ.
4. Nothing unticked is saved.
5. On a GL month, a kept correction of a vendor's account writes that company's entry in item 180's map. This is how Criss's hand picks become per-company accounts.
6. The OpenAI, Anthropic and Lovable entries stay owner-gated even when ticked.

**Owner decisions to put through AskUserQuestion, with a recommendation, before coding them:**
- the default state of each line (recommend: corrections ticked, conflicts unticked);
- whether an unticked lesson is dropped silently or recorded as "declined", so it is not offered again next month;
- whether Publish with zero lessons ticked still publishes (recommend: yes).

**Tests.** Route-level through `memory-plan` → `publish` with a skip list:
- the skipped lesson is absent from the learning store and the registry;
- the kept one is present;
- the plan shown and the commit ledger match;
- a conflict pair is not auto-saved.

Regress-check the filter.

**SPA half.**
- Write `docs/lovable-publish-checklist-prompt.md`: the Publish dialog lists the lessons with checkboxes, conflicts highlighted, in EN and PT-BR.
- Add its PROMPT-STATUS row.
- Give the prompt text in your reply inside a FOUR-backtick fence, labeled "paste into Lovable".

## 4. Item 172: each card's paid-through account checked
**Today.** Settings > Cards stores each card's `zoho_account` (entries `{label, digits, entity, person, zoho_account}`), and the export writes it as Paid Through. Card 3645 (billed on the 2838 statement) holds "Credit Card - 2838", while Zoho's account is "CHASE VISA - 2838 - TRAVEL".

**Build.**
1. `GET /api/settings` carries a per-card `account_check`: ok / not_in_chart / wrong_type / inactive, plus the closest matching account name.
2. The check runs against that card's company chart. Reuse the paid-through validation item 184 / queue item 6 shipped (numeric id, in the org's chart, active, not DNU, `credit_card` type, name match); do not write a second one.
3. `/api/cards/status` or the Settings reply names the cards that fail.
4. **Do not change any card's account on live settings.** That is master data and Criss's or the owner's call. List the failing cards with the suggested account in the reply.
5. If the chart file on the server is stale (item 207), say so next to every flag: a flag may mean the chart is old, not that the card is wrong.

**Tests.** Route-level through `GET /api/settings`:
- a card naming a real credit-card account passes;
- a card naming a non-existent name fails with the closest match;
- a card naming an expense account fails `wrong_type`.

Regress-check the wiring.

**SPA half.**
- Write `docs/lovable-card-account-check-prompt.md`: Settings > Cards shows a warning chip and the suggested account per failing card, in EN and PT-BR.
- Add its PROMPT-STATUS row.
- Give the prompt text in your reply inside a FOUR-backtick fence, labeled "paste into Lovable".

## 5. Order, ship chain, hazards
- **Order:**
  1. 180/181 backend and the suggestions table;
  2. 183 (it writes into 180's map);
  3. 172.

  Checkpoint after each item if context passes 300k. One branch and one PR per item.
- **B6.** Commit, push and PR are autonomous after real verification. Merge on green CI **in the same turn**: poll `gh pr checks`, then merge in a separate call, never chained with `--watch`. Never end a turn with a PR waiting.
- **Deploys** are pre-authorized after a green merge:
  - build from a clean detached origin/main worktree with `--build-arg GIT_COMMIT=$(git rev-parse HEAD)`;
  - under `MSYS_NO_PATHCONV=1`, pass flyctl the WINDOWS path;
  - verify the `/healthz` commit, then read the changed fields on the live API.
- **An SPA change is live only after the owner pastes and Publishes the Lovable prompt.** Then:
  - run `tools/lovable-bundle-audit.py` using field names and i18n keys (minified identifiers and TS types are not valid markers);
  - drive cold in EN and PT: `uv run --with playwright`, headless `channel="chrome"`; on the gate, type the code until Log in enables, then click;
  - mark the prompt Applied in PROMPT-STATUS.
- **Criss's months and live settings:**
  - no agent writes to live settings or on Criss's months without an owner order;
  - synthetic data only in a `TEST - ...` batch, deleted the same session.
- Never inject July. No writes to production Zoho orgs.
- Leaf codes include suffix-less parents (`E500010`): the regex is `^E\d{6}(-\d{2})*$`.
- Force-push is gated. Heredocs: no Python triple-quoted blocks, nothing over 80 lines (use the Write tool, then run the file). Bash mangles leading-slash args: prefix `MSYS_NO_PATHCONV=1`.
- Record each item in `workspace/clients/brisken/status/p1-improvement-backlog.md` and roll up in `p1-expense-reconciliation.md`.

## SESSION LOOP
[Standard checkpointing bands at 300k/500k apply; commit before checkpointing; never start items crossing 500k. End each iteration by listing the remaining queue items. Carry this SESSION LOOP block verbatim into the next continuation prompt.]
````

---

## Strategic Feedback

### What Worked Well This Session
- **Categorizing each row for the company the grid shows, not the receipt's own stamp.** Checking the grid's card chain before designing the switch caught that most live rows have a blank stamp. Using the stamp would have refused most of July as "no company".
- **A snapshot and a before/after capture around every live write.** One month at a time made the switch auditable: 16/12/12 rows with a category but no account went to 0/0/0, verified through the grid, the CSV and a cold browser drive.

### Suggestions
- `warn-stop-merge-left-pending` has now fired after the fact twice (2026-09-24 and today). As a warn it only reaches the agent on the next prompt, after the turn has ended. Upgrading it to a Stop-event `block` would make the turn continue into the merge instead of closing on a promise.

### System Health
- Recall-dependent hazards keep recurring even when the brief names them: the triple-quoted heredoc and `pytest -n`. The ones with a hook (heredoc gate, and now `block-flyctl-deploy-posix-path`) cost one call; the ones without cost minutes. Candidates for pattern rules: `pytest -n` in the brisken module, and tailing a piped task output file (the rule exists as a warn).
- **Autonomy:** 4 human interventions. Three were owner decisions via AskUserQuestion (item 197 first; items 201/196; Criss's picks) and one was the owner's Lovable paste. All four were genuine owner calls, not avoidable deferrals.
