# Checkpoint: Brisken Expense-Recon Fly UI Deletion + Deploy

**Date:** 2026-07-22
**Status:** SHIPPED AND LIVE. The Jinja HTML UI is deleted (PR #350, merged CI-green) and deployed to Fly v31 on the owner's order; the live origin is API-only and the SPA is the one review surface. The shared-clone mess from the failed attempt is fully reconciled.

---

## Summary

Undid the shared-clone damage the 2026-07-22 SPA-cutover session left behind (16 dirty + 19 untracked ledger entries blocking `git pull`, two stray clones, four orphaned dev-server processes), then redid the Fly HTML-UI deletion ast-first from the checkpoint's verified manifest, rewrote the test suite onto the `/api` surface (712 green), shipped it as PR #350, and deployed to Fly v31 with live verification.

---

## What Was Done This Session

### Task 1 — shared-clone reconciliation (unblocked other people)
1. Verified sibling sessions quiet (only a gitignored context YAML written in the prior 20 min), then diffed every one of the 19 untracked files against origin/main before touching it: 16 byte-identical, 2 session logs strict subsets of main (main carried the sibling's Upwork-Independence blocks), 1 identical modulo CRLF. Deleted all 19.
2. The 16 dirty tracked files: 13 already matched origin/main byte-for-byte, 3 (INDEX, friction-register, p1 status) strictly older than main. Synced and fast-forward pulled clean. origin/main moved mid-operation (sibling merges #338-#341); re-fetched and re-verified against the new tip rather than pulling blind.
3. Deleted `C:\br-v2`; `C:\br-spa` was pinned by four orphaned `npm run dev`/Vite processes from the failed session (found via `Win32_Process` after "Device or resource busy") — killed them, then removed the dir.

### Task 2 — the deletion, ast-first (PR #350)
4. Wrote an ast-based deletion script (scratchpad, ephemeral): exact decorator/function ranges from `lineno`/`end_lineno`, every manifest target asserted to match exactly once, ranges asserted non-overlapping, output re-parsed before writing. All 31 targets hit: 17 whole route blocks + 14 bare decorators. The multi-line-signature failure mode of the previous attempt is structurally impossible this way.
5. Collapsed `_wants_json` (deleted — `/api` is the only surface), `_not_found` JSON-only, deleted `_render_form_error` / `_operator_home_ctx` / `_user_home_ctx` / `_template_globals` / Jinja setup / `templates/` (12 files) / `static/` (4 files); dropped the `jinja2` dependency; deleted `_visible_run` (operator-only means `get_run`); dropped now-unused `request` params.
6. Stripped role plumbing: `ROLE_USER`, `code_role`'s user branch, `_OPERATOR_RULES`, `path_requires_operator`, `access_code()`, `OPEN_PREFIXES`, cookie-issuing helpers. Middleware is now: gate on -> valid token (bearer, legacy cookie accepted) or JSON 401. **Safety check first (B7):** `flyctl secrets list` proved `EXPENSE_RECON_ACCESS_CODE` was never set on Fly, so keying `gate_enabled()` on `EXPENSE_RECON_OPERATOR_CODE` alone changes nothing live.
7. Intake sync seam answers JSON `{run_id}` instead of a 303 to the deleted workbench; `serve.py` opens `/docs`; module docstring + README rewritten to the API-only surface.
8. Verified by enumeration: imported the rebuilt app, listed its route table — exactly the KEEP set (all `/api/*`, `/healthz`, `/jobs/{id}`, `/feedback.jsonl`, 4 downloads). app.py 1518 -> 1071 lines.

### Task 3 — tests (the larger half, as predicted)
9. Real blast radius was ~20 files / 132 failures, not just the named 9. Deleted `test_web_roles`, `test_web_api_twins`, `test_web_guides` (surviving concerns folded into rewritten auth/intake/memory/publish tests). Rewrote the rest onto `/api`: run creation via `POST /api/runs` -> `/jobs/{id}` poll (TestClient finishes background tasks before the response returns), HTML-page assertions became render-model assertions (`status`, `charge_category`, `n_learned_lines`, `duplicate_groups`).
10. Full suite **712 passed, 2 skipped, 0 failed** (772 baseline minus exactly the deleted HTML surface).

### Ship + deploy
11. PR #350 merged CI-green (Band 2); PR #351 fixed the duplicate YAML frontmatter #330's union-merge left in `docs/sessions/2026-07-21.md`.
12. On the owner's explicit "deploy": `flyctl deploy` from a clean detached origin/main worktree -> **Fly v31**. Live verification: `/healthz` 200; `/` and `/login` answer JSON 401 (HTML gone); `/api/runs/x` unauthenticated 401; `/api/login` wrong-code 401; CORS preflight reflects `brisken-reconcile-dash.lovable.app` exactly.
13. Memories updated (`project_brisken_expense_recon_review_surface`, `_lovable_frontend`, MEMORY.md index) to the deployed API-only state.

---

## Key Decisions Made

### Deploy now, on owner order
- **Choice:** the brief gated the deploy on "Criss confirmed on the SPA"; the owner's follow-up message ordered "deploy". Deployed v31.
- **Rationale:** an explicit owner order supersedes the earlier gate (and Fly deploys are permanently pre-authorized). Rollback is one `flyctl releases` redeploy of v30 if Criss surfaces on the old UI.

### access_code() deleted only after enumerating live secrets
- **Choice:** verify `flyctl secrets list` BEFORE stripping the env var from `gate_enabled()`.
- **Rationale:** if prod had keyed the gate on `EXPENSE_RECON_ACCESS_CODE`, the strip would have silently DISABLED auth on a tool holding bank data. It never was set, so the strip is behavior-neutral. Enumerate-before-build applied to a security boundary.

### Leave the sibling's fresh WIP alone
- **Choice:** after the merges, the shared clone had NEW dirty ledger files (a live health-pass session). Did not reconcile those; left the clone at its last clean fast-forward.
- **Rationale:** that is active work, not stale mess — exactly the clobber Task 1 existed to avoid. The sibling ships its own ledger.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `.../expense-reconciliation/src/expense_recon/web/app.py` | Modified | 31 route deletions + collapse; 1518 -> 1071 lines |
| `.../web/auth.py` | Rewritten | operator-only gate (101 lines) |
| `.../web/serve.py` | Modified | API wording; opens `/docs` |
| `.../web/templates/` (12), `.../web/static/` (4) | Deleted | the HTML surface |
| `.../pyproject.toml`, `uv.lock` | Modified | jinja2 dropped |
| `.../README.md` | Modified | API-only surface documented |
| `.../tests/` (3 deleted, ~18 rewritten incl. conftest) | Modified | suite on `/api`; 712 green |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | Modified | deletion row (deploy state bumped in follow-up PR) |
| `docs/sessions/2026-07-21.md` | Modified | frontmatter dedupe (PR #351) |
| memories: review_surface, lovable_frontend, MEMORY.md | Modified | deployed API-only state |
| Shared clone: 19 untracked removed, 16 dirty synced, `C:\br-spa` + `C:\br-v2` deleted | Cleanup | Task 1 |

---

## Current Status

- **Live:** `brisken-expense-recon.fly.dev` = Fly v31, API-only, gate on, verified by unauthenticated probes + CORS preflight. The SPA `brisken-reconcile-dash.lovable.app` is the only UI.
- **main:** PR #350 + #351 merged; `origin/main` app.py verified (parses, 1071 lines, no `_wants_json`).
- **Shared clone:** clean of the old mess; holds a live sibling's fresh WIP (their ledger, their PR).
- Platform: custom FastAPI/Fly build (tier "unknown" in infrastructure.yaml — no workflow-engine op count; assessed 2026-05-24).

## Next Steps

1. Confirm with Criss (via Dirk) that she is on the SPA; if she surfaces on the old UI instead, rollback = redeploy v30 (`flyctl releases`).
2. `/api/login` rate limit + the single shared operator code as the whole security boundary — open hardening item, now the top remaining risk on a tool holding bank statements.
3. Second-chance unmatched pass (`matching.llm_second_pass_unmatched`, ships OFF) — evaluate against the 6 labeled bundles (queued optimize candidate).
4. Zoho journal export idempotency (§4.8) still open in BLUEPRINT Phase 5.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/status/p1-expense-reconciliation.md` (roll-up)
- `.../automations/expense-reconciliation/src/expense_recon/web/app.py` (the API-only surface)
- Memory: `project_brisken_expense_recon_review_surface`, `project_brisken_expense_recon_lovable_frontend`

### Open Questions
- Has Criss actually used the SPA yet? (Joint call with her still unscheduled; Dirk to brief.)

### Working Notes (do not re-derive)
- **The ast pattern that worked:** parse once, map `(method, path)` from each `@app.<method>("<path>")` decorator via ast, whole-block delete = min(decorator lineno)..func.end_lineno, bare-decorator drop = that decorator's own lineno..end_lineno, assert every target matched exactly once + ranges disjoint, delete bottom-up, re-parse before write. 31/31 first try.
- **Test-suite conversion key:** `POST /api/runs` is always async, but Starlette's TestClient runs background tasks before the response returns, so `POST -> GET /jobs/{job_id} -> run_id` is synchronous in tests; no sync seam needed. The intake sync seam (`EXPENSE_RECON_WEB_SYNC=1`) survives only on `/api/intakes/{id}/run` and now answers `{run_id}` JSON.
- **Render-model fields used by the rewritten tests:** rows carry `status` (decision), `charge_category`, `has_learned`, `disposition`, `section`; summary carries `ai_unavailable`, `n_learned_lines`, `ready_to_post`; top level carries `llm_enabled`, `duplicate_groups`.
- **Fly secrets (names):** `EXPENSE_RECON_OPERATOR_CODE`, `EXPENSE_RECON_AUTH_SECRET`, `OPENAI_API_KEY` — no ACCESS_CODE, ever.
- **Session-log fan-out is live (#349):** write per-session shards `docs/sessions/YYYY-MM-DD-<slug>.md`; the nightly sweep folds + renumbers. Do not append to the daily file from a shared tree.

### Reference Materials
- PRs: agentic-ops1.01 #350 (deletion), #351 (frontmatter fix)
- https://brisken-expense-recon.fly.dev (v31) · https://brisken-reconcile-dash.lovable.app
- Prior checkpoint: `docs/2026-07-22 - Brisken Expense-Recon SPA Cutover + Fly UI Deletion Attempt/`

---

## How to Continue

Nothing is mid-flight. The next expense-recon work is either the hardening item (login rate limit) or the queued matching-accuracy optimize run; both start from a fresh worktree off origin/main. If Criss reports anything odd in the SPA, check the Fly logs first (`flyctl logs -a brisken-expense-recon`) — the backend contract her SPA uses is exactly the enumerated `/api` table in app.py's docstring.

---

## Strategic Feedback

### What Worked Well This Session
- The previous session's checkpoint carried the verified deletion manifest and the precise failure mode. Re-derivation cost: zero. The whole source edit landed in one pass because the expensive thinking was already banked.
- Diff-before-delete on every reconciliation file. The two session logs LOOKED like duplicates and were actually subsets; blind deletion would have been safe only by luck.

### Suggestions
- The 3-iteration limit + clean revert in the failed session is what made this session cheap: a broken half-fixed app.py would have cost far more than the reset did. Worth keeping as the default response when the instrument (not the plan) is wrong.

### System Health
- The suite for this module still is not in CI (platform + hooks only) — every expense-recon gate remains a local pre-ship discipline. With the HTML tests gone and the suite at 712/16s, a CI job is now cheap; recurring open decision, third checkpoint mentioning it.
- Autonomy score: 0 human interventions this session (two owner directives, zero corrections).
