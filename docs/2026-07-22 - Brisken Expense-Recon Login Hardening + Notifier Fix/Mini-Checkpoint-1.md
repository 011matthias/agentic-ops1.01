# Mini-Checkpoint: Brisken Expense-Recon Login Hardening + Notifier Fix

**Date:** 2026-07-22
**Status:** Hardening shipped and live (Fly v33). Notifier fixed and scheduled. Next task chosen but deliberately NOT started: spec-vs-build reconciliation.
**Type:** mini

---

## Summary

Post-cutover follow-through on p1: confirmed Criss was unaffected by the v31 UI
deletion, closed the `/api/login` rate-limit hole (two PRs, two deploys, live
429 probes), evaluated `matching.llm_second_pass_unmatched` to a recommendation
with zero LLM spend, then found and fixed the recon notifier, which had been
dead since the cutover, and registered it as a scheduled task.

## What Was Done

- **#367 + #369 — login throttle, live on Fly v33.** Per-caller 5 failures/15min
  then a 60s lockout doubling to a 1h cap; global 50/15min then 300s. Only
  failures count, success clears the caller, throttle runs BEFORE the code check.
  Callers bucket by IPv6 **/64** (a /128 key gave one end site 2^64 buckets).
  Suite 712 -> 728. Verified live end to end, incl. reading the stored bucket key
  off the volume both before and after the /64 change.
- **#373 — recon notifier fixed.** It had been broken since PR #350: logged in via
  the deleted `POST /login` (303 + cookie) so every run died on a 401, and all four
  human-facing links in its mails pointed into the deleted HTML UI — including the
  publish ping that goes to the USER. Now `/api/login` + bearer, handles the new
  429, links to `APP_URL` (the SPA).
- **Notifier scheduled.** Windows task `BriskenReconNotify`, 15-min repeat,
  `LastTaskResult 0` over two scheduler fires, 0 missed runs. State baselined via
  the script's own `apply_to_state` so the first fire did not mail the backlog.
- **#370 + #371 — status file + session shard/friction ledger.**
- **Second pass evaluated: recommend OFF.** Ceiling is 1-2 rescues out of 95
  labelled pairs across all 6 bundles, measured deterministically.

## Current Status

- Backend `brisken-expense-recon.fly.dev` at **v33**, API-only, throttle live.
  Rollback = redeploy v30/v31 via `flyctl releases`.
- SPA `brisken-reconcile-dash.lovable.app` clean, no open PRs, live. **Nothing to
  do in Lovable** — its `apiFetch` reads `data.error`, so the new 429 already
  surfaces as "too many login attempts".
- Notifier live on a 15-min schedule.
- **Criss has not used the tool since 2026-07-20** and has never been sent the SPA
  URL; her only link answers raw JSON 401. Owner is testing with existing data
  first, so no outbound yet — deliberate.

## Next Steps

1. **Spec-vs-build reconciliation (chosen, not started).** Read all 28 sections of
   `specs/1-spec/p1-expense-reconciliation-functional-spec.md` (1479 lines) against
   what shipped; produce a gap register (implemented / partial / missing /
   deliberately-deferred) with Dirk's four feedback notes mapped onto it. This is a
   HIGH-pressure task — budget it a fresh session. Rationale for choosing it over
   building: his three specific notes look like symptoms of the fourth ("I do not
   see the long requirements and functional design document reflected in this"),
   and the spec already has sections covering each (§22/§28/§20 master data,
   §8 Zoho Expense, §27/§24 flow order). Building the settings screen first would
   optimise execution of an unchecked goal.
2. Send Criss the SPA link + code (owner call; deferred until after own testing).
3. Label fixture re-validation — blocks the S1 optimize scorer. Only 37/95 confirmed
   pairs resolve to the labelled charge; cause NOT established (amount-proximity
   favours the label 32x, the matcher 20x).
4. Reconcile the shared clone: it is ~21 commits behind and carries the notifier fix
   as an uncommitted local edit (identical to main; it must live there because the
   task needs the gitignored `context/.env`). Before pulling:
   `git checkout -- tools/brisken-recon-notify.py`, then pull.

## Files to Read First

- `workspace/clients/brisken/status/p1-expense-reconciliation.md`
- `workspace/clients/brisken/specs/1-spec/p1-expense-reconciliation-functional-spec.md`
- `docs/sessions/2026-07-22-recon-login-hardening.md`
- `.../src/expense_recon/web/ratelimit.py`

## Working Notes (do not re-derive)

- **Fly overwrites `Fly-Client-IP`.** Proven by reading the stored throttle key on
  the volume: a real peer address, and a forged header sent alongside never became
  a key. But uvicorn runs WITHOUT `--proxy-headers`, so `request.client.host` is
  Fly's own `fdaa:` proxy — read the header, never the socket peer.
- **The agent CAN register scheduled tasks.** `Register-ScheduledTask` needs no
  elevation for user-level tasks. The standing "agent can't schtasks" claim was
  false and had deferred this for two days. See
  `feedback_agent_can_register_scheduled_tasks`.
- **Unactioned product feedback in the live feedback log** (4 operator notes,
  2026-07-20): flow is "backwards", wants settings/master-data, wants Zoho Expense
  auto-pull, and "I do not see the long requirements and functional design document
  reflected in this". None of it is on the status-file roadmap. This is what the
  reconciliation in Next Step 1 exists to answer.
- Three hand-picked label disagreements all favoured the matcher and nearly became a
  reported cause; the aggregate contradicted it 32-20. Population hypothesis needs
  population evidence.
