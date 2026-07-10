# Checkpoint: Brisken Calibration + Architecture Redirect

**Date:** 2026-06-11
**Status:** Calibration shipped; register synced; Dirk call logged; recommendation drafted; awaiting outbound + remaining data gates

---

## Summary
Unblocked and ran the live OCR calibration (13 real receipts, 100% header coverage, $0.02), brought the ANNEALING register back in sync with reality across two passes, logged the 2026-06-11 Dirk call that redirects the architecture (Expense = entry point, tool replaces manual classification, Zoho exit path), wrote the standalone-vs-in-Zoho recommendation, and captured three real monthly expense reports that deliver the GL subtree, card registry, and hard FX/DCC evidence.

---

## What Was Done This Session

### Live OCR calibration (P1, was key-blocked)
1. Verified no key in env/vault; user added vault entry "OpenAI Brisken" in-terminal (never entered transcript).
2. Repaired the staged `%TEMP%\brisken_ocr_calibration.py` (dead worktree SRC path → main; API surface + imports verified).
3. Ran calibration twice (second with PYTHONUTF8 to verify encoding): 13/13 extracted, date/total/vendor/currency 13/13, reference 12/13, currencies USD/EUR/BRL, line items incl. correct empty-list on unitemized invoice, $0.0204 total. UTF-8 vendor names intact (cp1252 console artifact only).
4. PR #110 merged (BLUEPRINT slice-2 calibration record; two acceptance criteria ticked; accuracy criterion explicitly left open pending ground truth).

### ANNEALING register sync (two passes)
5. PR #111: struck C1 (run-log half) / C3 / D2 / E5; A3 real-data evidence; E7 multi-currency note; new E8 (calibration script in %TEMP% = repeat-use tooling in throwaway location); anneal-order synced.
6. PR #113 (full audit after user push): 5 more missed strikes verified against code — C2 (PR #87+#68, live-verified vs real sandbox chart), E1/E2/E3/E6 (all PR #80), B6 half-struck (Zoho CSV shipped as zoho_export.py; JSON half → slice-6 trigger); corrected two wrong dates from #111 (PR #80 merged 06-07 not 06-09) and D1b's stale "judge_ambiguous remains a stub" line.

### 2026-06-11 Dirk call intake
7. PR #116: verbatim transcript → `reference/2026-06-11-call-transcript.md` (tracked); traced extraction → `context/2026-06-11-call-outcomes.md` (local-only by design, context/ is git-ignored).
8. Key outcomes: as-is Expense→Books process (two report types; GL=classification 1:1; fully manual reconciliation); historic-data sources named (Expense CSV + Books download); FX rules (USD cards, prefer printed USD, transaction-date rate, widening rounds); architecture redirect (Expense single entry point, tool owns classification + reports, direct bank-CSV ingest, 4-table model, journal export to Books with tool-hosted receipt URLs → Zoho switch-off path); LLM key on Books approved.

### Path recommendation (pending deliverable to Dirk)
9. `context/2026-06-11-path-recommendation.md`: recommends the standalone pipeline with Books API only at the output boundary (in-Zoho path optimizes the system Brisken plans to leave; determinism/run-log/reconciliation guarantee live in our tables; standalone is mostly built). Slice-map deltas + exact data asks listed.
10. Verified the load-bearing "Expense CSV has receipt URLs" claim against Zoho docs after user challenge: CSV export is docs-verified; receipt-URL field is NOT documented anywhere (API has receipt_name only, Receipts API upload-only) → downgraded to DIRK-STATED with fallback (bulk Download Receipts + receipt_name filename matching).

