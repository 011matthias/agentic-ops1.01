# Mini-Checkpoint: Expense-Recon Item 239 Gemini Reader

**Date:** 2026-09-28
**Status:** Built and measured; switch merged, NOT live (Fly login on this machine is dead)
**Type:** mini

---

## Summary
Dirk's Gemini key now drives an optional receipt reader in the recon tool (backlog item 239). A blind A/B on 251 stored documents had Gemini 3.8 Flash beat the OpenAI readers, so `fly.toml` switches reading to Gemini; it goes live only once the `GEMINI_API_KEY` Fly secret is set and the app is deployed.

## What Was Done
- Scoped on 2026-09-27 (9-agent workflow `wf_ebece896-543`), then verified the key is on a billed project (`1Expense`, Tier 1 Prepay: Pro answers 200 since 2026-09-28; it was free-tier the day before). Owner ruled no rotation; every local copy of the key outside `context/.env` was redacted (37 in transcripts, one probe leftover `%TEMP%\vx.json` deleted), never in git.
- Step 1, PR #1533 (merge `f66f364b`): `llm/gemini.py` GeminiReader (stdlib REST, key in `x-goog-api-key`), hooked into `OpenAIClient.extract_receipt` behind `EXPENSE_RECON_GEMINI_READS` = `images` / `all` or `cfg.llm.receipt_reader`; same prompt, fences, schema and cache; any failure falls back to OpenAI; priced; `/healthz.receipt_reader`; doctor check. 26 tests, suite 4144 passed / 2 skipped, two regress proofs TEST BITES.
- Step 2, A/B on the 251 documents of the 2026-09-25 backup (item 223's inputs and its two stored OpenAI passes): Flash x2 (USD 3.82), Pro x1 on the 39 disputed docs (USD 1.16), four blind checker agents on the 46 stable disagreements. Key fields: Gemini right 15, OpenAI 3 (2 both wrong, 1 unreadable); text-layer PDFs 8 to 0; document_kind OpenAI 5, Gemini 2. Full table in backlog item 239.
- Step 3, PR #1534 (merge `73e2fec8`): `fly.toml [env] EXPENSE_RECON_GEMINI_READS = "all"`.

## What Did NOT Work (and why)
- **Deploying either merge:** `flyctl auth whoami` = "no access token available" in Git Bash and PowerShell although `~/.fly/config.yml` holds a token (rewritten 10:27); the token is rejected, so no secret set and no deploy. Live is still `e38e29e7` with no `receipt_reader` on `/healthz`.
- **`generationConfig.responseFormat` with `mimeType: "application/json"`:** HTTP 400 on 3.8 Flash and 3.1 Pro; the enum spelling `APPLICATION_JSON` works (and `responseJsonSchema` is deprecated).
- **First key sweep:** `grep` over `Repo` timed out silently inside a 500 s `timeout` and returned nothing; the `.env` positive control exposed it. The second try failed because `rg` is a shell function `timeout` cannot run; use the VS Code `rg.exe` path.
- **Costing Flash from the one-receipt probe:** estimated USD 1.25 per 251-doc pass; real USD 1.98 (about 1,650 output tokens per doc with thinking), so Pro was cut to the disputed documents.

## Current Status
Main carries the reader and the switch. Production is unchanged: OpenAI reads every receipt until the secret exists and a deploy lands. brisken ops status: platform unknown plan (pre-flight). Worktree `agentic-ops1-gemini` (branch `client/brisken/p1-gemini-switch-on`, merged) holds the A/B harness in `.scratch/ab239/` and is kept until the switch is live.

## Next Steps
1. Owner: `flyctl auth login` (matneumann07@gmail.com).
2. Then set the secret without printing it (read `BRISKEN_GEMINI_API_KEY` from `workspace/clients/brisken/context/.env` into a variable, `flyctl secrets set GEMINI_API_KEY=... -a brisken-expense-recon --stage`), deploy `origin/main` via `deploy.py` from a detached worktree, and verify `/healthz.receipt_reader` = gemini-3.8-flash, reads all, `key_set: true`.
3. Watch the first arrivals after the switch (logs name any receipt Gemini could not read) and the duplicate groups of the next month with an invoice + receipt pair (Gemini labels charge confirmations `document_kind: invoice`).
4. Remove worktrees `agentic-ops1-gemini` and this checkpoint's once live.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 239
- `workspace/clients/brisken/automations/expense-reconciliation/docs/operating.md` "Switch the receipt reader"
- memory `project_brisken_recon_gemini_receipt_reader_scope.md`
