# Mini-Checkpoint: Expense-Recon Front 3 Account

**Date:** 2026-09-27
**Status:** item 224 steps 1-5 shipped and live (PR #1477, merge `3c904cfe`, Fly v262); steps 6-8 and three owner-approved actions open
**Type:** mini

---

## Summary
Front 3 of the 2026-09-25 five-front round: the posting account now reads the merchant list as it is now (identity, per-company account, descriptor tier, containment guard, ZOHO ERP guard, stale suggestions read as refusals), live and driven cold on September.

## What Was Done
- Step 1: `categorize.live_registry_accounts` / `live_registry_charge_accounts` (one builder `registry_mapped_categorization`, shared with `_registry_gl`) applied at view time in `build_expense_view`, `build_view` (incl. borrowed receipts and a company-blank receipt taking its charge's company) and the CSV / month report / bills.csv (`_expense_export_inputs(live_accounts=True)`); `vendor.stamped`, `merchant {name, match}`, `posting_category.stamped`.
- Step 2: descriptor tier `MerchantRegistry._descriptor_hit` (lead word, product word on Google/Microsoft/Amazon, only a country code / short code / Chase stub uncovered, a shop-kind word the name lacks = another business, a tie = no answer). Step 3: containment guard in `_fuzzy_score` + `_is_bare_platform_alias`. Step 4: `ACCOUNT_VENDOR_SPECIFIC` / `VENDOR_SPECIFIC_ACCOUNTS {"E500010-10": ("zoho",)}` in posting_resolution, wired into `_gl_model_result`. Step 5: `_stale_suggestion` re-reads stored model suggestions at view time.
- Tests: `tests/test_front3_identity_live.py` (8), `tests/test_front3_resolver.py` (12), contract guard in `test_view_contract.py`, refusal pin in `test_gl_engine.py`; 11 `regress_check` proofs bit. CI green (module `test` 5m53s); local suite 3905 passed, the 7 `test_smtp_starttls` failures are local-only (green in CI).
- Predicted per row before deploy (payloads `.scratch/recon-score-2026-09-25-front3-before/`): 21 receipts to the owner's OpenAI/Anthropic accounts (all 21 post), 46 receiptless + 5 matched charges; 24 join a Criss posting, 24 agree, 0 disagree. Live after deploy: grid `posting_category.stamped` 1/4/16 = 21 exactly; run payload 12 / 29 / 11; the 8 September rows the two build_view fixes target all read E700030-19 rule. Refusals live: `account_vendor_specific` run 1/6/4, grid 4/5/4; `model_picked_parent` run 7/12/1, grid 5/1/4.
- Consumer drive (headless Playwright, channel chrome, cold login): `/expenses/51a22ad72864` renders "OpenAI" 23 times and receipt 0010's registry account "COGS - DEV Infrastructure (SAP Apps & others)" (was the model's "IT: Computer and Internet Expenses"); no "Unknown" / "No receipt found". The SPA does not render the new fields yet (prompt pending).
- Owner decisions 2026-09-27: item 115 YES; merge the Lovable entries YES; restore `zoho-books-24mo.json` YES (done, expenses only).

## What Did NOT Work (and why)
- **`recon-categorization-score.py --zoho <24mo file> --pull-zoho`:** with `--pull-zoho`, `--zoho` is the WRITE target, so it overwrote the gitignored 24-month history with a Jul-Sep pull (own mistake). Restored by an owner-approved read-only re-pull: expenses only (2,357 vs 2,355; Holding's 1 missing), bills not restorable (`/books/v3/bills` and `/organizations` answer "not authorized" for our token).
- **agent-browser `--session recon-front3`:** hung past 180 s, then "os error 10060" on close; headless Playwright on installed Chrome worked.
- **Descriptor tier first cut:** matched 'Twilio Inc' to SendGrid through an alias, 'FENIX TURISMO' to Supermercado Fenix, and (caught by the full suite) 'Farmacia Pimentel' / 'NOBRE ATACADO E VAREJO'; fixed by the canonical-lead, uncovered-word and shop-kind rules.
- **Backlog number 221:** taken by front 1 while my CI ran; renumbered to 224 (Shipped row 144).

## Current Status
Live on v262. Item 224 steps 1-5 done; SPA prompt `docs/lovable-identity-live-prompt.md` pending. Ops status: brisken platform unknown plan (infrastructure.yaml has no assessment).

## Next Steps
1. Step 6 line-sum check (predict the 35 rows first).
2. Item 115 (owner yes): a seeded rule leads on a lined receipt, second read flags disagreement.
3. Lovable merge (owner yes): read-modify-write of `settings.merchants` with a readiness check.
4. Measure the descriptor tier on all 314 descriptors under the live and write-plan lists.
5. Present the write plan's uncontested rows to the owner.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 224
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last two sections)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorize.py` (`live_registry_accounts`, `_stale_suggestion`)

## Continuation prompt
``
/comd_resume brisken

# FRONT 3 continued: the posting account (item 224 steps 6-8, and three owner-approved actions)

## Where it stands
Session 2026-09-25/27 (front 3 of the 23-agent map round) shipped item 224 steps 1-5, PR #1477, merge `3c904cfe`, Fly v262 (checkpoint `docs/2026-09-27 - Expense-Recon Front 3 Account/Mini-Checkpoint-1.md`).
- (1) The grid, the run payload and the reviewer files (expenses.csv, month report, bills.csv) read the merchant list LIVE: `vendor.display/source` + `vendor.stamped`, parallel `merchant {name, match}`, and a merchant's per-company account decides as a rule with `posting_category.stamped`. Code: `categorize.live_registry_accounts` / `live_registry_charge_accounts` / `registry_mapped_categorization` (the one builder `_registry_gl` also uses); `web/service.py` end-of-file helpers `expense_vendor_view_live`, `receipt_merchant_field`, `charge_merchant_field`, `live_stamped_category`; `_expense_export_inputs(live_accounts=True)` on the CSV, report and bills callers only.
- (2) Descriptor tier `MerchantRegistry._descriptor_hit` + `_descriptor_score` (merchant_registry.py), `PLATFORM_WORDS` = google/microsoft/msft/amazon/amz/aws. (3) Containment guard in `_fuzzy_score` (canonical lead + platform product word, -0.5 so an equal-words name wins) and `_is_bare_platform_alias`. (4) `posting_resolution.ACCOUNT_VENDOR_SPECIFIC` + `VENDOR_SPECIFIC_ACCOUNTS {"E500010-10": ("zoho",)}` + `vendor_may_post`, wired in `_gl_model_result(vendor_names=)`. (5) `categorize._stale_suggestion` re-reads stored model suggestions (parent -> model_picked_parent, non-Zoho E500010-10 -> account_vendor_specific) at view time.
- Predicted before deploy (payloads `.scratch/recon-score-2026-09-25-front3-before/`, 16:49 UTC): 21 receipts move to the owner's OpenAI/Anthropic accounts and all 21 post; 46 receiptless charges + 5 matched charges move; 24 join a Criss posting, 24 agree, 0 disagree. Before-score 38/120 (rules 22/23, model 16/97), map answers 33 agree 33.
- The `zoho-books-24mo.json` in the main clone's gitignored context was overwritten by my `--zoho` + `--pull-zoho` misuse and restored 2026-09-27 by an owner-approved read-only re-pull: EXPENSES ONLY (2,357 vs the original 2,355; Holding's 1 missing because settings gives GmbH and Holding one org id; the 1,179 bills are NOT restored: our Books token gets "not authorized" on /bills). Never pass `--zoho` together with `--pull-zoho`.
- SPA half `docs/lovable-identity-live-prompt.md`: Pending (not pasted).

## Owner decisions taken 2026-09-27 (each is a yes; do the readiness check before any write)
1. Item 115: YES, a Zoho-seeded rule may decide a receipt with readable lines, with the item-115 second read flagging disagreement. Code: `categorize._categorize_one_gl` `leads` (`not has_lines or (not judge_each_receipt and recall.taught_by_person)`) -> let a seeded rule lead too; the disagreement read is `_gl_learned` (`decision = DECISION_LEARNED_OVER_LINE`). Consequence the owner accepted: ~41 unsure receipts gain a rule answer at their NEXT categorization. Code change only; no live re-run.
2. Merge the two Lovable entries into 'Lovable Labs' (move 'Lovable Labs Incorporated' into its aliases). A live settings write: read-modify-write of `settings.merchants` (keep every other entry verbatim, including OpenAI/Anthropic `accounts` + `accounts_locked`), readiness check first (the merged list resolves all 30 live Lovable rows to the one entry; needs_account shows one Lovable line; no account changes), then PUT once and verify by GET. Do NOT re-ask about Lovable's accounts. Note Publish refuses merchant-list writes for Lovable (`owner_gated`); the settings PUT is the path.
3. Item 216's account-map write plan (44 merchants, 46 accounts, `context/expense-reconciliation/account-map-260925-write-plan.json`): NOT yet decided. Present the list once via AskUserQuestion, recommending single-account rows with 3+ postings first.

## Remaining queue, in order
1. #1477 is LIVE (merge `3c904cfe`, Fly v262, driven cold 2026-09-27). Start with step 6.
2. Step 6, line-sum check: `expenses[].line_sum_gap` (signed string, ABSENT within 0.05) + a review note; the export marks `(lines do not add up)` only where the receipt splits across accounts (only then do wrong shares change what posts); `_posting_amounts` (output/posting_common.py:61-75) keeps pro-rating. Predict the 35 rows (12/11/12) on fresh payloads first.
3. Item 115 (decision 1 above), route-level test through a receipt upload.
4. Lovable merge (decision 2), live write with readiness check.
5. Measure step 2 on all 314 charge descriptors under the live list AND the write-plan list; list every new descriptor hit; confirm the 12 live fuzzy hits unchanged. Known misses kept on purpose: 'Host Europe RN36953805 Koeln' (a city word), 'ZOHO_BOOKS', 'GOOGLE*PLAY' (no Google Play listed), the truncated Brazilian twins (a tie).
6. After deploy, check steps 4-5 per row on the live months (map: 57 rows on E500010-10, 76 + 28 on a parent) and report every row that changes what Criss sees.
7. Present the write plan (decision 3).

## How to work
Protocol `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md` (own worktree off origin/main, append-only on shared files, deploy only via deploy.py from a detached origin/main worktree, own browser session `recon-front3`). Scorer: `uv run tools/recon-categorization-score.py --fetch --pull-zoho --payload-dir C:\Users\neuma_p1qrsic\Repo\agentic-ops1\.scratch\recon-score-<date>-front3 --batch 50622baec444 --batch 074a7b8905d7 --batch 51a22ad72864` WITHOUT `--zoho`. No live writes on Criss's months beyond the owner-approved ones above; only corrections are memorized; the model suggests, a rule or a person decides; OpenAI key bills Dirk (no model re-run). Every fix: route-level test through its caller + `tools/regress_check.py`.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)

1. Measure YOUR session's context, not the machine's. `uv run tools/session_state.py --status` prints the most recently active session on the machine; trust its `context=` only when its `session=` matches the UUID in your scratchpad path. Otherwise read your own transcript: the last assistant record's `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens) in `~/.claude/projects/c--Users-neuma-p1qrsic-Repo-agentic-ops1/<your-session-uuid>.jsonl` (keep a small script for it in your scratchpad), or the per-session `[PRESSURE: ...]` advisory. On 2026-09-17 `--status` read a sibling's 474k while this session sat at 307k. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or deploy. A small backend item with tests, suite, deploy and live check cost about 45k on 2026-09-17 (item 102); a matcher item with before/after measurement cost about 225k (item 137, 173k to 396k); a two-builder PDF restructure is budgeted at 150-250k. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body; merge only on green and only when the item is actually done). Never stop half-deployed: if a merge landed, deploy it and verify it first. Close browser sessions and clear `tools/bg_watch.py` entries.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; write the checkpoint prose after `finalize`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: first line `/comd_resume brisken`; where it stands (what shipped this session with PR numbers and Fly version, what is in flight and why, what waits on the owner or Criss); the remaining queue in order with the exact code pointers and live evidence the next session needs; the "How to work" section; then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence, together with any Lovable prompt written this session, and append the same continuation text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on the owner or Criss (owner directive 2026-09-17).
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty and no new feedback note is open, do not write another prompt: say the loop is done and list what shipped and what waits on the owner or Criss.
``
