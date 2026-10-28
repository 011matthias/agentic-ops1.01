# Mini-Checkpoint: WW Sales Process 72627 Build (release 3, canvas notes)

**Date:** 2026-10-11
**Status:** Release 3 live (6963954a, 49 nodes, test mode); Monday 2026-10-12 pre-flight and walkthrough next
**Type:** mini

---

## Summary
On Matthias's order, W2-14 got 9 explain-notes on its n8n canvas for the Monday presentation to Tobias and Sabine, shipped as release 3 through the guarded release tool. The first attempt rolled back after a network error, which exposed and fixed a tool gap: a rollback left W2-14 un-releasable.

## What Was Done
- `notizen()` in `tools/ww-deploy-vertrieb.mjs` (agentic-ops clone): 9 sticky notes (overview, 1 Start, 2 Lesen, 3 Entscheiden, 4a Mail, 4b Hero, 4c Aufgaben, Nur Protokoll, Fehler melden), German, no expressions or addresses, text follows test/live mode. `pinsAusBericht` now reads the node count from the previous report instead of a hard-coded 40. Commit b39cda7.
- `--rollback-snapshot <release-folder>/rollback-readback.json` (commit dbe64fc): accepts only the draft our own rollback wrote (same workflow, pinned version published, own draft id, graph equal to published, live draft byte-equal to the snapshot).
- Release 3 published 6963954a-edab-4631-a1ed-3f844495e3a4; acceptance 51074 read nodes + protocol only (12189161 Altbestand, 12189064 gesperrt); ledger 13 rows; Hero snapshot `04b-nach-release-3.json` identical to 04; export refreshed and recorded (155e300); PR akkton/agentic-ops#305 body has the release-3 row.
- Suites: logic 304, guards 143, mail-logbook 54, build 51, gql 61, release-plan 48, release-72627 142 + 1 skip. Each fix regressed and seen red.
- Runbook section 5b added; memory `feedback_interrupted_tool_may_have_run` extended (classifier-denied call still ran).

## What Did NOT Work (and why)
- **First release-3 call (17:18 Berlin):** reported as denied by the auto-mode classifier, but the process had started; it wrote a backup, a report and the lock file, then died before its PUT. The stale lock (dead pid 28376) blocked the next call; archived to `.scratch/ww-sales-72627/work/release-3-abgebrochen-1718/` and removed after confirming no execution ran.
- **Second attempt (17:23):** PUT and publish of afdb8b16 passed readback, then `fetch failed` before the acceptance webhook (no execution created). Rollback restored 13d662e5 but stored the old content as draft d2be90a1, and later releases refuse any draft id other than the published one. Fixed by `--rollback-snapshot`.

## Current Status
W2-14 live = draft = 6963954a, test mode, HUK-106489 only, mails to Tobias + Matthias, tasks to Sabine. Both test projects untouched in step 847254. PR #305 open at 155e300 (merge on Matthias's order). Ops: warme-wimmer has no infrastructure.yaml in agentic-ops1 (it lives in the clone).

## Next Steps
1. Monday morning: GET-only check against 6963954a, Hero snapshot 05 vs 04b, then runbook section 7 pre-flight with Sabine (per-action yes).
2. Walkthrough (section 8), reset (section 9), merge PR #305 on order.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (sections 5b, 7 to 9)

---

## Continuation prompt

