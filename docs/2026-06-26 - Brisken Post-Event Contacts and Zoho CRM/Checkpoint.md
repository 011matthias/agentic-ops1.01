# Checkpoint: Brisken Post-Event Contacts and Zoho CRM

**Date:** 2026-06-26
**Status:** Post-event lead intelligence built; Zoho CRM read-only connection live

---

## Summary
Turned the Rome post-event master contact sheet into a real follow-up tracker (per-wave reply columns, prior-relationship provenance, campaign-touch history) and stood up a secure read-only Zoho CRM API connection that now drives the `brisken_customer` flag across all 289 rows.

---

## What Was Done This Session

### Master contact sheet (rome2026-post-event-master-contacts.xlsx, 289 rows / 26 cols)
1. Replaced `MN-Email` + folded-in `dirk_notes` with six per-wave columns: `E1/E2/E3_response` + `E1/E2/E3_our_reply` (11 contacts have captured conversations; Lasse's reply attributed to Matthias, the rest Dirk).
2. Filled `if_we_know_them` for 34 external contacts from the warm-reconnect list (past TA Cook events: Rome 2025, Brussels 2024, EMEA/Chicago 2023); internal/team rows left blank.
3. Added `emails_sent` column from the three send logs: 9 got all 3 waves, 26 got E1 only, 160 never emailed.
4. Added Akash Gupta (Maersk) as a non-attendee email lead with his E3 exchange; Dirk owes him AI-in-treasury documentation (flagged in the cell).
5. `dirk_notes` intentionally left empty for manual use; booth lead-temperature tags dropped (never captured at the booth).

### Zoho CRM integration (read-only)
6. Walked the user through Zoho Self Client creation; data center = `.com`; scopes `ZohoCRM.modules.contacts.READ,ZohoCRM.modules.accounts.READ`.
7. Built `.scratch/zoho.py` (exchange + pull), secrets in gitignored `context/.env`, data to gitignored `context/zoho-crm.json`. Pulled 1,395 contacts + 465 accounts (120 customer-typed).
8. Matched into `brisken_customer` with a safe precedence (exact email -> unambiguous company domain -> account name). Caught and fixed a domain-poisoning bug where `sap.com` (mixed Customer/Partner/Lead) was mislabeling all SAP contacts as customers. Result: 18 Yes, 31 known non-customers, 16 In CRM (untyped), 220 no match, 3 team, 1 test.

### Deliverable
9. Generated `brisken-data-security-crm.pdf` (visual-first, 2 pages) explaining the data-security model to Dirk: read-only, gitignored creds, local-only, one-click revoke.

---

## Key Decisions Made

### Domain matching only when unambiguous
- **Choice:** Infer customer status from an email domain only when every CRM contact at that domain maps to a single account type.
- **Rationale:** `sap.com` mixes Customer, Partner, Lead and Referral Partner; a blanket domain inference labeled all SAP contacts as customers, contradicting the warm-list judgment that SAP is a partner. Exact-email and account-name matching resolve SAP correctly to "No (Partner)".

### Secrets in gitignored context/.env, not the vault
- **Choice:** Store the Zoho refresh token + client id/secret in `workspace/clients/brisken/context/.env`.
- **Rationale:** The encrypted vault is CLI-interactive and cannot be read by an unattended script; the `.env` is gitignored AND hook-blocked from commit (two independent locks), matching the existing GoDaddy-cred pattern.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx | Modified | enriched master sheet (gitignored) |
| .scratch/merge_contacts.py | Modified | sheet build script (source of truth) |
| .scratch/zoho.py | Created | Zoho CRM read-only client (exchange + pull) |
| workspace/clients/brisken/context/.env | Modified | Zoho creds added (gitignored) |
| workspace/clients/brisken/context/zoho-crm.json | Created | CRM pull, 1395 contacts + 465 accounts (gitignored) |
| workspace/clients/brisken/deliverables/brisken-data-security-crm.pdf | Created | client-facing data-security explainer |
| .scratch/brisken-data-security.html | Created | PDF source |
| workspace/hours-tracker.xlsx | Modified | Lead Generation row 44 (2026-06-26, 4h) |

---

## Current Status
The master sheet is the working post-event follow-up tracker: who we know, who replied to which wave and what was said, who got which emails, and who is a customer (from live CRM). The Zoho CRM connection is live and re-runnable (`zoho.py pull`).

---

## Next Steps
1. Type the 16 "In CRM" accounts in Zoho (account type unset) so the next pull resolves them to a clean Yes/No.
2. Dirk: send Akash Gupta (Maersk) the promised AI-in-treasury use-case documentation.
3. Work the prioritized follow-up: 18 confirmed customers + the booth repliers (Jose/Holcim booked, JB/JTI booth meeting, Christos/BSTDB will stop by, Uffe/Grundfos call after summer).
4. Optional: send Dirk the data-security PDF; consider pulling CRM Deals for relationship stage if needed.

---

## Context for Next Session
### Files to Read First
- workspace/clients/brisken/context/lead-generation/Rome-Event/event-admin/rome2026-post-event-master-contacts.xlsx (the tracker)
- .scratch/merge_contacts.py (rebuilds the sheet from all sources)
- .scratch/zoho.py (re-pull CRM)

### Open Questions
- Exact hours for 2026-06-26 (logged 4h as an estimate, awaiting user confirmation).
- Pull CRM Deals too, for relationship stage / open-deal signal?

### Working Notes
- The sheet is rebuilt by `.scratch/merge_contacts.py`; it reads TAC sponsor list + booth registrations + warm-customer-list + warm-reconnect + 3 send logs + `context/zoho-crm.json`, and folds the few manual reply/lead facts via in-script dicts (WAVE, EXTRA_LEADS). Regenerate via `uv run --directory <repo> --with openpyxl python .scratch/merge_contacts.py`.
- The xlsx is frequently open in Excel; close the specific workbook via COM (SaveChanges=$false) before regenerating, then reopen.
- Books-vs-CRM: initially built `zoho.py` for Zoho Books, switched to Zoho CRM when the user clarified "Brisken's CRM". The token-exchange flow is identical; only scopes + API base differ.
- CRM match precedence and the unambiguous-domain rule live in `merge_contacts.py` `crm_status()`.

### Reference Materials
- Zoho API console (DC `.com`): https://api-console.zoho.com
- Self Client scopes used: `ZohoCRM.modules.contacts.READ,ZohoCRM.modules.accounts.READ`

---

## How to Continue
Open the master sheet to read the current follow-up state. To refresh customer flags after typing accounts in Zoho, run `zoho.py pull` then regenerate the sheet via `merge_contacts.py`.

---

## Strategic Feedback

### What Worked Well This Session
- Dry-running the CRM match against known company names before writing surfaced the `sap.com` poisoning before it ever hit the sheet. Verify-against-source caught a real error.

### Suggestions
- When the hours aren't dictated, the clock times in the tracker are guesses; a one-line "worked ~Xh today" at session end keeps the billing record exact without me estimating.

### System Health
- The Zoho CRM connection is a new, re-usable client integration living in `.scratch/` (gitignored). If it becomes recurring, promote `zoho.py` to `tools/` with an INDEX row; right now it is correctly kept out of the tracked tree until proven.
- Autonomy score: 1 human intervention (one B1 closing-offer deferral, caught by the stop-hook and corrected; no user corrections to the work itself).
