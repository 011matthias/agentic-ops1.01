# Mini-Checkpoint: Expense-Recon Front 2 Step 7 Private No Company

**Date:** 2026-09-28
**Status:** Item 220 step 7 shipped, deployed (Fly v274) and verified live; front 2's queue is empty
**Type:** mini

---

## Summary
A confirmed-private receipt with no company no longer tells Criss to "Set the company": the grid restates the engine's `entity_missing` refusal as `private_no_company` with its own sentence, at read time, moving no box or count. Live exactly as predicted (July 0028 Brauhaus Kühler Krug, September 0024 DB Fernverkehr AG).

## What Was Done
- PR #1525 (merge `f1d7255c`): `service.private_no_company_review`, appended at the end of `service.py` and wired in `build_expense_view` right after `_expense_review`; same `pick` state and `category_refused` code. `tests/test_private_no_company_item220.py` (4, route-level through the grid: row flag, private card list, undo, private row showing a company keeps the engine verdict). `tools/regress_check.py`: TEST BITES (unwired: 3 failed / 1 passed). Module suite 4094 passed / 2 skipped / 7 failed, all 7 the known local-only `test_smtp_starttls.py`; CI all green. API contract section, `docs/lovable-private-no-company-prompt.md` (PT key only; the English sentence already renders through the `category_refused` fallback), PROMPT-STATUS Not-applied row, backlog Shipped row 157, item 220 heading marked SHIPPED steps 1-7.
- Predicted on fresh GETs by applying the branch's own function to every expense row: Jul 1 / Aug 0 / Sep 1. Deployed via `deploy.py` from a detached origin/main worktree (v274). After: the same two rows moved and only refusal + reason moved; no box, no summary key in any month; all three run payloads byte-identical. Cold English drive of `/expenses/{id}` (batch read once and replayed, 0 non-GET requests): September's DB Fernverkehr row shows the new sentence and "Set the company" is gone from the page. July shows the new sentence once and the old one twice, for the two Martino rows.
- Record PR #1528 (merge `f362feff`): PR number, release and live checks in backlog item 220 and the status row.

## What Did NOT Work (and why)
- **Importing item 206's `web` fixture by name into the new test module:** CI's Ruff step (the module's `src` and `tests` joined its scope on 2026-09-15) flagged six F811 redefinitions, because every test takes `web` as a parameter. Fixed with a local fixture built from item 206's `_app`. The usability-loop memory still says CI Ruff covers `tools` only, which is stale.
- **Asserting `needs_entity` as a non-private row's company ask in the fixture:** with the fixture's cards and no statement loaded, the ask reads `waits_for_statement` (item 204). The tests accept either.

## Current Status
Front 2 (receipts with nothing to land on, item 220) is done: steps 1-7 live. Fly v274 on `f1d7255c`. SPA prompt `docs/lovable-private-no-company-prompt.md` is not pasted, so PT readers see the English sentence on those two rows until it is. The platform line is unassessed (`platform: unknown plan`), and no comms log exists for Brisken.

## Next Steps
1. Owner: paste `docs/lovable-private-no-company-prompt.md`, then run `uv run tools/lovable-bundle-audit.py` and look for `gl.refusal.private_no_company`.
2. For siblings, found on this round's live read and not built by front 2:
   - July `0053` / `0067` MARTINO SUPERMERCADO print `VISA ...3876`, show Corporate Services through the card, and still carry `entity_missing` (posting-account side, the item-206 sweep lag).
   - September `0024`, private through the private card list, reads `charge_in_neighbouring_period` in `unmatched_receipts`, because `receipt_reason_code` has no private input. It is a label only: readiness counts already leave private receipts out.
3. Still open from earlier rounds: August 0008/0009 Lovable copies (front 4), `judge_unmatched` raw entity strings (front 5), September OPENAI 81.12 holding August's `0033` (matcher), SharePoint backup stale since 2026-09-25T03:35Z (ops), Holding `org_id` 696750461 vs the map's 813627567 (owner).

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (item 220, step 7 paragraphs)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/lovable-private-no-company-prompt.md`
- Harness: main clone `.scratch/front2-item220/` (`predict_step7.py`, `diff_step7.py`, `drive_step7.py`, `private_rows.py`; pulls `before-step7-2026-09-27`, `after-step7-2026-09-28`)
