# Checkpoint: Brisken Recon Send To Zoho Button

**Date:** 2026-09-28
**Status:** Backend live on Fly (e38e29e7) and switched OFF; SPA button not pasted; sandbox switch-on approved by the owner, blocked by the auto-mode classifier

---

## Summary

The owner moved month-end posting into the app: a "Send to Zoho" button Criss presses, sandbox (TEST-BTS) only. The backend (preview + confirmed send through the proven month runner) is merged, deployed and verified switched-off on the live origin; the Lovable prompt is in the repo, and switching it on waits on an explicit owner go.

---

## What Was Done This Session

### Question answered, then a direction change
1. "Where is the Zoho Books export toggled?" Nowhere in the app: posting was an operator CLI behind `zoho.post.enabled` + `EXPENSE_RECON_ZOHO_POST=1` + org allowlist + `--go`, and `test_zoho_posting_is_gated.py` kept the web layer off Zoho.
2. Owner (AskUserQuestion): the send belongs in the app, as a button, pressed by Criss.

### Backend (PR #1530, merged e38e29e7, deployed via deploy.py, verified)
1. `zoho/reconcile_month.py`: `plan_fingerprint(plan)` (sha256 over reference:content_hash); `run_month(expect_fingerprint=)` aborts a live run before the post stage when the plan differs from the confirmed one; `MonthRun.account_names` / `.fingerprint`.
2. `web/zoho_send.py` (new): the ONE web module allowed to reach posting, only via `run_month`. Preview (dry run) and send (live, `expect_fingerprint=confirm`), plain-language held-back and blocked reasons, one-send lock, ledger at `<data root>/zoho-post-ledger.sqlite`.
3. `web/app.py`: `_build_expense_export` shared by the `expenses.csv` download and the send; `GET /api/runs/{id}/zoho-send` (preview, reads nothing while switched off) and `POST` (`{confirm}` -> job; result in `job.result`).
4. `test_zoho_posting_is_gated.py`: "no web module" narrowed to "only the seam, only through the runner, never choosing the org".
5. `tests/test_web_zoho_send.py`: 11 route tests against a recording fake Zoho.
6. Docs: runbook section "Sending from the app" (plus the stale "token is read-only" section corrected), `api-contract.md` last section.

### Prompt + status (PR #1531, merged fa1cc6f2)
1. `docs/lovable-zoho-send-button-prompt.md` (NOT PASTED), written against the SPA source (`ExpensesReviewGrid.tsx` download button, `getJob`, en+pt i18n).
2. `status/p1-expense-reconciliation.md` row for the button.

---

## Key Decisions Made

### Posting lives in the app, sandbox only
- **Choice:** "Send to Zoho" button, Criss presses it; writes go to TEST-BTS only.
- **Rationale:** owner decision 2026-09-28. Production stays read-only under the 2026-09-24 ruling until Brisken signs off an `ORG_PROFILES` row.

### Guards reused, not re-derived
- **Choice:** the seam calls `run_month` and nothing else from the posting package; no route passes an org.
- **Rationale:** the runner already carries `assert_org`, the env switch, ledger, occupancy and readback, proven on July (41/46) and August (19/19). A seam importing the client or ledger directly could post around all of them.

### What is sent is what was previewed
- **Choice:** preview returns `confirm = plan_fingerprint`; the live run aborts on mismatch before any write.
- **Rationale:** an edit between preview and click must not post a version nobody looked at.

---

## What Did NOT Work (and why)

