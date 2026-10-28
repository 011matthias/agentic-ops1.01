# Mini-Checkpoint: WW Sales Process 72627 Build

**Date:** 2026-10-09
**Status:** Release 2 live (W2-14 13d662e5); Monday pre-flight, walkthrough and reset remain
**Type:** mini

---

## Summary
Matthias declined weekend test runs, which removed the reason to hold release 2 until Sunday. He approved it for Friday evening; it published 13d662e5 at 20:09 UTC with Tobias added to the test recipients and was verified outside the release tool.

## What Was Done
- GET-only check at session start: W2-14 still on 5ffdc4d6, no open executions, ledger 13 rows.
- Decision 1 (AskUserQuestion): no weekend Hero writes or test runs.
- Release-2 prep: rules-file backups in the clone's `.scratch/ww-sales-72627/` (`vertrieb-rules.v02-nach-release-1-2026-10-09.json`, `vertrieb-rules.v02-release-2-kandidat-2026-10-09.json`); `test_empfaenger` set to the two-address owner list; candidate `.scratch/ww-sales-72627/candidate-r2.json` (sha256 adcdb91a...); dry run `errors: []`, `entwurf=veroeffentlicht`, only `Webhook: Testlauf`, `Kandidaten` and `Faellige Aktionen` changed. Independent CFG diff confirmed `test_empfaenger` is the only difference.
- Fixed a test fixture (akkton/agentic-ops e2441e1): the release-2 tests rebuilt "release 1" from the live rules file. Once the file carried the release-2 recipients, R1 and R2 were identical, and "Release 2: abgelehnter PUT" failed. Release 1 is now pinned to neumath4 only, and the fixture asserts that R1 differs from R2. The suite now passes with the rules file in either state.
- Decision 2: Matthias said "release 2 now, just make sure emails and stuff get sent to me and any changes in hero or n8n only happen within the grounds of this project's test set up". Readiness check passed: in test mode every mail goes to the CFG list (both addresses in To, reply-to the same list), the customer address is never used, and HUK-106489 was in 847254 on its 10-06 entry.
- Release 2 apply: `candidateVersionId` 13d662e5-5469-4c3a-9dbb-2ca3869d5889, acceptance execution 50850 (read nodes plus the protocol NoOp; 12189161 Altbestand, 12189064 gesperrt), no rollback. Report: `workspace/clients/warme-wimmer/context/maintenance/2026-10-09-w214-72627-release-auf-5ffdc4d6.json` (gitignored).
- Independent verification: live CFG equals the candidate; `vertrieb_log` still has 13 rows; Hero snapshots `03-vor-release-2.json` and `04-nach-release-2.json` are identical; all 7 suites green (304/143/54/48/61/48/130+1 skip).
- Recorded in a633e89 (export, `infrastructure.yaml` release_2 block, spec a5 trigger/last_changes/next_steps). PR #305 body now has a release table. Runbook section 5 is marked DONE.

## What Did NOT Work (and why)
- **Release-72627 suite after runbook 5.2:** "Release 2: abgelehnter PUT" failed (`applied: true`, expected false). The fixtures derived R1 from the live rules file, so after 5.2 the candidate PUT hashed equal to the rollback payload and the mock accepted it. Fixed in e2441e1.

## Current Status
- W2-14 (n8n NPHbbRF2NVAbUyzF) publishes 13d662e5. Test mode, `test_nur_testlauf`, allowlist [12189161], recipients Tobias + Matthias, tasks only to 255797. The cron (Mon-Fri 06-19) skips test projects; only an authenticated test run acts.
- PR akkton/agentic-ops#305 is open at a633e89 (commits 2d61919, d37f39f, f51d41e, e2441e1, a633e89). That repo has no CI, so it merges only on Matthias's order.
- HUK-106489 (12189161) and HUK-106488 (12189064) are untouched, both in 847254.

## Next Steps
1. Monday 2026-10-12: pre-flight with Sabine (runbook section 7), walkthrough (section 8), reset (section 9). Each Hero write needs its own yes.
2. Merge #305 on Matthias's order.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (sections 7, 8, 9)
- This file's continuation prompt (below)

---

## Continuation prompt (Monday)

