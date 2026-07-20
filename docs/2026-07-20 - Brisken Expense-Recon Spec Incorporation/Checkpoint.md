# Checkpoint: Brisken Expense-Recon Spec Incorporation

**Date:** 2026-07-20
**Status:** Phase 3 shipped (PR #294 merged); plan approved for §17/§16/§18/§14; API-collision reconciled

---

## Summary

Verified the combined Tier-1 FX + Tier-2 receiptless-categorization build end-to-end on Criss's real April data (no LLM), assessed how far the shipped Brisken tool has diverged from Dirk's functional spec, produced an approved backend plan + a ready-to-paste Lovable frontend prompt for incorporating the remaining spec areas, discovered and reconciled a concurrent-session API collision, and shipped a genuine web-export bug fix found during verification.

---

## What Was Done This Session

### Verification (combined Tier-1 + Tier-2, no LLM)
1. Isolated worktree off origin/main; pulled Criss's April data (94-charge Chase CSV + ER-00215 36 receipts).
2. `calibrate` (Tier-1): 29 matched, invariant OK, 0 double-bound, FX multiplicity 0.11x, refunds bucket present (0 credits this month, correct). 29+17 review+48 unmatched = 94.
3. Full report (Tier-2): all 48 receiptless charges flow through `categorize_charges`; 5 categorized (all ANTHROPIC → Software & Subscriptions via the VENDOR keyword starter map). The other 43 stay blank in no-LLM mode because their vendors (Microsoft, Supabase, ElevenLabs, Lovable, Google Workspace, SAP, LinkedIn, Proton, SaaSRise, Base44) are not in the 13-entry keyword map. `expense-recon memory set` is the no-LLM path to cover them.
4. Suite: 617 passed, 2 skipped.
5. Combined coverage of 94 charges: (a) 29 matched to a receipt, (b) 5 categorized-but-receiptless, (c) 60 unresolved (17 FX-pending + 43 receiptless-uncategorized).

### Divergence analysis vs Dirk's functional spec
- Verdict: divergence from the spec-as-written is large but almost entirely deliberate (owner "working tool" directive). The spec describes a multi-tenant SaaS (Product A); we built a single-tenant Brisken tool (Product B).
- Genuine gaps even for internal use: §17 personal/business/reimbursement (zoho_export treats every line as business), §14 configurable automation, §21.2 receipt-attachment-into-Zoho.
- Areas we exceed the spec: matching/FX engine, cross-run learning.

### Plan + Lovable prompt (approved)
- Wrote the backend plan (phases 1-6) + a full paste-ready Lovable frontend prompt into the plan file. User approved. Decision: stays an internal tool; Lovable owns all UI.

### API collision + reconciliation
- The concurrent sibling session had already built + MERGED the SPA JSON API (`/api` + bearer + CORS, Lovable-hosted; PRs #290/#291/#293) while this session planned/built a competing `/api/v1` + same-origin-cookie surface (Phase 1, verified 646-green via a sub-agent).
- Discarded the `/api/v1` Phase 1 (never pushed); adopted the merged `/api`; corrected the plan + embedded Lovable prompt to bearer/cross-origin/`build_view`-render-model.

### Shipped: web-export Tier-2 drop bug (PR #294)
- Found during verification: `service.regenerate_report/zoho/reconciled/writeback` never passed `charge_categorizations` to their writers (only the CLI did), so web downloads dropped the receiptless-charge categories the workbench shows.
- Fix: new `service._charge_cats(run)` helper threaded into all four `regenerate_*`; zoho also honors the opt-in `zoho.export_receiptless_learned` flag (default off, output unchanged). Regression test `tests/test_web_export_charge_cats.py`. Suite 625 green. Merged on green CI.

---

## Key Decisions Made

### Stay an internal Brisken tool
- **Choice:** Do NOT pursue the multi-tenant SaaS; incorporate only spec areas that bite Brisken's real month.
- **Rationale:** Owner directive; the divergence is correctly-cut scope, not drift.

### Adopt the sibling session's merged `/api` (not my `/api/v1`)
- **Choice:** Discard the `/api/v1` + cookie Phase 1; build on the merged `/api` + bearer + CORS + Lovable-hosted surface.
- **Rationale:** Theirs is merged, coherent, and Lovable-native; a competing surface would fragment the codebase.

### Feature phases, not API rebuild, are the remaining value
- **Choice:** Focus this/next session on §17/§16/§18/§14 (API-convention-agnostic), starting with the verified web-export bug fix.
- **Rationale:** The API is done; the spec-gap features are what remain.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/service.py` | Modified (PR #294) | `_charge_cats` helper; thread charge_categorizations + include_receiptless_learned into all 4 `regenerate_*` |
| `automations/expense-reconciliation/tests/test_web_export_charge_cats.py` | Created (PR #294) | Regression: reconciled CSV carries the LEARNED category; zoho gated on the flag |
| `C:\Users\neuma_p1qrsic\.claude\plans\async-beaming-perlis.md` | Created + corrected | Backend plan (phases 1-6) + paste-ready Lovable prompt; COURSE CORRECTION block adopting `/api` + bearer |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | Add PR #294 row + spec-incorporation / SPA-API note |

Discarded (built then abandoned, never pushed): `web/api.py`, `web/api_models.py`, `/api/v1` edits to `app.py`/`auth.py`, `test_api_v1_*.py`.

---

## Current Status

- **main:** PR #294 merged (`99ed4ee`). The SPA `/api` (bearer/CORS) is on main via the sibling's #290/#291/#293. Brisken expense-recon tool live at brisken-expense-recon.fly.dev (not re-deployed this session — the fix is backend logic; a Fly deploy is a separate gated action).
- **Plan:** approved and corrected at `C:\Users\neuma_p1qrsic\.claude\plans\async-beaming-perlis.md`.
- **Remaining phases:** §17 disposition (Phase 2), §16 export-approved gate (4), §18 duplicate resolve (5), §14 automation (6).
- **Concurrency:** two sessions share this repo and collided once on the API. `service.py`/`build_view`/`store.py` are the shared-risk files for the remaining phases.

---

## Next Steps

1. **Phase 2 (§17 disposition)** on a fresh worktree off current `main`, per the plan: `decisions.disposition` column + `zoho_export` branching (skip personal/do-not-export, redirect reimbursable credit) + `reconciled_csv`/`report_xlsx` column + `POST /api/runs/{id}/disposition`. Seed default from `Receipt.reimbursable`.
2. Then Phase 4 (export-approved gate), Phase 5 (duplicate resolve), Phase 6 (automation, optional).
3. **Before any build: `git fetch origin main` + `git log <base>..origin/main --oneline`** to see what the sibling merged (the miss that caused the collision).
4. Coordinate file-area with the sibling session (they own `/api`/`app.py`; take `store.py`/`output/*`; rebase before shipping anything touching `service.py`/`build_view`).
5. User action still open (not agent-doable): register the notifier schtasks task on the dev box (PR #288).

---

## Context for Next Session

### Files to Read First
- `C:\Users\neuma_p1qrsic\.claude\plans\async-beaming-perlis.md` (the plan + Lovable prompt; read the COURSE CORRECTION block first)
- `workspace/clients/brisken/automations/expense-reconciliation/BLUEPRINT.md` ("Using-the-data revision 2026-07-20" + LD-5)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/{service.py,app.py,auth.py,store.py,serialize.py}`

### Open Questions
- Which auth/deploy model is canonical long-term? The merged one is bearer + CORS + Lovable-hosted; my plan had argued same-origin cookie for financial-data safety. Adopted the merged one; the security trade (token in JS storage vs cookie) is noted but not re-litigated.
- How should the two concurrent sessions divide this module to stop colliding?

### Working Notes
- No-LLM Tier-2 coverage on Criss's April month is 5/48 (only Anthropic hits the keyword map). Seeding ~10 recurring SaaS vendors via `expense-recon memory set` would take it from 5 to most of 48 without paying for the LLM.
- The merged `/api`: `POST /api/login` returns a bearer token; middleware accepts cookie OR bearer; `GET /api/runs/{id}` returns `jsonable_encoder(build_view(...))` (display-formatted amounts); existing `/runs/{id}/decisions|categories|manual-match|...` already accept JSON and are reused.
- CI ruff only checks `tools .claude/hooks tools/tests` (ci.yml:44) — the client module is NOT ruff-gated. Pre-existing F401s in service.py (STATUS_REJECTED, date) are not ours.
- Test data survived in the worktree at `workspace/clients/brisken/context/expense-reconciliation/expense-reports/csv/by-month/01-04-2026_ER-00215/` (gitignored; won't carry to a new worktree — re-copy or re-pull).

### Reference Materials
- PR #294: https://github.com/011matthias/agentic-ops1.01/pull/294
- Sibling API PRs: #290, #291, #293
- Memories: project_brisken_expense_recon_testing_loop, project_brisken_expense_recon_chris_process, project_brisken_expense_recon_review_surface

---

## How to Continue

Paste the handoff prompt (written this session, in the final chat message) into a fresh chat, OR: read the plan file, `git fetch origin main`, cut a fresh worktree off origin/main, and implement Phase 2 (§17 disposition) as its own PR.

---

## Strategic Feedback

### What Worked Well This Session
- Delegating the two hard designs (backend API + Lovable prompt) to parallel Plan agents produced a strong, grounded plan fast; delegating the Phase 1 build to a sub-agent kept the main context clean.
- Independently re-running the suite + reviewing the risky diff (not trusting the sub-agent's "646 green" report) caught the need to reconcile the diff-vs-origin/main confusion, and confirmed integrity.

### Suggestions
- When running two sessions on the same client module, divide by file-area up front (one owns the API/app.py, the other owns store/output/service features) and agree a "fetch + git log origin/main before building" ritual. This session lost a full Phase 1 build to a concurrent API collision.

### System Health
- **Recurring class: concurrent-session collisions on shared state.** Third instance in a week (2026-07-13 rollback-reverted-concurrent-work, 2026-07-14 session-log drift, today's duplicate API build). The SessionStart `sibling-session-gate.py` warns a session shares the tree but does not force a re-check of `origin/main` before a build. Structural candidate: extend it to flag "origin/main advanced N commits since session start — inspect before building." Enumerate-before-build (B7) is the right gate but depends on recall.
- Autonomy score: 1 friction event (self-detected duplicate `/api/v1` build), 0 direct human corrections on execution (the user's Lovable-direction clarification was a design answer, and the one deferral-offer was hook-caught then acted on).