```
Continue the Wärme Wimmer (WW) W2-14 work: Tobias's heat-pump sales process on Hero type 72627, Monday 2026-10-12 walkthrough with Tobias and Sabine.

## Where it stands (2026-10-11, about 17:50 Berlin)
- Read memory `project_warme_wimmer_takeover.md` first. All WW code and private context live in the clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (akkton/agentic-ops), NOT in agentic-ops1; work there with absolute paths. Checkpoints in agentic-ops1: `docs/2026-10-11 - WW Sales Process 72627 Build/Mini-Checkpoint-1.md` (release 3), `docs/2026-10-09 - WW Sales Process 72627 Build/Mini-Checkpoint-3.md` (release 2 detail).
- RELEASE 3 IS LIVE (owner order 2026-10-11): W2-14 (n8n NPHbbRF2NVAbUyzF) publishes 6963954a-edab-4631-a1ed-3f844495e3a4 = draft, 49 nodes: the 40 working nodes unchanged plus 9 explain-notes on the canvas for the presentation (`notizen()` in tools/ww-deploy-vertrieb.mjs). Acceptance execution 51074: read nodes + protocol only (12189161 Altbestand, 12189064 gesperrt). Live CFG: type 72627, test mode, test_nur_testlauf, allowlist [12189161], test_empfaenger "tobiaswimmer@me.com, neumath4@icloud.com", tasks only to 255797 (Sabine), go_live 2026-10-09T18:02:23Z, webhook header auth with credential DWE4TI9mE7L9Gsmb, cron 5,20,35,50 6-19 Mon-Fri. vertrieb_log 13 rows. Hero snapshot `.scratch\ww-sales-72627\snapshots\04b-nach-release-3.json` identical to 04. Report: `workspace\clients\warme-wimmer\context\maintenance\2026-10-11-w214-72627-release-auf-13d662e5.json` (gitignored). The next release pins with `--pins-aus-bericht <that report>` and `--testlauf-cred-id DWE4TI9mE7L9Gsmb` (node count now comes from the report: 49). Release history: f4f96005 (type 13293) -> 5ffdc4d6 (R1) -> 13d662e5 (R2) -> 6963954a (R3).
- Release 3's first attempt published afdb8b16, hit `fetch failed` before acceptance and rolled back; the rollback's new draft id blocked later releases, fixed by `--rollback-snapshot <release-folder>/rollback-readback.json` (only needed if a rollback ever repeats). Runbook section 5b has the detail.
- Both test projects untouched, in step 847254: HUK-106489 = 12189161 (entry 24993267, 10-06 12:17:37 UTC), HUK-106488 = 12189064 (entry 24992983, blocked).
- PR akkton/agentic-ops#305 (branch client/warme-wimmer/w2-14-sales-process-72627, head 155e300; release-3 commits b39cda7 notes, dbe64fc rollback snapshot, 155e300 record) is OPEN with a release table in its body. No CI in that repo: merge only on Matthias's order.
- Rules file `workspace\clients\warme-wimmer\context\vertrieb-rules.json` (gitignored) equals live (23 active rules).
- Suites (from the clone root, all must exit 0): node tools/ww-vertrieb-logic-test.mjs (304); node tools/ww-vertrieb-guards-test.mjs (143); node tools/ww-vertrieb-mail-logbook-test.mjs (54); node tools/ww-vertrieb-build-test.mjs (51); node tools/ww-vertrieb-gql-test.mjs (61); node --test tools/ww-vertrieb-release-plan-test.mjs (48); node --test tools/ww-vertrieb-release-72627-test.mjs (142 pass, 1 skip).
- Runbook: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5b release 3 DONE; section 7 Monday pre-flight, section 8 walkthrough, section 9 reset). Sticky notes cheat sheet (German): https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz, still accurate; local copy `.scratch\ww-sales-72627\tools\ww-spickzettel.html`; to update from a new chat: Artifact read, edit, republish with url.
- Read-only helpers in the clone: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\tools\` (gitignored, absolute paths inside, run with node from the clone root): hero-snapshot.mjs (`node .scratch/ww-sales-72627/tools/hero-snapshot.mjs <out.json>`), verify-release.mjs (GET-only: `node .scratch/ww-sales-72627/tools/verify-release.mjs 6963954a-edab-4631-a1ed-3f844495e3a4 <execution id>`), cfg-diff.mjs, dry-summary.mjs, wait-berlin.mjs (Git Bash TZ is UTC), rules-summary.mjs, mail-paths.mjs, edit-spickzettel.mjs.
- Matthias does not run commands himself ("you have to do it"); the agent runs every step, each write with his yes.

## Do next, in order
1. Monday 2026-10-12 morning, before the call: GET-only state check (verify-release.mjs with 6963954a and the newest execution id; expect 49 nodes, draft = published, no open executions, ledger 13 rows; Monday cron runs from 06:05 should be trigger-mode successes that skip the test project) and a Hero snapshot `.scratch\ww-sales-72627\snapshots\05-montag-vor-vorlauf.json` compared with 04b. Then the pre-flight with Sabine per runbook section 7: she shows the Hero settings for native rules on 72627; first R1 TEST mail (arrives at Tobias AND Matthias); task path; then park HUK-106489 in Planung. Every Hero write and every test run gets a per-action yes from Matthias with the plain scope of effects.
2. Walkthrough per runbook section 8 and the demo script, each write with its yes. On the canvas, walk the notes left to right (overview, 1 Start, 2 Lesen, 3 Entscheiden, 4a/4b/4c), then switch to Hero.
3. Reset per runbook section 9.
4. Re-publish the cheat sheet if anything changes before the call.
5. Merge PR #305 only when Matthias orders it.

## Not in this build (keep visible, do not act unasked)
- HUK-106488 (Max, entry 24992983) is HELD: the 2026-10-07 04:58 UTC R1 attempt has an unknown SMTP outcome. Never retry or reset it; reconcile first by asking Nico whether that TEST mail arrived.
- A Hero admin login (Raphael, or Nico's password manager) for Tobias's tab names, the missing "Termin bestätigt" tab and the upload status jump.
- The Error Handler and Watchdog still alert Nico. W2-05, W2-06 and W2-09 act on 72627 projects without a type filter (D17); decide before going live. Live mode also needs Phase B (mail reservation).
- Spec gate HIGH (pre-existing): `specs/1-spec/a5-vertriebsprozess.md` says `stage: test` while it sits in `1-spec/`; moving it changes paths that infrastructure.yaml references, so it waits for a decision.
- Housekeeping: the merged checkpoint worktrees `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627`, `-r2`, `-r3` and `-r4` (this checkpoint's docs PR, once merged) can be pruned.

## How to work
- This is a live client's production tenant. Read-only by default. Every n8n write (update, credential, activation, test-run webhook that can act) and every Hero write (moving a project, appointments, tasks) needs a per-action yes from Matthias with a plain scope of effects and a readiness check (memory `feedback_no_invasive_action_without_ask`). Matthias's standing condition (2026-10-09): mails reach him, and every Hero/n8n change stays inside this project's test setup (W2-14, HUK-106489, test mode).
- After any interrupted, rejected or classifier-denied call that could write, read the live state back AND check local traces (the lock `.scratch\ww-sales-72627\w214-testlauf.lock`, new release reports and folders) before saying what happened (memory `feedback_interrupted_tool_may_have_run`).
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
```
