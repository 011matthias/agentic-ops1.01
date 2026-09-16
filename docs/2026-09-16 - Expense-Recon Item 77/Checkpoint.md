# Checkpoint: Expense-Recon Item 77

**Date:** 2026-09-16
**Status:** Item 77 shipped and deployed (Fly v137); live fix applied on owner yes; SPA prompt pending paste; item 82 gate open

---

## Summary

This session was opened to build item 82 (the ECB monthly reference rate) and stopped at its gate, because neither item 77 nor item 81 had shipped. On "unblock it for me", item 81 was left to its live sibling session (it merged as #903), and item 77 was built, measured, shipped, deployed, and applied to Criss's live data.

---

## What Was Done This Session

### Gate and scope
1. Checked `origin/main`. Item 77 was unclaimed (no worktree, branch or PR). Item 81 was mid-build in `agentic-ops1-item81`, with files written 2 minutes before the check, so it was left alone.

### Measurement (before any prompt change shipped)
1. Pulled all 129 receipts stored on the six live batches off the Fly volume.
2. Re-read them without the cache on the production models, two runs per arm. The arms were:
   - the `origin/main` prompt (baseline);
   - locale rule plus the fields beside `reference`;
   - fields listed last in the instructions;
   - fields in the response schema only;
   - a one-word wording change as a no-op control.
3. A one-call transcription probe on Criss's receipt returned `04/01/26` for a slip that prints `04/07/26`.

### Build: PR #910 (merge `2b2f1755`)
1. `expenses[].month_move {month, label, batch_id?}` plus `summary.n_month_moves`. The offer appears only on a reviewer-typed date (or typed-in expense) outside the batch window, on company months.
2. `POST /api/runs/{id}/expenses/{doc}/move`:
   - The target is the batch month routing picks, created empty under `_MATERIALIZE_LOCK` when absent (`created_by: "move"`, with a pooled-mail claim after).
   - It carries the baseline receipt, the file, header and category edits, and provenance.
   - Identical bytes already in the target are not added twice.
   - The source row becomes a soft delete whose payload names the target, and its claims are released.
   - Both months re-match.
3. Amendment fields `time` / `invoice_number` / `receipt_number` flow ExtractedReceipt → Receipt → snapshot → `expenses[]` (absent-or-string). They are asked for in `_EXTRACT_SCHEMA` only; the instruction text is byte-identical to `origin/main` (checked programmatically) and the fingerprint bumped.
4. `docs/api-contract.md` section, `docs/lovable-month-move-prompt.md`, and a PROMPT-STATUS "Not applied" row.
5. Suite: 1887 → 1900 passed / 2 skipped. Four `regress_check.py` proofs bit: offer wiring 8 red, edits carried 2, target re-match 1, stored time 3.

### Ship, deploy, verify
1. Rebase hit append conflicts in four shared files (siblings 73/80/81 landed meanwhile); both sides kept, suite re-run.
2. CI green, merged, deployed Fly v137 from a detached `origin/main` worktree after a `fly.toml` parity check.
3. API read on all six months: January was the only one with an offer (naming July `50622baec444`); none returned null.
4. SPA drive: `agent-browser --session recon-item77` from a cold login rendered January's row with no fallback. The offer renderer doesn't exist yet.

### Live fix (owner yes via AskUserQuestion)
1. Readiness read, then one POST moved the Parada receipt January → July.
2. It settled `MP *PARADAOBRIGAT` USD 6.20 as `fx_reference` 0.99 (32.00 BRL × 0.192448 = 6.16, +0.68%). Field diff: exactly one July row changed, `judgments_new` 0. January is empty and kept.
3. PR #913 recorded it; the mini-checkpoint shipped as #915.

---

## Key Decisions Made

### Build 77, do not take over 81
- **Choice:** Build the unclaimed item and leave the in-flight one to its session.
- **Rationale:** 81's worktree had uncommitted writes minutes old. Taking it over would have collided with a live session, and 81 shipped on its own within the hour.

### The locale half is not built
- **Choice:** Close the locale-prior half with evidence instead of a prompt rule.
- **Rationale:**
  - The reported misread is a glyph (7 seen as 1), and the model already reads day-first.
  - The locale rule moved 0 of 129 dates.
  - Of the 65 dates with a ground-truth proxy, the 4 that disagree are one glyph misread and three correctly read printed invoice dates. None is a day/month swap.

### Amendment fields in the response schema only
- **Choice:** Schema properties with `description`; instruction text untouched.
- **Rationale:**
  - A one-word edit alone moves 12 of 129 stable readings.
  - Fields in the instructions moved 39–41 readings, including a Microsoft invoice re-read as `statement` (it would be quarantined) and Amazon.de re-read as Yubico (breaks the AMAZON match).
  - Schema-only moved 31, with nothing consequential: no date, total, currency, document type, or card that resolves.

### Offer only on typed dates; the move never deletes the source month
- **Choice:** A machine reading outside the window stays `date_outside_period`. An emptied month is kept.
- **Rationale:** Moving on a reading the guard distrusts would misfile twice. Deleting a month is a typed-confirm owner action, not a side effect.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/llm/client.py` | edit | 3 schema fields + `_time_hhmm` parser |
| `.../matching/types.py`, `.../web/serialize.py`, `.../ingest/receipts_folder.py` | edit | carry `detected_time` / `invoice_number` / `receipt_number` |
| `.../web/service.py` | append | `month_move_for_row`, `_month_move_source`, `move_expense_to_month`; offer + fields in `build_expense_view` |
| `.../web/app.py` | edit | `POST .../move`; `month_batch` lookup in `_expense_view` |
| `.../tests/test_month_move.py` | new | 12 route-level tests |
| `.../tests/test_view_contract.py` | append | absent-or-typed test |
| `.../docs/api-contract.md`, `lovable-month-move-prompt.md`, `PROMPT-STATUS.md` | append/new | contract, SPA prompt, pending row |
| `workspace/clients/brisken/status/p1-improvement-backlog.md` | edit | item 77 SHIPPED marker, Shipped row 49, live move |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | append | element row, deploy + live move |
| memory `project_brisken_expense_recon_usability_loop.md`, `MEMORY.md` | edit | item 77 findings, prompt-edit trap |

Paths under `automations/` are `workspace/clients/brisken/automations/...`.

---

## Current Status

- Backend is live on v137. The move offer is invisible to Criss until `docs/lovable-month-move-prompt.md` is pasted and published.
- "January 2026" (`4ceaeb461386`) exists with 0 expenses. No live month carries an offer now.
- Items 77 (#910) and 81 (#903) are on `origin/main`, so item 82's gate is open.
- Ops status (brisken): unknown plan, `infrastructure.yaml` has no platform section for the FastAPI app.
- `status/` flags two stale p2 files (`p2-product-decks.md` 55d, `p2-targeting.md` 56d). They are outside this session's scope and were left to the p2 workstream.

---

## Next Steps

1. Item 82 (ECB monthly reference rate) in its own session under PARALLEL-ROUND-PROTOCOL, using the owner's original item-82 prompt.
2. Owner pastes `lovable-month-move-prompt.md` (after `lovable-month-views-prompt.md` if still unpasted). Then run `tools/lovable-bundle-audit.py` for `month_move`, `n_month_moves`, `expx.review.monthMove`.
3. Build the pending consumer-gate fix: treat a tool response that was moved to the background at the harness timeout as not observed, with a case in `tools/tests/test_deploy_consumer_gate.py`. It has hit three sessions today.
4. Owner call: delete the empty "January 2026" month or keep it.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/PARALLEL-ROUND-PROTOCOL.md`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 82 (and item 77 / Shipped row 49 for the prompt-measurement finding)
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md`, sections "A corrected date moves the receipt" and item 81's `fx` fields

### Open Questions
- Delete the empty January 2026 month?
- Does item 82's month keying by receipt date need `invoice_number`/`time`? (No: they are not matcher inputs; noted so nobody re-derives it.)

### Working Notes
- **Prompt A/B harness** (scratchpad, not committed). It recreates in minutes:
  - Pull receipts: `tar czf /tmp/x.tgz <run>/receipts` over `flyctl ssh console -C`, then `flyctl ssh sftp get` with `MSYS_NO_PATHCONV=1`, then delete the tarball in the container.
  - Prepare PDF text and images serially; pypdfium2 in threads `abort()`s with exit 3 and no traceback.
  - Parallelize only `client.extract_receipt` calls.
  - Patch `_EXTRACT_INSTRUCTIONS` / `_EXTRACT_SCHEMA` in-process to run variants side by side.
  - Cost is about $0.02 per 129-receipt run.
- **Perturbation floor:** a one-word instruction edit moves ~12/129 readings on gpt-4o-mini temp 0 (vendor spellings, references, card hints). Any future extraction-prompt change must be judged against that floor, not against zero.
- Google invoices print the billing account `7696-8032-2544`, which the extractor offers as `card_last4` (2544 or 7696). No registered card matches, so it is inert, but it is noise.
- CRLF shared docs (`api-contract.md`, `PROMPT-STATUS.md`, both status files): multi-line `Edit` anchors fail. Append with a byte-level Python write.
- Rebase conflicts: enumerate with `git diff --name-only --diff-filter=U`. A `git status | head` cut hid `test_view_contract.py` and cost one suite run.

### Reference Materials
- PRs #910, #913, #915; Fly releases v137 (item 77), v138 (item 74 sibling)
- `docs/2026-09-16 - Expense-Recon Item 77/Mini-Checkpoint-1.md`

---

## How to Continue

Start item 82 with `/resume brisken`, then the owner's item-82 prompt. Its gate text ("item 77 shipped", "item 81 shipped") is now satisfied on `origin/main`. Step 1's simulation runs on v137+ code, which includes item 81's `reference_*` fields that 82 extends with source `ecb_month`.

---

## Strategic Feedback

### What Worked Well This Session
- Measuring the prompt with a no-op control arm. Without the 12-reading floor, variant C's 31 changed readings would have looked alarming. Without the per-field check, the owner's instruction to bundle the fields into the prompt would have shipped a change that quarantines a real Microsoft invoice on its next re-read.
- The live fix went through a read-only readiness pass first and a field-by-field diff after. The result was stated as "exactly one July row changed, 0 new judgments", not as "200 OK".

### Suggestions
- Build the deploy-consumer-gate timeout-background fix now as a small system PR. It is a one-condition change (response text says the command was moved to the background → not observed). Three sessions hit it today, and each relied on its own re-drive to avoid a false "consumer driven".

### System Health
- The parallel round held: four append conflicts on one rebase (siblings 73/80/81) resolved mechanically with both sides kept, and the suite count reconciled exactly (+13 = new tests).
- Autonomy: 2 human interventions ("unblock it for me", and the per-action yes the invasive gate requires for the live move).
