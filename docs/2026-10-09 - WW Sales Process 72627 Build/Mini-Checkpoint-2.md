# Mini-Checkpoint: WW Sales Process 72627 Build

**Date:** 2026-10-09
**Status:** W2-14 built, reviewed and RELEASED (release 1, test mode) on Hero type 72627; release 2 tooling ready for Sunday
**Type:** mini

---

## Summary
The dead build workflow was relaunched (session 4e2ed9fe, run wf_47e70f30-913), reviewed and fixed, then W2-14 was released to Hero type 72627 on Matthias's yes at 2026-10-09 18:02 UTC (published 5ffdc4d6, test mode, test mails only to neumath4@icloud.com) and verified end to end; tooling for Sunday's release 2 (adds Tobias) is committed. Everything is on akkton/agentic-ops PR #305, unmerged (no CI there; merge only on Matthias's order).

## What Was Done
- Recovered state: session 3cc7f367's run wf_287f540f-f75 died in its first agent with zero edits (rules hash 28585f69 unchanged). A second chat (f23834eb) launched the identical run and was interrupted 7 s later; a duplicate run here was stopped after confirming it only read. One run kept: wf_47e70f30-913, 11/11 agents, 0 errors.
- Build: engine R1-R23 on 72627 step ids, 40-node n8n candidate, guarded release tool `tools/ww-vertrieb-release-72627.mjs`. Reviews (fidelity, safety, runtime): no blocker; 3 majors fixed (S1 blind idle check, FID-1 tracked GraphQL schema test, RT-1 SMTP outcome lost when two branches fail). Guard proof: 70 mutations, every guard bites.
- Own fixes (Iteration 1/3): test recipients limited to an owner allowlist {tobiaswimmer@me.com, neumath4@icloud.com}; CLI `--apply` and dry-run GET guard tested through `main()`; owner checks on test_projekte / test_nur_testlauf tested (G4d/G5d); TEST header shows project_nr ("Projekt HUK 106489"; Hero display_id is the bare number, verified by a guarded read); `ww-build-hero-prototype.mjs` now refuses clearly (13293 preview, superseded). All regressed red on the real source.
- Release 1 (owner yes, 20:02 Berlin): credential 'W2-14 Testlauf' DWE4TI9mE7L9Gsmb, go_live 2026-10-09T18:02:23Z, acceptance execution 50839. Independently verified: live CFG (type 72627, test mode, allowlist [12189161], recipient neumath4@icloud.com, tasks 255797), only read nodes + protocol NoOp ran, no open executions, vertrieb_log still 13 rows, Hero snapshot of HUK-106488/106489 identical before and after, export redacted. infrastructure.yaml + spec a5 updated.
- Release 2 support (subagent, then verified): `--pins-aus-bericht` builds pins from the release-1 report + live GET; later releases accept only draft == published, treat the ledger as append-only (13 pinned rows unchanged, new rows only final ok), accept 12189161 in any rule-step state at the inert acceptance run; rollback goes to the release-1 version, go_live untouched. 46 new tests, 24 mutations red; also fixed two fixtures broken by release 1 writing go_live.
- Sticky notes republished (v2): "Kopie an mich", plus decision d10 (weekend due dates).
- Commits on PR #305: 2d619190 (build), d37f39f6 (release record), f51d41e5 (release-2 support). Final suites: logic 304, guards 143, mail-logbook 54, build 48, gql 61, release-plan 48, release-72627 130 (+1 self-skip).

## What Did NOT Work (and why)
- **Relying on the previous chat's workflow:** it runs inside that chat's process; the chat died at 15:42 and the run died with it (no journal result line, 0 edits).
- **Pasting the same continuation prompt into two chats:** both launched the identical run within a minute; caught only because `bg_watch.py list` showed a second fresh watch. Stopped the duplicate before any edit.
- **`TZ=Europe/Berlin date` in Git Bash:** returns UTC, so a wait-until-20:00 loop would have released at 22:00 Berlin. Use node `Intl.DateTimeFormat` with timeZone instead.
- **Not rerunning the suites after release 1:** release 1 writes go_live into the private rules file; two fixtures assumed the placeholder, so the build suite went 47/48 and the release suite failed to load. Found by the release-2 subagent, fixed in f51d41e5. Rerun every suite after any release that writes the rules file.
- **Moving spec a5 to `3-test/` to satisfy the spec gate:** not done; all five WW specs (4 live, 1 test) sit in `1-spec/` by that client's convention.

