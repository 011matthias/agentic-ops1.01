# Checkpoint: Brisken Expense-Recon Tier-2 Charge Categorization

**Date:** 2026-07-20
**Status:** Shipped (PR #287 merged to main, CI green)

---

## Summary
Built and shipped Tier-2 of the Brisken expense-recon "categorize + status EVERY charge" work: receiptless charges (every USD SaaS subscription with no expense-report receipt) are now categorized and, when LEARNED, posting-eligible to their real Zoho Books account. Verified end-to-end no-LLM on Criss's real April files. Isolated worktree, owned only the assigned Tier-2 surfaces; sibling Tier-1 (`ingest/*`+`matching/*`) untouched.

---

## What Was Done This Session

### Slice 10 — receiptless-charge categorization
1. New `categorize_charges.py`: builds a charge pseudo-receipt (empty `line_items` forces the vendor-fallback path, never LINE) and delegates to the existing `categorize_receipts`, so a charge resolves LEARNED-first then VENDOR fallback.
2. Post-match stage in `cli.reconcile()`: result rides in a `ReconcileResult.charge_categorizations` side-map (not a field on the frozen `Transaction`); runs after `match_month`, reads only `unmatched_transactions`, never changes buckets.
3. `zoho_export.build_journal_rows`: second loop over postable receiptless-LEARNED charges, behind the opt-in `zoho.export_receiptless_learned` flag (withheld-until-confirmed default). COA-gated; VENDOR/REVIEW/posted charges never export; blank reference columns (no receipt = B4 blank-over-fabricated).
4. Surfaced the category on the unmatched rows across `report_xlsx` (Unmatched sheet + card tabs), `sheet_writeback`, `reconciled_csv`, and the web workbench (snapshot side-key in `service.py` + `build_view` + no-receipt row suggestion in `workbench.html`).
5. `expense-recon memory set "<vendor>" --category .. --account .. --entity ..` — authors a standing rule directly (the Anthropic case), stored as a `manual-set` merchant_category row.

### Slice 11 (P1) — source-agnostic subscription status
6. `derive_subscription_status`: marks `entry_status="subscription"` for a vendor recurring in >=2 prior months of the built `StatementStore`. Annotation-only; precedence fill/operator > derived. Wired into `cli.run()` via `_derive_subscriptions` (opt-in: fires only when a `store.statements_path` exists on disk).

### Tests + verification
7. New `test_categorize_charges.py` (pseudo-receipt shape, LEARNED-wins, VENDOR fallback, REVIEW-no-invent, bucket-untouched, subscription derivation + precedence) and `test_web_charge_categorization.py`. Extended `test_zoho_export.py` (flag on/off, VENDOR/posted/gate-diverted exclusion, balanced coexistence), `test_reconciled_csv.py`, `test_report_xlsx.py`, `test_sheet_writeback.py`, `test_learning_cli.py` (memory set + end-to-end recall).
8. Full suite: **486 passed, 22 skipped**. `calibrate` exit 0.
9. Real-data verification (no LLM) on Criss's April files (ER-00215 + Chase 2838, run locally): 6 Anthropic charges → LEARNED, posted to `COGS - Other Infra and IT Costs for Cloud Business` through the COA gate; Adobe/OpenAI/GitHub → VENDOR, review-only (0 in journal); flag-off → 0 receiptless rows; 39 charges flagged subscription from history.

---

## Key Decisions Made

### Side-map, not a Transaction field
- **Choice:** Charge categorizations live on `ReconcileResult.charge_categorizations`, not on the `Transaction` dataclass.
- **Rationale:** Tier-1 owns `matching/types.py` (the frozen `Transaction`). A side-map keeps the tier boundary clean and keeps the annotation out of the reconciliation buckets.

### Postable only when LEARNED, and only behind a flag
- **Choice:** Only Tier-1 LEARNED charges are journal-eligible, gated by `zoho.export_receiptless_learned` (default off). VENDOR/REVIEW stay review-only.
- **Rationale:** A vendor keyword guess has no real Books account and must not auto-post; withheld-until-confirmed matches the "review everything for the first months" posture. The COA gate is a second backstop.

### Left the ledger uncommitted for the sweep
- **Choice:** Checkpoint ledger files written to the shared working tree, not committed via my own docs PR.
- **Rationale:** Three sibling sessions share this clone and are mid-checkpoint (p1-status, INDEX, friction-register all dirty; today's session log untracked). A competing docs PR would fragment/conflict. Matches the repo's observed uncommitted-backlog + `repo-sweep` workflow.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/categorize_charges.py` | Created | Slice 10/11 core: charge pseudo-receipt + subscription derivation |
| `.../src/expense_recon/cli.py` | Modified | Post-match charge-categorize stage, side-map, subscription derivation, wiring |
| `.../src/expense_recon/output/zoho_export.py` | Modified | Receiptless-LEARNED journal rows (flag + COA gate) |
| `.../src/expense_recon/output/report_xlsx.py` | Modified | Charge category on Unmatched sheet + card tabs |
| `.../src/expense_recon/output/reconciled_csv.py` | Modified | 3 charge-categorization columns |
| `.../src/expense_recon/output/sheet_writeback.py` | Modified | Charge account/confirm marker on unmatched rows |
| `.../src/expense_recon/web/service.py` | Modified | Snapshot side-key + build_view charge_category |
| `.../src/expense_recon/web/templates/workbench.html` | Modified | No-receipt row suggestion chip |
| `.../src/expense_recon/learning_cli.py` | Modified | `memory set` command |
| `.../tests/test_categorize_charges.py`, `test_web_charge_categorization.py` | Created | Slice 10/11 unit + web tests |
| `.../tests/test_zoho_export.py`, `test_reconciled_csv.py`, `test_report_xlsx.py`, `test_sheet_writeback.py`, `test_learning_cli.py` | Modified | Slice 10 coverage |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | Tier-2 element marked shipped (additive, on top of sibling refresh; left dirty) |

---

## Current Status
Tier-2 is merged to `main` (PR #287, squash `7bcf3f3`, all CI green). The feature is behind opt-in config, so it is inert until a run config sets `zoho.export_receiptless_learned` and/or a `store.statements_path`. Not yet deployed to Fly (the expense-recon app deploys separately; no deploy was part of this PR).

Platform: no `platform` section in Brisken infrastructure.yaml for this module (it is a Fly-hosted FastAPI app, not Make/n8n) — no ops-audit applies.

---

## Next Steps
1. **Tier-1 still pending** (sign-fix + PDF-first + deterministic FX; `ingest/*`+`matching/*`). Until it lands, no-LLM matching stays 0/94 on the activity CSV and Tier-2 journal debits carry the Chase-CSV negative sign. Ready-to-paste prompt in plan file `glimmering-herding-glade.md`.
2. **Deploy Tier-2 to Fly** and set `zoho.export_receiptless_learned` + the standing Anthropic `memory set` on the operator surface, once Tier-1's sign fix is in (so journal amounts are positive).
3. **Seed the real learning store** with `memory seed-zoho` (dev-side) so more receiptless vendors resolve LEARNED rather than VENDOR.
4. Joint no-LLM working run with Criss on a real month once both tiers are live.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` — "Using-the-data revision (2026-07-20)", Slice 10/11 (authority)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` — workstream roll-up
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/categorize_charges.py` — the new module

### Open Questions
- When Tier-1's sign normalization lands, re-verify the journal shows positive debits (Tier-2 needs no change — it reads `tx.amount`).
- Should the P1 subscription-derivation MIN_PRIOR_MONTHS stay at 2, or be tuned once Criss reviews a real month?

### Working Notes
- Verification harness lives in the session scratchpad (`tier2-verify/`): a `prep.py` that builds the Corporate Services (822741658) COA CSV from the cached `zoho-books-coa.json`, seeds `statements.sqlite` from `Chase2838_full_activity.csv` (dates converted DD-MM-YYYY -> ISO first, else 0 parse), and a flag-on/flag-off run config pair. Reproducible if needed.
- The real Books account for Anthropic is `COGS - Other Infra and IT Costs for Cloud Business` (code E700030-30, org 822741658) — confirmed present in the cached COA.
- Anthropic appears only 2026-04/05 in the lifetime activity, so it does NOT self-derive as a subscription for April (no >=2 prior months); the 39 that did are longer-running vendors (DB Fernverkehr, etc.). Correct behaviour.
- 133 vendors recur in >=2 pre-April months in the real history.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/287
- Memories: `project_brisken_expense_recon_testing_loop`, `project_brisken_expense_recon_chris_process`, `project_brisken_expense_recon_review_surface`

---

## How to Continue
Tier-2 is done and merged. The next build unit is Tier-1 (sign + FX) from `glimmering-herding-glade.md` in an isolated worktree; after it lands, deploy the combined module to Fly and turn on the receiptless-LEARNED export flag + standing Anthropic memory rule.

---

## Strategic Feedback

### What Worked Well This Session
- The task brief was a near-complete design spec (file ownership, the side-map decision, the LEARNED-first/never-LINE rule, the COA-gate seam, the exact verification recipe). That let the whole build run autonomously with zero mid-course corrections — the strongest single input to a clean autonomous session.
- Criss's real files already being local (from the prior testing-loop session) meant real-data verification needed no Fly retrieval.

### Suggestions
- When queuing paired tiers like this, a one-line "Tier 1 not yet merged, expect negative debits until it is" in the brief would have pre-answered the sign caveat I had to discover and document.

### System Health
- The shared-clone + multiple-sibling-session hazard is real and recurring (SIBLING-SESSION warning fired at start; INDEX/friction/session-log/p1-status all dirty from siblings mid-checkpoint). The isolated-worktree-per-build discipline held for the code, but the ledger-checkpoint step has no clean concurrent story beyond "leave it for the sweep." A worktree-scoped checkpoint mode, or a sweep that consolidates all sessions' ledger deltas, would close this.
- Autonomy score: 0 human interventions this session — fully autonomous. (Two `cd-guard` hook self-catches, a well-documented recurring class; the hook held both times.)
