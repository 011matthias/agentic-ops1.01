---
date: 2026-07-22
session: recon-login-hardening
projects_touched: [brisken]
friction_events: 1
work_types: [client-dev]
---

### Session — Brisken Expense-Recon Post-Cutover: Criss Check, Login Throttle, Second-Pass Evaluation
**Type:** client-dev
**Focus:** Post-cutover follow-through on p1 after the Jinja UI deletion shipped (v31): confirm whether Criss had been affected, close the `/api/login` rate-limit hole, and decide the `matching.llm_second_pass_unmatched` default.
**Projects:** brisken (p1-expense-reconciliation)

**Built:** 2 PRs merged CI-green + deployed to Fly.
- **#367** — `web/ratelimit.py` + `login_failures` table. Per-caller 5 failures/15min then a 60s lockout doubling to a 1h cap; global 50/15min then 300s. Only failures count, a success clears the caller, and the throttle runs BEFORE the code check so a locked caller cannot pass with the right code. Stdlib only, env-tunable, no-op when the gate is off. Suite 712 -> 725.
- **#369** — bucket callers by IPv6 **/64** rather than /128. Suite 725 -> 728.
- Deployed v32 then v33; verified against the live origin, not localhost.

**Verified (live, not asserted):** 5x401 -> 429 with `Retry-After: 60` and `scope: ip` -> correct code still 429 while locked -> lockout expiry -> 200 -> failure record cleared to 0 rows. Stored bucket key read off the Fly volume both before and after #369.

**The finding that changed the design.** Reading the key the deployed throttle actually stored (`2003:c6:3f3c:3200:5c56:c79:7bc4:fffa`) resolved an ambiguity a 429 alone could not: either Fly overwrites a forged `Fly-Client-IP` (per-IP keying is sound) or the header is absent and everyone shares the proxy bucket (any attacker could lock Criss out). It was the former — but the /128 key handed one IPv6 end site 2^64 fresh buckets, so the per-IP tier was defeatable by rotation with no forging at all. #369 fixed that and corrected #367's stated threat model, which had named header spoofing as the reason for the global tier.

**Task 1 — Criss:** not a rollback situation. Latest run 2026-07-21T10:19Z, latest feedback 2026-07-20T17:22Z, zero intakes, zero published runs; a both-mailbox all-folders Graph scan (`tools/brisken-outreach-truth.py`) since 07-14 shows her active on normal finance mail and silent on the tool. All activity predates v31. The real gap is forward-looking: her 2026-07-20 PT email gave one link, `brisken-expense-recon.fly.dev`, which now answers raw JSON 401, and she has never been sent the SPA URL. Surfaced to the owner; no outbound sent (brief said not to).

**Task 3 — second pass: recommend OFF.** The pass can only pair an unmatched charge with a still-unclaimed receipt, so its ceiling is deterministic and needed zero LLM spend: **1-2 rescues out of 95 labelled pairs across all 6 bundles**. Only 13 receipts remain unclaimed across the 6 months against 559 unmatched transactions; the unmatched bucket is dominated by receiptless statement charges, and no matching pass finds a receipt that does not exist. Cost would be ~40 calls/run (the cap, hit monthly) and every rescue lands in `judgment_required` = more review for Criss.

**Unplanned finding — the label fixture is not currently trustworthy.** Replaying the 6 bundles resolves only **37/95** confirmed pairs to the labelled charge; 53 have the receipt claimed by a different charge. Cause NOT established: on amount-proximity to the receipt's `base_amount` the label is closer 32x and the matcher 20x. So both stale positional ids (post-#285 ingest changes) and genuine mis-pairing are present, and this instrument cannot separate them. This blocks the S1 optimize scorer design, which scores against exactly these labels.

**Friction:** 1 — `verification-theater` (self-caught, pre-report). I read three hand-picked examples where the matcher clearly beat the label and was one step from reporting "the labels drifted" as established fact; the aggregate check contradicted it 32-20. Three unrepresentative examples are not a measurement. Corrected before it reached the status file or the owner.

**Gates:** B1:1 (used the existing Graph tool rather than asking) B2:4 B3:2 B4:3 B6:2 B7:1 skipped:0
**Autonomy:** 0 human interventions.
**Outcome:** Rate-limit hardening closed and live. Second-pass default decided with evidence and no spend. One new blocker surfaced for the optimize track. Owner decisions pending: send Criss the SPA link, and whether to re-validate the label fixture.

---

### Continuation — notifier revival + scheduling

**Built:** **#373** — the recon notifier had been dead since PR #350's UI deletion, not merely unscheduled. It logged in via the deleted `POST /login` (303 + cookie), so every run died on a 401 before reading state; and all four human-facing links in its mails pointed into the deleted HTML UI, including the publish ping that goes to the USER (it would have auto-sent Criss a dead link). Now `/api/login` + bearer, explicit 429 handling for the new throttle, and links to a new `APP_URL` (the SPA).

**Scheduled:** Windows task `BriskenReconNotify`, 15-min repeat, `LastTaskResult 0` across two scheduler fires, 0 missed runs. State baselined via the script's own `apply_to_state` so the first fire did not mail the 2-run + 7-note backlog.

**Friction (2nd):** `agent-deferred` / `missed-tool`, user-corrected. I told the owner "LIMITATION: I have no schtasks capability" and handed the registration back as a USER ACTION. It was false: `Register-ScheduledTask` needs no elevation for a user-level task. The claim was inherited from two memories and never tested, and it had deferred an automatable action for two days. The owner pushed back ("register the notifier first") and it took one call. Fix: structural-ish — new memory `feedback_agent_can_register_scheduled_tasks` plus corrections to `project_brisken_expense_recon_testing_loop` and the `project_repo_sweep_automation` index line, which carried the same false claim and had blocked the 03:30 sweep task the same way. Regression: yes, same class as `feedback_verify_limitations_before_asserting` — an inherited "can't" repeated without a test.

**Second lesson:** scheduling a broken job is worse than not scheduling it, because it looks live. Running it once before scheduling is what surfaced the cutover breakage.

**Blast-radius note:** the cutover checkpoint enumerated 9 test files as the deletion's blast radius but missed an out-of-app CONSUMER that also used the HTML surface.

**Outcome:** notifier live. Next task chosen and scoped (spec-vs-build reconciliation) but deliberately not started — high context pressure, and a half-finished gap register is worse than none.
