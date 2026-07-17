# Checkpoint: Expense Recon Feedback Widget + Deploy

**Date:** 2026-07-16 (session ran 2026-07-15 evening into 07-16)
**Status:** SHIPPED + DEPLOYED — live-verified on brisken-expense-recon.fly.dev

---

## Summary

Built the double-click anchored feedback widget into the Brisken expense-recon
web app (mirroring the OnePilot prototype widget), shipped it on PR #228
(squash-merged to main on green CI), and deployed to Fly on the owner's
explicit Band-3 order with an 11/11 live verification pass.

---

## What Was Done This Session

### Feature: anchored reviewer feedback

1. `base.html` widget on every logged-in page (standalone login stays clean):
   double-click opens a popover anchored at the clicked spot capturing card
   heading, CSS selector path, clicked text, and page coordinates; floating
   Feedback FAB for general notes; one-time explainer overlay; all strings
   in the existing EN/PT toggle (new `data-i18n-ph` placeholder extension);
   session-role attribution line. Brisken tokens, no em-dashes, no emoji.
2. `POST /feedback` appends to `/data/feedback.jsonl`; attribution is
   server-side only (session role, page, run id extracted from the path);
   position payload sanitized to known numeric fields.
3. Operator-only reads: `/feedback-log` (new nav tab, `feedback_log.html`)
   and raw `/feedback.jsonl`, both in `auth._OPERATOR_RULES` (users get 303).
4. `/api/operator/state` now exposes the feedback count;
   `tools/brisken-recon-notify.py` diffs it and mails the dev the new note
   bodies (pulled from `/feedback.jsonl` over the same operator session).
5. Tests: `tests/test_web_feedback.py` (10 new, all behavior-level via
   TestClient); `tools/tests/test_recon_notify_diff.py` extended for the
   feedback count diff.

### Ship + deploy

6. Commit `1f5f574` on `client/brisken/expense-recon-testing-mode` (the
   recon worktree), pushed; PR #228 body updated; CI green; **squash-merged
   to main** (Band 2).
7. **Deployed to Fly** on the owner's "deploy" order (Band 3). Pre-flight:
   worktree module tree byte-identical to merged main; all gate secrets
   already on the app. Post-deploy verification: 11/11 live checks
   (healthz, branded login, user + operator role paths, widget presence,
   log gating, full TEST-note POST -> jsonl -> log -> state-count round trip).
8. Memory `project_brisken_expense_recon_chris_process.md` updated
   (merged + deployed + vault pointer + cards.json still open).

---

## Key Decisions Made

### Ship on PR #228 instead of a new PR
- **Choice:** Commit the widget onto the still-open testing-mode branch/PR.
- **Rationale:** The widget rides the same unreleased build; one merge unit,
  one deploy unit, PR body updated to cover the addition.

### Attribution = session role, no name gate
- **Choice:** Notes are attributed to the HMAC-cookie role (user/operator) +
  page + server-extracted run id; nothing identity-related from the body.