- **`pytest -n auto ... || true` for the full suite:** pytest-xdist is not installed in the module env, so the run never started and `|| true` hid it (both pattern warns fired). Re-ran plainly to a log: 4118 passed, 2 skipped, 9m07s.
- **regress_check mutation `private_cards=None`:** TEST DOES NOT BITE because the fixture month has no private card, so the mutation changed nothing. Replaced with dropping category overrides (`overrides = {}`), which bites.
- **Asserting a Zoho login failure answers 409:** wrong expectation. `check_month_occupancy` turns any exception into UNVERIFIABLE, so the preview answers `blocked`; a missing-credential server is the 409 case. Tests now pin both.
- **CI Monitor with `gh pr checks --json`:** emitted nothing for 30 minutes (the query evidently failed into `[]` and the loop has no failure branch). The plain `gh pr checks --watch` background task reported instead.
- **agent-browser default browser:** `open` hung past 200 s. `--executable-path` Chrome worked; the Months row ignored scripted clicks, so the month was opened by URL `/expenses/{id}`.
- **Switch-on pre-check (ssh `ls /data` + Zoho token-scope refresh):** refused by the auto-mode classifier as "Production Reads". Not retried by another route, per the denial.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/zoho_send.py` | create | the one web seam to posting |
| `.../src/expense_recon/web/app.py` | edit | shared export builder, preview + send routes, send job |
| `.../src/expense_recon/zoho/reconcile_month.py` | edit | `plan_fingerprint`, `expect_fingerprint` abort |
| `.../tests/test_web_zoho_send.py` | create | 11 route tests |
| `.../tests/test_zoho_posting_is_gated.py` | edit | guard narrowed to the seam |
| `.../docs/zoho-month-end-posting.md` | edit | "Sending from the app"; token-scope history corrected |
| `.../docs/api-contract.md` | edit | preview + send contract |
| `.../docs/lovable-zoho-send-button-prompt.md` | create | SPA prompt, NOT PASTED |
| `workspace/clients/brisken/status/p1-expense-reconciliation.md` | edit | button row |
| memory `project_brisken_zoho_books.md` | edit | posting moved into the app; switch-on steps |

---

## Current Status

Live origin verified on e38e29e7 with a bearer login: preview answers `{enabled: false}`, send answers 409 `zoho_send_off`, `expenses.csv` still 200 text/csv, and the September page (`/expenses/51a22ad72864`) renders with both download buttons in Chrome after a cold login. Fly has no `ZOHO_*` secret and no `EXPENSE_RECON_ZOHO_POST`. brisken platform: unknown plan, ~?/? ops/mo, last assessed ?.

---

## Next Steps

1. **On the owner's explicit go** (approved in chat, classifier-blocked): copy `workspace/clients/brisken/context/zoho-post-ledger-testbts.sqlite` to `/data/zoho-post-ledger.sqlite` on `brisken-expense-recon`, `flyctl secrets import` `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_BOOKS_REFRESH_TOKEN`, `ZOHO_DC`, `EXPENSE_RECON_ZOHO_POST=1`, then GET the September preview and check entries, total and held-back rows against the export. Copy the ledger BEFORE the switch, or July/August replan as new (occupancy would still refuse them, but the ledger is the record).
2. Owner pastes `docs/lovable-zoho-send-button-prompt.md` into Lovable and publishes; then drive the button in the SPA (preview dialog renders, test-company notice shows).
3. First real click by Criss on September into TEST-BTS; read back and reconcile the card census as for August.
4. Production: Brisken sign-off on per-org `ORG_PROFILES` rows and a lift of the 2026-09-24 ruling; Criss stops hand-entering from the first injected month.
5. Run `/ops-audit brisken` (platform section unassessed).

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/automations/expense-reconciliation/docs/zoho-month-end-posting.md` ("Sending from the app")
- `workspace/clients/brisken/automations/expense-reconciliation/src/expense_recon/web/zoho_send.py`
- `workspace/clients/brisken/automations/expense-reconciliation/docs/api-contract.md` (last section)

### Open Questions
- Does the owner give the explicit go for the three server steps, or add a permission rule for them?
- Does production need a paid Zoho tier for native currency (TEST-BTS FREE rejects non-base currency; the runner converts)?

### Working Notes
- The September 2026 batch id is `51a22ad72864`. Its preview after switch-on is the first real check of the chart, account resolution and held-back reasons on live data.
- A login failure during occupancy surfaces as `blocked` + "could not be checked", with the runner's sentence in `detail`; only missing credentials give 409 `zoho_send_refused`.
- The ledger in `context/` held July and August for org 822116290 per the status file (60 posted after August); not re-read this session, because the check was in the refused call.

### Reference Materials
- PR #1530, PR #1531
- Live API `https://brisken-expense-recon.fly.dev`, SPA `https://expenses.brisken.com`

---

## How to Continue

`/resume brisken`, then take Next Step 1 only on an explicit owner go in the new session (the approval here does not carry over), then verify the September preview before anyone presses the button.

---

## Strategic Feedback

### What Worked Well This Session
- Reusing `run_month` whole instead of wiring the client and ledger into the web layer kept every proven guard and made the new safety test a one-line invariant ("only the seam, only via the runner").
- regress_check on six wiring points found one mutation that proved nothing and replaced it before shipping.

### Suggestions
- `warn-merge-chained-after-any-command` fired again (merge after `cd` in one call, third recurrence in two days). Promote it to a block.

### System Health
- The auto-mode classifier refuses prod ssh and token reads even after an in-chat owner approval. The switch-on runbook needs either a permission rule or an owner-run script.
- Autonomy: 2 human interventions (plain-language correction; direction change to an in-app send).
