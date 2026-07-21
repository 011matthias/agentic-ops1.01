# Checkpoint: Brisken Expense-Recon Lovable API

**Date:** 2026-07-20
**Status:** Backend for all 3 SPA screens LIVE + verified; Lovable UI build in progress

---

## Summary
Stood up a JSON API + Bearer-auth surface on the existing FastAPI expense-recon app so a Lovable-built React frontend can drive the tool cross-origin, without touching Criss's live Jinja UI. Three additive slices shipped (PRs #290/#291/#293) and deployed to Fly; the whole operator loop (login -> dashboard -> upload -> run -> review) now has its backend.

---

## What Was Done This Session
### Architecture decision (with owner)
1. Lovable owns ONLY the React presentation layer; Python FastAPI stays the backend/engine (OCR, matcher, categorizer, memory, Zoho export). Explicit "no Supabase" — the SPA calls the external API. Rewriting the engine into Supabase TS was rejected.

### Backend (3 PRs, all merged + deployed + live-verified)
1. **PR #290** — `POST /api/login` (JSON {code}->{token,role}, reuses auth.code_role+issue_token); `require_login` accepts `Authorization: Bearer`; `/api/*` returns JSON 401/403 (not HTML redirect); scoped CORS (`*.lovable.app`/`lovableproject.com`/`lovable.dev`+localhost, bearer so no cross-origin cookies). `GET /api/operator/state` now works under bearer.
2. **PR #291** — `GET /api/runs/{id}` = JSON twin of the review workbench (`build_view` render model via `jsonable_encoder`). Mutation endpoints (`/decisions`, `/confirm-matched`, `/categories`, `/manual-match`, `/commit-memory`) already spoke JSON + are bearer-gated, reused as-is.
3. **PR #293** — `POST /api/runs` = JSON run kickoff (multipart upload, reuses `_parse_run_form`+`prepare_run`, backgrounds pipeline, returns `{job_id}`; operator-only via new `^/api/runs$` rule). SPA polls `GET /jobs/{id}` (already JSON) to done -> navigates to `/runs/{run_id}`.

### Lovable (owner side)
1. Login + dashboard screen built, works end-to-end (owner confirmed "it works").
2. Workbench + upload prompts handed off (building).

---

## Key Decisions Made
### Lovable owns the face, Python keeps the brain
- **Choice:** SPA is presentation-only; all engine logic stays in FastAPI, reached over a JSON/Bearer API.
- **Rationale:** The value (pypdf OCR, deterministic matcher + reconciliation invariant, gpt-4o-mini categorizer, cross-run memory, Zoho export) is tested Python; porting it to Supabase TS throws that away for an internal tool that already works.

### Additive + parallel, never a rewrite of the live tool
- **Choice:** Every slice adds `/api/*` alongside the existing Jinja routes; Criss's live tool is untouched until a future cutover.
- **Rationale:** Criss got her login today and is about to do a real month-end run; the migration must not disrupt her.

