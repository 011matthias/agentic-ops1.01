# Checkpoint: Brisken Expense-Recon Lovable Extend + Spec-Backend Deploy

**Date:** 2026-07-21
**Status:** Merged §16/§17/§18 + settings backend DEPLOYED + verified live; Path-1 (extend current SPA) chosen; corrected increment prompts handed; `/api/memory` still to build

---

## Summary
Continued the Brisken expense-recon → Lovable frontend work. Mid-session discovered that a parallel "Spec Incorporation" workstream had already advanced `origin/main` well past the baseline I was working from (built §16/§17/§18 + `/api/settings` and written a full but architecturally-mismatched Lovable prompt). Reconciled, chose to keep and extend the existing SPA (Path 1), deployed the merged-but-undeployed backend to Fly (verified live, DB migration safe on Criss's data), and handed corrected increment prompts wired to the now-live `/api`.

---

## What Was Done This Session
### Frontend planning + prompts (Lovable SPA `brisken-expense-review`)
1. Verified the SPA↔backend contract against the live API (login, run detail shape, `VALID_STATUSES`) — the workbench + upload screens are correctly wired.
2. Found the Lovable app is **TanStack Start** (SSR scaffold, not a static bundle); confirmed the cutover is separate-origin (Lovable-hosted), CORS already allows `*.lovable.app` (empirically tested live). Custom domain (`recon.brisken.com`) would need one CORS-add + DNS.
3. Ran a full **parity audit** (Jinja tool vs SPA) and extracted the UI necessities from Dirk's functional spec.
4. Pulled the **live feedback-log** (7 entries) and triaged; Criss's "receipt photo must be available" (#3) and the "feels backwards / need Settings + master-data" operator notes (#4/#5/#6) folded into the prompts/guide.
5. Handed a **branding prompt** + the real Brisken logo assets (`web/static/brisken-logo-{light,dark}.png` 292×64, `favicon.png` 150×150, `tokens.css` palette) for a theme-aware logo + favicon + Brisken color system.
6. Handed the migration prompts (downloads helper, forget, drop-intake, commit-button bug fix) and, post-reconciliation, corrected increment prompts for **disposition, duplicates+resolve, settings**, plus a trilingual **Guide** page adapted to the new SPA flow.

### Reconciliation (the pivot)
7. Discovered via a worktree checkout that `origin/main` was at `#299` (24 commits ahead of local `main`): a parallel workstream shipped §16 export-gate (#297), §17 disposition (#296), §18 duplicate surfacing+resolve (#298), `/api/settings`, plus an approved-but-contradictory Lovable prompt (`.claude/plans/async-beaming-perlis.md`, still worded for `/api/v1`+cookie+serve-from-Fly).
8. Chose **Path 1: extend the current SPA** (keep `brisken-expense-review`, wire the shipped backend) over rebuilding from the plan's prompt.

### Backend deploy (Step 1 of Path 1)
9. Cut a clean detached `origin/main` worktree, ran the **full suite (670 passed / 2 skipped)** — the merged spec-incorporation code's real verification (CI does not run this subtree), then `flyctl deploy` to `brisken-expense-recon` (fra).
10. **Verified live:** `GET /api/settings` → 200 `{export_approved_only:false}` (was 404); run detail carries `duplicate_groups` + row `disposition`/`disposition_default:"business"`; Criss's 94-row run intact after the idempotent DB migration.

---

## Key Decisions Made
### Path 1 — extend the current SPA (not rebuild from the plan)
- **Choice:** Keep `brisken-expense-review` (built + branded); wire the shipped `/api` backend via incremental prompts; borrow the plan's feature detail but point it at the real `/api`+bearer.
- **Rationale:** The plan's prompt is comprehensive but written for a discarded architecture (`/api/v1` + same-origin cookie + serve-from-Fly) and would throw away the working, branded SPA. The adopted architecture (`/api` + bearer + Lovable-hosted) matches both the shipped backend and this session's cutover decision.

### Deploy the merged backend to make §16/§17/§18 live
- **Choice:** Deploy `origin/main` (after a self-run full suite) so disposition/duplicates/settings go live; verify existing data survived the migration.
- **Rationale:** Path 1 needs those endpoints live for the SPA to wire them. Inert-by-default design + full green suite + post-deploy verification made it safe on Criss's live tool.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| (Fly `brisken-expense-recon`) | Deployed | Brought live app from ~#293 to `origin/main` #299 (§16/§17/§18 + settings + web-export fix live) |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | SPA-extend plan + deploy note |
| `docs/2026-07-21 - .../Checkpoint.md` + session log + context YAML + INDEX + friction-register | Created/Updated | Ledger |

No repo source files were edited this session; deliverables were live-verified analysis + Lovable prompts + a deploy of already-merged code.

---

## Current Status
- Live app `brisken-expense-recon.fly.dev` now serves `origin/main` #299: §16 export-gate, §17 disposition, §18 duplicates+resolve, `/api/settings` all live and verified; login code `mn040307`.
- The Lovable SPA (`brisken-expense-review`) is separate-origin/Lovable-hosted; login/dashboard/workbench/upload built; branding + migration prompts in flight on the user's side.
- Two concurrent sessions share this module (active `agentic-ops1-recon` worktree seen); 3 collisions in a week.

---

## Next Steps
1. **Build `/api/memory` + `/api/memory/forget`** (the one missing backend for the SPA memory screen) — FIRST `git fetch origin main` + `git log` to confirm the parallel session hasn't touched `app.py`/`auth.py`; then PR + deploy. Coordinate file-area (they own `app.py`/`api`; the memory route is a small additive edit there — confirm no in-flight collision).
2. User (Lovable): apply the corrected increment prompts — disposition, duplicates+resolve, settings, receipt pane (Criss #3), guide — against the now-live `/api`.
3. Decide the SPA's production URL: Lovable URL now, or `recon.brisken.com` later (I own CORS-add + GoDaddy DNS; user attaches the domain in Lovable).
4. Deferred (need new backend): full Settings/master-data (legal entities/banks/currencies/FX, feedback #5), Zoho Expense auto-pull + manual add-receipt (feedback #6), §14 automation (plan Phase 6).

---

## Context for Next Session
### Files to Read First
- `memory/project_brisken_expense_recon_lovable_frontend.md` (API contract + deploy process)
- `.claude/plans/async-beaming-perlis.md` (the parallel workstream's plan + its Lovable prompt — read the COURSE CORRECTION block; body still says `/api/v1`+cookie, superseded)
- `docs/2026-07-20 - Brisken Expense-Recon Spec Incorporation/Checkpoint.md`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `.../web/app.py` (new `/api` routes: disposition, duplicates/resolve, settings) + `.../web/service.py` (build_view)

### Open Questions
- How do the two concurrent sessions divide this module to stop colliding? (`app.py`/`api` vs `store`/`service`/`output`.)
- SPA production URL: Lovable URL vs `recon.brisken.com`.

### Working Notes
- **Live `/api` surface (verified):** `POST /api/login`→{token,role}; bearer on all `/api/*`; `GET /api/runs/{id}` = `jsonable_encoder(build_view)` render model (`rows[]` with `disposition`/`disposition_default`, `duplicate_groups`, `candidates[]`, `unmatched_receipts[]` carrying `receipt_url`/`has_receipt_image`/`line_items`/`reference`); mutations `/runs/{id}/{decisions,confirm-matched,categories,manual-match,forget,commit-memory}`; `POST /api/runs/{id}/disposition` {transaction_id, disposition∈business|personal_on_business_card|reimbursable_personal|do_not_export}; `POST /api/runs/{id}/duplicates/resolve` {group_id, action∈ignore|confirmed}; `GET/PUT /api/settings` {export_approved_only}; downloads at ROOT `/runs/{id}/{zoho.csv,report.xlsx,reconciled.csv,statement-categorized.xlsx}` (bearer, cross-origin OK — NOT under `/api`).
- Receipt image preview uses `receipt_url` (may be Zoho-hosted; browser-loadability unverified — needs a real receipt-bearing run to confirm).
- `/api/memory` does NOT exist; `build_memory_view` returns `{categories:[{entity,vendor,category,zoho_account,count,last}], aliases:[{entity,stmt,receipt,count}], fx:[...], counts, total}` — the shape to serialize.
- Windows worktree gotcha: full checkout hits MAX_PATH on a deep SAP PDF; use `git -c core.longpaths=true worktree add C:/<short>` (a scratchpad-deep path fails).
- Deploy loop that worked: detached `origin/main` worktree → `uv run --extra dev --extra web pytest` → `flyctl deploy` (authed matneumann07) → urllib live-verify → `worktree remove`.

### Reference Materials
- Live app: https://brisken-expense-recon.fly.dev · SPA repo: `011matthias/brisken-expense-review`
- Recent origin/main: #294 web-export fix, #296 §17, #297 §16, #298 §18, #299 test fixture

---

## How to Continue
Read the memory + the plan file. To build `/api/memory`: fetch origin/main, confirm no sibling edit in `app.py`/`auth.py`, cut a fresh `client/brisken/...` worktree off origin/main (longpaths + short path), add `GET /api/memory` (jsonable_encoder(build_view_memory)) + `POST /api/memory/forget` (reuse `forget_memory_vendor`) operator-gated, test, PR, deploy. Otherwise: the corrected increment prompts (disposition/duplicates/settings/receipt/guide) are ready for the user to paste into Lovable against the live `/api`.

---

## Strategic Feedback

### What Worked Well This Session
- Reconciling BEFORE building: the worktree checkout surfaced the 24-commit gap and the parallel workstream, which stopped a duplicate `/api/memory` build and a stale prompt from shipping. Reading the sibling's checkpoint + plan turned a near-collision into a clean Path-1 decision.
- Deploy discipline: self-running the full 670-test suite (since CI skips this subtree) + post-deploy live verification (new endpoints AND existing-data-intact) gated a live financial-tool deploy correctly.

### Suggestions
- When resuming a hot client module, `git fetch origin main` + `git log local..origin/main` should be step zero — before any audit/prompt work. This session produced a parity audit + a prompt against stale state (#294) because origin/main had silently advanced to #299.

### System Health
- **Recurring: concurrent-session / origin-main-advanced collisions.** Fourth-ish instance in ~10 days; the prior checkpoint already proposed a SessionStart gate ("origin/main advanced N commits since session start — inspect before building") and it remains unbuilt → `infrastructure-deferred`. Build it.
- **B1 stop-gate phrasing false-fires** continued (delivered-artifact "if you want the file too", decision-point framings). Known class; the exemption for genuine decision-points/verbatim lines is still not implemented.
- Autonomy score: 2 human interventions (both design decisions the user made: the cutover-target and the Path-1 fork) + several B1 hook phrasing self-corrections. No execution corrections.
