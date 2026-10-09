# Mini-Checkpoint: WW Sales Process 72627 Build

**Date:** 2026-10-09
**Status:** Design done and adversarially reviewed; build workflow running on a branch; sticky notes published; nothing deployed
**Type:** mini

---

## Summary
Matthias inherited Nico's open Wärme Wimmer task: walk Tobias and Sabine through the new heat-pump sales process in Hero on a real test project and let them test it themselves. On owner order ("build the rest of it ... against the new Wärmepumpe tabs") the remaining stages are being built into W2-14 on Hero type 72627, test mode only, for a walkthrough on Monday 2026-10-12.

## What Was Done
- Briefed Matthias from the handover (Nico's mail, issue akkton/unpauseai-web#55, the 22 Sep and 6 Oct recordings, Tobias's drawing `23-Projekte Automatisierung.pdf`): what Tobias/Sabine expect, the stage list, the tools, the difference between Terminiert and Termin bestätigt, and Sabine's three open operations points including the upload status jump.
- Live read-only checks (2026-10-09): n8n has no failed production run since 10-07; W1-06 Messeformular processed 5 real leads; W2-14 unchanged since 10-06 and still bound to old type 13293; the two 72627 test projects HUK-106488/106489 untouched since 10-06; type 72627 still has Hero's 13 default tabs.
- Workflow wf_9c2c25ac-b98 (10 agents: 5 readers, design, 3 adversarial reviews, revise) produced the final build spec: R1-R23 on 72627 step IDs, MAN-1/MAN-2, 7 German mail drafts, 14 task templates, 18 engine changes, pre-flight and guarded-release ladder, 22 open decisions. Saved to the agentic-ops clone `.scratch/ww-sales-72627/`.
- Created branch `client/warme-wimmer/w2-14-sales-process-72627` in `C:\Users\neuma_p1qrsic\Repo\agentic-ops` (in place, clean main) and backed up the private `vertrieb-rules.json` (sha256 28585f69...).
- Launched build workflow wf_287f540f-f75 (implement engine + rules, n8n candidate + guarded release tool, verify, 3-lens review, up to 2 fix rounds, regress-prove 11 guards, docs). Background task wt1l9oa8u, bg_watch id `ww-sales-process-build-workflow`.
- Published the German sticky notes for the call (Tobias's drawing colour code): https://claude.ai/artifact/53PJEZd2ttwrJtW3EeACQz

## What Did NOT Work (and why)
- **Switching off the upload status jump via the Hero API:** there is no mutation for status automations or document rules (84 mutations, cached introspection); it needs a Hero web admin login, which Matthias does not have yet. Put on hold by the owner.
- **Creating or renaming Tobias's tabs via the Hero API:** `update_project_type` only takes id/name/name_plural/is_default/is_active; tabs need the Hero UI. The build therefore binds to the 13 default 72627 step IDs (renaming in the UI later keeps the IDs).
- **Reading the workflow output as `data["final"]`:** the task output wraps the return value under `result`; `json.loads(raw)["result"]["final"]` works.
- **`grep -P '\x{2014}'` on Windows Git Bash:** "character value in \x{} is too large"; use Python to count U+2014/U+2013.

## Current Status
- Owner decisions: test mails to `tobiaswimmer@me.com` (recipient field takes a comma list so a verifiable address can be added for pre-call checks); test tasks to Sabine (Hero user 255797); build against type 72627; no rule may depend on an installation date; booking-visibility question goes to the call; status-jump fix on hold.
- Held R1 on HUK-106488 (step entry 24992983) stays blocked by five independent guards in the design; the demo runs on HUK-106489 only.
- Nothing deployed. The release (credential + W2-14 PUT + acceptance + automatic rollback to f4f96005) needs an explicit owner yes. warme-wimmer has no infrastructure.yaml in agentic-ops1; its home is the agentic-ops clone.

## Next Steps
1. When wf_287f540f-f75 finishes: read its result (unresolved findings, prove report), clear bg_watch `ww-sales-process-build-workflow`, commit on the branch, push, open the PR on akkton/agentic-ops (no CI; merge on owner order).
2. Ask the owner for the release yes with a plain scope-of-effects; for the pre-call smoke test add a mailbox Matthias can read to `test_empfaenger`, switch to Tobias only before the call.
3. Monday morning pre-flight with Sabine (~30 min): Hero settings walk for native rules on 72627, first R1 delivery check, task path, park HUK-106489 in "Planung"; then the walkthrough per `.scratch/ww-sales-72627/release-runbook.md`.
4. Re-publish the sticky notes if the build deviates from the design (same file path in the session scratchpad).
5. Reconcile the held R1 (ask Nico whether the 2026-10-07 04:58 UTC TEST mail arrived) before any unblock; get the Hero admin login (Raphael) for tabs and the status jump.

## Files to Read First
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\final-design.json`
- `C:\Users\neuma_p1qrsic\.claude\projects\c--Users-neuma-p1qrsic-Repo-agentic-ops1\3cc7f367-8f86-4957-bc93-afa2fb12d83d\subagents\workflows\wf_287f540f-f75\journal.jsonl`
- `C:\Users\neuma_p1qrsic\Repo\agentic-ops\.scratch\ww-sales-72627\release-runbook.md` (written by the build's docs step)
- memory `project_warme_wimmer_takeover.md`
