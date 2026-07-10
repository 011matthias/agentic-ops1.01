# Mini-Checkpoint: Brisken Expense Recon — OCR + Doctor + Run-log

**Date:** 2026-06-11
**Status:** Ungated build complete. 3 slices shipped to main; only gated work (live calibration, 5a config, 4b posting, 3b tuning) remains.
**Type:** mini

---

## Summary
Built and shipped three expense-recon slices in one session (each its own PR, all CI-green-merged): slice 2.2 receipt OCR (folder ingest), slice 5.14 `doctor` pre-flight, slice 5b run history (SQLite run-log). The ungated critical path (slices 2, 2.2, 3a, 4, 5.14, 5b) is now on main; ~171 tests green. User has Zoho Expense access + dropped 13 real receipts into `context/drafts/`, but the live OCR calibration is blocked on a missing OpenAI key.

## What Was Done
- **Slice 2.2 — receipt OCR (PR #107, `32fcc64`).** `extract_receipt` on `LLMClient` (OpenAI vision for images; PDF text-layer via pypdf for digital receipts; pypdfium2 render fallback for scans). New `ingest/receipts_folder.py` (per-file tolerant; unsupported files → Errors sheet, never dropped; never invents line items per LD-2). CLI `receipts.source` csv|folder (inferred from path); `llm.vision_model` knob. Deps: pypdf, pypdfium2, pillow.
- **Slice 5.14 — `doctor` (PR #108, `11bab8b`).** `expense-recon doctor --config X`: read-only, no-network banded OK/WARN/FAIL over config JSON, statement file + column_map vs actual header, receipt source, llm/zoho env-cred presence, output path. Exit 1 on FAIL. Folder-mode example + env-gated live OCR test (2.9, `EXPENSE_RECON_LIVE_OPENAI=1`). Onboarding doc ANTHROPIC→OPENAI corrected.
- **Slice 5b — run history (PR #109, `fc0035e`).** `runlog.py` opt-in SQLite run-log (no `run_log:` block = no file, no behaviour change). `expense-recon history [--run id|prefix]` + `expense-recon diff id id`. Records every tx incl. unmatched; audit columns only (when/who/source/report/counts/cost) — never account/vendor/amount data. 11 tests.
- Zoho Expense **read** access confirmed earlier via vault smoke: the sandbox OAuth token is `ZohoBooks.fullaccess.all` scope only (Expense API returned 401, code 57). User's Expense access is a **UI login** on an existing vault account, not API. The `ZE_*` receipt filenames are Zoho Expense exports → folder-mode ingest already consumes that pipeline's output (makes slice 7 mobile-capture largely moot).

## Current Status
Ungated build done. Tool can: ingest statement (csv/xlsx) + receipts (csv OR folder-of-images/PDFs via OCR), deterministic match + LLM FX/ambiguous judgment, per-line LLM categorization against Brisken's real sandbox chart (4.6 live-verified 06-09), write 5+N-sheet xlsx + Zoho journal CSV, validate config via `doctor`, persist run history. No platform/Make infra (standalone Python CLI). Worktree removed; local main updated to `fc0035e`.

## Next Steps
1. **Live OCR calibration (BLOCKED on key).** LIMITATION: no OpenAI key on this machine — the 06-01 key was never persisted and was flagged for rotation; not in env, vault, or any .env. USER ACTION NEEDED: set `OPENAI_API_KEY` or add vault entry `OpenAI Brisken`, then run the staged script `C:\Users\neuma_p1qrsic\AppData\Local\Temp\brisken_ocr_calibration.py` against the 13 real receipts (~$0.01–0.05; first real-data quality number, feeds slice 3b).
2. **Slice 5a config layer** (gated on Chris's real card→Zoho-account pairings; lives in a separate private `brisken-config` repo).
3. **Slice 4b live Zoho posting** (gated floor — explicit owner go + irreversible-action protocol).
4. **Slice 3b matcher tuning** (gated on Chris's one real reconciled month).
5. 4.8 idempotency deferred (guards 4b posting; no surface until that lands).

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` (slice map; 2.2/2.9/5.14/5.7-5.10 now ticked)
- `src/expense_recon/ingest/receipts_folder.py`, `src/expense_recon/doctor.py`, `src/expense_recon/runlog.py` (this session's new modules)
- `src/expense_recon/cli.py` (subcommand dispatch: doctor / history / diff; opt-in `run_log:` recording)
- `context/drafts/` — 13 real Brisken receipts (git-ignored; ZE_ jpgs + Uber/ticket PDFs)
