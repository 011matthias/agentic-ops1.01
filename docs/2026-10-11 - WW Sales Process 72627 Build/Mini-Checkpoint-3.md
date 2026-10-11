# Mini-Checkpoint: WW Sales Process 72627 Build (release 4 live)

**Date:** 2026-10-11
**Status:** Release 4 live (7ec5e029); Monday 2026-10-12 pre-flight and walkthrough next
**Type:** mini

---

## Summary
Release 4 of W2-14 is live and independently verified: test mails to Sabine and Tobias (company addresses) plus Matthias, sales tasks to Tobias and all others to Sabine, the technical header note removed as Matthias decided. A background agent built and released it because this session reached 500k context.

## What Was Done
- 4f0b3cc (agent): Header W2-14 note dropped from the builder (48 nodes = 39 working + 9 notes); `--entwurf-ersetzen <id>` accepts exactly an owner-named UI draft whose working nodes and connections equal the published version and whose notes are unchanged or removed; `graphNormalisieren` treats three more editor-dropped defaults as equal; node floor 39. Suites: logic 304, guards 154, mail-logbook 54, build 53, gql 61, release-plan 48, release-72627 158 + 1 skip; five wiring points regressed and seen red.
- Release 4 published 7ec5e029-8e1e-4a66-a539-47be4f15ed17 (replaced draft d29fabd8); acceptance 51077 read-only (12189161 Altbestand, 12189064 gesperrt); record eec973d; PR #305 body row 4; runbook 5c plus pointers in sections 0 and 7.4; cheat sheet republished (version 3).
- Re-verified by this session: active = draft = 7ec5e029, 48 nodes, 9 notes, no header note, task allowlist [255797, 255830], new recipients, ledger 13, no open executions, Hero snapshot 04c byte-identical to 04b.

## What Did NOT Work (and why)
None in this step (the release-4 blocker and its fix are in Mini-Checkpoint-2).

## Current Status
W2-14 live = 7ec5e029, test mode, HUK-106489 only. PR akkton/agentic-ops#305 open at eec973d (merge on Matthias's order). Known leftover: "Notiz: 3 Entscheiden" still says "(siehe Kopfnotiz)", which no longer exists; fix in a later release.

## Next Steps
1. Monday morning: GET-only check against 7ec5e029, Hero snapshot 05 vs 04c, pre-flight with Sabine (runbook 7).
2. Walkthrough (runbook 8), reset (runbook 9), merge PR #305 on order.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5c, 7 to 9)

---

## Continuation prompt

