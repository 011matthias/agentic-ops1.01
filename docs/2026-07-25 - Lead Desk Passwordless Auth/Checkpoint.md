# Checkpoint: Lead Desk Passwordless Auth

**Date:** 2026-07-25
**Status:** Shipped + live. Magic-link email is the only sign-in; access code removed.

---

## Summary
Built passwordless (magic-link email) login plus an admin-approves-each-user registry for the Brisken Lead Desk, enabled it live from Matthias's Graph mailbox, then removed the shared access-code path entirely on owner direction. Two PRs (#433, #443), both merged and deployed to `brisken-lead-desk.fly.dev`.

---

## What Was Done This Session

### Build — passwordless + admin approval (PR #433)
1. Store migration v6: `users` (email PK, role, status) + single-use `login_tokens` (sha256-at-rest, 15-min TTL); seeds matthias + dirk as approved admins. Verified fresh / v5-upgrade-with-data / idempotent paths.
2. `accounts.py` (new): `request_magic_link` (pending vs sent), `verify_and_login` (single-use + revocation-safe), `is_admin`, `approve/invite`; email via the app-only Graph sender (matthias-only), dependency-injected for tests.
3. Routes: `/login/magic`, `/auth/verify`, `/admin/users` (+approve/disable/role/invite), deny-by-default admin gate, last-admin guard, CSRF; login.html email form + admin_users.html + admin nav link.
4. 24 new tests; full suite 284 pass.

### Enable — auth email live
5. `flyctl secrets set LEAD_DESK_AUTH_EMAILS=1 LEAD_DESK_BASE_URL=…` after the B5 invasive-action protocol (scope-of-effects + explicit "yes enable it" + read-only readiness check). Confirmed live on the machine.

### Remove — access code entirely (PR #443)
6. Re-based `gate_enabled()` on `LEAD_DESK_AUTH_SECRET` (was: access-code presence) so removing codes could not open the app; deleted `_codes`/`resolve_user`/code throttle/`POST /login`/login fallback/legacy admin mapping. Updated 7 test files (code-login helpers → direct cookie mint; gate-off fixtures unset AUTH_SECRET).
7. Deployed (code first), then `flyctl secrets unset LEAD_DESK_ACCESS_CODES`; live-verified the gate held after removal.

---

## Key Decisions Made

### Mechanism + signup policy
- **Choice:** Magic-link email + admin-approves-each-user (via AskUserQuestion).
- **Rationale:** Fits "Dirk runs it himself"; open self-signup unsafe for a PII tool.

### Gate signal after removing codes
- **Choice:** `gate_enabled()` keys on `LEAD_DESK_AUTH_SECRET`, not code presence.
- **Rationale:** The old key meant deleting the codes would silently disable the whole gate. AUTH_SECRET is set in prod, unset local — same prod/local split, fail-secure.

### Sender identity
- **Choice:** All auth email sends from `matthias.silva@brisken.com`, code-enforced (GraphMailer refuses any other from-address). Confirmed as already-the-case per owner ask.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| `.../web/store.py` | edit | v6 migration: users + login_tokens + seed admins; store methods |
| `.../web/auth.py` | edit | email/token helpers; gate rebased to AUTH_SECRET; code-login removed |
| `.../web/accounts.py` | add | magic-link + approval orchestration; injectable mailer |
| `.../web/app.py` | edit | magic/verify/admin routes; removed POST /login |
| `.../web/templates/login.html` | edit | email-only login (fallback removed) |
| `.../web/templates/admin_users.html` | add | admin user-management page |
| `.../web/templates/base.html` | edit | admin-only Users nav link |
| `.../tests/test_passwordless.py` | add | 24 tests: tokens, approval, admin-only, HTTP flow |
| `.../tests/test_p7,test_branding,test_outbox,test_p3,test_p4,test_p6,test_webflow.py` | edit | de-code test auth |

---

## Current Status
Live on `brisken-lead-desk.fly.dev`: gate ON (keys on AUTH_SECRET), login email-only, admins seeded (matthias + dirk), auth-email ON from Matthias's mailbox, ACCESS_CODES removed from Fly. Prod DB at `user_version=6`, 337 contacts intact. Campaign sender untouched (kill_switch=1). brisken ops status: `platform: unknown plan` in infrastructure.yaml (Lead Desk is a Fly app, not tracked there).

---

## Next Steps
1. None required — feature complete. Dirk/matthias sign in by entering their email; new people go to `/admin/users` for approval.
2. If broader rollout: add colleagues via `/admin/users` "Add user" (or they self-request → pending → approve).
3. Deferred infra: `friction-register.md` is 415 KB — run `checkpoint_scaffold.py archive-register` in a dedicated docs PR (skipped here to avoid conflicting with sibling sessions' pending ledger edits).

---

## Context for Next Session

### Files to Read First
- `~/.claude/.../memory/project_brisken_lead_desk.md` (canonical Lead Desk record; updated this session with both PRs + the enable/remove state)
- `workspace/clients/brisken/automations/lead-desk/src/lead_desk/web/{auth,accounts,app}.py`

### Open Questions
- None blocking. Note: no break-glass remains — if Graph email delivery fails, no one can log in until an access path is restored via deploy. Owner accepted this ("entirely").

### Working Notes
- Gate is fail-secure: `bool(LEAD_DESK_AUTH_SECRET)`; local dev (no secret) is ungated by design.
- The auto-mode classifier BLOCKS `curl -X POST /login/magic` (a live outbound-email trigger) even with in-chat authorization — the harness gates live email sends independently. The first verification send is owner-triggered (enter email on the live page) or needs a Bash allow rule.
- Deploy order for the removal mattered: new code (gate re-based) FIRST, then unset the secret; verified gate held at each step.

### Reference Materials
- PRs: #433 (build+enable), #443 (remove access code). App: https://brisken-lead-desk.fly.dev
- Worktree: `agentic-ops1-ldauth`.

---

## How to Continue
Feature is done and live. For user management, use `/admin/users` on the live app. For code changes, work in the `agentic-ops1-ldauth` worktree off origin/main.

---

## Strategic Feedback

### What Worked Well This Session
- Caught the load-bearing risk before it shipped: `gate_enabled()` keyed on code presence, so removing codes would have made the app public. Re-based it and verified the gate held live after unsetting the secret.
- Migration verified on the real upgrade path (v5-with-data → v6, contacts preserved), not just fresh DBs.

### Suggestions
- When a decision-point is a genuine gated/invasive action, phrase it AS a decision ("this is yours to authorize") from the first pass, not as an eager offer ("do you want me to…") — the B1 gate flagged the offer-phrasing four times before it landed as a clean decision-point.

### System Health
- Two clean CI-green auto-merges + two Fly deploys, all live-verified. B5 invasive-action protocol honored on the auth-email enablement.
- Autonomy: ~5 human touchpoints, but these were requirement evolution (build → send-from → enable → remove) plus one mandatory invasive-action authorization — driving the work, not correcting errors. Not an error-elevated session.
