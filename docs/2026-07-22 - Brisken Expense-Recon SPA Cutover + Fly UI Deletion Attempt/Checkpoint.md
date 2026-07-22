# Checkpoint: Brisken Expense-Recon SPA Cutover + Fly UI Deletion Attempt

**Date:** 2026-07-22
**Status:** SPA is at parity and LIVE in production; Criss can move. The Fly HTML UI deletion was attempted, hit the 3-iteration limit, and was cleanly reverted — it needs a fresh session with an ast-based approach.

---

## Summary

Audited the Lovable SPA against the `/api` surface that #317/#318 shipped, found it
could not reach any run at all, fixed that plus five missing surfaces, and got it
verified end-to-end on the production Lovable origin. Then attempted the Fly HTML UI
deletion, broke `app.py` with line-based scripted surgery, hit the iteration limit and
reset. Also batched two days of ledger backlog, merging rather than clobbering sibling
work.

---

## What Was Done This Session

### The audit found something the brief did not expect
1. The workbench mutations were **already wired** (confirm/reject, pick-a-candidate,
   recategorize, manual-match, commit-to-memory, disposition, forget). The brief assumed
   these were the gap; they were not.
2. **The real blocker: no run was reachable.** The dashboard rendered only
   `published_runs`, which was empty (live: `operator_runs=2, published_runs=0`), while
   `operator_runs` and `intakes` were fetched and discarded. No route listed runs. After
   a run finished you landed on the workbench once via the poller and could never return.
3. **And nothing could become published.** `publishRun` was imported by zero components
   AND pointed at the bare `/runs/{id}/publish`, which 303s on success — `fetch` follows
   to HTML and `res.json()` throws. The two conditions propped each other up.

### SPA work (brisken-expense-review #1, merged + published)
4. All-runs table with publish/unpublish + Open; queued-uploads table; publish control in
   the workbench summary bar.
5. Eight bare-path calls moved to `/api` (decisions, confirm-matched, categories,
   manual-match, commit-memory, forget, feedback, publish/unpublish). Seven worked by
   luck; `_not_found` returns HTML on the bare path so 404s surfaced as a generic
   "Request failed (404)". These are also exactly the routes the deletion collapses.
6. New surfaces for backend that had shipped without one: §18 duplicate resolve, §16
   export-approved + memory reset (`/settings`), `/compare`, intake queue
   (`/intakes/$intakeId`), and WS3's `card_pct` on every candidate.
7. **Two latent bugs found en route.** The duplicates panel read `duplicate_charges` as a
   flat list when the backend returns a list of GROUPS, so every cell rendered blank.
   And "Use AI categorization" defaulted unchecked while
   `want_llm = form.use_llm or _default_llm_on()` means the box can only force it ON —
   unchecked was a lie.

### SPA affordance fix (brisken-expense-review #2, merged + published)
8. Lovable's design pass collapsed the publish control to one button reading "Published",
   which reads as a status badge while the workbench one click away says "Unpublish" for
   the identical action. Split state from action.

### Backend (agentic-ops1.01 #323, merged + DEPLOYED)
9. `map_card` override. WS3's `guess_column_map` claims the card column from tight
   patterns; there was no escape hatch on either surface, so a statement spelling the
   header anything else silently lost card scoping. 6 new tests; suite 766 -> 772.

### Ledger (agentic-ops1.01 #330, merged)
10. 12 checkpoint folders, both session logs, INDEX rows, 27 friction lines — batched from
    an isolated worktree after the shared clone went quiet for 25 minutes.
11. **`INDEX.md` and `sessions/2026-07-21.md` were MERGED, not copied.** Both had diverged
    in two directions: main carried a sibling's committed Upwork-Independence row and
    session block, the working tree carried five Brisken sessions. A straight copy — the
    obvious move — would have reverted the sibling's work. Caught by diffing before
    committing (`-13` lines, `-1` row).

### Fly UI deletion — ATTEMPTED AND REVERTED
12. Route removal itself worked: all 31 targets hit (14 bare decorators dropped, 17 whole
    blocks removed), leaving a clean `/api/*`-only surface.
13. Then it broke. See "The failed approach" below. Reset, worktree removed, nothing
    committed, nothing deployed. `origin/main`'s `app.py` verified intact (parses, 1518
    lines, `_wants_json` still present).

---

## Key Decisions Made

### Lovable URL now, custom domain later
- **Choice:** ship on `brisken-reconcile-dash.lovable.app`.
- **Rationale:** the backend CORS regex already covers `*.lovable.app`; zero infra work.
  Verified: the preflight reflects that exact origin.