- **Rationale:** The app's auth model has role codes, not per-person names
  (unlike the OnePilot prototype's name gate); the user code IS Chris in
  testing mode, so the role is sufficient and unforgeable.

### Notifier stays poll-based, server stays API-free
- **Choice:** Expose only a count in `/api/operator/state`; the notifier
  fetches note bodies from `/feedback.jsonl` with its operator session.
- **Rationale:** Preserves the One Assessment precedent (no Graph creds on
  the box); count diff is exact because the jsonl is append-only.

### TEST note left in the production log
- **Choice:** The deploy-verification note (`TEST - deploy verification...`)
  stays in `feedback.jsonl`.
- **Rationale:** Test fixtures persist per rule_behaviors; jsonl is
  append-only by design (no delete endpoint). It will trigger exactly one
  self-addressed notifier mail on the next notify run.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/templates/base.html` | Modified | Widget CSS/HTML/JS, EN/PT strings, `data-i18n-ph`, operator Feedback tab |
| `.../src/expense_recon/web/templates/feedback_log.html` | Created | Operator feedback log page |
| `.../src/expense_recon/web/app.py` | Modified | POST /feedback, /feedback-log, /feedback.jsonl, state-API count, `_run_id_from_path` |
| `.../src/expense_recon/web/auth.py` | Modified | Operator rules for the two read routes |
| `.../tests/test_web_feedback.py` | Created | 10 behavior tests (attribution, gating, sanitization, round trip) |
| `.../README.md` | Modified | Feedback surface + notifier mail documented |
| `tools/brisken-recon-notify.py` | Modified | `diff_feedback` + `fetch_feedback_entries` + feedback mail plan |
| `tools/tests/test_recon_notify_diff.py` | Modified | Feedback diff coverage; state round-trip includes `seen_feedback_count` |
| `~/.claude/.../memory/project_brisken_expense_recon_chris_process.md` | Modified | Merged + deployed state, vault pointer, cards.json open item |

All module/tool changes shipped in PR #228 (squash commit on main).

---

## Current Status

- **Live:** brisken-expense-recon.fly.dev runs the testing-mode build WITH
  the feedback widget (deployed + verified 11/11). Access codes in the local
  vault under "Expense Recon App" (set on Fly 2026-07-15).
- **Suite:** 513 passed / 2 skipped; calibrate exit 0; rendered inline JS
  passes `node --check`.
- **Worktree:** `agentic-ops1-recon` sits on the now-merged branch
  `client/brisken/expense-recon-testing-mode`; next p1 session should cut a
  fresh branch off `main`.
- `/data/cards.json` still not authored; upload form fail-opens to a plain
  card-name text box (not blocking Chris's testing).

---

## Next Steps

1. **Owner action:** send Chris the app link + user code (vault: "Expense
   Recon App"). This was the commitment from the 2026-07-15 call.
2. Author `/data/cards.json` (real card list, shape in
   `examples/cards.example.json`) and put it on the volume; until then the
   card picker is a free-text box.
3. Run `uv run tools/brisken-recon-notify.py --once --env-file
   workspace/clients/brisken/context/.env` after Chris's first upload (or
   schedule it); the first run will also announce the one TEST note.
4. Standing: Exchange Application Access Policy for the Graph app
   (compensating allowlist in code until then).

---

## Context for Next Session

### Files to Read First
- `~/.claude/.../memory/project_brisken_expense_recon_chris_process.md` (state + process truth)
- `workspace/clients/brisken/automations/expense-reconciliation/README.md` (testing-mode + deploy section)
- `.../src/expense_recon/web/app.py` (feedback block near `/api/operator/state`)

### Open Questions
- Who authors the real card list for `cards.json` — pull card names/last4
  from Chris's per-card spreadsheets, or ask her once she's in the tool?

### Working Notes
- Deploy verification script pattern (requests session, both roles, TEST
  note round trip) lived inline in the session; rebuild from the checkpoint
  list if needed, no saved artifact (per W1).
- The notifier state file is `.scratch/recon-notify-state.json`; it has no
  `seen_feedback_count` yet, so the first run announces current count (1 =
  the TEST note) to the dev only.
- `gh pr merge --squash` matched main's history convention (single-parent
  `(#NNN)` commits). No worktree held main, so no false-FAIL (see
  reference_repo_tooling_gotchas).

### Reference Materials
- PR: https://github.com/011matthias/agentic-ops1.01/pull/228 (MERGED)
- App: https://brisken-expense-recon.fly.dev
- Widget reference: `workspace/clients/brisken/deliverables/brisken-onepilot-website-prototype.html` (~lines 483-540, 1264-1560) + `workspace/clients/brisken/onepilot-site/app.py`

---

## How to Continue

`/resume brisken`, read the memory file above. If Chris has tested: check
`/feedback-log` as operator (or run the notifier) and triage her notes into
the next build list. If not: nudge the owner on step 1 and author
`cards.json` (step 2).

---

## Strategic Feedback

### What Worked Well This Session
- The task brief carried exact reference anchors (file + line ranges for the
  OnePilot widget and its server half), which made this a single-pass port:
  no design detours, no re-derivation, zero corrections needed.

### Suggestions
- Decide the cards.json sourcing now (send me the card list, or approve
  pulling names from Chris's spreadsheets already in context) so the picker
  is live before Chris's first real upload.

### System Health
- CI still does not run the recon module suite (platform + hook jobs only);
  every recon ship relies on local gates. Recurring observation across p1
  checkpoints — a small CI job running `pytest` in the module dir would
  close it.
- Autonomy score: 0 human interventions — fully autonomous session (1
  self-detected friction event: missing session header block at start,
  logged to the register; first instance of that type).
- Gates: B1:2 (vault lookup instead of asking for codes; git/gh state
  instead of asking about worktree/PR) B2:3 (pre-ship suite+calibrate+node,
  CI-green merge, 11-check live deploy verification) B3:0 skipped:0.
