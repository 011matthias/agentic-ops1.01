# Checkpoint: Brisken Rome T3 Truth + Sales Nav Reconcile

**Date:** 2026-07-13
**Status:** Deliverables built + pushed (leadgen/task-7); Sales Nav list still being filled by owner

---

## Summary
Started as the Rome "Tier 3 booth/token-network" LinkedIn task (leadgen/task-7), then the owner corrected the premise: the real Tier 3 is whoever sits in Dirk's Outlook "T3 Following up" drafts (the sheet `Tier=T3` cold-reconnect set), not the `fob_encoded` booth network the task brief named. Rebuilt the real Tier-3 LinkedIn roster, reconciled the live Sales Nav list against the SharePoint master (65 on / 132 in scope / 67 missing), and wrote the "list = maximal coverage, tiers = outreach only" directive into context + memory.

---

## What Was Done This Session
### Tier-3 LinkedIn (leadgen/task-7, all pushed)
1. Built the initial booth/token roster (29, from the brief's `fob_encoded` premise), both runbooks, resolved-profiles (24/29), Sales Nav runbook.
2. Owner correction: traced "Tier 3" to its root — the sheet `Tier` column ("Tier column is the authority", per the T3 send pack) → the T3 send pack → Dirk's 25 Outlook drafts. Verified 25/25 draft recipients are `Tier=T3`, only 3 overlap the booth roster.
3. Rebuilt the REAL Tier-3 roster (`output/leadgen-task-7/tier3-real/`): 25 cold-reconnect prospects, connect runbook (3 booth / 21 conference / 1 no-show openers, no pitch), Sales Nav runbook, resolved-profiles (12/25 verified, 13 Sales Nav only — Saudi Aramco/Mobily/Norsk Hydro clusters have no public profiles).
4. Handed the 25 to Sales Nav in 5 throttle-safe tab batches over CDP; flagged 5 cross-tier dupes (3 booth-legit Katkoria/Forst/Blauth; 2 mislabeled-in-task-5 Ehlers+Timeshov, who are `Tier=T3` per drafts).

### Sales Nav list reconcile (vs SharePoint master)
5. Read the live "TA Cook Rome 26" list (65 members, 3 pages) via a fresh-tab CDP reader; reconciled against the SP DN-Edits master (132 in-scope). Result: **67 missing** (H5 2, T1 10, T2 9, T3 8, GA 38); 66 addable (drop the `Hardik(Hrisha Papa)` DUPLICATE row).
6. Fixed the reconcile tool: repointed to the SP master, made it read ALL pages (was hardcoded page1/page2, undercounting), fixed the matcher for abbreviated/reordered display names.

### Scope directive → context + memory
7. Wrote the owner directive (Sales Nav list = maximal coverage; tier/warmth is only for LinkedIn + email outreach, never list membership; GA-in; only STOP off) into 3 context files + memory.

---

## Key Decisions Made
### "Tier 3" is defined by the sheet Tier column + Dirk's drafts, not the task label
- **Choice:** Treat the master sheet `Tier` column (instantiated in Dirk's drafts) as the authority for tier membership; the task brief's "booth/token = fob_encoded" segment claim was a mislabel.
- **Rationale:** The T3 email task's own send pack scopes to `Tier=T3` and says "Tier column is the authority"; 25/25 drafts confirm it. The booth roster overlaps the real T3 by only 3 people.

### Sales Nav list is maximal-coverage, decoupled from tiers
- **Choice:** Every non-STOP named contact (132) goes on the list, GA included; tiers only drive outreach copy/cadence.
- **Rationale:** Owner directive 2026-07-13. Downstream value is job-change alerts, next-event audience, account mapping, CRM seed — which need breadth, not tier-filtering.

---

## Files Modified
| File | Action | Purpose |
|------|--------|---------|
| output/leadgen-task-7/tier3-real/* | Created | Real Tier-3 roster + runbooks + resolved-profiles (25) |
| output/leadgen-task-7/notes-for-other-tasks.md | Modified | T3-truth correction; Ehlers+Timeshov mislabeled in task-5 |
| output/leadgen-task-7/{SUMMARY,tier3-roster.csv,runbooks} | Modified | Relabel booth roster; Premium note decision |
| memory/project_brisken_rome_tier3_is_drafts.md | Created | Canonical T3 = drafts, not booth (source-of-truth rule) |
| memory/project_brisken_rome_leadgen_task_branches.md | Created | leadgen/task-N branch map + æ/ø dedup pitfall |
| memory/project_brisken_rome_salesnav_list.md | Modified | Max-inclusive scope directive + reconcile status |
| memory/reference_repo_tooling_gotchas.md | Modified | Workflow CRLF/args + auto-mode push-deny gotchas |
| context/.../targeting/sales-nav-add-list-rome2026.md | Modified | Scope directive (list-filling side) |
| context/.../Rome-Event/post-event-sequences.md | Modified | Scope note (outreach side) |
| context/.../Rome-Event/rome-post-event-plan.md | Modified | Track A max-inclusive scope |
| .scratch/reconcile_salesnav.py | Modified | Repoint SP master + all-pages + matcher fix |
| .scratch/read_list_owntab.py | Created | Fresh-tab all-pages Sales Nav list reader |

---

## Current Status
Tier-3 deliverables complete and pushed on `leadgen/task-7` (through commit `5edb67a`). Real Tier-3 roster is the canonical one; booth roster relabeled as plan track 1. Sales Nav list reconcile done: 65/132 on, 66 addable, GA the big gap. Owner is filling the list manually (adding is manual; Sales Nav has no bulk save-to-list). Scope directive is written into context + memory.

---

## Next Steps
1. Continue filling the Sales Nav list toward all 132 (66 still to add; GA-in). Hand the missing in throttle-safe tab batches — the 20 GA with captured URLs resolve instantly.
2. When outreach resumes: use the tiers for the message/cadence only; the real Tier-3 LinkedIn connect notes are ready in `tier3-real/runbook-linkedin-connect.md` (Dirk's Premium account, ~20/day, no pitch).
3. Task-5 owner: drop Ehlers + Timeshov from its Tier-2 roster (they're Tier-3 per the drafts).

---

## Context for Next Session
### Files to Read First
- output/leadgen-task-7/tier3-real/README.md + roster.csv (the real Tier-3)
- memory/project_brisken_rome_tier3_is_drafts.md (why T3 = drafts)
- workspace/clients/brisken/context/lead-generation/targeting/sales-nav-add-list-rome2026.md (list scope + reconcile method)
- .scratch/salesnav_gap.json (the 67 missing)

### Open Questions
- Shell cc's (Askew/Kerr/Appelman/Liew): add to the list? Askew is Dirk's live call thread.
- The 5 sheet-`Tier=T3` rows not in drafts (Boclinca no-channel, Opanasyk/Wandhoefer/Hill already in task-5, Graham not drafted) — LinkedIn handling.

### Working Notes
- Live Sales Nav list read: `.scratch/read_list_owntab.py` (fresh tab, loops pages). Reconcile: `.scratch/reconcile_salesnav.py` (SP master, all pages, alias map for abbreviated display names).
- SP master mirror (pulled today): `workspace/clients/brisken/context/lead-generation/targeting/TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx`, 295 rows / 132 in-scope.
- 13 of the 25 real-T3 have no public LinkedIn profile (Saudi Aramco/Mobily/Norsk Hydro); confirm in Sales Nav by role+company, skip if none fits.
- Adding to a Sales Nav list is manual (save only exists on the lead page); the agent can open tabs over CDP, the human saves.

### Reference Materials
- Sales Nav list: linkedin.com/sales/lists/people/7477347207906676736
- SP master: /sites/MARKETING/Shared Documents/30_Events/TA Cook/TA Cook 2026/TAC Rome2026-post-event-master-contacts_260627_DN-Edits.xlsx

---

## How to Continue
To keep filling the list: run the two scratch scripts to get the current missing set, then open batches of ~5 Sales Nav search tabs via `.scratch/open_tabs.py` for the owner to save. To resume outreach: the tier-3 connect runbook is ready; tiers drive message only.

---

## Strategic Feedback

### What Worked Well This Session
- The owner pointing at Dirk's draft box as ground truth was the single highest-leverage correction; empirical state (what's actually in the mailbox) beat the inherited task label. Worth defaulting to "verify the segment against the live artifact" before building any tier roster.

### Suggestions
- The leadgen task briefs are written by prior sessions and can carry stale/false premises (here: "fob_encoded = the T3 segment"). Before executing a task brief's segment claim, cross-check it against the sheet `Tier` column and Dirk's drafts (B7 enumerate-before-build).

### System Health
- The `.scratch/reconcile_salesnav.py` tool silently undercounted (hardcoded page1/page2) and mis-matched abbreviated names — a scratch tool doing load-bearing reconciliation. If Sales Nav reconciliation recurs, promote a hardened version to `tools/` with page-looping + the alias map baked in.
- Autonomy score: 4 human interventions this session (elevated — 1 major segment redirect, 1 cross-tier dupe catch, 2 B1 closing-offer nudges). The segment redirect is now closed by memory + B7.
