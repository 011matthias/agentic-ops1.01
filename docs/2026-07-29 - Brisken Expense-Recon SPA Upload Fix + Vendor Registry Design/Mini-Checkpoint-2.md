# Mini-Checkpoint: Brisken Expense-Recon SPA Upload Fix + Vendor Registry Design

**Date:** 2026-07-29
**Status:** Backend verified working; SPA upload broken (fix prompt delivered); vendor/categorization infra designed, not built
**Type:** mini

---

## Summary
Diagnosed why Criss can't upload receipts: the receipt-first backend works end-to-end (verified via direct API — 10 receipts → expenses → the card-driven Paid Through fired on the 2838 receipt), so the bug is entirely the Lovable folder-upload control (0 batches ever reached the backend). Delivered a Lovable fix prompt + a zip workaround, and designed a merchant-registry to make vendor naming + categorization consistent.

## What Was Done
- Extracted April ER-00215 receipts (37 scans) with the tool's own `render_receipt_pages` → `Downloads\ER-00215-receipts` / `-smoke10` (+ zips); identified the matching April 2838 statement (`Chase2838_Activity20260401_20260430_20260716.CSV`).
- **Verified the backend folder upload end-to-end via direct API** (batch `05d3db59b225`, label "AGENT-DIAG ER-00215 smoke", left in place as proof): multi-file `files` multipart → OCR job → 10 expenses; card fill confirmed (`VISA ...2838` → `CHASE VISA - 2838 - TRAVEL` [card]); the other 9 (Brazilian merchants, non-mapped cards) correctly "assign". `.zip` expansion confirmed in code (cap 80 files / 15 MB each).
- **Isolated the bug to the SPA**: `list-batches` was 0 before the test → no SPA upload ever reached the backend. Likely cause: `webkitRelativePath` used as the filename + a folder-only picker (the "Ordnername ist ungültig" error was a file selected in a folder picker).
- Delivered 3 Lovable prompts this session: month-first home (reconciliation as the month's closing step), the upload fix (multi-file/zip input, append each file as `files` basename, poll `/jobs/{id}` then load the batch), plus the earlier card-accounts editor + Paid-Through cell prompts.
- Designed the **merchant-registry** infrastructure for vendor naming + categorization (canonical vendor + default category/account; seeded from the by-month bundles; editable in the SPA like card_accounts; auto-grown from the Phase-6 `field_correction`/`merchant_entity` learning; consulted at `generate_expenses`, LLM fills gaps). Trigger: OCR returned "Mega Center" as 4 different vendor strings. Spec/prompt delivered; NOT built.

## Current Status
Card-driven Paid Through live + verified on real data (Fly v52). Criss remains blocked on uploading via the SPA until the Lovable folder-upload fix ships (backend is confirmed correct). Vendor/categorization: merchant-registry approach chosen and spec'd, unbuilt. brisken comms current (0d); p1 platform ops section unknown in `infrastructure.yaml`.

## Next Steps
1. Fix the SPA receipt upload in Lovable from the delivered prompt (multi-file + drag-drop + zip; append each file as `files` using the basename; poll `/jobs/{id}`). Backend needs no change.
2. Build the merchant-registry infra from the delivered spec; cheapest first win = the clean-name extraction-prompt tweak (strip `LTDA`/`SA`/`GmbH`).
3. Delete the `AGENT-DIAG` diagnostic batch once it is no longer needed as proof.
4. Owner-gated, unchanged: send Criss the SPA URL + operator code; `EXPENSE_COLUMNS` / Books-write consent; `zoho.post` stays off.

## Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `.../expense-reconciliation/src/expense_recon/web/app.py` (`POST /api/expense-batches` contract: `files` multipart, `{batch_id, job_id}`, poll `/jobs/{id}`)
- `.../expense-reconciliation/src/expense_recon/web/service.py` (`create_expense_batch`, `generate_expenses`, the `field_correction` learning path for the registry wiring)
