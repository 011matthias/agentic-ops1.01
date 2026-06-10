# Mini-Checkpoint: Brisken Zoho Integration Slice 4

**Date:** 2026-06-09
**Status:** Slice 4.1 + 4.2 shipped to main; 4.6/4.9 deferred
**Type:** mini

---

## Summary
Zoho Books access landed (admin on sandbox org "TEST"). Set up server-to-server OAuth, built the read client + chart-of-accounts ingest, then wired the chart of accounts into the categorizer scoped to the owner-approved operating-expense groups. Two PRs merged to main.

## What Was Done
- **Zoho OAuth (browser-driven):** logged into Zoho as `neumath4@icloud.com`, created a Self Client in api-console, exchanged a grant code for a long-lived refresh token. Creds stored in local vault under **"Zoho API Brisken Sandbox"** (client_id `1000.REGSY0WNFDDVRWQCF3KALXDMPYYA7V`, org_id `822116290`, US DC, scope `ZohoBooks.fullaccess.all`).
- **PR #87 (merged, 19b0a5d):** `zoho/client.py` (OAuth read path, pagination, stdlib urllib, mockable) + `ingest/chart_of_accounts.py` (Account/ChartOfAccounts, API+CSV, leaf/active/DO-NOT-USE filter). 117 tests + live smoke (195 accounts pulled).
- **PR #88 (merged, a614668):** categorizer forwards in-scope account labels to the LLM and captures `zoho_account` (line + vendor paths); `OpenAIClient` prompts list accounts + nullable `zoho_account` schema; `postable_expense_accounts(scope_groups=...)` + `root_group()`. 122 tests green.
- **Scope decision (owner-approved):** card-expense IN = Travel Expense, Marketing & Selling, Professional Fees, Office Infra and Admin, IT: Computer and Internet, Bank Fees and Charges, Lodging (39 leaves). OUT = COGS (core+intercompany), Payroll, Depreciation/Amortization, Interest, Tax, Bad Debt, Reconciliation Discrepancies, Purchase Discounts (50 leaves).

## Current Status
Zoho read integration is live and verified against the sandbox. The categorizer assigns a specific Zoho GL account per line item, restricted to the approved groups. The export still carries placeholder accounts (4.6 not done), and there is no `zoho:` run-config block yet (4.9).

## Next Steps
1. **Slice 4.6 + 4.9 (next session):** de-placeholder `zoho_export.py` (resolve the LLM-picked label to a real account via `ChartOfAccounts.resolve`, balancing card account); add the `zoho:` config block (creds env refs, the 7-group scope list, export path, CoA source = live API or CSV) wired into CLI `run()`.
3. **Credential rotation:** (a) the unrelated **meji "Zoho Client"** vault password was surfaced into a transcript today, rotate it; (b) Dirk's OpenAI key rotation still unconfirmed (pre-existing).
4. **Calibration (gated on Chris):** live LLM account-pick accuracy needs Chris's hand-categorized month + a working OpenAI key. PR #88 proved wiring, not accuracy.

## Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` (slice map; 4.6/4.9 are the next items)
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/zoho/client.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/ingest/chart_of_accounts.py`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/output/zoho_export.py` (the placeholder to de-place in 4.6)
- Vault entry "Zoho API Brisken Sandbox" (creds; `vault.py get`)

### Working Notes
- Brisken's real chart of accounts is sensitive (intercompany/shareholder/person names) and is deliberately NOT committed to this public repo. It is pulled live from the API; the approved scope-group list goes in the run config / private brisken-config, not the public tool.
- Env vars the tool reads at runtime: `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`, `ZOHO_ORG_ID` (+ optional `ZOHO_API_DOMAIN`/`ZOHO_ACCOUNTS_DOMAIN` for non-US DCs).
- Journal posting (4b) intentionally not built; it is irreversible and stays gated behind explicit confirmation even on the sandbox.
- Local tooling note: the Bash tool wedged its cwd in the home dir mid-session (a `cd ~` broke the relative-path hooks); used PowerShell for the rest. Harmless, but avoid `cd` out of repo root in the Bash tool.
