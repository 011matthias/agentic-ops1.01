# Mini-Checkpoint: WW Sales Process 72627 Build (release 4 prepared, not released)

**Date:** 2026-10-11
**Status:** Live = release 3 (6963954a); release 4 built, tested, committed (9607a1c), blocked by a UI draft the owner made; owner decided the fix
**Type:** mini

---

## Summary
Matthias ordered Sabine and Tobias as test mail recipients (company addresses only) and Tobias as a test task user (split by role). Release 4 is built and verified offline, but the GET-only dry run refuses: Matthias saved W2-14 in the n8n editor at 18:07 Berlin (deleted the yellow "Header W2-14" note); he wants that note gone for good.

## What Was Done
- Explained the automation to Matthias (what it does, how a cycle works, rules per tab, safety, gaps) and walked the Monday demo step by step (runbook section 8).
- Release-4 candidate, commit 9607a1c on akkton/agentic-ops#305: `test_empfaenger` = "sabine.wimmer@waerme-wimmer.de, tobias.wimmer@waerme-wimmer.de, [redacted iCloud address]" (OWNER_72627.testEmpfaenger replaced, [redacted me.com address] removed); new cfg `test_aufgaben_rollen: {"vertrieb": 255830}` (Tobias gets R6, R7, R10, R13, R17; Sabine 255797 everything else); logic `aufgabenEmpfaenger` + `konfigPruefen`, task-chain allowlist in the builder, owner pin + `kandidatPruefen` deep-equal in the release tool; canvas texts "Testbenutzer je nach Rolle". Rules file (gitignored) already holds the release-4 values; backup `.scratch\ww-sales-72627\vertrieb-rules.v02-release-4-kandidat-2026-10-11.json`.
- Suites: logic 304, guards 154, mail-logbook 54, build 52, gql 61, release-plan 48, release-72627 148 + 1 skip. Routing, chain allowlist and owner pin each regressed and seen red. Candidate `.scratch\ww-sales-72627\candidate-r4.json` (49 nodes).
- Checked the company-mailbox risk: no WW automation reads sabine.wimmer@ or tobias.wimmer@ inboxes; W2-11 triage watches hero.automation@ and trusts mails FROM sabine.wimmer@, so nobody may forward a TEST mail to hero.automation@.

## What Did NOT Work (and why)
- **Release-4 dry run (pins from the release-3 report):** refused with "Entwurf d29fabd8 ist nicht die veroeffentlichte Version". Matthias saved W2-14 in the editor at 16:07:47 UTC: "Header W2-14" deleted, all positions grid-snapped, UI-stripped defaults (sticky width/height/color defaults, code `mode`, webhook `responseMode`, dataTable `resource`/`options`, wait `resume`/`unit`, batch size); all code, note texts and connections identical to 6963954a. The release tool refuses any foreign draft by design.

## Current Status
Live W2-14 = 6963954a (release 3, test mode, mails to [redacted me.com address] + [redacted iCloud address], all tasks to Sabine). Draft d29fabd8 (Matthias's edit) is unpublished. The repo code and the rules file are the release-4 candidate, so the rules file no longer equals live. PR #305 open at 9607a1c.

## Next Steps
1. Tonight (releases blocked Mon-Fri 06:00-19:59): remove the Header W2-14 note from the builder, add a guarded way to replace Matthias's named draft, dry run, release 4, verify, update the cheat sheet and runbook.
2. Monday morning pre-flight, walkthrough, reset as before.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5b, 7 to 9)

---

## Continuation prompt

