# Mini-Checkpoint: Brisken Recon Item 218 Bills Path

**Date:** 2026-09-25
**Status:** Backend LIVE (PR #1444, Fly `a8a6809b`, driven cold); SPA prompt not pasted
**Type:** mini

---

## Summary
Build 4 of item 216 (cause 4): invoices paid by bank transfer leave the card queue for a Bills section inside their month, decided at read time. Three owner decisions taken first, on a measurement that overturned three premises of the brief.

## What Was Done
- Measured July/August/September once each (15 s apart) plus the five invoice files: only July carries bank-paid invoices; one of four names a wire in `payment_mode`; SAP and Redis are also card-charged every month (a supplier-name rule would be wrong); the Redis pair 0004/0070 DID group on IUS25300 and a reviewer ruled "Not a copy" (0070 is a past-due reminder); a settled-outside row still went into `expenses.csv`.
- Owner decisions (AskUserQuestion, all recommended): D1 Bills section in the month; D2 auto only on a stated bank method or Criss's settled-outside bank_transfer record, suggestion on printed bank details, person moves either way; D3 leave the 0070 ruling.
- Built via subagent, verified here: `src/expense_recon/payment_path.py`, `output/bills_csv.py`, effective settled-outside map threaded through `build_view`, `grid_card_chain`, exports and both PDFs; `payment_path` / `payment_path_source` / `bill_suggestion`; `n_bills` / `bills_by_ccy`; field PUT `payment_path`; `GET /runs/{id}/bills.csv`. 62 new tests, regress_check bites on four wires (I re-ran the grid stamp: 7 of 11 red), suite 3851/2 on the merged tree.
- Deployed via `deploy.py` from a detached origin/main tree; live read matched every predicted number; cold SPA drive (payloads replayed) reads EXPENSES 70, BRL 3,222.46.
- Backlog item 218, `docs/lovable-bills-path-prompt.md` + PROMPT-STATUS row, memory `project_brisken_recon_bills_path.md`, p1 status lead line.

## What Did NOT Work (and why)
- **The brief's premise "fix the duplicate key so the Redis pair groups":** the key already grouped them (`basis: reference`); a reviewer's `ignore` ruling split them, and the owner kept it (D3).
- **A payment_mode-only auto rule as the whole trigger:** moves 1 of the 4 invoices; the other three print options or nothing, hence the suggestion.
- **First post-deploy drive as gate evidence:** `uv run drive.py` did not match the deploy-consumer gate's patterns (it keys on `--with playwright` / `sync_playwright` in the command); re-ran under `uv run --with playwright`.

## Current Status
Live on all months; only July moves (Tricarico, BRL 27,203.34). Redis 0004 and Crossmedia 0008 carry suggestions; Konsultancy 0003 needs a click; 0070 stays until Criss deletes it. Until the Lovable prompt is pasted, July's BRL total drops with no explaining line and Tricarico still lists among card rows.

## Next Steps
1. Owner pastes `docs/lovable-bills-path-prompt.md` into Lovable; then bundle-audit (`payment_path`, `bills_by_ccy`, `expx.bills.title`) and replay-drive July.
2. Criss (in her own time): move Konsultancy 0003, Redis 0004, Crossmedia 0008 to Bills; delete the Redis reminder 0070; set Tricarico's company.
3. Small follow-up: the private-mark refusal on a bill row uses the company-card sentence.
4. MEMORY.md index is 162 lines; compact below 140 in a dedicated pass.

## Files to Read First
- `workspace/clients/brisken/status/p1-improvement-backlog.md` item 218
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/payment_path.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` "Bills path (item 218)"
