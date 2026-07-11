# Mini-Checkpoint: Brisken Expense-Recon Zoho + COA Gate

**Date:** 2026-07-01
**Status:** Phase-5 COA gate merged to main (PR #202); gate inert until configured + chart provisioned + deployed
**Type:** mini

---

## Summary
Unblocked Zoho Books read access for Brisken p1 (expense-reconciliation), pulled the real chart-of-accounts for all 8 orgs, and built + tested + merged the Phase-5 pre-write chart-of-accounts validation gate.

## What Was Done
- **Zoho Books read access live (2026-06-30).** The lead-gen CRM token is CRM-scoped only (Books → 401/code 57). Minted a SEPARATE Books token under `ZOHO_BOOKS_REFRESH_TOKEN` (CRM token untouched) via `.scratch/zoho.py exchange-books`. Scope gotcha: chart-of-accounts is in Zoho's `accountants` module, so it needs `ZohoBooks.accountants.READ` (not `settings.READ`). Granted `ZohoBooks.accountants.READ,ZohoBooks.settings.READ` (both read-only). Driver commands added to `.scratch/zoho.py`: `exchange-books`, `books`, `books-probe`.
- **Real chart-of-accounts pulled.** 1,252 active accounts across 8 orgs → gitignored `workspace/clients/brisken/context/zoho-books-coa.json` (native Zoho field names incl. `parent_account_name`; loads via `chart_of_accounts.from_api`). Verified: Corporate Services → 76 postable expense leaves, Consulting LLC → 82 (DO-NOT-USE + parent rollups filtered).
- **Phase-5 COA gate built + merged (PR #202).** New `coa_gate.py` validates each posting account against the target entity's chart (OK / MISSING / UNKNOWN / INACTIVE / DO_NOT_USE / NON_LEAF / OUT_OF_SCOPE) and diverts non-postable lines to REVIEW before the Books export. Wired into the shared `write_zoho_export` / `build_journal_rows` (CLI + web) behind opt-in `coa_validation:` config; absent = byte-for-byte unchanged. 23 new tests; suite 417 passed, 2 skipped; CI green; squash-merged to main 2026-06-30T22:56Z.
- Built on branch `client/brisken/expense-recon-coa-gate` in the **recon-main worktree** (`agentic-ops1-recon-main`, off main). The two target entities: **Corporate Services 822741658**, **Cloud Services 697686691** (owner pick).
- Memory written: `project_brisken_zoho_books.md` (connection, scope gotcha, 8 org ids, COA artifact).

## Current Status
Gate is on main but INERT: opt-in config absent + real chart gitignored (loaded at runtime) + not deployed. No runtime behavior change yet.

## Next Steps
1. Derive per-entity `scope_groups` (which expense subtrees count as card spend, excluding Payroll/tax) for Corporate Services + Cloud Services from `context/zoho-books-coa.json`.
2. Provision `zoho-books-coa.json` into the Fly runtime + add a `coa_validation:` block per entity (org_id + chart_path + scope_groups).
3. `flyctl deploy` to brisken-expense-recon.fly.dev (Band-3 gated — needs explicit "deploy" order), then verify the deployed origin.

## Files to Read First
- `.scratch/zoho.py` — Zoho CRM + Books read driver (`exchange-books` / `books` / `books-probe`)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/coa_gate.py` — the gate (in recon-main worktree / on main)
- `workspace/clients/brisken/context/zoho-books-coa.json` — real 8-org chart (gitignored)
- memory `project_brisken_zoho_books.md`, `project_brisken_expense_recon_review_surface.md`
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` (on main, ~985 lines)
