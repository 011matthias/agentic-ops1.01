# Checkpoint: Brisken Expense-Recon Card-Driven Paid Through

**Date:** 2026-07-28
**Status:** Shipped + deployed + verified live (Fly v52); Lovable prompt delivered

---

## Summary
Receipt-first expense export now resolves each expense's Zoho "Paid Through" account from the card number the OCR already reads off the receipt, replacing the manual per-expense "(paid-through - assign)" step. Two PRs (#467 resolution, #470 grid provenance), the live card→account map populated, and a Lovable prompt for the SPA.

---

## What Was Done This Session
### Backend (two ship + deploy cycles)
1. **PR #467 — card-number → Paid Through in the receipt-first export.** `_card_last4` + `_card_account` in `zoho_expense_export`; card step in `_paid_through` (order: override → receipt's own → card-derived → default → placeholder); `card_accounts` threaded through `build_expense_rows`/`write_zoho_expense_export`; folded into run config at expense-batch prepare (service.py) + the CLI local export. Unknown/cash cards fall through, never mis-post (B4). Fly v51.
2. **PR #470 — resolved account + provenance on the grid.** Extracted `resolve_paid_through()→(account, source)`; `_paid_through` delegates (exported account byte-identical); `build_expense_view` adds `row.posting_paid_through = {account, source}` (source: card|override|receipt|default|reimbursable|unassigned). Fly v52.

### Live settings
3. Populated `card_accounts` on the live app (readiness GET → PUT → verify GET): 5 corporate cards — 2838 Travel, 0113 Apple, 6013 Cloud Travel, 9693 Cloud Expenses, 8311 United — derived last4-from-account-name off the cached COA, owner-confirmed. Existing 2838 entry preserved, none lost.

### Frontend handoff
4. Lovable prompt delivered in-conversation. Change 1 = Paid-Through cell in the expense grid (render `posting_paid_through.account` + source badge "from card ···NNNN"; inline override via `PUT /api/runs/{id}/expenses/{doc}` field=paid_through). Change 2 = card-accounts settings editor (GET/PUT `/api/settings`, `card_accounts` map). Both buildable against the live API now.

---

## Key Decisions Made
### Card number is the primary Paid-Through signal (owner directive)
- **Choice:** Use the last4 the OCR reads off each receipt, mapped via `card_accounts`, instead of a single per-entity default (which drops to a fallback).
- **Rationale:** Per-receipt accurate (mixed-card trips), zero manual picks, no modal-card guess. The OCR already extracted the card (`payment_hint`) and `card_accounts` already existed for the journal credit; only the wiring was missing, and it had been skipped for a now-obsolete reason ("names a card, not a Zoho account" — which `card_accounts` is).

### Held the checking/debit cards
- **Choice:** Mapped only the 5 credit cards; left checking (9388/7292) unmapped.
- **Rationale:** Merchant receipts print the credit card; add debit only if a receipt surfaces one. Owner-confirmed.

### Worked from origin/main, not the stale shared tree
- Local `status/p1-expense-reconciliation.md` was 6 commits behind and said receipt-first was "PR pending, flag off"; origin/main shows it merged and LIVE (#464) plus 4b posting shipped OFF (#465). Read/edited current-main via isolated worktrees throughout.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| output/zoho_expense_export.py | edit | last4 parser + card→account resolver; `resolve_paid_through` provenance; `_paid_through` delegates |
| web/service.py | edit | fold `card_accounts` into run config; `posting_paid_through` on grid rows |
| cli.py | edit | pass `card_accounts` at the local/repro export |
| tests/test_zoho_expense_export.py | edit | 20 tests: parsing matrix + resolution order + source labels |
| (live) `card_accounts` settings | write | 5 corporate cards mapped, verified |

---

## Current Status
Card-driven Paid Through is live end-to-end: PRs #467 + #470 merged, Fly **v52** verified (healthz 200, `/api/settings` 401 gate intact), card map populated + verified live. The Lovable SPA changes are NOT built — the frontend is the remaining half; the prompt is handed over. p1-expense-reconciliation ops status: platform section unknown (no plan data in `infrastructure.yaml`). brisken comms-log 1 day old (current).

---

## Next Steps
1. Build the SPA changes in Lovable from the delivered prompt (Change 1 grid Paid-Through cell, Change 2 card-accounts editor). Needs SPA repo access (`011matthias/brisken-expense-review`).
2. Exercise the card-driven path on a real receipt-first run (a 2838 / 6013 receipt) to confirm end-to-end resolution + the source badge, once the SPA renders it.
3. Optional: add checking/debit cards (9388, 7292) to `card_accounts` only if a receipt surfaces one.
4. Other two 07-28 gaps remain, both owner-gated: send Criss the SPA URL + operator code; validate `EXPENSE_COLUMNS` vs the real Zoho Expenses import + Books write-scope consent. Do NOT enable `zoho.post` without an explicit order.

---

## Context for Next Session
### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `.../expense-reconciliation/src/expense_recon/output/zoho_expense_export.py` (`resolve_paid_through`)
- `.../expense-reconciliation/src/expense_recon/web/service.py` (`build_expense_view` → `posting_paid_through`)

### Open Questions
- Which cards actually appear on Criss's receipts (validates the 5-card map + whether debit cards are needed)?
- Does the SPA expense-batch UI exist yet, or does the Lovable build create it from scratch (Phase 7)?

### Working Notes
- `card_accounts` is a FLAT map keyed by last4, shared by Mode B (journal credit, keyed by `account_id` via endswith) and Mode A (paid_through, keyed by receipt last4). No last4 collisions across the two entities' cards.
- Grid uses `coa=None` (matches `posting_category`); the export resolves against the chart. Account agrees for the card/default cases; only the resolved-string canonicalization can differ, same as `posting_category` already accepts.
- A manual `paid_through` override is baked into `r.paid_through` by `apply_expense_edits`; `build_expense_view` passes the field-override explicitly so the source labels "override", not "receipt".
- Fly deploy runs from a clean origin/main worktree (`agentic-ops1-deploy`), pre-authorized post-merge.

### Reference Materials
- PR #467 (card resolution), PR #470 (grid provenance)
- Lovable prompt lives in this session's conversation (not filed; regenerate from this checkpoint if needed)

---

## How to Continue
`/resume brisken`, read the p1 status. The backend is done + live; the open work is the Lovable SPA build from the delivered prompt, then a real-receipt end-to-end check.

---

## Strategic Feedback

### What Worked Well This Session
- Enumerating the existing surface before building (B7): the OCR already read the card, `card_accounts` already existed, so the "feature" was a 4-file wiring rather than a build. Verifying that first avoided reinventing what was there.
- Two tight ship + deploy cycles with a byte-identical-export guarantee (the delegation refactor) kept a live financial tool safe while adding the provenance the SPA needs.

### Suggestions
- The receipt-first SPA (Phase 7) is now the sole thing between this backend and Criss using it; SPA repo access is the highest-leverage next unlock.

### System Health
- Autonomy: ~5 human touches — 2 B1 hook catches on closing-deferrals, plus 3 owner design refinements (simplify the jargon, "could Criss just decide?", the card-number insight). The refinements were productive collaboration, not corrections; the 2 B1 hits are the recurring closing-deferral authoring habit the gate keeps catching.
- Friction register at ~413 KB (over the 200 KB advisory) — archive deferred to keep this checkpoint PR focused; run `checkpoint_scaffold.py archive-register` in a following docs PR.
