# Mini-Checkpoint: Brisken Recon Categorization Score

**Date:** 2026-09-25
**Status:** Build 5 (item 216 cause 5) shipped, PR #1435 merged `5d93289c`; nothing to deploy
**Type:** mini

---

## Summary
`tools/recon-categorization-score.py` turns item 216's `measure.py` + `truth.py` into one command that scores the recon tool's accounts against Criss's Zoho postings by answer source. It reproduces the analysis exactly on the checkpoint's 03:29 UTC payloads and on today's live months: 135 joined, 21/97; strict 120, 19/87; open rows 1/23.

## What Was Done
- Tool: payload dir + Zoho pull in. Out: the screen-rule receipt baseline (55 engine refused / 5 partial / 35 intake on the GL months), receiptless charges beside the app's guess counter, a loose and a strict join, accuracy by source (non-code answers counted apart), open rows, amounts, and `merchants[].accounts` precision through the engine's own `MerchantRegistry.resolve` + `company_account`. Writes JSON + markdown with the join constants. `--fetch` reads each endpoint once, 15 s apart, 45 s brake; the token is never written.
- Live fetch at 05:06 UTC: 11 reads, each under 1 s, no writes. The numbers are identical to the 03:29 pull.
- 21 tests (`tools/tests/test_recon_categorization_score.py`). regress_check on six rules (copy exclusion, strict rule, REVIEW fold, open split, one-to-one, 3-day window): each mutation turns a named test red. INDEX row, backlog Shipped row 135, and status element row updated.

## What Did NOT Work (and why)
- **`VIRTUAL_ENV` leak made the CI-shaped local run meaningless:** the shell exports `VIRTUAL_ENV` pointing at the main clone's module `.venv`. `uv run --no-project` then puts that venv's site-packages (rapidfuzz) and the main clone's `src` on `sys.path`, so a test that CI skips passed locally. The fix is to run the CI shape under `env -u VIRTUAL_ENV -u PYTHONPATH`. The tool itself inserts its own checkout's `src` at `sys.path[0]`, so scoring is unaffected.
- **`gh pr checks --watch` into a file, and a background `gh` poll loop:** both exited 0 while checks were still pending (the watch log held only the first snapshot; the detached loop's `gh` printed nothing). `gh run watch <run-id> --exit-status` in the foreground was the reliable wait.
- **First join-window regress (3 → 5 days) stayed green:** the fixture had no posting 4 days out. A 4-day row was added, and it now bites.

## Current Status
On main. The account map lever reports "no map" today (`merchants[].accounts` empty in settings). A scratch-only probe (never written live) showed the bank descriptor `LOVABLE` resolves to the registry entry `Lovable Labs` (no map), not `Lovable Labs Incorporated`, so a map on the latter would not reach those charges. That is item 216's cause 3 (identity keyed on raw text), visible in the instrument. brisken ops status: platform unknown plan; comms-log none.

## Next Steps
1. Rerun the score after each structural build lands and after the Zoho re-pull once Criss books August and September: `uv run tools/recon-categorization-score.py --fetch --payload-dir <scratch> --batch 50622baec444 --batch 074a7b8905d7 --batch 51a22ad72864`.
2. Candidate, not built: run the score in CI or in the recon deploy gate against a committed synthetic payload. That needs rapidfuzz in the tools job, or the lever test moved to the module's job, so the map-lever test stops skipping in CI.
3. Build B (account map) and Build D (merchant identity): check the `Lovable Labs` vs `Lovable Labs Incorporated` split before writing any map; Lovable stays owner-gated.

## Files to Read First
- `tools/recon-categorization-score.py` (docstring: usage, constants)
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 216 and Shipped row 135