### Fly deploys permanently pre-authorized (owner order)
- **Choice:** `flyctl deploy` no longer needs a per-session order.
- **Consequence:** saved as `feedback_fly_deploy_preauthorized`. Scoped to DEPLOYS only —
  real sends, campaign activation, Graph writes and prod mutations keep their own gates.

### Stop the deletion rather than push through
- **Choice:** reset at the 3-iteration limit instead of a 4th patch.
- **Rationale:** the instrument was wrong, not the plan. Grinding it out at the end of a
  long session, on the tool Criss is about to depend on, is how a broken deploy happens.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| SPA `src/lib/api.ts` | Modified | 8 paths -> `/api`; `card_pct`; `resetMemory`; intake chain; duplicate-group types |
| SPA `src/components/OperatorDashboard.tsx` | Modified | all-runs + intake tables, publish/unpublish |
| SPA `src/components/RunWorkbench.tsx` | Modified | publish, duplicate-group resolve, `card_pct` |
| SPA `src/components/{SummaryBar,DashboardHeader,NewReconciliation}.tsx` | Modified | publish control, nav, LLM checkbox truth |
| SPA `src/components/{SettingsScreen,CompareScreen,IntakePrepare}.tsx` + routes | Created | §16, compare, intake queue |
| `.../web/app.py`, `service.py` | Modified | `map_card` through 3 run entry points; `STATEMENT_MAP_FIELDS` |
| `.../tests/test_web_card_column_override.py` | Created | 6 tests incl. the empty-override no-op |
| `docs/INDEX.md`, `friction-register.md`, `sessions/2026-07-2{1,2}.md`, 12 checkpoint folders | Merged | ledger backlog (#330) |
| `memory/feedback_fly_deploy_preauthorized.md`, `reference_lovable_merge_is_not_live.md` | Created | standing authorization; the merge-≠-live trap |

---

## Current Status

- **SPA LIVE and verified in production** at `brisken-reconcile-dash.lovable.app`:
  login -> both real runs listed (134 and 94 tx) -> workbench 94 rows ->
  `POST /api/runs/b67133b8df98/publish` 200 with preflight -> published table filled ->
  unpublished -> server confirmed back to zero. Brisken run data untouched.
- **Backend** `brisken-expense-recon.fly.dev` machine v30, `map_card` live, proven by
  executing the deployed module (`STATEMENT_MAP_FIELDS` includes `card`).
- **Deletion NOT started** in any committed form. `origin/main` is clean.

---

## Next Steps

1. **Undo the mess this session left in the shared clone** (see Working Notes) — the
   16 dirty `docs/` entries are now committed on main, so a `git pull` there will abort
   with "untracked working tree files would be overwritten".
2. **Redo the Fly UI deletion with `ast`**, not regex. Source edit is ~1/3 of the job.
3. **9 test files** cover the HTML surface and all need rewriting or deleting.
4. Remove the two stray clones at `C:\br-spa` (broken `.git`) and `C:\br-v2`.

---

## Context for Next Session

### Files to Read First
- `.../web/app.py` — the deletion target
- `.../web/auth.py` — role plumbing to strip
- SPA repo `011matthias/brisken-expense-review` @ `main`
- `workspace/clients/brisken/status/p1-expense-reconciliation.md`

### Open Questions
- Has Criss actually switched to the SPA? The deletion should not deploy until she has.
- Second-chance unmatched pass (`matching.llm_second_pass_unmatched`) still ships OFF and
  has one non-result on one month; worth evaluating against the 6 labeled bundles.
- `/api/login` has no rate limit and one shared code is the entire security boundary on a
  tool holding bank statements.

### Working Notes (do not re-derive)

**The failed approach, precisely.** A line-based script found each decorated route and
deleted from its decorator to "the first line with indent <= 4". That is wrong for
handlers whose signature spans many lines: it truncated `POST /runs`, leaving an orphaned
body. The follow-up fix searched for a stray `    ):` and matched the WRONG one, deleting
239 lines including a live handler. Three passes, broken file, reset.
**Use `ast`** — it gives exact `lineno`/`end_lineno` for every decorator and function.

**The verified deletion manifest** (built from the code, keep it):
- *Delete whole:* `GET /login`, `POST /login`, `POST /logout`, `GET /`, `POST /runs`,
  `GET /intakes/{id}/prepare`, `GET /feedback-log`, `GET /compare`, `GET /runs/{run_id}`,
  `GET /help`, `GET /guide`, `GET /how-it-works`, `GET /memory`, `POST /memory/forget`,
  `POST /memory/reset`, `GET /favicon.ico`, `GET /static/{name}` (17 blocks).
- *Drop bare decorator only* (keep the `/api` twin + shared handler, 14): `/intakes`,
  `/intakes/{id}/files`, `/intakes/{id}/run`, `/runs/{id}/publish`, `/unpublish`,
  `/feedback`, `/runs/{id}/decisions`, `/disposition`, `/duplicates/resolve`,
  `/decisions/confirm-matched`, `/categories`, `/manual-match`, `/forget`,
  `/commit-memory`.
- *KEEP:* all `/api/*`, `/healthz`, `/jobs/{job_id}`, `/feedback.jsonl`, and the 4
  download routes (`report.xlsx`, `zoho.csv`, `reconciled.csv`,
  `statement-categorized.xlsx`) — the SPA uses every one.
- *Then:* collapse `_wants_json` (always true once bare paths are gone), delete
  `_not_found`'s HTML arm, `_render_form_error`, `_operator_home_ctx`, `_user_home_ctx`,
  `_template_globals`, the `Jinja2Templates` setup, `_TEMPLATES_DIR`, `_STATIC_DIR`,
  `templates/` (12 files, 2455 lines), `static/` (4 files).
- *Role plumbing:* `ROLE_USER`, `code_role`'s user branch, `_OPERATOR_RULES`,
  `path_requires_operator`, `access_code()`, `OPEN_PATHS`/`OPEN_PREFIXES` entries for the
  deleted routes, `home_user.html`.
- *9 test files touch the HTML surface:* `test_web_app`, `test_web_auth`,
  `test_web_roles`, `test_web_publish`, `test_web_intake`, `test_web_guides`,
  `test_web_feedback`, `test_web_api_twins`, `test_web_expense_report_pdf_upload`.

**The shared-clone hazard I created.** #330 committed content that still exists as
UNTRACKED files in `C:\Users\neuma_p1qrsic\Repo\agentic-ops1`. Confirmed:
`docs/sessions/2026-07-21.md` and the 12 checkpoint folders are on main AND untracked
locally. A `git pull` / `git checkout origin/main` there aborts. `INDEX.md` and
`friction-register.md` are `M` and will conflict. Fix: from that clone, verify each
untracked file matches main's version, then delete the local copies (or
`git checkout -- docs/` after removing the untracked ones) so the tree reconciles. Do it
when siblings are quiet.