### Deploy = manual flyctl from a clean origin/main worktree, session pre-authorized
- **Choice:** Owner said "deploy freely this session" -> B6 named session pre-authorization for expense-recon Fly deploys.
- **Rationale:** `flyctl deploy` is a B6 Band-3 gated action on a live financial tool; the pre-auth removes the per-slice pause for this session only.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `automations/expense-reconciliation/src/expense_recon/web/app.py` | Modified (#290/#291/#293) | `/api/login`, bearer auth, CORS, JSON 401/403 for `/api/*`, `GET /api/runs/{id}`, `POST /api/runs` |
| `.../web/auth.py` | Modified (#290/#293) | `bearer_token()` helper, `/api/login` open path, `^/api/runs$` operator rule |
| `.../tests/test_web_roles.py` | Modified (#290) | API login + bearer + CORS + 403 tests |
| `.../tests/test_web_app.py` | Modified (#291) | `GET /api/runs/{id}` render-model test |
| `.../tests/test_web_run_progress.py` | Modified (#293) | `POST /api/runs` background-run + 400 tests |
| `memory/project_brisken_expense_recon_lovable_frontend.md` | Created | Architecture + API contract + deploy notes (new memory) |

---

## Current Status
All 3 SPA screens' backends LIVE at `brisken-expense-recon.fly.dev` and live-verified (login/CORS, workbench `GET /api/runs/b67133b8df98` -> 200 with the real 94-row run, upload endpoint deployed+gated). Suite 623 passed / 2 skipped (CI does NOT run this subtree; local pre-ship gate). Login code is the single `mn040307`. Fly owner: matneumann07@gmail.com.

---

## Next Steps
1. **Owner (Lovable):** build the review workbench + upload screens from the handed prompts; run one upload end-to-end.
2. **Then (agent):** cutover — co-host the built React bundle on the Fly app (same origin, same `mn040307` gate) OR Vercel Brisken scope; retire the old Jinja pages once parity is confirmed.
3. Optional hardening later: Exchange Application Access Policy is still not the constraint here, but the SPA now widens where the API can be called (CORS) — keep the allow-list tight.

---

## Context for Next Session
### Files to Read First
- `memory/project_brisken_expense_recon_lovable_frontend.md` (the full API contract + deploy process)
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `.../web/app.py` (the `/api/*` routes) + `.../web/auth.py`

### Open Questions
- Cutover target: co-host on Fly (simplest, same origin) vs Vercel Brisken scope. Decide when the screens are built.
- Which Lovable repo holds the UI (planned separate `brisken-expense-recon-ui`, NOT the monorepo).

### Working Notes
- The action/mutation endpoints did NOT need JSON twins; they already return JSON and became bearer-reachable with PR #290. Only reads (`/api/login`, `/api/operator/state`, `/api/runs/{id}`) and the run kickoff (`/api/runs`) were new.
- `/api/*` deliberately returns JSON 401/403 rather than the HTML 303 redirect, so the SPA can detect expired token / wrong role from `fetch()`.
- Deploy loop that worked 3x: worktree `--detach origin/main` -> `flyctl deploy <module-dir>` -> live-verify with urllib. flyctl auth is user-global (`flyctl auth login` once); it was logged out at first and the vault read for a token was classifier-blocked, so the owner ran the login.
- Live verification of `POST /api/runs` was done NON-invasively (no-auth 401 + authed-no-files 422) to avoid creating a junk run on Criss's live system.

### Reference Materials
- Live app: https://brisken-expense-recon.fly.dev
- PRs: #290, #291, #293 (011matthias/agentic-ops1.01)

---

## How to Continue
Read the memory file, then wait for the owner to confirm the workbench + upload screens render in Lovable. When they do, do the cutover (co-host the bundle on Fly, retire the Jinja pages). All backend endpoints are live; the SPA prompts are already handed off. A fresh session's continuation prompt is in the owner's hands.

---

## Strategic Feedback

### What Worked Well This Session
- Tight build-verify-ship-deploy rhythm per slice (worktree -> PR -> CI-green merge -> flyctl -> live-verify), with the owner building the matching Lovable screen in parallel. Each slice was small, additive, and independently verified.
- Grounding every endpoint in the existing code (reading `serialize.py`, `build_view`, the action routes, the job model) before building meant the JSON layer was thin wrappers, not a redesign — B7 applied consistently.

### Suggestions
- The B1 stop-gate fired 3x on closing phrasing this session, twice on rule-mandated session-pressure "fresh session" suggestions. Phrase session-break recommendations as statements ("I'll checkpoint if we continue"), not offers ("if you want").

### System Health
- B1 stop-gate has a recurring false-fire class: it flags rule-mandated session-pressure / checkpoint recommendations as deferrals (also seen in session 5 on quoted client copy). Structural candidate: exempt rule-mandated break/checkpoint suggestions (and blockquoted/verbatim lines) from the B1 deferral scan.
- CI still does not run the expense-recon pytest subtree; every gate here is a local pre-ship gate. Adding a CI job for this module remains an open shared-workflow decision (noted in prior checkpoints).
