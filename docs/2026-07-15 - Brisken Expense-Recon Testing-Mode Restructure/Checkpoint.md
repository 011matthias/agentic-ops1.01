# Checkpoint: Brisken Expense-Recon Testing-Mode Restructure

**Date:** 2026-07-15
**Status:** SHIPPED + DEPLOYED. PR #228 open (merges on CI-green); live at brisken-expense-recon.fly.dev.

---

## Summary
Transcribed Chris's 2026-07-15 PT process walkthrough, then restructured the
Brisken expense-recon web tool into a role-split testing-mode intake app
(users upload / operators run + publish), integrated the six walkthrough
learnings, and rebranded it Brisken. Built across 7 commits on a worktree
off main, deployed to Fly, and handed over the live link + access codes.

---

## What Was Done This Session

### Transcription + learnings
1. Transcribed `New Recording Expense Recon.m4a` (14-min PT, OpenAI
   gpt-4o-transcribe, chunked to beat the long-audio truncation). Saved to
   gitignored `context/expense-reconciliation/2026-07-15-chris-process-walkthrough-transcript-pt.txt`.
2. Extracted six learnings + captured them in memory
   `project_brisken_expense_recon_chris_process.md`.

### The build (7 PRs, one branch client/brisken/expense-recon-testing-mode)
- **PR-A** Brisken brand: single `web/static/tokens.css` (live-site palette),
  real logos + favicon, `/static/{name}` route (ungated), unified login,
  760px responsive.
- **PR-B** Testing mode: two access codes -> role in HMAC cookie
  (user/operator; gate-off local dev = operator); `intakes` + `jobs` tables
  + `runs.published`; operator-only route gating; durable jobs + startup
  sweep (scale-to-zero); publish/unpublish; `cards_provision.py` preset;
  dev-side `tools/brisken-recon-notify.py` (Graph mail, server API-free).
- **PR-C** L4 missing-receipt-image flag.
- **PR-D** L1 fill-color ingest (yellow=posted/gray=subscription via
  `Transaction.entry_status`), L6 formula-column warnings
  (`ParseIssue.severity`), L5 tabular FX columns (xlsx+csv).
- **PR-E/F** Workbench 5-bucket collapse sections + her color legend +
  `already_posted` status (z-key, excluded from Zoho journal) + EN/PT i18n;
  L3 `output/sheet_writeback.py` ("Zoho Account (tool)" column in her own xlsx).
- **PR-G** Staged progress stepper (on_stage -> durable job row) + merged
  trilingual `templates/help.html` (deleted the two drifted guides).
- **PR-H** L2 `expense-recon memory seed-zoho` (Zoho Books posting history ->
  merchant memory; kept the 8 categories per owner).

### Deploy
- Generated + staged user + operator codes (unambiguous alphabet), deployed
  the verified image, live-verified both codes/roles + static + gate.

---

