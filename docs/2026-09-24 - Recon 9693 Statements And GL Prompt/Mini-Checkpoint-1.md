# Mini-Checkpoint: Recon 9693 Statements And GL Prompt

**Date:** 2026-09-24
**Status:** Brisken p1 recon. Phase 1 SPA prompt written (NOT pasted, urgent); 9693 statement load owner-approved but blocked on OpenAI credits
**Type:** mini

---

## Summary

The missing card statements were read app-only from SharePoint, and the owner ordered them loaded. The load is blocked because the recon app's OpenAI key ran out of credits. Writing the Phase 1 Lovable prompt against the live API exposed a backend gap. It was fixed, merged and deployed as Fly `b8cb470a`, and the prompt now waits on the owner's paste.

## What Was Done

- **Statements (Graph app-only, read).** The ADMIN CLOUD SERVICES LLC site, under `10_Finance/10_BANKING/CHASE Brisken`, holds all of card 9693's 2026 statements up to the `0904` cycle.
  - 8311 and 6013 are dormant rather than missing: their cycles carry fees only and no receipts.
  - 0113 (the Apple Card) appears in no site or OneDrive the app can search. The tenant search did find the known 9693 and 8311 files, so the instrument can see statements.
  - Local copies are in the gitignored `context/expense-reconciliation/statements/`. The 8311 and 6013 "ALL Activity" workbooks are password-encrypted.
- **PR #1318.** Records Dirk's ruling that the six SPOT-CHECK accounts stay N (architecture doc and status file), plus the statement map in backlog item 108.
- **PR #1323, deployed as Fly `b8cb470a`** (`/healthz` commit verified). The live GL engine had been out since the item 192 deploy (`45d4c494`, 15:02 UTC), and two things were missing:
  - `gl_accounts` was keyed by the settings registry's long names (`Brisken Corp Services, LLC`), while rows carry the provisioning labels (`Corporate Services`), so no row could find its account list. It now uses the engine's own entity map: the batch's frozen `gl_entity_orgs` on month views, and settings plus provisioning elsewhere.
  - Nothing said which months are GL. `category_vocabulary` (`gl` / `buckets`) is now on both month views.
  - Refusal codes and vocabulary values are pinned as literals, and the contract probe collapses `gl_accounts` entity keys to `*`.
  - The PR also adds `docs/lovable-gl-accounts-prompt.md`, its PROMPT-STATUS row and the api-contract section.
  - Tests: 4 route-level tests, with every wiring point regress-checked green, then red, then green. The full suite ran 3307 passed / 2 skipped, and CI was green after one re-run of a wall-clock flake (`test_drop_speed_item_148`, 0.84s against 0.7s; 10/10 locally three times).
- **Live read after deploy.** August and September report `buckets`, and `gl_accounts` holds `Corporate Services` / `Cloud Services` / `Consulting`. A headless Chrome drive of the published August page (session token, render only) showed bucket names, no GL code, no fallback strings and zero non-GET requests.
- **9693 load.**
  - The owner answered "you load them", then "insert any bank statements you need".
  - Plan: `0804` into August and `0904` into September. Fly snapshot `vs_kKOxkR0mZ9lIKY3vmJ845D9` was taken first.
  - The August attach job `99d3f5629717` died at stage `judging` with OpenAI 429 `credit_balance_exhausted`. August re-reads identical to its baseline, so the attach is atomic and wrote nothing. September was not attempted.

## What Did NOT Work (and why)

- **Attaching 9693's `0804` statement to August:** the job errors at stage `judging` with OpenAI 429 `credit_balance_exhausted`. A statement attach cannot degrade to deterministic matching without the LLM.
- **Playwright MCP for the consumer drive:** it is wired to the owner's Edge on CDP :9222 and timed out after 30s. The fix was a headless `channel="chrome"` Python Playwright script with its own browser.
- **First `flyctl deploy` without `--build-arg GIT_COMMIT`:** `/healthz` would have reported an empty commit. Redeployed with the argument (the recipe in `docs/operating.md`, not memory's shorter one).
- **Rebase plus force-push to refresh a conflicting PR:** force-push is on the gated floor. Merging main into the branch gave a plain fast-forward push instead.

## Current Status

- **Live:** Fly `b8cb470a`. Every month created after 2026-09-24 15:02 UTC is a GL month. The published SPA shows such a month's categories as blank and offers the eight buckets, which the server accepts. The prompt has to be published before the next month is created.
- **Intake is parking mail.** Since 16:21 UTC an inbound mail sits as `held_body_only` with the same 429, and every receipt that arrives will park until the key has credit.
- **Waiting on the owner:**
  - OpenAI top-up on Dirk's key (vault "OpenAI Brisken").
  - The Lovable paste and Publish.
- **Excel watcher `b05umcdou`** is still waiting on the review copy (`~$` lock open in Excel). It deletes the copy only if its sha is unchanged.

## Next Steps

1. **After the OpenAI key has credit:**
   - Re-ingest the held mail.
   - Attach `20260804-statements-9693-.pdf` to August `074a7b8905d7`, then `20260904-statements-9693-.pdf` to September `51a22ad72864`, one after the other.
   - Form fields: `account_id=card-9693`, `account_card_currency=USD`.
   - Poll `/jobs/{id}`. Expect only a `statement_period_overlap` advisory, and no `entity_mismatch`.
   - Verify rows +21 / +32, the 9693 rows as Cloud Services, and August's 2838 counts unchanged.
   - Never attach a file to two months, and never run `statements/reread` on a month holding a PDF (it re-stamps the entity to `"card"`).
2. **After the owner publishes the GL prompt:**
   - Run the bundle audit for `category_vocabulary`, `gl_accounts`, `category_refused` and `gl.refusal.`.
   - Drive July cold: it must be unchanged.
   - Drive a `TEST - GL drive` batch for the prompt's section 6 rows, in EN and PT, then delete the batch.
   - Mark the prompt applied.
3. **Backlog candidates** (recorded under item 108, not built): the reread entity re-stamp, and the attach and intake failing closed on an exhausted LLM key.
4. **Waiting on others:**
   - Dirk: export the 0113 Apple Card statements from Wallet or card.apple.com.
   - Card 3645's `zoho_account` (item 172).

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-gl-accounts-prompt.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 108, 2026-09-24 evening paragraph)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("GL vocabulary (Phase 1)")