### Real expense-report samples
11. ER-00214/215/216 (Mar–May 2026 monthly admin buckets) copied to git-ignored `context/expense-reports/` (NOT drafts/ — folder-ingest would OCR them); extraction in `context/2026-06-11-expense-report-samples.md`.
12. Delivers: reports-table shape; travel GL subtree (E100010 + -01/-06/-26/-31); first card registry (4 Chase payment modes, one mode↔card ambiguity flagged); DCC evidence (card charged 6.7–12.8% above Zoho's USD estimate → matching tolerance + OCR-must-extract-DCC-amount requirements); one same-purchase specimen linking a report line to calibration receipt ZE_5210979 (330.00 charged vs 328.95 itemized + "do/dc Sabor" OCR misread).

### Memory
13. `project_brisken_openai_key.md` + MEMORY.md updated: key now persisted in vault, added in-terminal; whether it's the rotated key still unconfirmed with Dirk.

---

## Key Decisions Made

### Standalone pipeline over in-Zoho automation (recommendation, not yet sent)
- **Choice:** Build on the existing engine; Zoho Books only at the output boundary (journal entries + receipt URLs).
- **Rationale:** Dirk's own URL design exists to switch Books off later; determinism + reconciliation guarantee + run-log live in our tables; the engine is shipped and green; in-Zoho rebuilds the matcher inside a system slated for removal.

### BLUEPRINT realignment deferred until Dirk confirms the path
- **Choice:** Logged build implications in call-outcomes; did not rewrite the slice map.
- **Rationale:** The redirect adds real scope (reports table, bank-statement table, receipt hosting, Expense-CSV adapter); sequence is recommendation → Dirk's pick → slice map.

### Key handling via vault, never transcript
- **Choice:** User added the key in their own terminal; scripts read vault entry by name.
- **Rationale:** The 06-01 key leaked into a transcript and was flagged for rotation; this path structurally prevents a repeat.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/.../expense-reconciliation/BLUEPRINT.md | Modified (PR #110) | Calibration record + 2 acceptance ticks |
| workspace/.../expense-reconciliation/ANNEALING.md | Modified (PRs #111, #113) | 10 strikes total, evidence notes, new E8, date corrections |
| workspace/clients/brisken/reference/2026-06-11-call-transcript.md | Created (PR #116) | Verbatim Dirk call, primary source |
| workspace/clients/brisken/context/2026-06-11-call-outcomes.md | Created (local-only) | Traced extraction + open items |
| workspace/clients/brisken/context/2026-06-11-path-recommendation.md | Created (local-only) | Standalone-vs-in-Zoho decision analysis |
| workspace/clients/brisken/context/2026-06-11-expense-report-samples.md | Created (local-only) | ER-00214/215/216 structural extraction |
| workspace/clients/brisken/context/expense-reports/ER-0021{4,5,6}.pdf | Copied (git-ignored) | Real report sources |
| %TEMP%\brisken_ocr_calibration.py | Repaired (uncommitted) | Dead SRC path → main; see ANNEALING E8 |
| memory/project_brisken_openai_key.md + MEMORY.md | Modified | Vault-key state; rotation confirm still open |

PRs merged this session: #110, #111, #113, #116 (all CI-green auto-merge).

---

## Current Status
Ungated build remains complete (~171 tests green). Calibration done: first real-data quality number exists (coverage 100%, accuracy unproven). Register is in sync with code. The Dirk call redirected the target architecture; the recommendation backing our answer exists but has NOT been sent. Three real expense reports partially resolve the data gates (reports shape, GL subtree, card registry, FX evidence); matching calibration still impossible without the bank-side statements. No platform/orchestrator involved (standalone Python CLI).

---

## Next Steps
1. **Send Dirk the path answer** (user-gated: outbound comms only on explicit ask). The analysis is ready in `context/2026-06-11-path-recommendation.md`; fold in the three data asks (Chase statements for Mar–May, full chart-of-accounts export, one Expense CSV export — the last also settles the receipt-URL question).
2. **On Dirk's confirm:** realign BLUEPRINT slice map (Expense-CSV ingest adapter, bank-statement table w/ dedup, reports table, receipt URL hosting; FX rules into A1/3.7).
3. **When Chase statements land:** slice 3b matching calibration against ER-00214/215/216 (the expense side is already in hand).
4. **E8 trigger watch:** next calibration ask → promote `%TEMP%` script to an `expense-recon calibrate` subcommand.
5. **Confirm with Dirk** the vault key is the rotated one (open security item).
6. 4b live posting stays gated floor; 4.8 idempotency builds with it.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/context/2026-06-11-call-outcomes.md` (call decisions + open items)
- `workspace/clients/brisken/context/2026-06-11-path-recommendation.md` (the pending answer to Dirk)
- `workspace/clients/brisken/context/2026-06-11-expense-report-samples.md` (GL codes, card registry, FX/DCC evidence)
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` (slice map, pre-realignment)

### Open Questions
- Which path does Dirk confirm (standalone expected, but his "is it worth doing this?" was genuine)?
- Does the Expense CSV export actually carry receipt URLs? (Dirk-stated, docs-silent; one real export settles it.)
- Payment-mode↔card mapping: mode-1 lines show receipts charged to two different last-4s (…1672 and …2838); needs Chris.
- Is the vault key the rotated one?

### Working Notes
- Calibration one-liner: `( cd <expense-recon dir> && uv run --quiet python "$TEMP/brisken_ocr_calibration.py" )` — reads vault entry containing "openai"; force PYTHONUTF8=1 for clean console output. Test suite needs `--extra dev`: `uv run --quiet --extra dev python -m pytest -q`.
- `workspace/clients/*/context/` is git-ignored globally (.gitignore:92); reference/ is tracked — the two-file call convention (verbatim in reference/, extraction in context/) follows from that.
- gh PR commands: origin is `011matthias/agentic-ops1.01` — omit `--repo` (the `akkton/...` path in CLAUDE.md is the client-subtree example, not this repo).
- DCC numbers for the matcher: observed markups 6% (SIBS Lisbon), 12% (REDE Brazil), 16% wholesale note (Cielo); Zoho-estimate vs card-charged gaps up to 12.8%.
- Don't put non-receipt files in `context/drafts/` — folder ingest OCRs everything in it (the 3 `.md` files there already land in the Errors path each run).

### Reference Materials
- Zoho docs checked: Managing Expenses (export CSV/XLS), Export Templates (field picker, list undocumented), Expense API v1 (receipt_name only), Receipts API (upload-only).
- Prior checkpoint: `docs/2026-06-11 - Brisken Expense Recon OCR Doctor Runlog/Mini-Checkpoint-1.md`.

---

## How to Continue
`/resume brisken`. If Dirk has replied on the path question: log his reply to context, then realign BLUEPRINT to the confirmed path and start the Expense-CSV ingest adapter (largely a column-map over the existing receipts-CSV path). If statements arrived: start 3b calibration. The outbound answer itself is drafted-in-analysis but waits for the user's explicit ask.

---

## Strategic Feedback

### What Worked Well This Session
- The vault-first key handoff: the user adding the key in their own terminal (one sentence of instruction) kept the credential out of the transcript entirely while unblocking the highest-value gated item in minutes.
- Dropping the three real expense reports immediately after the call: the call described the data, the PDFs proved it — the FX/DCC findings came from having both in the same session.

### Suggestions
- The three asks to Dirk (Chase statements, chart export, one Expense CSV) are all standard downloads he described himself — bundling them into the path-answer message gets the 3b gate open in one round-trip instead of three.

### System Health
- The ANNEALING drift pattern (PR #80 shipped ~8 register items, struck zero; my first sync repeated the miss in miniature) shows mark-done discipline doesn't reach companion docs. If it drifts once more, register-audit-against-code should become a structural step in the brisken ship flow rather than recall.
- Autonomy score: 2 human interventions this session (full-audit push; CSV-claim challenge).