**Browser gotchas.** `agent-browser` + `networkidle` never settles on the Lovable page;
use `--time N`. The feedback widget's onboarding card USED to ship a full-screen
`fixed inset-0 z-[70]` backdrop that swallowed every click — Lovable fixed it to a scoped
corner card, verified via `document.elementFromPoint`. Refs shift after any DOM change;
prefer `eval` + row-content selectors over `@eN` for tables.

**Lovable merge ≠ live.** Merging to main syncs the editor only; the published site keeps
serving the last explicitly-published build. Verify with a structural DOM probe, not a
label — the changed control often reads identically in both builds.

### Reference Materials
- https://brisken-reconcile-dash.lovable.app (operator code in vault "Expense Recon App")
- https://brisken-expense-recon.fly.dev — machine v30
- PRs: agentic-ops1.01 #323, #330; brisken-expense-review #1, #2

---

## How to Continue

Start with the shared-clone reconciliation (Next Step 1) — it blocks anyone pulling main
in that tree. Then redo the deletion ast-first in a fresh worktree, using the manifest
above verbatim; it was verified against the code and is the expensive part to re-derive.
Do not deploy the deletion until Criss is confirmed on the SPA.

---

## Strategic Feedback

### What Worked Well This Session
- Auditing against the live API before building. The brief's premise (workbench mutations
  missing) was wrong; one `curl` of `/api/operator/state` showed `published_runs=0`
  against `operator_runs=2` and reframed the whole task in a minute.
- Diffing the ledger before committing. It caught a copy that would have silently reverted
  a sibling's committed session block and INDEX row.

### Suggestions
- The deletion's real cost is the 9 test files, not the source edit. Budget it as its own
  session rather than a tail-end task.

### System Health
- `stop-b1-gate` fired 3 times, all on closing phrasing (offering a bounded autonomous
  step instead of taking it). Correct every time. This is now a recurring class across
  five sessions — the hook holds, the habit does not improve. It is the strongest
  candidate for a structural fix beyond the hook.
- Autonomy score: 3 human interventions this session (all hook-caught phrasing, zero
  execution corrections).
