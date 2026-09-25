# Mini-Checkpoint: Expense-Recon Case 9 Build 2

**Date:** 2026-09-25
**Status:** Shipped and deployed (PR #1367, merge `191c7f8a`, Fly v231); rows move at each month's next natural re-match
**Type:** mini

---

## Summary
Item 204 step 6 (owner D5) shipped. A receipt with no card evidence is no longer booked to a charge whose merchant words disagree (`_vendor_score` < 0.5). The pair keeps its assignment, so it is still the top candidate and one click confirms it. It waits in review with `review_code` `no_card_vendor_disagrees` and lends no card.

## What Was Done
- `matching/deterministic.py`: knob `no_card_vendor_guard` (default on, mirrored in `config/match-tuning.json`), `NO_CARD_VENDOR_REVIEW`, `NO_CARD_VENDOR_FLOOR`, public `no_card_vendor_disagrees()`. The routing sits at assignment time (pass 2), so no other rule or threshold moves.
- `cli._apply_judgment`: the FX judge now judges FX pairs only (owner ruling asked in session via AskUserQuestion; the file was outside the build's ownership list). Without this, every re-match rebuilt the guarded pair as an LLM FX verdict: `review_code` and reason lost, `match_type` rewritten to `fx_judgment`, and the pair unbound whenever the model said no.
- Tests: new `tests/test_no_card_vendor_guard_c9.py` (11 tests: matcher, judgment layer, route-level on `/api/runs/{id}` and `/api/expense-batches/{id}`). Items 133 and 197 tests updated where they pinned the old booking. The bulk-confirm test now uses a receipt that prints its card; the 197 fixture now uses "Anthropic, PBC".
- Regress, caller-level, both TEST BITES: `if guarded:` (6 red, including the route test) and the cli pass-through (2 red).
- Suite on the final merged tree: 3551 passed, 2 skipped.
- Measured on a fresh DB copy (`recon-match-attribution.py --live`, July + August with labels), before (`5811aca1`) vs after. Four moves, all into review:
  - August `0025` Lovable on BASE44 50.00: wrong to review. Wrong bookings go 1 to 0.
  - July `0034` Erste Fracht on HOTEL AM TIERGARTEN: to review.
  - July `0066` Mega Center on BEATRYZ: to review.
  - August `0033` E A LOCACOES: to review.
  - Clean right unchanged at 26 / 6. Six bundles unchanged (70/95, 0 wrong, 76.0). CI fixtures unchanged, so `expected.json` and the deploy baseline did not move.
- Live read of every month (GET only) found exactly the five predicted rows (the four above plus April MARIA BETAN 24.59), all still `pending` in reconciled; September has none.
- Docs:
  - `docs/api-contract.md` section appended.
  - Lovable prompt `docs/lovable-no-card-vendor-guard-prompt.md` added, with a Not-applied row in `PROMPT-STATUS.md`.
  - Backlog paragraph `**Build 2 (step 6)**` at the end of item 204, plus Shipped row 125.
  - Status-file paragraph.

## What Did NOT Work (and why)
- **Routing into `judgment_required` alone, as the build prompt designed it:** `cli._apply_judgment` re-judged every entry there as FX. The route test showed `match_type: fx_judgment` with the reason "FX judgment: likely same purchase (p=0.90). ~1.00 USD from 50.00 USD" and no `review_code`. It needed the owner-approved pass-through.
- **`flyctl ssh sftp get ... "$SP\\$f"` in a loop:** the backslash escaped the `$`, so the file landed as a literal `scratchpad$f` and the second get refused to overwrite it. Use one call per file with a single-quoted Windows target.

## Current Status
Deployed on Fly v231 (`/healthz` commit `191c7f8a`). No live row has moved yet: each moves at its month's next natural re-match (Criss's own action), and no agent re-match was run. The SPA has no renderer for the new code until the Lovable prompt is pasted; the rows will show the applied `wb.noCardOnReceipt` line in review. The browser drive was skipped per the build prompt, because no row has moved yet. Watch item: live Anthropic invoices ("Anthropic, PBC") score 52% against "ANTHROPIC* CLAUDE SUB", just above the floor.

## Next Steps
1. Owner: paste `docs/lovable-no-card-vendor-guard-prompt.md` into Lovable. After the publish, run `tools/lovable-bundle-audit.py` and move the PROMPT-STATUS row to Applied.
2. After the next natural re-match of August (or July / April), read `GET /api/runs/074a7b8905d7`. BASE44 50.00 should sit in `review` with `review_code` `no_card_vendor_disagrees` and the Lovable receipt `card: null`. Drive `expenses.brisken.com` with `agent-browser --session recon-c9-2` on that row.
3. The rest of the case-9 round runs in its own sessions: build 3 (cross-month flow-back), build 4 (billing-account memory), build 5 (status fields). Build 1 shipped (#1362).
4. Owner / Criss: D2 (weekly Chase export, view access to 9693 / 1176) and D3 (load the 9693 history and the April-June 3876 / 0340 sheets).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 204, the "Build 2 (step 6)" paragraph; Shipped row 125)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_no_card_vendor_guard_c9.py`

Loop state: this session's queue (build 2) is empty and no new feedback note is open, so there is no continuation prompt (SESSION LOOP step 9).