````
Continue the Wärme Wimmer (WW) W2-14 work: Tobias's heat-pump sales process on Hero type 72627, Monday 2026-10-12 walkthrough with Tobias and Sabine.

## Where it stands (2026-10-09, about 22:20 Berlin)
- Read memory `project_warme_wimmer_takeover.md` first. All WW code and private context live in the clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (akkton/agentic-ops), NOT in agentic-ops1; work there with absolute paths. Checkpoints: `docs/2026-10-09 - WW Sales Process 72627 Build/Mini-Checkpoint-3.md` in agentic-ops1 (Mini-Checkpoint-2 for release 1).
- RELEASE 2 IS LIVE (owner yes 2026-10-09, moved up from Sunday because Matthias declined weekend test runs): W2-14 (n8n NPHbbRF2NVAbUyzF) publishes 13d662e5-5469-4c3a-9dbb-2ca3869d5889 (release 1 was 5ffdc4d6, before that f4f96005 on type 13293). Only change: test_empfaenger "tobiaswimmer@me.com, neumath4@icloud.com" (both in To, reply-to the same list). Acceptance execution 50850 success, read nodes + protocol NoOp only. Verified independently: live CFG type 72627, test mode, test_nur_testlauf, allowlist [12189161], go_live 2026-10-09T18:02:23Z, tasks only to 255797 (Sabine), webhook header auth with credential DWE4TI9mE7L9Gsmb; vertrieb_log 13 rows; Hero snapshots `.scratch\ww-sales-72627\snapshots\03-vor-release-2.json` and `04-nach-release-2.json` identical. Report: `workspace\clients\warme-wimmer\context\maintenance\2026-10-09-w214-72627-release-auf-5ffdc4d6.json` (gitignored). A later release pins with `--pins-aus-bericht <that report>` and `--testlauf-cred-id DWE4TI9mE7L9Gsmb`.
- No weekend writes (owner decision 2026-10-09): nothing ran on HUK-106489 since release 1. Cron 5,20,35,50 6-19 Mon-Fri runs but skips test projects in test mode; only an authenticated test run (`node tools/ww-deploy-vertrieb.mjs --testlauf --projekt 12189161`) acts.
- Both test projects untouched, in step 847254: HUK-106489 = 12189161 (entry 24993267, 10-06 12:17:37 UTC), HUK-106488 = 12189064 (entry 24992983, blocked).
- PR akkton/agentic-ops#305 (branch client/warme-wimmer/w2-14-sales-process-72627, head a633e89; commits 2d61919 build, d37f39f release-1 record, f51d41e release-2 support, e2441e1 release-2 fixture fix, a633e89 release-2 record) is OPEN with a release table in its body. No CI in that repo: merge only on Matthias's order.
- Rules file `workspace\clients\warme-wimmer\context\vertrieb-rules.json` (gitignored) equals live (release-2 values). Backups in `.scratch\ww-sales-72627\`: `vertrieb-rules.v02-nach-release-1-2026-10-09.json` (release 1), `vertrieb-rules.v02-release-2-kandidat-2026-10-09.json` (now live).
- Suites (from the clone root, all must exit 0): node tools/ww-vertrieb-logic-test.mjs (304); node tools/ww-vertrieb-guards-test.mjs (143); node tools/ww-vertrieb-mail-logbook-test.mjs (54); node tools/ww-vertrieb-build-test.mjs (48); node tools/ww-vertrieb-gql-test.mjs (61); node --test tools/ww-vertrieb-release-plan-test.mjs (48); node --test tools/ww-vertrieb-release-72627-test.mjs (130 pass, 1 skip). All green after release 2.
- Runbook: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (section 5 marked DONE; section 7 Monday pre-flight, section 8 walkthrough, section 9 reset). Sticky notes (German, v2): https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz, already describing the release-2 state ("Nur bei Tobias und in Kopie bei mir"); local copy in session 7fa4ebf9's scratchpad (`ww-spickzettel.html`); to update from a new chat: Artifact read, edit, republish with url.
- Read-only helpers in session 7fa4ebf9's scratchpad (`C:\Users\NEUMA_~1\AppData\Local\Temp\claude\c--Users-neuma-p1qrsic-Repo-agentic-ops1\7fa4ebf9-12ea-49b7-ae25-92eb5ec729c7\scratchpad\`; copy them): hero-snapshot.mjs (guarded Hero read on Matthias's key: `node hero-snapshot.mjs <out.json>`), verify-release.mjs (GET-only: `node verify-release.mjs 13d662e5-5469-4c3a-9dbb-2ca3869d5889 <execution id>`), cfg-diff.mjs (GET-only live CFG vs a candidate), dry-summary.mjs (summarize a release report), wait-berlin.mjs (Git Bash TZ is UTC; use this for Berlin times).

## Do next, in order
1. Monday 2026-10-12 morning, before the call: start with the GET-only state check (verify-release.mjs with the version above and the newest execution id; expect 13d662e5 active, no open executions, ledger 13 rows) and a Hero snapshot `05-montag-vor-vorlauf.json` compared with 04. Then the pre-flight with Sabine per runbook section 7: she shows the Hero settings for native rules on 72627; first R1 TEST mail (now arrives at Tobias AND Matthias); task path; then park HUK-106489 in Planung. Every Hero write and every test run gets a per-action yes from Matthias with the plain scope of effects.
2. Walkthrough per runbook section 8 and the demo script, each write with its yes.
3. Reset per runbook section 9.
4. Re-publish the sticky notes if anything changes before the call.
5. Merge PR #305 only when Matthias orders it.

## Not in this build (keep visible, do not act unasked)
- HUK-106488 (Max, entry 24992983) is HELD: the 2026-10-07 04:58 UTC R1 attempt has an unknown SMTP outcome. Never retry or reset it; reconcile first by asking Nico whether that TEST mail arrived.
- A Hero admin login (Raphael, or Nico's password manager) for Tobias's tab names, the missing "Termin bestätigt" tab and the upload status jump.
- The Error Handler and Watchdog still alert Nico. W2-05, W2-06 and W2-09 act on 72627 projects without a type filter (D17); decide before going live. Live mode also needs Phase B (mail reservation).
- Spec gate HIGH (pre-existing): `specs/1-spec/a5-vertriebsprozess.md` says `stage: test` while it sits in `1-spec/`; moving it changes paths that infrastructure.yaml references, so it waits for a decision.
- Housekeeping: the worktrees `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627` (merged as #1616) and `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627-r2` (this checkpoint's docs PR, once merged) can be pruned.

## How to work
- This is a live client's production tenant. Read-only by default. Every n8n write (update, credential, activation, test-run webhook that can act) and every Hero write (moving a project, appointments, tasks) needs a per-action yes from Matthias with a plain scope of effects and a readiness check (memory `feedback_no_invasive_action_without_ask`). Matthias's standing condition (2026-10-09): mails reach him, and every Hero/n8n change stays inside this project's test setup (W2-14, HUK-106489, test mode).
- n8n: `N8N_API_URL_WARME_WIMMER` (already ends in /api/v1) and `N8N_API_KEY_WARME_WIMMER` from the clone's `.env`; never print secrets. The n8n MCP server in agentic-ops1 is not the WW instance; use the REST helpers.
- Hero reads only through `tools/ww-hero-read-guard.mjs` (6 s spacing, skip the first 90 s of each quarter hour, stop on HTTP 429); use Matthias's read key `HERO_API_KEY_MATTHIAS_WARME_WIMMER`. Never run `tools/ww-graph-*`, `ww-inbox-window`, `ww-w204-probe` or `ww-final-push-demo*`: they create temporary production workflows or send mail.
- Write helper scripts with the Write tool into your scratchpad; a hook blocks heredocs that carry backslashes. Never `git stash`, `checkout --`, `restore` or `reset --hard` in the clone; restore from `.scratch` copies with `cp`. `/tmp` in Git Bash is not visible to Windows node; write logs into `.scratch` or the scratchpad.
- German customer text: Sie-form, no em-dashes, no "--".
- Only one chat may run this prompt. Before launching any workflow, run `uv run tools/bg_watch.py list` in agentic-ops1 and check sibling sessions (ListAgents) for a live run of the same work.

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
