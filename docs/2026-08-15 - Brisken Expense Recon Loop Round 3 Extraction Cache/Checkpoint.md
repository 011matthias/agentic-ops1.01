# Checkpoint: Brisken Expense Recon Loop Round 3 Extraction Cache

**Date:** 2026-08-15
**Status:** Shipped + deployed + verified (PR #536, Fly v59)

---

## Summary

Round 3 of the receipt-first usability loop: extraction cache ("same photo, same answer") plus CLI merchant-registry parity, shipped as PR #536 and deployed as Fly v59, with the fix verified at the output level (smoke10 run twice on the fixed code produced byte-identical CSVs; the second run made zero extraction calls).

---

## What Was Done This Session

### Evidence run (pre-fix)

1. Fresh baseline R4 on smoke10 against current main drifted vs the 2026-08-13 outputs on 8 of 9 rows, including a BRL→EUR currency flip (ERICK SPORT) and a 50.50→50.00 tax drift — so "money fields are stable run-to-run" did NOT hold across days, upgrading the defect from cosmetic text drift.

### Build (backlog items 1+2, one PR)

1. `llm/extraction_cache.py`: sqlite store of the RAW vision payload keyed sha256(prompt/schema fingerprint + model + document content); file name excluded from the key; parse stays live on hits; fail-open on every operation.
2. `OpenAIClient.extract_receipt` consults it; hits record no usage. On via `llm.extraction_cache_path` (config-dir relative, absolutized in `run()`) or env `EXPENSE_RECON_EXTRACTION_CACHE`; fly.toml sets `/data/extraction-cache.sqlite`.
3. `_build_cli_merchant_registry`: CLI expense runs build the web path's MerchantRegistry from `expense.merchants` / `expense.merchants_path` (loud ConfigError when configured-but-broken).
4. `zoho_expense_export` prefers `canonical_vendor` over raw OCR — the registry's one-spelling-per-merchant now reaches the exported CSV on web AND CLI (it previously reached only the grid display).
5. +20 tests (drift reproduced with cache off; one-API-call determinism; rebuild survival; model/prompt invalidation; parser-stays-live; fail-open; registry wiring incl. canonical-vendor e2e). Suite 1063 passed / 2 skipped.

### Ship + verify

1. PR #536 merged on green CI; Fly deploy v59 from the clean origin/main recon worktree; live checks: healthz 200, `/api/expense-batches` 401 (gated, not 404), `EXPENSE_RECON_EXTRACTION_CACHE` confirmed on the machine.
2. Output verification: R5/R6 double run byte-identical; cache holds exactly 10 rows, all written in run 1.

### Bookkeeping (in the same PR)

1. Backlog: items 1+2 → Shipped; open items renumbered; new watch-only item 4 (category flips on identical inputs — categorize calls are uncached).
2. Status file iter-3 row; loop runbook refreshed (post-cache state, R4/R5/R6 outputs, cache-delete trap, next target).
3. Memory `project_brisken_expense_recon_usability_loop` + MEMORY.md index updated post-deploy with v59.

---

## Key Decisions Made

### Cache the RAW payload, not the parsed result

- **Choice:** store the model's JSON string; re-parse through `_extraction_from_payload` on every hit.
- **Rationale:** parser fixes (whitelists, sentinel collapses like the #518 "null" fix) must apply to cached readings; caching parsed objects would fossilize old parser behavior.

### Exclude the file name from the cache key

- **Choice:** key on content + model + prompt/schema fingerprint only.
- **Rationale:** same photo, same answer regardless of what the file is called this month; the fingerprint auto-invalidates the store on any prompt or schema edit.

### Keep `_build_llm_client` single-arg; absolutize the cache path in `run()`

- **Choice:** after the first attempt (threading `config_dir` through the builder) broke 30 web tests that patch the builder with a 1-arg lambda, moved path resolution to `run()` and documented the seam constraint in code + tests.
- **Rationale:** the builder is a de-facto patch seam; its signature is part of the test contract.

### Extraction cache only — no classification cache yet

- **Choice:** scope held to the designed backlog item; category-flip risk recorded as watch-only backlog item 4.
- **Rationale:** the post-fix back-to-back pair was byte-identical including categories; learned/registry precedence already outranks the LLM for corrected merchants; build only if a flip is observed on cache-pinned inputs.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `...expense-reconciliation/src/expense_recon/llm/extraction_cache.py` | created | content-hash raw-payload store |
| `...expense-reconciliation/src/expense_recon/llm/client.py` | edited | cache consult in `extract_receipt`, fingerprint, constructor param |
| `...expense-reconciliation/src/expense_recon/cli.py` | edited | cache wiring + path absolutize in `run()`, `_build_cli_merchant_registry` |
| `...expense-reconciliation/src/expense_recon/output/zoho_expense_export.py` | edited | canonical vendor wins in CSV |
| `...expense-reconciliation/fly.toml` | edited | `EXPENSE_RECON_EXTRACTION_CACHE=/data/extraction-cache.sqlite` |
| `...expense-reconciliation/tests/test_extraction_cache.py` | created | 13 cache tests incl. drift repro |
| `...expense-reconciliation/tests/test_cli_merchant_registry_config.py` | created | 7 registry-wiring tests |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edited | Shipped rows, renumber, watch item 4 |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edited | iter-3 row |
| `workspace/clients/brisken/status/p1-recon-loop-prompt.md` | edited | next-round brief |
| `.scratch/criss-recon-runs/05d3db59b225/run.llm.json` | edited (untracked) | `extraction_cache_path` for local runs |

All tracked files merged to main in PR #536 (squash `daee1444`).

---

## Current Status

Live app at Fly v59 with the cache active; suite 1063/2 green; loop scorecard now has "same receipts → same vendor" done for re-runs (cross-month new photos remain the registry's job). Brisken platform ops status: unknown plan / unassessed per `infrastructure.yaml` (`pre` output) — this client runs FastAPI on Fly, no orchestrator platform section.

---

## Next Steps

1. Next loop iteration: backlog item 1 — set-aside files strip in the review screen (one backend override endpoint + a Lovable prompt for the owner; touches what Criss sees, so the UX framing needs the owner).
2. On the next diff: re-check category columns on cache-pinned inputs (backlog watch item 4).
3. For a prod-parity CLI run: pull live `settings["merchants"]` into a local JSON and point `expense.merchants_path` at it.
4. brisken comms-log is 8 days stale — log any recent Criss/Dirk conversations.
5. `status/p2-targeting.md` is stale (24d, different workstream) — bring current or delete in a p2 session.

---

## Context for Next Session

### Files to Read First

- `workspace/clients/brisken/status/p1-recon-loop-prompt.md` (the paste-in brief, refreshed this round)
- `workspace/clients/brisken/status/p1-improvement-backlog.md`

### Open Questions

- Split rows (one receipt → two accounts): fine for Criss or force one row? (backlog item 2, owner/Criss conversation)
- Should the seeded registry duplicates (MEGA CENTER/CENTRE, Fenix/Ki-Massa) be merged in the Merchants editor before the next quality run? (owner task, noted since 2026-08-07)

### Working Notes

- Pre-fix drift evidence preserved: `expenses-R4-PRECACHE.csv` vs `expenses-QUARANTINE-RUN3.csv` in `.scratch/criss-recon-runs/05d3db59b225/` (currency flip, tax drift, category flips). Post-fix identical pair: `expenses-R5-CACHED1.csv` / `expenses-R6-CACHED2.csv`; `extraction-cache.sqlite` beside them holds the 10 pinned readings (delete to force fresh).
- The failed first approach: widening `_build_llm_client(cfg, config_dir)` — 30 web tests patch it via `_patch_ocr` with `lambda cfg: (mock, None)`. Any future signature change there breaks them again.
- `flyctl` token auto-load trap did not fire this time, but the explicit `FLY_API_TOKEN` extraction from `~/.fly/config.yml` was used anyway (known gotcha).

### Reference Materials

- PR: <https://github.com/011matthias/agentic-ops1.01/pull/536>
- Memory: `project_brisken_expense_recon_usability_loop` (round-3 state incl. traps)

---

## How to Continue

Paste `workspace/clients/brisken/status/p1-recon-loop-prompt.md` into a fresh chat; it carries the full recipe, traps, and the current target.

---

## Strategic Feedback

### What Worked Well This Session

- Running the pre-fix baseline BEFORE building paid off twice: it upgraded the defect (currency/tax drift, not just text) and produced the exact evidence the drifting-fake regression tests then encoded.
- The backlog-file discipline (one ranked list, updated in the same PR) made target selection and bookkeeping near-zero-cost.

### Suggestions

- The `_patch_ocr` seam constraint existed only implicitly in 30 test files; it cost one full-suite iteration to discover. When touching any function that tests monkeypatch, grep `tests/` for the symbol first — cheap, and this repo's web tests patch seams heavily.

### System Health

- Autonomy: 0 human interventions (fully autonomous session); one Stop-hook B1 block on the closing checkpoint-offer, corrected by running the checkpoint.
- Gates: B1:1 B2:3 B3:1 skipped:0. The B3 moment worked as designed: the 30-failure diagnosis started from "my own change is the most likely cause" and landed in one traceback.