## Current Status
W2-14 (NPHbbRF2NVAbUyzF) publishes 5ffdc4d6 on Hero type 72627 in test mode: only the header-authenticated test run acts, only on 12189161 (HUK-106489), mails only to neumath4@icloud.com, tasks only to Sabine 255797; HUK-106488 blocked by entry 24992983 and project 12189064. Scheduled runs (Mon-Fri :05/:20/:35/:50 06-19) skip the test project. Both test projects are still in 847254 on their 10-06 entries, untouched. PR akkton/agentic-ops#305 open (3 commits), waits for Matthias's merge order.

## Next Steps
1. Matthias: merge PR #305 (no CI on that repo; merge only on his order).
2. Weekend (owner decision first): whether to run R1/task-path test runs on HUK-106489 before Sunday. Each run writes in Hero (TEST tasks for Sabine, logbook lines, status moves) and sends a TEST mail to neumath4@icloud.com, so each needs a per-action yes. Keep HUK-106489 in a rule step (847254/847255/847258-847262) until release 2; never park it in Planung before that.
3. Sunday evening, release 2 (own owner yes): set rules `test_empfaenger` to "tobiaswimmer@me.com, neumath4@icloud.com", rebuild the candidate, dry run with `--pins-aus-bericht workspace/clients/warme-wimmer/context/maintenance/2026-10-09-w214-72627-release.json`, apply with `--testlauf-cred-id DWE4TI9mE7L9Gsmb`, verify as for release 1, then rerun all seven suites and commit the refreshed export. Runbook section 5.
4. Monday morning: pre-flight with Sabine (runbook section 7), walkthrough (section 8, demo script), post-call reset (section 9).
5. Ask at the call: weekend due dates (sticky note d10) and the other "Heute einsammeln" items.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (sections 5, 7, 8, 9)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\context\maintenance\2026-10-09-w214-72627-release.json` (release-1 report, gitignored)
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\workspace\clients\warme-wimmer\specs\1-spec\a5-vertriebsprozess.md` (v0.5, Stand 72627 section)
- https://github.com/akkton/agentic-ops/pull/305

## Continuation prompt

````
Continue the Wärme Wimmer (WW) W2-14 work: Tobias's heat-pump sales process on Hero type 72627, for the Monday 2026-10-12 walkthrough with Tobias and Sabine.