```
Continue the Wärme Wimmer (WW) W2-14 work: Tobias's heat-pump sales process on Hero type 72627, Monday 2026-10-12 walkthrough with Tobias and Sabine.

## Where it stands (2026-10-11, about 19:20 Berlin)
- Read memory `project_warme_wimmer_takeover.md` first. All WW code and private context live in the clone `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (akkton/agentic-ops), NOT in agentic-ops1; work there with absolute paths. Checkpoints in agentic-ops1: `docs/2026-10-11 - WW Sales Process 72627 Build/Mini-Checkpoint-3.md` (release 4), Mini-Checkpoint-1 and -2 (releases 3 and the release-4 blocker).
- LIVE = RELEASE 4: W2-14 (n8n NPHbbRF2NVAbUyzF) publishes 7ec5e029-8e1e-4a66-a539-47be4f15ed17 = draft, 48 nodes (39 working + 9 explain-notes, no header note). Test mode, test_nur_testlauf, allowlist [12189161], test_empfaenger "sabine.wimmer@waerme-wimmer.de, tobias.wimmer@waerme-wimmer.de, neumath4@icloud.com" (owner: company addresses only for Sabine and Tobias), test_aufgaben_rollen {"vertrieb": 255830} = Tobias gets R6 call customer, R7 send offer, R10 phone follow-up, R13 offer lost, R17 AZ/AB; all other tasks to Sabine 255797. go_live 2026-10-09T18:02:23Z, webhook header auth credential DWE4TI9mE7L9Gsmb, cron 5,20,35,50 6-19 Mon-Fri. Acceptance 51077 read-only. vertrieb_log 13 rows. Hero snapshot `.scratch\ww-sales-72627\snapshots\04c-nach-release-4.json`. Release report `workspace\clients\warme-wimmer\context\maintenance\2026-10-11-w214-72627-release-auf-6963954a.json`: the next release pins with `--pins-aus-bericht <it> --testlauf-cred-id DWE4TI9mE7L9Gsmb`. History: f4f96005 (13293) -> 5ffdc4d6 (R1) -> 13d662e5 (R2) -> 6963954a (R3, notes) -> 7ec5e029 (R4).
- Release-tool flags for edge cases: `--rollback-snapshot <folder>/rollback-readback.json` (own rollback draft), `--entwurf-ersetzen <draft id>` (owner-named UI draft with unchanged working nodes). Use only when the case actually occurs.
- Both test projects untouched in step 847254: HUK-106489 = 12189161 ("TESTPROJEKT BIENE"), HUK-106488 = 12189064 (blocked).
- PR akkton/agentic-ops#305 (branch client/warme-wimmer/w2-14-sales-process-72627, head eec973d) is OPEN with releases 1-4 in its body. No CI in that repo: merge only on Matthias's order.
- Rules file `workspace\clients\warme-wimmer\context\vertrieb-rules.json` (gitignored) equals live (release 4).
- Suites (from the clone root, all must exit 0): logic 304, guards 154, mail-logbook 54, build 53, gql 61, release-plan 48, release-72627 158 + 1 skip (commands: node tools/ww-vertrieb-{logic,guards,mail-logbook,build,gql}-test.mjs; node --test tools/ww-vertrieb-{release-plan,release-72627}-test.mjs).
- Runbook `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (5c = release 4; sections 0 and 7.4 carry pointers that R6/R7 tasks now go to 255830; 7 pre-flight, 8 walkthrough, 9 reset). Cheat sheet (German, version 3, current): https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz (Tobias ticks the sales tasks in demo steps 6 and 8, "oder Sabine für ihn"; never forward a TEST mail to hero.automation@, because W2-11 triage trusts mails from sabine.wimmer@ and would create real tasks).
- Read-only helpers: `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\tools\` (verify-release.mjs `<version> <execution id>`, hero-snapshot.mjs `<out.json>`, cfg-diff.mjs, dry-summary.mjs, wait-berlin.mjs, rules-summary.mjs, edit-spickzettel.mjs).
- Matthias runs nothing himself ("you have to do it"): the agent runs every step, each write with his yes. If this session's context is short, delegate a bounded step to a background agent with an exact brief and verify its result independently.

## Do next, in order
1. Monday 2026-10-12 morning, before the call: GET-only check (verify-release.mjs 7ec5e029-8e1e-4a66-a539-47be4f15ed17 <newest execution id>; expect 48 nodes, draft = published, no open executions, ledger 13; Monday cron runs from 06:05 should be trigger-mode successes that skip the test project) and Hero snapshot `.scratch\ww-sales-72627\snapshots\05-montag-vor-vorlauf.json` compared with 04c. Then the pre-flight with Sabine per runbook section 7: she shows the Hero settings for native rules on 72627; first R1 TEST mail (now reaches Sabine, Tobias and Matthias); task path (R6/R7 tasks land with Tobias); then park HUK-106489 in Planung. Every Hero write and every test run gets a per-action yes from Matthias with the plain scope of effects (one up-front yes for the whole runbook-8 script is acceptable if he gives it explicitly).
2. Walkthrough per runbook section 8 and the demo script; canvas notes left to right first, then Hero.
3. Reset per runbook section 9.
4. Next release (not before Matthias asks): fix "Notiz: 3 Entscheiden" text "(siehe Kopfnotiz)", which points at the removed header note.
5. Merge PR #305 only when Matthias orders it.

## Not in this build (keep visible, do not act unasked)
- HUK-106488 (Max, entry 24992983) is HELD: the 2026-10-07 04:58 UTC R1 attempt has an unknown SMTP outcome. Never retry or reset it; reconcile first by asking Nico.
- A Hero admin login (Raphael or Nico) for tab names, the missing "Termin bestätigt" tab and the upload status jump.
- Error Handler and Watchdog still alert Nico. D17: W2-05, W2-06, W2-09 act on 72627 without a type filter; decide before live. Live also needs Phase B (mail reservation) and real role owners (rollen are null except katja).
- Spec gate HIGH (pre-existing): `specs/1-spec/a5-vertriebsprozess.md` says `stage: test` in `1-spec/`.
- Housekeeping: merged checkpoint worktrees `C:\Users\neuma_p1qrsic\Repo\agentic-ops1-ckpt-ww72627` and `-r2` to `-r6` can be pruned.

## How to work
- Live client production tenant. Read-only by default. Every n8n write and every Hero write needs Matthias's per-action yes with a plain scope of effects and a readiness check (memory `feedback_no_invasive_action_without_ask`). Standing condition: mails reach Matthias; every change stays inside the test setup (W2-14, HUK-106489, test mode).
- Nobody else edits W2-14 in the n8n UI; if the draft id differs from the published one, diff draft vs published read-only before anything else.
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