## Key Decisions Made
### Keep the 8 generic categories (LD-1 stands)
- **Choice:** No pivot to real Zoho account names in the picker.
- **Rationale:** Owner 2026-07-15 ("change in future, not sure you have
  access to their Zoho Books"). The L2 seed still stores the real account
  name in `zoho_account` under the 8-category model.

### Graph creds dev-side only (server API-free)
- **Choice:** Notifier runs on a dev machine, not on Fly.
- **Rationale:** Owner picked it; One Assessment precedent; the tenant-wide
  Mail.Send credential should not sit on the box.

### Rotated the user access code on deploy
- **Choice:** Fresh user + operator codes; old shared code retired.
- **Rationale:** New role model needs an operator code (else app is
  user-only); Chris has not tested yet so no code was in her hands.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../web/auth.py` | Modified | two codes + role-bearing HMAC token + operator route matcher |
| `.../web/store.py` | Modified | intakes/jobs tables, published cols, migration, already_posted |
| `.../web/service.py` | Modified | create_intake, prepare_intake_run, sections, writeback, on_stage |
| `.../web/app.py` | Modified | role middleware, intake/publish/notify routes, /help, static |
| `.../web/templates/{base,workbench,login,running}.html` | Modified | brand, roles, buckets, stepper |
| `.../web/templates/{home_user,home_operator,operator_run,_run_form,help}.html` | Created | new surfaces |
| `.../web/static/{tokens.css,brisken-logo-*.png,favicon.png}` | Created | brand assets |
| `.../ingest/{statement_xlsx,statement_csv,_common}.py`, `inspect.py` | Modified | L1/L5/L6 |
| `.../matching/types.py` | Modified | Receipt.has_receipt_image, Transaction.entry_status |
| `.../output/{reconciled_csv,report_xlsx,zoho_export,sheet_writeback}.py` | Modified/Created | L3/L4 + posted-skip |
| `.../cards_provision.py`, `learning_cli.py`, `zoho/client.py`, `categorize.py`, `cli.py` | Modified/Created | presets, seed-zoho, on_stage |
| `tools/brisken-recon-notify.py` | Created | dev-side Graph notifier |
| `tests/test_web_{roles,intake,publish,jobs_persist,already_posted,guides}.py`, `test_{entry_status,receipt_image_flag,sheet_writeback}.py`, `tools/tests/test_recon_notify_diff.py` | Created | ~50 new tests |

---

## Current Status
- Live: **brisken-expense-recon.fly.dev**, both codes verified against the
  live origin. Recon suite 503 passed / calibrate exit 0.
- PR #228 open against main (CI = platform + hook jobs only; recon suite is
  a local gate, already run green).
- Fly secrets: `EXPENSE_RECON_ACCESS_CODE` (user, rotated),
  `EXPENSE_RECON_OPERATOR_CODE` (new), `EXPENSE_RECON_AUTH_SECRET`,
  `OPENAI_API_KEY`. Codes in vault entry "Expense Recon App".

---

## Next Steps
1. **Next build (fresh chat):** add the double-click-to-give-feedback widget
   (see the continuation prompt: `docs/2026-07-15 - Brisken Expense-Recon
   Testing-Mode Restructure/CONTINUE-PROMPT.md`).
2. **Notifier:** set `EXPENSE_RECON_NOTIFY_USER` (Chris's email) + run
   `tools/brisken-recon-notify.py` (--once or scheduled task) so upload +
   ready mails fire. BLOCKED on Chris's email.
3. **Card dropdown:** author `/data/cards.json` from the real card list
   (label + entity + account id each) + upload to the volume. BLOCKED on the
   card list.
4. Send Chris the user code + link (owner's action).

---

## Context for Next Session
### Files to Read First
- `CONTINUE-PROMPT.md` (in this folder) — the double-click feedback task
- `memory/project_brisken_expense_recon_chris_process.md` — the built state
- `workspace/clients/brisken/onepilot-site/app.py` — server /feedback pattern
- `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html`
  — client-side dblclick feedback widget (lines ~483-540, 1264-1560)

### Open Questions
- Chris's email address (for the ready-ping).
- The full Brisken card list (labels, entities, account ids) for cards.json.

### Working Notes
- Finance work ships from a worktree off main
  (`agentic-ops1-recon`); the shared clone stays on the lead-desk branch (91
  commits behind — do NOT build expense-recon there).
- gpt-4o-transcribe truncates long audio; chunk with ffmpeg (5-min segments)
  and stitch.
- Fly `flyctl deploy` from the module dir ships the local worktree tree +
  staged secrets in one shot; machine is scale-to-zero (first hit ~5s cold).
- The double-click feedback widget: client-side dblclick -> anchored popover
  + a floating FAB + a one-time hint, POST /feedback with a reviewer name;
  server appends to `feedback.jsonl` on the volume, plus /feedback-log +
  /feedback.jsonl views. Port into the expense-recon FastAPI app's base.html
  + a /feedback route; the reviewer = the logged-in role/session.

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/228
- Live: https://brisken-expense-recon.fly.dev

---

## How to Continue
Open a fresh chat, paste `CONTINUE-PROMPT.md`. It resumes the build in the
`agentic-ops1-recon` worktree and adds the double-click feedback widget as
the next feature, mirroring the onepilot-site + website-prototype pattern.

---

## Strategic Feedback

### What Worked Well This Session
- The plan-mode fan-out (3 Explore + 3 Plan agents) front-loaded the whole
  design; the seven PRs then executed cleanly with two parallel build agents
  (sheet-writeback, Zoho-seed) running while the main loop did the web layer.

### Suggestions
- The card list + Chris's email are the only two things blocking full
  polish; grabbing both in one message would unblock the notifier + the
  card dropdown together.

### System Health
- Autonomy score: 2 human interventions (both B1 deferral-phrasing slips,
  hook-caught + corrected same-turn; no user-visible cost). The
  stop-b1-gate hook is doing its job.
- No new skill/rule gaps surfaced; the worktree-off-main finance-isolation
  convention held throughout.