## Where it stands (2026-10-09, about 21:00 Berlin)
- Read memory `project_warme_wimmer_takeover.md` first. All WW code and private context live in the clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (akkton/agentic-ops), NOT in agentic-ops1; work there with absolute paths. Checkpoints: `docs/2026-10-09 - WW Sales Process 72627 Build/Mini-Checkpoint-2.md` in agentic-ops1.
- RELEASE 1 IS LIVE (owner yes, 2026-10-09 18:02 UTC): W2-14 (n8n NPHbbRF2NVAbUyzF) publishes version 5ffdc4d6-037e-4242-9139-b1bfb59fad05 (previous f4f96005 on type 13293). go_live 2026-10-09T18:02:23Z; credential 'W2-14 Testlauf' DWE4TI9mE7L9Gsmb (header X-W214-Testlauf, token N8N_W214_TESTLAUF_TOKEN in the clone's .env); acceptance execution 50839 success, only read nodes + protocol NoOp. Verified independently: live CFG type 72627, test mode, test_nur_testlauf, allowlist [12189161], test_empfaenger "neumath4@icloud.com" only, tasks only to 255797 (Sabine); vertrieb_log 13 rows; Hero snapshots `.scratch\ww-sales-72627\snapshots\01-vor-release-1.json` and `02-nach-release-1.json` identical. Report: `workspace\clients\warme-wimmer\context\maintenance\2026-10-09-w214-72627-release.json` (gitignored).
- Both test projects untouched, in step 847254: HUK-106489 = 12189161 (entry 24993267, 10-06 12:17:37 UTC), HUK-106488 = 12189064 (entry 24992983, blocked).
- PR akkton/agentic-ops#305 (branch client/warme-wimmer/w2-14-sales-process-72627, commits 2d619190 build, d37f39f6 release record, f51d41e5 release-2 support) is OPEN. That repo has no CI: merge only on Matthias's order.
- Owner decisions 2026-10-09 evening: test mails at the weekend only to neumath4@icloud.com; a second release on Sunday evening switches test_empfaenger to "tobiaswimmer@me.com, neumath4@icloud.com". Both are in OWNER_72627.testEmpfaenger in the release tool. Release 2 needs its own explicit yes.
- Release tool facts: refuses apply Mon-Fri 06:00-19:59 Berlin (so release 2 must run on the weekend); later releases use `--pins-aus-bericht <release-1 report>` and `--testlauf-cred-id DWE4TI9mE7L9Gsmb`; acceptance needs HUK-106489 in a rule step (847254, 847255, 847258-847262), never parked in Planung or archived before release 2; a retry after an automatic rollback in release 2 refuses at the baseline (draft id changes) and needs a decision.
- Suites (run from the clone root, all must exit 0): node tools/ww-vertrieb-logic-test.mjs (304); node tools/ww-vertrieb-guards-test.mjs (143); node tools/ww-vertrieb-mail-logbook-test.mjs (54); node tools/ww-vertrieb-build-test.mjs (48); node tools/ww-vertrieb-gql-test.mjs (61); node --test tools/ww-vertrieb-release-plan-test.mjs (48); node --test tools/ww-vertrieb-release-72627-test.mjs (130 pass, 1 skip). Rerun all of them after any release, because a release writes the rules file.
- Runbook: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (section 5 release 2, section 7 Monday pre-flight, section 8 walkthrough, section 9 reset). Sticky notes (German, v2): https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz (local copy in the 4e2ed9fe scratchpad; to update from a new chat: Artifact read, edit, republish with url).
- Read-only helpers in session 4e2ed9fe's scratchpad (copy them if needed): hero-snapshot.mjs (guarded Hero read on Matthias's key), verify-release.mjs (GET-only n8n verification: `node verify-release.mjs <expected version> <execution id>`), wait-berlin.mjs (Git Bash TZ is UTC; use this for Berlin times).