```
Continue the Wärme Wimmer (WW) W2-14 work: Tobias's heat-pump sales process on Hero type 72627. FIRST finish release 4 TONIGHT (Sunday 2026-10-11; releases are blocked Mon-Fri 06:00-19:59 Berlin, so it must land before Monday 06:00), then the Monday 2026-10-12 walkthrough with Tobias and Sabine.

## Where it stands (2026-10-11, about 18:40 Berlin)
- Read memory `project_warme_wimmer_takeover.md` first. All WW code and private context live in the clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (akkton/agentic-ops), NOT in agentic-ops1; work there with absolute paths. Checkpoints in agentic-ops1: `docs/2026-10-11 - WW Sales Process 72627 Build/Mini-Checkpoint-2.md` (this handoff) and Mini-Checkpoint-1 (release 3).
- LIVE = RELEASE 3: W2-14 (n8n NPHbbRF2NVAbUyzF) publishes 6963954a-edab-4631-a1ed-3f844495e3a4, 49 nodes (40 working + 9 explain-notes), test mode, allowlist [12189161], test_empfaenger "[redacted me.com address], [redacted iCloud address]", all tasks to 255797 (Sabine), go_live 2026-10-09T18:02:23Z, webhook header auth credential DWE4TI9mE7L9Gsmb. Acceptance 51074 read-only. Release-3 report: `workspace\clients\warme-wimmer\context\maintenance\2026-10-11-w214-72627-release-auf-13d662e5.json` (pin the next release with `--pins-aus-bericht <it>` and `--testlauf-cred-id DWE4TI9mE7L9Gsmb`). vertrieb_log 13 rows. Hero snapshot `.scratch\ww-sales-72627\snapshots\04b-nach-release-3.json`.
- DRAFT d29fabd8-325b-431a-81e9-f3b06b5f65c8 (unpublished, saved by Matthias in the n8n editor 2026-10-11 16:07:47 UTC): deleted the yellow "Header W2-14" note; everything else is editor housekeeping (grid-snapped positions; stripped defaults: sticky width/height/color, code `mode`, webhook `responseMode`, dataTable `resource`/`options`/filter condition, splitInBatches `batchSize`, wait `resume`/`unit`). All code, note texts and connections are identical to 6963954a. OWNER DECISION 2026-10-11: the Header W2-14 note stays gone; release 4 may replace this draft.
- RELEASE 4 CANDIDATE (owner order 2026-10-11), commit 9607a1c on PR #305, NOT released: test mails to "sabine.wimmer@waerme-wimmer.de, tobias.wimmer@waerme-wimmer.de, [redacted iCloud address]" (company addresses only for Sabine and Tobias, owner: no private ones; OWNER_72627.testEmpfaenger changed accordingly); new cfg `test_aufgaben_rollen: {"vertrieb": 255830}` = sales tasks to Tobias Wimmer (R6 call customer, R7 send offer, R10 phone follow-up, R13 offer lost, R17 AZ/AB), everything else to Sabine 255797. The rules file `workspace\clients\warme-wimmer\context\vertrieb-rules.json` already holds these release-4 values (so it does NOT equal live); backup `.scratch\ww-sales-72627\vertrieb-rules.v02-release-4-kandidat-2026-10-11.json`. Suites green at 9607a1c: logic 304, guards 154, mail-logbook 54, build 52, gql 61, release-plan 48, release-72627 148 + 1 skip.
- The GET-only dry run refuses release 4 only because of the draft: "Spaeteres Release: Entwurf d29fabd8 ist nicht die veroeffentlichte Version". Draft rules live in `baselinePruefen` (tools/ww-vertrieb-release-72627.mjs); the existing `--rollback-snapshot` exception (dbe64fc) is the pattern to copy.
- Company-mailbox check done: no WW automation reads sabine.wimmer@ or tobias.wimmer@; W2-11 triage (staging, live to real users) watches hero.automation@ and trusts mails FROM sabine.wimmer@, so nobody may forward a TEST mail to hero.automation@ (say this in the call).
- Both test projects untouched in step 847254: HUK-106489 = 12189161 ("TESTPROJEKT BIENE", customer email [redacted T-Online address]), HUK-106488 = 12189064 (blocked).
- PR akkton/agentic-ops#305 (branch client/warme-wimmer/w2-14-sales-process-72627, head 9607a1c) is OPEN; release table in its body has releases 1-3. No CI in that repo: merge only on Matthias's order.
- Runbook `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5b = release 3; 7 pre-flight, 8 walkthrough, 9 reset). Cheat sheet https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz still says mails "nur bei Tobias und in Kopie bei mir" and tasks all to Sabine: must change after release 4. Read-only helpers: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\tools\` (verify-release.mjs, hero-snapshot.mjs, cfg-diff.mjs, dry-summary.mjs, wait-berlin.mjs, rules-summary.mjs, edit-spickzettel.mjs, local `ww-spickzettel.html`).
- Matthias runs nothing himself ("you have to do it"). His yes for release 4 is given (the order + the draft decision); still do the readiness dry run right before the write.

## Do next, in order
1. Release 4 tonight:
   a. Builder: remove the "Header W2-14" sticky (`w214-note`, `K.notiz` in tools/ww-deploy-vertrieb.mjs) so the built graph has 48 nodes (39 working + 9 notes); update build-test (node set, counts, note tests that include K.notiz), release tests (GEBAUT_KNOTEN = 48, `REVIEWED.nodes[0]` fixture at "anders.nodes[0].parameters.content"), mail-logbook test (candidateNodes) and the `KNOTEN_72627` floor in pinsAusBericht (40 working nodes: make the floor 39 or count non-sticky nodes).
   b. Release tool: accept the owner-named draft, e.g. `--entwurf-ersetzen d29fabd8-325b-431a-81e9-f3b06b5f65c8`: only when live.versionId equals it, the pinned version is published, and graphNormalisieren(draft) equals graphNormalisieren(published) after removing sticky notes from both (working nodes + connections identical); returns 'entwurf=owner-ersetzt'. Tests: positive + refusals (other id, working-node change, connection change). Regress-check it.
   c. All seven suites green; candidate `node tools/ww-deploy-vertrieb.mjs --aus .scratch/ww-sales-72627/candidate-r4.json`; GET-only dry run with `--pins-aus-bericht <release-3 report> --entwurf-ersetzen d29fabd8-... --kandidat ...`; expect diff = Header W2-14 removed + changed code nodes carrying the new CFG, nothing else.
   d. Apply (`--apply ... --testlauf-cred-id DWE4TI9mE7L9Gsmb`), verify independently (verify-release.mjs, sticky count 9, CFG recipients + test_aufgaben_rollen, acceptance read-only, ledger 13), Hero snapshot 04c vs 04b, commit the export + record, PR #305 body row 4, runbook 5c.
   e. Update the cheat sheet (Artifact read, edit, republish with url): mails go to Sabine, Tobias (company) and Matthias; tasks: Vertrieb to Tobias, rest to Sabine; demo steps 5-8: Tobias ticks "Angebot ... versenden" and "Angebot telefonisch nachfassen" (Sabine can tick on his behalf); "never forward a TEST mail to hero.automation@".
2. Monday 2026-10-12 morning: GET-only check against the release-4 version, Hero snapshot 05, pre-flight with Sabine (runbook 7; the first R1 TEST mail now reaches Sabine, Tobias and Matthias). Every Hero write and test run gets Matthias's yes.
3. Walkthrough (runbook 8), reset (runbook 9).
4. Merge PR #305 only on Matthias's order.

## Not in this build (keep visible, do not act unasked)
- HUK-106488 (Max, entry 24992983) is HELD: the 2026-10-07 04:58 UTC R1 attempt has an unknown SMTP outcome. Never retry or reset it; reconcile first by asking Nico.
- A Hero admin login (Raphael or Nico) for tab names, the missing "Termin bestätigt" tab and the upload status jump.
- Error Handler and Watchdog still alert Nico. D17: W2-05, W2-06, W2-09 act on 72627 without a type filter; decide before live. Live also needs Phase B (mail reservation) and real role owners (rollen are null except katja).
- Spec gate HIGH (pre-existing): `specs/1-spec/a5-vertriebsprozess.md` says `stage: test` in `1-spec/`.
- Housekeeping: merged checkpoint worktrees `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627`, `-r2` to `-r5` can be pruned.

## How to work
- Live client production tenant. Read-only by default. Every n8n write and every Hero write needs Matthias's per-action yes with a plain scope of effects and a readiness check (memory `feedback_no_invasive_action_without_ask`). Standing condition: mails reach Matthias; every change stays inside the test setup (W2-14, HUK-106489, test mode).
- Nobody else edits W2-14 in the n8n UI; if the draft id differs from what you expect, diff draft vs published read-only before anything else.
- After any interrupted, rejected or classifier-denied call that could write, read the live state back AND check local traces (`.scratch\ww-sales-72627\w214-testlauf.lock`, new release reports and folders) (memory `feedback_interrupted_tool_may_have_run`).
- n8n: `N8N_API_URL_WARME_WIMMER` (ends in /api/v1) and `N8N_API_KEY_WARME_WIMMER` from the clone's `.env`; never print secrets. Prefix inline node API scripts with MSYS_NO_PATHCONV=1 in Git Bash.
- Hero reads only through `tools/ww-hero-read-guard.mjs` with `HERO_API_KEY_MATTHIAS_WARME_WIMMER`. Never run `tools/ww-graph-*`, `ww-inbox-window`, `ww-w204-probe` or `ww-final-push-demo*`.
- Write helper scripts with the Write tool; a hook blocks heredocs with backslashes. Never `git stash`, `checkout --`, `restore` or `reset --hard` in the clone; restore from `.scratch` copies with `cp`. Run `gh pr checks --watch` and `gh pr merge` as separate calls.
- German customer text: Sie-form, no em-dashes, no "--".
- Only one chat may run this prompt. Check `uv run tools/bg_watch.py list` in agentic-ops1 and ListAgents first.

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
