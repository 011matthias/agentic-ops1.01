# Checkpoint: Brisken Expense-Recon LLM Categorization

**Date:** 2026-07-21
**Status:** PR1 merged (#313, not yet deployed); PR2 (vision + adjudication) planned + approved, not started

---

## Summary

Shipped the SPA memory API (`/api/memory`, PR #304, deployed to Fly v25). Then, from a real
Lovable-UI test upload (ER-00216), pivoted into the "LLM improves, not copies" categorization
work: shipped **PR1** (#313 — the tool's own category/account can override the Zoho report's,
`AI Category` columns in the reconciled CSV, hosted runs use the LLM by default). Live
verification exposed the true root cause of the ADOBE mis-categorization, and the owner chose to
fix it via **vision** (PR2). Planned PR2 (read receipt images + a deterministic top-level
adjudication gate) — approved.

---

## What Was Done This Session

### SPA memory API (PR #304 — shipped + deployed)
1. `GET /api/memory` (serialize `build_memory_view`) + `POST /api/memory/forget` (reuse
   `forget_memory_vendor`), both operator-gated (`^/api/memory($|/)` in auth.py), mirroring the
   HTML `/memory`. JSON twin of the operator surface for the Lovable memory screen.
2. Built in an isolated worktree off origin/main, 677 tests green, PR #304 merged, deployed to
   `brisken-expense-recon.fly.dev` (release **v25**), verified live as operator (401→200 with the
   operator token, correct JSON shape).

### Test loop on the user's real upload
3. Retrieved the user's SPA upload (run `edf6bc02baa6`, the ER-00216 pair) off the Fly volume
   (`flyctl sftp /data/runs/<id>/`, MSYS_NO_PATHCONV=1). Diagnosed the "0 matched": it is
   `n_reconciled` (auto-confirmed) — a fresh run auto-confirms nothing; 20 receipts sat in
   NEEDS_REVIEW (FX) by design. Also found the upload form captured `account_card_currency:
   "USD, BRL"` (a data-entry slip; should be `USD`).
4. Ran the full LLM pipeline (OpenAI Brisken key) → reconciled CSV. This surfaced the ADOBE
   problem: matched ADOBE/ANTHROPIC rows showed the report's wrong "Travel Expense | Food".

### PR1 — LLM owns category+account + hosted LLM default-on (#313, merged)
5. `categorization.override_er_category` flag; `_carry_zoho_account` keeps the LLM/learned
   account under the flag (falls back to the report's only when the line has no account).
   Threaded through `categorize_receipts`/`categorize_charges`/`cli.reconcile()`.
6. `AI Category` / `AI Zoho Account` / `AI Category Source` columns in the reconciled CSV
   (beside the report's `Zoho Category`).
7. Hosted LLM default-on: `EXPENSE_RECON_DEFAULT_LLM` (default on) + `EXPENSE_RECON_OVERRIDE_ER_CATEGORY`
   (default on); keyless runs fall back silently (banner stays tied to an explicit request).
8. Tests (override precedence, AI columns, hosted default-on) + full suite **690 green** + ruff.
   PR #313 merged on green CI.

### Root-cause finding (live verification of PR1)
9. Ran PR1's code on the real ER-00216: the AI Category came back **blank (REVIEW)** for
   ADOBE/ANTHROPIC. Cause: the ER **summary table carries no vendor** for ~9/19 matched receipts,
   so the categorizer has no signal. Receiptless charges categorize perfectly (they use the
   STATEMENT vendor). So PR1 surfaces + overrides but does NOT fix ADOBE.

### PR2 plan (approved)
10. WS2 = vision: render the ER PDF's receipt-image pages (pypdfium2), `extract_receipt` per
    image, map back to the summary row, populate `detected_vendor`/`line_items` at ingest.
11. Owner-added adjudication: after categorization, compare the tool's category to the report's
    `zoho_category` **deterministically at the top level** (Zoho root-group via
    `ChartOfAccounts.resolve`→`root_group`); insert the tool's finding ONLY on a heavy mismatch,
    else keep the report's. `Category Decision` column surfaces the verdict.

---

## Key Decisions Made

### Category source: LLM may override the report, gated by heavy mismatch (PR2)
- **Choice:** the tool's own category/account can override the Zoho report's (reverses Dirk
  2026-06-16). PR1 made it unconditional where the LLM had an account; PR2 narrows it so the
  override fires only on a heavy top-level mismatch.
- **Rationale:** trust the report unless the receipt clearly contradicts it; heavy rows become
  the review queue.

### Fix ADOBE via vision, not a statement-vendor fallback
- **Choice:** the owner declined the cheap "use the statement charge's vendor for matched
  receipts" fix and chose the LLM reading the receipt images (WS2 vision).
- **Rationale:** the receipt image is ground truth; the statement description can be cryptic.

### Adjudication: deterministic root-group comparison, gate governs insertion
- **Choice:** "differs heavily" = different Zoho root-group; the gate decides whether the LLM's
  finding is inserted (posts) vs the report's stays. Not an LLM adjudication call.
- **Rationale:** deterministic, auditable, no extra cost; reuses the COA's `root_group`.

### Matching: deterministic backbone + LLM layer (unchanged from first plan)
- Keep `match_month` (reconciliation invariant + tests); card as tie-break, FX-judgment enriched
  with card, optional second-chance pass — all in PR3 (WS3).

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| PR #304 (merged): `web/app.py`, `web/auth.py`, `tests/test_web_memory.py`, `tests/test_web_roles.py` | Merged to main | `/api/memory` + `/api/memory/forget` operator-gated |
| PR #313 (merged): `categorize.py`, `categorize_charges.py`, `cli.py`, `coa_gate.py`, `output/reconciled_csv.py`, `web/service.py`, `web/templates/_run_form.html`, `tests/test_categorize_llm.py`, `tests/test_reconciled_csv.py`, `tests/test_web_llm_default.py` | Merged to main | override_er_category + AI columns + hosted LLM default-on |
| `~/.claude/plans/plan-out-how-we-playful-boole.md` | Modified | The 4-workstream plan; WS2 now includes the vision + adjudication design |
| `docs/2026-07-21 - Brisken Expense-Recon LLM Categorization/Checkpoint.md` | Created | This checkpoint |

Ledger writes (this checkpoint, session log, context YAML, INDEX) are LOCAL only — not committed
from this shared tree (sibling sessions have uncommitted ledger edits here; committing would
entangle them). Batch onto a `docs/...` PR later per G1.

---

## Current Status

- **PR #304 `/api/memory`:** merged + deployed live (Fly v25), verified.
- **PR #313 categorization:** merged to main, **NOT deployed** (Band-3 deploy pending an explicit
  order — recommend bundling with PR2 so the visible payoff lands together).
- **PR2 (vision + adjudication):** planned + approved, **not started**. Large build.
- Platform: expense-recon runs on **Fly** (not Make/n8n) — no Make reconciliation needed.

---

## Next Steps

1. **Build PR2 (WS2 vision + adjudication) in a fresh session** — the large, highest-risk piece.
   First examine `ER-00216.pdf` page structure to nail the image→summary-row mapping.
2. **Deploy PR1+PR2 to Fly together** (Band-3, needs an explicit "deploy" order); verify via the
   SPA that a hosted run shows `llm_enabled=true`, vision categories, `Category Decision` values.
3. **PR3 (WS3 matching)** after: card tie-break signal + FX-judgment card enrichment + optional
   second-chance pass.

---

## Context for Next Session

### Files to Read First
- `~/.claude/plans/plan-out-how-we-playful-boole.md` — the full 4-WS plan (WS2 = vision + adjudication)
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md`
- `src/expense_recon/cli.py` `reconcile()` (~line 366) — the pipeline step order; vision slots between `_load_receipts` and `categorize_receipts`
- `src/expense_recon/ingest/receipts_folder.py` (`_pdf_page_images`, line 140) — the pypdfium2 render pattern to reuse
- `src/expense_recon/ingest/expense_report_pdf.py` — the current text-only ER parser (ignores the image pages)
- `src/expense_recon/llm/client.py` `extract_receipt` (line 204) — the existing vision extraction
- `src/expense_recon/categorize.py` `_carry_zoho_account` (line 246) — the override branch the adjudication refines
- `src/expense_recon/ingest/chart_of_accounts.py` `resolve`/`root_group` (164/177) — the deterministic top-level comparison
- `src/expense_recon/output/reconciled_csv.py` — the AI columns (PR1) + where `Category Decision` goes
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- **Image→summary-row mapping (main PR2 risk):** how the ER PDF lays out receipt images vs the
  summary table; primary = Ref#/expense-id on the image → summary `detected_reference`, fallback =
  page-order + amount. Resolve against the real `ER-00216.pdf` before building the merge.
- **`EXPENSE_CATEGORIES → root_group` fallback map:** confirm the top-8 ↔ Zoho root-group
  correspondence against the real Books groups (in `zoho-books-coa.json`).

### Working Notes
- **Root cause (do not re-derive):** the ER summary table has NO vendor for ~9/19 matched
  receipts on ER-00216 (ADOBE/ANTHROPIC included) → categorizer REVIEW/blank → report's account
  remains. Receiptless charges categorize well because `categorize_charges` uses the STATEMENT
  vendor. PR1 alone therefore shows a BLANK AI Category for ADOBE (honest). Vision (PR2) is the fix.
- **COA is available locally:** `workspace/clients/brisken/context/zoho-books-coa.json` +
  `coa-provision.json`. But `_build_chart_of_accounts` only takes `api`/`csv` (not the JSON), and
  the WEB path does not wire COA labels into the categorizer today — so the account-override's
  ACCOUNT effect is a no-op on hosted runs until COA labels are wired (the AI CATEGORY still
  surfaces). Consider wiring COA labels for the categorizer in PR2 (needed for the adjudication
  root-group comparison anyway).
- **The test data:** the ER-00216 bundle (statement.csv + ER-00216.pdf) lives at
  `workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/01-05-2026_ER-00216/`.
  A pulled copy + the run configs are in the session scratchpad `recon-edf6bc02baa6/`.
- **Reconciled CSVs handed to the user:**
  `workspace/clients/brisken/context/expense-reconciliation/reconciled-ER-00216-edf6bc02baa6.csv` (+ .xlsx).
- **Deploy owner:** `matneumann07@gmail.com`; deploy from a clean `origin/main` worktree.
- **OpenAI cost reference:** the full ER-00216 LLM run was ~$0.01 (144 gpt-4o-mini calls).

### Reference Materials
- Live app: https://brisken-expense-recon.fly.dev (operator code in vault "Expense Recon App" — `mn040307`)
- SPA repo: `011matthias/brisken-expense-review` (TanStack Start, Lovable-hosted)
- PR #304, PR #313 on `011matthias/agentic-ops1.01`

---

## How to Continue

`/resume brisken`, read the plan file, then build **PR2 (WS2 vision + adjudication)**. Start by
examining `ER-00216.pdf`'s page structure (the image→row mapping is the main unknown). Cut a fresh
`client/brisken/...` worktree off the latest origin/main (`git fetch origin main` first — this
module has concurrent sibling sessions). Ship PR2 via CI-green auto-merge, then request the
bundled PR1+PR2 Fly deploy.

---

## Strategic Feedback

### What Worked Well This Session
- Live verification on the REAL data (ER-00216) before declaring PR1 done caught the actual root
  cause (ER summary lacks vendor) that the plan's Plan-agents had gotten wrong — the verification
  step earned its keep and reshaped PR2.
- The AskUserQuestion forks (category source, matching depth, receipt source, adjudication) kept
  the design aligned with the owner's intent instead of guessing on direction changes.

### Suggestions
- The upload form free-texts `account_card_currency` (captured "USD, BRL" on the real upload). A
  currency dropdown / validation in the SPA would prevent a bogus currency tagging every charge.

### System Health
- The stop-b1-gate fired ~4× this session on closing phrasing (trailing "say the word" / "if you
  want" offers on messages that were genuine decision points). The hook held each time (reframed),
  so it worked as designed, but this is a recurring false-fire-adjacent phrasing class (also seen
  2026-07-20). Not promoted; the hook is the structural backstop.
- Autonomy score: 0 human error-corrections — the user's inputs were new directives (deploy, run
  the pipeline, output CSV, LLM-owns-category, add adjudication) and design decisions, not
  corrections of agent mistakes. Fully owner-directed, agent-executed.