## Do next, in order
1. Ask Matthias (AskUserQuestion) whether to run weekend test runs on HUK-106489 before Sunday (each writes in Hero: TEST tasks for Sabine, logbook lines, status moves, and sends a TEST mail to neumath4@icloud.com). Default: no weekend writes; release 2 first.
2. Release 2 (Sunday evening, after Matthias's explicit yes with the plain scope of effects: W2-14 republishes with Tobias added to the test recipients; nothing else changes; automatic rollback to 5ffdc4d6 on failure; nothing reaches a customer): copy the rules file to .scratch first, set `"test_empfaenger": "tobiaswimmer@me.com, neumath4@icloud.com"`, run all suites, `node tools/ww-deploy-vertrieb.mjs --trocken --aus .scratch/ww-sales-72627/candidate-w2-14.json`, dry run `node tools/ww-vertrieb-release-72627.mjs --pins-aus-bericht workspace/clients/warme-wimmer/context/maintenance/2026-10-09-w214-72627-release.json --kandidat .scratch/ww-sales-72627/candidate-w2-14.json` (errors [] and entwurf=veroeffentlicht), Hero snapshot before, apply `... --apply --pins-aus-bericht <same report> --kandidat <same> --testlauf-cred-id DWE4TI9mE7L9Gsmb`, then verify independently (live CFG recipients, acceptance execution nodes, ledger, Hero snapshot identical), rerun all suites, commit the refreshed export + infrastructure.yaml + spec last_changes on the branch, push.
3. Monday morning: pre-flight with Sabine per runbook section 7 (she shows the Hero settings for native rules on 72627, first R1 mail arrives, task path, then park HUK-106489 in Planung), each Hero write with a per-action yes; then the walkthrough per section 8 and the demo script; reset per section 9.
4. Re-publish the sticky notes if anything changes before the call.

## Not in this build (keep visible, do not act unasked)
- HUK-106488 (Max, entry 24992983) is HELD: the 2026-10-07 04:58 UTC R1 attempt has an unknown SMTP outcome. Never retry or reset it; reconcile first by asking Nico whether that TEST mail arrived.
- A Hero admin login (Raphael, or Nico's password manager) for Tobias's tab names, the missing "Termin bestätigt" tab and the upload status jump.
- The Error Handler and Watchdog still alert Nico. W2-05, W2-06 and W2-09 act on 72627 projects without a type filter (D17); decide before going live. Live mode also needs Phase B (mail reservation).
- Housekeeping: the dead session's worktree `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627` (branch merged as #1616, clean) can be pruned.

## How to work
- This is a live client's production tenant. Read-only by default. Every n8n write (update, credential, activation, test-run webhook that can act) and every Hero write (moving a project, appointments, tasks) needs a per-action yes from Matthias with a plain scope of effects and a readiness check (memory `feedback_no_invasive_action_without_ask`).
- n8n: `N8N_API_URL_WARME_WIMMER` (already ends in /api/v1) and `N8N_API_KEY_WARME_WIMMER` from the clone's `.env`; never print secrets.
- Hero reads only through `tools/ww-hero-read-guard.mjs` (6 s spacing, skip the first 90 s of each quarter hour, stop on HTTP 429); use Matthias's read key `HERO_API_KEY_MATTHIAS_WARME_WIMMER`. Never run `tools/ww-graph-*`, `ww-inbox-window`, `ww-w204-probe` or `ww-final-push-demo*`: they create temporary production workflows or send mail.
- Write helper scripts with the Write tool into your scratchpad; a hook blocks heredocs that carry backslashes. Never `git stash`, `checkout --`, `restore` or `reset --hard` in the clone; restore from `.scratch` copies with `cp`.
- German customer text: Sie-form, no em-dashes, no "--".
- Only one chat may run this prompt. Before launching any workflow, run `uv run tools/bg_watch.py list` in agentic-ops1 and check sibling sessions for a live run of the same work.

## SESSION LOOP (copy this whole section verbatim into every continuation prompt you write)
1. Measure YOUR session's context: `uv run tools/session_state.py --status` (trust it only when its `session=` matches the UUID in your scratchpad path), or the per-session `[PRESSURE: ...]` advisory. Bands on the 1M window: moderate 300k, high 500k, critical 700k. A resumed session starts near 170k before any work.
2. Measure before starting each item and after each merge or release. Never start an item that would cross 500k.
3. At moderate: keep replies short, read targeted line ranges instead of whole files, do not re-read what is already in context; let workflow agents carry the heavy reading.
4. When the next item will not fit, or context is at or past 500k: leave nothing uncommitted (commit and push the branch; open the PR even if the item is unfinished and say so in its body). Never stop half-released: if a release ran, verify it or roll it back first. Close browser sessions and clear `tools/bg_watch.py` entries of finished work.
5. Checkpoint: invoke the `/comd_checkpoint --mini` skill (never hand-roll it), with the ledger edits in a `docs/...` worktree off origin/main and `finalize --root <that worktree>`; do not clear friction candidates that belong to sibling sessions; commit, push, PR, merge on green.
6. Write the next continuation prompt: where it stands (what was built or released, with PR numbers and n8n version ids; what is in flight and why; what waits on Matthias, Tobias, Sabine, Raphael or Nico), the remaining queue in order with exact paths and live evidence, the "How to work" section, then this SESSION LOOP section verbatim. Deliver it in the reply inside a FOUR-backtick fence labelled "Continuation prompt for Claude Code:", and append the same text to the checkpoint file.
7. The closing reply of every loop iteration lays out, in the chat itself and not only inside the prompt, the items still left to work through: the remaining queue in order, then what waits on Matthias or the client.
8. At critical (700k): stop right after step 4's commit and push, then do steps 5, 6 and 7.
9. When the queue is empty, do not write another prompt: say the loop is done and list what shipped and what waits on Matthias or the client.
````
