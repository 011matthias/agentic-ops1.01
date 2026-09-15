# Mini-Checkpoint: Expense-Recon Item 64

**Date:** 2026-09-15
**Status:** Shipped (PR #830, merge 92552b82, Fly v122). Lovable half pending the owner's paste.
**Type:** mini

---

## Summary

Backlog item 64's two parser gaps are closed: an unrecognised statement `Type` label now keeps the sign the export printed instead of being read as a purchase, and each `statements[]` entry records the column map and card currency it was read with so the re-read reuses them. Both gaps are real defects that are inert on today's live data, which the live reads established before any code was written.

## What Was Done

- **Live first, and it moved the design.** Both months hold exactly ONE statement whose `file` still matches `config.statement.path`, so the re-read already reuses its map today; and both workbooks carry only `Sale` (109/111), `Payment` (1 each) and one August `Fee`, all handled as intended. Neither gap reproduces in production, so both fixtures are constructed.
- **(a) The constraint that shaped the fix.** "Unrecognised" could not mean "not a credit": `Sale` and `Fee` are not credits either, and treating those as unknown would flip all 109 negative August purchases into credits, breaking exactly the two live months. `DEBIT_TYPE_VALUES` + `is_known_type` make it "in neither vocabulary"; `is_credit_type` is unchanged. One `info`-severity `parse_issues` note per distinct unknown label with its row count, capped at ten plus a summary for a Type column mapped onto the wrong source column.
- **(b) `statements[]` records how it was read.** `column_map` + `card_currency`, parallel and absent on older entries, reused by `reread_statements`. The old `config.statement` paths stay as ordered fallbacks, and a re-read re-records both, so a month repairs its own record.
- **Rule 5 checked before the enum grew, not after.** The published bundle's only `parse_issues` severity consumer tests `severity === "error"` and renders `message` otherwise, so `"info"` degrades to plain text as `"warning"` already does. No parallel `severity_label` needed. A hand-rolled crawler returned 5 chunks / 655 KB with every control ABSENT; only `tools/lovable-bundle-audit.py`'s 48 files / 975 KB was believed.
- **Verified.** Module suite 1550 to 1557 on the branch, 1647 after three siblings merged in. Three regress proofs RED first. Deployed v122 and confirmed on the running container with the same probe that answered False before the deploy and True after.

## Current Status

Live at v122. The live months' entries predate both fields, so the API read on them correctly shows both ABSENT; the deployed-code probe is what proves the change is live, not the payload. Both workbench routes browser-driven on August: statements table renders its five columns, 64 "No receipt found" labels (the same legitimate count as the item-60 session) and zero other fallback strings.

**Finding worth keeping, found during the drive.** Both months' stored column maps have NO `type` key, which is why the live parse note still reads "sign convention inferred: 110 of 111 amounts are negative". The maps were captured 2026-09-10, one day before `guess_column_map` learned Chase's `Type` column (#805), and the 09-11 re-read faithfully reused them. The inference reaches the right answer, so no money is wrong. But a re-read of these months now would freeze the type-less map onto their entries, which argues for a re-upload with the Type column mapped rather than a plain re-read if anyone wants the Type path exercised on real data.

## Next Steps

1. Owner pastes `docs/lovable-statement-record-prompt.md`; then re-run `uv run tools/lovable-bundle-audit.py` with `card_currency` / `column_map` / `stm.col.readAs` in `NEW` and move the PROMPT-STATUS row to Applied.
2. Decide whether July and August should be re-uploaded with the `Type` column mapped. Not urgent; a production mutation on Criss's data, so it needs a per-action yes.
3. Items 62, 63, 66, 67, 68 and 17 remain in the parallel round.

## Files to Read First

- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` ("How an upload was read")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/_common.py` (`DEBIT_TYPE_VALUES`, `unknown_type_issues`)
- `workspace/clients/brisken/automations/expense-reconciliation/tests/test_statement_parser_gaps.py`
- `workspace/clients/brisken/status/p1-improvement-backlog.md` (Shipped row 38)
